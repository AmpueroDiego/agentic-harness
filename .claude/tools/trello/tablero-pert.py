"""Tablero PERT con el mismo formato del Excel de estimacion, mas el estado real de Trello.

    python .claude/tools/trello/tablero-pert.py [salida.html]

Tabla "Estimacion completa" (filas 1-56 del Excel), subtotal / reserva / total y fechas por HITO,
y aparte lo agregado despues del Excel (filas 57+, "Extras") y las tarjetas nuevas de Trello.
Lee Trello en vivo y el CSV de estimacion (reusa tablero-avance.py). Solo lee.
"""

import datetime as dt
import html
import importlib.util
import os
import re
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("tablero_avance", os.path.join(AQUI, "tablero-avance.py"))
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)

H_EXCEL = 9.8            # horas por dia del Excel (col. "Dias (9h)")
H_REAL = 9.35            # jornada real medida, para proyectar lo que falta
RESERVA = 0.15
INICIO = dt.date(2026, 9, 21)
ULTIMA_FILA_EXCEL = 56   # lo que sigue (57+) se agrego despues
PASAN_AL_HITO1 = {29, 30, 31, 45, 48}  # decisión del responsable (30/09 y 02/10): del resto del HITO 2 solo estas se agregan ahora
DESDE_EXCEL = dt.date(2026, 9, 21)
ORDEN_COL = ["En revisión (Revisor Principal)", "En revisión (el responsable)", "En desarrollo", "Backlog", "DEV", "Terminado", "Backlog del Backlog"]
e = html.escape

# Columna "Track" del Excel por numero de fila (el CSV no la trae).
TRACKS = {}
for _rng, _t in [((1, 19), "Backlog Trello - 'Backlog' (prioridad ahora)"), ((20, 24), "Ámbito / Tenant"),
                 ((25, 25), "Entidad"), ((26, 26), "Acuerdo"), ((27, 27), "Resumen"), ((28, 28), "Estado"),
                 ((29, 29), "Categorías"), ((30, 30), "Pruebas Flujo"), ((31, 31), "Continuidad operativa 1"),
                 ((32, 33), "Gestión"), ((34, 34), "Gestión - HITO 1"), ((35, 35), "Actividades de Soporte"),
                 ((36, 36), "Código de Operación"), ((37, 40), "Proveedor - Mensajería"), ((41, 44), "Proveedor - Llamada"),
                 ((45, 45), "Notificaciones"), ((46, 48), "Distribución automática de entidades"),
                 ((49, 49), "Reportería"), ((50, 52), "Pruebas de carga"), ((53, 54), "Gestión"),
                 ((55, 55), "Gestión - HITO 2"), ((56, 56), "Actividades de Soporte")]:
    for _i in range(_rng[0], _rng[1] + 1):
        TRACKS[_i] = _t

ETIQ = {"hecho": "Hecho", "curso": "En curso", "pendiente": "Por hacer", "gestion": "Gestión", "eliminada": "Almacenada", "hito2": "HITO 2"}

