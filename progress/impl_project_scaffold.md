# Implementación — feature 1 `project_scaffold`

- **Feature:** 1 — project_scaffold (`sdd: false`, `in_progress`; sin `specs/`, por diseño)
- **Agente:** implementer
- **Fecha:** 2026-09-14
- **Estado propuesto:** listo para revisión, ronda 2 (no marcado `done`)

## Archivos creados o modificados

Creados:
- `pyproject.toml`: build con setuptools (>=64, editable PEP 660), layout `src/`, versión dinámica
  desde `geoagent.__version__`, `requires-python = ">=3.9"`, `dependencies = []`, extra `dev`
  (`pytest>=8.0`, `ruff>=0.6.0`), scripts `geoagent-agent` y `geoagent-backend`, configuración de
  ruff (line-length 100, `target-version = "py39"`, reglas `E,F,W,I,UP,B`, comillas dobles,
  `extend-exclude = ["*.md"]` y `force-exclude = true`) y de pytest (`testpaths = ["tests"]`).
- `Makefile`: `help`, `install`, `lint`, `format`, `test`, `test-unit`, `test-integration`.
  - `install` depende del stamp `.venv/.installed`, que depende de `pyproject.toml`. Crea
    `.venv/` con `$(PYTHON) -m venv` (por defecto `python3`) e instala `-e ".[dev]"`.
  - Todos los objetivos dependen del stamp y usan `.venv/bin/ruff` o `.venv/bin/python -m pytest`,
    nunca las herramientas del sistema.
  - `lint` = `ruff check src tests` + `ruff format --check src tests`. `format` =
    `ruff check --select I --fix src tests` (orden de imports) + `ruff format src tests`.
    Los objetivos de ruff solo operan sobre `RUFF_PATHS := src tests`.
  - `test` = `test-unit` + `test-integration`. `test-integration` convierte de forma explícita
    el exit 5 de pytest ("no se recogieron tests") en 0 con un mensaje, y propaga cualquier
    otro código.
- `src/geoagent/__init__.py` (`__version__ = "0.1.0"`).
- `src/geoagent/{common,agent,backend,spark,tools}/__init__.py`.
- `src/geoagent/agent/cli.py` y `src/geoagent/backend/cli.py`: `main(argv=None) -> int` con
  `argparse` (`--version`). Sin argumentos muestra el uso por `sys.stderr` y devuelve 0. No
  implementan lógica de otras features y no tienen `print()`.
- `tests/__init__.py`, `tests/unit/__init__.py`, `tests/integration/__init__.py`
  (`tests/integration/` no contiene tests).
- `tests/unit/test_smoke.py`.
- `CONTRIBUTING.md`.
- `.github/workflows/ci.yml`.

Modificados a propósito:
- `.gitignore`: se añaden `.pytest_cache/`, `.ruff_cache/`, `*.egg-info/`, `build/` y `dist/`
  sin tocar las entradas existentes.
- `progress/current.md`: solo líneas en la Bitácora.

Modificado **por accidente** en la ronda 1, ya revertido:
- `docs/conventions.md`. La primera pasada de `make format` (ronda 1) ejecutaba `ruff format .`,
  y ruff 0.16.7 formatea también los bloques de código Python dentro de los `.md`. Así reescribió
  ese doc: añadió una línea en blanco tras el docstring del ejemplo "Estructura de archivo" y otra
  entre las clases del bloque de errores. Ese era el "1 file reformatted" de la ronda 1, y no un
  archivo escrito por mí, como afirmaba por error la versión anterior de este informe. No lo
  detecté ni lo declaré. El reviewer lo identificó y el **leader restauró** `docs/conventions.md`
  a su contenido previo. En la ronda 2 no he tocado ese archivo.

No se tocaron `init.sh`, `feature_list.json` ni `.claude/`. No se crearon `common/errors.py` ni
modelos. No se restauró el código antiguo borrado. Sin commits, ramas ni push.

## Mapa A<n> → evidencia

