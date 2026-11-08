from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession, TutorUser
from app.core.estados import EstadoPostulacion
from app.models import Oportunidad, Postulacion
from app.schemas.oportunidad import OportunidadCreate, OportunidadDetalle, OportunidadResumen
from app.services import oportunidades as svc
from app.services.permisos import puede_gestionar

router = APIRouter()


def _detalle(db, user, op: Oportunidad) -> OportunidadDetalle:
    postulacion = db.scalars(
        select(Postulacion)
        .where(Postulacion.oportunidad_id == op.id, Postulacion.usuario_id == user.id)
        .order_by(Postulacion.id.desc())
        .limit(1)
    ).first()
    estado = postulacion.estado if postulacion else None
    ve_whatsapp = estado == EstadoPostulacion.SELECCIONADO or puede_gestionar(db, user, op)
    return OportunidadDetalle(
        **svc.a_resumen(op).model_dump(),
        requisitos=svc.parsear_requisitos(op.requisitos),
        horas_voluntariado=op.horas_voluntariado,
        organizacion_id=op.organizacion_id,
        tutor_id=op.tutor_id,
        creado_en=op.creado_en,
        cupos_ocupados=svc.contar_seleccionados(db, op.id),
        whatsapp_grupo_url=op.whatsapp_grupo_url if ve_whatsapp else None,
        mi_postulacion_id=postulacion.id if postulacion else None,
        mi_postulacion_estado=estado,
    )


@router.post("", response_model=OportunidadDetalle, status_code=status.HTTP_201_CREATED)
def crear_oportunidad(data: OportunidadCreate, user: TutorUser, db: DbSession) -> OportunidadDetalle:
    """Crea una oportunidad y notifica (ACTIVIDAD_CREADA) a los voluntarios de la región."""
    op = svc.crear_oportunidad(db, user, data)
    return _detalle(db, user, op)


@router.get("", response_model=list[OportunidadResumen])
def listar_oportunidades(
    _: CurrentUser,
    db: DbSession,
    region_id: Annotated[int | None, Query(ge=1)] = None,
    comuna_id: Annotated[int | None, Query(ge=1)] = None,
    categoria: Annotated[str | None, Query(max_length=100)] = None,
    incluir_pasadas: bool = False,
    skip: Annotated[int, Query(ge=0)] = 0,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> list[OportunidadResumen]:
    """Oportunidades activas ordenadas por la próxima fecha de inicio (más cercana primero)."""
    return svc.listar_oportunidades(db, region_id, comuna_id, categoria, incluir_pasadas, skip, limit)


@router.get("/{oportunidad_id}", response_model=OportunidadDetalle)
def obtener_oportunidad(oportunidad_id: int, user: CurrentUser, db: DbSession) -> OportunidadDetalle:
    op = db.get(Oportunidad, oportunidad_id)
    if op is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Oportunidad no encontrada")
    return _detalle(db, user, op)
