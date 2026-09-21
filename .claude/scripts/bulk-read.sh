#!/usr/bin/env bash
# "shunt" (inspirado en Portal by Spotify): le pasa las RUTAS de los archivos
# grandes a un modelo barato (agy/Gemini flash), que las lee con sus propias
# herramientas (--add-dir) y responde. El contenido del archivo nunca pasa
# por argv de este script ni por el contexto de Claude - solo la respuesta.
#
# (Ojo: no se puede embeber el contenido del archivo en --print="..." como
# hace el articulo original de Portal - en Windows eso choca con el limite
# de longitud de linea de comando a partir de ~30-60 KB. Pasar la ruta y
# dejar que agy la lea con su propio tool de lectura lo evita del todo.)
#
# Uso: bulk-read.sh --question "..." --paths archivo1 [archivo2 ...]
set -euo pipefail

AGY="${SHUNT_AGY_BIN:-$HOME/AppData/Local/agy/bin/agy.exe}"
MODEL="${SHUNT_MODEL:-gemini-3.8-flash-medium}"
TIMEOUT="${SHUNT_TIMEOUT:-90s}"

QUESTION=""
PATHS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --question)
      QUESTION="$2"; shift 2 ;;
    --paths)
      shift
      while [ $# -gt 0 ] && [[ "$1" != --* ]]; do PATHS+=("$1"); shift; done
      ;;
    *)
      echo "Argumento desconocido: $1" >&2
      exit 1
      ;;
  esac
done

if [ -z "$QUESTION" ] || [ ${#PATHS[@]} -eq 0 ]; then
  echo 'Uso: bulk-read.sh --question "..." --paths archivo1 [archivo2 ...]' >&2
  exit 1
fi

if [ ! -f "$AGY" ]; then
  echo "No se encontro el CLI de agy en '$AGY'. Fijar SHUNT_AGY_BIN si esta en otra ruta." >&2
  exit 1
fi

ADD_DIRS=()
FILE_LIST=""
for F in "${PATHS[@]}"; do
  if [ ! -f "$F" ]; then
    echo "Aviso: no existe '$F', se omite." >&2
    continue
  fi
  DIR=$(dirname "$F")
  FOUND=0
  for D in "${ADD_DIRS[@]:-}"; do [ "$D" = "$DIR" ] && FOUND=1 && break; done
  [ "$FOUND" -eq 0 ] && ADD_DIRS+=("$DIR")
  FILE_LIST="$FILE_LIST- $F
"
done

if [ ${#ADD_DIRS[@]} -eq 0 ]; then
  echo "Ninguno de los archivos pasados existe." >&2
  exit 1
fi

ADD_DIR_ARGS=()
for D in "${ADD_DIRS[@]}"; do ADD_DIR_ARGS+=(--add-dir "$D"); done

PROMPT="Sos un analista de codigo preciso. Lee con tus herramientas los archivos listados abajo y responde la pregunta de forma concisa, en bullets estructurados. Sin saludos, sin prosa, sin preambulos.

Archivos:
${FILE_LIST}
Pregunta: ${QUESTION}"

EFFORT_ARGS=()
[ -n "${SHUNT_EFFORT:-}" ] && EFFORT_ARGS=(--effort "$SHUNT_EFFORT")

"$AGY" --model "$MODEL" "${EFFORT_ARGS[@]}" --mode plan "${ADD_DIR_ARGS[@]}" --print="$PROMPT" --print-timeout "$TIMEOUT"