| Criterio | Evidencia | Resultado |
|---|---|---|
| A1 Layout `src/geoagent/{common,agent,backend,spark,tools}/` y `tests/{unit,integration}/` con `__init__.py` | `TestPackageLayout.test_all_layer_packages_are_importable` (importa los 5 paquetes); `ruff check --show-files` lista los `__init__.py` de los 5 paquetes y de `tests/`, `tests/unit/` y `tests/integration/` | OK |
| A2 `pyproject.toml` instalable, dependencias y entry points | `make install` (exit 0) instala `-e .[dev]`; existen `.venv/bin/geoagent-agent` y `.venv/bin/geoagent-backend`; `TestEntryPoints.test_main_without_arguments_returns_zero_and_prints_usage_to_stderr` y `test_version_flag_exits_zero_and_reports_package_version`; los binarios instalados salen con 0 con y sin `--version` | OK |
| A3 `make lint`, `make test` y `make format` sin errores | Comandos de verificación de la ronda 2: todos con exit 0, también en la segunda pasada; ruff limitado a código Python (ver Ronda 2) | OK |
| A4 `CONTRIBUTING.md` con ramas `feat/<id>-<name>`, formato de commits y una feature por PR | Secciones "Ramas", "Commits" y "Pull requests" de `CONTRIBUTING.md` | OK (revisión documental) |
| A5 CI que ejecuta lint y tests en cada push y falla si alguno falla | `.github/workflows/ci.yml`: `on: push` (y `pull_request`), matriz Python 3.9/3.14, pasos `make install`, `make lint`, `make test` (cada paso falla el job si su exit != 0). Sondas locales (ronda 1): un `import os` sin usar hace que `make lint` salga con exit 2 y un test rojo hace que `make test` salga con exit 2; sondas eliminadas | OK localmente; no ejecutado en GitHub |
| A6 `pytest` en verde con test de humo en `tests/unit/test_smoke.py` | `make test-unit`: `5 passed, 11 subtests passed` | OK |

Qué cubre `tests/unit/test_smoke.py`:
- Los 5 paquetes de capa importan y su `__name__` es el esperado.
- `geoagent.__version__` tiene formato `X.Y.Z`.
- `main([])` de cada entry point devuelve 0, no escribe en stdout y escribe `usage: <prog>` en stderr.
- `main(["--version"])` sale con `SystemExit(0)` e imprime `<prog> <__version__>`.
- Un argumento desconocido sale con `SystemExit(2)` ("unrecognized arguments").

## Ronda 1 — verificación original (histórico)

Entorno: Python 3.14.4 (WSL), GNU Make 4.4.1. En `.venv`: ruff 0.16.7 y pytest 9.1.1. En esta
ronda ruff operaba sobre `.` **incluyendo** los `.md`, así que sus cifras (27 archivos) mezclan
`.py` y `.md`.

| Comando | Salida resumida | Exit |
|---|---|---|
| `make install` | `python3 -m venv .venv` → `pip install -e ".[dev]"` → `touch .venv/.installed` | 0 |
| `make format` (1.ª) | `1 file reformatted, 26 files left unchanged`: el archivo reformateado fue `docs/conventions.md` (modificación accidental, ver arriba) | 0 |
| `make lint` | `All checks passed!`; `27 files already formatted` | 0 |
| `make test` / `test-unit` / `test-integration` | `5 passed, 11 subtests passed`; integración vacía → OK | 0 |
| Entry points (sin argumentos y `--version`) | uso por stderr / `geoagent-{agent,backend} 0.1.0` | 0 |
| `./init.sh` | `[OK] Entorno listo` | 0 |
| Sonda `make lint` con import sin usar / `make test` con test rojo | falla | 2 / 2 |

## Ronda 2 — cambios pedidos por el reviewer

Origen: `progress/review_project_scaffold.md` (CHANGES_REQUESTED).

### Cambio 1 — ruff limitado al código Python del proyecto

