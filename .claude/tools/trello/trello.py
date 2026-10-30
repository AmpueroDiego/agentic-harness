"""Conector del tablero Trello del proyecto para la skill /trello.

Reemplaza a scripts/trello.ps1, que no conecta en la maquina del responsable: PowerShell y curl
usan schannel y el handshake contra api.trello.com se cae. Python usa OpenSSL y conecta.

Reglas que el script hace cumplir, en vez de confiar en que alguien las recuerde
(la fuente es docs/guias/ESTANDAR-ENTREGA-TRELLO-Y-GITHUB.md):
  - Toda mutacion es una SIMULACION salvo que se pase --aplicar. La simulacion imprime la
    propuesta exacta para mostrarsela al usuario antes de tocar el tablero.
  - Columnas, etiquetas y miembros se resuelven por nombre contra el tablero vivo, nunca
    contra ids anotados: ya hubo ids que pasaron a apuntar a otra columna.
  - El titulo de una tarjeta existente no se puede cambiar: no hay opcion para hacerlo.
  - No hay acciones de borrado: ni tarjetas, ni etiquetas, ni miembros, ni adjuntos.
  - Descripcion de 560 caracteres como maximo.
  - "revisor principal" es siempre Revisor Principal (<revisor-principal>), nunca otros integrantes.
  - Despues de escribir, se relee la tarjeta y se compara campo por campo.

Uso rapido:
  python trello.py tablero
  python trello.py buscar "mensajes en vivo"
  python trello.py ver <card-id>
  python trello.py crear --columna Backlog --titulo "... (web-app)" --desc-archivo desc.md --etiqueta Frontend --miembro <responsable>
  python trello.py actualizar <card-id> --columna "En revision (Revisor Principal)" --miembro 'revisor principal' --inicio 2026-09-10 --vence 2026-09-10
  python trello.py adjuntar <card-id> --url https://github.com/<org>/web-app/pull/12 --nombre "#12 Titulo del PR"
  python trello.py ordenar --columna Backlog --orden-archivo orden.txt
Agregar --aplicar a crear/actualizar/adjuntar/comentar/ordenar solo despues de la aprobacion expresa.
"""

import argparse
import datetime
import json
import mimetypes
import os
import re
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import uuid

LIMITE_DESCRIPCION = 560   # maximo inclusivo (el responsable, 2026-09-10; antes < 490)
API = "https://api.trello.com/1"
GITHUB_ORG = os.environ.get("GITHUB_ORG", "<org>")

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")


class ErrorTrello(Exception):
    pass


# ------------------------------------------------------------------ conexion

def cargar_credenciales():
    ruta = os.path.expanduser("~/.trello-credentials.json")
    if not os.path.exists(ruta):
        raise ErrorTrello(f"No existe {ruta}. Debe tener apiKey, token y defaultBoardId.")
    # El archivo se guardo con BOM: sin utf-8-sig, json.load falla en la linea 1 columna 1
    with open(ruta, encoding="utf-8-sig") as f:
        cred = json.load(f)
    for clave in ("apiKey", "token", "defaultBoardId"):
        if not cred.get(clave):
            raise ErrorTrello(f"Falta '{clave}' en {ruta}.")
    return cred


CRED = None


def llamar(metodo, ruta, params=None, datos=None, cuerpo=None, tipo=None):
    global CRED
    CRED = CRED or cargar_credenciales()
    query = dict(params or {}, key=CRED["apiKey"], token=CRED["token"])
    url = f"{API}/{ruta}?{urllib.parse.urlencode(query)}"
    encabezados = {}
    if datos is not None:
        cuerpo = urllib.parse.urlencode(datos, doseq=True).encode("utf-8")
        encabezados["Content-Type"] = "application/x-www-form-urlencoded; charset=utf-8"
    if tipo:
        encabezados["Content-Type"] = tipo
    req = urllib.request.Request(url, data=cuerpo, method=metodo, headers=encabezados)
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            texto = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        detalle = e.read().decode("utf-8", "replace")[:300]
        raise ErrorTrello(f"Trello respondio {e.code} en {metodo} /{ruta}: {detalle}")
    except urllib.error.URLError as e:
        raise ErrorTrello(f"No se pudo conectar con Trello: {e.reason}")
    return json.loads(texto) if texto else None


