# Informe de implementación — feature 3 `config_system` (sdd: false)

## Decisiones

- `load_agent_config(path=None, env=None)` y `load_backend_config(...)` devuelven dataclasses
  inmutables (`AgentConfig`, `BackendConfig`). `env` inyectable para tests; por defecto `os.environ`.
- Formato de archivo: solo TOML plano. YAML descartado: exigiría PyYAML (dependencia nueva) y el
  acceptance dice "TOML/YAML".
- Dependencia nueva: `tomli>=2.0; python_version < "3.11"` en `pyproject.toml` (condicional; en 3.11+ se
  usa `tomllib`). Necesaria por la matriz 3.9/3.14 de la CI. No instalada en el venv local (3.14).
- Errores: se reutiliza `ValidationError(message, field=...)`. El mensaje nombra la clave ofensora (la
  variable `GEOAGENT_*` si vino del entorno, o la clave del archivo).
- Aborto con exit != 0: `load_or_exit(loader, ...)` imprime a stderr y lanza `SystemExit(2)`.
- Secretos (`auth_token`, `api_token`, `queue_password`): solo por entorno; si aparecen en el archivo
  se rechaza (sin eco del valor) -> cumple "sin secretos en disco en claro". `repr()`/`str()` y
  `to_safe_dict()` los enmascaran como `***`. `queue_url` rechaza credenciales embebidas.
- Variable de entorno presente pero vacía cuenta como valor (así `GEOAGENT_BACKEND_URL=""` falla).
- Claves desconocidas en el archivo se rechazan.
- Los nombres de claves concretas (campos, defaults) no estaban en el acceptance; los fijé yo y
  están documentados en `docs/config.md`.
- "Ni en los logs": `common/logging.py` aún no existe; se ofrece `to_safe_dict()` para que el logger lo use.

## Mapa acceptance -> tests (`tests/unit/test_config.py`, 24 tests)

| Acceptance | Tests |
|---|---|
| Existe config.py con ambas funciones | todo el módulo de tests; `TestPrecedence.test_defaults_when_no_file_and_no_env` |
| Precedencia env > archivo > defaults | `test_file_overrides_defaults`, `test_env_overrides_file`, `test_env_overrides_default`, `test_file_path_from_env`, `test_unprefixed_env_is_ignored` |
| Prefijo `GEOAGENT_` documentado | `test_unprefixed_env_is_ignored`; `docs/config.md` |
| Config inválida aborta con exit != 0 y nombra la clave | `TestValidation.*` (puerto no numérico/fuera de rango, URL vacía/no http, `max_workers` 0 y -1, clave desconocida, archivo ausente/TOML inválido, queue_url con credenciales, secreto en archivo); `TestLoadOrExit.test_invalid_config_exits_nonzero_naming_key` |
| Secretos fuera de `repr()`/logs | `TestSecretMasking.*` (repr, str, to_safe_dict, backend, acceso al valor real, no enmascara vacío/no secretos) |
| test_config.py cubre precedencia, validación, enmascarado | las tres clases anteriores |

## Verificación

- `make lint`: OK. `make test-unit`: 125 passed (24 nuevos). `./init.sh`: OK (warn informativo de integración).

## Desviaciones

- Ninguna respecto al acceptance; la rama TOML de `tomli` (Python < 3.11) no se ejecuta localmente (3.14).
- `feature_list.json`: feature 3 en `in_progress`. No marcada `done`, sin commit.

## Ronda 2 (tras CHANGES_REQUESTED)

### Qué cambió

- `src/geoagent/common/config.py`:
  - `_http_url` rechaza credenciales embebidas (igual que `_queue_url`) y su mensaje de error ya no repite el valor crudo.
  - Nuevo `_finite_float` (con `math.isfinite`); `_positive_float` lo usa, así que `nan`/`inf` se rechazan en `heartbeat_interval`, `request_timeout` y cualquier float futuro, con la clave en el mensaje.
  - `load_or_exit` usa `sys.stderr.write(...)` en lugar de `print()`. `common/logging.py` aún no existe, así que se usa stderr como indica `docs/architecture.md`; conectar el logger queda para cuando exista (r1).
- No se tocó la decisión solo-TOML (pendiente del humano). Recomendaciones r2/r3 no aplicadas (r2 no es sencilla ni bloqueante; r3 es del humano).

### Mapa hallazgo → test (`tests/unit/test_config.py`)

| Hallazgo | Test |
|---|---|
| 1. credenciales en `backend_url` | `TestValidation.test_backend_url_with_credentials_rejected_without_leak`, `test_invalid_backend_url_error_does_not_echo_value` |
| 2. nan/inf | `TestValidation.test_non_finite_floats_rejected` (subtests por clave y valor), `test_non_finite_float_in_file_rejected` |
| 3. sin `print()` | `TestLoadOrExit.test_error_goes_to_stderr_not_stdout` (stdout vacío, stderr con el mensaje) |

### Resultados

