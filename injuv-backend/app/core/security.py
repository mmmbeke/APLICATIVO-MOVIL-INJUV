from datetime import datetime, timedelta, timezone
from typing import Any

import jwt
from passlib.context import CryptContext
from werkzeug.security import check_password_hash, generate_password_hash

from app.core.config import settings
from app.core.roles import Rol

_bcrypt = CryptContext(schemes=["bcrypt"], deprecated="auto")

# La web (Flask/Werkzeug) valida contraseñas con check_password_hash, que no entiende bcrypt.
# Por defecto se generan hashes Werkzeug para que un usuario registrado desde la app
# también pueda iniciar sesión en la web. Se verifican ambos formatos.
_WERKZEUG_METHOD = "pbkdf2:sha256:600000"


def get_password_hash(password: str) -> str:
    if settings.PASSWORD_HASH_SCHEME == "bcrypt":
        return _bcrypt.hash(password)
    return generate_password_hash(password, method=_WERKZEUG_METHOD)


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    password_hash = password_hash.strip()
    try:
        if password_hash.startswith("$2"):
            return _bcrypt.verify(password, password_hash)
        return check_password_hash(password_hash, password)
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: int, rol: Rol, expires_minutes: int | None = None) -> str:
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes or settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "user_id": user_id,
        "rol": rol.value,
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