# ------------------------------------------------------------------ tablero vivo

def normalizar(texto):
    sin_tildes = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sin_tildes).strip().lower()


class Tablero:
    def __init__(self):
        board = CRED_BOARD()
        self.id = board
        self.columnas = llamar("GET", f"boards/{board}/lists", {"filter": "open"})
        self.etiquetas = llamar("GET", f"boards/{board}/labels")
        self.miembros = llamar("GET", f"boards/{board}/members")

    def nombre_columna(self, id_):
        return next((c["name"] for c in self.columnas if c["id"] == id_), id_)

    def nombre_etiqueta(self, id_):
        return next((e["name"] or f"(sin nombre, {e['color']})" for e in self.etiquetas if e["id"] == id_), id_)

    def nombre_miembro(self, id_):
        return next((f"{m['fullName']} ({m['username']})" for m in self.miembros if m["id"] == id_), id_)

    def columna(self, nombre):
        return self._resolver("columna", nombre, self.columnas, lambda c: [c["name"]])

    def etiqueta(self, nombre):
        con_nombre = [e for e in self.etiquetas if e["name"]]
        return self._resolver("etiqueta", nombre, con_nombre, lambda e: [e["name"]])

    def miembro(self, nombre):
        # Regla del equipo: "Revisor Principal" a secas es Revisor Principal. otros integrantes solo por su username literal.
        if normalizar(nombre) in ("revisor principal", "revisor"):
            nombre = "<revisor-principal>"
        return self._resolver("miembro", nombre, self.miembros, lambda m: [m["username"], m["fullName"]])

    def _resolver(self, tipo, nombre, elementos, claves):
        buscado = normalizar(nombre)
        exactos = [e for e in elementos if any(normalizar(k) == buscado for k in claves(e))]
        if len(exactos) == 1:
            return exactos[0]
        parciales = [e for e in elementos if any(buscado in normalizar(k) for k in claves(e))]
        if len(parciales) == 1 and not exactos:
            return parciales[0]
        candidatos = exactos or parciales
        opciones = ", ".join(" / ".join(claves(e)) for e in (candidatos or elementos))
        if candidatos:
            raise ErrorTrello(f"'{nombre}' es ambiguo como {tipo}; coincide con: {opciones}. Usar el nombre exacto.")
        articulo = "el" if tipo == "miembro" else "la"
        raise ErrorTrello(f"No existe {articulo} {tipo} '{nombre}' en el tablero. Opciones: {opciones}.")


def CRED_BOARD():
    global CRED
    CRED = CRED or cargar_credenciales()
    return CRED["defaultBoardId"]


def id_de_tarjeta(valor):
    m = re.search(r"trello\.com/c/([A-Za-z0-9]+)", valor)
    return m.group(1) if m else valor.strip()


def leer_tarjeta(valor):
    return llamar("GET", f"cards/{id_de_tarjeta(valor)}", {"attachments": "true"})


def leer_archivo_texto(ruta):
    # Siempre desde archivo UTF-8: pasar tildes por argumento de consola en Windows las corrompe
    with open(ruta, encoding="utf-8-sig") as f:
        return f.read().strip()


def validar_descripcion(texto):
    if len(texto) > LIMITE_DESCRIPCION:
        raise ErrorTrello(
            f"La descripcion tiene {len(texto)} caracteres; el estandar permite {LIMITE_DESCRIPCION} como maximo. "
            "La tarjeta es un puntero: el detalle va al PR o a una guia.")


def fecha_iso(fecha, hora_utc):
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", fecha):
        raise ErrorTrello(f"Fecha '{fecha}' invalida; usar AAAA-MM-DD.")
    # Horas elegidas para que en Lima (UTC-5) la fecha visible sea la misma que se pidio
    return f"{fecha}T{hora_utc}.000Z"


def en_lima(iso):
    # Fecha visible en Lima (UTC-5): el vencimiento de las 19:00 cae en UTC al dia siguiente
    if not iso:
        return "-"
    instante = datetime.datetime.fromisoformat(iso.replace("Z", "+00:00"))
    return (instante - datetime.timedelta(hours=5)).date().isoformat()


