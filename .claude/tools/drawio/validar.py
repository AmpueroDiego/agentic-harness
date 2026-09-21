"""Valida un .drawio: detecta lo que hace que un diagrama sea ilegible.

Comprueba, pagina por pagina:
  E1  cajas que se solapan entre si
  E2  texto que desborda su caja (mas alto o mas ancho de lo que entra)
  E3  etiquetas de flecha que caen encima de una caja
  A1  tramos de flecha que atraviesan una caja  (aviso: el ruteo real lo
      decide draw.io, aca se aproxima)

Uso:
    python validar.py archivo.drawio [otro.drawio ...]

Sale con codigo 1 si hay errores (E*), 0 si solo hay avisos (A*).
"""

import re
import sys
import xml.etree.ElementTree as ET

from metricas import (ALTO_LINEA, alto_linea, ancho_texto, envolver,
                      lineas_con_formato, texto_plano)

# La consola de Windows usa cp1252: sin esto, un simbolo como ⚠ revienta el
# script en pleno reporte. Ver CLAUDE.md, "UTF-8 en la CLI de Windows".
for _flujo in (sys.stdout, sys.stderr):
    try:
        _flujo.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

PAD_H = 12.0   # padding horizontal que draw.io deja dentro de una caja
PAD_V = 10.0
TOLERANCIA = 2.0        # px de solapamiento que no molestan a la vista
SEP_ANCLAJE_MIN = 24.0  # px minimos entre dos flechas del mismo borde
HOLGURA_MIN = 14.0      # px minimos entre una linea y una estructura ajena


class Caja:
    __slots__ = ("id", "x", "y", "w", "h", "valor", "estilo", "padre",
                 "contenidas")

    def __init__(self, cid, x, y, w, h, valor, estilo, padre):
        self.id, self.x, self.y, self.w, self.h = cid, x, y, w, h
        self.valor, self.estilo, self.padre = valor, estilo, padre
        self.contenidas = 0

    @property
    def x2(self):
        return self.x + self.w

    @property
    def y2(self):
        return self.y + self.h

    def contiene(self, o):
        return (self.x <= o.x and self.y <= o.y
                and self.x2 >= o.x2 and self.y2 >= o.y2)

    def es_fondo(self):
        """Recuadro de agrupacion o lamina de relleno.

        No se decide por el estilo sino por la geometria: una caja que contiene
        enteras a otras es un contenedor, tenga relleno o no. Asi funciona
        igual con los .drawio hechos a mano, donde un rectangulo de relleno suele
        llevar color.
        """
        return self.contenidas > 0

    def es_texto_suelto(self):
        return self.estilo.startswith("text;")

    def etiqueta_afuera(self):
        """Formas cuyo texto se dibuja fuera de la caja (actores, iconos).
        Su alto no acota al texto, asi que no tiene sentido medirlo."""
        return ("verticalLabelPosition=bottom" in self.estilo
                or "verticalLabelPosition=top" in self.estilo
                or "labelPosition=right" in self.estilo
                or "labelPosition=left" in self.estilo)

    def texto_autoajusta(self):
        """Cajas cuyo alto no limita al texto: texto suelto y etiquetas."""
        return self.es_texto_suelto() or self.etiqueta_afuera()

    def centro(self):
        return (self.x + self.w / 2, self.y + self.h / 2)


def _solapan(a, b):
    ix = min(a.x2, b.x2) - max(a.x, b.x)
    iy = min(a.y2, b.y2) - max(a.y, b.y)
    if ix > TOLERANCIA and iy > TOLERANCIA:
        return ix, iy
    return None


def _punto_en(caja, px, py, margen=0.0):
    return (caja.x - margen <= px <= caja.x2 + margen
            and caja.y - margen <= py <= caja.y2 + margen)


def _distancia(caja, px, py):
    """Distancia de un punto al borde de una caja (0 si esta adentro)."""
    dx = max(caja.x - px, 0.0, px - caja.x2)
    dy = max(caja.y - py, 0.0, py - caja.y2)
    return (dx * dx + dy * dy) ** 0.5


