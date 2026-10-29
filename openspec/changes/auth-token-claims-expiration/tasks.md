# Tasks

## 1. Caracterizar el contrato actual de login

- [x] 1.1 En `auth/src/test`, ampliar `AuthResourceTest` para comprobar que un login válido responde HTTP 200 con `token`, `expiresIn` y los campos actuales de `user`; verificarlo ejecutando las pruebas de auth.
- [x] 1.2 Caracterizar credenciales inválidas como HTTP 401 sin token y username/password ausentes como HTTP 400; verificar los estados y la ausencia de token con pruebas de auth antes de cambiar el comportamiento funcional.

## 2. Añadir pruebas del contrato aprobado

- [x] 2.1 En pruebas de auth, comprobar que client ausente o en blanco responde HTTP 400 sin emitir token y que un client válido se recorta y se refleja en el claim; verificar ambos casos con pruebas de recurso.
- [x] 2.2 Añadir pruebas del token usando un `Clock` fijo y clave RSA aislada de pruebas: verificar firma RS256, `sub`, `client`, `iat`, `exp`, `iss`, `aud` y `role`, y que `exp` sea posterior a `iat`; ejecutar las pruebas de token.
- [ ] 2.3 Con el mismo reloj fijo, comprobar la vigencia de una hora, que `expiresIn` difiera de `exp - now` como máximo un segundo y que un token se considere expirado al alcanzar `exp`; verificar estos límites en auth sin esperas temporizadas ni pruebas del consumidor API.
- [ ] 2.4 Añadir pruebas de auth para la ausencia de configuración de firma fuera del laboratorio y para logs de login válido e inválido sin token ni material de clave; verificar el rechazo sin emitir token y la ausencia de valores sensibles en los logs capturados.

## 3. Implementar emisión y flujo de autenticación

- [x] 3.1 Incorporar la extensión Quarkus SmallRye JWT Build y la configuración de firma RS256, issuer y audience sin valores secretos por defecto; verificar que la configuración de auth compila y que no contiene material de firma incluido en el repositorio.
- [x] 3.2 Implementar un servicio de token con duración nominal de una hora, `Clock` inyectable y claims compatibles con la spec; verificar firma, claims y duración con las pruebas de token de 2.2 (la verificación de expiración de 2.3 sigue pendiente).
- [x] 3.3 Validar el client no vacío en el límite del login, recortarlo y delegar la autenticación y creación del token a servicios enfocados, manteniendo el endpoint y la respuesta exitosa actuales; verificar los casos de login y client de 1.1, 1.2 y 2.1.
- [x] 3.4 Exigir `AUTH_TOKEN_SECRET` y los valores de issuer/audience requeridos fuera del laboratorio, documentar su configuración y mantener las claves de prueba aisladas; verificar que la configuración ausente impide emitir tokens y que las pruebas usan solo material de prueba.
- [ ] 3.5 Asegurar que el flujo de login no registra tokens ni secretos; verificar con las pruebas de logs de 2.4 para solicitudes válidas e inválidas.

## 4. Validación del componente

- [ ] 4.1 Ejecutar `python tools/lab.py test auth` desde la raíz y resolver fallos del componente; confirmar que las pruebas de auth pasan y que la cobertura del código modificado alcanza al menos 85%.
- [ ] 4.2 Inspeccionar un JWT de prueba frente a la configuración documentada de issuer, audience y JWKS del consumidor, sin modificar ni ejecutar pruebas de `api/` o `web/`; registrar cualquier valor de despliegue pendiente sin incorporar secretos reales.