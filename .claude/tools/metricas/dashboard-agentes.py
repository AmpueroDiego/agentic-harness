#!/usr/bin/env python3
"""Tablero de productividad con agentes. Lee INDEX.md, TASKS.md, supercodex-rondas.md, git worktree y gh.
Uso: python .claude/tools/metricas/dashboard-agentes.py <salida.html>"""
import html, json, re, subprocess, sys, os
from datetime import datetime, timedelta, timezone
from pathlib import Path

GITHUB_ORG = os.environ.get("GITHUB_ORG", "<org>")

RAIZ = Path(__file__).resolve().parents[3]
REPOS = ["api-core", "web-app"]


def sh(cmd, cwd=RAIZ):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return r.stdout if r.returncode == 0 else ""


def celdas(linea):
    return [c.strip() for c in linea.strip().strip("|").split(" | ")]


def corridas():
    filas = []
    for l in (RAIZ / "docs/runs/INDEX.md").read_text(encoding="utf-8").splitlines():
        if not re.match(r"\| 20\d\d-\d\d-\d\d \|", l):
            continue
        c = celdas(l)
        if len(c) < 6:
            continue
        tok = re.search(r"~?([\d.]+)\s*K", c[4])
        dur = re.search(r"~?(\d+(?:[.,]\d+)?)\s*(min|h)\b", c[3])
        ciclos = re.match(r"\s*(\d+)", c[5])
        minutos = None
        if dur:
            v = float(dur.group(1).replace(",", "."))
            minutos = v * 60 if dur.group(2) == "h" else v
        filas.append({
            "fecha": c[0], "tarea": re.sub(r"[*`]", "", c[1])[:90], "ok": "✅" in c[2],
            "tokens_k": float(tok.group(1)) if tok else None, "min": minutos,
            "ciclos": int(ciclos.group(1)) if ciclos else None,
        })
    return filas


def pert():
    txt = (RAIZ / "TASKS.md").read_text(encoding="utf-8")
    sec = txt.split("## Medición: real vs PERT", 1)[-1]
    out = []
    for l in sec.splitlines():
        m = re.match(r"\| `?[\w` +]+`? \| (.+?) \| ([\d.]+) \| ([\d.]+) \|", l)
        if m:
            out.append({"tarea": m.group(1)[:60], "pert": float(m.group(2)), "real": float(m.group(3))})
    return out


def supercodex(desde="0000-00-00", hasta="9999-99-99"):
    p = RAIZ / "docs/runs/supercodex-rondas.md"
    if not p.exists():
        return {}
    por_pr = {}
    en = False
    for l in p.read_text(encoding="utf-8").splitlines():
        if l.startswith("## Rondas de"):
            en = True
            continue
        if en and re.match(r"\| 20", l):
            c = celdas(l)
            if len(c) >= 6:
                if not (desde <= c[0][:10] <= hasta):
                    continue
                d = por_pr.setdefault(f"{c[1]} #{c[2]}", {"rondas": 0, "limpias": 0})
                if c[5].lower().startswith(("limpia", "hallazgos")):
                    d["rondas"] += 1
                if c[5].lower().startswith("limpia"):
                    d["limpias"] += 1
    return por_pr


def worktrees():
    n = {}
    for r in ["."] + REPOS:
        for l in sh(["git", "worktree", "list", "--porcelain"], RAIZ / r).splitlines():
            if l.startswith("worktree "):
                n[l[9:].replace("\\", "/")] = 1
    activos = [p for p in n if "/.worktrees/" in p]
    por = {}
    for p in activos:
        k = p.split("/.worktrees/")[1].split("--")[0]
        por[k] = por.get(k, 0) + 1
    return len(activos), por


def prs():
    ahora = datetime.now(timezone.utc)
    abiertos, ciclo = [], []
    for r in REPOS:
        o = sh(["gh", "pr", "list", "-R", f"{GITHUB_ORG}/{r}", "--state", "open", "--json",
                "number,title,createdAt,reviewDecision,isDraft"])
        for p in json.loads(o or "[]"):
            dias = (ahora - datetime.fromisoformat(p["createdAt"].replace("Z", "+00:00"))).total_seconds() / 86400
            abiertos.append({"repo": r, "n": p["number"], "t": p["title"][:70], "dias": dias,
                             "estado": "borrador" if p["isDraft"] else (p["reviewDecision"] or "sin revisar")})
        m = sh(["gh", "pr", "list", "-R", f"{GITHUB_ORG}/{r}", "--state", "merged", "--limit", "40", "--json",
                "number,createdAt,mergedAt,reviews"])
        for p in json.loads(m or "[]"):
            h = (datetime.fromisoformat(p["mergedAt"].replace("Z", "+00:00")) -
                 datetime.fromisoformat(p["createdAt"].replace("Z", "+00:00"))).total_seconds() / 3600
            ciclo.append({"h": h, "revisiones": len(p["reviews"]), "fecha": p["mergedAt"][:10]})
    return sorted(abiertos, key=lambda x: -x["dias"]), ciclo


