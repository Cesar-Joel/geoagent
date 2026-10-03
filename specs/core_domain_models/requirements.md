# Requirements — feature 2 `core_domain_models`

> Feature: **2 — Modelos de dominio compartidos** (`"sdd": true`).
> Notación: EARS estricto (ver `docs/specs.md`). Un único `DEBE` / `NO DEBE` por requirement.
> Los nombres, tipos y restricciones de los campos de cada modelo están en el **Anexo A**, que
> forma parte de estos requirements. El origen de cada campo y su justificación están en
> `design.md` §4.

## Glosario

- **Modelo**: cualquiera de las seis clases `AgentInfo`, `Job`, `JobSpec`, `JobProgress`,
  `JobResult` y `Heartbeat`.
- **Payload**: valor que recibe `from_dict()`.
- **Sub-payload**: payload anidado dentro de otro. En esta feature solo existe el campo `spec`
  de `Job`, que contiene un payload de `JobSpec`.
- **Ruta de campo**: nombre del campo en el nivel superior (`job_id`) o nombres unidos por `.`
  en un sub-payload (`spec.dataset`).
- **Datetime aware**: `datetime` con `tzinfo` distinto de `None` y `utcoffset()` distinto de
  `None`. **Naive**: cualquier otro `datetime`.
- `SCHEMA_VERSION` y `SUPPORTED_SCHEMA_VERSIONS`: constantes de `src/geoagent/common/models.py`,
  con valores `1` y `frozenset({1})` en esta feature.

---

## 1. Módulos y excepciones

### R1
El sistema DEBE exponer en `src/geoagent/common/models.py` las clases `AgentInfo`, `Job`,
`JobSpec`, `JobProgress`, `JobResult` y `Heartbeat`, cada una con exactamente los campos que
declara para ella el Anexo A.

### R2
El sistema DEBE definir en `src/geoagent/common/errors.py` la excepción `ValidationError` como
subclase de `GeoAgentError`, que a su vez es subclase directa de `Exception`.

### R3
El sistema DEBE definir en `src/geoagent/common/errors.py` la excepción
`UnknownSchemaVersionError` como subclase de `ValidationError`, con los atributos `model`
(nombre de la clase del modelo) y `version` (valor de `schema_version` recibido).

### R4
CUANDO un modelo lanza `ValidationError`, o una subclase, a causa de un campo concreto, el
sistema DEBE exponer en el atributo `field` de la excepción la ruta de ese campo.

## 2. Inmutabilidad

### R5
SI un código cliente asigna o borra un atributo de una instancia de un modelo ENTONCES el
sistema DEBE lanzar `dataclasses.FrozenInstanceError` y dejar la instancia sin cambios.

### R6
CUANDO se construye un modelo con una `list`, `tuple` o `dict` en un campo de colección del
Anexo A, el sistema DEBE almacenar una copia de solo lectura (`tuple` para las secuencias y un
mapping que rechaza la asignación de claves para los `dict`) que no cambia si se muta el
objeto original.

## 3. Estados de job y causas de fallo

### R7
El sistema DEBE definir en `src/geoagent/common/models.py` el enum `JobStatus` con exactamente
los valores `queued`, `assigned`, `running`, `succeeded`, `failed` y `cancelled`.

### R8
CUANDO se invoca `can_transition(from_status, to_status)` con uno de estos pares, el sistema
DEBE devolver `True`: `queued→assigned`, `queued→cancelled`, `assigned→running`,
`assigned→queued`, `assigned→failed`, `assigned→cancelled`, `running→succeeded`,
`running→failed`, `running→cancelled` y `running→queued`.

### R9
CUANDO se invoca `can_transition(from_status, to_status)` con dos miembros de `JobStatus` que
no forman uno de los pares de R8 (incluidos los pares de un estado consigo mismo y todo par
cuyo origen es `succeeded`, `failed` o `cancelled`), el sistema DEBE devolver `False`.

### R10
CUANDO se consulta la propiedad `is_terminal` de un miembro de `JobStatus`, el sistema DEBE
devolver `True` exactamente para `succeeded`, `failed` y `cancelled`, y `False` para el resto.

