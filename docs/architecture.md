# Arquitectura — Qué significa "hacer un buen trabajo"

> Este documento define el estándar de calidad. Los agentes revisores
> evalúan código contra este archivo. Si no está aquí, no es un requisito.

## Principios

1. **Capas claras.** El proyecto se organiza en paquetes por responsabilidad,
   tal como define `feature_list.json`:
   - `src/geoagent/common/` — modelos de dominio, configuración, logging,
     cola, retry, geodata y utilidades transversales.
   - `src/geoagent/agent/` — runtime del endpoint: store local, cliente REST,
     motor de ejecución, heartbeat, gestión de recursos.
   - `src/geoagent/backend/` — servicio HTTP central: API REST, Job Manager,
     Agent Manager, Log Manager, métricas y persistencia.
   - `src/geoagent/spark/` — pipeline de agregación distribuida.
   - `src/geoagent/tools/` — CLIs auxiliares (log investigation, chaos, verify).
   No introducir capas adicionales (servicios genéricos, repositorios, ORMs)
   hasta que haya una razón concreta documentada en `feature_list.json`.

2. **Dependencias justificadas.** Solo se añade una dependencia externa si la
   feature que la requiere está aprobada y su spec lo documenta. Cualquier
   dependencia nueva se declara en `pyproject.toml` con versión mínima fijada.

3. **Errores explícitos y tipados.** Las funciones que pueden fallar lanzan
   excepciones nombradas y clasificadas (transitorias vs permanentes), nunca
   devuelven `None` para señalar fallo ni propagan excepciones crudas de
   librerías. Toda excepción de dominio hereda de una base común en
   `src/geoagent/common/errors.py`.

4. **Inmutabilidad por defecto.** Los modelos de dominio (`AgentInfo`, `Job`,
   `JobSpec`, `JobProgress`, `JobResult`, `Heartbeat`) son inmutables
   (`@dataclass(frozen=True)` o equivalente). Modificar = crear una instancia
   nueva. Toda instancia expone `to_dict()`/`from_dict()` y `schema_version`.

5. **Atomicidad y persistencia.** Toda escritura a disco (store local del
   agente, store del backend, caché de particiones) se hace primero en un
   archivo temporal y luego `os.replace()`. Nunca dejar un archivo a medio
   escribir ni un registro parcial en SQLite fuera de una transacción.

6. **Idempotencia y recuperación.** El sistema está diseñado para sobrevivir a
   reentregas, crashes y cortes de red. Toda operación que pueda repetirse
   (consumo de cola, POST con `Idempotency-Key`, reporte de resultado) es
   idempotente o deduplicable por clave estable.

## Flujo de datos

```
usuario / operador
│
├─→ backend REST (backend/app.py)
│ │
│ ├─ Job Manager ─→ JobQueue (common/queue.py) ─→ broker
│ ├─ Agent Manager ←─ POST /v1/agents/register y /heartbeat
│ ├─ Log Manager ←─ POST /v1/logs
│ └─ Backend Store (SQLite, esquema versionado)
│
└─→ agente (agent/runtime.py)
│
├─ BackendClient (agent/client.py) ─→ backend REST
├─ LocalStore (agent/store.py, SQLite, esquema versionado)
├─ JobQueue.consume/ack/nack
└─ execution engine ─→ GeoDataSource (common/geodata.py)
│
├─ EarthEngineSource (real)
└─ LocalFixtureSource (determinista)

resultados persistidos ─→ spark/aggregate.py ─→ agregaciones por región/fecha
```

## Qué NO hacer

- No usar `print()` para errores ni para logging operativo. Usa el logger
  estructurado de `common/logging.py`; para errores de CLI, `sys.stderr` y
  exit code != 0.
- No mezclar IO con lógica de dominio dentro de `common/models.py`. Los
  modelos no leen ni escriben disco.
- No leer/escribir el store en cada iteración de un bucle. Carga al inicio,
  modifica en memoria, persiste al final o en checkpoints explícitos.
- No añadir un sistema de configuración ad-hoc. Toda configuración pasa por
  `common/config.py` con la precedencia
  env > archivo > defaults y prefijo `GEOAGENT_`.
- No bloquear el proceso indefinidamente: toda llamada de red, cola o
  fuente de datos lleva timeout explícito.
- No registrar secretos (tokens, credenciales de broker) en logs ni en
  `repr()` de objetos de configuración.
