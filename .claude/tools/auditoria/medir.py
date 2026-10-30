"""Mide la arquitectura de web-app y api-core sobre origin/develop.

Uso:
    python .claude/tools/auditoria/medir.py [--fecha AAAA-MM-DD] [--web <commit>] [--api <commit>]

Sin argumentos mide origin/develop de hoy. Con --web/--api mide un commit
pasado (para reconstruir el historial). Cada medición queda en
historial/<fecha>.json; render.py las lee todas.

No instala nada en los repos: las herramientas corren con npx desde el worktree
de auditoría (.worktrees/web-app--auditoria) y api-core se lee con git archive.
Cada herramienta falla por separado: si una no corre, su bloque queda
{"medido": false, "motivo": ...} y el resto sigue.
"""

import argparse
import datetime as dt
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile

AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.abspath(os.path.join(AQUI, "..", "..", ".."))
WEB_REPO = os.path.join(RAIZ, "web-app")
WEB_WT = os.path.join(RAIZ, ".worktrees", "web-app--auditoria")
API_REPO = os.path.join(RAIZ, "api-core")
if not os.path.isdir(API_REPO):  # corrido desde un worktree de AcmeOrg: api-core vive en el checkout principal
    _comun = subprocess.run(["git", "-C", RAIZ, "rev-parse", "--path-format=absolute", "--git-common-dir"],
                            capture_output=True).stdout.decode().strip()
    API_REPO = os.path.join(os.path.dirname(_comun), "api-core")
TMP = os.path.join(tempfile.gettempdir(), "acmeorg-auditoria")
LIMITE_LINEAS = 400
LIMITE_COMPLEJIDAD = 15
NPX = "npx.cmd" if os.name == "nt" else "npx"

API_PROYECTOS = ["Domain", "Application", "Persistence", "Services", "Rest", "Host"]
# Clean Architecture: una capa no conoce a las que están más afuera.
API_PROHIBIDO = {
    "Domain": ["Application", "Persistence", "Services", "Rest", "Host"],
    "Application": ["Persistence", "Services", "Rest", "Host"],
    "Persistence": ["Services", "Rest", "Host"],
    "Services": ["Persistence", "Rest", "Host"],
    "Rest": ["Host"],
}


def run(cmd, cwd, timeout=900):
    r = subprocess.run(cmd, cwd=cwd, capture_output=True, timeout=timeout)
    return r.returncode, r.stdout.decode("utf-8", "replace"), r.stderr.decode("utf-8", "replace")


def git(repo, *args):
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, check=True).stdout.decode().strip()


def fallo_suave(nombre):
    def deco(fn):
        def envuelto(*a, **k):
            try:
                return fn(*a, **k)
            except Exception as e:  # una herramienta rota no tumba el tablero
                print("  [%s] no medido: %s" % (nombre, e))
                return {"medido": False, "motivo": str(e)[:300]}
        return envuelto
    return deco


def es_prod_ts(ruta):
    return (ruta.endswith((".ts", ".tsx")) and not re.search(r"\.test\.tsx?$", ruta)
            and not ruta.endswith("routeTree.gen.ts") and "/testing/" not in ruta
            and not ruta.endswith("test-setup.ts"))


def contar_lineas(ruta):
    with io.open(ruta, encoding="utf-8", errors="replace") as f:
        return sum(1 for _ in f)


# ---------------------------------------------------------------- preparar

def preparar_web(ref):
    git(WEB_REPO, "fetch", "-q", "origin")
    if not os.path.isdir(WEB_WT):
        git(WEB_REPO, "worktree", "add", "--detach", WEB_WT, ref)
    git(WEB_WT, "checkout", "-q", "--detach", ref)
    marca = os.path.join(WEB_WT, "node_modules", ".auditoria-lock")
    lock = io.open(os.path.join(WEB_WT, "package-lock.json"), encoding="utf-8").read()
    if not os.path.exists(marca) or io.open(marca, encoding="utf-8").read() != lock:
        print("  npm ci (cambió package-lock.json)")
        code, _, err = run([NPX.replace("npx", "npm"), "ci", "--silent"], WEB_WT, timeout=1200)
        if code != 0:
            raise RuntimeError("npm ci falló: " + err[-300:])
        io.open(marca, "w", encoding="utf-8").write(lock)
    return git(WEB_WT, "rev-parse", "--short", "HEAD")


