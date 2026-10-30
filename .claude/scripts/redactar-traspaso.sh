#!/usr/bin/env bash
# Delega el PRIMER BORRADOR de un traspaso de sesion a un modelo barato
# (agy/Gemini flash), para no gastar el modelo caro redactando justo cuando
# el contexto de la sesion ya esta carisimo (ver .claude/hooks/aviso-contexto.py).
# El modelo caro revisa, corrige y guarda el archivo final en .claude/traspasos/ -
# este script nunca escribe ahi ni ejecuta git por si mismo.
#
# Uso: redactar-traspaso.sh <ruta-al-transcript.jsonl>
# Imprime el borrador y lo deja además en un .md junto al transcript (la ruta sale por stderr).
set -euo pipefail

AGY="${SHUNT_AGY_BIN:-$(command -v agy || command -v agy.exe || true)}"
# "low": la tarea es resumir/extraer de una conversacion ya dada, no razonar sobre algo
# ambiguo - no necesita mas esfuerzo que eso, y consume menos computo por llamada (mas
# probable que tenga cupo libre si el server esta saturado). Si no responde, escala una
# vez a "medium"; no hace falta "high" para este trabajo.
MODEL="${SHUNT_MODEL:-gemini-3.8-flash-low}"
MODEL_FALLBACK="${SHUNT_MODEL_FALLBACK:-gemini-3.8-flash-medium}"
TIMEOUT="${SHUNT_TIMEOUT:-120s}"
DIR_SCRIPT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DIR_TRASPASOS="$DIR_SCRIPT/../traspasos"

TRANSCRIPT="${1:?Uso: redactar-traspaso.sh <ruta-al-transcript.jsonl>}"
[ -f "$TRANSCRIPT" ] || { echo "No existe el transcript: $TRANSCRIPT" >&2; exit 1; }
[ -f "$AGY" ] || { echo "No se encontro el CLI de agy en '$AGY'. Fijar SHUNT_AGY_BIN si esta en otra ruta." >&2; exit 1; }

SCRATCH="${SHUNT_SCRATCH_DIR:-$(dirname "$TRANSCRIPT")}"
DIGEST="$SCRATCH/traspaso-digest-$$.txt"
BORRADOR="$SCRATCH/traspaso-borrador-$$.txt"
ENTRADA="$SCRATCH/traspaso-entrada-$$.txt"
trap 'rm -f "$DIGEST" "$BORRADOR" "$ENTRADA"' EXIT

python "$DIR_SCRIPT/extraer-conversacion.py" "$TRANSCRIPT" > "$DIGEST"

GITLOG=$(git log --oneline -20 2>/dev/null || echo "(sin repo git aqui)")
GITSTATUS=$(git status --short 2>/dev/null || echo "(sin cambios o sin repo git aqui)")

