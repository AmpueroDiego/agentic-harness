"""Genera un .drawio a partir de una especificacion JSON, sin coordenadas.

La idea: quien escribe el diagrama declara QUE hay (nodos, grupos, flechas) y
en que celda de una grilla va cada cosa. Este script calcula DONDE va cada
pixel, midiendo el texto de verdad y reservando corredores vacios para las
flechas y sus etiquetas. Nadie escribe una coordenada a mano.

Reglas de oro de la maquetacion:
  * Las cajas viven en celdas de una grilla (col, fila). Nunca se tocan.
  * Entre columna y columna, y entre fila y fila, hay un CORREDOR vacio.
    Ninguna caja se dibuja en un corredor.
  * Toda etiqueta de flecha se ubica dentro de un corredor, en su propio
    carril. Dos flechas nunca comparten carril.
  * El alto de cada caja se deriva del texto ya envuelto: no puede desbordar.
  * Los paneles de texto al costado NO van: un diagrama muestra, no explica.

Uso:
    python generar.py especificacion.json
"""

import json
import os
import sys
import xml.etree.ElementTree as ET

from metricas import (ALTO_LINEA, PX_CUERPO, PX_ETIQUETA, PX_TITULO,
                      alto_linea, ancho_texto, envolver)

for _flujo in (sys.stdout, sys.stderr):
    try:
        _flujo.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# --- constantes de maquetacion ------------------------------------------
PAD_H, PAD_V = 12.0, 10.0          # aire dentro de una caja
ANCHO_COL = 280.0                  # ancho por defecto de una columna
ALTO_MIN = 78.0                    # 78/3 = 26px: alcanza para anclar 2 flechas
CORREDOR_X_MIN = 120.0             # corredor vertical entre columnas
CORREDOR_Y_MIN = 100.0             # corredor horizontal entre filas
MARGEN = 40.0
PAD_GRUPO, TITULO_GRUPO = 22.0, 34.0
# Holgura minima entre una linea y cualquier estructura que no sea su origen o
# su destino. Un corredor no basta: el recuadro de un grupo se mete PAD_GRUPO
# hacia adentro del corredor (y TITULO_GRUPO por arriba), asi que un carril
# calculado solo contra la fila caia sobre el borde del contenedor. Se ve como
# una linea pegada al marco, que es exactamente lo que hay que evitar.
HOLGURA = 18.0
BORDE_GRUPO_SUP = TITULO_GRUPO + HOLGURA   # espacio vedado arriba de una fila
BORDE_GRUPO_INF = PAD_GRUPO + HOLGURA      # espacio vedado abajo de una fila
ALTO_CARRIL_MIN = 26.0
SEP_CARRIL = 14.0
ANCHO_ETIQUETA = 230.0             # las etiquetas se envuelven a este ancho

# Paleta sobria: la caja es blanca y el color vive en una barra de 4px arriba.
# El color informa la categoria, no decora el relleno. Cuatro acentos, no siete.
ACENTOS = {
    "principal": "#1F4E79",   # azul profundo — lo central del diagrama
    "apoyo":     "#4E8098",   # azul apagado  — lo que rodea
    "acento":    "#B5651D",   # terracota     — lo que hay que mirar
    "neutro":    "#8C99A6",   # gris azulado  — lo secundario
    # estados, para roadmaps con "cajas_rellenas": true
    "hecho":     "#2E7D32",   # verde
    "curso":     "#C77700",   # ambar
    "pendiente": "#7A8794",   # gris
}
# Relleno de caja para el modo "cajas_rellenas": un tinte claro del acento.
TINTES = {
    "principal": "#DCE7F3", "apoyo": "#DDEAF0", "acento": "#F6E3D3",
    "neutro": "#E9EDF1", "hecho": "#D4EDD6", "curso": "#FCE8C8",
    "pendiente": "#ECEFF2",
}
# Nombres viejos del spec, para no reescribir diagramas ya hechos.
ALIAS_COLOR = {
    "azul": "principal", "verde": "apoyo", "naranja": "acento",
    "amarillo": "apoyo", "rojo": "acento", "morado": "neutro",
    "gris": "neutro", "nota": "neutro",
}

TINTA = "#1F2933"        # texto principal
TINTA_SUAVE = "#6B7A8C"  # texto secundario y etiquetas de flecha
BORDE = "#D3D8DE"        # borde de las cajas
PAPEL = "#FFFFFF"
BANDA = "#F6F8F9"        # relleno de los grupos
LINEA = "#A8B3BF"        # flechas
ALTO_BARRA = 4.0
ALTO_TITULO = 26.0


def acento(nombre):
    return ACENTOS.get(ALIAS_COLOR.get(nombre, nombre), ACENTOS["neutro"])


