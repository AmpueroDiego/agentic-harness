"""Reglas compartidas para secretos en el índice de Git y archivos del disco.

revisar_json devuelve pares (ruta, valor); revisar_bytes devuelve líneas redactadas.
No se inspeccionan archivos de texto ajenos a appsettings y Office.
"""
import argparse
import html
import io
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import zipfile


SENSIBLES = re.compile(
    r"^(ConexionSql|ConexionRedis|CoreDb|DefaultConnection|SecretKey|Password|"
    r"AppPassword|ApiKey|WebhookSecret|ApiAuth|URL_API_[A-Z_]+)$", re.I)
# Entre comillas el valor puede tener espacios ("ab 123456789"): sin eso se truncaba y pasaba el umbral
VALOR = (r'''(?P<valor>"[^"\r\n]{1,200}"|'[^'\r\n]{1,200}'|“[^”\r\n]{1,200}”|‘[^’\r\n]{1,200}’|'''
         r'''[^\s"'“”‘’;,]+)''')
CLAVE_VALOR = re.compile(
    r'''(?P<clave>[\w.-]*(?:api[ _-]?key|x-api-key|secret|password|contraseña|contrasena|pwd|token)'''
    r'''[\w .-]*?)["'“”‘’]?[ \t]*[:=][ \t]*''' + VALOR, re.I)
CONEXION = re.compile(r"\b(?:Server|Data Source)\s*=", re.I)
PASSWORD_CONEXION = re.compile(
    r"\b(?P<clave>Password|Pwd)\s*=\s*"
    r'''(?P<valor>"[^"\r\n]*"|'[^'\r\n]*'|[^\s"';]+)''', re.I)
MAX_ENTRADAS_OFFICE = 5000
MAX_BYTES_OFFICE = 200 * 1024 * 1024
LIMITES_XML = re.compile(r"</(?:w:p|a:p|si|c|row)\s*>|<w:(?:br|tab)\b[^>]*/>", re.I)


def una_linea(texto):
    return json.dumps(str(texto), ensure_ascii=False)[1:-1]


def redactar(valor):
    # También ocultar parte de valores de 1 a 4 caracteres.
    prefijo = valor[:min(4, max(0, len(valor) - 1))]
    return f'{una_linea(prefijo)}...[REDACTADO, {len(valor)} chars]'


def hallazgo(nombre, regla, ruta="archivo", valor=""):
    return f'{una_linea(nombre)}: {regla} — {una_linea(ruta)} = "{redactar(valor)}"'


def sin_comentarios_json(texto):
    """Quita // y /* */ fuera de strings y las comas finales antes de } o ]."""
    salida, i, n, en_string = [], 0, len(texto), False
    while i < n:
        c = texto[i]
        if en_string:
            salida.append(c)
            if c == "\\" and i + 1 < n:
                salida.append(texto[i + 1])
                i += 1
            elif c == '"':
                en_string = False
        elif c == '"':
            en_string = True
            salida.append(c)
        elif texto.startswith("//", i):
            fin = texto.find("\n", i)
            i = n if fin < 0 else fin
            continue
        elif texto.startswith("/*", i):
            fin = texto.find("*/", i + 2)
            i = n if fin < 0 else fin + 2
            continue
        else:
            salida.append(c)
        i += 1
    return re.sub(r",(\s*[}\]])", r"\1", "".join(salida))