def vencimiento_iso(fecha):
    # El vencimiento de una tarjeta es a las 19:00 de Lima (UTC-5) = 00:00 UTC del dia siguiente
    # (pedido del responsable, 2026-09-22; antes quedaba a las 18:00)
    fecha_iso(fecha, "00:00:00")
    siguiente = datetime.date.fromisoformat(fecha) + datetime.timedelta(days=1)
    return f"{siguiente.isoformat()}T00:00:00.000Z"


# ------------------------------------------------------------------ salida

def imprimir_propuesta(titulo, filas, aplicar):
    print(f"\nPropuesta para Trello: {titulo}")
    for campo, valor in filas:
        if valor in (None, "", []):
            continue
        if isinstance(valor, list):
            valor = ", ".join(valor)
        if "\n" in str(valor):
            print(f"- {campo}:")
            for linea in str(valor).splitlines():
                print(f"    {linea}")
        else:
            print(f"- {campo}: {valor}")
    if not aplicar:
        print("\nSIMULACION: no se envio nada. Mostrar esta propuesta al usuario y repetir con --aplicar tras su aprobacion.")


def verificar(tarjeta_id, esperado, tablero):
    real = leer_tarjeta(tarjeta_id)
    fallas = []
    for campo, valor in esperado.items():
        actual = real.get(campo)
        if campo in ("idLabels", "idMembers"):
            faltan = set(valor) - set(actual or [])
            if faltan:
                fallas.append(f"{campo}: faltan {sorted(faltan)}")
        elif campo in ("start", "due"):
            if not actual or actual[:10] != valor[:10]:
                fallas.append(f"{campo}: esperado {valor[:10]}, quedo {actual}")
        elif actual != valor:
            fallas.append(f"{campo}: no coincide")
    print(f"\nTarjeta: {real['shortUrl']}")
    print(f"Columna: {tablero.nombre_columna(real['idList'])} | "
          f"Etiquetas: {', '.join(tablero.nombre_etiqueta(i) for i in real['idLabels']) or '-'} | "
          f"Miembros: {', '.join(tablero.nombre_miembro(i) for i in real['idMembers']) or '-'} | "
          f"Inicio: {(real.get('start') or '-')[:10]} | Vence: {en_lima(real.get('due'))}")
    if fallas:
        print("VERIFICACION FALLIDA: " + "; ".join(fallas))
        return 1
    print("Verificado: la tarjeta releida coincide con lo pedido.")
    return 0


# ------------------------------------------------------------------ acciones

def accion_tablero(_args):
    t = Tablero()
    print("COLUMNAS")
    for c in t.columnas:
        print(f"  {c['name']}")
    print("ETIQUETAS")
    for e in t.etiquetas:
        print(f"  {e['name'] or '(sin nombre)'} [{e['color']}]")
    print("MIEMBROS")
    for m in t.miembros:
        print(f"  {m['username']} - {m['fullName']}")
    return 0


def palabras_clave(texto):
    ruido = {"de", "la", "el", "los", "las", "en", "y", "con", "sin", "al", "del", "un", "una", "para", "por", "que", "api-core", "web-app"}
    return {p for p in re.findall(r"[a-z0-9]{4,}", normalizar(texto)) if p not in ruido}


