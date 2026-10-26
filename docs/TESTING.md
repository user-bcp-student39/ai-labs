# Pruebas de contrato — API

**Componente:** api  
**Hallazgos relacionados:** H-API-01, H-API-02, H-API-03 y H-API-04  
**Contrato de referencia:** `docs/ENDPOINTS.md` (contrato observado en el código
actual). Las pruebas usan datos SQLite temporales, JWT RS256 ficticios y JWKS
servido en loopback. `backend-health` usa respuestas simuladas; ninguna prueba
contacta servicios remotos.

## Matriz de casos

| endpoint | caso | tipo | resultado esperado |
|---|---|---|---|
| `GET /api/tasks` | Listado con tareas semilla (`test_lists_seeded_tasks`) | Camino feliz | 200 y tareas del `sub` autenticado. |
| `GET /api/tasks` | Lista vacía (`test_lists_empty_task_collection`) | Borde | 200 y `[]`. |
| `GET /api/tasks` | Sin header / JWT inválido (`test_every_endpoint_rejects_missing_or_invalid_authentication`) | Error, H-API-01 | 401 `{"detail":"Invalid token"}`. |
| `GET /api/tasks` | Emisor/configuración ausente (`test_every_endpoint_returns_503_when_jwt_configuration_is_missing`) | Error, H-API-01 | 503 `Token verification is not configured`. |
| `GET /api/tasks` | JWKS no disponible (`test_every_endpoint_returns_503_when_jwks_is_unavailable`) | Error, H-API-01 | 503 `Token verification is unavailable`. |
| `GET /api/tasks` | Leer tareas de otro owner (`test_rejects_cross_owner_task_reads_and_summary`) | Error, H-API-02 | 403 `Not authorized for requested owner`. |
| `GET /api/tasks` | SQLite falla (`test_task_endpoints_return_500_for_sqlite_errors`) | Error | 500 `Internal Server Error`. |
| `POST /api/tasks` | Crear con campos válidos (`test_creates_task_and_summary`) | Camino feliz, H-API-03 | 201; respuesta contiene la tarea creada y el owner del token. |
| `POST /api/tasks` | Objeto JSON vacío (`test_creates_task_from_empty_json_object`) | Borde | 201; usa `""`, `TODO`, `MEDIUM` y el owner autenticado por defecto. |
| `POST /api/tasks` | Cuerpo ausente o JSON que no es objeto (`test_create_task_rejects_missing_or_non_object_json_body`) | Error | 422 con `detail` de validación. |
| `POST /api/tasks` | Crear para otro owner (`test_rejects_cross_owner_task_creation`) | Error, H-API-02 | 403 `Not authorized for requested owner`. |
| `POST /api/tasks` | Sin header / JWT inválido (`test_every_endpoint_rejects_missing_or_invalid_authentication`) | Error, H-API-01 | 401 `{"detail":"Invalid token"}`. |
| `POST /api/tasks` | Emisor/configuración ausente (`test_every_endpoint_returns_503_when_jwt_configuration_is_missing`) | Error, H-API-01 | 503 `Token verification is not configured`. |
| `POST /api/tasks` | JWKS no disponible (`test_every_endpoint_returns_503_when_jwks_is_unavailable`) | Error, H-API-01 | 503 `Token verification is unavailable`. |
| `POST /api/tasks` | SQLite falla (`test_task_endpoints_return_500_for_sqlite_errors`) | Error | 500 `Internal Server Error`. |
| `GET /api/summary` | Resumen de tareas semilla (`test_returns_summary_for_seeded_tasks`) | Camino feliz | 200 con total, conteo por estado y prioridad alta abierta. |
| `GET /api/summary` | Owner sin tareas (`test_returns_empty_summary_for_owner_without_tasks`) | Borde | 200, total 0, `byStatus` vacío y `highPriorityOpen` 0. |
| `GET /api/summary` | Owner distinto (`test_rejects_cross_owner_task_reads_and_summary`) | Error, H-API-02 | 403 `Not authorized for requested owner`. |
| `GET /api/summary` | Sin header / JWT inválido (`test_every_endpoint_rejects_missing_or_invalid_authentication`) | Error, H-API-01 | 401 `{"detail":"Invalid token"}`. |
| `GET /api/summary` | Emisor/configuración ausente (`test_every_endpoint_returns_503_when_jwt_configuration_is_missing`) | Error, H-API-01 | 503 `Token verification is not configured`. |
| `GET /api/summary` | JWKS no disponible (`test_every_endpoint_returns_503_when_jwks_is_unavailable`) | Error, H-API-01 | 503 `Token verification is unavailable`. |
| `GET /api/summary` | SQLite falla (`test_task_endpoints_return_500_for_sqlite_errors`) | Error | 500 `Internal Server Error`. |
| `POST /api/requirements` | Carga de archivo ficticio válida (`test_uploads_requirement`) | Camino feliz, H-API-04 | 201 con owner, nombre, ruta y tamaño; archivo guardado en `tmp_path`. |
| `POST /api/requirements` | Archivo de cero bytes (`test_uploads_empty_file`) | Borde, H-API-04 | 201, tamaño 0 y archivo vacío almacenado. |
| `POST /api/requirements` | Falta la parte `file` (`test_upload_requires_file_part`) | Error | 422 con `loc` igual a `["body","file"]`. |
| `POST /api/requirements` | Sin header / JWT inválido (`test_every_endpoint_rejects_missing_or_invalid_authentication`) | Error, H-API-01 | 401 `{"detail":"Invalid token"}`. |
| `POST /api/requirements` | Emisor/configuración ausente (`test_every_endpoint_returns_503_when_jwt_configuration_is_missing`) | Error, H-API-01 | 503 `Token verification is not configured`. |
| `POST /api/requirements` | JWKS no disponible (`test_every_endpoint_returns_503_when_jwks_is_unavailable`) | Error, H-API-01 | 503 `Token verification is unavailable`. |
| `POST /api/requirements` | Fallo simulado al escribir (`test_returns_500_when_file_write_fails`) | Error | 500 `Internal Server Error`. |
| `GET /api/backend-health` | Respuesta de salud simulada (`test_backend_health_passes_through_upstream_response`) | Camino feliz | 200; reproduce status y cuerpo del servicio, identifica al solicitante. |
| `GET /api/backend-health` | Servicio responde 503 (`test_backend_health_keeps_outer_200_for_upstream_error_status`) | Borde | HTTP exterior 200; `status` interno 503 y cuerpo reenviado. |
| `GET /api/backend-health` | Excepción de conexión simulada (`test_backend_health_encodes_upstream_exception_as_status_zero`) | Error de integración documentado | HTTP 200 con `status` 0 y el texto de la excepción en `body`. |
| `GET /api/backend-health` | Sin header / JWT inválido (`test_every_endpoint_rejects_missing_or_invalid_authentication`) | Error, H-API-01 | 401 `{"detail":"Invalid token"}`. |
| `GET /api/backend-health` | Emisor/configuración ausente (`test_every_endpoint_returns_503_when_jwt_configuration_is_missing`) | Error, H-API-01 | 503 `Token verification is not configured`. |
| `GET /api/backend-health` | JWKS no disponible (`test_every_endpoint_returns_503_when_jwks_is_unavailable`) | Error, H-API-01 | 503 `Token verification is unavailable`. |
| `GET /api/backend-health` | Error antes de consultar el servicio (`test_backend_health_returns_500_for_error_before_upstream_request`) | Error | 500 `Internal Server Error`. |

