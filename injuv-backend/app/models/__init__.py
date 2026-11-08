from app.models.usuario import Organizacion, Usuario
from app.models.oportunidad import Oportunidad, OportunidadFecha
from app.models.postulacion import AsistenciaTutor, Postulacion
from app.models.notificacion import Notificacion
from app.models.certificado import Certificado
from app.models.noticia import Noticia

__all__ = [
    "AsistenciaTutor",
    "Certificado",
    "Noticia",
    "Notificacion",
    "Oportunidad",
    "OportunidadFecha",
    "Organizacion",
    "Postulacion",
    "Usuario",
]
