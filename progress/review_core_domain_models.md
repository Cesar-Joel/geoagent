# Review — feature 2 `core_domain_models`

**Veredicto:** CHANGES_REQUESTED (RECHAZADO)

Revisado en la rama `feat/2-core_domain_models` (working tree sin commitear), 2026-09-24.
Inputs: `specs/core_domain_models/{requirements,design,tasks}.md`,
`progress/impl_core_domain_models.md`, `src/geoagent/common/{errors,models}.py`,
`tests/unit/{test_errors,test_models}.py`.

## Resumen

La implementación sigue bien el diseño aprobado. D1–D11 se respetan, no hay dependencias nuevas
y no se usan construcciones de 3.10+. Con una sonda manual confirmé que el comportamiento de
`from_dict` es correcto en los seis modelos: la clave obligatoria ausente produce el `field`
correcto, `UnknownSchemaVersionError` lleva el `model` correcto y un error de tipo anidado
produce `spec.region`.

Rechazo por dos motivos:
1. **Un defecto funcional contra R25:** se aceptan offsets con minutos >= 60.
2. **Tests insuficientes:** los tests de varios requirements (R23, R29 y R27/T16) no verifican
   lo que el requirement exige, aunque `tasks.md` marque T15 y T16 como `[x]`.

## Ejecución

| Comando | Resultado |
|---------|-----------|
| `./init.sh` | exit 0, `[OK] Entorno listo` |
| `make lint` | exit 0 (`ruff check` y `ruff format --check`, 16 archivos) |
| `make test-unit` | exit 0, 82 passed, 87 subtests passed, 0.42 s |
| typecheck | No hay objetivo (ni mypy ni pyright en `.venv`). N/A |
| cobertura | No se puede medir: `pytest-cov` no está en `[dev]` (`--cov` no se reconoce). Ver m8 |
| `make test-integration` / `make demo` | N/A (la feature no toca backend, agente, cola ni Spark) |

## Hallazgos

### Mayores (bloquean)

- **M1 — R25: se aceptan offsets inexistentes.** `src/geoagent/common/models.py:197-203`.
  `_parse_timestamp` construye `timedelta(hours=HH, minutes=MM)` sin comprobar `MM < 60`.
  Resultados comprobados:
  - `"2026-01-01T10:00:00+05:60"` se acepta como `+06:00` (sale 04:00Z).
  - `"...+00:99"` se acepta como `+01:39`.

  R25 exige `ValidationError` para un "offset inexistente". Hay que rechazar `MM >= 60` con
  `field` y añadir el caso (p. ej. `+05:60`) a
  `tests/unit/test_models.py:504` (`test_from_dict_rejects_invalid_timestamp_strings`).
- **M2 — El test de R23 no verifica el instante.** `tests/unit/test_models.py:483-497`
  (`test_from_dict_accepts_various_fractions_and_offsets`). Solo comprueba
  `tzinfo is timezone.utc`. R23 exige además que el resultado "representa el mismo instante",
  y T15 pide lo mismo ("produce UTC con el instante correcto"). Hay que añadir un valor
  esperado a cada caso: `-05:30` → `10:00Z`, `.5` → `500000` µs, `.123` → `123000` µs, etc.
  Con el test actual, un parser que ignore el offset o la fracción pasaría.
- **M3 — El test de R29 no verifica `field` ni prueba `from_dict`.**
  `tests/unit/test_models.py:569-583` (`test_wrong_type_in_constructor_and_from_dict`).
  - Pese al nombre, solo usa constructores.
  - En ninguno de los 7 casos comprueba `ctx.exception.field`, y R29 exige "con `field` igual
    a la ruta de ese campo".

  Hay que añadir la aserción de `field` en cada caso y al menos varios casos por `from_dict`,
  incluido uno anidado (`spec.region` con `[True]` → `field == "spec.region"`, que también
  refuerza R4).
- **M4 — T16 está marcada `[x]` pero la parte "para cada modelo y cada clave obligatoria" no
  está implementada.** `tests/unit/test_models.py:545-560`. Solo se elimina
  `JobSpec.dataset`, más el caso de orden `region`/`operation`. T16 pide expresamente recorrer
  los seis modelos y todas sus claves obligatorias. El acceptance #5/#6 ("validación de campos
  faltantes") depende de ello. Si una clave se declarara por error en `optional` en lugar de
  `required`, el resultado sería un `KeyError` crudo que ningún test detecta. Hay que añadir un
  test parametrizado con `subTest` sobre los 6 modelos × claves obligatorias. Mi sonda indica
  que hoy pasaría.

### Menores (hay que corregirlos en esta ronda o justificarlos en `progress/impl_core_domain_models.md`)

- **m1 — `TypeError` crudo con claves desconocidas de tipos mezclados.**
  `src/geoagent/common/models.py:241`. `sorted(...)` lanza `TypeError` si hay 2 o más claves
  desconocidas de tipos no comparables. Comprobado: `{**d, 1: "x", "zz": "y"}` →
  `TypeError: '<' not supported between instances of 'str' and 'int'`. Esto contradice
  `docs/architecture.md` principio 3 (no propagar excepciones crudas) y el espíritu de R35.
  Además, con una clave no `str` el `field` resultante es un `int`. Sugerencia: ordenar con
  `key=str` y usar `str(key)` en el `field`. Un payload JSON no puede producir este caso, pero
  un `Mapping` de Python sí.
- **m2 — R5: el test no comprueba que la instancia queda sin cambios.**
  `tests/unit/test_models.py:231-235` (`_assert_frozen`). R5 y T12 exigen "dejar la instancia
  sin cambios". Falta comparar el atributo o la instancia tras el intento.
- **m3 — R21: no hay un test de serialización con microsegundos distintos de cero.**
  `tests/unit/test_models.py:468-474`. T15 lo pide expresamente ("microsegundos"). Por ejemplo,
  `123456` µs debe dar `...10:00:00.123456Z`.
- **m4 — R6: cobertura parcial.** `tests/unit/test_models.py:255-277`. No se prueba que
  `Heartbeat.running_job_ids` sea una `tuple` ni que `Heartbeat.resource_usage` sea una copia de
  solo lectura. Solo se cubren `JobSpec.region`, `AgentInfo.capabilities` y `JobResult.metrics`.
- **m5 — R18/R19/R20 solo se ejercitan con `JobSpec` y con el `spec` anidado de `Job`.**
  `tests/unit/test_models.py:411-459`. El nombre del modelo va escrito a mano en cada
  `_check_version` (`models.py:278, 328, 377, 436, 496, 545`) y en cada `_check_payload`. Un
  error de copia en `model` no lo detectaría ningún test. Sugerencia: añadir un `subTest` por
  modelo.
- **m6 — R30/R33: casos incompletos respecto a T16/T17.**
  - R30 (`tests/unit/test_models.py:585`): T16 pide `nan` e `inf` tanto en `region` como en
    `metrics`, y solo hay `nan`/`region` e `inf`/`metrics`.
  - R33 (`:662`): dice "en el constructor o en `from_dict()`", y el camino `from_dict` con
    `"status": "queued"` no está probado.
- **m7 — Cambio fuera de alcance en `.gitignore`.** El working tree elimina las líneas
  `.notes.json` y `.notes_*.json` (fecha del archivo: 2026-09-19). No figura en el informe del
  implementer ni en design §2. Hay que sacarlo del commit de esta feature o justificarlo
  aparte.
- **m8 — C4 (cobertura ≥ 85%) no es verificable.** No hay `pytest-cov` en
  `pyproject.toml [dev]` y `make test-unit` no mide cobertura, aunque `docs/verification.md`
  Nivel 5 lo exige. Es un fallo de infraestructura heredado de la feature 1, no de esta feature,
  pero el checkpoint no se puede marcar. Hay que registrarlo como pendiente para el leader.

### Nits (no bloquean)

- **n1 — Comentarios-banner que no explican un "por qué".** `src/geoagent/common/models.py:75-77`
  y `:258-260`, y también en `tests/unit/test_models.py`. `docs/conventions.md` §Comentarios
  solo admite comentarios que explican un "por qué".
- **n2 — R2 dice "subclase directa de `Exception`".** `tests/unit/test_errors.py:14` usa
  `issubclass`. Sería más preciso `GeoAgentError.__bases__ == (Exception,)`.
- **n3 — Aserciones redundantes.** `tests/unit/test_models.py:551-552`: los
  `assertNotIsInstance(..., KeyError/TypeError)` no aportan nada porque `assertRaises(ValidationError)`
  ya lo garantiza.
- **n4 — `_reraise_nested` podría anotarse como `NoReturn`.** `src/geoagent/common/models.py:250`.
  Así desaparecería el `raise  # pragma: no cover` de `:352`.
- **n5 — Python 3.9 no se ha verificado en local.** Queda documentado en el informe (T20) y se
  delega en la matriz de CI. Aceptado, conforme a T20.

## Conformidad con el diseño (D1–D11)

- D1 [x] `errors.py` solo contiene `GeoAgentError`, `ValidationError` y `UnknownSchemaVersionError`.
- D2 [x] `UnknownSchemaVersionError(ValidationError)` conserva `model`/`version` en la ruta anidada (`models.py:250-255`).
- D3 [x] Campos y orden idénticos al Anexo A (verificado por `TestModelFields`).
- D4 [x] `region` sin aridad (`TestJobSpecBoundary`).
- D5 [x] `FailureCause` con 7 valores.
- D6 [x] `Heartbeat.status` es una `str` no vacía.
- D7 [x] `can_transition` devuelve `bool` y solo lanza con argumentos que no son `JobStatus`.
- D8 [x] `assigned → cancelled` es válida.
- D9 [x] Un único `SCHEMA_VERSION`.
- D10 [x] Clave desconocida → `ValidationError` (ver m1 por el caso con tipos mezclados).
- D11 [x] Se aceptan offsets `±HH:MM` (ver M1 por la validación de minutos).
- Orden de `from_dict` según design §5 [x]. §10 (3.9) [x]: sin `fromisoformat`, `get_type_hints`,
  `StrEnum`, `datetime.UTC`, `match` statement, `slots=` ni `kw_only=`. Sin `print()` ni IO.

## Trazabilidad requirements ↔ tests

