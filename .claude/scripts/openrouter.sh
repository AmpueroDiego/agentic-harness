#!/usr/bin/env bash
# Motor externo OpenRouter (modelos gratis): pregunta + archivo opcional -> solo la respuesta.
# Uso: openrouter.sh --question "..." [--file ruta] [--model id]   |   openrouter.sh --list
# Solo contenido que no sea código de la empresa (decisión pendiente de el responsable): los modelos
# gratis pueden registrar lo que reciben.
set -euo pipefail

MODEL="${OPENROUTER_MODEL:-openrouter/free}"
QUESTION=""
FILE=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --question) QUESTION="$2"; shift 2 ;;
    --file) FILE="$2"; shift 2 ;;
    --model) MODEL="$2"; shift 2 ;;
    --list) LIST=1; shift ;;
    *) echo "argumento desconocido: $1" >&2; exit 2 ;;
  esac
done

if [[ -n "${LIST:-}" ]]; then
  curl -s https://openrouter.ai/api/v1/models | python -c "
import json,sys
for m in json.load(sys.stdin)['data']:
    p=m['pricing']
    if p.get('prompt')=='0' and p.get('completion')=='0': print(m['id'], m.get('context_length'))"
  exit 0
fi

[[ -z "$QUESTION" ]] && { echo "falta --question" >&2; exit 2; }

# setx no llega a sesiones ya abiertas: si falta en el entorno, se lee del registro del usuario.
KEY="${OPENROUTER_API_KEY:-}"
if [[ -z "$KEY" ]] && command -v powershell >/dev/null; then
  KEY=$(powershell -NoProfile -c "[Environment]::GetEnvironmentVariable('OPENROUTER_API_KEY','User')" | tr -d '\r\n')
fi
[[ -z "$KEY" ]] && { echo "OPENROUTER_API_KEY no está configurada" >&2; exit 3; }

# El contenido va por archivo temporal: en Windows un argumento largo supera el límite de la línea de comando.
BODY=$(mktemp)
trap 'rm -f "$BODY"' EXIT
QUESTION="$QUESTION" FILE="$FILE" MODEL="$MODEL" python - "$BODY" <<'PY'
import json, os, sys, io
q, f, m = os.environ['QUESTION'], os.environ['FILE'], os.environ['MODEL']
content = q
if f:
    content += "\n\n--- " + os.path.basename(f) + " ---\n" + io.open(f, encoding='utf-8', errors='replace').read()
io.open(sys.argv[1], 'w', encoding='utf-8').write(json.dumps({"model": m, "messages": [{"role": "user", "content": content}]}))
PY

RESP=$(curl -s https://openrouter.ai/api/v1/chat/completions \
  -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" --data-binary "@$BODY")

# Un error del proveedor sale con código distinto de 0: acá el exit code sí dice la verdad.
printf '%s' "$RESP" | python -c "
import json,sys
d=json.loads(sys.stdin.buffer.read().decode('utf-8'))
if 'error' in d: print('ERROR OpenRouter:', d['error'].get('message', d['error']), file=sys.stderr); sys.exit(4)
sys.stdout.reconfigure(encoding='utf-8')
print(d['choices'][0]['message']['content'])
u=d.get('usage') or {}
print(f\"\n[modelo: {d.get('model')} | tokens: {u.get('total_tokens','?')}]\", file=sys.stderr)"
