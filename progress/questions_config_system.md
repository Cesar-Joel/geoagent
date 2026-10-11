# Sesión de preguntas del humano sobre `config_system` (2026-10-04)

> Cambios que surgieron de las preguntas del humano. Todos se aplicaron en las rondas 3-6
> (ver `progress/impl_config_system.md` y `progress/review_config_system.md`).

## Decisiones del humano (2026-10-04)

- **Punto 4:** `backend_url` rechaza query y fragmento; `queue_url` acepta la query pero
  `repr()`/`str()`/`to_safe_dict()` enmascaran **todos** sus valores (claves visibles).
- **Punto 6:** un número entre comillas en el TOML (`max_workers = "3"`) se **acepta**;
  fijarlo con un test.
- **r3 del reviewer:** ratificadas las tres: solo TOML (sin YAML), `tomli` condicional
  para < 3.11 y exit code 2.
- **Fragmento de `queue_url` (detectado tras la ronda 3):** se **rechaza**, igual que en
  `backend_url` (AMQP no usa fragmentos). Con su test y sin repetir el valor.
- **Reparto:** puntos 2-7 → implementer (ronda 3 de `config_system`) y reviewer (ronda 3).
  Punto 1 → leader (docs y `.gitignore`).

## 1. Probar en local con Python 3.9 (pregunta: pyenv / uv / Docker)

- **`.gitignore`**: cambiar `.venv/` por `.venv*/` para que un segundo entorno
  (p. ej. `.venv-py39/`) no aparezca como archivo sin seguimiento.
- **`docs/verification.md`** (o `CONTRIBUTING.md`): añadir una sección "Verificar con
  Python 3.9 en local" con la receta recomendada (uv) y la alternativa con Docker:
  - `uv python install 3.9`
  - `make install PYTHON="$(uv python find 3.9)" VENV=.venv-py39`
  - `make lint test VENV=.venv-py39`
  - Docker: `docker run --rm -v "$PWD":/app -w /app python:3.9-slim sh -c "pip install -q -e '.[dev]' && python -m pytest tests -q"`
- Fuera del repo: instalar uv en WSL (no está instalado), o activar la integración de
  Docker Desktop con esta distro de WSL si se prefiere Docker.
- Opcional: después, volver a ejecutar `test_config` con un 3.9 real para cerrar la
  verificación de `config_system`, que hoy está solo simulada
  (`progress/review_config_system.md`).

## 2. `_secret()` duplica a `_parse_str()` (pregunta: ¿para qué sirve `_secret()`?)

- **`src/geoagent/common/config.py:127-128`** (lo hace el implementer; la feature
  `config_system` está `in_progress`): eliminar `_secret()` y usar `_parse_str` en las
  tres specs secretas (`queue_password`, `auth_token`, `api_token`). Lo que marca un
  campo como secreto es `secret=True` en `_Spec`, no el parser.
- No cambia el comportamiento: los tests actuales de `test_config.py` deben seguir en verde
  sin modificarlos.

## 3. Limpieza de `TestPrecedence` en `tests/unit/test_config.py` (prioridad baja)

Pregunta: ¿por qué las líneas 32 y 37 no usan `cfg`? Respuesta: es estilo; la 32 consulta
un `BackendConfig` distinto del `cfg` (agente). Mejoras (las hace el implementer, no toca `src/`):

- Separar los valores por defecto del backend (línea 32) en su propio test,
  `test_backend_defaults_when_no_file_and_no_env`.
- Comprobar **todos** los valores por defecto comparando `to_safe_dict()` con un diccionario
  esperado completo para agente y backend (hoy solo se comprueban 3 de 10 y 1 de 9 campos).
- Unificar el estilo `cfg = ...` + aserción en toda la clase.
- `test_non_finite_float_in_file_rejected` (líneas 76-79): usar el helper `_write` en lugar de
  `open(...)` sin `encoding`. Es el único caso del repo (revisado `tests/` y `src/`); ya lo
  señaló el reviewer como m1 en `progress/review_config_system.md:100`.

## 4. Cobertura de credenciales en URLs (`tests/unit/test_config.py`)

Pregunta: ¿no deberían testearse todas las partes de la URL que pueden llevar secretos?
El código ya rechaza todas las variantes de userinfo (comprobado a mano); faltan los tests.

- **Tests (implementer):** un único test parametrizado con `subTest` para `backend_url` **y**
  `queue_url`, con estas variantes de userinfo: `u:SECRET@h`, `SECRET@h`, `:SECRET@h`,
  `SECRET:pw@h` y codificado `u%3ASECRET@h`. En cada una: `ValidationError`, la clave en el
  mensaje y `SECRET` ausente del mensaje.
  - Hoy `backend_url` cubre solo 2 de las 5 (líneas 82-88) y `queue_url` solo `user:pw@`
    (líneas 126-128), **sin** comprobar que no haya fuga en el mensaje.
- **Decisión del humano: query y fragmento.** `http://h/?token=SECRET` y `http://h/#SECRET`
  se aceptan y salen tal cual en `repr()`. Propuesta:
  - `backend_url`: rechazar query y fragmento (es una URL base y no los necesita), con su test.
  - `queue_url`: mantener la query permitida (AMQP la usa para opciones como `heartbeat`),
    pero **enmascarar los valores en `to_safe_dict()`/`repr()`** conservando las claves:
    `amqp://h/vhost?heartbeat=***&password=***`. Diseño propuesto: campo opcional
    `mask: Callable[[Any], Any] | None` en `_Spec`; `to_safe_dict()` lo aplica cuando existe
    (`_mask_query` con `urlsplit`/`parse_qsl`/`urlencode`, sin tocar el valor real del
    atributo). Tests: repr sin el secreto, claves visibles, valor real intacto, URL sin query
    sin cambios. Documentar en `docs/config.md` que la query se enmascara, pero que las
    credenciales van en `queue_username`/`queue_password` (la librería AMQP podría registrar
    la URL en sus propios logs).
  - El path no se puede vigilar; solo documentarlo.
- **Lista de claves de query seguras (seguimiento de las preguntas sobre `heartbeat`):** en
  `config_system`, enmascarar **todos** los valores de la query (opción segura por defecto, sin
  lista). La lista dinámica depende de qué opciones acepte el broker, y eso lo decide la feature
  `message_queue_layer` (`pending`). Anotar para su spec:
  - Preferible: exponer las opciones del broker como campos tipados (`queue_heartbeat`, …) en
    `_COMMON_SPECS` y prohibir la query en `queue_url`. Así el enmascarado sale de
    `secret=True`, sin lista aparte.
  - Alternativa: que `common/queue.py` declare una estructura con las opciones de query
    admitidas y su marca `secret`; `config.py` rechaza claves desconocidas y deriva la lista
    de claves visibles filtrando esa estructura (mismo patrón de introspección que
    `_iter_model_fields` en `test_models.py`).
  - Descartado: inspeccionar la librería AMQP (API privada, frágil).