def leer_pagina(diagrama):
    """Devuelve (nombre, cajas, flechas) de un <diagram>."""
    modelo = diagrama.find("mxGraphModel")
    if modelo is None:
        return diagrama.get("name", "?"), [], []

    cajas, flechas, geo_por_id = {}, [], {}
    for celda in modelo.iter("mxCell"):
        cid = celda.get("id")
        geo = celda.find("mxGeometry")
        estilo = celda.get("style") or ""
        valor = celda.get("value") or ""
        if celda.get("vertex") == "1" and geo is not None:
            cajas[cid] = Caja(
                cid,
                float(geo.get("x") or 0), float(geo.get("y") or 0),
                float(geo.get("width") or 0), float(geo.get("height") or 0),
                valor, estilo, celda.get("parent"))
            geo_por_id[cid] = cajas[cid]
        elif celda.get("edge") == "1":
            pts, libres = [], {}
            if geo is not None:
                arr = geo.find("Array")
                if arr is not None:
                    for p in arr.findall("mxPoint"):
                        pts.append((float(p.get("x") or 0),
                                    float(p.get("y") or 0)))
                # flechas sin caja de origen/destino (mensajes de un diagrama
                # de secuencia, lineas de vida): sus extremos son puntos sueltos
                for p in geo.findall("mxPoint"):
                    if p.get("as") in ("sourcePoint", "targetPoint"):
                        libres[p.get("as")] = (float(p.get("x") or 0),
                                               float(p.get("y") or 0))
            flechas.append({
                "id": cid, "valor": valor, "estilo": estilo,
                "origen": celda.get("source"), "destino": celda.get("target"),
                "puntos": pts,
                "p_origen": libres.get("sourcePoint"),
                "p_destino": libres.get("targetPoint"),
            })

    # coordenadas absolutas: sumar el offset de los padres que son cajas.
    # Se suma sobre las coordenadas RELATIVAS originales: si se mutara en el
    # mismo recorrido, un hijo de segundo nivel sumaria al abuelo dos veces
    # (una via el padre ya convertido y otra al subir la cadena).
    relativas = {cid: (c.x, c.y) for cid, c in cajas.items()}
    for c in cajas.values():
        p, guard = c.padre, 0
        while p in cajas and guard < 10:
            c.x += relativas[p][0]
            c.y += relativas[p][1]
            p = cajas[p].padre
            guard += 1

    # cuantas cajas contiene cada una: define quien es contenedor
    lista = [c for c in cajas.values() if c.w > 0 and c.h > 0]
    for a in lista:
        for b in lista:
            if a is not b and a.contiene(b) and (a.w * a.h) > (b.w * b.h):
                a.contenidas += 1

    return diagrama.get("name", "?"), list(cajas.values()), flechas


def polilinea(flecha, cajas_por_id):
    """Aproxima el recorrido de una flecha como lista de puntos."""
    o = cajas_por_id.get(flecha["origen"])
    d = cajas_por_id.get(flecha["destino"])
    inicio = o.centro() if o else flecha.get("p_origen")
    fin = d.centro() if d else flecha.get("p_destino")
    if not inicio or not fin:
        return []
    return [inicio] + flecha["puntos"] + [fin]


def punto_medio(pts):
    """Punto a mitad de recorrido de la polilinea (donde draw.io centra la
    etiqueta de una flecha)."""
    if len(pts) < 2:
        return None
    largos = []
    for i in range(len(pts) - 1):
        dx = pts[i + 1][0] - pts[i][0]
        dy = pts[i + 1][1] - pts[i][1]
        largos.append((dx * dx + dy * dy) ** 0.5)
    total = sum(largos)
    if total == 0:
        return pts[0]
    objetivo, acum = total / 2, 0.0
    for i, L in enumerate(largos):
        if acum + L >= objetivo:
            t = (objetivo - acum) / L if L else 0
            return (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t,
                    pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t)
        acum += L
    return pts[-1]


def _estructura_propia(fl, cajas, por_id):
    """Ids que una flecha puede rozar sin que sea un defecto.

    Son su origen y su destino, mas todo lo que forma parte de ellos: los hijos
    (la barra de color es un hijo de la caja) y los contenedores que los
    encierran (una flecha que sale de un nodo tiene que cruzar el borde de su
    propio grupo, no hay otra forma de salir).
    """
    extremos = {fl["origen"], fl["destino"]} - {None}
    propias = set(extremos)
    # el texto de un mensaje de secuencia es una celda aparte, marcada con
    # etiquetaDe=<id de la flecha>: va pegado a su flecha a proposito
    propias |= {c.id for c in cajas if f"etiquetaDe={fl['id']};" in c.estilo}
    for c in cajas:
        p, guard = c.padre, 0
        while p and guard < 10:                      # hijos y nietos
            if p in extremos:
                propias.add(c.id)
                break
            p = por_id[p].padre if p in por_id else None
            guard += 1
        for eid in extremos:                          # contenedores
            e = por_id.get(eid)
            if e and c.id != eid and c.contiene(e):
                propias.add(c.id)
    return propias


