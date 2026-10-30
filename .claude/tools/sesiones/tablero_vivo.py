#!/usr/bin/env python3
"""Tablero en vivo de las sesiones activas de Claude en AcmeOrg.

Uso:  python .claude/tools/sesiones/tablero_vivo.py [--puerto 5199]   ->  http://127.0.0.1:5199

Lee los puertos, la RAM y los logs de sesión (`~/.claude/projects/*/*.jsonl` y sus `subagents/`).
No escribe nada en los repos ni en las sesiones; los comentarios van a `~/.claude/tablero-notas.json`.
Escucha solo en 127.0.0.1.
"""
import argparse
from datetime import datetime
import ctypes
import json
import os
import re
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

try:  # marca de agua opcional de AcmeOrg
    LLAMA = __import__("base64").b64encode((Path(__file__).parent / "marca-azul.png").read_bytes()).decode()
except OSError:
    LLAMA = ""
PROYECTOS = Path.home() / ".claude" / "projects"
NOTAS = Path.home() / ".claude" / "tablero-notas.json"
ARCHIVADOS = Path.home() / ".claude" / "tablero-archivados.json"  # solo oculta: no borra ninguna sesión
PUERTOS = {"api-core": 5182, "api-contracts": 5119, "web-app": 5173, "servicio-mensajeria": 3000}
PROCESOS = ("claude", "node", "dotnet", "codex", "python", "docker", "agy")
REFRESCO_SEG = 3
ACTIVA_MAX_SEG = 1800  # una sesión sin movimiento en 30 min deja de mostrarse
ESTADO = {"archivados": [], "actualizado": 0.0, "sesiones": [], "puertos": [], "ram": {}, "coders": []}
LOCK = threading.Lock()


def puerto_abierto(puerto):
    try:
        with socket.create_connection(("127.0.0.1", puerto), timeout=0.4):
            return True
    except OSError:
        return False


def ram():
    class MEM(ctypes.Structure):
        _fields_ = [("l", ctypes.c_ulong), ("carga", ctypes.c_ulong), ("total", ctypes.c_ulonglong),
                    ("libre", ctypes.c_ulonglong), ("a", ctypes.c_ulonglong), ("b", ctypes.c_ulonglong),
                    ("c", ctypes.c_ulonglong), ("d", ctypes.c_ulonglong), ("e", ctypes.c_ulonglong)]
    m = MEM()
    m.l = ctypes.sizeof(MEM)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(m))
    grupos = {}
    try:
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "Get-Process " + ",".join(PROCESOS) + " -EA SilentlyContinue | Select Name,WorkingSet64 | ConvertTo-Json -Compress"],
                           capture_output=True, text=True, timeout=15)
        datos = json.loads(r.stdout or "[]")
        for p in datos if isinstance(datos, list) else [datos]:
            g = grupos.setdefault(p["Name"], [0, 0])
            g[0] += 1
            g[1] += p["WorkingSet64"]
    except Exception:
        pass
    return {"total_gb": round(m.total / 2**30, 1), "usada_pct": m.carga,
            "procesos": sorted(({"nombre": k, "n": v[0], "mb": round(v[1] / 2**20)} for k, v in grupos.items()),
                               key=lambda x: -x["mb"])}


def texto_de(c):
    if isinstance(c, str):
        return c
    if isinstance(c, list):
        return " ".join(p.get("text", "") for p in c if isinstance(p, dict) and p.get("type") == "text")
    return ""


CACHE_LECTURA = {}


def leer_entradas(archivo, bytes_=300_000):
    try:
        st = os.stat(archivo)
        clave = (str(archivo), bytes_)
        hit = CACHE_LECTURA.get(clave)
        if hit and hit[0] == (st.st_mtime_ns, st.st_size):
            return hit[1]
        salida = _leer_entradas(archivo, bytes_)
        CACHE_LECTURA[clave] = ((st.st_mtime_ns, st.st_size), salida)
        return salida
    except OSError:
        return []


def _leer_entradas(archivo, bytes_):
    try:
        with open(archivo, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - bytes_))
            lineas = f.read().decode("utf-8", errors="replace").splitlines()
    except OSError:
        return []
    salida = []
    for linea in lineas:
        try:
            salida.append(json.loads(linea))
        except ValueError:
            pass
    return salida


def relevantes(entradas):
    return [e for e in entradas if e.get("type") in ("user", "assistant") and not e.get("isMeta") and not e.get("isSidechain")]


MARCA = re.compile(r"\bPREGUNTA\b")  # convención: todo mensaje que espera respuesta termina con la palabra PREGUNTA
PIDE = re.compile(r"(dime|d[ií]game|confirma|autoriza|av[ií]same|elige|decide|apru[eé]ba|necesito que|si respondes|espero tu)", re.I)


def espera_de(entradas, edad=0):
    rel = relevantes(entradas)
    if not rel or rel[-1]["type"] == "user":
        return None
    partes = rel[-1].get("message", {}).get("content", [])
    partes = partes if isinstance(partes, list) else []
    for p in partes:
        if p.get("type") == "tool_use" and p.get("name") == "AskUserQuestion":
            qs = p.get("input", {}).get("questions", [])
            return {"tipo": "pregunta", "texto": " / ".join(q.get("question", "") for q in qs)[:400],
                    "opciones": [o.get("label", "") for q in qs[:1] for o in q.get("options", [])][:4]}
    if any(p.get("type") == "tool_use" for p in partes):
        nombres = {p.get("name") for p in partes if p.get("type") == "tool_use"}
        # Lo que termina al instante (Edit, Read…) y sigue sin resultado es un permiso; Bash puede ser un build largo;
        # agentes, workflows y esperas trabajan en segundo plano y nunca cuentan como bloqueo.
        largas = {"Agent", "Task", "Workflow", "Monitor", "ScheduleWakeup", "TaskOutput"}
        limite = 10**9 if nombres & largas else 300 if "Bash" in nombres else 20
        if edad > limite:
            return {"tipo": "permiso", "texto": "Sin respuesta de " + ", ".join(sorted(str(n) for n in nombres)) + ": " + next((str((p.get("input") or {}).get("command") or (p.get("input") or {}).get("file_path") or "")[:150] for p in partes if p.get("type") == "tool_use"), "") + " (permiso o comando largo)", "opciones": []}
        return None
    texto = " ".join(p.get("text", "") for p in partes if p.get("type") == "text").strip()
    ultimo = next((b for b in reversed(re.split(r"\n\s*\n", texto)) if b.strip()), "")
    pide = bool(MARCA.search(texto[-200:])) or "?" in ultimo or bool(PIDE.search(ultimo))  # te pide decidir algo: el cierre del mensaje trae la pregunta
    ruta = re.findall(r"\.claude/traspasos/[\w.\-]+\.md", texto)
    traspaso = {"ruta": ruta[-1]} if ruta else {"ruta": ""} if re.search(r"traspas", texto, re.I) else None
    return {"tipo": "pregunta" if pide else "terminó", "texto": texto[-300:], "opciones": [], "traspaso": traspaso}


