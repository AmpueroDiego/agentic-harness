"""Genera el tablero visual de avance del proyecto.

Lee el tablero de Trello en vivo (misma credencial que trello.py) y el CSV de
estimacion (contexto-negocio/estimacion-backlog-pert.csv, no versionado) y
escribe un HTML estatico listo para publicar como Artifact.

    python .claude/tools/trello/tablero-avance.py [salida.html]

No muta nada en Trello: solo lee.
"""

import csv
import datetime as dt
import io
import json
import os
import sys
import urllib.parse
import urllib.request

RAIZ = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))
CSV_ESTIMACION = os.path.join(RAIZ, "contexto-negocio", "estimacion-backlog-pert.csv")
CREDENCIALES = os.path.join(os.path.expanduser("~"), ".trello-credentials.json")

INICIO = dt.date(2026, 9, 21)
FIN_HITO1 = dt.date(2026, 10, 30)
FIN_HITO2 = dt.date(2027, 1, 5)
# Jornada real (el responsable, 2026-09-21): 9 h de lunes a viernes = 45 h/semana, mas
# 2 sabados al mes de 4 h. Eso son 203 h al mes en ~21.7 dias laborables, o sea
# 9.35 h por dia con los sabados ya prorrateados. La semana laboral que cuenta
# el calendario es de lunes a viernes; el Excel usa 9.8 h y cuenta sabados, por
# eso su columna de dias no coincide con esta.
# Jornada asumida para cumplir el 30/10 (decision del responsable, 2026-09-21): 11.9 h
# de lunes a viernes, el ritmo que exige el pendiente. Ademas se trabajan 4
# sabados de 4 h en el periodo (16 h), que entran como capacidad extra, y la
# reserva de fixes NO se planifica: es margen al final.
HORAS_DIA = 11.9
SABADOS = 4
HORAS_SABADO = 4.0
RESERVA_ES_MARGEN = True
# Sin factor de foco a proposito (decision del responsable, 2026-09-21): la
# contingencia por riesgo del Excel (15/20/30%) ya cubre el tiempo que se va en
# correos, interrupciones y cambios de contexto. Descontarlo otra vez seria
# contarlo dos veces.
FOCO = 1.00
CAP_DIA = HORAS_DIA * FOCO
RESERVA_FIXES = 0.15
HORAS_SIN_ESTIMAR = 4.0   # M: tarjeta nueva de Trello que aun no tiene fila en el CSV

# Columna del tablero -> estado en el tablero de avance.
ESTADOS = {
    "Backlog del Backlog": "pendiente",
    "Backlog": "pendiente",
    "En desarrollo": "curso",
    # En revisión (el responsable) todavía no pasó la puerta de Codex ni tu visto bueno: sigue en curso (el responsable, 02/10).
    "En revisión (el responsable)": "curso",
    # En revisión el código ya está terminado: solo falta la revisión del PR (el responsable, 23/09).
    "En revisión (Revisor Principal)": "hecho",
    "En revisión (Revisor Secundario)": "hecho",
    "DEV": "hecho",
    "Listo para PROD": "hecho",
    "Terminado": "hecho",
}


def credenciales():
    with io.open(CREDENCIALES, encoding="utf-8-sig") as f:
        return json.load(f)


def api(ruta, cred, **params):
    params.update({"key": cred["apiKey"], "token": cred["token"]})
    url = "https://api.trello.com/1/%s?%s" % (ruta, urllib.parse.urlencode(params))
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.load(r)


def leer_tablero():
    cred = credenciales()
    tablero = cred["defaultBoardId"]
    listas = {l["id"]: l["name"] for l in api("boards/%s/lists" % tablero, cred)}
    tarjetas = {}
    for t in api("boards/%s/cards" % tablero, cred, fields="name,idList,shortLink,dateLastActivity"):
        tarjetas[t["shortLink"]] = {
            "nombre": t["name"],
            "columna": listas.get(t["idList"], "?"),
            "actividad": (t.get("dateLastActivity") or "")[:10],
        }
    return tarjetas


def leer_estimacion():
    with io.open(CSV_ESTIMACION, encoding="utf-8") as f:
        return [r for r in csv.DictReader(f)]


def dias_habiles(desde, hasta):
    """Dias habiles entre dos fechas (lunes a viernes)."""
    if hasta < desde:
        return 0
    n, d = 0, desde
    while d < hasta:
        if d.weekday() < 5:
            n += 1
        d += dt.timedelta(days=1)
    return n