def revisar_pagina(nombre, cajas, flechas):
    errores, avisos = [], []
    # Las celdas de texto suelto tambien pueden chocar — el titulo de una
    # pagina encima de la etiqueta de un grupo se lee tan mal como dos cajas
    # superpuestas. Se miden por su texto, no por su ancho declarado, que en
    # los .drawio hechos a mano suele ser el de la lamina entera.
    for c in cajas:
        if c.es_texto_suelto() and c.valor:
            ls = lineas_con_formato(c.valor)
            if ls:
                c.w = min(c.w, max(ancho_texto(t, px, n) for t, px, n in ls) + 8)
                c.h = min(c.h, sum(alto_linea(px) for _, px, _ in ls) + 6)

    reales = [c for c in cajas if c.w > 0 and c.h > 0 and not c.es_fondo()]
    rellenos = [c for c in cajas if c.es_fondo()]
    por_id = {c.id: c for c in cajas}

    # --- E1: cajas superpuestas -------------------------------------------
    for i, a in enumerate(reales):
        for b in reales[i + 1:]:
            if a.contiene(b) or b.contiene(a):
                continue          # anidamiento explicito, no es choque
            s = _solapan(a, b)
            if s:
                errores.append(
                    f"E1 solapan '{_nom(a)}' y '{_nom(b)}' "
                    f"({s[0]:.0f}x{s[1]:.0f} px)")

    # un recuadro de agrupacion no debe pisar nodos que no le pertenecen
    for f in rellenos:
        for c in reales:
            # el anidamiento vale en los dos sentidos: un recuadro puede estar
            # dentro de un rectangulo de relleno que abarca toda la lamina
            if f.contiene(c) or c.contiene(f):
                continue
            s = _solapan(f, c)
            if s:
                errores.append(
                    f"E1 el recuadro '{_nom(f)}' pisa a '{_nom(c)}' "
                    f"({s[0]:.0f}x{s[1]:.0f} px) sin contenerlo")

    # dos recuadros que se cruzan sin que uno contenga al otro: marcos de un
    # diagrama de secuencia mal anidados, o grupos que se invaden
    for i, a in enumerate(rellenos):
        for b in rellenos[i + 1:]:
            if a.contiene(b) or b.contiene(a):
                continue
            s = _solapan(a, b)
            if s:
                errores.append(
                    f"E1 los recuadros '{_nom(a)}' y '{_nom(b)}' se cruzan "
                    f"({s[0]:.0f}x{s[1]:.0f} px) sin que uno contenga al otro")

    # --- E2: texto desbordado ---------------------------------------------
    for c in cajas:
        if c.w <= 0 or not c.valor or c.texto_autoajusta():
            continue
        if not texto_plano(c.valor).strip():
            continue
        disponible = c.w - 2 * PAD_H
        if disponible <= 10:
            continue
        alto_necesario, peor, n = 2 * PAD_V, 0.0, 0
        for txt, px, neg in lineas_con_formato(c.valor):
            trozos = envolver(txt, disponible, px, neg)
            n += len(trozos)
            alto_necesario += len(trozos) * alto_linea(px)
            peor = max(peor, max(ancho_texto(t, px, neg) for t in trozos))
        if alto_necesario > c.h + TOLERANCIA:
            errores.append(
                f"E2 '{_nom(c)}': el texto necesita {alto_necesario:.0f}px "
                f"de alto y la caja tiene {c.h:.0f}px ({n} lineas)")
        if peor > disponible + TOLERANCIA:
            errores.append(
                f"E2 '{_nom(c)}': una palabra mide {peor:.0f}px y solo "
                f"entran {disponible:.0f}px")

    # --- E4: flechas amontonadas en el mismo borde -------------------------
    bordes = {}
    for fl in flechas:
        s = fl["estilo"]
        for nid, kx, ky in ((fl["origen"], "exitX", "exitY"),
                            (fl["destino"], "entryX", "entryY")):
            mx_ = re.search(kx + r"=([\d.]+)", s)
            my_ = re.search(ky + r"=([\d.]+)", s)
            if not mx_ or not my_ or nid not in por_id:
                continue
            x, y = float(mx_.group(1)), float(my_.group(1))
            lado = ("arriba" if y == 0 else "abajo" if y == 1
                    else "izq" if x == 0 else "der" if x == 1 else None)
            if lado:
                bordes.setdefault((nid, lado), []).append(
                    (x if lado in ("arriba", "abajo") else y, fl))
    for (nid, lado), ocupantes in bordes.items():
        if len(ocupantes) < 2:
            continue
        caja = por_id[nid]
        largo = caja.w if lado in ("arriba", "abajo") else caja.h
        ocupantes.sort(key=lambda t: t[0])
        for i in range(len(ocupantes) - 1):
            sep = (ocupantes[i + 1][0] - ocupantes[i][0]) * largo
            # 0px = mismo punto exacto, y eso se lee como intencional
            if 0 < sep < SEP_ANCLAJE_MIN:
                errores.append(
                    f"E4 '{_nom(caja)}' borde {lado}: dos flechas ancladas a "
                    f"{sep:.0f}px ({_nom_flecha(ocupantes[i][1])} y "
                    f"{_nom_flecha(ocupantes[i + 1][1])}); se leen como una")

    # --- E3 / A1: flechas --------------------------------------------------
    for fl in flechas:
        pts = polilinea(fl, por_id)
        if not pts:
            continue
        # lineas sin punta (lineas de vida, separadores): cruzan marcos y
        # etiquetas a proposito; no son flechas que haya que rutear
        if "endArrow=none" in fl["estilo"]:
            continue
        if fl["valor"]:
            m = punto_medio(pts)
            plano = texto_plano(fl["valor"])
            lineas = plano.split("\n")
            w = max(ancho_texto(t) for t in lineas)
            h = len(lineas) * ALTO_LINEA
            etiqueta = Caja("lbl", m[0] - w / 2, m[1] - h / 2, w, h,
                            "", "", None)
            for c in reales:
                if c.id in (fl["origen"], fl["destino"]):
                    continue
                s = _solapan(etiqueta, c)
                if s:
                    errores.append(
                        f"E3 la etiqueta \"{plano[:40]}\" cae encima de "
                        f"'{_nom(c)}'")
        # tramos que atraviesan cajas ajenas (A1) o pasan pegados a una
        # estructura sin tocarla (A2). Lo segundo no rompe nada, pero se lee
        # como un error de dibujo: una linea lamiendo el marco de un grupo.
        propias = _estructura_propia(fl, cajas, por_id)
        ajenas = [c for c in reales if c.id not in propias]
        marcos = [c for c in cajas if c.es_fondo() and c.id not in propias]
        dentro, roce = set(), set()
        for i in range(len(pts) - 1):
            for paso in range(0, 21):
                t = paso / 20
                px = pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t
                py = pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t
                for c in ajenas:
                    if _punto_en(c, px, py, -4):
                        dentro.add(_nom(c))
                for c in ajenas + marcos:
                    if _punto_en(c, px, py, -4):
                        continue
                    d = _distancia(c, px, py)
                    if d < HOLGURA_MIN:
                        roce.add((_nom(c), round(d)))
        for nombre in sorted(dentro):
            avisos.append(
                f"A1 la flecha {_nom_flecha(fl)} pasa por dentro de '{nombre}'")
        for nombre, d in sorted(roce):
            if nombre in dentro:
                continue
            avisos.append(
                f"A2 la flecha {_nom_flecha(fl)} pasa a {d}px de '{nombre}'; "
                f"el minimo es {HOLGURA_MIN:.0f}px")

    return errores, sorted(set(avisos))