def esc(t):
    return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def html_caja(nodo):
    """Arma el label HTML y devuelve (html, alto_del_texto).

    Dos tamanos: el nombre en 13px negrita sobre tinta, el detalle en 11px
    gris. Es lo que da jerarquia sin necesidad de pintar la caja entera.
    """
    ancho = nodo["_w"] - 2 * PAD_H
    partes, alto = [], 0.0
    if nodo.get("titulo"):
        ls = envolver(nodo["titulo"], ancho, PX_TITULO, True)
        partes.append(
            f'<b style="font-size:{PX_TITULO}px;color:{TINTA}">'
            + "<br/>".join(esc(x) for x in ls) + "</b>")
        alto += len(ls) * alto_linea(PX_TITULO)
    for linea in nodo.get("lineas", []):
        cursiva = linea.startswith("_") and linea.endswith("_")
        txt = linea[1:-1] if cursiva else linea
        ls = envolver(txt, ancho, PX_CUERPO)
        cuerpo = "<br/>".join(esc(x) for x in ls)
        if cursiva:
            cuerpo = f"<i>{cuerpo}</i>"
        partes.append(
            f'<span style="font-size:{PX_CUERPO}px;color:{TINTA_SUAVE}">'
            f"{cuerpo}</span>")
        alto += len(ls) * alto_linea(PX_CUERPO)
    return "<br/>".join(partes), alto


def estilo_caja(nodo):
    forma = nodo.get("forma", "caja")
    nombre = ALIAS_COLOR.get(nodo.get("color", "neutro"), nodo.get("color", "neutro"))
    col = acento(nombre)
    comun = (f"whiteSpace=wrap;html=1;fillColor={PAPEL};strokeColor={BORDE};"
             f"strokeWidth=1;fontColor={TINTA};")
    if nodo.get("_relleno"):
        # modo marcado: la caja entera lleva el color, con borde del acento
        comun = (f"whiteSpace=wrap;html=1;fillColor={TINTES.get(nombre, PAPEL)};"
                 f"strokeColor={col};strokeWidth=2;fontColor={TINTA};"
                 + ("dashed=1;dashPattern=6 4;" if nodo.get("punteado") else ""))
        if forma == "caja":
            return "rounded=1;arcSize=12;" + comun
    if forma == "cilindro":
        return ("shape=cylinder3;boundedLbl=1;backgroundOutline=1;size=12;"
                "verticalAlign=middle;spacingTop=6;" + comun)
    if forma == "nota":
        return ("rounded=0;align=left;verticalAlign=top;spacingLeft=12;"
                f"spacingTop=8;fillColor={BANDA};strokeColor={BORDE};"
                f"whiteSpace=wrap;html=1;fontColor={TINTA};")
    if forma == "estado":
        return f"rounded=1;arcSize=20;strokeColor={col};strokeWidth=2;" + comun
    if forma == "entidad":
        return "rounded=0;verticalAlign=top;spacingTop=10;spacingLeft=4;" + comun
    if forma == "actor":
        return ("shape=umlActor;verticalLabelPosition=bottom;verticalAlign=top;"
                f"html=1;outlineConnect=0;strokeColor={TINTA_SUAVE};"
                f"fontColor={TINTA};")
    if forma == "inicio":
        return f"ellipse;html=1;fillColor={TINTA};strokeColor={TINTA};"
    if forma == "fin":
        return (f"ellipse;html=1;fillColor={PAPEL};strokeColor={TINTA};"
                "strokeWidth=3;")
    return "rounded=0;" + comun


def lleva_barra(nodo):
    """Que formas reciben la barra de color superior."""
    if nodo.get("_relleno"):
        return False   # la caja entera ya lleva el color
    return nodo.get("forma", "caja") in ("caja", "entidad", "cilindro")


# --- calculo de la grilla ------------------------------------------------

def medir_nodos(pagina):
    anchos_col = pagina.get("anchos_columna", {})
    for n in pagina["nodos"]:
        forma = n.get("forma", "caja")
        if forma == "actor":
            n["_w"], n["_h"] = 40.0, 66.0
            n["_h_layout"] = 66.0 + 2 * alto_linea(PX_CUERPO)   # label debajo
            n["_html"] = (
                f'<b style="font-size:{PX_TITULO}px;color:{TINTA}">'
                f"{esc(n.get('titulo',''))}</b>"
                + "".join(
                    f'<br/><span style="font-size:{PX_CUERPO}px;'
                    f'color:{TINTA_SUAVE}"><i>{esc(l.strip("_"))}</i></span>'
                    for l in n.get("lineas", [])))
            continue
        if forma in ("inicio", "fin"):
            n["_w"] = n["_h"] = n["_h_layout"] = 28.0
            n["_html"] = ""
            continue
        n["_w"] = float(n.get("ancho")
                        or anchos_col.get(str(n["col"]))
                        or ANCHO_COL)
        html, alto_texto = html_caja(n)
        n["_html"] = html
        extra = ALTO_BARRA if lleva_barra(n) else 0.0
        if forma == "cilindro":
            extra += 14           # la tapa del cilindro come alto util
        n["_h"] = max(ALTO_MIN, alto_texto + 2 * PAD_V + extra)
        n["_h_layout"] = n["_h"]