CSS = """:root{--bg:#f3f5f7;--card:#fff;--ink:#16222e;--mut:#5b6b7a;--line:#d9e0e6;--head:#e8edf2;--ok:#0f766e;--okb:#d6efec;--cur:#2563eb;--curb:#dce7fb;--pen:#64748b;--penb:#e6eaee;--ges:#b45309;--gesb:#fbe6cc;--del:#b42318;--delb:#fde4e1}
@media(prefers-color-scheme:dark){:root{--bg:#0f171f;--card:#17222c;--ink:#e6edf3;--mut:#9aa9b8;--line:#2a3947;--head:#22303c;--ok:#4fd1c5;--okb:#12403c;--cur:#7ea8ff;--curb:#1c2f57;--pen:#9aa8b6;--penb:#26323d;--ges:#f0a95a;--gesb:#4a3316;--del:#ff8a7a;--delb:#4a1f1a}}
*{box-sizing:border-box}body{margin:0;padding:24px 14px 56px;background:var(--bg);color:var(--ink);font:14px/1.4 system-ui,"Segoe UI",sans-serif}
.w{max-width:1280px;margin:auto}h1{font-size:1.5rem;margin:0}h2{font-size:1.1rem;margin:26px 0 8px}a{color:inherit}.hub{font-size:.85rem;color:var(--mut)}.sub{color:var(--mut);margin:4px 0 18px}
.sup{display:flex;gap:24px;flex-wrap:wrap;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 16px;margin-bottom:8px}
.sup div{min-width:150px}.sup b{display:block;font-size:1.05rem;font-variant-numeric:tabular-nums}.sup span{color:var(--mut);font-size:.78rem}
.scroll{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:12px}
table{width:100%;border-collapse:collapse;font-size:.84rem}th,td{padding:5px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:var(--head);font-weight:600;font-size:.76rem;position:sticky;top:0;white-space:nowrap}td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
td.ep{font-weight:600;white-space:nowrap}tr.primero td{border-top:2px solid var(--line)}
tr.hecho td.t{color:var(--mut)}tr.eliminada td{color:var(--mut);text-decoration:line-through}tr.eliminada td.e{text-decoration:none}
tr.sub td{background:var(--head);font-weight:600}tr.tot td{font-weight:700;border-top:2px solid var(--ink)}
.chip{display:inline-block;padding:1px 8px;border-radius:10px;font-size:.72rem;white-space:nowrap;text-decoration:none}
.chip.hecho{background:var(--okb);color:var(--ok)}.chip.curso{background:var(--curb);color:var(--cur)}.chip.pendiente{background:var(--penb);color:var(--pen)}.chip.gestion{background:var(--gesb);color:var(--ges)}.chip.eliminada{background:var(--delb);color:var(--del)}.chip.hito2{background:var(--head);color:var(--mut);border:1px solid var(--line)}.chip.mov{background:var(--curb);color:var(--cur);margin-left:4px}tr.hito2 td{color:var(--mut)}
.bloques{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:14px}
.bloque{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px 16px}.bloque h3{margin:0 0 6px;font-size:1rem}
.bloque table td,.bloque table th{padding:3px 6px}.bloque th{position:static;background:none;color:var(--mut)}
.bar{display:flex;height:8px;border-radius:4px;overflow:hidden;background:var(--penb);margin:4px 0 6px}.bar i{display:block}.bar .hecho{background:var(--ok)}.bar .curso{background:var(--cur)}
details{border-top:1px solid var(--line);padding:8px 0}summary{cursor:pointer;font-weight:600}summary small{font-weight:400;color:var(--mut)}
.nota{color:var(--mut);font-size:.8rem;margin-top:16px}.leyenda{color:var(--mut);font-size:.78rem;margin:6px 2px}"""


def enlace(texto, link):
    if not link:
        return e(texto)
    return '<a href="%s" target="_blank" rel="noopener">%s</a>' % ("https://trello.com" + "/c/" + link, e(texto))


def leer():
    """Tarjetas con fecha de creacion (los 8 primeros hex del id son el timestamp)."""
    cred = base.credenciales()
    tablero = cred["defaultBoardId"]
    listas = {l["id"]: l["name"] for l in base.api("boards/%s/lists" % tablero, cred)}
    return {t["shortLink"]: {"nombre": t["name"], "columna": listas.get(t["idList"], "?"),
                             "creada": dt.date.fromtimestamp(int(t["id"][:8], 16))}
            for t in base.api("boards/%s/cards" % tablero, cred, fields="name,idList,shortLink")}


