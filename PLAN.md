# Plan de corrección — API

### Aprobación humana
- Antonio
- 2026/10/26
- H-API-01,H-API-02,H-API-03,H-API-04

## Selección

Se seleccionaron H-API-01, H-API-02, H-API-03 y H-API-04. H-API-01 se implementó como prerrequisito directo de H-API-02; H-API-02 y H-API-03 también se implementaron. H-API-04 sigue pendiente por la política de carga. H-API-05 queda pendiente de verificar advisories; H-API-06 y H-API-07 se difieren para mantener acotada la intervención.

## Contrato y condiciones previas

`docs/ENDPOINTS.md` no existe. Se preservarán las rutas observadas (`GET /api/tasks`, `POST /api/tasks`, `GET /api/summary`, `POST /api/requirements` y `GET /api/backend-health`) y las formas de respuesta para las solicitudes autorizadas y válidas.

Contrato JWT acordado en esta sesión para la API: RS256; `iss` y `aud` se comparan con `jwt_iss` y `jwt_aud`; las claves se consultan desde `jwks_endpoint`; se requieren los claims `sub`, `role`, `exp`, `iss` y `aud`. Los valores y la clave privada permanecen fuera del repositorio. El emisor externo debe publicar JWKS y emitir ese formato; no se cambia código de otros componentes. Para cargas de archivos aún deben acordarse tamaño máximo y extensiones permitidas.

Aprobación registrada para H-API-01–H-API-04: Antonio, 2026/10/26; confirmada en esta sesión. La implementación autorizada cubre H-API-01, H-API-02 y H-API-03. El emisor externo debe cumplir el contrato antes de la integración real; esa coordinación no se verificó ni modificó fuera de `api/`. H-API-04 permanece pendiente por la política de carga.

## H-API-01 — Token Base64 con secreto embebido

- **Hallazgo:** H-API-01, ahora `Resuelto` en `HALLAZGOS.md`.
- **Problema:** `api/app/main.py:14,17,20,22,24` decodifica Base64 y compara una constante, sin verificar una firma JWT ni claims de issuer/audience. El token actual y el encabezado Bearer son parte del comportamiento observado.
- **Cambio propuesto:** separar la verificación en un módulo de seguridad; validar firma, algoritmo permitido, expiración, issuer y audience con valores de configuración, sin secretos reales en código. Mantener el encabezado Bearer y aplicar el nuevo formato solo después de confirmar la compatibilidad con el emisor. No aceptar el formato legado como alternativa permanente, porque conservaría el hallazgo. Evaluar una biblioteca JWT mantenida (por ejemplo, PyJWT) únicamente tras revisar advisories y coordinar la dependencia; no agregarla antes de esa decisión.
- **Archivos a tocar:** `api/app/main.py`, nuevo `api/app/security.py`, `api/requirements.txt` y `api/tests/test_api.py`.
- **Caracterización antes de tocar producción:** ampliar `api/tests/test_api.py` para registrar el comportamiento actual con un token legado válido, uno vencido y uno con secreto incorrecto: acceso actual para el válido y 401 para inválidos. Conservar el test de acceso existente como referencia. Después de acordar emisor y formato, agregar pruebas de JWT válido y de firma, expiración, issuer y audience incorrectos; los inválidos deben seguir recibiendo 401.
- **Integración pendiente:** el emisor debe desplegar tokens RS256 con los claims acordados y publicar JWKS en `jwks_endpoint`. La API rechaza el formato legado; usar claves efímeras y valores ficticios aislados en pruebas.
- **Configuración acordada:** `jwt_iss`, `jwt_aud` y `jwks_endpoint`; algoritmo RS256, con `sub`, `role`, `exp`, `iss` y `aud` requeridos.
- **Dependencia:** se aprobó añadir `PyJWT[crypto]==2.15.1` tras revisar PyPI y el historial oficial de releases/advisories. PyPI publica 2.15.1 el 2026-09-28; el historial oficial identifica 2.13.0 como release de seguridad. No se encontró evidencia de un advisory específico contra 2.15.1 en la revisión hecha; Dependency Review sigue siendo un control obligatorio.
- **Caracterización previa:** antes del cambio se ejecutó `.\.venv\Scripts\python.exe -m pytest tests/test_api.py -q` desde `api/`: 11 pruebas pasaron con el validador legado, incluyendo token válido, expirado y secreto incorrecto.

## H-API-02 — Autorización de tareas controlable por el cliente

