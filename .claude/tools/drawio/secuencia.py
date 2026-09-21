"""Paginas de tipo "secuencia" para generar.py.

Mismo principio que la grilla: el spec declara QUE pasa (participantes y pasos
en orden) y aca se calcula DONDE va cada pixel, midiendo el texto.

Spec de una pagina:
    {
      "nombre": "3 · Envio de WhatsApp",
      "tipo": "secuencia",
      "titulo": "Envio de WhatsApp y recuperacion por Outbox",
      "participantes": [
        {"id": "web", "titulo": "web-app", "color": "apoyo"},
        {"id": "ctrl", "titulo": "WhatsAppController", "color": "principal"},
        {"id": "db", "titulo": "CoreDb", "forma": "cilindro"},
        {"id": "agente", "titulo": "Agente", "forma": "actor"}
      ],
      "pasos": [
        "[seccion Intento inmediato]",
        "web -> ctrl: POST /WhatsApp/Enviar",
        "ctrl -> ctrl: Valida y normaliza",
        "[alt Envio confirmado]",
        "ctrl -> db: Guarda Mensaje Enviado",
        "[else WAHA rechaza]",
        "ctrl -> db: Guarda Mensaje + Outbox",
        "[end]",
        "ctrl --> web: 200 OK"
      ]
    }

Sintaxis de los pasos:
    A -> B: texto      llamada (linea continua)
    B --> A: texto     respuesta (linea punteada)
    A -> A: texto      accion propia (bucle a la derecha de la linea de vida)
    [alt cond] [else cond] [end]      tambien opt, par, loop, break, group
    [seccion titulo]                   separador a lo ancho de toda la lamina

Los mensajes se numeran solos. Las notas no existen (regla 1 de /diagramar):
el contexto va en claves "_apuntes..." del spec.
"""

import re
import xml.etree.ElementTree as ET

import generar as g
from metricas import PX_ETIQUETA, alto_linea, ancho_texto, envolver

BLOQUES = ("alt", "opt", "par", "loop", "break", "group")

# el maximo alcanza para un nombre de clase largo sin partirlo a mitad de palabra
ANCHO_PART_MIN, ANCHO_PART_MAX = 120.0, 280.0
SEP_PART = 40.0            # aire minimo entre dos cajas de participante
ANCHO_MSG_MAX = 250.0      # las etiquetas de mensaje se envuelven a este ancho
PAD_MSG = 18.0             # aire entre la etiqueta y las lineas de vida
BUCLE_W, BUCLE_H = 28.0, 22.0
AIRE_FLECHA = 6.0          # entre el texto y la flecha que lo lleva
SEP_BUCLE_TEXTO = 16.0     # entre el bucle de una accion propia y su texto
PASO_Y = 16.0              # aire despues de cada mensaje
ALTO_CAB_BLOQUE = 28.0     # rotulo "alt [condicion]"
ALTO_ELSE = 26.0
ALTO_FIN_BLOQUE = 14.0
ALTO_SECCION = 38.0
PAD_MARCO = 26.0           # cuanto sobresale un marco de sus lineas de vida
PAD_ANIDADO = 12.0         # cuanto sobresale un marco del marco que contiene
ALTO_ACTOR = 50.0
FUENTE_BLOQUE = PX_ETIQUETA

_MSG = re.compile(r"^\s*([\w.-]+)\s*(-->|->)\s*([\w.-]+)\s*:\s*(.*)$")
_CTRL = re.compile(r"^\s*\[\s*(\w+)\s*(.*?)\s*\]\s*$")


# --- lectura del spec ----------------------------------------------------