def revisar_json(texto):
    """Convención heredada: solo vacío y REPLACE_ME eximen claves JSON sensibles."""
    try:
        datos = json.loads(texto.lstrip("\ufeff"))
    except (ValueError, RecursionError):
        try:
            # .NET acepta comentarios y comas finales en appsettings: no pueden dejar pasar un secreto
            datos = json.loads(sin_comentarios_json(texto.lstrip("\ufeff")))
        except (ValueError, RecursionError):
            return []
    fallos = []
    pendientes = [(datos, "", "")]
    while pendientes:
        nodo, ruta, clave = pendientes.pop()
        # "AdminSettings:Password" en una sola clave es la misma clave de .NET que el objeto anidado
        if isinstance(nodo, str) and SENSIBLES.fullmatch(clave.rsplit(":", 1)[-1]):
            if nodo.strip().lower() not in {"", "replace_me"}:
                fallos.append((ruta, nodo))
        elif isinstance(nodo, dict):
            hijos = [(v, f"{ruta}.{k}" if ruta else k, k) for k, v in nodo.items()]
            pendientes.extend(reversed(hijos))
        elif isinstance(nodo, list):
            pendientes.extend(reversed([(v, f"{ruta}[{i}]", "") for i, v in enumerate(nodo)]))
    return fallos


def es_placeholder(valor):
    valor = valor.strip().strip("\"'“”‘’").strip().lower()
    return (
        valor in {"", "replace_me"}
        or re.fullmatch(r"(?:<.*>|\{.*\}|\$\{.*\}|%.*%)", valor) is not None
        or re.fullmatch(r"[*x.]+", valor) is not None
        or valor.startswith(("tu-", "tu_", "tu ", "your-", "your_", "your ", "ejemplo", "example", "changeme"))
    )


def texto_xml(datos):
    if datos.startswith((b"\xff\xfe", b"\xfe\xff")):
        texto = datos.decode("utf-16")
    else:
        declaracion = re.match(br'''\s*<\?xml[^>]*encoding=["']([^"']+)["']''', datos)
        encoding = declaracion.group(1).decode("ascii") if declaracion else "utf-8-sig"
        texto = datos.decode(encoding)
    texto = LIMITES_XML.sub("\n", texto)
    # No introducir espacios entre runs: Word puede partir claves y valores.
    texto = re.sub(r"<[^>]*>", "", texto)
    return html.unescape(texto)


def es_palabra(valor):
    # Opción A (el responsable del repo, 2026-09-17). Se exime solo lo que en la guía de WAHA limpia daba falsos
    # positivos: nombres de placeholder en MAYÚSCULAS ("DASHBOARD_PASS") y una palabra suelta corta
    # ("adelante", "SecretKey"). Frases entre comillas y palabras largas siguen bloqueando aunque
    # sean solo letras ("correct horse battery staple", "abcdefghijklmnop").
    # No aplica a cadenas de conexión.
    if re.fullmatch(r"[A-Z_]+", valor):
        return True
    minus = "a-záéíóúüñ"
    palabra = rf"[A-ZÁÉÍÓÚÑ]?[{minus}]+(?:[A-ZÁÉÍÓÚÑ][{minus}]{{2,}})*"
    return len(valor) <= 12 and re.fullmatch(palabra, valor) is not None


def revisar_texto(texto):
    encontrados = []
    vistos = set()
    patrones = [(CLAVE_VALOR, 8, "clave sensible en Office")]
    if CONEXION.search(texto):
        patrones.append((PASSWORD_CONEXION, 1, "cadena de conexión en Office"))
    for patron, minimo, regla in patrones:
        for match in patron.finditer(texto):
            valor = match.group("valor").strip("\"'“”‘’")
            posicion = match.span("valor")
            if patron is CLAVE_VALOR and es_palabra(valor):
                continue
            if len(valor) >= minimo and not es_placeholder(valor) and posicion not in vistos:
                vistos.add(posicion)
                encontrados.append((regla, match.group("clave"), valor))
    return encontrados


def es_candidato(nombre):
    base = str(nombre).replace("\\", "/").rsplit("/", 1)[-1].lower()
    return (base.startswith(".env") or (base.startswith("appsettings") and base.endswith(".json"))
            or Path(base).suffix in {".docx", ".xlsx", ".pptx"})


