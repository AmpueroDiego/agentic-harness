#!/usr/bin/env python3
"""
design.py — sistema visual → alimenta a `disenador`

Paleta por rol y por superficie ocupada, escala tipográfica con su razón,
escala de espaciado, forma y elevación. Todo determinista: ningún modelo
adivina un color que un parser lee con certeza.

    python -m tools.analyze.design <slug>
"""
from __future__ import annotations

import sys
from collections import Counter, defaultdict

from ._common import (cargar, escribir, rgb, hexa, px, escala, visibles,
                      contraste, fondo, tapado_por_descendiente)


def _accionable(e: dict) -> bool:
    cls = (e.get("cls") or "").lower()
    return (e["tag"] in ("button", "a")
            or "btn" in cls or "button" in cls or "cta" in cls)


def analizar(dump: dict) -> dict:
    els = visibles(dump)

    # --- paleta por superficie: distingue el dominante del acento -------------
    # Se cuenta el fondo efectivo (sólido o gradiente) y se descartan los
    # contenedores que otro elemento cubre por completo: si no, el cascarón del
    # constructor se lleva el recuento por delante del bloque que pinta la web.
    area_fondo: Counter = Counter()
    area_texto: Counter = Counter()
    for e in els:
        a = e["box"]["w"] * e["box"]["h"]
        c = fondo(e)
        if c and not tapado_por_descendiente(e, els):
            # Ponderar por opacidad: un halo translúcido no pinta superficie.
            area_fondo[hexa(c)] += a * c[3]
        if e.get("text"):
            t = rgb(e.get("color"))
            if t:
                area_texto[hexa(t)] += len(e["text"])

    total = sum(area_fondo.values()) or 1
    fondos = [{"hex": h, "superficie_pct": round(a * 100 / total, 2)}
              for h, a in area_fondo.most_common(12)]
    textos = [{"hex": h, "peso_texto": n} for h, n in area_texto.most_common(8)]

    # El acento es un color de poca superficie que aparece sobre todo en
    # elementos accionables. Buscarlo ahí y no en la lista general.
    acc: Counter = Counter()
    for e in els:
        txt = (e.get("text") or "").lower()
        clicable = (e["tag"] in ("button", "a")
                    or "btn" in (e.get("cls") or "").lower()
                    or "button" in (e.get("cls") or "").lower())
        if clicable and txt:
            c = fondo(e)
            if c:
                acc[hexa(c)] += 1
    acento = acc.most_common(3)

    # --- tipografía -----------------------------------------------------------
    familias: Counter = Counter()
    tamanos: Counter = Counter()
    pesos: Counter = Counter()
    for e in els:
        if not e.get("text"):
            continue
        fam = (e.get("font") or "").split(",")[0].strip().strip('"\'')
        if fam:
            familias[fam] += 1
        s = px(e.get("size"))
        if s:
            tamanos[s] += 1
        w = e.get("weight")
        if w:
            pesos[w] += 1

    # Jerarquía real por nivel de encabezado.
    jer = defaultdict(list)
    for e in els:
        if e["tag"] in ("h1", "h2", "h3", "h4", "p", "li", "span"):
            s = px(e.get("size"))
            if s:
                jer[e["tag"]].append((s, e.get("weight"), px(e.get("lh"))))
    jerarquia = {}
    for tag, vs in jer.items():
        s = Counter(v[0] for v in vs).most_common(1)[0][0]
        w = Counter(v[1] for v in vs).most_common(1)[0][0]
        jerarquia[tag] = {"size_px": s, "weight": w}

    # --- espaciado ------------------------------------------------------------
    huecos = []
    for e in els:
        for campo in ("pad", "margin", "gap"):
            for parte in (e.get(campo) or "").split():
                v = px(parte)
                if v and v > 0:
                    huecos.append(v)
    frec = Counter(huecos)
    comunes = sorted(v for v, _ in frec.most_common(10))
    base = None
    for cand in (4, 8, 6, 5, 10):
        if comunes and sum(1 for v in comunes if v % cand == 0) / len(comunes) > 0.7:
            base = cand
            break

    # --- forma y elevación ----------------------------------------------------
    radios = Counter(e.get("radius") for e in els if e.get("radius") and e["radius"] != "0px")
    sombras = Counter(e["shadow"] for e in els if e.get("shadow"))

    # Una lista global de radios no dice qué forma tiene cada cosa, y quien la
    # lee rellena el hueco con la convención que le suene — "los botones serán
    # los de radio píldora". Aquí eso era falso dos veces seguidas. El dato de
    # a quién pertenece cada radio ya está en el volcado: se conserva en vez de
    # promediarlo. Separar por accionable/no accionable es estructural, así que
    # vale igual en cualquier página.
    r_acc: Counter = Counter()
    r_resto: Counter = Counter()
    for e in els:
        r = e.get("radius")
        if not r or r == "0px":
            continue
        (r_acc if _accionable(e) else r_resto)[r] += 1

    # --- consistencia: ¿hay sistema o improvisación? --------------------------
    esc_tipo = escala([s for s, _ in tamanos.most_common(12)])
    consistencia = {
        "tamanos_distintos": len(tamanos),
        "familias_distintas": len(familias),
        "radios_distintos": len(radios),
        "veredicto": ("sistema" if len(tamanos) <= 8 and len(familias) <= 3
                      else "improvisación"),
        "nota": ("Más de 8 tamaños de texto o más de 3 familias significa que no hay "
                 "escala tipográfica: hay decisiones sueltas. No inventes un rigor "
                 "que el original no tenía."),
    }

    # --- contraste del texto principal ---------------------------------------
    fondo_dom = rgb("rgb(" + ",".join(
        str(int(x, 16)) for x in
        (fondos[0]["hex"][1:3], fondos[0]["hex"][3:5], fondos[0]["hex"][5:7])) + ")"
    ) if fondos else None
    texto_dom = rgb("rgb(" + ",".join(
        str(int(x, 16)) for x in
        (textos[0]["hex"][1:3], textos[0]["hex"][3:5], textos[0]["hex"][5:7])) + ")"
    ) if textos else None

    return {
        "paleta": {
            "fondos_por_superficie": fondos,
            "textos_por_peso": textos,
            "acento_en_accionables": [{"hex": h, "n": n} for h, n in acento],
            "contraste_texto_fondo": (contraste(texto_dom, fondo_dom)
                                      if texto_dom and fondo_dom else None),
        },
        "tipografia": {
            "familias": [{"nombre": f, "n": n} for f, n in familias.most_common(6)],
            "escala": esc_tipo,
            "pesos": [{"peso": w, "n": n} for w, n in pesos.most_common(6)],
            "jerarquia": jerarquia,
        },
        "espaciado": {
            "unidad_base_px": base,
            "valores_comunes": comunes,
            "sistematico": base is not None,
        },
        "forma": {
            "radios": [{"valor": r, "n": n} for r, n in radios.most_common(5)],
            "radios_en_accionables": [{"valor": r, "n": n}
                                      for r, n in r_acc.most_common(5)],
            "radios_en_resto": [{"valor": r, "n": n}
                                for r, n in r_resto.most_common(5)],
            "nota_radios": ("`radios` es el recuento global y no dice qué forma tiene "
                            "cada cosa. Para hablar de botones usa `radios_en_accionables`: "
                            "el radio píldora suele pertenecer a etiquetas, no a los CTA."),
            "sombras": [{"valor": s[:80], "n": n} for s, n in sombras.most_common(4)],
            "niveles_elevacion": len(sombras),
        },
        "consistencia": consistencia,
    }


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("uso: python -m tools.analyze.design <slug>")
    slug = sys.argv[1]
    dump, raw = cargar(slug)
    f = escribir(raw, "design", analizar(dump))
    print(f"design → {f}")


if __name__ == "__main__":
    main()