- **Hallazgo:** H-API-02, ahora `Resuelto` en `HALLAZGOS.md`; `owner` se compara con la identidad de JWT verificado.
- **Problema:** `api/app/main.py:68-70,78,83-85,91-93` permite que query/body `owner` sustituya a `identity["username"]` en lecturas y escrituras.
- **Cambio propuesto:** centralizar la comprobación de propietario en una función de autorización reutilizable. El propietario efectivo será la identidad verificada; si el cliente especifica otro propietario sin una regla de rol acordada, responder 403. Mantener rutas, parámetros/campos observados y formatos de respuesta para solicitudes autorizadas; el rechazo de acceso entre propietarios es un cambio de seguridad intencional.
- **Archivos a tocar:** `api/app/main.py`, nuevo `api/app/authorization.py` y `api/tests/test_api.py`.
- **Caracterización antes de tocar producción:** en una base SQLite temporal, registrar con pruebas que un token de `student` puede actualmente consultar tareas/resumen de `trainer` indicando `owner=trainer` y crear una tarea con ese owner. Mantener también la caracterización de defaults para `student`. Después, reemplazar las expectativas de acceso cruzado por 403 y comprobar que omitir `owner` o solicitar el owner propio conserva los resultados y formatos actuales.
- **Riesgo contractual:** no existe contrato acordado que defina acceso administrativo por rol. No inferir permisos de `role`; cualquier excepción para roles debe acordarse antes de implementarla.

## H-API-03 — Filtros e inserts SQL concatenados

- **Hallazgo:** H-API-03, ahora `Resuelto` en `HALLAZGOS.md`.
- **Problema:** `api/app/main.py:70-71,84-87,93` interpola valores de entrada en consultas de listado, creación y resumen.
- **Cambio propuesto:** mover las consultas afectadas a funciones de repositorio y usar placeholders SQLite (`?`) con secuencias de parámetros para cada valor variable. Mantener los mismos endpoints, columnas devueltas, orden y códigos/formas de respuesta en operaciones válidas; mantener el identificador de fila derivado de `lastrowid` como valor enlazado en la consulta posterior.
- **Archivos a tocar:** `api/app/main.py`, nuevo `api/app/repositories.py` y `api/tests/test_api.py`.
- **Caracterización antes de tocar producción:** conservar pruebas de listado, creación y resumen que registren los códigos y formas actuales para datos simples. Añadir un caso local con texto ficticio que contenga una comilla en un campo de tarea y registrar el comportamiento actual. Tras parametrizar, exigir que el valor se guarde y se devuelva literalmente, sin alterar otras filas; cubrir también filtros de propietario como valores literales.

## H-API-04 — Nombre de archivo no normalizado ni limitado

- **Hallazgo:** H-API-04, `Pendiente` en `HALLAZGOS.md`.
- **Problema:** `api/app/main.py:108-112` concatena `file.filename` al directorio, lee todo el contenido y escribe sin validar extensión, ruta ni tamaño.
- **Cambio propuesto:** encapsular el guardado en una responsabilidad separada; aceptar solo nombres normalizados que permanezcan dentro del directorio de cargas, aplicar una lista permitida de extensiones y leer como máximo el límite acordado más un byte para detectar exceso antes de escribir. Usar constantes con nombre para la lista y el límite, no valores mágicos. Mantener el endpoint y las claves de respuesta para cargas válidas; rechazar entradas inválidas con errores HTTP genéricos.
- **Archivos a tocar:** `api/app/main.py`, nuevo `api/app/file_storage.py` y `api/tests/test_api.py`. Solo agregar configuración si la política acordada requiere valores configurables.
- **Caracterización antes de tocar producción:** conservar el caso actual de `requirements.txt` y comprobar código 201, claves de respuesta y archivo almacenado. En `tmp_path`, añadir un caso con nombre de ruta relativa como `../escaped.txt` para registrar dónde escribe hoy, sin salir del directorio temporal. Después, exigir rechazo y ausencia de escritura fuera del directorio de cargas; agregar casos para extensión no permitida y tamaño superior al límite acordado.
- **Pendiente:** acordar extensiones aceptadas y máximo de bytes antes de fijar constantes y expectativas exactas de error.

## Verificación posterior prevista

