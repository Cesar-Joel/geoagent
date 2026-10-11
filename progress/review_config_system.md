# Review — feature 3 `config_system`

**Veredicto:** CHANGES_REQUESTED

Rama `feat/3-config_system`. La feature tiene `"sdd": false`, así que no hay `specs/config_system/`. La referencia es `description` + `acceptance` en `feature_list.json`.
Archivos revisados: `src/geoagent/common/config.py`, `tests/unit/test_config.py`, `docs/config.md`, `pyproject.toml` y `progress/impl_config_system.md`.

## Evidencia ejecutada

| Comando | Resultado |
|---|---|
| `make lint` | OK (ruff check + format, `target-version = "py39"`) |
| `make test-unit` | 125 passed, 243 subtests, 0.57 s |
| `./init.sh` | exit 0, "[OK] Entorno listo" (WARN informativo de integración) |
| Rama 3.9 simulada | En el entorno no hay intérprete < 3.11: solo `/usr/bin/python3.14`, sin pyenv ni uv, y el daemon de Docker no responde. Instalé `tomli` 2.4.1 en el scratchpad con `pip --target`, forcé `sys.version_info = (3, 9, ...)` al importar `geoagent.common.config` y ejecuté `test_config`. Se usa `tomli`; 24/24 OK |
| Casos límite a mano | `GEOAGENT_HEARTBEAT_INTERVAL=nan` → se acepta `nan`. `GEOAGENT_BACKEND_URL=http://u:s3cr3t@h` → `s3cr3t` aparece en `repr()`. `ftp://u:s3cr3t@h` → `s3cr3t` aparece en el mensaje de error |

## Acceptance ↔ tests

- A1 (`config.py` con `load_agent_config()`/`load_backend_config()`): [x] lo cubren `TestPrecedence.test_defaults_when_no_file_and_no_env` y el resto del módulo.
- A2 (precedencia env > archivo > defaults, con tests): [x] lo cubren `test_file_overrides_defaults`, `test_env_overrides_file`, `test_env_overrides_default` y `test_file_path_from_env`.
- A3 (prefijo `GEOAGENT_` y mapeo en `docs/config.md`): [x] `test_unprefixed_env_is_ignored`; la tabla completa está en `docs/config.md`.
- A4 (config inválida → exit != 0 y mensaje con la clave): [x] cubren los 3 ejemplos `test_non_numeric_port`, `test_empty_backend_url`, `test_zero_max_workers` / `test_negative_max_workers_in_file`, y además `TestLoadOrExit.test_invalid_config_exits_nonzero_naming_key` (`SystemExit` != 0 y `GEOAGENT_MAX_WORKERS` en stderr). Ver el hallazgo 2: valores no finitos.
- A5 (secretos fuera de `repr()` y logs): [~] para los campos marcados como secretos sí se cumple: `test_agent_repr_hides_secrets`, `test_backend_repr_hides_secrets` y `to_safe_dict()`. Pero un secreto puede filtrarse por `backend_url` (hallazgo 1). Lo de "ni en los logs" se apoya en `to_safe_dict()`, porque `common/logging.py` todavía no existe. Lo acepto así; cuando exista el logger hay que conectarlo.
- A6 (`tests/unit/test_config.py` cubre precedencia, validación y enmascarado): [x] con las clases `TestPrecedence`, `TestValidation`, `TestLoadOrExit` y `TestSecretMasking`.

## Dependencia condicional `tomli`

- El marcador `tomli>=2.0; python_version < "3.11"` es correcto. `tomli` 2.x soporta 3.7+, su API es la misma que la de `tomllib` (`load(fp_binario)`, `TOMLDecodeError`) y el archivo se abre en `"rb"`.
- La rama de import (`sys.version_info >= (3, 11)` → `tomllib`; si no, `import tomli as tomllib`) funciona: lo comprobé por simulación, no con un 3.9 real. El fallback `tomllib = None` y el error tipado en `_read_file` están bien protegidos: `TOMLDecodeError` solo se evalúa después de la comprobación de `None`.
- Compatibilidad sintáctica con 3.9: las anotaciones `X | None`, `dict[...]` y `frozenset[...]` son seguras por `from __future__ import annotations`. `_SECRETS` no se convierte en campo del dataclass (en `_Config` está anotado, pero `_Config` no es dataclass; en las subclases no lleva anotación). Ruff con `py39` + `UP` no da avisos. La validación definitiva será la matriz 3.9 de la CI.
- Justificación (C3): la dependencia no tiene spec porque la feature tiene `sdd: false`. Está justificada en `progress/impl_config_system.md` y `docs/config.md`, y solo se instala en < 3.11. La doy por aceptable, pero queda como decisión que debe ratificar el humano (ver más abajo).

## Decisiones del implementer sin respaldo explícito

- **Solo TOML, sin YAML.** No contradice el acceptance: ningún criterio exige YAML. "TOML/YAML" en la description se lee como alternativa de formato, y el principio 2 de la arquitectura desaconseja añadir PyYAML sin necesidad. Está documentado en `docs/config.md`. No bloquea, pero lo debe ratificar el humano, porque la description admite la lectura "ambos".
- **Secretos solo por entorno y rechazo si aparecen en el archivo.** Es coherente con "sin secretos en disco en claro" de la description y con la arquitectura. No contradice nada.
- **Nombres y defaults de las claves.** Son razonables y están documentados. `GEOAGENT_HOST`/`GEOAGENT_PORT` son genéricos, pero solo los usa el backend. No contradice nada.
- **Exit code 2.** El acceptance pide != 0; el 2 cumple y coincide con la convención de error de uso de `argparse`. No contradice nada.
- **Claves desconocidas en el archivo se rechazan, pero las variables `GEOAGENT_*` desconocidas se ignoran sin aviso.** Por ejemplo, una errata como `GEOAGENT_MAX_WORKER` pasa desapercibida. Es asimétrico, aunque defendible porque el espacio de entorno es compartido entre agente y backend. No bloquea (ver la recomendación r2).

## Checkpoints

- C1: [x] están los archivos base y los 4 docs; `./init.sh` termina con exit 0.
- C2: [x] solo la feature 3 está en `in_progress`; las features `done` tienen tests en verde; `progress/current.md` describe la sesión activa.
- C3: [ ] `src/geoagent/` solo contiene los paquetes previstos y no hay TODOs. Pero `load_or_exit` usa `print(..., file=sys.stderr)`, y la arquitectura dice "No usar `print()` para errores" (hallazgo 3). Además, `backend_url` permite que un secreto embebido llegue a `repr()` y a los mensajes de error (hallazgo 1). Lo de `tomli` se acepta, pendiente de que lo ratifique el humano.
- C4: [x] los tests usan `tempfile.TemporaryDirectory()`, no hay red ni mocks de filesystem, y `make test-unit` tarda < 60 s. La cobertura ≥ 85% sigue sin poder medirse (`pytest-cov` no está en `[dev]`; es el pendiente m8 heredado). Por inspección, solo quedan sin cubrir ramas menores (`OSError` al leer, `bool` en `_parse_int`/`_parse_float`, `log_level` inválido, `queue_url` sin esquema).
- C5: [x] por ahora: no hay archivos sueltos sospechosos (`__pycache__` está ignorado). La entrada en `history.md` corresponde al cierre, que todavía no ha ocurrido.
- C6: [x] no aplica (`sdd: false`).

## Cambios requeridos

1. **`backend_url` puede filtrar credenciales.** `_http_url` acepta `http://user:token@host`. Esa URL sale tal cual en `repr()`/`to_safe_dict()`, y además el mensaje de error de `_http_url` repite la URL completa (`got {text!r}`). `queue_url` ya rechaza las credenciales embebidas; `backend_url` debe hacer lo mismo (el agente usa `auth_token`). El mensaje de error de URL tampoco debe repetir el valor crudo. Hay que añadir tests: credenciales en `backend_url` → `ValidationError` con la clave, y el secreto ausente del mensaje.
2. **Se aceptan valores no finitos.** `_positive_float` acepta `"nan"` (`nan <= 0` es `False`) e `"inf"` en `heartbeat_interval` y `request_timeout`. Eso rompe la "validación temprana": un timeout `nan` o `inf` contradice además "toda llamada de red lleva timeout explícito". Hay que rechazarlos con `math.isfinite` y añadir un test por cada uno.
3. **`print()` para un error.** `load_or_exit` usa `print(f"invalid configuration: {exc}", file=sys.stderr)`. `docs/architecture.md` ("Qué NO hacer") prohíbe `print()` para errores y pide `sys.stderr` en los CLI. Hay que usar `sys.stderr.write(f"invalid configuration: {exc}\n")`. El test actual sigue valiendo.

## Recomendaciones (no bloquean)

- r1. Cuando exista `common/logging.py`, el logger debe enmascarar `AgentConfig`/`BackendConfig` mediante `to_safe_dict()`, con un test que compruebe la ausencia del secreto en la salida JSON.
- r2. Valorar un aviso (no un error) ante variables `GEOAGENT_*` desconocidas.
- r3. El humano debe ratificar: solo TOML (sin YAML), `tomli` condicional sin spec y exit code 2.

---

## Ronda 2

**Veredicto:** APPROVED

### Evidencia ejecutada

| Comando | Resultado |
|---|---|
| `make lint` | OK (`ruff check`: all checks passed; `ruff format --check`: 18 archivos ya formateados) |
| `make test-unit` | 130 passed, 255 subtests, 0.58 s |
| `./init.sh` | exit 0, "[OK] Entorno listo" (WARN informativo de integración) |
| `grep -rn "print(" src/` | sin resultados |
| Casos límite a mano | `http://u:s3cr3t@h`, `http://:s3cr3t@h` y `https://s3cr3t@h` → `ValidationError` "GEOAGENT_BACKEND_URL: must not embed credentials; use auth_token", sin el secreto. `GEOAGENT_REQUEST_TIMEOUT=1e400` (desborda a `inf`) y `nan` → "must be a finite number" |

### Hallazgos de la ronda 1

1. **Credenciales en `backend_url`:** [x] resuelto. `_http_url` rechaza `username`/`password` embebidos igual que `_queue_url`, y ninguno de sus dos mensajes repite el valor crudo. Al no poder construirse un `AgentConfig` con credenciales en la URL, estas no pueden llegar a `repr()`/`to_safe_dict()`. Lo verifican tests significativos: `test_backend_url_with_credentials_rejected_without_leak` (dos formas, `user:pass@` y `token@`, comprueba la clave en el error y la ausencia de `s3cr3t`) y `test_invalid_backend_url_error_does_not_echo_value` (esquema inválido con credenciales, sin eco).
2. **`nan`/`inf` en floats:** [x] resuelto. El nuevo `_finite_float` usa `math.isfinite` y lo usa `_positive_float`, así que cubre `heartbeat_interval` y `request_timeout`. Lo verifican `test_non_finite_floats_rejected` (10 subtests: 2 claves × `nan`/`inf`/`-inf`/`NaN`/`Infinity`, con la clave en el error vía `assert_invalid`) y `test_non_finite_float_in_file_rejected` (`inf` nativo de TOML desde el archivo).
3. **`print()` en `load_or_exit`:** [x] resuelto. Se usa `sys.stderr.write(...)`, conforme a `docs/architecture.md` (stderr en los CLI) y a `docs/conventions.md` (nada de `print()`). Como `common/logging.py` aún no existe, usar stderr es lo correcto por ahora. Lo verifica `test_error_goes_to_stderr_not_stdout` (stdout vacío, stderr con el prefijo y el salto de línea final).

### Acceptance de la feature 3 (sin regresiones)

- A1–A6: [x] siguen cubiertos por los mismos tests que en la ronda 1, todos en verde. A5 pasa de [~] a [x]: con el hallazgo 1 resuelto ya no queda ningún camino para filtrar secretos por `repr()`. La parte de "logs" sigue apoyándose en `to_safe_dict()` hasta que exista el logger (r1).

### Checkpoints

- C1: [x] están los archivos base y los 4 docs; `./init.sh` termina con exit 0.
- C2: [x] solo la feature 3 está en `in_progress`; `progress/current.md` describe la sesión activa.
- C3: [x] solo hay paquetes previstos, no hay `print()` en `src/` y no hay TODOs ni secretos. `tomli` condicional se acepta, pendiente de que lo ratifique el humano (r3).
- C4: [x] con la misma salvedad heredada: la cobertura ≥ 85% no se puede medir (`pytest-cov` no está en `[dev]`, pendiente m8). Los tests usan `tempfile.TemporaryDirectory()`, no hay red y la suite tarda < 60 s. `make test-integration` no aplica (la feature no toca el sistema completo).
- C5: [x] por ahora: no hay archivos sueltos sospechosos. La entrada en `history.md` y el estado `done` corresponden al cierre.
- C6: [x] no aplica (`sdd: false`).

### Observaciones menores (no bloquean)

- m1. `test_non_finite_float_in_file_rejected` abre el archivo con `open()` en lugar de usar el helper `_write` del módulo. Es solo una cuestión de homogeneidad.
- Siguen vigentes r1 (conectar `to_safe_dict()` al logger cuando exista), r2 (aviso ante variables `GEOAGENT_*` desconocidas) y r3: el humano debe ratificar solo TOML, `tomli` condicional y exit code 2. Solo TOML no se ha contado como bloqueante.

