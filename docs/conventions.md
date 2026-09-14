# Convenciones de código

> Homogeneidad extrema. La IA predice mejor cuando el repositorio se parece
> a sí mismo en todas partes.

## Estilo Python

- **Versión:** Python 3.9+ (sintaxis `list[str]` permitida).
- **Formato:** PEP 8. Líneas máximo 100 caracteres.
- **Imports:** stdlib primero, luego terceros, luego locales. Una línea por
  módulo.
- **Strings:** comillas dobles `"..."` siempre. Comillas simples solo
  para escapar comillas dobles dentro.
- **f-strings** para interpolación. Nada de `.format()` ni `%`.
- **Timestamps:** siempre ISO 8601 UTC con sufijo `Z` al serializar.
  Internamente `datetime` con `tzinfo=timezone.utc`.

## Nombres

| Tipo                    | Convención        | Ejemplo                     |
|-------------------------|-------------------|-----------------------------|
| Paquetes                | `snake_case`      | `geoagent.agent`            |
| Módulos                 | `snake_case`      | `store.py`                  |
| Clases                  | `PascalCase`      | `LocalStore`                |
| Funciones / variables   | `snake_case`      | `load_agent_config`         |
| Constantes              | `UPPER_SNAKE`     | `DEFAULT_HEARTBEAT_INTERVAL`|
| Privadas                | prefijo `_`       | `_atomic_write`             |
| Excepciones             | sufijo `Error`    | `TransientBackendError`     |
| Enums                   | `PascalCase`      | `JobStatus`                 |

## Estructura de archivo

Cada archivo en `src/` empieza con:

```python
"""Una línea describiendo el propósito del módulo."""
from __future__ import annotations

# imports stdlib
import json
import os

# imports terceros
import httpx

# imports locales
from geoagent.common.models import Job
```

## Tests

- Un archivo de test por módulo: `tests/unit/test_<módulo>.py` para unitarios y `tests/integration/test_<área>.py` para integración.
- Una clase `Test<Cosa>(unittest.TestCase)` por unidad lógica.
- Cada test usa `tempfile.TemporaryDirectory()` o un fixture equivalente y limpia tras de sí. Nunca se toca el sistema de archivos real fuera del directorio temporal.
- Nombres de test descriptivos: `test_load_returns_empty_when_file_missing`.
- Los tests que dependen del tiempo usan un reloj controlado; nada de `sleep` reales.
- Toda feature con `"sdd": true` documenta su trazabilidad `R<n> → test en progress/impl_<name>.md`.

## Manejo de errores

Jerarquía de errores del dominio, definida en `src/geoagent/common/errors.py`:

```python
class GeoAgentError(Exception):
    """Base para todos los errores del dominio."""

class ValidationError(GeoAgentError):
    """Payload o configuración inválida."""

class TransientBackendError(GeoAgentError):
    """Timeout, error de conexión, 5xx o 429."""

class PermanentBackendError(GeoAgentError):
    """4xx distinto de 429."""

class TransientGeoDataError(GeoAgentError):
    """Cuota, timeout o 5xx de la fuente geoespacial."""

class PermanentGeoDataError(GeoAgentError):
    """Región inválida o dataset inexistente."""
```

## Comentarios

Por defecto **no** se escriben. Solo se permiten cuando explican un **por qué**
no obvio (p. ej. workaround documentado, invariante sutil, decisión de
protocolo con la cola). Los nombres deben hacer el resto.

## Logging

- Nunca `print()` para diagnóstico. Usa el logger de `common/logging.py`.
- Cada evento de log es un objeto JSON con al menos `timestamp`, `level`, `event`, `component`, `agent_id`, `job_id`, `request_id` y `message`.
- `job_id` y `request_id` se propagan por contexto; no se pasan a mano.
- Los campos sensibles salen enmascarados.
