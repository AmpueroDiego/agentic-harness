#!/usr/bin/env python3
"""
run.py — ORQUESTADOR (la mitad determinista)

La orquestación tiene dos mitades:

  1. Determinista — capturar, medir, montar el esqueleto de carpetas y decir
     quién tiene que hacer qué. Eso es esto, y es código.

  2. Dirigida por modelo — leer, interpretar, resolver conflictos, escribir.
     Eso vive en orquestador/extraer.md y orquestador/reproducir.md,
     porque no se puede scriptear: lo ejecuta el agente que lea esos archivos.

Uso:
    python tools/run.py extraer https://ejemplo.com/oferta
    python tools/run.py extraer https://ejemplo.com --depth 2 --submit-optin --email x@y.com
    python tools/run.py plan <slug>            # solo imprime el reparto
    python tools/run.py estado <slug>          # qué falta por hacer
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

# La salida lleva flechas y acentos; la consola de Windows es cp1252 por defecto.
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

ESPECIALISTAS = [
    "frontend", "disenador", "neuromarketing", "psicologo", "linguista",
    "copywriter", "mercadologo", "sociologo", "ingeniero-industrial",
    "administrador", "growth-data",
]

OLAS = [
    (1, ["mercadologo", "administrador"],
     "Fijan avatar, consciencia, sofisticación y precio. Todo depende de esto."),
    (2, ["psicologo", "sociologo", "ingeniero-industrial", "disenador",
         "linguista", "frontend", "growth-data", "neuromarketing"],
     "En paralelo, con la ola 1 ya cerrada."),
    (3, ["copywriter"],
     "Escribe con el manual de voz, las resistencias y la oferta ya decididos."),
]

ENCARGO_EXTRAER = """Eres el especialista {esp}. Modo EXTRAER.
Lee CONTRATO.md y especialistas/{esp}/extraer.md.
{tool}Trabaja sobre casos/{slug}/raw/.
Escribe casos/{slug}/extraccion/{esp}.md con las 5 secciones del contrato.
No toques ningún otro archivo."""

ENCARGO_REPRODUCIR = """Eres el especialista {esp}. Modo REPRODUCIR.
Lee CONTRATO.md, especialistas/{esp}/extraer.md
y especialistas/{esp}/reproducir.md.
Entrada: casos/{slug}/extraccion/{esp}.md, ficha-producto.md,
sintesis.md, reproduccion/compatibilidad.md y las salidas de olas anteriores.
Pasa tu autoverificación antes de dar la salida por buena.
Escribe casos/{slug}/reproduccion/{esp}.md. Nada más."""


def _tool_de(esp: str) -> str:
    """Lee el campo `tools:` del frontmatter del especialista."""
    f = Path("especialistas") / esp / "extraer.md"
    if not f.exists():
        return ""
    for linea in f.read_text(encoding="utf-8").splitlines()[:8]:
        if linea.startswith("tools:"):
            v = linea.split(":", 1)[1].strip()
            if v.startswith("ninguna"):
                return ""
            return f"Lee primero {v.split('→')[-1].strip()} — son hechos medidos.\n"
    return ""


def _sh(cmd: list[str]) -> int:
    print(f"  $ {' '.join(cmd)}")
    return subprocess.call(cmd)


# --------------------------------------------------------------------------- #
# Slug y cola
#
# El slug es el dominio sin TLD, como manda CONTRATO.md. La relación entre
# funnels.txt y las carpetas no vive en el nombre sino en casos/README.md, que
# las empareja por la URL guardada en captura.json.
# --------------------------------------------------------------------------- #

FUNNELS = Path("funnels.txt")


def _urls_en_cola() -> list[str]:
    """Las URL de funnels.txt, en orden, sin blancos ni comentarios."""
    if not FUNNELS.exists():
        return []
    return [l.strip() for l in FUNNELS.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.strip().startswith("#")]


def _casos_existentes() -> list[Path]:
    base = Path("casos")
    if not base.exists():
        return []
    return sorted(d for d in base.iterdir() if d.is_dir())


def _slug_de(url: str) -> str:
    """Dominio sin TLD y en minúsculas, como define CONTRATO.md."""
    return re.sub(
        r"[^a-z0-9]+", "-",
        urlparse(url).netloc.lower().replace("www.", "").rsplit(".", 1)[0],
    ).strip("-")


def _url_del_caso(base: Path) -> str | None:
    """La URL vive en captura.json; es la única fuente fiable dentro del caso."""
    f = base / "raw" / "captura.json"
    if not f.exists():
        return None
    try:
        return json.loads(f.read_text(encoding="utf-8")).get("url")
    except Exception:
        return None


def extraer(url: str, slug: str | None, depth: int, passes: int,
            submit: bool, email: str | None) -> None:
    slug = slug or _slug_de(url)
    base = Path("casos") / slug
    for d in ("raw", "extraccion", "reproduccion"):
        (base / d).mkdir(parents=True, exist_ok=True)

    print(f"\n[1/3] CAPTURA → {base/'raw'}")
    cmd = [sys.executable, "tools/capture.py", url, "--slug", slug,
           "--depth", str(depth), "--passes", str(passes)]
    if submit:
        cmd.append("--submit-optin")
        if email:
            cmd += ["--email", email]
    if _sh(cmd) != 0:
        sys.exit("La captura falló. Sin raw/ no hay nada que analizar.")

    print(f"\n[2/3] MEDICIÓN → {base/'raw'/'analysis'}")
    _sh([sys.executable, "-m", "tools.analyze", slug])

    print(f"\n[3/3] REPARTO — los 11 especialistas, en paralelo")
    plan(slug, "extraer")
    indice(silencioso=True)

    print(f"""