def titulo_de(entradas, archivo):
    for e in reversed(entradas):
        if e.get("type") == "ai-title" and e.get("aiTitle"):
            return e["aiTitle"]
    for e in leer_entradas(archivo, 150_000)[:80]:
        if e.get("type") == "user" and not e.get("isMeta"):
            t = texto_de(e.get("message", {}).get("content", "")).strip()
            if t and not t.startswith("<"):
                return t.replace("\n", " ")[:80]
    return ""


def coders_de(dir_sesion, sid):
    carpeta = dir_sesion / "subagents"
    salida = []
    for meta in carpeta.glob("*.meta.json") if carpeta.exists() else []:
        log = meta.with_name(meta.name.replace(".meta.json", ".jsonl"))
        try:
            edad = time.time() - log.stat().st_mtime
            if edad > 600:
                continue
            m = json.loads(meta.read_text(encoding="utf-8"))
            salida.append({"sesion": sid, "tipo": m.get("agentType", "agente"), "descripcion": m.get("description", ""),
                           "activo": edad < 45, "hace_seg": int(edad)})
        except (OSError, ValueError):
            pass
    return salida


RAIZ = Path(__file__).resolve().parents[3]


def requisito_de(entradas):
    """El último REQ-#### que mencionó la sesión, con el nombre de su archivo en requisitos/."""
    for e in reversed(entradas):
        c = e.get("message", {}).get("content", "") if e.get("type") in ("user", "assistant") else ""
        ids = re.findall(r"REQ-\d{4}", c if isinstance(c, str) else json.dumps(c, ensure_ascii=False))
        if ids:
            f = next((RAIZ / "requisitos").glob(f"{ids[-1]}-*.md"), None)
            return f"{ids[-1]} · {f.stem[len(ids[-1]) + 1:].replace('-', ' ')}" if f else ids[-1]
    return ""


USO = {}  # archivo -> {"pos": bytes leídos, "ids": {message.id: usage}, "modelo": str}


def uso_de(archivo):
    """Tokens de la sesión, leyendo solo lo nuevo del jsonl; cada message.id se repite en varias líneas."""
    u = USO.setdefault(str(archivo), {"pos": 0, "ids": {}, "modelo": "", "ctx": 0})
    try:
        with open(archivo, "rb") as f:
            f.seek(u["pos"])
            datos = f.read()
    except OSError:
        return u
    corte = datos.rfind(b"\n") + 1  # una línea a medio escribir se lee en el siguiente refresco
    for linea in datos[:corte].decode("utf-8", errors="replace").splitlines():
        if '"usage"' not in linea:
            continue
        try:
            m = json.loads(linea).get("message") or {}
        except ValueError:
            continue
        if m.get("usage") and m.get("id"):
            u["ids"][m["id"]] = m["usage"]
            u["modelo"] = m.get("model") or u["modelo"]
            x = m["usage"]
            u["ctx"] = (x.get("input_tokens") or 0) + (x.get("cache_read_input_tokens") or 0) + (x.get("cache_creation_input_tokens") or 0)
    u["pos"] += corte
    return u


def resumen_uso(archivo):
    u = uso_de(archivo)
    nuevos = sum((x.get("input_tokens") or 0) + (x.get("output_tokens") or 0) + (x.get("cache_creation_input_tokens") or 0)
                 for x in u["ids"].values())
    return {"modelo": u["modelo"].replace("claude-", ""), "tokens": nuevos, "contexto": u["ctx"]}


def haciendo_de(entradas):
    rel = relevantes(entradas)
    if not rel or rel[-1]["type"] != "assistant":
        return "pensando" if rel else ""
    for p in reversed(rel[-1].get("message", {}).get("content", []) or []):
        if isinstance(p, dict) and p.get("type") == "tool_use":
            i = p.get("input") or {}
            return f'{p.get("name")} {str(i.get("command") or i.get("file_path") or i.get("pattern") or i.get("description") or "")[:110]}'.strip()
    return "escribiendo la respuesta"


def creada_de(archivo):
    try:
        with open(archivo, "rb") as f:
            for linea in f.read(60_000).decode("utf-8", errors="replace").splitlines():
                try:
                    ts = json.loads(linea).get("timestamp")
                except ValueError:
                    continue
                if ts:
                    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
    except (OSError, ValueError):
        pass
    return archivo.stat().st_ctime


def resumen_sesion(archivo):
    entradas = leer_entradas(archivo)
    rel = relevantes(entradas)
    edad = time.time() - archivo.stat().st_mtime
    espera = espera_de(entradas, edad)
    trabajando = bool(rel) and (rel[-1]["type"] == "user" or espera is None) and edad < 900
    bloqueada = bool(espera) and espera["tipo"] in ("pregunta", "permiso")
    estado = "procesando" if trabajando else "bloqueado" if bloqueada else "esperando" if espera else "reposo"
    prompt = next((texto_de(e["message"]["content"]).strip().replace("\n", " ")[:160] for e in reversed(rel)
                   if e["type"] == "user" and texto_de(e["message"]["content"]).strip()
                   and not texto_de(e["message"]["content"]).strip().startswith("<")), "")
    sid = archivo.stem
    return {"id": sid[:8], "cwd": next((e["cwd"] for e in reversed(entradas) if e.get("cwd")), ""),
            "titulo": titulo_de(entradas, archivo), "ultimo_pedido": prompt, "estado": estado,
            "hace_seg": int(edad), "creada": creada_de(archivo), "haciendo": haciendo_de(entradas), "uso": resumen_uso(archivo), "requisito": requisito_de(entradas), "espera": espera, "coders": coders_de(archivo.with_suffix(""), sid[:8])}


def lista_sesiones():
    limite = time.time() - ACTIVA_MAX_SEG
    archivos = sorted((a for a in PROYECTOS.glob("*/*.jsonl") if a.stat().st_mtime > limite),
                      key=lambda a: a.stat().st_mtime, reverse=True)
    return [s for s in (resumen_sesion(a) for a in archivos[:30]) if s]