- `make lint`: OK.
- `make test-unit`: 130 passed, 255 subtests.
- `./init.sh`: exit 0, "Entorno listo".

## Ronda 3 (cambios pedidos por el humano)

| Punto | Cambio | Tests |
|---|---|---|
| P2 | Eliminado `_secret()`; las 3 specs secretas usan `_parse_str` | toda `TestSecretMasking` (comportamiento sin cambios) |
| P3 | `TestPrecedence`: defaults de agente y backend en tests separados, comparando `to_safe_dict()` con el dict completo; estilo `cfg = ...` unificado; `_write` en lugar de `open` sin encoding | `test_agent_defaults_...`, `test_backend_defaults_when_no_file_and_no_env` |
| P4 | `_http_url` rechaza query y fragmento sin repetir el valor; `_Spec.mask` + `_mask_query` enmascara todos los valores de la query de `queue_url` en `to_safe_dict()`/`repr()`/`str()` (claves visibles, atributo intacto); `_Config._MASKS` | `TestUrlSecretsNeverEchoed` (variantes de userinfo, query/fragmento), `TestQueueUrlQueryMasking` |
| P5 | `_parse_str` informa solo del tipo (`got list`) | `test_url_secret_never_appears_in_error` (todas las ramas de rechazo de ambas URLs, env y archivo, incl. lista/tabla), `test_non_string_error_reports_only_the_type` |
| P6 | Tabla `INVALID` ejecutada desde env y archivo con `_load_from`; casos solo-archivo y solo-entorno; `max_workers = "3"` aceptado | `test_invalid_values_rejected_from_both_sources`, `test_invalid_toml_native_types_rejected`, `test_invalid_env_text_rejected`, `test_valid_native_and_text_values_accepted`, `test_quoted_number_in_file_is_accepted` |
| P7 | Enmascarado simétrico con secretos escritos a mano; MASK por cada secreto; vacíos, no secretos por introspección; secretos en archivo (todos los loaders, ruta por arg y por `GEOAGENT_CONFIG_FILE`); caso mixto | `TestSecretMasking` (6 tests) |
| Docs | `docs/config.md`: sección URLs, tipos del archivo, tabla actualizada | - |

Decisión posterior: `_queue_url` también rechaza el fragmento (sin repetir el valor); cubierto en `TestUrlSecretsNeverEchoed` y en la tabla `INVALID`; documentado en `docs/config.md`.

Verificación: `make lint` OK (ruff check + format); `make test`: 131 passed, 412 subtests passed; `./init.sh` en verde.

## Ronda 4

| Hallazgo | Cambio | Tests |
|---|---|---|
| 1 (bloqueante) | `_parse_url`: `urlparse` y `.port` dentro de `try/except ValueError` -> `ValidationError("must be a valid URL")` con la clave, sin el valor; usado por `_http_url` y `_queue_url` | `TestUrlSecretsNeverEchoed.test_url_secret_never_appears_in_error` (`[s3cr3t`, `[s3cr3t]`, `u@[s3cr3t]`, env y archivo), tabla `INVALID`, `TestLoadOrExit.test_malformed_url_exits_2_naming_key_without_secret` (exit 2, clave en stderr, sin secreto ni traceback) |
| 2 (bloqueante) | Puerto de las URL: numérico y 1-65535 | `h:s3cr3t`, `h:abc`, `h:0`, `h:99999`, `[::1]:99999` en ambos tests y en `INVALID` |
| m2 | `_describe`: `_parse_int`/`_parse_float` repiten solo str/int/float; listas/tablas informan del tipo | `test_non_scalar_in_numeric_field_reports_only_the_type` |
| m3 | (ronda 5: aplicado de verdad) `assertIsInstance(..., float)` para `heartbeat_interval = 5` | `test_valid_native_and_text_values_accepted` |
| m4 | Test de no-eco sin `"x'"` frágil (usa `got list`; centinela `s3cr3t` en el nuevo test) | `test_non_string_error_reports_only_the_type` |
| m5 | `docs/config.md`: `;params` forman parte del path (no se vigilan), nombres de query visibles, validación de host/puerto | - |

Verificación: `make lint` OK; `make test`: 133 passed, 488 subtests; `./init.sh` en verde.

## Ronda 5

| Hallazgo | Cambio | Tests |
|---|---|---|
| 1 (bloqueante) | `_read_file` convierte `UnicodeDecodeError` (TOML no UTF-8), `ValueError` (byte NUL en la ruta) y `RecursionError` (anidado patológico) en `ValidationError(field="config_file")` sin el contenido | `test_unreadable_files_raise_validation_error` (3 casos x ruta por argumento y por `GEOAGENT_CONFIG_FILE`), `test_non_utf8_file_via_load_or_exit_exits_2` (exit 2, `config_file` en stderr, sin secreto ni traceback) |
| Repaso de otras excepciones | Revisadas: `int()`/`float()` (ValueError capturado), `OSError`/directorio/permisos (capturados), `TOMLDecodeError`, `urlparse` (ronda 4). Sin más huecos conocidos. Host con caracteres de control (hallazgo 3 menor) no se toca | - |
| m3 | Aplicado de verdad: `assertIsInstance(cfg.heartbeat_interval, float)`; corregida la fila m3 de la ronda 4 | `test_valid_native_and_text_values_accepted` (verificado con grep en el archivo) |

