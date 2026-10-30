#!/usr/bin/env bash
# Simula la cola de merges de un repo sin tocar ninguna rama (git merge-tree): parte del origin/develop actual
# y mergea, en orden de número, cada PR abierto contra develop; cada PR entra sobre el resultado de los anteriores.
#
#   simular-cola.sh <repo> [rama]     p. ej. simular-cola.sh web-app feature/mi-rama
#
# [rama]: se agrega al final de la cola (la de /worktree sincronizar, antes de abrir su PR); vale origin/<rama> o la local.
# Imprime por PR "OK <#n> <rama>" o "CONFLICTO <#n> <rama> <archivos>". Un PR que choca no entra a la base simulada.
# Sale 0 si todo entra limpio, 1 si hay algún conflicto, 2 por error de uso o de git/gh. Solo lee (fetch incluido).
set -uo pipefail

AQUI=$(cd "$(dirname "$0")" && pwd)
# Los repos hijos viven en la raíz del checkout principal, también cuando el script corre desde un worktree.
RAIZ=$(cd "$(git -C "$AQUI" rev-parse --path-format=absolute --git-common-dir)/.." && pwd)
nombre=${1:?uso: simular-cola.sh <repo> [rama]}; extra=${2:-}
REPO=$RAIZ/$nombre
[[ -d $REPO ]] || { echo "no existe el repo $REPO" >&2; exit 2; }

git -C "$REPO" fetch -q origin || { echo "git fetch falló en $REPO" >&2; exit 2; }
prs=$(gh pr list -R "<org>/$nombre" --state open --base develop --json number,headRefName \
  --jq 'sort_by(.number) | .[] | "#\(.number)\t\(.headRefName)"') || { echo "gh pr list falló" >&2; exit 2; }
if [[ -n $extra ]]; then
  ref=origin/$extra
  git -C "$REPO" rev-parse -q --verify "$ref" >/dev/null || ref=$extra
  git -C "$REPO" rev-parse -q --verify "$ref" >/dev/null || { echo "no existe la rama $extra en $REPO" >&2; exit 2; }
  grep -q $'\t'"$extra"'$' <<<"$prs" || prs+=${prs:+$'\n'}$'(sin PR)\t'"$extra"
fi
[[ -n $prs ]] || { echo "sin PRs abiertos contra develop en $nombre"; exit 0; }

base=$(git -C "$REPO" rev-parse origin/develop)
choques=0
while IFS=$'\t' read -r n rama; do
  ref=origin/$rama
  git -C "$REPO" rev-parse -q --verify "$ref" >/dev/null || ref=$rama
  out=$(git -C "$REPO" merge-tree --write-tree --name-only "$base" "$ref" 2>&1); rc=$?
  if ((rc == 0)); then
    base=$(git -C "$REPO" commit-tree "$(head -1 <<<"$out")" -p "$base" -p "$ref" -m sim)
    echo "OK $n $rama"
  elif ((rc != 1)); then  # 1 es conflicto; otro código es un error de git (rama inexistente, git viejo)
    echo "ERROR $n $rama: $(tail -1 <<<"$out")" >&2; exit 2
  else
    # Tras el OID del árbol vienen los archivos en conflicto hasta la primera línea vacía.
    archivos=$(sed -n '2,/^$/p' <<<"$out" | grep -v '^$' | sort -u | paste -sd' ')
    echo "CONFLICTO $n $rama ${archivos:-$(tail -1 <<<"$out")}"
    choques=$((choques + 1))
  fi
done <<<"$prs"
((choques == 0))
