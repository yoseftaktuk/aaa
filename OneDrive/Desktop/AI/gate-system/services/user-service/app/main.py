import logging

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from gate_shared.auth import create_access_token
from gate_shared.errors import AppError, ErrorResponse
from gate_shared.logging import configure_logging

from .db import engine, get_db
from .deps import get_current_claims, require_admin
from .models import Base, User
from .schemas import (
    TokenResponse,
    UpdateProfileRequest,
    UserCreateRequest,
    UserLoginRequest,
    UserResponse,
)
from .security import hash_password, verify_password
from .settings import settings

logger = logging.getLogger(__name__)

app = FastAPI(
    title="User Service",
    version="0.1.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)


@app.on_event("startup")
async def startup() -> None:
    configure_logging(settings.service_name, settings.log_level)
    # lightweight schema bootstrap for starter (production: replace with Alembic migrations)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("startup_complete")


@app.exception_handler(AppError)
async def app_error_handler(_, exc: AppError):
    return JSONResponse(
        status_code=exc.http_status,
        content=ErrorResponse(code=exc.code, message=exc.message, details=exc.details).model_dump(),
    )


@app.get("/healthz")
async def healthz():
    return {"status": "ok", "service": settings.service_name}


@app.post(
    "/auth/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    responses={400: {"model": ErrorResponse}},
)
async def register(req: UserCreateRequest, db: AsyncSession = Depends(get_db)):
    existing = await db.scalar(select(User).where(User.email == req.email))
    if existing:
        raise AppError(code="email_taken", message="Email already registered", http_status=400)
    user = User(email=req.email, password_hash=hash_password(req.password), full_name=req.full_name, role="user", is_active=True)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user, from_attributes=True)


@app.post(
    "/auth/login",
    response_model=TokenResponse,
    responses={401: {"model": ErrorResponse}},
)
async def login(req: UserLoginRequest, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(User.email == req.email))
    if not user or not verify_password(req.password, user.password_hash) or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_credentials")
    access = create_access_token(
        subject=str(user.id),
        role=user.role,
        secret=settings.jwt_secret,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        ttl_seconds=settings.jwt_access_ttl_seconds,
    )
    refresh = create_access_token(
        subject=str(user.id),
        role=user.role,
        secret=settings.jwt_secret,
        issuer=settings.jwt_issuer,
        audience=settings.jwt_audience,
        ttl_seconds=settings.jwt_refresh_ttl_seconds,
    )
    return TokenResponse(access_token=access, refresh_token=refresh)


@app.get("/me", response_model=UserResponse)
async def me(claims=Depends(get_current_claims), db: AsyncSession = Depends(get_db)):
    user = await db.get(User, claims.sub)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")
    return UserResponse.model_validate(user, from_attributes=True)


@app.patch("/me", response_model=UserResponse)
async def update_me(req: UpdateProfileRequest, claims=Depends(get_current_claims), db: AsyncSession = Depends(get_db)):
    user = await db.get(User, claims.sub)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user_not_found")
    if req.full_name is not None:
        user.full_name = req.full_name
    await db.commit()
    await db.refresh(user)
    return UserResponse.model_validate(user, from_attributes=True)


@app.get("/admin/users", response_model=list[UserResponse], dependencies=[Depends(require_admin)])
async def list_users(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(User).order_by(User.created_at.desc()))).scalars().all()
    return [UserResponse.model_validate(u, from_attributes=True) for u in rows]

