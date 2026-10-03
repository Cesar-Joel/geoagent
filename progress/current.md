# Sesión actual

> Este archivo se vacía al cerrar cada sesión y se mueve a `history.md`.
> Mientras trabajas, **mantenlo actualizado en tiempo real**, no al final.

- **Feature en curso:** 2 `core_domain_models` (reabierta, ronda 4)
- **Inicio:** 2026-09-27
- **Agente:** leader → implementer → reviewer
- **Rama:** feat/2-core_domain_models

## Plan

1. implementer: resolver M7 de `progress/review_core_domain_models.md` (solo tests).
2. reviewer: ronda 4.
3. Si aprueba: el implementer cierra la feature (`done` y nota en `history.md`).

## Bitácora

- 2026-09-27: revisión humana. Siguiendo el criterio de M5 y M6 (un caso por campo para los tests de conexión), los campos `str` apenas tienen test de conexión: 3 de 14. Feature reabierta: `done` → `in_progress`.
- 2026-09-27: M7 se rehízo con tests generados por introspección (98 passed, 195 subtests). Reviewer, ronda 4 (mutaciones sobre una copia de `src/`, autorizado por el humano): CHANGES_REQUESTED. M8: el caso `failure_cause → 123` pasa por la regla de `succeeded` y no por la comprobación de tipo. Además: guarda del séptimo modelo y trazabilidad. Devuelto al implementer (ronda 4 bis).
- 2026-09-27: ronda 4 bis → CHANGES_REQUESTED por N2 (R28 solo en `Job.assigned_agent_id`); se resolvió en la ronda 4 ter con un test generado. Ronda 4 ter → CHANGES_REQUESTED tras un barrido completo de las conexiones de `from_dict()`: P1 (orden de R27), P2 (R31 en `JobResult.status`), P3 (R35 en 4 modelos). Devuelto al implementer (ronda 4 quater).
- 2026-09-27: ronda 4 quater → APPROVED (102 passed, 246 subtests). El test de R35 espía `_check_payload` con `mock` y es frágil. El humano elige D1: derivar las claves obligatorias y opcionales de `dataclasses.fields()`. Enmienda al spec en curso con el spec_author, que la dejará en `spec_ready`. ⏸ Después hace falta la aprobación humana.
- 2026-09-27: el spec_author deja la enmienda D12 (design §5 y tasks T21–T26) en `spec_ready`. ⏸ ESPERANDO APROBACIÓN HUMANA.
- 2026-10-02: el humano aprueba D12 ("aprobado D12, pásala a in_progress"). `spec_ready` → `in_progress`. Se lanza el implementer con T21–T26.
- 2026-10-02: implementer completa T21–T26 (lint OK, 101 passed, 240 subtests; mutante M2 equivalente). Reviewer, ronda D12: CHANGES_REQUESTED solo por H1 (fila R35 del mapa de trazabilidad citaba el test espía eliminado) y m1 (constancia de `./init.sh`). El leader corrige ambos en `progress/impl_core_domain_models.md`. Según el reviewer, con H1 resuelto la ronda queda APPROVED. ⏸ Pendiente: cierre de la feature.
- 2026-10-02: el humano resuelve n1 de la revisión D12 y pide alinear `test_status_other_than_succeeded_or_failed_raises_via_from_dict` con el test del constructor. El implementer lo hace con `_BAD_STATUSES` compartido (QUEUED, RUNNING, CANCELLED): 101 passed, 243 subtests, lint OK. ⏸ Pendiente: cierre de la feature.
- 2026-10-02: el humano autoriza el cierre. El implementer marca la feature 2 como `done` y la registra en `history.md` (lint OK, 101 passed, 243 subtests). El leader reescribe la sección "Idioma" de `docs/conventions.md` (código en inglés, todo lo demás en español) y añade a `CLAUDE.md` la regla de hablarle al humano en español.

## Próximo paso

m8: añadir medición de cobertura (pytest-cov) — pendiente de infraestructura.
