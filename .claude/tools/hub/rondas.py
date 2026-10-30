"""Vista de las rondas de Codex por PR, leída de docs/runs/supercodex-rondas.md.

    python .claude/tools/hub/rondas.py

Escribe rondas-codex.html en la raíz (fuera de git). Los PRs abiertos salen de `gh`; si gh falla,
se usa solo el registro. Sin librerías externas.
"""

import datetime as dt
import html
import json
import os
import re
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", "..", ".."))
REGISTRO = os.path.join(RAIZ, "docs", "runs", "supercodex-rondas.md")
SALIDA = os.path.join(RAIZ, "rondas-codex.html")
ORG = "<org>"
REPOS = ["api-core", "web-app"]
LISTO = 2  # limpias seguidas que dejan un PR listo para Revisor Principal
e = html.escape


def leer_registro():
    """Filas de la tabla 'Rondas de /supercodex', en el orden del archivo (la última de un PR es la vigente)."""
    filas, dentro = [], False
    with open(REGISTRO, encoding="utf-8") as f:
        for linea in f:
            if linea.startswith("## Rondas de"):
                dentro = True
                continue
            if dentro and linea.startswith("#"):
                break
            if not dentro or not linea.startswith("|"):
                continue
            c = [x.strip() for x in linea.strip().strip("|").split("|")]
            if len(c) != 8 or not c[2].startswith("#"):
                continue  # cabecera y separador
            limp = re.match(r"\d+", c[7])
            texto = c[6].replace("**", "").replace("`", "")
            nota = "" if len(re.findall(r"#\d+", c[2])) > 1 or texto == "ninguno" else texto  # nota de una fila compartida no es de cada PR
            prios = [int(p) for p in re.findall(r"\bP([0-3])\b", texto)]
            res = c[5].lower()
            filas.append({
                "fecha": c[0], "repo": c[1], "prs": [int(n) for n in re.findall(r"#(\d+)", c[2])],
                "ronda": c[3], "resultado": c[5],
                "tipo": "limpia" if res.startswith("limpia") else "hallazgos" if res.startswith("hallazgos")
                else "en curso" if res.startswith("en curso") else "sin respuesta",
                "texto": nota, "prio": min(prios) if prios else None,
                "limpias": int(limp.group()) if limp else 0,
                "cerrado": "cerrado" in c[7].lower(),
                # hallazgos nuevos por prioridad; un "repetido" ya estaba contado en otra ronda
                "conteo": [] if "repetido" in texto else
                [(int(p), int(n)) for n, p in re.findall(r"(\d+)\s*×\s*P([0-3])\b", texto)]})
    return filas


def por_pr(filas):
    estado = {}
    for fila in filas:
        for n in fila["prs"]:
            estado[(fila["repo"], n)] = fila  # la última fila del archivo manda
    return estado


def leer_github():
    """{(repo, n): {titulo, estado}} o None si gh no responde."""
    datos = {}
    for repo in REPOS:
        try:
            r = subprocess.run(["gh", "pr", "list", "-R", "%s/%s" % (ORG, repo), "--state", "all", "--limit", "200",
                                "--json", "number,title,state"], capture_output=True, text=True, timeout=40,
                               encoding="utf-8")
            if r.returncode != 0:
                return None
            for p in json.loads(r.stdout):
                datos[(repo, p["number"])] = {"titulo": p["title"], "estado": p["state"]}
        except (OSError, subprocess.SubprocessError, ValueError):
            return None
    return datos


def totales(filas):
    t = {0: 0, 1: 0, 2: 0, 3: 0}
    for fila in filas:
        for p, n in fila["conteo"]:
            t[p] += n
    return t


def arma_prs(vigente, gh):
    """Lista de PRs con su estado: abiertos (en rondas / listos) y cerrados."""
    claves = set(vigente) | (set(gh) if gh else set())
    prs = []
    for repo, n in claves:
        fila = vigente.get((repo, n))
        info = gh.get((repo, n)) if gh else None
        if gh:
            abierto = bool(info) and info["estado"] == "OPEN"
            if info is None and fila is not None:
                abierto = False  # fuera de las últimas 200: ya es viejo
        else:
            abierto = fila is not None and not fila["cerrado"]
        if gh and not abierto and fila is None:
            continue  # PR cerrado que nunca pasó por rondas: no es ruido útil
        prs.append({"repo": repo, "n": n, "fila": fila, "abierto": abierto,
                    "titulo": info["titulo"] if info else "",
                    "estado": info["estado"] if info else ("CLOSED" if fila and fila["cerrado"] else "OPEN"),
                    "listo": bool(fila) and fila["limpias"] >= LISTO and fila["tipo"] == "limpia"})
    return prs


