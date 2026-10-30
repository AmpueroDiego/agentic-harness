"""Lista los comentarios de Codex de un PR sin respuesta nuestra o sin nuestro 👍 (el responsable, 2026-10-13).
Uso: python supercodex-atendidos.py <dueño/repo> <pr> <login>. Sin salida = todo atendido."""
import json, subprocess, sys

sys.stdout.reconfigure(encoding="utf-8")  # la consola de Windows (cp1252) no imprime 👍

repo, pr, yo = sys.argv[1:4]

def gh(ruta):
    r = subprocess.run(["gh", "api", ruta, "--paginate"], capture_output=True, text=True, encoding="utf-8")
    if r.returncode:
        sys.exit(f"gh api {ruta}: {r.stderr.strip()}")
    return json.loads(r.stdout.replace("][", ",") or "[]")

comentarios = gh(f"repos/{repo}/pulls/{pr}/comments")
respondidos = {c.get("in_reply_to_id") for c in comentarios if c["user"]["login"] == yo}
for c in comentarios:
    if c.get("in_reply_to_id") or "codex" not in c["user"]["login"].lower():
        continue
    pulgar = any(r["content"] == "+1" and r["user"]["login"] == yo
                 for r in gh(f"repos/{repo}/pulls/comments/{c['id']}/reactions"))
    falta = [n for n, ok in (("respuesta", c["id"] in respondidos), ("👍", pulgar)) if not ok]
    if falta:
        print(c["id"], "sin " + " ni ".join(falta))
