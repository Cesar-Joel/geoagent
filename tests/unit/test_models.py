"""Tests de los modelos de dominio compartidos (feature 2, R1-R36)."""

from __future__ import annotations

import dataclasses
import inspect
import json
import unittest
from dataclasses import FrozenInstanceError, fields
from datetime import datetime, timedelta, timezone, tzinfo

import geoagent.common.models as models
from geoagent.common.errors import UnknownSchemaVersionError, ValidationError
from geoagent.common.models import (
    SCHEMA_VERSION,
    AgentInfo,
    FailureCause,
    Heartbeat,
    Job,
    JobProgress,
    JobResult,
    JobSpec,
    JobStatus,
    can_transition,
)


def _dt(year, month, day, hour=0, minute=0, second=0, microsecond=0, tz=timezone.utc):
    return datetime(year, month, day, hour, minute, second, microsecond, tzinfo=tz)


class _NoneOffsetTzInfo(tzinfo):
    """`tzinfo` cuyo `utcoffset()` devuelve `None` (segundo término de "naive" en R24/R25)."""

    def utcoffset(self, dt) -> None:
        return None

    def dst(self, dt) -> None:
        return None

    def tzname(self, dt) -> None:
        return None


def make_job_spec(**overrides):
    kwargs = dict(
        dataset="sentinel2",
        region=(1.0, 2.0, 3.0, 4.0),
        time_start=_dt(2026, 1, 1),
        time_end=_dt(2026, 1, 2),
        operation="ndvi_summary",
    )
    kwargs.update(overrides)
    return JobSpec(**kwargs)


def make_job(**overrides):
    kwargs = dict(
        job_id="job-1",
        spec=make_job_spec(),
        status=JobStatus.QUEUED,
        created_at=_dt(2026, 1, 1),
    )
    kwargs.update(overrides)
    return Job(**kwargs)


def make_job_progress(**overrides):
    kwargs = dict(job_id="job-1", percent=50.0, message="halfway")
    kwargs.update(overrides)
    return JobProgress(**kwargs)


def make_job_result(**overrides):
    kwargs = dict(
        job_id="job-1",
        partition_id="part-1",
        status=JobStatus.SUCCEEDED,
        observation_count=10,
        metrics={"mean": 0.5},
        finished_at=_dt(2026, 1, 3),
    )
    kwargs.update(overrides)
    return JobResult(**kwargs)


def make_agent_info(**overrides):
    kwargs = dict(
        hostname="host1",
        agent_version="1.0.0",
        platform="linux",
        capabilities=("ndvi",),
    )
    kwargs.update(overrides)
    return AgentInfo(**kwargs)


def make_heartbeat(**overrides):
    kwargs = dict(
        agent_id="agent-1",
        sent_at=_dt(2026, 1, 1),
        status="online",
        running_job_ids=("job-1",),
        resource_usage={"cpu": 0.5},
    )
    kwargs.update(overrides)
    return Heartbeat(**kwargs)


_MODEL_FACTORIES = {
    JobSpec: make_job_spec,
    Job: make_job,
    JobProgress: make_job_progress,
    JobResult: make_job_result,
    AgentInfo: make_agent_info,
    Heartbeat: make_heartbeat,
}

_REQUIRED_KEYS_BY_MODEL = {
    JobSpec: ("dataset", "region", "time_start", "time_end", "operation"),
    Job: ("job_id", "spec", "status", "created_at"),
    JobProgress: ("job_id", "percent", "message"),
    JobResult: (
        "job_id",
        "partition_id",
        "status",
        "observation_count",
        "metrics",
        "finished_at",
    ),
    AgentInfo: ("hostname", "agent_version", "platform", "capabilities"),
    Heartbeat: ("agent_id", "sent_at", "status", "running_job_ids", "resource_usage"),
}

# Valor inválido representativo por cada tipo de campo del Anexo A (`f.type`, cadena estable
# gracias a `from __future__ import annotations`). Alimenta los tests de conexión generados por
# introspección de `dataclasses.fields()` en vez de una tabla de campos escrita a mano: un campo
# nuevo de un tipo ya clasificado queda cubierto sin tocar el test; uno de un tipo nuevo hace
# fallar la guarda de completitud (R29, M7 ronda 4).
_INVALID_VALUE_BY_TYPE = {
    "str": 123,
    "str | None": 123,
    "tuple[float, ...]": "not-a-tuple",
    "tuple[str, ...]": "not-a-list",
    # Naive a propósito: conecta el campo con `_require_datetime` y, de paso, cubre el rechazo
    # de datetimes naive (R24) en los 5 campos `datetime`, sin repetir un test por campo.
    "datetime": datetime(2026, 9, 14, 10, 0, 0),
    "JobSpec": "not-a-jobspec",
    "JobStatus": "queued",
    "float": "not-a-number",
    "int": 1.5,
    "Mapping[str, float]": "not-a-mapping",
    "FailureCause | None": 123,
}

# (modelo, campo) que admiten `""` en vez de rechazarla — excepción explícita al Anexo A.
_EMPTY_STRING_EXCEPTIONS = {("JobProgress", "message")}

# (modelo, campo) → kwargs adicionales que hay que combinar con el valor inválido para que el
# caso llegue de verdad a la comprobación de tipo del campo. Algunos validadores son
# condicionales: `JobResult.failure_cause` solo pasa por `_require_enum` cuando `status` no es
# `succeeded` (si no, la regla de coherencia R34 "succeeded no admite failure_cause" lanza antes,
# con el mismo `field`, y esconde una regresión en `_require_enum`). Sin este contexto, borrar la
# comprobación de tipo de `failure_cause` no hace fallar ningún test (M8, ronda 4 bis).
_FIELD_CONTEXT = {("JobResult", "failure_cause"): {"status": JobStatus.FAILED}}


