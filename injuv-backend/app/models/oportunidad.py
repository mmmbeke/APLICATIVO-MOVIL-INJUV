from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Oportunidad(Base):
    """Tabla `oportunidades` compartida con la web.

    categoria, cupos_totales y creado_en apuntan a las columnas que ya usa la web
    (tipo_de_voluntariado, cupo_maximo, created_at) para que ambas plataformas vean lo mismo.
    """

    __tablename__ = "oportunidades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organizacion_id: Mapped[int | None] = mapped_column(Integer)
    tutor_id: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"))
    titulo: Mapped[str] = mapped_column(String(200))
    descripcion: Mapped[str] = mapped_column(Text)
    requisitos: Mapped[str | None] = mapped_column(Text)
    region_id: Mapped[int | None] = mapped_column(Integer)
    comuna_id: Mapped[int | None] = mapped_column(Integer)
    categoria: Mapped[str | None] = mapped_column("tipo_de_voluntariado", String(100))
    cupos_totales: Mapped[int | None] = mapped_column("cupo_maximo", Integer)
    whatsapp_grupo_url: Mapped[str | None] = mapped_column(String(500))
    estado: Mapped[str | None] = mapped_column(String(20))
    creado_en: Mapped[datetime | None] = mapped_column("created_at", DateTime)

    horas_voluntariado: Mapped[int | None] = mapped_column(Integer)
    fecha_inicio_voluntariado: Mapped[date | None] = mapped_column(Date)
    fecha_fin_voluntariado: Mapped[date | None] = mapped_column(Date)
    region_opor: Mapped[str | None] = mapped_column(String(255))
    comuna_opor: Mapped[str | None] = mapped_column(String(255))

    fechas: Mapped[list["OportunidadFecha"]] = relationship(
        back_populates="oportunidad",
        cascade="all, delete-orphan",
        order_by="OportunidadFecha.fecha_inicio",
        lazy="selectin",
    )


class OportunidadFecha(Base):
    __tablename__ = "oportunidad_fechas"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    oportunidad_id: Mapped[int] = mapped_column(ForeignKey("oportunidades.id", ondelete="CASCADE"))
    fecha_inicio: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    fecha_fin: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    oportunidad: Mapped[Oportunidad] = relationship(back_populates="fechas")