def _elegir_corredor(o, d, ocupadas):
    """Corredor por el que viaja una flecha ruteada.

    Una flecha ruteada tiene un tramo vertical largo y uno corto. El largo cae
    en la columna del origen o en la del destino segun donde se ponga el
    corredor, y hay que elegir la que este LIBRE en las filas del medio: una
    regla fija falla siempre en la mitad de los casos. Se comprobo con dos
    ejemplos opuestos el 2026-09-09 — en la pagina 3 servia la columna del
    destino, en la 6 la del origen.
    """
    if d["fila"] == o["fila"]:
        return o["fila"] + 1

    lo, hi = sorted((o["fila"], d["fila"]))
    medio = range(lo + 1, hi)
    libre_origen = all((o["col"], k) not in ocupadas for k in medio)
    libre_destino = all((d["col"], k) not in ocupadas for k in medio)

    if d["fila"] > o["fila"]:                 # baja
        por_origen, por_destino = d["fila"], o["fila"] + 1
    else:                                     # sube
        por_origen, por_destino = d["fila"] + 1, o["fila"]

    if libre_origen:
        return por_origen
    if libre_destino:
        return por_destino
    return por_origen        # ninguna limpia: el validador lo va a marcar


def clasificar_flechas(pagina, por_id):
    """Decide por donde va cada flecha y en que corredor cae su etiqueta."""
    ocupadas = {(n["col"], n["fila"]) for n in pagina["nodos"]}
    for f in pagina["flechas"]:
        o, d = por_id[f["de"]], por_id[f["a"]]
        f["_o"], f["_d"] = o, d
        mismo_fila = o["fila"] == d["fila"]
        mismo_col = o["col"] == d["col"]
        if mismo_fila and abs(o["col"] - d["col"]) == 1:
            f["_modo"] = "horizontal"
            f["_corredor_x"] = min(o["col"], d["col"])
        elif mismo_col and abs(o["fila"] - d["fila"]) == 1:
            f["_modo"] = "vertical"
            f["_corredor_y"] = max(o["fila"], d["fila"])
        elif mismo_col:
            # salto dentro de la misma columna: si fuera recto atravesaria
            # los nodos del medio, asi que sale por un carril lateral
            f["_modo"] = "lateral"
        else:
            f["_modo"] = "ruteada"
            f["_corredor_y"] = _elegir_corredor(o, d, ocupadas)
        if f.get("etiqueta"):
            f["_lineas_etq"] = envolver(f["etiqueta"], ANCHO_ETIQUETA,
                                        PX_ETIQUETA)
        else:
            f["_lineas_etq"] = []
        f["_w_etq"] = max(
            [ancho_texto(l, PX_ETIQUETA) for l in f["_lineas_etq"]] or [0])
        f["_h_etq"] = len(f["_lineas_etq"]) * alto_linea(PX_ETIQUETA)


def _lado_salida(f):
    o, d = f["_o"], f["_d"]
    if f["_modo"] == "horizontal":
        return "der" if o["col"] < d["col"] else "izq"
    if f["_modo"] == "lateral":
        return f["_lado"]
    if f["_modo"] == "vertical":
        return "abajo" if o["fila"] < d["fila"] else "arriba"
    return "abajo" if f["_corredor_y"] > o["fila"] else "arriba"


def _lado_entrada(f):
    o, d = f["_o"], f["_d"]
    if f["_modo"] == "horizontal":
        return "izq" if o["col"] < d["col"] else "der"
    if f["_modo"] == "lateral":
        return f["_lado"]
    return "arriba" if d["fila"] > o["fila"] else "abajo"


def separar_paralelas(pagina):
    """Reparte los puntos de anclaje sobre cada borde de cada nodo.

    Clave: el reparto es **por borde**, mezclando salidas y entradas en la
    misma bolsa. Calcularlos por separado fue el bug que se vio en pantalla:
    las salidas caian en 0.2/0.4/0.6/0.8 y las entradas en 0.333/0.667, y sobre
    una caja de 280px el 0.4 y el 0.333 quedan a 19px — se leen como el mismo
    punto. Un borde, una sola serie.
    """
    bordes = {}
    for f in pagina["flechas"]:
        bordes.setdefault((f["_o"]["id"], _lado_salida(f)), []).append(
            (f, "_ancla"))
        bordes.setdefault((f["_d"]["id"], _lado_entrada(f)), []).append(
            (f, "_ancla_ent"))
    por_id = {n["id"]: n for n in pagina["nodos"]}
    for (nid, lado), ocupantes in bordes.items():
        # Orden sobre el borde = orden del otro extremo. En el orden del spec,
        # una flecha que iba a la izquierda podia salir por la derecha y cruzar a
        # sus vecinas (visto en el C2 de api-core, 2026-09-10).
        def hacia(par):
            f, clave = par
            otro = f["_d"] if clave == "_ancla" else f["_o"]
            if lado in ("arriba", "abajo"):
                return (otro["col"], otro["fila"])
            return (otro["fila"], otro["col"])
        ocupantes.sort(key=hacia)
        n = len(ocupantes)
        nodo = por_id[nid]
        largo = nodo["_w"] if lado in ("arriba", "abajo") else nodo["_h"]
        # Si el borde es corto (un actor mide 40px), repartir da puntos a 13px
        # que se leen como uno solo mal dibujado. Ahi conviene lo contrario:
        # que salgan todas del centro y abran en abanico, que se lee a proposito.
        if n > 1 and largo / (n + 1) >= SEP_ANCLAJE_MIN:
            paso = 1.0 / (n + 1)
            for k, (f, clave) in enumerate(ocupantes):
                f[clave] = round(paso * (k + 1), 3)
        else:
            for f, clave in ocupantes:
                f[clave] = 0.5


