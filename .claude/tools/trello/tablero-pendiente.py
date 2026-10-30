"""Tablero de lo PENDIENTE del HITO 1: ¿llegamos a la fecha objetivo?

Lee Trello en vivo y el CSV de estimacion (reusa tablero-avance.py) y escribe un
HTML local; no publica nada ni gasta tokens.

    python .claude/tools/trello/tablero-pendiente.py [salida.html]

No muta nada en Trello: solo lee.
"""

import datetime as dt
import html
import importlib.util
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("tablero_avance", os.path.join(AQUI, "tablero-avance.py"))
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

# Decision pendiente del responsable (2026-09-30): ¿la columna "Backlog" cuenta como
# trabajo pendiente del HITO 1? Con False esas tarjetas salen del calculo.
BACKLOG_CUENTA = True

# Dos jornadas: la del plan (lo que exige la fecha objetivo) y la real medida (9 h de
# lunes a viernes + 2 sabados de 4 h al mes, prorrateados: 203 h / 21.7 dias).
JORNADAS = [("Plan", base.HORAS_DIA), ("Real", 9.35)]

# Los 4 sabados de 4 h del periodo (base.SABADOS); no se descuentan los ya trabajados.
HORAS_SABADOS = base.SABADOS * base.HORAS_SABADO


def calcular(ahora=None):
    ahora = ahora or dt.datetime.now()
    hoy = ahora.date()
    tarjetas = base.leer_tablero()
    pendientes = []   # {nombre, epica, estado, horas, estimada}
    en_csv = set()
    for f in base.leer_estimacion():
        if f["hito"] != "1":
            continue
        link = (f["trello"] or "").strip()
        horas = float(f["horas_cont"])
        if not link:
            pendientes.append({"nombre": f["tarea"], "epica": f["epica"], "estado": "gestion",
                               "horas": horas, "estimada": True})
            continue
        en_csv.add(link)
        t = tarjetas.get(link)
        if t is None:            # tarjeta borrada o fuera del tablero: no se sabe, no se cuenta
            continue
        estado = base.ESTADOS.get(t["columna"], "pendiente")
        if t["columna"] == "Backlog del Backlog" or estado == "hecho":
            continue
        if t["columna"] == "Backlog" and not BACKLOG_CUENTA:
            continue
        pendientes.append({"nombre": t["nombre"], "epica": f["epica"], "estado": estado,
                           "horas": horas, "estimada": True})
    # Tarjetas vivas sin fila en el CSV: cuentan con la estimacion por defecto,
    # pero solo si siguen sin terminar (las del DEV ya estan hechas).
    for link, t in tarjetas.items():
        if link in en_csv or t["actividad"] < base.INICIO.isoformat():
            continue
        estado = base.ESTADOS.get(t["columna"], "pendiente")
        if t["columna"] == "Backlog del Backlog" or estado == "hecho":
            continue
        if t["columna"] == "Backlog" and not BACKLOG_CUENTA:
            continue
        pendientes.append({"nombre": t["nombre"], "epica": "Extras", "estado": estado,
                           "horas": base.HORAS_SIN_ESTIMAR * 1.2, "estimada": False})

    # Los dias restantes descuentan lo que ya paso de hoy.
    dias = base.dias_habiles(hoy, base.FIN_HITO1) - base.fraccion_jornada(ahora)
    h_gestion = sum(p["horas"] for p in pendientes if p["estado"] == "gestion")
    h_total = sum(p["horas"] for p in pendientes)
    escenarios = []
    for nombre, jornada in JORNADAS:
        capacidad = dias * jornada + HORAS_SABADOS
        fila = {"nombre": nombre, "jornada": jornada, "capacidad": capacidad}
        for clave, pend in (("con", h_total), ("sin", h_total - h_gestion)):
            atraso = (pend - capacidad) / jornada          # >0 atraso, <0 adelanto
            cierre = base.sumar_habiles(hoy, max(0.0, (pend - HORAS_SABADOS) / jornada))
            fila[clave] = {"pendiente": pend, "atraso": atraso, "cierre": cierre}
        escenarios.append(fila)
    return {"ahora": ahora, "dias": dias, "pendientes": pendientes, "h_gestion": h_gestion,
            "h_total": h_total, "escenarios": escenarios}


def _atraso(d):
    if abs(d) < 0.05:
        return "en fecha", "ok"
    return ("%.1f días de atraso" % d, "mal") if d > 0 else ("%.1f días de adelanto" % -d, "ok")


