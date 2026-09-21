#!/bin/sh
# Instala hooks de AcmeOrg. Los worktrees comparten la config del repo:
# quedan cubiertos por la ruta absoluta de hooks de cada repo hijo.
# Uso: sh scripts/instalar-hooks.sh [--forzar]
set -u
FORZAR=0
case "${1:-}" in
    "") ;;
    --forzar) FORZAR=1 ;;
    *) echo "Uso: $0 [--forzar]" >&2; exit 1 ;;
esac
[ "$#" -le 1 ] || { echo "Uso: $0 [--forzar]" >&2; exit 1; }
RAIZ=$(cd "$(dirname "$0")/.." && pwd -P) || exit 1
HOOKS_HIJOS="$RAIZ/scripts/hooks-repos"
if command -v cygpath >/dev/null 2>&1; then
    HOOKS_HIJOS=$(cygpath -am "$HOOKS_HIJOS") || exit 1
fi
REPOS=". api-core web-app api-contracts api-people api-auth api-delivery"
ESTADO=0
for REPO in $REPOS; do
    CARPETA="$RAIZ/$REPO"
    [ -e "$CARPETA/.git" ] || continue
    if ! git -C "$CARPETA" rev-parse --git-dir >/dev/null 2>&1; then
        echo "AVISO: $REPO no es un repo accesible; se omite." >&2
        continue
    fi
    DESTINO="$HOOKS_HIJOS"
    [ "$REPO" != . ] || DESTINO="scripts/hooks"
    ACTUAL=$(git -C "$CARPETA" config --get core.hooksPath 2>/dev/null) || ACTUAL=""
    if [ "$FORZAR" -eq 0 ]; then
        if [ -n "$ACTUAL" ] && [ "$ACTUAL" != "$DESTINO" ]; then
            echo "AVISO: $REPO tiene otro core.hooksPath ($ACTUAL); se conserva. Usa --forzar para reemplazarlo." >&2
            continue
        fi
        # Ya instalado: .git/hooks ya estaba ignorado, no hay nada nuevo que advertir
        # (la raíz tiene un .git/hooks/pre-commit viejo desde antes de versionarlo).
        [ "$ACTUAL" = "$DESTINO" ] && continue
        COMUN=$(git -C "$CARPETA" rev-parse --git-common-dir) || { ESTADO=1; continue; }
        case "$COMUN" in
            /*|[A-Za-z]:/*) ;;
            *) COMUN="$CARPETA/$COMUN" ;;
        esac
        CON_HOOKS=0
        for HOOK in "$COMUN"/hooks/* "$COMUN"/hooks/.[!.]* "$COMUN"/hooks/..?*; do
            [ -f "$HOOK" ] || [ -L "$HOOK" ] || continue
            case "$HOOK" in *.sample) continue ;; esac
            CON_HOOKS=1
            break
        done
        if [ "$CON_HOOKS" -eq 1 ]; then
            echo "AVISO: $REPO tiene hooks propios en .git/hooks; se conservan. Usa --forzar para cambiar hooksPath." >&2
            continue
        fi
    fi
    git -C "$CARPETA" config core.hooksPath "$DESTINO" || ESTADO=1
done

printf '\n%-20s | %s\n' 'Repo' 'hooksPath'
for REPO in $REPOS; do
    [ -e "$RAIZ/$REPO/.git" ] || continue
    ACTUAL=$(git -C "$RAIZ/$REPO" config --get core.hooksPath 2>/dev/null) || ACTUAL="(predeterminado: .git/hooks)"
    printf '%-20s | %s\n' "$REPO" "$ACTUAL"
done
exit "$ESTADO"
