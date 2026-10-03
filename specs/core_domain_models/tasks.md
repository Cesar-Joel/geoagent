# Tasks — feature 2 `core_domain_models`

> Ejecutar en orden. Marcar `[x]` al completar cada task. Referencias: `requirements.md`
> (R<n> y Anexo A) y `design.md` (§ secciones).
> Tests: clases `Test<Cosa>(unittest.TestCase)` ejecutadas con pytest. Construir los modelos con
> argumentos nombrados. Sin IO ni reloj real: timestamps fijos construidos a mano.

## Excepciones

- [x] T1 — Crear `src/geoagent/common/errors.py` con `GeoAgentError(Exception)`,
  `ValidationError(GeoAgentError)` con atributos `message` y `field` (por defecto `None`) y
  `UnknownSchemaVersionError(ValidationError)` con atributos `model` y `version` y `field` por
  defecto `"schema_version"` (design §3). Cubre: R2, R3, R4.
- [x] T2 — Crear `tests/unit/test_errors.py` con `TestErrorHierarchy`: `issubclass` de las tres
  clases (`ValidationError` → `GeoAgentError` → `Exception`; `UnknownSchemaVersionError` →
  `ValidationError`), atributos `field`, `model` y `version`, y que `str(exc)` incluye el
  `field`. Cubre: R2, R3, R4.

## Enums y máquina de estados

- [x] T3 — Crear `src/geoagent/common/models.py` con la cabecera de módulo
  (`docs/conventions.md`), las constantes `SCHEMA_VERSION` y `SUPPORTED_SCHEMA_VERSIONS`,
  `JobStatus(str, Enum)` con la propiedad `is_terminal`, `FailureCause(str, Enum)`, la tabla
  inmutable `_VALID_TRANSITIONS` y `can_transition(from_status, to_status)`, que lanza
  `ValidationError` si algún argumento no es miembro de `JobStatus` (design §5 y §6).
  Cubre: R7, R8, R9, R10, R11, R12.
- [x] T4 — Crear `tests/unit/test_models.py` con:
  - `TestJobStatus`: conjunto exacto de valores e `is_terminal` para los 6 miembros (R7, R10).
  - `TestFailureCause`: conjunto exacto de valores (R12).
  - `TestCanTransition`: recorre con `subTest` los 36 pares `JobStatus × JobStatus`. Espera `True`
    exactamente para los 10 pares de R8 y `False` para los otros 26, incluidas las
    autotransiciones y toda salida de un estado terminal (R8, R9). Además,
    `can_transition("queued", JobStatus.ASSIGNED)`, `can_transition(JobStatus.QUEUED, None)` y
    `can_transition(JobStatus.QUEUED, "assigned")` lanzan `ValidationError` (R11).

  Cubre: R7, R8, R9, R10, R11, R12.

## Helpers de validación y timestamps

- [x] T5 — Implementar en `models.py` los helpers privados de validación de tipos y
  restricciones (`str` no vacía, `int` no `bool` con mínimo, número finito normalizado a
  `float`, enum miembro y enum desde cadena, tupla de `str`, tupla de números, mapping de solo
  lectura `str` → `float`) y los de versión y payload (`_check_version`, `_check_payload` con el
  orden de design §5: Mapping → presencia y tipo de `schema_version` → versión soportada → claves
  desconocidas → obligatorias ausentes). Cubre: R6, R18, R19, R20, R26, R27, R29, R30, R31, R35.
- [x] T6 — Implementar `_require_datetime` (aware → UTC; naive → `ValidationError`),
  `_format_timestamp` (`isoformat(timespec="microseconds")` + `Z`) y `_parse_timestamp` (regex
  `[0-9]` con `fullmatch`, fracción de 1 a 6 dígitos rellenada, `Z` / `±HH:MM`, `ValueError` →
  `ValidationError`), sin `datetime.fromisoformat` (design §8). Cubre: R21, R22, R23, R24, R25.

## Modelos

