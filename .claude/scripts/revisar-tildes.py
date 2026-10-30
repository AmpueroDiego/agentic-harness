"""Detecta tildes/eñes corrompidas que Codex en Windows deja al escribir ("D??a" por "Día").

Revisa las líneas agregadas del diff y los archivos nuevos. El operador `??` de TS lleva espacios; una `??`
pegada a letras por ambos lados, el carácter U+FFFD o el mojibake de UTF-8 leído como Latin-1 (U+00C3 o U+00C2 seguidos de otro carácter alto)
es corrupción. También avisa si un archivo tocado no es UTF-8 válido (guardado en Latin-1, visto el 19/10 con
luna). Sale con 1 si encuentra algo.
Uso: python revisar-tildes.py <RAIZ>
"""
import re
import subprocess
import sys

MALO = re.compile(r"[A-Za-z\u00c0-\u00ff]\?\?[A-Za-z\u00c0-\u00ff]|\ufffd|\u00c3[\u0080-\u00bf]|\u00c2[\u00a0-\u00bf]")
EXT = (".ts", ".tsx", ".cs", ".json", ".md", ".css", ".html")


def git(raiz, *args):
    return subprocess.run(["git", "-C", raiz, *args], capture_output=True, text=True, encoding="utf-8", errors="replace").stdout


def main():
    raiz = sys.argv[1]
    hallazgos = []
    for linea in git(raiz, "diff", "-U0").splitlines():
        if linea.startswith("+") and not linea.startswith("+++") and MALO.search(linea):
            hallazgos.append(linea)
    for f in git(raiz, "ls-files", "-o", "--exclude-standard").splitlines():
        if f.endswith(EXT):
            try:
                for n, linea in enumerate(open(f"{raiz}/{f}", encoding="utf-8", errors="replace"), 1):
                    if MALO.search(linea):
                        hallazgos.append(f"{f}:{n}: {linea.strip()}")
            except OSError:
                pass
    tocados = git(raiz, "diff", "--name-only").splitlines() + git(raiz, "ls-files", "-o", "--exclude-standard").splitlines()
    for f in tocados:
        if f.endswith(EXT):
            try:
                open(f"{raiz}/{f}", "rb").read().decode("utf-8")
            except UnicodeDecodeError as e:
                hallazgos.append(f"{f}: no es UTF-8 válido (byte 0x{e.object[e.start]:02x} en la posición {e.start}; ¿guardado en Latin-1?)")
            except OSError:
                pass
    if hallazgos:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # la consola cp1252 no imprime U+FFFD
        print("TILDES CORRUPTAS:")
        print("\n".join(h[:200] for h in hallazgos[:20]))
        sys.exit(1)
    print("tildes ok")


main()
