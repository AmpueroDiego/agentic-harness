#!/usr/bin/env python3
"""Corre todos los analizadores sobre un caso.   python -m tools.analyze <slug>"""
import sys, traceback
from . import design, attention, trackers, text, flow
from ._common import cargar, raw_de, escribir

# La salida lleva flechas y acentos; la consola de Windows es cp1252 por defecto.
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

def main():
    if len(sys.argv) < 2:
        raise SystemExit("uso: python -m tools.analyze <slug>")
    slug = sys.argv[1]
    raw = raw_de(slug)
    dump, _ = cargar(slug)
    tareas = [
        ("design",    lambda: design.analizar(dump)),
        ("attention", lambda: attention.analizar(dump)),
        ("text",      lambda: text.analizar(dump)),
        ("flow",      lambda: flow.analizar(dump, raw)),
        ("trackers",  lambda: trackers.analizar(raw)),
    ]
    for nombre, fn in tareas:
        try:
            escribir(raw, nombre, fn())
            print(f"  ok   {nombre}")
        except Exception as e:
            print(f"  FALLA {nombre}: {e}")
            traceback.print_exc(limit=1)
    print(f"\nresultados en {raw/'analysis'}")

if __name__ == "__main__":
    main()