def calcular():
    tarjetas = leer()
    filas = base.leer_estimacion()
    en_csv = {(f["trello"] or "").strip() for f in filas}
    tareas = []
    for f in filas:
        link = (f["trello"] or "").strip()
        t = tarjetas.get(link)
        if not link:
            estado, col = "gestion", "sin tarjeta (gestión)"
        elif t is None:
            estado, col = "eliminada", "tarjeta archivada"
        elif t["columna"] == "Backlog del Backlog":
            estado, col = "eliminada", "almacenada en Backlog del Backlog"
        else:
            estado, col = base.ESTADOS.get(t["columna"], "pendiente"), t["columna"]
        n = int(f["fila"])
        hito = 1 if n in PASAN_AL_HITO1 else int(f["hito"])
        movida = n in PASAN_AL_HITO1
        if hito == 2:
            estado, col = "hito2", "HITO 2 (no se considera ahora); en Trello: %s" % col
        elif movida and estado == "eliminada":
            estado, col = "pendiente", "agregado al HITO 1; su tarjeta sigue en Backlog del Backlog"
        riesgo = f["riesgo"]
        tareas.append({
            "n": n, "epica": f["epica"], "track": TRACKS.get(n, "Extras (agregadas después del Excel)"),
            "tarea": f["tarea"], "cx": f["complejidad"], "h": float(f["horas"]), "riesgo": riesgo,
            "cont": {"Bajo": 15, "Medio": 20, "Alto": 30}.get(riesgo, 20), "hc": float(f["horas_cont"]),
            "estado": estado, "col": col, "link": link, "hito": hito, "movida": movida})
    nuevas = [dict(t, link=k) for k, t in tarjetas.items() if k not in en_csv and t["creada"] >= DESDE_EXCEL]
    previas = sum(1 for k, t in tarjetas.items() if k not in en_csv and t["creada"] < DESDE_EXCEL
                  and t["columna"] != "Backlog del Backlog")
    return tareas, nuevas, previas


def chip(t):
    extra = '<span class="chip mov">agregado al HITO 1</span>' if t.get("movida") else ""
    return '<span class="chip %s" title="%s">%s</span>%s' % (t["estado"], e(t["col"]), ETIQ[t["estado"]], extra)


def tabla_estimacion(ts):
    cab = ("<tr><th>#</th><th>ÉPICA</th><th>Track</th><th>Tarea</th><th>Compl.</th><th>Horas</th><th>Riesgo</th>"
           "<th>Cont. %</th><th>Horas c/cont.</th><th>Días (9.8h)</th><th>Estado en Trello</th></tr>")
    filas, ultima = [], None
    for t in ts:
        nueva = t["epica"] != ultima
        ultima = t["epica"]
        filas.append(
            '<tr class="%s%s"><td class="n">%d</td><td class="ep">%s</td><td>%s</td><td class="t">%s</td><td>%s</td>'
            '<td class="n">%g</td><td>%s</td><td class="n">%d%%</td><td class="n">%.1f</td><td class="n">%.2f</td><td class="e">%s</td></tr>'
            % (t["estado"], " primero" if nueva else "", t["n"], e(t["epica"]) if nueva else "", e(t["track"]),
               enlace(t["tarea"], t["link"]), e(t["cx"]), t["h"], e(t["riesgo"]), t["cont"], t["hc"],
               t["hc"] / H_EXCEL, chip(t)))
    return '<div class="scroll"><table>%s%s</table></div>' % (cab, "".join(filas))