---

## Ronda 3

**Veredicto:** CHANGES_REQUESTED

### Evidencia ejecutada

| Comando | Resultado |
|---|---|
| `make lint` | OK (`ruff check`: all checks passed; `ruff format --check`: 18 archivos ya formateados) |
| `make test` | 131 passed, 424 subtests, 0.65 s (integración: sin tests, exit 5 tratado como OK) |
| `./init.sh` | exit 0, "[OK] Entorno listo" (WARN informativo de integración) |
| `grep -rn "print(\|TODO" src/` | sin resultados |
| Python 3.9 | No hay intérprete 3.9: solo `/usr/bin/python3.14`, sin uv ni pyenv, y `docker info` falla (el daemon no responde desde esta distro). Solo verifiqué la sintaxis: `ast.parse(..., feature_version=(3, 9))` pasa con `config.py` y `test_config.py`, y ruff `target-version = "py39"` está limpio. Las anotaciones `X \| None` de `_Spec` y `_Config` no se evalúan en tiempo de ejecución (`from __future__ import annotations`; `dataclass` no las resuelve). Sigue pendiente ejecutarlo con un 3.9 real (punto 1 de `questions_config_system.md`) |
| Casos límite a mano | unos 50 casos desde el entorno y desde el TOML (también listas, tablas, enteros y cadenas multilínea). Los detalles están en los hallazgos |

### Puntos 2-7 y decisiones del humano

- P2: [x] `_secret()` eliminado. Las tres specs secretas usan `_parse_str` con `secret=True`. Comportamiento sin cambios.
- P3: [x] `test_agent_defaults_...` y `test_backend_defaults_...` comparan `to_safe_dict()` con los diccionarios completos (10 y 9 campos) escritos a mano. El estilo `cfg = ...` está unificado y solo `_write` hace `open()`, con `encoding`.
- P4: [x] las 5 variantes de userinfo se prueban en `backend_url` (agente) y en `queue_url` (agente y backend), desde el entorno y desde el archivo, con la clave en el mensaje y sin el secreto en `str()`/`repr()` de la excepción. `backend_url` rechaza query y fragmento. La query de `queue_url` se enmascara entera con claves visibles, y se comprueban el valor exacto, el atributo intacto, la URL sin query sin cambios y un elemento sin `=`. Está documentado en `docs/config.md`, incluido que el path no se vigila.
- Decisión fragmento en `queue_url`: [x] se rechaza sin repetir el valor. Lo cubren la tabla `INVALID` (agente y backend, las dos fuentes) y `TestUrlSecretsNeverEchoed` (`amqp://h/#s3cr3t`, `...?heartbeat=1#s3cr3t`).
- P5: [x] `_parse_str` informa solo del tipo. El test parametrizado recorre esquema inválido, sin esquema, sin host, credenciales, query/fragmento y lista/tabla desde archivo. Pero hay una rama de rechazo que no lanza `ValidationError` (hallazgo 1).
- P6: [x] la tabla `INVALID` se ejecuta desde las dos fuentes y cubre todas las claves pedidas. También están los casos solo de archivo (`true`, `2.5`, `80.0`, `host = 1`, fecha, `log_level = 5`), los solo de entorno (`2.5`, `true`, `80.0`, solo espacios) y los aceptados (`" 3 "`, `heartbeat_interval = 5`). `max_workers = "3"` se acepta y lo fija `test_quoted_number_in_file_is_accepted`.
- P7: [x] los secretos están **escritos a mano** en `TestSecretMasking.CASES` (`{"auth_token", "queue_password"}` / `{"api_token", "queue_password"}`, con un comentario que explica por qué); no se derivan de `_*_SPECS`. La única introspección (`dataclasses.fields`) recorre los campos **no** secretos, como pedía el punto. Se cubren `MASK` por cada secreto, las tres vistas, el acceso por atributo, el secreto vacío → `""` en `repr()`/`str()`/`to_safe_dict()`, todos los no secretos visibles, el secreto en archivo por argumento y por `GEOAGENT_CONFIG_FILE` sin eco, y el caso mixto.
- r3: ratificada por el humano (solo TOML, `tomli` condicional, exit code 2). Ya no está pendiente.

### Hallazgos

1. **(Bloqueante) `urlparse` puede lanzar un `ValueError` sin capturar, y el error no nombra la clave y puede repetir el valor.** `_http_url` y `_queue_url` llaman a `urlparse(text)` sin `try`. Con un host entre corchetes mal formado, la excepción no es `ValidationError`, así que `load_or_exit` no la captura. Sale un traceback por stderr con exit code 1 y sin `GEOAGENT_<KEY>`, lo que incumple A4 ("mensaje que nombra la clave") y la regla de errores tipados. En Python 3.14 el mensaje además **repite el contenido de los corchetes**:
   - `GEOAGENT_BACKEND_URL='http://[s3cr3t'` → `ValueError: Invalid IPv6 URL`
   - `GEOAGENT_BACKEND_URL='http://[s3cr3t]'` (o `http://u@[s3cr3t]/`) → `ValueError: 's3cr3t' does not appear to be an IPv4 or IPv6 address`
   - lo mismo con `GEOAGENT_QUEUE_URL='amqp://[s3cr3t'`, y también desde el TOML.
   
   Arreglo: envolver `urlparse` (y el acceso a `.port`, ver hallazgo 2) en `try/except ValueError` → `ValidationError("must be a valid URL", field=key)` sin el valor y `from None`. Test: añadir `http://[s3cr3t`, `http://[s3cr3t]` y sus equivalentes `amqp://` a `TestUrlSecretsNeverEchoed.cases()` (entorno y archivo), más un caso en `TestLoadOrExit` que compruebe `SystemExit` == 2 y la clave en stderr.
2. **(Bloqueante, mismo arreglo) El puerto de las URL no se valida.** `urlparse` solo comprueba el puerto cuando se lee `.port`, y el código no lo lee. Se aceptan `http://h:s3cr3t`, `amqp://h:s3cr3t`, `amqp://h:99999` y `http://[::1]:99999`, que salen tal cual en `repr()`. Leer `parsed.port` dentro del mismo `try` lo rechaza (`ValueError: Port out of range` / `Port could not be cast`) y evita que lo que se haya escrito en la posición del puerto llegue a `repr()`. Test: `http://h:s3cr3t` y `amqp://h:99999` en la tabla `INVALID` y en `TestUrlSecretsNeverEchoed`.

### Observaciones menores (no bloquean)

- m2. `_parse_int`/`_parse_float` siguen repitiendo el valor, como permitió el humano en el punto 5. Pero desde el TOML también repiten **listas y tablas** (`port = {p="s3cr3t"}` → `port: must be an integer (got {'p': 's3cr3t'})`), que no son el caso de "texto de un campo numérico" que justificaba la excepción. Recomiendo repetir solo `str`/`int`/`float`, y para el resto informar del tipo, como hace `_parse_str`. No es un campo secreto ni una URL, así que no bloquea.
- m3. `test_valid_native_and_text_values_accepted` compara `heartbeat_interval` con `5.0`, pero `5 == 5.0`, así que no detectaría una regresión que devolviera `int`. Añadir `assertIsInstance(..., float)`.
- m4. `test_non_string_error_reports_only_the_type` comprueba `assertNotIn("x'", ...)`, que es frágil. Mejor usar un centinela distintivo (p. ej. `["s3cr3t"]`) y `assertNotIn("s3cr3t", ...)`.
- m5. Por diseño quedan visibles: el path y los parámetros `;` del path (`http://h/p;tok=s3cr3t`, `amqp://h/v;password=s3cr3t`), y los **nombres** de las claves de la query (`amqp://h/?s3cr3t=1` → `s3cr3t=***`). Lo primero está documentado en `docs/config.md` ("El path de una URL no se vigila"). Convendría mencionar ahí que los `;params` forman parte del path.
- m6. `http://h?` y `http://h#` (query o fragmento vacíos) se aceptan en `backend_url`. Es inofensivo.

### Acceptance de la feature 3 (sin regresiones)

- A1, A2, A3, A6: [x] siguen cubiertos (precedencia, prefijo, mapa en `docs/config.md`, las cuatro clases de tests más `TestUrlSecretsNeverEchoed` y `TestQueueUrlQueryMasking`).
- A4: [~] se cumple para todas las validaciones probadas, **salvo** el hallazgo 1: una URL con corchetes mal formados aborta con un traceback que no nombra la clave.
- A5: [~] los campos secretos y la query de `queue_url` no llegan a `repr()`/`str()`/`to_safe_dict()`, y los errores de URL no repiten el valor, **salvo** el `ValueError` del hallazgo 1 (repite el contenido entre corchetes) y el puerto sin validar del hallazgo 2.

### Checkpoints

- C1: [x] están los archivos base y los 4 docs; `./init.sh` termina con exit 0.
- C2: [x] solo la feature 3 está en `in_progress`; `progress/current.md` describe la sesión activa.
- C3: [x] solo hay paquetes previstos, no hay `print()` ni TODOs en `src/` y no hay secretos en el repositorio. `tomli` condicional está ratificado por el humano.
- C4: [x] con la salvedad heredada: la cobertura ≥ 85% no se puede medir (`pytest-cov` no está en `[dev]`, m8). Los tests usan `tempfile.TemporaryDirectory()`, sin red ni mocks de filesystem, y la suite tarda < 60 s. `make test-integration` no aplica.
- C5: [x] por ahora: no hay archivos sueltos sospechosos (`.venv*/` está ignorado). `history.md` y el estado `done` corresponden al cierre.
- C6: [x] no aplica (`sdd: false`).

### Cambios requeridos

1. Capturar el `ValueError` de `urlparse` en `_http_url` y `_queue_url` y convertirlo en `ValidationError` con la clave y sin el valor (hallazgo 1), con tests para `[`/`[...]` mal formados desde las dos fuentes y vía `load_or_exit`.
2. Validar el puerto de ambas URL leyendo `parsed.port` dentro del mismo `try` (hallazgo 2), con tests para un puerto no numérico y uno fuera de rango, sin eco.

---

## Ronda 4

**Veredicto:** CHANGES_REQUESTED

### Evidencia ejecutada

| Comando | Resultado |
|---|---|
| `make lint` | OK (`ruff check` limpio; `ruff format --check`: 18 archivos ya formateados) |
| `make test` / `pytest tests/unit` | 133 passed, 488 subtests, 0.66 s (integración: sin tests, exit 5 tratado como OK) |
| `./init.sh` | exit 0 |
| Python 3.9 | Sigue sin haber intérprete (solo 3.14, sin uv y con Docker caído). `ast.parse(..., feature_version=(3, 9))` pasa en `config.py` y `test_config.py` |
| Casos límite a mano | unos 45 casos por `load_or_exit`, desde el entorno y desde el TOML (también bytes crudos), con `s3cr3t` como centinela |

### Bloqueantes de la ronda 3

1. **`ValueError` de `urlparse`:** [x] resuelto. `_parse_url` envuelve `urlparse` y `.port` en un `try` y lanza `ValidationError("must be a valid URL")` sin repetir el valor. Lo comprobé a mano por `load_or_exit`: `http://[s3cr3t`, `http://[s3cr3t]`, `http://u@[s3cr3t]/`, `http://[::1]s3cr3t`, `http://s3cr3t]` y `amqp://[s3cr3t`, desde el entorno y el archivo, dan exit 2 con `GEOAGENT_<KEY>`/`<key>` en stderr y sin el secreto. Lo cubren `TestUrlSecretsNeverEchoed` y `test_malformed_url_exits_2_naming_key_without_secret`.
2. **Puerto de las URL:** [x] resuelto. Se rechazan `h:s3cr3t`, `h:abc`, `h:0`, `h:65536`, `h:99999`, `[::1]:99999`, `h:+80`, `h:-1`, `h: 80`, `h:1_0` y `h:８０` (dígitos de ancho completo). Se aceptan `h:65535`, `[::1]:8080` y `h:080`. Lo cubren la tabla `INVALID` y `TestUrlSecretsNeverEchoed`.

### Menores de la ronda 3

- m2: [x] `_describe` repite solo `str`/`int`/`float`. `port = ["s3cr3t"]`, `max_workers = {a="s3cr3t"}` y `heartbeat_interval = 1979-05-27` informan solo del tipo. Lo verifica `test_non_scalar_in_numeric_field_reports_only_the_type`.
- m3: [ ] **no aplicado**, aunque el informe de la ronda 4 lo da por hecho. `test_valid_native_and_text_values_accepted` (líneas 188-192) sigue con `assertEqual(..., 5.0)` y no hay `assertIsInstance` en todo el archivo.
- m4: [x] se eliminó la aserción frágil `"x'"`. La comprobación de que no se repite el valor con centinela queda cubierta por `TestUrlSecretsNeverEchoed` (lista/tabla con `s3cr3t`).
- m5: [x] `docs/config.md` documenta que los `;params` son parte del path y no se vigilan, y que los nombres de la query se ven.
- m6: se mantiene por decisión del leader.

### Hallazgos nuevos

