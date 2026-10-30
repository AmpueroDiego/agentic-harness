"""Extrae el texto plano (sin llamadas a herramientas) de un transcript de Claude Code.

Uso: python extraer-conversacion.py <transcript.jsonl>
Imprime a stdout, turno por turno, solo los bloques de texto de user/assistant
(excluye isSidechain, tool_use y tool_result) - pensado para pasarle una
conversacion legible a un modelo barato sin gastar contexto del modelo caro.
"""
import io
import json
import sys


def main():
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    ruta = sys.argv[1]
    with open(ruta, "r", encoding="utf-8", errors="replace") as f:
        lineas = f.readlines()

    for linea in lineas:
        try:
            d = json.loads(linea)
        except ValueError:
            continue
        if d.get("isSidechain"):
            continue
        tipo = d.get("type")
        if tipo not in ("user", "assistant"):
            continue
        contenido = (d.get("message") or {}).get("content")
        if isinstance(contenido, str):
            texto = contenido
        elif isinstance(contenido, list):
            texto = "\n".join(
                b.get("text", "") for b in contenido if isinstance(b, dict) and b.get("type") == "text"
            )
        else:
            texto = ""
        texto = texto.strip()
        if texto:
            print(f"[{tipo}] {texto}\n")


if __name__ == "__main__":
    main()