# Ejemplo real de traspaso para calibrar tono y estructura (el mas reciente que exista).
EJEMPLO=$(ls -t "$DIR_TRASPASOS"/*.md 2>/dev/null | head -1 || true)

PROMPT="Sos un asistente que redacta el PRIMER BORRADOR de un traspaso de sesion para el proyecto AcmeOrg sistema. No es la version final: un modelo mas capaz lo va a revisar y corregir antes de guardarlo, asi que preferi ser completo y literal antes que elegante o breve.

Estilo obligatorio (mira el ejemplo real que te doy al final):
- Espanol informal, sin emojis, sin relleno, sin saludos.
- Titulo con fecha y una linea de una frase de que trata la sesion.
- Si en la conversacion se menciona un traspaso anterior del que esta sesion parte, decir 'continua y supera a X' y como retomar en una sesion nueva.
- Secciones con encabezados ## y bullets cortos, nunca prosa larga.
- Primero el estado final: que quedo hecho, en que orden, con hashes de commit / numeros de PR o tarjeta si aparecen en la conversacion o el git log.
- Una seccion aparte por cada bug encontrado o decision no obvia tomada en el camino, con la leccion aprendida para la proxima.
- Una seccion final 'Pendiente' con lo que quedo sin resolver, tal como se haya dicho en la conversacion.
- Nunca inventes datos (PRs, hashes, nombres, numeros) que no esten literalmente en la conversacion o en el git log/status de abajo. Si algo es ambiguo, dejalo marcado como '(verificar)' en vez de adivinar.

Te doy:
1. El volcado de la conversacion de la sesion (turnos [user] y [assistant], sin las llamadas a herramientas), pegado al final entre las marcas VOLCADO.
2. El ejemplo de formato real (usalo solo para tono y estructura, no copies su contenido), tambien al final.
3. git log --oneline -20 y git status --short de este repo, ya pegados abajo.

git log:
$GITLOG

git status:
$GITSTATUS

Escribi el borrador completo en Markdown, listo para que alguien lo pegue en un .md. No uses herramientas ni comandos: todo lo que necesitas esta en este mensaje (en modo headless cualquier herramienta se niega y no hay salida)."

# Todo va por stdin, sin --add-dir ni lectura de archivos: leer archivos pide un permiso
# "command" que headless no puede aprobar (sin salida), y un argumento largo rompe el limite
# de la linea de comandos de Windows.
{
  printf '%s

===== VOLCADO =====
' "$PROMPT"
  cat "$DIGEST"
  printf '
===== FIN VOLCADO =====
'
  if [ -n "$EJEMPLO" ]; then
    printf '
===== EJEMPLO DE FORMATO =====
'
    cat "$EJEMPLO"
    printf '
===== FIN EJEMPLO =====
'
  fi
} > "$ENTRADA"

# agy sale con codigo 0 incluso si agota el print-timeout sin respuesta (el aviso va a
# stderr, stdout queda vacio) - por eso el fallback se decide por "hubo salida", no por
# el codigo de salida.
"$AGY" --model "$MODEL" --mode plan --print-timeout "$TIMEOUT" < "$ENTRADA" > "$BORRADOR" || true

if [ ! -s "$BORRADOR" ]; then
  echo "agy no respondio con '$MODEL' (probable falta de capacidad del server); reintentando con '$MODEL_FALLBACK'..." >&2
  "$AGY" --model "$MODEL_FALLBACK" --mode plan --print-timeout "$TIMEOUT" < "$ENTRADA" > "$BORRADOR" || true
fi

if [ ! -s "$BORRADOR" ]; then
  echo "agy no respondio con ningun modelo ('$MODEL' ni '$MODEL_FALLBACK')." >&2
  exit 1
fi

# El inventario de worktrees va tal cual, sin pasar por el modelo: el volcado solo ve lo que se
# habló, y el 22/10 el traspaso no nombró una rama con 5 commits sin subir (se duplicó su tarjeta).
{
  printf '\n## Trabajo en vuelo (automático, `trabajo-en-vuelo.py`)\n\nCada fila **sin PR** es trabajo a medias: retomarlo antes de crear tarjeta o rama nueva para lo mismo.\n\n'
  PYTHONIOENCODING=utf-8 python "$DIR_SCRIPT/trabajo-en-vuelo.py" 2>&1 || echo "(falló trabajo-en-vuelo.py: correrlo a mano)"
} >> "$BORRADOR"

# Además de imprimirlo, el borrador queda en un archivo: cortar la salida con `tail` lo perdía
# entero (19/10) y el último traspaso de .claude/traspasos/ parecía ser el «borrador».
GUARDADO="$SCRATCH/traspaso-borrador-$(date +%Y%m%d-%H%M).md"
cp "$BORRADOR" "$GUARDADO"
cat "$BORRADOR"
echo "Borrador guardado en: $GUARDADO (no está en .claude/traspasos/: revisarlo y guardar ahí la versión final)" >&2
