from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, or_, select

from app.api.deps import DbSession
from app.core.config import settings
from app.models import Noticia
from app.schemas.noticia import NoticiaOut

router = APIRouter()

_ESTADOS_OCULTOS = ("inactiva", "borrador")


def _imagen_url(archivo: str | None) -> str | None:
    if not archivo:
        return None
    if archivo.startswith(("http://", "https://")):
        return archivo
    return settings.NOTICIAS_IMAGEN_BASE_URL.rstrip("/") + "/" + archivo.lstrip("/")


def _out(n: Noticia) -> NoticiaOut:
    return NoticiaOut(
        id=n.id,
        titulo=n.titulo,
        bajada=n.bajada,
        cuerpo=n.cuerpo,
        imagen_url=_imagen_url(n.imagen_archivo),
        fecha_publicacion=n.fecha_publicacion or n.created_at,
    )


def _visibles():
    return select(Noticia).where(
        or_(Noticia.estado.is_(None), func.lower(Noticia.estado).not_in(_ESTADOS_OCULTOS))
    )


@router.get("", response_model=list[NoticiaOut])
def listar_noticias(
    db: DbSession,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[NoticiaOut]:
    stmt = (
        _visibles()
        .order_by(func.coalesce(Noticia.fecha_publicacion, Noticia.created_at).desc().nulls_last(), Noticia.id.desc())
        .offset(skip)
        .limit(limit)
    )
    return [_out(n) for n in db.scalars(stmt)]


@router.get("/{noticia_id}", response_model=NoticiaOut)
def obtener_noticia(noticia_id: int, db: DbSession) -> NoticiaOut:
    noticia = db.scalars(_visibles().where(Noticia.id == noticia_id)).first()
    if noticia is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Noticia no encontrada")
    return _out(noticia)