## 5. Fuga de URLs con credenciales por `_parse_str` + tests de "no eco" (prioridad alta)

Pregunta: ¿`test_invalid_backend_url_error_does_not_echo_value` duplica a
`test_backend_url_with_credentials_rejected_without_leak`? No: el primero falla en la
comprobación de esquema (a propósito) y el segundo en la de credenciales. Al revisarlo
encontré una fuga real.

- **Fuga (comprobada a mano):** si en el TOML `backend_url` o `queue_url` no es una cadena,
  `_parse_str` repite el valor en el error:
  `backend_url = ["http://u:s3cr3t@h"]` → `backend_url: must be a string (got ['http://u:s3cr3t@h'])`.
  Igual con una tabla en `queue_url`. Ese mensaje lo imprime `load_or_exit` por stderr.
- **Arreglo (`src/geoagent/common/config.py:64-67`, implementer):** que `_parse_str` informe
  solo del tipo: `f"must be a string (got {type(value).__name__})"`. `_parse_int`/`_parse_float`
  pueden seguir repitiendo el valor (números y bools no son secretos, y las cadenas que
  repiten vienen de campos numéricos).
- **Tests:** sustituir los dos tests por uno parametrizado con `subTest` "una URL con un
  secreto nunca aparece en el error", que recorra **todas** las ramas de rechazo de
  `_http_url` y `_queue_url`: esquema inválido, sin esquema, sin host, credenciales y
  valor no cadena desde archivo (lista/tabla). En cada caso: clave en el mensaje y secreto
  ausente.

## 6. Validaciones probadas desde las dos fuentes (archivo y entorno)

Pregunta: ¿no deberían probarse las validaciones desde el archivo y desde el entorno? Sí: el
parser es el mismo, pero los tipos que le llegan no (el entorno siempre da `str`; el TOML da
`int`, `float`, `bool`, `date`, listas, tablas e `inf`/`nan` nativos). Hoy solo `max_workers` (env
`0`, archivo `-1`) y los floats no finitos se prueban desde las dos.

- **Tests (implementer):** una tabla de casos inválidos `(loader, clave, valor_env, valor_toml)`
  que se ejecute con `subTest` desde **las dos fuentes** mediante un helper
  `_load_from(source, loader, key, raw)`. Comprobar la clave en el mensaje: `GEOAGENT_<KEY>`
  desde el entorno y `<key>` desde el archivo. Cubrir todas las claves con validación: `port`
  (no numérico, fuera de rango), `max_workers` (0, negativo), `heartbeat_interval` y
  `request_timeout` (0, no finito), `backend_url` y `queue_url` (vacía, esquema, credenciales),
  `log_level` (desconocido), `host`/`store_path`/`db_path` (vacíos). Sustituye a los tests
  sueltos equivalentes de `TestValidation`.
- **Casos solo de archivo (tipos nativos de TOML), hoy sin test:** `max_workers = true` y
  `max_workers = 2.5` (rechazados), `port = 80.0` (rechazado), `host = 1` (rechazado),
  `store_path = 1979-05-27` (rechazado; ojo con el eco del punto 5), `heartbeat_interval = 5`
  (aceptado como `5.0`).
- **Casos solo de entorno, hoy sin test:** espacios alrededor (`" 3 "` → aceptado como 3),
  `"2.5"` y `"true"` para enteros (rechazados), solo espacios en un campo no vacío (rechazado).
- **Decisión del humano (baja):** hoy `max_workers = "3"` (número entre comillas en el TOML) se
  **acepta**. Propuesta: mantenerlo (inofensivo y coherente con el entorno) y fijarlo con un test;
  la alternativa es ser estricto con los tipos cuando el valor viene del archivo.

## 7. `TestSecretMasking` asimétrico entre agente y backend

Pregunta: ¿por qué el test del backend solo comprueba `repr()`? Sin motivo; es una asimetría.

- **Tests (implementer):** un único test parametrizado con `subTest` por
  `(loader, campos_secretos_esperados)`:
  - agente → `{"auth_token", "queue_password"}`; backend → `{"api_token", "queue_password"}`,
    **escritos a mano** (no derivados de `_*_SPECS`: si alguien quita un `secret=True`, la
    introspección lo seguiría, y el test no lo detectaría).
  - Para cada configuración: ningún secreto en `repr()`, `str()` ni `str(to_safe_dict())`;
    `to_safe_dict()[k] == MASK` **por cada** campo secreto (hoy `assertIn(MASK, text)` pasa
    con que se enmascare uno solo); valor real accesible por atributo; secreto vacío → `""`
    sin enmascarar; campos no secretos visibles.
  - Hoy `test_secret_value_still_accessible`, `test_unset_secret_not_masked` y
    `test_non_secret_fields_visible` solo cubren el agente.
- **Ampliación (pregunta de seguimiento sobre los 3 tests de apoyo):**
  - `test_unset_secret_not_masked`: comprobar en las tres vistas (`repr()`, `str()`,
    `to_safe_dict()`) y para **cada** secreto de cada loader: `to_safe_dict()[k] == ""` y
    `f"{k}=''"` presente en `repr()`/`str()`.
  - `test_non_secret_fields_visible`: en las tres vistas y para **todos** los campos no
    secretos, recorridos por introspección (`dataclasses.fields(cfg)` menos la lista de
    secretos escrita a mano): `to_safe_dict()[k] == getattr(cfg, k)` y `f"{k}={v!r}"` en
    `repr()`/`str()`.
  - `test_secret_value_still_accessible`: se queda solo con el acceso por atributo (las vistas
    ya las cubre el test principal), pero para cada secreto de cada loader.
  - **Fuentes:** el enmascarado no depende de la fuente (actúa sobre el objeto final), así que
    no se duplica con archivo. Lo que sí se amplía es `test_secret_in_file_is_rejected`: que
    recorra **cada** secreto de **cada** loader (hoy solo `queue_password` del agente), también
    con la ruta dada por `GEOAGENT_CONFIG_FILE`, y que compruebe que el valor no aparece en el
    error. Más un caso mixto: archivo con campos no secretos + secretos por entorno →
    enmascarados.

---

# Sesión de preguntas del humano sobre `config_system` (2026-10-05)

> Revisión del humano después de los commits `e778f82`, `a9f4877` y `44a555b` (sin push). La
> feature está `done`: aplicar estos cambios exige que el humano autorice reabrirla.

## Decisiones del humano (2026-10-06)

- **Reapertura:** autorizada (`done` → `in_progress`). Puntos 8-16 en una ronda 7.
- **Punto 9:** los valores por defecto se validan en el código (`_resolve` los pasa por su parser).
- **Punto 12:** sintaxis completa del `host` del backend ya: IP sin corchetes o nombre DNS válido.
- **Punto 16:** un `;` literal en el path de `backend_url` y `queue_url` se rechaza; `%3B` se acepta.
- **Reparto:** todo en una ronda (los puntos 8-16 tocan los mismos dos archivos y se solapan:
  las tablas del punto 8 absorben casos de los puntos 10, 12, 14 y 16).

