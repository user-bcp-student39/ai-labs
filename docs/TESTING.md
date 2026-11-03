# Pruebas del componente api

Componente: api. IDs de hallazgos relacionados: H-API-01, H-API-02, H-API-03, H-API-04, H-API-07, H-API-10. Contrato de referencia: [docs/ENDPOINTS.md](docs/ENDPOINTS.md).

Archivos de prueba:
- [api/tests/test_api.py](api/tests/test_api.py): 7 pruebas (base y H-API-03).
- [api/tests/test_endpoints.py](api/tests/test_endpoints.py): 42 pruebas por endpoint (camino feliz, casos borde, errores y aislamiento de owner).

## Tabla de casos

Los casos marcados XFAIL están escritos con `pytest.mark.xfail(strict=True)` y su motivo. Fallan hoy por el hallazgo indicado y no se ajustaron para pasar. Si el hallazgo se corrige sin quitar la marca, la prueba falla y obliga a retirarla.

| endpoint | caso | tipo | resultado esperado |
|---|---|---|---|
| Protegidos (5 endpoints) | Sin encabezado, token expirado, secreto distinto o token mal formado (`test_protected_endpoints_return_401_for_invalid_token`, 20 casos) | Error | 401 con `detail` que empieza por `Invalid token: ` |
| GET /api/tasks | Lista las dos tareas sembradas de student (`test_list_returns_seeded_tasks_for_token_owner`) | Camino feliz | 200 con "Refactor login" y "Review API" |
| GET /api/tasks | owner=student igual al token (`test_list_with_own_owner_query_returns_same_tasks`) | Camino feliz | 200 con las mismas tareas |
| GET /api/tasks | Cada tarea tiene exactamente los 7 campos del contrato (`test_list_items_have_contract_fields`) | Camino feliz | Claves: id, title, description, status, owner, priority, createdAt |
| GET /api/tasks | Orden por id (`test_list_is_ordered_by_id`) | Caso borde | IDs en orden ascendente |
| GET /api/tasks | Usuario sin tareas (`test_list_returns_empty_array_when_owner_has_no_tasks`) | Caso borde | 200 con `[]` |
| GET /api/tasks | Un usuario lee tareas de trainer con owner=trainer (`test_list_user_cannot_read_other_owner_tasks`) | Seguridad, XFAIL H-API-02 | 403, o lista vacía. Hoy devuelve 200 con la tarea de trainer |
| POST /api/tasks | Cuerpo completo (`test_create_with_full_body_returns_201`) | Camino feliz | 201 con los valores enviados y owner student |
| POST /api/tasks | Cuerpo `{}` (`test_create_with_empty_payload_applies_defaults`) | Caso borde | 201 con title y description `""`, status TODO, priority MEDIUM |
| POST /api/tasks | Sin cuerpo (`test_create_without_body_returns_422`) | Error | 422 con `loc` igual a `["body"]` |
| POST /api/tasks | owner=trainer en el cuerpo (`test_create_ignores_owner_sent_in_body`) | Seguridad, XFAIL H-API-02 | 201 con owner student. Hoy la tarea queda a nombre de trainer |
| GET /api/summary | Resumen de student (`test_summary_for_token_owner`) | Camino feliz | `{"owner":"student","total":2,"byStatus":{"TODO":1,"IN_PROGRESS":1},"highPriorityOpen":1}` |
| GET /api/summary | Usuario sin tareas (`test_summary_for_owner_without_tasks_is_zero`) | Caso borde | total 0, byStatus `{}`, highPriorityOpen 0 |
| GET /api/summary | HIGH con DONE y ARCHIVED no cuenta como abierta (`test_summary_excludes_done_and_archived_from_high_priority_open`) | Caso borde | total 3, highPriorityOpen 1 |
| GET /api/summary | Resumen de trainer con owner=trainer (`test_summary_user_cannot_read_other_owner`) | Seguridad, XFAIL H-API-02 | 403, o total 0. Hoy devuelve total 1 |
| POST /api/requirements | Subida de requirements.txt (`test_upload_returns_201_with_contract_fields`) | Camino feliz | 201 con owner, fileName, storedAt, size 24; el archivo queda en uploads/ con su contenido |
| POST /api/requirements | Archivo de 0 bytes (`test_upload_empty_file_is_stored_with_size_zero`) | Caso borde | 201 con size 0 |
| POST /api/requirements | Archivo sin extensión (`test_upload_file_without_extension_is_accepted_as_observed`) | Caso borde, caracterización | 201. Comportamiento actual, sin validación de extensión (riesgo H-API-04) |
| POST /api/requirements | Archivo de 10 MiB (`test_upload_rejects_oversized_file`) | Caso borde de tamaño, XFAIL H-API-04 | 413. Hoy devuelve 201 |
| POST /api/requirements | Nombre `../escape.txt` (`test_upload_name_cannot_escape_upload_dir`) | Seguridad, XFAIL H-API-04 | El archivo no se crea fuera de uploads/. Hoy se crea en el directorio padre |
| POST /api/requirements | Sin campo file (`test_upload_without_file_returns_422`) | Error | 422 con `loc` igual a `["body","file"]` |
| GET /api/backend-health | Servicio local que responde 200 (`test_backend_health_reports_upstream_status`) | Camino feliz | 200 con `{"requestedBy":"student","status":200,"body":"{\"status\":\"UP\"}"}` |
| GET /api/backend-health | Servicio inalcanzable (`test_backend_health_unreachable_returns_200_with_status_zero`) | Error documentado | 200 con status 0 y body con el texto del error (H-API-10) |
| Base (test_api.py) | Listado con token válido (`test_lists_seeded_tasks`) | Camino feliz | 200 con 2 tareas |
| Base (test_api.py) | Creación y resumen (`test_creates_task_and_summary`) | Camino feliz | 201 y total 3 |
| Base (test_api.py) | Subida (`test_uploads_requirement`) | Camino feliz | 201 y archivo guardado |
| Base (test_api.py) | Token inválido (`test_rejects_invalid_token`) | Error | 401 |
| H-API-03 (test_api.py) | Título normal se guarda y lee (`test_characterizes_normal_title_round_trip`) | Camino feliz | 201 y título leído igual |
| H-API-03 (test_api.py) | Comilla en título (`test_stores_single_quote_title_literally`) | Caso borde | 201 con `O'Brien` guardado literal |
| H-API-03 (test_api.py) | Comilla en owner de consulta (`test_quote_in_owner_query_does_not_alter_filter`) | Seguridad | 200 con lista vacía, sin inyección |

