"""Estados compartidos con la web. Se guardan los textos que usa la web y la API expone el ENUM móvil."""
import enum


class EstadoPostulacion(str, enum.Enum):
    PENDIENTE = "PENDIENTE"
    SELECCIONADO = "SELECCIONADO"
    RECHAZADO = "RECHAZADO"


POSTULACION_TO_WEB = {
    EstadoPostulacion.PENDIENTE: "Pendiente de revisión",
    EstadoPostulacion.SELECCIONADO: "Seleccionado",
    EstadoPostulacion.RECHAZADO: "No seleccionado",
}

_POSTULACION_RECHAZO_WEB = {"no seleccionado", "rechazado", "rechazada", "declinada por usuario"}


def postulacion_from_web(value: str | None) -> EstadoPostulacion:
    v = (value or "").strip().lower()
    if v == "seleccionado":
        return EstadoPostulacion.SELECCIONADO
    if v in _POSTULACION_RECHAZO_WEB:
        return EstadoPostulacion.RECHAZADO
    return EstadoPostulacion.PENDIENTE


ESTADO_OPORTUNIDAD_NUEVA = "activa"
ESTADOS_OPORTUNIDAD_ACTIVA = ("activa", "abierta", "abierto", "publicada")


class TipoNotificacion(str, enum.Enum):
    FUISTE_SELECCIONADO = "FUISTE_SELECCIONADO"
    ACTIVIDAD_CREADA = "ACTIVIDAD_CREADA"
    CERTIFICADO_CARGADO = "CERTIFICADO_CARGADO"
    MENSAJE_TUTOR = "MENSAJE_TUTOR"
