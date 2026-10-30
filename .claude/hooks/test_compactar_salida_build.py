"""Tests de compactar-salida-build.py. Correr: python .claude/hooks/test_compactar_salida_build.py

Lo que se verifica es una sola cosa, desde varios angulos: que comprimir NUNCA
pierda un fallo. Un hook que esconde un error rojo es peor que no tener hook.
"""
import importlib.util
import json
import os
import subprocess
import sys

# La consola de Windows es cp1252: sin esto, imprimir un check o una tilde
# revienta el test aunque la comprobacion haya pasado.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

AQUI = os.path.dirname(os.path.abspath(__file__))
HOOK = os.path.join(AQUI, "compactar-salida-build.py")

_spec = importlib.util.spec_from_file_location("cs", HOOK)
_cs = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cs)

fallos = []


def check(nombre, cond, detalle=""):
    if cond:
        print("  OK   %s" % nombre)
    else:
        print("  FALLA %s %s" % (nombre, detalle))
        fallos.append(nombre)


def correr_hook(cmd, stdout, resultado=None):
    """`resultado=None` usa la forma esperada; se le puede pasar otra para
    probar que el hook tolera las tres formas que `tool_result` puede tomar.

    El payload va en UTF-8 a proposito: es la unica forma de ejercitar el
    `reconfigure` del hook. Con `text=True` a secas, Python usaria la
    codificacion local en los dos extremos y el bug nunca aparaceria.
    """
    if resultado is None:
        resultado = {"stdout": stdout, "stderr": "", "interrupted": False}
    entrada = json.dumps({
        "hook_event_name": "PostToolUse",
        "tool_name": "Bash",
        "tool_input": {"command": cmd},
        "tool_result": resultado,
    }, ensure_ascii=False)
    p = subprocess.run(
        [sys.executable, HOOK],
        input=entrada.encode("utf-8"),
        capture_output=True,
    )
    return p.stdout.decode("utf-8", "replace").strip()


# --- salida sintetica de dotnet test en verde, con un warning y un fallo ---
verde = "\n".join(
    ["Determining projects to restore..."]
    + ["  Restored C:/repo/Proyecto%d.csproj (in 1 sec)." % i for i in range(10)]
    + ["C:/repo/Domain/Entidad.cs(41,17): warning CS0168: se declaro la variable 'x'"]
    + ["  Domain -> C:/repo/Domain/bin/Debug/net10.0/Domain.dll"]
    + ["Build succeeded."]
    + ["  Passed Tests.Entidad.ActualizarEntidad_Ok [3 ms]" for _ in range(300)]
    + ["  Failed Tests.Canal.ResolverPorCodigo_Falla [12 ms]"]
    + ["  Error Message:"]
    + ["   Assert.Equal() Failure: Expected 'CANAL', Actual 'canal'"]
    + ["  Stack Trace:"]
    + ["     at Tests.Canal.ResolverPorCodigo_Falla() in Canal.cs:line 44"]
    + ["Failed!  - Failed: 1, Passed: 300, Skipped: 0, Total: 301, Duration: 2 s"]
)

print("dotnet test con 1 fallo entre 300 verdes:")
salida = correr_hook("dotnet test api-core.Tests", verde)
check("el hook emitio JSON", salida.startswith("{"))
nuevo = json.loads(salida)["updatedOutput"]["stdout"] if salida else ""
check("conserva el test fallido", "ResolverPorCodigo_Falla" in nuevo)
check("conserva el mensaje del assert", "Expected 'CANAL'" in nuevo)
check("conserva el stack", "Canal.cs:line 44" in nuevo)
check("conserva el warning CS0168", "CS0168" in nuevo)
check("conserva el resumen final", "Failed: 1, Passed: 300" in nuevo)
check("descarta los tests en verde", "Passed Tests.Entidad.ActualizarEntidad_Ok" not in nuevo)
check("descarta el ruido de restore", "Determining projects" not in nuevo)
check(
    "achica de verdad",
    len(nuevo.splitlines()) < 40,
    "(quedaron %d lineas de %d)" % (len(nuevo.splitlines()), len(verde.splitlines())),
)

print("\ndotnet build que falla:")
roto = "\n".join(
    ["Determining projects to restore..."]
    + ["  Restored X.csproj" for _ in range(80)]
    + ["C:/repo/Application/Handler.cs(12,9): error CS0103: el nombre 'canal' no existe"]
    + ["Build FAILED.", "    1 Error(s)"]
)
nuevo = json.loads(correr_hook("dotnet build", roto))["updatedOutput"]["stdout"]
check("conserva el error de compilacion", "CS0103" in nuevo)
check("conserva Build FAILED", "Build FAILED" in nuevo)

