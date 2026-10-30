"""Genera en .agents/skills/ un skill de Codex por cada comando de .claude/commands/ y cada skill de .claude/skills/.

La fuente sigue siendo .claude/: cada SKILL.md generado solo apunta al archivo original, así no hay dos copias que se desfasen.
Uso: python .claude/scripts/generar-skills-codex.py [--verificar]   (--verificar sale 1 si hay algo desactualizado, sin escribir)
"""
import pathlib
import re
import sys

HARNESS_ROOT = pathlib.Path(__file__).resolve().parents[2]
DESTINO = HARNESS_ROOT / ".agents" / "skills"
MARCA = "<!-- generado por .claude/scripts/generar-skills-codex.py; no editar a mano -->"


def descripcion(texto: str, nombre: str) -> str:
    m = re.match(r"---\s*\n(.*?)\n---", texto, re.S)
    if m:
        d = re.search(r"^description:\s*(.+)$", m.group(1), re.M)
        if d and d.group(1).strip() not in (">-", ">", "|"):
            return d.group(1).strip().strip('"')
    return f"Comando /{nombre} del sistema multiagente del proyecto."


def skill(nombre: str, fuente: pathlib.Path) -> str:
    rel = fuente.relative_to(HARNESS_ROOT).as_posix()
    desc = descripcion(fuente.read_text(encoding="utf-8"), nombre).replace('"', "'")
    return f"""---
name: {nombre}
description: "{desc}"
tipo: skill
tags: [harness]
---
{MARCA}

# /{nombre}

Leé completo `{rel}` (ruta relativa a la raíz del proyecto) y seguilo al pie de la letra. Ese archivo es la única fuente; este es solo un puntero.
Para cambiar este skill, editá `{rel}` y regenerá con `python .claude/scripts/generar-skills-codex.py`; no edites este archivo.

- `$ARGUMENTS` en ese archivo es lo que te pidió el usuario al invocar este skill.
- Donde diga lanzar un agente o subagente (`Agent`, `planner`, `qa`, `adversary`, `coder-web`…), usá `bash .claude/scripts/agente.sh <agente> <prompt.md> <salida.md>`.
- Donde diga invocar otro comando (`/trello`, `/supercodex`…), leé y seguí su `.claude/commands/<nombre>.md`.
- Equivalencias de herramientas de Claude y qué motor usar: `AGENTS.md` §3.
- Con varias sesiones abiertas, solo la coordinadora escribe los archivos compartidos de la raíz (`TASKS.md`, `CLAUDE.md`, `docs/runs/INDEX.md`…), sea del motor que sea (`CLAUDE.md`, «Flujo de trabajo»).
"""


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # la consola de Windows rompe las tildes
    verificar = "--verificar" in sys.argv
    fuentes = {p.stem: p for p in sorted((HARNESS_ROOT / ".claude" / "commands").glob("*.md"))}
    for p in sorted((HARNESS_ROOT / ".claude" / "skills").glob("*/SKILL.md")):
        fuentes.setdefault(p.parent.name, p)
    viejos = []
    for nombre, fuente in fuentes.items():
        archivo = DESTINO / nombre / "SKILL.md"
        nuevo = skill(nombre, fuente)
        if archivo.exists():
            actual = archivo.read_text(encoding="utf-8")
            if MARCA not in actual:
                print(f"se respeta (escrito a mano): {archivo.relative_to(HARNESS_ROOT).as_posix()}")
                continue
            if actual == nuevo:
                continue
        viejos.append(nombre)
        if not verificar:
            archivo.parent.mkdir(parents=True, exist_ok=True)
            archivo.write_text(nuevo, encoding="utf-8", newline="\n")
    huerfanos = [p.parent.name for p in DESTINO.glob("*/SKILL.md")
                 if p.parent.name not in fuentes and MARCA in p.read_text(encoding="utf-8")]
    for h in huerfanos:
        print(f"sin fuente (su comando ya no existe; no se borra solo): .agents/skills/{h}/SKILL.md")
    accion = "desactualizados" if verificar else "escritos"
    print(f"{len(fuentes)} comandos/skills; {len(viejos)} {accion}" + (f": {', '.join(viejos)}" if viejos else ""))
    return 1 if verificar and (viejos or huerfanos) else 0


if __name__ == "__main__":
    sys.exit(main())
