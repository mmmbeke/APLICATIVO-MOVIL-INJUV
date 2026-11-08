from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl, model_validator

from app.core.estados import EstadoPostulacion
from app.schemas.common import ORMModel


class FechaIn(BaseModel):
    fecha_inicio: datetime
    fecha_fin: datetime | None = None

    @model_validator(mode="after")
    def _rango(self):
        if self.fecha_fin and self.fecha_fin < self.fecha_inicio:
            raise ValueError("fecha_fin debe ser posterior o igual a fecha_inicio")
        return self


class FechaOut(ORMModel):
    id: int
    fecha_inicio: datetime
    fecha_fin: datetime | None


class OportunidadCreate(BaseModel):
    titulo: str = Field(..., min_length=3, max_length=200)
    descripcion: str = Field(..., min_length=1)
    requisitos: list[str] = Field(default_factory=list, description="Lista de requisitos")
    region_id: int = Field(..., ge=1)
    comuna_id: int = Field(..., ge=1)
    categoria: str = Field(..., min_length=1, max_length=100)
    cupos_totales: int = Field(..., ge=1)
    whatsapp_grupo_url: HttpUrl | None = None
    fechas: list[FechaIn] = Field(..., min_length=1)
    horas_voluntariado: int | None = Field(None, ge=0)
    region_nombre: str | None = Field(None, max_length=255, description="Nombre de la región (se muestra en la web)")
    comuna_nombre: str | None = Field(None, max_length=255, description="Nombre de la comuna (se muestra en la web)")
    organizacion_id: int | None = Field(
        None, description="Organización dueña. Si se omite se usa la organización del tutor."
    )


class OportunidadResumen(BaseModel):
    id: int
    titulo: str
    descripcion: str
    categoria: str | None
    region_id: int | None
    comuna_id: int | None
    region_nombre: str | None
    comuna_nombre: str | None
    cupos_totales: int | None
    estado: str | None
    proxima_fecha: datetime | None
    fechas: list[FechaOut]


class OportunidadDetalle(OportunidadResumen):
    requisitos: list[str]
    horas_voluntariado: int | None
    organizacion_id: int | None
    tutor_id: int | None
    creado_en: datetime | None
    cupos_ocupados: int
    whatsapp_grupo_url: str | None = Field(
        None, description="Solo visible para voluntarios SELECCIONADOS y para el tutor/admin"
    )
    mi_postulacion_id: int | None = None
    mi_postulacion_estado: EstadoPostulacion | None = None
