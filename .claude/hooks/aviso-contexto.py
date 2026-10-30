"""UserPromptSubmit: avisa cuando la sesion relee demasiado contexto Y ademas hay
una señal de que el trabajo actual esta cerrado.

Pasado el umbral, cada llamada del orquestador cuesta varias veces lo que costaria en una
sesion limpia (sesion 124ca073: $28.75 contra $17.01). Antes disparaba solo por umbral y
dejaba que el modelo caro redactara el traspaso justo con el contexto mas caro - el peor
momento posible para eso. Ahora es conservador: solo dispara si ademas detecta una señal de
cierre (texto tipo "cerrado"/"pusheado"/"traspaso" en la ultima respuesta, o un commit
reciente), y el aviso deriva el primer borrador a `.claude/scripts/redactar-traspaso.sh`
(modelo barato) en vez de pedirselo al modelo caro. El "¿de verdad termino?" sigue siendo
juicio del modelo caro - el hook solo evita que redacte el borrador el mismo.

Umbral por AVISO_CONTEXTO_K (miles de tokens), 200 por defecto.
Ventana de "commit reciente" por AVISO_CONTEXTO_COMMIT_MIN (minutos), 20 por defecto.
Nunca bloquea.
"""
import json
import os
import re
import subprocess
import sys
import time

PATRON_CIERRE = re.compile(
    r"(?i)\b(cerrad[oa]|pusheado|pusheada|mergead[oa]|traspaso|"
    r"todo (comiteado|pusheado)|queda pendiente|listo para (revisi[oó]n|mergear))\b"
)


def cola_transcript(ruta, bytes_max=2_000_000):
    with open(ruta, "rb") as f:
        f.seek(0, os.SEEK_END)
        f.seek(max(0, f.tell() - bytes_max))
        return f.read().decode("utf-8", errors="replace").splitlines()


def contexto_actual(lineas):
    for linea in reversed(lineas):
        try:
            d = json.loads(linea)
        except ValueError:
            continue
        u = (d.get("message") or {}).get("usage")
        if d.get("type") == "assistant" and u and not d.get("isSidechain"):
            return sum(u.get(k) or 0 for k in ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
    return 0


def ultimo_texto_asistente(lineas):
    for linea in reversed(lineas):
        try:
            d = json.loads(linea)
        except ValueError:
            continue
        if d.get("type") != "assistant" or d.get("isSidechain"):
            continue
        contenido = (d.get("message") or {}).get("content")
        if isinstance(contenido, list):
            return "\n".join(b.get("text", "") for b in contenido if isinstance(b, dict) and b.get("type") == "text")
        if isinstance(contenido, str):
            return contenido
    return ""


def commit_reciente(cwd, minutos):
    try:
        ts = subprocess.run(
            ["git", "-C", cwd, "log", "-1", "--format=%ct"],
            capture_output=True, text=True, timeout=3,
        ).stdout.strip()
        return bool(ts) and (time.time() - int(ts)) < minutos * 60
    except Exception:
        return False


def main():
    try:
        entrada = json.load(sys.stdin)
        ruta_transcript = entrada["transcript_path"]
        lineas = cola_transcript(ruta_transcript)
        ctx = contexto_actual(lineas)
    except Exception:
        return  # un aviso roto nunca debe frenar el prompt

    umbral = int(os.environ.get("AVISO_CONTEXTO_K", "200")) * 1000
    if ctx < umbral:
        return

    minutos = int(os.environ.get("AVISO_CONTEXTO_COMMIT_MIN", "20"))
    cwd = entrada.get("cwd") or os.getcwd()
    hay_cierre = bool(PATRON_CIERRE.search(ultimo_texto_asistente(lineas))) or commit_reciente(cwd, minutos)
    if not hay_cierre:
        return

    aviso = (
        f"Contexto en {ctx // 1000}K y parece que el trabajo cerro. Si es asi, corre "
        f'`.claude/scripts/redactar-traspaso.sh "{ruta_transcript}"` para que el modelo barato '
        "arme el primer borrador del traspaso; vos solo lo revisas, corregis y guardas en "
        ".claude/traspasos/."
    )
    print(json.dumps({
        "systemMessage": aviso,
        "hookSpecificOutput": {
            "hookEventName": "UserPromptSubmit",
            "additionalContext": (
                aviso + " Si el pedido nuevo es otro trabajo, sugiere cerrar primero con el "
                "traspaso delegado antes de empezar. No redactes el traspaso vos mismo salvo "
                "que el script falle."
            ),
        },
    }))  # JSON con acentos escapados: la consola de Windows no siempre es UTF-8


if __name__ == "__main__":
    main()