Verificación: `make lint` OK; `make test`: 135 passed, 494 subtests; `./init.sh` en verde.

## Ronda 6

- m7: `_describe` trunca el valor repetido a 40 caracteres con `…` (y nombra el tipo si el int es demasiado grande para `repr`); los mensajes "got {number}" usan `_describe`. Test: `test_long_numeric_value_is_truncated_in_error`, `test_huge_digit_string_and_native_int_are_rejected_briefly`.
- m8b: enteros y floats en texto validados con regex ASCII (sin `_` ni dígitos Unicode); se mantienen espacios, signo, decimal/exponencial, nan/inf (rechazados luego como no finitos) y nativos TOML. Tests: `test_numeric_text_accepts_only_ascii_digits_without_underscores`, `test_numeric_text_still_accepts_spaces_sign_and_exponent`, `test_quoted_number_in_file_is_accepted`.
- Host con control: `_check_host` en `_http_url` y `_queue_url` rechaza texto/host no imprimible (incluye `\t\r\n` que urlparse descarta) con "must be a valid URL", sin repetir el valor. Test: `test_control_characters_in_host_are_rejected_without_echo`.
- docs/config.md actualizado. `make lint`, `make test` (140 passed) e `./init.sh` OK. Feature NO marcada done.

## Ronda 7

Entrada: `progress/questions_config_system.md`, sesión 2026-10-05, puntos 8-16 y decisiones del 2026-10-06. Archivos: `src/geoagent/common/config.py`, `tests/unit/test_config.py`, `docs/config.md`.

### Código (`config.py`)
- Punto 9: `_resolve` pasa también `spec.default` por `spec.parser(key, default)`; un default inválido falla al cargar nombrando la clave.
- Punto 12: `_bind_host` (IP con `ipaddress.ip_address`, sin corchetes, o nombre DNS con etiquetas `[A-Za-z0-9-]` de 1-63 sin `-` en los extremos) para `host`; `_fs_path` (no vacío + rechazo de categoría Unicode `Cc`, incl. NUL) para `store_path`/`db_path`. Ningún error repite el valor.
- Punto 16: `_check_path` rechaza un `;` literal en `urlsplit(text).path` (no `parsed.params`: `urlparse` no lo ve en `a;t=x/b`, ni con `amqp`, ni `api;` vacío) en `_http_url` y `_queue_url`; `%3B` se acepta.

### Tests (`tests/unit/test_config.py`, reescrito)
- P8: tipos de validación `_HTTP_URL`, `_QUEUE_URL`, `_PORT`, `_POSITIVE_INT`, `_POSITIVE_FINITE_FLOAT`, `_LOG_LEVEL`, `_BIND_HOST`, `_PATH`, `_ANY_STR`, `_SECRET_TYPE` con filas `invalid (env, toml)` y `valid (env, toml, esperado)`; mapa `FIELD_TYPES` escrito a mano por clase. `test_every_field_is_classified` falla en ambos sentidos (campo sin clasificar / clasificado inexistente); `test_invalid_values_are_rejected_naming_the_key` recorre `dataclasses.fields` de ambos loaders desde las dos fuentes. Absorbe los tests sueltos de tipos nativos/texto.
- P9: `test_defaults_when_no_file_and_no_env` (dict completo + tipos exactos, ambos loaders); `test_invalid_default_is_rejected_naming_the_key` (parchea `_AGENT_SPECS`/`_BACKEND_SPECS` con `mock.patch.dict`: `max_workers=0`, `port=70000`, `host="h:80"`).
- P10: casos válidos con valor y `assertIs(type(v), type(esperado))`, con la columna del número entre comillas, en `test_valid_values_are_accepted_with_exact_type`; `test_file_path_from_env` comprueba también `request_timeout` (valor y tipo). Sustituye a `test_valid_native_and_text_values_accepted` y `test_quoted_number_in_file_is_accepted`.
- P11: `LOADERS`, `_INT_FIELD`, `_OTHER_KEY`; inventario aplicado (precedencia con `request_timeout` en ambos loaders; clave desconocida incl. la del otro loader; entorno del otro loader ignorado; archivo ausente / TOML inválido / ilegible por argumento y por `GEOAGENT_CONFIG_FILE`; load_or_exit con ambos loaders y fuentes; masking de query con ambos loaders y fuentes).
- P12: filas de host/URL/ruta con NUL, `\n`, `\x07` (escapados en TOML) y `\udcff` (solo entorno). `test_error_never_echoes_the_value`: para cada fila de los tipos `no_echo`, el valor decodificado no aparece ni tal cual ni escapado (`repr(v)[1:-1]`) en `str`/`repr` de la excepción, y `s3cr3t` tampoco.
- P13: context manager `_config_source(source, key, raw)` -> `(path, env)`; `_load_from` lo usa; `TestLoadOrExit` llama a `load_or_exit(loader, path, env=env)` con el loader real.
- P14: `TestUrlSecretsNeverEchoed` desaparece; `TestValidation` (qué se acepta) y `TestErrorMessages` (qué dice el mensaje: no eco, solo tipo, brevedad).
- P15: helpers `_views(cfg)` (ausencias) y `_assert_shown(test, cfg, key, shown)` (presencias en `to_safe_dict`, `repr`, `str`) usados en todos los sitios listados.
- P16: los casos de la tabla (`api;token=`, `a;token=/b`, `vhost;password=`, `v;p=...?heartbeat=1`, `api;`) en las tablas de `backend_url` y `queue_url` (ambos loaders, dos fuentes) y en el test de no eco; `%3B` aceptado (filas válidas y `test_url_without_query_unchanged`).
- Docs: `docs/config.md` (frase de `;params` sustituida por el rechazo, tabla con host/rutas, nota sobre defaults validados).