Los errores 403 de tareas comprueban además el cuerpo exacto. Los tests de
errores comunes de autenticación se parametrizan sobre las cinco rutas.

## Código de los tests añadidos

El código ejecutable está en [`api/tests/test_api.py`](../api/tests/test_api.py).
Este extracto reproduce los helpers y casos añadidos para completar la matriz;
los casos previos de JWT, SQL, autorización y carga permanecen en el mismo
archivo.

```python
EndpointName = Literal["list_tasks", "create_task", "summary", "upload_requirement", "backend_health"]
ENDPOINT_NAMES: tuple[EndpointName, ...] = (
    "list_tasks",
    "create_task",
    "summary",
    "upload_requirement",
    "backend_health",
)
SQL_ENDPOINT_NAMES: tuple[EndpointName, ...] = ("list_tasks", "create_task", "summary")


def request_endpoint(
    client: TestClient,
    endpoint: EndpointName,
    request_headers: dict[str, str],
) -> httpx.Response:
    if endpoint == "list_tasks":
        return client.get("/api/tasks", headers=request_headers)
    if endpoint == "create_task":
        return client.post(
            "/api/tasks",
            headers=request_headers,
            json={
                "title": "Contract task",
                "description": "Fictional test data",
                "status": "TODO",
                "priority": "MEDIUM",
            },
        )
    if endpoint == "summary":
        return client.get("/api/summary", headers=request_headers)
    if endpoint == "upload_requirement":
        return client.post(
            "/api/requirements",
            headers=request_headers,
            files={"file": ("requirements.txt", b"Fictional requirements", "text/plain")},
        )
    return client.get("/api/backend-health", headers=request_headers)


class StubHealthResponse:
    def __init__(self, status: int, body: bytes) -> None:
        self.status = status
        self.data = body


def install_health_response(
    monkeypatch: pytest.MonkeyPatch,
    status: int,
    body: bytes,
) -> list[tuple[str, str, float]]:
    calls: list[tuple[str, str, float]] = []
    upstream_response = StubHealthResponse(status, body)

    class StubPoolManager:
        def request(self, method: str, url: str, timeout: float) -> StubHealthResponse:
            calls.append((method, url, timeout))
            return upstream_response

    def create_pool_manager() -> StubPoolManager:
        return StubPoolManager()

    monkeypatch.setattr(api_main.urllib3, "PoolManager", create_pool_manager)
    return calls


def test_rejects_cross_owner_task_reads_and_summary(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        task_response = client.get(
            "/api/tasks",
            params={"owner": "trainer"},
            headers=headers(),
        )
        summary_response = client.get(
            "/api/summary",
            params={"owner": "trainer"},
            headers=headers(),
        )
    assert task_response.status_code == 403
    assert task_response.json() == {"detail": "Not authorized for requested owner"}
    assert summary_response.status_code == 403
    assert summary_response.json() == {"detail": "Not authorized for requested owner"}


def test_rejects_cross_owner_task_creation(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post(
            "/api/tasks",
            headers=headers(),
            json={
                "title": "Trainer task",
                "description": "Fictional characterization data",
                "owner": "trainer",
            },
        )
    assert response.status_code == 403
    assert response.json() == {"detail": "Not authorized for requested owner"}


@pytest.mark.parametrize("endpoint", ENDPOINT_NAMES)
@pytest.mark.parametrize(
    "request_headers",
    [{}, {"Authorization": "Bearer invalid"}],
    ids=["missing-header", "invalid-token"],
)
def test_every_endpoint_rejects_missing_or_invalid_authentication(
    tmp_path: Path,
    endpoint: EndpointName,
    request_headers: dict[str, str],
) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = request_endpoint(client, endpoint, request_headers)
    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid token"}


@pytest.mark.parametrize("endpoint", ENDPOINT_NAMES)
def test_every_endpoint_returns_503_when_jwt_configuration_is_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    endpoint: EndpointName,
) -> None:
    monkeypatch.delenv("jwt_iss")
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = request_endpoint(client, endpoint, headers())
    assert response.status_code == 503
    assert response.json() == {"detail": "Token verification is not configured"}


@pytest.mark.parametrize("endpoint", ENDPOINT_NAMES)
def test_every_endpoint_returns_503_when_jwks_is_unavailable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    endpoint: EndpointName,
) -> None:
    class UnavailableJwksClient:
        def get_signing_key_from_jwt(self, token_value: str) -> None:
            raise jwt.PyJWKClientConnectionError("fictional local JWKS failure")

    def unavailable_jwks_client(endpoint_url: str) -> UnavailableJwksClient:
        return UnavailableJwksClient()

    monkeypatch.setattr(security, "get_jwks_client", unavailable_jwks_client)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = request_endpoint(client, endpoint, headers())
    assert response.status_code == 503
    assert response.json() == {"detail": "Token verification is unavailable"}


def test_lists_empty_task_collection(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    app.state.connection.execute("DELETE FROM tasks WHERE owner = ?", ("student",))
    app.state.connection.commit()
    with TestClient(app) as client:
        response = client.get("/api/tasks", headers=headers())
    assert response.status_code == 200
    assert response.json() == []


def test_creates_task_from_empty_json_object(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post("/api/tasks", headers=headers(), json={})
    assert response.status_code == 201
    assert response.json()["title"] == ""
    assert response.json()["description"] == ""
    assert response.json()["status"] == "TODO"
    assert response.json()["priority"] == "MEDIUM"
    assert response.json()["owner"] == "student"


def test_create_task_rejects_missing_or_non_object_json_body(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        missing_body = client.post("/api/tasks", headers=headers())
        non_object_body = client.post("/api/tasks", headers=headers(), json=[])
    assert missing_body.status_code == 422
    assert missing_body.json()["detail"][0]["loc"] == ["body"]
    assert non_object_body.status_code == 422
    assert non_object_body.json()["detail"][0]["type"] == "dict_type"


def test_returns_summary_for_seeded_tasks(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/summary", headers=headers())
    assert response.status_code == 200
    assert response.json() == {
        "owner": "student",
        "total": 2,
        "byStatus": {"TODO": 1, "IN_PROGRESS": 1},
        "highPriorityOpen": 1,
    }


def test_returns_empty_summary_for_owner_without_tasks(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    app.state.connection.execute("DELETE FROM tasks WHERE owner = ?", ("student",))
    app.state.connection.commit()
    with TestClient(app) as client:
        response = client.get("/api/summary", headers=headers())
    assert response.status_code == 200
    assert response.json() == {
        "owner": "student",
        "total": 0,
        "byStatus": {},
        "highPriorityOpen": 0,
    }


def test_uploads_empty_file(tmp_path: Path) -> None:
    upload_dir = tmp_path / "uploads"
    app = create_app(str(tmp_path / "workshop.db"), str(upload_dir))
    with TestClient(app) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("empty.txt", b"", "text/plain")},
        )
    assert response.status_code == 201
    assert response.json()["size"] == 0
    assert (upload_dir / "empty.txt").read_bytes() == b""


def test_upload_requires_file_part(tmp_path: Path) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.post("/api/requirements", headers=headers())
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["body", "file"]


def test_returns_500_when_file_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_write_bytes = Path.write_bytes

    def fail_upload_write(path: Path, content: bytes) -> int:
        if path.name == "requirements.txt":
            raise OSError("fictional local write failure")
        return original_write_bytes(path, content)

    monkeypatch.setattr(Path, "write_bytes", fail_upload_write)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post(
            "/api/requirements",
            headers=headers(),
            files={"file": ("requirements.txt", b"Fictional content", "text/plain")},
        )
    assert response.status_code == 500
    assert response.text == "Internal Server Error"


@pytest.mark.parametrize("endpoint", SQL_ENDPOINT_NAMES)
def test_task_endpoints_return_500_for_sqlite_errors(
    tmp_path: Path,
    endpoint: EndpointName,
) -> None:
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    app.state.connection.execute("DROP TABLE tasks")
    app.state.connection.commit()
    with TestClient(app, raise_server_exceptions=False) as client:
        response = request_endpoint(client, endpoint, headers())
    assert response.status_code == 500
    assert response.text == "Internal Server Error"


def test_backend_health_passes_through_upstream_response(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = install_health_response(monkeypatch, 200, b'{"status":"UP"}')
    monkeypatch.setenv("AUTH_HEALTH_URL", "http://auth.example.test/q/health")
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/backend-health", headers=headers())
    assert response.status_code == 200
    assert response.json() == {
        "requestedBy": "student",
        "status": 200,
        "body": '{"status":"UP"}',
    }
    assert calls == [("GET", "http://auth.example.test/q/health", 3.0)]


def test_backend_health_keeps_outer_200_for_upstream_error_status(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    install_health_response(monkeypatch, 503, b"unavailable")
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/backend-health", headers=headers())
    assert response.status_code == 200
    assert response.json()["status"] == 503
    assert response.json()["body"] == "unavailable"


def test_backend_health_encodes_upstream_exception_as_status_zero(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class FailedPoolManager:
        def request(self, method: str, url: str, timeout: float) -> StubHealthResponse:
            raise RuntimeError("fictional local connection failure")

    def create_failed_pool_manager() -> FailedPoolManager:
        return FailedPoolManager()

    monkeypatch.setattr(api_main.urllib3, "PoolManager", create_failed_pool_manager)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app) as client:
        response = client.get("/api/backend-health", headers=headers())
    assert response.status_code == 200
    assert response.json() == {
        "requestedBy": "student",
        "status": 0,
        "body": "fictional local connection failure",
    }


def test_backend_health_returns_500_for_error_before_upstream_request(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original_getenv = api_main.os.getenv

    def fail_auth_health_setting(name: str, default: str | None = None) -> str | None:
        if name == "AUTH_HEALTH_URL":
            raise RuntimeError("fictional local configuration failure")
        return original_getenv(name, default)

    monkeypatch.setattr(api_main.os, "getenv", fail_auth_health_setting)
    app = create_app(str(tmp_path / "workshop.db"), str(tmp_path / "uploads"))
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/api/backend-health", headers=headers())
    assert response.status_code == 500
    assert response.text == "Internal Server Error"
```