Hay dos barreras independientes:
1. `pyproject.toml` `[tool.ruff]`: `extend-exclude = ["*.md"]` y `force-exclude = true`, para que
   la exclusión se aplique aunque se pase una ruta de `.md` de forma explícita (p. ej. desde un
   editor o un hook). Afecta a cualquier invocación de ruff sobre el repo, no solo al Makefile.
2. `Makefile`: `lint` y `format` operan solo sobre `RUFF_PATHS := src tests`.

Orden seguido: no se ejecutó `make format` ni `ruff format` sin `--check` hasta aplicar y verificar
la exclusión. Antes de cualquier comando de ruff se guardó el md5 de todos los `.md` del repo (18,
sin `.venv/` ni `.git/`).

Verificación de la exclusión, con `ruff` sobre `.` (la ruta más amplia, que ejercita la
configuración de `pyproject.toml` y no la del Makefile):

```
$ .venv/bin/ruff format --check -v .            # exit 0
Included .md: 0
Ignored via extend-exclude .md: 17              # p. ej.:
  [ruff_workspace::resolver][DEBUG] Ignored path via `extend-exclude`: "README.md"
  [ruff_workspace::resolver][DEBUG] Ignored path via `extend-exclude`: "docs/conventions.md"
Included paths:
  pyproject.toml
  tests/__init__.py, tests/integration/__init__.py, tests/unit/__init__.py, tests/unit/test_smoke.py
  src/geoagent/__init__.py, src/geoagent/{common,agent,spark,tools,backend}/__init__.py
  src/geoagent/agent/cli.py, src/geoagent/backend/cli.py
12 files already formatted                      # antes: 27-28 (incluía .md)

$ .venv/bin/ruff check --show-files .
pyproject.toml + los mismos 12 .py de src/ y tests/  → .md listados: 0
```

(Son 17 `.md` ignorados por `extend-exclude` y no 18 porque el 18.º es `.pytest_cache/README.md`
(generado por pytest). Ruff no entra en ese directorio: lo descarta antes por `.gitignore`, según
la línea verbose `ignoring .pytest_cache: ... Gitignore ... ".pytest_cache/"` y
`git check-ignore -v`, que da `.gitignore:8:.pytest_cache/`. En ningún caso se incluye un `.md`.)

Nota sobre la verificación: mi primer intento de guard contó cualquier línea con `.md` en la
salida verbose, incluidas las líneas "Ignored path", y abortó el script antes de formatear. Se
corrigió el filtro para contar solo `Included path` / `format_path` sobre `.md` y se repitió la
verificación. No se ejecutó ningún formateo con el guard erróneo.

### Cambio 2 — informe corregido

- Declarada la modificación accidental de `docs/conventions.md` en la ronda 1: qué cambió, por qué
  ocurrió y que el leader la ha revertido (sección "Modificado por accidente").
- Eliminada la afirmación falsa de que el archivo reformateado era uno de los escritos en la sesión.
- Eliminado el comentario de la ronda 1 que atribuía a una causa desconocida la diferencia de
  recuento entre `ruff check` (13) y `ruff format` (27): la causa eran los `.md`.
- `docs/conventions.md` no se ha tocado en la ronda 2.

### Verificación completa (ronda 2)

