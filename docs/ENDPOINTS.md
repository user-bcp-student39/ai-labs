# Contrato de la API de requerimientos (api)

Estado del documento: contrato observado en el código actual (rama day1/prompting, después del cambio de H-API-03). No hay contrato acordado con el equipo: esa parte queda como pendiente.

Base URL en el laboratorio: http://localhost:8000. Documentación interactiva generada por FastAPI: http://localhost:8000/docs.

## Clasificación del contrato

| Tipo | Contenido |
|---|---|
| Contrato observado | Rutas, campos, códigos y mensajes descritos en este documento, comprobados contra api/app/main.py y api/app/repository.py. |
| Contrato acordado | Pendiente. No existe un acuerdo escrito con auth ni con web sobre estos campos. |
| Riesgos pendientes | Sección final, con referencia a H-API-NN de HALLAZGOS.md. |

## Autenticación común

Todas las rutas requieren el encabezado:

```http
Authorization: Bearer <TOKEN>
```

`<TOKEN>` es la cadena Base64 de cuatro campos separados por barra vertical: `usuario|rol|expiracion|secreto`. `expiracion` es un Unix timestamp en segundos que debe ser mayor que la hora actual. `secreto` es el valor fijo del código (api/app/main.py:16). Este mecanismo no tiene firma ni verificación de emisor y audiencia (H-API-01, Aprobado; pendiente de corrección).

Si el token falta, está mal formado, expiró o el secreto no coincide, la respuesta es 401 (ver errores comunes).

## Errores comunes

| Código | Cuándo ocurre | Cuerpo observado |
|---|---|---|
| 401 | Falta el encabezado, el token está mal formado, expiró o el secreto no coincide. | `{"detail":"Invalid token: invalid token"}` cuando el token está vacío, expirado o con secreto distinto. `{"detail":"Invalid token: Incorrect padding"}` cuando la cadena Base64 es inválida. El texto después de `Invalid token:` proviene de la excepción interna y puede cambiar (H-API-07). |
| 422 | Falta el cuerpo o un campo obligatorio. Lo genera FastAPI, no el código de la aplicación. | `{"detail":[{"type":"missing","loc":["body"],"msg":"Field required","input":null}]}` |

## 1. GET /api/tasks

1. **Qué hace:** devuelve las tareas del usuario de la sesión, o las de otro owner si se indica el parámetro `owner` (ver seguridad).
2. **Autenticación:** sí. Encabezado `Authorization: Bearer <TOKEN>`.
3. **Request**

| Parámetro | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| owner (query) | string | No | Owner cuyas tareas se listan. Si se omite, se usa el usuario del token. |
| Authorization (header) | string | Sí | `Bearer <TOKEN>` |

Ejemplo real:

```http
GET /api/tasks HTTP/1.1
Host: localhost:8000
Authorization: Bearer <TOKEN>
```

Con parámetro owner:

```http
GET /api/tasks?owner=trainer HTTP/1.1
Host: localhost:8000
Authorization: Bearer <TOKEN>
```

4. **Respuesta exitosa: 200 OK**

Cuerpo: arreglo de tareas, ordenado por `id` ascendente.

| Campo | Tipo | Descripción |
|---|---|---|
| id | integer | Identificador autoincremental. |
| title | string | Título de la tarea. |
| description | string | Descripción. Puede ser cadena vacía. |
| status | string | Estado. El código no restringe los valores; los sembrados son TODO e IN_PROGRESS. |
| owner | string | Usuario propietario. |
| priority | string | Prioridad. El código no restringe los valores; los sembrados son HIGH, MEDIUM y LOW. |
| createdAt | string | Fecha y hora generadas por SQLite con `datetime('now')`, formato `YYYY-MM-DD HH:MM:SS`. Pendiente confirmar la zona horaria (pregunta abierta 4). |

Ejemplo real (usuario student, con datos sembrados):

```json
[
  {"id":1,"title":"Refactor login","description":"Separar responsabilidades en frontend","status":"TODO","owner":"student","priority":"HIGH","createdAt":"2026-11-02 22:11:15"},
  {"id":2,"title":"Review API","description":"Revisar seguridad de endpoints","status":"IN_PROGRESS","owner":"student","priority":"MEDIUM","createdAt":"2026-11-02 22:11:15"}
]
```

Ejemplo con `owner=trainer`: devuelve 200 con la tarea `{"id":3,"title":"Trainer notes",...,"owner":"trainer"}`.

5. **Errores posibles**

- 401: ver errores comunes. Ejemplo: `{"detail":"Invalid token: invalid token"}`.

6. **Notas de seguridad**

- El parámetro `owner` permite leer tareas de otro usuario con un token válido de student: `GET /api/tasks?owner=trainer` devuelve 200 con la tarea de trainer (api/app/main.py:71; H-API-02, Aprobado, sin corregir).
- La consulta usa parámetros SQL. La concatenación de H-API-03 quedó corregida en api/app/repository.py.

## 2. POST /api/tasks

1. **Qué hace:** crea una tarea. Si no se envían status, priority u owner, usa los valores por defecto.
2. **Autenticación:** sí. Encabezado `Authorization: Bearer <TOKEN>`.
3. **Request**