### Comprobaciones
- Ejecutado a mano: host (`h:80`, `http://h`, `[::1]`, `-h-`, `h\x00`, `h h`, `a..b`, `h.`, `\udcffh`, 64 `a` rechazados; `a-b.c`, `1.2.3.4`, `::1` aceptados) y los cuatro casos `;` + `%3B` en ambas URL.
- Mutaciones (código revertido después): quitar `_check_path` (58 tests fallan), no validar defaults (3), eco del host (37), eco de ruta con control (12), `host` con `_non_empty` (72), `_parse_str` con eco (12). Todas detectadas.
- `make lint test`: ruff check y format OK; 136 passed, 1261 subtests passed. `./init.sh` en verde (ver abajo).

### Dudas / huecos no cubiertos por las decisiones (no decididos)
1. IPv6 con zona (`fe80::1%eth0`) se acepta como IP (`ipaddress` de Python >= 3.9 la admite).
2. Nombres solo numéricos con puntos (`999.1.1.1`) pasan como DNS (cumplen la regla de etiquetas). No se limita la longitud total (253) ni se acepta el punto final (`h.` se rechaza).
3. `store_path`/`db_path`: solo se rechaza `Cc`; un sustituto aislado (`\udcff`) se acepta y puede fallar luego al abrir el archivo.
4. `;` solo se vigila en el path: en la query (`?a=1;b=2`) y en el netloc no. Con `_mask_query` la query ya se enmascara.
5. El nombre del tipo `_NON_EMPTY_STR` del punto 8 se dividió en `_BIND_HOST` y `_PATH` (cada uno con reglas propias); `_SECRET` se llama `_SECRET_TYPE` en el código.
6. Un default inválido informa con la clave (`field=key`), sin distinguir que viene del default.
7. Feature NO cambiada de estado en `feature_list.json`.

## Ronda 8

Entrada: B1-B5 y m11-m13 de "## Ronda 7" de `progress/review_config_system.md`; decisiones del humano del 2026-10-07 en `progress/questions_config_system.md`. Archivos: `src/geoagent/common/config.py`, `tests/unit/test_config.py`, `docs/config.md`. Estado de la feature en `feature_list.json` sin tocar.