## Decisiones del humano (2026-10-07), tras la ronda 7 del reviewer

Ronda 8: bloqueantes B1-B5 de "## Ronda 7" en `progress/review_config_system.md`, más:

- **Zona IPv6 del `host` (B1, duda 1):** se rechaza el `%` (sin zona). Además, el `host` debe ser
  imprimible y sin espacios antes de intentar la IP.
- **D1:** `queue_username`, `queue_password`, `auth_token` y `api_token` rechazan los caracteres
  de control (`Cc`), sin repetir el valor.
- **D3:** `store_path`/`db_path` exigen texto imprimible (`isprintable()`, como las URL).
- **D2:** los errores numéricos repiten el texto solo si es ASCII imprimible; si no, `got str`.
- **Límite de 253** caracteres en los nombres DNS del `host` (junto con B2, TLD numérico).
- **"(default)"** en el error de un valor por defecto inválido.
- **Menores m11-m13** del reviewer, incluidos.
- **Duda 5 del implementer** (renombre de tipos de validación: `_NON_EMPTY_STR` → `_BIND_HOST` +
  `_PATH`, `_SECRET` → `_SECRET_TYPE`): aceptado, sin cambios.
- **Duda 4:** el `;` en la query no se vigila (se enmascara entera); en el netloc sí (B3).

## 8. `TestValidation.INVALID` organizada por tipo de validación (prioridad media)

Pregunta: ¿no sería mejor que la lista de inválidos se organizara por tipo, como
`_INVALID_VALUE_BY_TYPE` en `test_models.py`? Respuesta: sí, pero por **tipo de validación**, no
por tipo de Python: dos campos `str` pueden tener validaciones distintas (`backend_url` frente a
`log_level`). Hoy la tabla está escrita a mano por (loader, campo) y la cobertura es desigual.

- **Problemas actuales (comprobado):**
  - Los campos que comparten agente y backend se prueban de forma desigual: `queue_url` con
    `[::1` y `h:abc` solo con el agente; `heartbeat_interval -inf` solo con el agente, etc.
  - `auth_token`, `api_token`, `queue_username` y `queue_password` no aparecen en la tabla, y nada
    falla si se añade un campo nuevo sin casos inválidos.
  - `queue_username = 1` desde el TOML (no es cadena) no tiene test.
- **`tests/unit/test_config.py` (implementer):**
  - Constantes por tipo de validación, cada una con sus casos `(texto_env, literal_toml)`:
    `_PORT`, `_POSITIVE_INT`, `_POSITIVE_FINITE_FLOAT`, `_HTTP_URL`, `_QUEUE_URL`, `_LOG_LEVEL`,
    `_NON_EMPTY_STR`, `_ANY_STR` (solo el caso del TOML que no es cadena) y `_SECRET` (el caso del
    archivo lo cubre `test_secret_in_file_is_rejected`; aquí, ninguno).
  - Un mapa campo → tipo de validación, escrito a mano (lo que debe validar cada campo lo fija el
    test, no `_*_SPECS`).
  - El test recorre `dataclasses.fields(AgentConfig)` y `fields(BackendConfig)` (API pública),
    ejecuta todos los casos del tipo de cada campo desde las dos fuentes, y **falla si un campo
    no está clasificado**, igual que `unclassified type` en `test_models.py`. También falla si el
    mapa tiene un campo que no existe.
  - Absorbe los casos sueltos de `test_invalid_toml_native_types_rejected` y
    `test_invalid_env_text_rejected` que encajen en un tipo; los que solo tienen sentido en una
    fuente se quedan como columna vacía de esa fuente.

## 9. Valores por defecto: sin validar y sin comprobar el tipo (prioridad media)

Pregunta: ¿qué pasa con `AGENT_DEFAULTS`/`BACKEND_DEFAULTS` si se añade, modifica o elimina un
campo? Respuesta: el test ya lo detecta (compara el diccionario completo con `assertEqual`: una
clave de más, de menos, renombrada o con otro valor lo hace fallar). Aquí la lista escrita a mano
es lo correcto. Pero hay dos huecos (comprobados parcheando `_AGENT_SPECS` en memoria):

- **Los valores por defecto no pasan por el parser** (`config.py:331`,
  `resolved[key] = spec.default`). Un `max_workers` por defecto de `0` se acepta. El test solo
  lo evitaría si quien cambia el valor no actualiza también la tabla; si la actualiza, nadie
  avisa de que el valor es inválido.
- **No se comprueba el tipo:** `30 == 30.0`, así que un `heartbeat_interval` por defecto `int`
  pasa el test, y el campo deja de ser `float` sin que nadie lo note.
- **`src/geoagent/common/config.py`** (implementer): validar los valores por defecto con su
  propio parser. Recomendado: `_resolve` aplica `spec.parser(key, spec.default)` también a los
  defaults (coste despreciable; así un default inválido falla en el arranque y en cualquier test).
  Alternativa: solo un test que pase cada default por su parser.
- **Tests:**
  - Comparar además los tipos: `{k: type(v) for k, v in ...}` con los tipos esperados
    (`int`, `float`, `str`), o `assertIs(type(...), ...)` por campo.
  - Un test que demuestre que un default inválido se rechaza (parcheando `_AGENT_SPECS` con
    `unittest.mock.patch.dict` o equivalente) y que nombra la clave.

## 10. Tipo exacto de los valores numéricos válidos, desde las dos fuentes (prioridad media)

Pregunta: ¿`test_valid_native_and_text_values_accepted` no debería comprobar también el tipo cuando
el valor llega por entorno, y con el archivo indicado por `GEOAGENT_CONFIG_FILE`? Respuesta: sí
para el entorno. El código ya devuelve el tipo correcto en todos los casos (comprobado: entorno
`"5"` → `5.0 float`, `" 3 "` → `3 int`; TOML `5`/`"5"` → `5.0 float`; `3`/`"3"` → `3 int`;
igual con `port` y `request_timeout`), pero solo `heartbeat_interval` desde el archivo tiene
`assertIsInstance`. `max_workers` desde el entorno usa `assertEqual(..., 3)`, que también pasaría
con `3.0`.
Con `GEOAGENT_CONFIG_FILE`, no hace falta repetirlo por campo: solo cambia cómo se encuentra la
ruta, y el parseo es el mismo (`_read_file`).

- **`tests/unit/test_config.py`** (implementer), junto con el punto 8: cada tipo de validación
  numérico (`_PORT`, `_POSITIVE_INT`, `_POSITIVE_FINITE_FLOAT`) lleva también **casos válidos**
  `(texto_env, literal_toml, valor_esperado)`, que se ejecutan desde las dos fuentes (incluido el
  número entre comillas en el TOML) sobre cada campo de ese tipo y de cada loader. Comprobar el
  valor y el tipo exacto con `assertIs(type(v), int|float)`, no con `assertIsInstance`: `bool` es
  subclase de `int`.
  Sustituye a `test_valid_native_and_text_values_accepted` y `test_quoted_number_in_file_is_accepted`.