def parsear(pagina):
    """Convierte la lista de pasos en un arbol de bloques. Valida ids."""
    ids = {p["id"] for p in pagina["participantes"]}
    raiz = {"tipo": "raiz", "ramas": [{"cond": "", "items": []}]}
    pila, numero = [raiz], 0
    for i, paso in enumerate(pagina["pasos"], start=1):
        m = _MSG.match(paso)
        if m:
            de, flecha, a, texto = m.groups()
            for pid in (de, a):
                if pid not in ids:
                    raise SystemExit(f"Paso {i}: participante desconocido '{pid}' en: {paso}")
            numero += 1
            pila[-1]["ramas"][-1]["items"].append({
                "tipo": "msg", "de": de, "a": a, "texto": texto.strip(),
                "respuesta": flecha == "-->", "num": numero})
            continue
        c = _CTRL.match(paso)
        if not c:
            raise SystemExit(f"Paso {i}: no se entiende: {paso}")
        palabra, resto = c.group(1).lower(), c.group(2)
        if palabra in BLOQUES:
            bloque = {"tipo": palabra, "ramas": [{"cond": resto, "items": []}]}
            pila[-1]["ramas"][-1]["items"].append(bloque)
            pila.append(bloque)
        elif palabra == "else":
            if len(pila) == 1:
                raise SystemExit(f"Paso {i}: [else] fuera de un bloque")
            pila[-1]["ramas"].append({"cond": resto, "items": []})
        elif palabra == "end":
            if len(pila) == 1:
                raise SystemExit(f"Paso {i}: [end] sin bloque abierto")
            pila.pop()
        elif palabra == "seccion":
            if len(pila) > 1:
                raise SystemExit(f"Paso {i}: [seccion] dentro de un bloque; cerralo antes")
            raiz["ramas"][0]["items"].append({"tipo": "seccion", "texto": resto})
        else:
            raise SystemExit(f"Paso {i}: bloque desconocido '[{palabra}]'")
    if len(pila) > 1:
        raise SystemExit(f"Falta [end] para el bloque '{pila[-1]['tipo']}'")
    return raiz


def _mensajes(nodo):
    for rama in nodo.get("ramas", []):
        for it in rama["items"]:
            if it["tipo"] == "msg":
                yield it
            elif it["tipo"] in BLOQUES:
                yield from _mensajes(it)


def _texto_msg(m):
    return f"{m['num']} · {m['texto']}"


def _ancho_etiqueta(texto):
    """Ancho a reservar para una etiqueta: su largo natural hasta el maximo de
    envoltura, pero nunca menos que su palabra mas larga (un nombre de metodo
    partido se lee mal). +2 de holgura: con el ancho exacto, el redondeo hacia
    que envolver() mandara una palabra a la linea siguiente."""
    natural = min(ancho_texto(texto, PX_ETIQUETA), ANCHO_MSG_MAX)
    palabras = texto.split(" ")
    palabra = max(ancho_texto(w, PX_ETIQUETA) for w in palabras)
    # "12 · Metodo" va junto: si no, con un metodo largo el numero queda solo
    cabeza = ancho_texto(" ".join(palabras[:3]), PX_ETIQUETA)
    return max(natural, palabra, cabeza) + 2


# --- geometria horizontal ------------------------------------------------

def medir_participantes(pagina):
    for p in pagina["participantes"]:
        forma = p.get("forma", "caja")
        lineas_titulo = p["titulo"].split("\n")
        # el detalle tambien cuenta: medido solo por el titulo, "Quartz" dejaba
        # sin lugar a "ProcessOutboxMessagesJob" y lo partia a mitad de palabra
        anchos = [ancho_texto(t, 13, True) for t in lineas_titulo]
        anchos += [ancho_texto(l.strip("_"), g.PX_CUERPO) for l in p.get("lineas", [])]
        natural = max(anchos) + 2 * g.PAD_H + 2
        p["_w"] = max(ANCHO_PART_MIN, min(ANCHO_PART_MAX, natural))
        if forma == "actor":
            p["_w_etiqueta"] = p["_w"]
            p["_w"] = 30.0


def ubicar_columnas(pagina, raiz):
    parts = pagina["participantes"]
    col = {p["id"]: i for i, p in enumerate(parts)}
    n = len(parts)
    ancho_vis = [p.get("_w_etiqueta", p["_w"]) for p in parts]
    # distancia entre centros de columnas contiguas
    dist = [(ancho_vis[i] + ancho_vis[i + 1]) / 2 + SEP_PART for i in range(n - 1)]
    extra_der = 0.0

    tramos = []
    for m in _mensajes(raiz):
        a, b = col[m["de"]], col[m["a"]]
        natural = _ancho_etiqueta(_texto_msg(m))
        if a == b:
            necesario = BUCLE_W + SEP_BUCLE_TEXTO + natural + PAD_MSG
            if a < n - 1:
                tramos.append((a, a + 1, necesario + ancho_vis[a + 1] / 2))
            else:
                extra_der = max(extra_der, necesario)
        else:
            tramos.append((min(a, b), max(a, b), natural + 2 * PAD_MSG))
    # los tramos cortos primero: si falta lugar, el deficit se reparte en el tramo
    for i, j, necesario in sorted(tramos, key=lambda t: t[1] - t[0]):
        actual = sum(dist[i:j])
        if actual < necesario:
            extra = (necesario - actual) / (j - i)
            for k in range(i, j):
                dist[k] += extra

    x = g.MARGEN + ancho_vis[0] / 2
    for i, p in enumerate(parts):
        p["_cx"] = x
        if i < n - 1:
            x += dist[i]
    pagina["_extra_der"] = extra_der
    return col