### R11
SI `can_transition` recibe como `from_status` o `to_status` un valor que no es miembro de
`JobStatus` (incluida su cadena equivalente, p. ej. `"queued"`) ENTONCES el sistema DEBE lanzar
`ValidationError`.

### R12
El sistema DEBE definir en `src/geoagent/common/models.py` el enum `FailureCause` con
exactamente los valores `network`, `timeout`, `data_source`, `resource_exhausted`, `bad_spec`,
`agent_crash` y `retries_exhausted`.

## 4. Versionado y serialización

### R13
El sistema DEBE dotar a cada modelo de un campo `schema_version` de tipo `int` cuyo valor por
defecto en el constructor es `SCHEMA_VERSION`.

### R14
CUANDO se invoca `to_dict()` sobre una instancia de un modelo, el sistema DEBE devolver un
`dict` nuevo cuyas claves son exactamente los nombres de campo del Anexo A para ese modelo y
cuyos valores son solo de tipos JSON (`dict`, `list`, `str`, `int`, `float`, `bool` o `None`).

### R15
CUANDO `to_dict()` serializa un campo de tipo `JobStatus` o `FailureCause`, el sistema DEBE
emitir el atributo `.value` del miembro (p. ej. `"queued"`).

### R16
CUANDO `Job.to_dict()` serializa el campo `spec`, el sistema DEBE emitir el resultado de
`JobSpec.to_dict()` de ese valor, incluido su propio `schema_version`.

### R17
CUANDO `from_dict()` de un modelo recibe la salida de `to_dict()` de una instancia de ese
modelo, directamente o tras `json.loads(json.dumps(...))`, el sistema DEBE devolver una
instancia igual (`==`) a la original.

### R18
SI `from_dict()` recibe un payload o un sub-payload cuyo `schema_version` es un `int` (no
`bool`) que no pertenece a `SUPPORTED_SCHEMA_VERSIONS` ENTONCES el sistema DEBE lanzar
`UnknownSchemaVersionError`, aunque el resto del payload sea inválido.

### R19
SI se invoca el constructor de un modelo con un `schema_version` de tipo `int` que no pertenece
a `SUPPORTED_SCHEMA_VERSIONS` ENTONCES el sistema DEBE lanzar `UnknownSchemaVersionError`.

### R20
SI `from_dict()` recibe un payload sin la clave `schema_version`, o con un `schema_version` que
no es `int` (incluidos `bool`, `str` y `float`) ENTONCES el sistema DEBE lanzar un
`ValidationError` que no es instancia de `UnknownSchemaVersionError` y cuyo `field` termina en
`schema_version`.

## 5. Timestamps

### R21
CUANDO `to_dict()` serializa un campo `datetime`, el sistema DEBE emitir una cadena ISO 8601 en
UTC con el formato fijo `YYYY-MM-DDTHH:MM:SS.ffffffZ`, con seis dígitos de microsegundos y
sufijo `Z`.

### R22
CUANDO se construye un modelo con un datetime aware de cualquier offset en un campo `datetime`,
el sistema DEBE almacenar el mismo instante con `tzinfo` igual a `datetime.timezone.utc`.

### R23
CUANDO `from_dict()` recibe en un campo `datetime` una cadena que cumple la gramática
`YYYY-MM-DDTHH:MM:SS[.F]Z` o `YYYY-MM-DDTHH:MM:SS[.F]±HH:MM`, con `F` de 1 a 6 dígitos ASCII,
el sistema DEBE producir un `datetime` con `tzinfo` igual a `datetime.timezone.utc` que
representa el mismo instante.

### R24
SI se invoca el constructor de un modelo con un datetime naive en un campo `datetime` ENTONCES
el sistema DEBE lanzar `ValidationError` con `field` igual a la ruta de ese campo.

### R25
SI `from_dict()` recibe en un campo `datetime` un valor que no es `str`, una cadena sin
designador de zona horaria, una cadena fuera de la gramática de R23 o una cadena con una fecha,
hora u offset inexistentes ENTONCES el sistema DEBE lanzar `ValidationError` con `field` igual
a la ruta de ese campo.

