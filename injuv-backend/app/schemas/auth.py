import re
from datetime import date

from pydantic import BaseModel, EmailStr, Field, field_validator

from app.core.roles import Rol
from app.schemas.common import ORMModel

_RUT_RE = re.compile(r"^\d{7,8}[0-9K]$")


def normalizar_rut(rut: str) -> str:
    return rut.replace(".", "").replace("-", "").replace(" ", "").upper()


class LoginRequest(BaseModel):
    identificador: str = Field(..., min_length=3, description="Email o RUT del usuario", examples=["voluntario@injuv.cl"])
    password: str = Field(..., min_length=1)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    rol: Rol


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    nombre: str = Field(..., min_length=1, max_length=100)
    apellido: str = Field(..., min_length=1, max_length=100)
    rut: str = Field(..., description="RUT con o sin puntos/guion", examples=["12.345.678-5"])
    telefono: str | None = Field(None, max_length=20)
    fecha_nacimiento: date | None = None
    region_id: int | None = Field(None, ge=1)
    comuna_id: int | None = Field(None, ge=1)
    region: str | None = Field(None, max_length=100, description="Nombre de la región (compatibilidad web)")
    comuna: str | None = Field(None, max_length=100, description="Nombre de la comuna (compatibilidad web)")

    @field_validator("email")
    @classmethod
    def _email_lower(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("rut")
    @classmethod
    def _rut_valido(cls, v: str) -> str:
        rut = normalizar_rut(v)
        if not _RUT_RE.match(rut):
            raise ValueError("RUT inválido")
        cuerpo, dv = rut[:-1], rut[-1]
        suma, factor = 0, 2
        for d in reversed(cuerpo):
            suma += int(d) * factor
            factor = 2 if factor == 7 else factor + 1
        resto = 11 - (suma % 11)
        esperado = "0" if resto == 11 else "K" if resto == 10 else str(resto)
        if dv != esperado:
            raise ValueError("RUT inválido (dígito verificador)")
        return rut


class UsuarioOut(ORMModel):
    id: int
    email: str | None
    nombre: str | None
    apellido: str | None
    rut: str | None
    telefono: str | None
    sexo: str | None
    fecha_nacimiento: date | None
    region: str | None
    comuna: str | None
    region_id: int | None
    comuna_id: int | None
    foto_perfil: str | None
    rol: Rol


class UsuarioUpdate(BaseModel):
    nombre: str | None = Field(None, min_length=1, max_length=100)
    apellido: str | None = Field(None, min_length=1, max_length=100)
    telefono: str | None = Field(None, max_length=20)
    sexo: str | None = Field(None, max_length=100)
    fecha_nacimiento: date | None = None
    region_id: int | None = Field(None, ge=1)
    comuna_id: int | None = Field(None, ge=1)
    region: str | None = Field(None, max_length=100)
    comuna: str | None = Field(None, max_length=100)
