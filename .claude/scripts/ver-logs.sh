#!/usr/bin/env bash
# Para un panel de Herdr por worktree: muestra en vivo los logs del trabajo. Solo mirar, no cambia nada.
#   ver-logs.sh <carpeta-de-salida>     (la SALIDA que usó flujo.sh/carriles.sh)
# Sin argumento, usa la carpeta de scratchpad más reciente.
DIR=${1:-$(ls -dt "$TEMP"/claude/*/*/scratchpad/*/ 2>/dev/null | head -1)}
[[ -d $DIR ]] || { echo "Carpeta no encontrada: $DIR" >&2; exit 1; }
echo "Vigilando $DIR (Ctrl+C para salir)"
tail -n 3 -F "$DIR"/*.log 2>/dev/null | cut -c1-200
