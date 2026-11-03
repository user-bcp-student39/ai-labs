# Plan de correccion ReqFlow

Estado: borrador de propuesta. Pendiente de revision y aprobacion humana antes de implementar. No hay aprobacion registrada en este archivo.

Alcance de esta version: componente api, hallazgos H-API-01, H-API-02 y H-API-03 (estado Pendiente en HALLAZGOS.md). H-API-04 a H-API-07 no se incluyen aqui. Solo se escribe codigo en api/ durante la implementacion. docs/ENDPOINTS.md no existe; se conserva el comportamiento observado en api/app/main.py.

## Aprobacion humana registrada
- Aprobador indicado en el plan: Esther Villar
- IDs aprobados: H-API-01, H-API-02 y H-API-03

## Reglas transversales

- Contrato intacto: rutas, metodos, cabecera Authorization Bearer, codigos 201 y 401, y campos de respuesta (owner, id, title, description, status, priority, createdAt, total, byStatus, highPriorityOpen) no cambian.
- Modelos Pydantic para el cuerpo y la respuesta de tareas (GOOD_PRACTICES: Modelos Pydantic). Los valores por defecto observados se conservan: status TODO, priority MEDIUM, description vacia, owner la identidad del token. Endurecer la validacion queda como decision aparte.
- Capas (GOOD_PRACTICES: rutas, servicio, repositorio): las rutas delegan en servicio y el servicio en repositorio con SQL parametrizado.
- Clean Code (AGENTS.md api): una responsabilidad por funcion, sin duplicacion, guard clauses en lugar de anidamiento, sin numeros ni cadenas magicas (constantes con nombre).
- Dependencias nuevas: solo con justificacion y aprobacion explicita. Ninguna se agrega en esta version.
- Pruebas: primero las de caracterizacion sobre el comportamiento observado; despues el cambio. Ejecucion desde la raiz con `python tools/lab.py test api` (cwd api/). Aun no ejecutadas.

## Dependencias externas (fuera de AMBITO, coordinar)

- auth: emite el token que api verifica. Cambiar el formato (H-API-01) exige cambiar el emisor en auth en el mismo corte. No se leyo auth/.
- web: no se sabe si envia el parametro owner en GET /api/tasks ni en GET /api/summary (H-API-02). No se leyo web/.

## H-API-01 Token Base64 con secreto embebido y sin firma

- Problema: api/app/main.py:14 fija el secreto; api/app/main.py:19-24 decodifica Base64, separa cuatro campos y solo valida la expiracion. Quien conozca el secreto puede forjar usuario y rol. api/tests/test_api.py:11 repite el secreto.
- Cambio propuesto: verificar un JWT firmado (HS256) con firma, expiracion, emisor y audiencia. El rol sale de un claim explicito. El secreto llega por variable de entorno; la configuracion queda a cargo de H-API-06, fuera de esta version.
- Dependencia propuesta: PyJWT. La biblioteca estandar no verifica JWT y una implementacion HMAC propia aumenta el riesgo. Version a fijar tras consultar la vigente; no verificada en esta fase. Requiere aprobacion explicita.
- Compatibilidad: el token Base64 actual dejaria de validar. Requiere corte coordinado con auth. Alternativa a decidir: periodo de transicion que acepte ambos formatos durante un tiempo fijo.
- Archivos: api/app/security.py (nuevo, justificado por capas), api/app/main.py, api/requirements.txt, api/tests/test_api.py.
- Prueba de caracterizacion antes de tocar: token valido responde 200 en GET /api/tasks; token vencido, con secreto distinto, mal formado o sin cuatro campos responde 401. Registrar la respuesta actual como referencia.
- Prueba de correccion (fallaria hoy): token Base64 con el secreto embebido responde 401 tras el cambio; token JWT con firma invalida responde 401.
- Clean Code: funcion `decode_identity` pequena; duracion y nombre de emisor como constantes con nombre.

## H-API-02 Autorizacion: el cliente elige el owner

