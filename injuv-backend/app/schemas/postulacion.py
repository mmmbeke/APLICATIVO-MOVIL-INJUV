from datetime import datetime
from typing import Literal

from pydantic import BaseModel

from app.core.estados import EstadoPostulacion
from app.schemas.common import ORMModel


class PostulacionOut(ORMModel):
    id: int
    usuario_id: int
    oportunidad_id: int
    estado: EstadoPostulacion
    fecha_postulacion: datetime | None


class MiPostulacionOut(PostulacionOut):
    oportunidad_titulo: str


class PostulanteUsuario(ORMModel):
    id: int
    nombre: str | None
    apellido: str | None
    email: str | None
    telefono: str | None
    rut: str | None


class PostulanteOut(PostulacionOut):
    usuario: PostulanteUsuario
    asistio: bool | None = None


class EstadoUpdate(BaseModel):
    estado: Literal[EstadoPostulacion.SELECCIONADO, EstadoPostulacion.RECHAZADO]
