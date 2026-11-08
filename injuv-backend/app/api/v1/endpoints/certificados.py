from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert

from app.api.deps import CurrentUser, DbSession, TutorUser
from app.core.estados import TipoNotificacion
from app.models import Certificado, Oportunidad, Postulacion
from app.schemas.certificado import CertificadoCargar, CertificadoOut, CertificadosResumen
from app.services.notificaciones import notificar
from app.services.permisos import get_oportunidad_gestionable

router = APIRouter()


@router.post("/cargar", response_model=CertificadoOut, status_code=status.HTTP_201_CREATED)
def cargar_certificado(data: CertificadoCargar, user: TutorUser, db: DbSession) -> CertificadoOut:
    """Adjunta (o reemplaza) el certificado de un voluntario seleccionado y lo notifica."""
    op = get_oportunidad_gestionable(db, user, data.oportunidad_id)
    seleccionado = db.scalar(
        select(func.count(Postulacion.id)).where(
            Postulacion.oportunidad_id == op.id,
            Postulacion.usuario_id == data.usuario_id,
            func.lower(Postulacion.estado_web) == "seleccionado",
        )
    )
    if not seleccionado:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST, "El voluntario no está SELECCIONADO en esta oportunidad"
        )

    stmt = insert(Certificado).values(
        usuario_id=data.usuario_id,
        oportunidad_id=op.id,
        url_pdf=str(data.url_pdf),
        horas_acreditadas=data.horas_acreditadas,
    )
    stmt = stmt.on_conflict_do_update(
        constraint="uq_certificados_usuario_oportunidad",
        set_={"url_pdf": stmt.excluded.url_pdf, "horas_acreditadas": stmt.excluded.horas_acreditadas, "fecha_carga": func.now()},
    ).returning(Certificado.id)
    certificado_id = db.scalar(stmt)

    notificar(
        db,
        [data.usuario_id],
        TipoNotificacion.CERTIFICADO_CARGADO,
        "Tu certificado está disponible",
        f"Se cargó tu certificado de \"{op.titulo}\" con {data.horas_acreditadas} horas acreditadas.",
        op.id,
    )
    db.commit()
    cert = db.get(Certificado, certificado_id, populate_existing=True)
    return CertificadoOut.model_validate(cert).model_copy(update={"oportunidad_titulo": op.titulo})


@router.get("", response_model=CertificadosResumen)
def mis_certificados(user: CurrentUser, db: DbSession) -> CertificadosResumen:
    rows = db.execute(
        select(Certificado, Oportunidad.titulo)
        .join(Oportunidad, Oportunidad.id == Certificado.oportunidad_id)
        .where(Certificado.usuario_id == user.id)
        .order_by(Certificado.fecha_carga.desc())
    ).all()
    certificados = [
        CertificadoOut.model_validate(c).model_copy(update={"oportunidad_titulo": titulo}) for c, titulo in rows
    ]
    total = sum((c.horas_acreditadas for c in certificados), Decimal("0"))
    return CertificadosResumen(total_horas=total, certificados=certificados)