## 6. Validación de payloads y campos

### R26
SI `from_dict()` recibe como payload o sub-payload un valor que no es
`collections.abc.Mapping` ENTONCES el sistema DEBE lanzar `ValidationError` con `field` igual a
`None` en el nivel superior o a la ruta del sub-payload (`spec`) si está anidado.

### R27
SI `from_dict()` recibe un payload o sub-payload al que le falta una clave obligatoria según el
Anexo A ENTONCES el sistema DEBE lanzar `ValidationError`, y no `KeyError` ni `TypeError`, con
`field` igual a la ruta de la primera clave ausente en el orden del Anexo A.

### R28
CUANDO `from_dict()` recibe un payload sin una clave marcada como opcional en el Anexo A, el
sistema DEBE construir la instancia con `None` en ese campo.

### R29
SI un campo recibe, en el constructor o en `from_dict()`, un valor cuyo tipo no coincide con el
del Anexo A (incluidos `None` en un campo obligatorio, `bool` en un campo numérico, `float` en
un campo `int` y un elemento o valor de colección de tipo incorrecto) ENTONCES el sistema DEBE
lanzar `ValidationError`, y no `TypeError`, con `field` igual a la ruta de ese campo.

### R30
SI un campo recibe, en el constructor o en `from_dict()`, un valor del tipo correcto que
incumple las restricciones "no vacía", "finito" o "≥ 0" del Anexo A ENTONCES el sistema DEBE
lanzar `ValidationError` con `field` igual a la ruta de ese campo.

### R31
SI `from_dict()` recibe en un campo `JobStatus` o `FailureCause` una cadena que no es el valor
de ningún miembro del enum ENTONCES el sistema DEBE lanzar `ValidationError`, y no
`ValueError`, con `field` igual a la ruta de ese campo.

### R32
SI `JobProgress` recibe, en el constructor o en `from_dict()`, un `percent` menor que `0`,
mayor que `100` o no finito ENTONCES el sistema DEBE lanzar `ValidationError` con `field` igual
a `percent`.

### R33
SI `JobResult` recibe, en el constructor o en `from_dict()`, un `status` distinto de
`succeeded` y `failed` ENTONCES el sistema DEBE lanzar `ValidationError` con `field` igual a
`status`.

### R34
SI `JobResult` recibe un `status` `failed` con `failure_cause` igual a `None`, o un `status`
`succeeded` con `failure_cause` distinto de `None`, ENTONCES el sistema DEBE lanzar
`ValidationError` con `field` igual a `failure_cause`.

### R35
SI `from_dict()` recibe un payload o sub-payload con una clave que no figura en el Anexo A para
ese modelo ENTONCES el sistema DEBE lanzar `ValidationError` con `field` igual a la ruta de esa
clave.

### R36
CUANDO se construye un `JobSpec` con tipos válidos pero con `time_end` anterior a
`time_start`, con una `region` de cualquier longitud (incluida vacía) o con una `operation` no
vacía que no corresponde a ninguna operación implementada, el sistema NO DEBE lanzar ninguna
excepción.

---

## Anexo A — Campos de los modelos (normativo)

Convenciones de la tabla:

- **Obligatorio** se refiere al payload de `from_dict()`. `schema_version` es obligatorio en el
  payload aunque el constructor tenga valor por defecto (R13). Los campos opcionales tienen
  `None` como valor por defecto en el constructor.
- `str` "no vacía" significa `len(value) > 0`.
- **Número** significa `int` o `float` que no es `bool`. Se almacena normalizado a `float`.
  "Finito" excluye `nan`, `inf` y `-inf`.
- `int` excluye `bool`.
- En los campos de colección, el tipo y la restricción se aplican a cada elemento o valor, y el
  `field` del error es la ruta del campo, sin índice ni clave.
- **Colección** indica los campos a los que aplica R6.

### `JobSpec`

