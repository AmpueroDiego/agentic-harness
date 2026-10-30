#!/usr/bin/env bash
# Una sola suite/coder .NET a la vez en toda la máquina: mkdir es atómico.
#   con-candado.sh <comando> [args...]
# CANDADO_DIR: ruta del candado (default ${TMPDIR:-/tmp}/acmeorg-dotnet.lock).
# VIGILAR_LOG=<archivo> [VIGILAR_MIN=10 | VIGILAR_SEG]: si ese log no crece en ese tiempo, mata el árbol y sale 4 (COLGADO).
set -uo pipefail
L=${CANDADO_DIR:-${TMPDIR:-/tmp}/acmeorg-dotnet.lock}
mkdir -p "$(dirname "$L")"

vivo() { [[ $1 =~ ^[0-9]+$ ]] && kill -0 "$1" 2>/dev/null; }

# Candado huérfano: su dueño murió sin limpiar (corte de sesión, kill -9). El mv es atómico: un solo esperador lo reclama.
reclamar_huerfano() {
  local quien=$L/quien pid edad
  if [[ -s $quien ]]; then
    read -r pid _ < "$quien"
  else
    # Sin "quien" puede ser alguien entre el mkdir y la escritura: solo es huérfano si ya pasaron 30 s.
    edad=$(( $(date +%s) - $(stat -c %Y "$L" 2>/dev/null || date +%s) ))
    (( edad > 30 )) || return 0; pid=""
  fi
  vivo "$pid" && return 0
  local tmp=$L.huerfano.$$
  mv "$L" "$tmp" 2>/dev/null || return 0
  # Si entre la lectura y el mv otro lo tomó de nuevo, se le devuelve.
  if [[ -s $tmp/quien ]] && read -r pid2 _ < "$tmp/quien" && [[ $pid2 != "$pid" ]] && vivo "$pid2"; then
    mv "$tmp" "$L" 2>/dev/null; return 0
  fi
  echo "con-candado: candado huérfano de ${pid:-?} liberado" >&2
  rm -rf "$tmp"
}

until mkdir "$L" 2>/dev/null; do
  reclamar_huerfano
  mkdir "$L" 2>/dev/null && break
  sleep "${CANDADO_ESPERA_SEG:-30}"
done
desde=$(date +%s)
echo "$$ $(date +%H:%M) $*" > "$L/quien"

matar_arbol() {  # taskkill /T llega a los nietos nativos (testhost, dotnet); los de MSYS no cuelgan del árbol de Windows: se buscan por /proc.
  local todos=("$1") i=0 p hijo wp
  while (( i < ${#todos[@]} )); do
    p=${todos[i]}; i=$((i + 1))
    for hijo in /proc/[0-9]*; do [[ $(cat "$hijo/ppid" 2>/dev/null) == "$p" ]] && todos+=("${hijo#/proc/}"); done
  done
  wp=$(cat "/proc/$1/winpid" 2>/dev/null)
  [[ -n $wp ]] && taskkill //PID "$wp" //T //F >/dev/null 2>&1
  kill -9 "${todos[@]}" 2>/dev/null
}

# Nodos MSBuild que dejó el comando: descendientes de su proceso, o creados después de tomar el candado
# y con el padre ya muerto. Nunca los de la máquina entera (Visual Studio del responsable, otros builds).
limpiar_msbuild() {
  dotnet build-server shutdown >/dev/null 2>&1
  command -v powershell.exe >/dev/null || return 0
  powershell.exe -NoProfile -NonInteractive -Command "
    \$raiz = ${winraiz:-0}; \$desde = [DateTimeOffset]::FromUnixTimeSeconds($desde).LocalDateTime
    \$todos = Get-CimInstance Win32_Process; \$vivos = @{}; \$todos | % { \$vivos[[int]\$_.ProcessId] = \$_ }
    \$todos | ? { \$_.CommandLine -match 'MSBuild\.dll.*nodemode' } | % {
      \$p = \$_; \$suyo = \$false; \$c = \$p; \$n = 0
      while (\$c -and \$n -lt 20) { if (\$c.ParentProcessId -eq \$raiz) { \$suyo = \$true; break }; \$c = \$vivos[[int]\$c.ParentProcessId]; \$n++ }
      if (-not \$suyo -and \$p.CreationDate -ge \$desde -and -not \$vivos.ContainsKey([int]\$p.ParentProcessId)) { \$suyo = \$true }
      if (\$suyo) { Stop-Process -Id \$p.ProcessId -Force -ErrorAction SilentlyContinue }
    }" >/dev/null 2>&1
}

# Raíz del árbol: este mismo bash; todo lo que lance el comando cuelga de él.
winraiz=$(cat "/proc/$$/winpid" 2>/dev/null)
trap 'limpiar_msbuild; rm -rf "$L"' EXIT
export MSBUILDDISABLENODEREUSE=1

if [[ -z ${VIGILAR_LOG:-} ]]; then
  "$@"; exit $?
fi

# Vigilante: suites con testhost colgados dejan el log quieto para siempre.
inact=${VIGILAR_SEG:-$(( ${VIGILAR_MIN:-10} * 60 ))}
paso=$(( inact / 2 )); (( paso < 1 )) && paso=1; (( paso > 15 )) && paso=15
"$@" &
pid=$!
tam=-1; quieto=0
while kill -0 "$pid" 2>/dev/null; do
  sleep "$paso"
  t=$(stat -c %s "$VIGILAR_LOG" 2>/dev/null || echo 0)
  if [[ $t == "$tam" ]]; then quieto=$((quieto + paso)); else tam=$t; quieto=0; fi
  if (( quieto >= inact )) && kill -0 "$pid" 2>/dev/null; then
    matar_arbol "$pid"; wait "$pid" 2>/dev/null
    echo "COLGADO: $VIGILAR_LOG no creció en ${inact}s; se mató el árbol de: $*" >&2; exit 4
  fi
done
wait "$pid"; exit $?