def render(d):
    e = html.escape
    filas = []
    for s in d["escenarios"]:
        celdas = ""
        for clave, titulo in (("con", "con Gestión y cierre"), ("sin", "sin Gestión y cierre")):
            x = s[clave]
            txt, cls = _atraso(x["atraso"])
            celdas += ('<td><b class="%s">%s</b><small>%.0f h pendientes · cierra %s</small></td>'
                       % (cls, txt, x["pendiente"], x["cierre"].strftime("%d/%m")))
        filas.append("<tr><th>%s · %.2f h/día<small>capacidad %.0f h</small></th>%s</tr>"
                     % (e(s["nombre"]), s["jornada"], s["capacidad"], celdas))

    por_epica = {}
    for p in d["pendientes"]:
        k = por_epica.setdefault(p["epica"], {"curso": 0.0, "pendiente": 0.0, "gestion": 0.0})
        k[p["estado"]] += p["horas"]
    epicas = "".join(
        "<tr><td>%s</td><td class=n>%.1f</td><td class=n>%.1f</td><td class=n>%.1f</td></tr>"
        % (e(n), v["curso"], v["pendiente"], v["gestion"]) for n, v in por_epica.items())
    curso = "".join("<li>%s <span class=n>%.1f h</span></li>" % (e(p["nombre"]), p["horas"])
                    for p in d["pendientes"] if p["estado"] == "curso")
    sin_est = [p for p in d["pendientes"] if not p["estimada"]]
    aviso = ("<p class=aviso>%d tarjetas vivas sin fila en el Excel entran con %.1f h por defecto: %s.</p>"
             % (len(sin_est), base.HORAS_SIN_ESTIMAR * 1.2, e("; ".join(p["nombre"] for p in sin_est)))
             if sin_est else "")
    return """<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Pendiente del HITO 1</title>
<style>
:root{--bg:#f3f5f7;--card:#fff;--ink:#16222e;--mut:#5b6b7a;--line:#d9e0e6;--ok:#0f766e;--mal:#b91c1c}
@media(prefers-color-scheme:dark){:root{--bg:#0f171f;--card:#17222c;--ink:#e6edf3;--mut:#9aa9b8;--line:#2a3947;--ok:#4fd1c5;--mal:#f87171}}
body{margin:0;padding:24px 16px 40px;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,"Segoe UI",sans-serif}
.w{max-width:860px;margin:auto}h1{font-size:1.4rem;margin:0 0 4px}h2{font-size:1rem;margin:28px 0 8px}
p{color:var(--mut);margin:0 0 12px}table{width:100%%;border-collapse:collapse;background:var(--card);border:1px solid var(--line)}
th,td{padding:10px 12px;border-top:1px solid var(--line);text-align:left;vertical-align:top}thead th{border-top:0;color:var(--mut);font-size:.8rem;font-weight:500}
small{display:block;color:var(--mut);font-weight:400}b{font-size:1.15rem}.ok{color:var(--ok)}.mal{color:var(--mal)}
.n{text-align:right;font-variant-numeric:tabular-nums}ul{padding-left:18px}.aviso{font-size:.85rem}
</style></head><body><div class="w">
<p><a href="hub.html">← Tableros</a></p>
<h1>¿Llegamos a la fecha objetivo?</h1>
<p>Solo lo pendiente: por hacer + en curso, sin lo entregado ni la reserva de fixes. Actualizado %(ahora)s ·
%(dias).1f días hábiles restantes + %(sab).0f h de sábados · Backlog %(backlog)s.</p>
<table><thead><tr><th>Escenario</th><th>Con Gestión y cierre (%(hg).0f h)</th><th>Sin Gestión y cierre</th></tr></thead>
<tbody>%(filas)s</tbody></table>
<h2>Pendiente por épica (horas con contingencia)</h2>
<table><thead><tr><th>Épica</th><th class=n>En curso</th><th class=n>Por hacer</th><th class=n>Gestión</th></tr></thead>
<tbody>%(epicas)s</tbody></table>%(aviso)s
<h2>En curso ahora</h2><ul>%(curso)s</ul>
</div></body></html>""" % {
        "ahora": d["ahora"].strftime("%d/%m/%Y %H:%M"), "dias": d["dias"], "sab": HORAS_SABADOS,
        "backlog": "cuenta como pendiente" if BACKLOG_CUENTA else "no cuenta",
        "hg": d["h_gestion"], "filas": "".join(filas), "epicas": epicas, "aviso": aviso, "curso": curso}


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    datos = calcular()
    salida = sys.argv[1] if len(sys.argv) > 1 else os.path.join(base.RAIZ, "tablero-pendiente.html")
    with open(salida, "w", encoding="utf-8") as f:
        f.write(render(datos))
    print("Escrito:", salida)
    for s in datos["escenarios"]:
        for clave in ("con", "sin"):
            x = s[clave]
            print("%s %s Gestión: pendiente %.0f h, capacidad %.0f h, %s" % (
                s["nombre"], clave, x["pendiente"], s["capacidad"], _atraso(x["atraso"])[0]))