- **Seguimiento (`test_quoted_number_in_file_is_accepted`):** hoy solo prueba `max_workers = "3"`
  con `assertEqual`, sin el tipo. Comprobado: `port = "8081"` → `8081 int`, `heartbeat_interval =
  "5"` → `5.0 float`, `request_timeout = "7.5"` → `7.5 float`; `max_workers = "2.5"`,
  `port = "80.0"` y `max_workers = "true"` se rechazan. En la tabla del punto 8, el número entre
  comillas es una **tercera columna** de cada tipo numérico (entorno, TOML nativo, TOML entre
  comillas), tanto en los casos válidos (valor y tipo exacto) como en los inválidos (`"2.5"` y
  `"80.0"` en enteros, `"true"`, `"nan"`). Así cada campo numérico de cada loader la recorre.
- **`test_file_path_from_env`**: que el archivo indicado por `GEOAGENT_CONFIG_FILE` incluya
  también un campo numérico y compruebe su valor y tipo (un solo caso, como prueba de la ruta).

## 11. Probar cada comportamiento con los dos loaders y las dos fuentes (prioridad media)

Pregunta: muchos tests usan un solo loader o una sola fuente cuando el comportamiento es común;
usar campos de `_COMMON_SPECS` (`request_timeout`, `log_level`, `queue_url`, `queue_username`,
`queue_password`) para cubrir `AgentConfig` y `BackendConfig` desde el entorno y desde el
archivo. Respuesta: sí; inventario completo abajo.

- **Herramientas comunes (implementer):**
  - `LOADERS = (load_agent_config, load_backend_config)` junto a `SOURCES`, y recorrer
    `loader × source` con `subTest` donde el comportamiento no dependa de ellos.
  - No hay ningún entero común. Para el camino de enteros: `_INT_FIELD = {load_agent_config:
    "max_workers", load_backend_config: "port"}`. Para floats: `request_timeout`. Para cadenas
    sin validación: `queue_username`. Para secretos: `queue_password`.
  - Que la fuente sea inherente (precedencia, secretos solo por entorno, tipos nativos de
    TOML) limita las fuentes, no los loaders.
- **Inventario** (los de `TestValidation.INVALID` y los de valores válidos ya están en los puntos
  8 y 10):

| Test | Hoy | Cambio |
|---|---|---|
| `test_file_overrides_defaults` | agente, `max_workers` | los dos loaders con `request_timeout` |
| `test_env_overrides_file` | backend, `port` | los dos loaders con `request_timeout` |
| `test_env_overrides_default` | agente, `max_workers` | los dos loaders con `request_timeout` |
| `test_file_path_from_env` | agente, `log_level` | los dos loaders (+ campo numérico, punto 10) |
| `test_unprefixed_env_is_ignored` | agente, `max_workers` | los dos loaders con `request_timeout` |
| `test_unknown_file_key` | agente | los dos loaders; añadir la clave del **otro** loader (`port` en el archivo del agente → rechazada; por entorno, `GEOAGENT_PORT` con el agente → ignorada). Comprobado |
| `test_missing_file` | agente, ruta por argumento | los dos loaders, por argumento y por `GEOAGENT_CONFIG_FILE` |
| `test_invalid_toml` | agente, ruta por argumento | los dos loaders, por argumento y por `GEOAGENT_CONFIG_FILE` |
| `test_unreadable_files_raise_validation_error` | agente | los dos loaders |
| `test_non_utf8_file_via_load_or_exit_exits_2` | agente | los dos loaders |
| `test_long_numeric_value_is_truncated_in_error` | agente, `max_workers` | los dos loaders: `_INT_FIELD` y `request_timeout`, desde las dos fuentes |
| `test_huge_digit_string_and_native_int_are_rejected_briefly` | `heartbeat_interval` (agente), `port` solo archivo | los dos loaders: `request_timeout` y `_INT_FIELD`, desde las dos fuentes |
| `test_numeric_text_accepts_only_ascii_digits_without_underscores` | agente | los dos loaders: `request_timeout` y `_INT_FIELD` |
| `test_control_characters_in_host_are_rejected_without_echo` | agente, solo entorno | las dos fuentes; `queue_url` con los dos loaders |
| `test_non_string_error_reports_only_the_type` | agente, `backend_url` | además `queue_username` (y `log_level`) con los dos loaders |
| `test_non_scalar_in_numeric_field_reports_only_the_type` | `port` (backend), `heartbeat_interval` (agente) | `request_timeout` y `_INT_FIELD` con los dos loaders |
| `test_invalid_config_exits_nonzero_naming_key` | agente, entorno | los dos loaders, las dos fuentes (`request_timeout = 0`); comprobar `code == 2` |
| `test_error_goes_to_stderr_not_stdout` | agente | los dos loaders |
| `test_malformed_url_exits_2_naming_key_without_secret` | siempre agente | `queue_url` también con el backend |
| `test_valid_config_is_returned` | backend | los dos loaders |
| `test_valueless_query_item_is_masked` | agente, entorno | los dos loaders, las dos fuentes |
| `test_url_without_query_unchanged` | agente, entorno | los dos loaders, las dos fuentes |
| `test_backend_url_has_no_masking` | agente, entorno | las dos fuentes (campo solo del agente) |

- Ya correctos, sin cambios: `TestUrlSecretsNeverEchoed.cases` (`queue_url` con los dos loaders),
  `TestSecretMasking` (dos loaders; la fuente es inherente), `test_query_values_masked_keys_visible`.

## 12. `host` del backend sin validar y aserción de "no eco" débil (prioridad alta)

Pregunta: ¿`test_control_characters_in_host_are_rejected_without_echo` no debería probar también
el `host` del backend? ¿Y por qué la línea 350 solo comprueba uno de los casos de `hosts`?

- **Hallazgo (comprobado):** el `host` del backend solo usa `_non_empty` (`config.py:219`), así
  que no pasa por `_check_host`. Se aceptan `"h\x00"`, `"h\nINFO fake"` (una línea falsa en
  cualquier log que lo imprima sin `repr`), `"\udcffh"`, `"h h"`, `"h:80"`, `"http://h"` y
  `"[::1]"`. Lo mismo pasa con un byte NUL en `store_path`/`db_path`: se acepta y falla
  después, al abrir el archivo (`ValueError: embedded null byte`), en vez de al arrancar.
- **Aserción débil (`test_config.py:350`):** `assertNotIn("udcff", ...)` solo tiene sentido para el
  primer caso, y ni siquiera para ese: si el mensaje repitiera el valor con `str()`, contendría
  el carácter `\udcff`, no el texto `"udcff"`, y el test pasaría. Para `\x00`, `\n` y `\x07` no
  se comprueba nada.
