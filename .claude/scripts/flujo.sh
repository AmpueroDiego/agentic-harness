#!/usr/bin/env bash
# Tramos fijos de /orquestar como workflow: corren acá y el orquestador solo lee el "## Resumen" final.
# Cada fase deja sus logs en <SALIDA>. .NET (api-core y hermanos) y web-app (package.json).
#
#   flujo.sh plan     <RAIZ> <tarea.md> <SALIDA>                 Nivel 1: ping de Codex + planner headless (Sonnet)
#   flujo.sh tests    <RAIZ> <SALIDA> <etiqueta> "<commit test(...)>" TDD+SDD: tests de aceptación del REQ → deben fallar → commit aparte; fija esos archivos
#   flujo.sh coder    <RAIZ> <SALIDA> <etiqueta> "<commit>" [solo] coder del plan (o solo del tramo "solo") → build → suite (1 reintento) → commit
#   flujo.sh gate     <SALIDA> [--adversary] [--codex] <RAIZ>... suites (reusa las del coder) → QA (+ adversary, + revisión de Codex) en paralelo
#   flujo.sh arreglar <RAIZ> <SALIDA> <prompt.md> [etiqueta]     arreglo sobre árbol sucio con las mismas compuertas (build, tildes, suite), sin commit
#   flujo.sh suite    <RAIZ> <SALIDA>                            suite completa sobre el HEAD ya commiteado (tras un arreglo a mano); el gate la reusa
#   flujo.sh ejecutar <RAIZ> <SALIDA> "<commit>"                 Nivel 1: coder + gate
#   flujo.sh chequear <RAIZ> [SALIDA]                            diagnóstico del ambiente (rama, Docker, Host, Codex con SALIDA) sin lanzar nada
#   flujo.sh integracion <RAIZ> [BASE]                           solo el chequeo de tests de integración de api-core que hace el gate (sale 1 si bloquea)
#
# CODER=agy (o antigravity) delante de coder/arreglar/ejecutar usa Antigravity (gemini-3.8-flash-high, AGY_MODEL lo cambia) en vez de Codex.
# CODER=claude fuerza Claude como coder (lo usa un orquestador que quiere «todo con Claude»; ver AGENTS.md §3).
# El plan va en <SALIDA>/plan.md (lo escribe `plan`, o el orquestador en pipeline completo).
# Con <SALIDA>/<etiqueta>-plan.md, `tests` y `coder` de esa etiqueta usan ese plan en vez de plan.md (24/10: el plan entero metía tramos ajenos en el prompt).
# Dos `coder` en paralelo (api y web) se lanzan con etiquetas distintas; el gate va después, una sola vez.
# El diff que revisa el gate es base..HEAD de cada raíz; la base sale de BASE_<etiqueta>, o de origin/develop.
#
# Motor: Codex siempre primero (coder, QA y adversary), hasta agotarlo. Coder: gpt-6.1-sol fast medium por defecto (el responsable, 2026-10-22: luna obligó a 2-3 vueltas por tarjeta: código minificado, tests borrados, campos inventados); luna solo para lo mecánico con CODEX_MODEL_CODER=gpt-6-luna. QA, adversary y revisión: gpt-6.1-sol (CLI 0.162+). Sin cuota de Codex, el respaldo es
# Claude; DeepSeek solo si Claude pasó el 70 % de su ventana de 5 h (lo escribe uso-claude-statusline.py).
set -uo pipefail
CODER_PEDIDO=${CODER:-}

HARNESS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
# Coder con sol o luna; la revisión con sol (gpt-6.1-luna no lo habilita la cuenta de ChatGPT, probado con la CLI 0.163.0).
[[ ${CODEX_MODEL_CODER:-gpt-6.1-sol} =~ ^(gpt-6\.1-sol|gpt-6-sol|gpt-6-luna)$ ]] || { echo "Coder de Codex solo con gpt-6.1-sol, gpt-6-sol o gpt-6-luna (pedido: $CODEX_MODEL_CODER)" >&2; exit 2; }
[[ ${CODEX_MODEL_REVISION:-gpt-6.1-sol} == gpt-6.1-sol || ${CODEX_MODEL_REVISION:-} == gpt-6-sol ]] || { echo "Revisión de Codex solo con gpt-6.1-sol o gpt-6-sol (pedido: $CODEX_MODEL_REVISION)" >&2; exit 2; }
FASE=${1:?fase: plan | tests | coder | arreglar | gate | suite | ejecutar | chequear}; shift
# Guards de recursos (21/10: 490 nodos de MSBuild huérfanos, 7,8 GB, y 3 corridas pesadas a la vez dejaron 0,1 GB libres).
# 1) Sin reuso de nodos de MSBuild; lo heredan el coder (Codex/agy) y sus builds.
export MSBUILDDISABLENODEREUSE=1 DOTNET_CLI_USE_MSBUILD_SERVER=0
# 5) recursos.tsv (el responsable, 23/10): muestras de la máquina y eventos (esperas, reintentos, colgados) para la sección «Máquina» del run doc.
#    Filas «M»: hora, fase, MB libres, CPU %, procesos dotnet, top 3. Filas «E»: hora, tipo, segundos, detalle. Las lee registrar_corrida.py --recursos.
REC=""; MUESTREO=""
evento() { [[ -n $REC ]] && printf 'E\t%s\t%s\t%s\t%s\n' "$(date +%FT%T)" "$1" "$2" "$3" >> "$REC"; return 0; }
iniciar_muestreo() {  # $1 carpeta de logs
  [[ -d $1 ]] || return 0
  REC="$1/recursos.tsv"
  ( while kill -0 $$ 2>/dev/null; do
      m=$(powershell -NoProfile -File "$HARNESS_ROOT/.claude/scripts/muestra-maquina.ps1" 2>/dev/null | tr -d '\r')
      [[ -n $m ]] && printf 'M\t%s\t%s\t%s\n' "$(date +%FT%T)" "$FASE" "$m" >> "$REC"
      sleep 30
    done ) > /dev/null 2>&1 &
  MUESTREO=$!
}
barrer_nodos_huerfanos() {  # nodos de MSBuild y vitest cuyo padre ya terminó: nadie los usa
  local n; n=$(powershell -NoProfile -File "$HARNESS_ROOT/.claude/scripts/barrer-huerfanos.ps1" 2>/dev/null | tr -d '\r')
  [[ $n =~ ^[1-9][0-9]*$ ]] && evento huerfanos 0 "$n nodos de MSBuild/vitest cerrados"
  return 0
}
memoria_libre_mb() { powershell -NoProfile -Command "[int]((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory/1KB)" 2>/dev/null | tr -d '\r'; }
CUPOS_DIR=${FLUJO_CUPOS_DIR:-${TMP:-/tmp}/flujo-cupos}; CUPOS=${FLUJO_CUPOS:-3}; MEMORIA_MIN_MB=${FLUJO_MEMORIA_MIN_MB:-2048}
CUPO=""; VIGIA=""
liberar_recursos() {
  [[ -n $MUESTREO ]] && kill "$MUESTREO" 2>/dev/null
  [[ -n $VIGIA ]] && kill "$VIGIA" 2>/dev/null
  [[ -n $CUPO ]] && rm -rf "$CUPO"
  barrer_nodos_huerfanos
}
trap liberar_recursos EXIT
# 2) Tope global de builds y suites a la vez en la máquina (no por sesión): un cupo = un directorio con el PID dueño.
#    Solo se toma alrededor de compilar() y suite(): el tiempo de Codex pensando no usa la máquina y antes
#    ocupaba el cupo entero (22/10: 6 tarjetas en fila con 2 cupos tomados por coders que solo esperaban al modelo).
#    Un cupo cuyo dueño murió se recupera. 3) Antes de arrancar una fase y de tomar cupo, espera memoria libre. 4) Con cupo, barre huérfanos cada minuto.
esperar_memoria() {
  local intento mb t0=$SECONDS
  for intento in $(seq 1 45); do  # hasta 15 min
    barrer_nodos_huerfanos
    mb=$(memoria_libre_mb)
    [[ -z $mb || $mb -ge $MEMORIA_MIN_MB ]] && { (( intento > 1 )) && evento memoria $((SECONDS - t0)) "esperó ${MEMORIA_MIN_MB} MB libres"; return 0; }
    (( intento == 1 )) && echo "Esperando memoria: ${mb} MB libres, hacen falta ${MEMORIA_MIN_MB}." >&2
    sleep 20
  done
  fallar "memoria insuficiente tras 15 min (${mb} MB libres de ${MEMORIA_MIN_MB}): cerrá algo o bajá FLUJO_CUPOS"
}
soltar_cupo() {
  [[ -n $VIGIA ]] && kill "$VIGIA" 2>/dev/null
  [[ -n $CUPO ]] && rm -rf "$CUPO"
  CUPO=""; VIGIA=""
}
tomar_cupo() {
  mkdir -p "$CUPOS_DIR"; local intento i t0=$SECONDS
  for intento in $(seq 1 180); do  # hasta 60 min
    for i in $(seq 1 "$CUPOS"); do
      local c="$CUPOS_DIR/cupo-$i"
      if [[ -d $c ]] && ! kill -0 "$(cat "$c/pid" 2>/dev/null)" 2>/dev/null; then rm -rf "$c"; fi
      if mkdir "$c" 2>/dev/null; then echo $$ > "$c/pid"; CUPO=$c; break 2; fi
    done
    (( intento == 1 )) && echo "Esperando cupo: ya hay $CUPOS corridas pesadas en la máquina (tope FLUJO_CUPOS)." >&2
    sleep 20
  done
  [[ -n $CUPO ]] || fallar "sin cupo tras 60 min: hay $CUPOS corridas pesadas colgadas en $CUPOS_DIR"
  (( intento > 1 )) && evento cupo $((SECONDS - t0)) "esperó un cupo libre (tope $CUPOS)"
  esperar_memoria
  ( while kill -0 $$ 2>/dev/null; do sleep 60; barrer_nodos_huerfanos; done ) > /dev/null 2>&1 &
  VIGIA=$!
}

