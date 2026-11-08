from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession, TutorUser
from app.core.estados import TipoNotificacion
from app.models import Notificacion, Postulacion
from app.schemas.notificacion import MensajeMasivoIn, MensajeMasivoOut, NotificacionOut
from app.services.notificaciones import notificar
from app.services.permisos import get_oportunidad_gestionable

router = APIRouter()


@router.get("", response_model=list[NotificacionOut])
def listar_notificaciones(
    user: CurrentUser,
    db: DbSession,
    solo_no_leidas: bool = False,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
) -> list[Notificacion]:
    stmt = select(Notificacion).where(Notificacion.usuario_id == user.id)
    if solo_no_leidas:
        stmt = stmt.where(Notificacion.leido.is_(False))
    stmt = stmt.order_by(Notificacion.fecha_envio.desc(), Notificacion.id.desc()).offset(skip).limit(limit)
    return list(db.scalars(stmt))


@router.patch("/{notificacion_id}/leer", response_model=NotificacionOut)
def marcar_leida(notificacion_id: int, user: CurrentUser, db: DbSession) -> Notificacion:
    notificacion = db.get(Notificacion, notificacion_id)
    if notificacion is None or notificacion.usuario_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Notificación no encontrada")
    notificacion.leido = True
    db.commit()
    db.refresh(notificacion)
    return notificacion


@router.post("/mensaje-masivo", response_model=MensajeMasivoOut, status_code=status.HTTP_201_CREATED)
def mensaje_masivo(data: MensajeMasivoIn, user: TutorUser, db: DbSession) -> MensajeMasivoOut:
    """Envía un mensaje a todos los voluntarios SELECCIONADOS de una oportunidad."""
    op = get_oportunidad_gestionable(db, user, data.oportunidad_id)
    destinatarios = db.scalars(
        select(Postulacion.usuario_id).where(
            Postulacion.oportunidad_id == op.id, func.lower(Postulacion.estado_web) == "seleccionado"
        )
    ).all()
    enviadas = notificar(db, destinatarios, TipoNotificacion.MENSAJE_TUTOR, data.titulo, data.mensaje, op.id)
    db.commit()
    return MensajeMasivoOut(enviadas=enviadas)
