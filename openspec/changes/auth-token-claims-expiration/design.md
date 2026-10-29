# Design

## Context

See `proposal.md` for motivation and `specs/auth-token-claims-expiration/spec.md` for the behavior contract.

`auth/` is a Quarkus 3.27.4 / Java 21 service. `AuthResource.login` currently validates request fields, queries `LegacyDatabase`, creates a token, and builds the response in one method. `LoginRequest` already has a `client` field, but the route does not use it. `LegacyTokenUtil` returns Base64-encoded text containing a username, role, expiry, and a hard-coded value; this is not a signed JWT. `AuthResourceTest` currently checks only a successful login, the username, and a non-null token. There is no JWT dependency or token-specific configuration in `auth/`.

The protected consumer contract in `docs/ENDPOINTS.md` requires RS256, configured issuer/audience/JWKS, and `exp`, `iss`, `aud`, `sub`, and `role`; invalid or expired tokens produce HTTP 401. The current repository implementation does not meet that contract. The design preserves the login response contract while producing a token compatible with the documented consumer policy; it does not change `api/`.

## Goals / Non-Goals

**Goals:**
- Keep the successful login status and response fields `token`, `expiresIn`, and `user`, and keep invalid credentials at HTTP 401.
- Validate and bind the request's non-blank `client` value to a signed token.
- Use a verifiable JWT with the claims and expiry semantics in the approved spec, including consumer-required claims.
- Require deployment-provided signing material outside the laboratory and keep token/key material out of logs.
- Make the authentication flow and token creation independently testable without changing persistence.

**Non-Goals:**
- Change `api/`, `web/`, routes, consumer error formats, the user database, credential storage, or roles.
- Add a client allowlist, token refresh/revocation, a new JWKS endpoint, key rotation service, or configurable token lifetime.
- Clean up unrelated legacy database, exception-response, or debug behavior.

## Contratos protegidos

- `POST /auth/login` remains the endpoint. A valid login returns HTTP 200 with `token`, `expiresIn`, and `user`; the current `user` fields (`username`, `displayName`, `role`) remain unchanged.
- Invalid credentials remain HTTP 401. Missing or blank `client` is rejected with HTTP 400, consistent with the route's existing request-validation status.
- Preserve the current one-hour token lifetime. Compute `iat`, `exp`, and `expiresIn` from one time source so the response value differs from `exp - now` by no more than the spec's one-second tolerance.
- The signed token includes the requested `sub`, `client`, `iat`, and `exp` claims as well as `iss`, `aud`, and `role` required by the documented API verifier. `client` is trimmed before it is put in the claim.
- The API's documented RS256/JWKS verification and its HTTP 401 behavior for invalid or expired tokens are not changed.

## Componentes afectados

- `AuthResource`: retain the HTTP boundary and response mapping; delegate authentication and token creation rather than adding more security logic to the route.
- `LoginRequest`: use the existing `client` field and validate it at the request boundary.
- A focused authentication service: coordinate credential lookup and token creation while leaving `LegacyDatabase` and its data model unchanged.
- A token service replacing `LegacyTokenUtil`: create and sign the JWT, centralize the one-hour lifetime, and use an injectable `Clock` for deterministic expiry tests.
- `auth/src/main/resources/application.properties`: map deployment configuration to the signing library without embedding key material or supplying a production default.
- `auth/src/test`: extend `AuthResourceTest` and add focused token/configuration tests. No source or tests in `api/` or `web/` are included.

## Decisions

### Use RS256 JWT signing through Quarkus SmallRye JWT Build

**Decision:** Add the Quarkus `quarkus-smallrye-jwt-build` extension, managed by the existing Quarkus BOM, and issue RS256 JWTs. Resolve the signing-key reference from `AUTH_TOKEN_SECRET`; outside the laboratory it identifies a mounted PEM private-key file, not inline source or a fallback value. Configure issuer and audience from deployment values that match the existing API verifier, and coordinate publication of the matching public key through the already-configured JWKS endpoint. Do not add a JWKS endpoint to `auth/`.

**Rationale:** The approved spec requires compatibility with the documented API consumer, which verifies RS256 via JWKS. The Issue body mentions HMAC, but HMAC cannot satisfy that verifier contract without changing `api/`, which is outside scope. The actual `auth/` implementation is Base64 encoding with a fixed value, not HMAC; preserving that format would also fail the signed-token contract.

**Alternatives considered:**
- HMAC-signed JWT using `AUTH_TOKEN_SECRET`: closer to the Issue's description, but incompatible with the consumer's documented RS256/JWKS policy.
- Continue the existing Base64 format: no library or configuration change, but it is not a signed JWT and cannot satisfy the approved claims or verification requirements.
- Hand-build JWT serialization and RS256 signing with JCA: avoids a library dependency but duplicates security-sensitive encoding and signing behavior already provided by the Quarkus JWT extension.

### Make missing production signing configuration fail closed

**Decision:** Do not provide a production default. Production startup requires `AUTH_TOKEN_SECRET` to resolve to usable signing material and requires issuer/audience values. Keep isolated test key material only in test resources; do not add real or production key material to the repository.

