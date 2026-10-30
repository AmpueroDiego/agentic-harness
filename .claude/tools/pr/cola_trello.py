#!/usr/bin/env python3
"""Cruza los PRs de api-core y web-app con sus tarjetas de Trello, solo con lectura.

Por PR imprime una linea con lo que encuentre:
  OK                       tarjeta con el PR adjunto y en una columna razonable
  SIN TARJETA              ninguna tarjeta abierta lo tiene adjunto
  COLUMNA: <col>           PR abierto con la tarjeta todavia en "En desarrollo" o Backlog
  FALTA PR DE <repo>       el titulo dice "(web-app, api-core)" y solo tiene adjunto el PR de un repo
  ARCHIVADA                la unica tarjeta que lo tiene adjunto esta archivada
  CERRADO SIN MERGE        el PR se cerro sin mergear y sigue adjunto a una tarjeta abierta

Uso: python .claude/tools/pr/cola_trello.py [repo#PR ...]   (sin args: los PRs abiertos de api-core y web-app)
Con repo#PR se evalua ese PR aunque este mergeado o cerrado (lo usa /worktree cerrar).
Sale 1 si algun PR tiene un problema. No escribe nada en GitHub ni en Trello.
"""
import json
import os
import re
import subprocess
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, "..", "trello"))
sys.path.insert(0, AQUI)
import trello  # noqa: E402  credenciales y HTTP del conector /trello, sin duplicarlos
from listo_para_merge import EXCLUIDOS, REPOS, gh  # noqa: E402

PR_URL = re.compile(r"github\.com/<org>/(api-core|web-app)/pull/(\d+)", re.I)
# Con un PR abierto la tarjeta ya no esta "en desarrollo": va a En revision (el responsable) al abrirlo.
COLUMNAS_TEMPRANAS = {"backlog del backlog", "backlog", "en desarrollo"}


def tarjetas_por_pr():
    """(repo, n) -> tarjetas que lo tienen adjunto. Una sola llamada trae todas, archivadas incluidas."""
    tablero = trello.Tablero()
    tarjetas = trello.llamar("GET", f"boards/{tablero.id}/cards/all",
                             {"fields": "name,idList,shortUrl,closed", "attachments": "true",
                              "attachment_fields": "url"})
    mapa = {}
    for t in tarjetas:
        t["columna"] = tablero.nombre_columna(t["idList"])
        t["prs"] = {(m.group(1).lower(), int(m.group(2)))
                    for a in t.get("attachments") or [] for m in [PR_URL.search(a.get("url") or "")] if m}
        for clave in t["prs"]:
            mapa.setdefault(clave, []).append(t)
    return mapa


def estado_pr(repo, n, cache):
    if (repo, n) not in cache:
        d = json.loads(gh("pr", "view", str(n), "--repo", f"<org>/{repo}", "--json", "state,title"))
        cache[(repo, n)] = d
    return cache[(repo, n)]


def evaluar(repo, n, estado, mapa, cache):
    todas = mapa.get((repo, n), [])
    abiertas = [t for t in todas if not t["closed"]]
    if not todas:
        return ["SIN TARJETA"], None
    if not abiertas:
        return ["ARCHIVADA"], todas[0]
    problemas = []
    if len(abiertas) > 1:
        problemas.append(f"VARIAS TARJETAS: {', '.join(t['shortUrl'] for t in abiertas)}")
    t = abiertas[0]
    if estado == "CLOSED":
        problemas.append("CERRADO SIN MERGE: sigue adjunto a una tarjeta abierta")
    if estado == "OPEN" and t["columna"].lower() in COLUMNAS_TEMPRANAS:
        problemas.append(f"COLUMNA: {t['columna']}")
    nombre = t["name"].lower()
    if "web-app" in nombre and "api-core" in nombre:
        otro = "api-core" if repo == "web-app" else "web-app"
        # Del otro repo vale un PR abierto o ya mergeado; uno cerrado sin mergear no cuenta.
        if not any(r == otro and estado_pr(r, m, cache)["state"] in ("OPEN", "MERGED") for r, m in t["prs"]):
            problemas.append(f"FALTA PR DE {otro}")
    return problemas or ["OK"], t


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # la consola de Windows es cp1252
    cache, objetivos = {}, []
    for a in sys.argv[1:]:
        r, _, n = a.partition("#")
        if r not in REPOS or not n.isdigit():
            raise SystemExit(f"argumento invalido: {a} (se espera api-core#N o web-app#N)")
        objetivos.append((r, int(n), estado_pr(r, int(n), cache)["state"]))
    if not objetivos:
        for r in REPOS:
            for p in json.loads(gh("pr", "list", "--repo", f"<org>/{r}", "--state", "open",
                                   "--json", "number,title,state")):
                cache[(r, p["number"])] = p
                if (r, p["number"]) not in EXCLUIDOS:
                    objetivos.append((r, p["number"], "OPEN"))
    try:
        mapa = tarjetas_por_pr()
    except trello.ErrorTrello as e:
        raise SystemExit(f"ERROR: {e}")

    con_problema = 0
    for r, n, estado in sorted(objetivos):
        problemas, t = evaluar(r, n, estado, mapa, cache)
        con_problema += problemas != ["OK"]
        tarjeta = f"{t['name']} ({t['columna']}) {t['shortUrl']}" if t else "-"
        print(f"{r}#{n} [{estado}] {' | '.join(problemas)}\n    tarjeta: {tarjeta}")
    print(f"\n{len(objetivos) - con_problema}/{len(objetivos)} OK")
    return 1 if con_problema else 0


if __name__ == "__main__":
    sys.exit(main())