def buscar_parecidas(texto, tablero):
    buscadas = palabras_clave(texto)
    tarjetas = llamar("GET", f"boards/{tablero.id}/cards", {"filter": "open", "fields": "name,idList,shortUrl"})
    resultado = []
    for c in tarjetas:
        comunes = buscadas & palabras_clave(c["name"])
        if buscadas and len(comunes) >= max(2, len(buscadas) // 3):
            resultado.append((len(comunes), c))
    return [c for _, c in sorted(resultado, key=lambda x: -x[0])]


def accion_buscar(args):
    t = Tablero()
    parecidas = buscar_parecidas(args.texto, t)
    if not parecidas:
        print("Sin tarjetas abiertas parecidas.")
    for c in parecidas:
        print(f"  [{t.nombre_columna(c['idList'])}] {c['name']}  {c['shortUrl']}")
    return 0


def accion_listar(args):
    t = Tablero()
    columna = t.columna(args.columna)
    tarjetas = llamar("GET", f"lists/{columna['id']}/cards",
                      {"fields": "name,desc,idLabels,idMembers,shortUrl,dateLastActivity"})
    print(f"{columna['name']}: {len(tarjetas)} tarjeta(s)")
    for c in tarjetas:
        etiquetas = ", ".join(t.nombre_etiqueta(i) for i in c["idLabels"]) or "-"
        miembros = ", ".join(t.nombre_miembro(i).split(" (")[-1].rstrip(")") for i in c["idMembers"]) or "-"
        print(f"\n- {c['name']}\n  {c['shortUrl']} | {etiquetas} | {miembros} | "
              f"actividad {c['dateLastActivity'][:10]}")
        if args.desc and c["desc"].strip():
            for linea in c["desc"].strip().splitlines():
                print(f"    {linea}")
    return 0


def accion_ver(args):
    t = Tablero()
    c = leer_tarjeta(args.tarjeta)
    print(f"{c['name']}\n{c['shortUrl']}")
    print(f"Columna: {t.nombre_columna(c['idList'])}")
    print(f"Etiquetas: {', '.join(t.nombre_etiqueta(i) for i in c['idLabels']) or '-'}")
    print(f"Miembros: {', '.join(t.nombre_miembro(i) for i in c['idMembers']) or '-'}")
    print(f"Inicio: {(c.get('start') or '-')[:10]} | Vence: {en_lima(c.get('due'))}")
    print(f"Adjuntos: {', '.join(a['name'] for a in c.get('attachments') or []) or '-'}")
    print(f"Descripcion ({len(c['desc'])} caracteres):\n{c['desc']}")
    return 0


def accion_crear(args):
    t = Tablero()
    desc = leer_archivo_texto(args.desc_archivo) if args.desc_archivo else ""
    validar_enlaces_en_texto(desc)
    validar_descripcion(desc)
    columna = t.columna(args.columna)
    etiquetas = [t.etiqueta(n) for n in args.etiqueta]
    miembros = [t.miembro(n) for n in args.miembro]
    datos = {"idList": columna["id"], "name": args.titulo, "desc": desc,
             "idLabels": ",".join(e["id"] for e in etiquetas), "idMembers": ",".join(m["id"] for m in miembros)}
    if args.inicio:
        datos["start"] = fecha_iso(args.inicio, "12:00:00")
    if args.vence:
        datos["due"] = vencimiento_iso(args.vence)

    parecidas = buscar_parecidas(args.titulo, t)
    imprimir_propuesta("tarjeta nueva", [
        ("Titulo", args.titulo),
        ("Columna", columna["name"]),
        ("Etiquetas", [e["name"] for e in etiquetas] or "ninguna"),
        ("Miembros", [f"{m['fullName']} ({m['username']})" for m in miembros] or "ninguno"),
        ("Inicio", args.inicio), ("Vence", args.vence),
        ("Descripcion", f"({len(desc)} caracteres)\n{desc}" if desc else "vacia"),
        ("Tarjetas parecidas ya abiertas", [f"{c['name']} {c['shortUrl']}" for c in parecidas] or None),
    ], args.aplicar)
    if not args.aplicar:
        return 0
    if parecidas and not args.aunque_exista:
        raise ErrorTrello("Hay tarjetas parecidas abiertas. Confirmar con el usuario que no es un duplicado y repetir con --aunque-exista.")

    nueva = llamar("POST", "cards", datos=datos)
    esperado = {"name": args.titulo, "desc": desc, "idList": columna["id"],
                "idLabels": [e["id"] for e in etiquetas], "idMembers": [m["id"] for m in miembros]}
    for campo in ("start", "due"):
        if campo in datos:
            esperado[campo] = datos[campo]
    return verificar(nueva["id"], esperado, t)


def accion_actualizar(args):
    t = Tablero()
    tarjeta = leer_tarjeta(args.tarjeta)
    datos, esperado, filas = {}, {}, []

    if args.titulo:
        if not args.confirmo_renombrar:
            raise ErrorTrello(
                "Renombrar una tarjeta existente es una excepcion puntual (seccion 1 de la guia: "
                "'su titulo original se respeta al 100%'). Falta --confirmo-renombrar para dejar "
                "constancia de que el usuario lo aprobo explicitamente para esta tarjeta."
            )
        if args.titulo != tarjeta["name"]:
            datos["name"] = esperado["name"] = args.titulo
            filas.append(("Titulo", f"{tarjeta['name']} -> {args.titulo}"))

    if args.columna:
        columna = t.columna(args.columna)
        datos["idList"] = esperado["idList"] = columna["id"]
        filas.append(("Columna", f"{t.nombre_columna(tarjeta['idList'])} -> {columna['name']}"))
        # Una tarjeta entregada a revision lleva inicio y vence (seccion 2 de la guia)
        if columna["name"].lower().startswith("en revisi"):
            faltan = [n for n, ya, nuevo in (("--inicio", tarjeta.get("start"), args.inicio),
                                             ("--vence", tarjeta.get("due"), args.vence)) if not (ya or nuevo)]
            if faltan:
                raise ErrorTrello(
                    f"No se pasa a '{columna['name']}' sin fechas: a la tarjeta le falta {' y '.join(faltan)} "
                    "(seccion 2 de la guia). Repetir el comando agregandolos.")
            # Y como minimo con el responsable y Revisor Principal de miembros (el responsable, 21/10).
            pedidos = {t.miembro(n)["id"] for n in args.miembro}
            sin_miembro = [u for u in ("<responsable>", "<revisor-principal>")
                           if t.miembro(u)["id"] not in set(tarjeta["idMembers"]) | pedidos]
            if sin_miembro:
                raise ErrorTrello(
                    f"No se pasa a '{columna['name']}' sin miembros obligatorios: falta "
                    f"{', '.join(sin_miembro)}. Repetir el comando con --miembro '<responsable>' --miembro 'revisor principal'.")
    if args.desc_archivo:
        desc = leer_archivo_texto(args.desc_archivo)
        validar_enlaces_en_texto(desc)
        validar_descripcion(desc)
        datos["desc"] = esperado["desc"] = desc
        filas.append(("Descripcion nueva", f"({len(desc)} caracteres)\n{desc}"))
    if args.archivar and not tarjeta.get("closed"):
        # Archivar no elimina: la tarjeta sale del tablero y se restaura desde "Elementos archivados".
        datos["closed"] = "true"  # Trello no acepta el "True" de Python en el formulario
        esperado["closed"] = True
        filas.append(("Archivar", "si (sale del tablero; se puede restaurar, no se elimina)"))
    if args.desarchivar and tarjeta.get("closed"):
        datos["closed"] = "false"
        esperado["closed"] = False
        filas.append(("Desarchivar", "si (vuelve al tablero en su columna)"))
    if args.inicio:
        datos["start"] = esperado["start"] = fecha_iso(args.inicio, "12:00:00")
        filas.append(("Inicio", args.inicio))
    if args.vence:
        datos["due"] = esperado["due"] = vencimiento_iso(args.vence)
        filas.append(("Vence", args.vence))

    etiquetas = [e for e in (t.etiqueta(n) for n in args.etiqueta) if e["id"] not in tarjeta["idLabels"]]
    miembros = [m for m in (t.miembro(n) for n in args.miembro) if m["id"] not in tarjeta["idMembers"]]
    if etiquetas:
        filas.append(("Agregar etiquetas", [e["name"] for e in etiquetas]))
        esperado["idLabels"] = [e["id"] for e in etiquetas]
    if miembros:
        filas.append(("Agregar miembros", [f"{m['fullName']} ({m['username']})" for m in miembros]))
        esperado["idMembers"] = [m["id"] for m in miembros]

    if not datos and not etiquetas and not miembros:
        print("Nada que cambiar: lo pedido ya esta en la tarjeta.")
        return 0
    if not args.titulo:
        filas.insert(0, ("Tarjeta", f"{tarjeta['name']} {tarjeta['shortUrl']} (titulo intacto)"))
    imprimir_propuesta("actualizar tarjeta existente", filas, args.aplicar)
    if not args.aplicar:
        return 0

    if datos:
        llamar("PUT", f"cards/{tarjeta['id']}", datos=datos)
    for e in etiquetas:
        llamar("POST", f"cards/{tarjeta['id']}/idLabels", datos={"value": e["id"]})
    for m in miembros:
        llamar("POST", f"cards/{tarjeta['id']}/idMembers", datos={"value": m["id"]})
    return verificar(tarjeta["id"], esperado, t)


# En las tarjetas solo van enlaces de GitHub del org AcmeOrg: nunca de la cuenta personal ni de agentic-harness (el responsable, 2026-10-20).
REPOS_ACMEORG = {"api-core", "api-contracts", "api-people", "api-auth", "api-delivery", "api-accounting", "web-app"}


def validar_url_github(url):
    m = re.match(r"https?://(?:www\.)?github\.com/([^/]+)/([^/#?]+)", url.strip(), re.I)
    if not m:
        return
    duenio, repo = m.group(1), m.group(2)
    if duenio != GITHUB_ORG or repo not in REPOS_ACMEORG:
        raise ErrorTrello(f"Enlace de GitHub fuera del org {GITHUB_ORG} ({duenio}/{repo}): en las tarjetas solo van "
                          f"PRs y ramas de {GITHUB_ORG}/{{{', '.join(sorted(REPOS_ACMEORG))}}}.")


def validar_enlaces_en_texto(texto):
    for url in re.findall(r"https?://(?:www\.)?github\.com/[^\s)\]>]+", texto or "", re.I):
        validar_url_github(url)


def accion_adjuntar(args):
    t = Tablero()
    tarjeta = leer_tarjeta(args.tarjeta)
    if bool(args.url) == bool(args.archivo):
        raise ErrorTrello("Indicar exactamente uno: --url o --archivo.")
    if args.url:
        validar_url_github(args.url)
        nombre = args.nombre or args.url
        ya = [a for a in tarjeta.get("attachments") or [] if a.get("url") == args.url]
        if ya:
            print(f"La tarjeta ya tiene ese adjunto: {ya[0]['name']}")
            return 0
        imprimir_propuesta("adjuntar enlace", [("Tarjeta", f"{tarjeta['name']} {tarjeta['shortUrl']}"),
                                               ("URL", args.url), ("Nombre", nombre)], args.aplicar)
        if not args.aplicar:
            return 0
        llamar("POST", f"cards/{tarjeta['id']}/attachments", datos={"url": args.url, "name": nombre})
    else:
        ruta = os.path.abspath(args.archivo)
        if not os.path.isfile(ruta):
            raise ErrorTrello(f"No existe el archivo {ruta}.")
        nombre = args.nombre or os.path.basename(ruta)
        imprimir_propuesta("adjuntar archivo", [("Tarjeta", f"{tarjeta['name']} {tarjeta['shortUrl']}"),
                                                ("Archivo", ruta), ("Nombre", nombre),
                                                ("Tamano", f"{os.path.getsize(ruta)} bytes")], args.aplicar)
        if not args.aplicar:
            return 0
        limite = uuid.uuid4().hex
        tipo = mimetypes.guess_type(ruta)[0] or "application/octet-stream"
        with open(ruta, "rb") as f:
            contenido = f.read()
        cuerpo = (f"--{limite}\r\nContent-Disposition: form-data; name=\"name\"\r\n\r\n{nombre}\r\n"
                  f"--{limite}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{os.path.basename(ruta)}\"\r\n"
                  f"Content-Type: {tipo}\r\n\r\n").encode("utf-8") + contenido + f"\r\n--{limite}--\r\n".encode("utf-8")
        llamar("POST", f"cards/{tarjeta['id']}/attachments", cuerpo=cuerpo, tipo=f"multipart/form-data; boundary={limite}")

    real = leer_tarjeta(tarjeta["id"])
    if any(a["name"] == nombre for a in real.get("attachments") or []):
        print(f"Verificado: adjunto '{nombre}' presente en {real['shortUrl']}")
        return 0
    print("VERIFICACION FALLIDA: el adjunto no aparece al releer la tarjeta.")
    return 1


def accion_quitar_adjunto(args):
    # Quitar es borrar: solo por URL exacta, nunca por nombre parecido, y con el OK del responsable.
    tarjeta = leer_tarjeta(args.tarjeta)
    sobran = [a for a in tarjeta.get("attachments") or [] if a.get("url") == args.url]
    if not sobran:
        print(f"La tarjeta no tiene un adjunto con esa URL: {args.url}")
        return 0
    imprimir_propuesta("quitar adjunto", [("Tarjeta", f"{tarjeta['name']} {tarjeta['shortUrl']}"),
                                          ("URL", args.url), ("Adjuntos a quitar", str(len(sobran)))], args.aplicar)
    if not args.aplicar:
        return 0
    for a in sobran:
        llamar("DELETE", f"cards/{tarjeta['id']}/attachments/{a['id']}")
    real = leer_tarjeta(tarjeta["id"])
    if any(a.get("url") == args.url for a in real.get("attachments") or []):
        print("VERIFICACION FALLIDA: el adjunto sigue al releer la tarjeta.")
        return 1
    print(f"Verificado: adjunto '{args.url}' quitado de {real['shortUrl']}")
    return 0


def accion_comentar(args):
    tarjeta = leer_tarjeta(args.tarjeta)
    texto = leer_archivo_texto(args.texto_archivo)
    if re.search(r"github\.com/[^/\s]+/[^/\s]+/pull/\d+", texto):
        raise ErrorTrello("El estandar prohibe comentar enlaces de PR: el PR va como adjunto (accion adjuntar).")
    imprimir_propuesta("comentario", [("Tarjeta", f"{tarjeta['name']} {tarjeta['shortUrl']}"),
                                      ("Texto", texto)], args.aplicar)
    if not args.aplicar:
        return 0
    llamar("POST", f"cards/{tarjeta['id']}/actions/comments", datos={"text": texto})
    print(f"Comentario publicado en {tarjeta['shortUrl']}")
    return 0


def accion_ordenar(args):
    t = Tablero()
    columna = t.columna(args.columna)

    def leer_columna():
        tarjetas = llamar("GET", f"lists/{columna['id']}/cards", {"fields": "name,shortLink,shortUrl,pos"})
        return sorted(tarjetas, key=lambda c: c["pos"])

    actuales = leer_columna()
    por_link = {c["shortLink"]: c for c in actuales}
    orden = [id_de_tarjeta(l) for l in leer_archivo_texto(args.orden_archivo).splitlines() if l.strip()]

    # El archivo tiene que cubrir la columna entera: con un orden parcial, las tarjetas no listadas
    # quedarian intercaladas donde caiga su pos y el resultado no seria el pedido.
    repetidas = sorted({l for l in orden if orden.count(l) > 1})
    ajenas = [l for l in orden if l not in por_link]
    faltan = [c for c in actuales if c["shortLink"] not in orden]
    if repetidas or ajenas or faltan:
        partes = []
        if repetidas:
            partes.append(f"repetidas: {', '.join(repetidas)}")
        if ajenas:
            partes.append(f"no estan en {columna['name']}: {', '.join(ajenas)}")
        if faltan:
            partes.append("faltan en el archivo: " + "; ".join(f"{c['shortLink']} {c['name']}" for c in faltan))
        raise ErrorTrello("El orden tiene que listar cada tarjeta de la columna una sola vez. " + " | ".join(partes))

    if [c["shortLink"] for c in actuales] == orden:
        print(f"Nada que cambiar: {columna['name']} ya esta en ese orden.")
        return 0

    def numerada(links):
        return "\n".join(f"{i:>2}. {por_link[l]['name']} ({l})" for i, l in enumerate(links, 1))

    imprimir_propuesta(f"ordenar la columna {columna['name']}",
                       [("Orden actual", numerada([c["shortLink"] for c in actuales])),
                        ("Orden nuevo", numerada(orden))], args.aplicar)
    if not args.aplicar:
        return 0

    for i, link in enumerate(orden, 1):
        llamar("PUT", f"cards/{por_link[link]['id']}", datos={"pos": 65536 * i})

    # Se compara la secuencia, no el valor de pos: Trello puede renormalizarlo
    real = [c["shortLink"] for c in leer_columna()]
    if real != orden:
        print("VERIFICACION FALLIDA: al releer la columna el orden es:\n" + numerada([l for l in real if l in por_link]))
        return 1
    print(f"Verificado: {columna['name']} quedo en el orden pedido ({len(orden)} tarjetas).")
    return 0


def main():
    p = argparse.ArgumentParser(description="Tablero Trello del proyecto (skill /trello)")
    sub = p.add_subparsers(dest="accion", required=True)

    sub.add_parser("tablero", help="columnas, etiquetas y miembros del tablero vivo")
    b = sub.add_parser("buscar", help="tarjetas abiertas con titulo parecido")
    b.add_argument("texto")
    li = sub.add_parser("listar", help="tarjetas de una columna")
    li.add_argument("--columna", required=True)
    li.add_argument("--desc", action="store_true", help="incluir la descripcion")
    v = sub.add_parser("ver", help="detalle de una tarjeta")
    v.add_argument("tarjeta", help="shortLink, URL o id")

    c = sub.add_parser("crear", help="crear tarjeta (simulacion salvo --aplicar)")
    c.add_argument("--columna", required=True)
    c.add_argument("--titulo", required=True)
    c.add_argument("--desc-archivo", help="archivo UTF-8 con la descripcion")
    c.add_argument("--etiqueta", action="append", default=[])
    c.add_argument("--miembro", action="append", default=[])
    c.add_argument("--inicio", help="AAAA-MM-DD")
    c.add_argument("--vence", help="AAAA-MM-DD")
    c.add_argument("--aunque-exista", action="store_true", help="crear aunque haya tarjetas parecidas")
    c.add_argument("--aplicar", action="store_true")

    a = sub.add_parser("actualizar", help="mover, describir, fechar o sumar etiquetas/miembros; el titulo solo con --titulo y --confirmo-renombrar")
    a.add_argument("tarjeta")
    a.add_argument("--columna")
    a.add_argument("--titulo", help="renombra la tarjeta existente; requiere ademas --confirmo-renombrar (excepcion puntual, no de rutina: seccion 1 de la guia)")
    a.add_argument("--confirmo-renombrar", action="store_true", help="el responsable aprobo explicitamente renombrar esta tarjeta existente")
    a.add_argument("--desc-archivo")
    a.add_argument("--archivar", action="store_true", help="archiva la tarjeta (reversible; NO la elimina)")
    a.add_argument("--desarchivar", action="store_true", help="restaura una tarjeta archivada")
    a.add_argument("--etiqueta", action="append", default=[])
    a.add_argument("--miembro", action="append", default=[])
    a.add_argument("--inicio")
    a.add_argument("--vence")
    a.add_argument("--aplicar", action="store_true")

    j = sub.add_parser("adjuntar", help="adjuntar un enlace (PR) o un archivo")
    j.add_argument("tarjeta")
    j.add_argument("--url")
    j.add_argument("--archivo")
    j.add_argument("--nombre")
    j.add_argument("--aplicar", action="store_true")

    q = sub.add_parser("quitar-adjunto", help="quitar un adjunto por su URL exacta (es borrar: solo con OK del responsable)")
    q.add_argument("tarjeta")
    q.add_argument("--url", required=True)
    q.add_argument("--aplicar", action="store_true")

    k = sub.add_parser("comentar", help="comentar una tarjeta (nunca enlaces de PR)")
    k.add_argument("tarjeta")
    k.add_argument("--texto-archivo", required=True)
    k.add_argument("--aplicar", action="store_true")

    o = sub.add_parser("ordenar", help="reordenar una columna entera segun un archivo (un shortLink o URL por linea)")
    o.add_argument("--columna", required=True)
    o.add_argument("--orden-archivo", required=True)
    o.add_argument("--aplicar", action="store_true")

    args = p.parse_args()
    acciones = {"tablero": accion_tablero, "buscar": accion_buscar, "listar": accion_listar,
                "ver": accion_ver, "crear": accion_crear,
                "actualizar": accion_actualizar, "adjuntar": accion_adjuntar, "quitar-adjunto": accion_quitar_adjunto, "comentar": accion_comentar,
                "ordenar": accion_ordenar}
    try:
        return acciones[args.accion](args)
    except ErrorTrello as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
