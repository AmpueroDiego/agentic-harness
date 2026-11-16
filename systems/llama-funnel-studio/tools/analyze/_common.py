"""Utilidades compartidas por los analizadores."""
from __future__ import annotations

import json
import re
from pathlib import Path

# ---------------------------------------------------------------- carga

def raw_de(slug: str) -> Path:
    p = Path("casos") / slug / "raw"
    if not p.exists():
        raise SystemExit(f"No existe {p}. Corre antes:  python tools/capture.py <url>")
    return p


def cargar(slug: str) -> tuple[dict, Path]:
    raw = raw_de(slug)
    f = raw / "elements.json"
    if not f.exists():
        raise SystemExit(f"Falta {f}. La captura no llegó a completarse.")
    return json.loads(f.read_text(encoding="utf-8")), raw


def escribir(raw: Path, nombre: str, datos: dict) -> Path:
    d = raw / "analysis"
    d.mkdir(exist_ok=True)
    f = d / f"{nombre}.json"
    f.write_text(json.dumps(datos, ensure_ascii=False, indent=1), encoding="utf-8")
    return f


# ---------------------------------------------------------------- color

_RGB = re.compile(r"rgba?\(\s*([\d.]+)[,\s]+([\d.]+)[,\s]+([\d.]+)(?:[,\s/]+([\d.]+))?")


def rgb(s: str | None) -> tuple[int, int, int, float] | None:
    """'rgb(228, 87, 46)' -> (228, 87, 46, 1.0). None si es transparente."""
    if not s:
        return None
    m = _RGB.search(s)
    if not m:
        return None
    r, g, b = (int(float(m.group(i))) for i in (1, 2, 3))
    a = float(m.group(4)) if m.group(4) is not None else 1.0
    return (r, g, b, a)


def hexa(c: tuple[int, int, int, float]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*c[:3])


_PARADA = re.compile(r"rgba?\([^)]*\)")


def fondo(e: dict, min_alpha: float = 0.05) -> tuple[int, int, int, float] | None:
    """Fondo efectivo de un elemento: color sólido o gradiente resuelto.

    Un gradiente vive en `background-image` y deja `background-color` en
    `rgba(0,0,0,0)`. Leer solo `bg` hace **invisible** todo elemento con fondo
    degradado, que suele ser justo el CTA y el fondo de la página. Pasó en
    creativos-lat-framer: los ocho botones desaparecieron del análisis de
    atención y la superficie dominante salió blanca en una página negra.

    Los gradientes se resuelven promediando sus paradas visibles, que es lo que
    el ojo percibe como color de la superficie.

    **La alfa devuelta importa:** un halo radial al 30 % es un elemento enorme
    que no pinta una superficie. Quien mida área debe ponderar por ella, o los
    acentos decorativos se comen el recuento del fondo real.
    """
    c = rgb(e.get("bg"))
    if c and c[3] > min_alpha:
        return c

    img = e.get("bgImage") or ""
    if "gradient" not in img:
        return None
    paradas = [p for p in (rgb(m) for m in _PARADA.findall(img))
               if p and p[3] > min_alpha]
    if not paradas:
        return None
    n = len(paradas)
    return (sum(p[0] for p in paradas) // n,
            sum(p[1] for p in paradas) // n,
            sum(p[2] for p in paradas) // n,
            round(sum(p[3] for p in paradas) / n, 3))


def tapado_por_descendiente(e: dict, els: list[dict], umbral: float = 0.92) -> bool:
    """¿Otro elemento con fondo propio cubre casi toda la caja de este?

    Sin esto, un contenedor gigante sin fondo visible se lleva el recuento de
    superficie por delante del bloque que de verdad pinta la página.
    """
    b = e["box"]
    area = b["w"] * b["h"]
    if area <= 0:
        return False
    for o in els:
        if o is e or fondo(o) is None:
            continue
        c = o["box"]
        # El otro tiene que ser casi tan grande como este y caber dentro de él:
        # es un descendiente que lo cubre, no un ancestro que lo contiene.
        if c["w"] * c["h"] < area * umbral:
            continue
        if (b["x"] <= c["x"] and b["y"] <= c["y"]
                and b["x"] + b["w"] >= c["x"] + c["w"]
                and b["y"] + b["h"] >= c["y"] + c["h"]):
            return True
    return False


def _lin(v: float) -> float:
    v /= 255
    return v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4


def luminancia(c: tuple[int, int, int, float]) -> float:
    r, g, b = (_lin(x) for x in c[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a: tuple, b: tuple) -> float:
    """Ratio WCAG entre dos colores. 1.0 = idénticos, 21.0 = negro sobre blanco."""
    la, lb = luminancia(a), luminancia(b)
    hi, lo = max(la, lb), min(la, lb)
    return round((hi + 0.05) / (lo + 0.05), 2)


def _lab(c: tuple) -> tuple[float, float, float]:
    r, g, b = (_lin(x) for x in c[:3])
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = (0.2126 * r + 0.7152 * g + 0.0722 * b)
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = f(x), f(y), f(z)
    return (116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz))


def delta_e(a: tuple, b: tuple) -> float:
    """Distancia perceptual CIE76. >10 = claramente distintos a simple vista."""
    la, lb = _lab(a), _lab(b)
    return round(sum((x - y) ** 2 for x, y in zip(la, lb)) ** 0.5, 2)


# ---------------------------------------------------------------- números

def px(s: str | None) -> float | None:
    if not s:
        return None
    m = re.match(r"^(-?[\d.]+)px$", s.strip())
    return float(m.group(1)) if m else None


def escala(valores: list[float]) -> dict:
    """Detecta si una serie de tamaños sigue una razón geométrica."""
    v = sorted(set(round(x, 1) for x in valores if x))
    if len(v) < 3:
        return {"valores": v, "razon": None, "sistematica": False}
    razones = [round(v[i + 1] / v[i], 3) for i in range(len(v) - 1) if v[i]]
    media = sum(razones) / len(razones)
    disp = max(abs(r - media) for r in razones)
    return {
        "valores": v,
        "razon": round(media, 3),
        # Si las razones no se desvían mucho de la media, hay escala real.
        "sistematica": disp < 0.18 and len(v) <= 9,
        "n_valores": len(v),
    }


def visibles(dump: dict, min_area: int = 100) -> list[dict]:
    return [e for e in dump["elements"] if e["box"]["w"] * e["box"]["h"] >= min_area]
