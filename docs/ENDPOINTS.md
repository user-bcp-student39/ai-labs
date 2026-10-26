# API FastAPI — contrato observado

Este documento describe las rutas que implementa `api/`. La base URL local del
laboratorio es `http://localhost:8000`; el puerto y host pueden cambiar por
despliegue. El código de la API no define un modelo Pydantic para las tareas ni
una lista permitida de valores de estado o prioridad.

## Autenticación común

Las cinco rutas requieren el encabezado exacto en esta forma:

```http
Authorization: Bearer <JWT>
```

La API verifica tokens RS256 con los valores de configuración `jwt_iss`,
`jwt_aud` y `jwks_endpoint`. Exige los claims `exp`, `iss`, `aud`, `sub` y
`role`; `sub` y `role` deben ser cadenas no vacías. La URL JWKS debe usar HTTPS,
salvo HTTP en `localhost`, `127.0.0.1` o `::1`. No hay una ruta de emisión de
tokens en esta API; el emisor y la configuración desplegada deben coordinarse
por separado. Evidencia: `api/app/security.py:12-18,38-64,74-97`.

Errores comunes de autenticación:

| Código | Cuándo ocurre | Ejemplo de cuerpo |
|---|---|---|
| 401 | Falta el encabezado Bearer o el JWT no es válido, no verifica o no contiene claims válidos. | `{"detail":"Invalid token"}` |
| 503 | Falta configuración JWT válida o no está disponible el servicio JWKS. | `{"detail":"Token verification is not configured"}` o `{"detail":"Token verification is unavailable"}` |

Evidencia: `api/app/security.py:38-70`.

---

## `GET /api/tasks`

### 1. Qué hace

Devuelve las tareas del propietario autenticado para que el cliente pueda
mostrar su lista de trabajo. Evidencia: `api/app/main.py:55-62`.

### 2. Autenticación

Requiere `Authorization: Bearer <JWT>` según la sección de autenticación común.

### 3. Request

No tiene cuerpo.

| Campo/parámetro | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `Authorization` (header) | Bearer JWT | Sí | Token firmado que identifica al usuario. |
| `owner` (query) | string | No | Si se omite, se usa el `sub` del token. Si se envía, debe coincidir con ese `sub`; no habilita consultar otro propietario. |

Ejemplo completo:

```bash
curl --get "http://localhost:8000/api/tasks" \
  --data-urlencode "owner=student" \
  -H "Authorization: Bearer $TOKEN"
```

`TOKEN` debe contener un JWT válido emitido para esta API.

### 4. Response exitosa

**200 OK**. El cuerpo es una lista, posiblemente vacía.

| Campo | Tipo | Descripción |
|---|---|---|
| elemento de la lista | object | Una tarea. |
| `id` | integer | Identificador de la tarea en SQLite. |
| `title` | string | Título. |
| `description` | string | Descripción. |
| `status` | string | Estado almacenado; el endpoint no restringe sus valores. |
| `owner` | string | Propietario de la tarea. |
| `priority` | string | Prioridad almacenada; el endpoint no restringe sus valores. |
| `createdAt` | string | Fecha y hora producidas por SQLite (`YYYY-MM-DD HH:MM:SS`). |

Ejemplo con la base recién inicializada y el usuario `student` (la fecha es
generada en ejecución):

```json
[
  {
    "id": 1,
    "title": "Refactor login",
    "description": "Separar responsabilidades en frontend",
    "status": "TODO",
    "owner": "student",
    "priority": "HIGH",
    "createdAt": "2026-10-26 21:58:36"
  },
  {
    "id": 2,
    "title": "Review API",
    "description": "Revisar seguridad de endpoints",
    "status": "IN_PROGRESS",
    "owner": "student",
    "priority": "MEDIUM",
    "createdAt": "2026-10-26 21:58:36"
  }
]
```

Evidencia de campos y semillas: `api/app/main.py:28-30,44-52`; consulta:
`api/app/repositories.py:4-9`.

### 5. Respuestas de error

| Código | Cuándo ocurre | Ejemplo de cuerpo |
|---|---|---|
| 401 | Autenticación ausente o inválida. | `{"detail":"Invalid token"}` |
| 403 | `owner` no coincide con el `sub` autenticado. | `{"detail":"Not authorized for requested owner"}` |
| 503 | Configuración JWT inválida/ausente o JWKS no disponible. | `{"detail":"Token verification is not configured"}` o `{"detail":"Token verification is unavailable"}` |
| 500 | Error inesperado al acceder a SQLite u otro error no capturado. La aplicación no define un cuerpo propio; respuesta predeterminada de FastAPI/Starlette: texto `Internal Server Error`. | `Internal Server Error` |

