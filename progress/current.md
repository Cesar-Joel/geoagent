# Sesión actual

> Este archivo se vacía al cerrar cada sesión y se mueve a `history.md`, salvo la sección
> "Notas para features futuras", que persiste (ver `AGENTS.md` §5 bis).
> Mientras trabajas, **mantenlo actualizado en tiempo real**, no al final.

- **Feature en curso:** ninguna (la feature 3 `config_system` se volvió a cerrar el 2026-10-11)
- **Inicio:**
- **Agente:**
- **Rama:**

## Plan

## Bitácora

## Notas para features futuras

> Sección persistente: **no se vacía al cerrar la sesión**. Reglas en `AGENTS.md` §5 bis.
> Una nota se borra cuando la feature destino la recoge (spec o implementación) o el humano la
> descarta, y se deja constancia en `history.md`.
> Ordenadas por id de feature. Una nota que afecta a varias features se escribe una sola vez, en
> la de menor id, y las demás la referencian.

### 5 `backend_api_skeleton`

- El `host` validado por `config` se usa en el `bind`. Que los errores de `bind` (`EADDRNOTAVAIL`,
  `EADDRINUSE`) nombren `host`/`port` y no repitan nada más. Si el CLI llega a pasar la ruta de la
  config como `Path`, añadir un test de arranque con `Path` (en `config` ya está cubierto).
  Origen: "Para features futuras" de las rondas 7 y 8 de `progress/review_config_system.md`.

### 7 `agent_http_client`

- Validar la sintaxis del host de `backend_url` y `queue_url` con la misma regla que `_bind_host`
  (IP o nombre DNS ASCII) o, como mínimo, rechazar `\` y `%` en el netloc, con un test que
  compruebe que el cliente HTTP conecta al mismo host que valida `config`. Hoy se aceptan
  `http://h h/`, `http://-h-/`, `http://ｅxample.com/` (IDNA/NFKC), `http://h%0aINFO/` y, sobre
  todo, `http://good\.evil.com/`: `urlparse` toma `good\.evil.com` como host, pero un parser
  WHATWG lee el host `good` y el path `/.evil.com`. Como mínimo, que el error de conexión nombre
  la clave de configuración y no repita la URL completa con su query. Afecta también a la
  feature 9. Origen: m9 de la ronda 6 y "Para features futuras" de la ronda 8 de
  `progress/review_config_system.md`.
- `config` ya rechaza `auth_token` con caracteres de control (D1, ronda 8). Aun así, usar una
  librería HTTP que rechace cabeceras con saltos de línea y añadir un test con un token así.
  Afecta también a la feature 9 (`queue_username`/`queue_password`). Origen: "Para features
  futuras" de la ronda 7 de `progress/review_config_system.md`.

### 9 `message_queue_layer`

- Decidir en su spec cómo llegan las opciones del broker. Preferible: campos tipados
  (`queue_heartbeat`, …) en `_COMMON_SPECS` de `config.py` y prohibir la query en `queue_url`;
  así el enmascarado sale de `secret=True`. Alternativa: que `common/queue.py` declare las
  opciones de query admitidas con su marca `secret` y que `config.py` derive de ahí la lista de
  claves visibles (hoy se enmascaran todos los valores de la query). Descartado: inspeccionar la
  librería AMQP. Origen: sesión de preguntas del 2026-10-04 (`progress/questions_config_system.md`, punto 4).
- No volcar `queue_url` sin enmascarar ni en los logs propios ni en los de la librería AMQP:
  usar siempre `to_safe_dict()`. Origen: "Para features futuras" de las rondas 4 y 7 de
  `progress/review_config_system.md`.
- Validación de la sintaxis del host de `queue_url` y credenciales con saltos de línea: ver las
  notas de la feature 7.

### 11 `agent_concurrency_runtime`

- `max_workers` no tiene límite superior (desde el TOML se acepta `99999999999999999999999`) y
  `request_timeout`/`heartbeat_interval` aceptan valores subnormales (`5e-324`). Fijar límites
  razonables (tope de `max_workers`, timeout mínimo) y validarlos en `config.py`. Afecta también a
  la feature 19. Origen: "Para features futuras" de la ronda 5 de `progress/review_config_system.md`.

