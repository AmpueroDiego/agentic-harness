#!/usr/bin/env bash
# Verifica un PR de web-app en local, como lo haría el CI: mezcla la rama del PR con origin/develop en un
# worktree temporal y corre tsc, eslint y vitest. Existe porque el CI de web-app solo corre al abrir el PR
# (types: [opened]) y no se modifica; el verde de un PR abierto no dice nada del commit actual.
#
#   verificar-pr.sh <PR> [<PR>...]      p. ej.: verificar-pr.sh 50 51 52
#   REPO=web-app  (por defecto; solo web-app por ahora)
#
# Logs en $SALIDA (por defecto un directorio temporal) y un resumen por PR al final. No toca la carpeta principal.
set -uo pipefail

MAQ=$(git -C "$(dirname "$0")" rev-parse --show-toplevel)
REPO=${REPO:-web-app}
[[ $REPO == web-app ]] || { echo "Solo web-app por ahora (.NET: pendiente)" >&2; exit 2; }
(( $# )) || { echo "uso: verificar-pr.sh <PR> [<PR>...]" >&2; exit 2; }

DIR=$MAQ/$REPO
SALIDA=${SALIDA:-$(mktemp -d)}
mkdir -p "$SALIDA"
git -C "$DIR" fetch -q origin || { echo "git fetch falló" >&2; exit 1; }

resumen=()
for pr in "$@"; do
  rama=$(gh pr view "$pr" -R "<org>/$REPO" --json headRefName --jq .headRefName 2>/dev/null)
  [[ -n $rama ]] || { resumen+=("PR$pr: no se pudo leer la rama"); continue; }

  W=$SALIDA/pr$pr
  git -C "$DIR" worktree add -q --detach "$W" "origin/$rama" 2>>"$SALIDA/pr$pr.log" \
    || { resumen+=("PR$pr: worktree falló (ver pr$pr.log)"); continue; }

  (
    cd "$W" || exit 1
    # Simula el estado tras mergear: la rama del PR + develop actual.
    if ! git -c user.name=verificar -c user.email=verificar@local merge -q --no-edit origin/develop >>"$SALIDA/pr$pr.log" 2>&1; then
      echo "PR$pr ($rama): CONFLICTO al mezclar con develop"; exit 0
    fi
    # Siempre npm ci en el árbol temporal: es su propia carpeta, sin enlaces ni junctions a la principal
    # (borrar un enlace así llegó a vaciar los node_modules reales, y una carpeta vacía daba ROJO falso).
    npm ci --prefer-offline --no-audit --no-fund >>"$SALIDA/pr$pr.log" 2>&1 || { echo "PR$pr ($rama): npm ci falló"; exit 0; }
    npx tsc -b >"$SALIDA/pr$pr.tsc.log" 2>&1; t=$?
    npx eslint . >"$SALIDA/pr$pr.eslint.log" 2>&1; e=$?
    npx vitest run >"$SALIDA/pr$pr.vitest.log" 2>&1; v=$?
    pruebas=$(sed 's/\x1b\[[0-9;]*m//g' "$SALIDA/pr$pr.vitest.log" | grep -E "Tests " | tr -s ' ')
    estado=VERDE; (( t || e || v )) && estado=ROJO
    echo "PR$pr ($rama) $estado — tsc=$t eslint=$e vitest=$v —$pruebas"
  ) | tee -a "$SALIDA/resumen.txt"
  # Quita el worktree temporal (su node_modules es propio, se borra con él).
  git -C "$DIR" worktree remove --force "$W" >/dev/null 2>&1
done

echo; echo "## Resumen (logs en $SALIDA)"; cat "$SALIDA/resumen.txt" 2>/dev/null
