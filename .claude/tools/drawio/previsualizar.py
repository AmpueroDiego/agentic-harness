"""Renderiza un .drawio a SVG, para poder mirarlo sin abrir draw.io.

Para que sirve: un .drawio no se ve en un telefono ni se pega en un chat. Un
SVG se abre en cualquier navegador. Tambien sirve para revisar el resultado sin
salir de la terminal.

Es una *previsualizacion*, no un render fiel: entiende el vocabulario de estilos
que emite `generar.py` (rectangulos, cilindros, actores, elipses, bandas de
grupo y flechas ortogonales), no el catalogo completo de draw.io. El archivo que
manda sigue siendo el .drawio.

Uso:
    python previsualizar.py archivo.drawio [-o carpeta_salida]
    python previsualizar.py archivo.drawio --pagina 5
"""

import argparse
import os
import re
import sys
import xml.etree.ElementTree as ET

from metricas import PX_BASE, alto_linea, ancho_texto, lineas_con_formato
from validar import leer_pagina, polilinea

for _flujo in (sys.stdout, sys.stderr):
    try:
        _flujo.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

MARGEN = 30
FUENTE = ("Helvetica, Arial, sans-serif")


def _est(estilo, clave, defecto=None):
    m = re.search(rf"(?:^|;){re.escape(clave)}=([^;]*)", estilo)
    return m.group(1) if m else defecto


def _tiene(estilo, palabra):
    return re.search(rf"(?:^|;){re.escape(palabra)}(?:=1)?(?:;|$)", estilo) is not None


def esc(t):
    return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def dibujar_caja(c, salida):
    est = c.estilo
    if est.startswith("text;"):
        return          # una celda de texto no tiene caja: solo su texto
    relleno = _est(est, "fillColor", "#FFFFFF")
    borde = _est(est, "strokeColor", "#000000")
    grosor = _est(est, "strokeWidth", "1")
    if relleno == "none":
        relleno = "none"
    if borde == "none":
        borde = "none"

    if "shape=umlActor" in est:
        # proporciones del umlActor de draw.io, escaladas al alto real de la
        # caja: con medidas fijas la figura invadia el nombre que va debajo
        cx, cy, h = c.x + c.w / 2, c.y, c.h
        r, brazos = h * 0.14, c.w * 0.5
        salida.append(
            f'<g stroke="{borde}" stroke-width="1.5" fill="none">'
            f'<circle cx="{cx:.0f}" cy="{cy + r:.0f}" r="{r:.0f}"/>'
            f'<line x1="{cx:.0f}" y1="{cy + 2 * r:.0f}" x2="{cx:.0f}" y2="{cy + h * 0.66:.0f}"/>'
            f'<line x1="{cx - brazos:.0f}" y1="{cy + h * 0.4:.0f}" x2="{cx + brazos:.0f}" y2="{cy + h * 0.4:.0f}"/>'
            f'<line x1="{cx:.0f}" y1="{cy + h * 0.66:.0f}" x2="{cx - brazos:.0f}" y2="{cy + h:.0f}"/>'
            f'<line x1="{cx:.0f}" y1="{cy + h * 0.66:.0f}" x2="{cx + brazos:.0f}" y2="{cy + h:.0f}"/>'
            f"</g>")
        return
    if "ellipse" in est:
        salida.append(
            f'<ellipse cx="{c.x + c.w / 2:.0f}" cy="{c.y + c.h / 2:.0f}" '
            f'rx="{c.w / 2:.0f}" ry="{c.h / 2:.0f}" fill="{relleno}" '
            f'stroke="{borde}" stroke-width="{grosor}"/>')
        return
    if "shape=cylinder3" in est:
        tapa = 12
        salida.append(
            f'<path d="M{c.x:.0f},{c.y + tapa:.0f} '
            f'a{c.w / 2:.0f},{tapa} 0 0 1 {c.w:.0f},0 '
            f'v{c.h - 2 * tapa:.0f} '
            f'a{c.w / 2:.0f},{tapa} 0 0 1 -{c.w:.0f},0 z" '
            f'fill="{relleno}" stroke="{borde}" stroke-width="{grosor}"/>'
            f'<path d="M{c.x:.0f},{c.y + tapa:.0f} '
            f'a{c.w / 2:.0f},{tapa} 0 0 0 {c.w:.0f},0" '
            f'fill="none" stroke="{borde}" stroke-width="{grosor}"/>')
        return
    radio = 6 if "rounded=1" in est else 0
    salida.append(
        f'<rect x="{c.x:.0f}" y="{c.y:.0f}" width="{c.w:.0f}" '
        f'height="{c.h:.0f}" rx="{radio}" fill="{relleno}" stroke="{borde}" '
        f'stroke-width="{grosor}"/>')


