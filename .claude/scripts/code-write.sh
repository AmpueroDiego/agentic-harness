#!/usr/bin/env bash
# "shunt" (inspirado en Portal by Spotify): genera un archivo de codigo a
# partir de una spec + un archivo de referencia (que agy lee el mismo con
# --add-dir, no embebido por argv - ver bulk-read.sh para el porque). Corre
# en modo plan (solo lee/razona, no toca archivos); este script es el que
# escribe a disco y limpia fences de markdown - Claude nunca ve el codigo
# generado, solo la confirmacion.
#
# Pensado para tareas mecanicas y acotadas dentro del reparto de coders de
# /orquestar (junto a agy/codex como coders propios) - el resultado sigue
# pasando por QA y adversary como cualquier otro coder, esto no reemplaza
# esa verificacion.
#
# Uso: code-write.sh --spec "..." [--reference archivo_referencia] --target archivo_destino
set -euo pipefail

AGY="${SHUNT_AGY_BIN:-$HOME/AppData/Local/agy/bin/agy.exe}"
MODEL="${SHUNT_MODEL:-gemini-3.8-flash-medium}"
TIMEOUT="${SHUNT_TIMEOUT:-90s}"

SPEC=""
REFERENCE=""
TARGET=""
while [ $# -gt 0 ]; do
  case "$1" in
    --spec) SPEC="$2"; shift 2 ;;
    --reference) REFERENCE="$2"; shift 2 ;;
    --target) TARGET="$2"; shift 2 ;;
    *) echo "Argumento desconocido: $1" >&2; exit 1 ;;
  esac
done

if [ -z "$SPEC" ] || [ -z "$TARGET" ]; then
  echo 'Uso: code-write.sh --spec "..." [--reference archivo] --target archivo_destino' >&2
  exit 1
fi

if [ ! -f "$AGY" ]; then
  echo "No se encontro el CLI de agy en '$AGY'. Fijar SHUNT_AGY_BIN si esta en otra ruta." >&2
  exit 1
fi

ADD_DIR_ARGS=()
REF_LINE=""
if [ -n "$REFERENCE" ] && [ -f "$REFERENCE" ]; then
  ADD_DIR_ARGS+=(--add-dir "$(dirname "$REFERENCE")")
  REF_LINE="Archivo de referencia (leelo con tus herramientas antes de generar): $REFERENCE"
fi

PROMPT="Generas archivos de codigo a partir de una especificacion y, si se da, un archivo de referencia.
Si hay archivo de referencia, igualalo exactamente en estilo, convenciones, nombres y patrones.
Devolve SOLO el contenido final del archivo de destino como texto plano. Sin explicaciones, sin fences de markdown.

${REF_LINE}
Spec: ${SPEC}
Destino: ${TARGET}"

EFFORT_ARGS=()
[ -n "${SHUNT_EFFORT:-}" ] && EFFORT_ARGS=(--effort "$SHUNT_EFFORT")

RAW=$("$AGY" --model "$MODEL" "${EFFORT_ARGS[@]}" --mode plan "${ADD_DIR_ARGS[@]:-}" --print="$PROMPT" --print-timeout "$TIMEOUT")

if [ -z "$RAW" ]; then
  echo "El modelo no devolvio contenido. No se escribio '$TARGET'." >&2
  exit 1
fi

# Pela SOLO un fence que envuelve toda la respuesta (primera/ultima linea),
# no cualquier linea que empiece con ``` - un ADR puede traer un bloque de
# codigo legitimo adentro y borrar toda linea con fence lo rompería.
CODE="$RAW"
FIRST_LINE=$(printf '%s\n' "$CODE" | head -n1)
if [[ "$FIRST_LINE" == '```'* ]]; then
  CODE=$(printf '%s\n' "$CODE" | tail -n +2)
fi
LAST_LINE=$(printf '%s\n' "$CODE" | tail -n1)
if [[ "$LAST_LINE" == '```' ]]; then
  CODE=$(printf '%s\n' "$CODE" | sed '$d')
fi

mkdir -p "$(dirname "$TARGET")"
printf '%s\n' "$CODE" > "$TARGET"

LINES=$(wc -l < "$TARGET" | tr -d ' ')
echo "Escrito: $TARGET ($LINES lineas). Este motor no reemplaza QA/adversary - revisar antes de dar la tarea por cerrada."
