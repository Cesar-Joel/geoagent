# Implementación — feature 2 `core_domain_models`

> Ejecutado por el subagente `implementer` a partir de `specs/core_domain_models/`
> (requirements.md, design.md, tasks.md), aprobado por el humano el 2026-09-24
> con las decisiones D1–D11 tal como estaban redactadas.

## Archivos creados

- `src/geoagent/common/errors.py` — `GeoAgentError`, `ValidationError`,
  `UnknownSchemaVersionError` (design §3, sin desviaciones).
- `src/geoagent/common/models.py` — `SCHEMA_VERSION`, `SUPPORTED_SCHEMA_VERSIONS`,
  `JobStatus`, `FailureCause`, `can_transition`, los seis modelos
  (`JobSpec`, `Job`, `JobProgress`, `JobResult`, `AgentInfo`, `Heartbeat`) con
  `__post_init__`, `to_dict()`, `from_dict()`, y los helpers privados de
  validación/serialización descritos en design §5–§8.
- `tests/unit/test_errors.py` — `TestErrorHierarchy` (9 tests).
- `tests/unit/test_models.py` — 12 clases de test. Tras la ronda 2:
  92 tests (141 subtests agregados vía `subTest`, ver más abajo).

## Archivos modificados

- `specs/core_domain_models/tasks.md` — las 20 tasks marcadas `[x]`.
- `progress/current.md` — bitácora de la sesión del implementer.

No se tocó `pyproject.toml`, `Makefile`, `init.sh`, CI, `docs/` ni
`src/geoagent/common/__init__.py`, tal como fija design §2.

## Mapeo tasks → código

| Task | Código |
|------|--------|
| T1 | `src/geoagent/common/errors.py` completo |
| T2 | `tests/unit/test_errors.py::TestErrorHierarchy` |
| T3 | `models.py`: `SCHEMA_VERSION`, `SUPPORTED_SCHEMA_VERSIONS`, `JobStatus`, `FailureCause`, `_VALID_TRANSITIONS`, `can_transition` |
| T4 | `test_models.py::TestJobStatus`, `TestFailureCause`, `TestCanTransition` |
| T5 | `models.py`: `_require_str`, `_require_optional_str`, `_require_int`, `_require_number`, `_require_enum`, `_parse_enum`, `_str_tuple`, `_number_tuple`, `_number_mapping`, `_check_version`, `_check_payload`, `_join` |
| T6 | `models.py`: `_require_datetime`, `_format_timestamp`, `_parse_timestamp`, `_TIMESTAMP_RE` |
| T7 | `models.py`: clases `JobSpec` y `JobProgress` |
| T8 | `models.py`: clase `Job` (incluye `_reraise_nested` para rutas anidadas `spec.*`) |
| T9 | `models.py`: clase `JobResult` |
| T10 | `models.py`: clases `AgentInfo` y `Heartbeat` |
| T11 | `test_models.py::TestModelFields` |
| T12 | `test_models.py::TestImmutability` |
| T13 | `test_models.py::TestRoundTrip` |
| T14 | `test_models.py::TestSchemaVersion` |
| T15 | `test_models.py::TestTimestamps` |
| T16 | `test_models.py::TestPayloadValidation` |
| T17 | `test_models.py::TestJobProgressBoundaries`, `TestJobResultBoundaries`, `TestJobSpecBoundary` |
| T18 | Revisión manual (`grep`) — sin `print()`, `get_type_hints`, `fromisoformat`, `datetime.UTC`, `StrEnum`, `match` statement, `slots=`, `kw_only=` |
| T19 | Este documento |
| T20 | `make lint` y `./init.sh` verdes (ver más abajo); sin Python 3.9 local disponible en este entorno — la matriz 3.9/3.14 de CI queda como verificación de compatibilidad pendiente de esa pipeline |

## Trazabilidad R<n> → test

