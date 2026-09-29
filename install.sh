#!/usr/bin/env bash
# install.sh — instala/configura el harness multi-agente en un proyecto destino.
#
# Uso:
#   ./install.sh [--target DIR] [--ini ARCHIVO] [--dry-run] [--non-interactive]
#                [--force] [--skip-hook]
#
#   --target DIR        Carpeta del proyecto donde se instala. Default: "."
#   --ini ARCHIVO        harness.ini ya completado (salta el asistente).
#   --dry-run             No escribe nada; solo muestra qué haría.
#   --non-interactive  No hace preguntas: usa harness.ini.example tal cual
#                          (o --ini si se dio) y valores por defecto.
#   --force                Sobrescribe archivos existentes sin backup.
#   --skip-hook            No toca core.hooksPath del repo destino.
#
# Idempotente: correr dos veces no debería producir un estado distinto de
# correr una. No destructivo: un archivo existente se respalda a .bak antes
# de reemplazarlo, salvo --force.
set -eu

SOURCE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"
TARGET="."
INI_ORIGEN=""
DRY_RUN=0
NON_INTERACTIVE=0
FORCE=0
SKIP_HOOK=0

while [ "$#" -gt 0 ]; do
    case "$1" in
        --target) TARGET="$2"; shift 2 ;;
        --ini) INI_ORIGEN="$2"; shift 2 ;;
        --dry-run) DRY_RUN=1; shift ;;
        --non-interactive) NON_INTERACTIVE=1; shift ;;
        --force) FORCE=1; shift ;;
        --skip-hook) SKIP_HOOK=1; shift ;;
        -h|--help) sed -n '2,17p' "$0"; exit 0 ;;
        *) echo "Argumento desconocido: $1" >&2; exit 1 ;;
    esac
done

mkdir -p "$TARGET" 2>/dev/null || true
TARGET="$(cd "$TARGET" && pwd -P)"

log()  { printf '%s\n' "$*"; }
step() { printf '\n== %s ==\n' "$*"; }
run()  { if [ "$DRY_RUN" -eq 1 ]; then printf '[dry-run] %s\n' "$*"; else eval "$@"; fi }

step "1/6 — Detectando herramientas"
detectar() {
    if command -v "$1" >/dev/null 2>&1; then
        printf '  [ok]      %-10s %s\n' "$1" "$("$1" "${2:---version}" 2>/dev/null | head -n1)"
        return 0
    else
        printf '  [omitido] %-10s no encontrado en PATH\n' "$1"
        return 1
    fi
}
detectar git || { echo "git es obligatorio. Instálalo y volvé a correr install.sh." >&2; exit 1; }
detectar gh || true
detectar node || true
detectar dotnet || true
detectar python3 --version || detectar python --version || true
detectar claude || true
detectar codex || true
detectar agy || true

step "2/6 — Resolviendo harness.ini"
INI_DESTINO="$TARGET/harness.ini"

pedir() {
    # pedir "pregunta" "default" -> stdout el valor elegido
    pregunta="$1"; def="$2"
    if [ "$NON_INTERACTIVE" -eq 1 ]; then printf '%s' "$def"; return; fi
    printf '%s [%s]: ' "$pregunta" "$def" >&2
    IFS= read -r respuesta || respuesta=""
    printf '%s' "${respuesta:-$def}"
}

if [ -n "$INI_ORIGEN" ]; then
    [ -f "$INI_ORIGEN" ] || { echo "No existe $INI_ORIGEN" >&2; exit 1; }
    run "cp \"$INI_ORIGEN\" \"$INI_DESTINO\""
elif [ -f "$INI_DESTINO" ]; then
    log "  Ya existe $INI_DESTINO — se reutiliza (borralo si querés repetir el asistente)."
elif [ "$NON_INTERACTIVE" -eq 1 ]; then
    log "  --non-interactive sin --ini: copiando harness.ini.example tal cual."
    run "cp \"$SOURCE/harness.ini.example\" \"$INI_DESTINO\""
else
    log "  Sin harness.ini — asistente interactivo (Enter para aceptar el default)."
    NOMBRE=$(pedir "Nombre del proyecto" "MiProyecto")
    BASE=$(pedir "Rama base (git)" "develop")
    MAIN=$(pedir "Rama de producción" "main")
    TRACKER=$(pedir "Tracker de tareas (none/trello/azuredevops/github-issues)" "none")
    if [ "$DRY_RUN" -eq 1 ]; then
        log "  [dry-run] generaría $INI_DESTINO con project.name=$NOMBRE git.base_branch=$BASE git.main_branch=$MAIN tracker.provider=$TRACKER"
    else
        cp "$SOURCE/harness.ini.example" "$INI_DESTINO"
        sed -i.bak \
            -e "s/^name = MiProyecto/name = $NOMBRE/" \
            -e "s/^base_branch = develop/base_branch = $BASE/" \
            -e "s/^main_branch = main/main_branch = $MAIN/" \
            -e "s/^provider = none/provider = $TRACKER/" \
            "$INI_DESTINO" 2>/dev/null || true
        rm -f "$INI_DESTINO.bak"
    fi