Totales: 49 pruebas. 44 pasan, 5 son XFAIL, 0 fallan.

## Ejecuciones

Todas se hicieron con el entorno del componente, `api/.venv`, pytest 9.0.2 y Python 3.13.15. No se instalaron dependencias.

| # | Directorio | Comando | Código de salida | Resultado | Componente e IDs |
|---|---|---|---|---|---|
| E1 | api/ | `.venv\Scripts\python.exe -m pytest tests -v -rxX -p no:cacheprovider --cov=app --cov-report=term-missing` | 0 | 44 passed, 5 xfailed | api; H-API-01, H-API-02, H-API-03, H-API-04, H-API-07, H-API-10 |
| E2 | api/ | `.venv\Scripts\python.exe -m pytest tests/test_endpoints.py --runxfail -k "other_owner or ignores_owner or oversized or escape"` | 1 | 5 failed por aserción | api; H-API-02, H-API-04 |
| E3 | raíz (ai-labs) | `python tools/lab.py test api` | 0 | 44 passed, 5 xfailed; cobertura 100%; umbral 85% cumplido | api; H-API-01 a H-API-04 |
| E4 | raíz (ai-labs) | `python tools/lab.py test api` (tras H-API-13) | 0 | 79 passed, 5 xfailed; cobertura 100% (165 sentencias, 30 ramas); umbral 85% cumplido | api; H-API-13 |