Los tests preexistentes relevantes incluyen `test_lists_seeded_tasks`,
`test_creates_task_and_summary`, `test_uploads_requirement`,
`test_rejects_cross_owner_task_reads_and_summary`,
`test_rejects_cross_owner_task_creation`, `test_binds_quoted_owner_filters`,
`test_binds_quoted_task_values` y las pruebas JWT RS256. También están en
`api/tests/test_api.py`.

## Ejecuciones y cobertura

**Entorno y directorio:** Windows, Python 3.13.15; cwd `api/`. Se configuraron
`WORKSHOP_DB_PATH` y `WORKSHOP_UPLOAD_DIR` en un directorio temporal nuevo para
aislar la base global y las cargas de la aplicación. La carpeta temporal y el
JSON auxiliar de cobertura se eliminaron al finalizar.

| Ejecución | Comando | Código de salida | Resultado |
|---|---|---:|---|
| Suite API y cobertura (2026-10-26) | `.\.venv\Scripts\python.exe -m pytest tests/test_api.py -q --cov=app --cov-report=term-missing --cov-report=json:<archivo-temporal>\coverage.json` | 0 | **54 passed**; sin fallos. El comando usa `.venv` y datos temporales. |
| Cálculo de numeradores/denominadores (2026-10-26) | `.\.venv\Scripts\python.exe -m coverage json -o <archivo-temporal>.json` | 0 | JSON de cobertura generado, leído para calcular líneas y ramas cubiertas; archivo temporal eliminado. |