def _iter_model_fields():
    """Recorre los 6 modelos y sus campos, excluyendo `schema_version` (tests propios)."""
    for model, factory in _MODEL_FACTORIES.items():
        for f in fields(model):
            if f.name == "schema_version":
                continue
            yield model, factory, f


class TestJobStatus(unittest.TestCase):
    def test_exact_values(self) -> None:
        self.assertEqual(
            {member.value for member in JobStatus},
            {"queued", "assigned", "running", "succeeded", "failed", "cancelled"},
        )

    def test_is_terminal(self) -> None:
        terminal = {JobStatus.SUCCEEDED, JobStatus.FAILED, JobStatus.CANCELLED}
        for member in JobStatus:
            with self.subTest(member=member):
                self.assertEqual(member.is_terminal, member in terminal)


class TestFailureCause(unittest.TestCase):
    def test_exact_values(self) -> None:
        self.assertEqual(
            {member.value for member in FailureCause},
            {
                "network",
                "timeout",
                "data_source",
                "resource_exhausted",
                "bad_spec",
                "agent_crash",
                "retries_exhausted",
            },
        )


class TestCanTransition(unittest.TestCase):
    _VALID_PAIRS = {
        (JobStatus.QUEUED, JobStatus.ASSIGNED),
        (JobStatus.QUEUED, JobStatus.CANCELLED),
        (JobStatus.ASSIGNED, JobStatus.RUNNING),
        (JobStatus.ASSIGNED, JobStatus.QUEUED),
        (JobStatus.ASSIGNED, JobStatus.FAILED),
        (JobStatus.ASSIGNED, JobStatus.CANCELLED),
        (JobStatus.RUNNING, JobStatus.SUCCEEDED),
        (JobStatus.RUNNING, JobStatus.FAILED),
        (JobStatus.RUNNING, JobStatus.CANCELLED),
        (JobStatus.RUNNING, JobStatus.QUEUED),
    }

    def test_all_36_pairs(self) -> None:
        for from_status in JobStatus:
            for to_status in JobStatus:
                with self.subTest(from_status=from_status, to_status=to_status):
                    expected = (from_status, to_status) in self._VALID_PAIRS
                    self.assertEqual(can_transition(from_status, to_status), expected)

    def test_invalid_arguments_raise_validation_error(self) -> None:
        with self.assertRaises(ValidationError):
            can_transition("queued", JobStatus.ASSIGNED)
        with self.assertRaises(ValidationError):
            can_transition(JobStatus.QUEUED, None)
        with self.assertRaises(ValidationError):
            can_transition(JobStatus.QUEUED, "assigned")


class TestModelFields(unittest.TestCase):
    def _assert_field_order(self, model, expected_names) -> None:
        names = [f.name for f in fields(model)]
        self.assertEqual(names, expected_names)
        version_field = next(f for f in fields(model) if f.name == "schema_version")
        self.assertEqual(version_field.default, SCHEMA_VERSION)

    def test_job_spec_fields(self) -> None:
        self._assert_field_order(
            JobSpec,
            ["dataset", "region", "time_start", "time_end", "operation", "schema_version"],
        )

    def test_job_fields(self) -> None:
        self._assert_field_order(
            Job,
            ["job_id", "spec", "status", "created_at", "assigned_agent_id", "schema_version"],
        )

    def test_job_progress_fields(self) -> None:
        self._assert_field_order(JobProgress, ["job_id", "percent", "message", "schema_version"])

    def test_job_result_fields(self) -> None:
        self._assert_field_order(
            JobResult,
            [
                "job_id",
                "partition_id",
                "status",
                "observation_count",
                "metrics",
                "finished_at",
                "failure_cause",
                "schema_version",
            ],
        )

    def test_agent_info_fields(self) -> None:
        self._assert_field_order(
            AgentInfo,
            ["hostname", "agent_version", "platform", "capabilities", "agent_id", "schema_version"],
        )

    def test_heartbeat_fields(self) -> None:
        self._assert_field_order(
            Heartbeat,
            [
                "agent_id",
                "sent_at",
                "status",
                "running_job_ids",
                "resource_usage",
                "schema_version",
            ],
        )

    def test_model_factories_cover_every_public_dataclass(self) -> None:
        """`_MODEL_FACTORIES` no debe quedarse atrás de un séptimo modelo público (m1, ronda 4).

        Un `dataclass` público nuevo en `models.py` sin fábrica en `_MODEL_FACTORIES` quedaría
        sin cobertura en todos los tests generados por introspección (claves obligatorias,
        conexión de tipos, cadena vacía, `None` opcional), y ningún otro test lo detectaría,
        porque `TestModelFields` es explícito por modelo."""
        public_dataclasses = {
            obj
            for _, obj in inspect.getmembers(models, inspect.isclass)
            if dataclasses.is_dataclass(obj)
            and obj.__module__ == models.__name__
            and not obj.__name__.startswith("_")
        }
        self.assertEqual(public_dataclasses, set(_MODEL_FACTORIES))

    def test_required_keys_by_model_matches_annex_a_order(self) -> None:
        """`_REQUIRED_KEYS_BY_MODEL` no debe desincronizarse de `fields(model)` (P1, ronda 4
        quater): mismo orden que los campos no opcionales del Anexo A, sin `schema_version`. Sin
        esta guarda, la tabla escrita a mano podría quedar obsoleta sin que ningún test lo
        note."""
        for model in _MODEL_FACTORIES:
            with self.subTest(model=model.__name__):
                expected = tuple(
                    f.name
                    for f in fields(model)
                    if f.name != "schema_version" and not f.type.endswith("| None")
                )
                self.assertEqual(_REQUIRED_KEYS_BY_MODEL[model], expected)


