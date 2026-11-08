"""Creación de notificaciones en BD y punto de extensión para notificaciones push (FCM)."""
import logging
from collections.abc import Iterable

from sqlalchemy import func, insert, literal, or_, select
from sqlalchemy.orm import Session

from app.core.estados import TipoNotificacion
from app.core.roles import WEB_ROLES_VOLUNTARIO
from app.models import Notificacion, Usuario

logger = logging.getLogger(__name__)


def enviar_push(usuario_ids: Iterable[int], titulo: str, mensaje: str) -> None:
    """Hook para push real (p. ej. Firebase Cloud Messaging). Por ahora solo registra el evento."""
    ids = list(usuario_ids)
    if ids:
        logger.info("push pendiente de integrar: %s destinatarios - %s", len(ids), titulo)


def notificar(
    db: Session,
    usuario_ids: Iterable[int],
    tipo: TipoNotificacion,
    titulo: str,
    mensaje: str,
    oportunidad_id: int | None = None,
) -> int:
    ids = sorted(set(usuario_ids))
    if not ids:
        return 0
    db.execute(
        insert(Notificacion),
        [
            {
                "usuario_id": uid,
                "tipo": tipo.value,
                "titulo": titulo,
                "mensaje": mensaje,
                "oportunidad_id": oportunidad_id,
            }
            for uid in ids
        ],
    )
    enviar_push(ids, titulo, mensaje)
    return len(ids)


def notificar_voluntarios_region(
    db: Session,
    region_id: int,
    tipo: TipoNotificacion,
    titulo: str,
    mensaje: str,
    oportunidad_id: int | None = None,
) -> int:
    voluntarios = (
        select(
            Usuario.id,
            literal(tipo.value),
            literal(titulo),
            literal(mensaje),
            literal(oportunidad_id),
        )
        .where(Usuario.region_id == region_id)
        .where(or_(Usuario.rol_web.is_(None), func.lower(Usuario.rol_web).in_(WEB_ROLES_VOLUNTARIO)))
    )
    result = db.execute(
        insert(Notificacion)
        .from_select(["usuario_id", "tipo", "titulo", "mensaje", "oportunidad_id"], voluntarios)
        .returning(Notificacion.usuario_id)
    )
    ids = list(result.scalars())
    enviar_push(ids, titulo, mensaje)
    return len(ids)