def asignar_laterales(pagina):
    """Reparte los saltos verticales en carriles a izquierda y derecha."""
    laterales = [f for f in pagina["flechas"] if f["_modo"] == "lateral"]
    izq, der = [], []
    for i, f in enumerate(laterales):
        lado = f.get("lado") or ("izq" if i % 2 == 0 else "der")
        (izq if lado == "izq" else der).append(f)
    for lista, lado in ((izq, "izq"), (der, "der")):
        for k, f in enumerate(lista):
            f["_lado"], f["_carril_lat"] = lado, k
    pagina["_n_lat_izq"], pagina["_n_lat_der"] = len(izq), len(der)


SEP_LATERAL = 70.0
SEP_ANCLAJE_MIN = 24.0   # px minimos entre dos flechas del mismo borde
SEP_CARRIL_X = 26.0      # aire horizontal entre dos flechas del mismo carril


def _tramo_x(f):
    """Rango horizontal que ocupa el tramo de una flecha en su corredor,
    incluyendo el ancho de su etiqueta, que va centrada sobre el tramo."""
    o, d = f["_o"], f["_d"]
    sx = o["_x"] + o["_w"] * f.get("_ancla", 0.5)
    tx = d["_x"] + d["_w"] * f.get("_ancla_ent", 0.5)
    izq, der = min(sx, tx), max(sx, tx)
    if f["_w_etq"]:
        medio = (sx + tx) / 2
        izq = min(izq, medio - f["_w_etq"] / 2)
        der = max(der, medio + f["_w_etq"] / 2)
    return izq, der


def _empaquetar_carriles(lista):
    """Reparte las flechas de un corredor en carriles, reusando el mismo cuando
    sus tramos no se cruzan.

    Sin esto, cada flecha reclamaba su propio carril y el corredor crecia sin
    razon: cuatro flechas saliendo del mismo nodo hacia lados opuestos nunca se
    tocan, pero ocupaban cuatro alturas. Es coloreo de intervalos, avaro.
    Devuelve la altura de cada carril usado.
    """
    if not lista:
        return []
    for f in lista:
        f["_tramo"] = _tramo_x(f)
        f["_alto_carril"] = max(ALTO_CARRIL_MIN, f["_h_etq"])
    ocupacion = []          # borde derecho ya usado por cada carril
    alturas = []
    for f in sorted(lista, key=lambda g: g["_tramo"][0]):
        izq, der = f["_tramo"]
        for k, tope in enumerate(ocupacion):
            if izq > tope + SEP_CARRIL_X:
                f["_carril"] = k
                ocupacion[k] = der
                alturas[k] = max(alturas[k], f["_alto_carril"])
                break
        else:
            f["_carril"] = len(ocupacion)
            ocupacion.append(der)
            alturas.append(f["_alto_carril"])
    return alturas


