#!/usr/bin/env bash
# shunt de lectura para GitHub: corre un subcomando DE SOLO LECTURA de gh,
# captura la salida a un temporal aislado, y delega a bulk-read.sh. Nunca
# corre pr create/merge/close/edit/comment/ready - eso sigue siendo de
# Claude via MCP o gh directo, protegido por git-guard.sh (que NO cubre este
# script: su regex es especifica a "gh pr create", asi que el rechazo de
# mutaciones vive aca adentro, no ahi). agy nunca corre gh el mismo.
#
# Uso: gh-read-shunt.sh --question "..." -- pr view 42 --json comments,reviews
#      gh-read-shunt.sh --question "..." -- pr diff 42
#      gh-read-shunt.sh --question "..." -- api repos/AcmeOrg/api-core/pulls/42/comments
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

QUESTION=""
GHARGS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --question) QUESTION="$2"; shift 2 ;;
    --) shift; GHARGS=("$@"); break ;;
    *) echo "Argumento desconocido: $1" >&2; exit 1 ;;
  esac
done

if [ -z "$QUESTION" ] || [ ${#GHARGS[@]} -eq 0 ]; then
  echo 'Uso: gh-read-shunt.sh --question "..." -- <subcomando gh de solo lectura> [args]' >&2
  exit 1
fi

SUB="${GHARGS[0]:-} ${GHARGS[1]:-}"
case "$SUB" in
  "pr view"|"pr diff"|"pr checks"|"pr status") ;;
  "api "*)
    for A in "${GHARGS[@]}"; do
      case "$A" in
        -X|--method) echo "Rechazado: 'gh api' con --method (no-GET) no corre aca." >&2; exit 1 ;;
      esac
    done
    ;;
  *)
    echo "Rechazado: 'gh ${GHARGS[*]}' no esta en la lista de solo lectura (pr view/diff/checks/status, api GET)." >&2
    echo "gh pr create/merge/close/edit siguen siendo de Claude via MCP o Bash directo (git-guard.sh)." >&2
    exit 1
    ;;
esac

TMPDIR_OWN=$(mktemp -d)
trap 'rm -rf "$TMPDIR_OWN"' EXIT
OUT="$TMPDIR_OWN/gh-output.txt"

gh "${GHARGS[@]}" > "$OUT" 2>&1
if [ ! -s "$OUT" ]; then
  echo "gh no devolvio nada para: gh ${GHARGS[*]}" >&2
  exit 1
fi

bash "$SCRIPT_DIR/bulk-read.sh" --question "$QUESTION" --paths "$OUT"
