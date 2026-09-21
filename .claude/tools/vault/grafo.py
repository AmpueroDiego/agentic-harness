#!/usr/bin/env python3
"""Analiza el grafo de enlaces del vault: islas, huerfanos, hojas y hubs.

Complementa a scripts/validar-vault.py, que corre en cada commit y solo
responde "hay huerfanos?". Esto responde "como esta armado el grafo?", que es
la pregunta cara y no hace falta contestar en cada commit.

Uso:
    python .claude/tools/vault/grafo.py            # resumen
    python .claude/tools/vault/grafo.py --detalle  # + hojas, hubs y las islas

Python 3 sin dependencias, igual que .claude/tools/drawio/.
"""

import os, sys, re, json, collections

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
EXT = (".md", ".drawio", ".canvas")
IGNORE = {"node_modules", ".git", "bin", "obj", "dist", "build", ".vs", ".idea", ".venv"}

WIKI = re.compile(r"\[\[([^\]\|#]+)(?:#[^\]\|]*)?(?:\|[^\]]*)?\]\]")
MD = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+?)(?:\s+\"[^\"]*\")?\)")


def exclusiones():
    """userIgnoreFilters de .obsidian/app.json — para medir lo que Obsidian ve."""
    p = os.path.join(ROOT, ".obsidian", "app.json")
    if not os.path.exists(p):
        return []
    try:
        return json.load(open(p, encoding="utf-8")).get("userIgnoreFilters", []) or []
    except Exception:
        return []


def visible(rel, filtros):
    if any(p.startswith(".") for p in rel.split("/")[:-1]):
        return False          # Obsidian no indexa carpetas con punto
    for f in filtros:
        if f.startswith("/") and f.rfind("/") > 0:
            cuerpo, flags = f[1 : f.rfind("/")], f[f.rfind("/") + 1 :]
            try:
                if re.search(cuerpo, rel, re.I if "i" in flags else 0):
                    return False
            except re.error:
                continue
        elif f and f in rel:
            return False
    return True


def escanear():
    archivos = []
    for root, dirs, fns in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in IGNORE]
        rel_root = os.path.relpath(root, ROOT).replace("\\", "/")
        if rel_root.startswith(".claude/worktrees"):
            dirs[:] = []
            continue
        for fn in fns:
            if fn.lower().endswith(EXT):
                archivos.append(os.path.relpath(os.path.join(root, fn), ROOT).replace("\\", "/"))
    return archivos


def construir(archivos, filtros):
    # Claves en minuscula: Obsidian resuelve enlaces sin distinguir mayusculas,
    # y validar-vault.py tambien. Si este script no lo hace, los dos cuentan
    # distinto sobre el mismo vault.
    por_ruta = {a.lower(): a for a in archivos}
    por_nombre = collections.defaultdict(list)
    for a in archivos:
        sin_ext = (a[:-3] if a.endswith(".md") else a).lower()
        por_nombre[sin_ext].append(a)
        por_nombre[os.path.basename(sin_ext)].append(a)

    def resolver(destino, origen):
        t = destino.strip().replace("\\", "/").split("#")[0].split("?")[0]
        if not t or t.startswith(("http://", "https://", "mailto:")):
            return None
        base = os.path.dirname(origen)
        for c in (os.path.normpath(os.path.join(base, t)).replace("\\", "/"), t):
            for cand in (c, c + ".md"):
                if cand.lower() in por_ruta:
                    return por_ruta[cand.lower()]
        clave = (t[:-3] if t.endswith(".md") else t).lower()
        # Por nombre suelto solo si el enlace no trae carpeta. Con carpeta, el
        # fallback por basename daba por buenos enlaces que Obsidian no resuelve:
        # `../../Meta/Graph-View-Config.md` desde `comandos-pipeline/` sale del
        # vault, y aun asi contaba como arista. Asi se escondio que /auditar-vault
        # estaba huerfana mientras validar-vault.py si la reportaba (2026-09-10).
        claves = (clave,) if "/" in clave else (clave, os.path.basename(clave))
        for k in claves:
            if k in por_nombre:
                return por_nombre[k][0]
        return None

    salientes = collections.defaultdict(set)
    rotos = collections.defaultdict(set)
    for a in archivos:
        if not a.endswith(".md"):
            continue
        try:
            txt = open(os.path.join(ROOT, a), encoding="utf-8", errors="replace").read()
        except Exception:
            continue
        cuerpo = re.sub(r"```.*?```", "", txt, flags=re.S)
        # Codigo en linea tambien: `[[ruta/nota|Alias]]` es un ejemplo de sintaxis,
        # no un enlace. Obsidian no lo resuelve y validar-vault.py ya lo quitaba.
        # Sin esto, 7 de 13 "enlaces rotos" eran ejemplos de documentacion.
        cuerpo = re.sub(r"`[^`\n]*`", "", cuerpo)
        for m in set(WIKI.findall(cuerpo)) | set(MD.findall(cuerpo)):
            r = resolver(m, a)
            if r and r != a:
                salientes[a].add(r)
                continue
            if r is not None or m.strip().startswith(("http", "mailto", "#")):
                continue
            # Enlace markdown a una carpeta que existe (`[diagramas/](diagramas/)`):
            # sirve en GitHub, que lista la carpeta. No es nota ni enlace roto.
            if os.path.isdir(os.path.join(ROOT, os.path.dirname(a), m.split("#")[0].strip())):
                continue
            # Notas vistas a traves de un junction (`comandos-pipeline/` ->
            # `.claude/commands/`): su `../../Meta/x.md` esta escrito para la ruta
            # real, y ahi existe — funciona en GitHub y para Claude. No suma arista
            # (no consta que Obsidian lo resuelva), pero tampoco es un enlace roto.
            real = os.path.realpath(os.path.join(ROOT, os.path.dirname(a)))
            if os.path.exists(os.path.join(real, m.split("#")[0].strip())):
                continue
            # Enlaces a archivos que no son notas (.sql, .json, .drawio, imagenes)
            # no son enlaces rotos del grafo: el destino existe, solo que no es
            # una nota. Contarlos inflaba el numero y lo volvia inutil.
            ext = os.path.splitext(m.split("#")[0].strip())[1].lower()
            if ext and ext not in EXT:
                continue
            rotos[a].add(m)

    md_vis = [a for a in archivos if a.endswith(".md") and visible(a, filtros)]
    out = {k: {x for x in v if visible(x, filtros)} for k, v in salientes.items() if visible(k, filtros)}
    inn = collections.defaultdict(set)
    for s, ts in out.items():
        for t in ts:
            inn[t].add(s)
    return md_vis, out, inn, rotos


