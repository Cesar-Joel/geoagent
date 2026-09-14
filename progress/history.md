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