- [x] T7 — Implementar `JobSpec` y `JobProgress` como `@dataclass(frozen=True)` con los campos y
  el orden del Anexo A, `__post_init__` (validación y normalización con `object.__setattr__`),
  `to_dict()` y `from_dict()`. `JobSpec` no valida aridad de `region`, orden del rango temporal ni
  catálogo de `operation`. `JobProgress` valida `0 ≤ percent ≤ 100`.
  Cubre: R1, R5, R6, R13, R14, R17, R18, R19, R20, R21, R22, R23, R24, R25, R26, R27, R29, R30,
  R32, R35, R36.
- [x] T8 — Implementar `Job` con `spec: JobSpec` anidado: `to_dict()` emite `spec.to_dict()` y
  `status.value`; `from_dict()` delega en `JobSpec.from_dict` y relanza los errores anidados con
  la misma clase y `field` prefijado con `spec.` (design §5, "Rutas anidadas"). `assigned_agent_id`
  es opcional. Cubre: R1, R4, R5, R13, R14, R15, R16, R17, R18, R26, R27, R28, R29, R30, R31, R35.
- [x] T9 — Implementar `JobResult`: `status` restringido a `succeeded` / `failed`, coherencia de
  `failure_cause`, `observation_count ≥ 0`, `metrics` como mapping de solo lectura (se admite
  `{}`) y serialización de enums con `.value`.
  Cubre: R1, R5, R6, R13, R14, R15, R17, R28, R29, R30, R31, R33, R34, R35.
- [x] T10 — Implementar `AgentInfo` (con `capabilities` como tupla y `agent_id` opcional) y
  `Heartbeat` (con `running_job_ids` como tupla y `resource_usage` como mapping de solo lectura).
  Cubre: R1, R5, R6, R13, R14, R17, R28, R29, R30, R35.

## Tests de modelos (en `tests/unit/test_models.py`)

- [x] T11 — `TestModelFields`: para cada uno de los seis modelos, el conjunto y el orden de
  `dataclasses.fields()` coinciden con el Anexo A, y `schema_version` vale `SCHEMA_VERSION` por
  defecto. Cubre: R1, R13.
- [x] T12 — `TestImmutability`: asignar y borrar un atributo lanza `FrozenInstanceError` en los
  seis modelos y deja la instancia igual. Mutar la `list` o el `dict` pasados al constructor no
  altera la instancia. Los campos de colección son `tuple` o rechazan
  `instance.metrics["k"] = 1.0` con `TypeError`. Cubre: R5, R6.
- [x] T13 — `TestRoundTrip`: para cada modelo, con al menos una instancia con opcionales a
  `None` y otra con opcionales informados (incluido un `JobResult` `failed` con causa), comprobar
  que `from_dict(x.to_dict()) == x` y `from_dict(json.loads(json.dumps(x.to_dict()))) == x`.
  Además: las claves de `to_dict()` son exactamente las del Anexo A, todos los valores son de
  tipos JSON (recorrido recursivo), dos llamadas devuelven dicts distintos (`is not`), los enums
  salen como `"queued"` / `"timeout"`, `Job.to_dict()["spec"] == spec.to_dict()` y un payload sin
  claves opcionales produce `None`. Cubre: R14, R15, R16, R17, R28.
- [x] T14 — `TestSchemaVersion`:
  - `from_dict` con `schema_version` 0, 2 y 999 lanza `UnknownSchemaVersionError` con `model` y
    `version` correctos, también cuando al payload le faltan campos o tiene claves extra (R18).
  - `Job.from_dict` con `spec.schema_version = 2` lanza `UnknownSchemaVersionError` con
    `field == "spec.schema_version"` (R18, R4).
  - Constructor con `schema_version=2` lanza `UnknownSchemaVersionError` (R19).
  - Payload sin `schema_version` o con `True`, `"1"` o `1.0` lanza `ValidationError` que no es
    `UnknownSchemaVersionError` (R20).

  Cubre: R4, R18, R19, R20.
