# Verificación — Cómo demostrar que el trabajo funciona

> Regla de oro: **el agente no dice "funciona", lo demuestra**.
> Toda feature termina con evidencia ejecutable, no con afirmaciones.

## Niveles de verificación

### Nivel 1 — Tests unitarios (obligatorio)

Toda función pública en `src/` tiene al menos un test en `tests/unit` que:

1. Cubre el camino feliz.
2. Cubre al menos un camino de error si la función puede fallar.

Comando:
```bash
make test-unit
# equivalente: python3 -m pytest tests/unit -q
```

Los tests unitarios no usan red real, ni broker real, ni credenciales de
Earth Engine. Los dobles de prueba están en `tests/conftest.py`.

### Nivel 2 — Test de integración (obligatorio para features de sistema)

Las features que tocan backend, agente, cola, recovery o Spark se verifican
levantando el entorno efímero (backend + broker + N agentes) y ejecutando la
suite contra él:

```bash
make test-integration
# equivalente: python3 -m pytest tests/integration -q
```

Cada test de integración usa puertos y directorios efímeros y es repetible
sin limpieza manual. Los logs del entorno se publican cuando la suite falla.

### Nivel 3 — Smoke end-to-end (obligatorio antes de cerrar features de sistema)

Antes de cerrar una feature que toca el flujo completo, ejecuta la demo
reproducible:

```bash
make demo
# levanta backend, broker y >=3 agentes, somete >=200 particiones,
# inyecta al menos un fallo y verifica invariantes finales.
```
Si make demo no termina en verde, no marques nada como done.

### Nivel 4 — Trazabilidad de requirements (obligatorio para features con `"sdd": true`)

Cada `R<n>` de `specs/<name>/requirements.md` debe poder mapearse a al
menos un test concreto en `tests/`. El reviewer rechaza si falta cobertura.

El implementer documenta el mapa en `progress/impl_<name>.md`:

```markdown
## Trazabilidad
- R1 → `test_local_store_cold_creation`
- R2 → `test_local_store_persistence_between_instances`
- R3 → `test_local_store_rollback_on_error`
- R4 → `test_local_store_migration`
- R5 → `test_local_store_concurrent_access`
```

### Nivel 5 - Cobertura mínima

La cobertura de los paquetes common, agent y backend debe ser al
menos del 85%. CI falla por debajo de ese umbral.

```bash
make test-unit        # incluye el chequeo de cobertura
```

## Anti-patrones (no hacer)

- ❌ "He añadido el endpoint, debería funcionar." → falta test ejecutable.
- ❌ Test que solo verifica que la función no lanza excepción. → tiene que
  comprobar el resultado concreto.
- ❌ `mock` del filesystem o del store. → usa `tempfile.TemporaryDirectory()` y el LocalStore real.
- ❌ Test que depende del orden de ejecución o de estado global compartido.
- ❌ `sleep` reales para verificar timeouts, heartbeats o backoff. → reloj controlado y aleatoriedad simulada.
- ❌ Marcar la feature como `done` sin pasar `./init.sh` y, si aplica, `make test-integration` y `make demo`.

## Verificación final antes de cerrar

```bash
./init.sh           # debe terminar con [OK] Entorno listo
make lint           # linter sin errores
make test           # unitarios en verde
```

Si `./init.sh` está rojo, **no** marques nada como `done`. Anota el bloqueo
en `progress/current.md` con estado `blocked` en `feature_list.json`.
