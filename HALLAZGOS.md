# Hallazgos de ReqFlow

Matriz de seguimiento compartida. Este archivo contiene las filas del componente api (IDs H-API-NN). Las filas de auth (H-AUTH-NN) y web (H-WEB-NN) se añadirán sin sobrescribir estas.

Alcance de esta versión: Discovery, sin cambios de código. Fuentes: RETO.md, docs/GOOD_PRACTICES.md, api/app/main.py, api/requirements.txt, api/tests/test_api.py. Rama local: day1/prompting.

## Contrato observado (api)

docs/ENDPOINTS.md no existe; el contrato siguiente se deriva del código y no es un contrato acordado.

| Ruta | Entrada | Respuesta observada | Evidencia |
|---|---|---|---|
| GET /api/tasks | Bearer; query owner opcional | 200 lista de tareas; 401 token inválido | api/app/main.py:67-75 |
| POST /api/tasks | Bearer; JSON title, description, status (TODO), priority (MEDIUM), owner (identidad por defecto) | 201 tarea creada | api/app/main.py:77-88 |
| GET /api/summary | Bearer; query owner opcional | 200 owner, total, byStatus, highPriorityOpen | api/app/main.py:90-105 |
| POST /api/requirements | Bearer; multipart file | 201 owner, fileName, storedAt, size | api/app/main.py:107-112 |
| GET /api/backend-health | Bearer | 200 requestedBy, status, body (status 0 si falla la llamada) | api/app/main.py:114-121 |

Flujo del token: el encabezado Authorization se decodifica de Base64 y se separa en usuario, rol, expiración y secreto. Se validan cuatro campos, el secreto fijo y la expiración futura (api/app/main.py:17-26). No hay firma, emisor ni audiencia. El rol no se usa para autorizar.

Acceso SQLite: una conexión compartida creada en api/app/main.py:35, siembra de tres tareas si la tabla está vacía (api/app/main.py:37-43). Las consultas se construyen por concatenación (api/app/main.py:70, 84, 87, 93).

Carga de archivos: api/app/main.py:109-112 guarda el contenido con el nombre recibido, sobrescribe archivos existentes, no limita tamaño ni extensión y devuelve la ruta del servidor.

Cobertura actual: api/tests/test_api.py tiene cuatro casos (listado, creación y resumen, subida, token inválido). No cubre owner ajeno, comillas en SQL, nombres de archivo ni CORS.

## Matriz de seguimiento

