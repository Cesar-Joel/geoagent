# Cómo contribuir

Este repositorio se desarrolla feature a feature a partir de `feature_list.json`
y siguiendo el flujo descrito en `AGENTS.md` y `docs/specs.md`.

## Entorno local

```bash
make install           # crea .venv/ e instala el paquete en modo editable con extras dev
make format            # formatea con ruff
make lint              # ruff check + ruff format --check
make test              # tests unitarios y de integración
make test-unit         # solo tests/unit
make test-integration  # solo tests/integration
```

Todos los objetivos usan las herramientas de `.venv/`, nunca las del sistema.
Antes de abrir un PR, `./init.sh`, `make lint` y `make test` deben estar en verde.

## Ramas

- Una rama por feature, creada desde `main`.
- Nombre: `feat/<id>-<name>`, donde `<id>` y `<name>` son los campos de la
  feature en `feature_list.json`.
  - Ejemplo: `feat/1-project_scaffold`, `feat/4-agent_local_store`.
- Correcciones que no son una feature de la lista: `fix/<descripción-corta>`.

## Commits

Formato (inspirado en Conventional Commits):

```
<tipo>(<ámbito>): <resumen en imperativo, máx. 72 caracteres>

<cuerpo opcional: qué cambia y por qué>

Refs: feature #<id>
```

- `<tipo>`: `feat`, `fix`, `test`, `docs`, `refactor`, `chore`, `ci`.
- `<ámbito>`: paquete o área afectada (`common`, `agent`, `backend`, `spark`,
  `tools`, `specs`, `ci`, ...).
- Ejemplo: `feat(agent): añade LocalStore con escritura atómica`.
- Commits pequeños y autocontenidos; cada commit deja los tests en verde.

## Pull requests

- **Una feature por PR.** Un PR implementa exactamente una feature de
  `feature_list.json`; no mezcla cambios de otras features ni refactors ajenos.
- El título sigue el formato de commit e incluye el id de la feature.
- La descripción enlaza el spec (`specs/<name>/`) cuando la feature es
  `"sdd": true` y el informe `progress/impl_<name>.md` con la trazabilidad.
- La CI (`.github/workflows/ci.yml`) debe estar en verde para fusionar.
