from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from pydantic import BaseModel


class JwtClaims(BaseModel):
    sub: str
    role: str
    iss: str
    aud: str
    iat: int
    exp: int


def create_access_token(*, subject: str, role: str, secret: str, issuer: str, audience: str, ttl_seconds: int) -> str:
    now = datetime.now(timezone.utc)
    payload: dict[str, Any] = {
        "sub": subject,
        "role": role,
        "iss": issuer,
        "aud": audience,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl_seconds)).timestamp()),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def decode_token(*, token: str, secret: str, issuer: str, audience: str) -> JwtClaims:
    try:
        payload = jwt.decode(token, secret, algorithms=["HS256"], issuer=issuer, audience=audience)
        return JwtClaims.model_validate(payload)
    except JWTError as e:
        raise ValueError("invalid_token") from e

