from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text
from werkzeug.security import check_password_hash, generate_password_hash

from app.core.config import settings
from app.db.session import engine

API = "/api/v1"
PASSWORD = "Secreta123"


def _exec(sql_text: str, **params):
    with engine.begin() as conn:
        return conn.execute(text(sql_text), params)


def _crear_usuario_web(email, rut, rol, region_id=None, password=PASSWORD):
    """Simula un usuario creado por la web (hash Werkzeug por defecto)."""
    return _exec(
        "INSERT INTO usuarios (nombre, apellido, rut, email, password_hash, rol, region_id, created_at) "
        "VALUES ('N', 'A', :rut, :email, :ph, :rol, :region_id, NOW()) RETURNING id",
        rut=rut, email=email, ph=generate_password_hash(password), rol=rol, region_id=region_id,
    ).scalar_one()


def _login(client, identificador, password=PASSWORD):
    r = client.post(f"{API}/auth/login", json={"identificador": identificador, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def ctx(client):
    tutor_id = _crear_usuario_web("tutor@org.cl", "111111111", "organizacion")
    otro_tutor_id = _crear_usuario_web("otro@org.cl", "222222222", "organizacion")
    admin_id = _crear_usuario_web("admin@injuv.cl", "333333333", "admin")
    org_id = _exec(
        "INSERT INTO organizaciones (nombre, id_usuario_org) VALUES ('Org Uno', :u) RETURNING id", u=tutor_id
    ).scalar_one()
    _exec("INSERT INTO organizaciones (nombre, id_usuario_org) VALUES ('Org Dos', :u)", u=otro_tutor_id)
    vol_rm = [_crear_usuario_web(f"vol{i}@mail.cl", f"44444444{i}", "user", region_id=13) for i in range(3)]
    vol_otra = _crear_usuario_web("lejos@mail.cl", "555555555", "user", region_id=5)
    return {
        "tutor_id": tutor_id,
        "admin_id": admin_id,
        "org_id": org_id,
        "vol_rm": vol_rm,
        "vol_otra": vol_otra,
        "tutor": _login(client, "tutor@org.cl"),
        "otro_tutor": _login(client, "otro@org.cl"),
        "admin": _login(client, "admin@injuv.cl"),
        "vols": [_login(client, f"vol{i}@mail.cl") for i in range(3)],
        "lejos": _login(client, "lejos@mail.cl"),
    }


def _payload(**over):
    ahora = datetime.now(timezone.utc)
    data = {
        "titulo": "Limpieza de playa",
        "descripcion": "Jornada de limpieza",
        "requisitos": ["Mayor de 18", "Traer agua"],
        "region_id": 13,
        "comuna_id": 101,
        "categoria": "Medio Ambiente",
        "cupos_totales": 2,
        "whatsapp_grupo_url": "https://chat.whatsapp.com/abc123",
        "fechas": [
            {"fecha_inicio": (ahora + timedelta(days=10)).isoformat(), "fecha_fin": (ahora + timedelta(days=10, hours=4)).isoformat()},
            {"fecha_inicio": (ahora + timedelta(days=3)).isoformat()},
        ],
        "region_nombre": "Región Metropolitana de Santiago",
    }
    data.update(over)
    return data


# ---------------------------------------------------------------- auth
def test_login_usuario_web_por_email_y_rut(client, ctx):
    r = client.post(f"{API}/auth/login", json={"identificador": "TUTOR@org.cl ", "password": PASSWORD})
    assert r.status_code == 200
    assert r.json()["rol"] == "TUTOR"
    r = client.post(f"{API}/auth/login", json={"identificador": "11.111.111-1", "password": PASSWORD})
    assert r.status_code == 200
    r = client.post(f"{API}/auth/login", json={"identificador": "tutor@org.cl", "password": "mala"})
    assert r.status_code == 401
    assert r.json() == {"detail": "Email/RUT o contraseña incorrectos"}


def test_token_form_para_swagger(client, ctx):
    r = client.post(f"{API}/auth/token", data={"username": "admin@injuv.cl", "password": PASSWORD})
    assert r.status_code == 200 and r.json()["rol"] == "ADMIN"


def test_registro_compatible_con_web(client):
    body = {
        "email": "Nuevo@Mail.cl", "password": "ClaveSegura1", "nombre": "Ana", "apellido": "Pérez",
        "rut": "12.345.678-5", "region_id": 13, "comuna_id": 101,
    }
    r = client.post(f"{API}/auth/register", json=body)
    assert r.status_code == 201, r.text
    assert r.json()["rol"] == "VOLUNTARIO" and r.json()["rut"] == "123456785"
    rol, ph = _exec("SELECT rol, password_hash FROM usuarios WHERE email='nuevo@mail.cl'").one()
    assert rol == "user"
    if settings.PASSWORD_HASH_SCHEME == "werkzeug":
        assert check_password_hash(ph, "ClaveSegura1")  # la web puede validar el hash

    assert client.post(f"{API}/auth/register", json=body).status_code == 409
    assert client.post(f"{API}/auth/register", json={**body, "email": "x@x.cl"}).status_code == 409
    r = client.post(f"{API}/auth/register", json={**body, "email": "y@y.cl", "rut": "12.345.678-9"})
    assert r.status_code == 422 and r.json()["detail"] == "Datos de entrada inválidos"


def test_me_y_actualizar(client, ctx):
    h = ctx["vols"][0]
    assert client.get(f"{API}/auth/me").status_code == 401
    assert client.get(f"{API}/auth/me", headers={"Authorization": "Bearer basura"}).status_code == 401
    r = client.put(f"{API}/auth/me", headers=h, json={"telefono": "+56911112222", "comuna_id": 102})
    assert r.status_code == 200
    assert r.json()["telefono"] == "+56911112222" and r.json()["comuna_id"] == 102 and r.json()["region_id"] == 13


# ---------------------------------------------------------------- oportunidades
def test_flujo_completo(client, ctx):
    # solo tutores/admin crean
    assert client.post(f"{API}/oportunidades", headers=ctx["vols"][0], json=_payload()).status_code == 403
    r = client.post(f"{API}/oportunidades", headers=ctx["tutor"], json=_payload())
    assert r.status_code == 201, r.text
    op = r.json()
    op_id = op["id"]
    assert op["requisitos"] == ["Mayor de 18", "Traer agua"]
    assert len(op["fechas"]) == 2 and op["fechas"][0]["fecha_inicio"] < op["fechas"][1]["fecha_inicio"]
    assert op["whatsapp_grupo_url"] == "https://chat.whatsapp.com/abc123"  # el tutor dueño lo ve

    # columnas web sincronizadas
    row = _exec(
        "SELECT organizacion_id, cupo_maximo, tipo_de_voluntariado, estado, fecha_inicio_voluntariado, region_opor "
        "FROM oportunidades WHERE id=:i", i=op_id,
    ).one()
    assert row[0] == ctx["org_id"] and row[1] == 2 and row[2] == "Medio Ambiente" and row[3] == "activa"
    assert row[4] is not None and row[5] == "Región Metropolitana de Santiago"

    # notificación ACTIVIDAD_CREADA solo a voluntarios de la región 13
    for h in ctx["vols"]:
        tipos = [n["tipo"] for n in client.get(f"{API}/notificaciones", headers=h).json()]
        assert "ACTIVIDAD_CREADA" in tipos
    assert client.get(f"{API}/notificaciones", headers=ctx["lejos"]).json() == []
    assert client.get(f"{API}/notificaciones", headers=ctx["tutor"]).json() == []

    # detalle: voluntario no ve WhatsApp antes de ser seleccionado
    det = client.get(f"{API}/oportunidades/{op_id}", headers=ctx["vols"][0]).json()
    assert det["whatsapp_grupo_url"] is None and det["mi_postulacion_estado"] is None

    # postulaciones
    assert client.post(f"{API}/postulaciones/{op_id}", headers=ctx["tutor"]).status_code == 403
    post_ids = []
    for h in ctx["vols"]:
        r = client.post(f"{API}/postulaciones/{op_id}", headers=h)
        assert r.status_code == 201 and r.json()["estado"] == "PENDIENTE"
        post_ids.append(r.json()["id"])
    assert client.post(f"{API}/postulaciones/{op_id}", headers=ctx["vols"][0]).status_code == 409
    assert _exec("SELECT estado FROM postulaciones WHERE id=:i", i=post_ids[0]).scalar_one() == "Pendiente de revisión"
    mias = client.get(f"{API}/postulaciones/mias", headers=ctx["vols"][0]).json()
    assert mias[0]["oportunidad_titulo"] == "Limpieza de playa"

    # listado de postulantes: solo el tutor dueño
    assert client.get(f"{API}/postulaciones/oportunidad/{op_id}", headers=ctx["otro_tutor"]).status_code == 403
    r = client.get(f"{API}/postulaciones/oportunidad/{op_id}", headers=ctx["tutor"])
    assert r.status_code == 200 and len(r.json()) == 3 and r.json()[0]["usuario"]["email"] == "vol0@mail.cl"

    # selección + notificación + cupos
    url = f"{API}/postulaciones/{{}}/estado"
    assert client.put(url.format(post_ids[0]), headers=ctx["otro_tutor"], json={"estado": "SELECCIONADO"}).status_code == 403
    assert client.put(url.format(post_ids[0]), headers=ctx["tutor"], json={"estado": "PENDIENTE"}).status_code == 422
    r = client.put(url.format(post_ids[0]), headers=ctx["tutor"], json={"estado": "SELECCIONADO"})
    assert r.status_code == 200 and r.json()["estado"] == "SELECCIONADO"
    assert _exec("SELECT estado FROM postulaciones WHERE id=:i", i=post_ids[0]).scalar_one() == "Seleccionado"
    assert client.put(url.format(post_ids[1]), headers=ctx["admin"], json={"estado": "SELECCIONADO"}).status_code == 200
    r = client.put(url.format(post_ids[2]), headers=ctx["tutor"], json={"estado": "SELECCIONADO"})
    assert r.status_code == 409
    r = client.put(url.format(post_ids[2]), headers=ctx["tutor"], json={"estado": "RECHAZADO"})
    assert r.json()["estado"] == "RECHAZADO"
    assert _exec("SELECT estado FROM postulaciones WHERE id=:i", i=post_ids[2]).scalar_one() == "No seleccionado"

    notifs = client.get(f"{API}/notificaciones", headers=ctx["vols"][0]).json()
    seleccion = [n for n in notifs if n["tipo"] == "FUISTE_SELECCIONADO"]
    assert len(seleccion) == 1 and seleccion[0]["oportunidad_id"] == op_id
    assert not any(n["tipo"] == "FUISTE_SELECCIONADO" for n in client.get(f"{API}/notificaciones", headers=ctx["vols"][2]).json())

    # ahora el seleccionado ve el WhatsApp, el rechazado no
    det = client.get(f"{API}/oportunidades/{op_id}", headers=ctx["vols"][0]).json()
    assert det["whatsapp_grupo_url"] == "https://chat.whatsapp.com/abc123" and det["mi_postulacion_estado"] == "SELECCIONADO"
    assert det["cupos_ocupados"] == 2
    assert client.get(f"{API}/oportunidades/{op_id}", headers=ctx["vols"][2]).json()["whatsapp_grupo_url"] is None

    # marcar leída
    nid = seleccion[0]["id"]
    assert client.patch(f"{API}/notificaciones/{nid}/leer", headers=ctx["vols"][1]).status_code == 404
    r = client.patch(f"{API}/notificaciones/{nid}/leer", headers=ctx["vols"][0])
    assert r.status_code == 200 and r.json()["leido"] is True
    no_leidas = client.get(f"{API}/notificaciones?solo_no_leidas=true", headers=ctx["vols"][0]).json()
    assert nid not in [n["id"] for n in no_leidas]

    # asistencia masiva
    asis = f"{API}/asistencia/marcar-masivo"
    assert client.post(asis, headers=ctx["vols"][0], json=[{"postulacion_id": post_ids[0], "asistio": True}]).status_code == 403
    assert client.post(asis, headers=ctx["tutor"], json=[{"postulacion_id": post_ids[2], "asistio": True}]).status_code == 400
    assert client.post(asis, headers=ctx["tutor"], json=[{"postulacion_id": 999999, "asistio": True}]).status_code == 404
    assert client.post(asis, headers=ctx["otro_tutor"], json=[{"postulacion_id": post_ids[0], "asistio": True}]).status_code == 403
    r = client.post(asis, headers=ctx["tutor"], json=[
        {"postulacion_id": post_ids[0], "asistio": True}, {"postulacion_id": post_ids[1], "asistio": True},
    ])
    assert r.status_code == 200 and [a["asistio"] for a in r.json()] == [True, True]
    r = client.post(asis, headers=ctx["tutor"], json=[{"postulacion_id": post_ids[1], "asistio": False}])
    assert r.status_code == 200 and r.json()[0]["asistio"] is False
    assert _exec("SELECT COUNT(*) FROM asistencias_tutor").scalar_one() == 2
    assert _exec("SELECT asistencia_actividad FROM postulaciones WHERE id=:i", i=post_ids[0]).scalar_one() == "Sí"
    assert _exec("SELECT asistencia_actividad FROM postulaciones WHERE id=:i", i=post_ids[1]).scalar_one() == "No"
    postulantes = client.get(f"{API}/postulaciones/oportunidad/{op_id}", headers=ctx["tutor"]).json()
    assert [p["asistio"] for p in postulantes] == [True, False, None]

    # mensaje masivo a seleccionados
    r = client.post(f"{API}/notificaciones/mensaje-masivo", headers=ctx["tutor"],
                    json={"oportunidad_id": op_id, "titulo": "Recordatorio", "mensaje": "Lleven bloqueador"})
    assert r.status_code == 201 and r.json() == {"enviadas": 2}
    assert any(n["tipo"] == "MENSAJE_TUTOR" for n in client.get(f"{API}/notificaciones", headers=ctx["vols"][1]).json())
    assert not any(n["tipo"] == "MENSAJE_TUTOR" for n in client.get(f"{API}/notificaciones", headers=ctx["vols"][2]).json())

    # certificados
    cert = {"usuario_id": ctx["vol_rm"][0], "oportunidad_id": op_id, "url_pdf": "https://cdn.injuv.cl/c1.pdf", "horas_acreditadas": 4.5}
    assert client.post(f"{API}/certificados/cargar", headers=ctx["tutor"], json={**cert, "usuario_id": ctx["vol_rm"][2]}).status_code == 400
    assert client.post(f"{API}/certificados/cargar", headers=ctx["otro_tutor"], json=cert).status_code == 403
    r = client.post(f"{API}/certificados/cargar", headers=ctx["tutor"], json=cert)
    assert r.status_code == 201, r.text
    r = client.post(f"{API}/certificados/cargar", headers=ctx["tutor"], json={**cert, "horas_acreditadas": 6})
    assert r.status_code == 201 and float(r.json()["horas_acreditadas"]) == 6.0
    mis = client.get(f"{API}/certificados", headers=ctx["vols"][0]).json()
    assert len(mis["certificados"]) == 1 and float(mis["total_horas"]) == 6.0
    assert mis["certificados"][0]["oportunidad_titulo"] == "Limpieza de playa"
    assert any(n["tipo"] == "CERTIFICADO_CARGADO" for n in client.get(f"{API}/notificaciones", headers=ctx["vols"][0]).json())


def test_listado_filtros_y_orden(client, ctx):
    ahora = datetime.now(timezone.utc)

    def crear(titulo, dias, **over):
        body = _payload(titulo=titulo, fechas=[{"fecha_inicio": (ahora + timedelta(days=dias)).isoformat()}], **over)
        r = client.post(f"{API}/oportunidades", headers=ctx["tutor"], json=body)
        assert r.status_code == 201, r.text
        return r.json()["id"]

    lejana = crear("Filtro lejana", 30, comuna_id=900, categoria="Educación")
    cercana = crear("Filtro cercana", 1, comuna_id=900, categoria="Educación")
    pasada = crear("Filtro pasada", -5, comuna_id=900, categoria="Educación")
    otra_cat = crear("Filtro otra categoría", 2, comuna_id=900, categoria="Salud")

    h = ctx["vols"][0]
    ids = [o["id"] for o in client.get(f"{API}/oportunidades?region_id=13&comuna_id=900&categoria=educación", headers=h).json()]
    assert ids == [cercana, lejana]
    ids = [o["id"] for o in client.get(f"{API}/oportunidades?comuna_id=900&incluir_pasadas=true&categoria=Educación", headers=h).json()]
    assert pasada in ids
    ids = [o["id"] for o in client.get(f"{API}/oportunidades?comuna_id=900", headers=h).json()]
    assert ids == [cercana, otra_cat, lejana]
    assert client.get(f"{API}/oportunidades?region_id=5&comuna_id=900", headers=h).json() == []
    assert client.get(f"{API}/oportunidades", headers=h).status_code == 200
    assert client.get(f"{API}/oportunidades").status_code == 401

    # una oportunidad cerrada no aparece y no admite postulaciones
    _exec("UPDATE oportunidades SET estado='cerrada' WHERE id=:i", i=lejana)
    ids = [o["id"] for o in client.get(f"{API}/oportunidades?comuna_id=900", headers=h).json()]
    assert lejana not in ids
    assert client.post(f"{API}/postulaciones/{lejana}", headers=h).status_code == 400


def test_oportunidad_creada_en_web_es_visible(client, ctx, has_web_schema):
    if not has_web_schema:
        pytest.skip("requiere esquema de la web")
    op_id = _exec(
        "INSERT INTO oportunidades (organizacion_id, titulo, descripcion, estado, cupo_maximo, tipo_de_voluntariado, "
        "fecha_inicio_voluntariado, created_at) VALUES (:o, 'Desde la web', 'desc', 'activa', 5, 'Cultura', "
        "CURRENT_DATE + 2, NOW()) RETURNING id", o=ctx["org_id"],
    ).scalar_one()
    lista = client.get(f"{API}/oportunidades?categoria=Cultura", headers=ctx["vols"][0]).json()
    assert [o["id"] for o in lista] == [op_id] and lista[0]["cupos_totales"] == 5
    det = client.get(f"{API}/oportunidades/{op_id}", headers=ctx["vols"][0]).json()
    assert det["requisitos"] == [] and det["fechas"] == []
    # el tutor de la organización la gestiona aunque no la creó desde la app
    assert client.get(f"{API}/postulaciones/oportunidad/{op_id}", headers=ctx["tutor"]).status_code == 200


def test_tutor_sin_organizacion_y_validaciones(client, ctx):
    _crear_usuario_web("huerfano@org.cl", "666666666", "organizacion")
    h = _login(client, "huerfano@org.cl")
    r = client.post(f"{API}/oportunidades", headers=h, json=_payload())
    assert r.status_code == 400
    r = client.post(f"{API}/oportunidades", headers=ctx["tutor"], json=_payload(fechas=[]))
    assert r.status_code == 422
    ahora = datetime.now(timezone.utc)
    malas = [{"fecha_inicio": ahora.isoformat(), "fecha_fin": (ahora - timedelta(hours=1)).isoformat()}]
    assert client.post(f"{API}/oportunidades", headers=ctx["tutor"], json=_payload(fechas=malas)).status_code == 422
    assert client.post(f"{API}/oportunidades", headers=ctx["admin"], json=_payload()).status_code == 400
    r = client.post(f"{API}/oportunidades", headers=ctx["admin"], json=_payload(organizacion_id=ctx["org_id"]))
    assert r.status_code == 201
    assert client.get(f"{API}/oportunidades/999999", headers=ctx["admin"]).status_code == 404


# ---------------------------------------------------------------- noticias
def test_noticias(client):
    _exec(
        "INSERT INTO noticias (titulo, contenido, resumen, estado, imagen_noticia, fecha_publicacion) VALUES "
        "('Activa', 'cuerpo', 'bajada', 'activa', 'noticia_1.jpg', NOW()),"
        "('Oculta', 'cuerpo', NULL, 'inactiva', NULL, NOW()),"
        "('Externa', 'cuerpo', NULL, 'publicada', 'https://img.cl/x.png', NOW() - INTERVAL '1 day')"
    )
    r = client.get(f"{API}/noticias")
    assert r.status_code == 200
    data = r.json()
    assert [n["titulo"] for n in data] == ["Activa", "Externa"]
    assert data[0]["bajada"] == "bajada" and data[0]["cuerpo"] == "cuerpo"
    assert data[0]["imagen_url"].endswith("/api/noticias/imagen/noticia_1.jpg")
    assert data[1]["imagen_url"] == "https://img.cl/x.png"
    assert client.get(f"{API}/noticias/{data[0]['id']}").status_code == 200


def test_health_y_docs(client):
    assert client.get("/health").json() == {"status": "ok", "database": "ok"}
    assert client.get("/docs").status_code == 200
    paths = client.get(f"{API}/openapi.json").json()["paths"]
    for p in ["/api/v1/auth/login", "/api/v1/oportunidades", "/api/v1/asistencia/marcar-masivo",
              "/api/v1/certificados/cargar", "/api/v1/notificaciones/mensaje-masivo"]:
        assert p in paths