def dimensionar(pagina, por_id):
    nodos = pagina["nodos"]
    n_col = max(n["col"] for n in nodos) + 1
    n_fila = max(n["fila"] for n in nodos) + 1

    ancho_col = [0.0] * n_col
    alto_fila = [0.0] * n_fila
    for n in nodos:
        ancho_col[n["col"]] = max(ancho_col[n["col"]], n["_w"])
        alto_fila[n["fila"]] = max(alto_fila[n["fila"]], n["_h_layout"])

    # corredores verticales: uno menos que columnas
    corr_x = [CORREDOR_X_MIN] * max(0, n_col - 1)
    for f in pagina["flechas"]:
        if f["_modo"] == "horizontal" and f["_w_etq"]:
            i = f["_corredor_x"]
            # la etiqueta va centrada, y a cada lado hay un grupo que se mete
            # PAD_GRUPO hacia adentro: hay que dejarle holgura a ambos
            corr_x[i] = max(corr_x[i], f["_w_etq"] + 2 * BORDE_GRUPO_INF)

    # Las x se resuelven primero, porque no dependen de los corredores
    # horizontales y hacen falta para repartir los carriles con criterio.
    margen_izq = MARGEN + pagina.get("_n_lat_izq", 0) * SEP_LATERAL
    margen_der = MARGEN + pagina.get("_n_lat_der", 0) * SEP_LATERAL
    x_col, x = [], margen_izq
    for i in range(n_col):
        x_col.append(x)
        x += ancho_col[i] + (corr_x[i] if i < len(corr_x) else 0)
    # x quedo en el borde derecho de la ultima columna: el bucle no agrega
    # corredor despues de la ultima, asi que no hay nada que descontar
    ancho_total = x + margen_der
    for n in nodos:
        n["_x"] = x_col[n["col"]] + (ancho_col[n["col"]] - n["_w"]) / 2

    # corredores horizontales: uno arriba de cada fila y uno al final
    carriles = {j: [] for j in range(n_fila + 1)}
    for f in pagina["flechas"]:
        if f["_modo"] in ("ruteada", "vertical"):
            carriles[f["_corredor_y"]].append(f)

    # el corredor de arriba tiene que alojar el titulo de la pagina Y el borde
    # superior del primer grupo: si no, la etiqueta del grupo cae debajo del
    # titulo y se leen encimadas
    alto_titulo = (ALTO_TITULO + BORDE_GRUPO_SUP) if pagina.get("titulo") else 0.0

    # que filas tienen un recuadro de grupo dibujado encima: solo esas obligan
    # a reservar el borde vedado. Reservarlo en todos los corredores estiraba
    # el diagrama a lo largo sin nada que proteger
    grupos = pagina.get("grupos", [])
    dibujados = {g["id"] for g in grupos
                 if sum(1 for n in nodos if n.get("grupo") == g["id"])
                 >= (1 if g.get("padre") else 2)}
    filas_con_grupo = {n["fila"] for n in nodos if n.get("grupo") in dibujados}

    # un grupo padre (semana con carriles) envuelve a sus carriles con su
    # propio titulo arriba y su padding abajo: la fila donde empieza y la
    # fila donde termina necesitan ese espacio extra en el corredor
    padre_de = {g["id"]: g.get("padre") for g in grupos}
    filas_por_padre = {}
    for n in nodos:
        p = padre_de.get(n.get("grupo"))
        if p and n.get("grupo") in dibujados:
            filas_por_padre.setdefault(p, set()).add(n["fila"])
    inicio_padre = {min(f) for f in filas_por_padre.values()}
    fin_padre = {max(f) for f in filas_por_padre.values()}

    corr_y, arriba_corr = [], []
    for j in range(n_fila + 1):
        if j == 0:
            base = MARGEN + (ALTO_TITULO if pagina.get("titulo") else 0.0)
        elif j < n_fila:
            base = CORREDOR_Y_MIN
        else:
            base = MARGEN
        arriba = BORDE_GRUPO_INF if (j - 1) in filas_con_grupo else HOLGURA
        abajo = BORDE_GRUPO_SUP if j in filas_con_grupo else HOLGURA
        if (j - 1) in fin_padre:
            arriba += PAD_GRUPO
        if j in inicio_padre:
            abajo += TITULO_GRUPO
        arriba_corr.append(arriba)
        if j == 0 and pagina.get("titulo"):
            base += abajo
        elif j < n_fila:
            base = max(base, arriba + abajo + HOLGURA)
        lista = _empaquetar_carriles(carriles[j])
        if not lista:
            corr_y.append(base)
            continue
        alto = arriba
        for altura in lista:
            alto += altura + SEP_CARRIL
        corr_y.append(max(base, alto + abajo))

    y_fila, y = [], 0.0
    for j in range(n_fila):
        y += corr_y[j]
        y_fila.append(y)
        y += alto_fila[j]
    alto_total = y + corr_y[n_fila]

    for n in nodos:
        fi = n["fila"]
        n["_y"] = y_fila[fi]
        # alineacion optica: todas las cajas de una fila miden lo mismo. Alturas
        # dispares en una misma linea es lo que hace ver "descuadrado" el bloque
        if n.get("forma", "caja") in ("caja", "entidad", "cilindro", "estado"):
            n["_h"] = alto_fila[fi]

    pagina["_x_col"], pagina["_ancho_col"] = x_col, ancho_col
    pagina["_y_fila"], pagina["_alto_fila"] = y_fila, alto_fila
    pagina["_corr_x"], pagina["_corr_y"] = corr_x, corr_y
    pagina["_carriles"] = carriles
    pagina["_filas_grupo"] = filas_con_grupo
    pagina["_arriba_corr"] = arriba_corr
    pagina["_ancho_total"], pagina["_alto_total"] = ancho_total, alto_total

    # x de cada carril lateral, por fuera de la grilla
    for f in pagina["flechas"]:
        if f["_modo"] != "lateral":
            continue
        c = f["_o"]["col"]
        if f["_lado"] == "izq":
            f["_x_carril"] = (x_col[c] - BORDE_GRUPO_INF
                              - f["_carril_lat"] * SEP_LATERAL)
        else:
            f["_x_carril"] = (x_col[c] + ancho_col[c] + BORDE_GRUPO_INF
                              + f["_carril_lat"] * SEP_LATERAL)

    # y de cada carril dentro de su corredor
    for j, lista in carriles.items():
        if not lista:
            continue
        tope = (y_fila[j - 1] + alto_fila[j - 1]) if j > 0 else 0.0
        # la altura de cada carril es la de la flecha mas alta que lo comparte
        altos = {}
        for f in lista:
            altos[f["_carril"]] = max(altos.get(f["_carril"], 0.0),
                                      f["_alto_carril"])
        y_de = {}
        arriba = pagina["_arriba_corr"][j]
        cursor = tope + arriba
        for k in sorted(altos):
            y_de[k] = cursor + altos[k] / 2
            cursor += altos[k] + SEP_CARRIL
        for f in lista:
            f["_y_carril"] = y_de[f["_carril"]]