def puntos(n):
    return "".join('<i class="p%s"></i>' % (" on" if i < min(n, LISTO) else "") for i in range(LISTO))


def fila_html(p):
    f = p["fila"]
    url = "https://github.com/%s/%s/pull/%d" % (ORG, p["repo"], p["n"])
    titulo = e(p["titulo"]) if p["titulo"] else ""
    if not f:
        estado = '<span class="chip nada">sin rondas</span>'
        return ('<tr><td>%s</td><td><a href="%s" target="_blank" rel="noopener">#%d</a> %s</td><td colspan="4" class="mut">'
                'Aún no pasó por /supercodex</td><td>%s</td></tr>' % (e(p["repo"]), url, p["n"], titulo, estado))
    if p["estado"] == "MERGED":
        estado = '<span class="chip nada">Mergeado</span>'
    elif p["estado"] == "CLOSED":
        estado = '<span class="chip nada">Cerrado</span>'
    elif p["listo"]:
        estado = '<span class="chip ok">Listo para Revisor Principal</span>'
    else:
        estado = '<span class="chip rondas">En rondas</span>'
    prio = '<span class="chip pr%d">P%d</span>' % (f["prio"], f["prio"]) if f["prio"] is not None else '<span class="mut">—</span>'
    corto = f["texto"] if len(f["texto"]) <= 130 else f["texto"][:127].rstrip() + "…"
    return ('<tr><td>%s</td><td><a href="%s" target="_blank" rel="noopener">#%d</a> %s</td><td class="c">%s</td>'
            '<td class="c">%s <small>%d</small></td><td><b class="%s">%s</b> <span class="mut" title="%s">%s</span></td>'
            '<td class="c">%s</td><td>%s</td></tr>'
            % (e(p["repo"]), url, p["n"], titulo, e(f["ronda"]), puntos(f["limpias"]), f["limpias"],
               f["tipo"].replace(" ", "-"), e(f["resultado"]), e(f["texto"]), e(corto) if corto else "", prio, estado))


CSS = """:root{--bg:#f3f5f7;--card:#fff;--ink:#16222e;--mut:#5b6b7a;--line:#d9e0e6;--head:#e8edf2;--acc:#2a78d6;--ok:#0f766e;--okb:#d6efec;--cur:#2563eb;--curb:#dce7fb;--pen:#64748b;--penb:#e6eaee;--warn:#b45309;--warnb:#fbe6cc;--bad:#b42318;--badb:#fde4e1}
@media(prefers-color-scheme:dark){:root{--bg:#0f171f;--card:#17222c;--ink:#e6edf3;--mut:#9aa9b8;--line:#2a3947;--head:#22303c;--acc:#7ea8ff;--ok:#4fd1c5;--okb:#12403c;--cur:#7ea8ff;--curb:#1c2f57;--pen:#9aa8b6;--penb:#26323d;--warn:#f0a95a;--warnb:#4a3316;--bad:#ff8a7a;--badb:#4a1f1a}}
*{box-sizing:border-box}body{margin:0;padding:24px 14px 56px;background:var(--bg);color:var(--ink);font:14px/1.4 system-ui,"Segoe UI",sans-serif}
.w{max-width:1100px;margin:auto}h1{font-size:1.5rem;margin:0}h2{font-size:1.1rem;margin:26px 0 8px}a{color:var(--acc)}.hub{font-size:.85rem}.hub a{color:var(--mut)}
.resumen{font-size:1.15rem;font-weight:600;margin:14px 0 4px}.sub{color:var(--mut);margin:0 0 16px;font-size:.85rem}
.prio{display:flex;gap:10px;flex-wrap:wrap;margin:0 0 18px}.prio div{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:8px 14px;min-width:84px}
.prio b{display:block;font-size:1.3rem;font-variant-numeric:tabular-nums}.prio span{color:var(--mut);font-size:.78rem}
.scroll{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:12px}
table{width:100%;border-collapse:collapse;font-size:.85rem}th,td{padding:7px 9px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{background:var(--head);font-size:.76rem;font-weight:600;white-space:nowrap}td.c{white-space:nowrap}tr:last-child td{border-bottom:0}
.mut{color:var(--mut)}small{color:var(--mut)}.p{display:inline-block;width:10px;height:10px;border-radius:50%;border:2px solid var(--mut);margin-right:3px;vertical-align:-1px}.p.on{background:var(--ok);border-color:var(--ok)}
.chip{display:inline-block;padding:1px 9px;border-radius:10px;font-size:.74rem;white-space:nowrap}
.chip.ok{background:var(--okb);color:var(--ok)}.chip.rondas{background:var(--curb);color:var(--cur)}.chip.nada{background:var(--penb);color:var(--pen)}
.chip.pr0,.chip.pr1{background:var(--badb);color:var(--bad)}.chip.pr2{background:var(--warnb);color:var(--warn)}.chip.pr3{background:var(--penb);color:var(--pen)}
b.limpia{color:var(--ok)}b.hallazgos{color:var(--warn)}b.en-curso{color:var(--cur)}b.sin-respuesta{color:var(--pen)}
details{margin-top:22px}summary{cursor:pointer;font-weight:600}summary small{font-weight:400}details .scroll{margin-top:8px}
.nota{color:var(--mut);font-size:.8rem;margin-top:18px}"""