1. **(Bloqueante) `_read_file` deja escapar excepciones sin capturar.** Es la misma clase de defecto que el hallazgo 1 de la ronda 3, ahora al leer el archivo. Sale un traceback con exit code 1 y sin el mensaje tipado `config_file: ...`, lo que incumple A4 y la regla de errores tipados:
   - Un archivo que no es UTF-8 (p. ej. `log_level = "\xff\xfe"` en bytes crudos) da `UnicodeDecodeError` (subclase de `ValueError`, que no es ni `OSError` ni `TOMLDecodeError`). `tomllib.load` decodifica el archivo y no convierte ese error en `TOMLDecodeError`.
   - Un byte NUL en la ruta (`GEOAGENT_CONFIG_FILE="/tmp/a\x00b"`) da `ValueError: embedded null byte` desde `open()`.
   
   Arreglo: en `_read_file`, añadir `except (UnicodeDecodeError, ValueError)` (después de `TOMLDecodeError`, que también es subclase de `ValueError`, o antes con el orden correcto) → `ValidationError(..., field="config_file")` sin el contenido. Test para ambos casos, más uno a través de `load_or_exit` (exit 2 y `config_file` en stderr).
2. **(Menor, recomendable en el mismo arreglo)** Un TOML con arrays anidados muy profundos (`x = [[[[...]]]]`, 5000 niveles) da `RecursionError` sin capturar en `tomllib`. El caso es patológico; basta con incluir `RecursionError` en el mismo `except`.
3. **(Menor, no bloquea)** El host de las URL no se valida más allá de que no esté vacío: se aceptan `http://h\x00x/`, `http://[v1.x]` (IPvFuture) y `http://[::1%25zone]`. No es un secreto (el host es visible por diseño), pero podría rechazarse un host con caracteres de control.

### Otras excepciones buscadas (sin problemas)

- Numéricos: `int()`/`float()` solo lanzan `ValueError`, que está capturado. Una cadena enorme (5000 dígitos, por encima del límite `int_max_str_digits`) se rechaza con `ValidationError`. `1e400` → "finite". Un NUL en `GEOAGENT_MAX_WORKERS` se rechaza.
- Cadenas: `.strip()`/`.upper()` no lanzan. `log_level = "ınfo"` (i sin punto) pasa a `INFO` tras `.upper()`, y eso es inofensivo.
- Archivo: un directorio da `IsADirectoryError` (subclase de `OSError`), que está capturado. El BOM UTF-8 da `TOMLDecodeError`, también capturado.
- `_mask_query` solo se ejecuta sobre URLs ya validadas, así que no le llegan entradas que hagan fallar a `urlsplit`.

### Acceptance de la feature 3

- A1, A2, A3, A6: [x] sin regresiones.
- A4: [~] se cumple en todos los campos y en las URL, **salvo** el hallazgo nuevo 1 (archivo no UTF-8 o ruta con NUL: traceback sin mensaje tipado).
- A5: [x] lo que se ha probado a mano no deja que un campo secreto, las credenciales o la query de una URL lleguen a `repr()`/`str()`/`to_safe_dict()` ni a un mensaje de error.

### Checkpoints

- C1: [x] están los archivos base y los 4 docs; `./init.sh` termina con exit 0.
- C2: [x] solo la feature 3 está en `in_progress`; `progress/current.md` describe la sesión activa.
- C3: [x] solo hay paquetes previstos, sin `print()` ni TODOs en `src/` y sin secretos. `tomli` condicional está ratificado.
- C4: [x] con la salvedad heredada (cobertura no medible, m8). Los tests usan `tempfile`, sin red, y tardan < 60 s.
- C5: [x] por ahora.
- C6: [x] no aplica (`sdd: false`).

### Cambios requeridos

1. Capturar en `_read_file` el `UnicodeDecodeError` y el `ValueError` de `open()` (e, idealmente, `RecursionError`) y convertirlos en `ValidationError(field="config_file")`, con tests (archivo no UTF-8, ruta con NUL y uno vía `load_or_exit`).
2. Aplicar m3 de verdad (`assertIsInstance(cfg.heartbeat_interval, float)`) y corregir la fila m3 del informe de la ronda 4.

---

## Ronda 5

**Veredicto:** APPROVED

### Evidencia ejecutada

| Comando | Resultado |
|---|---|
| `make lint` | OK (`ruff check` limpio; `ruff format --check`: 18 archivos ya formateados) |
| `make test` | 135 passed, 494 subtests, 0.71 s |
| `./init.sh` | exit 0 |
| Python 3.9 | Sigue sin haber intérprete (solo 3.14); la sintaxis 3.9 está verificada con `ast.parse` en las rondas 3 y 4 y no ha cambiado. Ejecutarlo con un 3.9 real sigue pendiente (punto 1 de `questions_config_system.md`; la CI con la matriz 3.9 lo cubrirá) |
| Barrido a mano | 59 casos por `load_or_exit`: 22 archivos, cada uno por argumento y por `GEOAGENT_CONFIG_FILE`, y 15 valores extremos del entorno. Lo ejecuté como uid 1000 (no root), así que la prueba de permisos es real |

### Bloqueante de la ronda 4 y m3

- Hallazgo 1: [x] resuelto. `_read_file` captura `UnicodeDecodeError`, el `ValueError` de `open()` y `RecursionError`. El orden de las cláusulas es correcto: `TOMLDecodeError` y `UnicodeDecodeError` (subclases de `ValueError`) van antes que `ValueError`, así que el mensaje de TOML inválido no se pierde. Comprobado a mano: un archivo UTF-16 o no UTF-8 da "is not valid UTF-8"; una ruta con NUL, "invalid config file path"; arrays (100 000 niveles) o tablas inline (3000 niveles) anidados, "nested too deeply". Todos salen con exit 2, `config_file` en stderr y sin contenido del archivo. Lo cubren `test_unreadable_files_raise_validation_error` (3 casos por las dos rutas) y `test_non_utf8_file_via_load_or_exit_exits_2` (exit 2, sin secreto y sin traceback).
- m3: [x] `assertIsInstance(cfg.heartbeat_interval, float)` en la línea 191.

### Barrido de excepciones no tipadas (todas tipadas o aceptadas correctamente)

- Archivo: sin permisos (`EACCES`), directorio (`EISDIR`), componente que no es directorio (`ENOTDIR`) y ruta de 5000 caracteres (`ENAMETOOLONG`) → `config_file: cannot read ...`. BOM UTF-8, clave duplicada y NUL dentro del archivo → `invalid TOML`. Una tabla anidada `[a.b.c]` → `a: unknown configuration key`. Una clave con punto o `[[max_workers]]` → tipo `dict`/`list` sin eco. Un secreto con clave con punto (`auth_token.x`) se rechaza como secreto. Un archivo vacío, `/dev/null`, CRLF y un archivo de 20 MB con comentarios cargan los valores por defecto o los del archivo. Una ruta con surrogates se escribe en stderr con `backslashreplace`, también con `PYTHONIOENCODING=ascii`, sin `UnicodeEncodeError`.
- Entorno: un entero de 100 000 dígitos (por encima de `int_max_str_digits`), surrogates, `0x10`, `1e-400` (→ 0.0, rechazado), `-0.0`, `\x00` en `log_level` y un esquema con surrogate → `ValidationError` con la clave. Una URL de 100 000 caracteres y una query de 100 000 pares se aceptan sin error.
- No queda ninguna excepción sin tipar en la carga.

### Observaciones menores (no bloquean)

- m7. Los mensajes numéricos repiten el valor completo, sin límite de longitud. `GEOAGENT_PORT=-9…9` (4300 dígitos) mete ~4300 caracteres en stderr. Es cosmético; se podría truncar en `_describe`.
- m8b. `int()`/`float()` aceptan dígitos Unicode y guiones bajos: `GEOAGENT_MAX_WORKERS=١٢` → 12 y `GEOAGENT_REQUEST_TIMEOUT=1_0.5` → 10.5. Es inofensivo, pero más permisivo de lo que dice `docs/config.md`.
- Sigue vigente el hallazgo 3 de la ronda 4 (el host no valida caracteres de control; p. ej. `http://\udcffh/` se acepta). Lo decide el leader.

### Acceptance de la feature 3

- A1-A6: [x]. A4 queda completo: toda configuración inválida probada (campos, URL y archivo) aborta con exit 2 y un mensaje que nombra la clave o `config_file`. A5: [x] sin caminos de fuga conocidos hacia `repr()`/`str()`/`to_safe_dict()` ni hacia los mensajes de error para los campos secretos, las credenciales o la query de las URL.

### Checkpoints

- C1: [x] están los archivos base y los 4 docs; `./init.sh` termina con exit 0.
- C2: [x] solo la feature 3 está en `in_progress`; `progress/current.md` describe la sesión activa.
- C3: [x] solo hay paquetes previstos, sin `print()` ni TODOs en `src/` y sin secretos. `tomli` condicional está ratificado.
- C4: [x] con la salvedad heredada (cobertura no medible hasta añadir `pytest-cov`). Los tests usan `tempfile`, sin red, y tardan < 60 s. Los tests con rutas fijas (`/tmp/a\x00b`) no tocan el disco: `open()` falla antes de acceder al sistema de archivos.
- C5: [x] por ahora: no hay archivos sueltos sospechosos. La entrada en `history.md` y el estado `done` corresponden al cierre.
- C6: [x] no aplica (`sdd: false`).

---

## Ronda 6

**Veredicto:** APPROVED

### Evidencia ejecutada

| Comando | Resultado |
|---|---|
| `make lint` | OK con ruff 0.16.7 (`ruff>=0.16.7,<0.17`, fijado por el leader en `pyproject.toml`): `ruff check` limpio y 18 archivos ya formateados |
| `make test` | 140 passed, 510 subtests, 0.71 s |
| `./init.sh` | exit 0 |
| Python 3.9 | Sigue sin haber intérprete. `ast.parse(..., feature_version=(3, 9))` pasa en `config.py` y `test_config.py` |
| Barrido a mano | ~90 casos por `load_or_exit`, desde el entorno y desde el TOML |

### Cambios de la ronda 6

- **m7 (truncado):** [x] `_describe` corta a 40 caracteres más `…`. Lo comprobé con una cadena de 5000 dígitos, `-9…9`, un int nativo de 400 dígitos en un campo float y una cadena larga entre comillas: los mensajes miden entre 55 y 111 caracteres. Si `repr` falla (int > 4300 dígitos), solo se nombra el tipo. El `OverflowError` de `float(int_enorme)` está capturado. Los mensajes `got {number}` de rango también pasan por `_describe`. Tests: `test_long_numeric_value_is_truncated_in_error` y `test_huge_digit_string_and_native_int_are_rejected_briefly`.
- **m8b (solo ASCII y sin `_` en el texto):** [x] se rechazan `1_0`, `١٢`, `３`, `0x10`, `3.0`, `1e2`, `+`, `--3`, `3-` y `" "` para enteros, y `1_0.5`, `١.٥`, `0x1p3`, `1e`, `e5`, `.`, `1.2.3` y `5 .0` para floats. **Valores válidos sin romper:** `" 3 "`, `+3`, `03`, `\t3\n`, `5`, `5.`, `.5`, `+1.5e3`, `1E-2` y `1e+2`. `nan`/`inf`/`-Infinity`/`inF` siguen rechazándose como "finite number". Desde el TOML se aceptan los nativos (`5` → `5.0`, `1e3`, `+1_000.0`, `1_000`, `0x10`, `0o17`, `9223372036854775807`), el número entre comillas (`"3"`, `" +3 "`, `" 2.5 "`) y el puerto `0x50`. `"1_000"` entre comillas se rechaza, coherente con la regla del texto. Está documentado en `docs/config.md`. Tests: `test_numeric_text_accepts_only_ascii_digits_without_underscores`, `test_numeric_text_still_accepts_spaces_sign_and_exponent` y `test_quoted_number_in_file_is_accepted`.
- **Caracteres de control en el host (hallazgo 3 de la ronda 4):** [x] `_check_host` se aplica a la URL completa y al `hostname`. Rechaza `\t`, `\r\n`, `\x00`, `\x7f`, `\x01` en la query, un surrogate, ZWSP (`\u200b`), NBSP y RLO (`\u202e`) con "must be a valid URL", sin repetir el valor, desde el entorno y desde el TOML (`"http://h\t/"`). **Hosts válidos sin romper:** `my-host.example.com:8080`, `rabbit-mq.svc:5672/vhost?heartbeat=30`, `[::1]:8080`, `[2001:db8::1]`, `[fe80::1%25eth0]`, `amqps://[::1]:5671/`, `xn--mnchen-3ya.de`, `münchen.de`, `h_1.local` y `127.0.0.1`. Test: `test_control_characters_in_host_are_rejected_without_echo`.

### Observaciones menores (no bloquean)

- m9. `_check_host` no valida la sintaxis DNS: se aceptan `http://h h/` (espacio en el host) y `http://-h-/`. No son caracteres de control ni secretos; el fallo aparecerá al conectar. Ver "Para features futuras" (7).
- m10. En Python 3.9, `urlparse(...).port` hace `int(port, 10)` sin comprobar `isdigit`/`isascii`. Por eso `http://h:1_0`, `http://h:+80` o `http://h: 80`, que en 3.14 se rechazan, podrían aceptarse allí con el puerto ya normalizado. No afecta a los secretos ni al rango (1-65535 se sigue comprobando), y no lo puedo verificar sin un 3.9. Si se quiere un comportamiento idéntico, validar el puerto con `parsed.netloc.rpartition(":")` y `_INT_RE` sin signo.
- Al truncar a 40 caracteres, un texto puesto por error en un campo numérico se repite en parte. Es lo que decidió el humano en el punto 5 (no son campos secretos ni URL).