def revisar_bytes(nombre, datos):
    """Revisa bytes sin mostrar secretos ni detalles de excepciones."""
    nombre = str(nombre)
    base = nombre.replace("\\", "/").rsplit("/", 1)[-1].lower()
    # .env y .env.<lo que sea> (incluido .env.prod.local), salvo plantillas terminadas en .example:
    # api-core versiona .env.waha.example con placeholders y la regla previa de git-guard la dejaba pasar.
    if (base in {"appsettings.development.json", "appsettings.local.json", ".env"}
            or (base.startswith(".env.") and not base.endswith(".example"))):
        return [hallazgo(nombre, "archivo prohibido")]
    try:
        if base.startswith("appsettings") and base.endswith(".json"):
            try:
                # .NET lee appsettings en UTF-16 con BOM: no puede quedar como "limpio" por encoding
                utf16 = datos.startswith((b"\xff\xfe", b"\xfe\xff"))
                texto = datos.decode("utf-16" if utf16 else "utf-8-sig")
            except UnicodeDecodeError:
                return []  # Igual que JSON inválido: no corresponde a esta regla.
            return [hallazgo(nombre, "clave sensible en appsettings", ruta, valor)
                    for ruta, valor in revisar_json(texto)]
        if Path(base).suffix in {".docx", ".xlsx", ".pptx"}:
            fallos = []
            try:
                with zipfile.ZipFile(io.BytesIO(datos)) as documento:
                    entradas = documento.infolist()
                    # Límites contra zip bombs: un documento que no se puede revisar entero bloquea
                    if (len(entradas) > MAX_ENTRADAS_OFFICE
                            or sum(e.file_size for e in entradas) > MAX_BYTES_OFFICE):
                        return [hallazgo(nombre, "documento Office demasiado grande para revisar")]
                    for entrada in entradas:
                        if entrada.filename.lower().endswith(".xml"):
                            texto = texto_xml(documento.read(entrada))
                            for regla, clave, valor in revisar_texto(texto):
                                fallos.append(hallazgo(nombre, regla, f"{entrada.filename}/{clave}", valor))
            except Exception:
                return [hallazgo(nombre, "documento Office ilegible")]
            return fallos
        return []
    except Exception:
        return [hallazgo(nombre, "no se pudo revisar el archivo")]


def git(repo, *argumentos):
    return subprocess.run(["git", "-C", str(repo), *argumentos],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)


def revisar_repo(repo):
    try:
        if git(repo, "rev-parse", "--git-dir").returncode:
            return []
        # --raw para conocer el modo: un gitlink de submódulo (160000) no es un blob de este repo
        staged = git(repo, "diff", "--cached", "--raw", "--no-renames", "--diff-filter=ACMR", "-z")
        if staged.returncode:
            return [hallazgo(repo, "no se pudo leer el stage")]
        fallos = []
        partes = staged.stdout.split(b"\0")
        for meta, ruta in zip(partes[0::2], partes[1::2]):
            if not ruta:
                continue
            if meta.split(b" ")[1:2] == [b"160000"]:
                continue
            nombre = os.fsdecode(ruta)
            if not es_candidato(nombre):
                continue  # No leer blobs que ninguna regla revisa
            try:
                contenido = git(repo, "show", ":" + nombre)
                if contenido.returncode:
                    fallos.append(hallazgo(nombre, "no se pudo leer el archivo staged"))
                else:
                    fallos.extend(revisar_bytes(nombre, contenido.stdout))
            except Exception:
                fallos.append(hallazgo(nombre, "no se pudo leer el archivo staged"))
        return fallos
    except Exception:
        return [hallazgo(repo, "no se pudo revisar el stage")]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    origen = parser.add_mutually_exclusive_group(required=True)
    origen.add_argument("--repo")
    origen.add_argument("--archivos", nargs="+")
    args = parser.parse_args()
    if args.repo is not None:
        fallos = revisar_repo(args.repo)
    else:
        fallos = []
        for nombre in args.archivos:
            try:
                fallos.extend(revisar_bytes(nombre, Path(nombre).read_bytes()))
            except Exception:
                fallos.append(hallazgo(nombre, "no se pudo leer el archivo"))
    for fallo in fallos[:20]:
        print(fallo)
    return 1 if fallos else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="backslashreplace")
    sys.exit(main())
