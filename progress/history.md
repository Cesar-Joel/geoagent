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
