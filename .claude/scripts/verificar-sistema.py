"""Chequeos del sistema multiagente que valen para cualquier motor (Claude, Codex, Antigravity). Lo corre el pre-commit de la raíz.

Bloquea (sale 1): punteros de Codex (.agents/skills) desactualizados o agentes de .claude/agents mal formados.
Solo avisa: copias de ~/.claude/hooks distintas de las versionadas (viven fuera del repo; las actualiza la persona a cargo).
Uso: python .claude/scripts/verificar-sistema.py
"""
import pathlib
import re
import subprocess
import sys

MAQ = pathlib.Path(__file__).resolve().parents[2]


def skills_al_dia() -> list[str]:
    r = subprocess.run([sys.executable, "-I", str(MAQ / ".claude/scripts/generar-skills-codex.py"), "--verificar"],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode == 0:
        return []
    return [f"punteros de Codex desactualizados: {r.stdout.strip()}",
            "  corré: python .claude/scripts/generar-skills-codex.py (y agregá .agents/skills al commit)"]


def agentes_bien_formados() -> list[str]:
    # agente.sh lee name/tools del frontmatter; Claude busca el agente por name.
    errores = []
    for f in sorted((MAQ / ".claude/agents").glob("*.md")):
        m = re.match(r"---\s*\n(.*?)\n---", f.read_text(encoding="utf-8"), re.S)
        cab = m.group(1) if m else ""
        nombre = re.search(r"^name:\s*(\S+)", cab, re.M)
        faltan = [c for c in ("description", "tools") if not re.search(rf"^{c}:\s*\S", cab, re.M)]
        if not nombre or nombre.group(1) != f.stem:
            faltan.insert(0, f"name: {f.stem}")
        if faltan:
            errores.append(f"agente mal formado .claude/agents/{f.name}: falta {', '.join(faltan)}")
    return errores


def iguales(a: pathlib.Path, b: pathlib.Path) -> bool:
    # Sin distinguir CRLF/LF: un checkout nuevo en Windows los convierte.
    return a.read_bytes().replace(b"\r\n", b"\n") == b.read_bytes().replace(b"\r\n", b"\n")


def copias_de_hooks() -> list[str]:
    casa = pathlib.Path.home() / ".claude/hooks"
    if not casa.is_dir():
        return []
    return [f"aviso: ~/.claude/hooks/{p.name} difiere de .claude/hooks/{p.name} (copiar la versionada, CLAUDE.md)"
            for p in sorted(casa.iterdir())
            if p.is_file() and (MAQ / ".claude/hooks" / p.name).is_file()
            and not iguales(p, MAQ / ".claude/hooks" / p.name)]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")  # la consola de Windows rompe las tildes
    bloquean = skills_al_dia() + agentes_bien_formados()
    for linea in bloquean + copias_de_hooks():
        print(linea)
    if not bloquean:
        print("sistema multiagente: punteros de Codex y agentes OK")
    return 1 if bloquean else 0


if __name__ == "__main__":
    sys.exit(main())
