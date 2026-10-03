# Design — feature 2 `core_domain_models`

> Cómo se construyen los requirements de `requirements.md`. Apoyado en
> `docs/architecture.md` (principios 3 y 4, "Qué NO hacer") y `docs/conventions.md`.
> Las decisiones marcadas **D<n>** están **sujetas a la aprobación humana** (§12).

> **Enmienda (post-aprobación inicial).** D12 (§5) formaliza la opción **D1** de "Ronda 4
> quater" en `progress/review_core_domain_models.md`: `_check_payload` deja de recibir
> `required`/`optional` escritos a mano y los deriva de `dataclasses.fields(cls)`. El resto de
> este documento describe el diseño ya aprobado e implementado; D12 es la única decisión nueva
> sujeta a aprobación humana en esta ronda.

## 1. Alcance

Esta feature crea los modelos de dominio que comparten agente y backend, su serialización
versionada, la máquina de estados de `JobStatus` y la base mínima de la jerarquía de errores.
No añade endpoints, persistencia, cola ni IO. Solo usa la stdlib.

## 2. Archivos

| Acción | Archivo | Contenido |
|--------|---------|-----------|
| Crear  | `src/geoagent/common/errors.py` | `GeoAgentError`, `ValidationError`, `UnknownSchemaVersionError` |
| Crear  | `src/geoagent/common/models.py` | Constantes de versión, `JobStatus`, `FailureCause`, `can_transition`, los seis modelos y sus helpers privados |
| Crear  | `tests/unit/test_errors.py` | Jerarquía y atributos de las excepciones (un archivo de test por módulo, `docs/conventions.md`) |
| Crear  | `tests/unit/test_models.py` | Tests de modelos, enums, transiciones, versionado, timestamps y validación |

No se modifican: `pyproject.toml` (sin dependencias nuevas), `src/geoagent/common/__init__.py`
(sin reexportaciones; se importa `geoagent.common.models` y `geoagent.common.errors`
directamente), `Makefile`, `init.sh`, CI ni `docs/`.

## 3. `src/geoagent/common/errors.py`

Alcance mínimo (**D1**): solo las tres excepciones que usa esta feature. `TransientBackendError`,
`PermanentBackendError`, `TransientGeoDataError` y `PermanentGeoDataError`, que aparecen en
`docs/conventions.md`, las añaden las features 7 y 13, que son las que las lanzan y las
prueban. Así cada excepción entra con su test y ningún tipo queda sin usar.

```python
"""Jerarquía de excepciones del dominio de geoagent."""
from __future__ import annotations


class GeoAgentError(Exception):
    """Base para todos los errores del dominio."""


class ValidationError(GeoAgentError):
    """Payload o configuración inválida."""

    def __init__(self, message: str, field: str | None = None) -> None: ...
    # atributos públicos: message: str, field: str | None
    # str(exc) incluye el field cuando no es None, p. ej. "spec.dataset: campo obligatorio ausente"


class UnknownSchemaVersionError(ValidationError):
    """Payload con un schema_version que el modelo no sabe leer."""

    def __init__(self, model: str, version: int, field: str = "schema_version") -> None: ...
    # atributos públicos: model: str, version: int, field (heredado)
```

- `UnknownSchemaVersionError` hereda de `ValidationError` (**D2**). Un payload con versión
  desconocida es un payload inválido, así que quien captura `ValidationError` (p. ej. el
  mapeo a 422 de la feature 5) lo trata sin un caso especial. Quien necesita distinguirlo
  (p. ej. un agente antiguo que lee un mensaje nuevo de la cola) captura la subclase.
- `ValidationError.__init__` llama a `super().__init__(texto)` para que `args`, `str()` y
  `pickle` se comporten como en una excepción normal.
- Ninguna de las tres es "transitoria". Un payload inválido no se arregla reintentando
  (`docs/architecture.md` principio 3). La clasificación transitoria/permanente formal llega
  con la feature 16.

## 4. Campos de los modelos y su origen

La feature 2 nombra los modelos pero no sus campos. El conjunto de abajo es el **mínimo
derivado** de lo que otras features de `feature_list.json` esperan de cada modelo (**D3**). No
se incluye ningún campo sin una feature que lo pida. Los tipos y restricciones normativos están
en el Anexo A de `requirements.md`. Esta tabla solo justifica su existencia.

