"""Mide una corrida de /orquestar desde los transcripts y la registra sin gastar llamadas del modelo.

Uso:
  python .claude/tools/orquestar/registrar_corrida.py [--sesion ID] [--desde ISO] [--hasta ISO]
      [--codex etiqueta=log ...] [--claude etiqueta=json ...] [--deepseek etiqueta=json ...]
      [--run-doc docs/agent-runs/NNNN-slug.md --cuerpo cuerpo.md --meta meta.json]
      [--index-fila fila.json] [--mapa "línea" --mapa-despues-de "texto único"]
      [--consumo $S/consumo.tsv] [--recursos $S/recursos.tsv]

--consumo y --recursos los deja flujo.sh: el primero suma cada codex exec como un --codex; el segundo,
filas «M» (hora, fase, MB libres, CPU %, procesos dotnet, top) y «E» (hora, tipo, segundos, detalle).

Sin --run-doc/--index-fila solo imprime la bitácora: sirve para medir sin escribir.
"""
import argparse
import glob
import json
import os
import re
import sys
from datetime import datetime

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
PROYECTO = os.path.join(os.path.expanduser("~/.claude/projects"), re.sub(r"[^a-zA-Z0-9]", "-", RAIZ))
INDEX = os.path.join(RAIZ, "docs", "agent-runs", "INDEX.md")

# Precio de lista por millón (entrada, salida), el mismo de orquestar.md. Caché: leer 0.1×, escribir 1.25×.
PRECIOS = {"fable": (10, 50), "opus": (4, 20), "sonnet": (2, 10), "haiku": (1, 5)}
CAMPOS = ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens", "output_tokens")


def precio(modelo, u):
    fam = next((f for f in PRECIOS if f in (modelo or "")), None)
    if not fam:
        return None
    ent, sal = PRECIOS[fam]
    return (u["input_tokens"] * ent + u["cache_creation_input_tokens"] * ent * 1.25
            + u["cache_read_input_tokens"] * ent * 0.1 + u["output_tokens"] * sal) / 1e6


def leer_usos(ruta, desde, hasta, solo_principal):
    """Suma usage por message.id (cada id se repite en varias líneas del jsonl)."""
    por_id, modelo, marcas = {}, None, []
    for linea in open(ruta, encoding="utf-8"):
        try:
            d = json.loads(linea)
        except ValueError:
            continue
        m = d.get("message") or {}
        if d.get("type") != "assistant" or not m.get("usage"):
            continue
        if solo_principal and d.get("isSidechain"):
            continue
        ts = d.get("timestamp") or ""
        if (desde and ts < desde) or (hasta and ts > hasta):
            continue
        por_id[m.get("id")] = m["usage"]
        modelo = m.get("model") or modelo
        marcas.append(ts)
    total = {k: sum(u.get(k) or 0 for u in por_id.values()) for k in CAMPOS}
    return total, len(por_id), modelo, marcas


def minutos(marcas):
    if len(marcas) < 2:
        return "—"
    f = lambda s: datetime.fromisoformat(s.replace("Z", "+00:00"))
    seg = (f(max(marcas)) - f(min(marcas))).total_seconds()
    return f"{seg:.0f} s" if seg < 90 else f"{seg / 60:.1f} min"


def fmt(u):
    return (f"{u['input_tokens']:,} entrada + {u['cache_creation_input_tokens']:,} caché escrito + "
            f"{u['cache_read_input_tokens']:,} caché leído + {u['output_tokens']:,} salida")


def tokens_codex(ruta):
    texto = open(ruta, encoding="utf-8", errors="replace").read()
    hallado = re.findall(r"tokens used\s*\n\s*([\d,]+)", texto)
    return int(hallado[-1].replace(",", "")) if hallado else None