def preparar_api(ref):
    git(API_REPO, "fetch", "-q", "origin")
    sha = git(API_REPO, "rev-parse", "--short", ref)
    destino = os.path.join(TMP, "api-core")
    # Carpeta propia de este script, sin enlaces: se puede borrar entera.
    shutil.rmtree(destino, ignore_errors=True)
    os.makedirs(destino)
    tar = subprocess.run(["git", "-C", API_REPO, "archive", ref], capture_output=True, check=True).stdout
    with tarfile.open(fileobj=io.BytesIO(tar)) as t:
        t.extractall(destino)
    return sha, destino


# ---------------------------------------------------------------- web-app

def modulo_web(ruta):
    """Unidad del gráfico de Martin: features/<f>/<capa>, domain/<sub> o carpeta de primer nivel."""
    p = ruta.split("/")
    if len(p) < 3:
        return None
    if p[1] == "features" and len(p) >= 4:
        return "/".join(p[:4]) if len(p) > 4 else "/".join(p[:3])
    if p[1] == "domain" and len(p) >= 4:
        return "/".join(p[:3])
    return "/".join(p[:2])


RE_ABSTRACTO_TS = re.compile(r"^export\s+(declare\s+)?(interface|type)\s+\w+|^export\s+abstract\s+class\s", re.M)
RE_CONCRETO_TS = re.compile(r"^export\s+(default\s+)?(async\s+)?(function|class|const|let|var|enum)\b|^export\s+default\s", re.M)


@fallo_suave("dependency-cruiser")
def medir_dependencias_web():
    cfg = os.path.join(AQUI, ".dependency-cruiser.cjs")
    code, out, err = run([NPX, "-y", "-p", "dependency-cruiser@16", "-p", "typescript@5", "depcruise", "src",
                          "--config", cfg, "--metrics", "--output-type", "json"], WEB_WT)
    if not out.strip():
        raise RuntimeError("sin salida: " + err[-300:])
    d = json.loads(out)
    if not d["modules"]:
        raise RuntimeError("0 módulos analizados")

    # Acoplamiento a nivel de módulo (Martin): Ca = módulos de afuera que dependen de este,
    # Ce = módulos de afuera de los que depende este.
    ca, ce, archivos = {}, {}, {}
    for m in d["modules"]:
        src = m["source"]
        if not src.startswith("src/") or not es_prod_ts(src):
            continue
        mod = modulo_web(src)
        if not mod:
            continue
        archivos.setdefault(mod, set()).add(src)
        for dep in m.get("dependencies", []):
            dst = dep.get("resolved", "")
            if not dst.startswith("src/") or not es_prod_ts(dst):
                continue
            mdst = modulo_web(dst)
            if mdst and mdst != mod:
                ce.setdefault(mod, set()).add(mdst)
                ca.setdefault(mdst, set()).add(mod)

    modulos = []
    for mod, fs in sorted(archivos.items()):
        abst = conc = 0
        for f in fs:
            txt = io.open(os.path.join(WEB_WT, f), encoding="utf-8", errors="replace").read()
            abst += len(RE_ABSTRACTO_TS.findall(txt))
            conc += len(RE_CONCRETO_TS.findall(txt))
        nca, nce = len(ca.get(mod, ())), len(ce.get(mod, ()))
        if nca + nce == 0 or abst + conc == 0:
            continue
        i = nce / (nca + nce)
        a = abst / (abst + conc)
        modulos.append({"nombre": mod.replace("src/", ""), "ca": nca, "ce": nce, "i": round(i, 3),
                        "a": round(a, 3), "d": round(abs(a + i - 1), 3), "archivos": len(fs),
                        "abstractos": abst, "concretos": conc})

    violaciones = []
    for v in d["summary"].get("violations", []):
        violaciones.append({"regla": v["rule"]["name"], "severidad": v["rule"]["severity"],
                            "desde": v["from"], "hacia": v.get("to", ""),
                            "ciclo": [c if isinstance(c, str) else c.get("name", "") for c in v.get("cycle", [])]})
    return {"medido": True, "modulos": modulos, "violaciones": violaciones,
            "archivos_analizados": sum(len(v) for v in archivos.values()),
            "dependencias": d["summary"].get("totalDependenciesCruised", 0)}