ruta() { (cd "$1" && pwd -W 2>/dev/null || pwd); }
es_web() { [[ -f $1/package.json ]]; }
fallar() { echo "## Resumen"; echo "FALLÓ: $1"; exit 1; }

prefijo() {  # $@ = raíces
  local r lista=""
  for r in "$@"; do lista+="$r (rama $(git -C "$r" branch --show-current)), "; done
  cat <<EOF
Raíz de trabajo: ${lista%, }. **Verificá por ruta absoluta que estás ahí antes de tocar un solo archivo; si tu directorio inicial no coincide, usá la ruta absoluta igual y decilo en tu reporte.** Todo archivo del repo destino que leas, edites, compiles o diffees va bajo esa ruta; la carpeta principal del repo no se toca.

Reglas: archivos de más de 350 líneas por \`grep -n\` + lectura con offset/limit. Salida de comandos a un archivo fuera del repo ($SALIDA) y leer solo el resumen. Todo \`dotnet build\` o \`dotnet test\` va con \`-m:1 --disable-build-servers\`: en el sandbox, MSBuild en paralelo no conecta con sus nodos y deja cientos colgados (23/10: 12 GB).

EOF
}

# Un worktree nuevo de web-app no trae node_modules: sin ellos no hay tsc ni vitest y el coder "rompe el build". Se instalan solos.
preparar_web() {  # $1 raíz, $2 carpeta de logs
  es_web "$1" || return 0
  [[ -d $1/node_modules/typescript ]] && return 0
  echo "[flujo] $1 sin node_modules: npm ci" >&2
  (cd "$1" && npm ci > "$2/npm-ci.log" 2>&1) || fallar "npm ci falló en $1; ver $2/npm-ci.log"
}

# El build regenera src/routeTree.gen.ts y Git lo ve modificado solo por los fines de línea. Si el cambio es solo eso, se restaura:
# así no se cuela en el commit del coder ni hace fallar el control de "un revisor modificó archivos". Un cambio real no se toca.
limpiar_generados() {  # $1 raíz
  es_web "$1" || return 0
  local g=src/routeTree.gen.ts
  [[ -n $(git -C "$1" status --porcelain -- "$g") ]] || return 0
  git -C "$1" diff --ignore-space-at-eol --quiet -- "$g" && git -C "$1" restore -- "$g"
}

compilar() {  # $1 raíz, $2 log
  tomar_cupo; local rc=0
  if es_web "$1"; then
    local ts; ts=$(git -C "$1" status --porcelain | cut -c4- | grep -E '\.tsx?$')
    (cd "$1" && npx tsc -b > "$2" 2>&1 && { [[ -z $ts ]] || npx eslint $ts >> "$2" 2>&1; }) || rc=$?
  else
    dotnet build "$1" > "$2" 2>&1 || rc=$?
  fi
  soltar_cupo; return $rc
}

normalizar_docker_host() { local h=$1; echo "${h/#npipe:\/\/\/\//npipe://}"; }

suite() {  # $1 raíz, $2 log → imprime la línea de resultado
  # Testcontainers usa npipe://./pipe/docker_engine; Docker Desktop escucha en el endpoint de su contexto (2026-10-13: 75 pruebas de integración cayeron por eso).
  # El contexto lo da como npipe:////./pipe/... y Testcontainers lo rechaza ("not a npipe URI"): se colapsa a npipe://./pipe/... Un DOCKER_HOST ya puesto se respeta.
  [[ -n ${DOCKER_HOST:-} ]] || { local h; h=$(docker context inspect --format '{{.Endpoints.docker.Host}}' 2>/dev/null); [[ -n $h ]] && export DOCKER_HOST=$(normalizar_docker_host "$h"); }
  tomar_cupo
  if es_web "$1"; then
    (cd "$1" && npx vitest run --maxWorkers="${FLUJO_VITEST_WORKERS:-3}" > "$2" 2>&1); grep -E "Tests +[0-9]" "$2" | tail -1
  else
    # Cada clase de integración levanta su SQL Server: sin tope eran 11 a la vez y Docker caía con 4 GB (21/10).
    dotnet test "$1" -- xUnit.MaxParallelThreads="${FLUJO_XUNIT_HILOS:-3}" > "$2" 2>&1; grep -E "Passed!|Failed!" "$2" | tr '\n' ' '
  fi
  soltar_cupo
}

suite_roja() {  # $1 log de suite; sin resumen de verde también cuenta como roja
  grep -qE "Failed!|Tests +.*[0-9]+ failed|error (CS|TS)[0-9]+" "$1" || ! grep -qE "Passed!|Tests +[0-9]+ passed" "$1"
}

fallas_suite() {  # $1 log → lo justo para que el coder arregle
  if grep -q "Failed!" "$1"; then grep -E -B2 -A15 "^\s*Failed |Error Message" "$1" | head -120
  else grep -E -A25 "FAIL |AssertionError|Error:" "$1" | head -120; fi
}

# Cada codex exec queda en consumo.tsv (etiqueta<TAB>log): registrar_corrida.py --consumo suma sus «tokens used».
anotar_consumo() { printf '%s\t%s\n' "$1" "$2" >> "$SALIDA/consumo.tsv"; }
# Un motor que llega al timeout queda como «colgado» en recursos.tsv.
anotar_timeout() { [[ $1 == 124 ]] && evento colgado "$2" "$3 llegó al timeout"; return 0; }

lanzar_coder() {  # $1 prompt, $2 log; usa CODER
  local rc=0 t0=$SECONDS
  if [[ $CODER == codex ]]; then
    # Prompt por stdin: como argumento, uno de más de ~32 KB falla en Windows (24/10: «Argument list too long»).
    # agy no lee stdin en --print: ahí va una instrucción corta con la ruta del prompt.
    anotar_consumo "$(basename "$2" .log)" "$2"
    (cd "$RAIZ" && timeout 25m codex exec --sandbox workspace-write -m "${CODEX_MODEL_CODER:-gpt-6.1-sol}" -c model_provider=openai -c service_tier="fast" -c windows.sandbox=\"unelevated\" -c model_reasoning_effort="${CODEX_EFFORT:-medium}" - < "$1" > "$2" 2>&1) || rc=$?
    anotar_timeout $rc $((SECONDS - t0)) "codex $(basename "$2" .log)"
    barrer_nodos_huerfanos
  elif [[ $CODER == antigravity || $CODER == agy ]]; then
    # Antigravity como coder pleno (el responsable, 2026-10-16): mismas reglas y mismo ## Coder Report que Codex.
    (cd "$RAIZ" && timeout 25m agy --model "${AGY_MODEL:-gemini-3.8-flash-high}" --effort high --mode accept-edits --print="Leé completo y seguí al pie de la letra las instrucciones del archivo $(cygpath -m "$1" 2>/dev/null || echo "$1")." < /dev/null > "$2" 2>&1)
  else
    cc "$CODER"
    (cd "$RAIZ" && timeout 30m "${CC[@]}" -p --permission-mode acceptEdits \
       --allowedTools "Bash(dotnet build:*)" "Bash(npx tsc:*)" "Bash(git diff:*)" "Bash(git status:*)" \
       < "$1" > "$2" 2>&1)
  fi
}

ping_codex() { (cd "$HARNESS_ROOT" && timeout 2m codex exec -m gpt-6-luna -c model_reasoning_effort="low" -c model_provider=openai -c service_tier="fast" -c windows.sandbox=\"unelevated\" "Respondé solo: OK" < /dev/null > "$SALIDA/codex-ping.log" 2>&1); }
hay_codex() {
  # Un ping viejo o fallido no vale: ya hubo un coder que cayó a Claude en silencio por un log rancio.
  if [[ ! -f $SALIDA/codex-ping.log || -n $(find "$SALIDA/codex-ping.log" -mmin +10 2>/dev/null) ]] || ! grep -qE "^OK\s*$" "$SALIDA/codex-ping.log"; then ping_codex; fi
  grep -qE "^OK\s*$" "$SALIDA/codex-ping.log" 2>/dev/null
}

# Antigravity: mismo criterio que Codex (ping en modo plan, sin editar; vale 10 min).
ping_antigravity() { (cd "$HARNESS_ROOT" && timeout 2m agy --model "${AGY_MODEL:-gemini-3.8-flash-high}" --mode plan --print-timeout 90s --print="Respondé solo: OK" < /dev/null > "$SALIDA/agy-ping.log" 2>&1); }
hay_antigravity() {
  if [[ ! -f $SALIDA/agy-ping.log || -n $(find "$SALIDA/agy-ping.log" -mmin +10 2>/dev/null) ]] || ! grep -qE "^OK\s*$" "$SALIDA/agy-ping.log"; then ping_antigravity; fi
  grep -qE "^OK\s*$" "$SALIDA/agy-ping.log" 2>/dev/null
}
# CODER=agy|antigravity al lanzar elige Antigravity; si no responde, se para (no cae a otro motor en silencio).
elegir_coder() {  # $1 fase
  if [[ ${CODER_PEDIDO:-} == agy || ${CODER_PEDIDO:-} == antigravity ]]; then
    hay_antigravity && { CODER=antigravity; return; }
    fallar "ANTIGRAVITY NO DISPONIBLE ($1): ver $SALIDA/agy-ping.log; relanzar o quitar CODER=agy"
  fi
  # CODER=claude (30/10): todo con Claude aunque Codex responda; DeepSeek si Claude pasó el 70 %.
  if [[ ${CODER_PEDIDO:-} == claude ]]; then CODER=$(respaldo); return; fi
  if hay_codex; then CODER=codex; elif [[ ${PERMITIR_RESPALDO:-0} == 1 ]]; then CODER=$(respaldo); else fallar "CODEX NO DISPONIBLE ($1): ver $SALIDA/codex-ping.log; relanzar o usar PERMITIR_RESPALDO=1"; fi
}

# Respaldo de Codex. Uso desconocido o viejo (> 30 min) cuenta como bajo; el resumen lo dice.
USO_CLAUDE=${USO_CLAUDE:-$HOME/.claude/uso-5h.txt}
# Sin caídas silenciosas a Claude: si Codex no responde, se para y se dice por qué.
# Solo con PERMITIR_RESPALDO=1 (decisión explícita de quien lanza) cae al respaldo.
respaldo_o_parar() {
  if [[ ${PERMITIR_RESPALDO:-0} == 1 ]]; then respaldo; return; fi
  echo "CODEX NO DISPONIBLE ($1): ver $SALIDA/codex-ping.log. No se cae a Claude solo; relanzar cuando Codex responda o usar PERMITIR_RESPALDO=1." >&2
  exit 3
}

respaldo() {
  local pct ts
  read -r pct ts 2>/dev/null < "$USO_CLAUDE"
  if [[ $pct =~ ^[0-9]+$ && $ts =~ ^[0-9]+$ ]] && (( $(date +%s) - ts < 1800 && pct >= 70 )); then echo deepseek; else echo claude; fi
}
uso_claude() { local pct ts; read -r pct ts 2>/dev/null < "$USO_CLAUDE" && echo "${pct}%" || echo "desconocido"; }
# Deja en CC el comando de Claude Code para el motor dado.
cc() { if [[ $1 == deepseek ]]; then CC=(bash "$HARNESS_ROOT/.claude/scripts/claude-deepseek.sh"); else CC=(claude --model sonnet); fi; }

# Antes de lanzar: lo que rompería a mitad de camino (build, suite, motor) se para acá, todo junto y con qué hacer.
chequear_ambiente() {  # $1 raíz, resto: chequeos (rama docker host codex)
  local r=$1 c rama win pids problemas=(); shift
  for c in "$@"; do case $c in
    rama)
      rama=$(git -C "$r" symbolic-ref --short -q HEAD)
      if [[ -z $rama ]]; then problemas+=("HEAD detached en $r: hacé checkout de la rama de la tarjeta")
      elif [[ $rama =~ ^(develop|main|qa)$ ]]; then problemas+=("$r está en $rama: se trabaja en una rama feature/ o fix/, en su worktree"); fi ;;
    docker)
      # Solo si la suite trae integración con Testcontainers: sin Docker cae a mitad de la suite.
      es_web "$r" || [[ -z $(find "$r" -maxdepth 3 -name '*.csproj' -not -path '*/bin/*' -exec grep -l Testcontainers {} + 2>/dev/null) ]] \
        || DOCKER_HOST= timeout 15s docker info > /dev/null 2>&1 \
        || if tasklist //FI "IMAGENAME eq Docker Desktop.exe" 2>/dev/null | grep -qi "Docker Desktop.exe"; then
             # Ya abierto (Electron muestra ~5 procesos de una sola instancia): abrir otro no arregla un motor colgado.
             problemas+=("Docker Desktop ya está abierto pero el motor no responde: reinicialo desde su menú (Restart), NO abras otra instancia")
           else problemas+=("Docker Desktop no está abierto y la suite usa Testcontainers: abrilo y esperá a que diga Running"); fi ;;
    host)
      # El Host corriendo desde esta raíz bloquea sus DLL y el build falla a mitad (playbook §12). La barra final evita que api-core\ coincida con api-core--x.
      es_web "$r" && continue
      command -v powershell.exe > /dev/null || { echo "[flujo] sin powershell.exe: no se chequea si el Host está corriendo" >&2; continue; }
      win="$(cygpath -w "$r")\\"
      pids=$(timeout 15s powershell.exe -NoProfile -Command "Get-CimInstance Win32_Process -Filter \"Name='Host.exe' or Name='dotnet.exe'\" | Where-Object { \$_.ExecutablePath -like '$win*' -or \$_.CommandLine -like '*$win*' } | ForEach-Object { \$_.ProcessId }" 2>/dev/null | tr -d '\r' | tr '\n' ' ')
      [[ -z ${pids// } ]] || problemas+=("Host corriendo desde $win (PID ${pids% }): bloquea las DLL al compilar; cerralo (taskkill //PID <pid> //F) y relanzá") ;;
    codex)
      # Reusa el ping cacheado de hay_codex (10 min): la fase no vuelve a pingear.
      hay_codex || [[ ${PERMITIR_RESPALDO:-0} == 1 ]] || problemas+=("Codex no responde (cuota o caída): ver $SALIDA/codex-ping.log; esperá o usá PERMITIR_RESPALDO=1") ;;
  esac; done
  (( ${#problemas[@]} )) || return 0
  fallar "ambiente no listo$(printf -- '\n- %s' "${problemas[@]}")"
}

# Recibo de suite verde atado al commit, en el git común (lo ven todos los worktrees): lo exige scripts/hooks-repos/pre-push.
recibo_verde() {  # $1 raíz, $2 línea de resultado
  local d; d="$(git -C "$1" rev-parse --path-format=absolute --git-common-dir)/flujo-recibos"
  mkdir -p "$d" && echo "$2 | $(date '+%F %T')" > "$d/$(git -C "$1" rev-parse HEAD)"
}

# Diagnóstico sin lanzar nada: los mismos chequeos que las fases. Codex solo con SALIDA (ahí deja el ping).
fase_chequear() {
  RAIZ=$(ruta "${1:?raíz}"); SALIDA=${2:-}; local checks=(rama docker host)
  if [[ -n $SALIDA ]]; then mkdir -p "$SALIDA"; checks+=(codex); else echo "codex: sin SALIDA no se chequea"; fi
  es_web "$RAIZ" && { [[ -d $RAIZ/node_modules/typescript ]] && echo "web: node_modules listo" || echo "web: sin node_modules; preparar_web hace npm ci al lanzar"; }
  chequear_ambiente "$RAIZ" "${checks[@]}"
  echo "## Resumen"; echo "ambiente listo en $RAIZ (${checks[*]})"
}

fase_plan() {
  RAIZ=$(ruta "${1:?raíz}"); TAREA=${2:?tarea.md}; SALIDA=${3:?salida}; mkdir -p "$SALIDA"
  ping_codex & PING=$!
  { prefijo "$RAIZ"
    echo "**Fast-path Nivel 1 (sin architect)**: no agregues alcance, no documentes límites fuera de alcance. Plan mínimo."
    echo 'Formato: `## Plan` con lista numerada de tareas (cada una con sus archivos), una línea `Archivos que cambian: <ruta>, <ruta>` con todos los archivos existentes que el coder tiene que modificar (sin los nuevos ni los de referencia), `### Risk Flags` (yes/no por concurrencia, auth, esquema, frontera ADR-0001) y `### QA Test Matrix` corta.'
    echo; echo "Tarea:"; cat "$TAREA"; } > "$SALIDA/planner-prompt.md"
  # Desde la raíz de AcmeOrg: --agent solo encuentra .claude/agents/ ahí.
  (cd "$HARNESS_ROOT" && timeout 15m claude -p --agent planner --model sonnet --output-format json --add-dir "$RAIZ" \
     --allowedTools "Read" "Grep" "Glob" < "$SALIDA/planner-prompt.md" > "$SALIDA/planner.json" 2> "$SALIDA/planner.err")
  # wait con PID: un wait pelado también espera al vigía, que no termina nunca.
  wait "$PING"
  PYTHONIOENCODING=utf-8 python - "$SALIDA" <<'EOF' || fallar "el planner no devolvió un plan (ver planner.err)"