def islas(md_vis, out):
    ady = collections.defaultdict(set)
    for s, ts in out.items():
        for t in ts:
            ady[s].add(t)
            ady[t].add(s)
    visto, comps = set(), []
    for a in md_vis:
        if a in visto:
            continue
        pila, comp = [a], []
        visto.add(a)
        while pila:
            x = pila.pop()
            comp.append(x)
            for n in ady[x]:
                if n not in visto:
                    visto.add(n)
                    pila.append(n)
        comps.append(sorted(comp))
    return sorted(comps, key=len, reverse=True)


def main():
    detalle = "--detalle" in sys.argv
    filtros = exclusiones()
    archivos = escanear()
    md_vis, out, inn, rotos = construir(archivos, filtros)
    comps = islas(md_vis, out)
    huerfanas = [a for a in md_vis if not out.get(a) and not inn.get(a)]

    print("🕸️  GRAFO DEL VAULT")
    print(f"   Notas visibles en Obsidian : {len(md_vis)}")
    print(f"   Islas (componentes conexas): {len(comps)}")
    print(f"   Nodos huérfanos            : {len(huerfanas)}")
    print(f"   Enlaces rotos              : {sum(len(v) for v in rotos.values())}")

    if len(comps) > 1:
        print("\n⚠️  El grafo está partido. Islas:")
        for c in comps:
            muestra = ", ".join(c[:3]) + (" ..." if len(c) > 3 else "")
            print(f"   [{len(c):>3}] {muestra}")
        print("\n   Antes de agregar enlaces a mano, revisá las exclusiones de Obsidian:")
        print("   una que esconda notas índice deja huérfano todo lo que colgaba de ellas.")
    else:
        print("\n✅ El grafo es una sola pieza.")

    if huerfanas:
        print(f"\n⚠️  Huérfanas ({len(huerfanas)}):")
        for h in huerfanas:
            print(f"   - {h}")

    if detalle:
        hojas = [a for a in md_vis if inn.get(a) and not out.get(a)]
        print(f"\n🍃 Hojas — tienen entrantes pero ningún saliente ({len(hojas)}):")
        for h in hojas[:20]:
            print(f"   {len(inn[h]):>3} in   {h}")
        if hojas:
            print("   Cuelgan de un hilo: si su índice se oculta o se borra, quedan sueltas.")

        print("\n🌟 Hubs — más enlaces salientes:")
        for a, s in sorted(out.items(), key=lambda x: -len(x[1]))[:10]:
            print(f"   {len(s):>3} out / {len(inn.get(a, [])):>3} in   {a}")

        if rotos:
            print("\n🔗 Enlaces rotos:")
            for a, ts in sorted(rotos.items()):
                for t in sorted(ts):
                    print(f"   [{a}] -> {t}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