def medir(a):
    sesion = a.sesion or max(glob.glob(os.path.join(PROYECTO, "*.jsonl")), key=os.path.getmtime)
    if not os.path.isfile(sesion):
        sesion = os.path.join(PROYECTO, sesion + ".jsonl")
    carpeta = sesion[:-len(".jsonl")]
    filas, costo_claude, sub_tokens = [], 0.0, 0

    for meta in sorted(glob.glob(os.path.join(carpeta, "subagents", "*.meta.json"))):
        tipo = json.load(open(meta, encoding="utf-8")).get("agentType", "?")
        u, n, modelo, marcas = leer_usos(meta.replace(".meta.json", ".jsonl"), a.desde, a.hasta, False)
        if not n:
            continue
        c = precio(modelo, u)
        costo_claude += c or 0
        # Mismo criterio que subagent_tokens de la notificación: lo nuevo, sin el caché leído.
        sub_tokens += u["input_tokens"] + u["cache_creation_input_tokens"] + u["output_tokens"]
        filas.append((f"`{tipo}`", "Claude", modelo, f"{fmt(u)} ({n} llamadas)", minutos(marcas),
                      f"~${c:.2f}" if c is not None else ""))

    for par in a.codex:
        etiqueta, ruta = par.split("=", 1)
        t = tokens_codex(ruta)
        filas.append((f"Codex ({etiqueta})", "OpenAI", "por defecto", f"{t:,}" if t else "sin reportar", "—", ""))

    for par in a.claude:
        # Agente de Claude lanzado headless (claude -p --output-format json), p. ej. el planner de nivel1.sh.
        etiqueta, ruta = par.split("=", 1)
        d = json.load(open(ruta, encoding="utf-8"))
        u = {k: (d.get("usage") or {}).get(k) or 0 for k in CAMPOS}
        modelo = next(iter(d.get("modelUsage") or {}), "?")
        c = precio(modelo, u)
        costo_claude += c or 0
        sub_tokens += u["input_tokens"] + u["cache_creation_input_tokens"] + u["output_tokens"]
        filas.append((f"`{etiqueta}` (headless)", "Claude", modelo, f"{fmt(u)} ({d.get('num_turns')} turnos)",
                      f"{(d.get('duration_ms') or 0) / 60000:.1f} min", f"~${c:.2f}" if c is not None else ""))

    for par in a.deepseek:
        etiqueta, ruta = par.split("=", 1)
        d = json.load(open(ruta, encoding="utf-8"))
        u = d.get("usage") or {}
        filas.append((f"`{etiqueta}` vía DeepSeek", "DeepSeek", "deepseek-v4-pro",
                      f"{u.get('input_tokens', 0):,} entrada + {u.get('cache_read_input_tokens', 0):,} caché + "
                      f"{u.get('output_tokens', 0):,} salida ({d.get('num_turns')} turnos)",
                      minutos([]) if not d.get("duration_ms") else f"{d['duration_ms'] / 60000:.1f} min", ""))

    u, n, modelo, marcas = leer_usos(sesion, a.desde, a.hasta, True)
    c = precio(modelo, u)
    costo_claude += c or 0
    leido = u["cache_read_input_tokens"]
    hit = leido / max(1, leido + u["cache_creation_input_tokens"] + u["input_tokens"])
    filas.append(("Orquestador", "Claude", modelo, f"{fmt(u)} ({n} llamadas)", minutos(marcas),
                  f"~${c:.2f}, hit rate {hit:.1%}" if c is not None else ""))

    tabla = ["| Agente / motor | Cuenta | Modelo | Tokens | Duración | Costo de lista |",
             "|---|---|---|---|---|---|"] + ["| " + " | ".join(str(c or "—") for c in f) + " |" for f in filas]
    resumen = (f"Claude subagentes {sub_tokens / 1000:.1f}K; orquestador {leido / 1e6:.2f}M caché leído + "
               f"{u['cache_creation_input_tokens'] / 1000:.1f}K escrito + {u['output_tokens'] / 1000:.1f}K salida "
               f"({n} llamadas); costo Claude de lista ~${costo_claude:.2f}")
    return "\n".join(tabla), resumen, sub_tokens, minutos(marcas)


def seccion_maquina(ruta):
    """Resumen de recursos.tsv de flujo.sh: dónde se perdió tiempo por la máquina (el responsable, 2026-10-23)."""
    if not ruta or not os.path.exists(ruta):
        return "## Máquina\n\nsin medir\n"
    libres, cpus, dotnets, espera, eventos = [], [], [], {}, []
    for linea in open(ruta, encoding="utf-8", errors="replace"):
        c = linea.rstrip("\n").split("\t")
        if c[0] == "M" and len(c) >= 6:
            libres.append(int(c[3])); cpus.append(float(c[4])); dotnets.append(int(c[5]))
        elif c[0] == "E" and len(c) >= 5:
            espera[c[2]] = espera.get(c[2], 0) + int(c[3] or 0)
            if c[2] in ("reintento", "colgado", "huerfanos"):
                eventos.append(f"- {c[1][11:16]} {c[2]}: {c[4]}")
    if not libres:
        return "## Máquina\n\nsin muestras\n"
    filas = [f"- RAM libre: mínimo {min(libres)} MB, media {sum(libres) // len(libres)} MB ({len(libres)} muestras)",
             f"- CPU media: {sum(cpus) / len(cpus):.0f} %; procesos dotnet a la vez: hasta {max(dotnets)}"]
    filas += [f"- Espera por {k}: {v} s" for k, v in sorted(espera.items()) if v]
    return "## Máquina\n\n" + "\n".join(filas + (eventos or ["- Sin reintentos ni procesos colgados"])) + "\n"