class TestImmutability(unittest.TestCase):
    def _assert_frozen(self, instance, attr) -> None:
        original = getattr(instance, attr)
        with self.assertRaises(FrozenInstanceError):
            setattr(instance, attr, "x")
        self.assertEqual(getattr(instance, attr), original)
        with self.assertRaises(FrozenInstanceError):
            delattr(instance, attr)
        self.assertTrue(hasattr(instance, attr))
        self.assertEqual(getattr(instance, attr), original)

    def test_job_spec_is_frozen(self) -> None:
        self._assert_frozen(make_job_spec(), "dataset")

    def test_job_is_frozen(self) -> None:
        self._assert_frozen(make_job(), "job_id")

    def test_job_progress_is_frozen(self) -> None:
        self._assert_frozen(make_job_progress(), "percent")

    def test_job_result_is_frozen(self) -> None:
        self._assert_frozen(make_job_result(), "observation_count")

    def test_agent_info_is_frozen(self) -> None:
        self._assert_frozen(make_agent_info(), "hostname")

    def test_heartbeat_is_frozen(self) -> None:
        self._assert_frozen(make_heartbeat(), "agent_id")

    def test_mutating_list_argument_does_not_affect_instance(self) -> None:
        region_list = [1.0, 2.0]
        spec = make_job_spec(region=region_list)
        region_list.append(99.0)
        self.assertEqual(spec.region, (1.0, 2.0))

    def test_mutating_dict_argument_does_not_affect_instance(self) -> None:
        metrics = {"mean": 1.0}
        result = make_job_result(metrics=metrics)
        metrics["extra"] = 2.0
        self.assertEqual(dict(result.metrics), {"mean": 1.0})

    def test_collection_fields_are_tuples(self) -> None:
        spec = make_job_spec()
        self.assertIsInstance(spec.region, tuple)
        agent = make_agent_info()
        self.assertIsInstance(agent.capabilities, tuple)
        heartbeat = make_heartbeat()
        self.assertIsInstance(heartbeat.running_job_ids, tuple)

    def test_mapping_field_rejects_item_assignment(self) -> None:
        result = make_job_result()
        with self.assertRaises(TypeError):
            result.metrics["k"] = 1.0
        heartbeat = make_heartbeat()
        with self.assertRaises(TypeError):
            heartbeat.resource_usage["k"] = 1.0

    def test_heartbeat_mutating_arguments_does_not_affect_instance(self) -> None:
        running = ["job-1"]
        usage = {"cpu": 0.5}
        heartbeat = make_heartbeat(running_job_ids=running, resource_usage=usage)
        running.append("job-2")
        usage["extra"] = 9.0
        self.assertEqual(heartbeat.running_job_ids, ("job-1",))
        self.assertEqual(dict(heartbeat.resource_usage), {"cpu": 0.5})