Evidencia de autorización: `api/app/authorization.py:4-6`; la ruta obtiene el
propietario a partir de la identidad en `api/app/main.py:56-58`.

### 6. Notas de seguridad

El filtro de propietario se restringe a la identidad del JWT verificado. Un
cliente no puede leer tareas de otra identidad cambiando `owner`. Las consultas
usan parámetros enlazados en SQLite. Evidencia:
`api/app/main.py:56-62`; `api/app/authorization.py:4-6`;
`api/app/repositories.py:4-9`.

---

## `POST /api/tasks`

### 1. Qué hace

Registra una tarea para el usuario autenticado y devuelve la tarea creada.
Evidencia: `api/app/main.py:64-72`.

### 2. Autenticación

Requiere `Authorization: Bearer <JWT>` según la sección de autenticación común.

### 3. Request

El cuerpo debe ser un objeto JSON. Sus propiedades son opcionales; el código las
convierte a string y no aplica validaciones de dominio ni enumera estados o
prioridades aceptados.

| Campo/parámetro | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `Authorization` (header) | Bearer JWT | Sí | Token firmado que identifica al usuario. |
| `title` (JSON) | valor JSON convertido a string | No | Título; valor predeterminado `""`. |
| `description` (JSON) | valor JSON convertido a string | No | Descripción; valor predeterminado `""`. |
| `status` (JSON) | valor JSON convertido a string | No | Estado; valor predeterminado `"TODO"`. |
| `priority` (JSON) | valor JSON convertido a string | No | Prioridad; valor predeterminado `"MEDIUM"`. |
| `owner` (JSON) | valor JSON convertido a string | No | Si se omite, se usa el `sub` del token. Si se envía, debe coincidir con el `sub` autenticado. |

Ejemplo completo:

```bash
curl -X POST "http://localhost:8000/api/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Add tests",
    "description": "Improve coverage",
    "status": "TODO",
    "priority": "HIGH",
    "owner": "student"
  }'
```

### 4. Response exitosa

**201 Created**. Devuelve un objeto tarea con los mismos campos que cada
elemento de `GET /api/tasks`.

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | integer | Identificador generado por SQLite. |
| `title` | string | Título almacenado. |
| `description` | string | Descripción almacenada. |
| `status` | string | Estado almacenado. |
| `owner` | string | Propietario autenticado. |
| `priority` | string | Prioridad almacenada. |
| `createdAt` | string | Fecha y hora SQLite (`YYYY-MM-DD HH:MM:SS`). |

Ejemplo para una base recién inicializada (la fecha se genera en ejecución):

```json
{
  "id": 4,
  "title": "Add tests",
  "description": "Improve coverage",
  "status": "TODO",
  "owner": "student",
  "priority": "HIGH",
  "createdAt": "2026-10-26 21:58:36"
}
```

Evidencia: `api/app/main.py:44-52,64-72`;
`api/app/repositories.py:12-32`.

### 5. Respuestas de error

| Código | Cuándo ocurre | Ejemplo de cuerpo |
|---|---|---|
| 401 | Autenticación ausente o inválida. | `{"detail":"Invalid token"}` |
| 403 | `owner` del cuerpo no coincide con el `sub` autenticado. | `{"detail":"Not authorized for requested owner"}` |
| 422 | Falta el cuerpo o no es un objeto JSON. Los detalles de `input` reflejan la entrada recibida. | `{"detail":[{"type":"missing","loc":["body"],"msg":"Field required","input":null}]}` |
| 503 | Configuración JWT inválida/ausente o JWKS no disponible. | `{"detail":"Token verification is not configured"}` o `{"detail":"Token verification is unavailable"}` |
| 500 | Error inesperado de SQLite u otro error no capturado; no hay cuerpo de error propio de la aplicación. | `Internal Server Error` |

Un cuerpo JSON de lista, por ejemplo, produce un 422 con `type` igual a
`dict_type` y mensaje `Input should be a valid dictionary`. Evidencia de
validación automática: `api/app/main.py:65`; forma de error comprobada con
FastAPI/Pydantic instalados en este workspace.

### 6. Notas de seguridad

La identidad verificada determina el propietario. Si el cliente aporta `owner`,
solo puede usar el mismo `sub`; no hay excepción administrativa basada en
`role`. Los valores SQL se enlazan como parámetros. Evidencia:
`api/app/main.py:65-72`; `api/app/authorization.py:4-6`;
`api/app/repositories.py:12-32`.

---

## `GET /api/summary`

### 1. Qué hace

