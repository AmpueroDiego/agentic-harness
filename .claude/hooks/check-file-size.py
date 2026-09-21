"""PreToolUse(Read) - inspirado en Portal by Spotify ("shunt"): bloquea la
lectura completa de un archivo grande y redirige a bulk-read.sh, que lo resume
con un modelo barato (agy/Gemini) sin que el contexto de Claude cargue el
archivo entero. Una lectura acotada (offset/limit) siempre pasa: el objetivo
es la lectura completa "para responder una pregunta", no la edición puntual.

Umbral configurable via SHUNT_MIN_LINES (default 350, igual que el articulo).
SHUNT_DISABLE=1 lo desactiva por completo (troubleshooting).
exit 2 = bloqueado, stderr vuelve al agente. exit 0 = pasa.
"""
import json
import os
import sys

BINARY_EXT = {
    ".png", ".jpg", ".jpeg", ".gif", ".ico", ".bmp", ".webp", ".svg",
    ".pdf", ".woff", ".woff2", ".ttf", ".eot", ".exe", ".dll", ".zip",
    ".7z", ".rar", ".gz", ".pdb", ".so", ".pyc", ".class", ".jar",
}


def main():
    if os.environ.get("SHUNT_DISABLE") == "1":
        return 0

    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    tool_input = payload.get("tool_input", {}) or {}
    file_path = tool_input.get("file_path", "")
    if not file_path:
        return 0

    # Lectura ya acotada: siempre pasa, es exactamente el caso "edicion puntual"
    # que el articulo dice que el worker no puede resolver (sin numeros de linea
    # confiables).
    if tool_input.get("offset") or tool_input.get("limit"):
        return 0

    _, ext = os.path.splitext(file_path)
    if ext.lower() in BINARY_EXT:
        return 0

    try:
        if not os.path.isfile(file_path):
            return 0
        with open(file_path, "r", encoding="utf-8", errors="ignore") as fh:
            line_count = sum(1 for _ in fh)
    except Exception:
        # No se pudo contar: no bloquear a ciegas, que el Read tool lo maneje.
        return 0

    threshold = int(os.environ.get("SHUNT_MIN_LINES", "350"))
    if line_count <= threshold:
        return 0

    sys.stderr.write(
        "BLOQUEADO por check-file-size.py - '%s' tiene %d lineas (> %d).\n"
        "En vez de leerlo completo, resumilo con bulk-read.sh (motor barato, "
        "no gasta tu contexto):\n\n"
        '  bash ~/.claude/scripts/bulk-read.sh --question "<tu pregunta>" --paths "%s"\n\n'
        "Si necesitas editar una seccion puntual, usa Read con offset/limit "
        "(eso siempre pasa). Ver skill /shunt para mas detalle.\n"
        % (file_path, line_count, threshold, file_path)
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