| Req. | Test(s) |
|------|---------|
| R1 | `TestModelFields` (las 6 clases existen con los campos del Anexo A) |
| R2 | `test_errors.py::TestErrorHierarchy::test_validation_error_is_subclass_of_geoagent_error`, `test_geoagent_error_is_direct_subclass_of_exception` |
| R3 | `test_errors.py::TestErrorHierarchy::test_unknown_schema_version_error_is_subclass_of_validation_error`, `test_unknown_schema_version_error_has_model_version_and_field` |
| R4 | `test_errors.py::test_validation_error_has_message_and_field`; `test_models.py::TestSchemaVersion::test_job_from_dict_rejects_unknown_nested_spec_version`; `TestPayloadValidation::test_missing_key_inside_spec_reports_prefixed_field`, `test_non_mapping_nested_spec_raises_with_field_spec`, `test_unknown_key_top_level_and_nested_raise_with_path` |
| R5 | `TestImmutability::test_*_is_frozen` (6 modelos; `_assert_frozen` verifica además que el atributo queda sin cambios tras `setattr`/`delattr`, ronda 2) |
| R6 | `TestImmutability::test_mutating_list_argument_does_not_affect_instance`, `test_mutating_dict_argument_does_not_affect_instance`, `test_collection_fields_are_tuples` (incluye `Heartbeat.running_job_ids`, ronda 2), `test_mapping_field_rejects_item_assignment` (incluye `Heartbeat.resource_usage`, ronda 2), `test_heartbeat_mutating_arguments_does_not_affect_instance` (ronda 2) |
| R7 | `TestJobStatus::test_exact_values` |
| R8 | `TestCanTransition::test_all_36_pairs` (10 pares `True`) |
| R9 | `TestCanTransition::test_all_36_pairs` (26 pares `False`, incluidas autotransiciones y salidas de estado terminal) |
| R10 | `TestJobStatus::test_is_terminal` |
| R11 | `TestCanTransition::test_invalid_arguments_raise_validation_error` |
| R12 | `TestFailureCause::test_exact_values` |
| R13 | `TestModelFields` (`schema_version` default `SCHEMA_VERSION` en las 6 clases) |
| R14 | `TestRoundTrip::test_to_dict_keys_match_annex_a`, `test_to_dict_values_are_json_types`, `test_to_dict_returns_new_dict_each_call` |
| R15 | `TestRoundTrip::test_enum_fields_serialize_as_value` |
| R16 | `TestRoundTrip::test_job_to_dict_spec_matches_jobspec_to_dict` |
| R17 | `TestRoundTrip::test_*_round_trip*` (9 tests, uno por variante de cada modelo) |
| R18 | `TestSchemaVersion::test_from_dict_rejects_unknown_versions`, `test_unknown_version_wins_even_with_missing_fields`, `test_unknown_version_wins_even_with_extra_keys`, `test_job_from_dict_rejects_unknown_nested_spec_version`, `test_from_dict_rejects_unknown_version_for_every_model` (los 6 modelos, ronda 2) |
| R19 | `TestSchemaVersion::test_constructor_rejects_unknown_version`, `test_constructor_rejects_unknown_version_for_every_model` (los 6 modelos, ronda 2) |
| R20 | `TestSchemaVersion::test_from_dict_missing_schema_version_raises_validation_error`, `test_from_dict_invalid_schema_version_types_raise_validation_error`, `test_from_dict_missing_schema_version_for_every_model` (los 6 modelos, ronda 2) |
| R21 | `TestTimestamps::test_serializes_with_microseconds_and_z_suffix`, `test_serializes_year_below_1000_padded`, `test_serializes_nonzero_microseconds` (`123456` µs, ronda 2) |
| R22 | `TestTimestamps::test_constructor_normalizes_offset_to_utc` |
| R23 | `TestTimestamps::test_from_dict_accepts_various_fractions_and_offsets` (ronda 2: cada caso compara el `datetime` UTC y el `microsecond` esperados, no solo el `tzinfo`) |
| R24 | `TestPayloadValidation::test_every_field_wrong_type_raises_with_field` (test de conexión generado por introspección de `dataclasses.fields()`; para el tipo `'datetime'` el valor inválido de la tabla es un `datetime` naive, así que este único test cubre a la vez la conexión y el rechazo de naive en los 5 campos `datetime` — `JobSpec.time_start`, `JobSpec.time_end`, `Job.created_at`, `JobResult.finished_at`, `Heartbeat.sent_at` — sustituye a `test_constructor_rejects_naive_datetime` de la ronda 3, ronda 4/M7), `TestTimestamps::test_constructor_rejects_datetime_whose_tzinfo_utcoffset_is_none` (segundo término de "naive" del glosario, `tzinfo` con `utcoffset() is None`, test de lógica, ronda 3, sin cambios) |
| R25 | `TestTimestamps::test_from_dict_rejects_invalid_timestamp_strings` (sin zona, `z` minúscula, espacio, 7 dígitos, mes 13, hora 25, offset `+24:00`, offset `+05:60`/`+00:99` con minutos ≥ 60 —ronda 2—, dígito no ASCII, no-`str`, sobre `JobSpec.time_start`), `test_from_dict_rejects_unzoned_string_for_every_datetime_field` (`subTest` sobre los 5 campos de los 4 modelos, ronda 3), `test_from_dict_rejects_datetime_object_instead_of_string` (`subTest` con objeto `datetime` naive y objeto `datetime` **aware**, no `str`, sobre `JobSpec.time_start` — ronda 3, ampliado en ronda 3 bis/N1 para cubrir también el caso aware), `test_job_from_dict_rejects_unzoned_nested_spec_time_start` (`field == "spec.time_start"`, ronda 3) |
| R26 | `TestPayloadValidation::test_non_mapping_payload_raises_with_field_none`, `test_non_mapping_nested_spec_raises_with_field_spec` |
| R27 | `TestPayloadValidation::test_missing_required_key_raises_validation_error`, `test_missing_key_inside_spec_reports_prefixed_field`, `test_missing_required_key_for_every_model_and_key` (`subTest` sobre los 6 modelos × cada clave obligatoria, ronda 2), `test_missing_required_keys_report_first_in_annex_a_order_for_every_model` (recorre, para cada modelo, cada índice `i` de `_REQUIRED_KEYS_BY_MODEL[model]` y borra el sufijo `keys[i:]`, comprobando `field == keys[i]`; detecta cualquier permutación de la tupla `required` de `from_dict()`, algo que borrar una sola clave no puede detectar — sustituye a `test_missing_required_key_reports_first_in_annex_a_order`, redundante porque solo cubría un par de claves de `JobSpec` — P1, ronda 4 quater), `TestModelFields::test_required_keys_by_model_matches_annex_a_order` (guarda de que `_REQUIRED_KEYS_BY_MODEL` coincide, en el mismo orden, con los campos no opcionales de `fields(model)` sin `schema_version` — P1, ronda 4 quater) |
| R28 | `TestRoundTrip::test_from_dict_without_optional_key_yields_none` (test de conexión generado por introspección sobre los campos cuyo tipo termina en `\| None` —`Job.assigned_agent_id`, `AgentInfo.agent_id`, `JobResult.failure_cause`—: construye el payload con la fábrica, **elimina la clave** y comprueba que `from_dict()` produce `None` en ese campo; detecta un `payload[...]` en vez de `payload.get(...)` en cualquiera de los 3 campos — ronda 4 ter, N2), `TestPayloadValidation::test_optional_fields_accept_none` (los mismos 3 campos aceptan `None` explícito en el constructor, coherente con el Anexo A — ronda 4, M7, realineado en ronda 4 bis, m3) |
| R29 | `TestPayloadValidation::test_wrong_type_in_constructor_raises_with_field` (con aserción de `field` en cada caso, ronda 2), `test_wrong_type_in_from_dict_raises_with_field` (casos vía `from_dict`, ronda 2), `test_wrong_type_in_nested_spec_reports_prefixed_field` (`spec.region`, ronda 2), `test_every_field_wrong_type_raises_with_field` (test de conexión generado por introspección: recorre `dataclasses.fields()` de los 6 modelos —excepto `schema_version`— con un valor inválido por tipo de `_INVALID_VALUE_BY_TYPE`, `field` correcto en los 30 campos incluido `JobResult.failure_cause`, que necesita el contexto `status=JobStatus.FAILED` de `_FIELD_CONTEXT` para alcanzar de verdad `_require_enum` en vez de la regla de coherencia R34 — ronda 4, M7, enfoque revisado; M8 corregido en ronda 4 bis, ver más abajo) |
| R30 | `TestPayloadValidation::test_constraint_violations` (ronda 2: añade `nan` en `region`/`metrics` e `inf` en `region`/`metrics`, las 4 combinaciones), `test_str_fields_reject_empty_string_unless_excepted` (recorre por introspección los 14 campos `str`/`str \| None`; `""` se rechaza salvo `("JobProgress", "message")`, la única excepción de `_EMPTY_STRING_EXCEPTIONS`, con guarda de que esa excepción existe) — ronda 4, M7, enfoque revisado |
| R31 | `TestPayloadValidation::test_unknown_enum_value_raises_validation_error_for_every_enum_field` (test de conexión generado por introspección sobre los campos cuyo `f.type` es `"JobStatus"` o `"FailureCause \| None"` — `Job.status`, `JobResult.status` y `JobResult.failure_cause` —, con la cadena `"paused"` y el contexto de `_FIELD_CONTEXT` aplicado sobre el propio payload para `failure_cause`; sustituye a la versión manual, que solo cubría `Job.status` y `JobResult.failure_cause` y no detectaba un `field` mal copiado en `_parse_enum` de `JobResult.status` — P2, ronda 4 quater) |
| R32 | `TestJobProgressBoundaries::test_percent_out_of_range_or_nan_raises`, `test_percent_boundaries_are_valid`, `test_percent_int_normalized_to_float` |
| R33 | `TestJobResultBoundaries::test_status_other_than_succeeded_or_failed_raises`, `test_status_other_than_succeeded_or_failed_raises_via_from_dict` (ronda 2; ambos recorren QUEUED/RUNNING/CANCELLED vía `_BAD_STATUSES` compartida) |
| R34 | `TestJobResultBoundaries::test_failed_without_cause_raises`, `test_succeeded_with_cause_raises` |
| R35 | `TestPayloadValidation::test_unknown_key_top_level_and_nested_raise_with_path`, `test_unknown_keys_with_mixed_types_do_not_raise_type_error` (regresión de m1, ronda 2), `test_unknown_key_raises_validation_error_for_every_model` (`"zz_unknown"` en cada uno de los 6 modelos — P3, ronda 4 quater). El test espía `test_check_payload_admits_exactly_the_annex_a_keys` se eliminó en D12 (T23): desde D12 las claves admitidas salen de `_payload_keys(cls)` y una tupla desincronizada es imposible por construcción |
| R36 | `TestJobSpecBoundary::test_time_end_before_time_start_is_allowed`, `test_region_any_length_including_empty_is_allowed`, `test_unknown_operation_is_allowed` |

## Acceptance (feature 2) → evidencia

| # | Criterio | Evidencia |
|---|----------|-----------|
| 1 | Modelos con inmutabilidad/copias de solo lectura | `models.py` (6 dataclasses frozen); `TestImmutability` |
| 2 | `JobStatus` + `can_transition` rechaza transiciones inválidas | `models.py::JobStatus/can_transition`; `TestJobStatus`, `TestCanTransition` |
| 3 | `to_dict`/`from_dict`/`schema_version` con rechazo de versión desconocida | `TestRoundTrip`, `TestSchemaVersion` |
| 4 | Timestamps ISO 8601 UTC con `Z` | `TestTimestamps` |
| 5 | Validación de dominio propia, no `KeyError`/`TypeError` | `TestPayloadValidation`, `TestJobProgressBoundaries`, `TestJobResultBoundaries`, `TestJobSpecBoundary` |
| 6 | `tests/unit/test_models.py` cubre round-trip, versión, transiciones y campos faltantes | Ver tabla de trazabilidad arriba |

## Desviaciones del spec

Ninguna. Todas las decisiones D1–D11 se implementaron tal como aprobó el
humano (alcance mínimo de `errors.py`, herencia `UnknownSchemaVersionError <
ValidationError`, conjunto de campos de design §4, `region` como secuencia
sin aridad fija, `FailureCause` con 7 valores, `Heartbeat.status` como `str`
libre, `can_transition` sin lanzar por transición inválida, `assigned →
cancelled` válida, un único `SCHEMA_VERSION` compartido, claves
desconocidas como error, offsets `±HH:MM` aceptados al leer). Un ajuste
menor no normativo: se añadió el helper privado `_join` (no listado
explícitamente en design §5) para componer rutas `padre.campo` de forma
reutilizable entre `_check_payload` y los mensajes de error; es un detalle
de implementación interno, no cambia ningún comportamiento observable ni
ninguna decisión D.

