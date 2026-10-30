#!/usr/bin/env bash
# shunt de lectura para Trello: corre un subcomando DE SOLO LECTURA de
# trello.py, captura su salida a un archivo temporal aislado, y delega a
# bulk-read.sh para que agy la lea (--add-dir) y responda una pregunta
# puntual. agy nunca corre trello.py - solo este script, subproceso de
# Claude, lo invoca. Ver .claude/commands/shunt.md.
#
# Las mutaciones (crear/actualizar/adjuntar/comentar/ordenar) NO pasan por
# aca: su salida en modo simulacion/--aplicar ya es corta por diseno
# (trello.py imprime la propuesta o la verificacion, no el objeto crudo) -
# pasarla por agy no ahorraria nada y si sumaria latencia. Se siguen
# corriendo directo, como documenta /trello.
#
# Uso: trello-read-shunt.sh --question "..." -- <tablero|buscar|listar|ver> [args]
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
TRELLO_PY="$REPO_ROOT/.claude/tools/trello/trello.py"

QUESTION=""
SUBARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --question) QUESTION="$2"; shift 2 ;;
    --) shift; SUBARGS=("$@"); break ;;
    *) echo "Argumento desconocido: $1" >&2; exit 1 ;;
  esac
done

if [ -z "$QUESTION" ] || [ ${#SUBARGS[@]} -eq 0 ]; then
  echo 'Uso: trello-read-shunt.sh --question "..." -- <tablero|buscar|listar|ver> [args]' >&2
  exit 1
fi

case "${SUBARGS[0]}" in
  tablero|buscar|listar|ver) ;;
  *)
    echo "Rechazado: '${SUBARGS[0]}' no es de solo lectura." >&2
    echo "Este script solo corre tablero/buscar/listar/ver. Las mutaciones van directo con trello.py (ver /trello)." >&2
    exit 1
    ;;
esac

if [ ! -f "$TRELLO_PY" ]; then
  echo "No se encontro trello.py en '$TRELLO_PY'." >&2
  exit 1
fi

# Directorio temporal propio (no un archivo suelto en /tmp compartido):
# --add-dir le da a agy acceso de lectura a TODO el directorio, no solo al
# archivo - aislarlo evita exponer temporales de otras sesiones/herramientas.
TMPDIR_OWN=$(mktemp -d)
trap 'rm -rf "$TMPDIR_OWN"' EXIT
OUT="$TMPDIR_OWN/trello-output.txt"

python "$TRELLO_PY" "${SUBARGS[@]}" > "$OUT" 2>&1
if [ ! -s "$OUT" ]; then
  echo "trello.py no devolvio nada para: ${SUBARGS[*]}" >&2
  exit 1
fi

bash "$SCRIPT_DIR/bulk-read.sh" --question "$QUESTION" --paths "$OUT"
