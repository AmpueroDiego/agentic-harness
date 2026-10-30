#!/usr/bin/env bash
# Abre el PR de un worktree contra develop y lo adjunta a su tarjeta de Trello. Solo cuando el responsable pide el PR.
#
#   entregar-pr.sh <repo> <worktree> <tarjeta> <cuerpo.md> --titulo "..." [--listo] [--simular]
#   p. ej.: entregar-pr.sh web-app web-app--nuevo-flujo '<card-id>' scratch/pr.md --titulo "feat: nuevo flujo" --simular
#
# <worktree>: ruta o nombre bajo .worktrees/. <tarjeta>: shortLink o URL de Trello.
# Valida antes de escribir: rama distinta de develop/main/qa, árbol limpio, origin/develop presente, commits
# por delante de develop, cuerpo UTF-8 sin BOM con "## Antes", "## Ahora" y "## Qué se arregló", y que la
# tarjeta exista. Luego: push -u, gh pr create --draft --base develop --reviewer <revisor-principal>, adjunto en Trello
# y, si la tarjeta sigue en "En desarrollo", la pasa a "En revisión (el responsable)".
# El PR nace en borrador (el CI lo salta hasta "Listo para revisión"); --listo lo abre listo para revisión.
# REVISOR configura la cuenta GitHub del revisor; el placeholder solo sirve en --simular.
# Si ya hay un PR abierto de la rama, lo reutiliza. --simular: valida y muestra el plan, sin escribir nada.
set -euo pipefail

uso() { sed -n '2,13p' "$0" | sed 's/^# \{0,1\}//'; }

RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
TRELLO=(python "$RAIZ/.claude/tools/trello/trello.py")
REVISOR=${REVISOR:-'<revisor-principal>'}
SIMULAR=0; TITULO=""; BORRADOR=(--draft); pos=()
while (($#)); do
  case $1 in
    --simular) SIMULAR=1 ;;
    --listo) BORRADOR=() ;;
    --titulo) TITULO=${2:?--titulo requiere un texto}; shift ;;
    -h|--help) uso; exit 0 ;;
    -*) echo "Opción desconocida: $1" >&2; exit 2 ;;
    *) pos+=("$1") ;;
  esac
  shift
