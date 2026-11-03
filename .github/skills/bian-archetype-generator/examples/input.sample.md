## Contexto de negocio (breve)
Estandarizar la creación de nuevos microservicios bancarios alineados al estándar BIAN
para reducir el tiempo de arranque de proyectos y asegurar consistencia entre equipos.

## Service Domain BIAN
- Nombre: Current Account
- Business Area: Retail Banking
- Business Domain: Deposits and Borrowings
- Functional Pattern: Fulfill
- Asset Type: Current Account Fulfillment Arrangement
- Versión BIAN de referencia: 12.0

## Control Record y Behavior Qualifiers
- Control Record (CR): Current Account Fulfillment Arrangement
- Behavior Qualifiers (BQ): Deposit, Withdrawal, Account Status

## Service Operations (acciones BIAN)
| Acción BIAN | Operación REST esperada | Incluida |
|-------------|-------------------------|----------|
| Initiate    | POST /current-account/{cr-reference-id}/initiation | Sí |
| Retrieve    | GET /current-account/{cr-reference-id}/retrieval | Sí |
| Update      | PUT /current-account/{cr-reference-id}/update | Sí |
| Control     | PUT /current-account/{cr-reference-id}/control | Sí |
| Execute     | PUT /current-account/{cr-reference-id}/execution | No |

## Stack tecnológico
- Lenguaje / framework: Java 21 + Quarkus 3
- Build: Maven
- Persistencia: PostgreSQL (acceso mediante repositorio, sin SQL en la capa API)
- Contrato API: OpenAPI 3.0 (contract-first)
- Contenedores: Docker

## Arquitectura y estructura esperada
- Capas: api (recursos REST) / service (reglas de negocio) / repository (datos) / security.
- Paquete base: com.bcp.bian.currentaccount
- Mapeo de nombres BIAN a paquetes y clases (CR, BQ y acciones visibles en el código).
- Un servicio por Service Domain.

## Alcance (dentro / fuera)
Dentro: estructura del proyecto, controladores con las operaciones indicadas, DTOs a partir del
contrato OpenAPI, capas vacías con interfaces, configuración base, Dockerfile y pruebas de humo.
Fuera: lógica de negocio real, infraestructura cloud, pipelines de despliegue y diseño de UI.

## Restricciones técnicas conocidas
Logging estandarizado sin datos sensibles; configuración y credenciales solo por variables de
entorno; sin secretos reales; sin dependencias nuevas fuera de las listadas sin justificación.

## Requisitos no funcionales
- Seguridad: OAuth2/JWT en todos los endpoints; autorización ligada a la identidad.
- Observabilidad: health checks, métricas y trazabilidad (correlation-id).
- Cobertura de pruebas del código generado: 85% o superior.

## Riesgos conocidos
Mapeo incorrecto del Service Domain o de sus acciones; exposición de datos sensibles en logs;
divergencia entre el contrato OpenAPI y la implementación.

## Dependencias
Catálogo BIAN del Service Landscape, servicio de identidad (OAuth2) y base de datos PostgreSQL.

## Definition of Done (DoD) del equipo
El proyecto compila, las pruebas pasan, el README describe el mapeo BIAN, el contrato OpenAPI es
válido y el cambio está revisado por pares.