- R1: [x] `TestModelFields::test_*_fields`
- R2: [x] `TestErrorHierarchy::test_validation_error_is_subclass_of_geoagent_error`, `test_geoagent_error_is_subclass_of_exception` (n2)
- R3: [x] `TestErrorHierarchy::test_unknown_schema_version_error_has_model_version_and_field`
- R4: [x] `TestSchemaVersion::test_job_from_dict_rejects_unknown_nested_spec_version`, `TestPayloadValidation::test_missing_key_inside_spec_reports_prefixed_field`, `test_unknown_key_top_level_and_nested_raise_with_path`
- R5: [~] `TestImmutability::test_*_is_frozen`. No comprueba que la instancia quede "sin cambios" (m2)
- R6: [~] `TestImmutability::test_mutating_*`, `test_mapping_field_rejects_item_assignment`. Faltan los campos de `Heartbeat` (m4)
- R7: [x] `TestJobStatus::test_exact_values`
- R8: [x] `TestCanTransition::test_all_36_pairs`
- R9: [x] `TestCanTransition::test_all_36_pairs`
- R10: [x] `TestJobStatus::test_is_terminal`
- R11: [x] `TestCanTransition::test_invalid_arguments_raise_validation_error`
- R12: [x] `TestFailureCause::test_exact_values`
- R13: [x] `TestModelFields::_assert_field_order` (default de `schema_version`)
- R14: [x] `TestRoundTrip::test_to_dict_keys_match_annex_a`, `test_to_dict_values_are_json_types`, `test_to_dict_returns_new_dict_each_call`
- R15: [x] `TestRoundTrip::test_enum_fields_serialize_as_value`
- R16: [x] `TestRoundTrip::test_job_to_dict_spec_matches_jobspec_to_dict`
- R17: [x] `TestRoundTrip::test_*_round_trip*`
- R18: [x] `TestSchemaVersion::test_from_dict_rejects_unknown_versions` y siguientes. Solo con `JobSpec`/`Job` (m5)
- R19: [x] `TestSchemaVersion::test_constructor_rejects_unknown_version`. Solo con `JobSpec` (m5)
- R20: [x] `TestSchemaVersion::test_from_dict_missing_schema_version_raises_validation_error`, `test_from_dict_invalid_schema_version_types_raise_validation_error`
- R21: [~] `TestTimestamps::test_serializes_*`. Falta un caso con microsegundos (m3)
- R22: [x] `TestTimestamps::test_constructor_normalizes_offset_to_utc`
- R23: [ ]  ← `test_from_dict_accepts_various_fractions_and_offsets` no verifica el instante (M2)
- R24: [x] `TestTimestamps::test_constructor_rejects_naive_datetime`
- R25: [ ]  ← Defecto: se acepta `+05:60`/`+00:99`, sin test (M1)
- R26: [x] `TestPayloadValidation::test_non_mapping_payload_raises_with_field_none`, `test_non_mapping_nested_spec_raises_with_field_spec`
- R27: [~] `TestPayloadValidation::test_missing_required_key_*`. No cubre cada modelo y cada clave, como pide T16 (M4)
- R28: [x] `TestRoundTrip::test_from_dict_without_optional_key_yields_none`
- R29: [ ]  ← `test_wrong_type_in_constructor_and_from_dict` no comprueba `field` ni ejercita `from_dict` (M3)
- R30: [x] `TestPayloadValidation::test_constraint_violations` (m6)
- R31: [x] `TestPayloadValidation::test_unknown_enum_value_raises_validation_error`
- R32: [x] `TestJobProgressBoundaries::*`
- R33: [x] `TestJobResultBoundaries::test_status_other_than_succeeded_or_failed_raises` (m6)
- R34: [x] `TestJobResultBoundaries::test_failed_without_cause_raises`, `test_succeeded_with_cause_raises`
- R35: [x] `TestPayloadValidation::test_unknown_key_top_level_and_nested_raise_with_path` (m1)
- R36: [x] `TestJobSpecBoundary::*`

Leyenda: [x] cubierto de forma significativa. [~] cubierto parcialmente (menor). [ ] sin cobertura
válida o con defecto (bloquea).

## Tasks completas

- T1: [x]
- T2: [x]
- T3: [x]
- T4: [x]
- T5: [x]
- T6: [~]  ← No rechaza offsets con `MM >= 60` (M1)
- T7: [x]
- T8: [x]
- T9: [x]
- T10: [x]
- T11: [x]
- T12: [~]  ← Falta "deja la instancia igual" y los campos de `Heartbeat` (m2, m4)
- T13: [x]
- T14: [x]
- T15: [ ]  ← Marcada `[x]`, pero faltan "microsegundos" en la serialización y "el instante correcto" en `from_dict` (M2, m3)
- T16: [ ]  ← Marcada `[x]`, pero falta "para cada modelo y cada clave obligatoria", el `field` en los errores de tipo y el camino `from_dict` (M3, M4)
- T17: [x]
- T18: [x]
- T19: [x]  (la tabla de trazabilidad existe; varias entradas sobrestiman la cobertura, ver arriba)
- T20: [x]  (3.9 sin verificar en local, documentado)

## Checkpoints

- C1: [x] Archivos base y docs presentes; `./init.sh` exit 0.
- C2: [x] Solo la feature 2 está `in_progress`; la feature 1 (`done`) sigue en verde; `progress/current.md` describe la sesión activa.
- C3: [x] `src/geoagent/` solo contiene `common/agent/backend/spark/tools`; sin dependencias nuevas; sin `print()` ni TODOs; sin secretos.
- C4: [ ] Cobertura ≥ 85% no verificable (m8). Resto OK: sin red, sin mocks de FS (los modelos no hacen IO), `make test-unit` < 1 s, integración N/A.
- C5: [x] Sin archivos sospechosos sin trackear. `history.md` tiene la entrada de la sesión anterior (la de esta sesión corresponde al cierre). Estado `in_progress` correcto. Nota: hay un cambio de `.gitignore` ajeno a la feature (m7).
- C6: [ ] Specs y EARS OK, mapa `R<n> → test` documentado. Pero R23, R25 y R29 no tienen un test que los verifique de forma significativa (M1–M3).

## Cambios requeridos

1. **M1:** en `_parse_timestamp`, rechazar minutos de offset `>= 60` con `ValidationError(field=...)` y añadir `+05:60` (y, opcionalmente, `+00:99`) a `test_from_dict_rejects_invalid_timestamp_strings`.
2. **M2:** en `test_from_dict_accepts_various_fractions_and_offsets`, comprobar el `datetime` UTC esperado de cada caso (instante y microsegundos).
3. **M3:** en el test de R29, comprobar `ctx.exception.field` en cada caso y añadir casos por `from_dict`, incluido uno anidado en `spec` (`field == "spec.region"`).
4. **M4:** añadir un test que recorra, con `subTest`, los 6 modelos y cada clave obligatoria eliminada, y compruebe `ValidationError` con `field == clave`.
5. **m1–m7:** corregirlos o justificarlos en `progress/impl_core_domain_models.md`. m7 (`.gitignore`) debe quedar fuera del commit de la feature o justificarse aparte.
6. Actualizar la tabla de trazabilidad de `progress/impl_core_domain_models.md` para que refleje los nuevos tests.
7. **m8:** decisión del leader. Registrar como pendiente de infraestructura (medición de cobertura) y no bloquear esta feature por ello.

---

# Ronda 2 — feature 2 `core_domain_models`

**Veredicto:** APPROVED (APROBADO)

Input: sección "Ronda 2 — respuesta a review" de `progress/impl_core_domain_models.md`. La he
contrastado con el código y los tests actuales.

## Ejecución (ronda 2)

| Comando | Resultado |
|---------|-----------|
| `./init.sh` | exit 0 (`[OK] Entorno listo`) |
| `make lint` | `All checks passed!`, 16 archivos formateados |
| `make test-unit` | 92 passed, 141 subtests passed, 0.45 s |

Además volví a ejecutar la sonda manual de la ronda 1:
- `+05:60` y `+00:99` → `ValidationError(field="time_start")`.
- `-05:30` → instante 10:00Z correcto.
- Claves desconocidas `{1, "zz"}` → `ValidationError` con `field="1"`, sin `TypeError`.
- `spec.region=[True]` → `field="spec.region"`.

## Verificación de hallazgos

- **M1** [x] `models.py:195-196` rechaza `minutes >= 60` con `field`. Los casos `+05:60` y
  `+00:99` están en `test_from_dict_rejects_invalid_timestamp_strings` (`test_models.py:547`).
- **M2** [x] `test_models.py:524-540` compara el `datetime` UTC esperado de cada caso (offset
  `-05:30` y fracciones `.5`, `.123` y `.123456`).
- **M3** [x] `test_wrong_type_in_constructor_raises_with_field` (`:607`) comprueba `field` en
  los 7 casos. `test_wrong_type_in_from_dict_raises_with_field` (`:623`) cubre 4 casos por
  `from_dict`. `test_wrong_type_in_nested_spec_reports_prefixed_field` (`:648`) cubre
  `spec.region`.
- **M4** [x] `test_missing_required_key_for_every_model_and_key` (`:723`) recorre los 6 modelos
  y cada clave obligatoria (`_REQUIRED_KEYS_BY_MODEL`, `:103`, coherente con el Anexo A) y
  comprueba `field == clave`.
- **m1** [x] `models.py:238-240`: `sorted(..., key=str)` y `str(extra[0])`. La regresión la
  cubre `:715`.
- **m2** [x] `_assert_frozen` (`:231`) comprueba que el valor no cambia tras los intentos de
  `setattr` y `delattr`.
- **m3** [x] `test_serializes_nonzero_microseconds` (`:513`).
- **m4** [x] Los campos de `Heartbeat` están en `:278-302`.
- **m5** [x] Tres tests recorren los 6 modelos y comprueban `exc.model` y `version` (`:476-502`).
- **m6** [x] Las 4 combinaciones `nan`/`inf` × `region`/`metrics` están en `:655`. R33 por
  `from_dict` está en `:761`.
- **m7 / m8**: fuera de alcance por decisión del leader. No bloquean. m8 sigue pendiente: al
  revisar, `progress/current.md` aún no lo registra. Le corresponde al leader.
- **n1–n4** [x] Se han quitado los banners (no queda `# ---` en `src/` ni en
  `test_models.py`). Hay un test de `__bases__` para R2, se han eliminado las aserciones
  redundantes y `_reraise_nested` devuelve `NoReturn`.

## Trazabilidad requirements ↔ tests (ronda 2)

R1–R36: [x]. Todos tienen al menos un test significativo que verifica el resultado concreto y el
`field` cuando el requirement lo exige. Las entradas que en la ronda 1 eran [~] o [ ] (R5, R6,
R21, R23, R25, R27, R29) ya están cubiertas por los tests citados arriba.

Observación no bloqueante: en la tabla de trazabilidad de `progress/impl_core_domain_models.md`,
la fila R2 todavía cita `test_geoagent_error_is_subclass_of_exception`, pero el test se llama
ahora `test_geoagent_error_is_direct_subclass_of_exception` (`tests/unit/test_errors.py:14`).
Conviene corregir el nombre al cerrar. El resto de la tabla coincide con los tests reales.

## Tasks completas (ronda 2)

- T1–T20: [x]. `tasks.md` no tiene ninguna `[ ]`. T6, T12, T15 y T16 ya reflejan el trabajo
  real tras las correcciones de M1–M4 y m2–m6.

## Checkpoints (ronda 2)

- C1: [x]
- C2: [x]
- C3: [x]
- C4: [~] Cobertura ≥ 85% no medible (m8). Queda como pendiente de infraestructura por decisión
  del leader. El resto está OK.
- C5: [x] (`.gitignore` queda fuera del commit de la feature por decisión del leader)
- C6: [x]

## Cambios requeridos

Ninguno bloqueante. Recomendaciones para el cierre:
1. Corregir el nombre del test de R2 en la tabla de trazabilidad de `progress/impl_core_domain_models.md`.
2. Leader: registrar m8 (medición de cobertura) en `progress/current.md` como había previsto.

---

# Ronda 3 — observaciones del leader (post-aprobación)

**Veredicto:** CHANGES_REQUESTED. La feature se reabre (`done` → `in_progress`) antes del commit.

Revisión humana de los tests de timestamps. El código cumple R24 y R25 en todos los campos (lo he
comprobado con una sonda manual sobre los 5 campos `datetime` y sobre `spec.time_start`), pero
los tests solo lo verifican en `JobSpec.time_start`. Una regresión en cualquier otro campo (una
llamada a `_require_datetime`/`_parse_timestamp` borrada o con el nombre de `field` mal copiado)
no la detectaría ningún test.

## Mayores (bloquean)

- **M5 — R24: el rechazo de datetimes naive en el constructor solo se prueba en
  `JobSpec.time_start`.** `tests/unit/test_models.py:542`
  (`test_constructor_rejects_naive_datetime`). R24 habla de "un campo `datetime`" y exige
  `field` igual a su ruta. Faltan `JobSpec.time_end`, `Job.created_at`, `JobResult.finished_at`
  y `Heartbeat.sent_at`. Tampoco se prueba el segundo término de la definición de naive
  (`requirements.md:18-19`): un `tzinfo` distinto de `None` cuyo `utcoffset()` devuelve `None`.
  Si la condición de `models.py:113` se simplificara a `value.tzinfo is None`, los tests
  seguirían en verde.
  - Hay que parametrizar con `subTest` sobre los 5 pares (fábrica, campo) y comprobar
    `ValidationError` con `field == campo`.
  - Hay que añadir un caso con un `tzinfo` personalizado cuyo `utcoffset()` devuelva `None`.
