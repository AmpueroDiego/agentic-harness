"""Vigía de Codex: espera en segundo plano y termina UNA vez, cuando un PR tiene algo que hacer.

Los PRs se quedaban parados con Codex ya respondido porque nadie miraba, y un /loop gasta tokens
en cada vuelta. Esto corre con run_in_background: no gasta nada mientras espera y, al salir, despierta a la sesión.

Uso:  python .claude/scripts/esperar-codex.py [--intervalo 300] [--tope-horas 8] [api-core#101 web-app#124 ...]
      python .claude/scripts/esperar-codex.py --tomar api-core#101 [--pid N] [--horas 3]
      python .claude/scripts/esperar-codex.py --soltar api-core#101
Sin PRs: todos los abiertos de api-core y web-app. Solo lee (gh): nunca responde hilos, ni hace push, ni pide @codex review.
Despierta (exit 0) con una respuesta de código nueva sobre el HEAD o un pedido de más de 30 min sin ella;
también al llegar al tope de horas. Un PR «tomado» (candado de PR o worktree con trabajo sin subir) no se mira.
"""
import argparse
import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

RAIZ = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
WORKTREES = os.path.join(RAIZ, ".worktrees")
LOCKS = os.path.join(RAIZ, ".claude", "locks")
# ESPERAR_CODEX_ESTADO solo para pruebas: así una corrida de prueba no marca respuestas como ya vistas.
ESTADO = os.environ.get("ESPERAR_CODEX_ESTADO") or os.path.join(RAIZ, ".claude", "tools", "supercodex", "esperar-codex-estado.json")
CANDADO_GLOBAL = os.path.join(tempfile.gettempdir(), "esperar-codex.lock")
REPOS = ("api-core", "web-app")
PERDIDA_MIN = 30

Q = """query($r:String!,$n:Int!){repository(owner:"<org>",name:$r){pullRequest(number:$n){
state headRefOid headRefName commits(last:1){nodes{commit{committedDate}}}
reviewThreads(first:100){nodes{isResolved}}
reviews(last:30){nodes{author{login} submittedAt body}}
comments(last:60){nodes{author{login} createdAt body}}}}}"""


# ---------- procesos y candados ----------

def pid_vivo(pid):
    if pid <= 0:
        return False
    if os.name == "nt":
        # En Windows os.kill(pid, 0) MATA el proceso (TerminateProcess): se consulta con la API.
        import ctypes
        k = ctypes.windll.kernel32
        h = k.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
        if not h:
            return False
        codigo = ctypes.c_ulong()
        ok = k.GetExitCodeProcess(h, ctypes.byref(codigo))
        k.CloseHandle(h)
        return bool(ok) and codigo.value == 259  # STILL_ACTIVE
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _leer_dueno(directorio):
    try:
        with open(os.path.join(directorio, "pid"), encoding="utf-8") as f:
            return json.loads(f.read())
    except (OSError, ValueError):
        return None


def _vigente(directorio):
    dueno = _leer_dueno(directorio)
    if dueno is None:
        # Recién creado y aún sin pid (mkdir y escritura no son atómicos juntos): vale un minuto.
        try:
            return time.time() - os.path.getmtime(directorio) < 60
        except OSError:
            return False
    if pid_vivo(int(dueno.get("pid") or 0)):
        return True
    # Sin pid vivo vale hasta su vencimiento: el --tomar desde la CLI muere enseguida y deja solo el plazo.
    return time.time() < float(dueno.get("vence") or 0)


def _tomar_dir(directorio, pid, horas):
    os.makedirs(os.path.dirname(directorio), exist_ok=True)
    for _ in range(2):
        try:
            os.mkdir(directorio)  # mkdir es atómico: el que lo crea, gana.
        except FileExistsError:
            if _vigente(directorio):
                return False
            shutil.rmtree(directorio, ignore_errors=True)  # dueño muerto o vencido: se recupera
            continue
        vence = time.time() + horas * 3600 if horas else 0
        with open(os.path.join(directorio, "pid"), "w", encoding="utf-8") as f:
            json.dump({"pid": pid, "vence": vence, "desde": datetime.datetime.now().isoformat(timespec="seconds")}, f)
        return True
    return False


def _candado_pr(repo, n):
    return os.path.join(LOCKS, f"pr-{repo}-{n}")


def tomar(repo, n, pid=None, horas=3):
    """Marca el PR como tomado. Con pid vivo dura lo que el proceso; sin él, `horas`."""
    return _tomar_dir(_candado_pr(repo, n), os.getpid() if pid is None else pid, horas)


def soltar(repo, n):
    shutil.rmtree(_candado_pr(repo, n), ignore_errors=True)


def pr_con_candado(repo, n):
    d = _candado_pr(repo, n)
    return os.path.isdir(d) and _vigente(d)


# ---------- worktrees ----------

