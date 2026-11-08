from fastapi import APIRouter, Body, HTTPException, status
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.api.deps import DbSession, TutorUser
from app.core.estados import EstadoPostulacion
from app.models import AsistenciaTutor, Oportunidad, Postulacion
from app.schemas.asistencia import AsistenciaItem, AsistenciaOut
from app.services.permisos import puede_gestionar

router = APIRouter()


@router.post("/marcar-masivo", response_model=list[AsistenciaOut])
def marcar_masivo(
    user: TutorUser,
    db: DbSession,
    registros: list[AsistenciaItem] = Body(..., min_length=1, max_length=500),
) -> list[AsistenciaTutor]:
    """Registra la asistencia (marcaje manual del tutor) de voluntarios SELECCIONADOS."""
    ids = [r.postulacion_id for r in registros]
    if len(ids) != len(set(ids)):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "postulacion_id duplicado en la lista")

    postulaciones = {p.id: p for p in db.scalars(select(Postulacion).where(Postulacion.id.in_(ids)))}
    faltantes = sorted(set(ids) - postulaciones.keys())
    if faltantes:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Postulaciones no encontradas: {faltantes}")

    oportunidades = {
        o.id: o
        for o in db.scalars(
            select(Oportunidad).where(Oportunidad.id.in_({p.oportunidad_id for p in postulaciones.values()}))
        )
    }
    for op in oportunidades.values():
        if not puede_gestionar(db, user, op):
            raise HTTPException(status.HTTP_403_FORBIDDEN, f"No tienes permisos sobre la oportunidad {op.id}")
    no_seleccionadas = sorted(pid for pid, p in postulaciones.items() if p.estado != EstadoPostulacion.SELECCIONADO)
    if no_seleccionadas:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Solo se puede marcar asistencia de postulaciones SELECCIONADAS: {no_seleccionadas}",
        )

    stmt = insert(AsistenciaTutor).values(
        [{"postulacion_id": r.postulacion_id, "tutor_id": user.id, "asistio": r.asistio} for r in registros]
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[AsistenciaTutor.postulacion_id],
        set_={"asistio": stmt.excluded.asistio, "tutor_id": stmt.excluded.tutor_id, "fecha_marcaje": stmt.excluded.fecha_marcaje},
    ).returning(AsistenciaTutor.id)
    asistencia_ids = list(db.scalars(stmt))

    # Mantiene sincronizado el seguimiento que muestra el panel web de organizaciones ('Sí' / 'No').
    for r in registros:
        postulaciones[r.postulacion_id].asistencia_actividad = "Sí" if r.asistio else "No"

    db.commit()
    return list(
        db.scalars(
            select(AsistenciaTutor)
            .where(AsistenciaTutor.id.in_(asistencia_ids))
            .order_by(AsistenciaTutor.postulacion_id)
            .execution_options(populate_existing=True)
        )
    )
