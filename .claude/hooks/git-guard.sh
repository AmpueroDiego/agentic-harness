#!/usr/bin/env bash
# PreToolUse(Bash) — convierte en bloqueo dos reglas de CLAUDE.md que hasta ahora
# eran solo texto:
#   1. Los PRs van contra `develop`, nunca main/qa/master.
#   2. Ningun appsettings*.json se comitea con un valor real en clave sensible.
# exit 2 = accion bloqueada, stderr vuelve al agente. exit 0 = pasa.
set -u
HOOK_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Resolver python: en Windows `python3` suele ser el stub de la Microsoft Store,
# que existe en PATH pero no ejecuta nada. Se valida que corra de verdad.
PY=""
for C in python3 python py; do
  if command -v "$C" >/dev/null 2>&1 && "$C" -c "pass" >/dev/null 2>&1; then PY="$C"; break; fi
done

RAW=$(cat)
if [ -z "$PY" ]; then
  if echo "$RAW" | grep -qE 'gh[^"]*pr[^"]*create|git[^"]*commit'; then
    echo "BLOQUEADO por git-guard.sh — no hay un python funcional para validar este comando." >&2
    echo "El guard no puede verificar base del PR ni secretos en el stage, y no deja pasar a ciegas." >&2
    exit 2
  fi
  exit 0
fi
CMD=$(printf '%s' "$RAW" | "$PY" -c 'import sys,json
try: print(json.load(sys.stdin).get("tool_input",{}).get("command",""))
except Exception: print("")')
[ -z "$CMD" ] && exit 0

# Repos a inspeccionar. A nivel de usuario este hook corre desde cualquier carpeta,
# asi que no puede haber lista fija: se descubre el repo abierto y, si es un
# contenedor (AcmeOrg), tambien sus repos hijos de primer nivel.
if [ -n "${GIT_GUARD_REPOS:-}" ]; then
  REPOS="$GIT_GUARD_REPOS"
else
  RAIZ="${CLAUDE_PROJECT_DIR:-$PWD}"
  REPOS="$RAIZ"
  for D in "$RAIZ"/*/; do
    [ -e "$D/.git" ] && REPOS="$REPOS $D"
  done
  # Worktrees anidados (2026-09-11): los de /worktree y los nativos de Claude Code
  # no son hijos de primer nivel, y el glob * no entra en carpetas con punto.
  # Sin esto un commit hecho desde un worktree pasaba sin chequeo de secretos.
  for D in "$RAIZ"/.worktrees/*/ "$RAIZ"/.claude/worktrees/*/; do
    [ -e "$D/.git" ] && REPOS="$REPOS $D"
  done
fi

# ---------- Regla 1: base del PR ----------
if echo "$CMD" | grep -qE '\bgh[[:space:]]+pr[[:space:]]+create\b'; then
  TIENE_DEVELOP=$(git -C "${CLAUDE_PROJECT_DIR:-$PWD}" ls-remote --heads origin develop 2>/dev/null | head -1)
  if echo "$CMD" | grep -qE '(--base|-B)[[:space:]=]+"?(main|master|qa)($|[^a-zA-Z0-9_-])'; then
    echo "BLOQUEADO por git-guard.sh - PR contra main/master/qa." >&2
    echo "El flujo es develop -> qa -> main. Usa: --base develop" >&2
    exit 2
  fi
  if ! echo "$CMD" | grep -qE '(--base|-B)[[:space:]=]'; then
    echo "BLOQUEADO por git-guard.sh - 'gh pr create' sin --base." >&2
    if [ -n "$TIENE_DEVELOP" ]; then
      echo "Este repo tiene rama develop y el default de GitHub puede ser main. Pasa --base develop." >&2
    else
      echo "Este repo no tiene rama develop; pasa --base explicito para no depender del default." >&2
    fi
    exit 2
  fi
fi

# ---------- Regla 2: secretos en el stage ----------
# No se parsea el 'cd' del comando: se inspecciona el stage real de cada repo.
if echo "$CMD" | grep -qE '\bgit\b[^|;&]*\bcommit\b'; then
  for R in $REPOS; do
    [ -d "$R/.git" ] || [ -f "$R/.git" ] || continue
    STAGED=$(git -C "$R" diff --cached --name-only 2>/dev/null) || continue
    [ -z "$STAGED" ] && continue

    HIT=$("$PY" "$HOOK_DIR/revisar_secretos.py" --repo "$R")
    if [ $? -ne 0 ]; then
      echo "BLOQUEADO por git-guard.sh — secretos en el stage de '$R':" >&2
      printf '%s\n' "$HIT" >&2
      echo "Deben quedar como \"\" o \"REPLACE_ME\" (CLAUDE.md). El valor real va por user-secrets / App Settings de Azure." >&2
      exit 2
    fi
  done
fi

exit 0