def sumar_habiles(desde, dias):
    """Suma N dias habiles (lunes a viernes) a una fecha."""
    d, restantes = desde, int(round(dias))
    while restantes > 0:
        d += dt.timedelta(days=1)
        if d.weekday() < 5:
            restantes -= 1
    return d


def fraccion_jornada(ahora):
    """Que parte de la jornada de hoy ya paso, entre 0 y 1.

    Lunes a viernes, 9:00 a 19:00 con una hora de refrigerio a las 13:00. Los
    sabados no cuentan como dia: sus horas ya estan prorrateadas en HORAS_DIA.
    """
    if ahora.weekday() >= 5:
        return 0.0
    t = ahora.hour + ahora.minute / 60.0
    trabajadas = max(0.0, min(13.0, t) - 9.0) + max(0.0, min(19.0, t) - 14.0)
    return max(0.0, min(1.0, trabajadas / 9.0))


# Unidad del tablero: la TARJETA (el responsable, 21/10). Las horas del CSV quedan
# como dato secundario y nunca se usan para prorratear avance ni fechas.
TERMINADA = {"DEV", "Listo para PROD", "Terminado"}
REVISION = {"En revisión (Revisor Principal)", "En revisión (Revisor Secundario)"}   # casi hechas: no cuentan como terminadas
CURSO = {"En desarrollo", "En revisión (el responsable)"}
PLAN = ["Backlog", "Tenant", "Nutrir de data"]
VENTANA_RECIENTE = 14   # dias corridos del ritmo reciente (2 semanas)


def estado_tarjeta(columna):
    if columna in TERMINADA:
        return "terminada"
    if columna in REVISION:
        return "revision"
    if columna in CURSO:
        return "curso"
    return "pendiente"


def leer_terminos(desde):
    """Fecha en que cada tarjeta llego por primera vez a una columna terminada."""
    cred = credenciales()
    tablero = cred["defaultBoardId"]
    acciones, antes = [], None
    while True:
        params = {"filter": "updateCard:idList,createCard", "limit": 1000,
                  "since": (desde - dt.timedelta(days=1)).isoformat()}
        if antes:
            params["before"] = antes
        lote = api("boards/%s/actions" % tablero, cred, **params)
        acciones += lote
        if len(lote) < 1000:
            break
        antes = lote[-1]["id"]
    llegadas = {}
    for a in sorted(acciones, key=lambda a: a["date"]):
        datos = a["data"]
        link = datos.get("card", {}).get("shortLink")
        destino = (datos.get("listAfter") or datos.get("list") or {}).get("name")
        if link and destino in TERMINADA and link not in llegadas:
            llegadas[link] = a["date"][:10]
    return llegadas