**Rationale:** Failing configuration early prevents successful-looking login responses that cannot be verified. Treating the environment variable as a protected key-file reference avoids placing a private key in `application.properties` or ordinary environment dumps.

**Alternative considered:** Continue with a sample/default key when configuration is absent. Rejected because it allows issuance with known or unintended signing material.

### Separate token creation while preserving the existing route boundary

**Decision:** Keep the change limited to the login flow: request validation and HTTP response remain at the resource boundary; a small service coordinates the existing credential lookup and a dedicated token service. Do not refactor `LegacyDatabase`.

**Rationale:** The route currently combines unrelated responsibilities, and separating only the new token policy makes signing/configuration testable without turning this issue into a persistence rewrite.

**Alternative considered:** Replace the entire authentication/database structure. Rejected as broader than the approved behavior and harder to review or roll back.

### Derive all time fields from one clock instant

**Decision:** Use an injected `Clock` and a named one-hour lifetime. Derive `iat` and `exp` from the same issuance instant and calculate `expiresIn` from the expiry at response construction.

**Rationale:** A shared time source avoids drift between token claims and response metadata and makes the one-second tolerance testable at expiry boundaries.

**Alternative considered:** Call the system clock independently for token and response values. Rejected because execution delay can produce avoidable discrepancies and flaky tests.

## Estrategia incremental

1. Add characterization coverage against the current route before replacing token behavior: successful status and response fields, existing `user` fields, invalid-credential status, and existing missing-username/password validation statuses. Do not assert or preserve the current Base64 token contents.
2. Add token-focused tests using a fixed `Clock` and an isolated RSA test key. Verify signature/claims, subject and role mapping, trimmed client, one-hour expiry, and `expiresIn` tolerance.
3. Add client validation and delegate token creation from the route. Keep the existing credential lookup and response mapping intact.
4. Add production configuration with no fallback, test the missing-key configuration path, and capture logs for successful and failed logins to assert that token and private-key material are absent.
5. Run the auth component's tests and inspect the resulting JWT against the issuer/audience/JWKS values documented for its deployment. Do not modify or run tests under other components as part of this change.

The repository's API contract says expired tokens receive HTTP 401, but the auth component does not validate inbound tokens. Auth-only tests can verify signing, claims, and expiry boundaries; they cannot prove the live API's 401 behavior. That consumer behavior remains unchanged and is not implemented or tested by changing `api/` in this scope.

## Pruebas necesarias

- Characterize existing `POST /auth/login` success shape and `user` fields, invalid credentials (401), and missing username/password (400) before refactoring.
- Verify a valid login yields a cryptographically verifiable RS256 JWT with non-empty `sub`/`client`, numeric `iat`/`exp`, `iss`/`aud`/`role`, and `exp > iat`.
- Verify missing/blank client returns 400 and issues no token; verify a non-blank client is trimmed and reflected in the claim.
- With a fixed clock, verify the retained 3600-second lifetime and `abs(expiresIn - (exp - now)) <= 1`.
- Verify production configuration without `AUTH_TOKEN_SECRET` cannot issue a token, while tests use only isolated key material.
- Capture auth logs for successful and failed requests and assert they do not contain the token or private-key contents.
- Verify an expired token is expired according to its `exp` claim using auth-side test fixtures; do not add API tests or change API behavior under this component scope.

## Riesgos / Trade-offs

- **[Signing format change invalidates assumptions of existing clients]** → Preserve the login response fields and coordinate issuer/audience/JWKS configuration before enabling JWT issuance; do not silently retain Base64 as a fallback.
- **[Private key unavailable or inconsistent with the configured JWKS]** → Fail closed when signing configuration is missing and verify a token against the deployed public-key metadata before rollout.
- **[Environment-specific configuration is currently undocumented in auth]** → Document required values and laboratory-only test configuration with the change; keep production key material outside the repository and image.
- **[One-second expiry tolerance is sensitive to observation timing]** → Derive fields from one injected clock and test with deterministic time rather than sleeps.
- **[The API's expired-token 401 cannot be tested within auth-only scope]** → Keep the existing consumer contract unchanged and record that live cross-component confirmation is outside this change, not simulate it by modifying API tests.
- **[Rollback to the repository's current Base64 issuer breaks the documented consumer contract]** → Roll back only to a release known to issue compatible RS256 tokens. Keep the matching public key available for at least the maximum token lifetime after issuance. If no compatible prior release exists, fail closed rather than re-enable Base64 issuance.

## Rollback

There is no database migration. Roll back the auth artifact and its configuration as one unit only to a previously verified RS256-compatible release. Keep any public key needed to verify already-issued tokens published until their maximum one-hour lifetime has elapsed. Do not remove a signing key while unexpired tokens signed with it may still be in use. The repository's current Base64 implementation is not a compatible rollback target for API consumers; if no compatible previous release is available, retain the JWT configuration and disable issuance rather than emit unverifiable tokens.

## Decisiones abiertas

No signing-algorithm decision remains open: RS256 is selected to preserve the approved API consumer contract. Deployment-specific issuer, audience, private-key reference, and JWKS URL values must be supplied by the environment and coordinated with the existing consumer configuration; this design does not prescribe production values or change other components.