def extension_x(nodo, col, parts, profundidad=0):
    """(x_izq, x_der) que ocupa un bloque, incluyendo etiquetas y sub-bloques."""
    izq, der = float("inf"), float("-inf")
    for rama in nodo["ramas"]:
        for it in rama["items"]:
            if it["tipo"] == "msg":
                xa, xb = parts[col[it["de"]]]["_cx"], parts[col[it["a"]]]["_cx"]
                if it["de"] == it["a"]:
                    ancho = _ancho_etiqueta(_texto_msg(it))
                    izq = min(izq, xa - PAD_MARCO)
                    der = max(der, xa + BUCLE_W + SEP_BUCLE_TEXTO + ancho + PAD_MARCO / 2)
                else:
                    izq = min(izq, min(xa, xb) - PAD_MARCO)
                    der = max(der, max(xa, xb) + PAD_MARCO)
            elif it["tipo"] in BLOQUES:
                si, sd = extension_x(it, col, parts, profundidad + 1)
                izq, der = min(izq, si - PAD_ANIDADO), max(der, sd + PAD_ANIDADO)
    if izq == float("inf"):      # bloque vacio: una columna de ancho minimo
        izq, der = parts[0]["_cx"] - PAD_MARCO, parts[0]["_cx"] + PAD_MARCO
    cab = ancho_texto(f"{nodo['tipo']}  [{nodo['ramas'][0]['cond']}]", FUENTE_BLOQUE, True) + 24
    der = max(der, izq + cab)
    for rama in nodo["ramas"][1:]:
        der = max(der, izq + ancho_texto(f"[{rama['cond']}]", FUENTE_BLOQUE) + 24)
    nodo["_x"], nodo["_x2"] = izq, der
    return izq, der


# --- emision ---------------------------------------------------------------

def _texto(root, cid, html, x, y, w, h, alinear="center", relleno=True, negrita=False,
           px=PX_ETIQUETA, extra=""):
    estilo = (f"text;html=1;whiteSpace=wrap;align={alinear};verticalAlign=middle;"
              f"fontSize={px};fontColor={g.TINTA_SUAVE};spacing=0;")
    if relleno:
        estilo += f"labelBackgroundColor={g.PAPEL};"
    if negrita:
        estilo += "fontStyle=1;"
    g.celda(root, cid, html, estilo + extra, x, y, w, h)


def _linea(root, cid, puntos, estilo):
    c = ET.SubElement(root, "mxCell", {"id": cid, "value": "", "style": estilo,
                                       "edge": "1", "parent": "1"})
    geo = ET.SubElement(c, "mxGeometry", {"relative": "1", "as": "geometry"})
    ET.SubElement(geo, "mxPoint", {"x": f"{puntos[0][0]:.0f}", "y": f"{puntos[0][1]:.0f}",
                                   "as": "sourcePoint"})
    ET.SubElement(geo, "mxPoint", {"x": f"{puntos[-1][0]:.0f}", "y": f"{puntos[-1][1]:.0f}",
                                   "as": "targetPoint"})
    if len(puntos) > 2:
        arr = ET.SubElement(geo, "Array", {"as": "points"})
        for px, py in puntos[1:-1]:
            ET.SubElement(arr, "mxPoint", {"x": f"{px:.0f}", "y": f"{py:.0f}"})


def _estilo_mensaje(respuesta):
    base = (f"html=1;rounded=0;strokeWidth=1;strokeColor={g.LINEA};"
            "endSize=7;")
    if respuesta:
        return base + "dashed=1;dashPattern=4 4;endArrow=open;endFill=0;"
    return base + f"endArrow=blockThin;endFill=1;strokeColor={g.TINTA_SUAVE};"


