#!/usr/bin/env python3
"""
grafico.py — investiga datos recientes o extrae de texto suelto, vía DeepSeek

No dibuja nada: eso lo hace `ui-grafico` (web/src/app/ui/molecules/grafico.ts).
Esto resuelve la parte tediosa de convertir un tema o un párrafo con números
en el JSON exacto que `DatosGrafico` espera en web/src/app/data/blog.data.ts.

Dos modos:

    python tools/grafico.py --tema "abandono de proyectos de IA"       # investiga
    python tools/grafico.py --tema "..." --n 8 --tipo dona
    python tools/grafico.py <archivo.txt>                              # extrae de texto ya tenido
    echo "texto con datos..." | python tools/grafico.py -

El modo `--tema` es el agente de investigación: busca en la web (DuckDuckGo,
sin API key — HTML público, sin dependencias nuevas) resultados recientes,
y le pide a DeepSeek que extraiga cifras SOLO de esos fragmentos, nunca de su
conocimiento previo, citando la URL exacta en 'fuente'. El modo de archivo es
el anterior: extrae de un texto que tú ya pegaste.

Regla dura, la misma de todo el sistema (CONTRATO.md): dato que falta se
declara, no se inventa. Si no hay cifra explícita y reciente, o no se puede
atar a una URL, el script lo dice — no rellena con un número plausible ni con
una fuente genérica. La clave se lee de DEEPSEEK_API_KEY (env o .env de la
raíz), igual que deepseek.py.
"""
from __future__ import annotations

import argparse
import datetime
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from deepseek import MODELO_POR_DEFECTO, api_key, llamar, log  # noqa: E402

SISTEMA = """Eres un extractor de datos, no un redactor ni un analista.

Tu única tarea: leer el texto que te pasan y, SI y solo si contiene cifras
numéricas explícitas con su etiqueta, devolver un JSON con esta forma exacta:

{
  "tipo": "barras" | "dona" | "linea",
  "titulo": "<título corto y neutro del gráfico, describe qué mide>",
  "unidad": "<símbolo si aplica, ej. '%', 'M USD'; omite el campo si no aplica>",
  "puntos": [
    {"etiqueta": "<nombre de la categoría>", "valor": <número>, "nota": "<opcional, contexto breve>"}
  ],
  "fuente": "<de dónde sale el dato, tal como lo dice el texto: informe, año, organización>"
}

Reglas, sin excepción:
1. NUNCA inventes un número que no esté explícito en el texto. Ni lo redondees
   ni lo estimes ni lo interpoles. Si el texto dice "más de 40%", el valor es
   40, no un número que "parezca razonable".
2. NUNCA inventes una fuente. Si el texto no dice de dónde sale el dato,
   el campo "fuente" debe ser exactamente "[FALTA: fuente no citada en el texto]".
   No pongas el nombre de la empresa ni del sitio como fuente por defecto.
3. "tipo": "dona" si los puntos son partes de un total (reparto, proporción,
   participación); "linea" si son el mismo indicador medido en 2 o más
   momentos en el tiempo (evolución, tendencia); "barras" para comparar
   magnitudes independientes que no son ni una cosa ni la otra.
4. Si el texto NO contiene ninguna cifra numérica explícita, no inventes
   ninguna: responde exactamente {"error": "sin datos numéricos explícitos en el texto"}.
5. Responde ÚNICAMENTE el JSON. Sin markdown, sin explicación, sin ``` .
"""


def construir_usuario(texto: str, tipo_forzado: str | None) -> str:
    pieza_tipo = (
        f'\nEl tipo de gráfico ya está decidido: usa "tipo": "{tipo_forzado}".\n'
        if tipo_forzado
        else ""
    )
    return f"Texto de origen:\n\n{texto.strip()}\n{pieza_tipo}"


# --------------------------------------------------------------------------- #
# Modo --tema: el agente de investigación
# --------------------------------------------------------------------------- #

