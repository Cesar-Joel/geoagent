# Review — feature 1

**Veredicto:** APPROVED (ronda 2)

Feature 1 `project_scaffold`, `"sdd": false`, `in_progress`. No tiene `specs/project_scaffold/` y es
correcto (`docs/specs.md`, "Cuándo NO aplica SDD"). La trazabilidad R<n> se sustituye por los
criterios `acceptance` de `feature_list.json`. Toda la evidencia la ha obtenido el reviewer
(2026-09-14, Python 3.14.4, GNU Make 4.4.1, ruff 0.16.7 y pytest 9.1.1 en `.venv`).

## Ronda 1 (histórico)

Veredicto: CHANGES_REQUESTED. Se pidió:
1. Limitar ruff al código Python. ruff 0.16.7 formateaba los bloques de código de los `.md`
   (`docs/`, `CHECKPOINTS.md`, specs, `.claude/agents/`), así que `make format` podía reescribir
   documentación aprobada y `make lint` podía fallar por fragmentos de la documentación.
2. Corregir el informe del implementer. La primera pasada de `make format` había reformateado
   `docs/conventions.md` (líneas en blanco en sus bloques python), no un archivo propio, como
   afirmaba el informe.

## Ronda 2: verificación de los cambios pedidos

- Cambio 1: [x] resuelto.
  - `pyproject.toml` `[tool.ruff]`: `extend-exclude = ["*.md"]` y `force-exclude = true`.
    `Makefile`: `RUFF_PATHS := src tests` en `lint` y `format`.
  - `ruff format --check -v .`: 0 `.md` en `Included path`/`format_path`. Incluye `pyproject.toml`
    y 12 `.py`: `12 files already formatted`.
  - `ruff check --show-files .`: 0 `.md` (`pyproject.toml` y los 12 `.py` de `src/` y `tests/`).
  - `ruff format --check -v src tests`: 0 `.md`.
  - `ruff format --check -v docs/conventions.md` (ruta explícita): `Ignored path via extend-exclude`
    y `No Python files found`, gracias a `force-exclude`.
  - Sondas en la copia `scratchpad/probe2`:

    | Sonda | Resultado |
    |---|---|
    | `.md` con `x = {  "a":1 }` en un bloque python, en la raíz y en `docs/` | `make format` y `make lint` salen con 0 sin tocarlo; `ruff format .` y `ruff format docs/probe_doc.md` tampoco lo tocan; los md5 de todos los `.md` quedan intactos |
    | Import sin usar en `src/` | `make lint` sale con 2 (F401) |
    | `.py` sin formatear en `src/` | `make lint` sale con 2 (`1 file would be reformatted`); `make format` lo corrige a `X = {"a": 1}` |
    | Imports desordenados en `tests/` | `make lint` sale con 2 (I001); `make format` los ordena |
    | Test unitario rojo | `make test` y `make test-unit` salen con 2 |
    | Test de integración rojo | `make test` y `make test-integration` salen con 2 |
    | Error de colección en integración | `make test-integration` sale con 2 |
    | Copia limpia al final | `make lint` y `make test` salen con 0 |

- Cambio 2: [x] resuelto.
  - `docs/conventions.md` ya no conserva rastro del formateo. Los dos bloques python vuelven a tener
    una sola línea en blanco: ninguna tras el docstring del ejemplo (línea 36-37) y una entre clases
    del bloque de errores. Si le aplico ruff en una copia sin exclusión, añade 6 líneas en blanco,
    lo que prueba que el archivo actual no es la salida de ruff. El resto del diff frente a HEAD son
    cambios previos del humano (no se evalúan).
  - `progress/impl_project_scaffold.md` incluye "Modificado **por accidente** en la ronda 1, ya
    revertido". Ahí nombra `docs/conventions.md`, explica la causa (ruff formatea `.md`), qué cambió
    y que lo restauró el leader. También reconoce que la afirmación anterior era errónea y retira la
    explicación incorrecta del recuento de archivos. Es una declaración honesta y verificable.
  - Entre las rondas 1 y 2, fuera de `pyproject.toml` y `Makefile`, solo cambian los md5 de
    `docs/conventions.md` (restauración), `progress/current.md`, `progress/impl_project_scaffold.md`
    y este informe. `src/`, `tests/`, `.github/workflows/ci.yml`, `CONTRIBUTING.md` y `.gitignore`
    no cambian.

