from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import urlsplit

import jwt
from fastapi import Header, HTTPException
from jwt.exceptions import PyJWKClientConnectionError, PyJWTError

JWT_ALGORITHM = "RS256"
JWT_ISSUER_SETTING = "jwt_iss"
JWT_AUDIENCE_SETTING = "jwt_aud"
JWKS_ENDPOINT_SETTING = "jwks_endpoint"
JWKS_REQUEST_TIMEOUT_SECONDS = 5
JWKS_CLIENT_CACHE_SIZE = 1
REQUIRED_JWT_CLAIMS = ("exp", "iss", "aud", "sub", "role")
LOCAL_HTTP_HOSTS = {"localhost", "127.0.0.1", "::1"}


@dataclass(frozen=True)
class JwtSettings:
    issuer: str
    audience: str
    jwks_endpoint: str


class TokenConfigurationError(ValueError):
    pass


@lru_cache(maxsize=JWKS_CLIENT_CACHE_SIZE)
def get_jwks_client(endpoint: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(endpoint, timeout=JWKS_REQUEST_TIMEOUT_SECONDS)


def verified_identity(authorization: str = Header(default="")) -> dict[str, str]:
    token = _extract_bearer_token(authorization)
    try:
        settings = _read_jwt_settings()
    except TokenConfigurationError as error:
        raise HTTPException(status_code=503, detail="Token verification is not configured") from error

    try:
        signing_key = get_jwks_client(settings.jwks_endpoint).get_signing_key_from_jwt(token).key
        claims = jwt.decode(
            token,
            signing_key,
            algorithms=[JWT_ALGORITHM],
            issuer=settings.issuer,
            audience=settings.audience,
            options={"require": list(REQUIRED_JWT_CLAIMS)},
        )
    except PyJWKClientConnectionError as error:
        raise HTTPException(status_code=503, detail="Token verification is unavailable") from error
    except PyJWTError as error:
        raise HTTPException(status_code=401, detail="Invalid token") from error

    username = claims.get("sub")
    role = claims.get("role")
    if not isinstance(username, str) or not username or not isinstance(role, str) or not role:
        raise HTTPException(status_code=401, detail="Invalid token")
    return {"username": username, "role": role}


def _extract_bearer_token(authorization: str) -> str:
    scheme, separator, token = authorization.partition(" ")
    if scheme != "Bearer" or not separator or not token.strip():
        raise HTTPException(status_code=401, detail="Invalid token")
    return token.strip()


def _read_jwt_settings() -> JwtSettings:
    issuer = _required_setting(JWT_ISSUER_SETTING)
    audience = _required_setting(JWT_AUDIENCE_SETTING)
    jwks_endpoint = _required_setting(JWKS_ENDPOINT_SETTING)
    _validate_jwks_endpoint(jwks_endpoint)
    return JwtSettings(issuer, audience, jwks_endpoint)


def _required_setting(setting_name: str) -> str:
    value = os.getenv(setting_name, "").strip()
    if not value:
        raise TokenConfigurationError(f"Missing required setting: {setting_name}")
    return value


def _validate_jwks_endpoint(endpoint: str) -> None:
    try:
        parsed_endpoint = urlsplit(endpoint)
    except ValueError as error:
        raise TokenConfigurationError("Invalid JWKS endpoint") from error
    if not parsed_endpoint.hostname or parsed_endpoint.scheme not in {"https", "http"}:
        raise TokenConfigurationError("Invalid JWKS endpoint")
    if parsed_endpoint.scheme == "http" and parsed_endpoint.hostname not in LOCAL_HTTP_HOSTS:
        raise TokenConfigurationError("JWKS endpoint must use HTTPS")