CAB = ("<tr><th>Repo</th><th>PR</th><th>Ronda</th><th>Limpias (2 = listo)</th><th>Último resultado</th>"
       "<th>Prioridad</th><th>Estado</th></tr>")


def render(filas, prs, hay_gh):
    abiertos = sorted((p for p in prs if p["abierto"]), key=lambda p: (p["listo"], p["repo"], p["n"]))
    cerrados = sorted((p for p in prs if not p["abierto"]), key=lambda p: (p["repo"], -p["n"]))
    listos = sum(1 for p in abiertos if p["listo"])
    en_rondas = sum(1 for p in abiertos if p["fila"] and not p["listo"])
    sin = len(abiertos) - listos - en_rondas
    resumen = "%d PRs listos para Revisor Principal, %d en rondas" % (listos, en_rondas)
    if sin:
        resumen += ", %d sin rondas" % sin
    t = totales(filas)
    chips = "".join('<div><b>%d</b><span>P%d%s</span></div>' % (t[k], k, " (bloqueante)" if k == 0 else "") for k in range(4))
    aviso = "" if hay_gh else " · gh no respondió: el estado sale solo del registro"
    ultima = filas[-1]["fecha"] if filas else "s/d"
    cerr = ""
    if cerrados:
        cerr = ('<details><summary>Cerrados o mergeados <small>%d PRs</small></summary><div class="scroll"><table>%s%s</table></div></details>'
                % (len(cerrados), CAB, "".join(fila_html(p) for p in cerrados)))
    return ('<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Rondas de Codex</title><style>%s</style></head><body><div class="w"><div class="hub"><a href="hub.html">← Tableros del proyecto</a></div>'
            '<h1>Rondas de Codex</h1><div class="resumen">%s</div>'
            '<p class="sub">Generado %s · última ronda registrada: %s%s</p>'
            '<h2>Hallazgos de Codex por prioridad</h2><div class="prio">%s</div>'
            '<h2>PRs abiertos</h2><div class="scroll"><table>%s%s</table></div>%s'
            '<p class="nota">Fuente: docs/runs/supercodex-rondas.md (última fila de cada PR). Un PR queda listo con %d rondas limpias seguidas. '
            'Los totales cuentan los hallazgos nuevos anotados en cada fila de la tabla; un hallazgo repetido no se vuelve a contar.</p></div></body></html>'
            % (CSS, e(resumen), dt.datetime.now().strftime("%d/%m/%Y %H:%M"), e(ultima), e(aviso), chips, CAB,
               "".join(fila_html(p) for p in abiertos), cerr, LISTO))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    filas = leer_registro()
    gh = leer_github()
    with open(SALIDA, "w", encoding="utf-8") as f:
        f.write(render(filas, arma_prs(por_pr(filas), gh), gh is not None))
    print("Escrito:", SALIDA)