import json, re, sys
s = sys.argv[1]
d = json.load(open(f"{s}/planner.json", encoding="utf-8"))
plan = d.get("result") or ""
if "## Plan" not in plan: sys.exit(1)
open(f"{s}/plan.md", "w", encoding="utf-8").write(plan[plan.index("## Plan"):])
flags = re.search(r"### Risk Flags(.*?)(\n### |\Z)", plan, re.S)
ping = open(f"{s}/codex-ping.log", encoding="utf-8", errors="replace").read()
print("## Resumen")
print("Plan:", f"{s}/plan.md", f"({plan.count(chr(10))} líneas, {d.get('num_turns')} turnos)")
print("Risk Flags:", (flags.group(1).strip() if flags else "NO ENCONTRADAS"))
print("Codex:", "con cuota" if re.search(r"^OK\s*$", ping, re.M) else "SIN CUOTA o caído (ver codex-ping.log)")
EOF
}

# Pasada antislop (22/10: el coder entregó comentarios basura y las skills no estaban conectadas a nada).
# Corre sobre una copia: vuelve al árbol solo lo que es puro cambio de comentario, y se revierte si rompe el build.
pasada_antislop() {  # $1 = arreglar para sumar base..HEAD; en coder base..HEAD son tramos ya limpiados
  ANTISLOP=""
  [[ ${FLUJO_ANTISLOP:-1} == 0 ]] && { ANTISLOP="omitida (FLUJO_ANTISLOP=0)"; return 0; }
  [[ $CODER == codex ]] && hay_codex || { ANTISLOP="omitida (coder $CODER, sin Codex)"; return 0; }
  local d f n=0 rc=0 base="" et var lista=()
  if [[ ${1:-} == arreglar ]]; then
    et=$(basename "$RAIZ" | tr -c 'A-Za-z0-9\n' '_'); var="BASE_$et"
    base=${!var:-$(git -C "$RAIZ" merge-base HEAD origin/develop 2>/dev/null)}
  fi
  # Generados y migraciones fuera: sus comentarios no son del coder.
  while read -r f; do [[ -f $RAIZ/$f ]] && lista+=("$f"); done < <(
    { git -C "$RAIZ" diff --name-only HEAD; git -C "$RAIZ" ls-files -o --exclude-standard
      [[ -n $base ]] && git -C "$RAIZ" diff --name-only "$base" HEAD; } | sort -u \
      | grep -E '\.(cs|tsx?|jsx?)$' | grep -vE '(^|/)Migrations/|\.Designer\.cs$|ModelSnapshot\.cs$|\.gen\.ts$')
  (( ${#lista[@]} )) || { ANTISLOP="sin archivos de código"; return 0; }
  d=$(mktemp -d "$SALIDA/${P}antislop.XXXXXX")
  for f in "${lista[@]}"; do mkdir -p "$d/copia/$(dirname "$f")" "$d/original/$(dirname "$f")"
    cp "$RAIZ/$f" "$d/copia/$f"; cp "$RAIZ/$f" "$d/original/$f"; done
  printf '%s\n' "${lista[@]}" > "$d/archivos.txt"
  # Líneas que tocó el diff (lado nuevo): Codex reescribía comentarios viejos fuera del diff (3 veces al 23/10).
  for f in "${lista[@]}"; do
    if git -C "$RAIZ" ls-files --error-unmatch -- "$f" >/dev/null 2>&1; then
      git -C "$RAIZ" diff -U0 --no-renames "${base:-HEAD}" -- "$f" \
        | sed -nE 's/^@@ -[0-9,]+ \+([0-9]+)(,([0-9]+))? @@.*/\1 \3/p' \
        | while read -r ini cant; do echo "$f $ini $(( ini + ${cant:-1} - 1 ))"; done
    else echo "$f 1 999999999"; fi
  done > "$d/rangos.txt"
  # Codex no carga skills: el texto de la skill va en el prompt, sin frontmatter.
  { awk 'n>=2; /^---$/{n++}' "$HARNESS_ROOT/.claude/skills/antislop-code/SKILL.md"; echo
    echo "Tarea: aplicá esta skill SOLO a los comentarios de estos archivos (rutas relativas a tu carpeta actual):"
    printf -- '- %s\n' "${lista[@]}"
    echo "Nunca toques código, nombres, imports, espacios, indentación, finales de línea ni BOM; no agregues comentarios nuevos ni crees archivos; no compiles ni corras comandos."
    echo "Los comentarios en español que explican el porqué (reglas de negocio, fechas de incidentes, trampas de plataforma) se quedan. Si dudás, no lo toques. Cerrá con la lista de archivos editados."
  } > "$d/prompt.md"
  (cd "$d/copia" && timeout 8m codex exec --skip-git-repo-check --sandbox workspace-write -m gpt-6-luna -c model_provider=openai -c service_tier="fast" -c windows.sandbox=\"unelevated\" -c model_reasoning_effort="low" - < "$d/prompt.md" > "$d/codex.log" 2>&1) || rc=$?
  # Control mecánico: cada línea cambiada debe ser comentario o blanco; un comentario al final de una línea de código puede irse, el código no.
  PYTHONIOENCODING=utf-8 python - "$d" > "$d/validacion.txt" <<'EOF'
import difflib, re, sys
d = sys.argv[1]
COMENT = re.compile(r"^\s*(//|/\*|\*|\{/\*)|^\s*$")
def eol(l): return l[len(l.rstrip("\r\n")):]
def codigo(l):  # la línea sin su comentario final, si el // o /* está fuera de comillas
    s = l.rstrip("\r\n")
    for m in re.finditer(r"\s(//|/\*)", s):
        antes = s[:m.start()]
        if all(antes.count(q) % 2 == 0 for q in "\"'`"): return antes.rstrip()
    return s.rstrip()
def ok_par(o, n):
    if eol(o) != eol(n): return False
    if COMENT.match(o) and COMENT.match(n): return True
    return codigo(o) == codigo(n) and codigo(n).strip() != ""
rangos = {}
for l in open(f"{d}/rangos.txt", encoding="utf-8").read().splitlines():
    f, ini, fin = l.rsplit(" ", 2)
    rangos.setdefault(f, []).append((int(ini), max(int(ini), int(fin))))
def en_diff(f, i1, i2):  # i1..i2 en base 0 del original; una inserción pura cuenta su línea vecina
    a, b = i1 + 1, max(i2, i1 + 1)
    return any(a <= fin and ini <= b for ini, fin in rangos.get(f, []))
for f in open(f"{d}/archivos.txt", encoding="utf-8").read().splitlines():
    a, b = open(f"{d}/original/{f}", "rb").read(), open(f"{d}/copia/{f}", "rb").read()
    if a == b: continue
    try: ta, tb = a.decode("utf-8"), b.decode("utf-8")
    except UnicodeDecodeError: print(f"RECHAZO {f} no es UTF-8"); continue
    if ta.startswith("﻿") != tb.startswith("﻿"): print(f"RECHAZO {f} cambió el BOM"); continue
    la, lb = ta.splitlines(True), tb.splitlines(True)
    malo, res, dentro, fuera = None, [], 0, 0
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, la, lb, autojunk=False).get_opcodes():
        viejas, nuevas = la[i1:i2], lb[j1:j2]
        if op == "equal": res += viejas; continue
        if not en_diff(f, i1, i2): res += viejas; fuera += 1; continue  # fuera del diff: queda el original
        res += nuevas; dentro += 1
        if all(COMENT.match(l) for l in viejas + nuevas): continue
        vo, vn = [l for l in viejas if not COMENT.match(l)], [l for l in nuevas if not COMENT.match(l)]
        if len(vo) == len(vn) and all(ok_par(o, n) for o, n in zip(vo, vn)): continue
        malo = i1 + 1; break
    if malo: print(f"RECHAZO {f} tocó código cerca de la línea {malo}"); continue
    if not dentro: print(f"FUERA {f} solo cambió comentarios fuera del diff ({fuera} tramo(s))"); continue
    open(f"{d}/copia/{f}", "wb").write("".join(res).encode("utf-8"))
    print(f"OK {f} ({dentro} tramo(s) en el diff, {fuera} fuera descartado(s))")
EOF
  local rechazos; rechazos=$(grep -c '^RECHAZO' "$d/validacion.txt")
  while read -r _ f _; do cp "$d/copia/$f" "$RAIZ/$f"; n=$((n + 1)); done < <(grep '^OK ' "$d/validacion.txt")
  (( n )) || { ANTISLOP="sin cambios aplicables (rc $rc, rechazados $rechazos; ver ${d##*/}/validacion.txt)"; return 0; }
  # Build y tildes otra vez: si algo se rompe, vuelven los originales y se sigue sin la pasada.
  if compilar "$RAIZ" "$d/build.log" && python "$(dirname "$0")/revisar-tildes.py" "$RAIZ" > "$d/tildes.log" 2>&1; then
    ANTISLOP="aplicada en $n archivo(s), rechazados $rechazos (ver ${d##*/}/validacion.txt)"
  else
    while read -r _ f _; do cp "$d/original/$f" "$RAIZ/$f"; done < <(grep '^OK ' "$d/validacion.txt")
    compilar "$RAIZ" "$SALIDA/${P}build.log" || fallar "[$ET] build roto aun tras revertir antislop; ver ${P}build.log"
    ANTISLOP="REVERTIDA: build o tildes rotos tras la pasada (ver ${d##*/}/build.log y tildes.log)"
  fi
  echo "[$ET] antislop: $ANTISLOP" >&2
}

# Tests de integración de api-core (#104, 23/10: un contenedor SQL por test, 203 s → 57 s). Solo en api-core o un worktree suyo.
# BLOQUEA (devuelve 1) si se agrega MsSqlBuilder fuera de los dos fixtures. AVISO por archivo nuevo y por test de migración vencido:
# el test nombra la migración anterior a la que prueba; con 2+ posteriores en el repo, o la probada con más de N días, ya se aplicó.
chequear_integracion() {  # $1 raíz, $2 base
  local r=$1 base=$2 it=api-core.IntegrationTests dias=${FLUJO_DIAS_TEST_MIGRACION:-14} f ref sig n edad hoy migs
  [[ -d $r/$it ]] || return 0
  f=$(git -C "$r" diff -U0 "$base" HEAD -- . ":!$it/DatabaseFixture.cs" ":!$it/ServidorSqlCompartido.cs" \
      | awk '/^\+\+\+ /{a=substr($0,7)} /^\+[^+]/ && /MsSqlBuilder/{print a}' | sort -u | tr '\n' ' ')
  [[ -z $f ]] || { echo "BLOQUEA: contenedor SQL nuevo (MsSqlBuilder) en ${f% }; los tests usan DatabaseFixture o ServidorSqlCompartido.CrearBaseNuevaAsync"; return 1; }
  git -C "$r" diff --name-only --diff-filter=A "$base" HEAD -- "$it/" \
    | sed 's/^/AVISO: archivo nuevo de integración, justificá en una línea del run doc por qué no alcanza un test unitario: /'
  migs=$(git -C "$r" ls-tree --name-only HEAD Persistence/Migrations/ | sed -n 's#.*/\([0-9]\{14\}_[A-Za-z0-9_]*\)\.cs$#\1#p' | sort)
  hoy=$(date +%s)
  while read -r f ref; do
    sig=$(awk -v m="$ref" '$0 > m' <<< "$migs" | head -1); [[ -n $sig ]] || continue
    n=$(awk -v m="$ref" '$0 > m' <<< "$migs" | wc -l)
    edad=$(( (hoy - $(date -d "${sig:0:8}" +%s)) / 86400 ))
    (( n >= 2 || edad > dias )) && echo "AVISO: $f prueba $sig (hace $edad días; $n migraciones después de la que nombra): confirmá si ya se aplicó en todas las bases y retiralo"
  done < <(git -C "$r" grep -oE '"[0-9]{14}_[A-Za-z0-9_]+"' HEAD -- "$it/" | sed 's/^HEAD://; s/:"/ /; s/"$//' | sort -k1,1 -k2,2r | awk '!v[$1]++')
  return 0
}

# TDD + SDD (el responsable, 2026-10-23): todo cambio de lógica o estado arranca con los tests de aceptación de su REQ confirmado,
# en rojo y commiteados aparte; el coder los pone en verde sin tocarlos. Texto y estilos quedan fuera con SIN_TDD="<motivo>".
es_test() { [[ $1 =~ \.test\.tsx?$ || $1 =~ (^|/)[^/]*Tests?\.cs$ || $1 =~ (^|/)[^/]*Tests?/ ]]; }

correr_tests() {  # $1 raíz, $2 log, resto: archivos de test
  local raiz=$1 log=$2; shift 2; tomar_cupo
  if es_web "$raiz"; then
    (cd "$raiz" && npx vitest run "$@" > "$log" 2>&1)
  else
    local f filtro=""; for f in "$@"; do filtro+="${filtro:+|}FullyQualifiedName~$(basename "$f" .cs)"; done
    dotnet test "$raiz" --filter "$filtro" > "$log" 2>&1
  fi
  soltar_cupo
}

fase_tests() {
  RAIZ=$(ruta "${1:?raíz}"); SALIDA=${2:?salida}; ET=${3-}; MENSAJE=${4:?commit}
  P=${ET:+$ET-}
  PLAN=$SALIDA/plan.md; [[ -f $SALIDA/${P}plan.md ]] && PLAN=$SALIDA/${P}plan.md  # plan solo del tramo (24/10)
  [[ -f $PLAN ]] || fallar "falta $PLAN"
  [[ $MENSAJE =~ ^test(\(|:) ]] || fallar "[$ET] el commit de los tests va como test(...): $MENSAJE"
  # SDD: el plan cita un REQ aprobado y los tests salen de sus escenarios. Manda el estado: del frontmatter, no la carpeta.
  REQ=$(grep -oE 'REQ-[0-9]{4}' "$PLAN" | head -1)
  [[ -n $REQ ]] || fallar "[$ET] el plan no cita un REQ: redactalo y confirmalo con /requisitos antes de los tests"
  REQ_ARCH=$( { compgen -G "$HARNESS_ROOT/requisitos/$REQ-*.md" || compgen -G "$HARNESS_ROOT/requisitos/propuestas/$REQ-*.md"; } | head -1)
  [[ -n $REQ_ARCH ]] || fallar "[$ET] $REQ no existe en requisitos/; redactalo con /requisitos"
  REQ_ESTADO=$(sed -n '2,/^---$/s/^estado:[[:space:]]*//p' "$REQ_ARCH" | head -1 | tr -d '\r ')
  [[ $REQ_ESTADO =~ ^(confirmado|implementado|verificado)$ ]] || fallar "[$ET] $REQ está «${REQ_ESTADO:-sin estado}»: confirmalo con /requisitos antes de los tests"
  grep -q '^### Tests de aceptación' "$PLAN" || fallar "[$ET] el plan no tiene la sección ### Tests de aceptación (archivo y escenario $REQ/En por test)"
  chequear_ambiente "$RAIZ" rama docker host codex
  preparar_web "$RAIZ" "$SALIDA"; limpiar_generados "$RAIZ"
  [[ -z $(git -C "$RAIZ" status --porcelain) ]] || fallar "[$ET] el árbol de $RAIZ no está limpio"
  { prefijo "$RAIZ"
    echo "**Fase de tests (TDD).** Escribí SOLO los tests de la sección \`### Tests de aceptación\` del plan: uno por escenario de $REQ, con el id del escenario ($REQ/E1, E2…) en el nombre del test. Leé el REQ en $REQ_ARCH."
    echo "No toques código de producción: los tests tienen que FALLAR ahora contra el código actual, por la razón que describe el escenario (una aserción, no un error de sintaxis). Calcá el formato y los helpers de los tests vecinos. Nunca borres tests existentes ni cambies sus aserciones."
    # 24/10: el coder tuvo que agregar setup a un test vecino ya fijado y el script lo frenó; ese setup va acá.
    echo "En cada archivo de test que toques, agregá también el setup mínimo (mocks, datos de arranque) que necesiten sus tests existentes para seguir representando lo mismo con la regla nueva, sin cambiar sus aserciones. Para eso podés correr SOLO esos archivos de test y ver cuáles existentes se rompen por setup."
    echo "No corras la suite completa ni hagas commit. Cerrá con \`## Coder Report\`: archivos de test, un renglón por escenario con el test que lo cubre y por qué debería fallar hoy, y el setup que agregaste a tests existentes."
    echo; cat "$PLAN"; } > "$SALIDA/${P}tests-prompt.md"
  elegir_coder coder
  lanzar_coder "$SALIDA/${P}tests-prompt.md" "$SALIDA/${P}tests.log"
  limpiar_generados "$RAIZ"
  mapfile -t TESTS < <(git -C "$RAIZ" status --porcelain --untracked-files=all | cut -c4-)
  [[ ${#TESTS[@]} -gt 0 ]] || fallar "[$ET] el coder ($CODER) no escribió tests; ver ${P}tests.log"
  for f in "${TESTS[@]}"; do es_test "$f" || fallar "[$ET] la fase de tests tocó código que no es test: $f"; done
  python "$(dirname "$0")/revisar-tildes.py" "$RAIZ" > "$SALIDA/${P}tildes.log" 2>&1 || fallar "[$ET] tildes corruptas en los tests; ver ${P}tildes.log"
  # Vitest no chequea tipos: un test rojo puede no compilar y romper el build del coder (24/10: `exact` en ByRole).
  if es_web "$RAIZ"; then (cd "$RAIZ" && npx tsc -b > "$SALIDA/${P}tests-tsc.log" 2>&1) || fallar "[$ET] los tests no compilan (tsc); ver ${P}tests-tsc.log"; fi
  correr_tests "$RAIZ" "$SALIDA/${P}tests-rojo.log" "${TESTS[@]}"
  suite_roja "$SALIDA/${P}tests-rojo.log" || fallar "[$ET] los tests nuevos ya pasan: no fijan el cambio del $REQ; ver ${P}tests-rojo.log"
  # 24/10: un test existente en rojo acá suele ser setup faltante que después nadie puede tocar (queda fijado). Solo aviso.
  local ajenos
  ajenos=$(grep -E '^\s*(Failed|FAIL) ' "$SALIDA/${P}tests-rojo.log" | grep -viE "REQ[-_]?${REQ#REQ-}" | sed -E 's/^\s*(Failed|FAIL)\s+//; s/\s+\[[^]]*\]\s*$//' | sort -u | head -5 | paste -sd ';' -)
  git -C "$RAIZ" add -A -- . ':(exclude,glob)**/.coder-obj/**'
  git -C "$RAIZ" commit -q -m "$MENSAJE" -m "Escenarios de $REQ, en rojo antes del código." -m "Co-Authored-By: Claude Opus 5.5 <agent@example.invalid>" || fallar "[$ET] commit rechazado (¿hook de secretos?)"
  printf '%s\n' "${TESTS[@]}" > "$SALIDA/${P}tests-fijados.txt"
  git -C "$RAIZ" rev-parse HEAD > "$SALIDA/${P}tests-fijados.sha"
  echo "## Resumen"
  echo "[$ET] tests de $REQ en rojo ($CODER) — commit $(git -C "$RAIZ" log --oneline -1)"
  echo "[$ET] fijados: ${TESTS[*]}"
  echo "[$ET] rojo: $(grep -E 'Tests +[0-9]|Failed!|error (CS|TS)' "$SALIDA/${P}tests-rojo.log" | tail -1)"
  [[ -z $ajenos ]] || echo "[$ET] aviso: tests existentes en rojo, probable setup faltante: $ajenos"
}

tests_intactos() {  # los tests fijados no cambian desde su commit, salvo setup agregado
  local sha r quitadas agregadas aserciones; sha=$(cat "$SALIDA/${P}tests-fijados.sha")
  mapfile -t FIJ < "$SALIDA/${P}tests-fijados.txt"
  git -C "$RAIZ" diff --quiet "$sha" -- "${FIJ[@]}" && return 0
  # 24/10: dos líneas de _asignaciones.Setup(...) en un test vecino frenaron la corrida entera. Solo agregar
  # líneas que no son aserciones (ni quitar nada) se acepta: el setup no cambia lo que el test exige.
  r=$(git -C "$RAIZ" diff --unified=0 "$sha" -- "${FIJ[@]}" | awk '
    /^\+\+\+ / { cs = ($0 ~ /\.cs$/); next }
    /^--- / { next }
    /^-/ { if ($0 !~ /^-[[:space:]]*$/) q++; next }
    /^\+/ { a++
            if (cs && $0 ~ /Should|Assert\.|\[Fact|\[Theory|\[InlineData|\[Property/) s++
            if (!cs && $0 ~ /expect\(|(^|[^A-Za-z0-9_$.])(it|test|describe)(\.[A-Za-z]+)*\(/) s++ }
    END { print q+0, a+0, s+0 }')
  read -r quitadas agregadas aserciones <<< "$r"
  [[ $quitadas == 0 && $aserciones == 0 ]] || fallar "[$ET] el coder ($CODER) modificó los tests fijados del REQ ($quitadas líneas quitadas, $aserciones aserciones agregadas): ${FIJ[*]}"
  SETUP_FIJADOS="[$ET] tests fijados: solo setup agregado ($agregadas líneas), aceptado"
}

fase_coder() {
  RAIZ=$(ruta "${1:?raíz}"); SALIDA=${2:?salida}; ET=${3-}; MENSAJE=${4:?commit}; SOLO=${5:-}
  P=${ET:+$ET-}  # prefijo de logs; vacío en Nivel 1 (ejecutar), así la receta de registro no cambia
  PLAN=$SALIDA/plan.md; [[ -f $SALIDA/${P}plan.md ]] && PLAN=$SALIDA/${P}plan.md  # plan solo del tramo (24/10)
  [[ -f $PLAN ]] || fallar "falta $PLAN"
  SETUP_FIJADOS=""
  if [[ -f $SALIDA/${P}tests-fijados.txt ]]; then TDD=sí
  elif [[ -n ${SIN_TDD:-} ]]; then TDD="no ($SIN_TDD)"
  else fallar "[$ET] sin tests en rojo: corré antes \`flujo.sh tests\` (lógica o estado) o declarás SIN_TDD=\"<motivo>\" (solo texto o estilos)"; fi
  chequear_ambiente "$RAIZ" rama docker host codex
  preparar_web "$RAIZ" "$SALIDA"; limpiar_generados "$RAIZ"
  PRINCIPAL=$(dirname "$(git -C "$RAIZ" rev-parse --path-format=absolute --git-common-dir)")
  git -C "$PRINCIPAL" status --porcelain > "$SALIDA/${P}principal-antes.txt"
  [[ -z $(git -C "$RAIZ" status --porcelain) ]] || fallar "[$ET] el árbol de $RAIZ no está limpio"
  # -m:1 --disable-build-servers: en el sandbox de Codex MSBuild no conecta con sus nodos y lanza nodos nuevos sin parar
  # (23/10: 360 nodos huérfanos, 12 GB, en un minuto; el build "falló con 0 errores" y en secuencial compiló).
  if es_web "$RAIZ"; then VERIF="npx tsc -b > $SALIDA/${P}build-coder.log 2>&1"; else VERIF="dotnet build $RAIZ -m:1 --disable-build-servers > $SALIDA/${P}build-coder.log 2>&1"; fi
  { prefijo "$RAIZ"
    [[ -n $SOLO ]] && echo "**Tu tramo: $SOLO.** El resto del plan es de otro coder: no lo toques."
    [[ $TDD == sí ]] && echo "**TDD:** estos tests ya están commiteados en rojo y son la spec: $(tr '\n' ' ' < "$SALIDA/${P}tests-fijados.txt"). Ponelos en verde cambiando el código de producción; NO los modifiques. Si uno te parece mal, decilo en \`### Deviations from Plan\` y dejalo como está."
    echo "Tocá SOLO los archivos de tu tramo. Compilá con \`$VERIF\` y leé el tail. No corras tests ni hagas commit: la suite la corre el script después. Cerrá con \`## Coder Report\` (archivos tocados, resultado del build, \`### Deviations from Plan\` y, si es un fix, \`### Causa raíz\`)."
    # GT-09 (0068): las dos fallas fueron lugares que copiaban el campo vecino y no el nuevo.
    echo "Si agregás un campo a un tipo, buscá con grep dónde se construye ese tipo o se copia un campo vecino (mappers, fallbacks, fixtures y objetos esperados de tests) y propagalo ahí también, aunque el plan no nombre ese archivo."
    # Corrida 2026-10-13: tests rojos por no adaptar los que ejercitaban el comportamiento cambiado, .log sueltos en la raíz y "verde" afirmado sin poder ejecutar.
    echo "Si el plan cambia un comportamiento, los tests que lo ejercitaban se actualizan dentro de tu tramo: antes de cerrar, buscá con grep los tests que lo nombran. Un test que contradice el plan se adapta; uno que contradice un invariante, no."
    echo "No dejes archivos temporales ni .log dentro del repo: redirigí toda salida a $SALIDA. Si tu sandbox bloquea npx, dotnet o docker, decilo literal en el reporte y NO afirmes que compiló o pasó: el orquestador lo verifica."
    echo "En .NET, un miembro nuevo en una interfaz se implementa también en fakes y stubs de TODOS los proyectos de tests (grep \": NombreDeLaInterfaz\" en todo el repo); compilá la solución completa, no solo el proyecto Rest."
    echo "Escribí los archivos en UTF-8 sin corromper tildes ni eñes (\"Día\", \"Interacción\"): nunca \"D??a\". El script lo revisa."
    # 22/10 (detalle de una entidad): el coder entregó código minificado con BOM, borró tests e inventó 4 nombres de campo.
    echo "Estilo: calcá el formato del archivo vecino más parecido (indentación, saltos de línea, nombres). Nunca minifiques ni juntes en una línea, nunca agregues BOM. Nunca borres ni saltees tests existentes: si uno ya no aplica, adaptalo y decilo en el reporte."
    echo "Contrato con otro servicio: los nombres y tipos de campo salen del DTO real del backend (grep del ViewModel/Request en el repo hermano) o del Swagger, nunca inventados ni deducidos del nombre."
    echo; cat "$PLAN"; } > "$SALIDA/${P}coder-prompt.md"
  elegir_coder coder
  lanzar_coder "$SALIDA/${P}coder-prompt.md" "$SALIDA/${P}coder.log"
  sed -n '/^## Coder Report/,$p' "$SALIDA/${P}coder.log" > "$SALIDA/coder-report-$(basename "$RAIZ").md"
  [[ $TDD == sí ]] && tests_intactos
  # Build propio: el reporte del motor no cuenta.
  compilar "$RAIZ" "$SALIDA/${P}build.log" || fallar "[$ET] build roto tras el coder ($CODER); ver ${P}build.log"
  python "$(dirname "$0")/revisar-tildes.py" "$RAIZ" > "$SALIDA/${P}tildes.log" 2>&1 || fallar "[$ET] tildes corruptas tras el coder ($CODER); ver ${P}tildes.log"
  pasada_antislop coder
  # Suite una sola vez, acá: si falla, un intento del coder con solo las fallas. El gate reusa el resultado.
  suite "$RAIZ" "$SALIDA/${P}suite.log" > "$SALIDA/${P}suite.txt"
  REINTENTO=no
  if suite_roja "$SALIDA/${P}suite.log"; then
    REINTENTO=sí; evento reintento 0 "[$ET] suite roja tras el coder: $(cat "$SALIDA/${P}suite.txt")"
    { prefijo "$RAIZ"
      echo "El cambio de tu tramo ya está en el árbol, sin commit (\`git diff\`). Compila, pero la suite falla. Arreglá solo estas fallas, sin tocar nada fuera de tu tramo; si el test tiene razón, arreglá el código, no el test. Una falla de IntegrationTests o de infraestructura (Docker, base de datos) no es de tu tramo: no la persigas. Nunca toques Persistence/, migraciones, el snapshot de EF ni Services/ para hacer pasar una suite. Compilá con \`$VERIF\`. No corras tests ni hagas commit."
      echo; fallas_suite "$SALIDA/${P}suite.log"; } > "$SALIDA/${P}coder-fix-prompt.md"
    lanzar_coder "$SALIDA/${P}coder-fix-prompt.md" "$SALIDA/${P}coder-fix.log"
    [[ $TDD == sí ]] && tests_intactos
    compilar "$RAIZ" "$SALIDA/${P}build.log" || fallar "[$ET] build roto tras el reintento ($CODER); ver ${P}build.log"
    python "$(dirname "$0")/revisar-tildes.py" "$RAIZ" > "$SALIDA/${P}tildes.log" 2>&1 || fallar "[$ET] tildes corruptas tras el reintento ($CODER); ver ${P}tildes.log"
    suite "$RAIZ" "$SALIDA/${P}suite.log" > "$SALIDA/${P}suite.txt"
    # 24/10 (el responsable): sin tercer intento; dos rojos seguidos suelen ser spec o partición, no el coder.
    suite_roja "$SALIDA/${P}suite.log" && fallar "[$ET] suite roja tras un reintento: $(cat "$SALIDA/${P}suite.txt"); ver ${P}suite.log — tras 2 intentos: revisá la spec o la partición del plan antes de insistir"
  fi
  limpiar_generados "$RAIZ"
  # .coder-obj/ es salida de build del coder, nunca va al commit (corridas 0105, 0109).
  CAMBIOS=$(git -C "$RAIZ" status --porcelain | grep -v '\.coder-obj/')
  [[ -n $CAMBIOS ]] || fallar "[$ET] el coder ($CODER) no cambió nada; ver ${P}coder.log"
  # Namespaces de tests que sombrean los de producción y rompen la compilación (corridas 0101, 0102, 0105).
  local ns
  ns=$(cut -c4- <<< "$CAMBIOS" | grep '\.cs$' | while read -r f; do grep -HnE '^\s*namespace\s+api_core\.Tests\.(Rest|Application|Services|Domain|Persistence)\b' "$RAIZ/$f" 2>/dev/null; done)
  [[ -z $ns ]] || fallar "[$ET] namespace de test prohibido (copiá el del archivo vecino): $ns"
  # Un archivo que el plan manda cambiar y el coder no tocó (corridas 0100, 0105, 0107, 0109). Sale de la línea fija
  # «Archivos que cambian:» del plan; sin esa línea, o con tramo (SOLO: el plan trae archivos de otros coders), no se controla.
  PLAN_ARCHIVOS="sin línea «Archivos que cambian:» en el plan"
  if [[ -n $SOLO ]]; then PLAN_ARCHIVOS="no aplica (tramo)"
  elif grep -q '^Archivos que cambian:' "$PLAN"; then
    local falta="" rutas f
    while read -r f; do
      # El plan puede nombrar solo el archivo: se resuelve contra el repo y cuenta si hay uno solo con ese nombre.
      rutas=$(git -C "$RAIZ" ls-files -- "$f" "*/${f##*/}")
      [[ $(grep -c . <<< "$rutas") == 1 ]] || continue
      grep -qF "$rutas" <<< "$CAMBIOS" || falta+="$f "
    done < <(grep '^Archivos que cambian:' "$PLAN" | cut -d: -f2- | tr ',`' '\n ' | tr -d ' \r' | grep .)
    [[ -z $falta || -n ${PLAN_SIN_TOCAR_OK:-} ]] || fallar "[$ET] el plan manda cambiar archivos que el coder no tocó: $falta(si es a propósito: PLAN_SIN_TOCAR_OK=\"<motivo>\")"
    PLAN_ARCHIVOS="todos tocados${falta:+ salvo $falta(PLAN_SIN_TOCAR_OK: ${PLAN_SIN_TOCAR_OK:-})}"
  fi
  git -C "$PRINCIPAL" status --porcelain | diff -q - "$SALIDA/${P}principal-antes.txt" > /dev/null \
    || fallar "[$ET] la carpeta principal $PRINCIPAL cambió durante el coder"
  # Archivos nuevos: se aceptan solo si el plan los nombra.
  # Una migración de EF lleva un timestamp que el plan no puede saber: se busca solo su nombre.
  while read -r nuevo; do
    n=$(basename "$nuevo")
    [[ $n =~ ^[0-9]{14}_([^.]+)\.(Designer\.)?cs$ ]] && n=${BASH_REMATCH[1]}
    grep -qF "$n" "$PLAN" || fallar "[$ET] archivo nuevo fuera del plan: $nuevo"
  done < <(grep '^??' <<< "$CAMBIOS" | cut -c4-)
  git -C "$RAIZ" add -A -- . ':(exclude,glob)**/.coder-obj/**'
  git -C "$RAIZ" commit -q -m "$MENSAJE" -m "Co-Authored-By: Claude Opus 5.5 <agent@example.invalid>" || fallar "[$ET] commit rechazado (¿hook de secretos?)"
  echo "## Resumen"
  echo "$(git -C "$RAIZ" rev-parse HEAD) $(cat "$SALIDA/${P}suite.txt")" > "$SALIDA/suite-$(basename "$RAIZ").txt"
  recibo_verde "$RAIZ" "$(cat "$SALIDA/${P}suite.txt")"
  echo "[$ET] coder $CODER (uso Claude 5 h: $(uso_claude)) — commit $(git -C "$RAIZ" log --oneline -1)"
  echo "[$ET] suite: $(cat "$SALIDA/${P}suite.txt") (reintento por suite roja: $REINTENTO)"
  echo "[$ET] TDD: $TDD"
  [[ -z $SETUP_FIJADOS ]] || echo "$SETUP_FIJADOS"
  echo "[$ET] antislop: $ANTISLOP"
  echo "[$ET] archivos del plan: $PLAN_ARCHIVOS"
  echo "[$ET] archivos: $(git -C "$RAIZ" show --name-only --format= HEAD | tr '\n' ' ')"
}

# Arreglo sobre un árbol con cambios sin commit (un coder que falló, un hallazgo de revisión): mismas compuertas
# que `coder` (build, tildes, suite) pero sin exigir árbol limpio y sin commitear. Nunca `codex exec` suelto:
# en la corrida del 2026-10-13 saltarse estas compuertas dejó tests rojos y un proyecto de integración sin compilar.
fase_arreglar() {
  RAIZ=$(ruta "${1:?raíz}"); SALIDA=${2:?salida}; PROMPT=${3:?prompt.md}; ET=${4:-fix}; mkdir -p "$SALIDA"
  P="$ET-"
  chequear_ambiente "$RAIZ" rama docker host codex
  preparar_web "$RAIZ" "$SALIDA"
  { prefijo "$RAIZ"; cat "$PROMPT"
    echo; echo "No commitees. Cerrá con la lista de archivos tocados y qué verificaste; si no pudiste ejecutar algo, decilo."; } > "$SALIDA/${P}coder-prompt.md"
  elegir_coder arreglar
  lanzar_coder "$SALIDA/${P}coder-prompt.md" "$SALIDA/${P}coder.log"
  compilar "$RAIZ" "$SALIDA/${P}build.log" || fallar "[$ET] build roto tras el arreglo ($CODER); ver ${P}build.log"
  python "$(dirname "$0")/revisar-tildes.py" "$RAIZ" > "$SALIDA/${P}tildes.log" 2>&1 || fallar "[$ET] tildes corruptas ($CODER); ver ${P}tildes.log"
  pasada_antislop arreglar
  suite "$RAIZ" "$SALIDA/${P}suite.log" > "$SALIDA/${P}suite.txt"
  suite_roja "$SALIDA/${P}suite.log" && fallar "[$ET] suite roja tras el arreglo: $(cat "$SALIDA/${P}suite.txt"); ver ${P}suite.log"
  echo "## Resumen"
  echo "[$ET] arreglo $CODER — suite: $(cat "$SALIDA/${P}suite.txt")"
  echo "[$ET] antislop: $ANTISLOP"
  echo "[$ET] sin commit; cambios: $(git -C "$RAIZ" status --porcelain | cut -c4- | tr '
' ' ')"
}

# Tras un arreglo a mano del orquestador: la suite completa se corre una vez, atada al HEAD, y el gate no la repite.
fase_suite() {
  RAIZ=$(cd "$1" && pwd); SALIDA=$2; mkdir -p "$SALIDA"
  [[ -z $(git -C "$RAIZ" status --porcelain) ]] || fallar "commiteá antes: la suite se ata al HEAD"
  chequear_ambiente "$RAIZ" docker host
  preparar_web "$RAIZ" "$SALIDA"
  linea=$(suite "$RAIZ" "$SALIDA/test-$(basename "$RAIZ").log")
  echo "$(git -C "$RAIZ" rev-parse HEAD) $linea" > "$SALIDA/suite-$(basename "$RAIZ").txt"
  echo "## Resumen"; echo "suite $(basename "$RAIZ"): $linea"
  suite_roja "$SALIDA/test-$(basename "$RAIZ").log" && exit 1
  recibo_verde "$RAIZ" "$linea"
}

fase_gate() {
  SALIDA=${1:?salida}; shift; ADV=0; CODEX=0; RAICES=()
  for a in "$@"; do
    case $a in --adversary) ADV=1 ;; --codex) CODEX=1 ;; *) RAICES+=("$(ruta "$a")") ;; esac
  done
  (( ${#RAICES[@]} )) || fallar "gate sin raíces"
  # Un segundo gate no pisa los logs del primero: los anteriores quedan con la hora de su última escritura (corrida 0100).
  #    consumo.tsv pasa a apuntar al log renombrado, así los tokens del primer gate no se pierden ni se cuentan dos veces.
  local f viejo
  for f in qa.log qa.json qa.err adversary.log adversary.json adversary.err codex-review.log; do
    [[ -f $SALIDA/$f ]] || continue
    viejo="${f%.*}-$(date -r "$SALIDA/$f" +%H%M%S).${f##*.}"
    mv "$SALIDA/$f" "$SALIDA/$viejo"
    [[ -f $SALIDA/consumo.tsv ]] && sed -i "s|\t$SALIDA/$f\$|\t$SALIDA/$viejo|" "$SALIDA/consumo.tsv"
  done
  for r in "${RAICES[@]}"; do chequear_ambiente "$r" rama docker host; done
  if hay_codex; then REV=codex; elif [[ ${PERMITIR_RESPALDO:-0} == 1 ]]; then REV=$(respaldo); else fallar "CODEX NO DISPONIBLE (revisión): ver $SALIDA/codex-ping.log; relanzar o usar PERMITIR_RESPALDO=1"; fi
  RANGOS=""; ADD=(); DIRS=(); AVISOS=""
  for r in "${RAICES[@]}"; do
    et=$(basename "$r" | tr -c 'A-Za-z0-9\n' '_'); var="BASE_$et"
    base=${!var:-$(git -C "$r" merge-base HEAD origin/develop)}
    # Chequeo mecánico antes de las suites y los revisores: un bloqueo no gasta tokens.
    av=$(chequear_integracion "$r" "$base") || fallar "$av"
    AVISOS+=${av:+$av$'\n'}
    RANGOS+="- \`git -C $r diff $base..HEAD\`"$'\n'; ADD+=(--add-dir "$r")
  done
  cuerpo() {
    prefijo "${RAICES[@]}"
    echo "Usá rutas absolutas, sin cd. El cambio a revisar:"; echo "$RANGOS"
    for r in "${RAICES[@]}"; do cat "$SALIDA/coder-report-$(basename "$r").md" 2>/dev/null; done
    echo "Cerrá con tu hand-off y \`### Result: <PASS | FINDINGS>\`."; echo; cat "$SALIDA/plan.md"
  }
  for r in "${RAICES[@]}"; do preparar_web "$r" "$SALIDA"; limpiar_generados "$r"; done
  ESTADO_ANTES=$(for r in "${RAICES[@]}"; do git -C "$r" status --porcelain; done)
  # Suites una sola vez: se reusa la del coder si el HEAD no cambió (ciclo 1); si cambió, se corre acá, antes de los revisores.
  SUITES=""
  for r in "${RAICES[@]}"; do
    f="$SALIDA/suite-$(basename "$r").txt"; head=$(git -C "$r" rev-parse HEAD)
    if [[ -f $f && $(cut -d' ' -f1 "$f") == "$head" ]]; then linea=$(cut -d' ' -f2- "$f")
    else linea=$(suite "$r" "$SALIDA/test-$(basename "$r").log"); echo "$head $linea" > "$f"
      suite_roja "$SALIDA/test-$(basename "$r").log" || recibo_verde "$r" "$linea"; fi
    SUITES+="$(basename "$r"): $linea"$'\n'
  done
  HERR=("Bash(dotnet build:*)" "Bash(dotnet test:*)" "Bash(npx:*)" "Bash(git -C:*)" "Bash(tail:*)" "Bash(grep:*)" "Read" "Grep" "Glob")
  { cuerpo; echo
    echo "Suites ya corridas por el script sobre este mismo HEAD (logs en $SALIDA, \`suite.log\`/\`test-*.log\`):"; echo "$SUITES"
    echo 'No vuelvas a correr las suites completas: revisá el código. Un test puntual (`--filter` / `vitest run <archivo>`) solo si tu revisión lo necesita. Hand-off: `## QA Verdict`.'
    [[ -n $AVISOS ]] && { echo; echo "Avisos del chequeo de integración del script (revisalos contra qa.md, punto de tests de integración):"; echo "$AVISOS"; }
    # Resumen de la skill thermo-nuclear (22/10: el coder entregó código minificado y nadie lo frenó). Gravedad acotada para no bloquear por estilo.
    echo; echo "Dimensión extra, mantenibilidad (skill thermo-nuclear, resumida). Las reglas de arquitectura de tu definición (capas, 400 líneas) siguen igual. Buscá en el diff:"
    echo "- Archivos gigantes o código minificado / juntado en una línea."
    echo "- Condiciones espagueti: if de caso especial metidos en un flujo ajeno, booleanos o modos de un solo uso, condicionales repetidas que piden un modelo o helper."
    echo "- Abstracciones malas: wrappers que solo reenvían, casts/any/opcionales que tapan el contrato, helper propio cuando ya hay uno canónico, lógica en la capa equivocada."
    echo "- La reestructura que borra ramas enteras sin cambiar el comportamiento, si es evidente."
    echo "Gravedad: todo esto es P3 (seguimiento, no bloquea). Solo es P2 si un archivo de producción (no tests ni migraciones) supera ~600 líneas por este diff, o un método nuevo o tocado pasa de complejidad ciclomática ~15. Medí con \`grep -c '' <archivo>\` o \`git diff --stat\` y contando ramas; poné archivo:línea y la cifra."; } > "$SALIDA/qa-prompt.md"
  (( ADV )) && { cuerpo; echo; echo 'Hand-off: `## Adversarial Audit Report`.'; } > "$SALIDA/adversary-prompt.md"
  revisor() {  # $1 = qa | adversary
    if [[ $REV == codex ]]; then
      # Codex no lee .claude/agents/: la definición va en el prompt, sin el frontmatter.
      { awk 'n>=2; /^---$/{n++}' "$HARNESS_ROOT/.claude/agents/$1.md"; echo; echo "No edites archivos del repo: solo revisás."; echo
        cat "$SALIDA/$1-prompt.md"; } > "$SALIDA/$1-codex-prompt.md"
      anotar_consumo "$1" "$SALIDA/$1.log"
      (cd "${RAICES[0]}" && timeout 30m codex exec --sandbox workspace-write -m "${CODEX_MODEL_REVISION:-gpt-6.1-sol}" -c model_provider=openai -c service_tier="fast" -c windows.sandbox=\"unelevated\" "${ADD[@]}" - \
         < "$SALIDA/$1-codex-prompt.md" > "$SALIDA/$1.log" 2>&1)
    else
      cc "$REV"
      # Desde la raíz de AcmeOrg: --agent no se encuentra desde un worktree.
      (cd "$HARNESS_ROOT" && timeout 30m "${CC[@]}" -p --agent "$1" --output-format json "${ADD[@]}" \
         --allowedTools "${HERR[@]}" < "$SALIDA/$1-prompt.md" > "$SALIDA/$1.json" 2> "$SALIDA/$1.err")
    fi
  }
  PIDS=()
  revisor qa & PIDS+=($!)
  (( ADV )) && { revisor adversary & PIDS+=($!); }
  if (( CODEX )) && hay_codex; then
    # El prompt va por stdin ("-"): como argumento, un plan largo pasa el limite de Windows ("Argument list too long").
    { cuerpo; echo; echo "Sos segundo revisor: bugs reales con archivo:línea, sin estilo. No edites nada."; echo "En UI revisá además el foco: si un control con foco se desmonta o se deshabilita (al terminar una carga, resolver un conflicto o cerrar un aviso), ¿adónde va el foco? Si cae en body o fuera del modal, es hallazgo."; } > "$SALIDA/codex-review-prompt.md"
    anotar_consumo codex-review "$SALIDA/codex-review.log"
    (cd "${RAICES[0]}" && timeout 20m codex exec -s read-only -m "${CODEX_MODEL_REVISION:-gpt-6.1-sol}" -c model_provider=openai -c service_tier="fast" -c windows.sandbox=\"unelevated\" "${ADD[@]}" \
       - < "$SALIDA/codex-review-prompt.md" > "$SALIDA/codex-review.log" 2>&1) & PIDS+=($!)
  fi
  # wait con PIDs: un wait pelado también espera al vigía, que no termina nunca.
  wait "${PIDS[@]}"
  for f in qa adversary; do grep -qi "not found" "$SALIDA/$f.err" 2>/dev/null && fallar "$REV no encontró el agente $f; ver $f.err"; done
  for r in "${RAICES[@]}"; do limpiar_generados "$r"; done
  [[ $ESTADO_ANTES == "$(for r in "${RAICES[@]}"; do git -C "$r" status --porcelain; done)" ]] \
    || fallar "un revisor ($REV) modificó archivos del repo; ver git status"
  PYTHONIOENCODING=utf-8 SUITES="$SUITES" AVISOS="$AVISOS" CODEX_PEDIDO=$CODEX REV=$REV USO="$(uso_claude)" python - "$SALIDA" <<'EOF'
import json, os, re, sys
s = sys.argv[1]

def final_codex(t):
    t = "\n".join(l for l in t.splitlines() if "rmcp::" not in l)
    i = t.rfind("\ncodex\n")
    t = t[i + 7:] if i >= 0 else t[-1500:]
    return t.split("\ntokens used")[0]  # Codex repite el mensaje final después del conteo

print("## Resumen")
print(f"revisores: {os.environ['REV']} (uso Claude 5 h: {os.environ['USO']})")
for nombre in ("qa", "adversary"):
    if os.path.exists(f"{s}/{nombre}.json"):
        d = json.load(open(f"{s}/{nombre}.json", encoding="utf-8"))
        txt, sesion, como = d.get("result") or "", d.get("session_id"), "--resume"
    elif os.path.exists(f"{s}/{nombre}.log"):
        crudo = open(f"{s}/{nombre}.log", encoding="utf-8", errors="replace").read()
        m = re.search(r"session id:\s*(\S+)", crudo)
        txt, sesion, como = final_codex(crudo), m and m.group(1), "codex exec resume"
    else:
        continue
    r = re.search(r"### Result:\s*(\w+)", txt)
    print(f"{nombre}: {r.group(1) if r else 'SIN VEREDICTO'} (sesión {sesion}, para {como})")
    if not r or r.group(1) != "PASS":
        f = re.search(r"(### (?:P1 |P2 )?(?:Findings|Hallazgos).*?)(?=\n### (?!P2 Findings)|\Z)", txt, re.S)
        print((f.group(1).strip() if f else txt[-1500:])[:2500])
p = f"{s}/codex-review.log"
if os.path.exists(p):
    t = final_codex(open(p, encoding="utf-8", errors="replace").read())
    print("codex review:\n" + t.strip()[:2500])
elif os.environ["CODEX_PEDIDO"] == "1":
    print("codex review: omitida (sin cuota)")
print("Suites:\n" + os.environ["SUITES"].strip())
if os.environ["AVISOS"].strip():
    print("Avisos de integración:\n" + os.environ["AVISOS"].strip())
EOF
}

if [[ $FASE =~ ^(tests|coder|arreglar|gate|suite|ejecutar)$ ]]; then
  if [[ $FASE == gate ]]; then iniciar_muestreo "${1:-}"; else iniciar_muestreo "${2:-}"; fi
  esperar_memoria
fi

case $FASE in
  plan) fase_plan "$@" ;;
  tests) fase_tests "$@" ;;
  coder) fase_coder "$@" ;;
  gate) fase_gate "$@" ;;
  suite) fase_suite "$@" ;;
  chequear) fase_chequear "$@" ;;
  integracion) R=$(ruta "${1:?raíz}"); chequear_integracion "$R" "${2:-$(git -C "$R" merge-base HEAD origin/develop)}" ;;
  arreglar) fase_arreglar "$@" ;;
  ejecutar)
    R=${1:?raíz}; SALIDA=${2:?salida}; M=${3:?commit}
    BASE_EJ=$(git -C "$R" rev-parse HEAD)
    # Con TDD, los tests en rojo van primero en su propio commit; el mensaje sale del plan (línea "Commit de tests: test(...)").
    if [[ -z ${SIN_TDD:-} ]]; then
      MT=$(grep -oP '^Commit de tests:\s*\K.+' "$SALIDA/plan.md" | head -1)
      [[ -n $MT ]] || fallar "el plan no trae la línea «Commit de tests: test(...)» (o declarás SIN_TDD=\"<motivo>\")"
      fase_tests "$R" "$SALIDA" "" "$MT" | tee "$SALIDA/tests-resumen.txt" | grep -q "^FALLÓ" && { cat "$SALIDA/tests-resumen.txt"; exit 1; }
      cat "$SALIDA/tests-resumen.txt"
    fi
    fase_coder "$R" "$SALIDA" "" "$M" | tee "$SALIDA/coder-resumen.txt" | grep -q "^FALLÓ" && { cat "$SALIDA/coder-resumen.txt"; exit 1; }
    cat "$SALIDA/coder-resumen.txt"
    export "BASE_$(basename "$(ruta "$R")" | tr -c 'A-Za-z0-9\n' '_')=$BASE_EJ"
    fase_gate "$SALIDA" "$R" ;;
  *) fallar "fase desconocida: $FASE" ;;
esac
