# -*- coding: utf-8 -*-
"""Prueba de humo de extremo a extremo de la API, contra SQLite y el PDF de ejemplo."""

import os
import pathlib
import sys

# La raiz del proyecto, dos niveles por encima de este fichero.
RAIZ = pathlib.Path(__file__).resolve().parents[2]
BD = pathlib.Path(__file__).parent / "prueba.db"
if BD.exists():
    BD.unlink()

os.environ["DATABASE_URL"] = f"sqlite:///{BD.as_posix()}"
os.environ["JWT_SECRETO"] = "secreto-de-prueba"
os.environ["CLAVE_ARRANQUE"] = "arranque-de-prueba"
os.environ["COOKIE_SEGURA"] = "false"
os.environ["COOKIE_SAMESITE"] = "lax"
os.environ["ORIGENES_PERMITIDOS"] = "http://localhost:5173"

sys.path.insert(0, str(RAIZ / "backend"))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

fallos = []


def check(titulo, condicion, extra=""):
    marca = "OK " if condicion else "FALLO"
    print(f"  [{marca}] {titulo}" + (f"  -> {extra}" if extra and not condicion else ""))
    if not condicion:
        fallos.append(titulo)


with TestClient(app) as c:
    print("\n== Arranque y autenticación ==")
    r = c.get("/api/salud")
    check("salud responde", r.status_code == 200 and r.json()["ok"], r.text)

    r = c.get("/api/auth/estado")
    check("estado dice que no hay usuarios", r.json() == {"instalado": False, "usuarios": 0}, r.text)

    r = c.get("/api/trabajadores")
    check("sin sesión devuelve 401", r.status_code == 401, r.text)

    r = c.post("/api/auth/arranque", json={
        "email": "admin@club.es", "nombre": "Admin Club",
        "clave": "clave-larga-1234", "clave_arranque": "mal"})
    check("clave de arranque incorrecta se rechaza", r.status_code == 403, r.text)

    r = c.post("/api/auth/arranque", json={
        "email": "admin@club.es", "nombre": "Admin Club",
        "clave": "clave-larga-1234", "clave_arranque": "arranque-de-prueba"})
    check("alta del primer admin", r.status_code == 201, r.text)
    token = r.json()["token"]
    cab = {"Authorization": f"Bearer {token}"}

    r = c.post("/api/auth/arranque", json={
        "email": "otro@club.es", "nombre": "Otro", "clave": "clave-larga-1234",
        "clave_arranque": "arranque-de-prueba"})
    check("no se puede repetir el arranque", r.status_code == 409, r.text)

    r = c.post("/api/auth/login", json={"email": "admin@club.es", "clave": "mala"})
    check("login con clave mala falla", r.status_code == 401, r.text)

    r = c.post("/api/auth/login", json={"email": "admin@club.es", "clave": "clave-larga-1234"})
    check("login correcto", r.status_code == 200, r.text)

    r = c.get("/api/auth/yo", headers=cab)
    check("yo devuelve el admin", r.json()["rol"] == "admin", r.text)

    print("\n== Plantilla ==")
    # Los cuatro trabajadores reales del PDF de ejemplo, mas uno que no aparece en el.
    nombres = ["Álvaro Ruiz Ferrán", "María José López Díaz", "Sergio Núñez Campos",
               "Pepe Desconocido García", "Tomás Iglesias Vega"]
    ids = {}
    for n in nombres:
        r = c.post("/api/trabajadores", json={"nombre": n, "puesto": "Jugador"}, headers=cab)
        if r.status_code != 201:
            check(f"alta de {n}", False, r.text)
        else:
            ids[n] = r.json()["id"]
    check("cinco altas", len(ids) == 5)

    r = c.post("/api/trabajadores", json={"nombre": "Álvaro Ruiz Ferrán"}, headers=cab)
    check("nombre duplicado se rechaza", r.status_code == 409, r.text)

    r = c.post("/api/trabajadores", json={"nombre": "Pepe"}, headers=cab)
    check("nombre sin apellido se rechaza", r.status_code == 422, r.text)

    print("\n== Procesar el PDF de ejemplo ==")
    pdf = (RAIZ / "ejemplo" / "nominas_ejemplo_enero.pdf").read_bytes()

    r = c.post("/api/documentos/procesar", headers=cab,
               files={"fichero": ("nominas_ejemplo_enero.pdf", pdf, "application/pdf")},
               data={"simular": "true"})
    check("simulación responde", r.status_code == 200, r.text)
    sim = r.json()
    print(f"       páginas={sim['paginas_totales']} nuevos={sim['nuevos']} "
          f"sin_identificar={sim['sin_identificar']} sin_texto={sim['sin_texto']}")
    for h in sim["hojas"]:
        print(f"       pág {h['paginas']:<5} -> {h['trabajador_nombre'] or '_Sin identificar':<22}"
              f" {h['periodo_txt']:<14} {h['nombre_fichero']}")
    check("la simulación no escribe nada", sim["nuevos"] == 0 and sim["simulado"])

    r = c.get("/api/documentos", headers=cab)
    check("tras simular no hay documentos", r.json() == [], r.text)

    r = c.post("/api/documentos/procesar", headers=cab,
               files={"fichero": ("nominas_ejemplo_enero.pdf", pdf, "application/pdf")},
               data={"simular": "false"})
    real = r.json()
    check("procesado real", r.status_code == 200, r.text)
    print(f"       nuevos={real['nuevos']} duplicados={real['duplicados']} "
          f"sin_identificar={real['sin_identificar']}")
    # El ejemplo trae 5 hojas de 4 trabajadores: Alvaro ocupa las paginas 1 y 2.
    check("identifica a los 4 trabajadores del ejemplo",
          real["nuevos"] == 4 and real["sin_identificar"] == 0,
          f"nuevos={real['nuevos']} sin_id={real['sin_identificar']}")

    r = c.post("/api/documentos/procesar", headers=cab,
               files={"fichero": ("nominas_ejemplo_enero.pdf", pdf, "application/pdf")},
               data={"simular": "false"})
    rep = r.json()
    check("reprocesar el mismo PDF no duplica",
          rep["nuevos"] == 0 and rep["duplicados"] == 4,
          f"nuevos={rep['nuevos']} dup={rep['duplicados']}")

    print("\n== Documentos, revisión y ZIP ==")
    r = c.get("/api/documentos", headers=cab)
    docs = r.json()
    check("hay 4 documentos", len(docs) == 4, str(len(docs)))
    check("todos con periodo Enero 2025",
          all(d["periodo_txt"] == "Enero 2025" for d in docs),
          str({d["periodo_txt"] for d in docs}))

    d0 = docs[0]
    r = c.get(f"/api/documentos/{d0['id']}/descargar", headers=cab)
    check("descarga un PDF válido",
          r.status_code == 200 and r.content[:5] == b"%PDF-", str(r.content[:10]))

    r = c.get("/api/revisar", params={"periodo": "Enero 2025"}, headers=cab)
    rev = r.json()
    check("revisión: solo falta el que no sale en el PDF",
          rev["total"] == 5 and rev["sin_nomina"] == ["Tomás Iglesias Vega"],
          str(rev.get("sin_nomina")))

    r = c.get("/api/revisar", params={"periodo": "Febrero 2025"}, headers=cab)
    check("revisión: faltan los 5 en febrero", len(r.json()["sin_nomina"]) == 5, r.text)

    r = c.get("/api/revisar", params={"periodo": "no es un periodo"}, headers=cab)
    check("periodo ilegible se rechaza", r.status_code == 422, r.text)

    r = c.patch(f"/api/documentos/{d0['id']}",
                json={"quitar_trabajador": True}, headers=cab)
    check("mandar hoja a sin identificar", r.json()["trabajador_id"] is None, r.text)
    r = c.get("/api/documentos", params={"sin_asignar": "true"}, headers=cab)
    check("aparece en sin asignar", len(r.json()) == 1, r.text)
    r = c.patch(f"/api/documentos/{d0['id']}",
                json={"trabajador_id": d0["trabajador_id"]}, headers=cab)
    check("reasignar de vuelta", r.json()["trabajador_id"] == d0["trabajador_id"], r.text)

    r = c.get("/api/documentos/zip/descargar", headers=cab)
    check("zip se genera", r.status_code == 200 and r.content[:2] == b"PK", str(r.content[:8]))
    import io, zipfile
    with zipfile.ZipFile(io.BytesIO(r.content)) as z:
        rutas = z.namelist()
    pdfs = [p for p in rutas if p.endswith(".pdf")]
    check("el zip trae los 4 PDF", len(pdfs) == 4, str(len(pdfs)))
    check("el zip conserva la estructura de carpetas",
          any("/Nóminas/" in p for p in pdfs) and any(p.endswith("/Contrato/") for p in rutas),
          str(rutas[:6]))

    print("\n== Permisos y auditoría ==")
    r = c.post("/api/usuarios", headers=cab, json={
        "email": "gestor@club.es", "nombre": "Gestor Club",
        "clave": "otra-clave-larga", "rol": "gestor"})
    check("alta de gestor", r.status_code == 201, r.text)
    rg = c.post("/api/auth/login", json={"email": "gestor@club.es", "clave": "otra-clave-larga"})
    cabg = {"Authorization": f"Bearer {rg.json()['token']}"}

    r = c.get("/api/trabajadores", headers=cabg)
    check("el gestor puede consultar la plantilla", r.status_code == 200, r.text)
    r = c.delete(f"/api/documentos/{d0['id']}", headers=cabg)
    check("el gestor no puede borrar documentos", r.status_code == 403, r.text)
    r = c.get("/api/usuarios", headers=cabg)
    check("el gestor no puede listar usuarios", r.status_code == 403, r.text)

    r = c.get("/api/registro", headers=cab)
    check("el registro tiene trazas", len(r.json()) > 5, str(len(r.json())))
    r = c.get("/api/registro/csv", headers=cab)
    check("el csv se exporta", r.status_code == 200 and b"fecha;usuario" in r.content,
          str(r.content[:60]))

    r = c.delete(f"/api/documentos/{d0['id']}", headers=cab)
    check("el admin sí puede borrar", r.status_code == 204, r.text)

print("\n" + "=" * 60)
if fallos:
    print(f"{len(fallos)} PRUEBA(S) FALLIDA(S):")
    for f in fallos:
        print("  -", f)
    sys.exit(1)
print("TODAS LAS PRUEBAS PASAN")