Resume el número y estado de las tareas del usuario autenticado y cuenta sus
tareas abiertas de prioridad alta. Evidencia: `api/app/main.py:75-90`.

### 2. Autenticación

Requiere `Authorization: Bearer <JWT>` según la sección de autenticación común.

### 3. Request

No tiene cuerpo.

| Campo/parámetro | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `Authorization` (header) | Bearer JWT | Sí | Token firmado que identifica al usuario. |
| `owner` (query) | string | No | Si se omite, se usa el `sub` del token. Si se envía, debe coincidir con ese `sub`. |

Ejemplo completo:

```bash
curl --get "http://localhost:8000/api/summary" \
  --data-urlencode "owner=student" \
  -H "Authorization: Bearer $TOKEN"
```

### 4. Response exitosa

**200 OK**.

| Campo | Tipo | Descripción |
|---|---|---|
| `owner` | string | Identidad autenticada. |
| `total` | integer | Total de tareas para ese usuario. |
| `byStatus` | object de string a integer | Cantidad de tareas por cada valor de estado presente. |
| `highPriorityOpen` | integer | Tareas con `priority` igual a `HIGH` cuyo estado no es `DONE` ni `ARCHIVED`. |

Ejemplo para las tareas semilla de `student`:

```json
{
  "owner": "student",
  "total": 2,
  "byStatus": {
    "TODO": 1,
    "IN_PROGRESS": 1
  },
  "highPriorityOpen": 1
}
```

Evidencia: `api/app/main.py:75-90`; consulta:
`api/app/repositories.py:35-40`.

### 5. Respuestas de error

| Código | Cuándo ocurre | Ejemplo de cuerpo |
|---|---|---|
| 401 | Autenticación ausente o inválida. | `{"detail":"Invalid token"}` |
| 403 | `owner` no coincide con el `sub` autenticado. | `{"detail":"Not authorized for requested owner"}` |
| 503 | Configuración JWT inválida/ausente o JWKS no disponible. | `{"detail":"Token verification is not configured"}` o `{"detail":"Token verification is unavailable"}` |
| 500 | Error inesperado de SQLite u otro error no capturado; no hay cuerpo de error propio de la aplicación. | `Internal Server Error` |

### 6. Notas de seguridad

El resumen se consulta exclusivamente para la identidad verificada; indicar un
`owner` diferente devuelve 403. La consulta de tareas usa parámetros enlazados.
Evidencia: `api/app/main.py:76-78`; `api/app/authorization.py:4-6`;
`api/app/repositories.py:35-40`.

---

## `POST /api/requirements`

### 1. Qué hace

Guarda un archivo de requerimientos y devuelve sus metadatos de almacenamiento.
Evidencia: `api/app/main.py:92-97`.

### 2. Autenticación

Requiere `Authorization: Bearer <JWT>` según la sección de autenticación común.

### 3. Request

El cuerpo es `multipart/form-data`; el cliente debe enviar una parte de archivo.

| Campo/parámetro | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `Authorization` (header) | Bearer JWT | Sí | Token firmado que identifica al usuario. |
| `file` (form-data) | archivo multipart | Sí | El nombre de archivo recibido se utiliza como nombre de destino. El contenido se guarda completo. |

Ejemplo completo:

```bash
curl -X POST "http://localhost:8000/api/requirements" \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@requirements.txt;type=text/plain"
```

No fijes manualmente el `Content-Type` multipart: `curl` debe generar el
boundary junto con la parte `file`.

### 4. Response exitosa

**201 Created**.

| Campo | Tipo | Descripción |
|---|---|---|
| `owner` | string | `sub` de la identidad autenticada. |
| `fileName` | string o null | Nombre recibido en la parte multipart. |
| `storedAt` | string | Ruta construida en el servidor; depende de `WORKSHOP_UPLOAD_DIR` y del sistema operativo. |
| `size` | integer | Número de bytes guardados. |

Ejemplo con el directorio por defecto en un entorno Unix-like (la ruta puede
cambiar por configuración y sistema operativo):

```json
{
  "owner": "student",
  "fileName": "requirements.txt",
  "storedAt": "uploads/requirements.txt",
  "size": 24
}
```

Evidencia: `api/app/main.py:19-23,92-97`.

### 5. Respuestas de error

