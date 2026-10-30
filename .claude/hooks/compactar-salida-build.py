"""PostToolUse(Bash) - comprime la salida de builds y suites de tests antes de
que entre al contexto del agente.

Los dos hooks de lectura (`check-file-size.py` / `check-bash-read.py`) solo
interceptan `Read` y `cat`: la salida en vivo de un subproceso nunca pasa por
ahi. Una corrida de `dotnet test` en verde mete 648 lineas de "Passed ..." al
contexto del coder y otra vez al de QA, sin aportar nada que el resumen final
no diga.

Que se conserva SIEMPRE (la regla que manda: nunca esconder un fallo):
  - cualquier linea con `error` o `warning`
  - `Build succeeded` / `Build FAILED`, los resumenes `Passed!` / `Failed!`
  - nombres de tests fallidos, `Assert`, `Expected`, `Actual`, `Stack Trace`
  - los marcos de stack (acotados a MAX_STACK por bloque)
  - las primeras 3 y las ultimas TAIL lineas (ahi vive el resumen)

Que se descarta: el ruido de restore de NuGet, los `-> ruta.dll` por proyecto,
los tests individuales que pasaron (`Passed Nombre.Del.Test`) y los `v` de
vitest.

Si la salida es corta (< SHUNT_BUILD_MIN_LINES) no toca nada. Ante cualquier
error propio, sale en silencio y la salida original pasa intacta: un hook que
falla nunca debe romper el comando ni ocultar su resultado.

Variables: SHUNT_BUILD_MIN_LINES (default 60), SHUNT_BUILD_MAX_LINES (200),
SHUNT_DISABLE=1 lo apaga entero.
"""
import json
import os
import re
import sys

# Comandos cuya salida vale la pena comprimir. Deliberadamente NO incluye
# `dotnet run` ni `npm run dev`: ahi la salida en vivo es el punto.
COMANDOS_RE = re.compile(
    r"\b("
    r"dotnet\s+(build|test|restore)"
    r"|npm\s+(run\s+)?test"
    r"|yarn\s+test"
    r"|npx\s+vitest"
    r"|vitest(\s+run)?"
    r"|npm\s+run\s+build"
    r")\b",
    re.IGNORECASE,
)

CONSERVAR_RE = re.compile(
    r"error"
    r"|warning"
    r"|Build succeeded"
    r"|Build FAILED"
    r"|Passed!"
    r"|Failed!"
    r"|Assert"
    r"|Expected"
    r"|Actual"
    r"|Received"
    r"|Stack Trace"
    r"|Test Files"
    r"|Unhandled"
    r"|FAIL\b"
    r"|\bskipped\b"
    r"|^\s*Failed\s"
    r"|^\s*[x×✗]\s",
    re.IGNORECASE | re.MULTILINE,
)

# Ganan sobre CONSERVAR_RE: ruido conocido que igual matchearia.
DESCARTAR_RE = re.compile(
    r"^\s*Determining projects to restore"
    r"|^\s*Restored\s"
    r"|^\s*All projects are up-to-date"
    r"|^\s*Passed\s+[A-Za-z_]"          # test individual en verde (no `Passed!`)
    r"|^\s*[✓√]\s"                       # vitest en verde
    r"|->\s+\S+\.dll$"
)

MARCO_STACK_RE = re.compile(r"^\s+at\s+\S")
MAX_STACK = 12

# Una advertencia de analizador (xUnit1051, CS8604, NU1510...) se repite una vez
# por cada sitio que la dispara, arrastrando cada vez su explicacion entera y su
# URL. Medido el 2026-09-22 en api-core: 207 de 254 lineas de un `dotnet build`
# limpio eran la MISMA xUnit1051, ~24K tokens de los ~29K de la salida.
WARNING_RE = re.compile(r"^(?P<sitio>.*?)(?P<resto>:?\s*warning\s+\w+\d+\s*:.*)$", re.I)
SITIO_RE = re.compile(r"([^\\/]+\(\d+,\d+\))\s*$")
MAX_SITIOS = 15


def _deduplicar_warnings(lineas):
    """Deja la primera aparicion entera de cada advertencia y resume el resto
    como una lista de sitios. No pierde ni el texto ni donde salta: pierde las
    206 copias del mismo parrafo.
    """
    vistas = {}
    for i, linea in enumerate(lineas):
        m = WARNING_RE.match(linea)
        if not m:
            continue
        clave = re.sub(r"\s*\[[^\]]*\]\s*$", "", m.group("resto")).strip()
        s = SITIO_RE.search(m.group("sitio"))
        vistas.setdefault(clave, []).append((i, s.group(1) if s else None))

    copias = set()          # indices a descartar
    resumen_tras = {}       # indice de la primera -> linea que la resume
    for apariciones in vistas.values():
        if len(apariciones) < 2:
            continue
        sitios = [s for _, s in apariciones[1:] if s]
        texto = "    ... la misma advertencia en %d lugar%s mas" % (
            len(apariciones) - 1, "es" if len(apariciones) > 2 else "",
        )
        if sitios:
            muestra = ", ".join(sitios[:MAX_SITIOS])
            if len(sitios) > MAX_SITIOS:
                muestra += ", +%d mas" % (len(sitios) - MAX_SITIOS)
            texto += ": " + muestra
        resumen_tras[apariciones[0][0]] = texto
        copias.update(idx for idx, _ in apariciones[1:])
    return copias, resumen_tras