def transcripcion(sid, n=120):
    archivo = next(iter(PROYECTOS.glob(f"*/{sid}*.jsonl")), None)
    if not archivo:
        return []
    salida = []
    for e in relevantes(leer_entradas(archivo, 400_000))[-n:]:
        c = e.get("message", {}).get("content", "")
        if e["type"] == "user":
            if isinstance(c, list):
                for p in c:
                    if p.get("type") == "tool_result":
                        r = p.get("content", "")
                        salida.append({"rol": "resultado", "texto": (texto_de(r) if isinstance(r, list) else str(r))[:300]})
                t = texto_de(c).strip()
                if t:
                    salida.append({"rol": "tú", "texto": t[:2000]})
            elif c.strip() and not c.strip().startswith("<"):
                salida.append({"rol": "tú", "texto": c.strip()[:2000]})
        else:
            for p in c if isinstance(c, list) else []:
                if p.get("type") == "text" and p.get("text", "").strip():
                    salida.append({"rol": "claude", "texto": p["text"].strip()[:4000]})
                elif p.get("type") == "tool_use":
                    entrada = p.get("input", {})
                    detalle = entrada.get("command") or entrada.get("file_path") or entrada.get("pattern") or entrada.get("description") or ""
                    salida.append({"rol": "herramienta", "texto": f'{p.get("name")} {str(detalle)[:200]}'})
    return salida