### Acceptance de la feature 3

- A1-A6: [x] sin regresiones. A4 y A5 se mantienen completos: toda configuración inválida probada aborta con exit 2 y la clave en el mensaje, sin repetir secretos, credenciales ni la query de las URL.

### Checkpoints

- C1: [x] están los archivos base y los 4 docs; `./init.sh` termina con exit 0.
- C2: [x] solo la feature 3 está en `in_progress`; `progress/current.md` describe la sesión activa.
- C3: [x] solo hay paquetes previstos, sin `print()` ni TODOs en `src/` y sin secretos. `tomli` condicional está ratificado. La acotación de `ruff` es de herramienta de desarrollo (`[dev]`) y la decidió el leader.
- C4: [x] con la salvedad heredada (cobertura no medible hasta añadir `pytest-cov`). Los tests usan `tempfile`, sin red, y tardan < 60 s.
- C5: [x] por ahora: no hay archivos sueltos sospechosos. La entrada en `history.md` y el estado `done` corresponden al cierre.
- C6: [x] no aplica (`sdd: false`).

## Para features futuras

- **20 `structured_logging`:** el logger debe serializar `AgentConfig`/`BackendConfig` solo mediante `to_safe_dict()`, con un test que compruebe que ni el secreto ni el valor de la query de `queue_url` aparecen en la salida JSON (r1). Valorar también un aviso ante variables `GEOAGENT_*` desconocidas (r2).
- **9 `message_queue_layer`:** decidir la lista de opciones de query de `queue_url`. Lo preferible es pasarlas a campos tipados y prohibir la query (punto 4 de `questions_config_system.md`). No pasar `queue_url` a la librería AMQP en logs propios sin enmascarar.
- **24 `unit_test_suite`:** añadir `pytest-cov` a `[dev]` para poder medir el ≥ 85% de C4 (m8, heredado).
- **19 `resource_management` / 11 `agent_concurrency_runtime`:** `max_workers` no tiene límite superior (`99999999999999999999999` desde el TOML se acepta), y `request_timeout`/`heartbeat_interval` aceptan valores subnormales (`5e-324`). Fijar en esas features los límites razonables (p. ej. `max_workers` ≤ núcleos o un tope configurable, timeout mínimo) y validarlos en `config.py`.
- **7 `agent_http_client` / 9 `message_queue_layer`:** si se quiere un fallo temprano, validar la sintaxis del host (etiquetas DNS o IP) de `backend_url`/`queue_url` (m9), o al menos que el error de conexión nombre la clave de configuración y no repita la URL completa con su query.
- **25 `integration_test_suite` (o la CI):** ejecutar `test_config` con Python 3.9 real para confirmar m10 (el puerto de las URL con `_`/signo/espacios, por cómo parsea `urlparse` en 3.9) y la rama `tomli`.

## Ronda 7

**Veredicto:** CHANGES_REQUESTED

Entrada: puntos 8-16 de `progress/questions_config_system.md` (decisiones del 2026-10-06) y "## Ronda 7" de `progress/impl_config_system.md`. Archivos revisados: `src/geoagent/common/config.py`, `tests/unit/test_config.py`, `docs/config.md`. El cambio en `tests/unit/test_smoke.py` (`PYTHON_COLORS=0`) es ajeno a esta ronda (`progress/fix_smoke_color.md`). Es correcto y no afecta a `config`.

### Evidencia ejecutada

| Comando | Resultado |
|---|---|
| `make lint` | OK (`ruff check` limpio, 18 archivos formateados) |
| `make test` | 136 passed, 1261 subtests, 2.07 s |
| `./init.sh` | exit 0, "Entorno listo" (WARN informativo de integración) |
| Python 3.9 | Sigue sin haber intérprete. `ast.parse(..., feature_version=(3, 9))` pasa en `config.py` y `test_config.py` |
| Mutaciones | 20 mutaciones de `config.py` (script en el scratchpad; el archivo se restauró después). Se detectan 19 y sobrevive 1 (ver B5) |
| Barrido a mano | Todas las ramas de error de `config.py` y todos los campos de los dos loaders, desde el entorno y desde el TOML |

### Puntos 8-16

- P8: [x] tablas por tipo de validación (`_HTTP_URL`, `_QUEUE_URL`, `_PORT`, `_POSITIVE_INT`, `_POSITIVE_FINITE_FLOAT`, `_LOG_LEVEL`, `_BIND_HOST`, `_PATH`, `_ANY_STR`, `_SECRET_TYPE`) y un mapa `FIELD_TYPES` escrito a mano. `test_every_field_is_classified` falla en los dos sentidos. Comprobé que se recorren los 10 campos del agente y los 9 del backend, desde las dos fuentes. Hay cambios de nombre frente a lo pedido: `_NON_EMPTY_STR` se dividió en `_BIND_HOST` y `_PATH`, y `_SECRET` pasó a llamarse `_SECRET_TYPE`. Son razonables (duda 5).
- P9: [x] `_resolve` pasa los defaults por el parser (`config.py:363`). Se comprueban el diccionario y los tipos exactos, y hay un test con `mock.patch.dict` para tres defaults inválidos. La mutación "no validar los defaults" la detectan 3 tests.
- P10: [x] los casos válidos comprueban valor y tipo con `assertIs(type(v), type(expected))` e incluyen la columna del número entre comillas. `test_file_path_from_env` comprueba también `request_timeout` (valor y tipo).
- P11: [x] el inventario está aplicado: `LOADERS`, `_INT_FIELD` y `_OTHER_KEY`, con precedencia, archivo ausente, TOML inválido, archivo ilegible, `load_or_exit` y enmascarado probados con los dos loaders y, donde aplica, con las dos fuentes.
- P12: [~] `host` usa `_bind_host` y `store_path`/`db_path` usan `_fs_path`. La aserción de "sin eco" ya es `assertNotIn(value)` + `assertNotIn(repr(value)[1:-1])` sobre `str` y `repr` de la excepción. **Pero el mínimo del punto 12 (texto imprimible y sin espacios) no se cumple para IPv6 con zona, y la regla de "nombre DNS válido" deja pasar nombres numéricos ambiguos** (B1, B2).
- P13: [x] `_config_source` existe y `TestLoadOrExit` llama a `load_or_exit(loader, path, env=env)` con el loader real.
- P14: [x] `TestUrlSecretsNeverEchoed` desaparece. Quedan `TestValidation` (qué se acepta) y `TestErrorMessages` (qué dice el mensaje).
- P15: [x] `_views` y `_assert_shown` están a nivel de módulo y se usan en todos los sitios listados (`TestSecretMasking` y `TestQueueUrlQueryMasking`).
- P16: [~] un `;` literal en el path de las dos URL se rechaza sin eco y `%3B`/`%3b` se acepta. Los cuatro casos de la tabla y `api;` están en `_url_invalid`, y `docs/config.md` está actualizado. **Pero el `;` en el netloc no se vigila: `http://h;token=s3cr3t` y `amqp://h;password=s3cr3t` se aceptan y salen tal cual en `repr()`** (B3).

### Cobertura tras la consolidación (140 → 136 tests)

Comparé caso a caso con `git show HEAD:tests/unit/test_config.py`. No se perdió ningún valor inválido ni válido de las tablas antiguas: `INVALID`, los tipos nativos, el texto del entorno, `m8b`, el número entre comillas, todas las ramas de `TestUrlSecretsNeverEchoed.cases`, el enmascarado y los secretos en archivo están todos en las tablas nuevas o en un test equivalente, y casi siempre ampliados a los dos loaders y las dos fuentes. Hay tres diferencias sin impacto:
- La precedencia ya no prueba un entero (`max_workers`/`port`) sino `request_timeout`. La lógica de `_resolve` es la misma y los enteros se prueban desde las dos fuentes en las tablas.
- El antiguo `test_control_characters_in_host_are_rejected_without_echo` comprobaba el texto "valid URL". Ahora no se comprueba, pero la mutación "`_check_host` solo sobre el hostname" sigue detectándose (12 fallos).
- El caso de no escalar sin eco de `heartbeat_interval` pasa a `request_timeout`, que usa el mismo parser.

Las mutaciones que se detectan son: el parser de cadenas con eco, `_fs_path` sin control de caracteres o solo con NUL, defaults sin validar, sin `_check_path` en cada URL, `_check_path` con `parsed.params`, DNS que admite `_`, etiqueta de 64 caracteres, `_bind_host` con eco, `_check_host` solo sobre el hostname, puerto 65536, clave desconocida aceptada, float que admite 0, entero sin `strip`, query sin valor sin enmascarar, secreto aceptado en el archivo, `_describe` sin truncar y precedencia invertida. **Sobrevive una: `_log_level` repitiendo el valor** (B5).

### Búsqueda sistemática de la clase de fallo

**(a) Mensajes de error que repiten valores:**

| Rama | Repite | Estado |
|---|---|---|
| `_http_url`, `_queue_url`, `_bind_host`, `_fs_path`, `_log_level`, `_parse_str`, secreto en archivo | nada (solo la clave o el tipo) | OK. `_log_level` no está protegido por test (B5) |
| `_parse_int`/`_parse_float`/rangos (`_describe`) | el texto escapado con `repr`, truncado a 40 caracteres: `GEOAGENT_MAX_WORKERS="1\nINFO s3cr3t"` da `got '1\nINFO s3cr3t'` | lo permite el punto 5. Ver D2 |
| `_read_file`: `file not found`, `cannot read`, `invalid TOML in`, `is not valid UTF-8`, `nested too deeply` | **la ruta tal cual**, con caracteres de control crudos: `GEOAGENT_CONFIG_FILE="/x/a\nINFO fake"` da `config_file: file not found: /x/a` + salto de línea real + `INFO fake` en stderr. Lo mismo pasa con `\x1b[31m` (secuencias ANSI) | **B4** |
| `_resolve`, clave desconocida (`field=key`) | **la clave del TOML tal cual**: `"x\nINFO fake" = 1` da un salto de línea real en stderr. `"s3cr3t" = 1` repite la clave | **B4** |
| `TOMLDecodeError` | solo posición y carácter escapado (`Illegal character '\n'`), sin contenido | OK |

**(b) Campos de texto que aceptan caracteres de control:**

| Campo | Acepta | Estado |
|---|---|---|
| `backend_url`, `queue_url` | nada no imprimible (`isprintable` sobre toda la URL) | OK |
| `log_level` | nada (lista cerrada) | OK |
| `host` | **IPv6 con zona arbitraria**: `fe80::1%a\nINFO fake`, `fe80::1%a\x00b` y `fe80::1%a b` se aceptan (`ipaddress` admite cualquier texto tras `%`) | **B1** |
| `store_path`, `db_path` | se rechaza `Cc` (NUL, `\n`, `\x85`), pero se aceptan ` ` (separador de línea), `‮` (RLO) y surrogates (`a\udcffb`; luego `open()` falla con `UnicodeEncodeError`, sin tipar y tarde) | D3 |
| `queue_username`, `queue_password`, `auth_token`, `api_token` | **todo**: `u\r\nX-Injected: 1\x00` se acepta. En `repr`/`to_safe_dict` sale escapado (o enmascarado), pero el valor llega tal cual a las cabeceras HTTP (`auth_token`) y a la autenticación AMQP | D1 |

**(c) Valores que llegan al objeto sin pasar por el parser:** por los loaders, ninguno: entorno, archivo y defaults pasan por `spec.parser`. La única vía es construir `AgentConfig(...)`/`BackendConfig(...)` a mano, que no valida nada. No forma parte del alcance de los loaders (ver "Para features futuras").

### Bloqueantes

