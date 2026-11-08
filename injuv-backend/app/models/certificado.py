from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Certificado(Base):
    __tablename__ = "certificados"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id", ondelete="CASCADE"))
    oportunidad_id: Mapped[int] = mapped_column(ForeignKey("oportunidades.id", ondelete="CASCADE"))
    url_pdf: Mapped[str] = mapped_column(Text)
    horas_acreditadas: Mapped[float] = mapped_column(Numeric(6, 1))
    fecha_carga: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
