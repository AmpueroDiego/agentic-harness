"""Tests de aviso-contexto.py: python .claude/hooks/test_aviso_contexto.py"""
import json
import os
import subprocess
import sys
import tempfile

HOOK = os.path.join(os.path.dirname(__file__), "aviso-contexto.py")


def correr(lineas, umbral="200"):
    with tempfile.NamedTemporaryFile("w", suffix=".jsonl", delete=False, encoding="utf-8") as f:
        f.write("\n".join(json.dumps(l) for l in lineas))
    r = subprocess.run([sys.executable, HOOK], input=json.dumps({"transcript_path": f.name}),
                       capture_output=True, text=True, encoding="utf-8",
                       env=dict(os.environ, AVISO_CONTEXTO_K=umbral))
    os.unlink(f.name)
    return r


def llamada(leido, lateral=False):
    return {"type": "assistant", "isSidechain": lateral,
            "message": {"usage": {"input_tokens": 10, "cache_creation_input_tokens": 1000, "cache_read_input_tokens": leido}}}


casos = [
    ("bajo el umbral no avisa", [llamada(100_000)], "", 0),
    ("sobre el umbral avisa", [llamada(250_000)], "251K", 0),
    ("mira la última llamada, no la mayor", [llamada(300_000), llamada(50_000)], "", 0),
    ("ignora subagentes", [llamada(50_000), llamada(900_000, lateral=True)], "", 0),
    ("transcript vacío no falla", [], "", 0),
]
fallas = 0
for nombre, lineas, esperado, codigo in casos:
    r = correr(lineas)
    ok = r.returncode == codigo and (esperado in r.stdout if esperado else r.stdout.strip() == "")
    if ok and esperado:
        ok = json.loads(r.stdout)["hookSpecificOutput"]["hookEventName"] == "UserPromptSubmit"
    print(("OK   " if ok else "FALLA"), nombre, "" if ok else repr(r.stdout + r.stderr))
    fallas += not ok
r = subprocess.run([sys.executable, HOOK], input="no es json", capture_output=True, text=True)
print(("OK   " if r.returncode == 0 and not r.stdout else "FALLA"), "entrada rota no frena el prompt")
fallas += not (r.returncode == 0 and not r.stdout)
sys.exit(1 if fallas else 0)
