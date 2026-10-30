#!/usr/bin/env python3
"""Anota una ronda de Codex en rondas-codex.tsv y hace cumplir el techo de 8 rondas sin 2 limpias seguidas.

  python .claude/tools/supercodex/registrar_ronda.py <repo> <tarjeta> <PASS|FINDINGS> [--pr N]
      [--bloqueantes N] [--no-bloqueantes N] [--resumen "P2 ..."] [--prompt base-diff+foco]
  python .claude/tools/supercodex/registrar_ronda.py --tope <repo> <tarjeta o #PR>     (solo cuenta, no escribe)

El número de ronda sale solo (r1, r2...). Las rondas se cuentan por repo + tarjeta (o #PR) en total:
un merge de develop limpio no reinicia el conteo. Desde la 8.ª, si las 2 últimas no son PASS, imprime
TOPE en stderr y sale 3 (la fila igual queda anotada): parar y pedir confirmación al responsable.
"""
import argparse
import datetime
import os
import sys

TSV = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rondas-codex.tsv")
TECHO = 8  # 5 es lo normal; de 6 a 8 solo con merges o refactors intermedios (supercodex.md)
CABECERA = "fecha\thora\ttarjeta\tronda\tveredicto\tbloqueantes\tno_bloqueantes\tprompt\tresumenes"


def filas_de(repo, clave):
    """Filas cuyo campo tarjeta («web-app <card-id> #<n>») trae el repo y la clave como palabras."""
    if not os.path.exists(TSV):
        return []
    out = []
    for linea in open(TSV, encoding="utf-8"):
        c = linea.rstrip("\r\n").split("\t")
        if len(c) >= 5 and c[0] != "fecha" and {repo, clave} <= set(c[2].split()):
            out.append(c)
    return out


def tope(repo, clave):
    """True si ya se llegó al techo sin 2 limpias seguidas al final."""
    filas = filas_de(repo, clave)
    limpias = [c[4] == "PASS" for c in filas[-2:]]
    if len(filas) >= TECHO and not (len(limpias) == 2 and all(limpias)):
        print(f"TOPE: {TECHO} rondas sin 2 limpias en {repo} {clave} ({len(filas)} anotadas). "
              "Parar y pedir confirmación al responsable.", file=sys.stderr)
        return True
    return False


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
    if len(sys.argv) == 4 and sys.argv[1] == "--tope":
        return 3 if tope(sys.argv[2], sys.argv[3]) else 0

    p = argparse.ArgumentParser(description="Anota una ronda de Codex en rondas-codex.tsv")
    p.add_argument("repo")
    p.add_argument("tarjeta", help="shortLink de la tarjeta")
    p.add_argument("veredicto", choices=["PASS", "FINDINGS"])
    p.add_argument("--pr", type=int)
    p.add_argument("--bloqueantes", type=int, default=0)
    p.add_argument("--no-bloqueantes", type=int, default=0)
    p.add_argument("--resumen", default="", help="hallazgos, separados por «; »")
    p.add_argument("--prompt", default="base-diff+foco", help="versión del contexto (bitacora-mejoras-codex.md)")
    a = p.parse_args()

    previas = filas_de(a.repo, a.tarjeta)
    n = 1 + max((int(c[3][1:]) for c in previas if c[3][1:].isdigit()), default=0)
    ahora = datetime.datetime.now()
    campo = " ".join([a.repo, a.tarjeta] + ([f"#{a.pr}"] if a.pr else []))
    fila = [ahora.strftime("%Y-%m-%d"), ahora.strftime("%H:%M"), campo, f"r{n}", a.veredicto,
            str(a.bloqueantes), str(a.no_bloqueantes), a.prompt, " ".join(a.resumen.split())]
    nuevo = not os.path.exists(TSV)
    with open(TSV, "a", encoding="utf-8") as f:  # fin de línea del sistema, como las filas que ya tiene
        f.write((CABECERA + "\n" if nuevo else "") + "\t".join(fila) + "\n")
    print("\t".join(fila))
    return 3 if tope(a.repo, a.tarjeta) else 0


if __name__ == "__main__":
    sys.exit(main())
