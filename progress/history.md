# Bitácora histórica (append-only)

> Cada vez que se cierra una sesión, su resumen se añade aquí.
> No edites entradas anteriores. Solo añades al final.

---

## 2026-04-20 — Bootstrap del proyecto
- **Agente:** humano (Martín)
- **Cambios:** estructura inicial del arnés (AGENTS.md, init.sh, feature_list.json, docs/).
- **Resultado:** entorno listo. `./init.sh` verde.

## 2026-09-14 — Feature 1 project_scaffold
- **Agente:** leader + implementer + reviewer
- **Cambios:**
  - `pyproject.toml`: paquete `geoagent` instalable con layout `src/`, versión desde
    `geoagent.__version__` (0.1.0), `requires-python >=3.9`, sin dependencias de runtime y extra
    `dev` (`pytest>=8.0`, `ruff>=0.6.0`). Entry points `geoagent-agent` y `geoagent-backend`
    (stubs argparse con `--version`, devuelven 0).
  - `src/geoagent/{common,agent,backend,spark,tools}/`: se incluye `tools/` según
    `docs/architecture.md` y CHECKPOINTS C3, aunque el acceptance solo lista 4 paquetes.
    También `tests/{unit,integration}/` con `__init__.py` y `tests/unit/test_smoke.py`.
  - `Makefile` con `install`, `lint`, `format`, `test`, `test-unit` y `test-integration`. Gestiona
    `.venv/` (stamp dependiente de `pyproject.toml`) y usa solo sus herramientas.
    `test-integration` trata el exit 5 de pytest (suite vacía) como OK.
  - ruff para lint y formato (línea 100, comillas dobles, py39) y pytest para tests. Los `*.md`
    quedan excluidos de ruff (`extend-exclude` + `force-exclude`, y los objetivos del Makefile
    sobre `src tests`) para no reescribir docs ni specs aprobados.
  - CI en GitHub Actions (`.github/workflows/ci.yml`): en push y PR, matriz 3.9/3.14,
    `make install`, `make lint` y `make test`.
  - `CONTRIBUTING.md` (ramas `feat/<id>-<name>`, formato de commits, una feature por PR) y
    `.gitignore` (cachés de pytest/ruff, `*.egg-info`, `build/`, `dist/`).
- **Incidencia (ronda 1):** la primera pasada de `make format` ejecutaba `ruff format .`, que
  formatea los bloques python de los `.md`, y añadió líneas en blanco a `docs/conventions.md` sin
  que el informe lo declarara. El reviewer lo detectó (CHANGES_REQUESTED). El leader revirtió el
  archivo y el implementer excluyó `*.md` de ruff y corrigió el informe.
- **Resultado:** APPROVED en la ronda 2. `./init.sh` en verde; `make lint`, `make format`,
  `make test`, `make test-unit` y `make test-integration` salen con 0. Detalle en
  `progress/impl_project_scaffold.md` y `progress/review_project_scaffold.md`.
- **Pendientes no bloqueantes:** la CI aún no se ha ejecutado en GitHub; hay que confirmar en el
  primer push que `setup-python` ofrece Python 3.9 en `ubuntu-latest`. `ruff>=0.6.0` sin tope: un
  cambio de versión de ruff en la CI puede alterar el resultado de lint o formato sin tocar el repo.

## 2026-09-24 — Feature 2 core_domain_models
- **Agente:** leader + spec_author + implementer + reviewer
- **Spec:** `specs/core_domain_models/{requirements,design,tasks}.md` — 36 requirements EARS
  (R1–R36), 11 decisiones sujetas a aprobación humana (D1–D11) y 20 tasks. El humano aprobó el
  spec y todas las decisiones D1–D11 tal como estaban redactadas.