print("\nvitest con un FAIL (payload en UTF-8, con checks reales):")
vitest = "\n".join(
    [" ✓ src/a%d.test.ts (12) 4ms" % i for i in range(200)]
    + [" FAIL src/canal.test.ts > resuelve por código",
       "AssertionError: expected 'CANAL' to be 'canal'",
       " Test Files  1 failed | 40 passed (41)",
       " Tests  1 failed | 262 passed (263)"]
)
salida = correr_hook("npx vitest run", vitest)
check("no se atraganto con el UTF-8 del payload", salida.startswith("{"))
nuevo = json.loads(salida)["updatedOutput"]["stdout"] if salida else ""
check("conserva el FAIL", "FAIL src/canal.test.ts" in nuevo)
check("conserva el AssertionError", "AssertionError" in nuevo)
check("conserva la tilde de 'codigo'", "código" in nuevo)
check("conserva el resumen de vitest", "1 failed | 262 passed" in nuevo)
check("descarta las lineas de check en verde", "✓ src/a1.test.ts" not in nuevo)

print("\nadvertencia de analizador repetida (el caso real de api-core):")
xunit = "\n".join(
    ["Build succeeded."]
    + ["C:/repo/Tests/Entidad%d.cs(%d,19): warning xUnit1051: Calls to methods which "
       "accept CancellationToken should use TestContext.Current.CancellationToken "
       "to allow test cancellation to be more responsive. "
       "(https://xunit.net/xunit.analyzers/rules/xUnit1051) [C:/repo/Tests.csproj]"
       % (i, 20 + i) for i in range(207)]
    + ["    207 Warning(s)", "    0 Error(s)"]
)
nuevo = json.loads(correr_hook("dotnet build", xunit))["updatedOutput"]["stdout"]
check("conserva una copia entera de la advertencia", "xUnit1051: Calls to methods" in nuevo)
check("conserva el link de la regla", "xunit.analyzers/rules/xUnit1051" in nuevo)
check("resume las 206 repeticiones", "en 206 lugares mas" in nuevo)
check("dice donde saltan las repetidas", "Entidad1.cs(21,19)" in nuevo)
check(
    "no repite el parrafo 207 veces",
    nuevo.count("Calls to methods which accept") == 1,
    "(aparecio %d veces)" % nuevo.count("Calls to methods which accept"),
)
check(
    "achica mas del 90%",
    len(nuevo) < len(xunit) * 0.1,
    "(%d chars de %d)" % (len(nuevo), len(xunit)),
)

print("\nformas alternativas de tool_result (la doc no fija cual es):")
salida = correr_hook("dotnet test", verde, resultado={"output": verde})
check("dict con `output` en vez de `stdout`", "ResolverPorCodigo_Falla" in salida)
check(
    "reemplaza la misma clave que leyo",
    json.loads(salida)["updatedOutput"].get("output", "").startswith("[salida comprimida"),
)
salida = correr_hook("dotnet test", verde, resultado=verde)
check("tool_result como texto pelado", "ResolverPorCodigo_Falla" in salida)
check(
    "devuelve texto, no dict, cuando entro texto",
    isinstance(json.loads(salida)["updatedOutput"], str),
)

print("\ncasos en que NO debe tocar nada:")
check("salida corta pasa intacta", correr_hook("dotnet build", "Build succeeded.\n") == "")
check(
    "comando que no es build/test pasa intacto",
    correr_hook("git log --oneline", verde) == "",
)
check(
    "dotnet run pasa intacto (la salida en vivo es el punto)",
    correr_hook("dotnet run --project Host", verde) == "",
)
os.environ["SHUNT_DISABLE"] = "1"
p = subprocess.run(
    [sys.executable, HOOK],
    input=json.dumps({"tool_input": {"command": "dotnet test"},
                      "tool_result": {"stdout": verde}}),
    capture_output=True, text=True, env={**os.environ},
)
check("SHUNT_DISABLE=1 lo apaga", p.stdout.strip() == "")

print()
if fallos:
    print("FALLARON %d: %s" % (len(fallos), ", ".join(fallos)))
    sys.exit(1)
print("Todo en verde.")