- **`src/geoagent/common/config.py`** (implementer):
  - `host`: validación propia `_bind_host`. Como mínimo: imprimible, sin espacios y sin repetir
    el valor en el error.
  - `store_path`/`db_path`: rechazar caracteres de control (al menos el NUL) sin repetir el valor.
- **Decisión del humano:** cuánto validar `host`.
  - (Recomendado) **Sintaxis completa ahora:** una IP (`ipaddress.ip_address`, sin corchetes) o un
    nombre DNS válido (etiquetas de 1-63 caracteres `[A-Za-z0-9-]` que no empiecen ni acaben en
    `-`). Rechaza `h:80`, `http://h`, `[::1]`, `-h-`. Es una dirección de escucha, no una URL:
    validarla es sencillo y el fallo al arrancar es mucho más claro que el de `bind`.
  - Solo caracteres de control ahora, como en las URL (m9), y la sintaxis para la feature 5
    `backend_api_skeleton` (nota en `current.md`).
- **Tests** (con el punto 11: los dos loaders y las dos fuentes donde aplique):
  - Para cada caso: `assertNotIn(raw, msg)` y `assertNotIn(repr(raw)[1:-1], msg)` (el valor tal
    cual y escapado), no una subcadena fija.
  - `queue_url` con los dos loaders, `backend_url` con el agente, `host` con el backend,
    `store_path`/`db_path` con su loader; desde el entorno y desde el TOML (en el TOML,
    `\u0000` y `\n` escapados dentro de la cadena).

## 13. `load_or_exit(_load_from, ...)` en lugar del loader real (prioridad baja)

Pregunta: ¿por qué `test_malformed_url_exits_2_naming_key_without_secret` (`test_config.py:397`)
pasa `_load_from` a `load_or_exit` en lugar de `load_agent_config`? Respuesta: por comodidad.
`load_or_exit(loader, *args, **kwargs)` (`config.py:351`) solo llama a `loader(*args, **kwargs)`
y captura `ValidationError`, así que acepta cualquier función; el test le pasa el helper para
reutilizar la preparación del entorno o del archivo temporal. Funciona (el error sigue saliendo
de `load_agent_config`, que el helper llama por dentro), pero el test no usa `load_or_exit` como
lo usará el arranque real (`load_or_exit(load_agent_config, path, env=...)`), y obliga a conocer
el helper para entenderlo.

- **`tests/unit/test_config.py`** (implementer): separar la preparación de la carga.
  - Un context manager `_config_source(source, key, raw)` que da `(path, env)`: para `"env"`,
    `(None, {"GEOAGENT_<KEY>": raw})`; para `"file"`, escribe el TOML en un directorio temporal
    y da `(ruta, {})`.
  - `_load_from` pasa a ser `with _config_source(...) as (path, env): return loader(path, env=env)`.
  - Los tests de `load_or_exit` llaman al loader real:
    `with _config_source(...) as (path, env): load_or_exit(loader, path, env=env)`.
  - Con el punto 11: los dos loaders (`queue_url` también con el backend).

## 14. `TestUrlSecretsNeverEchoed` mezcla tests que no son de URL (prioridad baja)

Pregunta: varios tests de `TestUrlSecretsNeverEchoed` no tienen que ver con secretos en URL (p. ej.
`test_long_numeric_value_is_truncated_in_error`). Respuesta: cierto; de sus 8 tests solo 1 encaja
del todo. Se fueron añadiendo ahí en las rondas 4-6 porque la clase ya tenía `SECRET`.

| Test | Qué prueba en realidad | Destino |
|---|---|---|
| `test_url_secret_never_appears_in_error` | secretos en URL nunca en el error | se queda |
| `test_control_characters_in_host_are_rejected_without_echo` | rechazo + mensaje sin eco | rechazo → tablas del punto 8 (con el punto 12); "sin eco" → `TestErrorMessages` |
| `test_long_numeric_value_is_truncated_in_error` | brevedad del mensaje (m7) | `TestErrorMessages` |
| `test_huge_digit_string_and_native_int_are_rejected_briefly` | brevedad del mensaje | `TestErrorMessages` |
| `test_non_string_error_reports_only_the_type` | el mensaje solo da el tipo | `TestErrorMessages` |
| `test_non_scalar_in_numeric_field_reports_only_the_type` | el mensaje solo da el tipo | `TestErrorMessages` |
| `test_numeric_text_accepts_only_ascii_digits_without_underscores` | qué se acepta (m8b) | casos inválidos de la tabla del punto 8 |
| `test_numeric_text_still_accepts_spaces_sign_and_exponent` | qué se acepta | casos válidos del punto 10 |

- **`tests/unit/test_config.py`** (implementer), criterio por clase:
  - `TestValidation`: **qué** se acepta y qué se rechaza (tablas por tipo de validación, puntos
    8 y 10).
  - `TestErrorMessages` (nueva): **qué dice** el mensaje: nombra la clave (`GEOAGENT_<KEY>` o
    `<key>` según la fuente), nunca repite un valor que pueda llevar secretos (ni tal cual ni
    escapado, punto 12), da solo el tipo cuando no es escalar y es breve con valores enormes.
    `SECRET` se mueve aquí.
  - `TestUrlSecretsNeverEchoed`: solo `test_url_secret_never_appears_in_error`; o se integra
    también en `TestErrorMessages` y la clase desaparece (recomendado: una sola clase para
    "el mensaje no filtra").
  - Con el punto 11: todos con los dos loaders y las dos fuentes.

## 15. Comprobar las tres vistas siempre con helpers comunes (prioridad baja)

Pregunta: hay sitios donde se podría haber usado `views()` (líneas 446, 457, 500, 508, 515 y 520).
Respuesta: sí, con un matiz. `views()` (`test_config.py:421`) sirve para comprobar **ausencias**
(`assertNotIn` en las tres vistas), pero no **presencias**: en `repr()`/`str()` un campo sale como
`auth_token=''` y en `str(to_safe_dict())` como `'auth_token': ''` (comprobado), así que un mismo
`assertIn(f"{key}=''", ...)` fallaría con la vista de diccionario. Además, `views()` es un método
de `TestSecretMasking` y no se puede usar desde `TestQueueUrlQueryMasking`.

| Línea | Hoy | Problema |
|---|---|---|
| 446-448 | dict + `repr` + `str` a mano | repetido; debería ser un helper |
| 457-460 | dict + `repr` + `str` a mano | ídem |
| 500 | copia literal de `views()` | en otra clase, no la alcanza |
| 508 | solo `repr()` | falta `str()` y `to_safe_dict()` |
| 515-516 | dict + `repr()` | falta `str()` |
| 520 | solo `to_safe_dict()` | faltan `repr()` y `str()` |

- **`tests/unit/test_config.py`** (implementer): dos helpers a nivel de módulo, usados en todos
  los sitios anteriores:
  - `_views(cfg)` → `(repr(cfg), str(cfg), str(cfg.to_safe_dict()))`, para las ausencias
    (sustituye al método `views()`).
  - `_assert_shown(test, cfg, key, shown)`: `cfg.to_safe_dict()[key] == shown` y
    `f"{key}={shown!r}"` en `repr(cfg)` y en `str(cfg)`. Para las presencias, también para los
    valores enmascarados (`shown = MASK` o la URL con la query enmascarada).

