"""Modelos de dominio inmutables y versionados compartidos por agente y backend."""

from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, fields
from datetime import datetime, timedelta, timezone
from enum import Enum
from types import MappingProxyType
from typing import Any, NoReturn

from geoagent.common.errors import UnknownSchemaVersionError, ValidationError

SCHEMA_VERSION = 1
SUPPORTED_SCHEMA_VERSIONS = frozenset({SCHEMA_VERSION})

_TIMESTAMP_RE = re.compile(
    r"([0-9]{4})-([0-9]{2})-([0-9]{2})T([0-9]{2}):([0-9]{2}):([0-9]{2})"
    r"(?:\.([0-9]{1,6}))?(Z|[+-][0-9]{2}:[0-9]{2})"
)


class JobStatus(str, Enum):
    """Estados posibles de un `Job`."""

    QUEUED = "queued"
    ASSIGNED = "assigned"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"

    @property
    def is_terminal(self) -> bool:
        return self in (JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED)


class FailureCause(str, Enum):
    """Causa normalizada de un `JobResult` fallido."""

    NETWORK = "network"
    TIMEOUT = "timeout"
    DATA_SOURCE = "data_source"
    RESOURCE_EXHAUSTED = "resource_exhausted"
    BAD_SPEC = "bad_spec"
    AGENT_CRASH = "agent_crash"
    RETRIES_EXHAUSTED = "retries_exhausted"


_VALID_TRANSITIONS: Mapping[JobStatus, frozenset] = MappingProxyType(
    {
        JobStatus.QUEUED: frozenset({JobStatus.ASSIGNED, JobStatus.CANCELLED}),
        JobStatus.ASSIGNED: frozenset(
            {JobStatus.RUNNING, JobStatus.QUEUED, JobStatus.FAILED, JobStatus.CANCELLED}
        ),
        JobStatus.RUNNING: frozenset(
            {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.QUEUED}
        ),
        JobStatus.SUCCEEDED: frozenset(),
        JobStatus.FAILED: frozenset(),
        JobStatus.CANCELLED: frozenset(),
    }
)


def can_transition(from_status: JobStatus, to_status: JobStatus) -> bool:
    """Indica si la transición `from_status -> to_status` está permitida."""
    if not isinstance(from_status, JobStatus) or not isinstance(to_status, JobStatus):
        raise ValidationError("JobStatus members expected")
    return to_status in _VALID_TRANSITIONS[from_status]


def _join(path: str | None, name: str) -> str:
    return name if path is None else f"{path}.{name}"


def _require_str(value: object, field: str, *, non_empty: bool = True) -> str:
    if not isinstance(value, str):
        raise ValidationError("string expected", field=field)
    if non_empty and len(value) == 0:
        raise ValidationError("string cannot be empty", field=field)
    return value


def _require_optional_str(value: object, field: str) -> str | None:
    if value is None:
        return None
    return _require_str(value, field, non_empty=True)


def _require_int(value: object, field: str, *, minimum: int | None = None) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("integer expected", field=field)
    if minimum is not None and value < minimum:
        raise ValidationError(f"integer must be >= {minimum}", field=field)
    return value


