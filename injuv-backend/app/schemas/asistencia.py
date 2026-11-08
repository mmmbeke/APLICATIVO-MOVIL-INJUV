from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import ORMModel


class AsistenciaItem(BaseModel):
    postulacion_id: int
    asistio: bool


class AsistenciaOut(ORMModel):
    id: int
    postulacion_id: int
    tutor_id: int | None
    asistio: bool
    fecha_marcaje: datetime