| Modelo.campo | Origen en `feature_list.json` |
|---|---|
| `JobSpec.dataset` | F8 ac.1 "`JobSpec` (dataset, región, rango temporal, operación)"; F13 `fetch_partition(region, time_range, dataset)` |
| `JobSpec.region` | F8 ac.1 "región"; F14 ac.1 "dado un bounding box". Tipo: secuencia de números (**D4**) |
| `JobSpec.time_start`, `JobSpec.time_end` | F8 ac.1 "rango temporal"; F8 ac.5 "rango temporal invertido" (la validación del orden es de F8) |
| `JobSpec.operation` | F8 ac.1 "operación"; F12 ac.1 "registro de handlers por tipo de operación"; F14 ac.2 `landcover_histogram`, `ndvi_summary` |
| `Job.job_id` | F8 ac.1 "devuelve 201 con el `job_id`" |
| `Job.spec` | F8 descripción "crea jobs a partir de un JobSpec" |
| `Job.status` | F8 ac.1 "estado `queued`"; F8 ac.2 `GET /v1/jobs?status=` |
| `Job.created_at` | F8 ac.1 (creación del job) y ac.4 (transiciones con timestamp); F22 ac.1 orden cronológico |
| `Job.assigned_agent_id` | F8 ac.2 "agente asignado"; F10 ac.4 "sus jobs `assigned` o `running` vuelven a `queued`" (hay que saber de qué agente son) |
| `JobProgress.job_id` | F15 ac.1 `POST /v1/jobs/{id}/progress` |
| `JobProgress.percent` | F12 ac.5 "eventos de progreso (`0-100`)"; F15 ac.1 "acepta porcentaje" |
| `JobProgress.message` | F15 ac.1 "acepta porcentaje y mensaje" |
| `JobResult.job_id` | F15 ac.2 `POST /v1/jobs/{id}/result`; F17 ac.4 "un único resultado almacenado" |
| `JobResult.partition_id` | F14 ac.3 "incluye el `partition_id`"; F29 ac.3 "cada partición tiene exactamente un resultado" |
| `JobResult.status` | F15 ac.2 "marca el job como `succeeded` o `failed`" |
| `JobResult.observation_count` | F14 ac.3 "el conteo de píxeles/observaciones" |
| `JobResult.metrics` | F14 ac.3 "las métricas calculadas"; F14 ac.5 "resultado vacío válido" (se admite `{}`) |
| `JobResult.finished_at` | F15 ac.3 "particionados por fecha y job"; F26 ac.1 filtro por rango temporal |
| `JobResult.failure_cause` | F12 ac.3 causa `timeout`; F16 ac.4 causa `retries_exhausted`; F19 ac.4 causa `resource_exhausted`; F23 ac.1 lista cerrada de causas (**D5**) |
| `AgentInfo.hostname`, `agent_version`, `platform`, `capabilities` | F6 ac.1 "acepta hostname, versión, plataforma y capacidades". `agent_version` evita confundirse con `schema_version` |
| `AgentInfo.agent_id` (opcional) | F6 ac.1 lo devuelve el backend (ausente en el alta); F6 ac.2 y F18 ac.3 el re-registro envía "la misma identidad persistida" |
| `Heartbeat.agent_id` | F10 ac.1 `POST /v1/agents/{id}/heartbeat` |
| `Heartbeat.sent_at` | F10 ac.3 "latidos perdidos" (hace falta el instante de cada latido); F22 ac.3 "últimos heartbeats" |
| `Heartbeat.status` | F10 ac.1 "con estado". Cadena libre no vacía; el conjunto de valores lo fijan F10/F18 (**D6**) |
| `Heartbeat.running_job_ids` | F10 ac.1 "jobs en ejecución" |
| `Heartbeat.resource_usage` | F10 ac.1 "uso de recursos"; F19 ac.5 concreta "CPU, memoria, disco y slots ocupados" (claves definidas por F19) |
| `*.schema_version` | F2 ac.3; `docs/architecture.md` principio 4 |

Campos **considerados y no incluidos** (los añadirá la feature que los necesite, subiendo
`schema_version` si cambia el formato): historial de transiciones y actor (F8), progreso dentro
de `Job` (F8 compone la respuesta), `timeout` del job (F12), número de intento e historial de
reintentos (F16), clave de idempotencia (F17), mensaje de error libre (F23 exige causa
normalizada, no texto libre) y timestamp de `JobProgress` (ninguna feature lo exige).

## 5. Firmas de `src/geoagent/common/models.py`

```python
"""Modelos de dominio inmutables y versionados compartidos por agente y backend."""
from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any

from geoagent.common.errors import UnknownSchemaVersionError, ValidationError

SCHEMA_VERSION = 1
SUPPORTED_SCHEMA_VERSIONS = frozenset({SCHEMA_VERSION})


class JobStatus(str, Enum):
    QUEUED = "queued"
    ASSIGNED = "assigned"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool: ...


class FailureCause(str, Enum):
    NETWORK = "network"
    TIMEOUT = "timeout"
    DATA_SOURCE = "data_source"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    BAD_SPEC = "bad_spec"
    AGENT_CRASH = "agent_crash"
    RETRIES_EXHAUSTED = "retries_exhausted"


def can_transition(from_status: JobStatus, to_status: JobStatus) -> bool: ...


@dataclass(frozen=True)
class JobSpec:
    dataset: str
    region: tuple[float, ...]
    time_start: datetime
    time_end: datetime
    operation: str
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None: ...
    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> JobSpec: ...


@dataclass(frozen=True)
class Job:
    job_id: str
    spec: JobSpec
    status: JobStatus
    created_at: datetime
    assigned_agent_id: str | None = None
    schema_version: int = SCHEMA_VERSION
    # __post_init__, to_dict, from_dict con las mismas firmas


@dataclass(frozen=True)
class JobProgress:
    job_id: str
    percent: float
    message: str
    schema_version: int = SCHEMA_VERSION


@dataclass(frozen=True)
class JobResult:
    job_id: str
    partition_id: str
    status: JobStatus
    observation_count: int
    metrics: Mapping[str, float]
    finished_at: datetime
    failure_cause: FailureCause | None = None
    schema_version: int = SCHEMA_VERSION


@dataclass(frozen=True)
class AgentInfo:
    hostname: str
    agent_version: str
    platform: str
    capabilities: tuple[str, ...]
    agent_id: str | None = None
    schema_version: int = SCHEMA_VERSION


@dataclass(frozen=True)
class Heartbeat:
    agent_id: str
    sent_at: datetime
    status: str
    running_job_ids: tuple[str, ...]
    resource_usage: Mapping[str, float]
    schema_version: int = SCHEMA_VERSION
```

