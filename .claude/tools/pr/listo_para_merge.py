#!/usr/bin/env python3
"""Verifica, solo con lectura, si cada PR abierto esta listo para merge.

Un PR esta LISTO cuando: apunta a develop, no tiene conflictos, todo hilo de
Codex esta respondido por nosotros y resuelto, y las 2 ultimas rondas de Codex
son limpias y la ultima cubre el HEAD actual. No escribe nada en GitHub ni Trello.

Uso: python .claude/tools/pr/listo_para_merge.py [repo#PR ...]   (sin args: api-core y web-app)
"""
import json
import re
import subprocess
import sys

REPOS = ["api-core", "web-app"]
BOT = "chatgpt-codex-connector"
LIMPIAS_REQUERIDAS = 2
# PRs fuera de la cola por decision del responsable: configurar pares (repo, numero).
EXCLUIDOS = set()


def gh(*args):
    r = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise SystemExit(f"gh {' '.join(args[:3])}... fallo: {r.stderr.strip()[:200]}")
    return r.stdout


def paginado(ruta):
    return [x for pagina in json.loads(gh("api", ruta, "--paginate", "--slurp")) for x in pagina]


def es_bot(login):
    return (login or "").startswith(BOT)


def hilos(repo, n):
    q = ('{repository(owner:"<org>",name:"%s"){pullRequest(number:%d){reviewThreads(first:100)'
         '{nodes{isResolved comments(first:50){nodes{author{login}}}}}}}}') % (repo, n)
    d = json.loads(gh("api", "graphql", "-f", "query=" + q))
    return d["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]


def rondas(repo, n):
    """Rondas de Codex en orden: (hora, sha_revisado, limpia).

    Limpia: comentario "Codex Review: Didn't find any major issues".
    Con hallazgos: review del bot (COMMENTED) con comentarios en linea.
    """
    out = []
    for c in paginado(f"repos/<org>/{repo}/issues/{n}/comments"):
        if not es_bot(c["user"]["login"]):
            continue
        cuerpo = c["body"]
        if "Codex Review" not in cuerpo or "Security Review" in cuerpo[:80]:
            continue
        m = re.search(r"Reviewed commit:\*{0,2}\s*`([0-9a-f]{7,40})`", cuerpo)
        out.append((c["created_at"], m.group(1) if m else "", "Didn't find any major issues" in cuerpo))
    for rv in paginado(f"repos/<org>/{repo}/pulls/{n}/reviews"):
        if es_bot(rv["user"]["login"]) and rv.get("state") == "COMMENTED":
            out.append((rv["submitted_at"], rv["commit_id"], False))
    # Ronda limpia sin texto: Codex reacciona con +1 al "@codex review" (y no comenta).
    for c in paginado(f"repos/<org>/{repo}/issues/{n}/comments"):
        if c["body"].strip() != "@codex review" or not c.get("reactions", {}).get("+1"):
            continue
        for rx in paginado(f"repos/<org>/{repo}/issues/comments/{c['id']}/reactions"):
            if es_bot(rx["user"]["login"]) and rx["content"] == "+1":
                out.append((rx["created_at"], "", True))
    return sorted(out)


def evaluar(repo, n):
    pr = json.loads(gh("pr", "view", str(n), "--repo", f"<org>/{repo}", "--json",
                       "title,baseRefName,headRefOid,mergeable,isDraft,headRefName"))
    motivos = []
    if pr["baseRefName"] != "develop":
        motivos.append(f"apunta a {pr['baseRefName']}, no a develop")
    if pr["mergeable"] == "CONFLICTING":
        motivos.append("tiene conflictos con develop")
    if pr["isDraft"]:
        motivos.append("es borrador")
    codex = [t for t in hilos(repo, n) if es_bot(t["comments"]["nodes"][0]["author"]["login"])]
    sin_resp = [t for t in codex if not any(not es_bot(c["author"]["login"]) for c in t["comments"]["nodes"])]
    abiertos = [t for t in codex if not t["isResolved"]]
    if sin_resp:
        motivos.append(f"{len(sin_resp)} hilo(s) de Codex sin respuesta nuestra")
    if abiertos:
        motivos.append(f"{len(abiertos)} hilo(s) de Codex sin resolver")
    rs = rondas(repo, n)
    limpias = 0
    for _, _, ok in reversed(rs):
        if not ok:
            break
        limpias += 1
    head = pr["headRefOid"]
    cubre_head = bool(rs) and rs[-1][1] and head.startswith(rs[-1][1][:7])
    if limpias < LIMPIAS_REQUERIDAS:
        motivos.append(f"{limpias}/{LIMPIAS_REQUERIDAS} rondas limpias seguidas")
    if rs and rs[-1][2] and not cubre_head:
        motivos.append(f"la ultima ronda revisó {rs[-1][1][:7] or '?'} y el HEAD es {head[:7]}: falta una ronda sobre el código actual")
    if not rs:
        motivos.append("sin rondas de Codex")
    return pr, len(codex), limpias, len(rs), motivos


def main():
    objetivos = []
    for a in sys.argv[1:]:
        r, _, n = a.partition("#")
        objetivos.append((r, int(n)))
    if not objetivos:
        for r in REPOS:
            for p in json.loads(gh("pr", "list", "--repo", f"<org>/{r}", "--state", "open", "--json", "number")):
                if (r, p["number"]) not in EXCLUIDOS:
                    objetivos.append((r, p["number"]))
    listos = 0
    for r, n in sorted(objetivos):
        pr, hilos_codex, limpias, total, motivos = evaluar(r, n)
        estado = "LISTO" if not motivos else "NO LISTO"
        listos += not motivos
        print(f"{r}#{n} [{pr['headRefName']}] {estado} - hilos Codex {hilos_codex}, rondas {total}, limpias seguidas {limpias}")
        for m in motivos:
            print(f"    - {m}")
    print(f"\n{listos}/{len(objetivos)} listos para merge")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