def construir(hoy=None, ahora=None):
    ahora = ahora or dt.datetime.now()
    hoy = hoy or ahora.date()
    tarjetas = leer_tablero()
    llegadas = leer_terminos(INICIO)
    filas = leer_estimacion()
    en_csv = {(f["trello"] or "").strip() for f in filas}

    # Universo del HITO 1, tarjeta por tarjeta. "Backlog del Backlog" son
    # ideas, no compromiso (el responsable, 23/09), y no entra en ningun bloque.
    universo, sin_tarjeta, gestion = [], [], []
    for f in filas:
        if f["hito"] != "1":
            continue
        link = (f["trello"] or "").strip()
        if not link:
            gestion.append({"nombre": f["tarea"], "horas": float(f["horas_cont"])})
            continue
        t = tarjetas.get(link)
        if t is None:
            sin_tarjeta.append(f["tarea"])     # borrada o fuera del tablero: no se cuenta
            continue
        if t["columna"] == "Backlog del Backlog":
            continue
        universo.append({"link": link, "nombre": t["nombre"], "columna": t["columna"],
                         "bloque": "Extras" if f["epica"] == "Extras" else f["epica"],
                         "horas": float(f["horas_cont"])})
    # Trabajo que aparecio en Trello despues del plan: Extras, sin horas
    # inventadas. Fuera lo que no se movio desde el inicio del hito.
    for link, t in tarjetas.items():
        if (link in en_csv or t["columna"] == "Backlog del Backlog"
                or t["actividad"] < INICIO.isoformat()):
            continue
        universo.append({"link": link, "nombre": t["nombre"], "columna": t["columna"],
                         "bloque": "Extras", "horas": None})
    for u in universo:
        u["estado"] = estado_tarjeta(u["columna"])
        # Sin movimiento registrado (p. ej. creada directo en DEV): ultima actividad.
        u["termino"] = (llegadas.get(u["link"]) or tarjetas[u["link"]]["actividad"]) \
            if u["estado"] == "terminada" else None

    def resumen(items):
        r = {"total": len(items), "terminada": 0, "revision": 0, "curso": 0, "pendiente": 0,
             "horas_est": 0.0, "n_est": 0}
        for u in items:
            r[u["estado"]] += 1
            if u["horas"] is not None:
                r["horas_est"] += u["horas"]
                r["n_est"] += 1
        r["pct"] = r["terminada"] / r["total"] * 100 if r["total"] else 0.0
        r["abiertas"] = r["total"] - r["terminada"]
        return r

    plan = [dict(resumen([u for u in universo if u["bloque"] == e]), nombre=e) for e in PLAN]
    plan_total = resumen([u for u in universo if u["bloque"] in PLAN])
    extras = resumen([u for u in universo if u["bloque"] == "Extras"])
    extras["sin_estimar"] = extras["total"] - extras["n_est"]
    hito = resumen(universo)

    # Ritmo real: tarjetas que llegaron a DEV/Terminado por dia habil. La parte
    # de hoy ya trabajada cuenta, asi el ritmo no salta a medianoche.
    frac = fraccion_jornada(ahora)
    transcurridos = dias_habiles(INICIO, hoy) + frac
    desde_rec = hoy - dt.timedelta(days=VENTANA_RECIENTE)
    dias_rec = dias_habiles(desde_rec, hoy) + frac
    term = [u["termino"] for u in universo if u["termino"] and u["termino"] >= INICIO.isoformat()]
    n_rec = sum(1 for d in term if d >= desde_rec.isoformat())
    ritmos = [
        {"nombre": "Desde el %s" % INICIO.strftime("%d/%m"), "n": len(term), "dias": transcurridos},
        {"nombre": "Últimas 2 semanas", "n": n_rec, "dias": dias_rec},
    ]
    restantes = max(0.0, dias_habiles(hoy, FIN_HITO1) - frac)
    for r in ritmos:
        r["ritmo"] = r["n"] / r["dias"] if r["dias"] >= 0.5 else 0.0
        if r["ritmo"] > 0:
            r["dias_faltan"] = hito["abiertas"] / r["ritmo"]
            fecha = sumar_habiles(hoy, r["dias_faltan"])
            r["cierre"] = fecha
            r["desvio"] = (dias_habiles(FIN_HITO1, fecha) if fecha > FIN_HITO1
                           else -dias_habiles(fecha, FIN_HITO1))
        else:
            r["dias_faltan"], r["cierre"], r["desvio"] = None, None, None
        r["capacidad"] = r["ritmo"] * restantes        # tarjetas que caben hasta el 30/10

    # Semanas: terminadas por semana (lunes a domingo) desde el inicio.
    semanas = []
    for i in range((hoy - INICIO).days // 7 + 1):
        ini = INICIO + dt.timedelta(days=7 * i)
        fin = ini + dt.timedelta(days=7)
        semanas.append({"label": "S%d" % (i + 1), "inicio": ini.strftime("%d/%m"),
                        "n": sum(1 for d in term if ini.isoformat() <= d < fin.isoformat())})

    en_curso = sorted((u for u in universo if u["estado"] in ("curso", "revision")),
                      key=lambda u: (u["estado"] != "revision", u["nombre"]))

    return {
        "hoy": hoy, "ahora": ahora, "actualizado": ahora.strftime("%d/%m/%Y %H:%M"),
        "dia": dias_habiles(INICIO, hoy) + 1, "plan_dias": dias_habiles(INICIO, FIN_HITO1),
        "fin1": FIN_HITO1, "restantes": restantes,
        "plan": plan, "plan_total": plan_total, "extras": extras, "hito": hito,
        "gestion": gestion, "sin_tarjeta": sin_tarjeta,
        "ritmos": ritmos, "semanas": semanas, "en_curso": en_curso,
    }


def render(d):
    from plantilla_avance import html  # plantilla en el mismo directorio
    return html(d)


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    datos = construir()
    salida = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "tablero-avance.html")
    io.open(salida, "w", encoding="utf-8", newline="\n").write(render(datos))
    print("Escrito: %s" % salida)
    for r in datos["ritmos"]:
        print("%s: %d terminadas, %.2f tarjetas/dia, cierre %s (%s dias habiles vs 30/10)" % (
            r["nombre"], r["n"], r["ritmo"], r["cierre"], r["desvio"]))
    print("Abiertas HITO 1: %d (%d en revision) de %d" % (
        datos["hito"]["abiertas"], datos["hito"]["revision"], datos["hito"]["total"]))
