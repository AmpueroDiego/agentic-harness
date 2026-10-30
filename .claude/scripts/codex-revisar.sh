#!/usr/bin/env bash
# Revisión local de Codex con veredicto JSON validado (reemplaza `codex exec ... | grep Result`).
#   codex-revisar.sh <raiz-worktree> <rango-git> <salida.json> [--rechazados <archivo.md>] [--foco <texto>]
# Salida: 0 PASS · 1 FINDINGS (una línea por hallazgo) · 2 SIN VEREDICTO · 3 sin cuota · 4 COLGADO.
# Un JSON faltante, vacío o fuera del schema nunca cuenta como PASS.
# Variables: CODEX_BIN (para tests), CODEX_MODEL_REVISION, CODEX_INACTIVIDAD_MIN (5) o CODEX_INACTIVIDAD_SEG, CODEX_MARCADOR.
set -uo pipefail
AQUI=$(cd "$(dirname "$0")" && pwd)
SCHEMA=$AQUI/codex-veredicto.schema.json
MARCADOR=${CODEX_MARCADOR:-$AQUI/../tools/codex-sin-cuota.until}
CODEX_BIN=${CODEX_BIN:-codex}

raiz=${1:?raiz del worktree}; rango=${2:?rango git, p. ej. abc123..HEAD}; salida=${3:?salida.json}; shift 3
rechazados=""; foco=""
while (($#)); do
  case $1 in
    --rechazados) rechazados=${2:?archivo}; shift 2 ;;
    --foco) foco=${2:?texto}; shift 2 ;;
    *) echo "argumento desconocido: $1" >&2; exit 64 ;;
  esac
done
raiz=$(cd "$raiz" && pwd) || exit 64
[[ -z $rechazados || -f $rechazados ]] || { echo "no existe $rechazados" >&2; exit 64; }

# Marcador de cuota vigente: ni se llama a Codex, así no se quema el intento.
if [[ -f $MARCADOR ]]; then
  read -r hasta _ < "$MARCADOR"
  if [[ $hasta =~ ^[0-9]+$ ]] && (( hasta > $(date +%s) )); then
    echo "SIN CUOTA: marcador vigente hasta $(date -d "@$hasta" +%H:%M) ($MARCADOR)"; exit 3
  fi
fi

base=${salida%.json}; LOG=$base.log; PROMPT=$base.prompt.md
mkdir -p "$(dirname "$salida")"; rm -f "$salida"; : > "$LOG"
# A..B se pasa a A...B (desde el ancestro común): si la base avanzó, el diff de dos puntos trae sus cambios al revés.
[[ $rango == *..* && $rango != *...* ]] && rango=${rango/../...}
diff_txt=$(git -C "$raiz" diff "$rango") || { echo "git diff $rango falló en $raiz" >&2; exit 64; }

# El prompt va por stdin: Windows corta los argumentos largos. El diff va adentro para que Codex no tenga que ejecutar nada.
{
  echo "Revisá el cambio de este repositorio. Raíz (ruta absoluta): $(cygpath -m "$raiz")"
  echo "Rango: $rango (equivale a \`git -C $(cygpath -m "$raiz") diff $rango\`; el diff completo va abajo)."
  echo
  echo "Reglas:"
  echo "- Solo lectura: no guardes, crees ni modifiques archivos."
  echo "- Solo bugs reales con archivo:línea y escenario de falla. Nada de estilo, nombres ni gustos."
  echo "- bloquea=true solo si es P1, o P2 que afecta datos o el flujo del agente (perder o duplicar un registro, datos de otro cliente, no poder abrir/guardar/cerrar). bloquea=false para accesibilidad, foco, estados de carga, casos borde de UI y estilo."
  echo "- Sin hallazgos: veredicto PASS y hallazgos []. Con alguno: FINDINGS."
  [[ -n $foco ]] && { echo; echo "Foco: $foco"; }
  if [[ -n $rechazados ]]; then
    echo; echo "## Ya evaluados — no los repitas salvo que el código nuevo los reabra"
    cat "$rechazados"
  fi
  echo; echo "## Diff"; echo '```diff'; printf '%s\n' "$diff_txt"; echo '```'
} > "$PROMPT"

