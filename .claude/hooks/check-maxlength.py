"""PostToolUse(Edit|Write) - aviso, no bloqueo.
Regla 2 de mensajeria (CLAUDE.md): los identificadores de proveedores externos
(Message-ID de correo, ids de WAHA) nunca van con nvarchar(100/200/255); van con
450, el maximo indexable en SQL Server. Solo avisa: el agente decide.
Mensajes en ASCII puro: stderr en Windows es cp1252 y corrompe tildes/guiones."""
import sys, json, re, os

IDS = re.compile(r"(MessageId|Message_Id|ExternalId|IdExterno|WahaId|ProveedorId|"
                 r"MensajeExternoId|CorrelationId|IdMensajeProveedor)", re.I)
CORTO = re.compile(r"(HasMaxLength\(\s*(\d{1,3})\s*\)|maxLength:\s*(\d{1,3}))")

try:
    ruta = json.load(sys.stdin).get("tool_input", {}).get("file_path", "")
except Exception:
    sys.exit(0)

if not ruta:
    sys.exit(0)
if not (ruta.endswith("Configuration.cs") or ("Migrations" + os.sep) in ruta):
    sys.exit(0)
if not os.path.isfile(ruta):
    sys.stderr.write("check-maxlength: no pude leer el archivo, chequeo omitido\n")
    sys.exit(0)

try:
    lineas = open(ruta, encoding="utf-8", errors="replace").read().splitlines()
except Exception:
    sys.stderr.write("check-maxlength: error leyendo el archivo, chequeo omitido\n")
    sys.exit(0)

avisos = []
for i, linea in enumerate(lineas):
    m = CORTO.search(linea)
    if not m:
        continue
    largo = int(m.group(2) or m.group(3))
    if largo >= 450:
        continue
    ventana = "\n".join(lineas[max(0, i - 2): i + 3])
    if IDS.search(ventana):
        avisos.append("  linea %d: longitud %d en un identificador externo" % (i + 1, largo))

if avisos:
    sys.stderr.write("AVISO (CLAUDE.md, regla 2 de mensajeria) - identificador de proveedor\n"
                     "externo con longitud < 450. Trunca ids reales y puede colgar el poller\n"
                     "en bucle. Usa nvarchar(450).\n"
                     + os.path.basename(ruta) + ":\n" + "\n".join(avisos[:5]) + "\n")
    sys.exit(2)