1. **B1 — `host` acepta caracteres de control y espacios en la zona IPv6.** `ipaddress.ip_address("fe80::1%a\nINFO fake")` es válido, así que `_bind_host` lo devuelve. Esto incumple el mínimo del punto 12 ("imprimible, sin espacios"). Arreglo: en `_bind_host`, antes del intento de IP, rechazar todo `text` que no sea `isprintable()` o que contenga espacios, sin repetir el valor. Además, decidir sobre la zona (duda 1): recomiendo rechazar el `%` (bind a link-local con zona es raro) o, como mínimo, restringir la zona a `[A-Za-z0-9_.-]+`. Tests: filas `fe80::1%a\nb`, `fe80::1%a\x00b` (en el TOML, escapados) y `fe80::1%a b` en `_BIND_HOST.invalid`, y `fe80::1%eth0` en la tabla que corresponda según la decisión.
2. **B2 — nombres numéricos ambiguos aceptados como DNS.** `010.0.0.1`, `0x7f.1`, `127.1`, `2130706433`, `999.1.1.1` y `1` pasan por la regla de etiquetas. `getaddrinfo` interpreta los primeros como IPv4 en notación `inet_aton`: `010.0.0.1` → **8.0.0.1** y `2130706433` → 127.0.0.1. No es "una IP o un nombre DNS válido" (RFC 1123 §2.1 y RFC 3696 §2: el TLD no puede ser totalmente numérico). Arreglo: rechazar el nombre si su última etiqueta es solo de dígitos. Recomiendo también el límite de 253 caracteres totales (duda 2). Tests: esas filas en `_BIND_HOST.invalid`.
3. **B3 — `;` en el netloc se salta el punto 16.** `http://h;token=s3cr3t` y `amqp://h;password=s3cr3t` se aceptan (`urlsplit` lo pone en el netloc, no en el path) y el secreto sale tal cual en `repr()`/`to_safe_dict()`. Un `;` nunca es válido en un host, y la parte de usuario ya se rechaza, así que rechazarlo no entra en conflicto con la decisión. Arreglo: `_check_path` (o un `_check_semicolon`) rechaza un `;` en `urlsplit(text).netloc` además del path, con el mismo mensaje sin eco. Tests: las dos filas en `_url_invalid` (también con `?x=1` detrás).
4. **B4 — la ruta del archivo y la clave desconocida se repiten tal cual, con caracteres de control.** Es la clase de fallo (a). `config_file: file not found: /x/a` + salto de línea real + `INFO fake` permite inyectar una línea falsa en cualquier log que capture stderr, y lo mismo pasa con una clave TOML entre comillas. Arreglo: un helper que muestre la ruta o la clave solo si es imprimible (y, para la clave, si coincide con `[A-Za-z0-9_.-]+`). Si no, un mensaje genérico ("path contains non-printable characters" o "unknown configuration key (non-printable name)", con `field` saneado). Tests en `TestErrorMessages`: ruta con `\n` y `\x1b` por argumento y por `GEOAGENT_CONFIG_FILE` en las cinco ramas de `_read_file` que la repiten (basta con "no existe" y "TOML inválido" como representantes), y una clave `"x\nINFO fake"`. En todos: ni el valor tal cual ni con el salto real en `str(exc)` ni en la salida de `load_or_exit`.
5. **B5 — el test de "sin eco" excluye tipos que no deben repetir el valor.** `_LOG_LEVEL` y `_ANY_STR` tienen `"no_echo": False`, así que la mutación "`_log_level` repite el valor" sobrevive a toda la suite. Con los dos a `True`, el código actual pasa: lo comprobé en una copia (296 subtests OK). Arreglo: ponerlos a `True`. Mejor aún, que `no_echo` sea `True` por defecto y que solo los tipos numéricos lo desactiven, con un comentario que cite el punto 5.

### Decisiones pendientes del humano (recomendadas, no bloquean por sí solas)

- **D1** (recomendado: sí, en esta ronda). Hoy `queue_username` y los tres secretos aceptan `\r`, `\n` y NUL. Propongo rechazar los caracteres de control (`Cc`) en esos campos, sin repetir el valor. `auth_token` irá en una cabecera `Authorization` (riesgo de inyección de cabeceras si la librería HTTP no lo filtra) y las credenciales AMQP van al protocolo. El punto 8 los dejó sin validación (`_ANY_STR`/`_SECRET`) porque reflejaba el código de entonces, no por una decisión explícita sobre los caracteres de control. Si se aprueba: filas en `_ANY_STR.invalid` y un `_SECRET_TYPE.invalid` solo de entorno, con no eco.
- **D2** (opcional). `_describe` repite el texto de los campos numéricos escapado con `repr`, incluidos los caracteres de control. Lo permite el punto 5. Propongo repetirlo solo si es ASCII imprimible y, si no, decir solo `got str`.
- **D3** (recomendado, barato). `_fs_path` solo rechaza `Cc`. Propongo la misma regla que las URL (`isprintable()`, que admite el espacio ASCII), así se rechazan ` `, RLO y los surrogates (este último evita el `UnicodeEncodeError` sin tipar al abrir el archivo). Contrapartida: se rechazarían rutas con NBSP u otros espacios Unicode.

### Valoración de las dudas del implementer

1. Zona IPv6: **bloqueante** en cuanto a su contenido (B1). Aceptar la zona en sí es opcional y lo decide el humano (recomiendo rechazar `%`).
2. Nombres numéricos y longitud total: **bloqueante** en cuanto al TLD numérico (B2). El límite de 253 caracteres es opcional (recomendado, una línea). Rechazar `h.` está bien: es una dirección de escucha, no un FQDN absoluto.
3. Surrogates en las rutas: **opcional** (D3, recomendado).
4. `;` en la query: **opcional, no hace falta** (la query ya se enmascara entera). En el netloc: **bloqueante** (B3).
5. Cambio de nombre de los tipos de validación: **no bloqueante**. Conviene dejarlo anotado en `questions_config_system.md` (punto 8).
6. El error de un default inválido no dice que viene del default: **opcional**. Es un error de programador, y el test y el arranque ya lo detectan con la clave. Añadir "(default)" al mensaje es barato pero prescindible.

### Observaciones menores (no bloquean)

- m11. `test_non_scalar_in_numeric_field_reports_only_the_type` solo comprueba que falta `s3cr3t`, no que el mensaje diga `got dict`/`got list`, como indica su nombre. Añadir `assertIn(f"got {tipo}", ...)`.
- m12. `_PATH` y `_BIND_HOST` comparten las filas de no escalares, pero `_HTTP_URL`/`_QUEUE_URL` no incluyen fecha ni `float`. Se puede añadir `1979-05-27` por coherencia (mismo parser `_parse_str`).
- m13. `docs/config.md`: la columna de `queue_url`/`backend_url` de la tabla no menciona el `;`, que solo aparece en la sección de notas. Basta con una referencia.

### Acceptance de la feature 3

- A1-A6: [x] sin regresiones en lo que ya cubrían. A4/A5 ("inválida → aborta nombrando la clave", "sin secretos en logs") quedan incompletos por B1, B3 y B4.

### Checkpoints

- C1: [x] están los archivos base y los 4 docs; `./init.sh` termina con exit 0.
- C2: [x] solo la feature 3 está en `in_progress` (reabierta con la autorización del humano); `progress/current.md` describe la sesión activa.
- C3: [x] solo hay paquetes previstos, sin `print()` en `src/` y sin dependencias nuevas (`ipaddress`, `unicodedata` y `re` son de la stdlib). Los tests no contienen secretos reales.
- C4: [x] con la salvedad heredada (cobertura no medible hasta añadir `pytest-cov`). Los tests usan `tempfile`, sin red y sin mocks de filesystem (`mock.patch.dict` solo sobre `_*_SPECS` y `os.environ`), y tardan < 60 s. `make test-integration` no aplica.
- C5: [ ] pendiente del cierre: no hay archivos sueltos sospechosos (`.claude/skills/` y `progress/fix_smoke_color.md` son del arnés), pero la entrada en `history.md` y el estado `done` corresponden al cierre.
- C6: [x] no aplica (`sdd: false`).

### Cambios requeridos

1. B1: `_bind_host` rechaza texto no imprimible o con espacios también en IPv6 con zona, y decidir la zona. Con tests.
2. B2: rechazar los nombres cuya última etiqueta sea totalmente numérica (y, recomendado, más de 253 caracteres). Con tests.
3. B3: rechazar `;` en el netloc de `backend_url` y `queue_url`, sin eco. Con tests.
4. B4: no repetir la ruta del archivo ni la clave desconocida si contienen caracteres no imprimibles. Con tests por las dos vías de ruta y por `load_or_exit`.
5. B5: `no_echo` a `True` en `_LOG_LEVEL` y `_ANY_STR` (o `True` por defecto salvo en los numéricos).
6. Si el humano aprueba D1/D3, aplicarlas en la misma ronda.

### Para features futuras

- **5 `backend_api_skeleton`:** el `host` validado se usa en el `bind`. Que el error de `bind` (`EADDRNOTAVAIL`, `EADDRINUSE`) nombre `host`/`port` y no repita otra cosa. Si se admite la zona IPv6, comprobar que el servidor HTTP elegido la acepta.
- **7 `agent_http_client`:** no confiar en que `auth_token` esté libre de `\r\n` si no se aprueba D1. Que el cliente use una librería que rechace las cabeceras con saltos de línea, y un test con un token así.
- **9 `message_queue_layer`:** lo mismo para `queue_username`/`queue_password`. Además, no pasar `queue_url` sin enmascarar a los logs de la librería AMQP (se mantiene lo de la ronda 6).
- **20 `structured_logging`:** el logger JSON debe escapar los caracteres de control en todos los campos (no solo en el `repr` de la config) y tener un test con `\n` y `\x1b` en un mensaje. Así un error de configuración con datos del usuario no puede romper una línea de log aunque B4 se escape por otra rama.
- **Sin feature asignada (o la primera que construya `AgentConfig`/`BackendConfig` a mano, p. ej. 24 `unit_test_suite`):** el constructor de las dataclasses no valida nada. O se documenta que los loaders son la única entrada válida, o se añade un `__post_init__` que pase cada campo por su parser.

## Ronda 8

**Veredicto:** CHANGES_REQUESTED

Entrada: B1-B5 y m11-m13 de "## Ronda 7", las decisiones del humano del 2026-10-07 (`progress/questions_config_system.md`) y "## Ronda 8" de `progress/impl_config_system.md`. Archivos revisados: `src/geoagent/common/config.py`, `tests/unit/test_config.py` y `docs/config.md`.

### Evidencia ejecutada

| Comando | Resultado |
|---|---|
| `make lint` | OK (`ruff check` limpio, 18 archivos formateados) |
| `make test` | 142 passed, 1885 subtests, 2.21 s |
| `./init.sh` | exit 0, "Entorno listo" (WARN informativo de integración) |
| Sondas a mano | Script en el scratchpad (`r8/probe.py`): host, `log_level`, rutas `Path`/`bytes`, errores de TOML, claves y rutas largas, URL, secretos con `Cf`, `load_or_exit` |
| Mutaciones propias | 25 mutaciones de `config.py` (`r8/mut.py`; el archivo se restauró y se comparó con `diff`). Se detectan 23 y sobreviven 2 (m15, m16) |
| Cobertura frente a la ronda 7 | Comparé con el borrador de la ronda 7 que hay en el scratchpad (`head.py` + `body.py`): no falta ningún test (35 → 41 funciones) y las únicas líneas eliminadas son filas o banderas que ahora están ampliadas (`no_echo`, `_ANY_STR`/`_SECRET_TYPE` con `_CONTROL_CHARS`) |

### Bloqueantes y decisiones de la ronda 7

- B1 (zona IPv6, imprimible, sin espacios): [x] `config.py:152`, con las filas de `_BIND_HOST.invalid` desde las dos fuentes. Comprobado.
- B2 (TLD numérico): [x] según la regla que pedí, **pero la regla se queda corta** (ver el nuevo B2).
- B3 (`;` en el netloc): [x] `_check_semicolon`, con 5 filas por esquema. La mutación "con `params`" la detectan 56 tests.
- B4 (ruta y clave no imprimibles): [x] en las 5 ramas que repiten la ruta, por argumento y por `GEOAGENT_CONFIG_FILE`, por excepción y por `load_or_exit`. Cada rama con la ruta cruda la detectan 20 tests. La rama `ValueError` no está en la tabla (m15).
- B5 (`no_echo` por defecto): [x] `vtype.get("no_echo", True)`, y solo los tres tipos numéricos lo desactivan.
- D1 (`Cc` en usuario y secretos): [x]. D3 (`isprintable` en rutas): [x]. D2 (eco numérico solo si es ASCII imprimible): [x]. Límite de 253: [x], con la frontera probada (253 válido, 254 inválido; `<` en lugar de `<=` se detecta). `(default)`: [x]. Duda 4 (`;` en la query aceptado): [x], con la fila válida `amqp://h/v?a=1;b=2`. m11-m13: [x].

### Búsqueda sistemática de la clase de fallo

| Rama / entrada | Resultado |
|---|---|
| `_read_file` (las 5 ramas que repiten la ruta) por argumento y por entorno | OK con `str`. **Con `pathlib.Path` o `bytes`, `AttributeError` sin tipar** (nuevo B1) |
| Rama `ValueError` (NUL en la ruta) | No repite nada, pero ningún test lo vigila (m15) |
| `TOMLDecodeError` | Repite nombres de clave (`Cannot declare ('x\\nINFO fake',) twice`, `Duplicate inline table key 's3cr3t'`) con `repr`: es imprimible y ocupa una línea, pero no se trunca (ver hueco 2) |
| Clave desconocida simple | Se repite sin límite: una clave de 100 000 caracteres da un mensaje de 100 027 (hueco 2) |
| Ruta imprimible larga | Se repite entera: 3 231 caracteres por `GEOAGENT_CONFIG_FILE` (hueco 2) |
| `_describe` | Solo repite ASCII imprimible, truncado. OK |
| `(default)` | Solo añade el motivo, sin el valor. OK |
| `load_or_exit` | Siempre una sola línea imprimible en las ramas probadas. Con `Path` da traceback (nuevo B1) |
| `host` | **`0x7f`, `0X7F`, `0x7f.0x1` y `1.0x1` se aceptan**, y `getaddrinfo` los lee como `0.0.0.127`, `127.0.0.1` y `1.0.0.1` (nuevo B2) |
| `log_level` | `ınfo` (U+0131) se acepta como `INFO` por el `upper()` Unicode (m14) |
| Secretos y `queue_username` | Se aceptan `Cf`/`Zs` (`‮`, `﻿`, ` `, ` `). Es lo decidido (solo `Cc`), ver hueco 5 |
| `backend_url`/`queue_url` | Se aceptan `http://h h/`, `http://good\.evil.com/`, `http://ｅxample.com/` y `http://h%0aINFO/`. No repiten nada, pero la sintaxis del host de las URL se dejó para las features 7/9 (m9). Ver "Para features futuras" |
| `GEOAGENT_CONFIG_FILE=""` | Se trata como si no estuviera, sin test ni documentación (m16) |

