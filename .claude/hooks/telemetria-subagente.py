#!/usr/bin/env python3
"""Mide tokens por subagente y los empuja a Prometheus.

POR QUE EXISTE
--------------
La metrica oficial `claude_code_token_usage_total` trae la etiqueta `agent_name`,
pero Claude Code solo publica el nombre real de los agentes built-in y de los de
plugins del marketplace oficial: los definidos en `.claude/agents/` se reportan
TODOS como "custom", en una sola bolsa. Asi no se puede saber si `adversary` sale
caro frente a `coder`.

Los hooks si tienen el dato: `SubagentStart`/`SubagentStop` reciben `agent_type`
con el nombre real. No traen tokens, pero traen `transcript_path`, y el transcript
si tiene un bloque `usage` por mensaje. Este script junta las dos mitades.

COMO MIDE
---------
Por diferencia, no por suma absoluta:

    SubagentStart -> anota el acumulado del transcript como linea base
    SubagentStop  -> vuelve a leer y se queda con la diferencia

Eso es correcto tanto si `transcript_path` apunta al transcript propio del
subagente (la base da 0) como si apunta al del padre (la base descuenta todo lo
que ya se habia gastado). No hace falta saber cual de los dos es.

GARANTIA
--------
Nunca bloquea ni rompe la sesion: cualquier fallo sale por stderr y termina con 0.

Probar a mano:
    echo '{"hook_event_name":"SubagentStop","agent_type":"qa","agent_id":"x",
           "session_id":"s","transcript_path":"..."}' | python telemetria-subagente.py
"""
import json
import os
import sys
import tempfile
import urllib.error
import urllib.request

PUSHGATEWAY = os.environ.get("PUSHGATEWAY_URL", "http://localhost:9091")
ESTADO_DIR = os.path.join(tempfile.gettempdir(), "claude-telemetria-subagentes")
TALLY = os.path.join(ESTADO_DIR, "tally.json")

# nombres del transcript -> nombres que ya usa la metrica oficial, para que los
# paneles se lean igual en los dos lados
TIPOS = {
    "input_tokens": "input",
    "output_tokens": "output",
    "cache_read_input_tokens": "cacheRead",
    "cache_creation_input_tokens": "cacheCreation",
}


def leer_json(path, defecto):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return defecto


def escribir_json(path, datos):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(datos, f)
    os.replace(tmp, path)  # atomico: dos subagentes en paralelo no se pisan


def acumulado_del_transcript(path):
    """Suma el bloque `usage` de cada mensaje del transcript."""
    total = dict.fromkeys(TIPOS.values(), 0)
    if not path or not os.path.exists(path):
        return total
    with open(path, encoding="utf-8", errors="replace") as f:
        for linea in f:
            try:
                d = json.loads(linea)
            except Exception:
                continue
            msg = d.get("message")
            uso = msg.get("usage") if isinstance(msg, dict) else None
            if not isinstance(uso, dict):
                continue
            for crudo, limpio in TIPOS.items():
                v = uso.get(crudo)
                if isinstance(v, int):
                    total[limpio] += v
    return total


def push(tally):
    """Empuja el tally COMPLETO con una sola clave de agrupacion.

    A proposito no se agrupa por invocacion: asi el Pushgateway guarda una serie
    por agente y tipo, y no crece sin techo con cada corrida de /orquestar.
    """
    lineas = [
        "# HELP claude_subagente_tokens_total Tokens por subagente, medidos desde el hook SubagentStop.",
        "# TYPE claude_subagente_tokens_total counter",
    ]
    for agente, tipos in sorted(tally.items()):
        for tipo, valor in sorted(tipos.items()):
            a = agente.replace("\\", "\\\\").replace('"', '\\"')
            lineas.append(
                'claude_subagente_tokens_total{agente="%s",tipo="%s"} %d' % (a, tipo, valor)
            )
    cuerpo = ("\n".join(lineas) + "\n").encode("utf-8")
    req = urllib.request.Request(
        PUSHGATEWAY + "/metrics/job/claude_subagente",
        data=cuerpo,
        method="PUT",  # PUT reemplaza el grupo entero; POST solo mergea
        headers={"Content-Type": "text/plain; version=0.0.4"},
    )
    urllib.request.urlopen(req, timeout=5).read()


def main():
    try:
        evento = json.load(sys.stdin)
    except Exception as e:
        print("telemetria-subagente: stdin ilegible: %s" % e, file=sys.stderr)
        return

    nombre = evento.get("hook_event_name")
    agente = evento.get("agent_type") or "desconocido"
    # agent_id distingue dos invocaciones simultaneas del mismo agente
    clave = "%s|%s" % (evento.get("session_id", ""), evento.get("agent_id", agente))
    transcript = evento.get("transcript_path")
    base_path = os.path.join(ESTADO_DIR, "base.json")

    if nombre == "SubagentStart":
        bases = leer_json(base_path, {})
        bases[clave] = acumulado_del_transcript(transcript)
        escribir_json(base_path, bases)
        return

    if nombre != "SubagentStop":
        return

    bases = leer_json(base_path, {})
    base = bases.pop(clave, None)
    ahora = acumulado_del_transcript(transcript)

    if base is None:
        # Sin linea base (p. ej. el hook Start no estaba registrado todavia) no se
        # puede calcular la diferencia. Se descarta en vez de inventar un numero:
        # sumar el acumulado entero contaria tokens de otros agentes.
        print(
            "telemetria-subagente: sin linea base para %s, se descarta la medicion" % agente,
            file=sys.stderr,
        )
        return

    delta = {t: max(0, ahora.get(t, 0) - base.get(t, 0)) for t in TIPOS.values()}
    escribir_json(base_path, bases)

    if not any(delta.values()):
        return

    tally = leer_json(TALLY, {})
    acum = tally.setdefault(agente, {})
    for tipo, valor in delta.items():
        acum[tipo] = acum.get(tipo, 0) + valor
    escribir_json(TALLY, tally)

    try:
        push(tally)
    except (urllib.error.URLError, OSError) as e:
        # El Pushgateway apagado no puede romper la sesion. El tally ya quedo en
        # disco, asi que el proximo subagente que termine lo empuja completo.
        print("telemetria-subagente: no se pudo empujar (%s)" % e, file=sys.stderr)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # ningun fallo puede bloquear al agente
        print("telemetria-subagente: %s" % e, file=sys.stderr)
    sys.exit(0)
