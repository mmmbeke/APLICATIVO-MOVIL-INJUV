from datetime import date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.roles import Rol, rol_from_web
from app.db.base import Base


class Usuario(Base):
    """Tabla `usuarios` de la web. Solo se agregan region_id y comuna_id."""

    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str | None] = mapped_column(String(100))
    apellido: Mapped[str | None] = mapped_column(String(100))
    rut: Mapped[str | None] = mapped_column(String(20))
    email: Mapped[str | None] = mapped_column(String(150))
    telefono: Mapped[str | None] = mapped_column(String(20))
    region: Mapped[str | None] = mapped_column(String(100))
    ciudad: Mapped[str | None] = mapped_column(String(100))
    comuna: Mapped[str | None] = mapped_column(String(100))
    sexo: Mapped[str | None] = mapped_column(String(100))
    fecha_nacimiento: Mapped[date | None] = mapped_column(Date)
    password_hash: Mapped[str | None] = mapped_column(String(255))
    rol_web: Mapped[str | None] = mapped_column("rol", String(100))
    hora_voluntariado: Mapped[int | None] = mapped_column(Integer)
    organizacion_afiliada: Mapped[int | None] = mapped_column(Integer)
    foto_perfil: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime | None] = mapped_column(DateTime)
    region_id: Mapped[int | None] = mapped_column(Integer)
    comuna_id: Mapped[int | None] = mapped_column(Integer)

    @property
    def rol(self) -> Rol:
        return rol_from_web(self.rol_web)


class Organizacion(Base):
    __tablename__ = "organizaciones"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str | None] = mapped_column(String(100))
    id_usuario_org: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
    id_usuario_admin: Mapped[int | None] = mapped_column(ForeignKey("usuarios.id"))