Tras aprobación e implementación, ejecutar desde `api/` `python -m pytest` y registrar el comando y resultado en `docs/TESTING.md` con los IDs afectados. Medir la cobertura del código modificado y perseguir el mínimo de 85% indicado en `AGENTS.md`; no alterar los quality gates. No crear `docs/TESTING.md` en esta etapa.

## Historial de ejecución

- **2026-10-26 — api — H-API-02, H-API-03 — caracterización antes del cambio:** `python -m pytest tests/test_api.py -q` con Python del sistema no inició porque no tiene `pytest` instalado; no hubo pruebas ejecutadas en ese intento.
- **2026-10-26 — api — H-API-02, H-API-03 — caracterización antes del cambio:** primera ejecución con `.\.venv\Scripts\python.exe -m pytest tests/test_api.py -q`: 7 pasaron y 1 falló porque el `TestClient` propagó la excepción SQL en vez de devolver el HTTP 500 caracterizado.
- **2026-10-26 — api — H-API-02, H-API-03 — caracterización antes del cambio:** tras configurar ese caso con `raise_server_exceptions=False`, la misma orden con el Python de `.venv` terminó con **8 pruebas pasadas**. Las pruebas confirmaron acceso cruzado actual y error SQL para valores con comilla. Se usaron rutas temporales aisladas para la base y cargas de la app global; no se modificó producción en esta fase.
- **2026-10-26 — api — H-API-02, H-API-03 — corrección después del cambio:** `.\.venv\Scripts\python.exe -m pytest tests/test_api.py -q --cov=app --cov-report=term-missing`, desde `api/`: **9 pruebas pasadas**. Cobertura informada: `app/main.py` 90%, `app/repositories.py` 86%, `app/authorization.py` 100% (cubierto completamente); total de los módulos medidos 90%. Las pruebas confirman 403 para acceso cruzado y round-trip de valores con comilla. Solo quedaron advertencias deprecadas existentes de `FastAPI.on_event`/Starlette.
- **2026-10-26 — api — H-API-02 — revisión local:** se regresó a `Pendiente` porque el control de owner depende de `legacy_identity`, que no autentica criptográficamente el token. H-API-03 permanece `Resuelto`. No se ejecutaron pruebas durante esta revisión.
- **2026-10-26 — api — H-API-01, H-API-02 — caracterización previa a JWT:** `.\.venv\Scripts\python.exe -m pytest tests/test_api.py -q`, desde `api/`: **11 pruebas pasadas** con el validador legado. Incluyeron token válido, vencido, secreto incorrecto, acceso cruzado y valores SQL con comillas.
- **2026-10-26 — api — H-API-01 — evaluación de dependencia:** se consultaron PyPI y las releases/advisories oficiales de PyJWT. Se identificó 2.15.1 como release actual publicada el 2026-09-28 y se autorizó `PyJWT[crypto]==2.15.1` para RS256; aún no se instaló ni se cambió el manifiesto.
- **2026-10-26 — api — H-API-01, H-API-02 — caracterización previa al cambio JWT:** `.\.venv\Scripts\python.exe -m pytest tests/test_api.py -q -k 'valid_rs256_token or legacy_token_format or configuration_is_missing'`, desde `api/`: 3 fallaron como se esperaba con el validador legado (JWT válido respondía 401, token Base64 legado respondía 200 y configuración JWT ausente no respondía 503).
- **2026-10-26 — api — H-API-01 — dependencia instalada:** después de agregar el pin, `.\.venv\Scripts\python.exe -m pip install 'PyJWT[crypto]==2.15.1'`, desde `api/`, terminó correctamente; instaló PyJWT 2.15.1 y el extra RSA `cryptography` 50.0.2.
- **2026-10-26 — api — H-API-01, H-API-02, H-API-03 — corrección después del cambio JWT:** `.\.venv\Scripts\python.exe -m pytest tests/test_api.py -q --cov=app --cov-report=term-missing`, desde `api/`: **19 pruebas pasadas**. Cobertura: `app/main.py` 91%, `app/repositories.py` 86%, `app/security.py` 87%, `app/authorization.py` completa; total 89%. Incluye firma RS256, expiración, issuer, audience, claims requeridos, rechazo de token legado, errores genéricos y regresiones de owner/SQL.
- **2026-10-26 — api — H-API-01, H-API-02, H-API-03 — verificación final:** se repitió la misma orden después de tipar el fixture JWKS; **19 pruebas pasadas**, `app/main.py` 91%, `app/repositories.py` 86%, `app/security.py` 87%, cobertura total 89%.
