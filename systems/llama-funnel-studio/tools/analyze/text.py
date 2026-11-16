#!/usr/bin/env python3
"""
text.py — métrica del lenguaje → alimenta a `linguista`

Longitud de frase, densidad léxica, persona gramatical, campo semántico,
microcopy. Da los números; el especialista interpreta el registro.

    python -m tools.analyze.text <slug>
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter

from ._common import cargar, escribir

VACIAS = set("""
a al algo ante antes aqui asi aun cada como con contra cual cuando de del desde donde
dos e el ella ellas ello ellos en entre era eran es esa ese eso esta estan este esto
estos fue fueron ha han hasta hay la las le les lo los mas me mi mientras muy nada ni
no nos o os otra otro para pero poco por porque que se ser si sin sobre solo son su
sus tambien tan te tiene todo tras un una uno unos y ya
""".split())

YO = re.compile(r"\b(nuestro|nuestra|nosotros|somos|ofrecemos|te ayudamos)\b", re.I)
TU = re.compile(r"\b(tu|tus|tienes|puedes|quieres|necesitas|conseguí|lograrás)\b", re.I)
USTED = re.compile(r"\b(usted|su empresa|puede usted|le ayudamos)\b", re.I)

CTA_MICRO = re.compile(r"^(ver|leer|saber|empezar|comprar|quiero|acceder|reservar|"
                       r"descargar|enviar|continuar|siguiente|suscribir)", re.I)


def analizar(dump: dict) -> dict:
    textos = [e["text"] for e in dump["elements"] if e.get("text")]
    cuerpo = " ".join(textos)
    palabras = re.findall(r"[a-záéíóúñü]+", cuerpo.lower())

    # --- métrica de frase -----------------------------------------------------
    frases = [f.strip() for f in re.split(r"[.!?…]+", cuerpo) if len(f.strip()) > 3]
    largos = [len(f.split()) for f in frases]
    media = round(sum(largos) / len(largos), 1) if largos else 0
    desv = round((sum((x - media) ** 2 for x in largos) / len(largos)) ** 0.5, 1) if largos else 0

    # --- densidad léxica ------------------------------------------------------
    contenido = [p for p in palabras if p not in VACIAS and len(p) > 2]
    densidad = round(len(contenido) / len(palabras), 3) if palabras else 0

    # --- campo semántico: los términos que construyen el mundo ---------------
    frec = Counter(contenido)
    campo = [{"termino": t, "n": n} for t, n in frec.most_common(25) if n > 1]

    # --- persona gramatical ---------------------------------------------------
    personas = {"nosotros": len(YO.findall(cuerpo)),
                "tu": len(TU.findall(cuerpo)),
                "usted": len(USTED.findall(cuerpo))}
    dominante = max(personas, key=personas.get) if any(personas.values()) else None

    # --- encabezados: la fórmula del titular vive aquí -----------------------
    heads = dump["doc"].get("headings", [])
    h1 = [h["text"] for h in heads if h["level"] == 1]
    palabras_h1 = len(h1[0].split()) if h1 else None

    # --- microcopy ------------------------------------------------------------
    botones = [b["text"] for b in dump["doc"].get("buttons", [])]
    placeholders = []
    for f in dump["doc"].get("forms", []):
        for c in f.get("fields", []):
            if c.get("placeholder"):
                placeholders.append(c["placeholder"])

    # --- señales de nivel de lectura -----------------------------------------
    largas = sum(1 for p in palabras if len(p) > 9)
    pct_largas = round(largas * 100 / len(palabras), 1) if palabras else 0

    return {
        "volumen": {
            "palabras": len(palabras),
            "bloques_de_texto": len(textos),
            "frases": len(frases),
        },
        "frase": {
            "longitud_media": media,
            "desviacion": desv,
            "ritmo": ("uniforme" if desv < 5 else "variado"),
            "mas_larga": max(largos) if largos else 0,
        },
        "densidad_lexica": {
            "valor": densidad,
            "lectura": ("densa" if densidad > 0.55 else
                        "conversacional" if densidad < 0.45 else "media"),
        },
        "persona_gramatical": {"conteo": personas, "dominante": dominante},
        "campo_semantico": campo,
        "titular": {
            "h1": h1[0] if h1 else None,
            "palabras": palabras_h1,
            "lleva_cifra": bool(h1 and re.search(r"\d", h1[0])),
            "n_h1": len(h1),
        },
        "jerarquia_encabezados": Counter(h["level"] for h in heads),
        "microcopy": {
            "botones": botones[:20],
            "botones_con_verbo_de_accion": sum(1 for b in botones if CTA_MICRO.match(b)),
            "placeholders": placeholders[:12],
        },
        "legibilidad": {
            "pct_palabras_largas": pct_largas,
            "señal": ("técnico" if pct_largas > 18 else "accesible"),
        },
        "idioma_declarado": dump["doc"].get("lang"),
        "nota": ("En Patrones transferibles va la FÓRMULA, nunca la frase. "
                 "Estos números describen cómo está escrito, no qué dice."),
    }


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("uso: python -m tools.analyze.text <slug>")
    dump, raw = cargar(sys.argv[1])
    f = escribir(raw, "text", analizar(dump))
    print(f"text → {f}")


if __name__ == "__main__":
    main()
