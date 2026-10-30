#!/usr/bin/env bash
# ¿Siguen valiendo las rondas limpias de Codex de un PR apilado tras un push?
#   rondas-vigentes.sh <repo> <pr> <sha-de-las-limpias>     p. ej. rondas-vigentes.sh web-app <pr> <sha>
# Compara el diff PROPIO del PR (lo que agrega sobre su base) en el commit donde salieron las limpias y en el actual.
# Si es el mismo (el push solo trajo lo propagado desde abajo), imprime VIGENTES y las limpias se conservan.
# Si cambió, imprime REINICIAR: hay que volver a pedir 2 rondas. Sale 0 en VIGENTES y 1 en REINICIAR.
set -uo pipefail
AQUI=$(cd "$(dirname "$0")" && pwd)
RAIZ=$(git -C "$AQUI" rev-parse --show-toplevel)
nombre=${1:?repo}; pr=${2:?pr}; antes=${3:?sha de las rondas limpias}
REPO=$RAIZ/$nombre
read -r base ahora < <(gh pr view "$pr" -R "<org>/$nombre" --json baseRefName,headRefOid -q '"\(.baseRefName) \(.headRefOid)"')
git -C "$REPO" fetch -q origin "$base" 2>/dev/null
B=origin/$base
# `B...C` = cambios de C desde su punto de unión con la base: lo propio del PR en ese momento, sin lo propagado.
propio() { git -C "$REPO" diff "$B...$1" | git -C "$REPO" patch-id --stable | awk '{print $1}' | sort | sha1sum | cut -c1-12; }
p_antes=$(propio "$antes"); p_ahora=$(propio "$ahora")
if [[ $p_antes == "$p_ahora" ]]; then
  echo "VIGENTES: el diff propio de #$pr no cambió entre ${antes:0:7} y ${ahora:0:7} (solo entró lo propagado)"; exit 0
fi
echo "REINICIAR: el diff propio de #$pr cambió entre ${antes:0:7} y ${ahora:0:7}"
git -C "$REPO" diff --stat "$antes" "$ahora" -- $(git -C "$REPO" diff --name-only "$B...$ahora") | tail -3
exit 1
