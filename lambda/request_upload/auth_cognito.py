import time
from functools import lru_cache
from typing import Any

import jwt
from jwt import PyJWKClient

from config import COGNITO_CLIENT_ID, COGNITO_REGION, COGNITO_USER_POOL_ID


class AuthError(Exception):
    def __init__(self, message: str, status_code: int = 401):
        super().__init__(message)
        self.status_code = status_code


ISSUER = (
    f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/{COGNITO_USER_POOL_ID}"
)
JWKS_URL = f"{ISSUER}/.well-known/jwks.json"


@lru_cache(maxsize=1)
def _jwk_client() -> PyJWKClient:
    return PyJWKClient(JWKS_URL)


def verify_bearer_token(authorization: str | None) -> dict[str, Any]:
    if not COGNITO_USER_POOL_ID or not COGNITO_CLIENT_ID:
        raise AuthError("Cognito is not configured", 500)
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthError("Missing Bearer token", 401)

    token = authorization.split(" ", 1)[1].strip()
    try:
        signing_key = _jwk_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=COGNITO_CLIENT_ID,
            issuer=ISSUER,
            options={"require": ["exp", "iss", "sub"]},
        )
    except jwt.PyJWTError as exc:
        raise AuthError(f"Invalid token: {exc}", 401) from exc

    if claims.get("exp", 0) < time.time():
        raise AuthError("Token expired", 401)

    return claims


def user_id_from_claims(claims: dict[str, Any]) -> str:
    return claims.get("sub") or claims.get("cognito:username") or "anonymous"