def geometria_grupos(pagina, por_id):
    """Cajas (grupo, x, y, w, h) en coordenadas absolutas, padres primero.

    Un grupo con "padre" es un carril dentro de otro grupo: el padre no tiene
    nodos propios, se dimensiona alrededor de sus carriles.
    """
    cajas, por_grupo = [], {}
    grupos = pagina.get("grupos", [])
    for g in grupos:
        miembros = [n for n in pagina["nodos"] if n.get("grupo") == g["id"]]
        # un grupo de uno no agrupa nada: el recuadro solo agrega ruido
        # (salvo que sea un carril: un carril de uno sigue siendo un carril)
        if len(miembros) < (1 if g.get("padre") else 2):
            continue
        x1 = min(n["_x"] for n in miembros) - PAD_GRUPO
        y1 = min(n["_y"] for n in miembros) - TITULO_GRUPO
        x2 = max(n["_x"] + n["_w"] for n in miembros) + PAD_GRUPO
        y2 = max(n["_y"] + n["_h_layout"] for n in miembros) + PAD_GRUPO
        por_grupo[g["id"]] = (g, x1, y1, x2 - x1, y2 - y1)

    # padres: envuelven a sus carriles con el mismo padding y su propio titulo
    for g in grupos:
        hijos = [por_grupo[h["id"]] for h in grupos
                 if h.get("padre") == g["id"] and h["id"] in por_grupo]
        if not hijos:
            continue
        x1 = min(c[1] for c in hijos) - PAD_GRUPO
        y1 = min(c[2] for c in hijos) - TITULO_GRUPO
        x2 = max(c[1] + c[3] for c in hijos) + PAD_GRUPO
        y2 = max(c[2] + c[4] for c in hijos) + PAD_GRUPO
        por_grupo[g["id"]] = (g, x1, y1, x2 - x1, y2 - y1)

    # padres antes que hijos, para que el contenedor exista al colgar el carril
    for g in grupos:
        if g["id"] in por_grupo and not g.get("padre"):
            cajas.append(por_grupo[g["id"]])
    for g in grupos:
        if g["id"] in por_grupo and g.get("padre"):
            cajas.append(por_grupo[g["id"]])
    return cajas


# --- emision del XML -----------------------------------------------------

def celda(root, cid, valor, estilo, x, y, w, h, vertex=True, parent="1"):
    c = ET.SubElement(root, "mxCell", {
        "id": cid, "value": valor, "style": estilo,
        "vertex": "1", "parent": parent})
    ET.SubElement(c, "mxGeometry", {
        "x": f"{x:.0f}", "y": f"{y:.0f}",
        "width": f"{w:.0f}", "height": f"{h:.0f}", "as": "geometry"})
    return c


def punto_medio_arco(pts):
    largos = [((pts[i + 1][0] - pts[i][0]) ** 2
               + (pts[i + 1][1] - pts[i][1]) ** 2) ** 0.5
              for i in range(len(pts) - 1)]
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