def git(ruta, *args):
    r = subprocess.run(["git", "-C", ruta, *args], capture_output=True, text=True, encoding="utf-8")
    return r.stdout.strip() if r.returncode == 0 else None


def worktree_ocupado(repo, rama):
    """El worktree de esa rama tiene cambios sin commit o commits sin subir: alguien está trabajando ahí."""
    if not os.path.isdir(WORKTREES):
        return None
    for nombre in os.listdir(WORKTREES):
        ruta = os.path.join(WORKTREES, nombre)
        if not nombre.startswith(f"{repo}--") or not os.path.isdir(ruta):
            continue
        if git(ruta, "rev-parse", "--abbrev-ref", "HEAD") != rama:
            continue
        # Solo archivos versionados: logs y node_modules sueltos no son trabajo.
        if git(ruta, "status", "--porcelain", "--untracked-files=no"):
            return f"{nombre}: cambios sin commit"
        remoto = "@{u}" if git(ruta, "rev-parse", "--verify", "-q", "@{u}") else f"origin/{rama}"
        if git(ruta, "rev-parse", "--verify", "-q", remoto):
            sin_subir = int(git(ruta, "rev-list", "--count", f"{remoto}..HEAD") or 0)
            if sin_subir:
                return f"{nombre}: {sin_subir} commit(s) sin subir"
    return None


# ---------- GitHub ----------

def gh(*args):
    r = subprocess.run(["gh", *args], capture_output=True, text=True, encoding="utf-8")
    return r.stdout


def objetivos(lista):
    if lista:
        for a in lista:
            repo, n = a.replace(":", "#").split("#")
            yield repo, int(n)
        return
    for repo in REPOS:
        for pr in json.loads(gh("pr", "list", "-R", f"<org>/{repo}", "--json", "number") or "[]"):
            yield repo, pr["number"]


def leer_pr(repo, n):
    for intento in range(3):
        salida = gh("api", "graphql", "-f", f"query={Q}", "-F", f"r={repo}", "-F", f"n={n}")
        if salida.strip():
            try:
                return json.loads(salida)["data"]["repository"]["pullRequest"]
            except (ValueError, KeyError, TypeError):
                pass
        time.sleep(3 * (intento + 1))
    return None


def es_codex(nodo):
    return "codex" in ((nodo.get("author") or {}).get("login") or "")


def commit_revisado(cuerpo):
    m = re.search(r"Reviewed commit:\*{0,2}\s*`([0-9a-f]{7,40})`", cuerpo)
    return m.group(1) if m else None


