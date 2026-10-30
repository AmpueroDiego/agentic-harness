"""Tabla de «¿cómo va Codex?»: un PR por fila, contado sobre su último commit.

Uso: python .claude/scripts/estado-prs.py web-app:113-118 api-core:89 [api-core:85,83]
Sin argumentos: todos los PRs abiertos de api-core y web-app.
Columnas: último commit, rondas desde ese commit (limpia / hallazgos / pedida sin respuesta), hilos abiertos
y si ya tiene el comentario «✅ 2 rondas…». En pilas, una limpia vieja puede seguir valiendo:
confirmarlo con rondas-vigentes.sh antes de contarla.
"""
import datetime
import json
import re
import subprocess
import sys
import time

# La consola de Windows es cp1252: sin esto, el ✅ de la cabecera revienta el script.
sys.stdout.reconfigure(encoding="utf-8")

Q ="""query($r:String!,$n:Int!){repository(owner:"<org>",name:$r){pullRequest(number:$n){
state headRefOid commits(last:1){nodes{commit{committedDate}}}
reviewThreads(first:100){nodes{isResolved}}
reviews(last:30){nodes{author{login} submittedAt}}
comments(last:60){nodes{author{login} createdAt body}}}}}"""


def gh(*args):
    r = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8")
    return r.stdout


def objetivos(argv):
    if not argv:
        for repo in ("api-core", "web-app"):
            for n in json.loads(gh("pr", "list", "-R", f"<org>/{repo}", "--json", "number") or "[]"):
                yield repo, n["number"]
        return
    for a in argv:
        repo, nums = a.split(":")
        for parte in nums.split(","):
            if "-" in parte:
                ini, fin = map(int, parte.split("-"))
                yield from ((repo, n) for n in range(ini, fin + 1))
            else:
                yield repo, int(parte)


def estado(repo, n):
    # La red hacia GitHub falla a ratos (timeouts): 3 intentos antes de dar el PR por no leído.
    for intento in range(3):
        salida = gh("api", "graphql", "-f", f"query={Q}", "-F", f"r={repo}", "-F", f"n={n}")
        if salida.strip():
            break
        time.sleep(3 * (intento + 1))
    else:
        return None
    d = json.loads(salida)
    p = d["data"]["repository"]["pullRequest"]
    sha = p["headRefOid"][:7]
    ultimo = p["commits"]["nodes"][0]["commit"]["committedDate"]
    abiertos = sum(not t["isResolved"] for t in p["reviewThreads"]["nodes"])
    pedidos, respuestas = [], []
    for r in p["reviews"]["nodes"]:
        if "codex" in ((r["author"] or {}).get("login") or ""):
            respuestas.append((r["submittedAt"], "hallazgos"))
    listo = False
    for c in p["comments"]["nodes"]:
        login = (c["author"] or {}).get("login") or ""
        if "codex" in login and "major issues" in c["body"]:
            respuestas.append((c["createdAt"], "limpia"))
        elif "codex" not in login and "@codex review" in c["body"]:
            pedidos.append(c["createdAt"])
        if "codex" not in login and "✅" in c["body"] and sha in c["body"]:
            listo = True
    pedidos.sort()
    # Una respuesta vale para el commit actual solo si su pedido (el último anterior a ella) es posterior
    # al último commit: una ronda pedida sobre el código viejo puede responder después del push.
    rondas = []
    for t, e in sorted(respuestas):
        previos = [x for x in pedidos if x <= t]
        if previos and previos[-1] > ultimo:
            rondas.append(e)
    # La revisión automática (al abrir o al pushear) no tiene pedido: solo deja el resumen con el sha revisado.
    # Cuenta como ronda si revisó el commit actual y ninguna ronda pedida la cubre ya (el resumen se reescribe con cada una).
    # Su fecha de creación marca la automática; si después se pidieron otras, el estado ya no es el suyo.
    for c in p["comments"]["nodes"]:
        m = re.search(r"codex-review-state:v1 (\{.*?\}) -->", c["body"])
        if not m or "codex" not in ((c["author"] or {}).get("login") or ""):
            continue
        t = c["createdAt"]
        if t > ultimo and not any(ultimo < x <= t for x in pedidos):
            # Con hallazgos deja una review inline en los minutos siguientes; sin ella, fue limpia.
            sigue = min([x for x in pedidos if x > t], default="9999")
            con = any(t[:15] <= r["submittedAt"] < sigue for r in p["reviews"]["nodes"]
                      if "codex" in ((r["author"] or {}).get("login") or ""))
            rondas.insert(0, "hallazgos" if con else "limpia")
        elif not rondas:
            cr = json.loads(m.group(1)).get("code_review", {})
            if cr.get("status") == "completed" and cr.get("commit_sha") == p["headRefOid"]:
                rondas.append("hallazgos" if cr.get("has_any_findings") else "limpia")
    pendiente = any(x > ultimo for x in pedidos) and (not respuestas or max(pedidos) > max(t for t, _ in respuestas))
    limpias = 0
    for e in reversed(rondas):
        if e != "limpia":
            break
        limpias += 1
    if pendiente:
        # La de código y la de seguridad llegan por separado, en cualquier orden, a 2-6 min del pedido.
        # Pasados 30 min sin la de código, se perdió (#91 y web #123, 22/10): recién ahí se vuelve a pedir.
        espera = datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(max(pedidos).replace("Z", "+00:00"))
        minutos = int(espera.total_seconds() // 60)
        rondas.append(f"pedida hace {minutos} min" if minutos < 30 else f"pedida hace {minutos // 60} h {minutos % 60} min, perdida: re-pedir")
    return p["state"], sha, ultimo[5:16].replace("T", " "), rondas, abiertos, limpias, listo


def main():
    print("| PR | Estado | Último commit (UTC) | Rondas desde ese commit | Limpias seguidas | Hilos abiertos | ✅ |")
    print("|---|---|---|---|---|---|---|")
    for repo, n in objetivos(sys.argv[1:]):
        fila = estado(repo, n)
        if fila is None:
            print(f"| {repo} #{n} | sin respuesta de GitHub | | | | | |")
            continue
        st, sha, cuando, rondas, abiertos, limpias, listo = fila
        print(f"| {repo} #{n} | {st} | `{sha}` {cuando} | {', '.join(rondas) or '—'} | {limpias} | {abiertos} | {'sí' if listo else ''} |")


if __name__ == "__main__":
    main()
