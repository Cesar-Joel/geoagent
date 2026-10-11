# Borrador del PR: feature 3 `config_system`

> Borrador para el humano, que es quien hace el push y abre el PR. Se borra cuando el PR
> esté abierto.

**Rama:** `feat/3-config_system` → `main`

**Título:**

```
feat(common): configuración por capas con validación temprana y secretos enmascarados (#3)
```

**Descripción:**

```markdown
## Qué hace

Añade `src/geoagent/common/config.py`, la configuración de agente y backend:

- `load_agent_config()` y `load_backend_config()`: **entorno (`GEOAGENT_*`) > archivo TOML >
  valores por defecto**. Los valores por defecto pasan por el mismo validador (si uno es
  inválido, el error lo marca con `(default)`).
- `load_or_exit()`: para los puntos de entrada. Escribe `invalid configuration: <clave>: <motivo>`
  en una sola línea de `stderr` y sale con código 2, sin traceback.
- Dataclasses inmutables `AgentConfig` y `BackendConfig`. `repr()`, `str()` y `to_safe_dict()`
  enmascaran los secretos (`auth_token`, `api_token`, `queue_password`) y los valores de la query
  de `queue_url`.

Mapa de claves, variables y reglas de validación en `docs/config.md`.

## Validación

- **Secretos:** solo por variable de entorno. En el TOML se rechazan y el error indica qué
  variable usar.
- **URL:** sin credenciales embebidas ni fragmento, y sin `;` en el host ni en el path (`%3B`
  sí). `backend_url` rechaza además la query y exige http(s). Puerto entre 1 y 65535.
- **`host` del backend:** una IP sin corchetes ni zona, o un nombre DNS válido. Se rechazan
  las formas ambiguas que el sistema resolvería a otra IP (`127.1`, `0x7f.0x1`, `010.0.0.1`),
  incluso con el `ipaddress` permisivo de Python 3.9.0-3.9.4 (CVE-2021-29921).
- **Números:** solo dígitos ASCII (sin `_` ni dígitos Unicode), finitos y mayores que 0.
- **Texto, rutas y secretos:** imprimibles (`str.isprintable()`): sin caracteres de control,
  BOM, NBSP, RLO ni separadores de línea.
- **Archivo:** `str` u `os.PathLike`. Errores tipados para un archivo inexistente, un
  directorio, TOML inválido, un archivo que no es UTF-8, anidamiento excesivo o un NUL en la ruta.
  `GEOAGENT_CONFIG_FILE` definida pero vacía es un error. Sin definir, se carga entorno + valores
  por defecto.

## Errores sin fugas

Ningún error repite un valor que pueda ser secreto. Los numéricos repiten el valor solo si es
ASCII imprimible, y truncado a 40 caracteres. La ruta del archivo y las claves TOML desconocidas
se muestran solo si son imprimibles, así que un nombre con `\n` no puede falsificar una línea de
log. Las rutas largas se truncan por el principio, para que se vea el nombre del archivo. Los
errores de TOML conservan `(at line L, column C)`.

## Tests

`tests/unit/test_config.py`: **155 passed, 2146 subtests** (toda la suite unitaria).

- Una tabla de casos válidos e inválidos por tipo de validación. Cada fila se prueba en los dos
  loaders y desde las dos fuentes, y comprueba el valor y el tipo exacto, la clave nombrada, el
  **motivo** del rechazo y que el error no repite el valor.
- `test_every_field_is_classified` falla si un campo nuevo de las dataclasses no está en las
  tablas.
- Mutaciones: cambiar cualquiera de los 36 textos de motivo de `config.py` hace fallar algún
  test.

`make lint test` y `./init.sh` en verde.

## Otros cambios en la rama

- `fix(tests)`: `tests/unit/test_smoke.py` fija `PYTHON_COLORS=0` en `TestEntryPoints`. Con
  `FORCE_COLOR` definido, Python 3.14 colorea el `usage` de `argparse` aunque la salida sea un
  `StringIO`, y dos subtests fallaban según el entorno (`progress/fix_smoke_color.md`).
- `chore(harness)`: "Notas para features futuras" persistentes (`AGENTS.md` §5 bis), Python 3.9
  en local (`docs/verification.md`) y las skills `sesion-preguntas` y `pausar-sesion`.
- `chore(progress)`: cierre de la sesión de la feature 2.

## Proceso

Trece rondas de implementer y reviewer, con tres sesiones de preguntas del humano. Detalle en
`progress/impl_config_system.md`, `progress/review_config_system.md` y
`progress/questions_config_system.md`. Las recomendaciones para otras features (5, 7, 9, 11, 19,
20, 24 y 25) están en "Notas para features futuras" de `progress/current.md`.

## Pendiente fuera de este PR

- Confirmar la rama `tomli` y el comportamiento de los puertos con un Python 3.9 real. La
  matriz 3.9 de la CI lo cubre en parte. Nota en la feature 25.

Refs: feature #3

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01MdppzQsTT1EabQDZUVCsZt
```
