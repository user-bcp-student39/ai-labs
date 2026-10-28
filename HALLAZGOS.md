# Hallazgos

## Contrato observado de API

`docs/ENDPOINTS.md` no existe en el workspace. Según `api/app/main.py`, las rutas observadas son: `GET /api/tasks` (lista tareas), `POST /api/tasks` (crea una tarea, respuesta 201), `GET /api/summary` (resumen), `POST /api/requirements` (carga un archivo, respuesta 201) y `GET /api/backend-health` (consulta el health del backend de autenticación). Las cinco rutas dependen de `legacy_identity`; las rutas de tareas y resumen admiten `owner`, la creación admite `owner` en el cuerpo, y la carga devuelve propietario y datos del archivo. Esto es contrato observado en el código, no contrato acordado.

## Matriz de seguimiento

| id | componente | hallazgo | tipo | explicacion | evidencia (archivo:linea) | severidad | estado |
|---|---|---|---|---|---|---|---|
| H-API-01 | api | Token Base64 con secreto embebido | Vulnerabilidad | Base64 no firma ni autentica el contenido. El secreto está fijado en el código; si se conoce, un cliente podría fabricar identidades, y el flujo no valida issuer ni audience. | api/app/security.py:38-56,74-97 | alta | Resuelto — se rechaza el formato legado y se verifica JWT RS256 con firma, exp, iss, aud, sub y role desde JWKS configurado. |
| H-API-02 | api | Autorización de tareas controlable por el cliente | Vulnerabilidad | `owner` de query o del cuerpo puede reemplazar la identidad del token al leer tareas, consultar el resumen o crear una tarea; esto puede permitir acceso o escritura entre propietarios. | api/app/authorization.py:4-6; api/app/security.py:38-64; api/app/main.py:56-77 | alta | Resuelto — owner debe coincidir con identidad del JWT verificado; accesos cruzados reciben 403. |
| H-API-03 | api | Filtros e inserts SQL concatenados | Vulnerabilidad | Valores del cliente se interpolan en SQL de lectura y creación. Comillas o contenido SQL pueden alterar la consulta, causar errores o cambiar qué filas/valores se procesan. | api/app/repositories.py:4-9,20-30,35-40 | alta | Resuelto — consultas de lectura, insert y recuperación usan placeholders enlazados. |
| H-API-04 | api | Nombre de archivo no normalizado ni limitado | Vulnerabilidad | El nombre proporcionado por la carga se une directamente al directorio y se escribe; no se ve validación de ruta/extensión ni límite de tamaño antes de leer todo el contenido. Una ruta manipulada puede escapar del directorio previsto donde el sistema de archivos lo permita, y archivos grandes pueden consumir memoria/disco. | api/app/main.py:94-96 (evidencia original) | media | Implementado localmente; pendiente de revisión |
| H-API-05 | api | Versiones de dependencias requieren revisión SCA | Sugerencia | `urllib3` y `python-multipart` aparecen en las versiones señaladas por `RETO.md`; si un advisory aplicable afecta esas versiones, el servicio podría quedar expuesto. La presencia y versión están comprobadas, pero no se verificaron advisories ni se afirma aquí un CVE. | api/requirements.txt:4-5; api/app/main.py:12,108 | media | Pendiente |
| H-API-06 | api | Rutas, persistencia, reglas y serialización concentradas en un módulo | Refactor | `create_app` crea la conexión y tabla y declara las rutas; las rutas consultan SQLite, aplican reglas y construyen respuestas en el mismo archivo. Esto acopla cambios y dificulta probar responsabilidades de forma aislada. | api/app/main.py:29-37,56-60,67-112 | baja | Pendiente |
| H-API-07 | api | Tipado amplio, excepciones genéricas y lógica anidada | Refactor | El cuerpo de creación usa `dict[str, Any]`, se capturan `Exception` en distintos flujos y `summary` anida condiciones; esto reduce validación estática y claridad y puede ocultar errores o exponer mensajes internos. | api/app/main.py:17-26,78,94-104,120-122 | baja | Pendiente |