@fallo_suave("tamaño web")
def medir_tamano_web():
    grandes, total = [], 0
    for base, _, fs in os.walk(os.path.join(WEB_WT, "src")):
        for f in fs:
            ruta = os.path.relpath(os.path.join(base, f), WEB_WT).replace("\\", "/")
            if not es_prod_ts(ruta):
                continue
            total += 1
            n = contar_lineas(os.path.join(base, f))
            if n > LIMITE_LINEAS:
                grandes.append({"archivo": ruta, "lineas": n})
    return {"medido": True, "total": total, "grandes": sorted(grandes, key=lambda x: -x["lineas"])}


@fallo_suave("complejidad")
def medir_complejidad_web():
    regla = '{"complexity": ["warn", %d]}' % LIMITE_COMPLEJIDAD
    code, out, err = run([NPX, "eslint", "src", "--rule", regla, "--format", "json"], WEB_WT)
    if not out.strip().startswith("["):
        raise RuntimeError("eslint sin JSON: " + err[-300:])
    funciones = []
    for f in json.loads(out):
        ruta = os.path.relpath(f["filePath"], WEB_WT).replace("\\", "/")
        if not es_prod_ts(ruta):
            continue
        for m in f["messages"]:
            if m.get("ruleId") == "complexity":
                n = re.search(r"complexity of (\d+)", m["message"])
                nombre = re.search(r"^(.*?) has a complexity", m["message"])
                funciones.append({"archivo": ruta, "linea": m["line"], "complejidad": int(n.group(1)) if n else 0,
                                  "funcion": nombre.group(1) if nombre else ""})
    return {"medido": True, "limite": LIMITE_COMPLEJIDAD, "tipo": "ciclomática (ESLint)",
            "funciones": sorted(funciones, key=lambda x: -x["complejidad"])}


@fallo_suave("knip")
def medir_codigo_muerto_web():
    code, out, err = run([NPX, "-y", "knip@5", "--reporter", "json", "--no-exit-code"], WEB_WT)
    if not out.strip().startswith("{"):
        raise RuntimeError("knip sin JSON: " + (err or out)[-300:])
    d = json.loads(out)
    archivos = [f for f in d.get("files", []) if es_prod_ts(f)]
    totales = 0
    for base, _, fs in os.walk(os.path.join(WEB_WT, "src")):
        for f in fs:
            ruta = os.path.relpath(os.path.join(base, f), WEB_WT).replace("\\", "/")
            if es_prod_ts(ruta):
                txt = io.open(os.path.join(base, f), encoding="utf-8", errors="replace").read()
                totales += len(RE_ABSTRACTO_TS.findall(txt)) + len(RE_CONCRETO_TS.findall(txt))
    exports = []
    for issue in d.get("issues", []):
        if not es_prod_ts(issue.get("file", "")):
            continue
        for e in issue.get("exports", []) + issue.get("types", []):
            exports.append({"archivo": issue["file"], "nombre": e.get("name", ""), "linea": e.get("line", 0)})
    return {"medido": True, "archivos": archivos, "exports": exports, "exports_totales": totales}


