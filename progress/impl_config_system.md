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
