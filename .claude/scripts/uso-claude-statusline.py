"""Statusline de Claude Code: muestra el uso de la ventana de 5 h y lo deja en ~/.claude/uso-5h.txt.

flujo.sh lee ese archivo para decidir el respaldo de Codex: DeepSeek solo si Claude pasó el 70 %.
Formato del archivo: "<porcentaje> <epoch>".
"""
import json
import os
import pathlib
import sys
import time

HOME = pathlib.Path.home() / ".claude"

# En Windows stdout sale en cp1252 y las tildes llegan como "�".
sys.stdout.reconfigure(encoding="utf-8")


def buscar_5h(nodo):
    # El campo cambió de nombre entre versiones; se busca cualquier "five_hour" con un porcentaje.
    if isinstance(nodo, dict):
        for clave, valor in nodo.items():
            if "five_hour" in clave and isinstance(valor, dict):
                for k in ("used_percentage", "utilization", "percent_used"):
                    if isinstance(valor.get(k), (int, float)):
                        return float(valor[k])
            hallado = buscar_5h(valor)
            if hallado is not None:
                return hallado
    return None


FRASES = [
    "La IA amplifica lo que ya sabes hacer.",
    "Pregunta bien y la IA responde mejor.",
    "La IA escribe rápido; tú decides qué vale.",
    "Automatiza lo repetitivo, piensa en lo importante.",
    "Cada prompt claro ahorra diez correcciones.",
    "La IA no reemplaza el criterio, lo multiplica.",
]


def frase():
    # Una por hora, para que cambie sin ser distractora.
    return FRASES[int(time.time() // 3600) % len(FRASES)]


def falta_reset(datos):
    # resets_at es un epoch en segundos; se muestra como "2h 05m" o "35m".
    limite = (datos.get("rate_limits") or {}).get("five_hour") or {}
    reset = limite.get("resets_at")
    if not isinstance(reset, (int, float)):
        return ""
    seg = int(reset - time.time())
    if seg <= 0:
        return ""
    h, m = divmod(seg // 60, 60)
    return f" (reinicia en {h}h {m:02d}m)" if h else f" (reinicia en {m}m)"


RITMO = HOME / "tokens-ritmo.json"
INTERVALO = 300  # s entre recálculos
VENTANA = 3      # intervalos en la media móvil


def ritmo(datos):
    """tok/min promedio, recalculado cada 5 min leyendo solo lo nuevo del transcript.

    Entre cortes devuelve el valor guardado sin tocar el transcript. Estado por sesión.
    """
    sid, ruta = datos.get("session_id"), datos.get("transcript_path")
    if not sid or not ruta:
        return ""
    ahora = time.time()
    try:
        estado = json.loads(RITMO.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        estado = {}
    s = estado.get(sid)
    if s and ahora - s["t"] < INTERVALO:
        return s.get("txt", "")
    try:
        tam = os.path.getsize(ruta)
    except OSError:
        return (s or {}).get("txt", "")
    if not s:  # primera vez: se parte desde el final, sin contar el historial previo
        estado[sid] = {"off": tam, "t": ahora, "ult": "", "h": [], "txt": ""}
    else:
        if tam < s["off"]:
            s["off"] = 0
        total, ult = 0, s["ult"]
        with open(ruta, "rb") as f:
            f.seek(s["off"])
            nuevo = f.read()
        # solo líneas completas; el resto se lee en el próximo corte
        fin = nuevo.rfind(b"\n") + 1
        vistos = {}
        for linea in nuevo[:fin].splitlines():
            if b'"usage"' not in linea:
                continue
            try:
                m = json.loads(linea).get("message") or {}
                u = m.get("usage") or {}
            except (ValueError, AttributeError):
                continue
            n = sum(u.get(k) or 0 for k in ("input_tokens", "output_tokens", "cache_creation_input_tokens"))
            # el transcript repite el mensaje por bloque: cuenta el id una sola vez (el último valor)
            vistos[m.get("id") or id(linea)] = n
        # el último id del corte anterior puede reaparecer: no se vuelve a sumar
        vistos.pop(ult, None)
        total = sum(vistos.values())
        if vistos:
            ult = list(vistos)[-1] if isinstance(list(vistos)[-1], str) else ult
        h = (s["h"] + [total / ((ahora - s["t"]) / 60)])[-VENTANA:]
        prom = sum(h) / len(h)
        txt = f" · {prom / 1000:.1f}K tok/min" if prom >= 1000 else (f" · {prom:.0f} tok/min" if prom >= 1 else "")
        estado[sid] = {"off": s["off"] + fin, "t": ahora, "ult": ult, "h": h, "txt": txt}
    for k in [k for k, v in estado.items() if ahora - v["t"] > 86400]:
        del estado[k]
    RITMO.write_text(json.dumps(estado), encoding="utf-8")
    return estado[sid]["txt"]


try:
    datos = json.loads(sys.stdin.buffer.read().decode("utf-8") or "{}")
except ValueError:
    datos = {}

(HOME / "uso-5h-raw.json").write_text(json.dumps(datos.get("rate_limits"), indent=1), encoding="utf-8")
pct = buscar_5h(datos)
modelo = (datos.get("model") or {}).get("display_name", "")
if pct is None:
    print(f"{modelo} | 5h: ? | {frase()}{ritmo(datos)}")
else:
    (HOME / "uso-5h.txt").write_text(f"{pct:.0f} {int(time.time())}", encoding="utf-8")
    print(f"{modelo} | 5h: {pct:.0f}%{falta_reset(datos)}" + (" | respaldo: DeepSeek" if pct >= 70 else "") + f" | {frase()}{ritmo(datos)}")
