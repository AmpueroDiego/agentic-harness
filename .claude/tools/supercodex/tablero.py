"""Tablero de rondas de /supercodex: lee GitHub con `gh` (sin gastar tokens) y escribe un HTML.

Uso:
  python .claude/tools/supercodex/tablero.py [salida.html]            # una vez
  python .claude/tools/supercodex/tablero.py [salida.html] --watch 60 # cada 60 s; la página se recarga sola
El historial de rondas ya resueltas vive en estado-rondas.json (junto a este script).
"""
import json, re, subprocess, sys, time, pathlib, datetime, os

GITHUB_ORG = os.environ.get("GITHUB_ORG", "<org>")

AQUI = pathlib.Path(__file__).parent
ESTADO = AQUI / "estado-rondas.json"
PLANTILLA = AQUI / "plantilla.html"
DESDE = "2026-09-29T17:25:00Z"  # inicio de /supercodex
PRS = {"api-core": [50, 51, 53, 54], "web-app": [50, 51, 52, 53]}
TEMAS = {"api-core#50": "Mapeo de una entidad", "api-core#51": "Confirmación de estado", "api-core#53": "Guía de Codex",
         "api-core#54": "CLAUDE.md, un solo contexto", "web-app#50": "Etiquetas de una acción",
         "web-app#51": "Entidad sin búsquedas innecesarias", "web-app#52": "Ajustar vocabulario",
         "web-app#53": "Instrucciones de revisión"}
PESO_ABIERTO = {"P0", "P1", "P2", "P3", "SEG"}


def gh(ruta):
    r = subprocess.run(["gh", "api", "--paginate", ruta], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        return []
    txt = r.stdout.strip()
    try:
        return json.loads(txt)
    except ValueError:  # --paginate concatena arreglos: [..][..]
        return [x for parte in re.split(r"(?<=\])\s*(?=\[)", txt) for x in json.loads(parte)]


def resumen(repo, n):
    for c in reversed(gh(f"repos/{GITHUB_ORG}/{repo}/issues/{n}/comments")):
        if "codex-pull-request-review-summary" in c["body"]:
            return c["body"].replace("\n", " ")
    return ""


def estados(cuerpo):
    out = {}
    for m in re.finditer(r"(Code|Security) Review\*\* \| \S+ \*\*([A-Za-z ]+)\*\*(?: <relative-time datetime=\"([^\"]+)\")?", cuerpo):
        out[m.group(1)] = (m.group(2).strip(), m.group(3) or "")
    return out


def resolver(repo, n, t, fin):
    """Resultado de la ronda disparada en t (fin = disparo siguiente o None)."""
    cuerpo = resumen(repo, n)
    est = estados(cuerpo)
    if len(est) < 2:
        return "curso", []
    for lado in ("Code", "Security"):
        estado, hora = est[lado]
        if estado in ("In progress", "Running", "Queued") or not hora or hora < t:
            return "curso", []
    if any(e[0] == "Failed" for e in est.values()):
        return "sinresp", []
    f = set()
    for c in gh(f"repos/{GITHUB_ORG}/{repo}/pulls/{n}/comments"):
        if c["user"]["login"].startswith("chatgpt-codex") and c["created_at"] > t and (fin is None or c["created_at"] < fin):
            m = re.search(r"badge/(P[0-3])-", c["body"])
            if m:
                f.add(m.group(1))
    # Un aviso que Codex marca "Resolved" ya no cuenta.
    avisos = re.findall(r"\)\s*·\s*\*\*(?:Low|Medium|High|Critical)\*\*(?:\s*·\s*\*\*(\w+)\*\*)?", cuerpo)
    if any(a != "Resolved" for a in avisos):
        f.add("SEG")
    return ("hallazgos", sorted(f)) if f else ("limpia", [])


def actualizar(estado):
    for repo, nums in PRS.items():
        for n in nums:
            k = f"{repo}#{n}"
            rondas = estado.setdefault(k, [])
            disparos = sorted(c["created_at"] for c in gh(f"repos/{GITHUB_ORG}/{repo}/issues/{n}/comments")
                              if c["body"].strip().lower().startswith("@codex review") and c["created_at"] >= DESDE)
            conocidos = {r["t"][:16] for r in rondas}  # a minuto: el semillado a mano no trae segundos
            for t in disparos:
                if t[:16] not in conocidos:
                    rondas.append({"t": t, "r": "curso", "f": []})
            rondas.sort(key=lambda r: r["t"])
            for i, r in enumerate(rondas):
                if r["r"] == "curso":
                    fin = rondas[i + 1]["t"] if i + 1 < len(rondas) else None
                    r["r"], r["f"] = resolver(repo, n, r["t"], fin)
    return estado


def abiertos(rondas):
    """Hallazgos sin una ronda limpia posterior que los confirme."""
    out = []
    for r in rondas:
        if r["r"] == "limpia":
            out = []
        elif r["r"] == "hallazgos":
            out += r["f"]
    return out


def datos(estado):
    lista = []
    for k, rondas in estado.items():
        repo, n = k.split("#")
        lista.append({"repo": repo, "n": int(n), "tema": TEMAS.get(k, ""),
                      "rondas": [{"r": r["r"], "f": r.get("f", [])} for r in rondas], "abiertos": abiertos(rondas)})
    return lista


def escribir(salida, refresco):
    estado = json.loads(ESTADO.read_text(encoding="utf-8")) if ESTADO.exists() else {}
    estado = actualizar(estado)
    ESTADO.write_text(json.dumps(estado, indent=1, ensure_ascii=False), encoding="utf-8")
    html = PLANTILLA.read_text(encoding="utf-8")
    html = html.replace("var PRS = /*DATA*/[];", "var PRS = " + json.dumps(datos(estado), ensure_ascii=False) + ";")
    html = html.replace("/*STAMP*/", datetime.datetime.now(datetime.timezone.utc).strftime("%d %b %Y, %H:%M UTC"))
    html = html.replace("<!--REFRESH-->", f'<meta http-equiv="refresh" content="{refresco}">' if refresco else "")
    pathlib.Path(salida).write_text(html, encoding="utf-8")


if __name__ == "__main__":
    args = [a for a in sys.argv[1:]]
    espera = 0
    if "--watch" in args:
        i = args.index("--watch")
        espera = int(args[i + 1])
        del args[i:i + 2]
    salida = args[0] if args else "tablero-supercodex.html"
    while True:
        escribir(salida, espera)
        print(time.strftime("%H:%M:%S"), "actualizado ->", salida, flush=True)
        if not espera:
            break
        time.sleep(espera)