def bloque_hito(nombre, ts, inicio, hoy, meta_excel):
    vivas = [t for t in ts if t["estado"] != "eliminada"]
    sub_h = sum(t["h"] for t in vivas)
    sub_hc = sum(t["hc"] for t in vivas)
    res = sub_hc * RESERVA
    tot = sub_hc + res
    dias = tot / H_EXCEL
    hechas = sum(t["hc"] for t in vivas if t["estado"] == "hecho")
    curso = sum(t["hc"] for t in vivas if t["estado"] == "curso")
    falta = sub_hc - hechas
    fin_real = base.sumar_habiles(hoy, max(1, int(-(-(falta * (1 + RESERVA)) // H_REAL))))
    filas = (
        '<tr><td>Subtotal</td><td class="n">%.0f h</td><td class="n">%.1f h c/cont.</td></tr>'
        '<tr><td>+ Reserva de fixes (%d%%)</td><td></td><td class="n">%.1f h</td></tr>'
        '<tr class="tot"><td>Total general</td><td></td><td class="n">%.1f h · %.1f días · %.1f sem.</td></tr>'
        '<tr><td>Inicio</td><td></td><td class="n">%s</td></tr>'
        '<tr><td>Término según el Excel</td><td></td><td class="n">%s</td></tr>'
        % (sub_h, sub_hc, RESERVA * 100, res, tot, dias, dias / 5, INICIO.strftime("%d/%m/%Y"), meta_excel))
    avance = (
        '<div class="bar"><i class="hecho" style="width:%.1f%%"></i><i class="curso" style="width:%.1f%%"></i></div>'
        '<table><tr><td>Hecho (Trello)</td><td class="n">%.0f h</td><td class="n">%.0f%%</td></tr>'
        '<tr><td>En curso</td><td class="n">%.0f h</td><td class="n">%.0f%%</td></tr>'
        '<tr><td>Falta (sin reserva)</td><td class="n">%.0f h</td><td class="n">%.0f%%</td></tr>'
        '<tr class="tot"><td>Terminaría al ritmo real (9.35 h/día, con reserva)</td><td></td><td class="n">%s</td></tr></table>'
        % (100 * hechas / sub_hc if sub_hc else 0, 100 * curso / sub_hc if sub_hc else 0,
           hechas, 100 * hechas / sub_hc if sub_hc else 0, curso, 100 * curso / sub_hc if sub_hc else 0,
           falta, 100 * falta / sub_hc if sub_hc else 0, fin_real.strftime("%d/%m/%Y")))
    # resumen por epica
    por_ep = {}
    for t in vivas:
        d = por_ep.setdefault(t["epica"], {"hc": 0.0, "hecho": 0.0, "n": 0})
        d["hc"] += t["hc"]
        d["n"] += 1
        if t["estado"] == "hecho":
            d["hecho"] += t["hc"]
    ep = "".join('<tr><td>%s</td><td class="n">%d</td><td class="n">%.1f</td><td class="n">%.1f</td><td class="n">%.0f%%</td></tr>'
                 % (e(k), v["n"], v["hc"], v["hc"] / H_EXCEL, 100 * v["hecho"] / v["hc"] if v["hc"] else 0)
                 for k, v in por_ep.items())
    return (
        '<div class="bloque"><h3>%s · totales y fechas</h3><table>%s</table></div>'
        '<div class="bloque"><h3>%s · avance real</h3>%s</div>'
        '<div class="bloque"><h3>%s · por épica</h3><table><tr><th>Épica</th><th>Tareas</th><th>Horas c/cont.</th><th>Días</th><th>Hecho</th></tr>%s</table></div>'
        % (nombre, filas, nombre, avance, nombre, ep))


def bloque_hito2(ts):
    sub_h = sum(t["h"] for t in ts)
    sub_hc = sum(t["hc"] for t in ts)
    por_ep = {}
    for t in ts:
        d = por_ep.setdefault(t["epica"], [0, 0.0])
        d[0] += 1
        d[1] += t["hc"]
    ep = "".join('<tr><td>%s</td><td class="n">%d</td><td class="n">%.1f</td><td class="n">%.1f</td></tr>'
                 % (e(k), v[0], v[1], v[1] / H_EXCEL) for k, v in por_ep.items())
    return ('<div class="bloque"><h3>HITO 2 · planificado, no se considera ahora</h3><table>'
            '<tr><td>Tareas</td><td class="n">%d</td></tr><tr><td>Subtotal</td><td class="n">%.0f h · %.1f h c/cont.</td></tr>'
            '<tr><td>No entra en los totales ni en las fechas del HITO 1</td><td></td></tr></table></div>'
            '<div class="bloque"><h3>HITO 2 · por épica</h3><table><tr><th>Épica</th><th>Tareas</th><th>Horas c/cont.</th><th>Días</th></tr>%s</table></div>'
            % (len(ts), sub_h, sub_hc, ep))


def repo_de(nombre):
    m = re.search(r"\(([^()]*)\)\s*$", nombre)
    return (m.group(1), nombre[:m.start()].strip()) if m else ("", nombre)


def nuevas_html(nuevas, previas):
    por_col = {}
    for t in nuevas:
        por_col.setdefault(t["columna"], []).append(t)
    cols = [c for c in ORDEN_COL if c in por_col] + [c for c in por_col if c not in ORDEN_COL]
    bl = []
    for c in cols:
        lista = sorted(por_col[c], key=lambda t: t["creada"], reverse=True)
        filas = "".join('<tr><td class="n">%s</td><td>%s</td><td>%s</td></tr>'
                        % (t["creada"].strftime("%d/%m"), enlace(repo_de(t["nombre"])[1], t["link"]), e(repo_de(t["nombre"])[0]))
                        for t in lista)
        bl.append('<details%s><summary>%s <small>%d tarjetas</small></summary><div class="scroll"><table><tr><th>Creada</th><th>Tarjeta</th><th>Repo</th></tr>%s</table></div></details>'
                  % (" open" if c in ("Backlog", "En desarrollo", "En revisión (el responsable)", "En revisión (Revisor Principal)") else "", e(c), len(lista), filas))
    return ('<h2>Tarjetas derivadas de las principales</h2><div class="leyenda">Desgloses de tarjetas principales que eran muy grandes o generales: sus horas ya están dentro de la principal, por eso no suman aparte. '
            '%d tarjetas creadas desde el %s. Además hay %d anteriores al Excel, casi todas ya en DEV o Terminado.</div>%s'
            % (len(nuevas), DESDE_EXCEL.strftime("%d/%m"), previas, "".join(bl)))


def render(tareas, nuevas, previas, ahora):
    hoy = ahora.date()
    # Notificaciones (fila 45) se muestra debajo de Continuidad operativa (31): el responsable, 21/10.
    excel = sorted((t for t in tareas if t["n"] <= ULTIMA_FILA_EXCEL), key=lambda t: 31.5 if t["n"] == 45 else t["n"])
    extras = [t for t in tareas if t["n"] > ULTIMA_FILA_EXCEL]
    h1 = [t for t in excel if t["hito"] == 1]
    h2 = [t for t in excel if t["hito"] == 2]
    sup = "".join('<div><b>%s</b><span>%s</span></div>' % kv for kv in [
        ("15% · 20% · 30%", "contingencia riesgo Bajo · Medio · Alto"), ("9.8 h", "horas por día (sáb. 9–13)"),
        ("21/09/2026", "fecha de inicio"), ("15%", "reserva de fixes post-entrega"),
        ("S · M · L · XL", "Simple · Media · Larga · Muy larga")])
    elim = [t for t in tareas if t["estado"] == "eliminada"]
    cuerpo = (
        '<h2>Supuestos</h2><div class="sup">%s</div>'
        '<h2>Estimación completa</h2><div class="leyenda">Filas 1–56 del Excel. «HITO 2» = planificado, no se considera ahora (solo #29, #30, #31, #45 y #48 pasaron al HITO 1). Tachadas = almacenadas (HITO 1 que pasó a Backlog del Backlog o con tarjeta archivada), no suman. La última columna es el estado real en Trello.</div>%s'
        '<h2>HITO 1 y HITO 2</h2><div class="bloques">%s</div><div class="bloques" style="margin-top:14px">%s</div>'
        % (sup, tabla_estimacion(excel),
           bloque_hito("HITO 1 (sin Gestión)", [t for t in h1 if not t["epica"].startswith("Gesti")], INICIO, hoy, "30/10/2026"),
           bloque_hito2(h2)))
    if extras:
        cuerpo += ('<h2>Agregadas después del Excel (Extras)</h2><div class="leyenda">Filas 57+ del CSV interno; no estaban en el Excel original y no entran en los totales de arriba.</div>%s'
                   % tabla_estimacion(extras))
    cuerpo += nuevas_html(nuevas, previas)
    return ('<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>PERT del sistema</title><style>%s</style></head><body><div class="w"><div class="hub"><a href="hub.html">← Tableros del sistema</a></div>'
            '<h1>PERT — estimación completa</h1><p class="sub">Mismo formato del Excel «estimacion-backlog-tecnico-pert» + estado real de Trello · generado %s · %d tareas almacenadas fuera del plan</p>%s'
            '<p class="nota">Hecho = En revisión, DEV, Listo para PROD o Terminado. Se considera solo el HITO 1 (más #29, #30, #31, #45 y #48 del HITO 2); el resto del HITO 2 queda a la vista pero fuera de los totales. '
            'Días = horas c/cont. ÷ 9.8, como la columna del Excel.</p></div></body></html>'
            % (CSS, ahora.strftime("%d/%m/%Y %H:%M"), len(elim), cuerpo))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ahora = dt.datetime.now()
    tareas, nuevas, previas = calcular()
    salida = sys.argv[1] if len(sys.argv) > 1 else os.path.join(base.RAIZ, "tablero-pert.html")
    with open(salida, "w", encoding="utf-8") as f:
        f.write(render(tareas, nuevas, previas, ahora))
    print("Escrito:", salida)