def construir_secuencia(pagina, indice):
    g._notas_prohibidas(pagina)
    raiz = parsear(pagina)
    parts = pagina["participantes"]
    medir_participantes(pagina)
    col = ubicar_columnas(pagina, raiz)
    for it in raiz["ramas"][0]["items"]:
        if it["tipo"] in BLOQUES:
            extension_x(it, col, parts)

    diagrama = ET.Element("diagram", {"id": f"pag{indice}", "name": pagina["nombre"]})
    modelo = ET.SubElement(diagrama, "mxGraphModel", {
        "dx": "1400", "dy": "900", "grid": "1", "gridSize": "10", "guides": "1",
        "tooltips": "1", "connect": "1", "arrows": "1", "fold": "1", "page": "1",
        "pageScale": "1", "pageWidth": "1600", "pageHeight": "1000",
        "math": "0", "shadow": "0"})
    root = ET.SubElement(modelo, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

    # Primero se apila todo para conocer alturas; se emite despues, en capas:
    # marcos detras, luego lineas de vida, cabeceras, mensajes y textos encima.
    marcos, textos, lineas = [], [], []

    y = g.MARGEN
    if pagina.get("titulo"):
        ancho_t = ancho_texto(pagina["titulo"], 14, True) + 16
        textos.append(("titulo", f'<span style="color:{g.TINTA}">{g.esc(pagina["titulo"])}</span>',
                       g.MARGEN, y - 6, ancho_t, g.ALTO_TITULO, "left", False, True, 14))
        y += g.ALTO_TITULO + 18

    # cabeceras: todas del mismo alto (regla de filas uniformes)
    alto_cab = 0.0
    for p in parts:
        if p.get("forma") == "actor":
            ls = envolver(p["titulo"].replace("\n", " "), p["_w_etiqueta"], 13, True)
            p["_h"] = ALTO_ACTOR + len(ls) * alto_linea(13) + 6
        else:
            nodo = {"titulo": p["titulo"].replace("\n", " "), "lineas": p.get("lineas", []),
                    "_w": p["_w"]}
            html, alto_txt = g.html_caja(nodo)
            p["_html"] = html
            p["_h"] = max(56.0, alto_txt + 2 * g.PAD_V + g.ALTO_BARRA)
        alto_cab = max(alto_cab, p["_h"])
    for p in parts:
        p["_y"] = y
    y_vidas = y + alto_cab
    y += alto_cab + 24

    contador = {"n": 0}

    def nuevo_id(prefijo):
        contador["n"] += 1
        return f"{prefijo}{contador['n']}"

    def apilar(items, profundidad):
        nonlocal y
        for it in items:
            if it["tipo"] == "seccion":
                ancho = ancho_texto(it["texto"], PX_ETIQUETA + 1, True) + 24
                yc = y + ALTO_SECCION / 2
                x0 = parts[0]["_cx"] - PAD_MARCO * 2
                x1 = parts[-1]["_cx"] + PAD_MARCO * 2 + pagina["_extra_der"]
                lineas.append((nuevo_id("sec"), [(x0, yc), (x1, yc)],
                               f"html=1;endArrow=none;strokeColor={g.BORDE};strokeWidth=1;"))
                cx = (x0 + x1) / 2
                textos.append((nuevo_id("sect"), g.esc(it["texto"].upper()),
                               cx - ancho / 2, yc - 9, ancho, 18, "center", True, True, PX_ETIQUETA))
                y += ALTO_SECCION
            elif it["tipo"] == "msg":
                pa, pb = parts[col[it["de"]]], parts[col[it["a"]]]
                texto = _texto_msg(it)
                if it["de"] == it["a"]:
                    ancho_max = _ancho_etiqueta(texto)
                    ls = envolver(texto, ancho_max, PX_ETIQUETA)
                    alto = len(ls) * alto_linea(PX_ETIQUETA)
                    x = pa["_cx"]
                    # 10px arriba: pegado al rotulo de un marco quedaba a 9px de su texto
                    y0 = y + 10
                    mid = nuevo_id("m")
                    lineas.append((mid, [(x, y0), (x + BUCLE_W, y0),
                                         (x + BUCLE_W, y0 + BUCLE_H), (x, y0 + BUCLE_H)],
                                   _estilo_mensaje(it["respuesta"])))
                    textos.append((f"{mid}t", "<br/>".join(g.esc(l) for l in ls),
                                   x + BUCLE_W + SEP_BUCLE_TEXTO, y0 + BUCLE_H / 2 - alto / 2 - 1,
                                   ancho_max + 2, alto + 2, "left", True, False, PX_ETIQUETA,
                                   f"etiquetaDe={mid};"))
                    y = y0 + max(BUCLE_H, alto) + PASO_Y
                else:
                    x0, x1 = pa["_cx"], pb["_cx"]
                    ancho_disp = min(abs(x1 - x0) - 2 * PAD_MSG, _ancho_etiqueta(texto))
                    ls = envolver(texto, ancho_disp, PX_ETIQUETA)
                    ancho = max(ancho_texto(l, PX_ETIQUETA) for l in ls) + 2
                    alto = len(ls) * alto_linea(PX_ETIQUETA)
                    cx = (x0 + x1) / 2
                    mid = nuevo_id("m")
                    textos.append((f"{mid}t", "<br/>".join(g.esc(l) for l in ls),
                                   cx - ancho / 2, y, ancho, alto + 2, "center", True, False,
                                   PX_ETIQUETA, f"etiquetaDe={mid};"))
                    yl = y + alto + 2 + AIRE_FLECHA
                    lineas.append((mid, [(x0, yl), (x1, yl)],
                                   _estilo_mensaje(it["respuesta"])))
                    y = yl + PASO_Y
            else:                                   # bloque
                y_ini = y
                cab = f"<b>{it['tipo']}</b>  [{g.esc(it['ramas'][0]['cond'])}]"
                ancho_cab = ancho_texto(f"{it['tipo']}  [{it['ramas'][0]['cond']}]",
                                        FUENTE_BLOQUE, True) + 12
                textos.append((nuevo_id("bt"), cab, it["_x"] + 8, y + 5, ancho_cab, 18,
                               "left", False, False, FUENTE_BLOQUE))
                y += ALTO_CAB_BLOQUE
                for k, rama in enumerate(it["ramas"]):
                    if k > 0:
                        lineas.append((nuevo_id("else"), [(it["_x"], y), (it["_x2"], y)],
                                       f"html=1;endArrow=none;dashed=1;dashPattern=6 4;"
                                       f"strokeColor={g.TINTA_SUAVE};strokeWidth=1;"))
                        txt = f"[{rama['cond']}]"
                        textos.append((nuevo_id("et"), g.esc(txt), it["_x"] + 8, y + 5,
                                       ancho_texto(txt, FUENTE_BLOQUE) + 12, 16,
                                       "left", False, False, FUENTE_BLOQUE))
                        y += ALTO_ELSE
                    apilar(rama["items"], profundidad + 1)
                y += ALTO_FIN_BLOQUE - PASO_Y / 2
                marcos.append((nuevo_id("blk"), it["_x"], y_ini, it["_x2"] - it["_x"],
                               y - y_ini, profundidad))
                y += PASO_Y

    apilar(raiz["ramas"][0]["items"], 0)
    y_fin = y + 10

    # 1) marcos (detras de todo), de afuera hacia adentro
    for cid, x, yy, w, h, _prof in sorted(marcos, key=lambda m: m[5]):
        g.celda(root, cid, "",
                f"rounded=0;html=1;fillColor=none;strokeColor={g.TINTA_SUAVE};strokeWidth=1;",
                x, yy, w, h)
    # 2) lineas de vida
    for p in parts:
        _linea(root, f"vida-{p['id']}", [(p["_cx"], y_vidas), (p["_cx"], y_fin)],
               f"html=1;endArrow=none;dashed=1;dashPattern=3 4;strokeColor={g.BORDE};strokeWidth=1;")
    # 3) cabeceras de participante
    for p in parts:
        forma = p.get("forma", "caja")
        nodo = {"forma": forma, "color": p.get("color", "apoyo")}
        if forma == "actor":
            x = p["_cx"] - 15
            g.celda(root, p["id"], f'<b style="font-size:13px;color:{g.TINTA}">'
                    f'{g.esc(p["titulo"].replace(chr(10), " "))}</b>',
                    g.estilo_caja(nodo), x, p["_y"], 30, ALTO_ACTOR)
            continue
        x = p["_cx"] - p["_w"] / 2
        g.celda(root, p["id"], p["_html"], g.estilo_caja(nodo), x, p["_y"], p["_w"], alto_cab)
        if g.lleva_barra(nodo):
            barra = ET.SubElement(root, "mxCell", {
                "id": f"{p['id']}-barra", "value": "",
                "style": (f"rounded=0;html=1;fillColor={g.acento(nodo['color'])};"
                          "strokeColor=none;movable=0;resizable=0;deletable=0;connectable=0;"),
                "vertex": "1", "parent": p["id"]})
            ET.SubElement(barra, "mxGeometry", {"x": "0", "y": "0", "width": f"{p['_w']:.0f}",
                                                "height": f"{g.ALTO_BARRA:.0f}", "as": "geometry"})
    # 4) mensajes y separadores
    for cid, puntos, estilo in lineas:
        _linea(root, cid, puntos, estilo)
    # 5) textos al final, encima de las lineas
    for cid, html, x, yy, w, h, alinear, relleno, negrita, px, *extra in textos:
        _texto(root, cid, html, x, yy, w, h, alinear, relleno, negrita, px, *extra)
    return diagrama
