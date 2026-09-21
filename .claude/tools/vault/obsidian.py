#!/usr/bin/env python3
"""Audita la configuracion de Obsidian contra los archivos que realmente existen.

Nada de esto se versiona: .obsidian/ esta en el .gitignore, asi que los grupos
de color, las fuerzas y las exclusiones viven solo en la máquina de cada uno.
Se desfasan en silencio — el 2026-09-09 habia dos grupos apuntando a carpetas
inexistentes, un repo entero sin color y la documentacion decia 13 grupos
cuando habia 21.

Revisa cuatro cosas:
  1. Grupos de color que no matchean ningun archivo.
  2. Carpetas con notas que ningun grupo cubre (salen grises).
  3. Colores repetidos entre grupos distintos (se ven identicos).
  4. Junctions faltantes para las carpetas con punto.

Uso:
    python .claude/tools/vault/obsidian.py

Python 3 sin dependencias.
"""

import os, sys, json, re, collections

sys.stdout.reconfigure(encoding="utf-8")

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
IGNORE = {"node_modules", ".git", "bin", "obj", "dist", "build", ".vs", ".idea", ".venv"}

# Carpetas con punto que necesitan un junction para que Obsidian las indexe.
JUNCTIONS = {"agentes-pipeline": ".claude/agents", "comandos-pipeline": ".claude/commands"}


def notas():
    out = []
    for root, dirs, fns in os.walk(ROOT):
        dirs[:] = [d for d in dirs if d not in IGNORE and d != ".claude"]
        for fn in fns:
            if fn.endswith(".md"):
                out.append(os.path.relpath(os.path.join(root, fn), ROOT).replace("\\", "/"))
    return out


def cargar(nombre):
    p = os.path.join(ROOT, ".obsidian", nombre)
    if not os.path.exists(p):
        return None
    try:
        return json.load(open(p, encoding="utf-8"))
    except Exception:
        return None


def main():
    g = cargar("graph.json")
    if g is None:
        print("❌ No se encontró .obsidian/graph.json — ¿el vault se abrió alguna vez en Obsidian?")
        return 1

    archivos = notas()
    grupos = g.get("colorGroups", [])
    problemas = 0

    print("🎨 GRUPOS DE COLOR\n")
    print(f"{'COLOR':<9} {'N':>4}  QUERY")
    print("-" * 64)
    rutas_cubiertas, por_color, muertos = [], collections.defaultdict(list), []
    for grp in grupos:
        q = grp.get("query", "")
        hexc = "#%06X" % grp.get("color", {}).get("rgb", 0)
        por_color[hexc].append(q)
        if q.startswith("path:"):
            p = q.split(":", 1)[1].strip('"')
            rutas_cubiertas.append(p)
            n = sum(1 for f in archivos if p in f)
        elif q.startswith("file:"):
            p = q.split(":", 1)[1]
            n = sum(1 for f in archivos if os.path.basename(f).startswith(p))
        else:
            n = "-"
        marca = ""
        if n == 0:
            marca = "   <-- NO MATCHEA NADA"
            muertos.append(q)
        print(f"{hexc:<9} {str(n):>4}  {q}{marca}")

    print(f"\nTotal: {len(grupos)} grupos", end="")
    tipos = collections.Counter(q.get("query", "").split(":")[0] for q in grupos)
    print(f"  ({', '.join(f'{v} por {k}' for k, v in sorted(tipos.items()))})")

    if muertos:
        problemas += 1
        print(f"\n⚠️  {len(muertos)} grupo(s) no matchean nada — la carpeta se movió o se borró:")
        for m in muertos:
            print(f"   - {m}")
        print("   No rompen nada, pero hacen creer que un contexto tiene color cuando sale gris.")

    sin_color = collections.Counter()
    for f in archivos:
        # Las carpetas con punto no las indexa Obsidian: no pueden salir grises
        # porque directamente no aparecen.
        if any(p.startswith(".") for p in f.split("/")[:-1]):
            continue
        if not any(p in f for p in rutas_cubiertas):
            sin_color["(raíz)" if "/" not in f else f.split("/")[0]] += 1
    if sin_color:
        problemas += 1
        print("\n⚠️  Carpetas con notas y sin grupo de color (nodos grises):")
        for k, v in sorted(sin_color.items(), key=lambda x: -x[1]):
            print(f"   {v:>4}  {k}")
        print("   Ojo: los grupos file: no se cuentan acá, así que Home/TASKS pueden ser falsos positivos.")

    repes = {c: qs for c, qs in por_color.items() if len(qs) > 1 and len(set(qs)) > 1}
    sospechosos = {c: qs for c, qs in repes.items()
                   if len({q.split(":")[0] for q in qs}) == 1 and qs[0].startswith("tag:")}
    if sospechosos:
        problemas += 1
        print("\n⚠️  Grupos por tag que comparten color exacto (se ven idénticos):")
        for c, qs in sospechosos.items():
            print(f"   {c}  ->  {', '.join(qs)}")

    print("\n🔗 JUNCTIONS (carpetas con punto que Obsidian no indexa)\n")
    for nombre, destino in JUNCTIONS.items():
        ruta = os.path.join(ROOT, nombre)
        if os.path.isdir(ruta):
            n = len([x for x in os.listdir(ruta) if x.endswith(".md")])
            print(f"   ✅ {nombre}/ -> {destino}  ({n} notas)")
        else:
            problemas += 1
            print(f"   ❌ {nombre}/ NO EXISTE — los enlaces [[{nombre}/...]] salen en rojo")
            print(f"      New-Item -ItemType Junction -Path \"{nombre}\" -Target \"{destino.replace('/', chr(92))}\"")

    filtros = (cargar("app.json") or {}).get("userIgnoreFilters", []) or []
    print("\n🚫 EXCLUSIONES\n")
    for f in filtros:
        print(f"   {f}")
    # Solo preocupan los filtros AMPLIOS. Excluir un archivo puntual por su ruta
    # exacta (api-people/README.md) es deliberado y no arrastra nada con el.
    riesgo = [f for f in filtros
              if re.search(r"readme|index", f, re.I)
              and not os.path.isfile(os.path.join(ROOT, f))]
    if riesgo:
        problemas += 1
        print("\n⚠️  Una exclusión toca nombres que usan las notas índice del vault:")
        for r in riesgo:
            print(f"   - {r}")
        print("   Esconder un índice deja huérfano todo lo que colgaba de él.")
        print("   Pasó el 2026-09-09: un filtro de README.md produjo 26 huérfanas.")

    print("\n⚙️  FUERZAS (anotalas en Meta/Graph-View-Config.md si las cambiaste)\n")
    for k in ("centerStrength", "repelStrength", "linkStrength", "linkDistance"):
        if k in g:
            print(f"   {k} = {g[k]}")

    print()
    if problemas:
        print(f"⚠️  {problemas} punto(s) a revisar. Nada se modificó: este script solo reporta.")
    else:
        print("✅ Configuración de Obsidian coherente con los archivos reales.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
