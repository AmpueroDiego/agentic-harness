#!/usr/bin/env bash
# Corre un agente de .claude/agents/ con cualquier motor, para orquestar igual desde Claude, Codex o Antigravity (30/10).
#   agente.sh <agente> <prompt.md> <salida.md> [raíz-de-trabajo]
# MOTOR=claude|codex|agy elige el motor. Sin MOTOR: Codex (regla «Codex primero»), salvo agentes con herramientas
# MCP (planner, analyst…), que van con Claude porque las bases solo están conectadas ahí.
# El agente es de solo lectura si su `tools:` no tiene Edit ni Write: Codex corre con -s read-only y agy en modo plan.
set -uo pipefail
# Raíz configurable o calculada desde el script.
MAQ=${PROYECTO_RAIZ:-$(git -C "$(dirname "$0")" rev-parse --show-toplevel)}
AGENTE=${1:?agente (nombre de .claude/agents/<agente>.md)}; PROMPT=${2:?prompt.md}; SALIDA=${3:?salida.md}; RAIZ=${4:-$MAQ}
DEF=$MAQ/.claude/agents/$AGENTE.md
[[ -f $DEF ]] || { echo "no existe $DEF" >&2; exit 2; }
[[ -f $PROMPT ]] || { echo "no existe $PROMPT" >&2; exit 2; }

TOOLS=$(sed -n '2,/^---$/p' "$DEF" | sed -n 's/^tools:[[:space:]]*//p')
MOTOR=${MOTOR:-}
[[ -z $MOTOR ]] && { [[ $TOOLS == *mcp__* ]] && MOTOR=claude || MOTOR=codex; }
[[ $TOOLS == *Edit* || $TOOLS == *Write* ]] && ESCRIBE=1 || ESCRIBE=0
mkdir -p "$(dirname "$SALIDA")"

# Codex y agy no conocen los agentes de Claude: el cuerpo del .md va como instrucciones, antes de la tarea.
combinado() {
  { echo "Sos el agente \`$AGENTE\` del sistema multiagente de AcmeOrg. Tus instrucciones (de $DEF):"; echo
    awk 'n >= 2 { print } /^---$/ { n++ }' "$DEF"
    echo; echo "Reglas del proyecto: $MAQ/AGENTS.md (y CLAUDE.md, al que apunta). Trabajás en: $RAIZ"
    echo; echo "## Tarea"; cat "$PROMPT"; } > "$1"
}

case $MOTOR in
  claude)
    IFS=',' read -ra T <<< "$TOOLS"; PERM=(); for t in "${T[@]}"; do t=${t// /}; [[ -n $t ]] && PERM+=("$t"); done
    # --agent solo encuentra .claude/agents/ desde la raíz de AcmeOrg.
    (cd "$MAQ" && timeout 30m claude -p --agent "$AGENTE" --add-dir "$RAIZ" \
       $( ((ESCRIBE)) && echo --permission-mode acceptEdits ) ${PERM:+--allowedTools "${PERM[@]}"} \
       < "$PROMPT" > "$SALIDA" 2> "$SALIDA.err") ;;
  codex)
    combinado "$SALIDA.prompt.md"
    ((ESCRIBE)) && SB=workspace-write || SB=read-only
    # Prompt por stdin: como argumento, uno de más de ~32 KB falla en Windows.
    (cd "$RAIZ" && timeout 30m codex exec -s "$SB" -c service_tier="fast" -c windows.sandbox=\"unelevated\" \
       --output-last-message "$SALIDA" - < "$SALIDA.prompt.md" > "$SALIDA.log" 2>&1) ;;
  agy|antigravity)
    combinado "$SALIDA.prompt.md"
    DIR=$RAIZ; MODO=(--mode accept-edits)
    if ((!ESCRIBE)); then
      # Headless, agy no corre comandos sin permiso. Requiere una regla autoMode.allow del usuario: plan + skip-permissions,
      # solo sobre una copia `git archive` en una carpeta temporal fuera del repo.
      DIR=$(mktemp -d) || exit 2; trap 'rm -rf "$DIR"' EXIT  # la copia es nuestra y desechable
      git -C "$RAIZ" archive HEAD | tar -x -C "$DIR" || { echo "no se pudo copiar $RAIZ" >&2; exit 2; }
      MODO=(--mode plan --dangerously-skip-permissions)
    fi
    # agy no lee stdin en --print: va la ruta del prompt.
    (cd "$DIR" && timeout 30m agy --model "${AGY_MODEL:-gemini-3.8-flash-high}" "${MODO[@]}" \
       --print="Leé completo y seguí al pie de la letra las instrucciones del archivo $(cygpath -m "$SALIDA.prompt.md" 2>/dev/null || echo "$SALIDA.prompt.md")." \
       < /dev/null > "$SALIDA" 2> "$SALIDA.err") ;;
  *) echo "MOTOR desconocido: $MOTOR (claude|codex|agy)" >&2; exit 2 ;;
esac
rc=$?
echo "[$AGENTE] motor $MOTOR, $( ((ESCRIBE)) && echo escribe || echo solo lectura ), rc $rc → $SALIDA" >&2
exit $rc
