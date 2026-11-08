"""Mapeo entre los roles de la app móvil y los valores que usa la plataforma web en usuarios.rol.

La web guarda 'user', 'organizacion' y 'admin' (VARCHAR); cambiar esos valores rompería la web,
por lo que la API expone el ENUM móvil y traduce al leer/escribir.
"""
import enum


class Rol(str, enum.Enum):
    VOLUNTARIO = "VOLUNTARIO"
    TUTOR = "TUTOR"
    ADMIN = "ADMIN"


_WEB_TO_MOBILE = {
    "user": Rol.VOLUNTARIO,
    "usuario": Rol.VOLUNTARIO,
    "voluntario": Rol.VOLUNTARIO,
    "organizacion": Rol.TUTOR,
    "tutor": Rol.TUTOR,
    "admin": Rol.ADMIN,
}

ROL_TO_WEB = {
    Rol.VOLUNTARIO: "user",
    Rol.TUTOR: "organizacion",
    Rol.ADMIN: "admin",
}

WEB_ROLES_VOLUNTARIO = ("user", "usuario", "voluntario")


def rol_from_web(value: str | None) -> Rol:
    if not value:
        return Rol.VOLUNTARIO
    return _WEB_TO_MOBILE.get(value.strip().lower(), Rol.VOLUNTARIO)
