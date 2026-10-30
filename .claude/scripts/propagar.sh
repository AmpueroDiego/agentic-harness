#!/usr/bin/env bash
# Pasa los cambios por una pila de ramas en orden: merge de cada rama en la siguiente, con chequeo tras cada merge.
#   propagar.sh <repo> <rama1> <rama2> [rama3 ...]     p. ej. propagar.sh web-app feature/paso-2 feature/paso-3 ...
# Cada rama desde la 2 tiene que estar abierta en un worktree (git worktree list) y limpio.
# Frena en el primer conflicto que rerere no resuelva solo o en el primer chequeo rojo: no deja merges rotos subidos.
# CHEQUEO cambia la verificación (por defecto `npx tsc -b`; en api-core, p. ej. CHEQUEO="dotnet build --no-restore -v q").
# PUSH=1 sube al final las ramas que cambiaron. Nunca force push, nunca a develop/main/qa, nunca a la rama de un PR ya mergeado.
set -uo pipefail
RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
REPO=$RAIZ/${1:?repo (web-app, api-core...)}; shift
(( $# >= 2 )) || { echo "Hacen falta al menos dos ramas, en orden de la pila" >&2; exit 2; }
CHEQUEO=${CHEQUEO:-npx tsc -b}
RAMAS=("$@")

worktree_de() {  # $1 rama -> ruta del worktree que la tiene abierta
  git -C "$REPO" worktree list --porcelain | awk -v b="refs/heads/$1" '/^worktree /{w=substr($0,10)} $0=="branch "b{print w; exit}'
}

for r in "${RAMAS[@]}"; do
  [[ $r == develop || $r == main || $r == qa ]] && { echo "No se propaga hacia $r" >&2; exit 2; }
done

git -C "$REPO" fetch -q origin
cambiadas=()
for ((i = 1; i < ${#RAMAS[@]}; i++)); do
  origen=${RAMAS[i-1]}; destino=${RAMAS[i]}
  wt=$(worktree_de "$destino")
  [[ -n $wt ]] || { echo "PARADA: $destino no está abierta en ningún worktree (git -C $REPO worktree add <ruta> $destino)" >&2; exit 1; }
  [[ -z $(git -C "$wt" status --porcelain --untracked-files=no) ]] || { echo "PARADA: $wt tiene cambios sin commit" >&2; exit 1; }
  antes=$(git -C "$wt" rev-parse HEAD)
  # La rama local de origen es la más nueva (puede tener merges de este mismo ciclo sin subir).
  if git -C "$wt" merge-base --is-ancestor "$origen" HEAD; then
    echo "= $destino ya tiene $origen"
  elif git -C "$wt" merge --no-edit "$origen" > /dev/null 2>&1; then
    echo "+ $origen -> $destino: merge limpio"
  else
    pendientes=$(git -C "$wt" diff --name-only --diff-filter=U)
    if [[ -z $pendientes ]]; then
      git -C "$wt" commit -q --no-edit && echo "+ $origen -> $destino: conflictos resueltos por rerere (revisar el diff)"
    else
      echo "PARADA: conflicto en $destino ($wt) al traer $origen:" >&2; echo "$pendientes" | sed 's/^/  /' >&2
      echo "Resolverlo a mano, commitear y volver a correr: rerere lo recordará la próxima vez." >&2
      exit 1
    fi
  fi
  if [[ $(git -C "$wt" rev-parse HEAD) != "$antes" ]]; then
    (cd "$wt" && eval "$CHEQUEO") > /dev/null 2>&1 || { echo "PARADA: chequeo rojo en $destino tras traer $origen ($CHEQUEO en $wt)" >&2; exit 1; }
    echo "  chequeo verde en $destino"
    cambiadas+=("$destino")
  fi
done

(( ${#cambiadas[@]} )) || { echo "Nada que propagar"; exit 0; }
if [[ ${PUSH:-0} == 1 ]]; then
  for r in "${cambiadas[@]}"; do
    nombre=$(basename "$REPO")
    origen=$(git -C "$REPO" remote get-url origin | sed -E 's#^.*github\.com[:/]##; s#\.git$##')
    if [[ -n $(gh pr list -R "$origen" --head "$r" --state merged --json number -q '.[].number' 2>/dev/null) ]]; then
      echo "SIN PUSH: el PR de $r ya está mergeado" >&2; continue
    fi
    git -C "$REPO" push -q origin "$r" && echo "^ push $r"
  done
else
  echo "Ramas con cambios sin subir: ${cambiadas[*]} (PUSH=1 para subirlas)"
fi
