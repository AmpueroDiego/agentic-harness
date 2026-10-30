#!/usr/bin/env bash
# Un ciclo de /supercodex sobre un PR: sube la rama, atiende los hilos de Codex (reacción + respuesta en el
# mismo hilo + resolver) y, solo si no queda ningún hilo abierto, dispara `@codex review`. Imprime la hora T.
#
#   supercodex-ciclo.sh <repo> <pr> <rama-o-worktree> [--respuestas <archivo.tsv>] [--simular]
#   p. ej.: supercodex-ciclo.sh web-app 12 web-app--nuevo-flujo --respuestas scratch/respuestas.tsv --simular
#
# <rama-o-worktree>: ruta del worktree, nombre bajo .worktrees/, o nombre de la rama (se busca su worktree).
# Archivo de respuestas (TSV, una línea por hilo; vacías y "#..." se ignoran):
#   <id_comentario><TAB><archivo_respuesta.md>        → 👍 + respuesta + resolver
#   -<id_comentario><TAB><archivo_respuesta.md>       → igual que sin guion: siempre 👍 (el responsable, 2026-10-13); el porqué va en la respuesta
# El id es el databaseId del comentario de Codex que abre el hilo (`gh api repos/<o>/<r>/pulls/<n>/comments`).
# Rutas relativas de las respuestas: respecto de la carpeta del TSV. Cada respuesta, UTF-8 sin BOM; el script
# no escribe texto propio, solo publica el del archivo (`-F body=@archivo`).
# --simular: hace las lecturas (git, gh) y muestra cada escritura sin ejecutarla.
# Sale 3 con hilos abiertos, 4 con un @codex review pendiente y 5 en el techo de 8 rondas (registrar_ronda.py).
set -euo pipefail

uso() { sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//'; }
[[ ${1:-} == -h || ${1:-} == --help ]] && { uso; exit 0; }

RAIZ="$(cd "$(dirname "$0")/../.." && pwd)"
SIMULAR=0; RESPUESTAS=""; pos=()
while (($#)); do
  case $1 in
    --simular) SIMULAR=1 ;;
    --respuestas) RESPUESTAS=${2:?--respuestas requiere un archivo}; shift ;;
    -h|--help) uso; exit 0 ;;
    -*) echo "Opción desconocida: $1" >&2; exit 2 ;;
    *) pos+=("$1") ;;
  esac
  shift
