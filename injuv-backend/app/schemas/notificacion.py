from datetime import datetime

from pydantic import BaseModel, Field

from app.core.estados import TipoNotificacion
from app.schemas.common import ORMModel


class NotificacionOut(ORMModel):
    id: int
    tipo: TipoNotificacion
    titulo: str
    mensaje: str
    oportunidad_id: int | None
    leido: bool
    fecha_envio: datetime


class MensajeMasivoIn(BaseModel):
    oportunidad_id: int
    titulo: str = Field(..., min_length=1, max_length=200)
    mensaje: str = Field(..., min_length=1, max_length=2000)


class MensajeMasivoOut(BaseModel):
    enviadas: int
