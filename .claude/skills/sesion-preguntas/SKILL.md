---
name: sesion-preguntas
description: Sesión de preguntas del humano sobre el código de una feature (normalmente tras su revisión). Responder sin implementar nada, anotar los cambios que surjan en progress/questions_<feature>.md y, solo cuando el humano diga que terminó, reunir sus decisiones y aplicar los cambios con el flujo leader → implementer → reviewer. Usar cuando el humano anuncie que va a hacer preguntas o dudas sobre el código, o que va a revisar una feature.
---

# Sesión de preguntas del humano

Sigues siendo el `leader` (ver `CLAUDE.md`). Esta skill añade una regla: **mientras el humano
pregunta, no se implementa nada**. Hablas en español.

## Fase 1 — Mientras el humano pregunta

### Qué haces

- **Responde tú directamente**, leyendo el código. No lances subagentes: son preguntas de
  lectura.
- **Verifica antes de afirmar.** Si la respuesta depende del comportamiento, ejecútalo:
  `PYTHONPATH=src python3 - <<'PY' ... PY`, con archivos temporales en el scratchpad. Una
  tabla de "entrada → resultado" convence más que una explicación.
- **Mira más allá de la pregunta.** Si al responder encuentras un fallo real (una fuga, una
  excepción sin capturar, una regla incumplida), dilo y anótalo como prioridad **alta**. Si
  preguntan por un caso, busca si el mismo error se repite en otros sitios.
- **Corrige la premisa si es falsa**, con evidencia (archivo:línea), sin rodeos.
- **Da una recomendación**, no un catálogo de opciones. Si hay alternativas reales, una tabla
  corta y la recomendada primero.

### Dónde anotas los cambios

En `progress/questions_<feature>.md`. Créalo con la primera pregunta que genere un cambio, con
el título `# Sesión de preguntas del humano sobre <feature> (<fecha>)`. Un punto numerado por
pregunta:

```markdown
## <n>. <título corto> (prioridad alta | media | baja)

Pregunta: <resumen de la pregunta>. Respuesta: <una o dos líneas>.

- **<archivo>:<líneas>** (implementer | leader): <cambio concreto>.
- **Tests:** <qué casos, con qué fuentes o variantes>.
- **Decisión del humano:** <solo si la hay: opciones y cuál recomiendas>.
```

- Una pregunta de seguimiento **amplía su punto** en lugar de crear uno nuevo.
- Si una pregunta no implica cambios, dilo en la respuesta y no anotes nada.
- Al final de cada respuesta: qué has anotado (o que no hay cambios) y "Siguiente pregunta
  cuando quieras."

### Qué NO haces

- ❌ Editar `src/`, `tests/`, `docs/` o la configuración. Solo escribes en
  `progress/questions_<feature>.md`.
- ❌ Lanzar al implementer o al reviewer.
- ❌ Preguntar las decisiones con `AskUserQuestion` en mitad de la sesión. Se anotan en su punto
  y se preguntan todas juntas al final, salvo que el humano pida decidir en el momento.
- ❌ Cambiar estados en `feature_list.json`.

## Fase 2 — Cuando el humano dice que terminó

Solo empieza cuando el humano lo dice explícitamente ("terminé", "ya quedó", "a implementar").

1. **Decisiones.** Reúne todas las decisiones abiertas de `progress/questions_<feature>.md`,
   más las que sigan pendientes en los informes de la feature, y pregúntalas en un único
   `AskUserQuestion` (máximo 4 preguntas por llamada, la opción recomendada primero). Anota
   las respuestas en una sección "Decisiones del humano (<fecha>)" al principio del archivo.
   Si el humano quiere pensarlas con calma y parar aquí, aplica la skill `pausar-sesion`.
2. **Estado de la feature.**
   - Si está `in_progress`, sigue con la siguiente ronda.
   - Si está `done`, pide al humano que autorice reabrirla (`done` → `in_progress`, como la
     "Reapertura" de la feature 2 en `progress/history.md`). Sin esa autorización, no se toca
     `src/` ni `tests/`.
3. **Reparto.** Tú decides cómo agrupar y lo explicas en una línea:
   - **Todo en una ronda** cuando los cambios tocan los mismos archivos o se solapan (lo
     normal: rehacerlos por separado reescribe los mismos tests varias veces).
   - **Por lotes** cuando hay grupos independientes y alguno es arriesgado o necesita una
     decisión que aún no está.
   - **Uno por uno** solo si cada cambio condiciona al siguiente.
   - Lo que queda fuera de `src/` y `tests/` (docs, `.gitignore`, `pyproject.toml`,
     `progress/`) lo haces tú mientras trabaja el implementer.
4. **Implementer.** Encárgale la ronda `N` con la ruta del archivo de preguntas como entrada.
   Debe escribir una sección "## Ronda N" en `progress/impl_<feature>.md` y responderte con una
   sola línea. Recuérdale que compruebe en el archivo cada cambio antes de darlo por hecho.
5. **Comprueba a mano** lo más importante del informe (el fallo de prioridad alta, el caso que
   motivó la pregunta) antes de lanzar al reviewer.
6. **Reviewer.** Ronda `N` en `progress/review_<feature>.md`. Pídele una búsqueda sistemática
   de la clase de fallo que se haya encontrado (p. ej. todas las excepciones sin tipar), no
   solo el caso concreto, y las recomendaciones para otras features en "## Para features
   futuras".
7. **Bucle.** Con CHANGES_REQUESTED, verifica los bloqueantes y devuelve la siguiente ronda al
   implementer. Cualquier hueco que las decisiones no cubrían, o una observación menor que no
   bloquea, se le pregunta al humano antes de actuar; no lo decides tú.
8. **Notas para features futuras.** Lo que corresponda a otra feature va a
   `progress/current.md` según `AGENTS.md` §5 bis: ordenado por id y con su origen.
9. **Cierre**, con APPROVED y la autorización del humano:
   - el implementer marca `done` y añade la entrada a `progress/history.md`, con referencia a
     `progress/questions_<feature>.md`;
   - tú vacías `progress/current.md` dejando la plantilla y las notas para features futuras;
   - commits y PR solo si el humano los autoriza, y con la agrupación que elija.

Mantén la bitácora de `progress/current.md` al día en cada paso de la fase 2.