### Bloqueantes

1. **B1 — regresión: `path` como `pathlib.Path` rompe la carga con un `AttributeError` sin tipar.** `_shown_path(path)` llama a `path.isprintable()` antes del `open`. En el código de `HEAD`, `load_agent_config(Path("ok.toml"))` cargaba bien y una ruta inexistente daba `ValidationError`. Ahora las dos fallan con `AttributeError`, y `load_or_exit` lo deja salir como traceback, porque solo captura `ValidationError`. Es probable que un CLI (argparse `type=Path`) o una feature futura pase un `Path`. Arreglo: al entrar en `_read_file` (o en `_resolve`), `path = os.fspath(path)` y, si el resultado no es `str` (es decir, `bytes`), lanzar `ValidationError("config file path must be text", field="config_file")`. Tests: un `Path` válido carga, y un `Path` inexistente y unos `bytes` dan `ValidationError` con `field == "config_file"`, con los dos loaders y también por `load_or_exit`. Si se quiere, ajustar la anotación a `str | os.PathLike[str] | None`.
2. **B2 — nombres hexadecimales ambiguos aceptados como `host` (hueco 1 del implementer).** Es la misma clase que el B2 de la ronda 7. La regla que propuse entonces ("última etiqueta solo dígitos") no contemplaba la notación hexadecimal de `inet_aton`: `0x7f` hace bind a `0.0.0.127` y `0x7f.0x1` a `127.0.0.1`, comprobado con `getaddrinfo`. Arreglo: tratar como numérica la última etiqueta que sea solo dígitos **o** que encaje con `0[xX][0-9A-Fa-f]*` (la regla "ends in a number" del estándar URL de WHATWG). Tests en `_BIND_HOST.invalid`: `0x7f`, `0X7F`, `0x7f.0x1`, `1.0x1` y `0x`. Para que `a.0x1g` siga siendo válido, añadir `0xg` y `a.0x1g` a las filas válidas. Actualizar la fila de `host` en `docs/config.md`.

### Mutaciones

- Detectadas (23): la ruta cruda en cada una de las 5 ramas, `_shown_path` con `isascii`, `strerror` con `exc.filename`, la clave con `match` (prefijo), la clave no imprimible con `field=key`, la etiqueta DNS con `match`, `_MAX_ECHO = 4000`, el truncado anulado para `str`, `_plain_str` con `Cf` o solo con el primer carácter, `;` con `params`, el TLD numérico solo si todo es numérico, el límite con `<`, `%` solo al principio, `_check_host` sin `text.isprintable()`, `_fs_path` sin `strip`, `(default)` con el valor, `load_or_exit` con `{exc!r}` y el secreto aceptado en el archivo.
- Sobreviven (2): la rama `ValueError` repitiendo la ruta (m15) y `GEOAGENT_CONFIG_FILE=""` tratado como ruta (m16).
- Las 2 equivalentes que reporta el implementer (quitar `not text.isprintable()` y quitar `" " in text` en `_bind_host`) **son equivalentes**. Con el `%` excluido, `ipaddress` solo acepta dígitos y hexadecimales ASCII y la regla DNS solo `[A-Za-z0-9-]`, así que cualquier carácter no imprimible o espacio interior se rechaza igual. El `strip` ya quita los de los extremos. Conviene mantenerlas: las pide la decisión y protegen ante un cambio futuro de `ipaddress` o de la regla DNS.

### Valoración de los huecos del implementer

1. `0x7f` como nombre DNS: **bloqueante** (B2).
2. La clave desconocida, la ruta imprimible y las claves en los errores de TOML no se truncan: **opcional, recomendado**. No pueden falsificar líneas (son imprimibles), pero un mensaje de 100 KB en stderr es un problema operativo. Un helper `_truncate(text)` con `_MAX_ECHO` (o 200) en `_shown_path`, en la clave y en el texto de `TOMLDecodeError` lo resuelve.
3. `field="config_file"` para la clave no imprimible: **aceptable, sin cambios**. No se puede nombrar la clave, y `config_file` lleva al operador al sitio correcto.
4. `cannot read` con `strerror` en vez de `str(exc)`: **correcto**. Evita repetir la ruta una segunda vez y sin pasar por el saneado.
5. D1 solo con `Cc` (se aceptan U+2028, RLO, BOM y NBSP en usuario y secretos): **opcional**. Los secretos no se muestran, el usuario sale escapado por `repr` y estos caracteres no permiten inyectar cabeceras. Un BOM o un NBSP en un token suele ser un error al pegarlo, así que rechazarlos con `isprintable()` (como D3) ayudaría a diagnosticar, pero no hace falta. El rechazo de NBSP en rutas (D3) es la contrapartida ya aceptada.
6. Construir las dataclasses o un `_Spec` a mano: heredado, ya está en "Para features futuras".

### Observaciones menores (no bloquean)

- m14. `_log_level` aplica `upper()` sobre texto Unicode: `ınfo` (i sin punto turca) se acepta como `INFO`. Exigir `text.isascii()` antes del `upper()` y añadir la fila `ınfo` a `_LOG_LEVEL.invalid`.
- m15. `_PATH_BRANCHES` no incluye la rama `ValueError` (NUL en la ruta): la mutación `f"invalid config file path: {path}"` (que repite un NUL crudo) pasa toda la suite. Añadir `nul_in_path` a la tabla de `TestUntrustedNamesInErrors`, por argumento y por el `env` explícito.
- m16. `GEOAGENT_CONFIG_FILE=""` se ignora (`or None`), sin test y sin documentación. Además, `docs/config.md` dice que una variable vacía "cuenta como valor". Documentar la excepción y añadir un test, o tratarla como error.
- m17. El informe cita `test_error_from_env_or_file_does_not_say_default`, que no existe. La comprobación está en `test_invalid_values_are_rejected_naming_the_key` (`assertNotIn("(default)")`), así que la cobertura es correcta, pero hay que corregir el informe.
- m18. Con Python 3.9.0-3.9.4, `ipaddress` aceptaba octetos con ceros a la izquierda (CVE-2021-29921, corregido en 3.9.5): allí `010.0.0.1` pasaría como IP y haría bind a `8.0.0.1`. Opciones: `requires-python = ">=3.9.5"` en `pyproject.toml`, o rechazar explícitamente los octetos con cero inicial en `_bind_host`. Barato. Recomiendo hacerlo junto con B2.

### Acceptance de la feature 3

- A1-A6: [x] sin regresiones en lo que ya cubrían, con dos salvedades: A1 (cargar desde el archivo) se rompe con `Path` (B1) y A4 ("inválida → aborta nombrando la clave") se rompe con el `host` hexadecimal (B2).

### Checkpoints

- C1: [x] están los archivos base y los docs; `./init.sh` termina con exit 0.
- C2: [x] solo la feature 3 está en `in_progress`; `progress/current.md` describe la sesión.
- C3: [x] solo hay paquetes previstos, sin `print()` en `src/`, sin cambios en `pyproject.toml` y sin secretos reales en los tests.
- C4: [x] con la salvedad heredada (cobertura no medible hasta añadir `pytest-cov`). Sin red ni mocks de filesystem, y < 60 s. `make test-integration` no aplica.
- C5: [ ] pendiente del cierre (entrada en `history.md` y estado `done`). `.claude/skills/` y `progress/fix_smoke_color.md` son del arnés.
- C6: [x] no aplica (`sdd: false`).

### Cambios requeridos

1. B1: aceptar `os.PathLike` en `path` (`os.fspath`) y rechazar con `ValidationError` lo que no sea texto. Con tests, también por `load_or_exit`.
2. B2: tratar como numérica la última etiqueta hexadecimal (`0[xX][0-9A-Fa-f]*`). Con tests y la fila de `docs/config.md` actualizada.
3. Recomendados en la misma ronda (baratos): m14, m15, m16, m17, m18 y el truncado del hueco 2.

### Para features futuras

