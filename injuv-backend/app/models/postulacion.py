from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.estados import EstadoPostulacion, postulacion_from_web
from app.db.base import Base
from app.models.oportunidad import Oportunidad
from app.models.usuario import Usuario


class Postulacion(Base):
    """Tabla `postulaciones` de la web. fecha_postulacion apunta a created_at."""

    __tablename__ = "postulaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    usuario_id: Mapped[int] = mapped_column(ForeignKey("usuarios.id"))
    oportunidad_id: Mapped[int] = mapped_column(ForeignKey("oportunidades.id"))
    estado_web: Mapped[str | None] = mapped_column("estado", String(50))
    estado_confirmacion: Mapped[str | None] = mapped_column(String(20))
    asistencia_capacitacion: Mapped[str | None] = mapped_column(String(20))
    asistencia_actividad: Mapped[str | None] = mapped_column(String(20))
    tiene_certificado: Mapped[bool | None] = mapped_column(Boolean)
    resena_org_publica: Mapped[bool | None] = mapped_column(Boolean)
    fecha_postulacion: Mapped[datetime | None] = mapped_column("created_at", DateTime)
    updated_at: Mapped[datetime | None] = mapped_column(DateTime)

    usuario: Mapped[Usuario] = relationship(lazy="joined")
    oportunidad: Mapped[Oportunidad] = relationship()
    asistencia: Mapped["AsistenciaTutor | None"] = relationship(
        back_populates="postulacion", uselist=False, lazy="selectin"
    )

    @property
    def estado(self) -> EstadoPostulacion:
        return postulacion_from_web(self.estado_web)


class AsistenciaTutor(Base):
    __tablename__ = "asistencias_tutor"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    postulacion_id: Mapped[int] = mapped_column(
        ForeignKey("postulaciones.id", ondelete="CASCADE"), unique=True
    )
    tutor_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    asistio: Mapped[bool] = mapped_column(Boolean)
    fecha_marcaje: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    postulacion: Mapped[Postulacion] = relationship(back_populates="asistencia")
