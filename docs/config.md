# Configuración

La configuración de agente y backend se carga con `load_agent_config()` y
`load_backend_config()` de `src/geoagent/common/config.py`.

## Precedencia

Variables de entorno > archivo TOML > valores por defecto. Los valores por defecto
pasan por el mismo validador que el resto: uno inválido falla al cargar, nombrando la clave y añadiendo `(default)` al motivo.

- Archivo: ruta pasada como argumento `path` (`str` o `os.PathLike`, p. ej. `Path`; cualquier
  otro tipo, como `bytes`, falla con `field="config_file"`) o, si no, la variable
  `GEOAGENT_CONFIG_FILE`. Formato TOML plano (claves en minúsculas, sin secciones).
  YAML no está soportado (evita una dependencia nueva).
- Entorno: `GEOAGENT_<CLAVE_EN_MAYÚSCULAS>`. Una variable presente pero vacía
  cuenta como valor y se valida (p. ej. una URL vacía falla). Lo mismo vale para
  `GEOAGENT_CONFIG_FILE`: **sin definir** → se cargan solo entorno + valores por defecto, sin
  error; **definida y vacía** (o solo espacios) → `ValidationError` con `field="config_file"`.
  Una ruta vacía pasada como argumento falla igual.
- Python < 3.11 usa el paquete `tomli` (dependencia condicional); 3.11+ usa `tomllib`.

## Claves

| Clave (archivo) | Variable de entorno | Capa | Por defecto | Validación |
|---|---|---|---|---|
| `backend_url` | `GEOAGENT_BACKEND_URL` | agente | `http://127.0.0.1:8080` | URL http(s) no vacía, sin credenciales, query ni fragmento, sin `;` en el host ni en el path (ver [URLs](#urls)) |
| `auth_token` (secreto) | `GEOAGENT_AUTH_TOKEN` | agente | vacío | texto imprimible (`str.isprintable()`: sin caracteres de control, BOM, NBSP, RLO, separadores de línea ni surrogates) |
| `max_workers` | `GEOAGENT_MAX_WORKERS` | agente | `2` | entero > 0 |
| `heartbeat_interval` | `GEOAGENT_HEARTBEAT_INTERVAL` | agente | `30.0` | número > 0 |
| `store_path` | `GEOAGENT_STORE_PATH` | agente | `agent_store.db` | no vacío e imprimible (`str.isprintable()`: sin caracteres de control, BOM, NBSP, RLO, separadores de línea ni surrogates) |
| `host` | `GEOAGENT_HOST` | backend | `127.0.0.1` | texto imprimible y sin espacios; IP sin corchetes ni zona IPv6 (`%`), o nombre DNS válido (etiquetas de 1-63 `[A-Za-z0-9-]`, sin `-` al inicio ni al final, máx. 253 caracteres, última etiqueta ni totalmente numérica ni hexadecimal tipo `0x7f`; octetos IPv4 sin ceros iniciales: `010.0.0.1` es inválido en cualquier versión de Python) |
| `port` | `GEOAGENT_PORT` | backend | `8080` | entero 1-65535 |
| `db_path` | `GEOAGENT_DB_PATH` | backend | `backend_store.db` | no vacío e imprimible (`str.isprintable()`: sin caracteres de control, BOM, NBSP, RLO, separadores de línea ni surrogates) |
| `api_token` (secreto) | `GEOAGENT_API_TOKEN` | backend | vacío | texto imprimible (`str.isprintable()`: sin caracteres de control, BOM, NBSP, RLO, separadores de línea ni surrogates) |
| `queue_url` | `GEOAGENT_QUEUE_URL` | ambos | `amqp://127.0.0.1:5672` | URL con esquema y host, sin credenciales ni fragmento, sin `;` en el host ni en el path (ver [URLs](#urls)); la query se acepta, pero se enmascara |
| `queue_username` | `GEOAGENT_QUEUE_USERNAME` | ambos | vacío | texto imprimible (`str.isprintable()`: sin caracteres de control, BOM, NBSP, RLO, separadores de línea ni surrogates) |
| `queue_password` (secreto) | `GEOAGENT_QUEUE_PASSWORD` | ambos | vacío | texto imprimible (`str.isprintable()`: sin caracteres de control, BOM, NBSP, RLO, separadores de línea ni surrogates) |
| `request_timeout` | `GEOAGENT_REQUEST_TIMEOUT` | ambos | `10.0` | número > 0 |
| `log_level` | `GEOAGENT_LOG_LEVEL` | ambos | `INFO` | DEBUG/INFO/WARNING/ERROR/CRITICAL, solo ASCII (`ınfo` con la i turca sin punto no vale) |

## Tipos y valores del archivo

Un número entre comillas en el TOML (`max_workers = "3"`) se acepta, igual que
en el entorno (donde todo es texto). Los booleanos y los flotantes con parte
fraccionaria no valen para enteros. Los enteros y flotantes en texto solo
admiten dígitos ASCII (sin `_`, `١٢` ni similares), con espacios, signo y, en
flotantes, notación decimal o exponencial. Los hosts de `backend_url` y
`queue_url` no pueden contener caracteres de control. Los errores numéricos repiten el valor
solo si es texto ASCII imprimible (si no, dicen `got str`) y lo truncan a 40 caracteres (`…`).

## Errores y arranque

Una configuración inválida lanza `ValidationError` cuyo mensaje nombra la clave
ofensora (la variable `GEOAGENT_*` o la clave del archivo). Claves desconocidas
en el archivo también se rechazan. En el punto de entrada se usa
`load_or_exit(load_agent_config)`: imprime `invalid configuration: <clave>: <motivo>`
en `stderr` y termina con exit code 2.

Para que un error no pueda falsificar líneas de log, la ruta del archivo (`config_file`) y
las claves TOML desconocidas se repiten solo si son imprimibles (la clave, además, solo
con `[A-Za-z0-9_.-]`); si no, el mensaje es genérico (`<path with non-printable
characters>` / `unknown configuration key (name has unsupported characters)`). Lo que sí se
repite (ruta imprimible, clave desconocida con caracteres válidos y el texto de un error de
TOML) se trunca a 40 caracteres con `…`, igual que los valores numéricos. Las rutas conservan
el final (`…` + últimos 40 caracteres, para ver el nombre del archivo) y el texto de un error de
TOML conserva intacto el sufijo de posición `(at line L, column C)` (o `end of document`), que
solo se acepta si lleva únicamente dígitos.

## Secretos

- Los campos secretos (`auth_token`, `api_token`, `queue_password`) solo se
  aceptan por entorno; si aparecen en el archivo, la carga falla (sin imprimir el valor). Como `queue_username`, exigen
  texto imprimible (`str.isprintable()`): se rechazan control (`\r`, `\n`, NUL...), BOM, NBSP, RLO,
  U+2028 y surrogates, nombrando la clave y sin repetir el valor.
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
- Un `;` literal en cualquier parte del path de `backend_url` y `queue_url`
  (`http://h/api;token=x`, `amqp://h/v;p=x`) se rechaza sin repetir el valor: es el
  mismo riesgo que la query y, a diferencia del resto del path, se detecta sin
  ambigüedad. También se rechaza en el host (`http://h;token=x`), donde `;` nunca es válido.
  Un `;` codificado (`%3B`, p. ej. en un vhost de AMQP) se acepta.
  El resto del path no se vigila: no pongas secretos en él. Los *nombres* de las
  claves de la query de `queue_url` quedan visibles.
- Ambas URL validan el host y el puerto: un host entre corchetes mal formado o un
  puerto no numérico o fuera de 1-65535 se rechaza con la clave y sin repetir el valor.
