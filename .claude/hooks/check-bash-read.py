"""PreToolUse(Bash) - complemento de check-file-size.py: intercepta el mismo
patron cuando se intenta esquivar el hook de Read leyendo el archivo grande
por shell (`cat archivo`, `type archivo`). Un comando con pipe (`cat x | grep
y`, `head`, `sed -n`, etc.) ya esta acotado y siempre pasa - ahi esta el
filtro, igual que un offset/limit en Read.

Solo mira comandos que EMPIEZAN en cat/type (a lo sumo despues de un `cd ... &&`).
No intenta parsear pipelines completos: si hay '|' en cualquier parte, pasa.

Umbral: SHUNT_MIN_LINES (default 350). SHUNT_DISABLE=1 lo apaga.
exit 2 = bloqueado, stderr vuelve al agente. exit 0 = pasa.
"""
import json
import os
import re
import sys

FULL_READ_RE = re.compile(r"^\s*(?:cd\s+\S+\s*&&\s*)?(cat|type)\s+(.+)$")


def _candidate_paths(args_str):
    # Heuristica simple: tokens que no empiezan con '-' (flags). No maneja
    # comillas con espacios internos a proposito - falla abierto (no bloquea)
    # si no encuentra nada razonable.
    paths = []
    for tok in args_str.split():
        tok = tok.strip("\"'")
        if tok.startswith("-"):
            continue
        paths.append(tok)
    return paths


def main():
    if os.environ.get("SHUNT_DISABLE") == "1":
        return 0

    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    cmd = (payload.get("tool_input", {}) or {}).get("command", "")
    if not cmd or "|" in cmd:
        return 0

    match = FULL_READ_RE.match(cmd)
    if not match:
        return 0

    threshold = int(os.environ.get("SHUNT_MIN_LINES", "350"))
    big_files = []
    for path in _candidate_paths(match.group(2)):
        try:
            if not os.path.isfile(path):
                continue
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                line_count = sum(1 for _ in fh)
        except Exception:
            continue
        if line_count > threshold:
            big_files.append((path, line_count))

    if not big_files:
        return 0

    detalle = "\n".join("  - %s (%d lineas)" % (p, n) for p, n in big_files)
    sys.stderr.write(
        "BLOQUEADO por check-bash-read.py - lectura completa de archivo(s) "
        "grande(s) por shell (> %d lineas):\n%s\n\n"
        "Usa bulk-read.sh (motor barato) en vez de volcarlo entero:\n\n"
        '  bash ~/.claude/scripts/bulk-read.sh --question "<tu pregunta>" --paths "%s"\n\n'
        "Si solo necesitas una parte, filtra con pipe (grep/head/tail/sed -n) "
        "- eso siempre pasa. Ver skill /shunt para mas detalle.\n"
        % (threshold, detalle, big_files[0][0])
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
