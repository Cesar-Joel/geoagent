# CHECKPOINTS — Evaluación del estado final

> En sistemas multi-agente no se evalúa el camino, se evalúa el destino.
> Estos son los checkpoints objetivos que un juez (humano o IA) puede usar
> para decidir si el proyecto está sano.

## C1 — El arnés está completo

- [ ] Existen los 4 archivos base: `AGENTS.md`, `init.sh`, `feature_list.json`,
      `progress/current.md`.
- [ ] Existen los 4 docs: `docs/architecture.md`, `docs/conventions.md`,
      `docs/verification.md`, `docs/specs.md`.
- [ ] `./init.sh` termina con exit code 0.

## C2 — El estado es coherente

- [ ] Como mucho una feature en `in_progress` en `feature_list.json`.
- [ ] Toda feature `done` tiene tests asociados que pasan.
- [ ] `progress/current.md` está vacío o describe la sesión activa
      (no contiene basura de sesiones anteriores).

## C3 — El código respeta la arquitectura

- [ ] `src/geoagent/` solo contiene los paquetes previstos en
      `docs/architecture.md`: `common/`, `agent/`, `backend/`, `spark/`,
      `tools/`.
- [ ] Toda dependencia externa declarada en `pyproject.toml` está justificada
      por una feature de `feature_list.json` y su spec correspondiente.
- [ ] No hay `print()` sueltos para debug, ni TODOs sin contexto.
- [ ] No hay secretos (tokens, credenciales de broker) en el repositorio ni
      en logs de sesión.

## C4 — La verificación es real

- [ ] `tests/unit/` cubre los paquetes `common`, `agent` y `backend` con una
      cobertura ≥ 85%.
- [ ] Los tests unitarios no usan red real, ni broker real, ni credenciales
      de Earth Engine.
- [ ] Los tests usan `tempfile.TemporaryDirectory()` o el store real, no
      mocks de filesystem.
- [ ] `make test-unit` corre en verde y termina en menos de 60 segundos.
- [ ] Si la feature tocada afecta al sistema completo, `make test-integration`
      corre en verde contra el entorno efímero.

## C5 — La sesión se cerró bien

- [ ] No hay archivos sin trackear sospechosos (`*.tmp`, `__pycache__`
      fuera del `.gitignore`).
- [ ] `progress/history.md` tiene una entrada por la última sesión.
- [ ] La última feature trabajada está reflejada en su estado correcto.

## C6 — Spec Driven Development

- [ ] Toda feature con `"sdd": true` en estado `spec_ready`, `in_progress`
      o `done` tiene su carpeta `specs/<name>/` con los 3 archivos:
      `requirements.md`, `design.md`, `tasks.md`.
- [ ] `requirements.md` usa EARS estricto (ver `docs/specs.md`).
- [ ] Toda feature `done` con `"sdd": true` tiene todas sus tasks marcadas
      `[x]` en `tasks.md`.
- [ ] Cada `R<n>` de `requirements.md` está cubierto por al menos un test
      concreto en `tests/`, y el mapa `R<n> → test` está documentado en
      `progress/impl_<name>.md`.

---

**Cómo usar este archivo:** un agente revisor (`.claude/agents/reviewer.md`)
recorre cada checkbox, marca `[x]` o `[ ]`, y rechaza el cierre de sesión
si quedan boxes vacíos en C1-C6.