class TestRoundTrip(unittest.TestCase):
    def _assert_round_trip(self, instance) -> None:
        cls = type(instance)
        data = instance.to_dict()
        self.assertEqual(cls.from_dict(data), instance)
        via_json = json.loads(json.dumps(data))
        self.assertEqual(cls.from_dict(via_json), instance)

    def test_job_spec_round_trip(self) -> None:
        self._assert_round_trip(make_job_spec())

    def test_job_round_trip_without_optional(self) -> None:
        self._assert_round_trip(make_job())

    def test_job_round_trip_with_optional(self) -> None:
        self._assert_round_trip(make_job(assigned_agent_id="agent-9", status=JobStatus.ASSIGNED))

    def test_job_progress_round_trip(self) -> None:
        self._assert_round_trip(make_job_progress())

    def test_job_result_round_trip_succeeded(self) -> None:
        self._assert_round_trip(make_job_result())

    def test_job_result_round_trip_failed_with_cause(self) -> None:
        self._assert_round_trip(
            make_job_result(status=JobStatus.FAILED, failure_cause=FailureCause.TIMEOUT)
        )

    def test_agent_info_round_trip_without_optional(self) -> None:
        self._assert_round_trip(make_agent_info())

    def test_agent_info_round_trip_with_optional(self) -> None:
        self._assert_round_trip(make_agent_info(agent_id="agent-1"))

    def test_heartbeat_round_trip(self) -> None:
        self._assert_round_trip(make_heartbeat())

    def test_to_dict_keys_match_annex_a(self) -> None:
        self.assertEqual(
            set(make_job_spec().to_dict().keys()),
            {"dataset", "region", "time_start", "time_end", "operation", "schema_version"},
        )
        self.assertEqual(
            set(make_job().to_dict().keys()),
            {"job_id", "spec", "status", "created_at", "assigned_agent_id", "schema_version"},
        )
        self.assertEqual(
            set(make_job_progress().to_dict().keys()),
            {"job_id", "percent", "message", "schema_version"},
        )
        self.assertEqual(
            set(make_job_result().to_dict().keys()),
            {
                "job_id",
                "partition_id",
                "status",
                "observation_count",
                "metrics",
                "finished_at",
                "failure_cause",
                "schema_version",
            },
        )
        self.assertEqual(
            set(make_agent_info().to_dict().keys()),
            {"hostname", "agent_version", "platform", "capabilities", "agent_id", "schema_version"},
        )
        self.assertEqual(
            set(make_heartbeat().to_dict().keys()),
            {
                "agent_id",
                "sent_at",
                "status",
                "running_job_ids",
                "resource_usage",
                "schema_version",
            },
        )

    def test_to_dict_values_are_json_types(self) -> None:
        def check(value) -> None:
            if isinstance(value, dict):
                for v in value.values():
                    check(v)
            elif isinstance(value, list):
                for v in value:
                    check(v)
            else:
                self.assertIsInstance(value, (str, int, float, bool, type(None)))

        instances = [
            make_job_spec(),
            make_job(),
            make_job_progress(),
            make_job_result(status=JobStatus.FAILED, failure_cause=FailureCause.TIMEOUT),
            make_agent_info(agent_id="a1"),
            make_heartbeat(),
        ]
        for instance in instances:
            check(instance.to_dict())

    def test_to_dict_returns_new_dict_each_call(self) -> None:
        spec = make_job_spec()
        self.assertIsNot(spec.to_dict(), spec.to_dict())

    def test_enum_fields_serialize_as_value(self) -> None:
        self.assertEqual(make_job().to_dict()["status"], "queued")
        result = make_job_result(status=JobStatus.FAILED, failure_cause=FailureCause.TIMEOUT)
        self.assertEqual(result.to_dict()["failure_cause"], "timeout")

    def test_job_to_dict_spec_matches_jobspec_to_dict(self) -> None:
        job = make_job()
        self.assertEqual(job.to_dict()["spec"], job.spec.to_dict())

    def test_from_dict_without_optional_key_yields_none(self) -> None:
        """R28: `from_dict()` sin la clave opcional produce `None`, generado por introspección
        sobre los campos cuyo tipo termina en `| None` (N2, ronda 4 ter). No basta con que el
        campo valga `None`: hay que eliminar la clave del payload para detectar un `payload[...]`
        que debería ser `payload.get(...)`."""
        optional_fields = [
            (model, factory, f)
            for model, factory, f in _iter_model_fields()
            if f.type.endswith("| None")
        ]
        self.assertTrue(optional_fields, "couldn't find any optional fields")
        for model, factory, f in optional_fields:
            with self.subTest(model=model.__name__, field=f.name):
                # Las fábricas por defecto ya producen `None` en los 3 ecampos opcionales
                # (JobResult usa status=SUCCEEDED), así que no hace falta `_FIELD_CONTEXT` aquí:
                # aplicarlo a `failure_cause` forzaría status=FAILED, que exige `failure_cause`
                # distinto de `None` (R34) y rompería este test.
                data = factory().to_dict()
                del data[f.name]
                rebuilt = model.from_dict(data)
                self.assertIsNone(getattr(rebuilt, f.name))


class TestSchemaVersion(unittest.TestCase):
    def test_from_dict_rejects_unknown_versions(self) -> None:
        data = make_job_spec().to_dict()
        for version in (0, 2, 999):
            with self.subTest(version=version):
                bad = dict(data, schema_version=version)
                with self.assertRaises(UnknownSchemaVersionError) as ctx:
                    JobSpec.from_dict(bad)
                self.assertEqual(ctx.exception.model, "JobSpec")
                self.assertEqual(ctx.exception.version, version)

    def test_unknown_version_wins_even_with_missing_fields(self) -> None:
        with self.assertRaises(UnknownSchemaVersionError):
            JobSpec.from_dict({"schema_version": 2})

    def test_unknown_version_wins_even_with_extra_keys(self) -> None:
        data = make_job_spec().to_dict()
        data["schema_version"] = 2
        data["extra"] = "x"
        with self.assertRaises(UnknownSchemaVersionError):
            JobSpec.from_dict(data)

    def test_job_from_dict_rejects_unknown_nested_spec_version(self) -> None:
        data = make_job().to_dict()
        data["spec"]["schema_version"] = 2
        with self.assertRaises(UnknownSchemaVersionError) as ctx:
            Job.from_dict(data)
        self.assertEqual(ctx.exception.field, "spec.schema_version")

    def test_constructor_rejects_unknown_version(self) -> None:
        with self.assertRaises(UnknownSchemaVersionError):
            make_job_spec(schema_version=2)

    def test_from_dict_missing_schema_version_raises_validation_error(self) -> None:
        data = make_job_spec().to_dict()
        del data["schema_version"]
        with self.assertRaises(ValidationError) as ctx:
            JobSpec.from_dict(data)
        self.assertNotIsInstance(ctx.exception, UnknownSchemaVersionError)
        self.assertTrue(ctx.exception.field.endswith("schema_version"))

    def test_from_dict_invalid_schema_version_types_raise_validation_error(self) -> None:
        for value in (True, "1", 1.0):
            with self.subTest(value=value):
                data = make_job_spec().to_dict()
                data["schema_version"] = value
                with self.assertRaises(ValidationError) as ctx:
                    JobSpec.from_dict(data)
                self.assertNotIsInstance(ctx.exception, UnknownSchemaVersionError)
                self.assertTrue(ctx.exception.field.endswith("schema_version"))

    def test_from_dict_rejects_unknown_version_for_every_model(self) -> None:
        for model, factory in _MODEL_FACTORIES.items():
            with self.subTest(model=model.__name__):
                data = factory().to_dict()
                data["schema_version"] = 2
                with self.assertRaises(UnknownSchemaVersionError) as ctx:
                    model.from_dict(data)
                self.assertEqual(ctx.exception.model, model.__name__)
                self.assertEqual(ctx.exception.version, 2)

    def test_constructor_rejects_unknown_version_for_every_model(self) -> None:
        for model, factory in _MODEL_FACTORIES.items():
            with self.subTest(model=model.__name__):
                with self.assertRaises(UnknownSchemaVersionError) as ctx:
                    factory(schema_version=2)
                self.assertEqual(ctx.exception.model, model.__name__)

    def test_from_dict_missing_schema_version_for_every_model(self) -> None:
        for model, factory in _MODEL_FACTORIES.items():
            with self.subTest(model=model.__name__):
                data = factory().to_dict()
                del data["schema_version"]
                with self.assertRaises(ValidationError) as ctx:
                    model.from_dict(data)
                self.assertNotIsInstance(ctx.exception, UnknownSchemaVersionError)
                self.assertTrue(ctx.exception.field.endswith("schema_version"))


