from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.roles import Rol
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import Usuario

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_V1_STR}/auth/token")

DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(db: DbSession, token: Annotated[str, Depends(oauth2_scheme)]) -> Usuario:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token inválido o expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError, TypeError):
        raise credentials_error
    user = db.get(Usuario, user_id)
    if user is None:
        raise credentials_error
    return user


CurrentUser = Annotated[Usuario, Depends(get_current_user)]


def require_roles(*roles: Rol) -> Callable[[Usuario], Usuario]:
    def checker(user: CurrentUser) -> Usuario:
        if user.rol not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acción permitida solo para: {', '.join(r.value for r in roles)}",
            )
        return user

    return checker


require_tutor = require_roles(Rol.TUTOR, Rol.ADMIN)
require_voluntario = require_roles(Rol.VOLUNTARIO)

TutorUser = Annotated[Usuario, Depends(require_tutor)]
VoluntarioUser = Annotated[Usuario, Depends(require_voluntario)]