## Acceptance ↔ evidencia

- A1: [x] `src/geoagent/{common,agent,backend,spark,tools}/` y `tests/{unit,integration}/`, todos
  con `__init__.py`. `TestPackageLayout.test_all_layer_packages_are_importable` pasa. `tools/` va
  incluido por decisión acordada.
- A2: [x] `pyproject.toml` es instalable, con `dependencies = []`, extra `dev` y
  `[project.scripts]` `geoagent-agent`/`geoagent-backend`. `make install` sale con 0. Los binarios
  de `.venv/bin/` salen con 0 sin argumentos y con `--version`; en la ronda 1 salían con 2 ante un
  argumento desconocido.
- A3: [x] `make lint` sale con 0 (`12 files already formatted`). `make format` sale con 0
  (`12 files left unchanged`), y los md5 de todo el árbol (42 archivos, 17 `.md`, sin `.git/`,
  `.venv/` ni cachés), antes y después, son idénticos. `make test`, `make test-unit` y
  `make test-integration` salen con 0 (integración vacía: exit 5 de pytest convertido en 0, los
  demás códigos se propagan).
- A4: [x] `CONTRIBUTING.md`: ramas `feat/<id>-<name>`, formato de commits y "Una feature por PR".
- A5: [x] (estático y local) `.github/workflows/ci.yml` es YAML válido, `on: push` y
  `pull_request`, y ejecuta `make install`, `make lint` y `make test`. No hay
  `continue-on-error`, `|| true`, `set +e` ni `if:`. Las sondas muestran que lint y tests salen
  con 2 ante fallos reales. No se ha ejecutado en GitHub.
- A6: [x] `make test-unit`: `5 passed, 11 subtests passed in 0.23s` con
  `tests/unit/test_smoke.py`.

## Tasks completas

- N/A: la feature tiene `"sdd": false`, así que no hay `specs/project_scaffold/tasks.md`.

## Checkpoints

- C1: [x] Existen los 4 archivos base y los 4 docs. `./init.sh` sale con 0 (ejecutado al final de
  esta ronda).
- C2: [x] Solo la feature 1 está en `in_progress`. No hay features `done` (N/A). `progress/current.md`
  describe la sesión activa.
- C3: [x] `src/geoagent/` contiene solo los 5 paquetes previstos. Sin dependencias de runtime; las
  dev están acordadas. Sin `print()` ni TODOs (grep limpio) y sin secretos. Cada módulo de `src/`
  tiene docstring y `from __future__ import annotations`.
- C4: [x] con N/A parcial. La cobertura ≥85% es N/A: es la feature 24. Los tests no usan red,
  broker ni credenciales. `tempfile` es N/A porque los tests no tocan el filesystem.
  `make test-unit` está en verde en menos de 60 s. `make test-integration` está en verde con la
  carpeta vacía.
- C5: [x] con N/A parcial. No hay archivos sin trackear sospechosos: `__pycache__`, `.venv`, cachés
  y `*.egg-info` están ignorados. La entrada de `history.md` es N/A: la escribe el cierre posterior
  al veredicto. La feature 1 está en `in_progress`, que es su estado correcto antes del cierre.
- C6: N/A. La feature tiene `"sdd": false`. `init.sh` confirma que no hay features sdd en un estado
  distinto de `pending` sin specs.

## Cambios requeridos (si aplica)

Ninguno.

Observaciones no bloqueantes (siguen vigentes):
- La CI no se ha ejecutado en GitHub. Hay que confirmar en el primer push que `setup-python` ofrece
  Python 3.9 en `ubuntu-latest`.
- `ruff>=0.6.0` sin tope: un cambio de versión de ruff en la CI puede alterar el resultado de lint o
  formato sin tocar el repo.