def analizar(p):
    """Qué le toca al PR ahora: (evento, detalle) o (None, motivo de espera)."""
    head = p["headRefOid"]
    ultimo = p["commits"]["nodes"][0]["commit"]["committedDate"]
    abiertos = sum(not t["isResolved"] for t in p["reviewThreads"]["nodes"])
    pedidos = sorted(c["createdAt"] for c in p["comments"]["nodes"]
                     if not es_codex(c) and "@codex review" in c["body"])
    # Cada pedido trae dos respuestas a destiempo; solo cuenta la de código, nunca la «Security Review».
    respuestas = []
    for c in p["comments"]["nodes"]:
        if es_codex(c) and "Didn't find any major issues" in c["body"] and "Security Review" not in c["body"]:
            respuestas.append((c["createdAt"], "limpia", commit_revisado(c["body"])))
    for r in p["reviews"]["nodes"]:
        if es_codex(r) and "Security Review" not in (r["body"] or ""):
            respuestas.append((r["submittedAt"], "hallazgos", commit_revisado(r["body"] or "")))
    respuestas.sort()

    def sobre_head(t, sha):
        # El «Reviewed commit» manda; sin él, vale si responde a un pedido posterior al último commit.
        if sha:
            return head.startswith(sha)
        previos = [x for x in pedidos if x <= t]
        return bool(previos) and previos[-1] > ultimo

    pedido = pedidos[-1] if pedidos and pedidos[-1] > ultimo else None
    if pedido and not any(t >= pedido for t, _, _ in respuestas):
        espera = datetime.datetime.now(datetime.timezone.utc) - datetime.datetime.fromisoformat(pedido.replace("Z", "+00:00"))
        minutos = int(espera.total_seconds() // 60)
        if minutos > PERDIDA_MIN:
            return f"perdida@{pedido}", f"pedida hace {minutos // 60} h {minutos % 60} min sin respuesta de código, perdida: re-pedir"
        # Ronda en vuelo: una respuesta vieja no despierta mientras la nueva puede llegar.
        return None, f"pedida hace {minutos} min"
    vigentes = [(t, e) for t, e, sha in respuestas if sobre_head(t, sha)]
    if not vigentes:
        # La revisión automática (al abrir o al pushear) no deja recibo: solo el resumen con el sha revisado.
        for c in p["comments"]["nodes"]:
            m = re.search(r"codex-review-state:v1 (\{.*?\}) -->", c["body"])
            if m and es_codex(c):
                cr = json.loads(m.group(1)).get("code_review", {})
                if cr.get("status") == "completed" and cr.get("commit_sha") == head:
                    vigentes.append((head[:7], "hallazgos" if cr.get("has_any_findings") else "limpia"))
    if not vigentes:
        return None, "sin ronda sobre el HEAD"
    t, e = vigentes[-1]
    detalle = "limpia" if e == "limpia" else f"hallazgos ({abiertos} hilo{'s' if abiertos != 1 else ''} abierto{'s' if abiertos != 1 else ''})"
    return f"{e}@{t}", detalle


# ---------- estado visto ----------

def cargar_estado():
    try:
        with open(ESTADO, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def guardar_estado(estado):
    os.makedirs(os.path.dirname(ESTADO), exist_ok=True)
    tmp = ESTADO + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=1)
    os.replace(tmp, ESTADO)


# ---------- vigía ----------

def pasada(lista, estado):
    novedades, tomados = [], []
    for repo, n in objetivos(lista):
        clave = f"{repo}#{n}"
        if pr_con_candado(repo, n):
            tomados.append(f"{clave} (candado)")
            continue
        p = leer_pr(repo, n)
        if p is None or p["state"] != "OPEN":
            continue
        ocupado = worktree_ocupado(repo, p["headRefName"])
        if ocupado:
            tomados.append(f"{clave} ({ocupado})")
            continue
        # Con el «✅ 2 rondas… sobre <sha>» del HEAD ya está listo: no hay nada que hacer con Codex.
        if any(not es_codex(c) and "✅" in c["body"] and p["headRefOid"][:7] in c["body"] for c in p["comments"]["nodes"]):
            continue
        evento, detalle = analizar(p)
        if evento and evento not in estado.get(clave, {}).get("vistos", []):
            novedades.append((clave, p["headRefOid"][:7], evento, detalle))
    return novedades, tomados


def vigilar(args):
    os.makedirs(os.path.dirname(CANDADO_GLOBAL), exist_ok=True)
    if not _tomar_dir(CANDADO_GLOBAL, os.getpid(), 0):
        dueno = _leer_dueno(CANDADO_GLOBAL) or {}
        print(f"Ya hay un vigía corriendo (pid {dueno.get('pid', '?')}, desde {dueno.get('desde', '?')}). "
              f"No se lanza otro: cuando ese termine, despierta a su sesión.")
        return 1
    try:
        fin = time.time() + args.tope_horas * 3600
        estado = cargar_estado()
        while True:
            novedades, tomados = pasada(args.prs, estado)
            if novedades:
                print("| PR | HEAD | Qué hay |")
                print("|---|---|---|")
                for clave, sha, evento, detalle in novedades:
                    print(f"| {clave} | `{sha}` | {detalle} |")
                    vistos = estado.setdefault(clave, {}).setdefault("vistos", [])
                    vistos.append(evento)
                    del vistos[:-20]  # solo hace falta recordar lo reciente
                if tomados:
                    print(f"\nNo mirados por estar tomados: {', '.join(tomados)}.")
                guardar_estado(estado)
                return 0
            if time.time() + args.intervalo > fin:
                print(f"Tope de {args.tope_horas:g} h sin novedades de Codex"
                      + (f"; tomados: {', '.join(tomados)}." if tomados else "."))
                return 0
            time.sleep(args.intervalo)
    finally:
        shutil.rmtree(CANDADO_GLOBAL, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser(description="Espera respuestas de Codex y termina cuando hay algo que hacer.")
    ap.add_argument("prs", nargs="*", help="repo#n (sin nada: todos los abiertos de api-core y web-app)")
    ap.add_argument("--intervalo", type=int, default=300, help="segundos entre pasadas")
    ap.add_argument("--tope-horas", type=float, default=8)
    ap.add_argument("--tomar", metavar="REPO#N")
    ap.add_argument("--soltar", metavar="REPO#N")
    ap.add_argument("--pid", type=int, default=0, help="con --tomar: proceso dueño (sin él, vale --horas)")
    ap.add_argument("--horas", type=float, default=3, help="con --tomar: vencimiento si el dueño no está vivo")
    args = ap.parse_args()
    if args.tomar or args.soltar:
        repo, n = (args.tomar or args.soltar).replace(":", "#").split("#")
        if args.soltar:
            soltar(repo, int(n))
            print(f"{repo}#{n} soltado.")
            return 0
        if tomar(repo, int(n), pid=args.pid, horas=args.horas):
            print(f"{repo}#{n} tomado.")
            return 0
        print(f"{repo}#{n} ya está tomado por otro: {_leer_dueno(_candado_pr(repo, int(n)))}")
        return 1
    return vigilar(args)


if __name__ == "__main__":
    sys.exit(main())