- [x] T15 — `TestTimestamps` (a través de `Heartbeat.sent_at`, `JobSpec.time_start` y
  `Job.created_at`):
  - Serialización exacta: `2026-09-14T10:00:00.000000Z`, microsegundos y un año < 1000 con
    relleno (R21).
  - Constructor con `+02:00` guarda el mismo instante con `tzinfo is timezone.utc` (R22).
  - `from_dict` acepta `Z`, `+00:00`, `-05:30` y fracciones de 1, 3 y 6 dígitos, y produce UTC
    con el instante correcto (R23).
  - Constructor con datetime naive lanza `ValidationError` con `field` (R24).
  - `from_dict` rechaza con `ValidationError` y `field`: sin zona, `z` minúscula, espacio en
    lugar de `T`, 7 dígitos de fracción, mes 13, `25:00:00`, offset `+24:00`, dígitos no ASCII y
    valores no `str` (R25).

  Cubre: R21, R22, R23, R24, R25.
- [x] T16 — `TestPayloadValidation`:
  - Payload no Mapping (`None`, `[]`, `"x"`) lanza `ValidationError` con `field is None`, y
    `spec` no Mapping da `field == "spec"` (R26).
  - Para cada modelo y cada clave obligatoria, eliminarla lanza `ValidationError` (y nunca
    `KeyError` / `TypeError`) con `field` igual a esa clave. Con varias ausentes, la primera del
    Anexo A. Una ausente en `spec` da `field == "spec.dataset"` (R27, R4).
  - Tipos incorrectos en constructor y `from_dict`: `None` en un obligatorio, `True` en un
    numérico, `1.5` en `observation_count`, `"queued"` como `status` en el constructor, `str` en
    `capabilities`, elemento no `str` en `running_job_ids`, valor no numérico en `metrics`
    (R29).
  - Restricciones: `""` en `job_id` / `hostname` / clave de `resource_usage`, `nan` e `inf` en
    `region` y `metrics`, `observation_count = -1` (R30).
  - Valor de enum desconocido en `from_dict` (`"paused"`, `"oom"`) lanza `ValidationError`, no
    `ValueError` (R31).
  - Clave desconocida en el nivel superior y dentro de `spec` lanza `ValidationError` con la ruta
    (R35).

  Cubre: R4, R26, R27, R29, R30, R31, R35.
- [x] T17 — `TestJobProgress`, `TestJobResult` y `TestJobSpecBoundary`:
  - `percent` −0.1, 100.1 y `nan` fallan con `field == "percent"`; 0 y 100 son válidos; un
    `int` se normaliza a `float` (R32).
  - `JobResult` con `status` `queued` / `running` / `cancelled` falla con `field == "status"`
    (R33).
  - `failed` sin causa y `succeeded` con causa fallan con `field == "failure_cause"` (R34).
  - `JobSpec` con `time_end < time_start`, `region=()`, `region` de 3 o 5 números y
    `operation="unknown_op"` se construye sin excepción (R36).

  Cubre: R32, R33, R34, R36.

## Verificación y trazabilidad

- [x] T18 — Revisar que `models.py` y `errors.py` no importan módulos de IO ni usan
  `typing.get_type_hints`, `datetime.fromisoformat`, `datetime.UTC`, `StrEnum`, `match`,
  `slots=` o `kw_only=` (design §10), y que no hay `print()`. Cubre: R1, R21, R23.
- [x] T19 — Documentar en `progress/impl_core_domain_models.md` la trazabilidad `R1…R36 → test`
  (nombre de clase y método) y la tabla Acceptance → evidencia. Cubre: R1–R36.
- [x] T20 — Verificación final: `make lint` sin errores, `make test-unit` en verde y `./init.sh`
  terminando con `[OK] Entorno listo`. Si hay un intérprete 3.9 local, ejecutar además
  `python3.9 -m pytest tests/unit -q`; si no, dejar constancia de que la matriz 3.9/3.14 de CI es
  la verificación de compatibilidad. Cubre: R1–R36.

## Enmienda D12 — derivar `required`/`optional` de `dataclasses.fields(cls)`

> Formaliza la opción D1 de "Ronda 4 quater" en `progress/review_core_domain_models.md`. Ver
> `design.md` §5 ("Helpers privados" y la sección "D12") para el diseño completo. Ninguna task
> de esta sección toca comportamiento observable nuevo: R27, R28 y R35 no cambian de redacción
> (ver `requirements.md`, sin cambios).