def _comprimir(texto, min_lineas, max_lineas):
    lineas = texto.splitlines()
    if len(lineas) < min_lineas:
        return None

    total = len(lineas)
    tail = 15
    conservar = set(range(0, min(3, total)))
    conservar.update(range(max(0, total - tail), total))

    stack_seguidos = 0
    for i, linea in enumerate(lineas):
        if MARCO_STACK_RE.match(linea):
            stack_seguidos += 1
            if stack_seguidos <= MAX_STACK:
                conservar.add(i)
            continue
        stack_seguidos = 0
        if DESCARTAR_RE.search(linea):
            continue
        if CONSERVAR_RE.search(linea):
            conservar.add(i)

    # El ruido conocido gana sobre el "primeras 3 / ultimas 15": esas dos son
    # heuristicas para no perder el resumen, no una razon para dejar pasar
    # 8 lineas de tests en verde o el restore de NuGet.
    conservar = {i for i in conservar if not DESCARTAR_RE.search(lineas[i])}

    copias, resumen_tras = _deduplicar_warnings(lineas)
    conservar -= copias

    if len(conservar) >= total:
        return None

    salida = []
    omitidas = 0
    for i, linea in enumerate(lineas):
        if i in conservar:
            if omitidas:
                salida.append("    ... %d lineas omitidas ..." % omitidas)
                omitidas = 0
            salida.append(linea)
            if i in resumen_tras:
                salida.append(resumen_tras[i])
        elif i in copias:
            pass  # ya resumida bajo su primera aparicion
        else:
            omitidas += 1
    if omitidas:
        salida.append("    ... %d lineas omitidas ..." % omitidas)

    if len(salida) > max_lineas:
        mitad = max_lineas // 2
        recorte = len(salida) - 2 * mitad
        salida = (
            salida[:mitad]
            + ["    ... %d lineas mas, recortadas por tamano ..." % recorte]
            + salida[-mitad:]
        )

    cabecera = (
        "[salida comprimida por compactar-salida-build.py: %d de %d lineas. "
        "Se conservaron errores, warnings, tests fallidos y el resumen. "
        "Para verla entera: repetir el comando redirigiendo a un archivo "
        "(`> build.log 2>&1`) y leerlo con offset/limit.]"
    ) % (len(salida), total)

    return cabecera + "\n" + "\n".join(salida)


def _volcar_forma(resultado):
    """SHUNT_BUILD_DEBUG=1: anota que forma real tiene `tool_result`.

    Existe para una sola pregunta, la unica que los tests no pueden responder:
    si el hook no comprime nada despues de instalarlo, ¿es porque la salida
    era corta o porque la clave no es `stdout`?
    """
    try:
        destino = os.path.join(
            os.environ.get("TEMP", "."), "shunt-build-forma.txt"
        )
        with open(destino, "a", encoding="utf-8") as f:
            claves = sorted(resultado) if isinstance(resultado, dict) else "-"
            f.write("%s claves=%s\n" % (type(resultado).__name__, claves))
    except Exception:
        pass


def main():
    if os.environ.get("SHUNT_DISABLE") == "1":
        return 0

    # PowerShell entrega el payload en UTF-8, pero en Windows stdin se abre con
    # la codificacion local (cp1252). Sin esto, un `v` de vitest o una tilde de
    # `dotnet test` rompen el json.load y el hook falla-abierto justo en las
    # salidas para las que existe. Ver la seccion de UTF-8 de CLAUDE.md.
    try:
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0

    try:
        cmd = (payload.get("tool_input") or {}).get("command", "") or ""
        if not COMANDOS_RE.search(cmd):
            return 0

        resultado = payload.get("tool_result")

        if os.environ.get("SHUNT_BUILD_DEBUG") == "1":
            _volcar_forma(resultado)

        # La forma exacta de `tool_result` para Bash no esta documentada, asi
        # que se toleran las tres que puede tomar en vez de asumir una: dict
        # con `stdout`, dict con `output`, o el texto pelado.
        clave = None
        if isinstance(resultado, str):
            stdout = resultado
        elif isinstance(resultado, dict):
            for k in ("stdout", "output", "content"):
                if isinstance(resultado.get(k), str):
                    clave, stdout = k, resultado[k]
                    break
            else:
                return 0
        else:
            return 0

        if not stdout.strip():
            return 0

        min_lineas = int(os.environ.get("SHUNT_BUILD_MIN_LINES", "60"))
        max_lineas = int(os.environ.get("SHUNT_BUILD_MAX_LINES", "200"))

        comprimido = _comprimir(stdout, min_lineas, max_lineas)
        if comprimido is None:
            return 0

        if clave is None:
            nuevo = comprimido
        else:
            nuevo = dict(resultado)
            nuevo[clave] = comprimido
        print(json.dumps({
            "hookSpecificOutput": {"hookEventName": "PostToolUse"},
            "updatedOutput": nuevo,
        }))
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
