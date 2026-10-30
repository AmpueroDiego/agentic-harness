#!/usr/bin/env bash
# Pasa PRs ya verificados a revisión de Revisor Principal: sube cada rama, mueve su tarjeta a
# "En revisión (Revisor Principal)" (miembros el responsable + Revisor Principal, fechas) y ordena la columna.
#
# Uso, desde la raíz de AcmeOrg (por defecto solo muestra lo que haría):
#   bash .claude/scripts/a-revision.sh [--aplicar] <worktree>:<rama>:<tarjeta>:<inicio AAAA-MM-DD> ...
# El orden de los argumentos es el orden de la columna (el primero se mergea primero).
# Ejemplo:
#   bash .claude/scripts/a-revision.sh --aplicar \
#     'api-core--sincronizacion-robusta:fix/sincronizacion-robusta:<card-id>:2026-09-29'
#
# Solo lo corre el responsable (o lo autoriza): sube ramas y escribe en Trello. Nunca borra ni fuerza.
# MIEMBRO_RESPONSABLE y MIEMBRO_REVISOR configuran los usuarios del tablero; placeholders solo en simulación.
set -euo pipefail

APLICAR=0
if [ "${1:-}" = "--aplicar" ]; then APLICAR=1; shift; fi
[ $# -gt 0 ] || { echo "Uso: a-revision.sh [--aplicar] worktree:rama:tarjeta:inicio ..."; exit 2; }
MIEMBRO_RESPONSABLE=${MIEMBRO_RESPONSABLE:-'<responsable>'}
MIEMBRO_REVISOR=${MIEMBRO_REVISOR:-'<revisor-principal>'}
if [ "$APLICAR" -eq 1 ] && { [ "$MIEMBRO_RESPONSABLE" = '<responsable>' ] || [ "$MIEMBRO_REVISOR" = '<revisor-principal>' ]; }; then
  echo "Configurá MIEMBRO_RESPONSABLE y MIEMBRO_REVISOR con los usuarios del tablero" >&2
  exit 2
fi

RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
TRELLO="python $RAIZ/.claude/tools/trello/trello.py"
HOY="$(date +%F)"
ORDEN="$(mktemp)"
trap 'rm -f "$ORDEN"' EXIT

echo "Modo: $([ $APLICAR -eq 1 ] && echo APLICAR || echo simulación) | vence: $HOY"

for item in "$@"; do
  IFS=: read -r wt rama tarjeta inicio <<<"$item"
  ruta="$RAIZ/.worktrees/$wt"
  [ -d "$ruta" ] || { echo "No existe $ruta"; exit 1; }
  [ -z "$(git -C "$ruta" status --porcelain)" ] || { echo "$wt tiene cambios sin commitear: se detiene"; exit 1; }
  [ "$(git -C "$ruta" branch --show-current)" = "$rama" ] || { echo "$wt no está en la rama $rama"; exit 1; }
  adelante="$(git -C "$ruta" log --oneline "origin/$rama..HEAD" | wc -l | tr -d ' ')"
  echo "- $wt ($rama): $adelante commit(s) por subir; tarjeta $tarjeta, inicio $inicio"
  echo "$tarjeta" >> "$ORDEN"  # ordenar acepta shortLink o URL; no necesita una URL estática

  if [ $APLICAR -eq 1 ]; then
    [ "$adelante" = "0" ] || git -C "$ruta" push origin "$rama"
  fi
  $TRELLO actualizar "$tarjeta" --columna "En revisión (Revisor Principal)" \
    --miembro "$MIEMBRO_RESPONSABLE" --miembro "$MIEMBRO_REVISOR" \
    --inicio "$inicio" --vence "$HOY" $([ $APLICAR -eq 1 ] && echo --aplicar)
done

echo "Orden de la columna:"; cat "$ORDEN"
$TRELLO ordenar --columna "En revisión (Revisor Principal)" --orden-archivo "$ORDEN" $([ $APLICAR -eq 1 ] && echo --aplicar) || { [ $APLICAR -eq 1 ] && exit 1; echo "(simulación: el orden se valida cuando las tarjetas ya están en la columna)"; }
