#!/usr/bin/env python3
"""
flow.py — el funnel como proceso → alimenta a `ingeniero-industrial`

Pasos, fricción por paso, campos de formulario, decisiones exigidas,
salidas del camino crítico y páginas ocultas. También sirve a `frontend`
para el esqueleto y los breakpoints.

    python -m tools.analyze.flow <slug>
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter

from ._common import cargar, escribir, px, visibles

SECCION = re.compile(r"(hero|header|footer|pricing|precio|faq|testimon|garant|"
                     r"beneficio|feature|cta|contacto|nav)", re.I)

def _rasgos(e: dict, els: list[dict]) -> dict:
    """Qué hay dentro de una franja vertical, contado.

    **No se nombra el bloque, se describe.** Nombrarlo exige leer el texto, y un
    clasificador por palabras clave solo funciona en el idioma y el sector para
    los que se escribió: en cuanto la página es de otro nicho o de otra lengua,
    devuelve etiquetas peores que ninguna. Estos conteos son los mismos en
    cualquier página, y con ellos el especialista nombra el bloque él.
    """
    y0, y1 = e["box"]["y"], e["box"]["y"] + e["box"]["h"]
    dentro = [x for x in els if y0 <= x["box"]["y"] < y1]

    palabras = sum(len((x.get("text") or "").split()) for x in dentro)
    rejillas = [x.get("cols") for x in dentro if x.get("cols")]
    return {
        "h1": any(x["tag"] == "h1" for x in dentro),
        "encabezados": sum(x["tag"] in ("h1", "h2", "h3") for x in dentro),
        "accionables": sum(x["tag"] in ("button", "a") and bool(x.get("text"))
                           for x in dentro),
        "campos": sum(x["tag"] in ("input", "select", "textarea") for x in dentro),
        "videos": sum(x["tag"] == "video" for x in dentro),
        "imagenes": sum(x["tag"] == "img" for x in dentro),
        "palabras": palabras,
        "rejilla": rejillas[0] if rejillas else None,
        "columnas": (len(rejillas[0].split()) if rejillas else None),
        # Cifra grande y suelta: precios, contadores, pasos numerados. Qué sea
        # depende del contexto, y eso lo decide quien lee, no el parser.
        "cifras_destacadas": sum(
            1 for x in dentro
            if (x.get("text") or "").strip().replace(",", "").replace(".", "").isdigit()
            and (px(x.get("size")) or 0) >= 32
        ),
    }


def analizar(dump: dict, raw) -> dict:
    els = visibles(dump)
    doc = dump["doc"]

    # --- formularios: donde vive la fricción ---------------------------------
    forms = []
    for f in doc.get("forms", []):
        campos = f.get("fields", [])
        visibles_ = [c for c in campos if not c.get("hidden")]
        forms.append({
            "action": f.get("action"),
            "campos_visibles": len(visibles_),
            "campos_ocultos": len(campos) - len(visibles_),
            "obligatorios": sum(1 for c in visibles_ if c.get("required")),
            "tipos": Counter(c["type"] for c in visibles_),
            "friccion": ("baja" if len(visibles_) <= 2 else
                         "media" if len(visibles_) <= 5 else "alta"),
        })

    # --- decisiones: cuántas opciones se ofrecen a la vez --------------------
    accionables = [e for e in els
                   if (e["tag"] in ("button", "a") or "btn" in (e.get("cls") or "").lower())
                   and e.get("text")]
    por_pantalla: Counter = Counter()
    for e in accionables:
        por_pantalla[e["box"]["y"] // 900] += 1

    # --- salidas del camino crítico ------------------------------------------
    externos = [l for l in doc.get("links", []) if l.get("external")]
    dominios_ext = Counter(re.sub(r"^https?://([^/]+).*", r"\1", l["href"])
                           for l in externos)

    # --- esqueleto: secciones de primer nivel --------------------------------
    grandes = [e for e in els
               if e["box"]["w"] > 900 and e["box"]["h"] > 200
               and e["tag"] in ("section", "div", "main", "header", "footer")]
    grandes.sort(key=lambda e: e["box"]["y"])
    bloques = []
    ultimo_y = -300
    for e in grandes:
        if e["box"]["y"] - ultimo_y < 150:
            continue
        ultimo_y = e["box"]["y"]
        bloques.append(e)

    # El contenedor raíz abarca la página entera: es el marco, no una sección.
    alto_doc = doc.get("h") or 0
    esqueleto = []
    for e in bloques:
        raiz = bool(alto_doc) and e["box"]["h"] >= alto_doc * 0.9
        pista = SECCION.search((e.get("cls") or "") + " " + (e.get("id") or ""))
        esqueleto.append({
            "y": e["box"]["y"],
            "alto": e["box"]["h"],
            "tag": e["tag"],
            "contenedor_raiz": raiz,
            # Solo cuando el propio marcado lo declara. Si no, se deja en null:
            # inventar una etiqueta es peor que no darla.
            "tipo_declarado": pista.group(1).lower() if pista else None,
            "rasgos": _rasgos(e, els),
        })

    # --- layout ---------------------------------------------------------------
    contenedores = [e["box"]["w"] for e in els
                    if e["display"] in ("block", "flex", "grid") and e["box"]["w"] > 600]
    ancho_max = max(contenedores) if contenedores else None
    frec_ancho = Counter(contenedores).most_common(3)
    rejillas = Counter(e["cols"] for e in els if e.get("cols"))

    # --- breakpoints declarados ----------------------------------------------
    breakpoints = []
    css_f = raw / "styles.css"
    if css_f.exists():
        css = css_f.read_text(encoding="utf-8", errors="ignore")
        breakpoints = sorted({int(m) for m in
                              re.findall(r"max-width:\s*(\d+)px", css)}, reverse=True)[:6]

    # --- páginas ocultas y pasos seguidos ------------------------------------
    pasos = []
    cap = raw / "captura.json"
    if cap.exists():
        c = json.loads(cap.read_text(encoding="utf-8"))
        pasos = c.get("pasos", [])
        optin = c.get("optin")
    else:
        optin = None

    noindex = any(m.get("name") == "robots" and "noindex" in (m.get("content") or "").lower()
                  for m in doc.get("metas", []))

    total_campos = sum(f["campos_visibles"] for f in forms)
    return {
        "esqueleto": esqueleto,
        "layout": {
            "ancho_max_contenedor": ancho_max,
            "anchos_frecuentes": [{"px": w, "n": n} for w, n in frec_ancho],
            "rejillas": [{"cols": c, "n": n} for c, n in rejillas.most_common(4)],
            "breakpoints_declarados": breakpoints,
        },
        "formularios": forms,
        "friccion": {
            "campos_visibles_totales": total_campos,
            "decisiones_por_pantalla": dict(sorted(por_pantalla.items())),
            "max_decisiones_en_una_pantalla": max(por_pantalla.values()) if por_pantalla else 0,
            "diagnostico": (
                "Se pide mucho antes de entregar nada: reordenar valor y esfuerzo "
                "suele valer más que reescribir el copy."
                if total_campos > 4 else
                "La captación es ligera; la fricción no está en el formulario."),
        },
        "salidas_del_camino": {
            "enlaces_externos": len(externos),
            "dominios": dict(dominios_ext.most_common(8)),
        },
        "pasos_capturados": pasos,
        "optin": optin,
        "noindex": noindex,
        "n_pasos_conocidos": 1 + len(pasos),
    }


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("uso: python -m tools.analyze.flow <slug>")
    dump, raw = cargar(sys.argv[1])
    f = escribir(raw, "flow", analizar(dump, raw))
    print(f"flow → {f}")


if __name__ == "__main__":
    main()