### Punto por punto
- **B1** `_bind_host`: antes del intento de IP rechaza texto no imprimible, con espacio ASCII o con `%` (sin zona IPv6). Filas en `_BIND_HOST.invalid`: `fe80::1%eth0`, `fe80::1%1`, `fe80::1%a b`, `h%25`, `%`, `fe80::1%a\n b`, `fe80::1%a\x00b`, `fe80::1%a\x1b[31m`, `h\tb`, NBSP, U+2028, `::1\nINFO fake`, `1.2.3.4\x00` (dos loaders, dos fuentes; las de control escapadas en el TOML).
- **B2** `_bind_host`: rechaza nombres de más de 253 caracteres (`_MAX_HOST_LEN`) y los de última etiqueta solo dígitos (`labels[-1].isdigit()`, tras validar etiquetas ASCII). Filas inválidas: `010.0.0.1`, `0x7f.1`, `127.1`, `2130706433`, `999.1.1.1`, `1`, `a.1`, `a.123`, `1.2.3`, dos nombres de 254 caracteres. Válidas: nombre de exactamente 253, `1a`, `a.b1`, `1.example.com`.
- **B3** `_check_path` renombrada `_check_semicolon`: rechaza `;` en `urlsplit(text).netloc` o en el path, mensaje sin eco. Filas en `_url_invalid` (http y amqp, dos fuentes): `h;token=s3cr3t`, `h;password=s3cr3t/p`, `h;token=s3cr3t:80`, `h;token=s3cr3t?x=1`, `;s3cr3t`. Para `http` la fila con query ya la rechaza otra regla antes; `amqp` prueba la de `;`.
- **B4** `_shown_path` (ruta imprimible o `<path with non-printable characters>`) en las ramas de `_read_file`: no existe, `cannot read` (ahora con `exc.strerror`, no `str(exc)`), TOML inválido, no UTF-8 y anidado profundo. La clave TOML desconocida se repite solo si cumple `[A-Za-z0-9_.-]+`; si no, `config_file: unknown configuration key (name has unsupported characters)`. Tests (`TestUntrustedNamesInErrors`): 5 ramas x 5 nombres (`\n`, `\x1b`, `\r`, U+2028, surrogate; el archivo existe de verdad con ese nombre) x argumento/`GEOAGENT_CONFIG_FILE` x 2 loaders, comprobando `str` y `repr` de la excepción (imprimible, sin el nombre ni su escape, sin `INFO fake`, sin el directorio temporal); lo mismo por `load_or_exit` (stderr: una sola línea, imprimible); ruta imprimible sigue mostrándose; claves `"x\nINFO fake"`, `\x1b`, `\r`, espacio, U+2028, `é`, `a/b` por excepción y por `load_or_exit`; claves simples (`bogus`, `a-b_c`, `s3cr3t`) siguen nombradas.
- **B5** `no_echo` es `True` por defecto (`vtype.get("no_echo", True)`); solo `_PORT`, `_POSITIVE_INT` y `_POSITIVE_FINITE_FLOAT` ponen `False`, con un comentario que cita el punto 5. `_LOG_LEVEL`, `_ANY_STR` y `_SECRET_TYPE` quedan vigilados.
- **D1** `_plain_str` (`_parse_str` + rechazo de `Cc`) en `queue_username`, `queue_password`, `auth_token`, `api_token`. Filas `_CONTROL_CHARS` (`\r\n`, NUL, ESC, DEL, `\x85`, tab) en `_ANY_STR.invalid` (dos fuentes) y en `_SECRET_TYPE.invalid` solo entorno (los secretos en archivo ya se rechazan antes). Válido nuevo: `é ü`. Pasan por el test de sin eco.
- **D3** `_fs_path` exige `isprintable()`. Filas: U+2028, RLO (U+202E), NBSP, `\x1b`, surrogate `a\udcffb` (solo entorno).
- **D2** `_describe` repite un `str` solo si `isascii() and isprintable()`; si no, `got str`. Test `test_numeric_error_echo_is_ascii_only` (dos loaders, int y float, dos fuentes: `abc` se repite; salto de línea, ESC, NUL, `é1`, `١٢`, RLO dan `got str`, sin el valor ni su escape).
- **"(default)"**: `_resolve` añade ` (default)` al motivo de un default inválido (el `field` sigue siendo la clave). Tests: el de defaults inválidos exige `(default)`; `test_invalid_values_are_rejected_naming_the_key` exige su ausencia en errores de entorno/archivo (no existe un test aparte `test_error_from_env_or_file_does_not_say_default`; corregido en la ronda 9).
- **m11** `test_non_scalar_in_numeric_field_reports_only_the_type` comprueba `got dict` / `got list`. **m12** `_url_invalid` incluye `1.5` y `1979-05-27`. **m13** la tabla de `docs/config.md` menciona el `;` en `backend_url` y `queue_url`.
- **Docs** (`docs/config.md`): tabla de claves (host, rutas, secretos, `queue_username`, URLs), D2, `(default)`, `;` en el host y párrafo sobre ruta y claves no imprimibles.

### Comprobaciones
- Leído en el archivo cada cambio de `config.py` tras editarlo. Ejecutado a mano: `fe80::1%eth0`, `010.0.0.1` y `2130706433` rechazados como `host`; `0x7f` aceptado (ver huecos).
- Mutaciones (script en el scratchpad; `config.py` restaurado y comparado): detectadas 26 de 28: `%` permitido, sin límite 253 (y límite 254), sin regla de TLD numérico (y sobre la primera etiqueta), `;` sin vigilar en netloc / en path, ruta cruda, `cannot read` con `str(exc)`, clave cruda / regex con espacio / regex `.+`, `_plain_str` sin comprobar (y cada uno de los cuatro campos por separado), `_fs_path` solo `Cc`, `_describe` repitiendo no ASCII / solo ASCII / solo imprimible, sin `(default)`, `(default)` también en entorno/archivo, `_log_level` con eco, `_plain_str` con eco. Sobreviven 2, **equivalentes**: quitar `not text.isprintable()` y quitar `" " in text` en `_bind_host`, porque tras ellos la regla de etiquetas ASCII y `ipaddress` (sin `%`) ya rechazan lo mismo. Se mantienen porque la decisión los pide explícitamente antes de la IP.
- `make lint test`: ruff check y format OK; 142 passed, 1885 subtests. `./init.sh` exit 0.

