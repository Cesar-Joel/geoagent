# Borrador del PR: feature 3 `config_system`

> Borrador para el humano, que es quien hace el push y abre el PR. Se borra cuando el PR
> esté abierto. El título y la descripción van en inglés (ver "Idioma" en
> `docs/conventions.md`).

**Rama:** `feat/3-config_system` → `main`

**Título:**

```
feat(common): layered configuration with early validation and masked secrets (#3)
```

**Descripción:**

```markdown
## What it does

Adds `src/geoagent/common/config.py`, the configuration for the agent and the backend:

- `load_agent_config()` and `load_backend_config()`: **environment (`GEOAGENT_*`) > TOML file >
  defaults**. Defaults go through the same validator (an invalid default is reported with
  `(default)`).
- `load_or_exit()` for entry points: writes `invalid configuration: <key>: <reason>` as a single
  line on `stderr` and exits with code 2, no traceback.
- Immutable `AgentConfig` and `BackendConfig` dataclasses. `repr()`, `str()` and
  `to_safe_dict()` mask the secrets (`auth_token`, `api_token`, `queue_password`) and the query
  values of `queue_url`.

Keys, environment variables and validation rules are listed in `docs/config.md`.

## Validation

- **Secrets:** environment only. A secret in the TOML file is rejected, and the error names the
  variable to use instead.
- **URLs:** no embedded credentials, no fragment, and no `;` in the host or path (`%3B` is
  fine). `backend_url` also rejects a query and requires http(s). Port between 1 and 65535.
- **Backend `host`:** an IP address without brackets or zone, or a valid DNS name. Ambiguous
  forms that the system would resolve to another address (`127.1`, `0x7f.0x1`, `010.0.0.1`) are
  rejected, even with the lenient `ipaddress` of Python 3.9.0-3.9.4 (CVE-2021-29921).
- **Numbers:** ASCII digits only (no `_`, no Unicode digits), finite and greater than 0.
- **Text, paths and secrets:** printable only (`str.isprintable()`): no control characters,
  BOM, NBSP, RLO or line separators.
- **Config file:** `str` or `os.PathLike`. Typed errors for a missing file, a directory, invalid
  TOML, non-UTF-8 content, excessive nesting or a NUL in the path. `GEOAGENT_CONFIG_FILE` set but
  empty is an error; unset, the environment and defaults are loaded.

## Errors that do not leak

No error repeats a value that may be a secret. Numeric errors repeat the value only if it is
printable ASCII, truncated to 40 characters. The config file path and unknown TOML keys are
shown only if printable, so a name containing `\n` cannot forge a log line. Long paths are
truncated from the start so the file name stays visible. TOML errors keep
`(at line L, column C)`.

## Tests

`tests/unit/test_config.py`: **155 passed, 2146 subtests** (whole unit suite).

- One table of valid and invalid cases per validation type. Every row runs against both
  loaders and both sources, and checks the exact value and type, the key named in the error,
  the **rejection reason** and that the value is not echoed.
- `test_every_field_is_classified` fails if a new dataclass field is missing from the tables.
- Mutation-checked: changing any of the 36 reason messages in `config.py` makes a test fail.

`make lint test` and `./init.sh` pass.

## Other changes on this branch

- `fix(tests)`: `tests/unit/test_smoke.py` sets `PYTHON_COLORS=0` in `TestEntryPoints`. With
  `FORCE_COLOR` set, Python 3.14 colors the `argparse` usage even when writing to a `StringIO`,
  so two subtests failed depending on the environment (`progress/fix_smoke_color.md`).
- `chore(harness)`: persistent "Notas para features futuras" (`AGENTS.md` §5 bis), Python 3.9
  locally (`docs/verification.md`), and the `sesion-preguntas` and `pausar-sesion` skills.
- `chore(progress)`: closes the feature 2 session.

## Process

Thirteen implementer/reviewer rounds, with three Q&A sessions with the human. Details in
`progress/impl_config_system.md`, `progress/review_config_system.md` and
`progress/questions_config_system.md` (in Spanish). Recommendations for other features (5, 7, 9,
11, 19, 20, 24 and 25) are under "Notas para features futuras" in `progress/current.md`.

## Out of scope

- Confirming the `tomli` branch and port parsing on a real Python 3.9. The CI 3.9 matrix
  covers part of it. Tracked as a note for feature 25.

Refs: feature #3

🤖 Generated with [Claude Code](https://claude.com/claude-code)

https://claude.ai/code/session_01MdppzQsTT1EabQDZUVCsZt
```
