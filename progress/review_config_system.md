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
