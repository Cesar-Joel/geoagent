# Sesión actual

> Este archivo se vacía al cerrar cada sesión y se mueve a `history.md`, salvo la sección
> "Notas para features futuras", que persiste (ver `AGENTS.md` §5 bis).
> Mientras trabajas, **mantenlo actualizado en tiempo real**, no al final.

- **Feature en curso:** ninguna (la feature 3 `config_system` se cerró el 2026-10-04)
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

### 7 `agent_http_client`

- Si se quiere un fallo temprano, validar la sintaxis del host (etiquetas DNS o IP) de
  `backend_url` y `queue_url`: hoy se aceptan `http://h h/` y `http://-h-/`. Como mínimo, que el
  error de conexión nombre la clave de configuración y no repita la URL completa con su query.
  Afecta también a la feature 9. Origen: m9 de la ronda 6 de `progress/review_config_system.md`.

### 9 `message_queue_layer`

- Decidir en su spec cómo llegan las opciones del broker. Preferible: campos tipados
  (`queue_heartbeat`, …) en `_COMMON_SPECS` de `config.py` y prohibir la query en `queue_url`;
  así el enmascarado sale de `secret=True`. Alternativa: que `common/queue.py` declare las
  opciones de query admitidas con su marca `secret` y que `config.py` derive de ahí la lista de
  claves visibles (hoy se enmascaran todos los valores de la query). Descartado: inspeccionar la
  librería AMQP. Origen: sesión de preguntas del 2026-10-04 (`progress/questions_config_system.md`, punto 4).
- No volcar `queue_url` en logs propios sin enmascarar: usar siempre `to_safe_dict()`. Origen:
  "Para features futuras" de la ronda 4 de `progress/review_config_system.md`.
- Validación de la sintaxis del host de `queue_url`: ver la nota de la feature 7.

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

### 24 `unit_test_suite`

- m8: añadir `pytest-cov` a `[dev]` y un objetivo de Makefile que mida la cobertura y falle por
  debajo del 85%. `docs/verification.md` (Nivel 5) dice que `make test-unit` ya la comprueba y hoy
  no es cierto. Origen: `progress/review_core_domain_models.md` (m8) y `history.md`.

### 25 `integration_test_suite`

- Ejecutar `test_config` con un Python 3.9 real (ver `docs/verification.md`): confirmar la rama
  `tomli` y m10, porque en 3.9 `urlparse(...).port` podría aceptar puertos como `h:1_0`, `h:+80`
  o `h: 80`, que en 3.14 se rechazan. Si hay diferencia, validar el puerto a mano con
  `netloc.rpartition(":")`. La matriz 3.9 de la CI del PR lo cubre en parte. Origen: m10 de la
  ronda 6 de `progress/review_config_system.md`.

## Próximo paso

Siguiente feature `pending`: 4 `agent_local_store` (`"sdd": true` → `spec_author`).