La configuración de `api/pyproject.toml` activa branch coverage y limita el
source a `app`. Por tanto, la cobertura de `tests/test_api.py` no se incluye
como código fuente medido. En este cambio no se modificó código de producción;
los módulos de aplicación ejecutados por la suite superan el 85%:

| Alcance | Numerador / denominador | Método | Resultado |
|---|---:|---|---:|
| `app/main.py` | 94 / 97 unidades (83/83 sentencias + 11/14 ramas) | Coverage.py, sentencias y ramas | 96.9% |
| `app/repositories.py` | 12 / 14 unidades (11/12 sentencias + 1/2 ramas) | Coverage.py, sentencias y ramas | 85.7% |
| `app/security.py` | 71 / 79 unidades (64/69 sentencias + 7/10 ramas) | Coverage.py, sentencias y ramas | 89.9% |
| `app/authorization.py` | 7 / 7 unidades (5/5 sentencias + 2/2 ramas) | Coverage.py, sentencias y ramas | 100% |
| **Global `app/`** | **184 / 197 unidades (163/169 sentencias + 21/28 ramas)** | **Coverage.py, branch coverage** | **93.4% (93% redondeado en pytest)** |

La suite emitió advertencias deprecadas existentes de `FastAPI.on_event` y
Starlette; no impidieron la ejecución.

