# AGENTS.md — Mapa de navegación para agentes de IA

> Este archivo es el **punto de entrada** para cualquier agente que trabaje en este
> repositorio. NO es una biblia de reglas: es un **mapa**. Lee solo lo que
> necesites cuando lo necesites (divulgación progresiva).

---

## 1. Antes de empezar (obligatorio)

1. Ejecuta `./init.sh` y verifica que termina sin errores. Si falla, **para**
   y resuelve el entorno antes de tocar código.
2. Lee `progress/current.md` para entender en qué estado quedó la última sesión.
3. Lee `feature_list.json`. Toda feature nueva (`"sdd": true`) pasa por
   **Spec Driven Development** — ver `docs/specs.md` y §4 de este archivo.
4. Lee `docs/specs.md` antes de tocar cualquier spec o feature `sdd: true`.

## 2. Mapa del repositorio

| Archivo / carpeta            | Qué contiene                                                                | Cuándo leerlo |
|------------------------------|-----------------------------------------------------------------------------|---------------|
| `feature_list.json`          | Lista de tareas con estado (`pending` / `spec_ready` / `in_progress` / `done` / `blocked`) | Siempre, al empezar |
| `progress/current.md`        | Estado de la sesión actual + notas persistentes para features futuras      | Siempre, al empezar |
| `progress/history.md`        | Bitácora append-only de sesiones anteriores                                 | Si necesitas contexto histórico |
| `specs/<feature>/`           | `requirements.md` + `design.md` + `tasks.md` (Kiro-style)                   | Antes de implementar cualquier feature con `"sdd": true` |
| `docs/architecture.md`       | Qué significa "hacer un buen trabajo" en este proyecto                      | Antes de implementar |
| `docs/conventions.md`        | Reglas de estilo, nombres, estructura                                       | Antes de escribir código |
| `docs/specs.md`              | Proceso SDD: EARS notation, los 3 archivos, puerta de aprobación humana     | Antes de redactar o leer un spec |
| `docs/verification.md`       | Cómo verificar que tu trabajo funciona (incluye trazabilidad requirements)  | Antes de declarar una tarea como `done` |
| `CHECKPOINTS.md`             | Criterios objetivos de "estado final correcto"                              | Para auto-evaluarte |
| `.claude/agents/`            | Definiciones de subagentes (`leader`, `spec_author`, `implementer`, `reviewer`) | Si orquestas trabajo |
| `.claude/skills/`            | Procedimientos reutilizables (`sesion-preguntas`: dudas del humano sobre el código; `pausar-sesion`: pausar y retomar una feature a medias) | Cuando el humano los invoque o el caso encaje |
| `src/`                       | Código de la aplicación                                                     | Para implementar |
| `tests/`                     | Tests automáticos                                                           | Para verificar |

## 3. Reglas duras (no negociables)

- **Una sola feature a la vez.** No mezcles cambios de varias tareas en la misma sesión.
- **No declares una tarea `done` sin pruebas verdes.** Ejecuta `./init.sh` y
  asegúrate de que el bloque de tests pasa al 100%.
- **No saltes la fase de spec.** Toda feature con `"sdd": true` debe pasar
  por `spec_author` y obtener aprobación humana antes de tocar código.
- **No saltes la puerta de aprobación humana.** El leader detiene el flujo
  en `spec_ready` y espera.
- **Documenta lo que haces** en `progress/current.md` mientras trabajas, no al final.
- **Deja el repositorio limpio** antes de cerrar la sesión (ver §5).
- **Si no sabes algo, busca en `docs/`** antes de inventarlo.

## 4. Flujo de trabajo (SDD)

```
pending → [spec_author] → spec_ready → ⏸ HUMANO → in_progress → [implementer → reviewer] → done
```

1. El leader detecta la primera feature `pending` con `"sdd": true`.
2. El leader lanza `spec_author`, que crea
   `specs/<name>/{requirements,design,tasks}.md` y marca el status como
   `spec_ready`.
3. **Pausa.** El humano lee el spec en `specs/<name>/` y aprueba (o pide cambios).
4. Una vez aprobado, el leader cambia el status a `in_progress` y lanza `implementer`.
5. El implementer ejecuta `tasks.md` una a una, marcándolas `[x]`.
6. El reviewer verifica trazabilidad `R<n>` ↔ test y tasks completas;
   aprueba o rechaza.
7. Si aprueba, el implementer marca `done` y mueve el resumen a
   `progress/history.md`.

## 5. Cierre de sesión (lifecycle)

Si hay que parar con la feature a medias, no apliques este cierre: usa la skill
`pausar-sesion`, que guarda el estado y el siguiente paso sin vaciar `progress/current.md`.

Antes de terminar:

1. Ejecuta `./init.sh` — todo verde.
2. Si la tarea está acabada: marca `status: "done"` en `feature_list.json`.
3. Mueve el resumen de `progress/current.md` al final de `progress/history.md`.
4. Vacía `progress/current.md` dejando solo la plantilla, **pero conserva intacta la
   sección "Notas para features futuras"** (ver §5 bis).
5. No dejes archivos temporales, ni `print()` de debug, ni TODOs sin contexto.

## 5 bis. Notas para features futuras

Todo lo que surja en una sesión y corresponda a **otra** feature (recomendaciones del reviewer,
decisiones aplazadas, deuda de tooling) va a la sección "Notas para features futuras" de
`progress/current.md`. Esa sección **sobrevive al cierre de sesión**.

- **Formato:** un subapartado `### <id> <name>` por feature destino (o "Sin feature asignada",
  al final), **ordenados por id**, con una viñeta por nota que indique el **origen** (archivo y
  punto, p. ej. r1 de `progress/review_<feature>.md`). Una nota que afecta a varias features se
  escribe una sola vez, en la de menor id, indicando a qué otras afecta; cada una de las demás
  lleva una viñeta "ver la nota de la feature <id>".
- **Quién escribe:** el leader, al recibir cada informe del implementer o del reviewer, y
  cuando una conversación con el humano deje algo para más adelante. No se dejan notas para
  features futuras solo en los informes de `progress/`.
- **Quién lee:** al empezar una feature, el leader pasa sus notas al `spec_author` (o al
  `implementer` si es `"sdd": false`), que las cubre o las descarta con justificación en el
  spec o en su informe.
- **Cuándo se borran:** cuando la feature destino queda `done` con la nota recogida, o cuando el
  humano la descarta. Se deja constancia en la entrada de `progress/history.md`.

## 6. Si te bloqueas

- Relee la sección relevante de `docs/`.
- Si la herramienta no hace lo que esperas, **no inventes un workaround**:
  documenta el bloqueo en `progress/current.md` y para la sesión.
