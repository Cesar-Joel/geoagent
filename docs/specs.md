# Spec Driven Development (SDD)

> Este proyecto sigue un flujo Kiro-style: requirements → design → tasks → code.
> El código no se escribe hasta que el spec está aprobado por un humano.

## Estructura

Cada feature nueva (`"sdd": true` en `feature_list.json`) tiene una carpeta
dedicada en cuanto deja `pending`:

```
specs/<feature-name>/
├── requirements.md   # QUÉ se necesita (EARS notation)
├── design.md         # CÓMO se construirá (decisiones técnicas)
└── tasks.md          # PASOS concretos a implementar
```

El `feature-name` coincide con el campo `name` de `feature_list.json`
(p. ej. `specs/core_domain_models/`, `specs/agent_local_store/`,
`specs/message_queue_layer/`).

## Estados de una feature

| Estado         | Significado                                                    |
|----------------|----------------------------------------------------------------|
| `pending`      | Sin spec. El `spec_author` es el primero en actuar.            |
| `spec_ready`   | Spec drafted. Esperando aprobación humana. NO se toca código.  |
| `in_progress`  | Spec aprobado. `implementer` trabajando.                       |
| `done`         | Código verde, `reviewer` aprobó, sesión cerrada.               |
| `blocked`      | Atascado. Razón en `progress/current.md`.                      |

## La puerta de aprobación humana

El flujo automático se detiene **una vez**: cuando el `spec_author` termina
sus tres archivos, marca la feature como `spec_ready` y para. El humano
lee `specs/<feature>/` y dice "aprobado" (o pide cambios).

Solo entonces el `leader` transiciona `spec_ready → in_progress` y lanza
el `implementer`.

```
pending → [spec_author] → spec_ready → ⏸ HUMANO → in_progress → [implementer → reviewer] → done
```

## requirements.md — EARS estricto

Las requirements se redactan en **EARS** (Easy Approach to Requirements
Syntax). Cada requirement es un párrafo numerado con uno de estos cinco
patrones:

| Patrón         | Plantilla                                                   |
|----------------|-------------------------------------------------------------|
| **Ubicuo**     | `El sistema DEBE <acción>.`                                 |
| **Evento**     | `CUANDO <disparador>, el sistema DEBE <acción>.`            |
| **Estado**     | `MIENTRAS <estado>, el sistema DEBE <acción>.`              |
| **Opcional**   | `DONDE <feature opcional>, el sistema DEBE <acción>.`       |
| **No deseado** | `SI <evento no deseado> ENTONCES el sistema DEBE <acción>.` |

Reglas duras:

- Cada requirement tiene un id estable: `R1`, `R2`, ...
- Cada requirement DEBE ser verificable por al menos un test concreto.
- No mezcles varios `DEBE` en un mismo requirement. Si hay más de uno, parte.
- No uses verbos blandos ("podría", "puede", "soporta"). Solo `DEBE` / `NO DEBE`.

Ejemplo:

```markdown
## R1
CUANDO el backend recibe `POST /v1/jobs` con un `JobSpec` válido, el sistema
DEBE crear el job, persistirlo con estado `queued` y devolver 201 con su
`job_id`.

## R2
SI el `JobSpec` tiene un rango temporal invertido ENTONCES el sistema DEBE
devolver 422 con el campo ofensor en el cuerpo de error.
```

## design.md — decisiones técnicas

Captura **antes** de tocar código:

- Qué archivos se crean / modifican.
- Qué firmas nuevas aparecen (funciones, clases, endpoints, comandos).
- Qué excepciones se reutilizan o se añaden desde `common/errors.py`.
- Qué contratos con la cola, el store o la fuente geoespacial se ven afectados.
- Qué alternativa se descartó y por qué (mínimo una).

NO es ingeniería desde primeros principios — apóyate en
`docs/architecture.md` y `docs/conventions.md`. El `design.md` documenta los
puntos donde tu feature roza la frontera de esas reglas.

## tasks.md — checklist ejecutable

Pasos discretos en orden, cada uno con checkbox. Cada task referencia al
menos un `R<n>` que cubre.

Ejemplo:

```markdown
- [ ] T1 — Definir esquema SQLite versionado en `src/geoagent/agent/store.py`. Cubre: R1, R2.
- [ ] T2 — Implementar `LocalStore.__init__` con creación en frío y migración automática. Cubre: R3, R4.
- [ ] T3 — Serializar acceso desde varios hilos con conexión por hilo o lock. Cubre: R5.
- [ ] T4 — Añadir `test_local_store_cold_creation` en `tests/unit/test_local_store.py`. Cubre: R1.
- [ ] T5 — Añadir `test_local_store_rollback_on_error` y `test_local_store_migration`. Cubre: R3, R4.
```

El `implementer` marca `[x]` cada task al completarla. El `reviewer`
rechaza si queda alguna `[ ]` sin justificación documentada.

## Trazabilidad (regla dura)

- Cada test en `tests/` debe poder mapearse a un `R<n>` de su spec.
- Cada `R<n>` debe tener al menos un test concreto.
- El `reviewer` comprueba esta correspondencia explícitamente y rechaza
  si falta.

El `implementer` documenta el mapa en `progress/impl_<name>.md`:

```markdown
## Trazabilidad
- R1 → `test_local_store_cold_creation`
- R2 → `test_local_store_persistence_between_instances`
- R3 → `test_local_store_rollback_on_error`
- R4 → `test_local_store_migration`
- R5 → `test_local_store_concurrent_access`
```

## Cuándo NO aplica SDD

Las features con "sdd": false (por ejemplo `project_scaffold`,
`config_system`, `unit_test_suite` en `feature_list.json`) NO tienen spec.
SDD solo se aplica a las features marcadas con `"sdd": true`.