def notas():
    try:
        return json.loads(NOTAS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


FRASES = ["La IA amplifica lo que ya sabes hacer.", "Pregunta bien y la IA responde mejor.",
          "La IA escribe rápido; tú decides qué vale.", "Automatiza lo repetitivo, piensa en lo importante.",
          "Cada prompt claro ahorra diez correcciones.", "La IA no reemplaza el criterio, lo multiplica."]


def ventana(usado, reinicia, nombre):
    seg = int((reinicia or 0) - time.time())
    falta = "" if seg <= 0 else f"{seg // 86400}d {seg % 86400 // 3600}h" if seg >= 86400 else f"{seg // 3600}h {seg % 3600 // 60:02d}m"
    return {"nombre": nombre, "usado": round(usado), "falta": falta}


def cuotas():
    salida = {"claude": [], "codex": [], "frase": FRASES[int(time.time() // 3600) % len(FRASES)]}
    try:  # lo deja la línea de estado de Claude Code en cada refresco de una sesión
        d = json.loads((Path.home() / ".claude" / "uso-5h-raw.json").read_text(encoding="utf-8")) or {}
        for clave, nombre in (("five_hour", "5 h"), ("seven_day", "semana")):
            v = d.get(clave) or {}
            if isinstance(v.get("used_percentage"), (int, float)):
                salida["claude"].append(ventana(v["used_percentage"], v.get("resets_at"), nombre))
    except (OSError, ValueError):
        pass
    try:  # último evento token_count de la sesión de Codex más reciente
        raiz = Path.home() / ".codex" / "sessions"
        for f in sorted(raiz.rglob("rollout-*.jsonl"), key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
            ult = None
            for e in leer_entradas(f, 400_000):
                rl = (e.get("payload") or {}).get("rate_limits")
                if rl and rl.get("primary"):
                    ult = rl
            if ult:
                for clave in ("primary", "secondary"):
                    v = ult.get(clave)
                    if v:
                        m = v.get("window_minutes") or 0
                        nombre = "5 h" if m <= 300 else "semana" if m >= 10000 else f"{m // 60} h"
                        salida["codex"].append(ventana(v.get("used_percent", 0), v.get("resets_at"), nombre))
                break
    except OSError:
        pass
    return salida


TRASPASOS = {}  # id de sesión -> texto de estado del traspaso en curso
PEDIDO_TRASPASO = (
    "Escribe tu traspaso en .claude/traspasos/<slug-corto>.md (en la raiz de AcmeOrg) con las secciones: "
    "Hecho, Decisiones, Pendiente (con dueno) y Trampas, maximo 25 lineas. No edites TASKS.md, INDEX.md ni "
    "archivos compartidos de la raiz. Responde solo la ruta relativa del archivo."
)


def traspasar(sid, archivo):
    """Pide a la sesión su traspaso y abre una terminal nueva que lo lee y continúa."""
    try:
        carpeta = RAIZ / ".claude" / "traspasos"
        carpeta.mkdir(exist_ok=True)
        antes = time.time() - 1
        TRASPASOS[sid] = "⏳ la sesión está escribiendo su traspaso…"
        entradas = leer_entradas(archivo)
        hecho = ((espera_de(entradas, 999) or {}).get("traspaso") or {}).get("ruta", "")
        if hecho and (RAIZ / hecho).exists():
            subprocess.Popen(f'start "" cmd /k claude "lee {hecho} y continua con los pendientes"', cwd=str(RAIZ), shell=True)
            TRASPASOS[sid] = f"✔ terminal nueva abierta con {hecho}"
            return
        cwd = next((e["cwd"] for e in reversed(entradas) if e.get("cwd")), str(RAIZ))
        pedido = subprocess.Popen(["claude", "--resume", archivo.stem, "-p"], cwd=cwd, stdin=subprocess.PIPE,
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=(os.name == "nt"))
        try:
            pedido.communicate(PEDIDO_TRASPASO.encode("utf-8"), timeout=300)
        except subprocess.TimeoutExpired:
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(pedido.pid)], capture_output=True)  # mata también al claude hijo
            TRASPASOS[sid] = "✖ la sesión tardó más de 5 min en escribir el traspaso"
            return
        nuevos = sorted((f for f in carpeta.glob("*.md") if f.stat().st_mtime >= antes), key=lambda f: f.stat().st_mtime)
        if not nuevos:
            TRASPASOS[sid] = "✖ la sesión no dejó ningún traspaso"
            return
        ruta = f".claude/traspasos/{nuevos[-1].name}"
        subprocess.Popen(f'start "" cmd /k claude "lee {ruta} y continua con los pendientes"', cwd=str(RAIZ), shell=True)
        TRASPASOS[sid] = f"✔ traspaso en {ruta}; terminal nueva abierta"
    except Exception as ex:  # cualquier fallo debe sacar el "⏳", si no el botón queda pegado
        TRASPASOS[sid] = f"✖ no se pudo traspasar ({type(ex).__name__})"


def carpetas():
    base = [str(RAIZ)]
    for d in sorted((RAIZ / ".worktrees").glob("*")) if (RAIZ / ".worktrees").exists() else []:
        base.append(str(d))
    return base


def nueva_sesion(cwd, prompt):
    destino = Path(cwd).resolve()
    if destino != RAIZ and RAIZ not in destino.parents:
        raise ValueError("carpeta fuera de AcmeOrg")
    comando = f"Set-Location -LiteralPath '{str(destino).replace(chr(39), chr(39) * 2)}'; claude"
    if prompt.strip():
        carpeta = Path.home() / ".claude" / "tablero-prompts"
        carpeta.mkdir(exist_ok=True)
        f = carpeta / f"{int(time.time())}.txt"
        f.write_text(prompt, encoding="utf-8")  # por archivo: las tildes no sobreviven a un argumento de cmd
        comando += f" (Get-Content -Raw -Encoding utf8 -LiteralPath '{f}')"
    subprocess.Popen(["cmd", "/c", "start", "", "powershell", "-NoExit", "-Command", comando])


def archivados():
    try:
        return json.loads(ARCHIVADOS.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def archivar(sid, restaurar):
    datos = archivados()
    if restaurar:
        datos.pop(sid, None)
    else:
        with LOCK:
            s = next((x for x in ESTADO["sesiones"] if x["id"] == sid), None)
        datos[sid] = {"id": sid, "titulo": (s or {}).get("titulo") or sid, "cwd": (s or {}).get("cwd", ""),
                      "cuando": time.time()}
    ARCHIVADOS.write_text(json.dumps(datos, ensure_ascii=False), encoding="utf-8")
    with LOCK:  # se refleja ya, sin esperar al siguiente refresco
        ESTADO["sesiones"] = [x for x in ESTADO["sesiones"] if x["id"] not in datos]
        ESTADO["coders"] = [c for c in ESTADO["coders"] if c["sesion"] not in datos]
        ESTADO["archivados"] = sorted(datos.values(), key=lambda a: -a["cuando"])
    publicar(True)


COND = threading.Condition()
VERSION = {"n": 0, "firma": "", "t": 0.0}


def publicar(forzar=False):
    """Avisa a los navegadores conectados solo si algo cambió (o cada 5 s para los "hace X")."""
    with LOCK:
        copia = {k: v for k, v in ESTADO.items() if k not in ("actualizado",)}
        copia["sesiones"] = [{k: v for k, v in x.items() if k != "hace_seg"} for x in copia["sesiones"]]
        firma = json.dumps(copia, sort_keys=True, default=str)
    if forzar or firma != VERSION["firma"] or time.time() - VERSION["t"] > 5:
        with COND:
            VERSION.update(n=VERSION["n"] + 1, firma=firma, t=time.time())
            COND.notify_all()


def rapido():
    arch = archivados()
    sesiones = [x for x in lista_sesiones() if x["id"] not in arch]
    n = notas()
    for x in sesiones:
        x["nota"] = n.get(x["id"], "")
    with LOCK:
        ESTADO.update(actualizado=time.time(), sesiones=sesiones, coders=[c for x in sesiones for c in x["coders"]],
                      traspasos=dict(TRASPASOS), carpetas=carpetas(),
                      archivados=sorted(arch.values(), key=lambda a: -a["cuando"]))
    publicar()


def lento():
    memoria, c = ram(), cuotas()
    puertos = [{"nombre": k, "puerto": p, "arriba": puerto_abierto(p)} for k, p in PUERTOS.items()]
    with LOCK:
        ESTADO.update(ram=memoria, cuotas=c, puertos=puertos)
    publicar()


def refrescar():
    lento()
    rapido()


def bucle():
    while True:
        try:
            rapido()
        except Exception as ex:
            print("refresco falló:", ex)
        time.sleep(0.25)


def bucle_lento():
    while True:
        time.sleep(10)
        try:
            lento()
        except Exception as ex:
            print("refresco lento falló:", ex)


PAGINA = r"""<!doctype html><html lang="es"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Sesiones activas</title>
<style>
:root{--bg:#14161a;--card:#1c1f25;--ink:#e8eaee;--mut:#98a2b3;--bd:#2b3038;--ok:#4cc38a;--warn:#f0a35e;--hot:#f4786d;--acc:#8ea2ff;--code:#12141a}  /* la página es oscura siempre (html{color-scheme:dark}) */
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,sans-serif;padding:16px}
h1{font-size:18px;margin:0 0 4px}h2{font-size:13px;text-transform:uppercase;letter-spacing:.05em;color:var(--mut);margin:20px 0 8px}
.top{display:flex;gap:12px;flex-wrap:wrap;align-items:center;justify-content:space-between}.pills{display:flex;gap:6px;flex-wrap:wrap}
.pill{display:inline-flex;gap:6px;align-items:center;border:1px solid var(--bd);border-radius:99px;padding:2px 10px;background:var(--card);font-size:12px}
.dot{width:8px;height:8px;border-radius:50%;background:var(--mut)}.up .dot{background:var(--ok)}.down .dot{background:var(--hot)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:10px}
.card{background:var(--card);border:1px solid var(--bd);border-radius:10px;padding:10px 12px}.card.clic{cursor:pointer}
.card{height:300px;overflow:hidden;box-sizing:border-box}
:root,:root *{--bg:#0c0c0c;--card:#0c0c0c;--ink:#cccccc;--mut:#8c8c8c;--bd:#3a3a3a;--ok:#13a10e;--warn:#c19c00;--hot:#e74856;--acc:#61d6d6;--code:#0c0c0c}
html,body,button,input,textarea{font-family:"Cascadia Mono",Consolas,"Courier New",monospace!important;font-size:16px!important;background:#0c0c0c;color:#cccccc}
h1{font-size:16px!important}.m,.tag,.pill,.op,.arch,.l{font-size:14px!important}
.card .n,.card .m,.card .q{display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:1;overflow:hidden}
.card{display:flex;flex-direction:column;position:relative}
.arc{padding:4px 12px!important;font-size:13px!important;background:#0c0c0c;color:var(--mut);border:1px solid var(--bd);border-radius:6px;padding:1px 8px;cursor:pointer}
.card>.n{display:flex!important;gap:10px;align-items:baseline;justify-content:space-between}.card>.n .tit{min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.card>.n .tag{margin-left:auto;flex:0 0 auto;white-space:nowrap}
.card .pie{margin-top:auto;display:flex;gap:8px;justify-content:flex-end;padding-top:6px}.fila{padding:3px 0;display:block!important;-webkit-line-clamp:unset!important}
details summary{cursor:pointer}
*{scrollbar-width:thin;scrollbar-color:#1c1c1c #050505}
::-webkit-scrollbar{width:8px;height:8px}::-webkit-scrollbar-track{background:#050505}::-webkit-scrollbar-thumb{background:#1c1c1c;border-radius:4px}::-webkit-scrollbar-thumb:hover{background:#2e2e2e}
html{color-scheme:dark}
*:focus-visible{outline:2px solid var(--acc);outline-offset:-2px}
button:hover{background:#1d1d1d!important}.card.clic:hover{border-color:var(--mut)}
body{position:relative;min-height:100vh}
body::before{content:"";position:fixed;inset:0;z-index:0;pointer-events:none;opacity:.10;
 background:url(data:image/png;base64,__LLAMA__) no-repeat right 4vw bottom 4vh/min(60vh,520px)}
body>*{position:relative;z-index:1}#panel{position:fixed}
.card{background:rgba(12,12,12,.86)}
.marca{color:var(--acc);font-size:13px!important}
.tbl{margin:6px 0;overflow-x:auto;white-space:pre!important;line-height:1.25;color:#cccccc}
#nueva{display:none;border:1px solid var(--bd);padding:10px;margin:8px 0;background:rgba(12,12,12,.92)}#nueva.abierta{display:block}
select,option,input{background:#0c0c0c;color:#cccccc;font:inherit}select:focus,textarea:focus,input:focus{outline:1px solid var(--acc)}
#nueva select,#nueva textarea{width:100%;margin:4px 0 8px;border:1px solid var(--bd);border-radius:6px;padding:5px 8px}
#nueva textarea{height:90px;resize:vertical}
@media(max-width:700px){body{padding:10px}.grid{grid-template-columns:1fr}.card{height:auto;min-height:260px}.top{align-items:flex-start}
 html,body,button,input,textarea{font-size:14px!important}.m,.tag,.pill,.op,.l{font-size:12.5px!important}.htop{grid-template-columns:1fr}
 #panel{width:100%;border-left:none}.fila{overflow-wrap:anywhere}}
.card .q{display:block!important;overflow-y:auto;flex:1 1 0;min-height:48px;font-size:14px!important;white-space:pre-wrap}
.card .resp{flex:0 0 auto}.card .tras{margin-top:4px;align-self:flex-start;font-size:13px!important;background:#0c0c0c;color:var(--acc);border:1px solid var(--bd);border-radius:6px;padding:2px 8px;cursor:pointer}
.card.preg{border-left:4px solid var(--hot)}
#ptras .tras:disabled{opacity:.4;cursor:not-allowed;border-color:var(--bd)}#ptras .tras{font-size:13px!important;background:#0c0c0c;color:var(--acc);border:1px solid var(--acc);border-radius:6px;padding:4px 10px;cursor:pointer}
.n{font-weight:600;word-break:break-word}.m{color:var(--mut);font-size:12px}.tag{font-size:11px;padding:1px 7px;border-radius:6px;border:1px solid var(--bd)}
.procesando{color:var(--ok);border-color:var(--ok)}.esperando{color:var(--warn);border-color:var(--warn)}.bloqueado{color:var(--hot);border-color:var(--hot);font-weight:700}.reposo{color:var(--mut)}
.pulso{animation:p 1.2s infinite}@keyframes p{50%{opacity:.35}}@media (prefers-reduced-motion:reduce){.pulso{animation:none}}
.arch{font-size:11px;color:var(--mut);margin-top:4px;word-break:break-all}.q{margin-top:6px;white-space:pre-wrap}
.resp{display:block;width:100%;box-sizing:border-box;margin-top:6px;padding:5px 8px;background:transparent;color:inherit;border:1px solid var(--bd);border-radius:6px;font:inherit}
.op{display:inline-block;margin:4px 4px 0 0;padding:1px 8px;border:1px solid var(--bd);border-radius:6px;font-size:12px}
.bar{height:6px;border-radius:3px;background:var(--bd);overflow:hidden;width:140px;margin:4px 0}.bar i{display:block;height:100%;background:var(--acc)}
.htop{display:grid;grid-template-columns:1fr 1fr;gap:24px;border-top:1px dashed var(--bd);border-bottom:1px dashed var(--bd);padding:8px 0}.htop pre{margin:0;font:inherit;font-size:14px!important;white-space:pre-wrap;overflow:hidden}.dim{color:var(--mut)}.okc{color:var(--ok)}.warnc{color:var(--warn)}@media(max-width:900px){.htop{grid-template-columns:1fr}}
.hot{color:var(--hot)}
#panel{position:fixed;top:0;right:0;bottom:0;width:min(max(760px,62vw),100%);background:var(--card);border-left:1px solid var(--bd);padding:12px;display:none;flex-direction:column;gap:8px;z-index:9}
#panel.ancho{width:min(96vw,1500px)}#panel.abierto{display:flex}#log{flex:1;overflow:auto;background:var(--code);border-radius:8px;padding:10px;font-size:13px;line-height:1.5}
.l{margin-bottom:8px;white-space:pre-wrap;word-break:break-word}.l b{color:var(--acc)}.l.herramienta,.l.resultado{color:var(--mut)}.l.tú b{color:var(--warn)}
textarea{width:100%;min-height:60px;background:var(--code);color:var(--ink);border:1px solid var(--bd);border-radius:8px;padding:8px;font:inherit}
button{background:var(--card);color:var(--ink);border:1px solid var(--bd);border-radius:8px;padding:4px 12px;cursor:pointer}
</style>
<div class="top"><div><h1>Sesiones activas · AcmeOrg</h1><div class="marca">Un producto de AcmeOrg</div><div class="m" id="hora">cargando…</div></div><div class="pills" id="puertos"></div></div>
<div class="m" id="cuotas"></div>
<h2>Máquina</h2><div class="htop"><pre id="ram"></pre><pre id="coders"></pre></div>
<h2>Te esperan <span class="m" id="nespera"></span></h2><div class="grid" id="espera"></div>
<h2 style="display:flex;align-items:center;gap:12px">Sesiones <span class="m" id="cuenta"></span> <button style="margin-left:auto" id="bnueva" onclick="$('nueva').classList.toggle('abierta')">+ Nueva sesión</button></h2>
<div id="nueva"><div class="m">Carpeta de trabajo</div><select id="ncwd"></select>
<div class="m">Primer mensaje (opcional)</div><textarea id="nprompt" placeholder="Qué quieres que haga la sesión nueva"></textarea>
<button onclick="crea()">Abrir sesión en una terminal nueva</button> <span class="m" id="nest"></span></div>
<div class="grid" id="sesiones"></div>
<details id="archivo"><summary><h2 style="display:inline">Archivados <span class="m" id="narch"></span></h2></summary><div id="archivados"></div></details>
<aside id="panel"><div style="display:flex;justify-content:space-between;gap:8px"><div><div class="n" id="pt"></div><div class="m" id="pc"></div></div><span><button onclick="ancho()" title="Ampliar o reducir el panel">⤢ Ampliar</button> <button onclick="cerrar()">Cerrar</button></span></div>
<div id="ptras"></div><div id="popc"></div><div id="log"></div><div class="m">Escribe y pulsa Enter para enviar a esta sesión (Shift+Enter = salto de línea)</div><textarea id="nota"></textarea></aside>
<script>
const _f=window.fetch;window.fetch=(u,o={})=>_f(u,{...o,headers:{...(o.headers||{}),"X-Tablero":"1"}});
const $=id=>document.getElementById(id);
const esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));
const hace=s=>s<120?s+" s":s<7200?Math.round(s/60)+" min":s<172800?Math.round(s/3600)+" h":Math.round(s/86400)+" d";
const k=n=>n>=1e6?(n/1e6).toFixed(1)+"M":n>=1e3?Math.round(n/1e3)+"k":String(n);
const creo=t=>{const d=new Date(t*1000),h=d.toLocaleTimeString("es-PE",{hour:"2-digit",minute:"2-digit"});return `creada ${d.toDateString()===new Date().toDateString()?"hoy":d.toLocaleDateString("es-PE",{day:"2-digit",month:"2-digit"})} ${h} (hace ${hace(Math.round(Date.now()/1000-t))})`};
let abierta=null,estado={sesiones:[]};
const sesion=(s,extra="")=>`<div class="card clic ${s.estado==="bloqueado"?"preg":""}" onclick="abrir('${s.id}')">
<div class="n"><span class="tit">${esc(s.titulo||s.id)}</span><span class="tag ${s.estado} ${s.estado==="procesando"?"pulso":""}">${s.estado}${s.estado==="bloqueado"&&s.espera?" · "+(s.espera.tipo==="permiso"?"permiso":"te espera"):""}</span></div>
<div class="m">${esc(s.id)} · ${esc(s.cwd.split(/[\\/]/).slice(-2).join("/"))} · hace ${hace(s.hace_seg)} · ${creo(s.creada)}${s.coders.some(c=>c.activo)?` · ${s.coders.filter(c=>c.activo).length} coder(s) activo(s)`:""}</div>
${s.requisito?`<div class="m">📌 ${esc(s.requisito)}</div>`:""}${s.estado==="procesando"&&s.haciendo?`<div class="m">⏺ ${esc(s.haciendo)} · hace ${hace(s.hace_seg)}</div>`:""}<div class="m">🤖 ${esc(s.uso.modelo||"?")} · ${k(s.uso.tokens)} tokens gastados · contexto ${k(s.uso.contexto)}</div><div class="m">▶ ${esc(s.ultimo_pedido)}</div>${s.nota?`<div class="m">📝 ${esc(s.nota)}</div>`:""}${extra}<div class="pie"><button class="arc" title="Archivar (se puede restaurar)" onclick="event.stopPropagation();archiva('${s.id}',false)">Archivar</button></div></div>`;
function pinta(e){
 estado=e;const edad=Math.round(Date.now()/1000-e.actualizado);
 $("hora").innerHTML=`datos de hace ${edad} s${edad>15?' <span class="hot">· el servidor no refresca</span>':""}`;
 if(!$("ncwd").options.length||$("ncwd").dataset.n!=String((e.carpetas||[]).length)){$("ncwd").dataset.n=(e.carpetas||[]).length;$("ncwd").innerHTML=(e.carpetas||[]).map(c=>`<option>${esc(c)}</option>`).join("")}
 const q=e.cuotas||{claude:[],codex:[]},fq=(n,l)=>l.length?`<b>${n}</b> `+l.map(v=>`${v.nombre}: queda ${100-v.usado}%${v.falta?` (reinicia en ${v.falta})`:""}`).join(" · "):`<b>${n}</b> sin dato`;
 $("cuotas").innerHTML=fq("Claude",q.claude)+" &nbsp;|&nbsp; "+fq("Codex",q.codex)+" &nbsp;|&nbsp; "+esc(q.frase||"");
 $("puertos").innerHTML=e.puertos.map(p=>`<span class="pill ${p.arriba?"up":"down"}"><span class="dot"></span>${esc(p.nombre)} :${p.puerto}</span>`).join("");
 const barra=(pct,n=24)=>{const l=Math.round(pct/100*n);return `<span class="${pct>=85?"hot":pct>=65?"warnc":"okc"}">${"█".repeat(l)}</span><span class="dim">${"░".repeat(n-l)}</span>`};
 const r=e.ram,maxmb=Math.max(1,...(r.procesos||[]).map(p=>p.mb));
 $("ram").innerHTML=`<b>RAM</b>  [${barra(r.usada_pct)}] ${r.usada_pct}%  de ${r.total_gb} GB\n`+(r.procesos||[]).map(p=>` ${esc(p.nombre).padEnd(8)} ×${String(p.n).padEnd(3)} ${String(p.mb).padStart(5)} MB <span class="dim">${"▪".repeat(Math.max(1,Math.round(p.mb/maxmb*14)))}</span>`).join("\n");
 $("coders").innerHTML=`<b>SUBAGENTES</b> <span class="dim">(últimos 10 min)</span>\n`+(e.coders.length?e.coders.map(c=>` <span class="${c.activo?"okc":"dim"}">${c.activo?"●":"○"}</span> ${esc(c.tipo)} <span class="dim">${esc(c.descripcion)} · ${esc(c.sesion)} · hace ${hace(c.hace_seg)}</span>`).join("\n"):'<span class="dim"> ninguno</span>');
 const pend=e.sesiones.filter(s=>s.espera).sort((a,b)=>(b.estado==="bloqueado")-(a.estado==="bloqueado")||a.hace_seg-b.hace_seg);
 $("nespera").textContent=`(${pend.filter(s=>s.estado==="bloqueado").length} bloqueadas, ${pend.filter(s=>s.estado!=="bloqueado").length} esperando)`;
 if(!document.activeElement?.classList.contains("resp"))$("espera").innerHTML=pend.map(s=>sesion(s,`<div class="q">${esc(s.espera.texto)}</div>${s.espera.opciones.map(o=>`<span class="op">${esc(o)}</span>`).join("")}${s.espera?.traspaso?`<button class="tras" onclick="event.stopPropagation();traspasa('${s.id}')">${s.espera.traspaso.ruta?"Lanzar traspaso en terminal nueva":"Pedir traspaso y lanzarlo"}</button>`:""}<input class="resp" data-id="${s.id}" placeholder="Responder y Enter para enviar a esta sesión" onclick="event.stopPropagation()" value="${esc(borrador[s.id]||"")}"><div class="m" id="env-${s.id}">${esc((e.traspasos||{})[s.id]||enviados[s.id]||"")}</div>`)).join("")||'<div class="m">nada pendiente</div>';
 $("narch").textContent=`(${(e.archivados||[]).length})`;
 $("archivados").innerHTML=(e.archivados||[]).map(a=>`<div class="m fila">${esc(a.id)} · ${esc(a.titulo)} · ${esc((a.cwd||"").split(/[\\/]/).slice(-2).join("/"))} · archivada ${new Date(a.cuando*1000).toLocaleString("es-PE",{day:"2-digit",month:"2-digit",hour:"2-digit",minute:"2-digit"})} <button class="arc" onclick="archiva('${a.id}',true)">Restaurar</button></div>`).join("")||'<div class="m">ninguna</div>';
 $("cuenta").textContent=`(${e.sesiones.length})`;
 panelTras();panelOpc();
 $("sesiones").innerHTML=e.sesiones.map(s=>sesion(s,``)).join("")||'<div class="m">sin sesiones activas</div>';
}
function panelOpc(){const el=$("popc");if(!abierta){el.innerHTML="";return}
 const s=estado.sesiones.find(x=>x.id===abierta),o=s?.espera?.opciones||[];
 el.innerHTML=(s?.espera?`<div class="m">${esc(s.espera.texto)}</div>`:"")+o.map((t,i)=>`<button class="tras" data-o="${i}">${esc(t)}</button>`).join(" ")+` <button class="tras" onclick="const l=$('log');l.scrollTop=l.scrollHeight">↓ Ir al final</button>`
  +`<div>${["sí","ok","dale","go","¿cómo va?","¿cuánto falta?"].map((t,i)=>`<button class="tras" data-c="${i}">${t}</button>`).join(" ")}</div>`;
 el.querySelectorAll("[data-o]").forEach(b=>b.onclick=()=>envia(o[+b.dataset.o]));
 el.querySelectorAll("[data-c]").forEach(b=>b.onclick=()=>envia(b.textContent))}
function panelTras(){const el=$("ptras");if(!abierta){el.innerHTML="";return}
 const s=estado.sesiones.find(x=>x.id===abierta),t=s?.espera?.traspaso,est=(estado.traspasos||{})[abierta]||enviados[abierta]||"";
 const corre=est.includes("⏳"),ocupada=s?.estado==="procesando",off=!s||corre||ocupada;
 const why=!s?"La sesión ya no está activa":corre?"Ya se está preparando el traspaso":ocupada?"La sesión está trabajando: espera a que termine":"";
 el.innerHTML=`<button class="tras"${off?' disabled':''} title="${esc(why)}" onclick="traspasa('${abierta}')">${t?.ruta?"Lanzar traspaso en terminal nueva":"Pedir traspaso y lanzarlo"}</button> <span class="m">${esc(off&&!corre&&why?why:est)}</span>`}
async function abrir(id){abierta=id;const s=estado.sesiones.find(x=>x.id===id);$("pt").textContent=s?.titulo||id;$("pc").textContent=(s?.cwd||"")+" · "+id;
 $("nota").value="";$("nota").placeholder="Escribe y pulsa Enter";$("panel").classList.add("abierto");panelTras();panelOpc();await log(true)}
function ancho(){const on=$("panel").classList.toggle("ancho");try{localStorage.setItem("tablero-ancho",on?"1":"")}catch{}}
try{if(localStorage.getItem("tablero-ancho"))$("panel").classList.add("ancho")}catch{}
function cerrar(){abierta=null;$("ptras").innerHTML="";$("popc").innerHTML="";$("panel").classList.remove("abierto")}
async function log(abajo){if(!abierta)return;const l=await (await fetch("/api/sesion?id="+abierta,{cache:"no-store"})).json();const el=$("log");
 const pegado=abajo||el.scrollTop+el.clientHeight>=el.scrollHeight-40;
 el.innerHTML=l.map(x=>`<div class="l ${x.rol}"><b>${x.rol==="claude"?"●":x.rol==="tú"?">":x.rol==="herramienta"?"⏺":"⎿"}</b> ${cajas(x.texto)}</div>`).join("");
 if(pegado)el.scrollTop=el.scrollHeight}
async function envia(texto){
 const r=await fetch("/api/enviar",{method:"POST",body:JSON.stringify({id:abierta,texto})});
 if(!r.ok){$("nota").placeholder="✖ no se pudo enviar";return false}
 $("nota").value="";$("nota").placeholder="⏳ enviado, esperando que la sesión lo reciba…";
 const id=abierta,clave=texto.slice(0,40);
 for(let i=0;i<15&&abierta===id;i++){await new Promise(r=>setTimeout(r,2000));
  const l=await (await fetch("/api/sesion?id="+id,{cache:"no-store"})).json();
  if(l.some(x=>x.rol==="tú"&&x.texto.includes(clave))){$("nota").placeholder="✔ recibido por la sesión; la respuesta sale en la bitácora";log(false);return true}}
 if(abierta===id)$("nota").placeholder="⚠ no apareció en 30 s: revisa ~/.claude/tablero-envios.log";return false}
$("nota").addEventListener("keydown",e=>{
 if(e.key!=="Enter"||e.shiftKey||!abierta)return;e.preventDefault();
 const texto=$("nota").value.trim();if(texto)envia(texto)});
const borrador={},enviados={};
async function crea(){const r=await fetch("/api/nueva",{method:"POST",body:JSON.stringify({cwd:$("ncwd").value,prompt:$("nprompt").value})});
 $("nest").textContent=r.ok?"✔ terminal abierta":"✖ no se pudo abrir";if(r.ok){$("nprompt").value="";setTimeout(()=>$("nueva").classList.remove("abierta"),1200)}}
document.addEventListener("click",ev=>{if(abierta&&!ev.target.closest("#panel")&&!ev.target.closest(".card"))cerrar()});
document.addEventListener("keydown",ev=>{if(ev.key==="Escape"&&abierta)cerrar()});
function cajas(t){const f=t.split("\n"),o=[];let i=0;
 while(i<f.length){if(/^\s*\|.*\|\s*$/.test(f[i])){const b=[];while(i<f.length&&/^\s*\|.*\|\s*$/.test(f[i]))b.push(f[i++]);
   const filas=b.filter(l=>!/^\s*\|[\s:|-]+\|\s*$/.test(l)).map(l=>l.trim().slice(1,-1).split("|").map(c=>c.trim().replace(/\*\*|`/g,"")));
   const n=Math.max(...filas.map(x=>x.length)),w=Array.from({length:n},(_,c)=>Math.max(...filas.map(x=>[...(x[c]||"")].length)));
   const lin=(a,m,z)=>a+w.map(x=>"─".repeat(x+2)).join(m)+z,fila=x=>"│"+w.map((ww,c)=>" "+(x[c]||"").padEnd(ww)+" ").join("│")+"│";
   const out=[lin("┌","┬","┐")];filas.forEach((x,k)=>{out.push(fila(x));if(k===0&&filas.length>1)out.push(lin("├","┼","┤"))});out.push(lin("└","┴","┘"));
   o.push(`<div class="tbl">${esc(out.join("\n"))}</div>`)}else{const t2=[];while(i<f.length&&!/^\s*\|.*\|\s*$/.test(f[i]))t2.push(f[i++]);o.push(esc(t2.join("\n")))}}
 return o.join("")}
async function archiva(id,restaurar){await fetch("/api/archivar",{method:"POST",body:JSON.stringify({id,restaurar})});if(abierta===id)cerrar();tick()}
async function traspasa(id){const r=await fetch("/api/traspasar",{method:"POST",body:JSON.stringify({id})});enviados[id]=r.ok?"⏳ pidiendo el traspaso…":"✖ no se pudo iniciar";if($("env-"+id))$("env-"+id).textContent=enviados[id];panelTras()}
document.addEventListener("input",e=>{if(e.target.classList.contains("resp"))borrador[e.target.dataset.id]=e.target.value});
document.addEventListener("keydown",async e=>{
 if(e.key!=="Enter"||!e.target.classList.contains("resp"))return;
 const id=e.target.dataset.id,texto=e.target.value.trim();if(!texto)return;
 const r=await fetch("/api/enviar",{method:"POST",body:JSON.stringify({id,texto})});
 enviados[id]=r.ok?"✔ enviado: "+texto.slice(0,80)+" (la respuesta aparece en la bitácora)":"✖ no se pudo enviar";
 if(r.ok){borrador[id]="";e.target.value=""}$("env-"+id).textContent=enviados[id]});
let ultimo=null,recibido=0;
function recibe(e){ultimo=e;recibido=Date.now();pinta(e);log(false)}
function reloj(){if(!ultimo||document.activeElement?.classList.contains("resp"))return;
 const d=Math.round((Date.now()-recibido)/1000);if(!d)return;
 pinta({...ultimo,sesiones:ultimo.sesiones.map(s=>({...s,hace_seg:s.hace_seg+d}))})}
function conecta(){const es=new EventSource("/api/eventos");es.onmessage=m=>recibe(JSON.parse(m.data));
 es.onerror=()=>{$("hora").textContent="sin conexión con el servidor local; reintentando…"}}
conecta();setInterval(reloj,1000);
</script></html>"""


class Manejador(BaseHTTPRequestHandler):
    def responde(self, cuerpo, tipo):
        self.send_response(200)
        self.send_header("Content-Type", tipo)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/api/eventos":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            visto = -1
            try:
                while True:
                    with COND:
                        COND.wait_for(lambda: VERSION["n"] != visto, timeout=15)
                        visto = VERSION["n"]
                    with LOCK:
                        carga = json.dumps(ESTADO, default=str)
                    self.wfile.write(f"data: {carga}\n\n".encode())
                    self.wfile.flush()
            except (OSError, ValueError):
                return
        if url.path == "/api/estado":
            with LOCK:
                self.responde(json.dumps(ESTADO, default=str).encode(), "application/json")
        elif url.path == "/api/sesion":
            sid = parse_qs(url.query).get("id", [""])[0]
            self.responde(json.dumps(transcripcion(sid) if sid.isalnum() else []).encode(), "application/json")
        elif url.path in ("/", "/index.html"):
            self.responde(PAGINA.replace("__LLAMA__", LLAMA).encode(), "text/html; charset=utf-8")
        else:
            self.send_error(404)

    def enviar(self):
        try:
            d = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            sid, texto = str(d["id"]), str(d["texto"]).strip()
            archivo = next(PROYECTOS.glob(f"*/{sid}*.jsonl"), None) if sid.isalnum() else None
            if not archivo or not texto:
                raise ValueError
            cwd = next((e["cwd"] for e in reversed(leer_entradas(archivo)) if e.get("cwd")), None)
            envio = Path.home() / ".claude" / "tablero-prompts"
            envio.mkdir(exist_ok=True)
            entrada = envio / f"envio-{int(time.time() * 1000)}.txt"
            entrada.write_text(texto, encoding="utf-8")  # por stdin: en un argumento de cmd, `"` y `&` ejecutan comandos
            with open(Path.home() / ".claude" / "tablero-envios.log", "ab") as salida, open(entrada, "rb") as stdin:
                subprocess.Popen(["claude", "--resume", archivo.stem, "-p"], cwd=cwd, stdout=salida,
                                 stderr=subprocess.STDOUT, stdin=stdin, shell=(os.name == "nt"))
        except (ValueError, KeyError, OSError):
            self.send_error(400)
            return
        self.responde(b"{}", "application/json")

    def permitido(self):
        """Solo la página del propio tablero: una web ajena no puede lanzar sesiones (CSRF / DNS rebinding)."""
        puerto = self.server.server_address[1]
        ok = {f"127.0.0.1:{puerto}", f"localhost:{puerto}"}
        origen = self.headers.get("Origin")
        return (self.headers.get("Host") in ok and self.headers.get("X-Tablero") == "1"
                and (origen is None or origen.split("//")[-1] in ok))

    def do_POST(self):
        if not self.permitido():
            self.send_error(403)
            return
        if urlparse(self.path).path == "/api/nueva":
            try:
                d = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                nueva_sesion(str(d["cwd"]), str(d.get("prompt", ""))[:4000])
            except (ValueError, KeyError, OSError):
                self.send_error(400)
                return
            self.responde(b"{}", "application/json")
            return
        if urlparse(self.path).path == "/api/archivar":
            try:
                d = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
                if not str(d["id"]).isalnum():
                    raise ValueError
                archivar(str(d["id"]), bool(d.get("restaurar")))
            except (ValueError, KeyError, OSError):
                self.send_error(400)
                return
            self.responde(b"{}", "application/json")
            return
        if urlparse(self.path).path == "/api/traspasar":
            try:
                sid = str(json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))["id"])
                archivo = next(PROYECTOS.glob(f"*/{sid}*.jsonl"), None) if sid.isalnum() else None
                with LOCK:
                    ocupada = next((x["estado"] == "procesando" for x in ESTADO["sesiones"] if x["id"] == sid[:8]), False)
                    if not archivo or ocupada or "⏳" in TRASPASOS.get(sid, ""):
                        raise ValueError
                    TRASPASOS[sid] = "⏳ la sesión está escribiendo su traspaso…"
                threading.Thread(target=traspasar, args=(sid, archivo), daemon=True).start()
            except (ValueError, KeyError, OSError):
                self.send_error(400)
                return
            self.responde(b"{}", "application/json")
            return
        if urlparse(self.path).path == "/api/enviar":
            self.enviar()
            return
        if urlparse(self.path).path != "/api/nota":
            self.send_error(404)
            return
        try:
            d = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            if str(d["id"]).isalnum():
                n = notas()
                n[d["id"]] = str(d["texto"])[:500]
                NOTAS.write_text(json.dumps(n, ensure_ascii=False), encoding="utf-8")
        except (ValueError, KeyError, OSError):
            self.send_error(400)
            return
        self.responde(b"{}", "application/json")

    def log_message(self, *_):
        pass


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--puerto", type=int, default=5199)
    puerto = ap.parse_args().puerto
    refrescar()
    threading.Thread(target=bucle, daemon=True).start()
    threading.Thread(target=bucle_lento, daemon=True).start()
    print(f"Tablero en vivo: http://127.0.0.1:{puerto}  (Ctrl+C para cerrar)")
    ThreadingHTTPServer(("127.0.0.1", puerto), Manejador).serve_forever()
