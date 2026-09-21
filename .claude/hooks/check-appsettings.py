"""Compatibilidad stdin: la lista de reglas vive en revisar_secretos.py."""
from pathlib import Path
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from revisar_secretos import redactar, revisar_json, una_linea


if __name__ == "__main__":
    sys.stdin.reconfigure(encoding="utf-8-sig", errors="replace")
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    fallos = revisar_json(sys.stdin.read())
    for ruta, valor in fallos[:5]:
        print(f'  {una_linea(ruta)} = "{redactar(valor)}"')
    sys.exit(1 if fallos else 0)
