from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Noticia(Base):
    """Tabla `noticias` de la web: bajada=resumen, cuerpo=contenido, imagen_url=imagen_noticia."""

    __tablename__ = "noticias"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    titulo: Mapped[str] = mapped_column(String(200))
    bajada: Mapped[str | None] = mapped_column("resumen", String(500))
    cuerpo: Mapped[str] = mapped_column("contenido", Text)
    imagen_archivo: Mapped[str | None] = mapped_column("imagen_noticia", String(500))
    estado: Mapped[str | None] = mapped_column(String(20))
    fecha_publicacion: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime | None] = mapped_column(DateTime)