### Huecos que las decisiones no cubren (no decididos)
1. `0x7f` (un solo componente hexadecimal) pasa como nombre DNS: su última etiqueta no es solo dígitos pero `inet_aton` lo lee como 127.0.0.1; igual `0x7f.0x1`. La regla pedida (última etiqueta numérica) no lo ve. Opciones: rechazar etiquetas `0x...` o aceptarlo.
2. La clave TOML desconocida que cumple `[A-Za-z0-9_.-]+` se repite sin límite de longitud (una clave de megabytes saldría entera). Ni la ruta imprimible ni la clave se truncan como `_describe`.
3. El mensaje de una clave desconocida no imprimible usa `field="config_file"` (la clave no se puede nombrar); se podría usar otro campo o ninguno.
4. `cannot read` ya no incluye el texto de `str(exc)` (solo `strerror`); es un cambio de redacción para no repetir la ruta una segunda vez.
5. D1 solo exige ausencia de `Cc`: U+2028, RLO, etc. se aceptan en `queue_username` y secretos. D3 rechaza rutas con NBSP u otros espacios Unicode (contrapartida ya avisada).
6. Un `_Spec` construido a mano o las dataclasses no pasan por estos parsers (heredado, "Para features futuras").


## Ronda 9

Entrada: B1-B2 de "Decisiones pendientes tras la ronda 8" y las decisiones del 2026-10-08 (P1-P4) en `progress/questions_config_system.md`. Cada cambio con filas/tests en `tests/unit/test_config.py` y reflejado en `docs/config.md`.

### Cambios por punto
- **B1** `_config_path` (nuevo, en `_resolve`): `os.fspath(path)`; si no es `str` (bytes, int, objeto...) `ValidationError(field="config_file")` sin repetir el valor. `Path` se acepta. Tests: `TestConfigFilePath.test_pathlib_path_is_accepted`, `test_missing_pathlib_path_names_config_file`, `test_non_text_paths_are_rejected_without_echo` (dos loaders, y por `load_or_exit`: exit 2, sin traceback).
- **B2** `_bind_host`: la última etiqueta se rechaza si es solo dígitos o encaja con `0[xX][0-9A-Fa-f]*` (`_HEX_LABEL_RE`). Filas inválidas: `0x7f`, `0X7F`, `0x7f.0x1`, `1.0x1`, `0x`, `a.0xAb`, `0x0`; válidas: `0xg`, `a.0x1g`, `0x1.example.com`.
- **P1** `_bind_host`: tras aceptar `ipaddress.ip_address`, rechaza a mano octetos IPv4 con cero inicial (también en `::ffff:a.b.c.d`). Filas inválidas: `1.02.3.4`, `::ffff:01.2.3.4`, `00.0.0.0` (y `010.0.0.1`, ya existente); válidas `::ffff:1.2.3.4`. `TestBindHostPythonCompat` simula el `ip_address` permisivo de 3.9.0-3.9.4 (mock) para probar que el rechazo manual funciona en cualquier versión.
- **P2** `_resolve` ya no usa `or None`: `GEOAGENT_CONFIG_FILE` definida y vacía (o solo espacios), o `path=""`, da `ValidationError(field="config_file", "config file path must not be empty")`; sin definir sigue cargando entorno + defaults. Tests: `test_empty_path_argument_is_an_error`, `test_empty_env_variable_is_an_error_but_unset_is_not` (incluye `load_or_exit`), `test_explicit_path_wins_over_empty_env_variable`. `docs/config.md` deja explícita la diferencia.
- **P3** `_plain_str` exige `isprintable()` (mensaje "must be printable text without control characters", sin eco) en `queue_username`, `queue_password`, `auth_token`, `api_token`. Filas en `_CONTROL_CHARS`: BOM, NBSP, RLO, U+2028; y surrogate (solo entorno) en `_CONTROL_CHARS_ENV_ONLY`. Se quitó el `import unicodedata`.
- **P4 truncado** `_clip` (límite `_MAX_ECHO`, compartido con `_describe`) en la ruta mostrada (`_shown_path`), en la clave desconocida (`field=_clip(key)`) y en el texto de `TOMLDecodeError` (si no es imprimible se omite). Tests: `test_long_path_is_truncated` (todas las ramas salvo NUL, argumento y entorno, y por `load_or_exit`), `test_long_unknown_key_is_truncated` (clave de 100 000 caracteres), `test_long_toml_error_text_is_truncated`. `test_printable_path_is_still_shown` sigue pasando (ruta corta).
- **P4 m14** `_log_level`: si el texto no es ASCII no llama a `upper()` y falla. Filas `_LOG_LEVEL.invalid`: `ınfo`, `ınfo` en mayúsculas dotless (`\u0131NFO`).
- **P4 m15** `_PATH_BRANCHES["nul_in_path"] = {"nul": True}` (`_file_named(..., nul=True)` añade un NUL crudo sin crear nada); lo recorren `test_path_with_control_characters_is_not_repeated` y `..._via_load_or_exit` (argumento y entorno). `test_printable_path_is_still_shown` y `test_long_path_is_truncated` lo saltan (su mensaje no muestra la ruta).
- **P4 m17** corregida la cita del test inexistente en la ronda 8 (arriba).