class TestTimestamps(unittest.TestCase):
    def test_serializes_with_microseconds_and_z_suffix(self) -> None:
        hb = make_heartbeat(sent_at=_dt(2026, 9, 14, 10, 0, 0, 0))
        self.assertEqual(hb.to_dict()["sent_at"], "2026-09-14T10:00:00.000000Z")

    def test_serializes_year_below_1000_padded(self) -> None:
        hb = make_heartbeat(sent_at=_dt(999, 1, 1))
        self.assertEqual(hb.to_dict()["sent_at"], "0999-01-01T00:00:00.000000Z")

    def test_serializes_nonzero_microseconds(self) -> None:
        hb = make_heartbeat(sent_at=_dt(2026, 9, 14, 10, 0, 0, 123456))
        self.assertEqual(hb.to_dict()["sent_at"], "2026-09-14T10:00:00.123456Z")

    def test_constructor_normalizes_offset_to_utc(self) -> None:
        tz = timezone(timedelta(hours=2))
        dt = datetime(2026, 9, 14, 12, 0, 0, tzinfo=tz)
        spec = make_job_spec(time_start=dt)
        self.assertIs(spec.time_start.tzinfo, timezone.utc)
        self.assertEqual(spec.time_start, dt)

    def test_from_dict_accepts_various_fractions_and_offsets(self) -> None:
        cases = [
            ("2026-09-14T10:00:00Z", _dt(2026, 9, 14, 10, 0, 0, 0)),
            ("2026-09-14T10:00:00.5Z", _dt(2026, 9, 14, 10, 0, 0, 500000)),
            ("2026-09-14T10:00:00.123Z", _dt(2026, 9, 14, 10, 0, 0, 123000)),
            ("2026-09-14T10:00:00.123456Z", _dt(2026, 9, 14, 10, 0, 0, 123456)),
            ("2026-09-14T10:00:00+00:00", _dt(2026, 9, 14, 10, 0, 0, 0)),
            ("2026-09-14T04:30:00-05:30", _dt(2026, 9, 14, 10, 0, 0, 0)),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                data = make_job_spec().to_dict()
                data["time_start"] = value
                spec = JobSpec.from_dict(data)
                self.assertIs(spec.time_start.tzinfo, timezone.utc)
                self.assertEqual(spec.time_start, expected)
                self.assertEqual(spec.time_start.microsecond, expected.microsecond)

    def test_constructor_rejects_datetime_whose_tzinfo_utcoffset_is_none(self) -> None:
        broken = datetime(2026, 9, 14, 10, 0, 0, tzinfo=_NoneOffsetTzInfo())
        with self.assertRaises(ValidationError) as ctx:
            make_job_spec(time_start=broken)
        self.assertEqual(ctx.exception.field, "time_start")

    def test_from_dict_rejects_invalid_timestamp_strings(self) -> None:
        invalid = [
            "2026-09-14T10:00:00",
            "2026-09-14T10:00:00z",
            "2026-09-14 10:00:00Z",
            "2026-09-14T10:00:00.1234567Z",
            "2026-13-01T10:00:00Z",
            "2026-09-14T25:00:00Z",
            "2026-09-14T10:00:00+24:00",
            "2026-09-14T10:00:00+05:60",
            "2026-09-14T10:00:00+00:99",
            "2026-09-14T1٠:00:00Z",
            12345,
        ]
        for value in invalid:
            with self.subTest(value=value):
                data = make_job_spec().to_dict()
                data["time_start"] = value
                with self.assertRaises(ValidationError) as ctx:
                    JobSpec.from_dict(data)
                self.assertEqual(ctx.exception.field, "time_start")

    def test_from_dict_rejects_unzoned_string_for_every_datetime_field(self) -> None:
        unzoned = "2026-09-14T10:00:00"
        cases = [
            (JobSpec, make_job_spec, "time_start"),
            (JobSpec, make_job_spec, "time_end"),
            (Job, make_job, "created_at"),
            (JobResult, make_job_result, "finished_at"),
            (Heartbeat, make_heartbeat, "sent_at"),
        ]
        for model, factory, field in cases:
            with self.subTest(field=field):
                data = factory().to_dict()
                data[field] = unzoned
                with self.assertRaises(ValidationError) as ctx:
                    model.from_dict(data)
                self.assertEqual(ctx.exception.field, field)

    def test_from_dict_rejects_datetime_object_instead_of_string(self) -> None:
        cases = [
            ("naive", datetime(2026, 9, 14, 10, 0, 0)),
            ("aware", _dt(2026, 9, 14, 10)),
        ]
        for label, value in cases:
            with self.subTest(value=label):
                data = make_job_spec().to_dict()
                data["time_start"] = value
                with self.assertRaises(ValidationError) as ctx:
                    JobSpec.from_dict(data)
                self.assertEqual(ctx.exception.field, "time_start")

    def test_job_from_dict_rejects_unzoned_nested_spec_time_start(self) -> None:
        data = make_job().to_dict()
        data["spec"]["time_start"] = "2026-09-14T10:00:00"
        with self.assertRaises(ValidationError) as ctx:
            Job.from_dict(data)
        self.assertEqual(ctx.exception.field, "spec.time_start")


class TestPayloadValidation(unittest.TestCase):
    def test_non_mapping_payload_raises_with_field_none(self) -> None:
        for bad in (None, [], "x", 123):
            with self.subTest(bad=bad):
                with self.assertRaises(ValidationError) as ctx:
                    JobSpec.from_dict(bad)
                self.assertIsNone(ctx.exception.field)

    def test_non_mapping_nested_spec_raises_with_field_spec(self) -> None:
        data = make_job().to_dict()
        data["spec"] = "not-a-mapping"
        with self.assertRaises(ValidationError) as ctx:
            Job.from_dict(data)
        self.assertEqual(ctx.exception.field, "spec")

    def test_missing_required_key_raises_validation_error(self) -> None:
        data = make_job_spec().to_dict()
        del data["dataset"]
        with self.assertRaises(ValidationError) as ctx:
            JobSpec.from_dict(data)
        self.assertEqual(ctx.exception.field, "dataset")

    def test_missing_key_inside_spec_reports_prefixed_field(self) -> None:
        data = make_job().to_dict()
        del data["spec"]["dataset"]
        with self.assertRaises(ValidationError) as ctx:
            Job.from_dict(data)
        self.assertEqual(ctx.exception.field, "spec.dataset")

    def test_wrong_type_in_constructor_raises_with_field(self) -> None:
        cases = [
            (lambda: make_job_spec(dataset=None), "dataset"),
            (lambda: make_job_result(observation_count=True), "observation_count"),
            (lambda: make_job_result(observation_count=1.5), "observation_count"),
            (lambda: make_job(status="queued"), "status"),
            (lambda: make_agent_info(capabilities="ndvi"), "capabilities"),
            (lambda: make_heartbeat(running_job_ids=(1, 2)), "running_job_ids"),
            (lambda: make_job_result(metrics={"mean": "high"}), "metrics"),
        ]
        for build, expected_field in cases:
            with self.subTest(expected_field=expected_field):
                with self.assertRaises(ValidationError) as ctx:
                    build()
                self.assertEqual(ctx.exception.field, expected_field)

    def test_wrong_type_in_from_dict_raises_with_field(self) -> None:
        job_spec_data = make_job_spec().to_dict()
        job_spec_data["dataset"] = None
        with self.assertRaises(ValidationError) as ctx:
            JobSpec.from_dict(job_spec_data)
        self.assertEqual(ctx.exception.field, "dataset")

        job_result_data = make_job_result().to_dict()
        job_result_data["observation_count"] = True
        with self.assertRaises(ValidationError) as ctx:
            JobResult.from_dict(job_result_data)
        self.assertEqual(ctx.exception.field, "observation_count")

        agent_data = make_agent_info().to_dict()
        agent_data["capabilities"] = "ndvi"
        with self.assertRaises(ValidationError) as ctx:
            AgentInfo.from_dict(agent_data)
        self.assertEqual(ctx.exception.field, "capabilities")

        heartbeat_data = make_heartbeat().to_dict()
        heartbeat_data["running_job_ids"] = [1, 2]
        with self.assertRaises(ValidationError) as ctx:
            Heartbeat.from_dict(heartbeat_data)
        self.assertEqual(ctx.exception.field, "running_job_ids")

    def test_wrong_type_in_nested_spec_reports_prefixed_field(self) -> None:
        job_data = make_job().to_dict()
        job_data["spec"]["region"] = [True]
        with self.assertRaises(ValidationError) as ctx:
            Job.from_dict(job_data)
        self.assertEqual(ctx.exception.field, "spec.region")

    def test_constraint_violations(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            make_job(job_id="")
        self.assertEqual(ctx.exception.field, "job_id")

        with self.assertRaises(ValidationError) as ctx:
            make_agent_info(hostname="")
        self.assertEqual(ctx.exception.field, "hostname")

        with self.assertRaises(ValidationError) as ctx:
            make_heartbeat(resource_usage={"": 1.0})
        self.assertEqual(ctx.exception.field, "resource_usage")

        with self.assertRaises(ValidationError) as ctx:
            make_job_spec(region=(float("nan"),))
        self.assertEqual(ctx.exception.field, "region")

        with self.assertRaises(ValidationError) as ctx:
            make_job_spec(region=(float("inf"),))
        self.assertEqual(ctx.exception.field, "region")

        with self.assertRaises(ValidationError) as ctx:
            make_job_result(metrics={"mean": float("inf")})
        self.assertEqual(ctx.exception.field, "metrics")

        with self.assertRaises(ValidationError) as ctx:
            make_job_result(metrics={"mean": float("nan")})
        self.assertEqual(ctx.exception.field, "metrics")

        with self.assertRaises(ValidationError) as ctx:
            make_job_result(observation_count=-1)
        self.assertEqual(ctx.exception.field, "observation_count")

    def test_unknown_enum_value_raises_validation_error_for_every_enum_field(self) -> None:
        """R31: `from_dict()` con un  valor de enum desconocido, generado por introspección sobre
        los campos cuyo `f.type` es `"JobStatus"` o `"FailureCause | None"` (P2, ronda 4 quater).
        Sustituye a la versión manual, que solo cubría `Job.status` y `JobResult.failure_cause` y
        no detectaba un `field` mal copiado en `_parse_enum` de `JobResult.status` (G2)."""
        enum_fields = [
            (model, factory, f)
            for model, factory, f in _iter_model_fields()
            if f.type in ("JobStatus", "FailureCause | None")
        ]
        self.assertTrue(enum_fields, "couldn't find any enum fields")
        for model, factory, f in enum_fields:
            with self.subTest(model=model.__name__, field=f.name):
                data = factory().to_dict()
                # Para `failure_cause`, aplica el contexto status=FAILED de `_FIELD_CONTEXT`
                # sobre el propio payload (no sobre el constructor de la fábrica) para que el
                # payload siga siendo coherente con R34, aunque no haga falta para que
                # `_parse_enum` lance: en `from_dict()`, a diferencia del constructor (M8), la
                # comprobación del enum no depende de otro campo.
                context = _FIELD_CONTEXT.get((model.__name__, f.name), {})
                for key, value in context.items():
                    data[key] = getattr(value, "value", value)
                data[f.name] = "paused"
                with self.assertRaises(ValidationError) as ctx:
                    model.from_dict(data)
                self.assertEqual(ctx.exception.field, f.name)

    def test_unknown_key_raises_validation_error_for_every_model(self) -> None:
        """R35: una clave que no figura en el Anexo A se rechaza en cada uno de los 6 modelos
        (P3, ronda 4 quater). `test_unknown_key_top_level_and_nested_raise_with_path` solo
        cubría `JobSpec` y el `spec` anidado de `Job`; una clave de más en `JobResult`,
        `JobProgress`, `AgentInfo` o `Heartbeat` no la detectaba nada (G5-G7)."""
        for model, factory in _MODEL_FACTORIES.items():
            with self.subTest(model=model.__name__):
                data = factory().to_dict()
                data["zz_unknown"] = "x"
                with self.assertRaises(ValidationError) as ctx:
                    model.from_dict(data)
                self.assertEqual(ctx.exception.field, "zz_unknown")

    def test_unknown_key_top_level_and_nested_raise_with_path(self) -> None:
        data = make_job_spec().to_dict()
        data["dataset_id"] = "x"
        with self.assertRaises(ValidationError) as ctx:
            JobSpec.from_dict(data)
        self.assertEqual(ctx.exception.field, "dataset_id")

        data2 = make_job().to_dict()
        data2["spec"]["dataset_id"] = "x"
        with self.assertRaises(ValidationError) as ctx2:
            Job.from_dict(data2)
        self.assertEqual(ctx2.exception.field, "spec.dataset_id")

    def test_unknown_keys_with_mixed_types_do_not_raise_type_error(self) -> None:
        data = dict(make_job_spec().to_dict())
        data[1] = "x"
        data["zz"] = "y"
        with self.assertRaises(ValidationError) as ctx:
            JobSpec.from_dict(data)
        self.assertIsInstance(ctx.exception.field, str)

    def test_missing_required_key_for_every_model_and_key(self) -> None:
        for model, factory in _MODEL_FACTORIES.items():
            required_keys = _REQUIRED_KEYS_BY_MODEL[model]
            for key in required_keys:
                with self.subTest(model=model.__name__, key=key):
                    data = factory().to_dict()
                    del data[key]
                    with self.assertRaises(ValidationError) as ctx:
                        model.from_dict(data)
                    self.assertEqual(ctx.exception.field, key)

    def test_missing_required_keys_report_first_in_annex_a_order_for_every_model(self) -> None:
        """R27: cuando faltan varias claves obligatorias a la vez, se informa la primera en el
        orden del Anexo A. Recorre, para cada modelo, cada índice `i` de
        `_REQUIRED_KEYS_BY_MODEL[model]` y borra el sufijo `keys[i:]`; así detecta cualquier
        permutación de la tupla `required` de `from_dict()` (P1, ronda 4 quater), algo que
        `test_missing_required_key_for_every_model_and_key` no puede detectar porque solo borra
        una clave a la vez y nunca deja más de una candidata."""
        for model, factory in _MODEL_FACTORIES.items():
            keys = _REQUIRED_KEYS_BY_MODEL[model]
            for i, expected_field in enumerate(keys):
                with self.subTest(model=model.__name__, index=i, expected_field=expected_field):
                    data = factory().to_dict()
                    for key in keys[i:]:
                        del data[key]
                    with self.assertRaises(ValidationError) as ctx:
                        model.from_dict(data)
                    self.assertEqual(ctx.exception.field, expected_field)

    def test_every_field_wrong_type_raises_with_field(self) -> None:
        """Test de conexión generado por introspección: un caso por campo (R29, M7 ronda 4).

        Cada caso se combina con el contexto de `_FIELD_CONTEXT` cuando existe uno para ese
        (modelo, campo), para que el valor inválido llegue de verdad a la comprobación de tipo
        del campo y no a una regla de coherencia previa que dependa de otro campo (M8, ronda 4
        bis)."""
        context_keys_seen = set()
        for model, factory, f in _iter_model_fields():
            if f.type not in _INVALID_VALUE_BY_TYPE:
                self.fail(f"unclassified type: {model.__name__}.{f.name}: {f.type}")
            invalid = _INVALID_VALUE_BY_TYPE[f.type]
            key = (model.__name__, f.name)
            context = _FIELD_CONTEXT.get(key, {})
            if key in _FIELD_CONTEXT:
                context_keys_seen.add(key)
            with self.subTest(model=model.__name__, field=f.name, type=f.type):
                with self.assertRaises(ValidationError) as ctx:
                    factory(**context, **{f.name: invalid})
                self.assertEqual(ctx.exception.field, f.name)
        missing_context_targets = set(_FIELD_CONTEXT) - context_keys_seen
        self.assertFalse(
            missing_context_targets,
            f"_FIELD_CONTEXT has entries for nonexisting fields: {missing_context_targets}",
        )

    def test_optional_fields_accept_none(self) -> None:
        """Anexo A (constructor): todo campo cuyo tipo termina en `| None` admite `None`
        explícito. No verifica R28 (esa vía es `from_dict()` sin la clave, cubierta por
        `test_from_dict_without_optional_key_yields_none`); realineado en ronda 4 ter, m3."""
        optional_fields = [
            (model, factory, f)
            for model, factory, f in _iter_model_fields()
            if f.type.endswith("| None")
        ]
        self.assertTrue(optional_fields, "couldn't find optional fields")
        for model, factory, f in optional_fields:
            with self.subTest(model=model.__name__, field=f.name):
                instance = factory(**{f.name: None})
                self.assertIsNone(getattr(instance, f.name))

    def test_str_fields_reject_empty_string_unless_excepted(self) -> None:
        """R30: `""` se rechaza en todo campo `str`/`str | None`, salvo la excepción explícita."""
        exceptions_seen = set()
        for model, factory, f in _iter_model_fields():
            if f.type not in ("str", "str | None"):
                continue
            key = (model.__name__, f.name)
            with self.subTest(model=model.__name__, field=f.name):
                if key in _EMPTY_STRING_EXCEPTIONS:
                    exceptions_seen.add(key)
                    instance = factory(**{f.name: ""})
                    self.assertEqual(getattr(instance, f.name), "")
                else:
                    with self.assertRaises(ValidationError) as ctx:
                        factory(**{f.name: ""})
                    self.assertEqual(ctx.exception.field, f.name)
        missing = _EMPTY_STRING_EXCEPTIONS - exceptions_seen
        self.assertFalse(missing, f"nonexisting empty string exceptions: {missing}")


class TestJobProgressBoundaries(unittest.TestCase):
    def test_percent_out_of_range_or_nan_raises(self) -> None:
        for bad in (-0.1, 100.1, float("nan")):
            with self.subTest(bad=bad):
                with self.assertRaises(ValidationError) as ctx:
                    make_job_progress(percent=bad)
                self.assertEqual(ctx.exception.field, "percent")

    def test_percent_boundaries_are_valid(self) -> None:
        self.assertEqual(make_job_progress(percent=0).percent, 0.0)
        self.assertEqual(make_job_progress(percent=100).percent, 100.0)

    def test_percent_int_normalized_to_float(self) -> None:
        progress = make_job_progress(percent=50)
        self.assertIsInstance(progress.percent, float)
        self.assertEqual(progress.percent, 50.0)


class TestJobResultBoundaries(unittest.TestCase):
    _BAD_STATUSES = (JobStatus.QUEUED, JobStatus.RUNNING, JobStatus.CANCELLED)

    def test_status_other_than_succeeded_or_failed_raises(self) -> None:
        for bad_status in self._BAD_STATUSES:
            with self.subTest(bad_status=bad_status):
                with self.assertRaises(ValidationError) as ctx:
                    make_job_result(status=bad_status, failure_cause=None)
                self.assertEqual(ctx.exception.field, "status")

    def test_status_other_than_succeeded_or_failed_raises_via_from_dict(self) -> None:
        for bad_status in self._BAD_STATUSES:
            with self.subTest(bad_status=bad_status):
                data = make_job_result().to_dict()
                data["status"] = bad_status.value
                data["failure_cause"] = None
                with self.assertRaises(ValidationError) as ctx:
                    JobResult.from_dict(data)
                self.assertEqual(ctx.exception.field, "status")

    def test_failed_without_cause_raises(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            make_job_result(status=JobStatus.FAILED, failure_cause=None)
        self.assertEqual(ctx.exception.field, "failure_cause")

    def test_succeeded_with_cause_raises(self) -> None:
        with self.assertRaises(ValidationError) as ctx:
            make_job_result(status=JobStatus.SUCCEEDED, failure_cause=FailureCause.TIMEOUT)
        self.assertEqual(ctx.exception.field, "failure_cause")


class TestJobSpecBoundary(unittest.TestCase):
    def test_time_end_before_time_start_is_allowed(self) -> None:
        spec = make_job_spec(time_start=_dt(2026, 1, 2), time_end=_dt(2026, 1, 1))
        self.assertEqual(spec.time_start, _dt(2026, 1, 2))
        self.assertEqual(spec.time_end, _dt(2026, 1, 1))

    def test_region_any_length_including_empty_is_allowed(self) -> None:
        for region in ((), (1.0, 2.0, 3.0), (1.0, 2.0, 3.0, 4.0, 5.0)):
            with self.subTest(region=region):
                spec = make_job_spec(region=region)
                self.assertEqual(spec.region, tuple(float(x) for x in region))

    def test_unknown_operation_is_allowed(self) -> None:
        spec = make_job_spec(operation="unknown_op")
        self.assertEqual(spec.operation, "unknown_op")


if __name__ == "__main__":
    unittest.main()