- El nombre de parámetro `from` del acceptance es palabra reservada en Python. Se usa
  `from_status` / `to_status`.
- El orden de los campos es el del Anexo A: obligatorios primero, luego opcionales y
  `schema_version` al final. Python 3.9 no tiene `kw_only`, así que los campos con valor por
  defecto deben ir detrás. En los tests, construir siempre con argumentos nombrados.
- `to_dict()` y `from_dict()` son métodos explícitos por modelo, no reflexión genérica sobre
  `dataclasses.fields()` (ver §10, alternativa A4). **Enmienda D12** (más abajo, tras "Helpers
  privados"): la única reflexión que se añade es en `_check_payload`, para derivar qué claves
  son obligatorias/opcionales — nunca para convertir o validar tipos.

### Helpers privados (orientativos; el implementer ajusta nombres)

```python
_TIMESTAMP_RE = re.compile(
    r"([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})"
    r"(?:\.([0-9]{1,6}))?(Z|[+-][0-9]{2}:[0-9]{2})"
)

def _require_str(value: object, field: str, *, non_empty: bool = True) -> str: ...
def _require_optional_str(value: object, field: str) -> str | None: ...
def _require_int(value: object, field: str, *, minimum: int | None = None) -> int: ...
def _require_number(value: object, field: str) -> float: ...          # finito, no bool
def _require_datetime(value: object, field: str) -> datetime: ...     # aware → UTC; naive → error
def _require_enum(value: object, enum_cls: type[Enum], field: str) -> Enum: ...   # constructor: miembro
def _parse_enum(value: object, enum_cls: type[Enum], field: str) -> Enum: ...     # from_dict: cadena
def _str_tuple(value: object, field: str) -> tuple[str, ...]: ...
def _number_tuple(value: object, field: str) -> tuple[float, ...]: ...
def _number_mapping(value: object, field: str) -> Mapping[str, float]: ...        # MappingProxyType(dict(...))
def _format_timestamp(value: datetime) -> str: ...
def _parse_timestamp(value: object, field: str) -> datetime: ...
def _check_version(model: str, value: object, field: str) -> None: ...

# D12 (enmienda): `_check_payload` ya no recibe `required`/`optional` escritos a mano. Recibe la
# propia clase y deriva las dos tuplas de `dataclasses.fields(cls)` vía `_payload_keys`.
def _payload_keys(cls: type) -> tuple[tuple[str, ...], tuple[str, ...]]: ...
    # (required, optional), en el orden de declaración de `fields(cls)` (= Anexo A).
    # Excluye "schema_version" por nombre. Optativo si `f.default is None` (ver D12).
def _check_payload(cls: type, data: object, path: str | None = None) -> Mapping[str, Any]: ...
    # `model = cls.__name__`; `required, optional = _payload_keys(cls)`. Resto del
    # comportamiento (§5, pasos 1–5) sin cambios.
```

### D12 — `required`/`optional` de `_check_payload` se derivan de `dataclasses.fields(cls)`

**Contexto (enmienda posterior a la aprobación inicial).** Cada `from_dict()` pasaba a
`_check_payload` dos tuplas `required`/`optional` escritas a mano. Si una tupla se
desincronizaba del modelo (una clave de más o de menos, o una copiada de otro modelo), ninguna
prueba de comportamiento lo detectaba: solo lo detectaba un test que espiaba `_check_payload`
con `mock.patch.object` y comprobaba los argumentos de la llamada
(`test_check_payload_admits_exactly_the_annex_a_keys`), frágil ante refactors legítimos que no
cambian ningún comportamiento observable. Ronda 4 quater de
`progress/review_core_domain_models.md` documenta el problema (P3) y tres refactors sin bug que
rompían ese test (RF1–RF3) y propone la opción **D1**, que aquí se formaliza como **D12**.

**Decisión.** `_check_payload` deja de recibir `required`/`optional` como parámetros. Recibe la
clase del modelo (`cls`) y un helper nuevo, `_payload_keys(cls)`, deriva las dos tuplas
recorriendo `dataclasses.fields(cls)` **en su orden de declaración**, que la guarda
`test_required_keys_by_model_matches_annex_a_order` ya fija como el orden del Anexo A. Cada
campo, salvo `schema_version`, se clasifica como `optional` si `f.default is None`, y como
`required` en caso contrario. Los seis `from_dict()` pasan a llamar
`_check_payload(cls, data, path)` sin tuplas.

**Justificación.** La clase de bug que motivó el test espía (una tupla con una clave de más, de
menos o intercambiada) deja de poder escribirse: no hay tupla que mantener sincronizada con el
modelo. `dataclasses.fields(cls)` ya era la única fuente de verdad para el propio `dataclass`;
D12 hace que también lo sea para la validación de payload. No se prueba la ausencia del bug, se
hace **imposible** de introducir. La guarda `test_required_keys_by_model_matches_annex_a_order`
sigue teniendo sentido tal cual está: compara la tabla del test (`_REQUIRED_KEYS_BY_MODEL`,
escrita a mano para otros tests que sí necesitan iterar las claves obligatorias) contra
`fields(model)`, y eso protege contra un error de declaración en `models.py` (un campo en el
orden equivocado, o sin el `| None` que le correspondía) que la derivación en `src/` no puede
detectar por sí sola, porque confía ciegamente en cómo está escrito `models.py`.

**Alternativas descartadas** (nombres tomados de "Ronda 4 quater" en
`progress/review_core_domain_models.md`):

- **D2 de la ronda — `ClassVar` público** (`REQUIRED_KEYS` / `OPTIONAL_KEYS` en cada modelo, que
  `from_dict()` usaría obligatoriamente). Añade superficie pública nueva (dos constantes por
  clase) que ninguna otra feature necesita, y "`from_dict` usa la constante y no otra tupla"
  seguiría siendo una conexión que probar por separado. No elimina la clase de bug: la traslada
  de dentro de `from_dict` a la cabecera de la clase. Se descarta.
- **Endurecer el test espía** (m1 de la ronda: `inspect.signature(_check_payload).bind(...)` y
  seleccionar la llamada por `model.__name__` en vez de por `call_args_list[0]`). Elimina RF1 y
  la dependencia del orden de las llamadas anidadas, pero no el acoplamiento al nombre del
  helper (RF3) ni, sobre todo, la naturaleza del test: sigue verificando *qué se llama*, no *qué
  acepta* `from_dict()`. Con D12 la pregunta que hacía ese test deja de tener sentido, porque no
  quedan tuplas que inspeccionar por fuera. Se descarta como parche transitorio ya innecesario
  una vez aprobado D12.

**Impacto en A4** ("sin reflexión genérica en `to_dict`/`from_dict`", §13). A4 se mantiene en lo
esencial. La reflexión que introduce D12 se limita a **enumerar nombres de campo y su valor por
defecto** para construir dos tuplas de claves; no decide **cómo convertir o validar** cada valor,
que sigue siendo código explícito por campo en `__post_init__`, `to_dict()` y `from_dict()`,
exactamente como antes. D12 no reintroduce el problema que motivó A4 (resolver anotaciones de
tipo en runtime con `get_type_hints()`, que falla en 3.9 para `X | None`): D12 no toca `f.type`
en absoluto (ver criterio de "opcional" abajo). La restricción de §10 "prohibido evaluar
anotaciones en runtime… ni inspeccionar `dataclasses.fields(...).type`" queda intacta y sin
necesidad de excepción ni matiz.

**Criterio para identificar un campo opcional.** Opciones consideradas:

a. Anotación en cadena que termina en `"| None"` (posible porque `from __future__ import
   annotations` convierte toda anotación en el texto tal como se escribió, sin evaluarla). Es el
   criterio que ya usa, en `tests/`, la guarda `test_required_keys_by_model_matches_annex_a_order`
   (`f.type.endswith("| None")`).
b. `f.default is None`.
c. `f.default is not dataclasses.MISSING` (clasifica por "tiene o no tiene default", no por si
   el default es `None`).

**Elegido: (b) `f.default is None`.**

Motivos:

- El §10 de este `design.md` prohíbe explícitamente, para `src/`, "inspeccionar
  `dataclasses.fields(...).type`". La opción (a) no *evalúa* la anotación (solo compara texto),
  pero sí la *inspecciona*, que es justo lo que ese párrafo nombra. Elegirla en `src/` obligaría
  a reabrir y matizar esa restricción para distinguir "leer la cadena" de "evaluarla". La opción
  (b) no toca `f.type` en absoluto, así que la restricción de §10 queda intacta sin necesidad de
  excepción.
- (b) no depende del formato exacto de la anotación (orden de la unión, espacios, un futuro
  `Optional[X]` en vez de `X | None`); depende solo del valor por defecto, un objeto Python
  normal e idéntico en 3.9 y 3.14.
- (c) generalizaría a "tiene default" en vez de "el default es `None`". Hoy da el mismo
  resultado que (b) porque el único campo con default no-`None` es `schema_version` (excluido
  por nombre), pero escondería en silencio un futuro campo con default no-`None` que no fuera
  opcional-en-payload. (b) no lo esconde: un campo así cae en `required` y, si de verdad debiera
  ser opcional, la spec de esa feature tiene que decidirlo explícitamente en vez de heredar un
  comportamiento implícito de "tiene default".

**¿Coincide con cómo están declarados hoy los opcionales en `src/geoagent/common/models.py`?**
Sí, plenamente. Los tres campos opcionales del Anexo A (`Job.assigned_agent_id`,
`JobResult.failure_cause`, `AgentInfo.agent_id`) están hoy declarados como `X | None = None`:
cumplen **a la vez** (a) y (b). Hoy no hay ningún campo donde (a) y (b) diverjan, así que elegir
(b) sobre (a) es una decisión de robustez y de encaje con §10, no la corrección de una
inconsistencia existente. Límite documentado: si en el futuro un campo tuviera anotación
`X | None` sin default `None`, o un default `None` sin esa anotación, (a) y (b) darían
resultados distintos; `_payload_keys` seguiría (b), y esa divergencia debería resolverse de
forma explícita en la spec que introduzca ese campo, no en silencio.

**`schema_version`.** Se excluye de `_payload_keys` por nombre (`if f.name == "schema_version":
continue`), no por el criterio (a)/(b): su default (`SCHEMA_VERSION`) no es `None`, así que ya
quedaría fuera de `optional` con el criterio (b), pero se excluye explícitamente para que quede
igual de claro que con (a) y para que no dependa de qué valor tenga `SCHEMA_VERSION`.
`schema_version` sigue teniendo el manejo dedicado y anterior que ya tenía en `_check_payload`
(comprobación de presencia, tipo y pertenencia a `SUPPORTED_SCHEMA_VERSIONS` vía
`_check_version`, antes de comprobar claves desconocidas u obligatorias — §5, pasos 2–3). D12 no
cambia ese orden ni ese manejo.

**`JobSpec` anidado en `Job`.** Sin cambios de comportamiento. `_payload_keys(Job)` deriva `spec`
como clave obligatoria (no tiene default y no es `schema_version`), igual que la tupla escrita a
mano de hoy. `_check_payload(Job, data, path)` solo comprueba que la clave `spec` está presente
y es una de las claves conocidas del nivel superior; no valida su contenido. La validación
recursiva del sub-payload sigue ocurriendo exactamente igual que antes de esta enmienda:
`Job.from_dict` construye `spec = JobSpec.from_dict(payload["spec"])` dentro de un
`try`/`except ValidationError`, y `_reraise_nested` prefija el `field` con `"spec."` (§5, "Rutas
anidadas"). D12 solo cambia cómo `_check_payload` obtiene sus propias tuplas `required`/
`optional`; no toca la lógica de anidamiento ni el helper `_reraise_nested`.

**Por qué no se añade un test nuevo que nombre `_payload_keys`.** Nombrar el helper nuevo desde
un test reproduciría el mismo acoplamiento que motivó eliminar el test espía (valoración de P3,
ronda 4 quater, punto 1: el diseño declara los helpers privados "orientativos"). La cobertura de
D12 es por comportamiento (R27, R28, R35 a través de `from_dict()`, como ya estaba) más la
guarda estructural ya existente (`test_required_keys_by_model_matches_annex_a_order`), que
compara contra `fields(model)` y no contra ningún helper interno con nombre propio.

### Validación en el constructor (`__post_init__`)

`__post_init__` valida cada campo en el orden del Anexo A y normaliza con
`object.__setattr__(self, name, value)`, porque la clase es `frozen`. Normalizaciones:

- Secuencias (`list` o `tuple`) → `tuple`. Cualquier otro tipo, incluidos `str` y `set`, es
  error de tipo (R29): una `str` es iterable y se colaría como tupla de caracteres.
- `dict` / `Mapping` → `MappingProxyType(dict(value))`: copia y vista de solo lectura (R6).
- Números → `float(value)` tras comprobar `isinstance(value, (int, float))` y
  `not isinstance(value, bool)` y `math.isfinite` (R29, R30).
- `datetime` aware → `value.astimezone(timezone.utc)`; naive → `ValidationError` (R22, R24).
  Se comprueba `value.tzinfo is not None and value.utcoffset() is not None`.
- `schema_version`: `int` no `bool` (si no, `ValidationError`, R29) y dentro de
  `SUPPORTED_SCHEMA_VERSIONS` (si no, `UnknownSchemaVersionError`, R19).
- Enums: el constructor exige el miembro (`isinstance(value, JobStatus)`). La cadena `"queued"`
  es error de tipo aunque `JobStatus.QUEUED == "queued"` sea `True` por el mixin `str`.

`Job.__post_init__` exige `isinstance(spec, JobSpec)`. La validación del propio `JobSpec` ya
ocurrió al construirlo.

### Orden de validación en `from_dict()` (determinista)

1. `data` no es `Mapping` → `ValidationError(field=path)` (R26).
2. Falta `schema_version` o no es `int` no `bool` → `ValidationError(field="…schema_version")`
   (R20).
3. `schema_version` fuera de `SUPPORTED_SCHEMA_VERSIONS` → `UnknownSchemaVersionError` (R18).
   Va antes que cualquier otra comprobación: un payload de una versión futura puede tener otras
   claves y debe fallar por su versión, no por la clave desconocida o la ausente.
4. Claves desconocidas → `ValidationError(field=clave)` (R35). Si hay varias, se informa de la
   primera en orden alfabético, para que el resultado sea determinista. El conjunto de claves
   admitidas (`required ∪ optional ∪ {"schema_version"}`) sale de `_payload_keys(cls)` (D12), no
   de una tupla escrita a mano.
5. Claves obligatorias ausentes → `ValidationError(field=clave)`, la primera en el orden del
   Anexo A (R27), que es el orden de `_payload_keys(cls)` (= `dataclasses.fields(cls)`, D12).
   Nunca `data[key]` sin comprobar antes (así no hay `KeyError`).
6. Conversión de tipos de wire: cadenas → `datetime` (`_parse_timestamp`), cadenas → enum
   (`_parse_enum`), `dict` → `JobSpec.from_dict` con ruta `spec`.
7. Construcción con `cls(**kwargs)`, que aplica `__post_init__`.

`from_dict()` no modifica `data`.

**Rutas anidadas (R4).** `Job.from_dict` captura el `ValidationError` que lanza
`JobSpec.from_dict` y relanza una excepción **de la misma clase** con `field` prefijado
(`"spec." + field`, o `"spec"` si `field` era `None`), encadenada con `from exc`. Para
`UnknownSchemaVersionError` se conservan `model` y `version`. Otra opción es pasar un parámetro
privado `path` a una función interna `_from_dict(data, path)`. Cualquiera de las dos cumple el
requirement.

### `to_dict()`

Devuelve un `dict` nuevo en cada llamada (R14):

- `str`, `int`, `float` y `None` tal cual.
- `tuple` → `list`. Mapping → `dict(value)`.
- Enum → `member.value` (R15). **Nunca** `str(member)` ni f-string: desde Python 3.11
  `format()` de un enum con mixin `str` devuelve `"JobStatus.QUEUED"`, y la CI prueba con 3.9 y
  con 3.14.
- `datetime` → `_format_timestamp` (R21).
- `JobSpec` anidado → `spec.to_dict()` (R16).

## 6. Máquina de estados de `JobStatus`

`can_transition` consulta una tabla inmutable a nivel de módulo:

```python
_VALID_TRANSITIONS: Mapping[JobStatus, frozenset[JobStatus]] = MappingProxyType({...})
```

Si algún argumento no es `isinstance(x, JobStatus)`, lanza `ValidationError` (R11). En otro
caso devuelve `to_status in _VALID_TRANSITIONS[from_status]`. Es una función pura: no lanza
por transición inválida, devuelve `False` (**D7**).

### Transiciones válidas (R8)

| Desde → Hasta | Justificación |
|---|---|
| `queued → assigned` | El backend entrega el job a un agente (F8 ac.2 "agente asignado"; F9 consumo de la cola). |
| `queued → cancelled` | F8 ac.3: "mueve un job `queued` o `running` a `cancelled`". |
| `assigned → running` | El agente empieza a ejecutarlo (F12). |
| `assigned → queued` | F10 ac.4: al declarar un agente `offline`, "sus jobs `assigned` o `running` vuelven a `queued`". |
| `assigned → failed` | El agente rechaza el job antes de ejecutarlo con una causa normalizada: F19 ac.4 "los jobs nuevos se rechazan con causa `resource_exhausted`"; F12 ac.1 "operación desconocida falla como error permanente sin reintentos". |
| `assigned → cancelled` | **D8.** F8 ac.3 solo nombra `queued` y `running`, pero solo devuelve 409 "si el job ya terminó", y `assigned` no está terminado. Sin esta transición, un job asignado que aún no ha empezado no se podría cancelar, y F8 ac.6 prueba "cancelación en cada estado". |
| `running → succeeded` | F15 ac.2: el resultado "marca el job como `succeeded`". |
| `running → failed` | F15 ac.2 (resultado fallido); F12 ac.3 (timeout); F16 ac.4 (`retries_exhausted`). |
| `running → cancelled` | F8 ac.3. |
| `running → queued` | F10 ac.4 (agente `offline` con jobs `running`); F18 ac.1 "reencola los jobs que quedaron `running`". |

### Estados terminales

`succeeded`, `failed` y `cancelled` son terminales: no tienen transiciones de salida (R9, R10).
Motivos: F8 ac.3 devuelve 409 "si el job ya terminó", F15 ac.1 rechaza progreso de un job
terminado con 409 y F27 ac.5 exige que "todos los jobs [queden] en estado terminal".

### Transiciones rechazadas de forma explícita

- Autotransiciones (`running → running`, etc.): una actualización de progreso no es un cambio
  de estado (F15 ac.1).
- `queued → running`: un job no se ejecuta sin asignarse antes (F8 ac.2 expone el agente
  asignado).
- `queued → succeeded` / `queued → failed`: ningún resultado se produce sin ejecución o
  rechazo por parte de un agente asignado.
- Cualquier salida de un estado terminal. **Nota para la feature 23**: `POST /v1/dlq/{id}/requeue`
  sobre un job `failed` necesitará o bien crear un intento/job nuevo, o bien una transición
  `failed → queued`. Esa decisión corresponde a la spec de F23, que en el segundo caso
  modificará esta tabla.

## 7. Política de `schema_version`

- Tipo `int`, serializado como integer JSON. Valor actual `SCHEMA_VERSION = 1`, conjunto
  aceptado `SUPPORTED_SCHEMA_VERSIONS = frozenset({1})`.
- **Una única versión compartida por los seis modelos** (**D9**). Cualquier cambio del formato
  de wire de cualquier modelo (añadir, quitar o renombrar un campo, o cambiar su tipo o su
  semántica) incrementa `SCHEMA_VERSION`. Si más adelante un modelo necesita evolucionar solo,
  la spec de ese cambio introduce versiones por modelo (alternativa A3).
- `to_dict()` emite siempre el `schema_version` de la instancia, que por R19 siempre está
  soportado.
- `from_dict()` comprueba la versión antes que todo lo demás (§5, paso 3).
- Lectura estricta: una clave desconocida es un error (R35, **D10**). Como todo cambio de
  formato sube la versión, una clave extra dentro de la versión 1 solo puede ser un error del
  emisor (p. ej. `dataset_id` en lugar de `dataset`) y conviene detectarlo.
- Cuando exista la versión 2, la feature que la introduzca decide si `from_dict` migra la v1 en
  memoria (añadiendo `1` a `SUPPORTED_SCHEMA_VERSIONS`) o la rechaza.
- Un sub-payload anidado (`Job.spec`) lleva y valida su propio `schema_version` (R16, R18).

## 8. Timestamps

- **En memoria**: `datetime` aware con `tzinfo is timezone.utc` (`docs/conventions.md`).
- **Constructor**:
  - datetime aware con cualquier offset → se convierte a UTC conservando el instante (R22).
  - datetime naive → `ValidationError` (R24). No se asume la hora local ni UTC: un naive es
    ambiguo y el error aparece en el punto donde se crea el valor.
- **Serialización** (R21): `value.astimezone(timezone.utc).replace(tzinfo=None).isoformat(timespec="microseconds") + "Z"`,
  p. ej. `2026-09-14T10:00:00.000000Z`. Se usa `isoformat`, que rellena el año a 4 dígitos, y
  no `strftime("%Y")`, que en glibc no rellena años < 1000. El ancho es fijo (siempre 6 dígitos
  de fracción), así que el orden lexicográfico de las cadenas coincide con el cronológico, lo
  que aprovechan los filtros y ordenaciones por texto de F21 y F22.
- **Deserialización** (R23, R25): `_parse_timestamp` **no** usa `datetime.fromisoformat`, porque
  su gramática cambia entre versiones (3.9 no acepta `Z` ni fracciones de 1, 2, 4 o 5 dígitos;
  3.11+ acepta muchas más formas), y la CI corre en 3.9 y 3.14. En su lugar:
  1. `value` no es `str` → `ValidationError`.
  2. `_TIMESTAMP_RE.fullmatch(value)`. Con `[0-9]` y no `\d`, para no aceptar dígitos Unicode no
     ASCII. `T` y `Z` en mayúscula. Sin coincidencia → `ValidationError`. Esto incluye las
     cadenas sin zona horaria (naive), que se rechazan.
  3. La fracción de 1 a 6 dígitos se rellena por la derecha hasta 6 (`"5"` → `500000` µs).
  4. `Z` → `timezone.utc`. `±HH:MM` → `timezone(±timedelta(hours=HH, minutes=MM))`.
  5. Se construye `datetime(...)`. Si `datetime`, `timedelta` o `timezone` lanzan `ValueError`
     (mes 13, `25:00`, offset `+24:00`), se traduce a `ValidationError` con `from exc`.
  6. `.astimezone(timezone.utc)`.
- Se aceptan offsets distintos de UTC al leer (**D11**): son inequívocos y RFC 3339 los permite.
  Rechazarlos no aporta seguridad y rompería clientes que no emiten `Z`. Lo que se garantiza es
  la **salida** siempre en `Z`.
- Nota para los tests: dos `datetime` aware del mismo instante son `==` aunque su `tzinfo`
  difiera. Para R22 y R23 hay que comprobar además `value.tzinfo is timezone.utc`.

## 9. Frontera de validación

| Valida esta feature | No valida (dueño) |
|---|---|
| Presencia de claves obligatorias y ausencia de claves desconocidas | Forma, aridad y rangos de `region`; 422 (F8, F14) |
| Tipo básico de cada campo (`str`, `int`, número, `datetime`, enum, secuencia, mapping) | `time_end ≥ time_start` (F8) |
| Cadenas no vacías, números finitos, `observation_count ≥ 0` | `operation` pertenece al catálogo de handlers (F8, F12) |
| `0 ≤ percent ≤ 100` | Transición persistida con actor y timestamp; 409 (F8) |
| `schema_version` presente, entero y soportado | Coherencia `Job.status` ↔ `assigned_agent_id` (F8, F10) |
| `JobResult.status ∈ {succeeded, failed}` y coherencia con `failure_cause` | Valores de `Heartbeat.status` y claves de `resource_usage` (F10, F18, F19) |
| Timestamps aware / UTC / gramática | Esquema de `metrics` (F14, `docs/results_schema.md`) |
| Pares válidos de `can_transition` | Aplicar la transición a un job (F8) |

R36 fija con un test que `JobSpec` **no** adelanta las validaciones de F8.

## 10. Compatibilidad con Python 3.9 (restricciones para el implementer)

- `from __future__ import annotations` en todos los archivos. Las anotaciones `str | None`,
  `tuple[str, ...]` y `Mapping[str, float]` quedan como cadenas y `dataclasses` no las evalúa.
  Ruff (`UP`, `target-version = "py39"`) propone `X | None` en anotaciones cuando existe ese
  import, así que se usa esa forma.
- **Prohibido evaluar anotaciones en runtime**: nada de `typing.get_type_hints()` ni de
  inspeccionar `dataclasses.fields(...).type`. En 3.9, `eval("str | None")` lanza `TypeError`.
  La validación es explícita campo a campo.
- `isinstance(x, (int, float))` con tupla, nunca `isinstance(x, int | float)` (3.10+).
- Sin `dataclass(slots=True)` ni `kw_only=True` (3.10+), sin `match` (3.10+), sin
  `enum.StrEnum` (3.11+; se usa `class JobStatus(str, Enum)`), sin `datetime.UTC` (3.11+; se usa
  `timezone.utc`) y sin `zip(strict=...)` (3.10+).
- Serialización de enums siempre con `.value` (ver §5).
- No usar `datetime.fromisoformat` para parsear (ver §8).

## 11. Contratos afectados

- **REST (F5, F6, F8, F10, F15)**: los cuerpos JSON de estos endpoints se construirán con
  `to_dict()` / `from_dict()`. Los nombres de campo del Anexo A (snake_case) forman el contrato
  de wire v1. Cambiarlos exige subir `schema_version`.
- **Cola (F9)**: el cuerpo del mensaje de job será `Job.to_dict()` serializado a JSON. Un agente
  que recibe una versión que no conoce obtiene `UnknownSchemaVersionError`. Qué hace entonces
  (`nack`, DLQ) lo decide F9.
- **LocalStore (F4) y Backend Store (F5)**: pueden guardar `to_dict()` como JSON. El versionado
  del esquema SQLite es independiente de `schema_version`.
- **GeoDataSource (F13)**: sin cambios. `JobSpec` aporta `dataset`, `region` y el rango
  temporal que recibirá `fetch_partition`.
- **Hash**: los modelos con campos mapping (`JobResult`, `Heartbeat`) no son hashables, porque
  `MappingProxyType` no lo es y `hash()` lanza `TypeError`. Ninguna feature necesita usarlos
  como claves de `dict` o `set`. `Job`, `JobSpec`, `JobProgress` y `AgentInfo` sí son
  hashables. No es un requirement.

## 12. Decisiones sujetas a aprobación humana

| Id | Decisión | Alternativa si se rechaza |
|----|----------|---------------------------|
| D1 | `errors.py` solo con `GeoAgentError`, `ValidationError` y `UnknownSchemaVersionError` | Crear ya las seis excepciones de `docs/conventions.md` |
| D2 | `UnknownSchemaVersionError` hereda de `ValidationError` | Hermana directa de `ValidationError` bajo `GeoAgentError` |
| D3 | Conjunto mínimo de campos de §4, derivado de F6, F8, F10, F12, F14, F15, F19 y F23 | Otro conjunto que indique el humano |
| D4 | `JobSpec.region` es una secuencia de números finitos sin aridad fija | Bounding box de exactamente 4 números, u objeto GeoJSON |
| D5 | `failure_cause` usa el enum `FailureCause` con los 7 valores de F23, creado ya en esta feature | `failure_cause: str | None` y que F23 introduzca el enum |
| D6 | `Heartbeat.status` es `str` no vacía sin enum | Enum de estados del agente definido ahora |
| D7 | `can_transition` devuelve `bool` y no lanza por transición inválida | Además, una función `ensure_transition` que lance `InvalidTransitionError` |
| D8 | `assigned → cancelled` es válida | Excluirla y que F8 devuelva 409 al cancelar un job `assigned` |
| D9 | Un único `SCHEMA_VERSION` para todos los modelos | Versión independiente por modelo (A3) |
| D10 | Las claves desconocidas en `from_dict` son error | Ignorarlas (lector tolerante) |
| D11 | Al leer se aceptan offsets `±HH:MM` y se normalizan a UTC | Aceptar solo el sufijo `Z` |
| D12 (enmienda) | `_check_payload` deriva `required`/`optional` de `dataclasses.fields(cls)` (criterio: opcional si `f.default is None`, excluido `schema_version` por nombre); elimina las tuplas escritas a mano y el test espía `test_check_payload_admits_exactly_the_annex_a_keys` (ver §5, "D12") | Exponer `REQUIRED_KEYS`/`OPTIONAL_KEYS` como `ClassVar` público en cada modelo, o mantener las tuplas a mano y solo endurecer el test espía |

## 13. Alternativas descartadas

- **A1 — pydantic / attrs / marshmallow.** Resuelven validación y serialización, pero añaden una
  dependencia de runtime a un paquete que hoy tiene `dependencies = []`, y
  `docs/architecture.md` §2 exige justificar cada dependencia. pydantic v2 además arrastra un
  binario compilado (`pydantic-core`), lo que complica la matriz 3.9/3.14 de CI y los endpoints
  remotos. El volumen de validación de esta feature (6 modelos, tipos básicos) no lo justifica.
- **A2 — `TypedDict` o dicts planos.** No dan inmutabilidad (principio 4), no validan en runtime
  y no ofrecen un sitio para `to_dict` / `from_dict`.
- **A3 — Versión de esquema por modelo** (`ClassVar` en cada clase). Permite evolucionar un
  modelo sin tocar los demás, pero hoy todos están en v1 y ninguna feature pide evolución
  independiente. Añade seis constantes y la detección de `ClassVar` en anotaciones de cadena, que
  en 3.9 es frágil. Se pospone hasta que haga falta (D9).
- **A4 — Validación y serialización genéricas por reflexión** (recorrer `dataclasses.fields()` y
  sus tipos). Con `from __future__ import annotations` los tipos son cadenas, y resolverlos con
  `get_type_hints` falla en 3.9 para `X | None`. Además, las restricciones por campo (no vacía,
  rango de `percent`, coherencia de `failure_cause`) necesitarían metadatos adicionales. El
  código explícito por modelo es más largo pero lineal y fácil de revisar. **Matiz de la
  enmienda D12** (§5): esta alternativa sigue descartada para *validar y serializar valores*.
  Lo único que ahora sí recorre `dataclasses.fields()` es la derivación de qué claves son
  obligatorias/opcionales dentro de `_check_payload`, que no inspecciona tipos ni convierte
  nada — ver D12 para la justificación completa de por qué esto no reabre A4.
- **A5 — `datetime.fromisoformat` para parsear timestamps.** Su gramática difiere entre 3.9 y
  3.11+, así que el mismo payload se aceptaría en una versión y se rechazaría en otra (§8).
- **A6 — Enums como cadenas sueltas (constantes `str`).** Pierde la comprobación de pertenencia y
  la tabla de transiciones indexada por miembro. F23 exige además "causa normalizada y no un texto
  libre".