SISTEMA_INVESTIGACION = """Eres un extractor de datos que trabaja SOLO con los
resultados de búsqueda que te paso a continuación — nunca con tu conocimiento
previo, aunque te parezca más actualizado o más preciso que lo que ves aquí.

Te paso una lista numerada de resultados de búsqueda (título, fragmento y URL)
sobre un tema. Tu única tarea: encontrar, DENTRO de esos fragmentos, cifras
numéricas explícitas y recientes, y devolver un JSON con esta forma exacta:

{
  "tipo": "barras" | "dona" | "linea",
  "titulo": "<título corto y neutro del gráfico, describe qué mide>",
  "unidad": "<símbolo si aplica, ej. '%', 'M USD'; omite el campo si no aplica>",
  "puntos": [
    {"etiqueta": "<categoría>", "valor": <número>, "nota": "<opcional, contexto breve>"}
  ],
  "fuente": "<organización/informe, año, y la URL exacta del resultado usado>"
}

Reglas, sin excepción:
1. Usa ÚNICAMENTE números que aparezcan literalmente en los fragmentos que te
   paso. Nunca completes un número que el fragmento trae parcial o vago
   ("más de 40%" → el valor es 40, no un número mayor que "parezca" correcto).
2. "fuente" DEBE incluir la URL exacta del resultado usado, copiada tal cual
   aparece en la lista (no la resumas, no la inventes, no uses el dominio raíz
   si el resultado trae una URL más específica).
3. Si dos resultados dan cifras distintas para lo que parece la misma
   pregunta, no promedies ni elijas por intuición: usa el de fecha más clara
   y reciente, y explica la discrepancia en "nota". Si no puedes decidir con
   lo que tienes, aplica la regla 5.
4. "tipo": "dona" si los puntos son partes de un total; "linea" si son el
   mismo indicador en 2 o más momentos en el tiempo; "barras" para
   comparar magnitudes independientes que no son ni una cosa ni la otra.
5. Si NINGÚN resultado trae una cifra numérica explícita y reciente sobre el
   tema, no inventes ninguna: responde exactamente
   {"error": "sin datos numéricos explícitos y recientes en los resultados de búsqueda"}.
6. Responde ÚNICAMENTE el JSON. Sin markdown, sin explicación, sin ``` .
"""


