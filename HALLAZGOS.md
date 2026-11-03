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

Todos los hallazgos de RETO.md para api aparecen en el código; ninguno queda como "No encontrado". H-API-05 está presente en requirements, pero su condición de CVE queda por verificar.

## Pendientes y dependencias

- docs/ENDPOINTS.md no existe y no se creó en este paso; queda pendiente para la fase de documentación.
- docs/TESTING.md no existe; pendiente.
- Sin ejecución de pruebas en esta fase. Pendiente: `python tools/lab.py test api` tras preparar el componente. No hay evidencia de cobertura.
- Sin verificación de advisories para H-API-05; pendiente en la fase SCA.
- Dependencia con auth: RETO.md describe el mismo patrón de token Base64 con secreto embebido en auth. No se leyó auth/ por alcance. Cualquier cambio de formato de token (H-API-01) requiere coordinación con el responsable de auth y revisión de ambos consumidores.
- Pregunta abierta: ¿un trainer puede ver tareas de otro owner, o la autorización debe ser estrictamente por identidad?
- Pendiente humano: revisión y aprobación del plan antes de implementar. No registrado como aprobado.