| id | componente | hallazgo | tipo | explicacion | evidencia (archivo:linea) | severidad | estado |
|---|---|---|---|---|---|---|---|
| H-API-01 | api | Token Base64 con secreto embebido y sin firma | Vulnerabilidad | El token es Base64 de cuatro campos separados por barra vertical, con el secreto en claro. Quien conozca el secreto, que está en el código, puede forjar identidad y rol. Solo se valida la expiración. | api/app/main.py:14; api/app/main.py:19-24; api/tests/test_api.py:11 | alta | Aprobado |
| H-API-02 | api | Autorización: el cliente elige el owner consultado | Vulnerabilidad | El parámetro owner reemplaza la identidad del token en listado y resumen, y en la creación el owner llega en el cuerpo. Un usuario puede leer o insertar tareas de otro owner. | api/app/main.py:69; api/app/main.py:83; api/app/main.py:92 | alta | Aprobado |
| H-API-03 | api | Filtros e inserts concatenados en SQL | Vulnerabilidad | Valores del cliente se concatenan en las consultas. Una comilla altera la sentencia y puede leer o escribir datos ajenos. Un token forjado (H-API-01) amplía el alcance. | api/app/main.py:70; api/app/main.py:84; api/app/main.py:87; api/app/main.py:93 | alta | Resuelto: consultas parametrizadas en api/app/repository.py, usadas desde api/app/main.py; pruebas en api/tests/test_api.py |
| H-API-04 | api | Nombre de archivo subido usado tal cual; sin límite de tamaño ni extensión | Vulnerabilidad | Path(upload_dir) con file.filename permite nombres con separadores o rutas relativas que salgan de uploads/. Un nombre repetido sobrescribe el archivo anterior. El contenido se lee completo en memoria sin tope y la respuesta expone la ruta del servidor. | api/app/main.py:109; api/app/main.py:110; api/app/main.py:111; api/app/main.py:112 | alta | Pendiente |
| H-API-05 | api | Dependencias fijadas a versiones a verificar: urllib3 2.5.0 y python-multipart 0.0.21 | Vulnerabilidad | urllib3 hace la llamada de backend-health y python-multipart parsea las subidas. Si hay advisories abiertos para estas versiones, la API queda expuesta. No se consultaron advisories en esta fase. | api/requirements.txt:4; api/requirements.txt:5 | media | Pendiente |
| H-API-06 | api | Secreto y configuración fijos en código | Refactor | El secreto aparece en el código y en las pruebas. Rutas por defecto y la URL de salud también están fijadas. Cambiar de entorno exige editar código y el secreto queda versionado. | api/app/main.py:14; api/app/main.py:30-31; api/app/main.py:116; api/tests/test_api.py:11 | media | Pendiente |
| H-API-07 | api | Errores exponen detalle interno | Vulnerabilidad | El 401 incluye str(error) y backend-health devuelve str(error) en el cuerpo. Puede revelar detalles de parseo o de red al cliente. | api/app/main.py:26; api/app/main.py:121 | media | Pendiente |
| H-API-08 | api | Lógica de rutas, base de datos, reglas y serialización en un solo archivo | Refactor | create_app concentra conexión, siembra, SQL, reglas de resumen y respuestas. No se puede probar ni reemplazar una capa por separado. | api/app/main.py:29-127 | media | Pendiente |
| H-API-09 | api | Tipado débil y duplicación | Refactor | Payloads y respuestas como dict[str, Any]; SELECT de columnas repetido; conteo por estado duplicado; tres if anidados para tareas HIGH abiertas. Un error de clave no se detecta en tiempo de análisis. | api/app/main.py:56; api/app/main.py:70; api/app/main.py:78; api/app/main.py:87; api/app/main.py:97-104 | baja | Pendiente |
| H-API-10 | api | Excepciones amplias que ocultan la causa | Bug | legacy_identity captura Exception y convierte cualquier fallo en 401. backend_health captura Exception y responde HTTP 200 con status 0; un cliente que ignore el campo status toma el fallo como éxito. | api/app/main.py:25; api/app/main.py:120-121 | baja | Pendiente |
| H-API-11 | api | Conexión SQLite compartida entre hilos sin sincronización | Bug | La conexión se crea con check_same_thread=False y la usan rutas síncronas que FastAPI ejecuta en un pool de hilos. Sin lock, escrituras concurrentes pueden fallar o intercalarse. No reproducido. | api/app/main.py:35; api/app/main.py:46 | baja | Pendiente |
| H-API-12 | api | CORS con origen comodín y credenciales habilitadas | Vulnerabilidad | allow_origins=["*"] junto con allow_credentials=True permite a cualquier origen llamar a la API desde el navegador. El riesgo real depende de si se usan cookies; hoy el token viaja en el encabezado. | api/app/main.py:48-54 | baja | Pendiente |
| H-API-13 | api | Sin validación de title, status, priority ni longitudes en POST /api/tasks | Bug | El cuerpo se acepta como dict libre y cada campo se convierte con str(); admite título vacío, estados o prioridades arbitrarios y textos sin tope. | api/app/main.py:79-84; api/app/main.py:99-102 | media | Implementado en rama local day1/prompting (api/app/task_validation.py); pendiente de revisión humana, PR local en PR_H-API-13.md |
| H-API-14 | api | Imagen Docker ejecuta como root y escucha en 0.0.0.0 | Vulnerabilidad | El Dockerfile no define USER; uvicorn corre como root y escribe en /data y /uploads. Un fallo de subida (H-API-04) tendría más alcance. | api/Dockerfile:1-9; compose.yaml:13-15 | media | CANDIDATO |
| H-API-15 | api | create_app() se ejecuta al importar el módulo (efectos en disco) | Refactor | `app = create_app()` abre SQLite, crea directorios y siembra datos en la importación, con rutas relativas al directorio actual. Importar app.main desde otro cwd crea data/ y uploads/ allí. | api/app/main.py:32-35; api/app/main.py:128 | baja | CANDIDATO |
| H-API-16 | api | Ciclo de vida: on_event deprecado y PoolManager nuevo por petición | Refactor | on_event("shutdown") está deprecado en FastAPI (aviso en pytest) y backend_health crea un urllib3.PoolManager por llamada sin reutilizar ni cerrar. | api/app/main.py:116; api/app/main.py:121 | baja | CANDIDATO |

Todos los hallazgos de RETO.md para api aparecen en el código; ninguno queda como "No encontrado". H-API-05 está presente en requirements, pero su condición de CVE queda por verificar.

## Candidatos de discovery adicionales (api)

Estado de todos: CANDIDATO, pendientes de revisión humana. No se modificó código ni se crearon issues. Línea base: `python tools/lab.py test api` → 44 passed, 5 xfailed, cobertura 100 %. Nota: las líneas citadas en las filas H-API-01 a H-API-12 corresponden a una versión anterior de api/app/main.py (por ejemplo, la secuencia de SQL ya está en api/app/repository.py); no se modificaron.