def dibujar_texto(c, salida):
    if not c.valor:
        return
    est = c.estilo
    px_estilo = int(float(_est(est, "fontSize", str(PX_BASE))))
    negrita_estilo = _est(est, "fontStyle") == "1"
    lineas = [(t, px, neg or negrita_estilo)
              for t, px, neg in lineas_con_formato(c.valor, px_estilo) if t.strip()]
    if not lineas:
        return
    color_base = _est(est, "fontColor", "#1F2933")
    alineado = _est(est, "align", "center")
    vertical = _est(est, "verticalAlign", "middle")
    afuera = "verticalLabelPosition=bottom" in est

    alto_total = sum(alto_linea(px) for _, px, _ in lineas)
    if afuera:
        y = c.y + c.h + alto_linea(lineas[0][1])
    elif vertical == "top":
        y = c.y + float(_est(est, "spacingTop", "6")) + lineas[0][1]
    else:
        y = c.y + (c.h - alto_total) / 2 + lineas[0][1]

    if alineado == "left" and not afuera:
        x = c.x + float(_est(est, "spacingLeft", "6")) + 4
        anclaje = "start"
    else:
        x = c.x + c.w / 2
        anclaje = "middle"

    if _est(est, "labelBackgroundColor") not in (None, "none"):
        salida.append(
            f'<rect x="{c.x:.0f}" y="{c.y:.0f}" width="{c.w:.0f}" height="{c.h:.0f}" '
            f'fill="{_est(est, "labelBackgroundColor")}" stroke="none"/>')

    for txt, px, neg in lineas:
        # el color de cada linea sale del span que la envuelve; el titulo (13px
        # negrita) va siempre en tinta, el detalle en gris
        # el color vigente es el ultimo declarado antes del texto: con un
        # detalle envuelto en varias lineas, las de abajo siguen dentro del
        # mismo span gris aunque no vengan pegadas a su apertura
        pos = c.valor.find(esc(txt))
        previos = re.findall(r'color:(#[0-9A-Fa-f]{6})', c.valor[:pos]) if pos >= 0 else []
        color = previos[-1] if previos else color_base
        salida.append(
            f'<text x="{x:.0f}" y="{y:.0f}" font-family="{FUENTE}" '
            f'font-size="{px}" fill="{color}" text-anchor="{anclaje}"'
            + (' font-weight="bold"' if neg else "")
            + f">{esc(txt)}</text>")
        y += alto_linea(px)


