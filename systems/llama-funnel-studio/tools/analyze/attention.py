#!/usr/bin/env python3
"""
attention.py — arquitectura de atención → alimenta a `neuromarketing`

Saliencia del CTA en delta-E contra su entorno, competencia de atención,
qué entra en el primer viewport, decisiones por pantalla (Hick), ancho de
medida en caracteres. Todo medido sobre el render, nada interpretado.

    python -m tools.analyze.attention <slug>
"""
from __future__ import annotations

import re
import sys

from ._common import (cargar, escribir, rgb, hexa, px, delta_e, contraste,
                      visibles, fondo, tapado_por_descendiente)

FOLD = 900   # alto del viewport desktop usado en la captura
CTA = re.compile(r"(comprar|quiero|empez|acced|reserv|agend|descarg|suscrib|"
                 r"unirme|apunt|solicit|contact|prueba|gratis|ver más|registr)", re.I)


def _es_accionable(e: dict) -> bool:
    cls = (e.get("cls") or "").lower()
    return (e["tag"] in ("button", "a")
            or "btn" in cls or "button" in cls or "cta" in cls)


def analizar(dump: dict) -> dict:
    els = visibles(dump)
    alto = dump["doc"].get("h") or 0

    # --- fondo dominante, para medir contra él -------------------------------
    from collections import Counter
    areas: Counter = Counter()
    for e in els:
        c = fondo(e)
        if c and not tapado_por_descendiente(e, els):
            areas[hexa(c)] += e["box"]["w"] * e["box"]["h"] * c[3]
    fondo_hex = areas.most_common(1)[0][0] if areas else "#FFFFFF"
    dominante = rgb("rgb({},{},{})".format(
        *(int(fondo_hex[i:i + 2], 16) for i in (1, 3, 5))))

    # --- candidatos a CTA -----------------------------------------------------
    ctas = []
    for e in els:
        txt = (e.get("text") or "").strip()
        if not txt or len(txt) > 60 or not _es_accionable(e):
            continue
        c = fondo(e)
        if not c:
            continue
        ctas.append({
            "texto": txt,
            "y": e["box"]["y"],
            "sobre_el_pliegue": e["box"]["y"] < FOLD,
            "area_px": e["box"]["w"] * e["box"]["h"],
            "color": hexa(c),
            "delta_e_vs_fondo": delta_e(c, dominante),
            "contraste_vs_fondo": contraste(c, dominante),
            "verbo_de_accion": bool(CTA.search(txt)),
        })
    ctas.sort(key=lambda x: (-x["delta_e_vs_fondo"], x["y"]))

    # --- competencia de atención ---------------------------------------------
    # Un CTA llamativo no sirve si hay otros seis igual de llamativos.
    # Un elemento más alto que una pantalla es telón de fondo, no foco: nadie
    # compite por la atención con el lienzo sobre el que está pintado todo lo
    # demás. Sin este corte, el propio fondo de la página aparecía como el
    # elemento más saliente y el diagnóstico salía invertido.
    tope_area = (dump["doc"].get("w") or 1440) * FOLD

    salientes = []
    for e in els:
        c = fondo(e)
        if not c:
            continue
        # La saliencia se pondera por opacidad: un halo al 30 % no llama la
        # atención como un bloque sólido del mismo color, por muy grande que sea.
        d = round(delta_e(c, dominante) * c[3], 2)
        area = e["box"]["w"] * e["box"]["h"]
        if area > tope_area:
            continue
        if d > 25 and area > 2500:
            salientes.append({"y": e["box"]["y"], "delta_e": d, "area": area,
                              "accionable": _es_accionable(e),
                              "texto": (e.get("text") or "")[:60] or None})
    salientes.sort(key=lambda x: -x["delta_e"])
    sobre_pliegue = [s for s in salientes if s["y"] < FOLD]

    top = ctas[0] if ctas else None
    competidores = [
        s for s in sobre_pliegue
        if not s["accionable"] and top
        and s["delta_e"] >= top["delta_e_vs_fondo"] * 0.8
    ]

    # --- above the fold -------------------------------------------------------
    en_pliegue = [e for e in els if e["box"]["y"] < FOLD and e.get("text")]
    h1 = next((e for e in els if e["tag"] == "h1"), None)

    # --- Hick: decisiones simultáneas ----------------------------------------
    decisiones = len([e for e in els
                      if e["box"]["y"] < FOLD and _es_accionable(e) and e.get("text")])

    # --- fluidez: ancho de medida en caracteres ------------------------------
    medidas = []
    for e in els:
        t = e.get("text") or ""
        s = px(e.get("size"))
        if len(t) > 60 and s and e["box"]["w"]:
            # ~0.5em por carácter en fuentes proporcionales
            medidas.append(round(e["box"]["w"] / (s * 0.5)))
    medida = round(sum(medidas) / len(medidas)) if medidas else None

    # Si hay accionables con texto pero ninguno pasó el filtro de fondo, el que
    # falla es el detector, no la página. Decirlo aquí evita que un especialista
    # concluya "no hay CTA" sobre un artefacto.
    accionables = [e for e in els if _es_accionable(e) and (e.get("text") or "").strip()]
    aviso = None
    if accionables and not ctas:
        aviso = (f"{len(accionables)} elementos accionables con texto y ningún candidato "
                 "a CTA detectado: es un fallo de detección, no una página sin CTA. "
                 "Contrasta con las capturas antes de concluir nada.")

    return {
        "cta": {
            "candidatos": ctas[:8],
            "principal": top,
            "n_sobre_el_pliegue": sum(1 for c in ctas if c["sobre_el_pliegue"]),
            "n_accionables_con_texto": len(accionables),
            "aviso": aviso,
        },
        "competencia_de_atencion": {
            "elementos_salientes_sobre_el_pliegue": len(sobre_pliegue),
            "compiten_con_el_cta": competidores[:5],
            "diagnostico": (
                "El CTA no gana: hay elementos no accionables igual de salientes, "
                "la atención se reparte." if competidores else
                "El CTA es el elemento más saliente sobre el pliegue."),
        },
        "above_the_fold": {
            "alto_pagina_px": alto,
            "pct_visible_sin_scroll": round(FOLD * 100 / alto, 1) if alto else None,
            "h1": (h1.get("text") if h1 else None),
            "h1_sobre_el_pliegue": bool(h1 and h1["box"]["y"] < FOLD),
            "bloques_de_texto": len(en_pliegue),
        },
        "carga_cognitiva": {
            "decisiones_sobre_el_pliegue": decisiones,
            "ley_de_hick": ("alta" if decisiones > 3 else
                            "media" if decisiones > 1 else "baja"),
        },
        "fluidez": {
            "ancho_medida_caracteres": medida,
            "en_rango_optimo_45_75": (45 <= medida <= 75) if medida else None,
        },
        "nota": ("Todo aquí es medición sobre el render, no interpretación. "
                 "Reporta lo observado, nunca un resultado de conversión prometido."),
    }


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("uso: python -m tools.analyze.attention <slug>")
    dump, raw = cargar(sys.argv[1])
    f = escribir(raw, "attention", analizar(dump))
    print(f"attention → {f}")


if __name__ == "__main__":
    main()