| Comando | Salida resumida | Exit |
|---|---|---|
| `make install` | reinstalación tras editar `pyproject.toml`; luego `Nothing to be done for 'install'` | 0 |
| `make lint` | `ruff check src tests`: `All checks passed!`; `ruff format --check src tests`: `12 files already formatted` | 0 |
| `make format` | `ruff check --select I --fix src tests`: `All checks passed!`; `ruff format src tests`: `12 files left unchanged` | 0 |
| `make test` | unit: `5 passed, 11 subtests passed`; integration: `no tests ran` → `sin tests todavía (pytest exit 5), se considera OK` | 0 |
| `make test-unit` | `5 passed, 11 subtests passed in 0.23s` | 0 |
| `make test-integration` | `no tests ran in 0.06s` → mensaje de suite vacía | 0 |
| `.venv/bin/geoagent-agent` / `--version` | uso por stderr / `geoagent-agent 0.1.0` | 0 / 0 |
| `.venv/bin/geoagent-backend` / `--version` | uso por stderr / `geoagent-backend 0.1.0` | 0 / 0 |
| `./init.sh` | [OK] en bloques 1-4 (incluidos `pyproject.toml`, `feature_list.json válido (29 features)` y `make test-unit en verde`); [WARN] informativo por `tests/integration/`; `[OK] Entorno listo` | 0 |
| Idempotencia: `make format` (2.ª) | `12 files left unchanged` | 0 |
| Idempotencia: `make lint` y `make test` (2.ª) | en verde | 0 / 0 |
| md5 de los 18 `.md`, antes de ruff y al final | `diff` vacío: **idénticos** | — |

### `git status --short` (final de la ronda 2)

```
 M .claude/agents/{implementer,leader,reviewer,spec_author}.md, .claude/settings.json
 M .gitignore
 M CHECKPOINTS.md, docs/{architecture,conventions,specs,verification}.md
 M feature_list.json, init.sh
 M progress/current.md, progress/history.md
 D progress/{explore_*,impl_cli_*,review_cli_*}.md, specs/cli_recent/*.md
 D src/{__init__,cli,notes,storage}.py, tests/test_{cli,notes,storage}.py
?? .github/  CONTRIBUTING.md  Makefile  pyproject.toml  src/geoagent/  tests/integration/  tests/unit/
?? progress/impl_project_scaffold.md  progress/review_project_scaffold.md
```

Lectura: los `.md` en `M` (`.claude/agents/*`, `CHECKPOINTS.md`, `docs/*`, `progress/history.md`)
ya aparecían modificados en el `git status` inicial, antes de que empezara la ronda 1. Son cambios
previos del humano o del leader respecto a HEAD, y `git status` no permite distinguirlos por sí
solo. La prueba de que en la ronda 2 no he cambiado ningún `.md` aparte de
`progress/impl_project_scaffold.md` y `progress/current.md` es la comparación de md5: se tomó antes
de ejecutar ruff y se repitió después de toda la verificación, con los 18 `.md` idénticos (este
informe y la Bitácora se editaron después de ese diff). `progress/review_project_scaffold.md` es
del reviewer.

## Desviaciones y limitaciones

- **CI no ejecutada en GitHub.** Desde aquí no hay push. El workflow se validó por
  inspección y reproduciendo en local sus pasos (`make install`, `make lint`, `make test`),
  incluido que salen con código distinto de 0 ante un fallo. En la CI, `make install` recibe
  `PYTHON=python` para usar el intérprete de `actions/setup-python`. Queda pendiente confirmar
  en el primer push que la matriz 3.9/3.14 está disponible en `ubuntu-latest` (3.9 está fuera de
  soporte desde octubre de 2025; en local no hay intérprete 3.9).
- **Dependencias dev con solo versión mínima** (`pytest>=8.0`, `ruff>=0.6.0`), según lo
  indicado. La CI usará la última versión de ruff, así que un cambio de versión puede alterar el
  resultado de lint o formato sin tocar el repo. En Python 3.9, pip resolverá pytest 8.x.
- **A1 y `tools`:** el acceptance de `feature_list.json` lista `{common,agent,backend,spark}`.
  Se añadió también `tools/`, siguiendo la descripción de la feature, `docs/architecture.md` y
  CHECKPOINTS C3.
- **`__init__.py` en `tests/`, `tests/unit/` y `tests/integration/`:** se añadieron para cumplir
  al pie de la letra "cada paquete con su `__init__.py`".
- **Cobertura:** no se añade (feature 24).
- **`make format`** también ejecuta `ruff check --select I --fix` para ordenar imports (el
  formateador de ruff no los reordena). No aplica otros autofixes de lint.