@fallo_suave("jscpd")
def medir_duplicacion(cwd, rutas, formato, ignorar):
    salida = os.path.join(TMP, "jscpd-" + formato)
    shutil.rmtree(salida, ignore_errors=True)
    cmd = [NPX, "-y", "jscpd@4", *rutas, "--reporters", "json", "--output", salida, "--silent",
           "--min-lines", "8", "--format", formato, "--ignore", ignorar]
    run(cmd, cwd)
    reporte = os.path.join(salida, "jscpd-report.json")
    if not os.path.exists(reporte):
        raise RuntimeError("jscpd no generó reporte")
    d = json.load(io.open(reporte, encoding="utf-8"))
    t = d["statistics"]["total"]
    clones = [{"a": c["firstFile"]["name"].replace("\\", "/"), "b": c["secondFile"]["name"].replace("\\", "/"),
               "lineas": c["lines"]} for c in d.get("duplicates", [])]
    return {"medido": True, "porcentaje": round(t["percentage"], 2), "lineas_duplicadas": t["duplicatedLines"],
            "lineas": t["lines"], "clones": sorted(clones, key=lambda x: -x["lineas"])[:15]}


# ---------------------------------------------------------------- api-core

RE_TIPO_CS = re.compile(r"^\s*(?:public|internal)\s+(?:(?:static|sealed|partial|readonly|abstract)\s+)*"
                        r"(class|record|interface|enum|struct)\s+\w+", re.M)
RE_ABSTRACTO_CS = re.compile(r"^\s*(?:public|internal)\s+(?:(?:partial)\s+)*(interface\s+\w+|abstract\s+(?:partial\s+)?class\s+\w+)", re.M)
RE_USING_CS = re.compile(r"^\s*using\s+(?:static\s+)?(\w+)", re.M)


def archivos_cs(raiz, proyecto):
    for base, _, fs in os.walk(os.path.join(raiz, proyecto)):
        if re.search(r"[\\/](bin|obj|Migrations)([\\/]|$)", base):
            continue
        for f in fs:
            if f.endswith(".cs"):
                yield os.path.join(base, f)


@fallo_suave("capas api-core")
def medir_capas_api(raiz):
    refs = {}
    for p in API_PROYECTOS:
        txt = io.open(os.path.join(raiz, p, p + ".csproj"), encoding="utf-8").read()
        refs[p] = sorted({os.path.splitext(os.path.basename(r.replace("\\", "/")))[0]
                          for r in re.findall(r'ProjectReference\s+Include="([^"]+)"', txt)} & set(API_PROYECTOS))
    modulos, violaciones = [], []
    for p in API_PROYECTOS:
        abst = conc = 0
        for f in archivos_cs(raiz, p):
            txt = io.open(f, encoding="utf-8-sig", errors="replace").read()
            tipos = len(RE_TIPO_CS.findall(txt))
            a = len(RE_ABSTRACTO_CS.findall(txt))
            abst += a
            conc += max(tipos - a, 0)
            for u in set(RE_USING_CS.findall(txt)):
                if u in API_PROHIBIDO.get(p, []):
                    violaciones.append({"regla": "%s no depende de %s" % (p, u),
                                        "desde": os.path.relpath(f, raiz).replace("\\", "/"), "hacia": u})
        ce = len(refs[p])
        ca = sum(1 for q in API_PROYECTOS if p in refs[q])
        if ca + ce == 0 or abst + conc == 0:
            continue
        i = ce / (ca + ce)
        a = abst / (abst + conc)
        modulos.append({"nombre": p, "ca": ca, "ce": ce, "i": round(i, 3), "a": round(a, 3),
                        "d": round(abs(a + i - 1), 3), "abstractos": abst, "concretos": conc, "referencias": refs[p]})
    return {"medido": True, "modulos": modulos, "violaciones": violaciones, "referencias": refs}


@fallo_suave("tamaño api-core")
def medir_tamano_api(raiz):
    grandes, total = [], 0
    for p in API_PROYECTOS:
        for f in archivos_cs(raiz, p):
            total += 1
            n = contar_lineas(f)
            if n > LIMITE_LINEAS:
                grandes.append({"archivo": os.path.relpath(f, raiz).replace("\\", "/"), "lineas": n})
    return {"medido": True, "total": total, "grandes": sorted(grandes, key=lambda x: -x["lineas"])}