matar_arbol() {  # taskkill /T llega a los nietos nativos; los de MSYS (bash, sleep) no cuelgan del árbol de Windows: se buscan por /proc.
  local todos=("$1") i=0 p hijo wp
  while (( i < ${#todos[@]} )); do
    p=${todos[i]}; i=$((i + 1))
    for hijo in /proc/[0-9]*; do [[ $(cat "$hijo/ppid" 2>/dev/null) == "$p" ]] && todos+=("${hijo#/proc/}"); done
  done
  wp=$(cat "/proc/$1/winpid" 2>/dev/null)
  [[ -n $wp ]] && taskkill //PID "$wp" //T //F >/dev/null 2>&1
  kill -9 "${todos[@]}" 2>/dev/null
}

inact=${CODEX_INACTIVIDAD_SEG:-$(( ${CODEX_INACTIVIDAD_MIN:-5} * 60 ))}
paso=$(( inact / 2 )); (( paso < 1 )) && paso=1; (( paso > 5 )) && paso=5

"$CODEX_BIN" exec -C "$(cygpath -m "$raiz")" --ephemeral -s read-only -m "${CODEX_MODEL_REVISION:-gpt-6.1-sol}" \
  -c model_provider=openai -c service_tier="fast" -c windows.sandbox=\"unelevated\" \
  --output-schema "$(cygpath -m "$SCHEMA")" -o "$(cygpath -m "$salida")" - < "$PROMPT" > "$LOG" 2>&1 &
pid=$!

# Vigilante: si el log no crece en $inact segundos, Codex quedó colgado (pasó con stdin abierto y con el sandbox).
tam=-1; quieto=0
while kill -0 "$pid" 2>/dev/null; do
  sleep "$paso"
  t=$(stat -c %s "$LOG" 2>/dev/null || echo 0)
  if [[ $t == "$tam" ]]; then quieto=$((quieto + paso)); else tam=$t; quieto=0; fi
  if (( quieto >= inact )) && kill -0 "$pid" 2>/dev/null; then
    matar_arbol "$pid"; wait "$pid" 2>/dev/null
    echo "COLGADO: el log no creció en ${inact}s ($LOG)"; exit 4
  fi
done
wait "$pid"; rc=$?

veredicto=$(python - "$(cygpath -m "$salida")" <<'PY'
import json, sys
# Validación a mano del schema: sin dependencias y estricta (claves de más o de menos = inválido).
def malo(msg): print("INVALIDO " + msg); sys.exit(0)
try:
    txt = open(sys.argv[1], encoding="utf-8").read().strip()
except OSError: malo("sin archivo")
if not txt: malo("vacio")
try: d = json.loads(txt)
except ValueError as e: malo("no es JSON: %s" % e)
if not isinstance(d, dict) or set(d) != {"veredicto", "hallazgos"}: malo("claves de la raiz")
if d["veredicto"] not in ("PASS", "FINDINGS") or not isinstance(d["hallazgos"], list): malo("veredicto/hallazgos")
claves = {"prioridad", "archivo", "linea", "resumen", "evidencia", "arreglo", "bloquea"}
for h in d["hallazgos"]:
    if not isinstance(h, dict) or set(h) != claves: malo("claves de un hallazgo")
    if h["prioridad"] not in ("P1", "P2", "P3"): malo("prioridad")
    if not all(isinstance(h[k], str) for k in ("archivo", "resumen", "evidencia", "arreglo")): malo("tipos de texto")
    if h["linea"] is not None and (type(h["linea"]) is not int): malo("linea")
    if type(h["bloquea"]) is not bool: malo("bloquea")
if d["veredicto"] == "FINDINGS" and not d["hallazgos"]: malo("FINDINGS sin hallazgos")
# Un PASS con hallazgos se trata como FINDINGS: ante la duda, nunca PASS.
if not d["hallazgos"]: print("PASS"); sys.exit(0)
print("FINDINGS")
for h in d["hallazgos"]:
    lugar = h["archivo"] + (":%d" % h["linea"] if h["linea"] is not None else "")
    print("%s bloquea=%s %s %s" % (h["prioridad"], "si" if h["bloquea"] else "no", lugar, " ".join(h["resumen"].split())))
PY
)

veredicto=${veredicto//$'\r'/}  # python en Windows imprime CRLF
case ${veredicto%%$'\n'*} in
  PASS) echo "PASS"; exit 0 ;;
  FINDINGS) printf '%s\n' "$veredicto"; exit 1 ;;
esac
# Sin JSON válido: recién ahí se mira si fue la cuota (así un "429" dentro del diff no la simula).
if grep -qiE 'usage limit|rate limit|too many requests|\b429\b|quota exceeded|exceeded your' "$LOG"; then
  hasta=$(( $(date +%s) + 3600 ))
  echo "$hasta $(date -d "@$hasta" +%H:%M)" > "$MARCADOR"
  echo "SIN CUOTA: marcador hasta $(date -d "@$hasta" +%H:%M) ($MARCADOR)"; exit 3
fi
echo "SIN VEREDICTO: ${veredicto#INVALIDO } (codex rc=$rc, log $LOG)"; exit 2
