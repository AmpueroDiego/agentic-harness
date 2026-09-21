"""Medicion aproximada de texto para diagramas draw.io.

draw.io renderiza con Helvetica. No podemos medir el texto real sin un
navegador, asi que usamos una tabla de anchos por caracter calibrada contra
Helvetica y *sobreestimamos* a proposito: una caja de mas es un problema
cosmetico, una caja de menos es texto encima del vecino.

Una caja mezcla tamanos (titulo 13px negrita, detalle 11px gris), asi que
`lineas_con_formato` desarma el HTML y devuelve cada linea con SU tamano.
Medir todo a 12px daba falsos positivos en el validador.
"""

import re

# Ancho de cada caracter como fraccion del tamano de fuente (Helvetica).
_ANGOSTOS = "iljI|.,:;'`!()[]{}/\\ft-"
_ANCHOS = "mMW@%"
_MAYUS = "ABCDEFGHJKLNOPQRSTUVXYZ"

PX_TITULO = 13
PX_CUERPO = 11
PX_ETIQUETA = 10
PX_BASE = 12


def _factor(c: str) -> float:
    if c == " ":
        return 0.30
    if c in _ANGOSTOS:
        return 0.34
    if c in _ANCHOS:
        return 0.92
    if c in _MAYUS:
        return 0.70
    if c.isdigit():
        return 0.58
    if not c.isascii():          # tildes, enies, flechas, vinetas
        return 0.62
    return 0.56


def ancho_texto(txt: str, px: int = PX_BASE, negrita: bool = False) -> float:
    """Ancho en pixeles que ocuparia `txt` en una sola linea."""
    base = sum(_factor(c) for c in txt) * px
    return base * (1.06 if negrita else 1.0)


def envolver(txt: str, ancho_px: float, px: int = PX_BASE, negrita: bool = False):
    """Parte `txt` en lineas que quepan en `ancho_px`. Devuelve lista de lineas.

    Si una palabra sola no entra (una URL larga, un nombre de clase), se corta
    a la fuerza: preferimos partir feo a desbordar.
    """
    lineas, actual = [], ""
    for palabra in txt.split(" "):
        tentativa = f"{actual} {palabra}".strip()
        if ancho_texto(tentativa, px, negrita) <= ancho_px or not actual:
            if ancho_texto(tentativa, px, negrita) > ancho_px and not actual:
                trozo = ""
                for c in palabra:
                    if ancho_texto(trozo + c, px, negrita) > ancho_px and trozo:
                        lineas.append(trozo)
                        trozo = c
                    else:
                        trozo += c
                actual = trozo
                continue
            actual = tentativa
        else:
            lineas.append(actual)
            actual = palabra
    if actual:
        lineas.append(actual)
    return lineas or [""]


def alto_linea(px: int = PX_BASE) -> float:
    """Alto de una linea de texto de `px` pixeles, con su interlineado."""
    return px * 1.45


ALTO_LINEA = alto_linea(PX_BASE)


_ENTIDADES = (("&lt;", "<"), ("&gt;", ">"), ("&quot;", '"'),
              ("&nbsp;", " "), ("&#10;", "\n"), ("&amp;", "&"))


def _desescapar(t: str) -> str:
    for ent, ch in _ENTIDADES:
        t = t.replace(ent, ch)
    return t


def texto_plano(html: str) -> str:
    """El value de un mxCell (que puede traer HTML) como texto plano,
    conservando los saltos de linea."""
    if not html:
        return ""
    t = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    t = re.sub(r"<hr[^>]*>", "\n", t, flags=re.I)
    t = re.sub(r"</(div|p|li)>", "\n", t, flags=re.I)
    t = re.sub(r"<[^>]+>", "", t)
    return _desescapar(t)


_TAG = re.compile(r"<(/?)(\w+)([^>]*)>")
_SIZE = re.compile(r"font-size:\s*(\d+)", re.I)


def lineas_con_formato(html: str, px_base: int = PX_BASE):
    """Desarma un label HTML en [(linea, px, negrita)].

    Sigue los tamanos declarados con `font-size:` y el estado de negrita, que
    es lo que permite medir una caja con titulo 13px y detalle 11px sin inflar
    ni subestimar.
    """
    if not html:
        return []
    lineas, actual = [], []
    px_pila, negrita = [px_base], 0
    pos = 0
    for m in _TAG.finditer(html):
        texto = html[pos:m.start()]
        if texto:
            actual.append((_desescapar(texto), px_pila[-1], negrita > 0))
        pos = m.end()
        cierre, tag, attrs = m.group(1), m.group(2).lower(), m.group(3)
        if tag in ("br", "hr"):
            lineas.append(actual)
            actual = []
        elif tag in ("b", "strong"):
            negrita += -1 if cierre else 1
            negrita = max(0, negrita)
        elif tag in ("span", "font", "div", "i", "em"):
            if cierre:
                if len(px_pila) > 1:
                    px_pila.pop()
            else:
                s = _SIZE.search(attrs)
                px_pila.append(int(s.group(1)) if s else px_pila[-1])
    resto = html[pos:]
    if resto:
        actual.append((_desescapar(resto), px_pila[-1], negrita > 0))
    lineas.append(actual)

    salida = []
    for trozos in lineas:
        txt = "".join(t for t, _, _ in trozos)
        px = max([p for _, p, _ in trozos] or [px_base])
        neg = any(n for _, _, n in trozos)
        salida.append((txt, px, neg))
    return salida