**Enmienda D12 (aplicada tras la aprobación inicial).** Se aplicó D12 (`specs/core_domain_models/
design.md` §5): `_check_payload(cls, data, path=None)` deriva `required`/`optional` de
`dataclasses.fields(cls)` vía el helper privado `_payload_keys(cls)` (orden de declaración, excluye
`schema_version` por nombre, opcional si `f.default is None`; no toca `f.type`). Aprobada por el
humano a partir de la opción D1 de "Ronda 4 quater" en `progress/review_core_domain_models.md`.
Se cierra la nota m2 de esa ronda (acoplamiento del test espía al nombre y la firma de
`_check_payload`): el test `test_check_payload_admits_exactly_the_annex_a_keys` se eliminó (T23)
y la advertencia ya no aplica, porque no quedan tuplas escritas a mano que sincronizar ni
llamadas que espiar; los refactors RF1–RF3 ya no rompen ningún test (ver "Ronda D12").

## Verificación (ronda 1)

- `make test-unit` → **82 passed, 87 subtests passed** (0.4s).
- `make lint` (`ruff check` + `ruff format --check`) → **sin errores**
  (tras aplicar `make format` para homogeneizar el estilo).
- `./init.sh` → **`[OK] Entorno listo`** (exit 0).
- Python 3.9: no hay intérprete 3.9 disponible en este entorno de
  ejecución (`command -v python3.9` no encuentra nada). Se revisó
  manualmente (T18) que `models.py`/`errors.py` no usan ninguna construcción
  exclusiva de 3.10+/3.11+ (`isinstance` con tuplas en vez de `X | Y`,
  sin `match`, sin `StrEnum`, sin `datetime.UTC`, sin `slots=`/`kw_only=`,
  sin `datetime.fromisoformat`). La verificación de compatibilidad real
  con 3.9 queda pendiente de la matriz 3.9/3.14 de CI, como prevé la task
  T20 cuando no hay intérprete local.

## Ronda 2 — respuesta a review

Input: `progress/review_core_domain_models.md` (veredicto `CHANGES_REQUESTED`).
Alcance de esta ronda según el leader: M1–M4 obligatorios, m1–m6 (corregir o
justificar), m7/m8 fuera de alcance (los gestiona el leader), n1–n4 opcionales
si son triviales. Solo se tocó `src/geoagent/common/` y `tests/unit/`; sin
commits; `feature_list.json` no se tocó.

### Mayores (bloqueantes)

- **M1 — offsets con minutos ≥ 60 aceptados (R25).** Corregido en
  `_parse_timestamp` (`src/geoagent/common/models.py`): tras extraer
  `hours`/`minutes` del offset, se rechaza explícitamente `minutes >= 60`
  con `ValidationError(field=field)` antes de construir el `timedelta`.
  Verificado manualmente que `"+05:60"` y `"+00:99"` ya no se aceptan.
  Test: se añadieron los casos `"...+05:60"` y `"...+00:99"` a
  `TestTimestamps::test_from_dict_rejects_invalid_timestamp_strings`.
- **M2 — el test de R23 no verificaba el instante.** Reescrito
  `TestTimestamps::test_from_dict_accepts_various_fractions_and_offsets`:
  cada caso ahora es una tupla `(cadena, datetime_utc_esperado)` y el test
  compara `spec.time_start` (instante completo) y `.microsecond` contra el
  valor esperado, además de `tzinfo is timezone.utc`. Cubre `-05:30` → mismo
  instante que `10:00Z`, y fracciones `.5` → `500000` µs, `.123` → `123000`
  µs, `.123456` → `123456` µs.
- **M3 — el test de R29 no verificaba `field` ni ejercitaba `from_dict`.**
  Dividido en tres tests en `TestPayloadValidation`:
  `test_wrong_type_in_constructor_raises_with_field` (7 casos, cada uno con
  `subTest` y aserción de `ctx.exception.field`),
  `test_wrong_type_in_from_dict_raises_with_field` (4 casos vía `from_dict`)
  y `test_wrong_type_in_nested_spec_reports_prefixed_field` (`Job.from_dict`
  con `spec.region = [True]` → `field == "spec.region"`, refuerza R4).
- **M4 — T16 no recorría los 6 modelos × cada clave obligatoria.** Añadido
  `TestPayloadValidation::test_missing_required_key_for_every_model_and_key`:
  itera con `subTest(model=..., key=...)` sobre `_REQUIRED_KEYS_BY_MODEL`
  (las claves obligatorias de cada modelo según el Anexo A, sin
  `schema_version`) y comprueba que eliminar cada una produce
  `ValidationError(field == key)` vía `from_dict`.

### Menores

- **m1 — `TypeError` con claves desconocidas de tipos mezclados.** Corregido
  en `_check_payload`: `sorted(..., key=str)` en vez de `sorted(...)`, y
  `field=_join(path, str(extra[0]))` para garantizar que `field` sea
  siempre `str`. Test de regresión:
  `TestPayloadValidation::test_unknown_keys_with_mixed_types_do_not_raise_type_error`.
- **m2 — el test de R5 no comprobaba que la instancia quedara sin
  cambios.** `TestImmutability::_assert_frozen` ahora captura el valor
  original del atributo, comprueba que sigue igual tras el intento de
  `setattr` fallido, y que el atributo sigue existiendo con el mismo valor
  tras el intento de `delattr` fallido.
- **m3 — sin test de R21 con microsegundos != 0.** Añadido
  `TestTimestamps::test_serializes_nonzero_microseconds`
  (`123456` µs → `...10:00:00.123456Z`).
- **m4 — R6 no cubría `Heartbeat`.** Añadidas aserciones para
  `Heartbeat.running_job_ids` (es `tuple`) y `Heartbeat.resource_usage`
  (rechaza `__setitem__`) en `TestImmutability::test_collection_fields_are_tuples`
  y `test_mapping_field_rejects_item_assignment`, más un test dedicado
  `test_heartbeat_mutating_arguments_does_not_affect_instance`.
- **m5 — R18/19/20 solo se probaban con `JobSpec`/`Job`.** Añadidos
  `TestSchemaVersion::test_from_dict_rejects_unknown_version_for_every_model`,
  `test_constructor_rejects_unknown_version_for_every_model` y
  `test_from_dict_missing_schema_version_for_every_model`, cada uno con
  `subTest` sobre los 6 modelos (`_MODEL_FACTORIES`), comprobando
  `exc.model == model.__name__` en cada caso.
- **m6 — R30/R33 con casos incompletos.**
  `TestPayloadValidation::test_constraint_violations` ahora prueba las 4
  combinaciones `nan`/`inf` × `region`/`metrics` (antes solo 2). Añadido
  `TestJobResultBoundaries::test_status_other_than_succeeded_or_failed_raises_via_from_dict`
  para el camino `from_dict` de R33 (`"status": "queued"`).
- **m7 (`.gitignore`) y m8 (cobertura/`pytest-cov`):** no tocados en esta
  ronda, conforme a la instrucción explícita del leader — los gestiona el
  leader como cambios fuera del alcance de esta feature / pendiente de
  infraestructura.

### Nits

- **n1** — Eliminados los comentarios-banner (`# ----`) de `models.py` y
  `test_models.py` que solo delimitaban secciones sin explicar un "por qué"
  (`docs/conventions.md` §Comentarios).
- **n2** — `test_geoagent_error_is_subclass_of_exception` reemplazado por
  `test_geoagent_error_is_direct_subclass_of_exception`, que comprueba
  `GeoAgentError.__bases__ == (Exception,)` (subclase *directa*, como pide
  R2 literalmente).
- **n3** — Eliminadas las aserciones redundantes
  `assertNotIsInstance(ctx.exception, KeyError/TypeError)` en
  `test_missing_required_key_raises_validation_error`: ya las garantiza
  `assertRaises(ValidationError)`.
- **n4** — `_reraise_nested` anotado como `-> NoReturn`; eliminado el
  `raise  # pragma: no cover` sobrante en `Job.from_dict`.
- **n5** — Sin cambios (aceptado por el reviewer, ver revisión).

### Verificación (ronda 2)

- `make test-unit` → **92 passed, 141 subtests passed** (0.46s).
- `make lint` (`ruff check` + `ruff format --check`, tras `make format`) →
  **sin errores**.
- `./init.sh` → **`[OK] Entorno listo`** (exit 0).
- Comprobación manual adicional (fuera de pytest) de que `"+05:60"` y la
  clave desconocida de tipo `int` mezclada con `str` ya no rompen con una
  excepción distinta de `ValidationError`.
- `git status --porcelain`: solo cambian `src/geoagent/common/{errors,models}.py`,
  `tests/unit/{test_errors,test_models}.py`, `specs/core_domain_models/tasks.md`
  y `progress/{current,impl_core_domain_models}.md`, más
  `progress/review_core_domain_models.md` (creado por el reviewer, no por
  este agente). `.gitignore` y `feature_list.json` no se tocaron en esta
  ronda.

## Estado