def ruta_ortogonal(fl, por_id):
    """Reconstruye el recorrido de una flecha, respetando los anclajes."""
    o, d = por_id.get(fl["origen"]), por_id.get(fl["destino"])
    if not o or not d:
        # flecha sin cajas (mensaje de secuencia, linea de vida): su recorrido
        # son los puntos declarados, tal cual
        if fl.get("p_origen") and fl.get("p_destino"):
            return [fl["p_origen"]] + fl["puntos"] + [fl["p_destino"]]
        return []
    est = fl["estilo"]

    def ancla(caja, kx, ky):
        fx = _est(est, kx)
        fy = _est(est, ky)
        if fx is None or fy is None:
            return (caja.x + caja.w / 2, caja.y + caja.h / 2)
        return (caja.x + caja.w * float(fx), caja.y + caja.h * float(fy))

    p0 = ancla(o, "exitX", "exitY")
    p1 = ancla(d, "entryX", "entryY")
    medios = fl["puntos"]
    if medios:
        pts = [p0]
        for mx, my in medios:
            pts.append((mx, p0[1]) if abs(pts[-1][1] - my) > abs(pts[-1][0] - mx)
                       else (mx, my))
            pts.append((mx, my))
        pts.append((medios[-1][0], p1[1]))
        pts.append(p1)
        # limpiar duplicados consecutivos
        limpio = [pts[0]]
        for p in pts[1:]:
            if abs(p[0] - limpio[-1][0]) > 0.5 or abs(p[1] - limpio[-1][1]) > 0.5:
                limpio.append(p)
        return limpio
    # sin waypoints: codo simple en el eje dominante
    if abs(p1[0] - p0[0]) < 1 or abs(p1[1] - p0[1]) < 1:
        return [p0, p1]
    horizontal = "exitX=1" in est or "exitX=0;" in est or _est(est, "exitY") in ("0.5",)
    if horizontal and _est(est, "exitY") not in ("0", "1"):
        m = (p0[0] + p1[0]) / 2
        return [p0, (m, p0[1]), (m, p1[1]), p1]
    m = (p0[1] + p1[1]) / 2
    return [p0, (p0[0], m), (p1[0], m), p1]


def segmento_mas_largo(pts):
    mejor, largo = None, -1
    for i in range(len(pts) - 1):
        d = abs(pts[i + 1][0] - pts[i][0]) + abs(pts[i + 1][1] - pts[i][1])
        if d > largo:
            largo, mejor = d, ((pts[i][0] + pts[i + 1][0]) / 2,
                               (pts[i][1] + pts[i + 1][1]) / 2)
    return mejor


def dibujar_flecha(fl, por_id, salida):
    pts = ruta_ortogonal(fl, por_id)
    if len(pts) < 2:
        return None
    est = fl["estilo"]
    color = _est(est, "strokeColor", "#A8B3BF")
    grosor = _est(est, "strokeWidth", "1")
    guion = ' stroke-dasharray="4 4"' if "dashed=1" in est else ""
    d = "M" + " L".join(f"{x:.0f},{y:.0f}" for x, y in pts)
    punta = _est(est, "endArrow", "blockThin")
    marca = ("" if punta == "none" else
             ' marker-end="url(#abierta)"' if punta == "open" else
             ' marker-end="url(#punta)"')
    salida.append(
        f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{grosor}"'
        f'{guion}{marca}/>')
    if "startArrow" in est:
        salida.append(
            f'<path d="M{pts[1][0]:.0f},{pts[1][1]:.0f} '
            f'L{pts[0][0]:.0f},{pts[0][1]:.0f}" fill="none" stroke="{color}" '
            f'stroke-width="{grosor}" marker-end="url(#punta)"/>')
    return segmento_mas_largo(pts)