def _limpiar_html(fragmento: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", fragmento)).strip()


def _resolver_url(href: str) -> str:
    """DuckDuckGo redirige los resultados vía /l/?uddg=<url codificada>."""
    m = re.search(r"uddg=([^&]+)", href)
    if m:
        return urllib.parse.unquote(m.group(1))
    return href if href.startswith("http") else f"https:{href}"


def buscar_web(consulta: str, n: int = 6) -> list[dict]:
    """Busca en DuckDuckGo (HTML público, sin API key, sin dependencias
    nuevas — mismo principio que el resto de tools/: stdlib primero).
    POST, no GET: DuckDuckGo responde el reto anti-bot ("bots use DuckDuckGo
    too") a peticiones GET sin sesión de navegador; POST replica el submit
    real del formulario de /html/ y lo evita.
    Best-effort: si DuckDuckGo cambia su marcado, esto puede devolver una
    lista vacía; el caller lo trata como 'sin resultados', nunca lo rellena.
    """
    cuerpo = urllib.parse.urlencode({"q": consulta}).encode()
    req = urllib.request.Request(
        "https://html.duckduckgo.com/html/",
        data=cuerpo,
        headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            pagina = r.read().decode("utf-8", "replace")
    except urllib.error.URLError as e:
        log(f"[error] no se pudo consultar la búsqueda: {e}")
        return []

    bloques = re.findall(
        r'<a rel="nofollow" class="result__a" href="([^"]+)"[^>]*>(.*?)</a>.*?'
        r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
        pagina,
        re.S,
    )
    resultados = []
    for href, titulo, snippet in bloques[:n]:
        resultados.append({
            "url": _resolver_url(href),
            "titulo": _limpiar_html(titulo),
            "snippet": _limpiar_html(snippet),
        })
    return resultados


def construir_usuario_investigacion(
    tema: str, resultados: list[dict], tipo_forzado: str | None,
) -> str:
    piezas = [f"Tema a investigar: {tema}\n"]
    for i, r in enumerate(resultados, 1):
        piezas.append(f"[{i}] {r['titulo']}\nURL: {r['url']}\n{r['snippet']}\n")
    if tipo_forzado:
        piezas.append(f'\nEl tipo de gráfico ya está decidido: usa "tipo": "{tipo_forzado}".\n')
    return "\n".join(piezas)


def limpiar_json(txt: str) -> str:
    t = txt.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()


def validar(datos: dict) -> list[str]:
    """Comprobaciones mecánicas, no de criterio — igual espíritu que verificar.py."""
    problemas = []
    if datos.get("tipo") not in ("barras", "dona", "linea"):
        problemas.append("'tipo' debe ser 'barras', 'dona' o 'linea'")
    if not datos.get("titulo"):
        problemas.append("falta 'titulo'")
    puntos = datos.get("puntos")
    if not isinstance(puntos, list) or not puntos:
        problemas.append("'puntos' vacío o ausente")
    else:
        for i, p in enumerate(puntos):
            if not isinstance(p.get("valor"), (int, float)):
                problemas.append(f"puntos[{i}].valor no es numérico")
            if not p.get("etiqueta"):
                problemas.append(f"puntos[{i}] sin etiqueta")
    fuente = datos.get("fuente", "")
    if not fuente:
        problemas.append("falta 'fuente'")
    elif fuente.startswith("[FALTA"):
        problemas.append(
            "el texto no citaba una fuente — revisa si de verdad quieres "
            "publicar este gráfico sin ella, o consigue la cita real"
        )
    return problemas


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("entrada", nargs="?", help="Ruta a un .txt con el texto/tabla, o '-' para leer de stdin")
    p.add_argument("--tema", help="Modo investigación: busca en la web datos recientes sobre este tema")
    p.add_argument("--n", type=int, default=6, help="Resultados de búsqueda a considerar (modo --tema). Por defecto 6")
    p.add_argument("--tipo", choices=["barras", "dona", "linea"], help="Fuerza el tipo de gráfico")
    p.add_argument("--modelo", default=MODELO_POR_DEFECTO)
    p.add_argument("--out", help="Si se pasa, escribe el JSON ahí además de imprimirlo")
    args = p.parse_args()

    if not args.tema and not args.entrada:
        sys.exit("Pasa --tema '<tema>' para investigar, o un archivo/'-' para extraer de texto ya tenido.")

    key = api_key()

    if args.tema:
        anio_actual = datetime.date.today().year
        consulta = f"{args.tema} {anio_actual - 1} {anio_actual} estadísticas"
        log(f"· buscando: {consulta}")
        resultados = buscar_web(consulta, args.n)
        if not resultados:
            log("[error] la búsqueda no devolvió resultados — no hay nada de qué extraer.")
            return 1
        for r in resultados:
            log(f"  · {r['titulo']} — {r['url']}")
        log("· consultando a DeepSeek con los resultados…")
        salida = llamar(
            SISTEMA_INVESTIGACION,
            construir_usuario_investigacion(args.tema, resultados, args.tipo),
            args.modelo, key, max_tokens=4000,
        )
    else:
        texto = sys.stdin.read() if args.entrada == "-" else Path(args.entrada).read_text(encoding="utf-8")
        if not texto.strip():
            sys.exit("Entrada vacía.")
        log("· consultando a DeepSeek…")
        salida = llamar(SISTEMA, construir_usuario(texto, args.tipo), args.modelo, key, max_tokens=4000)

    limpio = limpiar_json(salida)

    try:
        datos = json.loads(limpio)
    except json.JSONDecodeError as e:
        log(f"[error] la respuesta no fue JSON válido: {e}")
        log(limpio)
        return 1

    if "error" in datos:
        log(f"[grafico] {datos['error']}")
        return 1

    problemas = validar(datos)
    for pr in problemas:
        log(f"[atención] {pr}")

    resultado = json.dumps(datos, ensure_ascii=False, indent=2)
    print(resultado)

    if args.out:
        Path(args.out).write_text(resultado, encoding="utf-8")
        log(f"· escrito en {args.out}")

    return 1 if any("valor" in pr or "etiqueta" in pr or "titulo" in pr or "tipo" in pr for pr in problemas) else 0


if __name__ == "__main__":
    sys.exit(main())
