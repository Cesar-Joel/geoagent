# Configuración

La configuración de agente y backend se carga con `load_agent_config()` y
`load_backend_config()` de `src/geoagent/common/config.py`.

## Precedencia

Variables de entorno > archivo TOML > valores por defecto.

- Archivo: ruta pasada como argumento `path` o, si no, la variable
  `GEOAGENT_CONFIG_FILE`. Formato TOML plano (claves en minúsculas, sin secciones).
  YAML no está soportado (evita una dependencia nueva).
- Entorno: `GEOAGENT_<CLAVE_EN_MAYÚSCULAS>`. Una variable presente pero vacía
  cuenta como valor y se valida (p. ej. una URL vacía falla).
- Python < 3.11 usa el paquete `tomli` (dependencia condicional); 3.11+ usa `tomllib`.

## Claves

| Clave (archivo) | Variable de entorno | Capa | Por defecto | Validación |
|---|---|---|---|---|
| `backend_url` | `GEOAGENT_BACKEND_URL` | agente | `http://127.0.0.1:8080` | URL http(s) no vacía, sin credenciales, query ni fragmento |
| `auth_token` (secreto) | `GEOAGENT_AUTH_TOKEN` | agente | vacío | texto |
| `max_workers` | `GEOAGENT_MAX_WORKERS` | agente | `2` | entero > 0 |
| `heartbeat_interval` | `GEOAGENT_HEARTBEAT_INTERVAL` | agente | `30.0` | número > 0 |
| `store_path` | `GEOAGENT_STORE_PATH` | agente | `agent_store.db` | no vacío |
| `host` | `GEOAGENT_HOST` | backend | `127.0.0.1` | no vacío |
| `port` | `GEOAGENT_PORT` | backend | `8080` | entero 1-65535 |
| `db_path` | `GEOAGENT_DB_PATH` | backend | `backend_store.db` | no vacío |
| `api_token` (secreto) | `GEOAGENT_API_TOKEN` | backend | vacío | texto |
| `queue_url` | `GEOAGENT_QUEUE_URL` | ambos | `amqp://127.0.0.1:5672` | URL con esquema y host, sin credenciales ni fragmento (la query se acepta, pero se enmascara) |
| `queue_username` | `GEOAGENT_QUEUE_USERNAME` | ambos | vacío | texto |
| `queue_password` (secreto) | `GEOAGENT_QUEUE_PASSWORD` | ambos | vacío | texto |
| `request_timeout` | `GEOAGENT_REQUEST_TIMEOUT` | ambos | `10.0` | número > 0 |
| `log_level` | `GEOAGENT_LOG_LEVEL` | ambos | `INFO` | DEBUG/INFO/WARNING/ERROR/CRITICAL |

## Tipos y valores del archivo

Un número entre comillas en el TOML (`max_workers = "3"`) se acepta, igual que
en el entorno (donde todo es texto). Los booleanos y los flotantes con parte
fraccionaria no valen para enteros. Los enteros y flotantes en texto solo
admiten dígitos ASCII (sin `_`, `١٢` ni similares), con espacios, signo y, en
flotantes, notación decimal o exponencial. Los hosts de `backend_url` y
`queue_url` no pueden contener caracteres de control. Los valores repetidos en
los errores numéricos se truncan a 40 caracteres (`…`).

## Errores y arranque

Una configuración inválida lanza `ValidationError` cuyo mensaje nombra la clave
ofensora (la variable `GEOAGENT_*` o la clave del archivo). Claves desconocidas
en el archivo también se rechazan. En el punto de entrada se usa
`load_or_exit(load_agent_config)`: imprime `invalid configuration: <clave>: <motivo>`
en `stderr` y termina con exit code 2.

## Secretos

- Los campos secretos (`auth_token`, `api_token`, `queue_password`) solo se
  aceptan por entorno; si aparecen en el archivo, la carga falla (sin imprimir el valor).
- `repr()`/`str()` y `to_safe_dict()` los muestran como `***`. Para logs, usar
  siempre `to_safe_dict()` o `repr()`, nunca volcar los campos a mano.

## URLs

- `backend_url` rechaza credenciales, query (`?...`) y fragmento (`#...`): es una
  URL base y no los necesita. El error nombra la clave pero nunca repite el valor.
- `queue_url` rechaza el fragmento (`#...`; AMQP no lo usa), sin repetir el valor. Acepta query (AMQP la usa para opciones como `heartbeat`), pero
  `repr()`/`str()`/`to_safe_dict()` enmascaran **todos** sus valores conservando
  las claves: `amqp://h/vhost?heartbeat=***`. El atributo conserva el valor real.
  Las credenciales deben ir en `queue_username`/`queue_password`, no en la URL
  (la librería AMQP podría registrar la URL en sus propios logs).
- El path de una URL no se vigila: no pongas secretos en él. Los `;params` del
  path (`http://h/p;tok=x`) forman parte del path y tampoco se vigilan; los
  *nombres* de las claves de la query de `queue_url` quedan visibles.
- Ambas URL validan el host y el puerto: un host entre corchetes mal formado o un
  puerto no numérico o fuera de 1-65535 se rechaza con la clave y sin repetir el valor.