def _nom(caja):
    t = texto_plano(caja.valor).strip().split("\n")[0]
    return (t[:38] or f"#{caja.id}")


def _nom_flecha(fl):
    v = texto_plano(fl["valor"]).strip().split("\n")[0]
    return f'"{v[:30]}"' if v else f'{fl["origen"]}->{fl["destino"]}'


def main(rutas):
    total_err = 0
    for ruta in rutas:
        print(f"\n=== {ruta} ===")
        try:
            arbol = ET.parse(ruta)
        except ET.ParseError as e:
            print(f"  XML invalido: {e}")
            total_err += 1
            continue
        paginas = arbol.getroot().findall("diagram")
        if not paginas:
            print("  sin paginas <diagram>")
            continue
        for d in paginas:
            if d.find("mxGraphModel") is None and (d.text or "").strip():
                print(f"  [{d.get('name')}] comprimida — "
                      "guardala desde draw.io con Extras > Edit Diagram")
                continue
            nombre, cajas, flechas = leer_pagina(d)
            errores, avisos = revisar_pagina(nombre, cajas, flechas)
            estado = "OK" if not errores else f"{len(errores)} ERROR(ES)"
            print(f"  [{nombre}] {len(cajas)} cajas, {len(flechas)} flechas "
                  f"-> {estado}"
                  + (f", {len(avisos)} aviso(s)" if avisos else ""))
            for e in errores:
                print(f"      {e}")
            for a in avisos:
                print(f"      {a}")
            total_err += len(errores)
    print(f"\nTotal de errores: {total_err}")
    return 1 if total_err else 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    sys.exit(main(sys.argv[1:]))