done
((${#pos[@]} == 3)) || { uso >&2; exit 2; }
REPO=${pos[0]}; PR=${pos[1]}; OBJ=${pos[2]}
[[ $PR =~ ^[0-9]+$ ]] || { echo "PR inválido: $PR" >&2; exit 2; }

paso() { echo "[$(date -u +%H:%M:%SZ)] $*"; }
falla() { echo "ERROR: $*" >&2; exit 1; }
escribir() {  # ejecuta o, en simulación, solo muestra
  if ((SIMULAR)); then echo "  [simular] $*"; else "$@"; fi
}

# --- Worktree y rama ---------------------------------------------------------------------------------------
if [[ -d $OBJ ]]; then WT=$(cd "$OBJ" && pwd)
elif [[ -d $RAIZ/.worktrees/$OBJ ]]; then WT=$RAIZ/.worktrees/$OBJ
else
  [[ -d $RAIZ/$REPO ]] || falla "no existe el repo $RAIZ/$REPO"
  WT=$(git -C "$RAIZ/$REPO" worktree list --porcelain | awk -v b="branch refs/heads/$OBJ" '
    /^worktree /{w=substr($0,10)} $0==b{print w; exit}')
  [[ -n $WT ]] || falla "la rama $OBJ no tiene worktree; pasá la ruta del worktree"
fi
RAMA=$(git -C "$WT" branch --show-current)
[[ -n $RAMA ]] || falla "$WT está en HEAD separado"
[[ $RAMA != develop && $RAMA != main && $RAMA != qa ]] || falla "la rama es $RAMA: no se sube desde acá"

ORIGEN=$(git -C "$WT" remote get-url origin)
OR=$(sed -E 's#^.*github\.com[:/]##; s#\.git$##' <<<"$ORIGEN")
[[ ${OR#*/} == "$REPO" ]] || falla "el origin del worktree es $OR, no */$REPO"
DUENO=${OR%%/*}; NOMBRE=${OR#*/}
paso "PR $OR#$PR, rama $RAMA, worktree $WT$( ((SIMULAR)) && echo ' (SIMULACIÓN)')"

[[ -z $(git -C "$WT" status --porcelain) ]] || falla "$WT tiene cambios sin commitear"

datos=$(gh pr view "$PR" -R "$OR" --json headRefName,state,baseRefName \
  --jq '[.headRefName,.state,.baseRefName]|@tsv') || falla "no se pudo leer el PR #$PR"
IFS=$'\t' read -r P_RAMA P_ESTADO P_BASE <<<"$datos"
[[ $P_RAMA == "$RAMA" ]] || falla "el PR #$PR es de la rama $P_RAMA, no de $RAMA"
[[ $P_ESTADO == OPEN ]] || falla "el PR #$PR está $P_ESTADO"
[[ $P_BASE == develop ]] || echo "AVISO: el PR #$PR apunta a $P_BASE, no a develop"

# --- Mapa de hilos: databaseId del primer comentario → id del hilo ------------------------------------------
Q_HILOS='query($owner:String!,$name:String!,$n:Int!){repository(owner:$owner,name:$name){pullRequest(number:$n){
  reviewThreads(first:100){pageInfo{hasNextPage} nodes{id isResolved comments(first:1){nodes{databaseId author{login}}}}}}}}'
leer_hilos() {  # → databaseId<TAB>threadId<TAB>isResolved<TAB>autor
  gh api graphql -f query="$Q_HILOS" -f owner="$DUENO" -f name="$NOMBRE" -F n="$PR" \
    --jq '.data.repository.pullRequest.reviewThreads |
      (if .pageInfo.hasNextPage then "AVISO\tmás de 100 hilos: solo se leen 100\t\t" else empty end),
      (.nodes[] | "\(.comments.nodes[0].databaseId)\t\(.id)\t\(.isResolved)\t\(.comments.nodes[0].author.login)")'
}
HILOS=$(leer_hilos)
grep -q '^AVISO' <<<"$HILOS" && grep '^AVISO' <<<"$HILOS" | cut -f2
HILOS=$(grep -v '^AVISO' <<<"$HILOS" || :)

# --- Validación de respuestas (todo antes de escribir) -----------------------------------------------------
lineas=()   # signo<TAB>id<TAB>archivo<TAB>threadId<TAB>resuelto
if [[ -n $RESPUESTAS ]]; then
  [[ -f $RESPUESTAS ]] || falla "no existe $RESPUESTAS"
  BASE_R=$(cd "$(dirname "$RESPUESTAS")" && pwd)
  while IFS=$'\t' read -r id archivo _ || [[ -n ${id:-} ]]; do
    id=${id%$'\r'}; archivo=${archivo%$'\r'}
    [[ -z ${id// } || $id == \#* ]] && continue
    signo=+1; id=${id#-}  # siempre 👍, también en lo que no aplica (el responsable, 2026-10-13)
    [[ $id =~ ^[0-9]+$ ]] || falla "id inválido en $RESPUESTAS: '$id'"
    [[ -n $archivo ]] || falla "falta el archivo de respuesta del comentario $id"
    [[ $archivo == /* || $archivo =~ ^[A-Za-z]: ]] || archivo=$BASE_R/$archivo
    [[ -s $archivo ]] || falla "respuesta vacía o inexistente: $archivo"
    # gh.exe es nativo de Windows: `body=@/tmp/...` no se traduce solo, se le pasa la ruta mixta (C:/...).
    command -v cygpath >/dev/null && archivo=$(cygpath -m "$archivo")
    [[ $(head -c3 "$archivo" | od -An -tx1 | tr -d ' \n') != efbbbf ]] || falla "$archivo tiene BOM: guardalo UTF-8 sin BOM"
    iconv -f UTF-8 -t UTF-8 "$archivo" >/dev/null 2>&1 || falla "$archivo no es UTF-8 válido"
    fila=$(awk -F'\t' -v i="$id" '$1==i' <<<"$HILOS")
    [[ -n $fila ]] || falla "el comentario $id no abre ningún hilo del PR #$PR (¿es una respuesta y no el primero?)"
    IFS=$'\t' read -r _ hilo resuelto _ <<<"$fila"
    lineas+=("$signo"$'\t'"$id"$'\t'"$archivo"$'\t'"$hilo"$'\t'"$resuelto")
  done < "$RESPUESTAS"
  paso "respuestas validadas: ${#lineas[@]}"
fi

# --- 1. Push ------------------------------------------------------------------------------------------------
# Siempre explícito: las ramas nacen con --no-track y un `git push` pelado puede apuntar a develop.
if git -C "$WT" rev-parse --abbrev-ref '@{u}' >/dev/null 2>&1; then
  pendientes=$(git -C "$WT" rev-list --count '@{u}..HEAD')
  paso "push: $pendientes commit(s) por subir"
  ((pendientes == 0)) || escribir git -C "$WT" push origin "$RAMA"
else
  paso "push: primera vez (-u)"
  escribir git -C "$WT" push -u origin "$RAMA"
fi
paso "HEAD $(git -C "$WT" rev-parse --short HEAD)"

# --- 2. Hilos -----------------------------------------------------------------------------------------------
Q_RESOLVER='mutation($id:ID!){resolveReviewThread(input:{threadId:$id}){thread{isResolved}}}'
YO=$(gh api user --jq .login)
simulados=""
for l in "${lineas[@]}"; do
  IFS=$'\t' read -r signo id archivo hilo resuelto <<<"$l"
  if [[ $resuelto == true ]]; then paso "hilo $id: ya resuelto, se salta"; continue; fi
  emoji=👍; [[ $signo == -1 ]] && emoji=👎
  paso "hilo $id: $emoji"
  escribir gh api -X POST "repos/$OR/pulls/comments/$id/reactions" -f content="$signo" --silent
  ya=$(gh api "repos/$OR/pulls/$PR/comments" --paginate \
    --jq "[.[] | select(.in_reply_to_id == $id and .user.login == \"$YO\")] | length" | awk '{s+=$1} END{print s+0}')
  if ((ya > 0)); then
    paso "hilo $id: ya tiene $ya respuesta(s) tuya(s); no se repite"
  else
    paso "hilo $id: respuesta desde $(basename "$archivo")"
    escribir gh api -X POST "repos/$OR/pulls/$PR/comments/$id/replies" -F body=@"$archivo" --silent
  fi
  paso "hilo $id: resolver"
  escribir gh api graphql -f query="$Q_RESOLVER" -f id="$hilo" --silent
  simulados+=" $id "
done

# --- 3. Hilos abiertos --------------------------------------------------------------------------------------
abiertos=$(leer_hilos | grep -v '^AVISO' | awk -F'\t' '$3=="false"' || :)
if ((SIMULAR)); then  # en simulación, los que se iban a resolver cuentan como resueltos
  abiertos=$(awk -F'\t' -v s="$simulados" 'index(s, " " $1 " ")==0' <<<"$abiertos" || :)
fi
n_abiertos=$(grep -c . <<<"$abiertos" || :)
if ((n_abiertos > 0)); then
  paso "quedan $n_abiertos hilo(s) abierto(s): NO se dispara @codex review"
  awk -F'\t' '{print "  - comentario " $1 " (" $4 ")"}' <<<"$abiertos"
  exit 3
fi
paso "0 hilos abiertos"

# Cada comentario de Codex (aunque su hilo esté resuelto) lleva respuesta nuestra y nuestro 👍 (el responsable, 2026-10-13).
if ! ((SIMULAR)); then
  sin_atender=$(PYTHONIOENCODING=utf-8 python "$(dirname "$0")/supercodex-atendidos.py" "$DUENO/$NOMBRE" "$PR" "$YO") || falla "no se pudo auditar los comentarios de Codex"
  if [[ -n $sin_atender ]]; then
    paso "comentarios de Codex sin atender: NO se dispara @codex review"
    sed 's/^/  - comentario /' <<<"$sin_atender"
    exit 3
  fi
  paso "todos los comentarios de Codex con respuesta y 👍"
fi

# Un solo @codex review por vez (el responsable, 2026-10-20): dos en el mismo minuto se juntan en una ronda.
# Si el último pedido no tiene todavía respuesta del bot, no se dispara otro, salvo que lleve más de 15 min colgado.
ultimo=$(gh api "repos/$OR/issues/$PR/comments" --paginate --jq '.[] | select((.body | gsub("[[:space:]]"; "")) == "@codexreview") | .created_at' | tail -1)
if [[ -n $ultimo ]]; then
  respuesta=$(gh api "repos/$OR/issues/$PR/comments" --paginate \
    --jq ".[] | select((.user.login | test(\"codex\")) and .created_at > \"$ultimo\") | .created_at" | head -1)
  edad=$(( $(date -u +%s) - $(date -u -d "$ultimo" +%s) ))
  if [[ -z $respuesta ]] && ((edad < 900)); then
    paso "ya hay un @codex review sin respuesta del bot (pedido $ultimo, hace $((edad / 60)) min): NO se dispara otro"
    exit 4
  fi
fi

# Techo de 8 rondas sin 2 limpias seguidas (retro 2026-10-27): cuenta las filas de rondas-codex.tsv con este #PR.
if ! python "$RAIZ/.claude/tools/supercodex/registrar_ronda.py" --tope "$REPO" "#$PR"; then
  paso "techo de rondas alcanzado: NO se dispara @codex review"
  exit 5
fi

# --- 4. Disparo ---------------------------------------------------------------------------------------------
T=$(date -u +%FT%TZ)
if ((SIMULAR)); then
  echo "  [simular] gh pr comment $PR -R $OR --body '@codex review'"
  paso "T (simulado) = $T"
else
  url=$(gh pr comment "$PR" -R "$OR" --body '@codex review')
  cid=${url##*issuecomment-}
  [[ $cid =~ ^[0-9]+$ ]] && T=$(gh api "repos/$OR/issues/comments/$cid" --jq .created_at 2>/dev/null || echo "$T")
  paso "@codex review disparado: $url"
  paso "T = $T"
fi