Ronda 2 completa. Tasks T1–T20 siguen marcadas `[x]` en
`specs/core_domain_models/tasks.md` — T6, T12, T15 y T16 estaban marcadas
`[x]` mientras tenían defectos de cobertura/comportamiento señalados por el
reviewer (M1–M4, m2, m3, m4, m6); tras esta ronda esos defectos están
corregidos y las tasks vuelven a reflejar el estado real del trabajo, por lo
que permanecen `[x]`. La feature permanece en `in_progress` en
`feature_list.json` — no se marca `done` (corresponde al leader tras la
revisión del `reviewer`).

## Ronda 3 — respuesta a review

Alcance de esta ronda: solo `tests/unit/test_models.py` (M5 y M6 de "Ronda 3 —
observaciones del leader" en `progress/review_core_domain_models.md`). No se
tocó `src/` porque el comportamiento ya era correcto en los 5 campos
`datetime` — el leader lo comprobó con una sonda manual y esta ronda solo
añade los tests que faltaban.

### M5 — R24: rechazo de naive en el constructor, parametrizado sobre los 5 campos

- `TestTimestamps::test_constructor_rejects_naive_datetime`
  (`tests/unit/test_models.py:555`): reescrito con `subTest` sobre los 5
  pares (fábrica, campo): `make_job_spec(time_start=...)` → `"time_start"`,
  `make_job_spec(time_end=...)` → `"time_end"`, `make_job(created_at=...)` →
  `"created_at"`, `make_job_result(finished_at=...)` → `"finished_at"`,
  `make_heartbeat(sent_at=...)` → `"sent_at"`. Cada caso comprueba
  `ValidationError` con `field` igual al campo.
- `TestTimestamps::test_constructor_rejects_datetime_whose_tzinfo_utcoffset_is_none`
  (`tests/unit/test_models.py:570`): cubre el segundo término de la
  definición de "naive" (`requirements.md:18-19`) — un `tzinfo` distinto de
  `None` cuyo `utcoffset()` devuelve `None`. Se añadió la clase auxiliar
  `_NoneOffsetTzInfo(tzinfo)` (`tests/unit/test_models.py:29`) con
  `utcoffset`/`dst`/`tzname` devolviendo `None`, usada en `JobSpec.time_start`.
  Antes de escribir el test se comprobó manualmente contra `models.py:113`
  (`value.tzinfo is None or value.utcoffset() is None`) que este caso ya se
  rechaza hoy con `field == "time_start"`.

### M6 — R25: rechazo de naive en `from_dict`, los 5 campos y el caso anidado

- `TestTimestamps::test_from_dict_rejects_invalid_timestamp_strings`
  (`tests/unit/test_models.py:576`): sin cambios de fondo; sigue cubriendo
  `JobSpec.time_start` con la cadena sin zona y el resto de gramáticas
  inválidas (ronda 1/2).
- `TestTimestamps::test_from_dict_rejects_unzoned_string_for_every_datetime_field`
  (`tests/unit/test_models.py:598`, nuevo): `subTest` sobre los 5 pares
  (modelo, fábrica, campo) — `JobSpec.time_start`, `JobSpec.time_end`,
  `Job.created_at`, `JobResult.finished_at`, `Heartbeat.sent_at` — pasando la
  cadena `"2026-09-14T10:00:00"` (sin designador de zona) a `from_dict` y
  comprobando `ValidationError` con `field` igual al campo.
- `TestTimestamps::test_from_dict_rejects_naive_datetime_object_instead_of_string`
  (`tests/unit/test_models.py:615`, nuevo en esta ronda): pasa un objeto
  `datetime` naive (no `str`) en `time_start` a `JobSpec.from_dict` y
  comprueba `ValidationError` con `field == "time_start"`. Es el caso que el
  review señaló como el más fácil de "flexibilizar" por error (R25 exige
  rechazar cualquier valor que no sea `str`). Renombrado y ampliado en la
  ronda 3 bis (ver "Ronda 3 bis — N1" más abajo): el objeto naive por sí solo
  no protegía la comprobación de tipo en `_parse_timestamp`, porque el
  constructor lo rechaza igual por ser naive.
- `TestTimestamps::test_job_from_dict_rejects_unzoned_nested_spec_time_start`
  (`tests/unit/test_models.py:623`, nuevo): `Job.from_dict` con
  `spec.time_start` sin zona → `ValidationError` con
  `field == "spec.time_start"` (ruta anidada, refuerza también R4).

### Trazabilidad

Filas R24 y R25 de la tabla "Trazabilidad R<n> → test" actualizadas (ver
arriba) para citar los tests nuevos y parametrizados de esta ronda.

### Ronda 3 bis — N1

Alcance: respuesta a N1 de "Ronda 3 — feature 2 `core_domain_models`" en
`progress/review_core_domain_models.md`. Solo tests; no se tocó `src/`.

- El review detectó que `test_from_dict_rejects_naive_datetime_object_instead_of_string`
  solo probaba un objeto `datetime` **naive**, y ese caso lo rechaza el
  constructor (`_require_datetime`, por ser naive) aunque `_parse_timestamp`
  dejase de exigir `str` (mutación M-j del review). El test no protegía la
  comprobación de tipo que R25 exige en `from_dict` ("cualquier valor que no
  sea `str`").
- Renombrado a `TestTimestamps::test_from_dict_rejects_datetime_object_instead_of_string`
  (`tests/unit/test_models.py:615`) y ampliado con `subTest` a dos casos:
  un objeto `datetime` naive (`datetime(2026, 9, 14, 10, 0, 0)`, caso previo)
  y un objeto `datetime` **aware** (`_dt(2026, 9, 14, 10)`). Ambos se pasan
  en `time_start` a `JobSpec.from_dict` y el test comprueba `ValidationError`
  con `field == "time_start"`. El caso aware es el que faltaba: obliga a que
  `_parse_timestamp` (`models.py:182-183`) siga exigiendo `str` antes de
  delegar en `_require_datetime`, sin depender de que el valor sea también
  naive.
- Fila R25 de la tabla de trazabilidad actualizada para citar el test
  renombrado y el caso aware.

### Observación de la ronda 2 sobre el nombre del test de R2

Revisado: la fila R2 de la tabla de trazabilidad y `tests/unit/test_errors.py:14`
ya citan/usan `test_geoagent_error_is_direct_subclass_of_exception` (no
`test_geoagent_error_is_subclass_of_exception`). No hizo falta ningún cambio;
se deja constancia de la verificación.

### Verificación (ronda 3)

- `make lint` → `ruff check`: **All checks passed!**; `ruff format --check`:
  **16 files already formatted**.
- `make test-unit` → **96 passed, 151 subtests passed** (0.54s).
- Tras la ronda 3 bis: `make test-unit` → **96 passed, 153 subtests passed** (los 2 subtests nuevos son del caso naive y el aware de `test_from_dict_rejects_datetime_object_instead_of_string`).
- `./init.sh` → **`[OK] Entorno listo`** (exit 0).
- Alcance de los cambios: solo `tests/unit/test_models.py` y este archivo
  (`progress/impl_core_domain_models.md`). `src/`, `feature_list.json` y
  `tasks.md` no se tocaron en esta ronda.

## Estado (ronda 3)

M5 y M6 resueltos, solo con tests nuevos/parametrizados. `src/` no se
modificó. La feature permanece en `in_progress` en `feature_list.json` — no
se marca `done` (corresponde al leader tras la revisión del `reviewer`).

## Ronda 4 — respuesta a review

Alcance: M7 de "Ronda 4 — observaciones del leader" de
`progress/review_core_domain_models.md`, con el enfoque revisado de la
subsección "## M7 — enfoque revisado" (sustituye a los "Cambios requeridos"
1-3 originales de M7): los tests de conexión para los campos `str` no se
escriben a mano, se **generan por introspección** de `dataclasses.fields()`,
igual que ya hace `test_missing_required_key_for_every_model_and_key` para
las claves obligatorias. Solo se tocó `tests/unit/test_models.py`; no se
tocó `src/` porque el comportamiento ya era correcto.

### M7 — R29/R30: tests de conexión generados por introspección

- `_INVALID_VALUE_BY_TYPE` (`tests/unit/test_models.py`, junto a
  `_REQUIRED_KEYS_BY_MODEL`): tabla `f.type` (cadena, gracias a
  `from __future__ import annotations`) → valor inválido representativo. No
  se usa `typing.get_type_hints`. Cubre los 11 tipos que aparecen en los 6
  modelos: `'str'` (123), `'str | None'` (123), `'tuple[float, ...]'`
  (`"not-a-tuple"`), `'tuple[str, ...]'` (`"not-a-list"`), `'datetime'` (un
  `datetime` **naive**), `'JobSpec'` (`"not-a-jobspec"`), `'JobStatus'`
  (`"queued"`), `'float'` (`"not-a-number"`), `'int'` (`1.5`),
  `'Mapping[str, float]'` (`"not-a-mapping"`) y `'FailureCause | None'`
  (123). El valor de `'datetime'` es naive a propósito: además de probar la
  conexión, ejercita el rechazo de naive (R24) en los 5 campos `datetime`
  sin repetir un test por campo (ver más abajo).
- `_EMPTY_STRING_EXCEPTIONS = {("JobProgress", "message")}`: la única
  excepción semántica a "`str` no vacía" del Anexo A.
- `_iter_model_fields()`: recorre los 6 modelos (`_MODEL_FACTORIES`) y sus
  `dataclasses.fields()`, excluyendo `schema_version` (tiene sus propios
  tests en `TestSchemaVersion`).
- `TestPayloadValidation::test_every_field_wrong_type_raises_with_field`
  (nuevo): para cada uno de los 30 campos (6 modelos × sus campos, sin
  `schema_version`), busca el valor inválido de `_INVALID_VALUE_BY_TYPE`
  según `f.type` y comprueba `ValidationError` con `field == f.name` por el
  constructor. **Guarda de completitud:** si `f.type` no está en la tabla,
  `self.fail(f"tipo sin clasificar: {model}.{field}: {f.type}")` — un campo
  nuevo de un tipo nuevo obliga a decidir cómo se valida antes de que el
  test pueda pasar.
- `TestPayloadValidation::test_optional_fields_accept_none` (nuevo): para
  cada campo cuyo `f.type` termina en `"| None"` (`Job.assigned_agent_id`,
  `AgentInfo.agent_id`, `JobResult.failure_cause`), comprueba que `None` se
  acepta y que el atributo queda en `None`.
- `TestPayloadValidation::test_str_fields_reject_empty_string_unless_excepted`
  (nuevo): para cada campo cuyo `f.type` es `'str'` o `'str | None'` (14 en
  total), comprueba que `""` se rechaza con `field == f.name`, salvo que
  `(modelo, campo)` esté en `_EMPTY_STRING_EXCEPTIONS`, en cuyo caso
  comprueba que `""` se acepta. **Guarda de que la lista de excepciones no
  queda obsoleta:** acumula en un `set` las claves de la excepción que
  realmente se visitan durante el recorrido y, al final,
  `self.assertFalse(_EMPTY_STRING_EXCEPTIONS - visitadas, ...)` — si alguien
  añade una excepción para un `(modelo, campo)` que no existe o no es
  `str`/`str | None`, el test falla.
- Se eliminó `TestTimestamps::test_constructor_rejects_naive_datetime`
  (ronda 3, M5): quedó redundante porque `test_every_field_wrong_type_raises_with_field`
  ya cubre los mismos 5 campos con un `datetime` naive como valor inválido
  de tipo `'datetime'`. `test_constructor_rejects_datetime_whose_tzinfo_utcoffset_is_none`
  (ronda 3) se mantiene sin cambios: es un test de **lógica** (el segundo
  término de la definición de "naive" del glosario), no de conexión, y basta
  con probarlo en un campo.
- Se mantuvieron sin cambios `test_wrong_type_in_constructor_raises_with_field`,
  `test_wrong_type_in_from_dict_raises_with_field` y
  `test_wrong_type_in_nested_spec_reports_prefixed_field` (ronda 2): no son
  redundantes con el test generado porque ejercitan valores inválidos
  distintos y semánticamente relevantes para R29 (`None` en un obligatorio,
  `bool` en un campo numérico, `float` en `observation_count`, el camino
  `from_dict` y la ruta anidada `spec.region`), y el punto 4 de M7 fija que
  el camino `from_dict` de los 14 campos `str` no necesita test propio.
- `TestJobSpecBoundary`, `TestJobProgressBoundaries`, `TestJobResultBoundaries`
  y los demás tests de lógica (gramática de timestamps, `nan`/`inf`,
  límites de `percent`, coherencia `status`/`failure_cause`) no se
  modificaron, conforme al enfoque revisado ("los tests de lógica se quedan
  como están").

### Por qué la introspección resuelve el problema de fondo de M7

Antes de esta ronda, la cobertura de conexión de los campos `str` dependía de
una lista escrita a mano que un campo nuevo podía dejar desactualizada sin
que ningún test lo notara. Ahora, un campo `str` nuevo en cualquiera de los
6 modelos queda cubierto por `test_every_field_wrong_type_raises_with_field`
y por `test_str_fields_reject_empty_string_unless_excepted` sin tocar el
test (porque `'str'` ya está clasificado en `_INVALID_VALUE_BY_TYPE`), y un
campo de un tipo verdaderamente nuevo hace fallar la guarda de completitud
con un mensaje explícito en vez de pasar en silencio.

### Verificación manual antes de escribir los tests

Antes de codificar el test genérico, comprobé con un script de solo lectura
(sin tocar `src/`) que `dataclasses.fields()` produce, con
`from __future__ import annotations`, exactamente las cadenas de tipo
esperadas para los 6 modelos (`'str'`, `'str | None'`,
`'tuple[float, ...]'`, `'datetime'`, `'JobSpec'`, `'JobStatus'`, `'float'`,
`'int'`, `'Mapping[str, float]'`, `'tuple[str, ...]'`,
`'FailureCause | None'`), y que cada valor inválido propuesto en
`_INVALID_VALUE_BY_TYPE` produce `ValidationError` con el `field` esperado
en un campo representativo de cada tipo (incluidos `Job.spec`,
`Job.status`, `JobResult.failure_cause` y los 5 campos `datetime` con un
valor naive). No pude completar una mutación temporal de `src/` (revertida)
como en las rondas 2 y 3 bis: el entorno de ejecución de esta sesión bloquea
cualquier escritura sobre `src/`, incluso temporal. La cobertura por
`subTest` es independiente por campo (sin agregación), así que borrar o
copiar mal cualquiera de las llamadas de validación haría fallar
exactamente el `subTest` de ese campo.

### Trazabilidad

Filas R24, R29 y R30 de la tabla "Trazabilidad R<n> → test" actualizadas
(ver arriba) para citar los tests generados por introspección de esta ronda
y la sustitución de `test_constructor_rejects_naive_datetime`.

### Verificación (ronda 4)

- `make lint` → `ruff check`: **All checks passed!**; `ruff format --check`:
  **16 files already formatted**.
- `make test-unit` → **98 passed, 195 subtests passed** (0.53s). Antes de
  esta ronda: 96 passed, 153 subtests passed. El neto de esta ronda es +2
  tests (+3 nuevos generados por introspección, −1 por la eliminación de
  `test_constructor_rejects_naive_datetime`) y +42 subtests (47 subtests de
  los 3 tests nuevos: 30 + 3 + 14, menos 5 subtests del test eliminado).
- Alcance de los cambios: solo `tests/unit/test_models.py` y este archivo
  (`progress/impl_core_domain_models.md`). `src/`, `feature_list.json` y
  `tasks.md` no se tocaron en esta ronda.

### Ronda 4 bis

Alcance: sección "# Ronda 4 — feature 2 `core_domain_models`" (la del veredicto
`CHANGES_REQUESTED` posterior al enfoque revisado de M7) de
`progress/review_core_domain_models.md`: M8 (bloqueante), la guarda del séptimo
modelo (m1, menor) y la trazabilidad de R28/R29/R30 (m2, m3). Solo se tocó
`tests/unit/test_models.py` y este archivo; no se tocó `src/`.

- **M8 — `JobResult.failure_cause` no llegaba a la comprobación de tipo.**
  Añadida `_FIELD_CONTEXT = {("JobResult", "failure_cause"): {"status":
  JobStatus.FAILED}}` junto a `_EMPTY_STRING_EXCEPTIONS`, con un comentario que
  explica el porqué: con el `status=JobStatus.SUCCEEDED` por defecto de
  `make_job_result`, un valor inválido de `failure_cause` entraba antes en la
  regla de coherencia R34 ("succeeded no admite failure_cause"), que lanza
  `ValidationError(field="failure_cause")` sin pasar por `_require_enum`.
  `test_every_field_wrong_type_raises_with_field` ahora combina
  `_FIELD_CONTEXT.get((model.__name__, f.name), {})` con el valor inválido
  antes de invocar la fábrica, así que el caso de `failure_cause` se construye
  con `status=JobStatus.FAILED` y el valor inválido llega de verdad a
  `_require_enum`. Se añadió una guarda de completitud (mismo patrón que
  `_EMPTY_STRING_EXCEPTIONS`): el test acumula las claves de `_FIELD_CONTEXT`
  que visita durante el recorrido de `_iter_model_fields()` y falla si alguna
  entrada de `_FIELD_CONTEXT` no corresponde a un campo existente.
  `test_optional_fields_accept_none` no se tocó, porque el valor `None` en
  `failure_cause` con `status=JobStatus.SUCCEEDED` (el default) sigue siendo
  válido y no depende del contexto.
  - **Verificación con mutación (solo en una copia, sin escribir en `src/`):**
    se copió `src/` a
    `/tmp/claude-1000/-mnt-c-Users-Usuario-Documents-Cesar-Programacion-ProyectoHarnessSDD-harness-sdd/b6c744c0-2c5e-4ef8-994e-ce8ca70f6ebd/scratchpad/mut2/src`
    y se confirmó con
    `PYTHONPATH=<copia> .venv/bin/python -c "import geoagent.common.models as m; print(m.__file__)"`
    que se cargaba la copia. Se quitó, solo en la copia, la línea
    `failure_cause = _require_enum(failure_cause, FailureCause, "failure_cause")`
    de `JobResult.__post_init__` (la comprobación de tipo de `failure_cause`).
    `PYTHONPATH=<copia> .venv/bin/python -m pytest tests/unit -q` dio
    **1 failed, 99 passed, 194 subtests passed**, con el fallo exacto esperado:
    `SUBFAILED(model='JobResult', field='failure_cause', type='FailureCause | None')
    test_every_field_wrong_type_raises_with_field` → `AssertionError: ValidationError not raised`.
    La mutación queda detectada. Tras la comprobación se borró la copia
    (`rm -rf` del directorio de scratchpad) y se confirmó que `src/` no
    cambió: `sha256sum src/geoagent/common/models.py` da el mismo hash
    (`e8d40b64...fba610`) antes y después, y `git status --porcelain -- src/`
    solo muestra los dos archivos `??` de la feature (`errors.py`,
    `models.py`), sin modificaciones de contenido.
- **m1 — guarda del séptimo modelo.** Añadido
  `TestModelFields::test_model_factories_cover_every_public_dataclass`: calcula
  `{obj for _, obj in inspect.getmembers(models, inspect.isclass) if
  dataclasses.is_dataclass(obj) and obj.__module__ == models.__name__ and not
  obj.__name__.startswith("_")}` y comprueba que coincide con
  `set(_MODEL_FACTORIES)`. Requiere `import dataclasses`, `import inspect` y
  `import geoagent.common.models as models` nuevos en `tests/unit/test_models.py`.
  Hoy los 6 `dataclass` públicos de `models.py` están todos en
  `_MODEL_FACTORIES`, así que el test pasa sin cambios de comportamiento.
- **m2/m3 — trazabilidad de R28/R29/R30.** Fila R29 corregida: ya no afirma sin
  matiz "`field` correcto en los 30 campos" sin explicar `failure_cause`; ahora
  cita que ese campo necesita el contexto `status=JobStatus.FAILED` de
  `_FIELD_CONTEXT` para alcanzar `_require_enum`, y que M8 quedó corregido en
  esta ronda. `test_optional_fields_accept_none` estaba en la fila R30 de la
  tabla, pero su docstring ya decía R28 desde que se escribió en la ronda 4.
  Revisando `specs/core_domain_models/requirements.md`: R30 trata de valores
  del **tipo correcto** que incumplen restricciones ("no vacía", "finito",
  "≥ 0"), y no tiene nada que ver con aceptar `None`; R28 trata justo de los
  campos "marcados como opcional en el Anexo A" (aunque por la vía de
  `from_dict()` sin la clave, no por el constructor con `None` explícito). R28
  es la referencia más cercana, así que se movió la cita de
  `test_optional_fields_accept_none` de la fila R30 a la fila R28 (que ya
  citaba `test_from_dict_without_optional_key_yields_none`), sin tocar el
  docstring del test (ya decía R28). La fila R30 conserva
  `test_constraint_violations` y `test_str_fields_reject_empty_string_unless_excepted`.

### Verificación (ronda 4 bis)

- `make lint` → `ruff check`: **All checks passed!**; `ruff format --check`:
  **16 files already formatted** (tras `ruff format tests/unit/test_models.py`
  para una línea larga en el mensaje de la guarda de `_FIELD_CONTEXT`).
- `make test-unit` → **99 passed, 195 subtests passed** (0.49s). Antes de esta
  ronda: 98 passed, 195 subtests passed. El neto es +1 test
  (`test_model_factories_cover_every_public_dataclass`, sin `subTest`, por lo
  que el número de subtests no cambia) y el mismo `test_every_field_wrong_type_raises_with_field`
  sigue teniendo un subtest por campo (30).
- `./init.sh` → **`[OK] Entorno listo`** (exit 0).
- Alcance de los cambios: solo `tests/unit/test_models.py` y este archivo
  (`progress/impl_core_domain_models.md`). `src/`, `feature_list.json` y
  `specs/core_domain_models/tasks.md` no se tocaron en esta ronda.

## Estado (ronda 4 / ronda 4 bis)

M7 resuelto con el enfoque revisado (tests de conexión generados por
introspección), solo con cambios en tests. Tras la ronda 4 bis, también
quedan resueltos M8 (conexión real de `JobResult.failure_cause` vía
`_FIELD_CONTEXT`, verificada con mutación en una copia), la guarda del
séptimo modelo (m1) y la trazabilidad de R28/R29/R30 (m2, m3). `src/` no se
modificó en ninguna de las dos rondas (verificado con `sha256sum` y
`git status --porcelain`). La feature permanece en `in_progress` en
`feature_list.json` — no se marca `done` (corresponde al leader tras la
revisión del `reviewer`).

### Ronda 4 ter

Alcance: N2 de "# Ronda 4 bis — feature 2 `core_domain_models`" en
`progress/review_core_domain_models.md`. Solo se tocó
`tests/unit/test_models.py` y este archivo; no se tocó `src/`.

- **N2 — R28 solo se verificaba para 1 de los 3 campos opcionales.**
  `TestRoundTrip::test_from_dict_without_optional_key_yields_none`
  (`tests/unit/test_models.py:491`) solo cubría `Job.assigned_agent_id` y
  usaba una `del data["assigned_agent_id"]` escrita a mano. Reescrito con el
  mismo enfoque de introspección de la ronda 4: recorre `_iter_model_fields()`
  y selecciona los campos cuyo `f.type` termina en `"| None"`
  (`Job.assigned_agent_id`, `AgentInfo.agent_id`, `JobResult.failure_cause`).
  Para cada uno, construye `factory().to_dict()`, **elimina la clave** del
  payload (no basta con que valga `None`, que es justo lo que
  `test_optional_fields_accept_none` ya comprueba por el constructor) y
  comprueba que `model.from_dict(data)` produce `None` en ese campo. Incluye
  la guarda `self.assertTrue(optional_fields, "no se encontró ningún campo
  opcional")`.
  - No usa `_FIELD_CONTEXT`: aplicarlo a `("JobResult", "failure_cause")`
    forzaría `status=JobStatus.FAILED`, que exige `failure_cause` distinto de
    `None` (R34) y haría fallar el propio test al eliminar la clave. Las
    fábricas por defecto (`JobResult` con `status=SUCCEEDED`) ya producen
    `None` en los 3 campos opcionales sin necesidad de contexto adicional.
    Queda documentado en un comentario dentro del test.
  - No se toca el sub-payload `spec` de `Job`: ninguno de sus campos
    (`JobSpec`) es opcional en el Anexo A, así que `_iter_model_fields()` no
    genera ningún caso ahí.

#### Verificación con mutación (solo en una copia, sin escribir en `src/`)

- Copia de `src/` en
  `/tmp/claude-1000/-mnt-c-Users-Usuario-Documents-Cesar-Programacion-ProyectoHarnessSDD-harness-sdd/b6c744c0-2c5e-4ef8-994e-ce8ca70f6ebd/scratchpad/mut4/src`.
  Se confirmó que se cargaba la copia:
  `PYTHONPATH=<copia> .venv/bin/python -c "import geoagent.common.models as m; print(m.__file__)"`
  devuelve la ruta de la copia. Sin mutar: 99 passed, 198 subtests passed.
- Mutaciones aplicadas solo en la copia de `models.py` (`sed`, una sola vez,
  sin tocar el original):
  - R28-a: `AgentInfo.from_dict`, `agent_id=payload.get("agent_id")` →
    `agent_id=payload["agent_id"]` (`models.py:512`).
  - R28-b: `JobResult.from_dict`, `failure_cause_raw = payload.get("failure_cause")`
    → `failure_cause_raw = payload["failure_cause"]` (`models.py:456`).
  - Se comprobó con `grep` que no se tocó por error la línea análoga (y
    correcta, porque `Heartbeat.agent_id` es obligatorio) `agent_id=payload["agent_id"]`
    de `Heartbeat.from_dict` (`models.py:562`).
- `PYTHONPATH=<copia> .venv/bin/python -m pytest tests/unit -q` con las dos
  mutaciones aplicadas a la vez: **2 failed, 99 passed, 196 subtests passed**.
  Los dos fallos son exactamente los esperados:
  `SUBFAILED(model='JobResult', field='failure_cause') ...::test_from_dict_without_optional_key_yields_none`
  y `SUBFAILED(model='AgentInfo', field='agent_id') ...::test_from_dict_without_optional_key_yields_none`,
  ambos con `KeyError` sin capturar (no `AssertionError`), lo que también
  confirma que R27/R28 exigen `ValidationError`/`None`, nunca `KeyError`
  crudo.
- Tras la comprobación se borró la copia (`rm -rf` del directorio de
  scratchpad) y se confirmó que `src/` no cambió:
  `sha256sum src/geoagent/common/models.py` da el mismo hash
  (`e8d40b64...fba610`, igual al de las rondas 4 y 4 bis) y
  `git status --porcelain -- src/` sigue mostrando solo los dos archivos
  `??` de la feature (`errors.py`, `models.py`), sin modificaciones de
  contenido.

#### Trazabilidad

Fila R28 de la tabla "Trazabilidad R<n> → test" actualizada (ver arriba)
para citar el test reescrito por introspección y precisar que
`test_optional_fields_accept_none` cubre el mismo Anexo A pero por el
constructor, no por `from_dict()` sin la clave.

#### Verificación (ronda 4 ter)

- `make lint` → `ruff check`: **All checks passed!**; `ruff format --check`:
  **16 files already formatted**.
- `make test-unit` → **99 passed, 198 subtests passed** (0.49s). Antes de
  esta ronda: 99 passed, 195 subtests passed. El neto es +3 subtests (el
  test reescrito pasa de 0 `subTest` a 3, uno por campo opcional) y 0 tests
  nuevos (se reescribió el mismo test, no se añadió otro).
- `./init.sh` → **`[OK] Entorno listo`** (exit 0).
- Alcance de los cambios: solo `tests/unit/test_models.py` y este archivo
  (`progress/impl_core_domain_models.md`). `src/`, `feature_list.json` y
  `specs/core_domain_models/tasks.md` no se tocaron en esta ronda.

## Estado (ronda 4 ter)

N2 resuelto: `test_from_dict_without_optional_key_yields_none` ahora recorre
por introspección los 3 campos opcionales y detecta un `payload[...]` en vez
de `payload.get(...)` en cualquiera de ellos (verificado con las mutaciones
R28-a y R28-b sobre una copia). `src/` no se modificó. La feature permanece
en `in_progress` en `feature_list.json` — no se marca `done` (corresponde al
leader tras la revisión del `reviewer`).

### Ronda 4 quater

Alcance: P1, P2, P3 y el hallazgo menor (docstring de `test_optional_fields_accept_none`) de
"# Ronda 4 ter — feature 2 `core_domain_models`" en `progress/review_core_domain_models.md`.
Solo se tocó `tests/unit/test_models.py` y este archivo; no se tocó `src/`.

- **P1 — R27: el orden del Anexo A solo se probaba con un par de claves de `JobSpec`.**
  - `TestModelFields::test_required_keys_by_model_matches_annex_a_order` (nueva guarda): para
    cada modelo, comprueba que `_REQUIRED_KEYS_BY_MODEL[model]` es exactamente
    `tuple(f.name for f in fields(model) if f.name != "schema_version" and not
    f.type.endswith("| None"))`. Antes de escribirla se revisó `_check_payload` en `models.py`
    (solo lectura): `schema_version` se comprueba aparte (presencia, tipo y versión soportada)
    y nunca forma parte de la tupla `required` que reciben los `from_dict()` de cada modelo, así
    que excluirla de la fórmula es correcto.
  - `TestPayloadValidation::test_missing_required_keys_report_first_in_annex_a_order_for_every_model`
    (nuevo): para cada modelo y cada índice `i` de `_REQUIRED_KEYS_BY_MODEL[model]`, borra el
    sufijo `keys[i:]` del payload y comprueba `ValidationError` con `field == keys[i]`. Al faltar
    varias claves a la vez, detecta cualquier permutación de la tupla `required` interna de
    `from_dict()`, cosa que borrar una sola clave (como ya hace
    `test_missing_required_key_for_every_model_and_key`) no puede detectar porque nunca deja más
    de una candidata.
  - Se eliminó `test_missing_required_key_reports_first_in_annex_a_order` (solo cubría `region`
    y `operation` de `JobSpec`): queda subsumido por el test nuevo, que recorre los 6 modelos y
    todos los índices.
- **P2 — R31: `JobResult.status` no se probaba por `from_dict()`.**
  - `TestPayloadValidation::test_unknown_enum_value_raises_validation_error_for_every_enum_field`
    (nuevo, sustituye a la versión manual): recorre por introspección los campos cuyo `f.type` es
    `"JobStatus"` o `"FailureCause | None"` (`Job.status`, `JobResult.status`,
    `JobResult.failure_cause`), pone la cadena `"paused"` en ese campo del payload y comprueba
    `ValidationError` con `field == f.name`. Para `failure_cause` se reutiliza `_FIELD_CONTEXT`,
    aplicando `status=JobStatus.FAILED` **sobre el propio payload** (`data["status"] = "failed"`)
    en vez de sobre la fábrica: aplicarlo a la fábrica (`factory(status=JobStatus.FAILED)`) sin
    dar también un `failure_cause` válido rompería la construcción por R34 ("failed requiere
    failure_cause"). No es estrictamente necesario para que la comprobación de `_parse_enum`
    salte —en `from_dict()`, a diferencia del constructor (M8), la clave `failure_cause_raw` se
    procesa antes de llamar a `cls(...)`, así que dispara con cualquier `status`—, pero deja el
    payload de prueba coherente con R34.
  - Se eliminó la versión manual `test_unknown_enum_value_raises_validation_error` (cubría solo
    `Job.status` y `JobResult.failure_cause`, ambos ya cubiertos por el test generado).
- **P3 — R35: solo se probaba en `JobSpec` y en el `spec` anidado de `Job`.**
  - `TestPayloadValidation::test_unknown_key_raises_validation_error_for_every_model` (nuevo):
    para cada modelo, añade `"zz_unknown"` a `factory().to_dict()` y comprueba `ValidationError`
    con `field == "zz_unknown"`.
  - Al mutar G5-G7 sobre una copia (ver abajo) se comprobó que este test por sí solo **no** las
    detecta: una clave añadida por error a la tupla `optional` interna (p. ej. `"failure_reason"`,
    `"zone"`) no tiene ningún efecto observable salvo dejar de rechazar justo ese nombre, y
    `"zz_unknown"` es un nombre distinto. La sugerencia "conviene también" del review
    (comparar `set(factory().to_dict())` contra el Anexo A) tampoco la detecta, porque
    `to_dict()` nunca emite esa clave de más.
  - Se añadió `TestPayloadValidation::test_check_payload_admits_exactly_the_annex_a_keys`: envuelve
    `models._check_payload` con `mock.patch.object(models, "_check_payload",
    wraps=models._check_payload)`, invoca `model.from_dict(factory().to_dict())` y captura, con
    `spy.call_args_list[0].kwargs`, las tuplas `required`/`optional` que la llamada de nivel
    superior le pasó de verdad. Se usa `call_args_list[0]` (no la última llamada) porque
    `Job.from_dict` llama primero a `_check_payload("Job", ...)` y solo después, al delegar en
    `JobSpec.from_dict`, a `_check_payload("JobSpec", ...)`; con la última llamada se estaría
    comprobando el `JobSpec` anidado en vez del modelo bajo prueba. Compara
    `set(required) == set(_REQUIRED_KEYS_BY_MODEL[model])` y
    `set(optional) == {f.name for f in fields(model) if f.type.endswith("| None")}`. Al capturar
    el valor real de la tupla, detecta cualquier clave de más (o de menos) sin importar su
    nombre.
- **Menor — docstring de `test_optional_fields_accept_none`.** Decía `"(R28)"`. Corregido a
  `"Anexo A (constructor): ... No verifica R28 (esa vía es from_dict() sin la clave, cubierta por
  test_from_dict_without_optional_key_yields_none)"`, para que coincida con la fila R28/R30 de la
  tabla de trazabilidad (realineada en ronda 4 ter, m3).

#### Verificación con mutación (solo en una copia, sin escribir en `src/`)

- Copia única en
  `/tmp/claude-1000/-mnt-c-Users-Usuario-Documents-Cesar-Programacion-ProyectoHarnessSDD-harness-sdd/b6c744c0-2c5e-4ef8-994e-ce8ca70f6ebd/scratchpad/mut6/src`
  (ruta fijada por el leader para esta ronda). Antes de mutar se confirmó que se cargaba la
  copia: `PYTHONPATH=<copia> .venv/bin/python -c "import geoagent.common.models as m;
  print(m.__file__)"` devuelve la ruta de la copia. Sin mutar: 102 passed, 246 subtests passed.
- **Una mutación a la vez**: la copia se borra y se regenera desde `src/` antes de cada mutación
  (`rm -rf <copia> && cp -r src <copia>`), y se ejecuta
  `PYTHONPATH=<copia> .venv/bin/python -m pytest tests/unit -q`. Al terminar la ronda se borró la
  copia (`rm -rf`).
- `src/` no cambió: `sha256sum src/geoagent/common/models.py` da `e8d40b64…fba610`, el mismo
  valor que en las rondas 4, 4 bis y 4 ter, y `git status --porcelain -- src/` sigue mostrando
  solo los dos archivos `??` de la feature (`errors.py`, `models.py`), sin modificaciones de
  contenido.

| Mutación | Resultado |
|---|---|
| G1a: `JobResult` `required` con `job_id`↔`partition_id` intercambiados | Detectada: `test_missing_required_keys_report_first_in_annex_a_order_for_every_model` [JobResult, index=0] |
| G1b: `AgentInfo` `required` con `hostname`↔`agent_version` intercambiados | Detectada: mismo test [AgentInfo, index=0] |
| G1c: `Job` `required` con `job_id`↔`spec` intercambiados | Detectada: mismo test [Job, index=0] |
| G1d: `JobProgress` `required` con `job_id`↔`percent` intercambiados | Detectada: mismo test [JobProgress, index=0] |
| G1e: `JobSpec` `required` con `region`↔`time_start` intercambiados | Detectada: mismo test [JobSpec, index=1] |
| G2: `JobResult.from_dict`, `_parse_enum(payload["status"], JobStatus, "estado")` (nombre de `field` mal copiado) | Detectada: `test_unknown_enum_value_raises_validation_error_for_every_enum_field` [JobResult, status] |
| G5: `JobResult` con `optional=("failure_cause", "failure_reason")` | Detectada: `test_check_payload_admits_exactly_the_annex_a_keys` [JobResult] (`test_unknown_key_raises_validation_error_for_every_model` no la detecta, como se esperaba) |
| G6: `AgentInfo` con `optional=("agent_id", "zone")` | Detectada: mismo test [AgentInfo] |
| G7: `Heartbeat` con `optional=("zone",)` | Detectada: mismo test [Heartbeat] |

Se detectan las 8 mutaciones que pidió el leader (G1a-G1e, G2, G5-G7). Además, para descartar
regresiones, se repitieron sobre la misma copia las mutaciones ya exigidas en rondas anteriores:
M8/A (borrar `_require_enum` de `failure_cause` en el constructor), B/M12 (séptimo `@dataclass`
público `AgentCommand` sin fábrica) y R28-c (`Job.from_dict`: `payload.get("assigned_agent_id")`
→ `payload["assigned_agent_id"]`). Las tres siguen detectadas, sin cambios de resultado respecto
a las rondas 4, 4 bis y 4 ter.

#### Verificación (ronda 4 quater)

- `make lint` → `ruff check`: **All checks passed!**; `ruff format --check`: **16 files already
  formatted** (tras `ruff format tests/unit/test_models.py` para una línea larga en la
  comprensión de `expected_optional`).
- `make test-unit` → **102 passed, 246 subtests passed** (0.5s). Antes de esta ronda: 99 passed,
  198 subtests passed. Neto: +3 tests (`test_required_keys_by_model_matches_annex_a_order`,
  `test_missing_required_keys_report_first_in_annex_a_order_for_every_model`,
  `test_check_payload_admits_exactly_the_annex_a_keys`, más la renombrada
  `test_unknown_enum_value_raises_validation_error_for_every_enum_field` y la nueva
  `test_unknown_key_raises_validation_error_for_every_model`, menos las 2 eliminadas
  `test_missing_required_key_reports_first_in_annex_a_order` y
  `test_unknown_enum_value_raises_validation_error`).
- `./init.sh` → **`[OK] Entorno listo`** (exit 0).
- Alcance de los cambios: solo `tests/unit/test_models.py` y este archivo
  (`progress/impl_core_domain_models.md`). `src/`, `feature_list.json` y
  `specs/core_domain_models/tasks.md` no se tocaron en esta ronda.

## Estado (ronda 4 quater)

P1, P2 y P3 resueltos con tests nuevos/generados por introspección, y el hallazgo menor del
docstring corregido. `src/` no se modificó (verificado con `sha256sum` y `git status
--porcelain`). Las filas R27, R31 y R35 de la tabla de trazabilidad están actualizadas. La
feature permanece en `in_progress` en `feature_list.json` — no se marca `done` (corresponde al
leader tras la revisión del `reviewer`).


## Ronda D12 — T21–T26

- `src/geoagent/common/models.py`: nuevo `_payload_keys`; `_check_payload(cls, data, path=None)`;
  los 6 `from_dict()` llaman `_check_payload(cls, data)`. Sin `required=`/`optional=` residuales.
- `tests/unit/test_models.py`: eliminado `test_check_payload_admits_exactly_the_annex_a_keys` y el
  import `mock` (ya sin uso). Sonda `zz_unknown` y `test_required_keys_by_model_matches_annex_a_order`
  intactas.
- `make lint`: sin errores. `make test-unit`: 101 passed, 240 subtests passed.

### Mutaciones (T24)

Copia de `src/` y `tests/` en el scratchpad (`mutd12/`), `PYTHONPATH=<copia>/src` (verificado que
importa la copia); una mutación cada vez; `src/` real sin cambios (`diff -r` vacío).

| # | Mutación (solo en la copia) | Resultado | Test que falla |
|---|---|---|---|
| SANITY | `JobSpec.from_dict` lanza `RuntimeError` | Detectada | muchos (confirma que se carga la copia) |
| M1 | `_payload_keys`: `required.append` -> `insert(0, ...)` (orden invertido) | Detectada | `test_missing_required_keys_report_first_in_annex_a_order_for_every_model` (21 subtests) |
| M2 | `_payload_keys`: no excluir `schema_version` | **SOBREVIVE (mutante equivalente)** | Ninguno. `schema_version` pasaría a `required`, pero `_check_payload` ya exige su presencia y lo incluye en `allowed` antes; no hay diferencia observable |
| M3 | criterio invertido (`f.default is not None`) | Detectada | `test_missing_required_key_for_every_model_and_key`, `test_missing_required_keys_report_first_in_annex_a_order_for_every_model`, `test_from_dict_without_optional_key_yields_none`, `test_missing_required_key_raises_validation_error`, `test_missing_key_inside_spec_reports_prefixed_field` |
| RF-a | renombrar `_payload_keys` | No rompe nada (101 passed) | - |
| RF-b | renombrar `_check_payload` | No rompe nada (101 passed) | - |
| RF-c | permutar parámetros posicionales `(data, cls)` | No rompe nada (101 passed) | - |

RF-a/b/c confirman el objetivo de D12: los refactores sin bug que rompían el test espía en la
ronda 4 quater (RF1–RF3) ya no rompen ningún test. Nota sobre M2: es equivalente en comportamiento;
la exclusión por nombre es defensa de coherencia, no observable.

### Verificación final (T26)

`make lint` y `make test-unit` en verde (101 passed, 240 subtests). `./init.sh`: exit 0, `[OK] Entorno listo` (m1 de la revisión D12). La feature sigue en
`in_progress`; pendiente de revisión.

### Ajuste post-D12 (test R33)

`test_status_other_than_succeeded_or_failed_raises_via_from_dict` ahora cubre QUEUED, RUNNING y CANCELLED (subTest) con la constante de clase `_BAD_STATUSES` compartida. `make lint` y `make test-unit` en verde: 101 passed, 243 subtests. Feature sigue `in_progress`.
