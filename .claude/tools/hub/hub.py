"""Hub local de tableros del sistema: una portada con un rectángulo por tablero.

    python .claude/tools/hub/hub.py [--actualizar pendiente,avance,auditoria]

Escribe hub.html en la raiz (fuera de git). Cada rectangulo abre el HTML local
de su tablero y muestra cuándo se generó. Con --actualizar regenera antes los
tableros pedidos (leen Trello o miden los repos; no publican ni gastan tokens).
"""

import argparse
import datetime as dt
import glob
import html
import json
import math
import os
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", "..", ".."))
PY = sys.executable

# clave, título, pregunta que responde, archivo local, comando para regenerar, enlace publicado (opcional)
TABLEROS = [
    ("pert", "PERT por fase",
     "Estimación por HITO y épica, tarea por tarea, contra el estado real de Trello.",
     "tablero-pert.html", [PY, ".claude/tools/trello/tablero-pert.py"], None),
    ("pendiente", "¿Llegamos a la fecha objetivo?",
     "Lo que falta del HITO 1 contra la capacidad del equipo: días de atraso con y sin Gestión.",
     "tablero-pendiente.html", [PY, ".claude/tools/trello/tablero-pendiente.py"], None),
    ("avance", "Avance del HITO 1",
     "Horas entregadas por épica, plan por semanas y cierre proyectado.",
     "tablero-avance.html", [PY, ".claude/tools/trello/tablero-avance.py"], None),
    ("auditoria", "Salud de arquitectura",
     "Dependencias, tamaño, complejidad y duplicación de web-app y api-core, medición tras medición.",
     "auditoria-arquitectura.html",
     [PY, ".claude/tools/auditoria/medir.py", "&&", PY, ".claude/tools/auditoria/render.py"], None),
    ("codex", "Rondas de Codex",
     "Por PR abierto: ronda, limpias seguidas (2 = listo para Revisor Principal), último resultado y prioridad.",
     "rondas-codex.html", [PY, ".claude/tools/hub/rondas.py"], None),
]


META = 85
PESOS = {"dep": 30, "mar": 20, "tam": 15, "cx": 15, "dup": 10, "mue": 10}


def _lin(valor, cero):
    return math.floor(100 * (1 - max(0.0, min(1.0, valor / cero))) + 0.5)


def puntajes():
    """Puntaje de web-app y api-core de la última medición. Misma fórmula que
    plantilla.html (auditoria); si allá cambia, cambiarla acá."""
    archivos = sorted(glob.glob(os.path.join(RAIZ, ".claude", "tools", "auditoria", "historial", "*.json")))
    if not archivos:
        return None
    with open(archivos[-1], encoding="utf-8") as f:
        d = json.load(f)
    w, a = d["web"], d["api"]

    def media_d(mods):
        return sum(m["d"] for m in mods) / len(mods)

    def total(o):
        pesos = sum(PESOS[k] for k in o)
        return math.floor(sum(PESOS[k] * v for k, v in o.items()) / pesos + 0.5) if pesos else None

    ow = {}
    dep = w["dependencias"]
    if dep.get("medido"):
        err = sum(1 for v in dep["violaciones"] if v["severidad"] == "error")
        ow["dep"] = max(0, 100 - 20 * err - 2 * (len(dep["violaciones"]) - err))
        if dep["modulos"]:
            ow["mar"] = _lin(media_d(dep["modulos"]), 0.7)
    if w["tamano"].get("medido"):
        ow["tam"] = _lin(len(w["tamano"]["grandes"]) / w["tamano"]["total"], 0.1)
        if w["complejidad"].get("medido"):
            ow["cx"] = _lin(len(w["complejidad"]["funciones"]) / w["tamano"]["total"], 0.1)
    k = w["codigo_muerto"]
    if k.get("medido") and k.get("exports_totales"):
        ow["mue"] = _lin((len(k["exports"]) + len(k["archivos"])) / k["exports_totales"], 0.05)
    if w["duplicacion"].get("medido"):
        ow["dup"] = _lin(w["duplicacion"]["porcentaje"], 6)

    oa = {}
    c = a["capas"]
    if c.get("medido"):
        oa["dep"] = max(0, 100 - 20 * len(c["violaciones"]))
        if c["modulos"]:
            oa["mar"] = _lin(media_d(c["modulos"]), 0.7)
    if a["tamano"].get("medido"):
        oa["tam"] = _lin(len(a["tamano"]["grandes"]) / a["tamano"]["total"], 0.1)
        if a.get("complejidad", {}).get("medido"):
            oa["cx"] = _lin(len(a["complejidad"]["funciones"]) / a["tamano"]["total"], 0.1)
    km = a.get("codigo_muerto", {})
    if km.get("medido") and km.get("exports_totales"):
        oa["mue"] = _lin((len(km.get("exports", [])) + len(km.get("miembros", []))) / km["exports_totales"], 0.05)
    if a["duplicacion"].get("medido"):
        oa["dup"] = _lin(a["duplicacion"]["porcentaje"], 6)
    return {"fecha": d["fecha"], "web": total(ow), "api": total(oa)}