- **7 `agent_http_client`:** el host de `backend_url` no se valida sintácticamente (m9, ronda 6). Casos concretos aceptados hoy: `http://h h/`, `http://ｅxample.com/` (IDNA/NFKC), `http://h%0aINFO/` y, sobre todo, `http://good\.evil.com/`. `urlparse` toma `good\.evil.com` como host, pero un parser WHATWG lo lee como host `good` y path `/.evil.com`. Validar el host de la URL con la misma regla que `_bind_host` (IP o nombre DNS ASCII), o como mínimo rechazar `\` y `%` en el netloc, con un test que compruebe que el cliente HTTP conecta al host que valida `config`.
- **9 `message_queue_layer`:** lo mismo para el host de `queue_url`.
- **5 `backend_api_skeleton`:** lo que se recomendó en la ronda 7 sigue vigente: el error de `bind` nombra `host`/`port`. Además, si alguna vez se pasa la ruta de la config como `Path` desde el CLI, que haya un test de arranque con `Path` (B1 lo cubre a nivel de `config`).
- **20 `structured_logging`:** sigue vigente lo de las rondas 6 y 7. Además, que el logger trunque los campos largos, porque los mensajes de `config` pueden llevar claves o rutas largas si no se aplica el hueco 2.
- **25 `integration_test_suite` (o la CI):** probar con Python 3.9 real, incluida una versión anterior a 3.9.5 si se mantiene `>=3.9` (m18), y la rama `tomli`.

## Ronda 9

**Veredicto:** APPROVED

Entrada: B1-B2 de "Decisiones pendientes tras la ronda 8", las decisiones del humano del 2026-10-08 (P1-P4) en `progress/questions_config_system.md` y "## Ronda 9" de `progress/impl_config_system.md`. Archivos revisados: `src/geoagent/common/config.py`, `tests/unit/test_config.py`, `docs/config.md` (y el cambio de arnés en `tests/unit/test_smoke.py`, `PYTHON_COLORS=0`, que no es de esta feature).

### Evidencia ejecutada

| Comando | Resultado |
|---|---|
| `make lint` | OK (`ruff check` limpio, 18 archivos formateados) |
| `make test` | 152 passed, 2120 subtests, 2.51 s (Python 3.14.4) |
| `./init.sh` | exit 0, "Entorno listo" (integración sin tests, exit 5 tolerado) |
| Sondas a mano | `r9/probe.py` en el scratchpad: `Path`/`bytes`/`PathLike`, `GEOAGENT_CONFIG_FILE` vacío/espacios/`\t`/`\n`, 26 hosts contrastados con `getaddrinfo(AI_NUMERICHOST)`, `log_level` Unicode, 9 caracteres invisibles en secretos y usuario, 9 errores de TOML, rutas largas, `load_or_exit` |
| Mutaciones propias | 28 mutaciones de `config.py` (`r9/mut.py`; copia en `r9/config.py.bak`, restaurado y comparado con `diff`: idéntico). Se detectan 27, sobrevive 1 equivalente |

### Bloqueantes de la ronda 8

- **B1 (`Path`):** [x] `_config_path` hace `os.fspath` y rechaza lo que no sea `str` con `field="config_file"` y sin eco. Sondas: `Path` válido carga con los dos loaders; `Path` inexistente da `file not found`; `bytes` y un `PathLike` que devuelve `bytes` dan `ValidationError`. Por `load_or_exit`: exit 2 y sin traceback (`test_non_text_paths_are_rejected_without_echo`). Mutaciones "sin `fspath`", "decodificar `bytes`" y "repetir `repr(path)`": detectadas.
- **B2 (host hexadecimal):** [x] `0x7f`, `0X7F`, `0x7f.0x1`, `1.0x1`, `0x`, `0x7f.0`, `a.b.0x` y `0177.1` se rechazan (todos los que `getaddrinfo` lee como IPv4 numérica); `0xg`, `a.0x1g`, `0x7F.example`, `1e3` y `localhost` se aceptan. Las 6 variantes del regex (sin `X`, `+` en lugar de `*`, solo minúsculas, `match` en lugar de `fullmatch`, sobre la primera etiqueta, quitarlo) se detectan. `docs/config.md` actualizado.

### Decisiones del humano

- **P1 (ceros iniciales):** [x] El rechazo manual funciona también con un `ip_address` permisivo (mock de 3.9.0-3.9.4 en `TestBindHostPythonCompat`). Las 5 mutaciones (quitarlo, sin `rsplit(":")`, `len > 2`, cualquier `0`, solo el primer octeto) se detectan; las válidas `0.0.0.0`/`10.0.0.1` vigilan el exceso de celo.
- **P2 (`GEOAGENT_CONFIG_FILE=""`):** [x] Definida y vacía (o `"  "`, `\t`, `\n`) da `config_file: config file path must not be empty`, también por `load_or_exit` (exit 2). Sin definir se cargan entorno + defaults. Un `path` explícito gana a la variable vacía. `docs/config.md:15-19` deja clara la diferencia. Mutaciones "`or None`/`env.get`", "sin `strip`", "quitar la comprobación" e "ignorar el `path` explícito": detectadas.
- **P3 (`isprintable` en credenciales):** [x] BOM, NBSP, RLO, U+2028, surrogate, U+200B y soft hyphen se rechazan en `auth_token`, `api_token`, `queue_password` y `queue_username`, sin repetir el valor; espacio ASCII y `ñandú` siguen siendo válidos. Las mutaciones "solo `Cc`" (72 fallos) y "repetir el valor" (84) se detectan.
- **P4:** [x] truncado (ruta, clave desconocida, texto de `TOMLDecodeError`): las mutaciones que quitan `_clip` en cada sitio, suben `_MAX_ECHO` o conservan el final se detectan. [x] m14: `ınfo`/`ıNFO` rechazados; quitar `isascii` lo detectan 16 tests. [x] m15: `nul_in_path` en `_PATH_BRANCHES`; repetir la ruta con el NUL lo detectan 40 tests. [x] m17: corregido en `progress/impl_config_system.md:161`.

### Ningún mensaje repite secretos ni caracteres de control

Revisadas todas las ramas que construyen mensajes: `_describe` (solo ASCII imprimible, truncado), `_plain_str`/`_fs_path`/`_bind_host`/URLs (sin eco), `_config_path` (sin eco), `_shown_path` (imprimible y truncada, o genérica), clave desconocida (solo `[A-Za-z0-9_.-]`, truncada), `TOMLDecodeError` (solo si es imprimible, truncado). Todas las sondas producen una sola línea imprimible.

### Mutación superviviente (equivalente)

- Quitar `if detail.isprintable()` en la rama `TOMLDecodeError`: ningún test lo detecta porque `tomllib`/`tomli` siempre formatean los caracteres y las claves con `repr` (sondas con `\x01`, `\x7f`, U+2028 en clave y en valor: todos los mensajes son imprimibles). Es una defensa ante un cambio de la librería; se puede mantener sin test.

### Valoración de las dudas del implementer

1. **El texto de `TOMLDecodeError` pierde la posición:** confirmado y es **la duda más relevante**. Con 40 caracteres, los errores de sintaxis más habituales quedan sin línea: `Cannot overwrite a value (at line 2, col…`, `Illegal character '\x01' (at line 1, col…`. En `HEAD` se mostraba entera. Es lo que decidió el humano (P4), así que no bloquea, pero recomiendo (m19) conservar el sufijo `(at line L, column C)`: separarlo con `re.search(r" \(at line \d+, column \d+\)$", detail)` (o `end of document`), truncar solo lo anterior y añadirlo después. El sufijo solo tiene dígitos, así que no reabre el riesgo. Conviene que el leader se lo plantee al humano antes de cerrar.
2. **La ruta se trunca por el principio:** confirmado (`file not found: /tmp/tmpqvxht3yv/ddddddddddddddddddddddd…` pierde `cfg.toml`). Menor (m20): para una ruta, el final (`…` + últimos 40 caracteres) identifica mejor el archivo. La mutación "conservar el final" falla 22 tests, así que el cambio necesitaría ajustar `test_long_path_is_truncated`. Opcional.
3. **Ruta de solo espacios tratada como vacía:** aceptable, sin cambios. Es coherente con `_non_empty` y un archivo llamado `" "` no es un caso real. Una ruta con espacios a los extremos (`" ok.toml"`) no se recorta y se usa tal cual, que es lo correcto.

### Observaciones menores (no bloquean)

- m19. Posición de los errores de TOML (duda 1, arriba).
- m20. Truncar la ruta conservando el final (duda 2, arriba).
- m21. `docs/config.md:30,33` (`store_path`, `db_path`) enumera "sin caracteres de control, separadores de línea, RLO ni surrogates", mientras que las credenciales (líneas 27, 34, 36, 37) añaden BOM y NBSP. Los dos usan `isprintable()`, que también rechaza BOM y NBSP en rutas (D3). Unificar el paréntesis para no sugerir que en las rutas se aceptan.
- m22. Un `os.PathLike` cuyo `__fspath__` lanza algo distinto de `TypeError` (sonda: `ValueError`) sale sin tipar. Es un objeto defectuoso del llamante, no una entrada del usuario: sin cambios.

### Acceptance de la feature 3

- A1-A6: [x]. Las salvedades de la ronda 8 (A1 con `Path`, A4 con host hexadecimal) quedan resueltas.

### Checkpoints

- C1: [x] están los archivos base y los docs; `./init.sh` termina con exit 0.
- C2: [x] solo la feature 3 está en `in_progress`; `progress/current.md` describe la sesión.
- C3: [x] sin paquetes nuevos, sin `print()` en `src/`, `pyproject.toml` sin cambios, sin secretos reales en los tests.
- C4: [x] con la salvedad heredada (cobertura no medible hasta añadir `pytest-cov`). Sin red; el único mock nuevo es `ipaddress.ip_address` (compatibilidad de versión), no de filesystem. < 60 s. `make test-integration` no aplica.
- C5: [ ] pendiente del cierre (entrada en `history.md` y estado `done`, que hace el leader). `.claude/skills/`, `AGENTS.md`, `tests/unit/test_smoke.py` y `progress/fix_smoke_color.md` son cambios del arnés.
- C6: [x] no aplica (`sdd: false`).

### Cambios requeridos

Ninguno bloqueante. Recomendado antes de cerrar (decisión del humano): m19. Opcionales: m20, m21.

### Para features futuras

- Siguen vigentes los de la ronda 8 (features 5, 7, 9, 20 y 25), que el leader pasa a `progress/current.md` al cerrar.
- **20 `structured_logging`:** si el logger trunca campos (recomendación de la ronda 8), usar el mismo criterio que `config` (`_clip`, 40 + `…`) o uno común en `geoagent.common`, y decidir si las rutas se truncan por el final (m20).
- **25 `integration_test_suite` (o la CI):** el rechazo de ceros iniciales (P1) solo se prueba con un mock de `ipaddress`; si la CI incluye un Python 3.9.0-3.9.4 real, añadir allí `GEOAGENT_HOST=010.0.0.1` como prueba de humo.

## Ronda 10

**Veredicto:** APPROVED

Entrada: m19, m20 y m21 de "Decisiones del humano tras la ronda 9 del reviewer (2026-10-08)" en `progress/questions_config_system.md` y "## Ronda 10" de `progress/impl_config_system.md`. Delta revisado: `_TOML_POSITION_RE`, `_clip_toml_error`, `_clip_tail` y `_shown_path` en `src/geoagent/common/config.py`; los tests `test_long_path_is_truncated`, `test_long_toml_syntax_error_keeps_position`, `test_short_toml_syntax_error_shows_line` y `test_toml_position_suffix_is_strict` en `tests/unit/test_config.py`; `docs/config.md`.

### Evidencia ejecutada

| Comando | Resultado |
|---|---|
| `make lint` | OK (`ruff check` limpio, 18 archivos formateados) |
| `make test` | 155 passed, 2131 subtests (Python 3.14); igual con `FORCE_COLOR=3` |
| `./init.sh` | exit 0 (integración sin tests, exit 5 tolerado) |
| Sondas | `r10/probe.py` en el scratchpad: 12 TOML con sufijos falsos en claves y valores, rutas largas, `load_or_exit`, 8 entradas directas a `_clip_toml_error` |
| Mutaciones | 18 mutaciones del delta (`r10/mut.py`; copia en `r10/config.py.bak`, restaurado y comparado con `diff`: idéntico). Se detectan 15; sobreviven 3, todas inofensivas (ver abajo) |

### m19: el sufijo de posición se conserva y su patrón es estricto

[x] `_clip_toml_error` trunca solo el texto anterior y añade el sufijo tal cual. Ejemplos reales: `Cannot overwrite a value (at line 2, column 6)`, `Invalid value (at end of document)`, `Cannot declare ('sss…… (at line 2, column 226)`.

[x] El patrón no puede repetir caracteres de control ni secretos: `re.ASCII`, `[0-9]+`, texto fijo y anclado con `\Z`, que no admite un `\n` al final como `$`. Sondas con sufijos falsos inyectados:
- En claves de tabla duplicadas: `"k (at line 9, column 9)"`, `"x\n (at line 1, column 1)"`, `"SECRET\x01 (at …)"`, `"a INFO fake (at …)"` y una clave de 200 caracteres. `tomllib` muestra la clave con `repr`, así que el sufijo falso queda dentro del texto, que se trunca. El sufijo que se conserva es siempre el real, al final y solo con dígitos. Todos los mensajes son imprimibles y de una línea.
- En valores: `"tok (at line 5, column 5)` sin cerrar y `"\q (at …)"`. `tomllib` no repite el valor, solo la posición real.
- Directas: un sufijo con `\n` dentro o al final, un dígito `٣`, `x` o texto detrás se truncan enteros (`test_toml_position_suffix_is_strict`). Con varios sufijos seguidos, o un número de línea enorme, se conserva solo texto fijo y dígitos, sin riesgo.

[x] Mutaciones detectadas: recortar todo con `_clip`, `\Z` → `$`, quitar el ancla, `\d` sin `re.ASCII`, dígitos → `.+` y → `[^)]+`, quitar `end of document`, aceptar solo `col`, no truncar el texto anterior y usar `_clip` en `_read_file`.

### m20: la ruta conserva el final

[x] `_clip_tail` devuelve `…` + los últimos 40 caracteres: `file not found: …dddddddddddddddddddd/my-real-config.toml`, también en `invalid TOML in …` y por `load_or_exit` (exit 2, una línea). `_shown_path` sigue comprobando `isprintable()` sobre la ruta **completa** antes de recortarla. Por eso un `\n` en cualquier punto da `<path with non-printable characters>` (sonda `a\nINFO fake…`), y el final mostrado no puede tener caracteres de control. En `str` no hay pares surrogate que se puedan partir. Un acento combinante al principio del recorte sigue siendo imprimible.

[x] Mutaciones detectadas (20 tests cada una): volver a recortar por el principio, quitar `…`, recortar un carácter de más, no truncar y quitar la comprobación de `isprintable` (100 tests).

### m21: docs coherentes con el código

[x] En `docs/config.md`, las filas `store_path`/`db_path` dicen lo mismo que las credenciales (BOM, NBSP, `isprintable()`), igual que `_fs_path` y `_plain_str`. El párrafo de truncado describe el recorte por el final de las rutas y el sufijo de posición limitado a dígitos. Coincide con el código.

### Mutaciones supervivientes

- Usar `detail[match.start():]` en lugar de `match.group()`: es equivalente, porque con `\Z` las dos dan lo mismo.
- Quitar `if detail.isprintable()`: ya estaba en la ronda 9. Es una defensa ante cambios de la librería; ninguna entrada real la activa.
- Aceptar solo `column` (quitar `col(?:umn)?`): sobrevive. `tomllib` (3.14) y `tomli>=2.0` siempre escriben `column`, así que la alternativa `col` no se usa y ningún test la cubre. Como solo acepta texto fijo, no supone ningún riesgo (m23, opcional).

### Regresiones

Ninguna. Los 155 tests pasan, incluidos `test_long_toml_error_text_is_truncated`, `test_printable_path_is_still_shown` y las ramas de `_PATH_BRANCHES` con ruta no imprimible y con NUL.

### Observaciones menores (no bloquean)

- m23. Quitar `col(?:umn)?` de `_TOML_POSITION_RE` y de las regex de los tests, o añadir una fila con `col` en `test_toml_position_suffix_is_strict`. Ahora mismo es una alternativa que nunca se usa. Opcional.

### Checkpoints

- C1: [x] `./init.sh` termina con exit 0.
- C2: [x] solo la feature 3 está en `in_progress`.
- C3: [x] sin paquetes nuevos ni `print()` en `src/`, sin secretos reales.
- C4: [x] tests deterministas y sin red, < 60 s. `make test-integration` no aplica. Sigue la salvedad de que la cobertura no se puede medir.
- C5: [ ] pendiente del cierre (`history.md` y estado `done`, que hace el leader).
- C6: [x] no aplica (`sdd: false`).

### Cambios requeridos

Ninguno.

### Para features futuras

Nada nuevo. Siguen vigentes las notas de las rondas 8 y 9 (features 5, 7, 9, 20 y 25). Para la 20 `structured_logging`, el criterio de truncado ya está fijado: `_clip` (por el principio) para valores y claves, `_clip_tail` (por el final) para rutas.

## Ronda 11

**Veredicto:** APPROVED

Delta mínimo sobre la ronda 10 (m23, decisión del humano del 2026-10-08).

- `_TOML_POSITION_RE` (`src/geoagent/common/config.py:51-53`) acepta solo `line N, column M` o
  `end of document`; no queda alternativa `col` en `src/` ni en las regex de los tests.
- `test_toml_position_suffix_is_strict`: nueva fila `" (at line 2, col 3)"` que exige truncado sin
  sufijo. Mutación `col(?:umn)?` aplicada en una copia en el scratchpad: el subTest de esa fila
  falla (`... (at line 2, col 3)' != '...…'`); sin la mutación, pasa (6 subtests).
- Sin regresiones: `make lint` (ruff check + format) limpio; `make test` 155 passed, 2132 subtests;
  `./init.sh` exit 0. `docs/config.md` ya documentaba `column`.

### Checkpoints
Sin cambios respecto a la ronda 10 (todos en verde).

### Recordatorio
Según la decisión del humano, la feature no se cierra sin su revisión completa del código y
autorización expresa.

## Ronda 12

**Veredicto:** CHANGES_REQUESTED

Revisa la ronda 12 del implementer (puntos 17-22 de "Sesión de preguntas: revisión del código
antes del cierre", decisiones del humano del 2026-10-11). Solo cambia `tests/unit/test_config.py`.

### Comprobaciones previas
- `src/` sin cambios: `md5sum src/geoagent/common/config.py` = `2ea300bb…` (igual que el md5
  tomado antes de la ronda 12 y que la copia de seguridad del implementer); `git diff --stat src/`
  sigue en 146 inserciones / 23 borrados; m23 (`column` estricto) intacto.
- Cambio manual del humano respetado: `("u\udcffp", None)` está en `_CONTROL_CHARS`
  (`tests/unit/test_config.py:254`) y `_CONTROL_CHARS_ENV_ONLY` (l. 256) ya no lo añade aparte.
- `make lint` exit 0; `make test` 155 passed, 2142 subtests; `./init.sh` exit 0.

### Puntos 18-22 (correctos)
- **18:** `_config_file_args` es función de módulo (l. 68-70) y se usa en `TestValidation`
  (`test_missing_file`, `test_invalid_toml`, `test_unreadable_files_raise_validation_error`), en las
  4 apariciones de `TestUntrustedNamesInErrors` y en `test_secret_in_file_is_rejected`. No queda
  ningún `if via_env` ni la expresión repetida (solo `test_file_path_from_env`, que es a propósito
  solo por variable).
- **19:** `load_or_exit(loader, arg, env=env)` (l. 896); 0 apariciones de `…`, 7 de `…`.
- **20:** dos filas `(url, mostrado)` con `_assert_shown`: `amqp://h/?{MASK}` y
  `amqp://h/?a={MASK}&{MASK}`.
- **21:** bucle `via_env` con el helper.
- **22:** tuplas `(loader, key, expected)`.

### Punto 3: cobertura
Comparación de identidades de subtest (parche de `TestCase.subTest` que registra los parámetros,
rutas temporales normalizadas) entre la versión anterior (copia del 2026-10-10 en el scratchpad,
con el duplicado del surrogate quitado como hizo el humano: 1893 subtests en `test_config.py`, es
decir, 2136 en total) y la actual (1899, es decir, 2142): **conjuntos idénticos salvo** +2 de
`test_non_utf8_file_via_load_or_exit_exits_2` (`via_env`) y +4 de
`test_valueless_query_item_is_masked` (fila mixta). Ninguna fila de las tablas se ha eliminado ni
alterado (las tablas pasan a `(env, toml, motivo)` con los mismos `(env, toml)`).

### Punto 17: motivo → test (mutación en copia de `src/` en el scratchpad, `PYTHONPATH` verificado)
Se mutaron **los 36 textos** de motivo uno a uno; "fallos" = subtests que fallan.

| Línea | Motivo | Test que lo comprueba | Fallos con mutación |
|---|---|---|---|
| 84 | `must be an integer` (bool) | `test_invalid_values_are_rejected_naming_the_key` (TOML `true`) | 2 |
| 94 | `must be an integer (got …)` | ídem | 42 |
| 99 | `must be a number` (bool) | ídem | 3 |
| 112 | `must be a number (got …)` | ídem | 39 |
| 118 | `must be a finite number` | ídem | 30 |
| 124 | `must be a string` | ídem | 48 |
| 132 | `must be printable text…` (`_plain_str`) | ídem | 86 |
| 139 | `must be greater than 0` (int) | ídem | 4 |
| 146 | `must be greater than 0` (float) | ídem | 12 |
| 153 | `must be between 1 and 65535` | ídem | 8 |
| 160 | `must not be empty` | ídem | 28 |
| 168 | `must be printable text…` (`_fs_path`) | ídem | 30 |
| 175 | `must be an IP address or a valid host name` | ídem | 103 |
| 207 | `must not contain ';' …` | ídem | 56 |
| 216 | `must be a valid URL` (ValueError) | ídem | 48 |
| 218 | `must be a valid URL` (puerto 0) | ídem (`h:0/s3cr3t`) | 6 |
| 225 | `must be a valid URL` (controles) | ídem | 21 |
| 233 | `must be an http(s) URL with a host` | ídem | 8 |
| 235 | `must not embed credentials; use auth_token` | ídem | 10 |
| 237 | `must not contain a query or fragment` | ídem | 12 |
| 247 | `must be a URL with scheme and host` | ídem | 12 |
| 250 | `… use queue_username and queue_password` | ídem | 24 |
| 253 | `must not contain a fragment` | ídem | 8 |
| 263 | `must be one of …` | ídem | 12 |
| 387 | `config file path must be a string or a path` | `test_non_text_paths_are_rejected_without_echo` | 10 |
| 389 | `config file path must not be empty` | `test_empty_path_argument_is_an_error`, `test_empty_env_variable_…` | 8 |
| 401 | `file not found` | `test_missing_file`, `test_missing_pathlib_path_names_config_file` | 6 |
| 404 | `cannot read …` | **ninguno** | **0** |
| 409 | `invalid TOML in` | `test_invalid_toml`, `test_long_toml_error_text_is_truncated` | 8 |
| 411 | `is not valid UTF-8` | `test_unreadable_files_raise_validation_error` | 4 |
| 413 | `invalid config file path` | ídem | 4 |
| 415 | `nested too deeply` | ídem | 4 |
| 430 | `unknown configuration key` (clave simple) | **ninguno** | **0** |
| 432 | `… (name has unsupported characters)` | **ninguno** (solo se comprueba el prefijo común) | **0** |
| 437 | `secrets must not be stored in the config file; set …` | **ninguno** | **0** |
| 452 | `(default)` | `test_invalid_default_is_rejected_naming_the_key` | 3 |

(l. 395, `TOML support requires the 'tomli' package`, es `pragma: no cover` y no aplica.)

Cada fila de las tablas espera el motivo de su rama real: todas pasan con el `src/` actual y cada
mutación de una rama concreta hace fallar solo las filas de esa rama (incluidas las tres de
`must be a valid URL` por separado, la ordenación http/amqp de `;` frente a query, y los dos
`must be greater than 0`). No hay motivos genéricos que pasen por casualidad: ningún `R_*` es
subcadena de otro motivo que pueda dar la misma fila.

### Bloqueantes
1. **`cannot read` (`_read_file`, l. 404) sin comprobar.** Está dentro del alcance explícito
   (motivos de `_read_file`) y el humano pidió "todos los motivos". La rama ya se ejercita
   (`_PATH_BRANCHES["cannot_read"]`, un directorio), pero ningún test hace `assertIn`. Añadir
   p. ej. un caso `"directory": (tmp, "cannot read")` en `test_unreadable_files_raise_validation_error`
   (sin comprobar el `strerror`, que depende del sistema).
2. **Motivos de `_resolve` sin comprobar** (también "motivos de rechazo"; alcance completo según el
   humano):
   - l. 430 `unknown configuration key`: `test_unknown_file_key` y `test_plain_unknown_key_is_named`
     solo miran `field`/la clave; añadir `assertIn("unknown configuration key", ...)`.
   - l. 432 `(name has unsupported characters)`: `test_unknown_key_is_repeated_only_if_plain`
     solo comprueba el prefijo, que comparte con l. 430; añadir `assertIn("unsupported characters", ...)`.
   - l. 437 `secrets must not be stored in the config file; set GEOAGENT_<KEY>`:
     `test_secret_in_file_is_rejected` solo mira `field` y que no repite el valor; añadir
     `assertIn("must not be stored in the config file", ...)` (y, si se quiere, `f"set GEOAGENT_{key.upper()}"`).
   Repetir las mutaciones de estas 4 líneas tras el cambio: cada una debe hacer fallar algún test.

### Observaciones menores (no bloquean)
- La copia en `/tmp/.../scratchpad/` que usé como "antes" es la del implementer del 2026-10-10
  menos el duplicado del surrogate; coincide en número (2136) con lo anotado por el leader.

### Checkpoints
Sin cambios respecto a la ronda 11 (todos en verde); el bloqueo es solo de cobertura del punto 17.

### Recordatorio
La feature no se cierra sin la autorización expresa del humano tras un APPROVED.

## Ronda 13

**Veredicto:** APPROVED

Revisa la ronda 13 del implementer, que responde a los bloqueantes 1 y 2 de la ronda 12. Solo
cambia `tests/unit/test_config.py`.

### Comprobaciones previas
- `src/` sin cambios: `md5sum src/geoagent/common/config.py` = `2ea300bb…` (el mismo que en la
  ronda 12); `git diff --stat src/` sigue en 146 inserciones / 23 borrados.
- `make lint` exit 0 (ruff check y format OK); `make test` 155 passed, 2146 subtests; `./init.sh`
  exit 0.

### Bloqueantes de la ronda 12 (resueltos)
- **1. l. 404 `cannot read`:** caso `"directory": (tmp, R_CANNOT_READ)` en
  `test_unreadable_files_raise_validation_error` (l. 637). `R_CANNOT_READ = "cannot read "` no
  comprueba el `strerror`, que depende del sistema operativo. Un directorio da `OSError` en Linux
  (`IsADirectoryError`) y en Windows (`PermissionError`), así que entra en esta rama y no en la de
  `FileNotFoundError`.
- **2. l. 430 / 432:** `test_unknown_file_key` (l. 597-598) y `test_plain_unknown_key_is_named`
  (l. 991-992) hacen `assertIn(R_UNKNOWN_KEY)` y `assertNotIn(R_UNSUPPORTED_CHARS)`;
  `test_unknown_key_is_repeated_only_if_plain` (l. 870-871) hace `assertIn` de los dos. Cada
  rama se distingue de la otra en las dos direcciones.
- **2. l. 437:** `test_secret_in_file_is_rejected` (l. 1223-1224) comprueba
  `secrets must not be stored in the config file` y `set GEOAGENT_{key.upper()}`.

### Punto 1: mutaciones de los 4 motivos
Las hice en una copia nueva de `src/` en el scratchpad (`r13/mut/src`). Con `PYTHONPATH`
apuntando a la copia, `geoagent.common.config.__file__` resuelve a esa copia. Lancé los tests del
repo contra cada mutación por separado; "fallos" son subtests que fallan.

| Línea | Mutación | Fallos | Tests que fallan |
|---|---|---|---|
| 404 | `cannot read` -> `unable to read` | 4 | `test_unreadable_files_raise_validation_error` |
| 430 | `"unknown configuration key"` -> `"unexpected key"` | 10 | `test_unknown_file_key`, `test_plain_unknown_key_is_named` |
| 432 | sin el sufijo `(name has unsupported characters)` | 14 | `test_unknown_key_is_repeated_only_if_plain` |
| 432 | prefijo `unknown configuration key (name` -> `unexpected key (name` | 14 | ídem |
| 437 | `secrets must not be stored in the config file` -> `no secrets in the file` | 8 | `test_secret_in_file_is_rejected` |
| 437 | `; set {ENV_PREFIX}` -> `; use {ENV_PREFIX}` | 8 | ídem |
| 437 | `{key.upper()}` -> `{key}` | 8 | ídem |

Cada mutación hace fallar solo los tests de su rama. Las tres últimas mutaciones de la tabla
(prefijo de 432, `set` y `key.upper()` de 437) son mías y van más allá de lo que pedía la ronda 12.

### Punto 2: tabla completa motivo -> test (36 textos)
Repetí las 36 mutaciones de la tabla de la ronda 12 contra los tests de la ronda 13. **Todas hacen
fallar al menos un test.** Las 32 líneas que ya estaban cubiertas dan los mismos números que en la
ronda 12. Las cuatro líneas que antes daban 0 fallos ahora dan:

| Línea | Ronda 12 | Ronda 13 |
|---|---|---|
| 404 | 0 | 4 |
| 430 | 0 | 10 |
| 432 | 0 | 14 |
| 437 | 0 | 8 |

Ya no queda ningún motivo de rechazo sin comprobar (l. 395 sigue con `pragma: no cover`).

### Punto 3: cobertura (2142 -> 2146)
Comparé las identidades de los subtests de `test_config.py` con el mismo registrador que en la
ronda 12, que parchea `TestCase.subTest` y normaliza las rutas temporales. Pasa de 1899 a 1903 y
la diferencia es exactamente **+4**:
`test_unreadable_files_raise_validation_error` con `case='directory'` × 2 loaders × `via_env` en
{False, True}. Todos los subtests de la ronda 12 siguen ahí con los mismos parámetros. No se ha
perdido ninguno.

### Observaciones menores (no bloquean)
- `test_secret_in_file_is_rejected` escribe `GEOAGENT_` literal en vez de `ENV_PREFIX`. Es
  deliberado y aceptable: así un cambio accidental del prefijo también rompe el test.
- En el scratchpad del implementer, `mut/src/geoagent/common/config.py` se quedó con la mutación
  `nope; set …` de l. 437 sin restaurar. Solo afecta a la copia; el `src/` real está intacto (md5
  verificado). Conviene restaurar las copias de trabajo al terminar para no confundir rondas
  posteriores.

### Checkpoints
Sin cambios respecto a la ronda 11: todos en verde. Ya no queda pendiente el bloqueo de cobertura
del punto 17.

### Recordatorio
La feature no se cierra sin la autorización expresa del humano tras este APPROVED.