## 16. `;params` en el path de las URL (prioridad media)

Pregunta: según `docs/config.md` los `;params` del path no se vigilan; ¿no deberían? Respuesta: sí.
Son el mismo riesgo que la query (`;token=...` es una forma habitual de pasar credenciales) y,
a diferencia del resto del path, se detectan sin ambigüedad. Comprobado: se aceptan y salen tal
cual en `repr()`:

| URL | Resultado |
|---|---|
| `http://h/api;token=s3cr3t` (`backend_url`) | aceptada; `repr` con el secreto |
| `http://h/a;token=s3cr3t/b` (`backend_url`) | aceptada; `urlparse(...).params == ''` (solo separa el último segmento) |
| `amqp://h/vhost;password=s3cr3t` (`queue_url`) | aceptada; `params == ''` (`urlparse` no separa params con `amqp`) |
| `amqp://h/v;p=s3cr3t?heartbeat=1` (`queue_url`) | aceptada; la query se enmascara, los params no |

Por eso no basta con mirar `parsed.params`: hay que buscar `;` en todo el path.

- **`src/geoagent/common/config.py`** (implementer): `_http_url` y `_queue_url` rechazan un `;`
  literal en el path, sin repetir el valor. Un `;` codificado (`%3B`, p. ej. en un vhost de AMQP)
  se sigue aceptando.
- **`docs/config.md:70-71`** (implementer): sustituir la frase de los `;params` por el rechazo; se
  mantiene el aviso de que el resto del path no se vigila.
- **Tests:** los cuatro casos de la tabla, en `backend_url` y `queue_url` (dos loaders, dos
  fuentes), dentro de la tabla de inválidos del punto 8 y del test de "sin eco"; y `%3B` aceptado.
- **Decisión del humano:** rechazar (recomendado: ninguna de las dos URL los necesita, y el
  rechazo es coherente con la query y el fragmento de `backend_url`) o enmascarar como la query.

---

## Decisiones pendientes tras la ronda 8 del reviewer (2026-10-08)

> **Estado: CERRADA** (ver "Decisiones del humano (2026-10-08, al retomar)").
>
> (Antes: SIN CERRAR. El humano pidió dejarlas documentadas para revisarlas con calma.)
> Al retomar: el leader responde las dudas que tenga el humano y después le hace **estas mismas
> preguntas** con `AskUserQuestion` (máximo 4 por llamada, con la recomendada primero). Las
> respuestas que aparecen como "provisional" se dieron el 2026-10-08, pero el humano todavía
> puede cambiarlas. Cuando estén confirmadas, se pasan a una sección "Decisiones del humano
> (<fecha>)" y se lanza la ronda 9 del implementer.
>
> Origen: "## Ronda 8" de `progress/review_config_system.md` (veredicto CHANGES_REQUESTED).

### Bloqueantes (no necesitan decisión: van en la ronda 9 sí o sí)

- **B1, regresión:** `load_agent_config(Path("ok.toml"))` lanza `AttributeError: 'PosixPath'
  object has no attribute 'isprintable'` (comprobado por el leader). En `HEAD` funcionaba.
  Arreglo: `os.fspath(path)` al entrar; si no es `str` (por ejemplo, `bytes`), `ValidationError`
  con `field="config_file"`. Tests con `Path` válido, `Path` inexistente y `bytes`, en los dos
  loaders y por `load_or_exit`.
- **B2, `host` hexadecimal:** `0x7f`, `0X7F`, `0x7f.0x1` y `1.0x1` se aceptan como nombre DNS,
  y `getaddrinfo("0x7f.0x1")` da `127.0.0.1` (comprobado). Arreglo: tratar como numérica la
  última etiqueta que sea solo dígitos **o** que encaje con `0[xX][0-9A-Fa-f]*`. Filas inválidas:
  `0x7f`, `0X7F`, `0x7f.0x1`, `1.0x1`, `0x`. Filas válidas: `0xg`, `a.0x1g`. Actualizar
  `docs/config.md`.

### P1. m18: Python 3.9.0-3.9.4 y `010.0.0.1` — respuesta provisional: rechazar ceros iniciales

Contexto: con Python 3.9.0-3.9.4, `ipaddress` acepta octetos con cero inicial
(CVE-2021-29921, corregido en 3.9.5). En esas versiones, `010.0.0.1` pasaría como IP y haría
bind a `8.0.0.1`. `pyproject.toml` tiene `requires-python = ">=3.9"`.

| Opción | Qué implica |
|---|---|
| **Rechazar ceros iniciales (recomendado)** | `_bind_host` rechaza a mano los octetos IPv4 con cero inicial. No cambia `requires-python` y funciona igual en cualquier versión. |
| `requires-python >=3.9.5` | Más simple, pero excluye esos parches de 3.9. |
| Ambas | Las dos medidas. |

**Confirmada (2026-10-08, al retomar):** rechazar ceros iniciales.

### P2. m16: `GEOAGENT_CONFIG_FILE=""` — respuesta provisional: sí, se valida

Contexto: `docs/config.md:14-15` dice que "una variable presente pero vacía cuenta como valor y
se valida". Pero `config.py:375` hace `path = env.get(CONFIG_FILE_ENV) or None`, y el `or None`
convierte la cadena vacía en "no hay archivo": se descarta sin validarla y sin avisar. Hay
ambigüedad porque `GEOAGENT_CONFIG_FILE` no es un campo de la tabla, sino la variable que indica
dónde está el archivo.

Duda que aclaró el humano: "¿no se debería aceptar como valor y que la validación tire el
error?". Sí: es exactamente la opción recomendada (la primera redacción, "tratarla como error",
lo hacía parecer otra cosa).

| Opción | Qué implica |
|---|---|
| **Sí, se valida (recomendado)** | Se quita el `or None`. La ruta vacía falla en la validación (`ValidationError`, `field=config_file`), con un test por loader y la regla de `docs/config.md` extendida a esta variable. |
| Ignorarla y documentarlo | Se mantiene: una variable vacía equivale a no tenerla. Se añade un test y se documenta como excepción. |

**Confirmada (2026-10-08, al retomar):** sí, se valida. Duda del humano: ¿falla si se configura
solo con entorno + defaults? Aclarado: no; la variable **sin definir** sigue cargando entorno +
defaults. Solo falla la variable **definida y vacía**. Al documentarlo, dejar explícita esa
distinción en `docs/config.md`.

### P3. Hueco 5: caracteres invisibles en las credenciales — respuesta provisional: exigir imprimible

Contexto: D1 (2026-10-07) rechaza solo la categoría `Cc` en `queue_username`, `queue_password`,
`auth_token` y `api_token`. Quedan aceptados los caracteres de otras categorías:

| Carácter | Qué es | Categoría | De dónde suele venir |
|---|---|---|---|
| U+FEFF BOM | espacio de ancho cero sin ruptura | `Cf` | archivos UTF-8 con BOM (Notepad, Excel) |
| U+00A0 NBSP | espacio sin ruptura | `Zs` | copiar desde webs, Word, Slack |
| U+202E RLO | fuerza escritura de derecha a izquierda | `Cf` | texto bidireccional |
| U+2028 | separador de línea | `Zl` | salto de línea "lógico" de Unicode |

- **¿Sirve aceptarlos?** Prácticamente no. Los tokens son ASCII, y las letras Unicode y el
  espacio ASCII siguen siendo válidos con `isprintable()`.
- **¿Es explotable en `config`?** No. La inyección de cabeceras necesita `\r\n` (ya lo bloquea D1);
  los secretos se enmascaran y `queue_username` sale con `repr`, que escapa estos caracteres;
  en AMQP solo harían fallar la autenticación.
- **Pero hay un fallo tardío y sin tipar (comprobado por el leader):** con un `auth_token` que
  contiene BOM, RLO o U+2028, `http.client.putheader("Authorization", ...)` lanza
  `UnicodeEncodeError`. El NBSP pasa, pero el servidor rechazaría el token. Es el mismo caso que
  justificó D3 en las rutas.

| Opción | Qué implica |
|---|---|
| **Exigir imprimible (recomendado)** | `isprintable()` en los cuatro campos: se rechazan al arrancar nombrando la clave y sin repetir el valor. |
| Dejar solo `Cc` | Se mantiene, con una nota a la feature 7 para que el cliente HTTP lo maneje. |

(La primera recomendación del leader fue "dejar solo `Cc`". La cambió al comprobar el
`UnicodeEncodeError`).

### P4. Arreglos menores — respuesta provisional: m14 y m17 (sin truncado ni m15)

Selección múltiple:

| Opción | Qué es |
|---|---|
| Truncar claves y rutas | Hueco 2: una clave desconocida o una ruta imprimible muy larga se repiten enteras (una clave de 100 000 caracteres da un mensaje de 100 027 en stderr; también el texto de `TOMLDecodeError`). Se truncan con el mismo límite que los valores (`_MAX_ECHO`). No permite falsificar líneas (es imprimible); es un problema operativo. |
| m14: `log_level` solo ASCII | `ınfo` (i sin punto turca, U+0131) se acepta como `INFO` por el `upper()` Unicode. Exigir `isascii()` antes del `upper()`, con la fila en `_LOG_LEVEL.invalid`. |
| m15: test de NUL en la ruta | La rama `ValueError` de `_read_file` no está en `_PATH_BRANCHES`: la mutación que repite la ruta con un NUL crudo pasa toda la suite. Añadir `nul_in_path`, por argumento y por entorno. |
| m17: corregir el informe | `progress/impl_config_system.md` (ronda 8) cita `test_error_from_env_or_file_does_not_say_default`, que no existe (la comprobación está en `test_invalid_values_are_rejected_naming_the_key`). |

El humano quería hacer preguntas sobre esta selección antes de confirmarla (aún no las ha
hecho).

### Sin decisión (valoración del reviewer, aceptada tal cual)

- Hueco 3 (`field="config_file"` para una clave no imprimible) y hueco 4 (`cannot read` solo con
  `strerror`): correctos, sin cambios.
- Las 2 mutaciones equivalentes de `_bind_host` (`isprintable` y espacio) se mantienen.
- "Para features futuras" de la ronda 8 (features 5, 7, 9, 20 y 25): el leader las pasa a
  `progress/current.md` al cerrar la feature.

## Decisiones del humano (2026-10-08, al retomar)

Van a la ronda 9 del implementer junto con los bloqueantes B1 y B2 de la sección anterior.

- **P1 (m18):** rechazar a mano los octetos IPv4 con cero inicial en `_bind_host` (`010.0.0.1`
  inválido en cualquier versión de Python). No cambia `requires-python`.
- **P2 (m16):** `GEOAGENT_CONFIG_FILE` definida y vacía → `ValidationError` con
  `field="config_file"` (se quita el `or None`). Sin definir → entorno + defaults, como hasta ahora,
  sin fallo. `docs/config.md` debe dejar explícita la diferencia entre "sin definir" y "vacía".
- **P3 (hueco 5):** `isprintable()` en `queue_username`, `queue_password`, `auth_token` y
  `api_token`: se rechazan al arrancar nombrando la clave y sin repetir el valor.
- **P4 (menores, las cuatro):** truncar claves desconocidas y rutas con `_MAX_ECHO` (incluido el
  texto de `TOMLDecodeError`); m14 (`log_level` exige `isascii()` antes del `upper()`); m15
  (`nul_in_path` en `_PATH_BRANCHES`, por argumento y por entorno); m17 (corregir la cita del test
  inexistente en la ronda 8 de `progress/impl_config_system.md`).

## Decisiones del humano tras la ronda 9 del reviewer (2026-10-08)

Origen: "Observaciones menores" de "## Ronda 9" en `progress/review_config_system.md` (veredicto
APPROVED). El humano elige los tres menores; van a la ronda 10 del implementer.

- **m19:** en los errores de `TOMLDecodeError`, truncar solo el texto y conservar el sufijo de
  posición `(at line L, column C)` (o `end of document`), que solo lleva dígitos. Comprobado por el
  leader: hoy sale `Cannot overwrite a value (at line 2, col…`.
- **m20:** truncar las rutas conservando el final (`…` + últimos `_MAX_ECHO` caracteres), para que
  se vea el nombre del archivo. Ajustar `test_long_path_is_truncated`.
- **m21:** `docs/config.md`, filas `store_path`/`db_path`: unificar con las credenciales (también
  se rechazan BOM y NBSP, por `isprintable()`).

## Decisiones del humano tras la ronda 10 del reviewer (2026-10-08)

- **m23:** quitar la alternativa `col` de `_TOML_POSITION_RE` (solo `column`) y de las regex de
  los tests, y añadir un test que compruebe que un sufijo con `col` **no** se conserva (se trunca
  como texto). Va a la ronda 11.
- **Cierre:** no se cierra la feature sin que el humano revise todo el código y lo autorice
  expresamente.

## Sesión de preguntas: revisión del código antes del cierre (2026-10-09 a 2026-10-11)

> El humano recorre por bloques el diff de `tests/unit/test_config.py`. Los cambios que hizo él
> mismo a mano (el surrogate en `_CONTROL_CHARS`) no se anotan aquí, por decisión suya; constan
> en la bitácora de `progress/current.md`.

### Decisiones del humano (2026-10-11)

- **Puntos 17-22:** todos aprobados tal como están redactados. Punto 17 con el alcance completo
  (todos los motivos de rechazo, no solo las URL).
- **Sin decisiones abiertas:** no queda nada por preguntar; la ronda 11 del reviewer fue APPROVED
  sin pendientes.
