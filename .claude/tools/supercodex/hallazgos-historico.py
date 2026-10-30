"""Histórico de hallazgos del bot de Codex en api-core y web-app.

Uso:  PYTHONIOENCODING=utf-8 python .claude/tools/supercodex/hallazgos-historico.py [--json salida.json]
Solo lectura en GitHub (gh api). Escribe hallazgos-codex-historico.tsv junto a este script
y, con --json, los datos agregados que embebe la página del Artifact.

Fuentes:
- Hallazgo = comentario inline de `chatgpt-codex-connector[bot]` (pulls/comments). Si trae
  `codex-security-review-finding` es fuente=security; si no, fuente=code.
- Ronda con hallazgos = review_id distinto. Ronda limpia = comentario «Codex Review: Didn't find
  any major issues». Ronda fallida = «usage limits» o «Something went wrong».
- Respuesta humana al hilo (in_reply_to_id) para detectar ruido.
- Hitos: filas con fecha de bitacora-mejoras-codex.md.

Criterio de tema (primera regla que calza, sobre título + primer párrafo, en minúsculas):
 1 ruido        los primeros 160 caracteres de la respuesta humana dicen «no aplica» (no «en este PR»),
                no procede, a propósito, se mantiene/deja así, decisión de producto/diseño/despliegue,
                imposible, no puede existir/ocurrir, falso positivo, riesgo aceptado, ya estaba cubierto;
                y NO empiezan con aplica / válido / corregido / tenías razón / confirmado
 2 merge        al mezclar, merge de develop, after merging, rebase, rama base, marcadores de conflicto,
                ambas ramas, apilado/stacked, ya mergeado (subestima: el bot rara vez lo dice explícito)
 3 seguridad    fuente=security
 4 version      409, versión/version, rowversion, concurrency token, bloqueo/lock, optimista, conflict
 5 concurrencia race/carrera, stale/obsolet, tardía/late, reintento/retry, en vuelo/in-flight,
                concurren, out-of-order, desorden, abort, cancel, doble envío/double, idempot,
                anterior/previous response, sesión cambia
 6 seguridad    permiso/permission, 403, forbidden, autoriz/authoriz, tenant, token, jwt, secret,
                expone/expose/leak, xss, inyecc/inject, rol/role, credencial
 7 datos        migración/migration, columna/column, índice/index, schema/esquema, sql, backfill,
                persist, base de datos/database, nvarchar, null en bd, transacción/transaction
 8 ui           foco/focus, aria, teclado/keyboard, accesib/accessib, lector/screen reader, botón/
                button, modal, scroll, pestaña/tab, render, layout, etiqueta/label, visible, pantalla
 9 validacion   valid, rechaz/reject, obligatori/requir, permit/allow, acept/accept, cierre/clos,
                estado/state/status, caso/case, contrato, negocio
10 otro
"""
import json, re, subprocess, sys, os, datetime as dt, collections

GITHUB_ORG = os.environ.get("GITHUB_ORG", "<org>")

AQUI = os.path.dirname(os.path.abspath(__file__))
REPOS = ["api-core", "web-app"]
BOT = "chatgpt-codex-connector[bot]"
LIMA = dt.timezone(dt.timedelta(hours=-5))


def gh(path):
    # --jq '.[]' deja un objeto JSON por línea, sin importar cuántas páginas haya
    out = subprocess.run(["gh", "api", "--paginate", path, "--jq", ".[]"], capture_output=True, check=True).stdout
    return [json.loads(l) for l in out.decode("utf-8").splitlines() if l.strip()]


REGLAS = [
    ("merge", r"al mezclar|tras mezclar|merge de develop|merging develop|after merg|rebase|rama base|base branch|marcadores de conflicto|conflict marker|<<<<<<<|ambas ramas|both branches|apilad|stacked|ya mergead|already merged"),
    ("version", r"\b409\b|versi[oó]n|\bversion|rowversion|concurrency token|bloqueo|\block|optimist|optimista|conflict"),
    ("concurrencia", r"\brace|carrera|stale|obsolet|tard[ií]a|\blate\b|reintent|retry|en vuelo|in-flight|in flight|concurren|out-of-order|desorden|abort|cancel|double|doble|idempot|anterior|previous|sesi[oó]n cambi"),
    ("seguridad", r"permis|permission|\b403\b|forbidden|autoriz|authoriz|tenant|token|\bjwt|secret|expon|expose|leak|xss|inyecc|inject|\brol\b|\broles?\b|credencial|credential"),
    ("datos", r"migraci|migration|columna|column|[ií]ndice|\bindex|schema|esquema|\bsql\b|backfill|persist|base de datos|database|nvarchar|transacci|transaction"),
    ("ui", r"foco|focus|aria|teclado|keyboard|accesib|accessib|lector|screen reader|bot[oó]n|button|modal|scroll|pesta[ñn]a|\btab\b|render|layout|etiqueta|label|visible|pantalla|toast"),
    ("validacion", r"valid|rechaz|reject|obligatori|requir|permit|allow|acept|accept|cierre|clos|cerrad|estado|state|status|\bcaso|\bcase|contrato|negocio"),
]
RUIDO = r"no aplica(?! en este pr)|no procede|por dise[ñn]o|a prop[oó]sito|se mantiene as[ií]|se deja as[ií]|decisi[oó]n (de producto|de dise[ñn]o|de despliegue|ya tomada)|imposible|no puede (existir|ocurrir)|no ocurre|falso positivo|riesgo aceptado|ya estaba cubierto|no es un descuido|no corresponde"
REAL = r"^\W*(aplica|v[aá]lido|corregido|ten[ií]as raz[oó]n|confirmado|tienes raz[oó]n|bien visto|correcto|fixed|resuelto en)"


