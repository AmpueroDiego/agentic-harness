"""Genera el tablero HTML de la auditoría con todo el historial de mediciones.

Uso:
    python .claude/tools/auditoria/render.py [salida.html]

Lee historial/*.json (uno por medición, de medir.py). Se publica como Artifact
con la misma ruta de salida para conservar el enlace.
"""

import glob
import io
import json
import os
import sys

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", "..", ".."))


def main():
    salida = sys.argv[1] if len(sys.argv) > 1 else os.path.join(RAIZ, "auditoria-arquitectura.html")
    mediciones = [json.load(io.open(f, encoding="utf-8"))
                  for f in sorted(glob.glob(os.path.join(AQUI, "historial", "*.json")))]
    if not mediciones:
        sys.exit("No hay mediciones en historial/: corré medir.py primero.")
    datos = json.dumps(mediciones, ensure_ascii=False)
    plantilla = io.open(os.path.join(AQUI, "plantilla.html"), encoding="utf-8").read()
    # "</" dentro del JSON cerraría el <script> que lo contiene.
    html = plantilla.replace("__DATOS__", datos.replace("</", "<\\/"))
    io.open(salida, "w", encoding="utf-8", newline="\n").write(html)
    print("Escrito: %s (%d mediciones)" % (salida, len(mediciones)))


if __name__ == "__main__":
    main()