# Las tres que retro cuenta (anexo-registro.md). Eran texto y 0131/0132 salieron sin ellas: ahora frenan el cierre.
LINEAS_OBLIGATORIAS = (("Codex: rondas hasta 2 limpias", r"^Codex: rondas hasta 2 limpias"),
                       ("Escapó al QA:", r"^Escapó al QA:"),
                       ("## Reglas que rompí", r"^## Reglas que rompí"))


def faltantes_run_doc(texto):
    return [nombre for nombre, patron in LINEAS_OBLIGATORIAS if not re.search(patron, texto, re.M)]


def escribir_run_doc(a, tabla, resumen, sub_tokens, duracion):
    meta = json.load(open(a.meta, encoding="utf-8"))
    front = ["---", "tipo: run", f'numero: "{meta["numero"]}"', f"fecha: {meta['fecha']}",
             f"resultado: {meta['resultado']}", f"ciclos_qa: {meta.get('ciclos_qa', 0)}",
             f'duracion: "~{duracion}"', f'tokens: "{resumen}"', f"tokens_num: {sub_tokens}",
             'tokens_fuente: "real (transcripts de la sesión, logs de Codex, JSON de DeepSeek)"',
             f"rama: {meta['rama']}", f"tags: [{', '.join(meta.get('tags', ['run', 'api-core', 'orquestador']))}]",
             "---", "", ""]
    cuerpo = open(a.cuerpo, encoding="utf-8").read().rstrip()
    doc = ("\n".join(front) + cuerpo + "\n\n## Bitácora de consumo\n\n" + tabla + "\n\n"
           + seccion_maquina(a.recursos))
    open(os.path.join(RAIZ, a.run_doc), "w", encoding="utf-8", newline="").write(doc)


def escribir_index(a, resumen, duracion):
    s = open(INDEX, encoding="utf-8", newline="").read()
    if a.mapa:
        if s.count(a.mapa_despues_de) != 1:
            sys.exit(f"--mapa-despues-de debe aparecer una sola vez en INDEX.md: {a.mapa_despues_de!r}")
        fin = s.index("\n", s.index(a.mapa_despues_de)) + 1
        s = s[:fin] + a.mapa.rstrip() + "\n" + s[fin:]
    if a.index_fila:
        f = json.load(open(a.index_fila, encoding="utf-8"))
        fila = (f"| {f['fecha']} | {f['tarea']} | {f['resultado']} | ~{duracion} | {resumen} | "
                f"{f.get('ciclos_qa', 0)} | `{f['rama']}` | [{f['numero']}]({os.path.basename(a.run_doc)}) |")
        lineas = s.split("\n")
        ultima = max(i for i, l in enumerate(lineas) if re.match(r"\| \d{4}-\d{2}-\d{2} \|", l))
        lineas.insert(ultima + 1, fila)
        s = "\n".join(lineas)
    open(INDEX, "w", encoding="utf-8", newline="").write(s)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sesion")
    p.add_argument("--desde", help="timestamp ISO UTC; lo anterior no cuenta")
    p.add_argument("--hasta", help="timestamp ISO UTC; lo posterior no cuenta (ej. el Step 5)")
    p.add_argument("--codex", action="append", default=[])
    p.add_argument("--claude", action="append", default=[], help="etiqueta=json de claude -p")
    p.add_argument("--deepseek", action="append", default=[])
    p.add_argument("--run-doc")
    p.add_argument("--cuerpo")
    p.add_argument("--meta")
    p.add_argument("--index-fila")
    p.add_argument("--mapa")
    p.add_argument("--mapa-despues-de")
    p.add_argument("--consumo", help="consumo.tsv de flujo.sh: etiqueta<TAB>log de cada codex exec")
    p.add_argument("--recursos", help="recursos.tsv de flujo.sh: muestras de la máquina y esperas")
    a = p.parse_args()
    if a.consumo and os.path.exists(a.consumo):
        a.codex += ["=".join(l.rstrip("\n").split("\t", 1)) for l in open(a.consumo, encoding="utf-8") if "\t" in l]

    if a.run_doc and a.cuerpo and a.meta:
        faltan = faltantes_run_doc(open(a.cuerpo, encoding="utf-8").read())
        if faltan:
            print(f"ERROR: al cuerpo del run doc le falta: {', '.join(faltan)} "
                  "(con 0, «no» o «ninguna» si no hubo; ver .claude/orquestar/anexo-registro.md)", file=sys.stderr)
            sys.exit(1)

    tabla, resumen, sub_tokens, duracion = medir(a)
    print(tabla, "\n\n" + resumen)
    if a.recursos:
        print("\n" + seccion_maquina(a.recursos))
    if a.run_doc and a.cuerpo and a.meta:
        escribir_run_doc(a, tabla, resumen, sub_tokens, duracion)
        print(f"\nrun doc: {a.run_doc}")
    if a.index_fila or a.mapa:
        escribir_index(a, resumen, duracion)
        print("INDEX.md actualizado")


if __name__ == "__main__":
    main()