def emitir_flecha(root, f, idx):
    o, d = f["_o"], f["_d"]
    cx_o, cy_o = o["_x"] + o["_w"] / 2, o["_y"] + o["_h"] / 2
    cx_d, cy_d = d["_x"] + d["_w"] / 2, d["_y"] + d["_h"] / 2

    trazo = f.get("tipo", "solida")
    partes = ["edgeStyle=orthogonalEdgeStyle", "rounded=1", "arcSize=6",
              "html=1", "endArrow=blockThin", "endFill=1", "endSize=6",
              "jettySize=14", f"fontSize={PX_ETIQUETA}",
              f"fontColor={TINTA_SUAVE}", f"strokeColor={LINEA}",
              "strokeWidth=1"]
    if trazo == "punteada":
        partes.append("dashed=1;dashPattern=4 4")
    if trazo == "gruesa":
        partes += [f"strokeColor={TINTA}", "strokeWidth=1.5"]
    if f.get("color"):
        partes.append(f"strokeColor={acento(f['color'])}")
    if f.get("bidireccional"):
        partes += ["startArrow=blockThin", "startFill=1", "startSize=6"]

    puntos, deseado = [], None
    if f["_modo"] == "horizontal":
        izq = o["col"] < d["col"]
        a, b = f.get("_ancla", 0.5), f.get("_ancla_ent", 0.5)
        partes += [f"exitX={1 if izq else 0}", f"exitY={a}", "exitDx=0", "exitDy=0",
                   f"entryX={0 if izq else 1}", f"entryY={b}",
                   "entryDx=0", "entryDy=0"]
        sx = o["_x"] + (o["_w"] if izq else 0)
        tx = d["_x"] + (0 if izq else d["_w"])
        deseado = ((sx + tx) / 2, o["_y"] + o["_h"] * a)
    elif f["_modo"] == "vertical":
        baja = o["fila"] < d["fila"]
        a, b = f.get("_ancla", 0.5), f.get("_ancla_ent", 0.5)
        partes += [f"exitX={a}", f"exitY={1 if baja else 0}", "exitDx=0", "exitDy=0",
                   f"entryX={b}", f"entryY={0 if baja else 1}",
                   "entryDx=0", "entryDy=0"]
        deseado = (o["_x"] + o["_w"] * a,
                   f.get("_y_carril", (cy_o + cy_d) / 2))
    elif f["_modo"] == "lateral":
        izq = f["_lado"] == "izq"
        xl = f["_x_carril"]
        a, b = f.get("_ancla", 0.5), f.get("_ancla_ent", 0.5)
        partes += [f"exitX={0 if izq else 1}", f"exitY={a}", "exitDx=0", "exitDy=0",
                   f"entryX={0 if izq else 1}", f"entryY={b}",
                   "entryDx=0", "entryDy=0"]
        sy, ty = o["_y"] + o["_h"] * a, d["_y"] + d["_h"] * b
        puntos = [(xl, sy), (xl, ty)]
        deseado = (xl, (sy + ty) / 2)
        cy_o, cy_d = sy, ty
    else:
        baja = f["_corredor_y"] > o["fila"]
        y_carril = f["_y_carril"]
        a, b = f.get("_ancla", 0.5), f.get("_ancla_ent", 0.5)
        partes += [f"exitX={a}", f"exitY={1 if baja else 0}", "exitDx=0", "exitDy=0",
                   f"entryX={b}", f"entryY={0 if d['fila'] > o['fila'] else 1}",
                   "entryDx=0", "entryDy=0"]
        sx, tx = o["_x"] + o["_w"] * a, d["_x"] + d["_w"] * b
        puntos = [(sx, y_carril), (tx, y_carril)]
        deseado = ((sx + tx) / 2, y_carril)
        cx_o, cx_d = sx, tx

    eid = f"f{idx}"
    celdaf = ET.SubElement(root, "mxCell", {
        "id": eid, "value": "", "style": ";".join(partes) + ";",
        "edge": "1", "parent": "1",
        "source": o["id"], "target": d["id"]})
    geo = ET.SubElement(celdaf, "mxGeometry",
                        {"relative": "1", "as": "geometry"})
    if puntos:
        arr = ET.SubElement(geo, "Array", {"as": "points"})
        for px, py in puntos:
            ET.SubElement(arr, "mxPoint", {"x": f"{px:.0f}", "y": f"{py:.0f}"})

    if f["_lineas_etq"]:
        # el label se ancla al punto medio del recorrido; le calculamos el
        # desplazamiento exacto para que caiga en el corredor, no sobre una caja
        recorrido = [(cx_o, cy_o)] + puntos + [(cx_d, cy_d)]
        mx, my = punto_medio_arco(recorrido)
        dx, dy = deseado[0] - mx, deseado[1] - my
        texto = "<br/>".join(esc(l) for l in f["_lineas_etq"])
        lbl = ET.SubElement(root, "mxCell", {
            "id": f"{eid}l", "value": texto,
            "style": ("edgeLabel;html=1;align=center;verticalAlign=middle;"
                      f"resizable=0;points=[];fontSize={PX_ETIQUETA};"
                      f"fontColor={TINTA_SUAVE};labelBackgroundColor={PAPEL};"
                      "spacing=2;"),
            "vertex": "1", "connectable": "0", "parent": eid})
        g2 = ET.SubElement(lbl, "mxGeometry",
                           {"x": "0", "relative": "1", "as": "geometry"})
        ET.SubElement(g2, "mxPoint",
                      {"x": f"{dx:.0f}", "y": f"{dy:.0f}", "as": "offset"})