def clasificar(texto, fuente, respuesta):
    r = (respuesta or "").lower()[:160]
    if r and not re.search(REAL, r) and re.search(RUIDO, r):
        return "ruido"
    t = texto.lower()
    for tema, rx in REGLAS:
        if tema == "version" and fuente == "security":
            return "seguridad"
        if re.search(rx, t):
            return tema
    return "seguridad" if fuente == "security" else "otro"


def titulo(body):
    for linea in body.splitlines():
        m = re.search(r"Badge\]\([^)]*\)\)?</sub></sub>\s*(.+)", linea)
        if m:
            return re.sub(r"\*\*", "", m.group(1)).strip()
    return ""


def primer_parrafo(body):
    partes = [p for p in body.split("\n\n") if p.strip() and "Badge" not in p and not p.startswith(("<!--", "###"))]
    return partes[0] if partes else ""


def fecha_lima(iso):
    return dt.datetime.fromisoformat(iso.replace("Z", "+00:00")).astimezone(LIMA)


def hitos():
    filas = []
    for l in open(os.path.join(AQUI, "bitacora-mejoras-codex.md"), encoding="utf-8"):
        m = re.match(r"\|\s*(\d{4}-\d{2}-\d{2})\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|", l)
        if m:
            filas.append({"fecha": m.group(1), "cambio": re.sub(r"[`*]", "", m.group(2)), "espera": m.group(3)})
    return filas


def main():
    filas, rondas = [], []  # rondas: (repo, pr, fecha, tipo)
    for repo in REPOS:
        com = gh(f"repos/{GITHUB_ORG}/{repo}/pulls/comments?per_page=100")
        resp = collections.defaultdict(list)
        for c in com:
            if c["user"]["login"] != BOT and c.get("in_reply_to_id"):
                resp[c["in_reply_to_id"]].append(c["body"])
        vistos, reviews = set(), {}
        bot = sorted((c for c in com if c["user"]["login"] == BOT and not c.get("in_reply_to_id")), key=lambda c: c["created_at"])
        for c in bot:
            b = c["body"]
            m = re.search(r"(P[0-3]) Badge", b)
            if not m:
                continue  # aviso de cuota pegado como inline
            fuente = "security" if "codex-security-review-finding" in b else "code"
            tit = titulo(b)
            pr = int(c["pull_request_url"].rsplit("/", 1)[1])
            r = " ".join(resp.get(c["id"], []))
            clave = (repo, pr, c["path"], re.sub(r"\W+", "", tit.lower().replace("security:", "")))
            f = fecha_lima(c["created_at"])
            filas.append({
                "repo": repo, "pr": pr, "fecha": f.strftime("%Y-%m-%d"), "hora": f.strftime("%H:%M"),
                "prioridad": m.group(1), "fuente": fuente,
                "tema": clasificar(tit + " " + primer_parrafo(b), fuente, r),
                "repetido": "si" if clave in vistos else "no",
                "archivo": c["path"], "resumen": tit.replace("\t", " "),
                "respuesta": r.replace("\t", " ").replace("\r", " ").replace("\n", " ")[:160],
                "review_id": c.get("pull_request_review_id"), "id": c["id"],
            })
            vistos.add(clave)
            reviews.setdefault(c.get("pull_request_review_id"), (repo, pr, f.strftime("%Y-%m-%d")))
        rondas += [(rp, p, d, "hallazgos") for rp, p, d in reviews.values()]
        for c in gh(f"repos/{GITHUB_ORG}/{repo}/issues/comments?per_page=100"):
            if c["user"]["login"] != BOT:
                continue
            b, pr = c["body"].strip(), int(c["issue_url"].rsplit("/", 1)[1])
            d = fecha_lima(c["created_at"]).strftime("%Y-%m-%d")
            if b.startswith("Codex Review: Didn't find"):
                rondas.append((repo, pr, d, "limpia"))
            elif "usage limits" in b[:120] or "Something went wrong" in b[:120]:
                rondas.append((repo, pr, d, "fallida"))

    cols = ["repo", "pr", "fecha", "hora", "prioridad", "fuente", "tema", "repetido", "archivo", "resumen", "respuesta", "id"]
    with open(os.path.join(AQUI, "hallazgos-codex-historico.tsv"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\t".join(cols) + "\n")
        for x in sorted(filas, key=lambda x: (x["fecha"], x["hora"], x["repo"], x["pr"])):
            fh.write("\t".join(str(x[k]) for k in cols) + "\n")
    print(f"{len(filas)} hallazgos, {len(rondas)} rondas")

    if "--json" in sys.argv:
        salida = sys.argv[sys.argv.index("--json") + 1]
        datos = {
            "hallazgos": [[x["repo"][:3], x["pr"], x["fecha"], x["prioridad"], x["tema"], x["repetido"] == "si", x["fuente"], x["resumen"][:110]] for x in filas],
            "rondas": [[r[0][:3], r[1], r[2], r[3]] for r in rondas],
            "hitos": hitos(),
            "prs": {},
        }
        for repo in REPOS:
            for p in json.loads(subprocess.run(["gh", "pr", "list", "-R", f"{GITHUB_ORG}/{repo}", "--state", "all", "--limit", "500", "--json", "number,title"], capture_output=True, check=True).stdout.decode("utf-8")):
                datos["prs"][f"{repo[:3]}#{p['number']}"] = p["title"][:90]
        with open(salida, "w", encoding="utf-8") as fh:
            json.dump(datos, fh, ensure_ascii=False, separators=(",", ":"))


if __name__ == "__main__":
    main()