@fallo_suave("CI api-core")
def estado_tests_arquitectura_api():
    # El workflow "CI" (el que corre api-core.ArchitectureTests) corre en los PRs, no en develop.
    code, out, err = run(["gh", "run", "list", "--workflow", "CI", "--limit", "1",
                          "--json", "conclusion,status,displayTitle,url,createdAt,headBranch"], API_REPO, timeout=60)
    runs = json.loads(out or "[]")
    if not runs:
        raise RuntimeError("sin corridas del workflow CI")
    r = runs[0]
    return {"medido": True, "conclusion": r.get("conclusion") or r.get("status"), "url": r["url"],
            "fecha": r["createdAt"], "rama": r["headBranch"], "titulo": r["displayTitle"],
            "reglas": ["Capas (Application no depende de Persistence)", "DbContext encapsulado",
                       "Handlers con nombre y ubicación correctos", "Controllers con autorización"]}


# Roslyn corre dentro de la carpeta exportada (git archive): se le agregan reglas ahí, nunca en el repo.
_BUILD_API = {}
RE_ADVERTENCIA = re.compile(r"^(?:\s*\d+>)?(.+?)\((\d+),\d+\): warning (\w+): (.*?)(?: \[.*)?$", re.M)
# Tipos que el framework conecta solo (DI, MediatR, MVC, EF): "sin referencias" no significa "sin uso".
RE_CABLEADO = re.compile(r"(Handler|Controller|Registration|Extensions?|Validator)$")


def compilar_api(raiz):
    """Compila Host con CA1502 (umbral 15) y las reglas de código sin uso; devuelve las advertencias."""
    if raiz in _BUILD_API:
        return _BUILD_API[raiz]
    with io.open(os.path.join(raiz, ".editorconfig"), "a", encoding="utf-8") as f:
        f.write("\n[*.cs]\n" + "".join("dotnet_diagnostic.%s.severity = warning\n" % r
                                        for r in ["CA1502", "IDE0051", "IDE0052", "IDE0060", "IDE0005", "CS8019"]))
    io.open(os.path.join(raiz, "CodeMetricsConfig.txt"), "w", encoding="utf-8").write("CA1502: %d\n" % LIMITE_COMPLEJIDAD)
    io.open(os.path.join(raiz, "Directory.Build.targets"), "w", encoding="utf-8").write(
        '<Project><ItemGroup><AdditionalFiles Include="$(MSBuildThisFileDirectory)CodeMetricsConfig.txt" /></ItemGroup></Project>')
    # GenerateDocumentationFile hace que IDE0005 (usings sobrantes) se vea en dotnet build.
    code, out, err = run(["dotnet", "build", os.path.join("Host", "Host.csproj"), "-c", "Release", "-nologo", "-v:n",
                          "-p:TreatWarningsAsErrors=false", "-p:GenerateDocumentationFile=true",
                          "-p:NoWarn=CS1591"], raiz, timeout=1500)
    if code != 0:
        raise RuntimeError("dotnet build falló: " + (out + err)[-300:])
    adv = {}
    for m in RE_ADVERTENCIA.finditer(out):
        ruta = os.path.relpath(m.group(1).strip(), raiz).replace("\\", "/")
        adv[(ruta, int(m.group(2)), m.group(3))] = m.group(4)
    _BUILD_API[raiz] = adv
    return adv


@fallo_suave("complejidad api-core")
def medir_complejidad_api(raiz):
    funciones = []
    for (ruta, linea, regla), msg in compilar_api(raiz).items():
        if regla != "CA1502" or ruta.startswith("api-core."):
            continue
        n = re.search(r"complexity of '(\d+)'", msg)
        nombre = re.search(r"^'([^']+)'", msg)
        funciones.append({"archivo": ruta, "linea": linea, "complejidad": int(n.group(1)) if n else 0,
                          "funcion": nombre.group(1) if nombre else ""})
    return {"medido": True, "limite": LIMITE_COMPLEJIDAD, "tipo": "ciclomática (Roslyn CA1502)",
            "funciones": sorted(funciones, key=lambda x: -x["complejidad"])}