def construir_pagina(pagina, indice):
    if pagina.get("tipo") == "secuencia":
        # import tardio: secuencia.py reutiliza las utilidades de este modulo
        from secuencia import construir_secuencia
        return construir_secuencia(pagina, indice)
    por_id = {n["id"]: n for n in pagina["nodos"]}
    _notas_prohibidas(pagina)
    if pagina.get("cajas_rellenas"):
        for n in pagina["nodos"]:
            n["_relleno"] = True
    medir_nodos(pagina)
    clasificar_flechas(pagina, por_id)
    asignar_laterales(pagina)   # antes de separar: define el lado de cada lateral
    separar_paralelas(pagina)
    dimensionar(pagina, por_id)

    diagrama = ET.Element("diagram", {
        "id": f"pag{indice}", "name": pagina["nombre"]})
    modelo = ET.SubElement(diagrama, "mxGraphModel", {
        "dx": "1400", "dy": "900", "grid": "1", "gridSize": "10",
        "guides": "1", "tooltips": "1", "connect": "1", "arrows": "1",
        "fold": "1", "page": "1", "pageScale": "1",
        "pageWidth": "1600", "pageHeight": "1000",
        "math": "0", "shadow": "0"})
    root = ET.SubElement(modelo, "root")
    ET.SubElement(root, "mxCell", {"id": "0"})
    ET.SubElement(root, "mxCell", {"id": "1", "parent": "0"})

    # 1) bandas de grupo primero, para que queden atras. Sin linea punteada:
    #    un relleno muy claro agrupa igual y no compite con las cajas.
    #    Con "contenedor": true (en el grupo, o "grupos_contenedores": true en
    #    la pagina) la banda es un contenedor real de draw.io: colapsable, y
    #    sus nodos van como hijos con coordenadas relativas, asi que al mover
    #    o plegar la banda se mueve todo junto.
    contenedores = {}
    for g, x, y, w, h in geometria_grupos(pagina, por_id):
        es_contenedor = g.get("contenedor", pagina.get("grupos_contenedores", False))
        extra, padre, px, py = "", "1", 0.0, 0.0
        if es_contenedor:
            extra = (f"container=1;collapsible=1;strokeColor={BORDE};"
                     f"collapsedFillColor={BANDA};")
            contenedores[g["id"]] = (x, y)
        if g.get("padre") in contenedores:
            padre = f"g-{g['padre']}"
            px, py = contenedores[g["padre"]]
        # un carril se distingue de su padre por un relleno apenas mas claro;
        # "relleno" (hex) en el grupo pisa el color, y "titulo_color" el del rotulo
        relleno = g.get("relleno", PAPEL if g.get("padre") else BANDA)
        color_titulo = g.get("titulo_color", TINTA_SUAVE)
        tam_titulo = 12 if not g.get("padre") and pagina.get("cajas_rellenas") else 10
        celda(root, f"g-{g['id']}",
              f'<span style="letter-spacing:1px">'
              f'{esc(g.get("titulo", "").upper())}</span>',
              f"rounded=0;whiteSpace=wrap;html=1;fillColor={relleno};"
              f"strokeColor=none;verticalAlign=top;align=left;spacingLeft=12;"
              f"spacingTop=4;fontSize={tam_titulo};fontStyle=1;fontColor={color_titulo};"
              + extra,
              x - px, y - py, w, h, parent=padre)

    # 2) titulo de la pagina, arriba del todo. Se dimensiona al texto: una caja
    #    de ancho completo se solapa con todo y esconde el choque al validador
    if pagina.get("titulo"):
        ancho_t = min(ancho_texto(pagina["titulo"], 14, True) + 16,
                      pagina["_ancho_total"] - 2 * MARGEN)
        celda(root, "titulo",
              f'<span style="color:{TINTA}">{esc(pagina["titulo"])}</span>',
              "text;html=1;align=left;verticalAlign=middle;fontSize=14;"
              "fontStyle=1;",
              MARGEN, MARGEN - 6, ancho_t, ALTO_TITULO)

    # 3) nodos, cada uno con su barra de color como hijo. Si su grupo es un
    #    contenedor, el nodo cuelga de el con coordenadas relativas.
    for n in pagina["nodos"]:
        gid = n.get("grupo")
        if gid in contenedores:
            gx, gy = contenedores[gid]
            celda(root, n["id"], n["_html"], estilo_caja(n),
                  n["_x"] - gx, n["_y"] - gy, n["_w"], n["_h"],
                  parent=f"g-{gid}")
        else:
            celda(root, n["id"], n["_html"], estilo_caja(n),
                  n["_x"], n["_y"], n["_w"], n["_h"])
        if lleva_barra(n):
            barra = ET.SubElement(root, "mxCell", {
                "id": f"{n['id']}-barra", "value": "",
                "style": (f"rounded=0;html=1;fillColor="
                          f"{acento(n.get('color', 'neutro'))};"
                          "strokeColor=none;movable=0;resizable=0;"
                          "deletable=0;connectable=0;"),
                "vertex": "1", "parent": n["id"]})
            ET.SubElement(barra, "mxGeometry", {
                "x": "0", "y": "0", "width": f"{n['_w']:.0f}",
                "height": f"{ALTO_BARRA:.0f}", "as": "geometry"})

    # 4) flechas
    for i, f in enumerate(pagina["flechas"]):
        emitir_flecha(root, f, i)

    return diagrama


def _notas_prohibidas(pagina):
    """Los paneles de texto al costado no van. Nunca.

    Regla del responsable del repo (2026-09-09): un diagrama muestra, no explica. Un bloque de
    prosa flotando al lado de las cajas no es parte del dibujo — es una nota al
    pie que se coló adentro, y es lo primero que hace ver cargada una lamina.
    Si el contexto hace falta, va en el .diagrama.json bajo una clave que
    empiece con guion bajo (no se dibuja), o en el documento que cita el
    diagrama.
    """
    if pagina.get("notas"):
        raise SystemExit(
            f"ERROR en la pagina '{pagina['nombre']}': trae 'notas'.\n"
            "Los paneles de texto al costado no van en ningun diagrama.\n"
            "Renombra la clave a '_apuntes_no_se_dibujan' si queres conservar "
            "el texto en el archivo fuente sin que salga en la lamina.")




def main(ruta_spec):
    with open(ruta_spec, encoding="utf-8") as fh:
        spec = json.load(fh)

    raiz = ET.Element("mxfile", {
        "host": "app.diagrams.net", "version": "24.7.17", "type": "device"})
    for i, pagina in enumerate(spec["paginas"]):
        raiz.append(construir_pagina(pagina, i))

    ET.indent(raiz, space="  ")
    salida = spec["archivo"]
    if not os.path.isabs(salida):
        salida = os.path.join(os.path.dirname(os.path.abspath(ruta_spec)),
                              salida)
    salida = os.path.normpath(salida)
    with open(salida, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(ET.tostring(raiz, encoding="unicode"))
    print(f"Generado: {salida}")
    print(f"  {len(spec['paginas'])} pagina(s)")
    return salida


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(2)
    main(sys.argv[1])
