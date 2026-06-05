from fastapi import Depends, Header, HTTPException, status

from gate_shared.auth import decode_token

from .settings import settings


def get_current_claims(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing_bearer_token")
    token = authorization.split(" ", 1)[1].strip()
    try:
        return decode_token(token=token, secret=settings.jwt_secret, issuer=settings.jwt_issuer, audience=settings.jwt_audience)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")


def require_admin(claims=Depends(get_current_claims)):
    if claims.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return claims