- **Reparto:** todo en una ronda (ronda 12 del implementer), porque los seis puntos tocan solo
  `tests/unit/test_config.py` y se solapan (17 cambia las tablas; 18, 19 y 21 los mismos tests de
  archivo). Sin cambios en `src/`. Después, la ronda 12 del reviewer.
- **Cierre:** sigue haciendo falta la autorización expresa del humano después del APPROVED.

## 17. Casi ningún test comprueba el motivo del rechazo (prioridad baja)

Pregunta: revisión del bloque 5 (`TestErrorMessages`). Respuesta: el antiguo
`test_control_characters_in_host_are_rejected_without_echo` (en `TestUrlSecretsNeverEchoed`)
comprobaba `assertIn("valid URL", ...)`. Lo sustituyeron las filas de control de `_url_invalid`
más `test_error_never_echoes_the_value`, que solo comprueban que el error nombra la clave y no
repite el valor. Al buscar si había más casos (`grep -cF` de cada motivo en
`tests/unit/test_config.py`, 2026-10-11), el hueco es general: de los 20 motivos de
`src/geoagent/common/config.py` solo se comprueban `must be a string` y `must not be empty`. Ni
`must be a valid URL` (l. 216, 218, 225), ni `between 1 and 65535`, ni `must not contain ';'`, ni
`must not embed credentials`, ni `file not found`… Si un motivo cambiara a otro equivocado, nada
fallaría. Sí se comprueban `got list`/`got dict`, `(default)`, `unknown configuration key` e
`invalid TOML in`.

- **tests/unit/test_config.py** (implementer): añadir a las tablas del bloque 2 el motivo
  esperado. Recomendado: una columna o un campo `"reason"` por tipo (p. ej. `_PORT` →
  `between 1 and 65535`), o filas `(env, toml, motivo)` donde un mismo tipo tenga varios (las
  URL: esquema, credenciales, query/fragmento, `;`, URL mal formada), y que
  `test_invalid_values_are_rejected_naming_the_key` haga `assertIn(motivo, ...)`. El implementer
  debe listar los motivos reales que da hoy cada fila en lugar de suponerlos. Los motivos de
  `config_file` (`file not found`, `not valid UTF-8`, `nested too deeply`, `invalid config file
  path`) en `test_missing_file` y `test_unreadable_files_raise_validation_error`.
- **Tests:** las mutaciones "cambiar el texto de `config.py:216`" y "cambiar el de
  `config.py:153`" deben hacer fallar algún test.
- **Decisión del humano (2026-10-11):** acepta la propuesta: **todos los motivos**, con el
  motivo esperado en las tablas del bloque 2 y los de `config_file` en sus tests.

## 18. Helper común para pasar la ruta por argumento o por `GEOAGENT_CONFIG_FILE` (prioridad baja)

Pregunta: revisión del bloque 6 (`TestUntrustedNamesInErrors`). Respuesta: la expresión
`(None, {"GEOAGENT_CONFIG_FILE": path}) if via_env else (path, {})` se repite 4 veces en el
bloque (`test_path_with_control_characters_is_not_repeated`,
`test_path_with_control_characters_via_load_or_exit`, `test_long_path_is_truncated` y
`test_long_toml_error_text_is_truncated`), y es lo mismo que `TestValidation._config_file_args`,
que al ser un método no se puede usar fuera de su clase.

- **tests/unit/test_config.py** (implementer): convertir `_config_file_args` en una función de
  módulo (junto a los helpers del bloque 1) y usarla en `TestValidation` y en las 4 apariciones
  de `TestUntrustedNamesInErrors`. Usarla también en `TestSecretMasking.test_secret_in_file_is_rejected`,
  que hace lo mismo con `if via_env: loader(env={"GEOAGENT_CONFIG_FILE": path}) else: loader(path, env={})`
  (observación 4 del bloque 8). El bloque 7 no la repite (pasa la ruta directamente).
- **Tests:** sin cambio de cobertura; mismo número de subtests antes y después.
- **Decisión del humano:** sí (2026-10-11).

## 19. Legibilidad en `test_long_path_is_truncated` y `…` frente a `\u2026` (prioridad baja)

Pregunta: revisión del bloque 6. Respuesta: `load_or_exit(loader, *args[:1], env=args[1])`
equivale a `load_or_exit(loader, args[0], env=args[1])` pero se lee peor; y en el archivo se
mezclan `"…"` y `"\u2026"` para el mismo carácter.

- **tests/unit/test_config.py** (implementer): usar `args[0]` (o el desempaquetado `path, env`
  del helper del punto 18) y unificar el carácter en todo el archivo. Recomendado: `"…"` literal
  (el archivo ya es UTF-8 y se lee mejor).
- **Tests:** sin cambio de cobertura.
- **Decisión del humano:** sí (2026-10-11).

## 20. `test_valueless_query_item_is_masked` no comprueba lo que se muestra (prioridad baja)

Pregunta: revisión del bloque 8 (`TestQueueUrlQueryMasking`). Respuesta: el test solo comprueba
que `s3cr3t` no aparece en las tres vistas y que `cfg.queue_url` queda intacta. Comprobado por el
leader (2026-10-11): `amqp://h/?s3cr3t` se muestra como `amqp://h/?***`
(`amqp://h/?a=1&s3cr3t` → `amqp://h/?a=***&***`). Si el código mostrara `amqp://h/?` o quitara la
query, el test seguiría pasando.

- **tests/unit/test_config.py** (implementer): añadir
  `_assert_shown(self, cfg, "queue_url", f"amqp://h/?{MASK}")`. Valorar una segunda fila mixta
  (`amqp://h/?a=1&s3cr3t` → `amqp://h/?a=***&***`).
- **Tests:** los dos loaders × las dos fuentes, como ahora.
- **Decisión del humano:** sí (2026-10-11).

## 21. `test_non_utf8_file_via_load_or_exit_exits_2` solo prueba la ruta como argumento (prioridad baja)

Pregunta: revisión del bloque 8 (`TestLoadOrExit`). Respuesta: el resto de tests de archivo
(bloques 4 y 6) prueban también `GEOAGENT_CONFIG_FILE`; este no.

- **tests/unit/test_config.py** (implementer): añadir el bucle `via_env` usando el helper del
  punto 18.
- **Tests:** los dos loaders × las dos vías.
- **Decisión del humano:** sí (2026-10-11).

## 22. `test_valid_config_is_returned`: valor esperado en la tupla (prioridad baja)

Pregunta: revisión del bloque 8. Respuesta: el valor esperado se busca en un diccionario dentro
del `assert` (`{"max_workers": 2, "port": 8080}[key]`).

- **tests/unit/test_config.py** (implementer): iterar sobre tuplas
  `(loader, key, expected)`: `(load_agent_config, "max_workers", 2)`,
  `(load_backend_config, "port", 8080)`. Solo estilo.
- **Tests:** sin cambio de cobertura.
- **Decisión del humano:** sí (2026-10-11).