- **Cambios:**
  - `src/geoagent/common/errors.py`: `GeoAgentError(Exception)`, `ValidationError(GeoAgentError)`
    (con `message` y `field`) y `UnknownSchemaVersionError(ValidationError)` (con `model` y
    `version`). Alcance mínimo (D1): las otras excepciones de `docs/conventions.md` las añadirán
    las features que las lancen.
  - `src/geoagent/common/models.py`: `SCHEMA_VERSION`/`SUPPORTED_SCHEMA_VERSIONS`, los enums
    `JobStatus` (con `is_terminal`) y `FailureCause`, la tabla de transiciones válidas y
    `can_transition(from_status, to_status)` (D7: no lanza por transición inválida, solo por
    argumentos que no son `JobStatus`), y los seis modelos inmutables
    (`JobSpec`, `Job`, `JobProgress`, `JobResult`, `AgentInfo`, `Heartbeat`) como
    `@dataclass(frozen=True)` con `__post_init__` (validación y normalización),
    `to_dict()`/`from_dict()` explícitos por modelo y helpers privados de validación,
    parseo/formateo de timestamps (ISO 8601 UTC con sufijo `Z`, sin `datetime.fromisoformat`
    por incompatibilidad 3.9/3.11+) y de payload (`_check_payload`, orden determinista:
    Mapping → `schema_version` → claves desconocidas → claves obligatorias ausentes).
    Sin dependencias nuevas, sin IO, compatible con Python 3.9 (sin `match`, `StrEnum`,
    `datetime.UTC`, `slots=`/`kw_only=`, `get_type_hints`).
  - `tests/unit/test_errors.py` (`TestErrorHierarchy`) y `tests/unit/test_models.py` (12 clases:
    `TestJobStatus`, `TestFailureCause`, `TestCanTransition`, `TestModelFields`,
    `TestImmutability`, `TestRoundTrip`, `TestSchemaVersion`, `TestTimestamps`,
    `TestPayloadValidation`, `TestJobProgressBoundaries`, `TestJobResultBoundaries`,
    `TestJobSpecBoundary`).
- **Incidencia (ronda 1):** `CHANGES_REQUESTED`. Un defecto funcional contra R25 (`_parse_timestamp`
  aceptaba offsets `±HH:MM` con minutos ≥ 60, p. ej. `+05:60`) y tests insuficientes en varios
  requirements aunque `tasks.md` marcara las tasks correspondientes como `[x]`: R23 (no verificaba
  el instante/microsegundos resultante), R29 (no comprobaba `field` ni ejercitaba `from_dict`) y
  R27/T16 (no recorría los 6 modelos × cada clave obligatoria). Más seis hallazgos menores
  (m1–m6: `TypeError` crudo con claves desconocidas de tipos mezclados, R5 sin comprobar que la
  instancia queda sin cambios, R21 sin caso de microsegundos != 0, R6 sin cubrir `Heartbeat`,
  R18/19/20 solo probados con `JobSpec`/`Job`, R30/R33 con casos incompletos) y cinco nits
  (n1–n5). El implementer corrigió M1–M4 y m1–m6, y aplicó los nits triviales n1–n4 en una
  segunda ronda; m7 (un cambio en `.gitignore` ajeno a esta feature, preexistente del humano en
  el working tree) y m8 (cobertura no medible) quedaron fuera del alcance de esta feature por
  decisión del leader.
- **Resultado:** `APPROVED` en la ronda 2. `./init.sh` en verde; `make lint` y `make test-unit`
  (92 passed, 141 subtests passed) en verde. R1–R36 con al menos un test significativo que
  verifica el resultado concreto y el `field` cuando el requirement lo exige. `tasks.md` con
  T1–T20 en `[x]` reflejando el trabajo real. Detalle completo, mapeo tasks→código y
  trazabilidad `R<n> → test` en `progress/impl_core_domain_models.md`; veredictos de ambas
  rondas en `progress/review_core_domain_models.md`.
- **Nota del leader — `.gitignore` (m7):** el cambio que quita `.notes.json`/`.notes_*.json` de
  `.gitignore` es preexistente del humano (ya estaba en el working tree al inicio de la sesión,
  antes de que empezara el trabajo de esta feature). No forma parte del alcance de la feature 2 y
  queda fuera de su commit; lo gestiona el humano/leader por separado.
- **Pendientes de infraestructura (m8):** `pytest-cov` no está en `pyproject.toml [dev]` y
  `make test-unit` no mide cobertura, por lo que el checkpoint C4 (cobertura ≥ 85%,
  `docs/verification.md` Nivel 5) no es verificable. Es un fallo heredado de la feature 1, no de
  la feature 2, y no la bloqueó. Queda como candidato a una feature o tarea de tooling futura:
  añadir `pytest-cov` a `[dev]` y un objetivo de Makefile que mida y reporte cobertura.
- **Pendientes no bloqueantes:** Python 3.9 no se verificó con un intérprete local en esta sesión
  (no disponible en el entorno); se revisó manualmente que el código no usa construcciones
  exclusivas de 3.10+/3.11+, y la verificación real queda delegada a la matriz 3.9/3.14 de CI.

### Reapertura (ronda 3, 2026-09-27)
- **Motivo:** revisión humana post-aprobación: los tests de R24 y R25 (rechazo de `datetime`
  naive en el constructor y en `from_dict`) solo cubrían `JobSpec.time_start`; una regresión en
  cualquier otro campo `datetime` de los seis modelos no la habría detectado la suite. Feature
  reabierta `done` → `in_progress`.