- **M6 — R25: el rechazo de timestamps naive en `from_dict` solo se prueba en
  `JobSpec.time_start`.** `tests/unit/test_models.py:546`
  (`test_from_dict_rejects_invalid_timestamp_strings`). La cadena sin zona
  (`"2026-09-14T10:00:00"`) solo se prueba en `time_start`. Hay que añadir:
  - Un test con `subTest` sobre los 5 campos `datetime` de los 4 modelos que los tienen. Se pasa
    la cadena sin zona y se comprueba `ValidationError` con `field == campo`.
  - Un caso de un objeto `datetime` naive (no `str`) pasado a `from_dict`. R25 exige rechazar
    cualquier valor que no sea `str`, y este es el caso más fácil de que alguien lo "flexibilice"
    por error.
  - Un caso anidado: `Job.from_dict` con `spec.time_start` sin zona → `field == "spec.time_start"`.

## Cambios requeridos

1. M5 y M6: solo tests. No hace falta tocar `src/`, porque el comportamiento ya es correcto.
2. Actualizar las filas R24 y R25 de la tabla de trazabilidad de
   `progress/impl_core_domain_models.md`. Ya puestos, corregir el nombre del test de R2
   (observación pendiente de la ronda 2).
3. Dejar `make lint` y `make test-unit` en verde.

---

# Ronda 3 — feature 2 `core_domain_models`

**Veredicto:** CHANGES_REQUESTED

Alcance: respuesta del implementer a M5 y M6 (sección "## Ronda 3 — respuesta a review" de
`progress/impl_core_domain_models.md`). La he contrastado con `tests/unit/test_models.py`
(`TestTimestamps`, líneas 555-628), con R24 y R25 y con la definición de naive
(`specs/core_domain_models/requirements.md:18-19`).

## M5 — R24 (constructor): resuelto

- `test_constructor_rejects_naive_datetime` usa `subTest` sobre los 5 pares (fábrica, campo):
  `JobSpec.time_start`, `JobSpec.time_end`, `Job.created_at`, `JobResult.finished_at` y
  `Heartbeat.sent_at`. En cada caso comprueba `ValidationError` y `field == campo`. [x]
- `test_constructor_rejects_datetime_whose_tzinfo_utcoffset_is_none` usa `_NoneOffsetTzInfo`
  (`utcoffset() -> None`) y cubre el segundo término de la definición de naive. [x]

## M6 — R25 (`from_dict`): resuelto en lo pedido, con un hueco

- `test_from_dict_rejects_unzoned_string_for_every_datetime_field` pasa una cadena sin zona en
  los 5 campos y comprueba `field`. [x]
- `test_job_from_dict_rejects_unzoned_nested_spec_time_start` comprueba
  `field == "spec.time_start"`. [x]
- `test_from_dict_rejects_naive_datetime_object_instead_of_string` pasa un `datetime` naive en
  lugar de una `str`. [x] Existe y pasa, pero no protege `_parse_timestamp` (ver N1).

## Mutaciones temporales en `src/geoagent/common/models.py` (revertidas)

Antes de mutar guardé una copia del archivo y el `sha256` de todo `src/`. Después comparé los
hashes y **`src/` quedó idéntico**. Para las mutaciones M-a a M-i ejecuté `pytest -k Timestamps`;
para M-j, la suite unitaria completa.

| Mutación | Resultado |
|---|---|
| M-a: `_require_datetime` simplificado a `value.tzinfo is None` | detectada (`..._utcoffset_is_none`) |
| M-b: constructor `time_end` con `field="time_start"` | detectada (subTest `time_end`) |
| M-c: se elimina la validación de `created_at` en el constructor | detectada (subTest `created_at`) |
| M-d: constructor `finished_at` con un `field` erróneo | detectada (subTest `finished_at`) |
| M-e: se elimina la validación de `sent_at` en el constructor | detectada (subTest `sent_at`) |
| M-f / M-g / M-i: `_parse_timestamp` con un `field` erróneo en `sent_at` / `created_at` / `finished_at` | detectadas (`..._unzoned_string_for_every_datetime_field`) |
| M-h: `_parse_timestamp` acepta objetos `datetime` y devuelve tal cual los naive | **no detectada**: el naive lo rechaza después el constructor, con el mismo `field` |
| M-j: `_parse_timestamp` acepta objetos `datetime` aware (`if isinstance(value, datetime): return _require_datetime(value, field)`) | **no detectada**: 96 passed, 151 subtests passed |

## Hallazgos

### Mayores (bloquean)

- **N1 — R25: `from_dict` puede aceptar un objeto `datetime` aware y ningún test lo detecta.**
  R25 exige `ValidationError` para cualquier valor de un campo `datetime` que no sea `str`. El
  test que añadió esta ronda para el objeto `datetime` usa uno **naive**. Ese caso lo rechaza
  también el constructor (`_require_datetime`) con el mismo `field`, así que el test pasa aunque
  `_parse_timestamp` deje de exigir `str` (M-h). La "flexibilización" más probable es aceptar
  objetos `datetime` en `from_dict` (M-j), y la suite entera sigue en verde con ella. El único
  otro valor no `str` que se prueba es `12345`, que no activa esa rama. El objetivo de M6
  ("el caso más fácil de que alguien lo flexibilice por error") queda sin proteger.
  - Cambio requerido: añadir un caso con un objeto `datetime` **aware** (por ejemplo,
    `_dt(2026, 9, 14, 10)`) pasado a `from_dict`. Debe comprobar `ValidationError` y
    `field == "time_start"`. Puede ir en la lista `invalid` de
    `test_from_dict_rejects_invalid_timestamp_strings` o en el test del objeto naive. Solo
    cambian los tests. El código actual ya lo rechaza (`_parse_timestamp`, `models.py:182-183`).

### Menores

- Ninguno.

## Otras comprobaciones

- `src/` sin cambios en esta ronda: `models.py` tiene mtime 2026-09-25 y `errors.py`
  2026-09-24, ambos anteriores a las observaciones del leader de la ronda 3. Después de las
  mutaciones, el hash de todo `src/` coincide con el inicial. [x]
- Trazabilidad `progress/impl_core_domain_models.md`: la fila R24 (línea 80) y la fila R25
  (línea 81) citan tests que existen y se corresponden con su contenido. [x] Cuando se resuelva
  N1, la fila R25 debe mencionar también el caso del `datetime` aware.
- Fila R2: `test_geoagent_error_is_direct_subclass_of_exception` existe en
  `tests/unit/test_errors.py:14` y la tabla la cita correctamente. La observación de la ronda 2
  queda cerrada. [x]
- `make lint`: `All checks passed!` y `16 files already formatted`. [x]
- `make test-unit`: 96 passed, 151 subtests passed. [x]
- `./init.sh`: exit 0 (`[OK] Entorno listo`). [x]
- `feature_list.json`: la feature 2 está en `in_progress`. [x]

## Cambios requeridos

1. N1: añadir el caso del objeto `datetime` aware en `from_dict` (R25) y comprobar `field`.
2. Actualizar la fila R25 de la tabla de trazabilidad.
3. Dejar `make lint` y `make test-unit` en verde.

# Ronda 3 bis — feature 2 `core_domain_models`

**Veredicto:** APPROVED

Alcance: resolución de N1 (ronda 3), según la subsección "### Ronda 3 bis — N1" de
`progress/impl_core_domain_models.md`.

## N1 — R25 (`from_dict` con objeto `datetime` aware): resuelto

- `TestTimestamps::test_from_dict_rejects_datetime_object_instead_of_string`
  (`tests/unit/test_models.py:615`) usa `subTest` con dos casos: `naive`
  (`datetime(2026, 9, 14, 10, 0, 0)`) y `aware` (`_dt(2026, 9, 14, 10)`). Los dos se pasan en
  `time_start` a `JobSpec.from_dict`, y en ambos el test comprueba `ValidationError` y
  `field == "time_start"`. [x]

## Mutación temporal en `src/geoagent/common/models.py` (revertida)

Antes de mutar guardé el `sha256` de todos los archivos de `src/` y una copia de `models.py`.

| Mutación | Resultado |
|---|---|
| M-j: al principio de `_parse_timestamp`, `if isinstance(value, datetime): return _require_datetime(value, field)` | **detectada**: `SUBFAILED(value='aware') ...::test_from_dict_rejects_datetime_object_instead_of_string` (`ValidationError not raised`). Resultado: 1 failed, 96 passed, 152 subtests passed |

Después restauré la copia y volví a calcular los hashes. El `diff` con los hashes iniciales sale
vacío: **`src/` quedó idéntico**. [x]

## Otras comprobaciones

- Fila R25 de la trazabilidad (`progress/impl_core_domain_models.md:81`): cita el test con su
  nuevo nombre e indica los casos naive y aware. Todos los tests que cita existen. [x]
- `make lint`: `All checks passed!` y `16 files already formatted`. [x]
- `make test-unit`: 96 passed, 153 subtests passed. [x]
- `./init.sh`: exit 0 (`[OK] Entorno listo`). [x]
- `feature_list.json`: la feature 2 sigue en `in_progress`. [x]

## Hallazgos

### Mayores (bloquean)

- Ninguno.

### Menores

- La sección "### Verificación (ronda 3)" de `progress/impl_core_domain_models.md` dice
  "151 subtests passed". Tras el caso aware salen 153. El dato es solo documental y no bloquea.

## Cambios requeridos

- Ninguno. Los cambios requeridos de la ronda 3 (N1, fila R25 y lint/tests en verde) quedan
  resueltos.

---

# Ronda 4 — observaciones del leader (post-aprobación)

**Veredicto:** CHANGES_REQUESTED. La feature se reabre (`done` → `in_progress`) antes del commit.

## Criterio

Aquí se distinguen dos clases de test:
- **De lógica:** prueban un helper compartido (gramática de timestamps, `nan`/`inf`, límites).
  Basta con probarlo en un campo. No hace falta repetirlo en todos.
- **De conexión:** prueban que cada campo llama a su validador con su nombre de `field`. Cada
  llamada en `__post_init__` está escrita a mano y puede faltar o tener el nombre mal copiado,
  así que hace falta **un caso por campo**, con un único valor inválido representativo.

M5 y M6 aplicaron este criterio a los campos `datetime`. Esta ronda lo extiende a los campos `str`.

## Mayores (bloquean)

- **M7 — R29: los campos `str` apenas tienen test de conexión.** Cobertura actual de
  `tests/unit/test_models.py`, en `test_wrong_type_in_constructor_raises_with_field` y
  `test_constraint_violations`:
  - `_require_str` (obligatoria, no vacía), 11 campos. Probados: `JobSpec.dataset`,
    `Job.job_id` y `AgentInfo.hostname`. **Sin probar:** `JobSpec.operation`,
    `JobProgress.job_id`, `JobResult.job_id`, `JobResult.partition_id`,
    `AgentInfo.agent_version`, `AgentInfo.platform`, `Heartbeat.agent_id` y `Heartbeat.status`.
  - `_require_optional_str`, 2 campos. **Sin probar:** `Job.assigned_agent_id` y
    `AgentInfo.agent_id`.
  - `_require_str(..., non_empty=False)`, 1 campo. **Sin probar:** `JobProgress.message`.

  Si se borra la llamada o se escribe mal el nombre de `field` en cualquiera de estos campos,
  la suite sigue en verde. Cambios requeridos:
  1. Un test con `subTest` que recorra los 14 campos `str` (fábrica, campo) por el
     constructor con un valor que no sea `str` (p. ej. `123`) y compruebe `ValidationError` y
     `field == campo`. Para los dos opcionales, comprobar también que `None` se acepta.
  2. Para los 11 campos obligatorios y los 2 opcionales,
     comprobar también que `""` se rechaza con `field` correcto. Así se protege
     `non_empty=True` frente a un `non_empty=False` copiado por error.
  3. `JobProgress.message`: comprobar que `""` **se acepta**, porque es el único campo `str` que
     admite la cadena vacía. Así se protege frente a un `non_empty=True` copiado por error.
  4. Basta con el constructor: `from_dict` pasa estos campos tal cual al constructor, y un
     error de correspondencia en `from_dict` ya lo detectan los round-trips.

