# Fix: test_smoke y colores de argparse

**Causa:** el entorno tiene `FORCE_COLOR=3`; con Python 3.14 `argparse` colorea el `usage` aunque stderr sea un `StringIO`, y `assertIn("usage: geoagent-agent", ...)` fallaba (2 subtests).

**Cambio:** `tests/unit/test_smoke.py`, clase `TestEntryPoints`: `setUp` aplica `mock.patch.dict(os.environ, {"PYTHON_COLORS": "0"})` (con `addCleanup`). Cubre también los otros tests de la clase que leen salida de argparse. En 3.13+ `PYTHON_COLORS` prima sobre `FORCE_COLOR`; en 3.9 no tiene efecto. Otros tests (`test_config.py`, `test_models.py`) no comparan salida de argparse. Sin cambios en `src/`.

**Verificación (salida, colores ANSI omitidos en lo posible):**
```
$ FORCE_COLOR=3 make test
140 passed, 510 subtests passed in 0.68s

no tests ran in 0.06s
tests/integration: sin tests todavía (pytest exit 5), se considera OK
$ FORCE_COLOR=3 ./init.sh
── 5. Suites de integración y demo (informativas) ──────
[WARN]  Existe tests/integration/. Ejecuta 'make test-integration' cuando la feature lo requiera.

── 6. Resumen ──────────────────────────────────────────
[OK]    Entorno listo. Puedes empezar a trabajar o cerrar la sesión.
$ env -u FORCE_COLOR make test
140 passed, 510 subtests passed in 0.69s

no tests ran in 0.07s
tests/integration: sin tests todavía (pytest exit 5), se considera OK
$ make lint
.venv/bin/ruff check src tests
All checks passed!
.venv/bin/ruff format --check src tests
18 files already formatted
```
