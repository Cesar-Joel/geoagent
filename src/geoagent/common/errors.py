"""Jerarquía de excepciones del dominio de geoagent."""

from __future__ import annotations


class GeoAgentError(Exception):
    """Base para todos los errores del dominio."""


class ValidationError(GeoAgentError):
    """Payload o configuración inválida."""

    def __init__(self, message: str, field: str | None = None) -> None:
        self.message = message
        self.field = field
        if field is not None:
            super().__init__(f"{field}: {message}")
        else:
            super().__init__(message)


class UnknownSchemaVersionError(ValidationError):
    """Payload con un schema_version que el modelo no sabe leer."""

    def __init__(self, model: str, version: int, field: str = "schema_version") -> None:
        self.model = model
        self.version = version
        message = f"{model}: unknown schema version ({version!r})"
        super().__init__(message, field=field)
