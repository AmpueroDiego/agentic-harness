#!/usr/bin/env bash
# Varios coders de Codex en paralelo sobre UN worktree, cada uno con sus archivos (dueño exclusivo).
#   carriles.sh <RAIZ> <SALIDA> <prompt1.md> [prompt2.md ...]
# Un carril por prompt; el nombre del prompt (sin .md) da el log <SALIDA>/<nombre>.log.
# Modelo: gpt-6-luna en fast, obligatorio para coders (el responsable, 2026-10-19).
# No commitea: los coders no tocan git. Termina cuando terminan todos y muestra el final de cada log.
set -uo pipefail
RAIZ=${1:?raiz}; SALIDA=${2:?salida}; shift 2
MODELO=${CODEX_MODEL:-gpt-6-luna}
[[ $MODELO == gpt-6-luna ]] || { echo "Coder solo con gpt-6-luna (pedido: $MODELO)" >&2; exit 2; }
mkdir -p "$SALIDA"
pids=()
for p in "$@"; do
  n=$(basename "$p" .md)
  (cd "$RAIZ" && timeout 30m codex exec --sandbox workspace-write -m "$MODELO" -c model_provider=openai -c service_tier="fast" -c windows.sandbox=\"unelevated\" -c model_reasoning_effort="${CODEX_EFFORT:-medium}" "$(cat "$p")" < /dev/null > "$SALIDA/$n.log" 2>&1) &
  pids+=($!)
done
for pid in "${pids[@]}"; do wait "$pid"; done
for p in "$@"; do n=$(basename "$p" .md); echo "== $n"; grep -q "tokens used" "$SALIDA/$n.log" && tail -12 "$SALIDA/$n.log" | cut -c1-260 || echo "SIN CIERRE: revisar $SALIDA/$n.log"; done
python "$(dirname "$0")/revisar-tildes.py" "$RAIZ"
