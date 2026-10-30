#!/usr/bin/env bash
# Pruebas de codex-revisar.sh y con-candado.sh con un Codex falso (CODEX_BIN): no gastan cuota, tardan segundos.
#   bash .claude/scripts/test_codex_revisar.sh
set -uo pipefail
AQUI=$(cd "$(dirname "$0")" && pwd)
T=$(mktemp -d "${TMPDIR:-/tmp}/test-codex-revisar.XXXX")
trap 'rm -rf "$T"' EXIT
# Marcador y candado en el temporal: los reales los usan los carriles en este momento.
export CODEX_MARCADOR=$T/sin-cuota.until CODEX_INACTIVIDAD_SEG=3 CODEX_BIN=$T/codex-falso
fallas=0
ok() { echo "ok    $1"; }
mal() { echo "FALLA $1"; fallas=$((fallas + 1)); }
espera() {  # espera <nombre> <exit esperado> <exit real> [texto que debe aparecer] [salida]
  if [[ $3 == "$2" && ( -z ${4:-} || ${5:-} == *"$4"* ) ]]; then ok "$1 (exit $3)"; else mal "$1: exit $3 (esperado $2) salida: ${5:-}"; fi
}

# Repo de juguete con un cambio para el rango.
git init -q "$T/repo"; git -C "$T/repo" -c user.email=t@t -c user.name=t commit -q --allow-empty -m base
echo "x = 1" > "$T/repo/a.py"; git -C "$T/repo" add a.py
git -C "$T/repo" -c user.email=t@t -c user.name=t commit -q -m cambio

# El falso escribe en el archivo de -o lo que pida FALSO_MODO y deja un testigo de que lo llamaron.
cat > "$CODEX_BIN" <<'EOF'
#!/usr/bin/env bash
touch "$FALSO_TESTIGO"; out=""
while (($#)); do [[ $1 == -o ]] && out=$2; shift; done
cat > /dev/null
case $FALSO_MODO in
  pass) echo '{"veredicto":"PASS","hallazgos":[]}' > "$out" ;;
  vacio) : > "$out" ;;
  invalido) echo '{"veredicto":"PASS","hallazgos":[],"extra":1}' > "$out" ;;
  findings) echo '{"veredicto":"FINDINGS","hallazgos":[{"prioridad":"P2","archivo":"a.py","linea":1,"resumen":"pierde el registro","evidencia":"e","arreglo":"r","bloquea":true},{"prioridad":"P3","archivo":"b.ts","linea":null,"resumen":"foco","evidencia":"e","arreglo":"r","bloquea":false}]}' > "$out" ;;
  cuota) echo "ERROR: You've hit your usage limit. 429 Too Many Requests" ;;
  mudo) echo $$ > "$FALSO_TESTIGO.pid"; sleep 300 & echo $! > "$FALSO_TESTIGO.sleep"; wait ;;
esac
EOF
chmod +x "$CODEX_BIN"
export FALSO_TESTIGO=$T/llamado

correr() { rm -f "$FALSO_TESTIGO"; FALSO_MODO=$1 bash "$AQUI/codex-revisar.sh" "$T/repo" HEAD~1..HEAD "$T/out/v.json" "${@:2}" 2>&1; }

s=$(correr pass); espera "PASS válido" 0 $? PASS "$s"
s=$(correr vacio); espera "JSON vacío" 2 $? "SIN VEREDICTO" "$s"
s=$(correr invalido); espera "JSON fuera del schema" 2 $? "SIN VEREDICTO" "$s"
printf -- '- P2 a.py:9 X — no aplica\n' > "$T/rech.md"
s=$(correr findings --rechazados "$T/rech.md" --foco "migración"); r=$?
espera "FINDINGS con líneas" 1 $r "P2 bloquea=si a.py:1 pierde el registro" "$s"
[[ $s == *"P3 bloquea=no b.ts foco"* ]] && ok "FINDINGS: línea sin número" || mal "FINDINGS: falta la línea P3 ($s)"
grep -q "Ya evaluados — no los repitas" "$T/out/v.prompt.md" && grep -q "Foco: migración" "$T/out/v.prompt.md" && grep -q "x = 1" "$T/out/v.prompt.md" \
  && ok "prompt con rechazados, foco y diff" || mal "prompt incompleto"

s=$(correr cuota); espera "sin cuota escribe marcador" 3 $? "SIN CUOTA" "$s"
[[ -s $CODEX_MARCADOR ]] && ok "marcador creado" || mal "no se creó el marcador"
s=$(correr pass); espera "marcador vigente" 3 $? "marcador vigente" "$s"
[[ ! -e $FALSO_TESTIGO ]] && ok "marcador vigente: no invocó el binario" || mal "invocó el binario con marcador vigente"
echo "$(( $(date +%s) - 10 )) vencido" > "$CODEX_MARCADOR"
s=$(correr pass); espera "marcador vencido se ignora" 0 $? PASS "$s"
rm -f "$CODEX_MARCADOR"

t0=$(date +%s); s=$(correr mudo); r=$?; dt=$(( $(date +%s) - t0 ))
espera "Codex mudo → COLGADO" 4 $r COLGADO "$s"
(( dt <= CODEX_INACTIVIDAD_SEG + 60 )) && ok "COLGADO en ${dt}s" || mal "COLGADO tardó ${dt}s"
sp=$(cat "$FALSO_TESTIGO.sleep" 2>/dev/null); sleep 1
if [[ -n $sp ]] && kill -0 "$sp" 2>/dev/null; then mal "quedó vivo el nieto ($sp)"; kill -9 "$sp"; else ok "árbol del colgado muerto"; fi

# con-candado: huérfano y vigilante.
export CANDADO_DIR=$T/candado.lock CANDADO_ESPERA_SEG=1
mkdir "$CANDADO_DIR"; echo "999999 00:00 suite muerta" > "$CANDADO_DIR/quien"
s=$(timeout 30 bash "$AQUI/con-candado.sh" echo tomado 2>&1); r=$?
espera "candado huérfano se toma" 0 $r tomado "$s"
[[ ! -e $CANDADO_DIR ]] && ok "candado liberado al salir" || mal "quedó el candado"

: > "$T/suite.log"
t0=$(date +%s)
s=$(VIGILAR_LOG=$T/suite.log VIGILAR_SEG=3 timeout 60 bash "$AQUI/con-candado.sh" sleep 300 2>&1); r=$?; dt=$(( $(date +%s) - t0 ))
espera "con-candado: log quieto → COLGADO" 4 $r COLGADO "$s"
echo "      (cortó en ${dt}s)"
[[ ! -e $CANDADO_DIR ]] && ok "candado liberado tras COLGADO" || mal "quedó el candado tras COLGADO"

s=$(VIGILAR_LOG=$T/suite2.log VIGILAR_SEG=3 timeout 60 bash "$AQUI/con-candado.sh" bash -c 'for i in 1 2 3 4 5 6; do echo $i >> "$0"; sleep 1; done; echo fin' "$T/suite2.log" 2>&1); r=$?
espera "con-candado: log que crece no se corta" 0 $r fin "$s"

echo; (( fallas == 0 )) && echo "TODAS OK" || echo "$fallas FALLAS"
exit $(( fallas > 0 ))