| Orden | Campo            | Tipo en memoria         | Tipo JSON         | Obligatorio | Restricción básica | Colección |
|-------|------------------|-------------------------|-------------------|-------------|--------------------|-----------|
| 1     | `dataset`        | `str`                   | string            | sí          | no vacía           | no        |
| 2     | `region`         | `tuple[float, ...]`     | array de number   | sí          | cada elemento finito | sí      |
| 3     | `time_start`     | `datetime` (UTC)        | string (R21)      | sí          | —                  | no        |
| 4     | `time_end`       | `datetime` (UTC)        | string (R21)      | sí          | —                  | no        |
| 5     | `operation`      | `str`                   | string            | sí          | no vacía           | no        |
| 6     | `schema_version` | `int`                   | integer           | sí          | R18 / R19          | no        |

### `Job`

| Orden | Campo               | Tipo en memoria  | Tipo JSON          | Obligatorio | Restricción básica | Colección |
|-------|---------------------|------------------|--------------------|-------------|--------------------|-----------|
| 1     | `job_id`            | `str`            | string             | sí          | no vacía           | no        |
| 2     | `spec`              | `JobSpec`        | object (R16)       | sí          | —                  | no        |
| 3     | `status`            | `JobStatus`      | string             | sí          | miembro del enum   | no        |
| 4     | `created_at`        | `datetime` (UTC) | string (R21)       | sí          | —                  | no        |
| 5     | `assigned_agent_id` | `str` o `None`   | string o null      | no          | no vacía si es `str` | no      |
| 6     | `schema_version`    | `int`            | integer            | sí          | R18 / R19          | no        |

### `JobProgress`

| Orden | Campo            | Tipo en memoria | Tipo JSON | Obligatorio | Restricción básica          | Colección |
|-------|------------------|-----------------|-----------|-------------|-----------------------------|-----------|
| 1     | `job_id`         | `str`           | string    | sí          | no vacía                    | no        |
| 2     | `percent`        | número (`float`) | number   | sí          | finito, `0 ≤ percent ≤ 100` (R32) | no  |
| 3     | `message`        | `str`           | string    | sí          | — (se admite `""`)          | no        |
| 4     | `schema_version` | `int`           | integer   | sí          | R18 / R19                   | no        |

### `JobResult`

| Orden | Campo               | Tipo en memoria           | Tipo JSON          | Obligatorio | Restricción básica                     | Colección |
|-------|---------------------|---------------------------|--------------------|-------------|----------------------------------------|-----------|
| 1     | `job_id`            | `str`                     | string             | sí          | no vacía                               | no        |
| 2     | `partition_id`      | `str`                     | string             | sí          | no vacía                               | no        |
| 3     | `status`            | `JobStatus`               | string             | sí          | `succeeded` o `failed` (R33)           | no        |
| 4     | `observation_count` | `int`                     | integer            | sí          | ≥ 0                                    | no        |
| 5     | `metrics`           | mapping `str` → `float`   | object de number   | sí          | claves no vacías, valores finitos (se admite `{}`) | sí |
| 6     | `finished_at`       | `datetime` (UTC)          | string (R21)       | sí          | —                                      | no        |
| 7     | `failure_cause`     | `FailureCause` o `None`   | string o null      | no          | coherente con `status` (R34)           | no        |
| 8     | `schema_version`    | `int`                     | integer            | sí          | R18 / R19                              | no        |

### `AgentInfo`

| Orden | Campo            | Tipo en memoria    | Tipo JSON        | Obligatorio | Restricción básica           | Colección |
|-------|------------------|--------------------|------------------|-------------|------------------------------|-----------|
| 1     | `hostname`       | `str`              | string           | sí          | no vacía                     | no        |
| 2     | `agent_version`  | `str`              | string           | sí          | no vacía                     | no        |
| 3     | `platform`       | `str`              | string           | sí          | no vacía                     | no        |
| 4     | `capabilities`   | `tuple[str, ...]`  | array de string  | sí          | cada elemento no vacío (se admite `[]`) | sí |
| 5     | `agent_id`       | `str` o `None`     | string o null    | no          | no vacía si es `str`         | no        |
| 6     | `schema_version` | `int`              | integer          | sí          | R18 / R19                    | no        |