- Problema: api/app/main.py:69 usa el parametro owner en el listado; api/app/main.py:92 en el resumen; api/app/main.py:83 toma owner del cuerpo al crear. Un usuario puede leer o insertar tareas de otro owner.
- Cambio propuesto: el owner de consulta y creacion sale de la identidad verificada. Si owner llega en query y es distinto de la identidad, responder 403 (alternativa: ignorarlo; decision pendiente). El cuerpo de creacion deja de definir owner.
- Decision abierta: si un trainer puede ver tareas ajenas. Hoy el codigo no tiene regla de rol; no se inventa.
- Archivos: api/app/services/tasks.py (nuevo, justificado por capas), api/app/main.py, api/tests/test_api.py.
- Prueba de caracterizacion antes de tocar: GET /api/tasks sin owner devuelve las dos tareas de student; GET /api/summary sin owner devuelve total 2; crear tarea sin owner asigna student. Hoy GET /api/tasks?owner=trainer devuelve la tarea de trainer; esto se registra como comportamiento observado.
- Prueba de correccion (fallaria hoy): student consulta owner=trainer y no recibe tareas ajenas (403 o lista propia, segun decision); crear con owner=trainer en el cuerpo asigna student.
- Clean Code: una funcion `resolve_owner(identity, requested)` reutilizada por listado y resumen, para eliminar duplicacion.

## H-API-03 Filtros e inserts concatenados en SQL

- Problema: api/app/main.py:70 y api/app/main.py:93 concatenan owner en SELECT; api/app/main.py:84 concatena cinco campos en INSERT; api/app/main.py:87 concatena el id en SELECT.
- Cambio propuesto: consultas con marcadores `?` y tuplas de parametros dentro de un repositorio (api/app/repository.py, nuevo, justificado por capas). Un solo SELECT de columnas, definido como constante.
- Archivos: api/app/repository.py (nuevo), api/app/main.py, api/tests/test_api.py.
- Prueba de caracterizacion antes de tocar: crear tarea con titulo normal y leerla igual; crear tarea con comilla simple en el titulo, por ejemplo "O'Brien". Esperado segun el analisis: la respuesta es error interno, porque el INSERT concatenado queda mal formado. Pendiente de ejecutar.
- Prueba de correccion (fallaria hoy): el titulo "O'Brien" se guarda literal y el listado lo devuelve sin error; un owner con comilla en la query no altera el resultado.
- Clean Code: funciones `insert_task` y `find_tasks_by_owner`, cada una con una sola responsabilidad.

## Preguntas abiertas para la revision humana

1. H-API-01: algoritmo y biblioteca del token, aprobacion de PyJWT y periodo de transicion con auth.
2. H-API-02: si owner distinto de la identidad responde 403 o se ignora, y si un trainer puede ver tareas ajenas.
3. Confirmar que web y auth no dependen del formato actual de owner ni del token Base64.

## Ejecuciones (api)

- H-API-03, antes del cambio (cwd api/, .venv, pytest tests/test_api.py): 9 pruebas; 7 PASSED, 2 FAILED. Fallas de correccion esperadas: test_stores_single_quote_title_literally (sqlite3.OperationalError en app/main.py:85) y test_quote_in_owner_query_does_not_alter_filter (devuelve 3 filas en vez de 0).
- H-API-03, despues del cambio: 7 PASSED, 0 FAILED. Cobertura (--cov=app): app/repository.py 100%; app/main.py 91%, sin lineas modificadas sin cubrir (faltan 25 y 114-119, fuera del cambio).
- Desviaciones de H-API-03: (1) se retiraron dos pruebas de caracterizacion que documentaban la falla (comilla en titulo y comilla en owner); las pruebas de correccion las reemplazan. (2) La consulta de resumen (app/main.py:93) tambien se parametriza, como indica el hallazgo. (3) No se agregaron modelos Pydantic: pertenecen a H-API-09, fuera de esta ejecucion.
- H-API-01 y H-API-02: no implementados. Quedan bloqueados por las decisiones abiertas (PyJWT y transicion con auth; 403 o ignorar owner, y regla de trainer).

## Orden sugerido

1. Caracterizacion de H-API-01, H-API-02 y H-API-03 (sin cambios de codigo).
2. H-API-03 (SQL parametrizado), por ser independiente de las decisiones abiertas.
3. H-API-02 (autorizacion), tras responder la pregunta 2.
4. H-API-01 (token), tras aprobacion de PyJWT y coordinacion con auth.