- **Cambios (solo tests, sin tocar `src/`):** M5 y M6 de la ronda 3 — se parametrizó con
  `subTest` la comprobación de R24/R25 sobre los cinco campos `datetime` (`JobSpec.time_start`,
  `JobSpec.time_end`, `Job.created_at`, `JobResult.finished_at`, `Heartbeat.sent_at`), se añadió
  el caso de `tzinfo` personalizado con `utcoffset() -> None`, el caso anidado
  `Job.from_dict`/`spec.time_start` y el caso de objeto `datetime` naive en `from_dict`. Ronda 3
  del reviewer detectó N1 (el caso naive no protegía contra un objeto `datetime` **aware** en
  `from_dict`); el implementer añadió ese caso (subsección "Ronda 3 bis — N1").
- **Resultado:** `APPROVED` en la ronda 3 bis. `./init.sh`, `make lint` y `make test-unit` en
  verde: 96 passed, 153 subtests. Veredictos completos en
  `progress/review_core_domain_models.md` ("Ronda 3", "Ronda 3 — feature 2" y "Ronda 3 bis").

### Cierre enmienda D12 (2026-10-02)
- **Feature:** 2 `core_domain_models` — `in_progress` → `done` tras autorización humana.
- **Cambios:** enmienda D12 aplicada (T21–T26); test de R33 alineado vía `from_dict` con `_BAD_STATUSES`.
- **Resultado:** `APPROVED` en la "Ronda D12" (H1 y m1 resueltos). `make lint` limpio y `make test-unit`: 101 passed, 243 subtests. Veredicto en `progress/review_core_domain_models.md`.