### `Heartbeat`

| Orden | Campo             | Tipo en memoria         | Tipo JSON         | Obligatorio | Restricción básica                  | Colección |
|-------|-------------------|-------------------------|-------------------|-------------|-------------------------------------|-----------|
| 1     | `agent_id`        | `str`                   | string            | sí          | no vacía                            | no        |
| 2     | `sent_at`         | `datetime` (UTC)        | string (R21)      | sí          | —                                   | no        |
| 3     | `status`          | `str`                   | string            | sí          | no vacía                            | no        |
| 4     | `running_job_ids` | `tuple[str, ...]`       | array de string   | sí          | cada elemento no vacío (se admite `[]`) | sí    |
| 5     | `resource_usage`  | mapping `str` → `float` | object de number  | sí          | claves no vacías, valores finitos (se admite `{}`) | sí |
| 6     | `schema_version`  | `int`                   | integer           | sí          | R18 / R19                           | no        |

---

## Fuera de alcance (no son requirements de esta feature)

Estas validaciones y comportamientos pertenecen a otras features. Esta feature NO los
implementa y R36 fija la frontera para `JobSpec`:

- Forma, aridad, orden y rangos de `region` y respuesta 422 por región mal formada → feature 8
  (`job_manager`) y feature 14 (`geo_job_operations`).
- Rango temporal invertido y catálogo de operaciones conocidas → features 8 y 12.
- Persistencia de transiciones con timestamp y actor y respuesta 409 → feature 8.
- Estados `online` / `stale` / `offline` del fleet → features 6 y 10.
- Conjunto de valores de `Heartbeat.status` y claves concretas de `resource_usage` →
  features 10, 18 y 19.
- Esquema concreto de `JobResult.metrics` (`docs/results_schema.md`) → feature 14.
- Clave de idempotencia, número de intento, `timeout` del job e historial de reintentos →
  features 12, 16 y 17.
- Cualquier IO (disco, red, cola). Los modelos no hacen IO (`docs/architecture.md`).

---

## Acceptance → R<n>

| # | Criterio de `acceptance` (feature 2)                                                                                              | Requirements |
|---|-----------------------------------------------------------------------------------------------------------------------------------|--------------|
| 1 | Existe `src/geoagent/common/models.py` con los modelos `AgentInfo`, `Job`, `JobSpec`, `JobProgress`, `JobResult` y `Heartbeat`     | R1, R5, R6 |
| 2 | Existe el enum `JobStatus` con los valores `queued`, `assigned`, `running`, `succeeded`, `failed`, `cancelled` y una función `can_transition(from, to)` que rechaza transiciones inválidas | R7, R8, R9, R10, R11 |
| 3 | Todo modelo expone `to_dict()`/`from_dict()` y un campo `schema_version`; `from_dict()` rechaza payloads con versión desconocida lanzando una excepción tipada | R3, R13, R14, R15, R16, R17, R18, R19, R20 |
| 4 | Los timestamps se serializan en ISO 8601 UTC con sufijo `Z`                                                                        | R21, R22, R23, R24, R25 |
| 5 | La validación de campos obligatorios falla con un error de dominio propio (`ValidationError`), no con `KeyError`/`TypeError`       | R2, R4, R26, R27, R28, R29, R30, R31, R32, R33, R34, R35, R36 |
| 6 | `tests/unit/test_models.py` cubre: round-trip serialización, rechazo de versión desconocida, transiciones válidas e inválidas de `JobStatus` y validación de campos faltantes | R17, R18, R8, R9, R27 (tests en `tests/unit/test_models.py`, ver `tasks.md`) |

`R12` (`FailureCause`) no sale de un criterio literal de la feature 2. Es el tipo del campo
`JobResult.failure_cause`, que exige la descripción de la feature ("sus enums") y cuyos valores
fija la feature 23. Ver la decisión D5 en `design.md`.