@fallo_suave("código muerto api-core")
def medir_codigo_muerto_api(raiz):
    """Tipos public/internal que ningún otro texto de producción nombra (heurística de texto) más los
    miembros sin uso que Roslyn sí prueba (IDE0051/IDE0052/CS9113/IDE0060). Es una cota inferior: los
    miembros públicos sin uso no se detectan."""
    texto = {}
    for p in API_PROYECTOS:
        for f in archivos_cs(raiz, p):
            texto[os.path.relpath(f, raiz).replace("\\", "/")] = io.open(f, encoding="utf-8-sig", errors="replace").read()
    todo = "\n".join(texto.values())
    exports, sin_uso, cableados = 0, [], 0
    for ruta, txt in texto.items():
        for m in RE_TIPO_CS.finditer(txt):
            nombre = re.match(r"\s*(?:public|internal)\s+(?:(?:static|sealed|partial|readonly|abstract)\s+)*\w+\s+(\w+)", m.group(0)).group(1)
            exports += 1
            if len(re.findall(r"\b%s\b" % nombre, todo)) > 1:  # 1 = su propia declaración
                continue
            if RE_CABLEADO.search(nombre) or "Rest/Controllers/" in ruta or "static class" in m.group(0) and "(this " in txt:
                cableados += 1
                continue
            sin_uso.append({"archivo": ruta, "nombre": nombre, "linea": txt[:m.start()].count("\n") + 1})
    miembros = [{"archivo": r, "linea": l, "regla": g, "mensaje": msg[:120]}
                for (r, l, g), msg in compilar_api(raiz).items()
                if g in ("IDE0051", "IDE0052", "IDE0060", "CS9113") and not r.startswith("api-core.")]
    return {"medido": True, "tipo": "tipos sin referencias (texto) + miembros privados (Roslyn)",
            "exports": sin_uso, "miembros": miembros, "exports_totales": exports, "cableados_omitidos": cableados}


# ---------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fecha", default=dt.date.today().isoformat())
    ap.add_argument("--web", default="origin/develop")
    ap.add_argument("--api", default="origin/develop")
    args = ap.parse_args()
    actual = args.web == "origin/develop" and args.api == "origin/develop"
    salida = os.path.join(AQUI, "historial", args.fecha + ".json")
    os.makedirs(os.path.dirname(salida), exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    print("web-app: preparando worktree de auditoría en %s" % args.web)
    web_sha = preparar_web(args.web)
    print("api-core: exportando %s" % args.api)
    api_sha, api_raiz = preparar_api(args.api)

    print("web-app: dependencias, tamaño, complejidad, código muerto, duplicación")
    web = {
        "sha": web_sha,
        "dependencias": medir_dependencias_web(),
        "tamano": medir_tamano_web(),
        "complejidad": medir_complejidad_web(),
        "codigo_muerto": medir_codigo_muerto_web(),
        "duplicacion": medir_duplicacion(WEB_WT, ["src"], "typescript,tsx",
                                         "**/*.test.ts,**/*.test.tsx,**/routeTree.gen.ts,**/testing/**"),
    }
    print("api-core: capas, tamaño, duplicación, complejidad y código muerto (dotnet build), CI")
    api = {
        "sha": api_sha,
        "capas": medir_capas_api(api_raiz),
        "tamano": medir_tamano_api(api_raiz),
        "duplicacion": medir_duplicacion(api_raiz, API_PROYECTOS, "csharp", "**/Migrations/**,**/bin/**,**/obj/**"),
        # El estado del CI solo tiene sentido para la medición de hoy.
        "complejidad": medir_complejidad_api(api_raiz),
        "codigo_muerto": medir_codigo_muerto_api(api_raiz),
        "tests_arquitectura": estado_tests_arquitectura_api() if actual
        else {"medido": False, "motivo": "Solo se consulta en la medición actual."},
    }
    if not actual:
        git(WEB_WT, "checkout", "-q", "--detach", "origin/develop")
    datos = {"fecha": args.fecha, "medido_el": dt.datetime.now().strftime("%Y-%m-%d %H:%M"),
             "limite_lineas": LIMITE_LINEAS, "web": web, "api": api}
    io.open(salida, "w", encoding="utf-8", newline="\n").write(json.dumps(datos, ensure_ascii=False, indent=1))
    print("Escrito: %s" % salida)


if __name__ == "__main__":
    main()