### Bitácora de la sesión (ronda 4 → D12, 2026-09-27 a 2026-10-02)
- **Agente:** leader → spec_author → implementer → reviewer
- **Rama:** feat/2-core_domain_models (fusionada en `main` en el PR #3)
- 2026-09-27: revisión humana. Siguiendo el criterio de M5 y M6 (un caso por campo para los tests de conexión), los campos `str` apenas tienen test de conexión: 3 de 14. Feature reabierta: `done` → `in_progress`.
- 2026-09-27: M7 se rehízo con tests generados por introspección (98 passed, 195 subtests). Reviewer, ronda 4 (mutaciones sobre una copia de `src/`, autorizado por el humano): CHANGES_REQUESTED. M8: el caso `failure_cause → 123` pasa por la regla de `succeeded` y no por la comprobación de tipo. Además: guarda del séptimo modelo y trazabilidad. Devuelto al implementer (ronda 4 bis).
- 2026-09-27: ronda 4 bis → CHANGES_REQUESTED por N2 (R28 solo en `Job.assigned_agent_id`); se resolvió en la ronda 4 ter con un test generado. Ronda 4 ter → CHANGES_REQUESTED tras un barrido completo de las conexiones de `from_dict()`: P1 (orden de R27), P2 (R31 en `JobResult.status`), P3 (R35 en 4 modelos). Devuelto al implementer (ronda 4 quater).
- 2026-09-27: ronda 4 quater → APPROVED (102 passed, 246 subtests). El test de R35 espía `_check_payload` con `mock` y es frágil. El humano elige D1: derivar las claves obligatorias y opcionales de `dataclasses.fields()`. Enmienda al spec en curso con el spec_author, que la dejará en `spec_ready`. ⏸ Después hace falta la aprobación humana.
- 2026-09-27: el spec_author deja la enmienda D12 (design §5 y tasks T21–T26) en `spec_ready`. ⏸ ESPERANDO APROBACIÓN HUMANA.
- 2026-10-02: el humano aprueba D12 ("aprobado D12, pásala a in_progress"). `spec_ready` → `in_progress`. Se lanza el implementer con T21–T26.
- 2026-10-02: implementer completa T21–T26 (lint OK, 101 passed, 240 subtests; mutante M2 equivalente). Reviewer, ronda D12: CHANGES_REQUESTED solo por H1 (fila R35 del mapa de trazabilidad citaba el test espía eliminado) y m1 (constancia de `./init.sh`). El leader corrige ambos en `progress/impl_core_domain_models.md`. Según el reviewer, con H1 resuelto la ronda queda APPROVED. ⏸ Pendiente: cierre de la feature.
- 2026-10-02: el humano resuelve n1 de la revisión D12 y pide alinear `test_status_other_than_succeeded_or_failed_raises_via_from_dict` con el test del constructor. El implementer lo hace con `_BAD_STATUSES` compartido (QUEUED, RUNNING, CANCELLED): 101 passed, 243 subtests, lint OK. ⏸ Pendiente: cierre de la feature.
- 2026-10-02: el humano autoriza el cierre. El implementer marca la feature 2 como `done` y la registra en `history.md` (lint OK, 101 passed, 243 subtests). El leader reescribe la sección "Idioma" de `docs/conventions.md` (código en inglés, todo lo demás en español) y añade a `CLAUDE.md` la regla de hablarle al humano en español.
- 2026-10-02: commits `84b044b` (feature 2, PR #3) y `2270858` (`chore(harness)`: reglas de idioma y `.gitignore`, PR #2), ambos fusionados en `main`.
- **Próximo paso pendiente:** m8, medir cobertura con `pytest-cov` (pendiente de infraestructura).


## 2026-10-04 — Feature 3 config_system
- **Agente:** leader + implementer + reviewer (`"sdd": false`, sin spec)
- **Rama:** feat/3-config_system
- **Cambios:**
  - `src/geoagent/common/config.py`: configuración por capas (defaults < TOML < variables
    `GEOAGENT_*`) para agente y backend, con `load_agent_config`, `load_backend_config` y
    `load_or_exit` (stderr y exit code 2). Dataclasses inmutables con `repr` y `to_safe_dict()`
    que enmascaran secretos; secretos solo por variable de entorno; validación temprana con
    `ValidationError` que nombra la clave sin repetir valores sensibles.
  - `tests/unit/test_config.py` (140 tests, 510 subtests) y `docs/config.md`.
- **Rondas** (detalle en `progress/impl_config_system.md`, veredictos en
  `progress/review_config_system.md`, sesión de preguntas en `progress/questions_config_system.md`):
  - Ronda 1: CHANGES_REQUESTED (credenciales de `backend_url` en `repr()`/errores, `nan`/`inf`
    aceptados, `print()` en `load_or_exit`).
  - Ronda 2: APPROVED.
  - Ronda 3 (sesión de preguntas del humano, 7 puntos, incluida una fuga real en `_parse_str`):
    CHANGES_REQUESTED por `ValueError` de `urlparse` con IPv6 mal formado y puerto sin validar.
  - Ronda 4: CHANGES_REQUESTED por `UnicodeDecodeError` y ruta con NUL en `_read_file`; m3 sin aplicar.
  - Ronda 5: APPROVED (135 passed).
  - Ronda 6 (corta): m7 (truncado de valores en errores numéricos), m8b (solo dígitos ASCII, sin
    `_`) y caracteres de control en el host; APPROVED (140 passed, lint e `init.sh` en verde).
- **Decisiones del humano:** solo TOML (sin YAML); `tomli` condicional para Python <3.11; exit
  code 2 ante configuración inválida; `backend_url` rechaza query y la query de `queue_url` se
  enmascara; fragmento rechazado; número entre comillas en el TOML (`max_workers = "3"`) aceptado.
- **Notas sin feature asignada resueltas:** `ruff>=0.16.7,<0.17` fijado en `pyproject.toml` y CI
  3.9/3.14 confirmada en verde por el humano en GitHub.
- **Bitácora de la sesión (`progress/current.md`):**
- 2026-10-02: cierre de la sesión de la feature 2 (bitácora movida a `history.md`). `./init.sh` en verde. Se lanza el implementer para la feature 3.
- 2026-10-02: el implementer termina la feature 3 (`in_progress`, informe en `progress/impl_config_system.md`; 125 passed, lint OK). Decisiones abiertas para el humano: `tomli` condicional para <3.11, solo TOML (sin YAML), secretos solo por variable de entorno, nombres y defaults propios, exit code 2. Se lanza el reviewer.
- 2026-10-02: reviewer, ronda 1 → CHANGES_REQUESTED (`progress/review_config_system.md`): credenciales de `backend_url` visibles en `repr()` y en errores; `nan`/`inf` aceptados en `heartbeat_interval` y `request_timeout`; `print()` en `load_or_exit`. Rama `tomli` comprobada solo por simulación. Se devuelve al implementer (ronda 2); la decisión solo-TOML queda pendiente del humano.
- 2026-10-02: el implementer resuelve la ronda 1 (130 tests; detalle en la sección "Ronda 2" de `progress/impl_config_system.md`). Se lanza el reviewer, ronda 2.
- 2026-10-02: reviewer, ronda 2 → APPROVED (130 passed, lint e `init.sh` en verde). ⏸ Pendiente del humano: decisión solo-TOML vs. YAML y autorización de cierre.
- 2026-10-04: sesión de preguntas del humano sobre `config.py` y `test_config.py`. Cambios anotados en `progress/questions_config_system.md` (7 puntos), incluida una fuga real: `_parse_str` repetía en el error una URL con credenciales cuando en el TOML el valor no es una cadena. Decisiones del humano: `backend_url` rechaza query y fragmento; la query de `queue_url` se enmascara entera; `max_workers = "3"` en el TOML se acepta; **r3 ratificada** (solo TOML, `tomli` condicional, exit code 2). `./init.sh` en verde (130 passed).
- 2026-10-04: punto 1 hecho por el leader (`.gitignore` → `.venv*/`; sección de Python 3.9 en local en `docs/verification.md`). Se lanza el implementer, ronda 3 (puntos 2-7).
- 2026-10-04: implementer, ronda 3 (puntos 2-7, más el rechazo del fragmento en `queue_url`, decidido por el humano tras el aviso del implementer): 131 passed, 424 subtests, lint OK, `./init.sh` en verde. Se lanza el reviewer, ronda 3.
- 2026-10-04: a petición del humano, el leader reúne en "Notas para features futuras" las notas dispersas del proyecto y lo convierte en regla del arnés (`AGENTS.md` §5 y §5 bis, `leader.md`, `spec_author.md`, `implementer.md`, `reviewer.md`, `CHECKPOINTS.md` C2).
- 2026-10-04: reviewer, ronda 3 → CHANGES_REQUESTED (`progress/review_config_system.md`, "Ronda 3"): `urlparse` lanza un `ValueError` sin capturar con hosts IPv6 mal formados (traceback, la clave no aparece y el valor se repite) y el puerto de las URL no se valida. Menores m2-m6. r3 ya no figura como pendiente. 3.9 solo comprobado por sintaxis. Se devuelve al implementer, ronda 4 (bloqueantes + m2-m5).
- 2026-10-04: implementer, ronda 4: 133 passed, 488 subtests, lint OK, `./init.sh` en verde (`progress/impl_config_system.md`, "Ronda 4"). Se lanza el reviewer, ronda 4.
- 2026-10-04: reviewer, ronda 4 → CHANGES_REQUESTED: los bloqueantes de la ronda 3 y m2, m4 y m5 están resueltos. Bloqueante nuevo: `_read_file` no captura `UnicodeDecodeError` (TOML que no es UTF-8; verificado por el leader) ni el `ValueError` de una ruta con un byte NUL. Además, m3 no se aplicó aunque el informe lo daba por hecho. Las notas para features futuras ya están en esta sección. Se devuelve al implementer, ronda 5.
- 2026-10-04: implementer, ronda 5: 135 passed, 494 subtests, lint OK, `./init.sh` en verde. El leader comprueba que m3 está aplicado y que un TOML que no es UTF-8 sale con exit 2. Se lanza el reviewer, ronda 5.
- 2026-10-04: reviewer, ronda 5 → **APPROVED** (135 passed, lint e `init.sh` en verde; 59 casos límite pasados por `load_or_exit` sin ninguna excepción sin tipar). Quedan tres menores para decisión del humano: m7 (mensajes numéricos sin límite de longitud), m8b (`int`/`float` aceptan dígitos Unicode y `_`) y caracteres de control en el host de las URL.
- 2026-10-04: decisiones del humano: ronda 6 corta (m7, m8b y caracteres de control en el host) antes de cerrar. Se resuelven las dos notas sin feature asignada: (1) el leader fija `ruff>=0.16.7,<0.17` en `pyproject.toml` (`make lint` en verde con 0.16.7); (2) el humano confirmó en GitHub que la matriz 3.9/3.14 de la CI corre en verde. Commit y PR autorizados tras el cierre: un commit de la feature 3 y otro `chore(harness)`. Se lanza el implementer, ronda 6.
- 2026-10-04: implementer, ronda 6: m7, m8b y caracteres de control en el host resueltos; 140 passed, lint e `init.sh` OK. El leader los comprueba a mano. Se lanza el reviewer, ronda 6.
- 2026-10-04: reviewer, ronda 6 → **APPROVED** (140 passed, lint con ruff 0.16.7 e `init.sh` en verde; unos 90 casos válidos siguen aceptándose). m9 y m10 pasan a "Notas para features futuras". `pending_changes.md` se renombra a `progress/questions_config_system.md` como registro de la sesión de preguntas. Se lanza el implementer para cerrar la feature.
- 2026-10-04: el implementer cierra la feature 3 (`done`). El leader vacía `progress/current.md` y conserva "Notas para features futuras".