def franja():
    p = puntajes()
    if not p or p["web"] is None or p["api"] is None:
        return ""
    e = html.escape

    def item(nombre, n):
        falta = META - n
        estado = "llegó" if falta <= 0 else "faltan %d" % falta
        ancho = max(0, min(100, n))
        return ('<div class="meta"><span class="nombre">%s</span><b>%d</b><span class="flecha">→ %d</span>'
                '<span class="falta">%s</span><div class="barra"><i style="width:%d%%"></i>'
                '<u style="left:%d%%"></u></div></div>' % (e(nombre), n, META, estado, ancho, META))

    return ('<a class="franja" href="auditoria-arquitectura.html#t-meta85"><div class="t">Salud de arquitectura: '
            'meta %d puntos <small>medición %s · ver cómo llegar</small></div>%s%s</a>'
            % (META, e(p["fecha"]), item("web-app", p["web"]), item("api-core", p["api"])))


def actualizar(clave):
    for k, _, _, _, cmd, _ in TABLEROS:
        if k != clave or not cmd:
            continue
        pasos, actual = [], []
        for parte in cmd:
            if parte == "&&":
                pasos.append(actual)
                actual = []
            else:
                actual.append(parte)
        pasos.append(actual)
        for paso in pasos:
            print("Actualizando %s: %s" % (clave, " ".join(os.path.basename(p) for p in paso[1:])))
            if subprocess.run(paso, cwd=RAIZ).returncode != 0:
                print("  no se pudo actualizar %s; se deja el anterior" % clave)
                return


def tarjeta(titulo, que, archivo, publicado):
    e = html.escape
    ruta = os.path.join(RAIZ, archivo)
    if os.path.exists(ruta):
        hora = dt.datetime.fromtimestamp(os.path.getmtime(ruta)).strftime("%d/%m %H:%M")
        estado = "Generado %s" % hora
        cuerpo = '<a class="card" href="%s">' % e(archivo)
        cierre = "</a>"
    else:
        estado = "Aún no generado"
        cuerpo = '<div class="card off">'
        cierre = "</div>"
    extra = ('<span class="pub"><a href="%s" target="_blank" rel="noopener">versión publicada</a></span>'
             % e(publicado)) if publicado else ""
    return ('<div class="cell">%s<h2>%s</h2><p>%s</p><span class="estado">%s</span>%s%s</div>'
            % (cuerpo, e(titulo), e(que), e(estado), cierre, extra))


def render():
    celdas = "".join(tarjeta(t, q, a, p) for _, t, q, a, _, p in TABLEROS)
    hoy = dt.datetime.now().strftime("%d/%m/%Y %H:%M")
    return """<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>Tableros del sistema</title>
<style>
:root{--bg:#f3f5f7;--card:#fff;--ink:#16222e;--mut:#5b6b7a;--line:#d9e0e6;--acc:#2a78d6}
@media(prefers-color-scheme:dark){:root{--bg:#0f171f;--card:#17222c;--ink:#e6edf3;--mut:#9aa9b8;--line:#2a3947;--acc:#7ea8ff}}
*{box-sizing:border-box}body{margin:0;padding:32px 16px 48px;background:var(--bg);color:var(--ink);font:15px/1.45 system-ui,"Segoe UI",sans-serif}
.w{max-width:960px;margin:auto}h1{font-size:1.5rem;margin:0 0 4px}.sub{color:var(--mut);margin:0 0 24px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px}
.cell{display:grid;gap:6px}
.card{display:grid;gap:8px;align-content:start;min-height:150px;padding:18px;background:var(--card);border:1px solid var(--line);border-radius:12px;color:inherit;text-decoration:none}
a.card:hover,a.card:focus-visible{border-color:var(--acc);outline:2px solid var(--acc);outline-offset:1px}
.card.off{opacity:.6}.card h2{margin:0;font-size:1.05rem}.card p{margin:0;color:var(--mut);font-size:.9rem}
.franja{display:grid;gap:10px;margin:0 0 20px;padding:16px 18px;background:var(--card);border:1px solid var(--line);border-radius:12px;color:inherit;text-decoration:none}
.franja:hover,.franja:focus-visible{border-color:var(--acc);outline:2px solid var(--acc);outline-offset:1px}
.franja .t{font-weight:600}.franja small{font-weight:400;color:var(--mut);margin-left:8px}
.meta{display:grid;grid-template-columns:80px 48px 60px 1fr;gap:8px;align-items:center}
.meta b{font-size:1.3rem;font-variant-numeric:tabular-nums}.meta .nombre,.meta .falta,.meta .flecha{color:var(--mut);font-size:.85rem}
.barra{position:relative;height:8px;background:var(--line);border-radius:4px;grid-column:1/-1}
.barra i{position:absolute;inset:0 auto 0 0;background:var(--acc);border-radius:4px}.barra u{position:absolute;top:-3px;bottom:-3px;width:2px;background:var(--ink)}
.estado{font-size:.78rem;color:var(--mut);margin-top:auto}.pub{font-size:.8rem}.pub a{color:var(--acc)}
</style></head><body><div class="w">
<h1>Tableros del sistema</h1><p class="sub">Un rectángulo por tablero. Hub generado %s.</p>
%s<div class="grid">%s</div></div></body></html>""" % (hoy, franja(), celdas)


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("--actualizar", default="")
    args = ap.parse_args()
    for clave in [c for c in args.actualizar.split(",") if c]:
        actualizar(clave)
    salida = os.path.join(RAIZ, "hub.html")
    with open(salida, "w", encoding="utf-8") as f:
        f.write(render())
    print("Escrito:", salida)