def render(nombre, cajas, flechas):
    por_id = {c.id: c for c in cajas}
    etiquetas = {c.padre: c for c in cajas if "edgeLabel" in c.estilo}
    cuerpos = [c for c in cajas
               if c.w > 0 and c.h > 0 and "edgeLabel" not in c.estilo]
    # relleno primero, luego cajas normales
    cuerpos.sort(key=lambda c: (0 if c.es_fondo() else 1, c.y))

    partes, textos, ys_extra = [], [], []
    for c in cuerpos:
        dibujar_caja(c, partes)
    # los textos van despues de las flechas: una etiqueta con relleno tapa la
    # linea que la cruza, en vez de quedar tachada
    for c in cuerpos:
        dibujar_texto(c, textos)
    for fl in flechas:
        centro = dibujar_flecha(fl, por_id, partes)
        lbl = etiquetas.get(fl["id"])
        if lbl and centro:
            lineas = [t for t, _, _ in lineas_con_formato(lbl.valor) if t.strip()]
            if not lineas:
                continue
            ancho = max(ancho_texto(t, 10) for t in lineas) + 8
            alto = len(lineas) * alto_linea(10) + 4
            partes.append(
                f'<rect x="{centro[0] - ancho / 2:.0f}" '
                f'y="{centro[1] - alto / 2:.0f}" width="{ancho:.0f}" '
                f'height="{alto:.0f}" fill="#FFFFFF" stroke="none"/>')
            y = centro[1] - alto / 2 + 11
            for t in lineas:
                partes.append(
                    f'<text x="{centro[0]:.0f}" y="{y:.0f}" '
                    f'font-family="{FUENTE}" font-size="10" fill="#6B7A8C" '
                    f'text-anchor="middle">{esc(t)}</text>')
                y += alto_linea(10)
    partes += textos

    xs = [c.x for c in cuerpos] + [c.x + c.w for c in cuerpos]
    for fl in flechas:
        for px_, py_ in ruta_ortogonal(fl, por_id):
            xs.append(px_)
            ys_extra.append(py_)
    ys = [c.y for c in cuerpos] + [c.y + c.h for c in cuerpos] + ys_extra
    x0, y0 = min(xs) - MARGEN, min(ys) - MARGEN
    ancho = max(xs) - x0 + MARGEN
    alto = max(ys) - y0 + MARGEN + 20

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{ancho:.0f}" '
        f'height="{alto:.0f}" viewBox="{x0:.0f} {y0:.0f} {ancho:.0f} {alto:.0f}">'
        '<defs><marker id="punta" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="6" markerHeight="6" orient="auto-start-reverse">'
        '<path d="M0,1 L9,5 L0,9 z" fill="#8C99A6"/></marker>'
        '<marker id="abierta" viewBox="0 0 10 10" refX="9" refY="5" '
        'markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
        '<path d="M0,1 L9,5 L0,9" fill="none" stroke="#8C99A6" stroke-width="1.2"/>'
        '</marker></defs>'
        f'<rect x="{x0:.0f}" y="{y0:.0f}" width="{ancho:.0f}" '
        f'height="{alto:.0f}" fill="#FFFFFF"/>'
        + "".join(partes) + "</svg>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("archivo")
    ap.add_argument("-o", "--salida", default=None,
                    help="carpeta de salida (por defecto: la del .drawio)")
    ap.add_argument("--pagina", default=None,
                    help="numero o prefijo del nombre de la pagina")
    args = ap.parse_args()

    arbol = ET.parse(args.archivo)
    base = os.path.splitext(os.path.basename(args.archivo))[0]
    # Por convencion cada diagrama tiene su carpeta, con el .drawio, su
    # .diagrama.json y sus SVG juntos (pedido del responsable del repo, 2026-09-10). Es el
    # default para no depender de acordarse del -o.
    carpeta = args.salida or os.path.dirname(os.path.abspath(args.archivo))
    os.makedirs(carpeta, exist_ok=True)

    generados = []
    for i, d in enumerate(arbol.getroot().findall("diagram"), start=1):
        nombre = d.get("name", f"pagina{i}")
        if args.pagina and not (str(i) == args.pagina
                                or nombre.startswith(args.pagina)):
            continue
        if d.find("mxGraphModel") is None:
            print(f"  [{nombre}] comprimida, se omite")
            continue
        _, cajas, flechas = leer_pagina(d)
        svg = render(nombre, cajas, flechas)
        limpio = re.sub(r"[^A-Za-z0-9]+", "-", nombre).strip("-").lower()
        ruta = os.path.join(carpeta, f"{base}--{limpio}.svg")
        with open(ruta, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(svg)
        generados.append(ruta)
        print(f"  {ruta}")
    if not generados:
        print("no se genero ninguna pagina")
    return generados


if __name__ == "__main__":
    main()