### Comprobaciones
- Mutaciones (una a una, `config.py` restaurado desde copia): sin `_HEX_LABEL_RE` (28 fallos), sin rechazo de ceros iniciales (4), sin `isascii` en `log_level` (16), sin `isprintable` en `_plain_str` (168), `or None` de vuelta (2), sin `_clip` en la clave (2), en el texto TOML (4), en la ruta (20), sin `os.fspath` (4): todas detectadas.
- `make lint test`: ruff check y format OK; 152 passed, 2120 subtests passed. `./init.sh` exit 0. Igual con `FORCE_COLOR=3`.

### Dudas abiertas
1. Truncar el texto de `TOMLDecodeError` a 40 caracteres suele cortar el sufijo `(at line L, column C)`; si se quiere conservar la posición, habría que truncar solo la parte inicial. Se dejó como decidió el humano.
2. La ruta se trunca por el principio (se pierde el nombre del archivo en rutas largas); alternativa: conservar el final.
3. `path` solo espacios se trata como vacío (igual que `_non_empty`); un archivo llamado literalmente `" "` no se podría cargar.

## Ronda 10

Entrada: m19, m20, m21 de "Decisiones del humano tras la ronda 9 del reviewer".

- **m19:** `config.py` añade `_TOML_POSITION_RE` (`\(at (line D+, col(umn)? D+|end of document)\)\Z`, `re.ASCII`, dígitos `[0-9]`) y `_clip_toml_error`: trunca solo el texto previo y añade el sufijo intacto; si el sufijo no cumple el patrón estricto (no dígitos, saltos de línea, texto detrás) se trunca todo como antes. Tests: `test_long_toml_syntax_error_keeps_position` (mensaje largo, muestra `… (at line 2, column N)`), `test_short_toml_syntax_error_shows_line` (`Cannot overwrite`/`Illegal character` con línea), `test_toml_position_suffix_is_strict`; `test_long_toml_error_text_is_truncated` sigue demostrando que el resto se trunca.
- **m20:** `_clip_tail` (`…` + últimos `_MAX_ECHO`) usado por `_shown_path`. `test_long_path_is_truncated` ahora exige `…` + final de la ruta, el nombre acortado y que no aparezca el principio (falla si se vuelve a truncar por el principio).
- **m21:** `docs/config.md`: filas `store_path`/`db_path` unificadas con las credenciales (BOM, NBSP); párrafo de truncado actualizado (rutas por el final, sufijo de posición).
- Ningún mensaje repite secretos ni caracteres de control (el sufijo se valida con dígitos; `message.isprintable()` comprobado en los tests).
- Verificación: `make lint test` y `./init.sh` en verde, también con `FORCE_COLOR=3`: 155 passed, 2131 subtests.

## Ronda 11

- m23: `_TOML_POSITION_RE` (src/geoagent/common/config.py) acepta solo `column`; regex de los tests (líneas ~896 y ~907) también.
- `test_toml_position_suffix_is_strict`: nueva fila `" (at line 2, col 3)"` sobre texto largo -> se trunca sin sufijo.
- Mutación `col(?:umn)?` reintroducida: el test falla (subTest de esa fila); revertida.
- `docs/config.md` ya decía `column`; sin cambios.
- `make lint test` (155 passed) e `./init.sh` OK, también con `FORCE_COLOR=3`.

## Ronda 12

Entrada: puntos 17 a 22 de "Sesión de preguntas: revisión del código antes del cierre". Solo `tests/unit/test_config.py`; `src/` sin tocar (`md5sum` de `config.py` idéntico antes y después, el diff previo de `src/` sigue siendo el de las rondas anteriores). Respetado el surrogate de `_CONTROL_CHARS` editado por el humano (sin cambios en esa lista ni en `_CONTROL_CHARS_ENV_ONLY`).

- **17:** las filas `invalid` de las tablas pasan a `(env, toml, motivo)`. Helper `_because(motivo, filas)` y constantes `R_*` con el texto esperado. `test_invalid_values_are_rejected_naming_the_key` hace `assertIn(motivo, str(exc))`; `test_error_never_echoes_the_value` desempaqueta 3 campos. `_INT_INVALID` pasa a `_int_invalid(not_positive)` (`-1` y `0` dan `greater than 0` en `max_workers` y `between 1 and 65535` en `port`); `_url_invalid(scheme, credentials, no_host, fragment, semicolon_and_query)` agrupa las filas por motivo. `config_file`: `file not found` (`test_missing_file`), `invalid TOML in` (`test_invalid_toml`), `not valid UTF-8` / `invalid config file path` / `nested too deeply` (`test_unreadable_files_raise_validation_error`, ahora `cases` con `(ruta, motivo)`).
- **18:** `_config_file_args(via_env, path)` es función de módulo (tras `_label`). Usada en `TestValidation`, en las 4 apariciones de `TestUntrustedNamesInErrors` y en `TestSecretMasking.test_secret_in_file_is_rejected`.
- **19:** `load_or_exit(loader, arg, env=env)`; todos los `…` pasan a `…` (7 apariciones, ninguna `…` queda).
- **20:** `test_valueless_query_item_is_masked` itera filas `(url, mostrado)`: `amqp://h/?s3cr3t` -> `amqp://h/?{MASK}` y `amqp://h/?a=1&s3cr3t` -> `amqp://h/?a={MASK}&{MASK}`, con `_assert_shown`.
- **21:** `test_non_utf8_file_via_load_or_exit_exits_2` con bucle `via_env` y el helper.
- **22:** `test_valid_config_is_returned` itera `(loader, key, expected)`.

