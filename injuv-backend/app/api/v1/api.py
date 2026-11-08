from fastapi import APIRouter

from app.api.v1.endpoints import asistencia, auth, certificados, noticias, notificaciones, oportunidades, postulaciones

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Auth y perfil"])
api_router.include_router(oportunidades.router, prefix="/oportunidades", tags=["Oportunidades"])
api_router.include_router(postulaciones.router, prefix="/postulaciones", tags=["Postulaciones"])
api_router.include_router(asistencia.router, prefix="/asistencia", tags=["Asistencia"])
api_router.include_router(notificaciones.router, prefix="/notificaciones", tags=["Notificaciones"])
api_router.include_router(certificados.router, prefix="/certificados", tags=["Certificados"])
api_router.include_router(noticias.router, prefix="/noticias", tags=["Noticias"])
