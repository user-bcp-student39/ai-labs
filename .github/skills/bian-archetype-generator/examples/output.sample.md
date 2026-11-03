# BIAN Archetype: Current Account

## 1. Resumen
Arquetipo base del servicio **Current Account** (Retail Banking / Deposits and Borrowings,
patrón Fulfill, BIAN 12.0) en Java 21 + Quarkus 3. Incluye las acciones Initiate, Retrieve,
Update y Control; Execute queda fuera de alcance. Sin lógica de negocio.

## 2. Mapeo BIAN
| Concepto BIAN | Elemento en el código |
|---------------|-----------------------|
| Service Domain: Current Account | Paquete `com.bcp.bian.currentaccount` |
| Control Record: Current Account Fulfillment Arrangement | `CurrentAccountFulfillmentArrangement` (DTO/entidad) |
| BQ: Deposit, Withdrawal, Account Status | Sub-recursos `/deposit`, `/withdrawal`, `/account-status` |
| Initiate | `POST /current-account/{crReferenceId}/initiation` |
| Retrieve | `GET /current-account/{crReferenceId}/retrieval` |
| Update | `PUT /current-account/{crReferenceId}/update` |
| Control | `PUT /current-account/{crReferenceId}/control` |

## 3. Estructura del proyecto
```text
bian-current-account/
├── pom.xml
├── Dockerfile
├── README.md
└── src/
    ├── main/
    │   ├── java/com/bcp/bian/currentaccount/
    │   │   ├── api/CurrentAccountResource.java
    │   │   ├── api/dto/CurrentAccountFulfillmentArrangement.java
    │   │   ├── service/CurrentAccountService.java
    │   │   ├── repository/CurrentAccountRepository.java
    │   │   ├── security/CorrelationIdFilter.java
    │   │   └── BianConstants.java
    │   └── resources/
    │       ├── application.properties
    │       └── openapi/current-account.yaml
    └── test/java/com/bcp/bian/currentaccount/
        ├── api/CurrentAccountResourceTest.java
        └── service/CurrentAccountServiceTest.java
```

## 4. Contrato API (fragmento)
```yaml
openapi: 3.0.3
info:
  title: Current Account
  version: 0.1.0
paths:
  /current-account/{crReferenceId}/retrieval:
    get:
      operationId: retrieveCurrentAccount
      parameters:
        - { name: crReferenceId, in: path, required: true, schema: { type: string } }
      responses:
        "200": { description: Control Record recuperado }
        "404": { description: Referencia no encontrada }
  /current-account/initiation:
    post:
      operationId: initiateCurrentAccount
      responses:
        "201": { description: Control Record creado }
```

## 5. Esqueletos de código
```java
public final class BianConstants {
    public static final String BASE_PATH = "/current-account";
    public static final String CORRELATION_HEADER = "X-Correlation-Id";
    private BianConstants() {}
}

@Path(BianConstants.BASE_PATH)
public class CurrentAccountResource {
    private final CurrentAccountService service;

    public CurrentAccountResource(CurrentAccountService service) {
        this.service = service;
    }

    @GET
    @Path("/{crReferenceId}/retrieval")
    public CurrentAccountFulfillmentArrangement retrieve(@PathParam("crReferenceId") String crReferenceId) {
        return service.retrieve(crReferenceId);
    }
}

public interface CurrentAccountService {
    CurrentAccountFulfillmentArrangement retrieve(String crReferenceId);
}

public interface CurrentAccountRepository {
    Optional<CurrentAccountFulfillmentArrangement> findByReferenceId(String crReferenceId);
}
```

## 6. Configuración base
- Variables de entorno: `DB_URL`, `DB_USER`, `DB_PASSWORD`, `OIDC_AUTH_SERVER_URL` (sin valores reales en el repositorio).
- Health y métricas habilitados (`/q/health`, `/q/metrics`).
- Logging estandarizado con `X-Correlation-Id`; sin datos sensibles.
- OAuth2/JWT requerido en todos los endpoints.

## 7. Supuestos
- Se usa el catálogo BIAN 12.0 tal como se indicó en la entrada.
- Las rutas REST siguen el patrón de la tabla de Service Operations de la entrada.

## 8. Riesgos y mitigaciones
- **Mapeo incorrecto de acciones BIAN:** revisión de arquitectura contra el Service Landscape y pruebas de contrato.
- **Exposición de datos sensibles en logs:** filtro de logging con enmascarado y prueba que verifica ausencia de campos sensibles.
- **Divergencia OpenAPI vs. implementación:** generación de DTOs desde el contrato y validación en CI.

## 9. Criterios de aceptación (medibles)
- `mvn verify` finaliza sin errores y el proyecto arranca con `/q/health` en `UP`.
- 4 de 4 acciones incluidas responden según el contrato OpenAPI (pruebas de contrato).
- Cobertura del código generado >= 85%.
- 0 secretos en el repositorio.

## 10. Plan de validación
- **Pruebas unitarias:** `CurrentAccountServiceTest` con repositorio simulado.
- **Pruebas funcionales:** `CurrentAccountResourceTest` por cada acción incluida.
- **Seguridad:** acceso sin token devuelve 401; un token de otra identidad no accede al recurso.
- **Evidencia requerida:** salida de `mvn verify`, reporte de cobertura y OpenAPI validado.

## 11. Preguntas abiertas
- ¿Cuál es el esquema de datos del Control Record en PostgreSQL?
- ¿Se requiere versionado de la API en la ruta (`/v1`)?
- ¿Qué proveedor OAuth2 aplica en cada ambiente?
