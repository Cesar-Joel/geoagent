---
name: pausar-sesion
description: Pausar una sesión con una feature a medias y dejarla lista para retomarla en otra sesión sin recargar el contexto. Guarda el estado comprobado, el siguiente paso, las decisiones pendientes (redactadas para volver a preguntarlas con AskUserQuestion) y lo que queda sin commit. Usar cuando el humano diga que tiene que irse, que lo dejan para mañana o que guarde el progreso antes de terminar una feature. También al retomar ("seguimos", "retomemos <feature>") si `progress/current.md` tiene una pausa registrada (⏸ en "## Próximo paso").
---

# Pausar y retomar una sesión

Sigues siendo el `leader` (ver `CLAUDE.md`). Hablas en español.

El objetivo es que la siguiente sesión arranque leyendo **solo** la sección "## Próximo paso" de
`progress/current.md` y que, desde ahí, abra únicamente las secciones que necesite. No hace falta
volver a leer informes enteros ni la bitácora completa.

Esto **no** es el cierre de sesión de `AGENTS.md` §5: la feature mantiene su estado,
`progress/current.md` no se vacía y nada se mueve a `progress/history.md`.

## Fase 1 — Pausar

### Qué NO haces

- ❌ Lanzar subagentes nuevos, tocar `src/` o `tests/` ni cambiar estados en `feature_list.json`.
- ❌ Convertir respuestas provisionales en decisiones, ni decidir por el humano lo que quedó
  abierto.
- ❌ Hacer commits sin autorización. Los propones, agrupados.

### Pasos

1. **Subagentes en marcha.** Un subagente en segundo plano no sobrevive al cierre de la sesión.
   Si hay alguno trabajando, díselo al humano y recomiéndale esperar su notificación, para que la
   ronda quede completa con su informe. Si no puede esperar, anota que la ronda `N` quedó a medias:
   al retomar habrá que revisar `git diff` y relanzarla.

2. **Foto del estado.** Compruébala ejecutando los comandos; no la reconstruyas de memoria:
   - `./init.sh`: verde, o rojo y por qué. Si está en rojo por trabajo a medias, se anota y no se
     arregla.
   - `git status --short` y `git log --oneline main..HEAD`: cambios sin commit y commits sin subir.
   - Estado de la feature en `feature_list.json`, y última ronda del implementer y del reviewer,
     con su veredicto (`grep -n "^## Ronda" progress/impl_<feature>.md progress/review_<feature>.md`).

3. **Decisiones pendientes.** Todo lo que había que preguntarle al humano y no se cerró va a
   `progress/questions_<feature>.md`, en una sección nueva al final. Si el archivo no existe, se
   crea con el título de la skill `sesion-preguntas`. Esto incluye un `AskUserQuestion` que el
   humano rechazó para aclarar dudas: las respuestas que llegó a marcar cuentan como
   **provisionales**. Plantilla:

   ```markdown
   ## Decisiones pendientes tras <origen, p. ej. la ronda 8 del reviewer> (<fecha>)

   > **Estado: SIN CERRAR.** Al retomar, el leader responde las dudas del humano y le hace
   > estas mismas preguntas con `AskUserQuestion`. Las respuestas "provisionales" pueden cambiar.
   >
   > Origen: <archivo y sección, p. ej. "## Ronda 8" de `progress/review_<feature>.md`>.

   ### Bloqueantes (no necesitan decisión: van en la ronda <N> sí o sí)

   - **B<n>:** <qué falla, con la entrada → resultado comprobado>. Arreglo: <...>. Tests: <...>.

   ### P<n>. <título corto> — respuesta provisional: <respuesta | sin respuesta>

   Contexto: <lo mínimo para decidir, con evidencia comprobada (archivo:línea, entrada → resultado)>.

   | Opción | Qué implica |
   |---|---|
   | **<recomendada> (recomendado)** | <...> |
   | <alternativa> | <...> |

   <Dudas que planteó el humano y cómo se aclararon. Si cambiaste de recomendación, la anterior
   y por qué.>

   ### Sin decisión

   - <lo que se valoró y no hace falta preguntar, con su motivo>.
   ```

   - Una `P<n>` por pregunta, redactada de forma que se pueda pasar tal cual a `AskUserQuestion`
     (como máximo 4 opciones, y en las de selección múltiple, dilo).
   - Los bloqueantes del reviewer van aparte para que nadie los pregunte como si fueran opcionales.
   - Si lo que estaba abierto era la fase 1 de `sesion-preguntas` (el humano aún preguntaba), no
     hay decisiones que redactar. Anota en "## Próximo paso" que la sesión de preguntas sigue
     abierta y cuál fue el último punto.