### H-API-13 — Sin validación de title, status, priority ni longitudes en POST /api/tasks
- Estado: Implementado en rama local day1/prompting; pendiente de revisión humana (el texto de evidencia describe el estado antes del cambio). Decisiones aplicadas: status/priority estrictos en mayúsculas, title obligatorio y no vacío, 400 con manejador propio, validación manual en api/app/task_validation.py.
- Evidencia (estado previo al cambio): api/app/main.py:79-84 (`str(payload.get(...))` sin validar); api/app/main.py:99-102 (el resumen compara exactamente "HIGH", "DONE", "ARCHIVED"); docs/ENDPOINTS.md:107-108 ("Sin validación de valores") y :304 (pregunta abierta); api/tests/test_endpoints.py:142 (payload vacío se acepta con valores por defecto).
- Impacto: una tarea con priority "high" o status "Done" no se cuenta correctamente en highPriorityOpen; títulos vacíos o muy largos se almacenan; datos inconsistentes llegan al frontend.
- Prioridad propuesta: media.
- Contrato potencialmente afectado: POST /api/tasks (nuevo 422 o 400 para valores inválidos) y GET /api/summary. Requiere decidir los valores válidos (pregunta abierta en docs/ENDPOINTS.md:304) y confirmar con web.
- Cómo validarlo: POST /api/tasks con `{"title":"","priority":"high","status":"x"}` y comprobar que devuelve 201; luego GET /api/summary y observar que highPriorityOpen no cuenta la tarea. Añadir pruebas de caracterización antes de cambiar.

### H-API-14 — Imagen Docker ejecuta como root
- Estado: CANDIDATO
- Evidencia: api/Dockerfile:1-9 (sin instrucción USER; `mkdir -p /data /uploads`; CMD uvicorn en 0.0.0.0:8000); compose.yaml:13-15 (volúmenes api-data y api-uploads escribibles); el puerto se publica solo en 127.0.0.1:8000 (compose.yaml:17).
- Impacto: un compromiso del proceso (p. ej. mediante la subida de archivos de H-API-04) obtiene privilegios de root dentro del contenedor y acceso de escritura a datos y subidas. La exposición del puerto está acotada a localhost.
- Prioridad propuesta: media.
- Contrato potencialmente afectado: ninguno de API; afecta a Dockerfile, permisos de los volúmenes /data y /uploads y compose.yaml.
- Cómo validarlo: `docker compose build api` y `docker compose run --rm api id` (esperado hoy: uid=0). Tras el cambio, comprobar que el usuario no root puede escribir en /data y /uploads y que las pruebas de subida y persistencia siguen en verde.

### H-API-15 — create_app() se ejecuta al importar el módulo
- Estado: CANDIDATO
- Evidencia: api/app/main.py:128 (`app = create_app()`); api/app/main.py:32-35 (rutas por defecto "./data/workshop.db" y "./uploads", creación de directorios); api/app/main.py:36-45 (conexión y siembra durante create_app).
- Impacto: importar app.main (pruebas, herramientas, análisis estático) crea base de datos y carpetas según el directorio actual; dificulta aislar pruebas y cambiar configuración (relacionado con H-API-06 y H-API-08).
- Prioridad propuesta: baja.
- Contrato potencialmente afectado: el punto de entrada `app.main:app` usado por api/Dockerfile:9 debe mantenerse.
- Cómo validarlo: desde un directorio temporal, `python -c "import sys; sys.path.insert(0,'<ruta>/api'); import app.main"` y comprobar que se crean ./data y ./uploads. Tras el cambio, confirmar que importar no crea archivos y que `uvicorn app.main:app` sigue arrancando.

### H-API-16 — on_event deprecado y PoolManager por petición
- Estado: CANDIDATO
- Evidencia: api/app/main.py:116 (`urllib3.PoolManager()` en cada llamada a backend-health); api/app/main.py:121 (`@app.on_event("shutdown")`); salida de `python tools/lab.py test api`: DeprecationWarning "on_event is deprecated, use lifespan event handlers" (101 avisos).
- Impacto: se pierde la reutilización de conexiones y se acumulan pools sin cerrar bajo carga; el hook de cierre dejará de funcionar si se elimina la API deprecada en una actualización de FastAPI.
- Prioridad propuesta: baja.
- Contrato potencialmente afectado: GET /api/backend-health no debe cambiar su respuesta (requestedBy, status, body); el cierre de la conexión SQLite debe conservarse.
- Cómo validarlo: `python tools/lab.py test api` (comprobar que desaparece el aviso) y las pruebas de backend-health en api/tests/test_endpoints.py:243-252 siguen pasando; revisar que la conexión se cierra al apagar.

## Pendientes y dependencias

- docs/ENDPOINTS.md no existe y no se creó en este paso; queda pendiente para la fase de documentación.
- docs/TESTING.md no existe; pendiente.
- Sin ejecución de pruebas en esta fase. Pendiente: `python tools/lab.py test api` tras preparar el componente. No hay evidencia de cobertura.
- Sin verificación de advisories para H-API-05; pendiente en la fase SCA.
- Dependencia con auth: RETO.md describe el mismo patrón de token Base64 con secreto embebido en auth. No se leyó auth/ por alcance. Cualquier cambio de formato de token (H-API-01) requiere coordinación con el responsable de auth y revisión de ambos consumidores.
- Pregunta abierta: ¿un trainer puede ver tareas de otro owner, o la autorización debe ser estrictamente por identidad?
- Pendiente humano: revisión y aprobación del plan antes de implementar. No registrado como aprobado.