- [x] T21 — Implementar `_payload_keys(cls: type) -> tuple[tuple[str, ...], tuple[str, ...]]`
  en `src/geoagent/common/models.py`: recorre `dataclasses.fields(cls)` en orden de declaración,
  excluye `schema_version` por nombre y clasifica cada campo restante como `optional` si
  `f.default is None`, o como `required` en caso contrario (design §5, "D12", criterio (b)).
  Cubre: R27, R28, R35.
- [x] T22 — Cambiar la firma de `_check_payload` a
  `_check_payload(cls: type, data: object, path: str | None = None) -> Mapping[str, Any]`: usa
  `cls.__name__` como `model` y `_payload_keys(cls)` para obtener `required`/`optional`; sin
  cambios en el orden de comprobación (Mapping → `schema_version` → claves desconocidas → claves
  obligatorias, design §5 pasos 1–5). Actualizar los seis `from_dict()`
  (`JobSpec`, `Job`, `JobProgress`, `JobResult`, `AgentInfo`, `Heartbeat`) para llamar
  `_check_payload(cls, data, path)` sin pasar tuplas escritas a mano. Sin cambio de
  comportamiento observable: `test-unit` debe seguir en verde sin tocar ningún test de
  comportamiento. Cubre: R1, R17, R18, R19, R20, R26, R27, R28, R35.
- [x] T23 — En `tests/unit/test_models.py`, eliminar
  `test_check_payload_admits_exactly_the_annex_a_keys` (el test espía con `mock.patch.object`
  sobre `_check_payload`; design §5, "D12"). Mantener sin modificar la sonda `zz_unknown`
  (el test que añade una clave `"zz_unknown"` al payload de cada modelo y comprueba
  `ValidationError` con `field == "zz_unknown"`) y la guarda
  `test_required_keys_by_model_matches_annex_a_order` (compara `_REQUIRED_KEYS_BY_MODEL` contra
  `fields(model)`; vive en `tests/`, no le aplica la restricción de `design.md` §10 sobre
  inspeccionar `.type` en `src/`). Cubre: R27, R35.
- [x] T24 — Verificación por mutación de D12, sobre una copia de `src/` y `tests/` en el
  scratchpad (nunca sobre `src/` real; mismo método que "Método de mutación" en "Ronda 4 quater"
  de `progress/review_core_domain_models.md`):
  - Mutar `_payload_keys` para invertir el orden de dos campos de un modelo, para no excluir
    `schema_version`, o para invertir el criterio (`f.default is None` → `f.default is not
    None`) en un campo opcional, y comprobar que los tests de comportamiento existentes
    (R27, R28, R35) siguen detectando cada mutación una a una.
  - Confirmar, como control de "refactor sin bug", que renombrar `_payload_keys` o
    `_check_payload`, o reordenar sus parámetros posicionales por unos equivalentes, **ya no
    rompe ningún test**, a diferencia de RF1–RF3 de la ronda anterior. Esto es la evidencia de
    que D12 cumple su objetivo.
  - Documentar la tabla de mutaciones (mutación, resultado, test que falla o "sobrevive") en
    `progress/impl_core_domain_models.md`, igual que la tabla de "Ronda 4 quater".
  Cubre: R27, R28, R35.
- [x] T25 — Actualizar `progress/impl_core_domain_models.md`, sección "Desviaciones del spec":
  registrar que se aplicó la enmienda D12 (`specs/core_domain_models/design.md` §5), aprobada
  por el humano a partir de la opción D1 de "Ronda 4 quater" en
  `progress/review_core_domain_models.md`, y cerrar la nota m2 de esa misma ronda (el
  acoplamiento del test espía al nombre y la firma de `_check_payload`), indicando que el test
  se eliminó (T23) y por qué la advertencia ya no aplica. Cubre: documentación de m2 (sin `R<n>`
  directo).
- [x] T26 — Verificación final tras el refactor de D12: `make lint` sin errores, `make
  test-unit` en verde, `./init.sh` con `[OK] Entorno listo` y `src/` / `tests/` sin quedar con
  ninguna referencia residual a las tuplas `required=`/`optional=` escritas a mano en los seis
  `from_dict()`. Cubre: R1–R36.
