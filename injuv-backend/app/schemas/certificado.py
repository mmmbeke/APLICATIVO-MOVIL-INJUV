from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.common import ORMModel


class CertificadoCargar(BaseModel):
    usuario_id: int
    oportunidad_id: int
    url_pdf: HttpUrl
    horas_acreditadas: Decimal = Field(..., gt=0, le=9999, decimal_places=1)


class CertificadoOut(ORMModel):
    id: int
    usuario_id: int
    oportunidad_id: int
    oportunidad_titulo: str | None = None
    url_pdf: str
    horas_acreditadas: Decimal
    fecha_carga: datetime


class CertificadosResumen(BaseModel):
    total_horas: Decimal
    certificados: list[CertificadoOut]
