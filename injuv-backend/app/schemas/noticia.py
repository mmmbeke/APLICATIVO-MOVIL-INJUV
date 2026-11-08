from datetime import datetime

from pydantic import BaseModel


class NoticiaOut(BaseModel):
    id: int
    titulo: str
    bajada: str | None
    cuerpo: str
    imagen_url: str | None
    fecha_publicacion: datetime | None
