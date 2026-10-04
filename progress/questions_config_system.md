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
