---
name: bian-archetype-generator
description: Genera el arquetipo base de un proyecto alineado al estándar BIAN (Service Domain, Control Record, Behavior Qualifiers y Service Operations) a partir de una ficha de entrada, produciendo estructura, contrato API, esqueletos de capas, configuración y plan de validación.
---

# Skill: BIAN Archetype Generator

## 1) Metadata
- **Skill ID:** bian-archetype-generator
- **Version:** 0.1.0
- **Purpose:** Generar el arquetipo base (esqueleto) de un microservicio asociado a un Service Domain BIAN, con nombres, rutas y capas consistentes con el estándar.
- **Audience (roles):** Arquitectura, Tech Lead, Backend, QA, Cyber
- **When to use:** Al iniciar un nuevo servicio que implementa un Service Domain BIAN, antes de escribir lógica de negocio.
- **When NOT to use:** Cambios sobre servicios existentes, incidentes de producción o proyectos que no se alinean a BIAN.
- **Sensitive inputs:** No incluyas datos reales de clientes, credenciales, secretos, tokens ni URLs internas no autorizadas.
- **Expected output:** Markdown estructurado según la sección Output.

## 2) Inputs
Proporciona la información en este formato (ver `examples/input.sample.md`):

- **Contexto de negocio (breve):**
- **Service Domain BIAN:** nombre, Business Area, Business Domain, Functional Pattern, Asset Type y versión BIAN.
- **Control Record y Behavior Qualifiers:**
- **Service Operations:** acciones BIAN (Initiate, Retrieve, Update, Control, Execute, etc.) y operación REST esperada, indicando cuáles se incluyen.
- **Stack tecnológico:** lenguaje, framework, build, persistencia, contrato API, contenedores.
- **Arquitectura y estructura esperada:** capas y paquete base.
- **Alcance (dentro / fuera):**
- **Restricciones técnicas conocidas:**
- **Requisitos no funcionales:** seguridad, observabilidad, cobertura.
- **Riesgos conocidos:**
- **Dependencias:**
- **Definition of Done (DoD) del equipo:**

## 3) Output
Devuelve **solo** un documento Markdown con estas secciones:

1. **Resumen**
2. **Mapeo BIAN** (Service Domain, CR, BQ y acciones -> paquetes, clases y endpoints)
3. **Estructura del proyecto** (árbol de carpetas y archivos)
4. **Contrato API** (fragmento OpenAPI de las operaciones incluidas)
5. **Esqueletos de código** (recurso, servicio, repositorio y DTO, sin lógica de negocio)
6. **Configuración base** (variables de entorno, health, logging, seguridad)
7. **Supuestos**
8. **Riesgos y mitigaciones**
9. **Criterios de aceptación (medibles)**
10. **Plan de validación** (pruebas, seguridad, evidencia requerida)
11. **Preguntas abiertas**

## 4) Constraints
- No inventes requisitos: lo que falte en la entrada va en **Preguntas abiertas**.
- Respeta los nombres oficiales BIAN para Service Domain, CR, BQ y acciones; no los renombres.
- Incluye solo las Service Operations marcadas como incluidas.
- Separa las capas api / service / repository / security; sin SQL ni reglas de negocio en la capa API.
- No propongas herramientas ni dependencias fuera del stack indicado.
- No incluyas secretos ni datos reales; usa variables de entorno y valores de prueba.
- Sin valores mágicos: usa constantes con nombre para rutas, claves y tiempos.
- Los criterios de aceptación deben ser verificables y con métrica.
- Mantén la salida concisa; los esqueletos deben ser mínimos y compilables en intención, no implementaciones completas.

## 5) Validation Rules
La salida es válida si:
- Incluye todas las secciones definidas en Output.
- Cada acción BIAN incluida aparece en el mapeo, en el contrato API y en un esqueleto de recurso.
- El árbol del proyecto refleja las capas y el paquete base de la entrada.
- Tiene al menos 3 criterios de aceptación medibles, incluida la cobertura indicada.
- Incluye al menos 2 riesgos con mitigaciones.
- No contiene datos sensibles, secretos ni supuestos no declarados.

## 6) Evidence
Adjunta o referencia estos elementos en el PR o entrega:
- `SKILL.md` versionado.
- `examples/input.sample.md`.
- `examples/output.sample.md`.
- Tag de versión para el Skill, como `skill-bian-archetype-v0.1.0`.
