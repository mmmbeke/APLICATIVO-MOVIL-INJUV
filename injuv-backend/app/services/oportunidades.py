import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from sqlalchemy import DateTime, and_, cast, exists, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.estados import (
    ESTADO_OPORTUNIDAD_NUEVA,
    ESTADOS_OPORTUNIDAD_ACTIVA,
    TipoNotificacion,
)
from app.core.roles import Rol
from app.models import Oportunidad, OportunidadFecha, Postulacion, Usuario
from app.schemas.oportunidad import FechaOut, OportunidadCreate, OportunidadResumen
from app.services.notificaciones import notificar_voluntarios_region
from app.services.permisos import organizaciones_de

_TZ = ZoneInfo(settings.TIMEZONE)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _aware(dt: datetime) -> datetime:
    return dt.replace(tzinfo=_TZ) if dt.tzinfo is None else dt


def serializar_requisitos(requisitos: list[str]) -> str | None:
    limpios = [r.strip() for r in requisitos if r and r.strip()]
    return json.dumps(limpios, ensure_ascii=False) if limpios else None


def parsear_requisitos(valor: str | None) -> list[str]:
    if not valor:
        return []
    try:
        data = json.loads(valor)
        if isinstance(data, list):
            return [str(x) for x in data]
    except ValueError:
        pass
    return [line.strip() for line in valor.splitlines() if line.strip()]


def _resolver_organizacion(db: Session, user: Usuario, solicitada: int | None) -> int:
    if user.rol == Rol.ADMIN:
        if solicitada is None:
            propias = organizaciones_de(db, user)
            if not propias:
                raise HTTPException(status.HTTP_400_BAD_REQUEST, "Debes indicar organizacion_id")
            return min(propias)
        return solicitada
    propias = organizaciones_de(db, user)
    if solicitada is not None:
        if solicitada not in propias:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No perteneces a esa organización")
        return solicitada
    if not propias:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Tu usuario no tiene una organización asociada en la plataforma web",
        )
    return min(propias)


def crear_oportunidad(db: Session, user: Usuario, data: OportunidadCreate) -> Oportunidad:
    organizacion_id = _resolver_organizacion(db, user, data.organizacion_id)
    fechas = sorted(
        (OportunidadFecha(fecha_inicio=_aware(f.fecha_inicio), fecha_fin=_aware(f.fecha_fin) if f.fecha_fin else None)
         for f in data.fechas),
        key=lambda f: f.fecha_inicio,
    )
    ultima = max((f.fecha_fin or f.fecha_inicio) for f in fechas)
    oportunidad = Oportunidad(
        organizacion_id=organizacion_id,
        tutor_id=user.id,
        titulo=data.titulo.strip(),
        descripcion=data.descripcion.strip(),
        requisitos=serializar_requisitos(data.requisitos),
        region_id=data.region_id,
        comuna_id=data.comuna_id,
        categoria=data.categoria.strip(),
        cupos_totales=data.cupos_totales,
        whatsapp_grupo_url=str(data.whatsapp_grupo_url) if data.whatsapp_grupo_url else None,
        estado=ESTADO_OPORTUNIDAD_NUEVA,
        creado_en=datetime.now(),
        horas_voluntariado=data.horas_voluntariado,
        fecha_inicio_voluntariado=fechas[0].fecha_inicio.astimezone(_TZ).date(),
        fecha_fin_voluntariado=ultima.astimezone(_TZ).date(),
        region_opor=data.region_nombre,
        comuna_opor=data.comuna_nombre,
        fechas=fechas,
    )
    db.add(oportunidad)
    db.flush()
    notificar_voluntarios_region(
        db,
        data.region_id,
        TipoNotificacion.ACTIVIDAD_CREADA,
        "Nueva actividad en tu región",
        f"Se publicó la actividad \"{oportunidad.titulo}\". ¡Postula desde la app!",
        oportunidad.id,
    )
    db.commit()
    db.refresh(oportunidad)
    return oportunidad


def _proxima_fecha_expr():
    now = func.now()
    return (
        select(func.min(OportunidadFecha.fecha_inicio))
        .where(
            OportunidadFecha.oportunidad_id == Oportunidad.id,
            func.coalesce(OportunidadFecha.fecha_fin, OportunidadFecha.fecha_inicio) >= now,
        )
        .correlate(Oportunidad)
        .scalar_subquery()
    )


def listar_oportunidades(
    db: Session,
    region_id: int | None,
    comuna_id: int | None,
    categoria: str | None,
    incluir_pasadas: bool,
    skip: int,
    limit: int,
) -> list[OportunidadResumen]:
    proxima = _proxima_fecha_expr()
    tiene_fechas = exists().where(OportunidadFecha.oportunidad_id == Oportunidad.id)
    orden = func.coalesce(proxima, cast(Oportunidad.fecha_inicio_voluntariado, DateTime(timezone=True)))

    stmt = select(Oportunidad, proxima.label("proxima")).where(
        func.lower(Oportunidad.estado).in_(ESTADOS_OPORTUNIDAD_ACTIVA)
    )
    if region_id is not None:
        stmt = stmt.where(Oportunidad.region_id == region_id)
    if comuna_id is not None:
        stmt = stmt.where(Oportunidad.comuna_id == comuna_id)
    if categoria:
        stmt = stmt.where(func.lower(Oportunidad.categoria) == categoria.strip().lower())
    if not incluir_pasadas:
        stmt = stmt.where(
            or_(
                and_(tiene_fechas, proxima.is_not(None)),
                and_(
                    ~tiene_fechas,
                    or_(
                        Oportunidad.fecha_fin_voluntariado.is_(None),
                        Oportunidad.fecha_fin_voluntariado >= func.current_date(),
                    ),
                ),
            )
        )
    stmt = stmt.order_by(orden.asc().nulls_last(), Oportunidad.id.asc()).offset(skip).limit(limit)

    return [a_resumen(op, prox) for op, prox in db.execute(stmt).all()]


def a_resumen(op: Oportunidad, proxima: datetime | None = None) -> OportunidadResumen:
    if proxima is None:
        now = utcnow()
        proxima = next((f.fecha_inicio for f in op.fechas if (f.fecha_fin or f.fecha_inicio) >= now), None)
    return OportunidadResumen(
        id=op.id,
        titulo=op.titulo,
        descripcion=op.descripcion,
        categoria=op.categoria,
        region_id=op.region_id,
        comuna_id=op.comuna_id,
        region_nombre=op.region_opor,
        comuna_nombre=op.comuna_opor,
        cupos_totales=op.cupos_totales,
        estado=op.estado,
        proxima_fecha=proxima,
        fechas=[FechaOut.model_validate(f) for f in op.fechas],
    )


def contar_seleccionados(db: Session, oportunidad_id: int) -> int:
    return db.scalar(
        select(func.count(Postulacion.id)).where(
            Postulacion.oportunidad_id == oportunidad_id,
            func.lower(Postulacion.estado_web) == "seleccionado",
        )
    ) or 0