fi

# --- parser mínimo de INI: ini_get seccion clave default -------------------
ini_get() {
    seccion="$1"; clave="$2"; def="${3:-}"
    [ -f "$INI_DESTINO" ] || { printf '%s' "$def"; return; }
    valor=$(awk -v s="[$seccion]" -v k="$clave" '
        $0==s {in_s=1; next}
        /^\[/ {in_s=0}
        in_s && $0 ~ "^[ \t]*"k"[ \t]*=" {
            sub("^[^=]*=[ \t]*", ""); sub(/[ \t]+$/, ""); print; found=1
        }
        END { if (!found) exit 1 }
    ' "$INI_DESTINO" 2>/dev/null) || valor=""
    printf '%s' "${valor:-$def}"
}
ini_sections() {
    # lista secciones que empiezan con un prefijo dado, ej. "repo:"
    [ -f "$INI_DESTINO" ] || return 0
    grep -o "^\[$1[^]]*\]" "$INI_DESTINO" 2>/dev/null | tr -d '[]' || true
}

PROYECTO=$(ini_get project name "MiProyecto")
BASE_BRANCH=$(ini_get git base_branch "develop")
TRACKER_PROVIDER=$(ini_get tracker provider "none")
CODEX_ON=$(ini_get engines codex_enabled "false")
ANTIGRAVITY_ON=$(ini_get engines antigravity_enabled "false")
DB_MCP=$(ini_get databases enabled_mcp_servers "")
VAULT_ON=$(ini_get vault enabled "false")

# Directorio de staging: los .md que llevan placeholders se sustituyen ACA,
# antes de comparar/copiar al destino. Si se sustituyera despues de copiar,
# cada corrida vería su propio resultado anterior (ya sustituido) como
# "distinto" del original con AcmeOrg y generaría un .bak espurio en cada
# corrida — rompiendo la idempotencia real, aunque el contenido final fuera
# el mismo.
STAGE=$(mktemp -d 2>/dev/null || mktemp -d -t harness-install)
trap 'rm -rf "$STAGE"' EXIT

sustituir_placeholders() {
    # sustituir_placeholders <archivo-en-stage>
    f="$1"
    sed -i.tmp "s/AcmeOrg/$PROYECTO/g" "$f" 2>/dev/null && rm -f "$f.tmp"
    if [ "$BASE_BRANCH" != "develop" ]; then
        sed -i.tmp "s/\`develop\`/\`$BASE_BRANCH\`/g" "$f" 2>/dev/null && rm -f "$f.tmp"
    fi
}

mkdir -p "$STAGE/.claude/agents" "$STAGE/.claude/commands"
for f in "$SOURCE"/.claude/agents/*.md; do
    [ -f "$f" ] || continue
    cp "$f" "$STAGE/.claude/agents/$(basename "$f")"
    sustituir_placeholders "$STAGE/.claude/agents/$(basename "$f")"
done
for f in "$SOURCE"/.claude/commands/*.md; do
    [ -f "$f" ] || continue
    cp "$f" "$STAGE/.claude/commands/$(basename "$f")"
    sustituir_placeholders "$STAGE/.claude/commands/$(basename "$f")"
done
cp "$SOURCE/CLAUDE.md" "$STAGE/CLAUDE.md"; sustituir_placeholders "$STAGE/CLAUDE.md"
cp "$SOURCE/AGENTS.md" "$STAGE/AGENTS.md"; sustituir_placeholders "$STAGE/AGENTS.md"

step "3/6 — Copiando agentes, comandos, hooks y scripts (con placeholders ya resueltos)"
copiar_arbol() {
    origen="$1"; destino="$2"
    [ -d "$origen" ] || return 0
    [ "$DRY_RUN" -eq 1 ] || mkdir -p "$destino" 2>/dev/null || true
    find "$origen" -type f | while IFS= read -r f; do
        rel="${f#"$origen"/}"
        d="$destino/$rel"
        if [ -f "$d" ] && [ "$FORCE" -ne 1 ] && ! cmp -s "$f" "$d" 2>/dev/null; then
            run "cp \"$d\" \"$d.bak\""
            log "    (respaldado $d -> $d.bak, contenido distinto)"
        fi
        run "mkdir -p \"$(dirname "$d")\""
        run "cp \"$f\" \"$d\""
    done
}
copiar_arbol "$STAGE/.claude/agents"    "$TARGET/.claude/agents"
copiar_arbol "$STAGE/.claude/commands"  "$TARGET/.claude/commands"
copiar_arbol "$SOURCE/.claude/hooks"    "$TARGET/.claude/hooks"
copiar_arbol "$SOURCE/.claude/scripts"  "$TARGET/.claude/scripts"
copiar_arbol "$SOURCE/.claude/tools"    "$TARGET/.claude/tools"
copiar_arbol "$SOURCE/profiles"         "$TARGET/.claude/profiles"

for f in CLAUDE.md AGENTS.md; do
    if [ -f "$TARGET/$f" ] && [ "$FORCE" -ne 1 ] && ! cmp -s "$STAGE/$f" "$TARGET/$f" 2>/dev/null; then
        run "cp \"$TARGET/$f\" \"$TARGET/$f.bak\""
        log "    (respaldado $TARGET/$f -> $f.bak, contenido distinto)"
    fi
    run "cp \"$STAGE/$f\" \"$TARGET/$f\""
done
if [ -f "$SOURCE/.claude/settings.json" ] && [ ! -f "$TARGET/.claude/settings.json" ]; then
    run "cp \"$SOURCE/.claude/settings.json\" \"$TARGET/.claude/settings.json\""
fi
log "  Placeholders resueltos: AcmeOrg -> $PROYECTO$( [ "$BASE_BRANCH" != "develop" ] && echo ", \`develop\` -> \`$BASE_BRANCH\`" )."
log "  Revisá a mano los nombres de repo (api-core, web-app, ...): el instalador no adivina"
log "  los tuyos — editá CLAUDE.md y los agentes con los nombres reales de tus repos."

step "4/6 — (sin uso; ver paso 3 — placeholders y copia van juntos para no romper idempotencia)"

step "5/6 — Hook de git (revisión de secretos antes de cada commit)"
if [ "$SKIP_HOOK" -eq 1 ]; then
    log "  Omitido (--skip-hook)."
elif [ ! -d "$TARGET/.git" ]; then
    log "  $TARGET no es la raíz de un repo git — omitido. Corré 'git init' primero, o instala el hook a mano después."
else
    # Se instala DENTRO de .claude/ (a la misma profundidad que
    # scripts/hooks-repos/ en este repo) porque scripts/hooks-repos/pre-commit
    # ubica el resto del sistema con "dirname/../.." — dos niveles arriba de
    # donde vive el propio script. Si se copiara a un solo nivel de $TARGET,
    # esa cuenta apuntaría fuera del proyecto y el hook no encontraría
    # revisar_secretos.py. Ver .claude/hooks/git-guard.sh para el mismo patrón.
    HOOKS_DIR="$TARGET/.claude/hooks-git"
    run "mkdir -p \"$HOOKS_DIR\""
    run "cp \"$SOURCE/scripts/hooks-repos/pre-commit\" \"$HOOKS_DIR/pre-commit\""
    run "chmod +x \"$HOOKS_DIR/pre-commit\""
    HOOKSPATH_REL=".claude/hooks-git"
    ACTUAL=$(git -C "$TARGET" config --get core.hooksPath 2>/dev/null || echo "")
    if [ -n "$ACTUAL" ] && [ "$ACTUAL" != "$HOOKSPATH_REL" ] && [ "$FORCE" -ne 1 ]; then
        log "  $TARGET ya tiene core.hooksPath=$ACTUAL — se conserva. Usá --force para reemplazarlo."
    else
        run "git -C \"$TARGET\" config core.hooksPath \"$HOOKSPATH_REL\""
        log "  Instalado: core.hooksPath -> $HOOKSPATH_REL (revisar_secretos.py corre antes de cada commit)."
    fi
fi

step "6/6 — doctor: resumen de lo configurado"
estado() { [ "$2" = "true" ] || [ "$2" = "yes" ] && echo "activo" || echo "omitido"; }
cat <<EOF

  Proyecto:            $PROYECTO
  Rama base:            $BASE_BRANCH
  harness.ini:         $INI_DESTINO
  Tracker:              $TRACKER_PROVIDER $( [ "$TRACKER_PROVIDER" = "none" ] && echo "(sin integración — los agentes lo asumen manual)" )
  Codex CLI:             $(estado codex "$CODEX_ON")
  Antigravity CLI:      $(estado antigravity "$ANTIGRAVITY_ON")
  MCP de base de datos: ${DB_MCP:-"(ninguno declarado)"}
  Vault Obsidian:       $(estado vault "$VAULT_ON")
  Hook de secretos:     $([ "$SKIP_HOOK" -eq 1 ] && echo "omitido (--skip-hook)" || echo "ver paso 5/6 arriba")

Próximos pasos:
  1. Editá $INI_DESTINO con tus repos reales bajo [repo:<nombre>].
  2. Completá la sección "Visión de dominio" de $TARGET/CLAUDE.md.
  3. Revisá que los nombres de repo en los agentes (api-core, web-app, ...)
     coincidan con los tuyos — el instalador solo sustituyó el nombre del
     proyecto y la rama base, no los nombres de repo.
  4. harness.ini NO se versiona (ya está en .gitignore si copiaste el de este repo).
EOF
