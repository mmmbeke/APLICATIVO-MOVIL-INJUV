from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.core.roles import ROL_TO_WEB, Rol
from app.core.security import create_access_token, get_password_hash, verify_password
from app.models import Usuario
from app.schemas.auth import LoginRequest, RegisterRequest, Token, UsuarioOut, UsuarioUpdate, normalizar_rut
from app.services.oportunidades import utcnow

router = APIRouter()

_CREDENCIALES_INVALIDAS = "Email/RUT o contraseña incorrectos"


def _buscar_usuario(db, identificador: str) -> Usuario | None:
    identificador = identificador.strip()
    if "@" in identificador:
        stmt = select(Usuario).where(func.lower(func.trim(Usuario.email)) == identificador.lower())
    else:
        rut_col = func.upper(func.replace(func.replace(Usuario.rut, ".", ""), "-", ""))
        stmt = select(Usuario).where(rut_col == normalizar_rut(identificador))
    return db.scalars(stmt.order_by(Usuario.id).limit(1)).first()


def _autenticar(db, identificador: str, password: str) -> Token:
    user = _buscar_usuario(db, identificador)
    if user is None or not verify_password(password.strip(), user.password_hash):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED, _CREDENCIALES_INVALIDAS, headers={"WWW-Authenticate": "Bearer"}
        )
    return Token(access_token=create_access_token(user.id, user.rol), user_id=user.id, rol=user.rol)


@router.post("/login", response_model=Token, summary="Login con email o RUT (JSON)")
def login(data: LoginRequest, db: DbSession) -> Token:
    return _autenticar(db, data.identificador, data.password)


@router.post("/token", response_model=Token, summary="Login OAuth2 (formulario, usado por Swagger)")
def login_form(form: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession) -> Token:
    return _autenticar(db, form.username, form.password)


@router.post("/register", response_model=UsuarioOut, status_code=status.HTTP_201_CREATED)
def register(data: RegisterRequest, db: DbSession) -> Usuario:
    if db.scalar(select(Usuario.id).where(func.lower(func.trim(Usuario.email)) == data.email).limit(1)):
        raise HTTPException(status.HTTP_409_CONFLICT, "El email ya está registrado")
    rut_col = func.upper(func.replace(func.replace(Usuario.rut, ".", ""), "-", ""))
    if db.scalar(select(Usuario.id).where(rut_col == data.rut).limit(1)):
        raise HTTPException(status.HTTP_409_CONFLICT, "El RUT ya está registrado")

    user = Usuario(
        email=data.email,
        password_hash=get_password_hash(data.password),
        nombre=data.nombre.strip(),
        apellido=data.apellido.strip(),
        rut=data.rut,
        telefono=data.telefono,
        fecha_nacimiento=data.fecha_nacimiento,
        region_id=data.region_id,
        comuna_id=data.comuna_id,
        region=data.region,
        comuna=data.comuna,
        rol_web=ROL_TO_WEB[Rol.VOLUNTARIO],
        created_at=utcnow().replace(tzinfo=None),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/me", response_model=UsuarioOut)
def read_me(user: CurrentUser) -> Usuario:
    return user


@router.put("/me", response_model=UsuarioOut)
def update_me(data: UsuarioUpdate, user: CurrentUser, db: DbSession) -> Usuario:
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user