def _require_number(value: object, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValidationError("number expected", field=field)
    result = float(value)
    if not math.isfinite(result):
        raise ValidationError("number must be finite", field=field)
    return result


def _require_datetime(value: object, field: str) -> datetime:
    if not isinstance(value, datetime):
        raise ValidationError("datetime object expected", field=field)
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValidationError("datetime must have timezone", field=field)
    return value.astimezone(timezone.utc)


def _require_enum(value: object, enum_cls: type[Enum], field: str) -> Enum:
    if not isinstance(value, enum_cls):
        raise ValidationError(f"{enum_cls.__name__} member expected", field=field)
    return value


def _parse_enum(value: object, enum_cls: type[Enum], field: str) -> Enum:
    if not isinstance(value, str):
        raise ValidationError("string expected", field=field)
    try:
        return enum_cls(value)
    except ValueError as exc:
        raise ValidationError("unknown enum value", field=field) from exc


def _str_tuple(value: object, field: str) -> tuple:
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        raise ValidationError("string list expected", field=field)
    items = []
    for item in value:
        if not isinstance(item, str):
            raise ValidationError("every element must be string", field=field)
        if len(item) == 0:
            raise ValidationError("every element must non-empty", field=field)
        items.append(item)
    return tuple(items)


def _number_tuple(value: object, field: str) -> tuple:
    if isinstance(value, str) or not isinstance(value, (list, tuple)):
        raise ValidationError("number list expected", field=field)
    items = []
    for item in value:
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ValidationError("every value must be a number", field=field)
        number = float(item)
        if not math.isfinite(number):
            raise ValidationError("every element must be finite", field=field)
        items.append(number)
    return tuple(items)


def _number_mapping(value: object, field: str) -> Mapping:
    if not isinstance(value, Mapping):
        raise ValidationError("number mapping expected", field=field)
    result: dict = {}
    for key, item in value.items():
        if not isinstance(key, str) or len(key) == 0:
            raise ValidationError("keys have to be non-empty strings", field=field)
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise ValidationError("values must be numbers", field=field)
        number = float(item)
        if not math.isfinite(number):
            raise ValidationError("values must be finite", field=field)
        result[key] = number
    return MappingProxyType(result)


def _format_timestamp(value: datetime) -> str:
    utc_value = value.astimezone(timezone.utc)
    return utc_value.replace(tzinfo=None).isoformat(timespec="microseconds") + "Z"


def _parse_timestamp(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise ValidationError("string expected", field=field)
    match = _TIMESTAMP_RE.fullmatch(value)
    if match is None:
        raise ValidationError("invalid timestamp format", field=field)
    year, month, day, hour, minute, second, fraction, offset = match.groups()
    microsecond = int((fraction or "").ljust(6, "0"))
    if offset == "Z":
        tzinfo = timezone.utc
    else:
        sign = 1 if offset[0] == "+" else -1
        hours = int(offset[1:3])
        minutes = int(offset[4:6])
        if minutes >= 60:
            raise ValidationError("invalid timezone offset", field=field)
        try:
            tzinfo = timezone(sign * timedelta(hours=hours, minutes=minutes))
        except ValueError as exc:
            raise ValidationError("invalid timezone offset", field=field) from exc
    try:
        parsed = datetime(
            int(year),
            int(month),
            int(day),
            int(hour),
            int(minute),
            int(second),
            microsecond,
            tzinfo=tzinfo,
        )
    except ValueError as exc:
        raise ValidationError("missing date or hour", field=field) from exc
    return parsed.astimezone(timezone.utc)


def _check_version(model: str, value: object, field: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValidationError("schema_version must be int", field=field)
    if value not in SUPPORTED_SCHEMA_VERSIONS:
        raise UnknownSchemaVersionError(model=model, version=value, field=field)


def _payload_keys(cls: type) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Devuelve `(required, optional)` derivados de `dataclasses.fields(cls)` (D12).

    Respeta el orden de declaración, excluye `schema_version` por nombre y trata como
    opcional todo campo cuyo valor por defecto es `None`. No inspecciona `f.type`.
    """
    required: list[str] = []
    optional: list[str] = []
    for f in fields(cls):
        if f.name == "schema_version":
            continue
        (optional if f.default is None else required).append(f.name)
    return tuple(required), tuple(optional)


def _check_payload(cls: type, data: object, path: str | None = None) -> Mapping[str, Any]:
    model = cls.__name__
    required, optional = _payload_keys(cls)
    if not isinstance(data, Mapping):
        raise ValidationError("mapping expected", field=path)
    version_field = _join(path, "schema_version")
    if "schema_version" not in data:
        raise ValidationError("missing required key", field=version_field)
    _check_version(model, data["schema_version"], version_field)
    allowed = set(required) | set(optional) | {"schema_version"}
    extra = sorted((key for key in data.keys() if key not in allowed), key=str)
    if extra:
        raise ValidationError("unknown key", field=_join(path, str(extra[0])))
    for key in required:
        if key not in data:
            raise ValidationError("missing required key", field=_join(path, key))
    return data


def _reraise_nested(exc: ValidationError, prefix: str) -> NoReturn:
    """Relanza `exc` con el `field` prefijado por `prefix.` (o `prefix` si era `None`)."""
    field = prefix if exc.field is None else f"{_join(prefix, exc.field)}"
    if isinstance(exc, UnknownSchemaVersionError):
        raise UnknownSchemaVersionError(model=exc.model, version=exc.version, field=field) from exc
    raise ValidationError(exc.message, field=field) from exc


@dataclass(frozen=True)
class JobSpec:
    dataset: str
    region: tuple[float, ...]
    time_start: datetime
    time_end: datetime
    operation: str
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "dataset", _require_str(self.dataset, "dataset"))
        object.__setattr__(self, "region", _number_tuple(self.region, "region"))
        object.__setattr__(self, "time_start", _require_datetime(self.time_start, "time_start"))
        object.__setattr__(self, "time_end", _require_datetime(self.time_end, "time_end"))
        object.__setattr__(self, "operation", _require_str(self.operation, "operation"))
        _check_version("JobSpec", self.schema_version, "schema_version")

    def to_dict(self) -> dict[str, Any]:
        return {
            "dataset": self.dataset,
            "region": list(self.region),
            "time_start": _format_timestamp(self.time_start),
            "time_end": _format_timestamp(self.time_end),
            "operation": self.operation,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> JobSpec:
        payload = _check_payload(cls, data)
        return cls(
            dataset=payload["dataset"],
            region=payload["region"],
            time_start=_parse_timestamp(payload["time_start"], "time_start"),
            time_end=_parse_timestamp(payload["time_end"], "time_end"),
            operation=payload["operation"],
            schema_version=payload["schema_version"],
        )


@dataclass(frozen=True)
class Job:
    job_id: str
    spec: JobSpec
    status: JobStatus
    created_at: datetime
    assigned_agent_id: str | None = None
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "job_id", _require_str(self.job_id, "job_id"))
        if not isinstance(self.spec, JobSpec):
            raise ValidationError("JobSpec expected", field="spec")
        object.__setattr__(self, "status", _require_enum(self.status, JobStatus, "status"))
        object.__setattr__(self, "created_at", _require_datetime(self.created_at, "created_at"))
        object.__setattr__(
            self,
            "assigned_agent_id",
            _require_optional_str(self.assigned_agent_id, "assigned_agent_id"),
        )
        _check_version("Job", self.schema_version, "schema_version")

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "spec": self.spec.to_dict(),
            "status": self.status.value,
            "created_at": _format_timestamp(self.created_at),
            "assigned_agent_id": self.assigned_agent_id,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Job:
        payload = _check_payload(cls, data)
        try:
            spec = JobSpec.from_dict(payload["spec"])
        except ValidationError as exc:
            _reraise_nested(exc, "spec")
        return cls(
            job_id=payload["job_id"],
            spec=spec,
            status=_parse_enum(payload["status"], JobStatus, "status"),
            created_at=_parse_timestamp(payload["created_at"], "created_at"),
            assigned_agent_id=payload.get("assigned_agent_id"),
            schema_version=payload["schema_version"],
        )


@dataclass(frozen=True)
class JobProgress:
    job_id: str
    percent: float
    message: str
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "job_id", _require_str(self.job_id, "job_id"))
        percent = _require_number(self.percent, "percent")
        if not (0 <= percent <= 100):
            raise ValidationError("percent must be between 0 and 100", field="percent")
        object.__setattr__(self, "percent", percent)
        object.__setattr__(self, "message", _require_str(self.message, "message", non_empty=False))
        _check_version("JobProgress", self.schema_version, "schema_version")

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "percent": self.percent,
            "message": self.message,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> JobProgress:
        payload = _check_payload(cls, data)
        return cls(
            job_id=payload["job_id"],
            percent=payload["percent"],
            message=payload["message"],
            schema_version=payload["schema_version"],
        )


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

    def __post_init__(self) -> None:
        object.__setattr__(self, "job_id", _require_str(self.job_id, "job_id"))
        object.__setattr__(self, "partition_id", _require_str(self.partition_id, "partition_id"))
        status = _require_enum(self.status, JobStatus, "status")
        if status not in (JobStatus.SUCCEEDED, JobStatus.FAILED):
            raise ValidationError("status must be succeeded or failed", field="status")
        object.__setattr__(self, "status", status)
        object.__setattr__(
            self,
            "observation_count",
            _require_int(self.observation_count, "observation_count", minimum=0),
        )
        object.__setattr__(self, "metrics", _number_mapping(self.metrics, "metrics"))
        object.__setattr__(self, "finished_at", _require_datetime(self.finished_at, "finished_at"))
        failure_cause = self.failure_cause
        if failure_cause is not None:
            failure_cause = _require_enum(failure_cause, FailureCause, "failure_cause")
        if status == JobStatus.FAILED and failure_cause is None:
            raise ValidationError("failed requieres failure_cause", field="failure_cause")
        if status == JobStatus.SUCCEEDED and failure_cause is not None:
            raise ValidationError("succeeded doesn't admit failure_cause", field="failure_cause")
        object.__setattr__(self, "failure_cause", failure_cause)
        _check_version("JobResult", self.schema_version, "schema_version")

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "partition_id": self.partition_id,
            "status": self.status.value,
            "observation_count": self.observation_count,
            "metrics": dict(self.metrics),
            "finished_at": _format_timestamp(self.finished_at),
            "failure_cause": (self.failure_cause.value if self.failure_cause is not None else None),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> JobResult:
        payload = _check_payload(cls, data)
        failure_cause_raw = payload.get("failure_cause")
        failure_cause = None
        if failure_cause_raw is not None:
            failure_cause = _parse_enum(failure_cause_raw, FailureCause, "failure_cause")
        return cls(
            job_id=payload["job_id"],
            partition_id=payload["partition_id"],
            status=_parse_enum(payload["status"], JobStatus, "status"),
            observation_count=payload["observation_count"],
            metrics=payload["metrics"],
            finished_at=_parse_timestamp(payload["finished_at"], "finished_at"),
            failure_cause=failure_cause,
            schema_version=payload["schema_version"],
        )


@dataclass(frozen=True)
class AgentInfo:
    hostname: str
    agent_version: str
    platform: str
    capabilities: tuple[str, ...]
    agent_id: str | None = None
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "hostname", _require_str(self.hostname, "hostname"))
        object.__setattr__(self, "agent_version", _require_str(self.agent_version, "agent_version"))
        object.__setattr__(self, "platform", _require_str(self.platform, "platform"))
        object.__setattr__(self, "capabilities", _str_tuple(self.capabilities, "capabilities"))
        object.__setattr__(self, "agent_id", _require_optional_str(self.agent_id, "agent_id"))
        _check_version("AgentInfo", self.schema_version, "schema_version")

    def to_dict(self) -> dict[str, Any]:
        return {
            "hostname": self.hostname,
            "agent_version": self.agent_version,
            "platform": self.platform,
            "capabilities": list(self.capabilities),
            "agent_id": self.agent_id,
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AgentInfo:
        payload = _check_payload(cls, data)
        return cls(
            hostname=payload["hostname"],
            agent_version=payload["agent_version"],
            platform=payload["platform"],
            capabilities=payload["capabilities"],
            agent_id=payload.get("agent_id"),
            schema_version=payload["schema_version"],
        )


@dataclass(frozen=True)
class Heartbeat:
    agent_id: str
    sent_at: datetime
    status: str
    running_job_ids: tuple[str, ...]
    resource_usage: Mapping[str, float]
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(self, "agent_id", _require_str(self.agent_id, "agent_id"))
        object.__setattr__(self, "sent_at", _require_datetime(self.sent_at, "sent_at"))
        object.__setattr__(self, "status", _require_str(self.status, "status"))
        object.__setattr__(
            self, "running_job_ids", _str_tuple(self.running_job_ids, "running_job_ids")
        )
        object.__setattr__(
            self, "resource_usage", _number_mapping(self.resource_usage, "resource_usage")
        )
        _check_version("Heartbeat", self.schema_version, "schema_version")

    def to_dict(self) -> dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "sent_at": _format_timestamp(self.sent_at),
            "status": self.status,
            "running_job_ids": list(self.running_job_ids),
            "resource_usage": dict(self.resource_usage),
            "schema_version": self.schema_version,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Heartbeat:
        payload = _check_payload(cls, data)
        return cls(
            agent_id=payload["agent_id"],
            sent_at=_parse_timestamp(payload["sent_at"], "sent_at"),
            status=payload["status"],
            running_job_ids=payload["running_job_ids"],
            resource_usage=payload["resource_usage"],
            schema_version=payload["schema_version"],
        )