## Cambios requeridos

1. M7: solo tests. No hace falta tocar `src/`.
2. Actualizar la fila R29 (y la R30 si procede) de la tabla de trazabilidad de
   `progress/impl_core_domain_models.md`.
3. Dejar `make lint` y `make test-unit` en verde.

## M7 — enfoque revisado (sustituye a "Cambios requeridos" 1-3 de M7)

Revisión humana: una tabla escrita a mano obliga a actualizarla cada vez que se añade o se
quita un campo, y un campo nuevo olvidado no haría fallar nada. Por eso los tests de conexión
se **generan por introspección** de los modelos:

- Se recorren los 6 modelos y, para cada uno, `dataclasses.fields(Modelo)`. `models.py` usa
  `from __future__ import annotations`, así que `f.type` es una cadena estable en 3.9 y 3.14
  (`'str'`, `'str | None'`, `'datetime'`, `'tuple[float, ...]'`, `'Mapping[str, float]'`,
  `'JobStatus'`, `'FailureCause | None'`, `'int'`, `'float'`, `'JobSpec'`). No se usa
  `typing.get_type_hints`, porque en 3.9 no puede evaluar `X | None`.
- Una tabla `tipo (cadena) → valor inválido` (p. ej. `'str' → 123` y `'datetime' → datetime`
  naive). Para cada campo se construye el modelo con la fábrica `make_*` sobrescribiendo ese
  campo, y se comprueba `ValidationError` con `field == f.name`. Se excluye `schema_version`,
  porque ya lo cubren sus propios tests.
- **Guarda de completitud:** si un campo tiene un tipo que no está en la tabla, el test falla
  con un mensaje explícito ("tipo sin clasificar: Modelo.campo: T"). Así, un campo nuevo de un
  tipo nuevo obliga a decidir cómo se valida, y uno de un tipo conocido queda cubierto sin
  tocar el test.
- Reglas derivadas del tipo:
  - `... | None` → `None` se acepta.
  - `'str'` y `'str | None'` → `""` se rechaza, **salvo** los campos de una lista explícita de
    excepciones semánticas. Hoy es solo `("JobProgress", "message")`, que debe aceptar `""`.
    La guarda debe comprobar también que cada entrada de la lista de excepciones existe, para
    que no quede obsoleta.
- Casos que la tabla no puede expresar: si alguno de los validadores condicionales
  (`failure_cause` depende de `status`) no encaja en la regla general, que quede fuera de la
  generación con un comentario que lo justifique. Los tests explícitos que ya existen siguen
  cubriéndolo.
- `TestModelFields` **sigue siendo explícito**. Es el contrato contra el Anexo A del spec y no
  debe derivarse del código bajo prueba. Por eso, si alguien añade un campo, ese test obliga a
  actualizar el spec, y los tests de conexión lo cubren automáticamente.
- Los tests de conexión escritos a mano en la ronda 3 (5 campos `datetime`) y las filas de
  conexión de `test_wrong_type_in_constructor_raises_with_field` que queden redundantes se
  pueden sustituir por el test generado. Los tests de **lógica** (gramática de timestamps,
  `nan`/`inf`, `utcoffset() -> None`, límites) se mantienen tal cual.

---

# Ronda 4 — feature 2 `core_domain_models`

**Veredicto:** CHANGES_REQUESTED

Alcance: respuesta del implementer a M7 ("## M7 — enfoque revisado"), en
"## Ronda 4 — respuesta a review" de `progress/impl_core_domain_models.md`, y los tests
nuevos de `tests/unit/test_models.py` (`_INVALID_VALUE_BY_TYPE`, `_EMPTY_STRING_EXCEPTIONS`,
`_iter_model_fields`, `test_every_field_wrong_type_raises_with_field`,
`test_optional_fields_accept_none` y `test_str_fields_reject_empty_string_unless_excepted`).

## Método de mutación (sin escribir en `src/`)

- Copia de `src/` en
  `/tmp/claude-1000/-mnt-c-Users-Usuario-Documents-Cesar-Programacion-ProyectoHarnessSDD-harness-sdd/b6c744c0-2c5e-4ef8-994e-ce8ca70f6ebd/scratchpad/mut/src`.
  Se comprobó que se cargaba la copia: `PYTHONPATH=<copia> .venv/bin/python -c "import geoagent.common.models as m; print(m.__file__)"`
  devuelve la ruta de la copia. Sin mutar, la suite sobre la copia da 98 passed, 195 subtests passed.
- Cada mutación se aplica solo a la copia de `models.py`, que se regenera desde `src/` antes de
  cada mutación. Comando: `PYTHONPATH=<copia> .venv/bin/python -m pytest tests/unit -q`.
- `src/` no cambió: el hash SHA-256 de los `.py` de `src/` es el mismo antes y después
  (`ff023f84…b7bb0c`), `git status --porcelain` es idéntico al del inicio de la ronda, y
  `diff -r src <copia>` no da diferencias al terminar.

## Tabla de mutaciones

| # | Mutación (solo en la copia) | Resultado | Tests que fallan |
|---|---|---|---|
| M1 | Borrar la validación de `AgentInfo.platform` | Detectada | `test_every_field_wrong_type_raises_with_field` [AgentInfo.platform], `test_str_fields_reject_empty_string_unless_excepted` [AgentInfo.platform] |
| M2 | `field="agent_id"` en `Job.assigned_agent_id` | Detectada | `test_every_field_wrong_type…` [Job.assigned_agent_id], `test_str_fields_reject_empty…` [Job.assigned_agent_id] |
| M3 | `non_empty=False` en `JobResult.partition_id` | Detectada | `test_str_fields_reject_empty…` [JobResult.partition_id] |
| M4 | `non_empty=True` en `JobProgress.message` | Detectada | `test_str_fields_reject_empty…` [JobProgress.message] |
| M5 | Borrar la validación de `JobResult.finished_at` | Detectada | `test_every_field_wrong_type…` [JobResult.finished_at] |
| M6 | Nuevo campo `AgentInfo.region_tag: str = "eu"` sin validar, antes de `schema_version` | Detectada | `TestModelFields::test_agent_info_fields` (**falla, como se esperaba**), `test_every_field_wrong_type…` [AgentInfo.region_tag], `test_str_fields_reject_empty…` [AgentInfo.region_tag] |
| M7 | Nuevo campo `AgentInfo.weight: bytes = b""` (tipo sin clasificar) | Detectada | Salta la guarda de completitud de `test_every_field_wrong_type…` ("tipo sin clasificar: AgentInfo.weight: bytes"). También falla `TestModelFields::test_agent_info_fields` |
| M8 | Borrar `_require_enum` de `JobResult.failure_cause` (`failure_cause = …` → `pass`) | **SOBREVIVE** | Ninguno: 98 passed, 195 subtests passed |
| M9 | `field="cause"` en `_require_enum` de `failure_cause` | Detectada | `test_every_field_wrong_type…` [JobResult.failure_cause] |
| M10 | Borrar la validación de `AgentInfo.agent_id` (opcional) | Detectada | `test_every_field_wrong_type…` [AgentInfo.agent_id], `test_str_fields_reject_empty…` [AgentInfo.agent_id] |
| M11 | `_require_str` en vez de `_require_optional_str` en `Job.assigned_agent_id` (rechaza `None`) | Detectada | `test_optional_fields_accept_none` [Job.assigned_agent_id] y 22 tests más |
| M12 | Séptimo `@dataclass` público `AgentCommand(agent_id: str, command: str)` sin validar y sin añadir a `_MODEL_FACTORIES` | **SOBREVIVE** | Ninguno: 98 passed, 195 subtests passed |
| M13 | `field="created"` en `Job.created_at` | Detectada | `test_every_field_wrong_type…` [Job.created_at] |
| M14 | `_require_datetime` deja de rechazar naive | Detectada | `test_every_field_wrong_type…` en los 5 campos `datetime` y `test_constructor_rejects_datetime_whose_tzinfo_utcoffset_is_none` |
| M15 | Borrar la validación de `Heartbeat.sent_at` | Detectada | `test_every_field_wrong_type…` [Heartbeat.sent_at] |

Se detectan las 7 mutaciones mínimas que pidió el leader (M1–M7). Sobreviven M8 y M12.

## Hallazgos

### Mayores (bloquean)

