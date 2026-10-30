"""Inventario del trabajo en vuelo: cada worktree de .worktrees/ con commits fuera de develop o cambios sin commit.

El traspaso se arma desde la conversación y no ve lo que quedó a medias en otros worktrees
(22/10: el aviso web tenía 5 commits sin subir y el traspaso no lo nombraba; se creó una tarjeta duplicada).
Este listado sale de git y gh, no de la memoria de nadie.

Uso: python .claude/scripts/trabajo-en-vuelo.py [--dias N]   (por defecto 14: más viejos solo se cuentan)
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WORKTREES = os.path.join(RAIZ, ".worktrees")


def git(ruta, *args):
    r = subprocess.run(["git", "-C", ruta, *args], capture_output=True, text=True, encoding="utf-8")
    return r.stdout.strip() if r.returncode == 0 else None


def prs_por_rama(repo):
    origen = git(os.path.join(RAIZ, repo), "remote", "get-url", "origin")
    if not origen:
        return None
    origen = re.sub(r"^.*github\.com[:/]", "", origen).removesuffix(".git")
    r = subprocess.run(["gh", "pr", "list", "-R", origen, "--state", "all", "--limit", "300",
                        "--json", "number,state,headRefName,updatedAt"],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        return None
    prs = {}
    # El PR más reciente de cada rama manda: una rama reusada puede tener uno viejo cerrado.
    for pr in sorted(json.loads(r.stdout), key=lambda p: p["updatedAt"]):
        prs[pr["headRefName"]] = pr
    return prs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dias", type=int, default=14)
    args = ap.parse_args()
    limite = datetime.date.today() - datetime.timedelta(days=args.dias)

    filas, viejos, cache_prs = [], 0, {}
    for nombre in sorted(os.listdir(WORKTREES)):
        ruta = os.path.join(WORKTREES, nombre)
        if not os.path.isdir(ruta) or "--" not in nombre:
            continue
        # Una carpeta que no es worktree hace que git suba hasta el repo de la raíz.
        tope = git(ruta, "rev-parse", "--show-toplevel")
        if tope is None or os.path.normcase(os.path.abspath(tope)) != os.path.normcase(ruta):
            continue
        repo = nombre.split("--", 1)[0]
        rama = git(ruta, "rev-parse", "--abbrev-ref", "HEAD") or "?"
        # Demos locales y HEAD suelto son entornos de prueba, no trabajo de una tarjeta.
        if rama == "HEAD" or rama.startswith("local/"):
            continue
        base = "origin/develop" if git(ruta, "rev-parse", "--verify", "-q", "origin/develop") else None
        adelante = int(git(ruta, "rev-list", "--count", f"{base}..HEAD") or 0) if base else 0
        sucios = len([l for l in (git(ruta, "status", "--porcelain") or "").splitlines() if l.strip()])
        if adelante == 0 and sucios == 0:
            continue
        fecha = git(ruta, "log", "-1", "--format=%cs") or "?"
        if fecha != "?" and datetime.date.fromisoformat(fecha) < limite:
            viejos += 1
            continue
        if repo not in cache_prs:
            cache_prs[repo] = prs_por_rama(repo) if repo != "raiz" and repo != "acmeorg" else {}
        prs = cache_prs[repo]
        pr = prs.get(rama) if prs else None
        # Lo que quede sucio en una rama ya mergeada es residuo (routeTree, node_modules), no trabajo.
        if pr and pr["state"] == "MERGED":
            continue
        sin_subir = None
        if git(ruta, "rev-parse", "--verify", "-q", "@{u}"):
            sin_subir = int(git(ruta, "rev-list", "--count", "@{u}..HEAD") or 0)
        if prs is None:
            estado_pr = "(gh falló)"
        elif pr:
            estado_pr = f"#{pr['number']} {pr['state'].lower()}"
        else:
            estado_pr = "**sin PR**"
        subida = "sin rama remota" if sin_subir is None else (f"{sin_subir} sin subir" if sin_subir else "al día")
        filas.append((fecha, f"| `{nombre}` | `{rama}` | {adelante} | {sucios or '-'} | {subida} | {estado_pr} | {fecha} |"))

    print("| Worktree | Rama | Commits fuera de develop | Archivos sin commit | Remoto | PR | Último commit |")
    print("|---|---|---|---|---|---|---|")
    for _, fila in sorted(filas, reverse=True):
        print(fila)
    if not filas:
        print("| (nada en vuelo) | | | | | | |")
    if viejos:
        print(f"\n{viejos} worktree(s) con trabajo de hace más de {args.dias} días no se listan (`--dias` para verlos).")


if __name__ == "__main__":
    sys.exit(main())