## Candidatos de discovery — API

### H-API-04 — La carga no restringe rutas ni tamaño del archivo
- Estado: Aprobado para implementación; cambio local pendiente de revisión
- Evidencia: `api/app/main.py:94-96` concatena `file.filename` al directorio de carga y escribe el resultado sin comprobar que la ruta resuelta permanezca dentro de ese directorio; además, `await file.read()` carga el archivo completo en memoria. `api/tests/test_api.py:187-197,508-519` comprueba una carga ordinaria y una vacía, no nombres/rutas ni límites de tamaño.
- Impacto: un usuario autenticado podría intentar sobrescribir archivos a los que tenga acceso el proceso mediante un nombre con segmentos de ruta; una carga grande también puede consumir memoria y disco. El resultado depende del sistema de archivos y de los permisos del proceso.
- Prioridad propuesta: Media
- Contrato potencialmente afectado: `POST /api/requirements` (nombre aceptado, destino de almacenamiento, límite de tamaño y respuesta `201`).
- Cómo validarlo: con un directorio temporal, probar nombres con segmentos de ruta en Windows y POSIX y verificar que ningún archivo se cree o sobrescriba fuera del directorio permitido; probar el límite acordado y comprobar que las cargas mayores se rechacen sin leerlas completas en memoria.

### H-API-08 — La creación permite tareas vacías y valores de estado/prioridad sin validar
- Estado: CANDIDATO
- Evidencia: `api/app/main.py:65-74` convierte valores del cuerpo con `str()` y usa valores por defecto, sin validar contenido, longitud ni opciones de `status` y `priority`. `api/tests/test_api.py:470-478` confirma que `{}` crea una tarea `201` con título y descripción vacíos.
- Impacto: se pueden persistir tareas mal formadas o con estados/prioridades desconocidos, lo que puede contaminar `GET /api/summary` y producir datos inesperados para los consumidores.
- Prioridad propuesta: Media
- Contrato potencialmente afectado: `POST /api/tasks` (campos requeridos, valores válidos y respuesta `201`) y `GET /api/summary` (`byStatus` y `highPriorityOpen`).
- Cómo validarlo: enviar campos ausentes, cadenas vacías, tipos JSON no textuales y valores desconocidos de estado/prioridad; confirmar el comportamiento contractual esperado y que los casos inválidos no persistan ni alteren el resumen.

### H-API-09 — El health del backend responde HTTP 200 ante fallas del upstream
- Estado: CANDIDATO
- Evidencia: `api/app/main.py:100-106` devuelve el estado del upstream dentro del JSON y transforma cualquier excepción en `status: 0`, sin cambiar el estado HTTP exterior. `api/tests/test_api.py:582-603` confirma HTTP `200` ante upstream `503` y ante una excepción, incluyendo el texto de la excepción en `body`.
- Impacto: monitores o clientes que dependan del estado HTTP pueden interpretar como exitoso un backend no disponible; el mensaje de excepción también puede revelar detalles de red o del entorno a usuarios autenticados.
- Prioridad propuesta: Media
- Contrato potencialmente afectado: `GET /api/backend-health` (semántica de éxito/error HTTP y contenido de `body`).
- Cómo validarlo: simular respuestas upstream `503` y errores de conexión, comprobar el estado HTTP y la información expuesta, y acordar si el contrato requiere propagar un error HTTP o mantener explícitamente la envoltura `200` con un estado de aplicación.

## Evidencia de implementación — H-API-04 (API)

- Decisiones aprobadas: máximo 5 MiB; extensiones `.txt`, `.md` y `.json`; normalización a nombre base; rechazo de duplicados; archivos vacíos permitidos; `storedAt` relativo.
- Validación ejecutada desde la raíz: `python tools/lab.py test api` — código 0, **65 passed**, cobertura total **93.89%** (gate mínimo 85%).
- Estado: implementación local lista para revisión; no integrada.
- Riesgo residual: el límite se aplica al leer la carga en la aplicación; no limita por sí mismo el cuerpo HTTP que la infraestructura multipart pueda recibir o almacenar temporalmente.