## Fallos, pendientes y pruebas propuestas

### Fallos de ejecución

Ninguno: las 54 pruebas terminaron correctamente con código de salida 0.

### Hallazgos y pendientes

- **H-API-04 continúa siendo un defecto pendiente, no una expectativa que se
  haya convertido en un test de éxito.** `api/app/main.py:94-96` usa el nombre
  recibido para construir la ruta, lee todo el archivo y no aplica límite de
  tamaño ni filtro de extensión. Los casos de nombre sin extensión y tamaño
  máximo no se fijan como aprobados/rechazados porque `docs/ENDPOINTS.md` y
  `PLAN.md` no contienen una política acordada. El test de archivo vacío cubre
  el borde de cero bytes, no demuestra que exista un límite.
- El valor exacto del emisor/JWKS desplegado no se probó; todos los JWT y JWKS
  de la suite son ficticios y locales.
- La cobertura no alcanza todas las ramas posibles de `security.py` ni la rama
  de fila ausente en `repositories.py`; las cifras se muestran sin ocultar esas
  partes.

### Pruebas propuestas, no ejecutadas

Después de acordar en H-API-04 la lista de extensiones y el límite en bytes,
agregar pruebas para extensión no permitida, nombre que intente salir del
directorio, tamaño exactamente en el límite y tamaño límite + 1. No se asigna
un valor de límite ni una lista provisional de extensiones.

## Documentos consultados

`README.md`, `RETO.md`, `docs/GOOD_PRACTICES.md`, `docs/ENDPOINTS.md`,
`HALLAZGOS.md`, `PLAN.md`, `api/pyproject.toml`, `api/app/main.py`,
`api/app/security.py`, `api/app/authorization.py`,
`api/app/repositories.py` y `api/tests/test_api.py`.
