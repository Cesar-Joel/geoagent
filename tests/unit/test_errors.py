"""Tests de la jerarquía de excepciones del dominio (R2, R3, R4)."""

from __future__ import annotations

import unittest

from geoagent.common.errors import GeoAgentError, UnknownSchemaVersionError, ValidationError


class TestErrorHierarchy(unittest.TestCase):
    def test_validation_error_is_subclass_of_geoagent_error(self) -> None:
        self.assertTrue(issubclass(ValidationError, GeoAgentError))

    def test_geoagent_error_is_direct_subclass_of_exception(self) -> None:
        self.assertEqual(GeoAgentError.__bases__, (Exception,))

    def test_unknown_schema_version_error_is_subclass_of_validation_error(self) -> None:
        self.assertTrue(issubclass(UnknownSchemaVersionError, ValidationError))

    def test_validation_error_has_message_and_field(self) -> None:
        exc = ValidationError("missing mandatory field", field="spec.dataset")
        self.assertEqual(exc.message, "missing mandatory field")
        self.assertEqual(exc.field, "spec.dataset")

    def test_validation_error_field_defaults_to_none(self) -> None:
        exc = ValidationError("mensaje")
        self.assertIsNone(exc.field)

    def test_str_includes_field_when_present(self) -> None:
        exc = ValidationError("missing mandatory field", field="spec.dataset")
        self.assertIn("spec.dataset", str(exc))

    def test_str_without_field_does_not_crash(self) -> None:
        exc = ValidationError("mensaje")
        self.assertIn("mensaje", str(exc))

    def test_unknown_schema_version_error_has_model_version_and_field(self) -> None:
        exc = UnknownSchemaVersionError(model="Job", version=99)
        self.assertEqual(exc.model, "Job")
        self.assertEqual(exc.version, 99)
        self.assertEqual(exc.field, "schema_version")

    def test_unknown_schema_version_error_accepts_custom_field(self) -> None:
        exc = UnknownSchemaVersionError(model="JobSpec", version=2, field="spec.schema_version")
        self.assertEqual(exc.field, "spec.schema_version")

    def test_unknown_schema_version_error_str_includes_field(self) -> None:
        exc = UnknownSchemaVersionError(model="Job", version=2)
        self.assertIn("schema_version", str(exc))


if __name__ == "__main__":
    unittest.main()