done
((${#pos[@]} == 4)) || { uso >&2; exit 2; }
REPO=${pos[0]}; OBJ=${pos[1]}; TARJETA=${pos[2]}; CUERPO=${pos[3]}
[[ -n ${TITULO// } ]] || { echo "Falta --titulo" >&2; exit 2; }

paso() { echo "[$(date -u +%H:%M:%SZ)] $*"; }
falla() { echo "ERROR: $*" >&2; exit 1; }
escribir() { if ((SIMULAR)); then echo "  [simular] $*"; else "$@"; fi; }

((SIMULAR)) || [[ $REVISOR != '<revisor-principal>' ]] || falla "configurá REVISOR con la cuenta de revisión"

# --- Validaciones -------------------------------------------------------------------------------------------
if [[ -d $OBJ ]]; then WT=$(cd "$OBJ" && pwd)
elif [[ -d $RAIZ/.worktrees/$OBJ ]]; then WT=$RAIZ/.worktrees/$OBJ
else falla "no existe el worktree $OBJ"; fi

RAMA=$(git -C "$WT" branch --show-current)
[[ -n $RAMA ]] || falla "$WT está en HEAD separado"
[[ $RAMA != develop && $RAMA != main && $RAMA != qa && $RAMA != master ]] || falla "la rama es $RAMA: un PR sale de una rama de trabajo"
[[ -z $(git -C "$WT" status --porcelain) ]] || falla "$WT tiene cambios sin commitear"

OR=$(git -C "$WT" remote get-url origin | sed -E 's#^.*github\.com[:/]##; s#\.git$##')
[[ ${OR#*/} == "$REPO" ]] || falla "el origin del worktree es $OR, no */$REPO"
git -C "$WT" rev-parse -q --verify origin/develop >/dev/null || falla "no existe origin/develop en $OR"
adelante=$(git -C "$WT" rev-list --count origin/develop..HEAD)
((adelante > 0)) || falla "la rama no tiene commits por delante de origin/develop"

[[ -s $CUERPO ]] || falla "cuerpo vacío o inexistente: $CUERPO"
[[ $(head -c3 "$CUERPO" | od -An -tx1 | tr -d ' \n') != efbbbf ]] || falla "$CUERPO tiene BOM: guardalo UTF-8 sin BOM"
iconv -f UTF-8 -t UTF-8 "$CUERPO" >/dev/null 2>&1 || falla "$CUERPO no es UTF-8 válido"
for s in "## Antes" "## Ahora" "## Qué se arregló"; do
  grep -qE "^$s[[:space:]]*\$" "$CUERPO" || falla "al cuerpo le falta la sección '$s'"
done
command -v cygpath >/dev/null && CUERPO=$(cygpath -m "$CUERPO")  # gh.exe nativo no traduce rutas /tmp/...

paso "PR de $OR: $RAMA → develop ($adelante commit(s)), tarjeta $TARJETA$( ((SIMULAR)) && echo ' (SIMULACIÓN)')"
VER=$("${TRELLO[@]}" ver "$TARJETA" 2>/dev/null) || {
  ((SIMULAR)) && echo "AVISO: no se pudo leer la tarjeta $TARJETA (en real se detendría acá)" || falla "no se pudo leer la tarjeta $TARJETA"; }
COLUMNA=$(sed -n 's/^Columna: //p' <<<"${VER:-}" | tr -d '\r')

buscar_pr() {  # → número<TAB>url<TAB>base del PR abierto de la rama, o nada
  gh pr list -R "$OR" --head "$RAMA" --state open --json number,url,baseRefName \
    --jq '.[0] | select(. != null) | "\(.number)\t\(.url)\t\(.baseRefName)"'
}
EXISTE=$(buscar_pr)
if [[ -n $EXISTE ]]; then
  IFS=$'\t' read -r N URL BASE <<<"$EXISTE"
  [[ $BASE == develop ]] || falla "ya hay un PR abierto (#$N) contra $BASE, no develop: corregilo a mano"
  paso "ya existe el PR #$N ($URL): no se crea otro"
fi

# --- 1. Push ------------------------------------------------------------------------------------------------
paso "push -u origin $RAMA"
escribir git -C "$WT" push -u origin "$RAMA"

# --- 2. PR --------------------------------------------------------------------------------------------------
if [[ -z $EXISTE ]]; then
  paso "gh pr create ${BORRADOR[*]} --base develop --reviewer $REVISOR"
  if ((SIMULAR)); then
    echo "  [simular] gh pr create -R $OR --head $RAMA --base develop ${BORRADOR[*]} --title \"$TITULO\" --body-file $CUERPO --reviewer $REVISOR"
    N="<n>"; URL="https://github.com/$OR/pull/<n>"
  else
    if URL=$(cd "$WT" && gh pr create -R "$OR" --head "$RAMA" --base develop "${BORRADOR[@]}" --title "$TITULO" --body-file "$CUERPO" --reviewer "$REVISOR"); then
      URL=$(grep -oE 'https://github\.com/[^ ]+/pull/[0-9]+' <<<"$URL" | tail -1 || :)
      [[ -n $URL ]] || falla "gh pr create no devolvió la URL; buscalo con gh pr list -R $OR --head $RAMA"
      N=${URL##*/}; BASE=develop
    else
      # El revisor se agrega después de crear el PR: un error de GraphQL ahí deja el PR creado igual.
      EXISTE=$(buscar_pr)
      [[ -n $EXISTE ]] || falla "gh pr create falló y no hay PR abierto de $RAMA"
      IFS=$'\t' read -r N URL BASE <<<"$EXISTE"
      paso "gh pr create devolvió error pero el PR #$N existe; se reintenta el revisor"
      gh pr edit "$N" -R "$OR" --add-reviewer "$REVISOR" >/dev/null \
        || echo "AVISO: no se pudo agregar a $REVISOR; agregalo a mano: gh pr edit $N -R $OR --add-reviewer $REVISOR"
    fi
    [[ $BASE == develop ]] || falla "el PR #$N quedó contra $BASE"
    paso "PR #$N: $URL"
  fi
fi

# --- 3. Trello ----------------------------------------------------------------------------------------------
paso "adjuntar a la tarjeta $TARJETA: \"#$N $TITULO\""
escribir "${TRELLO[@]}" adjuntar "$TARJETA" --url "$URL" --nombre "#$N $TITULO" --aplicar
# Con el PR abierto la tarjeta pasa a En revisión (el responsable), nunca a Revisor Principal (retro 2026-10-27).
# trello.py se niega sin fechas o miembros: se avisa y la entrega sigue, el PR ya está.
if [[ $COLUMNA == "En desarrollo" ]]; then
  paso "mover la tarjeta $TARJETA: En desarrollo → En revisión (el responsable)"
  escribir "${TRELLO[@]}" actualizar "$TARJETA" --columna "En revisión (el responsable)" --aplicar \
    || echo "AVISO: no se pudo mover la tarjeta a «En revisión (el responsable)»; completala y movela con /trello" >&2
else
  paso "la tarjeta está en «${COLUMNA:-?}»: no se mueve"
fi
paso "listo: $URL"