| Código | Cuándo ocurre | Ejemplo de cuerpo |
|---|---|---|
| 401 | Autenticación ausente o inválida. | `{"detail":"Invalid token"}` |
| 422 | Falta la parte `file` o el cuerpo no corresponde al formulario requerido. | `{"detail":[{"type":"missing","loc":["body","file"],"msg":"Field required","input":null}]}` |
| 503 | Configuración JWT inválida/ausente o JWKS no disponible. | `{"detail":"Token verification is not configured"}` o `{"detail":"Token verification is unavailable"}` |
| 500 | Error inesperado al crear/escribir el archivo u otro error no capturado; no hay cuerpo de error propio de la aplicación. | `Internal Server Error` |

La forma de 422 mostrada se comprobó localmente con el framework instalado; el
detalle puede variar con la versión de FastAPI/Pydantic.

### 6. Notas de seguridad

Esta ruta exige identidad verificada, pero el código actual concatena el nombre
de archivo recibido al directorio, lee el archivo completo en memoria y no
comprueba extensión ni tamaño. No debe interpretarse como una garantía de
almacenamiento seguro. `storedAt` también revela la ruta del servidor.
H-API-04 permanece pendiente. Evidencia: `api/app/main.py:92-97`.

---

## `GET /api/backend-health`

### 1. Qué hace

Consulta el endpoint de salud de autenticación configurado para que el cliente
pueda comprobar su estado desde la API. Evidencia: `api/app/main.py:99-106`.

### 2. Autenticación

Requiere `Authorization: Bearer <JWT>` según la sección de autenticación común.

### 3. Request

No tiene query parameters ni cuerpo.

| Campo/parámetro | Tipo | Obligatorio | Descripción |
|---|---|---|---|
| `Authorization` (header) | Bearer JWT | Sí | Token firmado que identifica al usuario. |

Ejemplo completo:

```bash
curl "http://localhost:8000/api/backend-health" \
  -H "Authorization: Bearer $TOKEN"
```

El destino consultado es `AUTH_HEALTH_URL`; si no se configura, el valor
predeterminado en el código es `http://localhost:8080/q/health`.

### 4. Response exitosa

**200 OK**. Este código externo permanece 200 incluso cuando falla la consulta
al servicio de salud; en ese caso se devuelve `status: 0`.

| Campo | Tipo | Descripción |
|---|---|---|
| `requestedBy` | string | `sub` de la identidad autenticada. |
| `status` | integer | Código HTTP del servicio consultado; vale `0` si la solicitud genera una excepción. |
| `body` | string | Cuerpo recibido del servicio, decodificado como UTF-8; ante una excepción contiene `str(error)`. |

Ejemplo ilustrativo de respuesta cuando el servicio consultado devuelve el
cuerpo `{"status":"UP"}`:

```json
{
  "requestedBy": "student",
  "status": 200,
  "body": "{\"status\":\"UP\"}"
}
```

El contenido exacto de `body` depende de la respuesta del servicio configurado
y no está fijado por esta API. Evidencia: `api/app/main.py:100-106`.

### 5. Respuestas de error

| Código | Cuándo ocurre | Ejemplo de cuerpo |
|---|---|---|
| 401 | Autenticación ausente o inválida. | `{"detail":"Invalid token"}` |
| 503 | Configuración JWT inválida/ausente o JWKS no disponible. | `{"detail":"Token verification is not configured"}` o `{"detail":"Token verification is unavailable"}` |
| 500 | Error inesperado fuera del bloque que captura fallos de la consulta; la aplicación no define un cuerpo propio. | `Internal Server Error` |

Un error de conexión ocurrido durante la consulta no es una respuesta HTTP de
error de esta ruta: queda representado en la respuesta 200 con `status: 0` y el
texto de la excepción en `body`.

### 6. Notas de seguridad

La respuesta identifica al solicitante con el `sub` verificado. El endpoint
reenvía el cuerpo de salud y, si ocurre una excepción, incluye su texto mediante
`str(error)`; no se sanitiza ni se transforma en un mensaje genérico.
Evidencia: `api/app/main.py:100-106`.

---

## Preguntas abiertas

- ¿Qué emisor desplegado proporciona el JWT y qué valores de `jwt_iss`,
  `jwt_aud` y `jwks_endpoint` deben usarse en cada entorno? La compatibilidad
  real con el emisor no se verifica en este contrato.
- ¿Qué extensiones y tamaño máximo deben permitirse en `/api/requirements`?
  Actualmente no hay límites de extensión o tamaño implementados.
- ¿Qué valores de `status` y `priority` deben considerarse válidos para crear
  tareas? El código actual convierte los valores a string sin validar un
  conjunto permitido.
- ¿Qué esquema de cuerpo de salud publica el servicio externo? La API solo
  transporta ese cuerpo como texto.
- Los errores 500 no tienen contrato de aplicación: el cuerpo depende del
  middleware y del despliegue que maneje el error.