E2 confirma que cada XFAIL falla por la aserción y no por una excepción no relacionada. En el caso de `../escape.txt`, el archivo sí aparece fuera de uploads/.

Las ejecuciones de H-API-03 antes y después del cambio están en [PLAN.md](PLAN.md), en "Ejecuciones (api)".

Artefactos generados: `api/.coverage` y `api/htmlcov/`. Están en [api/.gitignore](api/.gitignore) y no entran en el commit.

## Cobertura

Método: pytest-cov con cobertura de líneas y ramas (`branch = true` en [api/pyproject.toml](api/pyproject.toml)). Medida sobre el paquete `app`, que contiene el código modificado (app/main.py y app/repository.py).

| Medida | Numerador | Denominador | Resultado |
|---|---|---|---|
| Líneas, paquete app (código modificado y global) | 106 | 106 | 100% |
| Ramas, paquete app | 16 | 16 | 100% |

El informe omite los archivos con cobertura completa, así que no muestra por separado app/main.py y app/repository.py. Ambos aparecen en el informe como cubiertos. La cobertura global de la API y la del código modificado coinciden porque el paquete `app` es todo el código de la API.

No se ejecutó una herramienta de cobertura por diferencias (diff-cover). Requiere una dependencia nueva que no está aprobada. El cálculo anterior es sobre archivos completos, no solo sobre las líneas cambiadas.

## Fallos

Ningún fallo real en E1 ni E3. Los cinco XFAIL son fallos conocidos:

- H-API-02: `test_list_user_cannot_read_other_owner_tasks`, `test_create_ignores_owner_sent_in_body`, `test_summary_user_cannot_read_other_owner`.
- H-API-04: `test_upload_rejects_oversized_file`, `test_upload_name_cannot_escape_upload_dir`.

## Pendientes

- H-API-02: falta decidir si owner distinto de la identidad responde 403 o se ignora. La prueba de aislamiento acepta ambas opciones.
- H-API-04: el umbral de tamaño no está decidido. La prueba usa 10 MiB como sonda y espera 413. Hay que ajustarla cuando se fije el umbral. La lista de extensiones tampoco está decidida; la prueba de archivo sin extensión es de caracterización y deberá cambiar.
- H-API-01: no hay prueba de token con firma válida pero forjada con el secreto conocido. Las pruebas cubren solo las variantes de token inválido.
- backend-health: la prueba de éxito usa un stub local, no el servicio auth real. No hay verificación contra auth en ejecución.
- H-API-07: las pruebas no fijan el texto del detalle del 401. Solo comprueban el prefijo `Invalid token: `.
- Advertencia observada, sin ID: FastAPI avisa que `on_event` está obsoleto en [api/app/main.py](api/app/main.py#L121). No es un hallazgo de RETO.md.

## Pruebas propuestas (no ejecutadas)

- POST /api/tasks con JSON inválido: esperado 422 por FastAPI. No comprobado.
- POST /api/tasks con `title: null`: según el código se guardaría como `"None"`. Pregunta abierta 1 de docs/ENDPOINTS.md.
- backend-health con el servicio respondiendo 503: el campo `status` debería reflejar 503 y no 0.
- Preflight CORS con un origen cualquiera (H-API-12).
- Token forjado con el secreto del código: debería rechazarse tras corregir H-API-01.

## Documentos consultados

- [docs/ENDPOINTS.md](docs/ENDPOINTS.md), para los contratos y las preguntas abiertas.
- [api/app/main.py](api/app/main.py) y [api/app/repository.py](api/app/repository.py), para las líneas citadas.
- [api/pyproject.toml](api/pyproject.toml) y [api/.gitignore](api/.gitignore), para la configuración de cobertura y los artefactos ignorados.
- HALLAZGOS.md y PLAN.md, para los IDs y las decisiones pendientes.
- README.md, RETO.md y docs/GOOD_PRACTICES.md, para el comando de prueba y las convenciones.