4. **Scratchpad.** Se pierde al terminar la sesión. Revisa qué contiene. Lo que haga falta para
   retomar (un borrador de descripción de PR o de mensaje de commit, un script de comprobación
   reutilizable) se copia a `progress/` (p. ej. `progress/pr_<feature>.md`) o se resume en la
   pausa. Lo demás se descarta. Si un informe cita archivos del scratchpad, anota que ya no
   existirán.

5. **Notas para features futuras.** Lo que haya surgido para otras features y aún no esté en
   `progress/current.md` se mueve ahora, según `AGENTS.md` §5 bis. Si depende de un informe que
   todavía puede cambiar (una ronda sin aprobar), se lista en la pausa como "pendiente de mover",
   con su origen.

6. **Escribe la pausa en `progress/current.md`:**
   - Actualiza la cabecera (feature, rama, commits sin subir) y "## Plan" si se ha quedado
     desfasado.
   - Añade a la bitácora una entrada `- <fecha>: ⏸ pausa. <estado en una línea>`.
   - Reescribe "## Próximo paso" con esta plantilla. Debe ser corta (unas 25 líneas como máximo):
     los detalles se enlazan, no se copian.

   ```markdown
   ## Próximo paso

   > ⏸ **Sesión pausada el <fecha>.** Al retomar, aplica la fase 2 de la skill `pausar-sesion`.

   - **Estado:** feature <id> `<name>` (`<status>`). Última ronda: implementer <N>, reviewer <N>
     (<veredicto>). `./init.sh`: <verde (<n> passed) | rojo: <causa>>.
   - **En curso al pausar:** <nada | <agente>, ronda <N>, a medias: revisar `git diff` y relanzarla>.
   - **Leer al retomar (solo esto):** `<archivo>` → "<sección exacta>"; ...
   - **No hace falta leer:** <lo que ya está resumido aquí, p. ej. las rondas anteriores>.

   1. <primer paso concreto, p. ej. "resolver las dudas del humano y preguntarle P1-P4 con
      `AskUserQuestion`">.
   2. <...>

   - **Sin commit:** <grupos de commit propuestos, o "nada">.
   - **Perdido con el scratchpad:** <nada | qué era y cómo rehacerlo>.
   ```

7. **Confirma al humano** en pocas líneas: dónde quedó, qué preguntas le esperan (solo los
   títulos) y cómo retomar ("seguimos con `<feature>`"). Si quiere guardar los cambios, propón los
   commits agrupados y hazlos solo si lo autoriza.

## Fase 2 — Retomar

Cuando el humano retome y "## Próximo paso" tenga la marca ⏸:

1. **Lee poco.** Sigue el protocolo de arranque de `CLAUDE.md`, pero de `progress/current.md`
   basta con la cabecera, "## Próximo paso" y la última entrada de la bitácora. Abre solo las
   secciones de "Leer al retomar", buscándolas por su encabezado (`grep -n` + `sed -n`), no los
   archivos enteros.
2. **Comprueba que la foto sigue valiendo:** `./init.sh` y `git status --short`. Si algo no
   coincide con lo anotado (cambios nuevos, commits nuevos, tests en otro estado), díselo al
   humano antes de seguir.
3. **Ronda a medias.** Si quedó un subagente sin terminar, mira si su informe tiene la sección de
   esa ronda. Si no la tiene, revisa `git diff` y relanza la ronda.
4. **Decisiones pendientes.** Primero pregúntale al humano si tiene dudas sobre las `P<n>` o si
   se las preguntas ya. Después hazle las preguntas con `AskUserQuestion`, tal como están
   redactadas: la recomendada primero y, en la descripción, su respuesta provisional.
   - **Anota cada respuesta en cuanto llegue**, aunque rechace la llamada para aclarar algo. Las
     opciones que marcó en una llamada rechazada son respuestas válidas.
   - Después de aclarar, vuelve a preguntar **solo** lo que quedó sin respuesta.
5. **Cierra la pausa.** Pasa las respuestas a "Decisiones del humano (<fecha>)" en el archivo de
   preguntas y marca la sección de pendientes como `**Estado: CERRADA** (ver "Decisiones del
   humano (<fecha>)")`. Quita la marca ⏸ de "## Próximo paso", añade a la bitácora
   `- <fecha>: ▶ se retoma. ...` y sigue el flujo normal (la fase 2 de `sesion-preguntas` o las
   reglas del `leader`).
