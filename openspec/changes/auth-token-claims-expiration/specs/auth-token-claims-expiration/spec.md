# Spec Delta

## Purpose

Define the observable login-token contract for identity, client attribution, expiration, and safe handling of signing configuration so downstream consumers can verify issued tokens.

## ADDED Requirements

### Requirement: Login preserves its successful response contract
Successful authentication MUST continue to return HTTP 200 with `token`, `expiresIn`, and `user`. Invalid credentials MUST continue to return HTTP 401.

#### Scenario: Successful login
- **WHEN** a caller submits valid credentials and a valid client
- **THEN** the response is HTTP 200 and contains `token`, `expiresIn`, and `user`

#### Scenario: Invalid credentials
- **WHEN** a caller submits credentials that do not authenticate a user
- **THEN** the response is HTTP 401 and no token is issued

### Requirement: Login validates and binds the requested client
The login request MUST contain a `client` string with non-whitespace content. The token's `client` claim MUST equal that value after trimming leading and trailing whitespace.

#### Scenario: Client is included in the token
- **WHEN** a caller submits valid credentials and a non-blank client
- **THEN** the returned token's `client` claim equals the trimmed request value

#### Scenario: Client is missing or blank
- **WHEN** a caller submits a login request without a client value or with only whitespace
- **THEN** the request is rejected with HTTP 400 and no token is issued

### Requirement: Issued tokens include required identity and time claims
An unexpired token returned by successful login MUST contain non-empty `sub` and `client` claims and numeric `iat` and `exp` claims where `exp` is later than `iat`. It MUST also remain compatible with the API consumer's documented verification contract, including its configured signature, issuer, audience, and required `exp`, `iss`, `aud`, `sub`, and `role` claims.

#### Scenario: Token has the required claims
- **WHEN** a caller successfully logs in
- **THEN** the token has non-empty `sub` and `client`, numeric `iat` and `exp`, and `exp` is later than `iat`

#### Scenario: Token remains valid for the documented consumer
- **WHEN** the API consumer verifies an unexpired token issued by a successful login using its documented configuration
- **THEN** verification succeeds and the token satisfies the consumer's configured signature, issuer, audience, and required-claim policy

### Requirement: Login expiration metadata matches token expiry
For a successful login response, `expiresIn` MUST be a positive number of seconds and differ from `exp - now` by no more than one second, where `now` is the current Unix time in seconds when the response is observed.

#### Scenario: Expiration metadata is coherent
- **WHEN** a caller observes a successful login response and decodes its token
- **THEN** `expiresIn` is positive and `abs(expiresIn - (exp - now))` is at most one second

### Requirement: Expired tokens remain unauthorized
At or after the token's `exp` time, the documented API consumer MUST reject the token with HTTP 401, preserving the existing authentication error contract.

#### Scenario: Consumer rejects an expired login token
- **WHEN** a caller presents an issued token at or after its `exp` time to the API consumer
- **THEN** the consumer responds with HTTP 401

### Requirement: Non-laboratory environments require configured signing material
Outside the laboratory, the authentication service MUST NOT issue tokens using an implicit or sample signing secret. `AUTH_TOKEN_SECRET` and its environment-specific requirements MUST be documented, and a missing required value MUST prevent token issuance.

#### Scenario: Required secret is absent outside the laboratory
- **WHEN** a login is attempted outside the laboratory without the required `AUTH_TOKEN_SECRET`
- **THEN** no token is issued

### Requirement: Sensitive authentication values are not logged
Authentication logs MUST NOT contain issued token values or signing-secret values during successful or failed login processing.

#### Scenario: Logs omit token and secret values
- **WHEN** successful and failed login requests are processed
- **THEN** captured authentication logs contain neither the issued token nor the configured signing secret
