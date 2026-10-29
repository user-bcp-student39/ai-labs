# Proposal

## Why

Issue [#24](https://github.com/user-bcp-student39/ai-labs/issues/24) pide que los tokens de login expresen una identidad y una expiración verificables, que el cliente quede ligado a la solicitud y que no se expongan secretos en logs. Esto importa para que consumidores puedan validar la identidad y vigencia del token, y para evitar configuraciones inseguras fuera del laboratorio.

## What Changes

- Definir el contrato observable de los claims `sub`, `client`, `iat` y `exp`, y la relación verificable entre `expiresIn` y la expiración.
- Validar el `client` recibido en el login y exigir que su valor quede reflejado en el token.
- Precisar el manejo de credenciales inválidas, tokens expirados, configuración de `AUTH_TOKEN_SECRET` y logs sin valores sensibles.
- Preservar `POST /auth/login` y su respuesta exitosa con `token`, `expiresIn` y `user`; no cambiar rutas ni formatos documentados de la API consumidora.

**Alcance:** requisitos del componente `auth` para emisión y configuración del token, compatibilidad del contrato de login y protección de valores sensibles.

**Fuera de alcance:** cambios funcionales en `api/` o `web/`, nuevos endpoints, cambios de persistencia o de credenciales, y la selección de HMAC frente a una librería JWT u otra decisión técnica de firma.

**Comportamiento que se preserva:** el login exitoso mantiene los campos `token`, `expiresIn` y `user`. [docs/ENDPOINTS.md](../../../docs/ENDPOINTS.md) describe la política del consumidor API: no emite tokens, verifica tokens RS256 con emisor/audiencia/JWKS configurados, requiere `exp`, `iss`, `aud`, `sub` y `role`, y responde 401 ante un token inválido o expirado. La propuesta no cambia esos endpoints ni formatos; los claims nuevos son aditivos y el token emitido debe seguir siendo compatible con esa política.

El cuerpo de #24 contiene los criterios de HU-01, aunque el título visible del Issue se refiere a otro asunto. Además, el Issue describe la implementación como HMAC con `AUTH_TOKEN_SECRET`, mientras que el código de `auth/` observado codifica datos y un secreto fijo en Base64. Se toma el cuerpo y sus criterios como alcance comprometido; esta discrepancia queda registrada para resolverla en el diseño, sin escoger aquí un mecanismo de firma.

## Capabilities

### New Capabilities
- `auth-token-claims-expiration`: contrato de claims, expiración, compatibilidad de login y tratamiento de configuración/logs sensibles.

### Modified Capabilities
- Ninguna.

## Impact

- Componente objetivo: `auth/`, ruta existente `POST /auth/login`.
- Consumidor y baseline de compatibilidad: política de autenticación documentada en `docs/ENDPOINTS.md`; no se modifica `api/`.
- Configuración/documentación: `AUTH_TOKEN_SECRET`; no se incorporan secretos reales ni dependencias como parte de esta propuesta.
- Verificación futura: escenarios de login válido, credenciales inválidas, claims, expiración, secreto ausente fuera del laboratorio y logs redactados.