- **M8 — el caso `FailureCause | None → 123` no prueba la conexión.** La fábrica
  `make_job_result` usa `status=JobStatus.SUCCEEDED` por defecto. Con `failure_cause=123`, si
  se borra `_require_enum(failure_cause, FailureCause, "failure_cause")` (`models.py:421`), el
  valor llega a la regla de coherencia `succeeded no admite failure_cause` (`models.py:424-425`),
  que lanza `ValidationError(field="failure_cause")`. El subtest pasa por esa otra vía. Con la
  mutación M8, `JobResult(status=FAILED, failure_cause=123)` se construye sin error y guarda
  `failure_cause == 123` (comprobado sobre la copia mutada). Ningún otro test lo detecta:
  `test_unknown_enum_value_raises_validation_error` entra por `from_dict`, donde valida
  `_parse_enum`, no el constructor.
  El enfoque revisado ya preveía este caso: los validadores condicionales que no encajen en la
  regla general deben quedar fuera de la generación, con un comentario, y tener un test
  explícito. No se hizo, y la respuesta del implementer afirma algo que no se cumple en este
  campo ("borrar o copiar mal cualquiera de las llamadas de validación haría fallar exactamente
  el `subTest` de ese campo").
  **Cambio requerido** (cualquiera de las dos opciones):
  - (a) Una tabla pequeña de *overrides de contexto* por `(modelo, campo)`, p. ej.
    `{("JobResult", "failure_cause"): {"status": JobStatus.FAILED}}`, que el test generado
    combine con el valor inválido. Con `status=FAILED`, el código actual lanza con
    `field="failure_cause"` desde `_require_enum` (comprobado), y M8 dejaría de sobrevivir. Si la
    tabla tiene una guarda de entradas obsoletas como la de `_EMPTY_STRING_EXCEPTIONS`, mejor.
  - (b) Sacar el campo de la generación con un comentario que lo justifique y añadir un test
    explícito `make_job_result(status=JobStatus.FAILED, failure_cause=123)` → `ValidationError`
    con `field == "failure_cause"`.
  En los dos casos hay que volver a pasar M8 y confirmar que se detecta.

### Menores

- **m1 — Un modelo nuevo que no se añada a `_MODEL_FACTORIES` queda sin cubrir (M12).**
  Severidad: **menor**, pero recomiendo cerrarlo en esta misma ronda porque es barato. Un
  séptimo modelo supone cambiar el Anexo A y pasar por spec, y `TestModelFields` tampoco lo
  detectaría, porque es explícito por modelo. Aun así, deja el mismo tipo de hueco que M7 quería
  cerrar: una lista escrita a mano (esta vez de modelos) que puede quedarse desactualizada sin
  que nada falle. Guarda propuesta: un test que compare
  `{o for o in vars(models).values() if dataclasses.is_dataclass(o) and isinstance(o, type) and o.__module__ == models.__name__}`
  con `set(_MODEL_FACTORIES)` y falle con un mensaje explícito si no coinciden. Hoy los 6
  `dataclass` públicos de `models.py` están todos en `_MODEL_FACTORIES`.
- **m2 — La trazabilidad de R29 contiene una afirmación falsa.** La fila R29 de
  `progress/impl_core_domain_models.md` dice "`field` correcto en los 30 campos". Por M8, no se
  cumple en `JobResult.failure_cause`. Hay que corregirla cuando se resuelva M8.
- **m3 — `test_optional_fields_accept_none` está en la fila equivocada.** La tabla lo pone en
  R30 ("no vacía", "finito", "≥ 0"), que no trata de aceptar `None`, y su docstring dice R28
  (`from_dict` sin la clave opcional produce `None`), que es otra cosa. Lo que comprueba es que el
  constructor acepta `None` en los tipos `X | None` del Anexo A. Lo más cercano es R28/Anexo A.
  Hay que alinear el docstring y la fila de la tabla. Es cosmético.
- **m4 (observación, no requiere cambio).** La guarda de completitud llama a `self.fail(...)`
  fuera del `subTest`, así que el primer tipo sin clasificar corta el recorrido del resto de
  campos. Es aceptable, porque el mensaje señala el campo exacto y la guarda cumple su función
  (M7).

## Comprobaciones pedidas

- **R24 tras retirar `test_constructor_rejects_naive_datetime`:** sigue cubierto. El valor de
  `'datetime'` en `_INVALID_VALUE_BY_TYPE` es un `datetime` naive, y
  `test_every_field_wrong_type_raises_with_field` genera un subtest por cada uno de los 5 campos
  (`JobSpec.time_start`, `JobSpec.time_end`, `Job.created_at`, `JobResult.finished_at` y
  `Heartbeat.sent_at`) y comprueba `field == f.name`. M5, M13, M14 y M15 lo confirman: con
  M14 fallan los 5 subtests, así que el test prueba de verdad el rechazo de naive y no solo el
  de tipo. El segundo término de "naive" (`utcoffset() is None`) sigue cubierto por
  `test_constructor_rejects_datetime_whose_tzinfo_utcoffset_is_none`.
- **Trazabilidad:**
  - R24: correcta.
  - R29: correcta en los tests que cita, pero con la afirmación falsa de m2.
  - R30: correcta para `test_str_fields_reject_empty_string_unless_excepted`, que M3 y M4
    confirman, y para `test_constraint_violations`. `test_optional_fields_accept_none` está mal
    asignado (m3).
- **Guarda de `_EMPTY_STRING_EXCEPTIONS`:** revisada en el código. Acumula las claves visitadas
  y falla si alguna excepción no existe o no es `str`/`str | None`. Es correcta.
- **`make lint`:** en verde (`ruff check`: All checks passed!; `ruff format --check`: 16 files
  already formatted).
- **`make test-unit`:** en verde (98 passed, 195 subtests passed).
- **`./init.sh`:** exit code 0.
- **`specs/core_domain_models/tasks.md`:** sin tasks `[ ]`.

## Cambios requeridos

1. M8 (mayor): conectar de verdad el caso `JobResult.failure_cause` con la opción (a) o la (b),
   y verificar que la mutación M8 (borrar `_require_enum` de `failure_cause`) hace fallar la
   suite. Solo tests. No hace falta tocar `src/`.
2. m1 (recomendado en esta ronda): guarda de que `_MODEL_FACTORIES` contiene todos los
   `dataclass` públicos de `models.py`.
3. m2 y m3: corregir las filas R29 y R30 (y el docstring de `test_optional_fields_accept_none`)
   en `progress/impl_core_domain_models.md` y en `tests/unit/test_models.py`.
4. Dejar `make lint`, `make test-unit` e `./init.sh` en verde.

# Ronda 4 bis — feature 2 `core_domain_models`

**Veredicto:** CHANGES_REQUESTED

Alcance: respuesta del implementer en "### Ronda 4 bis" de `progress/impl_core_domain_models.md`
a los hallazgos de "# Ronda 4 — feature 2 `core_domain_models`" (M8, m1, m2, m3). Tests
revisados en `tests/unit/test_models.py`: `_FIELD_CONTEXT`,
`test_every_field_wrong_type_raises_with_field` y
`TestModelFields::test_model_factories_cover_every_public_dataclass`.

## Método de mutación (sin escribir en `src/` ni dejar `tests/` modificado)

- Copias en
  `/tmp/claude-1000/-mnt-c-Users-Usuario-Documents-Cesar-Programacion-ProyectoHarnessSDD-harness-sdd/b6c744c0-2c5e-4ef8-994e-ce8ca70f6ebd/scratchpad/mut3/{src,tests}`.
  `PYTHONPATH=<copia>/src .venv/bin/python -c "import geoagent.common.models as m; print(m.__file__)"`
  devuelve la ruta de la copia. Sin mutar: 99 passed, 195 subtests passed.
- Las mutaciones de `src` se aplican solo a la copia de `models.py`, que se regenera desde el
  original antes de cada mutación. La mutación del test se aplica solo a la copia de
  `tests/unit/test_models.py` y se ejecuta con `pytest <copia>/tests/unit`.
- `src/` no cambió: el SHA-256 conjunto de los `.py` de `src/` es `ff023f84…b7bb0c` (igual al de
  la ronda 4), `models.py` es `e8d40b64…fba610` antes y después, `git status --porcelain` es
  idéntico al del inicio, y `diff -r -x __pycache__` entre `src/`/`tests/` y sus copias no da
  diferencias al terminar.

## Tabla de mutaciones

| # | Mutación (solo en la copia) | Resultado | Tests que fallan |
|---|---|---|---|
| A (=M8) | Quitar `_require_enum` de `JobResult.failure_cause` (`→ pass`) | Detectada | `test_every_field_wrong_type…` [JobResult.failure_cause] |
| B (=M12) | Séptimo `@dataclass` público `AgentCommand(agent_id: str, command: str)` | Detectada | `TestModelFields::test_model_factories_cover_every_public_dataclass` |
| C | Entrada obsoleta `("JobResult", "failure_reason")` en `_FIELD_CONTEXT` (copia de `tests/`) | Detectada | `test_every_field_wrong_type…`: "_FIELD_CONTEXT tiene entradas para campos que no existen: {('JobResult', 'failure_reason')}" |
| M1 | Borrar la validación de `AgentInfo.platform` | Detectada | `test_every_field_wrong_type…` y `test_str_fields_reject_empty…` [AgentInfo.platform] |
| M2 | `field="agent_id"` en `Job.assigned_agent_id` | Detectada | `test_every_field_wrong_type…` y `test_str_fields_reject_empty…` [Job.assigned_agent_id] |
| M3 | `non_empty=False` en `JobResult.partition_id` | Detectada | `test_str_fields_reject_empty…` [JobResult.partition_id] |
| M4 | `non_empty=True` en `JobProgress.message` | Detectada | `test_str_fields_reject_empty…` [JobProgress.message] |
| M5 | Borrar la validación de `JobResult.finished_at` | Detectada | `test_every_field_wrong_type…` [JobResult.finished_at] |
| M6 | Nuevo `AgentInfo.region_tag: str = "eu"` sin validar | Detectada | `test_agent_info_fields`, `test_every_field_wrong_type…` y `test_str_fields_reject_empty…` [AgentInfo.region_tag] |
| M7 | Nuevo `AgentInfo.weight: bytes = b""` | Detectada | `test_agent_info_fields` y la guarda de tipos sin clasificar de `test_every_field_wrong_type…` |
| R28-a | `AgentInfo.from_dict`: `payload.get("agent_id")` → `payload["agent_id"]` | **SOBREVIVE** | Ninguno: 99 passed, 195 subtests passed |
| R28-b | `JobResult.from_dict`: `payload.get("failure_cause")` → `payload["failure_cause"]` | **SOBREVIVE** | Ninguno: 99 passed, 195 subtests passed |

Las 3 mutaciones pedidas (A, B y C) se detectan. Las 7 de la ronda 4 (M1–M7) siguen
detectándose, sin regresiones. `_iter_model_fields()` recorre 30 campos. R28-a y R28-b se
añadieron al revisar la trazabilidad de R28 (ver abajo).

## Resolución de los hallazgos de la ronda 4

- **M8 (mayor): resuelto.** `_FIELD_CONTEXT` combina `status=JobStatus.FAILED` con el valor
  inválido, así que el caso llega a `_require_enum`. La mutación A lo confirma. El comentario
  explica por qué hace falta el contexto, y la guarda de entradas obsoletas funciona (mutación C).
- **m1: resuelto.** `test_model_factories_cover_every_public_dataclass` compara los `dataclass`
  públicos del módulo con `set(_MODEL_FACTORIES)`. La mutación B lo confirma.
- **m2: resuelto.** La fila R29 ya explica el caso de `failure_cause` y `_FIELD_CONTEXT`, y ahora
  es cierta.
- **m3: resuelto en parte.** `test_optional_fields_accept_none` se ha movido a la fila R28, pero
  esto deja al descubierto el hallazgo N2.

## Hallazgos

### Mayores (bloquean)

- **N2 — R28 solo se verifica para 1 de los 3 campos opcionales.** R28 dice: "CUANDO
  `from_dict()` recibe un payload sin una clave marcada como opcional en el Anexo A, el sistema
  DEBE construir la instancia con `None` en ese campo". El único test de esa vía,
  `TestRoundTrip::test_from_dict_without_optional_key_yields_none`, cubre solo
  `Job.assigned_agent_id`. `test_optional_fields_accept_none` usa el constructor con `None`
  explícito y no pasa por `from_dict()` sin la clave. Por eso no verifica R28, aunque la fila R28
  ahora afirme que cubre "los 3 campos". Si la clave falta en `AgentInfo.from_dict`
  (`models.py:512`) o en `JobResult.from_dict` (`models.py:456`) y se lee con `payload[...]`, se
  lanza `KeyError`, algo que R28 y el criterio 5 prohíben, y la suite sigue en verde (R28-a y
  R28-b). Es el mismo tipo de hueco que M7 quería cerrar: un caso escrito a mano en lugar de uno
  por campo. Además, la fila de trazabilidad afirma más de lo que se prueba, igual que en m2.

### Menores

- Ninguno nuevo.

## Trazabilidad R28 / R29

- R28: [ ]  ← `test_from_dict_without_optional_key_yields_none` cubre solo
  `Job.assigned_agent_id`. `AgentInfo.agent_id` y `JobResult.failure_cause` no se verifican por
  `from_dict()` (N2).
- R29: [x] cubierto por `test_wrong_type_in_constructor_raises_with_field`,
  `test_wrong_type_in_from_dict_raises_with_field`,
  `test_wrong_type_in_nested_spec_reports_prefixed_field` y
  `test_every_field_wrong_type_raises_with_field` (30 campos, `failure_cause` incluido gracias a
  `_FIELD_CONTEXT`).

## Otras comprobaciones

- `make lint`: en verde (`ruff check`: All checks passed!; `ruff format --check`: 16 files
  already formatted).
- `make test-unit`: en verde (99 passed, 195 subtests passed).
- `./init.sh`: exit code 0.
- `specs/core_domain_models/tasks.md`: sin tasks `[ ]` (sin cambios en esta ronda).

## Cambios requeridos

1. N2 (mayor, solo en tests): hacer que el test de R28 recorra los campos opcionales por
   introspección. Por ejemplo, para cada `(model, factory, f)` de `_iter_model_fields()` cuyo tipo
   termine en `| None`: `data = factory().to_dict(); del data[f.name]`, y comprobar que
   `getattr(model.from_dict(data), f.name) is None`. Las fábricas actuales ya producen `None` en
   los 3 campos (JobResult con `status=SUCCEEDED`), así que no hace falta contexto. Después hay
   que confirmar que R28-a y R28-b se detectan.
2. Corregir la fila R28 de `progress/impl_core_domain_models.md` para que cite el test que
   verifica R28 por `from_dict()` y deje `test_optional_fields_accept_none` como verificación
   del Anexo A por el constructor, no como cobertura de R28.
3. Dejar `make lint`, `make test-unit` e `./init.sh` en verde.

# Ronda 4 ter — feature 2 `core_domain_models`

**Veredicto:** CHANGES_REQUESTED

Alcance: la respuesta del implementer a N2 en "### Ronda 4 ter" de
`progress/impl_core_domain_models.md` y el test reescrito
`TestRoundTrip::test_from_dict_without_optional_key_yields_none`
(`tests/unit/test_models.py:491`). A petición del leader, también se han buscado de una vez
todos los huecos restantes del mismo tipo (conexión por campo o por modelo) en la vía
`from_dict()`.

**N2 queda resuelto.** El veredicto es CHANGES_REQUESTED porque aparecen 3 huecos nuevos del
mismo tipo (P1–P3). Se enumeran todos a la vez, como pidió el leader.

## Método de mutación (sin escribir en `src/`)

- Copias en
  `/tmp/claude-1000/-mnt-c-Users-Usuario-Documents-Cesar-Programacion-ProyectoHarnessSDD-harness-sdd/b6c744c0-2c5e-4ef8-994e-ce8ca70f6ebd/scratchpad/mut5/{src,tests}`.
  `PYTHONPATH=<copia>/src .venv/bin/python -c "import geoagent.common.models as m; print(m.__file__)"`
  devuelve la ruta de la copia. Sin mutar, la suite da 99 passed y 198 subtests passed.
- El script `scratchpad/run_mut5.py` regenera la copia de `models.py` (y la de
  `test_models.py`, en la mutación C) desde el original antes de cada mutación. Aplica **una sola
  mutación** cada vez y ejecuta `pytest <copia>/tests/unit` con `PYTHONPATH=<copia>/src`. Al
  terminar, restaura las copias: `diff -r -x __pycache__` contra `src/` y `tests/` no muestra
  diferencias.
- `src/` no cambió. El SHA-256 de cada `.py` de `src/` y `tests/` es el mismo antes y después
  (diff vacío entre los dos listados). `models.py` sigue en `e8d40b64…fba610`, el mismo valor que
  en las rondas 4 y 4 bis. `git status --short` coincide con el del inicio de la ronda.

## Tabla de mutaciones

| # | Mutación (solo en la copia, una cada vez) | Resultado | Tests que fallan |
|---|---|---|---|
| R28-a | `AgentInfo.from_dict`: `payload.get("agent_id")` → `payload["agent_id"]` | Detectada | `test_from_dict_without_optional_key_yields_none` [AgentInfo.agent_id] |
| R28-b | `JobResult.from_dict`: `payload.get("failure_cause")` → `payload["failure_cause"]` | Detectada | `test_from_dict_without_optional_key_yields_none` [JobResult.failure_cause] |
| R28-c | `Job.from_dict`: `payload.get("assigned_agent_id")` → `payload["assigned_agent_id"]` | Detectada | `test_from_dict_without_optional_key_yields_none` [Job.assigned_agent_id] |
| M1 | Borrar la validación de `AgentInfo.platform` | Detectada | `test_every_field_wrong_type…` y `test_str_fields_reject_empty…` [AgentInfo.platform] |
| M2 | `field="agent_id"` en `Job.assigned_agent_id` | Detectada | `test_every_field_wrong_type…` y `test_str_fields_reject_empty…` [Job.assigned_agent_id] |
| M3 | `non_empty=False` en `JobResult.partition_id` | Detectada | `test_str_fields_reject_empty…` [JobResult.partition_id] |
| M4 | `non_empty=True` en `JobProgress.message` | Detectada | `test_str_fields_reject_empty…` [JobProgress.message] |
| M5 | Borrar la validación de `JobResult.finished_at` | Detectada | `test_every_field_wrong_type…` [JobResult.finished_at] |
| M6 | Nuevo `AgentInfo.region_tag: str = "eu"` sin validar | Detectada | `test_agent_info_fields` y los subtests [AgentInfo.region_tag] |
| M7 | Nuevo `AgentInfo.weight: bytes = b""` | Detectada | `test_agent_info_fields` y la guarda "tipo sin clasificar" |
| A (=M8) | Quitar `_require_enum` de `failure_cause` en el constructor | Detectada | `test_every_field_wrong_type…` [JobResult.failure_cause] |
| B (=M12) | Séptimo `@dataclass` público `AgentCommand` | Detectada | `test_model_factories_cover_every_public_dataclass` |
| C | Entrada obsoleta en `_FIELD_CONTEXT` (copia de `tests/`) | Detectada | guarda de entradas obsoletas de `test_every_field_wrong_type…` |
| G1a | R27, orden de `required` en `JobResult`: `job_id` ↔ `partition_id` | **SOBREVIVE** | Ninguno |
| G1b | R27, orden de `required` en `AgentInfo`: `hostname` ↔ `agent_version` | **SOBREVIVE** | Ninguno |
| G1c | R27, orden de `required` en `Job`: `job_id` ↔ `spec` | **SOBREVIVE** | Ninguno |
| G1d | R27, orden de `required` en `JobProgress`: `job_id` ↔ `percent` | **SOBREVIVE** | Ninguno |
| G1e | R27, orden de `required` en `JobSpec`: `region` ↔ `time_start` | **SOBREVIVE** | Ninguno |
| G2 | R31, `JobResult.from_dict`: `_parse_enum(payload["status"], JobStatus, "estado")` | **SOBREVIVE** | Ninguno |
| G2' | R31, lo mismo en `Job.from_dict` (control) | Detectada | `test_unknown_enum_value_raises_validation_error` |
| G3 | R31, `field="cause"` en `_parse_enum` de `failure_cause` en `from_dict` (control) | Detectada | `test_unknown_enum_value_raises_validation_error` |
| G4 | `AgentInfo` con `optional=()` (control) | Detectada | 7 fallos (round-trip y R27) |
| G5 | R35, `JobResult` con `optional=("failure_cause", "failure_reason")` | **SOBREVIVE** | Ninguno |
| G6 | R35, `AgentInfo` con `optional=("agent_id", "zone")` | **SOBREVIVE** | Ninguno |
| G7 | R35, `Heartbeat` con `optional=("zone",)` | **SOBREVIVE** | Ninguno |

Se detectan R28-a, R28-b y R28-c, cada una por separado y con un único subtest fallido, el del
campo mutado. Las mutaciones de las rondas 4 y 4 bis (M1–M7, A, B y C) se siguen detectando, así
que no hay regresiones.

## Resolución de N2

- **Una mutación cada vez:** las 3 (R28-a, R28-b y R28-c) hacen fallar exactamente el subtest de
  su campo. El implementer solo había probado R28-a y R28-b juntas. R28-c, la de
  `Job.assigned_agent_id`, también se detecta.
- **Se elimina la clave:** sí. `del data[f.name]` (línea 509), sobre el resultado de
  `factory().to_dict()`, que siempre incluye la clave. No se limita a dejarla en `None`.
- **Guarda de "al menos un opcional":** sí,
  `self.assertTrue(optional_fields, "no se encontró ningún campo opcional")` (línea 501).
- **No usar `_FIELD_CONTEXT` es correcto.** Con `status=FAILED`, eliminar `failure_cause` haría
  que R34 lanzara `ValidationError` (failed requiere cause), y el test no podría comprobar R28 en
  ese campo. Con las fábricas por defecto, los 3 opcionales valen `None`, y un `JobResult` con
  `status=SUCCEEDED` sin `failure_cause` es el único caso válido del modelo para R28. El
  comentario del test lo explica. Además, la mutación R28-b demuestra que el campo se prueba de
  verdad sin contexto.
- **Trazabilidad de R28:** correcta. La fila R28 cita el test reescrito como verificación de la
  vía `from_dict()` sin la clave, y deja `test_optional_fields_accept_none` como verificación del
  Anexo A por el constructor.
  - Menor (cosmético): el docstring de `test_optional_fields_accept_none` sigue diciendo
    "(R28)". Conviene cambiarlo a "Anexo A (constructor)" para que coincida con la fila.

## Hallazgos

### Mayores (bloquean). Son todos los huecos del mismo tipo que se han encontrado

Revisé todas las conexiones de `from_dict()` que dependen del campo o del modelo:
`required`/`optional` de `_check_payload`, `_parse_timestamp`, `_parse_enum`, `payload.get`, el
nombre del modelo en `_check_version` y el prefijo `spec.`. Quedan 3 huecos:

- **P1 — R27 (orden del Anexo A) solo se prueba con un par de claves de `JobSpec`.**
  `test_missing_required_key_reports_first_in_annex_a_order` borra `region` y `operation`, y
  `test_missing_required_key_for_every_model_and_key` borra una sola clave, así que el orden de la
  tupla `required` no importa. Cualquier permutación de `required` en cualquiera de los 6 modelos
  sobrevive (G1a–G1e). Incluso en `JobSpec` sobrevive el intercambio `region` ↔ `time_start`.
  **Cambio:** que `test_missing_required_key_for_every_model_and_key`, o un test nuevo, borre para
  cada modelo e índice `i` las claves `keys[i:]` de `_REQUIRED_KEYS_BY_MODEL[model]` y compruebe
  que `field == keys[i]`. Así se detecta cualquier permutación. Además, una guarda de que
  `_REQUIRED_KEYS_BY_MODEL[model]` es igual a
  `tuple(f.name for f in fields(model) if not f.type.endswith("| None") and f.name != "schema_version")`,
  para que la lista escrita a mano no se desincronice del modelo.
- **P2 — R31 no se prueba en `JobResult.status` por `from_dict()`.**
  `test_unknown_enum_value_raises_validation_error` solo cubre `Job.status` y
  `JobResult.failure_cause`. `test_status_other_than_succeeded_or_failed_raises_via_from_dict`
  usa `"queued"`, que es un valor válido del enum, así que falla en el constructor y no en
  `_parse_enum`. Por eso G2 sobrevive.
  **Cambio:** generar el caso de R31 para los 3 campos enum (`Job.status`, `JobResult.status` y
  `JobResult.failure_cause`) por introspección de `f.type` (`"JobStatus"` o
  `"FailureCause | None"`), con una cadena desconocida (`"paused"`) y el contexto
  `status=FAILED` para `failure_cause`, en lo posible reutilizando `_FIELD_CONTEXT`. Hay que
  comprobar `field == f.name`.
- **P3 — R35 (clave desconocida) solo se prueba en `JobSpec` y en el `spec` anidado de `Job`.**
  Si se añade una clave de más a `optional` o a `required` en `JobResult`, `AgentInfo` o
  `Heartbeat`, la suite no se entera (G5–G7). Lo mismo pasa con `JobProgress`, que se ha revisado
  en el código pero no se ha mutado. El conjunto de claves admitidas es propio de cada modelo, y
  cada uno necesita su caso. **Cambio:** un test por cada modelo de `_MODEL_FACTORIES` que añada
  una clave desconocida (p. ej. `"zz_unknown"`) a `factory().to_dict()` y compruebe
  `ValidationError` con `field == "zz_unknown"`. Conviene también una comprobación explícita de
  que `set(factory().to_dict())` es igual a las claves del Anexo A. Ya lo hace en parte
  `test_to_dict_keys_match_annex_a`, pero por la vía de `to_dict()`, no de las admitidas por
  `from_dict()`.

Otras conexiones revisadas, todas cubiertas campo a campo o modelo a modelo:
- `_parse_timestamp` en los 5 campos `datetime`
  (`test_from_dict_rejects_unzoned_string_for_every_datetime_field`).
- El nombre del modelo en `_check_payload` y `_check_version`
  (`test_*_unknown_version_for_every_model`).
- La clave `schema_version` ausente (`test_from_dict_missing_schema_version_for_every_model`).
- El prefijo `spec.`.
- Que `from_dict` no mezcle campos, porque las fábricas usan valores distintos y los tests de
  round-trip lo detectarían.

### Menores

- Docstring de `test_optional_fields_accept_none`: sigue diciendo "(R28)" (ver arriba).

## Trazabilidad afectada

- R28: [x] cubierto por `test_from_dict_without_optional_key_yields_none`, con los 3 campos y
  cada mutación detectada por separado.
- R27: [ ]  ← el orden del Anexo A solo se verifica para un par de claves de `JobSpec` (P1).
- R31: [ ]  ← `JobResult.status` no se verifica por `from_dict()` con una cadena desconocida
  (P2).
- R35: [ ]  ← solo se verifica en `JobSpec` y en `Job.spec` (P3).

## Otras comprobaciones

- `make lint`: en verde (`ruff check`: All checks passed!; `ruff format --check`: 16 files
  already formatted).
- `make test-unit`: en verde (99 passed, 198 subtests passed).
- `./init.sh`: exit code 0 ("Entorno listo").
- `specs/core_domain_models/tasks.md`: sin tasks `[ ]`.
- `src/` sin cambios (hash y `git status` como arriba).

## Cambios requeridos

Solo en tests. No hace falta tocar `src/`.

1. P1: generar la comprobación de R27 por modelo borrando `keys[i:]`, y añadir la guarda de
   que `_REQUIRED_KEYS_BY_MODEL` coincide con `fields()`. Después, verificar que G1a–G1e se
   detectan.
2. P2: generar R31 para los 3 campos enum por introspección y verificar que G2 se detecta.
3. P3: generar R35 para los 6 modelos y verificar que G5–G7 se detectan.
4. Actualizar las filas R27, R31 y R35 de `progress/impl_core_domain_models.md`, y el docstring
   de `test_optional_fields_accept_none`.
5. Dejar `make lint`, `make test-unit` e `./init.sh` en verde.

# Ronda 4 quater — feature 2 `core_domain_models`

**Veredicto:** APPROVED

Alcance: la respuesta del implementer a P1, P2, P3 y al hallazgo menor de la ronda 4 ter
("### Ronda 4 quater" de `progress/impl_core_domain_models.md`), la valoración de diseño del test
espía de P3 y las filas R27, R31 y R35. **P1, P2, P3 y el menor quedan resueltos.** No hay
hallazgos bloqueantes. El test espía de P3 se clasifica como **menor (no bloqueante)** y se
documenta abajo con una recomendación.

## Método de mutación (sin escribir en `src/`)

- Copia única en
  `/tmp/claude-1000/-mnt-c-Users-Usuario-Documents-Cesar-Programacion-ProyectoHarnessSDD-harness-sdd/b6c744c0-2c5e-4ef8-994e-ce8ca70f6ebd/scratchpad/mut7/{src,tests}`.
  `PYTHONPATH=<copia>/src .venv/bin/python -c "import geoagent.common.models as m; print(m.__file__)"`
  devuelve `.../scratchpad/mut7/src/geoagent/common/models.py`. Sin mutar: 102 passed y 246
  subtests passed, igual que en el repo.
- `scratchpad/run_mut7.py` regenera `models.py` (y `test_models.py` en la mutación C) desde el
  original antes de cada mutación. Aplica **una sola mutación** cada vez, comprueba que el texto
  mutado difiere del original y ejecuta `pytest <copia>/tests/unit` con `PYTHONPATH=<copia>/src`.
  Una mutación de control (`SANITY`: `JobSpec.from_dict` lanza `RuntimeError`) hace fallar 64
  tests. Eso confirma que pytest carga la copia y no `src/`.
- `src/` y `tests/` no cambiaron. El SHA-256 de cada `.py` de `src/` y `tests/` es idéntico antes
  y después (`diff` vacío). `models.py` sigue en `e8d40b64…fba610`. La salida de
  `git status --short` coincide con la del inicio. Al terminar, `diff -r -x __pycache__` de la
  copia contra `src/` y `tests/` no muestra diferencias.

## Tabla de mutaciones

| # | Mutación (solo en la copia, una cada vez) | Resultado | Test que falla |
|---|---|---|---|
| G1a | R27, `JobResult.required`: `job_id` ↔ `partition_id` | Detectada | `test_missing_required_keys_report_first_in_annex_a_order_for_every_model` [JobResult, index=0] |
| G1b | R27, `AgentInfo.required`: `hostname` ↔ `agent_version` | Detectada | ídem [AgentInfo, index=0] |
| G1c | R27, `Job.required`: `job_id` ↔ `spec` | Detectada | ídem [Job, index=0] |
| G1d | R27, `JobProgress.required`: `job_id` ↔ `percent` | Detectada | ídem [JobProgress, index=0] |
| G1e | R27, `JobSpec.required`: `region` ↔ `time_start` | Detectada | ídem [JobSpec, index=1] |
| G1f | R27, `Heartbeat.required`: `agent_id` ↔ `sent_at` (nueva, completa los 6 modelos) | Detectada | ídem [Heartbeat, index=0] |
| G2 | R31, `JobResult.from_dict`: `_parse_enum(..., "estado")` | Detectada | `test_unknown_enum_value_raises_validation_error_for_every_enum_field` [JobResult, status] |
| G5 | R35, `JobResult` `optional=("failure_cause", "failure_reason")` | Detectada | `test_check_payload_admits_exactly_the_annex_a_keys` [JobResult] |
| G6 | R35, `AgentInfo` `optional=("agent_id", "zone")` | Detectada | ídem [AgentInfo] |
| G7 | R35, `Heartbeat` `optional=("zone",)` | Detectada | ídem [Heartbeat] |
| G8 | R35, `JobProgress` `optional=("eta",)` (nueva) | Detectada | ídem [JobProgress] |
| G9 | R35, `JobSpec` `optional=("dataset_id",)` (nueva) | Detectada | ídem [JobSpec] y `test_unknown_key_top_level_and_nested_raise_with_path` |
| G10 | `JobResult.required` con una clave de más, `"extra_req"` (nueva) | Detectada | 9 fallos (round-trip, R27, R35…) |
| G11 | `_check_payload`: `allowed = … \| {"schema_version", "zone"}` (nueva, dentro del helper) | **SOBREVIVE** | Ninguno. Ver "Observación O1" |
| R28-a/b/c | `payload.get(...)` → `payload[...]` en los 3 opcionales | Detectadas | `test_from_dict_without_optional_key_yields_none` [su campo] |
| M1–M7 | Rondas 4 / 4 bis | Detectadas | Las mismas que en la ronda 4 ter |
| A (=M8), B (=M12), C | Rondas 4 bis / 4 ter | Detectadas | Las mismas que en la ronda 4 ter |
| G2', G3, G4 | Controles de la ronda 4 ter | Detectadas | Las mismas que en la ronda 4 ter |
| RF1 | **Refactor sin bug**: `JobResult.from_dict` pasa `required`/`optional` en posición | Falla | `test_check_payload_admits_exactly_the_annex_a_keys` [JobResult] (`KeyError`) |
| RF2 | **Refactor sin bug**: renombrar el parámetro `optional` → `allowed_optional` | Falla | ídem, 6 subtests |
| RF3 | **Refactor sin bug**: renombrar `_check_payload` → `_validate_payload` | Falla | ídem, 6 subtests (`AttributeError` en `patch.object`) |

Resultado: G1a–G1e, G2 y G5–G7 se detectan una a una, y también G1f, G8, G9 y G10. Las
mutaciones de las rondas 4, 4 bis y 4 ter siguen detectándose, así que no hay regresiones. RF1–RF3
muestran el coste del test espía, que se valora abajo. En los tres casos solo falla ese test.

## Resolución de los hallazgos de la ronda 4 ter

- **P1 (R27):** resuelto. `test_missing_required_keys_report_first_in_annex_a_order_for_every_model`
  borra `keys[i:]` para cada modelo e índice y comprueba `field == keys[i]`. La guarda
  `test_required_keys_by_model_matches_annex_a_order` compara `_REQUIRED_KEYS_BY_MODEL` con
  `fields()`, respetando el orden. Borrar `test_missing_required_key_reports_first_in_annex_a_order`
  es correcto, porque el test nuevo lo cubre entero (G1e se detecta en index=1).
- **P2 (R31):** resuelto. Los campos enum se generan por introspección de `f.type` (hay 3) y hay
  guarda de lista no vacía. Se comprueba `field == f.name`. El contexto `status=failed` se aplica
  al payload. Es coherente con R34 y está bien explicado.
- **P3 (R35):** resuelto funcionalmente. Hay sonda `"zz_unknown"` en los 6 modelos y un test
  espía para las claves admitidas. El implementer señala que mi sugerencia de "comparar
  `set(to_dict())`" no detectaba G5–G7. Tiene razón.
- **Menor (docstring):** resuelto. `test_optional_fields_accept_none` ya dice "Anexo A
  (constructor)… No verifica R28".

## Valoración de diseño: `test_check_payload_admits_exactly_the_annex_a_keys`

**Clasificación: menor (no bloqueante), aceptable de forma transitoria con la justificación de
abajo.**

1. **Encaje con las normas del proyecto.**
   - `docs/conventions.md` no dice nada sobre mocks ni sobre probar funciones privadas.
   - `docs/verification.md` solo prohíbe el mock del filesystem o del store (anti-patrones). No
     se incumple ninguna regla escrita.
   - Sí hay tensión con `specs/core_domain_models/design.md`, §"Helpers privados
     (orientativos; el implementer ajusta nombres)". El diseño declara que el nombre y la firma
     de `_check_payload` **no son contractuales**. El test los convierte en un contrato de hecho:
     el nombre del helper, los nombres de los kwargs `required`/`optional`, que se pasen por
     nombre y que la primera llamada sea la del modelo de nivel superior. El propio design
     también admite como alternativa para el anidamiento una función interna
     `_from_dict(data, path)`, y ese cambio también podría alterar el orden o la forma de las
     llamadas.
2. **Refactors legítimos que lo rompen sin que haya bug** (verificados en la copia como RF1–RF3):
   - pasar `required`/`optional` en posición (`KeyError`);
   - renombrar un parámetro (`KeyError`);
   - renombrar el helper (`AttributeError`).

   Por inspección, también lo romperían:
   - partir `_check_payload` en `_check_unknown_keys` y `_check_required_keys`;
   - enlazar el helper en tiempo de import (alias o `functools.partial`), con lo que el espía no
     vería ninguna llamada (`IndexError`);
   - validar el `spec` anidado antes que el nivel superior (cambia `call_args_list[0]`).

   **Atenuante importante:** en todos estos casos el fallo es ruidoso (error o aserción). Ninguno
   da un falso verde, y quien hace el refactor lo ve en el mismo cambio.
3. **¿Hay alternativa observable sin tocar `src/`?** No hay una que sea completa. El conjunto de
   claves que admite `from_dict()` solo se observa sondeando nombres concretos, y el espacio de
   nombres no tiene límite. Los nombres de G5–G7 (`failure_reason`, `zone`) no son claves de
   ningún modelo, así que tampoco los detectaría una sonda con la unión de las claves del Anexo A
   de los 6 modelos. Esa sonda sí cubriría el error más probable, pegar la lista de otro modelo,
   pero no el caso general. Lo que sí se puede hacer solo en tests es **reducir el acoplamiento**
   sin perder detección:
   - normalizar la llamada con
     `inspect.signature(models._check_payload).bind(*call.args, **call.kwargs).arguments`, lo que
     elimina RF1;
   - seleccionar la llamada por su primer argumento (`model == model.__name__`) en vez de por
     `call_args_list[0]`, lo que elimina la dependencia del orden de las llamadas anidadas.

   RF2 y RF3 seguirían rompiendo el test, aunque de forma ruidosa.
4. **Cambio de spec o diseño que eliminaría el acoplamiento** (requiere aprobación humana, porque
   toca design §10 A4 o la API):
   - **Opción D1 (preferida):** una enmienda al design según la cual `_check_payload` deriva
     `required`/`optional` de `dataclasses.fields(cls)`. Obligatorias son las que no terminan en
     `| None` y no son `schema_version`, en el orden de declaración. Opcionales son las que
     terminan en `| None`. Así desaparecen las tuplas escritas a mano en cada `from_dict()`, y
     con ellas la clase de bug G5–G10: no se prueba, se hace imposible. La guarda
     `test_required_keys_by_model_matches_annex_a_order` ya fija que el orden de `fields()` es el
     del Anexo A. El test espía sobraría y quedaría la sonda `zz_unknown`. Solo afecta a la
     derivación de claves, no a la conversión de tipos, así que la alternativa A4 ("no reflexión
     genérica en to_dict/from_dict") se mantiene en lo esencial, pero hay que anotarlo.
   - **Opción D2:** exponer como API pública las claves del Anexo A de cada modelo, p. ej.
     `ClassVar` `REQUIRED_KEYS`/`OPTIONAL_KEYS`, que `from_dict()` usaría obligatoriamente. El
     test compararía la constante con `fields()` sin mock. Tiene más superficie pública que
     mantener, y el paso "from_dict usa la constante" sigue siendo una conexión que habría que
     probar.
5. **Recomendación:** no bloquear la feature 2.
   - Ahora, como menor y solo en tests: endurecer el espía con `signature.bind` y seleccionar la
     llamada por nombre de modelo.
   - Registrar la opción D1 como decisión de diseño pendiente para el humano (backlog o una
     futura feature). Cuando se apruebe, borrar el test espía.

## Observación O1 (no bloqueante, límite inherente)

G11 sobrevive: una clave fija de más en el `allowed` de `_check_payload`, compartido por los 6
modelos. El espía verifica los argumentos del helper, no lo que hace con ellos. Ninguna prueba
por sondeo puede verificar de forma completa "rechaza toda clave fuera de S". Es un límite
inherente de R35, no un hueco de conexión por campo o por modelo como P1–P3, y su probabilidad
real es muy baja. D1 no lo resuelve, pero tampoco lo empeora. No requiere cambios.

## Menores

- m1 (valoración de diseño, punto 5): endurecer `test_check_payload_admits_exactly_the_annex_a_keys`
  con `inspect.signature(...).bind(...)` y seleccionar la llamada por el argumento `model`, no
  por `call_args_list[0]`.
- m2: anotar en `progress/impl_core_domain_models.md`, sección "Desviaciones del spec", que el
  test de R35 depende del nombre y la firma de `_check_payload`, que design §"Helpers privados"
  declara orientativos. También anotar la decisión D1 pendiente.

## Trazabilidad afectada

- R27: [x] cubierto por
  `test_missing_required_keys_report_first_in_annex_a_order_for_every_model`,
  `test_missing_required_key_for_every_model_and_key` y la guarda
  `test_required_keys_by_model_matches_annex_a_order`. Todos los tests citados en la fila
  existen. El test eliminado solo se menciona como "sustituye a".
- R31: [x] cubierto por `test_unknown_enum_value_raises_validation_error_for_every_enum_field`
  (3 campos, G2 detectada).
- R35: [x] cubierto por `test_unknown_key_raises_validation_error_for_every_model`,
  `test_check_payload_admits_exactly_the_annex_a_keys`,
  `test_unknown_key_top_level_and_nested_raise_with_path` y
  `test_unknown_keys_with_mixed_types_do_not_raise_type_error`. Todos existen.
- Ninguna fila de la tabla de trazabilidad cita como evidencia vigente un test que ya no existe.
  Las menciones a tests eliminados que quedan son históricas, de secciones de rondas anteriores.

## Otras comprobaciones

- `make lint`: en verde (`ruff check`: All checks passed!; `ruff format --check`: 16 files
  already formatted).
- `make test-unit`: en verde (102 passed, 246 subtests passed).
- `./init.sh`: exit code 0 ("[OK] Entorno listo").
- `specs/core_domain_models/tasks.md`: sin tasks `[ ]`.
- `src/` sin cambios (hash y `git status`, como se indica arriba).

## Cambios requeridos

Ninguno bloqueante. Los menores m1 y m2 y la decisión D1 quedan a criterio del leader y del
humano.

---

# Ronda D12 — feature 2 `core_domain_models`

**Veredicto:** CHANGES_REQUESTED

Alcance: enmienda D12 (design §5 "D12", tasks T21–T26). Hay un único hallazgo bloqueante, H1,
y es solo de documentación en `progress/`: el código y los tests cumplen D12.

## Revisión de código (D12)

- `_payload_keys(cls)` (`src/geoagent/common/models.py:224`): recorre `fields(cls)` en orden de
  declaración, excluye `schema_version` por nombre y clasifica con `f.default is None`
  (criterio (b)). No toca `f.type`, así que la restricción de §10 queda intacta. Cumple T21.
- `_check_payload(cls, data, path=None)` (`:239`): `model = cls.__name__`; el orden de
  comprobación (Mapping → `schema_version` → claves desconocidas → obligatorias) no cambia. Los
  seis `from_dict()` llaman a `_check_payload(cls, data)` y ninguno pasa tuplas.
  `grep "required=\|optional="` sobre `src/` y `tests/` no da resultados. Cumple T22 y T26.
- `tests/unit/test_models.py`: el test espía y el import `mock` ya no están (cumple T23). Siguen
  la sonda `zz_unknown` (`test_unknown_key_raises_validation_error_for_every_model`) y la guarda
  `test_required_keys_by_model_matches_annex_a_order`.

## Mutaciones del revisor (copia en el scratchpad, `src/` real sin tocar)

Método: copia de `src/` y `tests/` en el scratchpad y `PYTHONPATH=<copia>/src`. En cada mutante
se comprobó que `geoagent.common.models.__file__` apunta a la copia. Una mutación cada vez.
`git status` sobre `src/` no cambia.

| # | Mutación | Resultado | Detectada por |
|---|---|---|---|
| SANITY | `JobSpec.from_dict` lanza `RuntimeError` | Detectada (62 failed) | varios |
| M1 | `required` invertido (`reversed`) | Detectada (21 subtests) | `test_missing_required_keys_report_first_in_annex_a_order_for_every_model` |
| M2 | no excluir `schema_version` | Sobrevive: equivalente | — |
| M3b | criterio invertido solo para `AgentInfo.agent_id` (granularidad de un campo opcional) | Detectada | `test_from_dict_without_optional_key_yields_none` [AgentInfo.agent_id] |
| M4 | `failure_cause` excluido de `required` y `optional` | Detectada (19) | `test_unknown_key_raises_validation_error_for_every_model` [JobResult], round-trips de `JobResult`, etc. |
| M5 | `schema_version` añadido a `optional` | Sobrevive: equivalente | — |
| M6 | criterio (c) `f.default is not MISSING` | Sobrevive: equivalente | — |

**¿Es correcta la justificación de M2?** Sí. Con la mutación, `_payload_keys(Job)` devuelve
`required = (..., 'created_at', 'schema_version')`. Eso no cambia ningún comportamiento
observable, por dos razones:
1. `_check_payload` comprueba si falta `"schema_version"` (línea 245) antes de recorrer
   `required`, así que el bucle nunca llega a informar de esa clave.
2. `allowed` ya incluye `{"schema_version"}` de forma explícita (línea 248).

Por tanto ningún test de comportamiento puede matar este mutante, y lo mismo vale para M5. M6 es
equivalente porque el único campo con un default distinto de `None` es `schema_version`, que ya
se excluye por nombre.

**¿Lo admite T24?** T24 pide "comprobar que los tests de comportamiento siguen detectando cada
mutación". Al pie de la letra no prevé mutantes equivalentes. Aun así, un mutante equivalente es
indetectable por definición sin volver a un test de implementación, que es justo lo que D12
elimina. El implementer lo documentó con una justificación correcta, que el revisor ha
verificado de forma independiente. Lo acepto como cumplimiento de T24. Las otras dos mutaciones
que pide T24 (orden y criterio) se detectan, y el criterio se detecta también campo a campo
(M3b). Recomendación no bloqueante: que el leader añada a T24 o a D12 una línea que reconozca
que la exclusión de `schema_version` es defensiva y no observable.

## Hallazgos

1. **H1 (bloqueante, C6) — el mapa `R<n> → test` cita un test eliminado.** En
   `progress/impl_core_domain_models.md`, línea 91 (fila R35 de la tabla de trazabilidad), sigue
   apareciendo `test_check_payload_admits_exactly_the_annex_a_keys` como evidencia vigente de
   R35, con la explicación de `mock.patch.object`. Ese test ya no existe (T23). La ronda 4
   quater exigía que "ninguna fila cite como evidencia vigente un test que ya no existe", y C6
   exige que el mapa esté documentado. R35 sigue cubierta por los otros tres tests de la fila,
   así que la cobertura no se pierde; lo que hay que arreglar es solo el mapa.
   Arreglo: quitar ese test de la fila R35 y, si se quiere, añadir "(la clase de bug de tupla
   desincronizada es imposible por construcción desde D12)". El arreglo está en `progress/`, así
   que puede hacerlo el leader sin lanzar al implementer.
2. **m1 (no bloqueante) — T26 sin constancia de `./init.sh`.** La sección "Verificación final
   (T26)" del informe solo menciona `make lint` y `make test-unit`. El revisor ejecutó
   `./init.sh`: exit 0, `[OK] Entorno listo`. Basta con dejar constancia.
3. **n1 (nit) — erratas en un comentario.** `tests/unit/test_models.py`, en
   `test_from_dict_without_optional_key_yields_none`, dice "producen `None` n los 3 ecampos
   opcionales". Se corrige cuando se vuelva a tocar el archivo; no requiere otra ronda.

## Trazabilidad requirements ↔ tests (afectados por D12)

- R27: [x] `test_missing_required_key_for_every_model_and_key`,
  `test_missing_required_keys_report_first_in_annex_a_order_for_every_model`,
  `test_missing_required_key_raises_validation_error`,
  `test_missing_key_inside_spec_reports_prefixed_field`, más la guarda
  `test_required_keys_by_model_matches_annex_a_order`. Todos van por `from_dict()`.
- R28: [x] `test_from_dict_without_optional_key_yields_none` (los 3 campos opcionales; borra la
  clave y llama a `from_dict()`).
- R35: [x] `test_unknown_key_raises_validation_error_for_every_model` (sonda `zz_unknown`, 6
  modelos), `test_unknown_key_top_level_and_nested_raise_with_path`,
  `test_unknown_keys_with_mixed_types_do_not_raise_type_error`. La cobertura es real, pero el
  mapa documentado está desactualizado (H1).
- El resto de `R<n>` no cambia respecto a la ronda 4 quater (D12 no toca su código ni sus tests).

## Tasks completas

- T1–T20: [x] (sin cambios)
- T21: [x]
- T22: [x]
- T23: [x]
- T24: [x] (M2 equivalente aceptado; ver arriba)
- T25: [x] ("Desviaciones del spec" registra D12 y cierra m2. Pero el mapa de trazabilidad
  del mismo archivo no se actualizó: H1)
- T26: [x] (lint y test-unit en verde, sin tuplas residuales; falta constancia de `./init.sh`: m1)

## Checkpoints

- C1: [x] `./init.sh` exit 0.
- C2: [x] Una sola feature en `in_progress` (la otra coincidencia de `grep` es la lista
  `valid_status`).
- C3: [x] Sin dependencias nuevas, sin `print()`, sin secretos.
- C4: [~] `make test-unit` en verde (101 passed, 240 subtests, ~0.5 s), sin red ni mocks de
  filesystem. La cobertura ≥ 85% no se puede medir porque `pytest-cov` no está instalado
  (pendiente de infraestructura, igual que en rondas anteriores, m8).
- C5: [x] Solo `__pycache__` ignorados. Estado `in_progress` correcto.
- C6: [ ] Specs y tasks OK, pero el mapa `R<n> → test` de `progress/impl_core_domain_models.md`
  cita como vigente un test eliminado (H1).

## Otras comprobaciones

- `make lint`: en verde (`ruff check`: All checks passed!; `ruff format --check`: 16 files
  already formatted).
- `make test-unit`: en verde (101 passed, 240 subtests passed).
- `./init.sh`: exit 0.

## Cambios requeridos

1. H1: quitar `test_check_payload_admits_exactly_the_annex_a_keys` de la fila R35 de la tabla
   de trazabilidad de `progress/impl_core_domain_models.md` (línea 91). Con eso, y sin tocar
   código, esta ronda pasa a APPROVED.
2. (Opcional) m1: dejar constancia de `./init.sh` en "Verificación final (T26)".