def med(v):
    v = sorted(v)
    return v[len(v) // 2] if v else None


def fmt(x, d=1, suf=""):
    return "s/d" if x is None else f"{x:.{d}f}{suf}"


def barras(items, maxv, unidad, clase=""):
    if not items:
        return '<p class="vacio">Sin datos todavía.</p>'
    out = []
    for etiqueta, v in items:
        w = 0 if not maxv else max(2, v / maxv * 100)
        out.append(f'<div class="fila"><span class="et" title="{html.escape(etiqueta)}">{html.escape(etiqueta)}</span>'
                   f'<span class="bar"><i class="{clase}" style="width:{w:.0f}%"></i></span><b>{v:.1f}{unidad}</b></div>')
    return "".join(out)


def linea_tokens(filas):
    pts = [f for f in filas if f["tokens_k"]]
    if len(pts) < 2:
        return ""
    W, H, P = 640, 150, 28
    mx = max(p["tokens_k"] for p in pts)
    xs = lambda i: P + i * (W - 2 * P) / (len(pts) - 1)
    ys = lambda v: H - P - v / mx * (H - 2 * P)
    d = " ".join(f"{xs(i):.1f},{ys(p['tokens_k']):.1f}" for i, p in enumerate(pts))
    area = f"{P},{H-P} {d} {W-P},{H-P}"
    ult = pts[-1]
    return (f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Tokens por corrida">'
            f'<line class="g" x1="{P}" x2="{W-P}" y1="{H-P}" y2="{H-P}"/><line class="g" x1="{P}" x2="{W-P}" y1="{ys(mx):.1f}" y2="{ys(mx):.1f}"/>'
            f'<text class="t" x="{P}" y="{ys(mx)-5:.1f}">{mx:.0f}K</text><text class="t" x="{P}" y="{H-8}">{pts[0]["fecha"]}</text>'
            f'<text class="t" x="{W-P}" y="{H-8}" text-anchor="end">{ult["fecha"]}</text>'
            f'<polygon class="a" points="{area}"/><polyline class="l" points="{d}"/>'
            f'<circle class="p" cx="{xs(len(pts)-1):.1f}" cy="{ys(ult["tokens_k"]):.1f}" r="4"/></svg>')


def lunes(f):
    d = datetime.strptime(f, "%Y-%m-%d")
    return (d - timedelta(days=d.weekday())).strftime("%Y-%m-%d")


def vista(desde, hasta, cor_all, abiertos, ciclo_all, pt, n_wt, wt_repo):
    cor = [c for c in cor_all if desde <= c["fecha"] <= hasta]
    ciclo = [c for c in ciclo_all if desde <= c["fecha"] <= hasta]
    con_ciclos = [c for c in cor if c["ciclos"]]
    primera = sum(1 for c in con_ciclos if c["ciclos"] == 1)
    toks = [c["tokens_k"] for c in cor if c["tokens_k"]]
    mins = [c["min"] for c in cor if c["min"]]
    por_mes = {}
    for c in cor:
        m = por_mes.setdefault(lunes(c["fecha"]), {"n": 0, "tok": 0})
        m["n"] += 1
        m["tok"] += c["tokens_k"] or 0
    sc = supercodex(desde, hasta)
    tot_p, tot_r = sum(x["pert"] for x in pt), sum(x["real"] for x in pt)
    dist = {}
    for c in con_ciclos:
        k = min(c["ciclos"], 4)
        dist[k] = dist.get(k, 0) + 1
    por_dia = {}
    for c in cor:
        por_dia[c["fecha"]] = por_dia.get(c["fecha"], 0) + 1
    mes_rows = [("sem. " + m[5:], d["tok"] / d["n"]) for m, d in sorted(por_mes.items())]
    ciclo_rows = [(("1 ciclo" if k == 1 else (f"{k}+ ciclos" if k == 4 else f"{k} ciclos")), v) for k, v in sorted(dist.items())]
    pr_rows = "".join(
        f'<tr data-repo="{a["repo"]}"><td>{a["repo"]} #{a["n"]}</td><td>{html.escape(a["t"])}</td><td class="num">{a["dias"]:.1f} d</td>'
        f'<td><span class="pill {"warn" if a["dias"] > 3 else ""}">{html.escape(a["estado"].lower())}</span></td></tr>' for a in abiertos)
    sc_rows = "".join(f'<tr><td>{html.escape(k)}</td><td class="num">{v["rondas"]}</td><td class="num">{v["limpias"]}</td></tr>' for k, v in sc.items())
    pert_rows = [(x["tarea"], x["real"] / x["pert"] * 100) for x in pt]
    rev = [c["revisiones"] for c in ciclo]
    return {
        "N_CORRIDAS": str(len(cor)), "TOK_MED": fmt(med(toks), 0, "K"), "MIN_MED": fmt(med(mins), 0, " min"),
        "PRIMERA": fmt(primera / len(con_ciclos) * 100 if con_ciclos else None, 0, " %"), "N_WT": str(n_wt),
        "WT_REPO": ", ".join(f"{k}: {v}" for k, v in sorted(wt_repo.items())) or "ninguno",
        "DIAS_PAR": f"{sum(1 for v in por_dia.values() if v >= 2)} de {len(por_dia)}",
        "PR_ABIERTOS": str(len(abiertos)), "PR_H_MED": fmt(med([c["h"] for c in ciclo]), 0, " h"),
        "REV_PROM": fmt(sum(rev) / len(rev) if rev else None, 1),
        "PERT_TOT": f"{tot_r:.1f} h de {tot_p:.1f} h" if pt else "s/d",
        "PERT_PCT": fmt(tot_r / tot_p * 100 if tot_p else None, 0, " %"),
        "GRAF_TOK": linea_tokens(cor), "BARRAS_MES": barras(mes_rows, max([v for _, v in mes_rows] or [0]), "K"),
        "BARRAS_CICLOS": barras(ciclo_rows, max([v for _, v in ciclo_rows] or [0]), "", "sec"),
        "BARRAS_PERT": barras(pert_rows, max([v for _, v in pert_rows] + [100]), " %", "sec"),
        "FILAS_PR": pr_rows or '<tr><td colspan="4" class="vacio">Ningún PR abierto.</td></tr>',
        "FILAS_SC": sc_rows or '<tr><td colspan="3" class="vacio">Sin rondas en este período.</td></tr>',
    }


def main():
    salida = Path(sys.argv[1] if len(sys.argv) > 1 else "tablero-agentes.html")
    cor = corridas()
    n_wt, wt_repo = worktrees()
    abiertos, ciclo = prs()
    pt = pert()
    hoy = datetime.now()
    tpl = (Path(__file__).parent / "plantilla-dashboard.html").read_text(encoding="utf-8")
    pre, resto = tpl.split("<!--VISTA-->")
    cuerpo, post = resto.split("<!--/VISTA-->")
    vistas, opciones = [], []
    lun = hoy - timedelta(days=hoy.weekday())
    rangos = [("todo", "0000-00-00", "9999-99-99", "Todo el histórico")]
    for i in range(8):
        a = lun - timedelta(weeks=i)
        b = a + timedelta(days=6)
        et = ("Esta semana" if i == 0 else "Semana pasada" if i == 1 else f"Hace {i} semanas") + f" ({a.strftime('%d/%m')} al {b.strftime('%d/%m')})"
        rangos.append((f"s{i}", a.strftime("%Y-%m-%d"), b.strftime("%Y-%m-%d"), et))
    for clave, desde, hasta, et in rangos:
        d = vista(desde, hasta, cor, abiertos, ciclo, pt, n_wt, wt_repo)
        b = cuerpo
        for k, v in d.items():
            b = b.replace("{{" + k + "}}", v)
        vistas.append(f'<div class="vista" data-p="{clave}"{"" if clave == "s0" else " hidden"}>{b}</div>')
        opciones.append(f'<option value="{clave}"{" selected" if clave == "s0" else ""}>{et}</option>')
    pre = pre.replace("{{OPCIONES}}", "".join(opciones))
    out = (pre + "".join(vistas) + post).replace("{{GENERADO}}", hoy.strftime("%Y-%m-%d %H:%M"))
    salida.write_text(out, encoding="utf-8")
    print(f"OK {salida} · {len(cor)} corridas · {len(abiertos)} PRs abiertos · {n_wt} worktrees")


main()