Cuerpo JSON (`Content-Type: application/json`):

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| title | string | No (por defecto `""`) | Título. El código lo convierte con `str()` (api/app/main.py:80). |
| description | string | No (por defecto `""`) | Descripción. |
| status | string | No (por defecto `TODO`) | Estado. Sin validación de valores. |
| priority | string | No (por defecto `MEDIUM`) | Prioridad. Sin validación de valores. |
| owner | string | No (por defecto identidad del token) | Propietario. Actualmente se acepta del cuerpo sin validar (H-API-02). |

Ejemplo real:

```http
POST /api/tasks HTTP/1.1
Host: localhost:8000
Authorization: Bearer <TOKEN>
Content-Type: application/json

{"title":"Nueva tarea","description":"Detalle","status":"TODO","priority":"HIGH"}
```

4. **Respuesta exitosa: 201 Created**

Cuerpo: la tarea creada, con los mismos campos que en GET /api/tasks.

Ejemplo real para el cuerpo anterior:

```json
{"id":4,"title":"Nueva tarea","description":"Detalle","status":"TODO","owner":"student","priority":"HIGH","createdAt":"2026-11-02 22:11:15"}
```

Ejemplo real con solo `{"title":"Solo titulo"}`:

```json
{"id":5,"title":"Solo titulo","description":"","status":"TODO","owner":"student","priority":"MEDIUM","createdAt":"2026-11-02 22:11:15"}
```

5. **Errores posibles**

- 401: ver errores comunes.
- 422 cuando no hay cuerpo. Ejemplo: `{"detail":[{"type":"missing","loc":["body"],"msg":"Field required","input":null}]}`.
- Otros cuerpos mal formados (por ejemplo, JSON inválido o campos de tipo distinto) no se comprobaron en esta documentación. Pregunta abierta 1.

6. **Notas de seguridad**

- Con `{"owner":"trainer"}` en el cuerpo, la tarea se crea con owner trainer y la respuesta es 201 (verificado). Corresponde a H-API-02, Aprobado y sin corregir.
- Como `str()` se aplica a los campos, un `null` en `title` se guardaría como la cadena `"None"`. Derivado del código en api/app/main.py:80; no comprobado en ejecución (pregunta abierta 1).

## 3. GET /api/summary

1. **Qué hace:** devuelve el total de tareas de un owner, el conteo por estado y el número de tareas de prioridad HIGH que no están DONE ni ARCHIVED.
2. **Autenticación:** sí. Encabezado `Authorization: Bearer <TOKEN>`.
3. **Request**

| Parámetro | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| owner (query) | string | No | Owner a resumir. Si se omite, se usa el usuario del token. |
| Authorization (header) | string | Sí | `Bearer <TOKEN>` |

Ejemplo real:

```http
GET /api/summary HTTP/1.1
Host: localhost:8000
Authorization: Bearer <TOKEN>
```

4. **Respuesta exitosa: 200 OK**

| Campo | Tipo | Descripción |
|---|---|---|
| owner | string | Owner resumido. |
| total | integer | Número de tareas del owner. |
| byStatus | object | Mapa estado → cantidad. |
| highPriorityOpen | integer | Tareas con priority HIGH cuyo status no es DONE ni ARCHIVED. |

Ejemplo real (student, después de crear las tareas 4 y 5):

```json
{"owner":"student","total":4,"byStatus":{"TODO":3,"IN_PROGRESS":1},"highPriorityOpen":2}
```

Ejemplo real con `owner=trainer`:

```json
{"owner":"trainer","total":2,"byStatus":{"TODO":2},"highPriorityOpen":0}
```

5. **Errores posibles**

- 401: ver errores comunes.

6. **Notas de seguridad**

- Mismo riesgo que GET /api/tasks: el parámetro `owner` permite consultar el resumen de otro owner (api/app/main.py:90; H-API-02).

## 4. POST /api/requirements

1. **Qué hace:** guarda un archivo de requerimientos subido en el servidor y devuelve sus datos.
2. **Autenticación:** sí. Encabezado `Authorization: Bearer <TOKEN>`.
3. **Request**

Cuerpo `multipart/form-data`:

| Campo | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| file | archivo | Sí | Contenido a guardar. El nombre se toma del campo `filename` de la parte. |
| Authorization (header) | string | Sí | `Bearer <TOKEN>` |

Ejemplo real con `curl`:

```bash
curl -X POST http://localhost:8000/api/requirements \
  -H "Authorization: Bearer <TOKEN>" \
  -F "file=@requirements.txt;type=text/plain"
```

4. **Respuesta exitosa: 201 Created**

| Campo | Tipo | Descripción |
|---|---|---|
| owner | string | Usuario del token. |
| fileName | string | Nombre recibido en la subida, sin normalizar. |
| storedAt | string | Ruta absoluta en el servidor donde se guardó el archivo. Depende del sistema operativo. |
| size | integer | Tamaño en bytes. |

Ejemplo real (archivo `requirements.txt` con 24 bytes; ruta de la ejecución de prueba):