La parte determinista está hecha. La otra mitad la ejecuta el agente:

  · Lee orquestador/extraer.md desde el Paso 2 y lanza los encargos de arriba.
  · Cada encargo es un agente independiente; pueden ir en paralelo.

Después: fundir las 11 extracciones en sintesis.md y generar el super-skill
desde casos/_PLANTILLA.md.
""")


def plan(slug: str, modo: str) -> None:
    if modo == "extraer":
        print("\n  Todos a la vez - son lecturas independientes del mismo material.\n")
        for e in ESPECIALISTAS:
            print("  " + "-" * 66)
            print("  " + ENCARGO_EXTRAER.format(esp=e, slug=slug,
                                                tool=_tool_de(e)).replace("\n", "\n  "))
    else:
        print("\n  En tres olas - unas decisiones condicionan a otras.\n")
        for n, esps, por_que in OLAS:
            print(f"  == OLA {n} -- {por_que}")
            for e in esps:
                print("  " + "-" * 66)
                print("  " + ENCARGO_REPRODUCIR.format(esp=e, slug=slug).replace("\n", "\n  "))
            print()


def _fase_de(base: Path) -> str:
    """En qué punto del recorrido está un caso."""
    extr = base / "extraccion"
    n = sum((extr / f"{e}.md").exists() for e in ESPECIALISTAS) if extr.exists() else 0
    if (base / "reproduccion" / "build.html").exists():
        return "reproducido"
    if (base / "SKILL.md").exists():
        return "super-skill"
    if (base / "sintesis.md").exists():
        return "sintetizado"
    if n == len(ESPECIALISTAS):
        return "extraído"
    if n:
        return f"extrayendo ({n}/{len(ESPECIALISTAS)})"
    if (base / "raw" / "analysis").exists():
        return "medido"
    if (base / "raw").exists() and any((base / "raw").iterdir()):
        return "capturado"
    return "vacío"


def indice(silencioso: bool = False) -> None:
    """Regenera casos/README.md: la tabla que liga funnels.txt con las carpetas."""
    cola = _urls_en_cola()
    casos = _casos_existentes()
    por_url = {(_url_del_caso(c) or "").rstrip("/"): c for c in casos}

    filas, emparejados = [], set()
    for i, url in enumerate(cola, 1):
        c = por_url.get(url.rstrip("/"))
        if c is not None:
            emparejados.add(c.name)
            filas.append((f"{i:02d}", url, f"[`{c.name}/`]({c.name}/)", _fase_de(c)))
        else:
            filas.append((f"{i:02d}", url, "—", "**pendiente**"))

    # Casos que no vienen de funnels.txt: se analizaron pasando la URL suelta.
    for c in casos:
        if c.name not in emparejados:
            filas.append(("—", _url_del_caso(c) or "?",
                          f"[`{c.name}/`]({c.name}/)", _fase_de(c)))

    hechos = sum(1 for f in filas if f[3] not in ("**pendiente**", "vacío"))
    lineas = [
        "# casos/",
        "",
        "**Un funnel analizado, una carpeta.** Nada se mezcla entre casos.",
        "",
        "Esta tabla la regenera `python tools/run.py indice` — y sola al final de cada",
        "`run.py extraer`. No se edita a mano.",
        "",
        f"`funnels.txt`: {len(cola)} en cola · "
        f"`casos/`: {len(casos)} carpeta{'s' if len(casos) != 1 else ''} · "
        f"{hechos} con trabajo hecho",
        "",
        "| # | URL de origen | Carpeta | Fase |",
        "|---|---|---|---|",
    ]
    lineas += [f"| {n} | {u} | {c} | {f} |" for n, u, c, f in filas]
    lineas += [
        "",
        "El `#` es la posición de la URL en `funnels.txt`. El emparejamiento no se hace",
        "por el nombre de la carpeta sino por la URL guardada en `raw/captura.json`, así",
        "que el slug sigue siendo el dominio sin TLD que manda `CONTRATO.md`. Un `—` en la",
        "columna `#` es un caso analizado pasando la URL suelta, sin pasar por la cola.",
        "",
        "**Fases:** `capturado` → `medido` → `extrayendo` → `extraído` → `sintetizado` →",
        "`super-skill` → `reproducido`. `python tools/run.py estado <slug>` da el detalle",
        "de uno solo.",
        "",
        "`_PLANTILLA.md` no es un caso: es el molde con el que se escribe cada `SKILL.md`.",
        "",
    ]
    destino = Path("casos") / "README.md"
    destino.write_text("\n".join(lineas), encoding="utf-8")
    if not silencioso:
        print(f"  índice regenerado → {destino}  ({len(filas)} filas)")


def estado(slug: str) -> None:
    base = Path("casos") / slug
    if not base.exists():
        sys.exit(f"No existe {base}")
    raw, extr, repr_ = base / "raw", base / "extraccion", base / "reproduccion"

    def marca(ok: bool) -> str:
        return "[x]" if ok else "[ ]"

    print(f"\n  {slug}\n")
    print(f"  {marca(raw.exists() and any(raw.iterdir()))} captura")
    an = raw / "analysis"
    for j in ("design", "attention", "text", "flow", "trackers"):
        print(f"    {marca((an / f'{j}.json').exists())} analysis/{j}.json")
    print()
    hechas = 0
    for e in ESPECIALISTAS:
        ok = (extr / f"{e}.md").exists()
        hechas += ok
        print(f"  {marca(ok)} extraccion/{e}.md")
    print(f"\n  {marca((base/'sintesis.md').exists())} sintesis.md")
    print(f"  {marca((base/'SKILL.md').exists())} SKILL.md  (el super-skill)")
    print(f"\n  extracciones: {hechas}/{len(ESPECIALISTAS)}")
    if hechas < len(ESPECIALISTAS):
        faltan = [e for e in ESPECIALISTAS if not (extr / f"{e}.md").exists()]
        print(f"  faltan: {', '.join(faltan)}")

    # Un origen sirve a varios productos: cada uno en su subcarpeta.
    productos = sorted(d for d in repr_.iterdir() if d.is_dir()) if repr_.exists() else []
    print(f"\n  reproducciones: {len(productos)}")
    for d in productos:
        n = sum((d / f"{e}.md").exists() for e in ESPECIALISTAS)
        print(f"\n    {d.name}/")
        print(f"      {marca((d/'ficha-producto.md').exists())} ficha-producto.md")
        print(f"      {marca((d/'compatibilidad.md').exists())} compatibilidad.md")
        print(f"      {marca(n == len(ESPECIALISTAS))} directivas  ({n}/{len(ESPECIALISTAS)})")
        print(f"      {marca((d/'plan.md').exists())} plan.md")
        print(f"      {marca((d/'build.html').exists())} build.html  (opcional)")
    if not productos:
        print("    ninguna todavía — el paso 1 es la ficha del producto")
    print()


def main() -> None:
    # La consola de Windows suele ser cp1252: forzar UTF-8 evita
    # que un guion largo reviente todo el reparto.
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Orquestador — la mitad determinista")
    sub = ap.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("extraer", help="capturar + medir + repartir")
    e.add_argument("url")
    e.add_argument("--slug")
    e.add_argument("--depth", type=int, default=1)
    e.add_argument("--passes", type=int, default=3)
    e.add_argument("--submit-optin", action="store_true")
    e.add_argument("--email")

    p = sub.add_parser("plan", help="imprimir el reparto sin ejecutar nada")
    p.add_argument("slug")
    p.add_argument("--modo", choices=["extraer", "reproducir"], default="extraer")

    s = sub.add_parser("estado", help="qué falta por hacer en un caso")
    s.add_argument("slug")

    sub.add_parser("indice", help="regenerar casos/README.md")

    a = ap.parse_args()
    if a.cmd == "extraer":
        extraer(a.url, a.slug, a.depth, a.passes, a.submit_optin, a.email)
    elif a.cmd == "indice":
        indice()
    elif a.cmd == "plan":
        plan(a.slug, a.modo)
    else:
        estado(a.slug)


if __name__ == "__main__":
    main()
