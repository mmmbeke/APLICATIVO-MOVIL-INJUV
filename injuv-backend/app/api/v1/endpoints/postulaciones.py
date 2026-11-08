from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from app.api.deps import DbSession, TutorUser, VoluntarioUser
from app.core.estados import ESTADOS_OPORTUNIDAD_ACTIVA, POSTULACION_TO_WEB, EstadoPostulacion, TipoNotificacion
from app.models import Oportunidad, Postulacion
from app.schemas.postulacion import EstadoUpdate, MiPostulacionOut, PostulacionOut, PostulanteOut
from app.services.notificaciones import notificar
from app.services.oportunidades import contar_seleccionados
from app.services.permisos import get_oportunidad_gestionable

router = APIRouter()


@router.get("/mias", response_model=list[MiPostulacionOut], summary="Postulaciones del voluntario autenticado")
def mis_postulaciones(user: VoluntarioUser, db: DbSession) -> list[MiPostulacionOut]:
    rows = db.execute(
        select(Postulacion, Oportunidad.titulo)
        .join(Oportunidad, Oportunidad.id == Postulacion.oportunidad_id)
        .where(Postulacion.usuario_id == user.id)
        .order_by(Postulacion.id.desc())
    ).all()
    return [
        MiPostulacionOut(**PostulacionOut.model_validate(p).model_dump(), oportunidad_titulo=titulo)
        for p, titulo in rows
    ]


@router.post("/{oportunidad_id}", response_model=PostulacionOut, status_code=status.HTTP_201_CREATED)
def postular(oportunidad_id: int, user: VoluntarioUser, db: DbSession) -> Postulacion:
    op = db.get(Oportunidad, oportunidad_id)
    if op is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Oportunidad no encontrada")
    if (op.estado or "").lower() not in ESTADOS_OPORTUNIDAD_ACTIVA:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La oportunidad no está abierta a postulaciones")
    ya_postulo = db.scalar(
        select(func.count(Postulacion.id)).where(
            Postulacion.oportunidad_id == oportunidad_id, Postulacion.usuario_id == user.id
        )
    )
    if ya_postulo:
        raise HTTPException(status.HTTP_409_CONFLICT, "Ya postulaste a esta oportunidad")

    ahora = datetime.now()
    postulacion = Postulacion(
        usuario_id=user.id,
        oportunidad_id=oportunidad_id,
        estado_web=POSTULACION_TO_WEB[EstadoPostulacion.PENDIENTE],
        estado_confirmacion="Pendiente",
        asistencia_capacitacion="No aplica",
        asistencia_actividad="No aplica",
        tiene_certificado=False,
        resena_org_publica=False,
        fecha_postulacion=ahora,
        updated_at=ahora,
    )
    db.add(postulacion)
    db.commit()
    db.refresh(postulacion)
    return postulacion


@router.get("/oportunidad/{oportunidad_id}", response_model=list[PostulanteOut])
def listar_postulantes(oportunidad_id: int, user: TutorUser, db: DbSession) -> list[PostulanteOut]:
    get_oportunidad_gestionable(db, user, oportunidad_id)
    postulaciones = db.scalars(
        select(Postulacion).where(Postulacion.oportunidad_id == oportunidad_id).order_by(Postulacion.id)
    ).all()
    return [
        PostulanteOut.model_validate(p).model_copy(update={"asistio": p.asistencia.asistio if p.asistencia else None})
        for p in postulaciones
    ]


@router.put("/{postulacion_id}/estado", response_model=PostulacionOut)
def cambiar_estado(postulacion_id: int, data: EstadoUpdate, user: TutorUser, db: DbSession) -> Postulacion:
    postulacion = db.get(Postulacion, postulacion_id)
    if postulacion is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Postulación no encontrada")
    op = get_oportunidad_gestionable(db, user, postulacion.oportunidad_id)

    anterior = postulacion.estado
    nuevo = EstadoPostulacion(data.estado)
    if anterior == nuevo:
        return postulacion
    if nuevo == EstadoPostulacion.SELECCIONADO and op.cupos_totales:
        if contar_seleccionados(db, op.id) >= op.cupos_totales:
            raise HTTPException(status.HTTP_409_CONFLICT, "No quedan cupos disponibles en esta oportunidad")

    postulacion.estado_web = POSTULACION_TO_WEB[nuevo]
    postulacion.updated_at = datetime.now()
    if nuevo == EstadoPostulacion.SELECCIONADO:
        notificar(
            db,
            [postulacion.usuario_id],
            TipoNotificacion.FUISTE_SELECCIONADO,
            "¡Fuiste seleccionado!",
            f"Fuiste seleccionado para \"{op.titulo}\". Revisa los detalles y el grupo de WhatsApp en la app.",
            op.id,
        )
    db.commit()
    db.refresh(postulacion)
    return postulacion