```json
{"owner":"student","fileName":"requirements.txt","storedAt":"C:\\Users\\Usuario\\AppData\\Local\\Temp\\tmplovia9ce\\uploads\\requirements.txt","size":24}
```

5. **Errores posibles**

- 401: ver errores comunes.
- 422 cuando no se envía el campo `file`. Ejemplo: `{"detail":[{"type":"missing","loc":["body","file"],"msg":"Field required","input":null}]}`.

6. **Notas de seguridad**

- El nombre del archivo se usa tal cual para construir la ruta de destino (api/app/main.py:107). Un nombre con segmentos `..` no fue probado en esta documentación; el riesgo está registrado como H-API-04 (Pendiente).
- No hay límite de tamaño ni lista de extensiones permitidas. Un archivo con el mismo nombre se sobrescribe (api/app/main.py:109).
- `storedAt` expone la ruta absoluta del servidor (H-API-04).

## 5. GET /api/backend-health

1. **Qué hace:** consulta la salud del servicio de autenticación y devuelve su respuesta.
2. **Autenticación:** sí. Encabezado `Authorization: Bearer <TOKEN>`.
3. **Request**

Sin parámetros ni cuerpo. La URL consultada se toma de la variable de entorno `AUTH_HEALTH_URL`; si no existe, usa `http://localhost:8080/q/health` (api/app/main.py:114). Tiempo de espera: 3 segundos.

```http
GET /api/backend-health HTTP/1.1
Host: localhost:8000
Authorization: Bearer <TOKEN>
```

4. **Respuesta exitosa: 200 OK**

| Campo | Tipo | Descripción |
|---|---|---|
| requestedBy | string | Usuario del token. |
| status | integer | Código HTTP devuelto por el servicio consultado. Vale 0 si no hubo respuesta. |
| body | string | Cuerpo devuelto por el servicio, o el texto del error si falló la conexión. |

Ejemplo real con un stub local que responde 200 (no es el servicio auth real; verificar contra auth en ejecución):

```json
{"requestedBy":"student","status":200,"body":"{\"status\":\"UP\"}"}
```

Ejemplo real con el servicio inalcanzable. El texto del error depende del sistema y del idioma; este es de Windows en español, truncado al final por brevedad:

```json
{"requestedBy":"student","status":0,"body":"HTTPConnectionPool(host='127.0.0.1', port=9): Max retries exceeded with url: /q/health (Caused by NewConnectionError('<urllib3.connection.HTTPConnection object at 0x...>: Failed to establish a new connection: [WinError 10061] ...'))"}
```

5. **Errores posibles**

- 401: ver errores comunes.
- No hay respuesta 5xx: un fallo al consultar el servicio se devuelve como 200 con `status` 0 (H-API-10).

6. **Notas de seguridad**

- El cuerpo del error interno se devuelve al cliente (api/app/main.py:119; H-API-07).
- La URL de salud está fijada en código y en variables de entorno (H-API-06).

## Riesgos pendientes

| ID | Riesgo | Estado |
|---|---|---|
| H-API-01 | Token sin firma, con secreto fijo en el código. | Aprobado, sin corregir |
| H-API-02 | El parámetro `owner` y el campo `owner` del cuerpo permiten actuar sobre otro owner. | Aprobado, sin corregir |
| H-API-03 | Consultas parametrizadas. | Resuelto |
| H-API-04 | Nombre de archivo sin normalizar, sin límite de tamaño ni extensión, y `storedAt` con ruta absoluta. | Pendiente |
| H-API-06 | Secreto y URL de salud fijados en código. | Pendiente |
| H-API-07 | Detalle interno en 401 y en backend-health. | Pendiente |
| H-API-10 | backend-health responde 200 ante fallos. | Pendiente |
| H-API-12 | CORS con origen `*` y credenciales habilitadas (api/app/main.py:52-53). | Pendiente |

## Preguntas abiertas

1. ¿Qué se espera cuando el cuerpo de POST /api/tasks tiene tipos distintos o nulos (por ejemplo, `title: null`, que hoy se convertiría en `"None"`)?
2. ¿Qué valores válidos tienen `status` y `priority`? El código no los valida.
3. ¿Un usuario con rol trainer puede consultar tareas de otros owners? El código no tiene regla de rol.
4. ¿`createdAt` debe mostrarse en UTC? SQLite `datetime('now')` devuelve UTC y el código no lo indica.
5. ¿El campo `status` de backend-health debe devolver un código de error (por ejemplo, 503) en lugar de 200 con 0? Cambiaría el contrato observado.
6. ¿La respuesta de backend-health con el servicio auth real coincide con la del stub? No se verificó contra auth en ejecución.

## Documentos consultados

- api/app/main.py y api/app/repository.py (contrato, líneas citadas).
- HALLAZGOS.md (estado y IDs de riesgos).
- PLAN.md (decisiones abiertas, comportamiento observado de H-API-01 a H-API-03).
- README.md (URL base y `/docs`), RETO.md y docs/GOOD_PRACTICES.md (referencia de convenciones).
- No existe docs/ENDPOINTS.md antes de esta versión, así que no hubo contrato previo que preservar.