### Motivos reales (ejecutados, iguales con env y con archivo; los de números llevan además `(got ...)`)
- Enteros: `must be an integer` (texto, float, bool, fecha, lista, dict, vacío, `1_0`, dígitos no ASCII); `must be greater than 0` (`-1`, `0`) en `max_workers`; `must be between 1 and 65535` (`-1`, `0`, `65536`, `70000`) en `port`.
- Floats: `must be a number` (texto, `true`, `1_0.5`, vacío, lista, dict, fecha); `must be greater than 0` (`0`, `-1`); `must be a finite number` (`nan`, `inf`, `-inf`, `Infinity`).
- `log_level`: `must be one of DEBUG, INFO, WARNING, ERROR, CRITICAL` (`LOUD`, `ınfo`, `ıNFO`); `must not be empty` (`""`); `must be a string` (no texto).
- `host`: `must not be empty` (`""`, `"   "`); `must be an IP address or a valid host name` (resto de texto, incluidos controles y surrogate); `must be a string` (no texto).
- Rutas (`store_path`, `db_path`): `must not be empty`; `must be printable text without control characters`; `must be a string`. `queue_username` y secretos: `must be a string` / `must be printable text without control characters`.
- `backend_url`: `must not embed credentials; use auth_token`; `must be an http(s) URL with a host` (sin host, `ftp`); `must be a valid URL` (corchetes, puerto, controles, surrogate); `must not contain a query or fragment` (también `h/v;p=..?q` y `h;t=..?x=1`, porque la query se comprueba antes que `;`); `must not contain ';' in the host or path (use %3B)`; `must not be empty`; `must be a string`.
- `queue_url`: `must not embed credentials; use queue_username and queue_password`; `must be a URL with scheme and host` (`nohost`, `amqp:///x`, sin esquema); `must be a valid URL`; `must not contain a fragment`; `must not contain ';' ...` (incluidas las filas con `;` y `?`); `must not be empty`; `must be a string`.
- Hallazgo menor, sin fallo: `http` y `amqp` ordenan distinto la comprobación de `;` frente a query (de ahí el parámetro `semicolon_and_query`).

### Mutaciones (una a una, `config.py` restaurado desde copia tras cada una; `md5sum -c` OK y `git diff --stat src/` igual que antes: 146 inserciones, 23 borrados)
- `:216` `must be a valid URL` -> `must be a bad URL`: 48 fallos.
- `:153` `must be between 1 and 65535` -> `must be a valid port`: 8 fallos.
- `:415` `nested too deeply` -> `too nested`: 4 fallos.
- `:401` `file not found` -> `missing file`: 6 fallos (incluye `test_missing_file`).

### Comprobaciones
- `make lint test`: ruff check y format OK; 155 passed, 2142 subtests passed (antes 2136; +4 de la fila mixta del 20, +2 del bucle `via_env` del 21; el resto, igual). `./init.sh` exit 0, mismos números.

### Dudas abiertas
Ninguna.

## Ronda 13

Solo tests (`tests/unit/test_config.py`), sin tocar `src/`. Cierra el punto 17: los 4 motivos de rechazo que faltaban.

- Constantes nuevas `R_UNKNOWN_KEY`, `R_UNSUPPORTED_CHARS`, `R_CANNOT_READ`.
- `test_unreadable_files_raise_validation_error`: caso `directory` (un directorio como config file) comprueba `cannot read ` (sin `strerror`).
- `test_unknown_file_key` y `test_plain_unknown_key_is_named`: `assertIn(R_UNKNOWN_KEY)` y `assertNotIn(R_UNSUPPORTED_CHARS)`.
- `test_unknown_key_is_repeated_only_if_plain`: `assertIn(R_UNSUPPORTED_CHARS)`.
- `test_secret_in_file_is_rejected`: `secrets must not be stored in the config file` y `set GEOAGENT_<KEY>`.

Mutaciones (copia de `src/` en scratchpad, `PYTHONPATH`; base 54 tests OK en test_config):
- l.404 `cannot read` -> 4 fallos
- l.430 `unknown configuration key` -> 10 fallos
- l.432 `(name has unsupported characters)` eliminado -> 14 fallos
- l.437 `secrets must not be stored...` -> 8 fallos; `set GEOAGENT_` -> `use GEOAGENT_` -> 8 fallos

`make lint test` en verde; `./init.sh` en verde: 155 passed, 2146 subtests passed.