### 19 `resource_management`

- Límites de `max_workers` y de los timeouts: ver la nota de la feature 11.

### 20 `structured_logging`

- Que el logger enmascare `AgentConfig`/`BackendConfig` mediante `to_safe_dict()`, con un test
  que compruebe que ni los secretos ni los valores de la query de `queue_url` aparecen en la
  salida JSON. Hasta entonces, la parte "ni en los logs" del acceptance de `config_system` se
  apoya solo en `to_safe_dict()`. Origen: r1 de `progress/review_config_system.md`.
- Valorar un aviso (no un error) ante variables `GEOAGENT_*` desconocidas (una errata como
  `GEOAGENT_MAX_WORKER` hoy pasa desapercibida). Necesita el logger; sin decisión del humano.
  Origen: r2 de `progress/review_config_system.md`.
- Revisar si `load_or_exit` debe seguir usando `sys.stderr.write` o pasar al logger.
  Origen: hallazgo 3 de la ronda 1 de `progress/review_config_system.md`.
- Escapar los caracteres de control en **todos** los campos del log JSON, no solo en el `repr`
  de la config, con un test con `\n` y `\x1b` en un mensaje. Así, un error de configuración con
  datos del usuario no puede romper una línea de log aunque se escape por otra rama. Origen:
  "Para features futuras" de la ronda 7 de `progress/review_config_system.md`.
- Truncar los campos largos con el mismo criterio que `config` (o uno común en
  `geoagent.common`): `_clip` (conserva el principio, 40 caracteres + `…`) para valores y claves,
  y `_clip_tail` (conserva el final) para rutas. Origen: "Para features futuras" de las rondas
  8-10 de `progress/review_config_system.md`.

### 24 `unit_test_suite`

- m8: añadir `pytest-cov` a `[dev]` y un objetivo de Makefile que mida la cobertura y falle por
  debajo del 85%. `docs/verification.md` (Nivel 5) dice que `make test-unit` ya la comprueba y hoy
  no es cierto. Origen: `progress/review_core_domain_models.md` (m8) y `history.md`.
- El constructor de `AgentConfig`/`BackendConfig` no valida nada. O se documenta que los
  loaders son la única entrada válida, o se añade un `__post_init__` que pase cada campo por su
  parser. Aplica a la primera feature que construya las dataclasses a mano. Origen: "Para
  features futuras" de la ronda 7 de `progress/review_config_system.md` ("sin feature asignada").

### 25 `integration_test_suite`

- Ejecutar `test_config` con un Python 3.9 real (ver `docs/verification.md`) para confirmar la
  rama `tomli` y m10: en 3.9, `urlparse(...).port` podría aceptar puertos como `h:1_0`, `h:+80`
  o `h: 80`, que en 3.14 se rechazan. Si hay diferencia, validar el puerto a mano con
  `netloc.rpartition(":")`. Si se mantiene `>=3.9`, incluir una versión anterior a 3.9.5 (m18):
  el rechazo de ceros iniciales en IPv4 (P1) solo se prueba con un mock de `ipaddress`, así que
  allí habría que añadir `GEOAGENT_HOST=010.0.0.1` como prueba de humo. La matriz 3.9 de la CI
  del PR lo cubre en parte. Origen: m10 de la ronda 6 y "Para features futuras" de las rondas
  8 y 9 de `progress/review_config_system.md`.

### Sin feature asignada

- Homogeneizar el idioma del proyecto: decidir si `README.md`, `docs/`, `specs/`, `progress/` y
  `AGENTS.md` pasan al inglés (son visibles en el repo) y si se traducen los commits y PR
  anteriores al 2026-10-11, que están en español. Desde esa fecha, los commits y los PR van en
  inglés. Origen: decisión del humano del 2026-10-11 ("Idioma" en `docs/conventions.md`).

## Próximo paso

Siguiente feature `pending`: 4 `agent_local_store` (`"sdd": true` → `spec_author`).
Pendiente del humano: push de `feat/3-config_system` y PR (borrador en `progress/pr_config_system.md`).
