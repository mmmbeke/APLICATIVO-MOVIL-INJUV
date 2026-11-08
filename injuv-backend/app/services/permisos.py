from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.roles import Rol
from app.models import Oportunidad, Organizacion, Usuario


def organizaciones_de(db: Session, user: Usuario) -> set[int]:
    ids = set(
        db.scalars(
            select(Organizacion.id).where(
                or_(Organizacion.id_usuario_org == user.id, Organizacion.id_usuario_admin == user.id)
            )
        )
    )
    if user.rol == Rol.TUTOR and user.organizacion_afiliada:
        ids.add(user.organizacion_afiliada)
    return ids


def puede_gestionar(db: Session, user: Usuario, oportunidad: Oportunidad) -> bool:
    if user.rol == Rol.ADMIN or oportunidad.tutor_id == user.id:
        return True
    if user.rol != Rol.TUTOR:
        return False
    return oportunidad.organizacion_id in organizaciones_de(db, user)


def get_oportunidad_gestionable(db: Session, user: Usuario, oportunidad_id: int) -> Oportunidad:
    oportunidad = db.get(Oportunidad, oportunidad_id)
    if oportunidad is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Oportunidad no encontrada")
    if not puede_gestionar(db, user, oportunidad):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permisos sobre esta oportunidad")
    return oportunidad
