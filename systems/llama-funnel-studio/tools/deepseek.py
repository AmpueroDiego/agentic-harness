#!/usr/bin/env python3
"""
deepseek.py — ejecuta los encargos de los especialistas contra la API de DeepSeek

`run.py` imprime los 11 encargos; esto los ejecuta. Misma mitad determinista,
pero en vez de dejar el trabajo a un agente lo manda a un modelo barato y
escribe las salidas en disco.

Uso:
    python tools/deepseek.py extraer <slug>
    python tools/deepseek.py extraer <slug> --solo frontend,disenador
    python tools/deepseek.py extraer <slug> --excepto frontend
    python tools/deepseek.py extraer <slug> --modelo deepseek-v4-flash --workers 4
    python tools/deepseek.py extraer <slug> --dry-run      # imprime el prompt y sale

    python tools/deepseek.py reproducir <slug> <producto>          # las tres olas
    python tools/deepseek.py reproducir <slug> <producto> --ola 2  # una suelta

Un mismo origen sirve a varios productos: el activo generalizado se comparte y
cada producto vive en `casos/<slug>/reproduccion/<producto>/`.

La clave se lee de la variable DEEPSEEK_API_KEY o del archivo .env de la raíz.

Por qué material curado y no raw/ entero: elements.json son 156K y page.html 108K.
Ninguna ventana de contexto asumible los admite junto al resto. Lo que se manda
son los cinco JSON de raw/analysis/ (hechos ya medidos), el texto plano de la
página y un bloque de hechos del DOM contados aquí. Unos 15-20K tokens.
"""
from __future__ import annotations

import argparse
import collections
import html
import json
import os
import re
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# La salida lleva flechas y acentos; la consola de Windows es cp1252 por defecto.
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

RAIZ = Path(__file__).resolve().parent.parent
API_URL = "https://api.deepseek.com/chat/completions"
# La API rechaza cualquier nombre fuera de esta lista, así que el error llega
# como HTTP 400 y no como un modelo distinto al esperado.
MODELO_POR_DEFECTO = "deepseek-v4-pro"

ESPECIALISTAS = [
    "frontend", "disenador", "neuromarketing", "psicologo", "linguista",
    "copywriter", "mercadologo", "sociologo", "ingeniero-industrial",
    "administrador", "growth-data",
]

# Avisos que solo aplican a quien depende de lo que hay detrás del formulario.
AVISOS = {
    "ingeniero-industrial":
        "El opt-in NO se envió: hacerlo mete datos en un sistema ajeno y requiere "
        "permiso explícito. `captura.json` registra `pasos: []`. Solo puedes medir "
        "el proceso hasta la primera puerta; lo que haya después del formulario es "
        "desconocido y se declara como tal.",
    "administrador":
        "El opt-in NO se envió. Si el precio real vive detrás del formulario, no lo "
        "tienes: decláralo desconocido en vez de inferirlo. Ese hueco es en sí un "
        "hallazgo sobre el modelo de negocio.",
    "growth-data":
        "El opt-in NO se envió, así que los píxeles de conversión que disparan tras "
        "el formulario no están en network.json. Solo ves lo que carga en la vista inicial.",
}

_print_lock = threading.Lock()


def log(msg: str) -> None:
    with _print_lock:
        print(msg, flush=True)


# --------------------------------------------------------------------------- #
# Clave
# --------------------------------------------------------------------------- #

def cargar_env() -> None:
    """Mete el .env de la raíz en os.environ sin pisar lo ya definido."""
    f = RAIZ / ".env"
    if not f.exists():
        return
    for linea in f.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        k, v = linea.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def api_key() -> str:
    cargar_env()
    k = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if not k:
        sys.exit("Falta DEEPSEEK_API_KEY (variable de entorno o .env en la raíz).")
    return k


# --------------------------------------------------------------------------- #
# Material curado
# --------------------------------------------------------------------------- #

def texto_de_pagina(page_html: str) -> str:
    """HTML → texto legible, en el orden en que se lee la página."""
    s = re.sub(r"<script.*?</script>", "", page_html, flags=re.S | re.I)
    s = re.sub(r"<style.*?</style>", "", s, flags=re.S | re.I)
    s = re.sub(r"<svg.*?</svg>", "", s, flags=re.S | re.I)
    s = re.sub(r"<(h1|h2|h3|h4|li|p|div|section|button|a)\b[^>]*>", r"\n<\1>", s, flags=re.I)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))

    lineas: list[str] = []
    for bruta in s.split("\n"):
        linea = " ".join(bruta.split())
        if linea and (not lineas or lineas[-1] != linea):
            lineas.append(linea)
    return "\n".join(lineas)


def hechos_del_dom(page_html: str, styles: str) -> dict:
    """Lo que un parser puede contar y un modelo no debe estimar."""
    def n(pat: str) -> int:
        return len(re.findall(pat, page_html, flags=re.I))

    def top(pat: str, k: int = 12, flags=0) -> list:
        c = collections.Counter(re.findall(pat, page_html, flags))
        return [{"valor": v, "n": x} for v, x in c.most_common(k)]

    gen = re.search(r'name="generator" content="([^"]*)"', page_html)

    # Conteos crudos que nadie interpreta si no se los nombra.
    cableado = {
        p: n(re.escape(p)) for p in
        ("onclick", "addEventListener", "checkout", "hotmart", "stripe", "gumroad",
         "mercadopago", "wa.me", "location.href", "window.open", "fbq(")
    }
    n_a, n_button, n_form = n(r"<a\b"), n(r"<button\b"), n(r"<form\b")
    # `addEventListener` se excluye: los runtimes de los constructores traen los suyos
    # y darían un falso negativo.
    hay_destino = bool(
        n_a or n_form
        or any(v for k, v in cableado.items() if k not in ("addEventListener", "fbq("))
    )

    return {
        "diagnostico_de_cableado": {
            "hay_algun_destino_en_el_dom": hay_destino,
            "n_enlaces": n_a,
            "n_botones": n_button,
            "n_formularios": n_form,
            "ADVERTENCIA": (
                None if hay_destino else
                f"La página tiene {n_button} <button> y CERO enlaces, formularios, "
                "handlers de click propios o URL de pasarela de pago. En el DOM servido "
                "NINGUNA llamada a la acción lleva a ninguna parte. No interpretes esto "
                "como un funnel de un solo paso ni como fricción eliminada a propósito: "
                "el hecho observable es que no hay destino. Puede que se cablee en "
                "runtime por código que la captura no ejecutó, o que se publicara sin "
                "conectar; el raw no permite distinguirlo. Decláralo como desconocido."
            ),
        },
        "conteo_de_etiquetas": {
            t: n(rf"<{t}\b") for t in
            ("a", "button", "form", "input", "video", "img", "section", "h1", "h2", "h3")
        },
        "estilado": {
            "atributos_style_inline": n(r'style="'),
            "atributos_class": n(r'class="'),
            "nota": "Muchos style inline y casi ningún class = bloque HTML pegado a mano, "
                    "no componentes del constructor.",
        },
        "media_queries": sorted(set(m.strip() for m in re.findall(r"@media[^{]*", styles))),
        "generator": gen.group(1) if gen else None,
        "destinos_de_enlace": top(r'href="([^"]*)"', 20),
        "colores_hex": [
            {"valor": v, "n": x} for v, x in
            collections.Counter(c.upper() for c in re.findall(r"#[0-9a-fA-F]{6}\b", page_html)).most_common(15)
        ],
        "rgba": top(r"rgba\([^)]*\)", 12),
        "gradientes": top(r"linear-gradient\([^)]*\)", 8),
        "radios": top(r"border-radius:([^;\"]+)", 10),
        "line_height": top(r"line-height:([\d.]+)", 8),
        "letter_spacing": top(r"letter-spacing:(-?[\d.]+em)", 8),
        "senales_de_cableado": cableado,
        "atributos_de_idioma": re.findall(r"<html[^>]*>", page_html)[:1],
    }


def material(slug: str) -> str:
    raw = RAIZ / "casos" / slug / "raw"
    if not raw.exists():
        sys.exit(f"No existe {raw}. Corre antes: python tools/run.py extraer <url>")

    page = (raw / "page.html").read_text(encoding="utf-8", errors="replace")
    styles_f = raw / "styles.css"
    styles = styles_f.read_text(encoding="utf-8", errors="replace") if styles_f.exists() else ""

    partes = ["## Hechos medidos — raw/analysis/\n"]
    for nombre in ("design", "attention", "text", "flow", "trackers"):
        f = raw / "analysis" / f"{nombre}.json"
        if f.exists():
            partes.append(f"### {nombre}.json\n```json\n{f.read_text(encoding='utf-8')}\n```\n")

    cap = raw / "captura.json"
    if cap.exists():
        partes.append(f"### captura.json\n```json\n{cap.read_text(encoding='utf-8')}\n```\n")

    partes.append(
        "## Hechos del DOM — contados sobre page.html y styles.css\n```json\n"
        + json.dumps(hechos_del_dom(page, styles), ensure_ascii=False, indent=1)
        + "\n```\n"
    )
    partes.append(
        "## Texto de la página, en orden de lectura\n"
        "Es el contenido íntegro. Cítalo como evidencia, pero recuerda que en "
        "Patrones transferibles va la fórmula y jamás la frase.\n\n```\n"
        + texto_de_pagina(page)
        + "\n```\n"
    )
    return "\n".join(partes)


OLAS = [
    (1, ["mercadologo", "administrador"],
     "Fijan avatar, consciencia, sofisticación y precio. Todo depende de esto."),
    (2, ["psicologo", "sociologo", "ingeniero-industrial", "disenador",
         "linguista", "frontend", "growth-data", "neuromarketing"],
     "En paralelo, con la ola 1 ya cerrada."),
    (3, ["copywriter"],
     "Escribe con el manual de voz, las resistencias y la oferta ya decididos."),
]


# --------------------------------------------------------------------------- #
# Prompt
# --------------------------------------------------------------------------- #

def tool_de(esp: str) -> str | None:
    """El JSON que el especialista declara en su frontmatter."""
    f = RAIZ / "especialistas" / esp / "extraer.md"
    for linea in f.read_text(encoding="utf-8").splitlines()[:8]:
        if linea.startswith("tools:"):
            v = linea.split(":", 1)[1].strip()
            return None if v.startswith("ninguna") else v.split("→")[-1].strip()
    return None


def _leer(f: Path, titulo: str) -> str:
    return f"# {titulo}\n\n{f.read_text(encoding='utf-8')}\n\n---\n" if f.exists() else ""


def carpeta_producto(slug: str, producto: str) -> Path:
    """Dónde vive una reproducción concreta.

    Un mismo origen sirve a varios productos: el activo generalizado —SKILL.md,
    sintesis.md, extraccion/— se comparte, y cada producto tiene su subcarpeta
    con su ficha y su plan. Sin esta separación, la segunda reproducción del
    mismo funnel pisaba a la primera.
    """
    return RAIZ / "casos" / slug / "reproduccion" / producto


def productos_de(slug: str) -> list[str]:
    base = RAIZ / "casos" / slug / "reproduccion"
    return sorted(d.name for d in base.iterdir() if d.is_dir()) if base.exists() else []


def material_revisar(slug: str, producto: str) -> str:
    """Lo mínimo para revisar un build: el archivo y el plan. Nada más.

    `programador` es barato a propósito, para poder relanzarlo tras cada
    corrección. Añadirle la ficha, la síntesis o las once directivas sueltas
    multiplicaría el prompt sin aportar: el plan ya las consolidó.
    """
    dest = carpeta_producto(slug, producto)
    build = dest / "build.html"
    if not build.exists():
        sys.exit(f"Falta {build}. El paso 5 construye antes de revisar.")
    return (_leer(dest / "plan.md", "El plan — lo que se decidió")
            + f"# El build — lo que se construyó\n\n```html\n"
            + build.read_text(encoding="utf-8") + "\n```\n")


def material_reproducir(slug: str, producto: str) -> str:
    """Lo compartido por los once en modo reproducir.

    Va primero en el prompt, igual que en extraer, para que sea prefijo común
    y la caché de contexto lo cubra en las once llamadas.
    """
    caso = RAIZ / "casos" / slug
    dest = carpeta_producto(slug, producto)
    ficha = dest / "ficha-producto.md"
    if not ficha.exists():
        otros = productos_de(slug)
        sys.exit(f"Falta {ficha}.\nEl paso 1 de orquestador/reproducir.md es la ficha."
                 + (f"\nProductos con carpeta: {', '.join(otros)}" if otros else ""))

    partes = [_leer(ficha, "Ficha del producto destino")]
    comp = dest / "compatibilidad.md"
    if not comp.exists():
        log(f"  aviso: falta {comp.name} — el paso 2 no se salta\n")
    partes.append(_leer(comp, "Auditoría de compatibilidad"))
    partes.append(_leer(caso / "sintesis.md", "Síntesis del funnel de origen"))
    return "\n".join(p for p in partes if p)


def contexto_de_olas(slug: str, esp: str, producto: str) -> str:
    """Las salidas de las olas anteriores a la del especialista.

    Es lo que hace que reproducir no sea paralelo: quien va en la ola 2 tiene
    que decidir con el avatar y el precio ya fijados, no a la vez.
    """
    mi_ola = next((n for n, esps, _ in OLAS if esp in esps), 1)
    if mi_ola == 1:
        return ""

    base = carpeta_producto(slug, producto)
    trozos = []
    for n, esps, _ in OLAS:
        if n >= mi_ola:
            break
        for e in esps:
            f = base / f"{e}.md"
            if not f.exists():
                continue
            doc = f.read_text(encoding="utf-8")
            # Solo lo que condiciona: qué se decidió y qué se ordena. Descartes,
            # Faltantes y Conflictos son para el orquestador, no para quien
            # construye encima. Pasar el documento entero multiplicaba por tres
            # el prompt de la ola 3 y lo dejaba sin sitio para responder.
            partes = [m.group(0).strip() for m in
                      re.finditer(r"^##\s*(?:Decisiones|Directivas)\b.*?(?=\n##\s|\Z)",
                                  doc, re.S | re.M)]
            if partes:
                trozos.append(f"## Ola {n} — {e}\n\n" + "\n\n".join(partes))
    if not trozos:
        return ""
    return ("# Decisiones ya cerradas en olas anteriores\n\n"
            "**No se renegocian.** Si tu criterio choca con alguna, no la cambies: "
            "decláralo en tu sección Conflictos y que lo resuelva el orquestador.\n\n"
            + "\n\n".join(trozos) + "\n\n---\n")


def construir_prompt_reproducir(esp: str, slug: str, mat: str,
                                producto: str) -> tuple[str, str]:
    contrato = (RAIZ / "CONTRATO.md").read_text(encoding="utf-8")
    identidad = (RAIZ / "especialistas" / esp / "extraer.md").read_text(encoding="utf-8")
    protocolo_f = RAIZ / "especialistas" / esp / "reproducir.md"
    if not protocolo_f.exists():
        sys.exit(f"Falta {protocolo_f}")
    protocolo = protocolo_f.read_text(encoding="utf-8")
    extraccion = _leer(RAIZ / "casos" / slug / "extraccion" / f"{esp}.md",
                       f"Tu propia extracción del origen — {esp}")

    sistema = (
        f"Eres el especialista `{esp}` de un sistema de reproducción de funnels. "
        "Modo REPRODUCIR. No analizas el original: decides qué se hace en el "
        "producto nuevo, y tus directivas las ejecuta quien construye.\n\n"
        "Reglas innegociables:\n"
        "1. **Un dato que falta se declara, no se inventa.** Escribe `[FALTA: …]` "
        "por cada cosa que necesites y la ficha no tenga. Es la regla más "
        "importante del sistema: rellenar un hueco con algo plausible acaba en "
        "una página que promete lo que el producto no hace.\n"
        "2. **Declarar conflictos, no resolverlos.** Si tu criterio choca con otro "
        "especialista, escríbelo en Conflictos y sigue. No negocias: escalas.\n"
        "3. **Nada literal del original.** Ni frases, ni cifras, ni nombres.\n"
        "4. **Directiva ejecutable.** 'Mejorar la jerarquía' no vale. "
        "'H1 a 56px, H2 a 32px, sin pesos intermedios' sí.\n\n"
        "Respondes con el documento markdown y nada más. El contrato describe "
        "cada sección antes de que la escribas: esas descripciones son "
        "instrucciones para ti, no contenido, y no se copian."
    )

    usuario = f"""# CONTRATO.md

{contrato}

---

{mat}
{contexto_de_olas(slug, esp, producto)}
# Quién eres — especialistas/{esp}/extraer.md

{identidad}

---

# Tu protocolo de reproducción — especialistas/{esp}/reproducir.md

{protocolo}

---

{extraccion}
# Encargo

Ejecuta tu PROTOCOLO REPRODUCIR y devuelve el documento completo de
`casos/{slug}/reproduccion/{producto}/{esp}.md`, con exactamente estas cinco secciones:

1. Decisiones
2. Directivas — `D-{esp}-<n>`
3. Descartes
4. Faltantes — un `[FALTA: …]` por dato que necesites y no tengas
5. Conflictos

Pasa tu autoverificación antes de dar la salida por buena.
Empieza directamente por `# {esp.capitalize()} — directivas de reproducción`."""

    return sistema, usuario


def construir_prompt(esp: str, slug: str, mat: str) -> tuple[str, str]:
    contrato = (RAIZ / "CONTRATO.md").read_text(encoding="utf-8")
    protocolo = (RAIZ / "especialistas" / esp / "extraer.md").read_text(encoding="utf-8")
    tool = tool_de(esp)

    sistema = (
        f"Eres el especialista `{esp}` de un sistema de extracción de funnels. "
        "Modo EXTRAER. Trabajas dentro de un contrato que otros diez especialistas "
        "cumplen a la vez: si te sales del formato, tu salida no encaja con las suyas.\n\n"
        "Reglas innegociables:\n"
        "1. Observar, no suponer. Sin evidencia en el material no hay hallazgo.\n"
        "2. No invadir otra disciplina. Lo que cae fuera de tu Frontera se remite "
        "por nombre al especialista que le toca.\n"
        "3. Sin promesas de resultado. Nunca 'esto sube la conversión un X%'.\n"
        "4. Patrón, no copia. En Patrones transferibles va la fórmula, jamás la "
        "frase literal del original.\n"
        "5. Un dato que falta se declara, no se inventa.\n\n"
        "Respondes con el documento markdown y nada más: sin preámbulo, sin "
        "explicar lo que vas a hacer, sin cerrar con un resumen.\n\n"
        "El contrato describe cada sección antes de que la escribas. Esas "
        "descripciones son instrucciones para ti, no contenido: no las copies "
        "bajo tus encabezados. Debajo de cada título va directamente tu análisis."
    )

    aviso = AVISOS.get(esp, "")
    # Orden deliberado: primero lo idéntico en las 11 llamadas (contrato y
    # material), después lo único de cada especialista. Así el bloque grande
    # queda como prefijo común y la caché de contexto del proveedor lo cubre;
    # con el protocolo en medio, cada llamada rompía el prefijo y se pagaba
    # entero once veces.
    usuario = f"""# CONTRATO.md

{contrato}

---

# Material del caso `{slug}`

{mat}

---

# Tu protocolo — especialistas/{esp}/extraer.md

{protocolo}

{"**AVISO SOBRE LOS LÍMITES DE ESTA CAPTURA:** " + aviso + chr(10) * 2 if aviso else ""}\
{"Tu tool declarada es `" + tool + "`: son hechos ya medidos, tu trabajo empieza donde acaba el parser." + chr(10) * 2 if tool else ""}
---

# Encargo

Ejecuta tu PROTOCOLO EXTRAER sobre el material de arriba y devuelve el documento
completo de `casos/{slug}/extraccion/{esp}.md`, con exactamente las cinco secciones
del contrato y estos prefijos:

1. Hallazgos
2. Patrones transferibles — `PT-{esp}-<n>`
3. Contaminación — `CT-{esp}-<n>`
4. Preguntas al producto destino — `Q-{esp}-<n>`
5. Veredicto

Empieza directamente por `# {esp.capitalize()} — {slug}`."""

    return sistema, usuario


# --------------------------------------------------------------------------- #
# API
# --------------------------------------------------------------------------- #

def llamar(sistema: str, usuario: str, modelo: str, key: str,
           max_tokens: int, reintentos: int = 4) -> str:
    cuerpo = json.dumps({
        "model": modelo,
        "messages": [
            {"role": "system", "content": sistema},
            {"role": "user", "content": usuario},
        ],
        "max_tokens": max_tokens,
        "temperature": 0.3,
        "stream": False,
    }).encode("utf-8")

    ultimo = ""
    for intento in range(1, reintentos + 1):
        req = urllib.request.Request(
            API_URL,
            data=cuerpo,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=900) as r:
                d = json.loads(r.read().decode("utf-8"))
            return d["choices"][0]["message"]["content"]
        except urllib.error.HTTPError as e:
            detalle = e.read().decode("utf-8", "replace")[:300]
            ultimo = f"HTTP {e.code}: {detalle}"
            # 4xx que no sea 429 no se arregla reintentando
            if e.code != 429 and 400 <= e.code < 500:
                raise RuntimeError(ultimo) from None
        except Exception as e:
            ultimo = f"{type(e).__name__}: {e}"

        if intento < reintentos:
            espera = 2 ** intento
            log(f"  · reintento {intento}/{reintentos - 1} en {espera}s — {ultimo}")
            time.sleep(espera)

    raise RuntimeError(f"agotados los reintentos — {ultimo}")


# --------------------------------------------------------------------------- #
# Ejecución
# --------------------------------------------------------------------------- #

# Frases con las que CONTRATO.md describe cada sección. Varios modelos las
# reproducen bajo su propio encabezado, como si fueran contenido.
#
# Cada patrón lleva sus propios flags, y ninguno mezcla DOTALL con `.*$`: bajo
# DOTALL el punto also casa saltos de línea, así que `.*$` no para al final de
# la línea sino al final del documento. Esa mezcla se llevó por delante las
# secciones 2 a 5 de dos extracciones enteras.
_ECO = [
    (r"Lo que observo, con evidencia\.[^\n]*\n[^\n]*no se afirma\.", re.I),
    (r"Lo que funcionar[íi]a para OTRO producto\.\s*Patrones, no contenido\.", re.I),
    (r"Lo que NO transfiere: espec[íi]fico del original, de su marca o de su nicho\.", re.I),
    (r"Qu[ée] necesito saber del producto nuevo para poder reproducir mi parte\.", re.I),
    (r"Un p[áa]rrafo\.[^\n]*rehacerse\.", re.I),
    # `Formato: PT-<esp>-<n>: …`, con <esp> literal o ya sustituido.
    (r"^[ \t]*Formato:[ \t]*`?(PT|CT|Q)-[\w<>-]+[^\n]*$", re.I | re.M),
]


# Guiones tipográficos que un modelo cuela donde debería ir el ASCII. En prosa
# da igual; dentro de un identificador `PT-<esp>-<n>` rompe el contrato, porque
# nada que lo busque lo encuentra. Un especialista entero apareció sin un solo
# patrón por escribir `PT‑neuromarketing‑1` con guion no separable.
_GUIONES = str.maketrans({"‐": "-", "‑": "-", "‒": "-", "–": "-"})


def limpiar(txt: str) -> str:
    """Quita la valla de markdown y el eco de las instrucciones del contrato."""
    t = txt.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-zA-Z]*\n", "", t)
        t = re.sub(r"\n```$", "", t)

    # Solo dentro de los identificadores: la raya larga en prosa se respeta.
    t = re.sub(r"\b(PT|CT|Q)[‐-–\-][\w‐-–-]*?[‐-–\-]\d+",
               lambda m: m.group(0).translate(_GUIONES), t)
    for pat, flags in _ECO:
        t = re.sub(pat, "", t, flags=flags)
    # Los borrados dejan huecos de tres o más saltos.
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = t.strip() + "\n"

    # Red de seguridad: una limpieza jamás debe llevarse una sección por delante.
    # Se compara el número de encabezados, no el tamaño: quitar el eco reduce el
    # texto en una proporción que depende de lo largo que sea el documento, pero
    # nunca debe cambiar su estructura. Ante la duda, sucio antes que mutilado.
    cuenta = lambda s: len(re.findall(r"^#{1,3} ", s, re.M))
    if cuenta(t) < cuenta(txt):
        return txt.strip() + "\n"
    return t


def uno(esp: str, slug: str, mat: str, modelo: str, key: str, max_tokens: int,
        modo: str = "extraer", producto: str = "") -> tuple[str, bool, str]:
    if modo == "extraer":
        destino = RAIZ / "casos" / slug / "extraccion" / f"{esp}.md"
    else:
        destino = carpeta_producto(slug, producto) / f"{esp}.md"
    t0 = time.time()
    try:
        if modo == "extraer":
            sistema, usuario = construir_prompt(esp, slug, mat)
        else:
            sistema, usuario = construir_prompt_reproducir(esp, slug, mat, producto)
        salida = limpiar(llamar(sistema, usuario, modelo, key, max_tokens))
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(salida, encoding="utf-8")
        seg = time.time() - t0
        return esp, True, f"{len(salida):,} car en {seg:.0f}s"
    except Exception as e:
        return esp, False, str(e)[:200]


def extraer(slug: str, quienes: list[str], modelo: str, workers: int,
            max_tokens: int, dry_run: bool) -> int:
    mat = material(slug)

    if dry_run:
        sistema, usuario = construir_prompt(quienes[0], slug, mat)
        print(f"===== SYSTEM ({quienes[0]}) =====\n{sistema}\n")
        print(f"===== USER ({quienes[0]}) =====\n{usuario}")
        print(f"\n===== tamaño: {len(sistema) + len(usuario):,} caracteres "
              f"(~{(len(sistema) + len(usuario)) // 3:,} tokens) =====")
        return 0

    key = api_key()
    log(f"Caso {slug} · modelo {modelo} · {len(quienes)} especialistas "
        f"· {workers} en paralelo")
    log(f"Material curado: {len(mat):,} caracteres (~{len(mat) // 3:,} tokens) por encargo\n")

    ok, fallos = [], []
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futuros = {
            pool.submit(uno, e, slug, mat, modelo, key, max_tokens): e
            for e in quienes
        }
        for f in as_completed(futuros):
            esp, bien, nota = f.result()
            if bien:
                ok.append(esp)
                log(f"  ok    {esp:22} {nota}")
            else:
                fallos.append(esp)
                log(f"  FALLA {esp:22} {nota}")

    log(f"\n{len(ok)}/{len(quienes)} escritos en casos/{slug}/extraccion/")
    if fallos:
        log("Fallaron: " + ", ".join(sorted(fallos)))
        log(f"Reintenta solo esos:  python tools/deepseek.py extraer {slug} "
            f"--solo {','.join(sorted(fallos))}")
    return 1 if fallos else 0


def reproducir(slug: str, producto: str, solo_ola: int | None, modelo: str,
               workers: int, max_tokens: int, dry_run: bool) -> int:
    """Las tres olas, en orden. Dentro de cada una sí van en paralelo.

    Entre olas se espera: si `copywriter` escribe antes de que `mercadologo`
    fije el nivel de consciencia, escribe para el avatar equivocado y hay que
    rehacerlo entero.
    """
    mat = material_reproducir(slug, producto)

    if dry_run:
        esp = OLAS[(solo_ola or 1) - 1][1][0]
        sistema, usuario = construir_prompt_reproducir(esp, slug, mat, producto)
        print(f"===== SYSTEM ({esp}) =====\n{sistema}\n")
        print(f"===== USER ({esp}) =====\n{usuario}")
        print(f"\n===== tamaño: {len(sistema) + len(usuario):,} caracteres "
              f"(~{(len(sistema) + len(usuario)) // 3:,} tokens) =====")
        return 0

    key = api_key()
    carpeta_producto(slug, producto).mkdir(parents=True, exist_ok=True)
    log(f"Origen {slug} → producto {producto} · modelo {modelo} · modo REPRODUCIR")
    log(f"Compartido: {len(mat):,} caracteres (~{len(mat) // 3:,} tokens)\n")

    fallos_totales = []
    for n, esps, por_que in OLAS:
        if solo_ola and n != solo_ola:
            continue
        log(f"== OLA {n} — {por_que}")
        ok, fallos = [], []
        with ThreadPoolExecutor(max_workers=min(workers, len(esps))) as pool:
            futuros = {pool.submit(uno, e, slug, mat, modelo, key,
                                   max_tokens, "reproducir", producto): e
                       for e in esps}
            for f in as_completed(futuros):
                esp, bien, nota = f.result()
                (ok if bien else fallos).append(esp)
                log(f"  {'ok   ' if bien else 'FALLA'} {esp:22} {nota}")
        log(f"  ola {n}: {len(ok)}/{len(esps)}\n")
        fallos_totales += fallos
        if fallos and not solo_ola:
            log("  Una ola incompleta condiciona a las siguientes: se para aquí.")
            log(f"  Reintenta:  python tools/deepseek.py reproducir {slug} "
                f"{producto} --ola {n}")
            break

    log(f"Salidas en casos/{slug}/reproduccion/{producto}/")
    return 1 if fallos_totales else 0


def revisar(slug: str, producto: str, modelo: str, max_tokens: int,
            dry_run: bool) -> int:
    """Paso 6b: `programador` compara el build con el plan. Una sola llamada."""
    mat = material_revisar(slug, producto)
    contrato = (RAIZ / "CONTRATO.md").read_text(encoding="utf-8")
    protocolo = (RAIZ / "especialistas" / "programador" / "reproducir.md").read_text(encoding="utf-8")
    identidad = (RAIZ / "especialistas" / "programador" / "extraer.md").read_text(encoding="utf-8")

    sistema = (
        "Eres el especialista `programador`. Revisas un build ya construido "
        "contra el plan que lo ordenó. Eres el único que ve el resultado.\n\n"
        "1. **No reabres decisiones.** Si una directiva te parece equivocada, "
        "va a Conflictos y sigues. La discusión ya ocurrió.\n"
        "2. **Cada hallazgo cita la línea del archivo y la directiva del plan.** "
        "Si no puedes citar ambas, no es un hallazgo: es una opinión.\n"
        "3. **Lo inventado va primero.** Un testimonio de relleno, una cifra "
        "estimada o una foto que el plan no pedía es el hallazgo más grave.\n\n"
        "Respondes con el documento markdown y nada más."
    )
    usuario = (f"# CONTRATO.md\n\n{contrato}\n\n---\n\n{mat}\n---\n\n"
               f"# Quién eres\n\n{identidad}\n\n---\n\n"
               f"# Tu protocolo\n\n{protocolo}\n\n---\n\n# Encargo\n\n"
               f"Ejecuta tu protocolo y devuelve el documento completo de "
               f"`casos/{slug}/reproduccion/{producto}/programador.md`, con las cinco "
               f"secciones del contrato. Las Directivas son correcciones concretas, "
               f"con el formato `D-programador-<n>`, ordenadas por gravedad.\n\n"
               f"Empieza directamente por `# Programador — revisión del build`.")

    if dry_run:
        print(f"===== SYSTEM =====\n{sistema}\n\n===== USER =====\n{usuario}")
        print(f"\n===== tamaño: {len(sistema) + len(usuario):,} caracteres "
              f"(~{(len(sistema) + len(usuario)) // 3:,} tokens) =====")
        return 0

    key = api_key()
    log(f"Revisión de {slug} → {producto} · modelo {modelo}")
    log(f"Material: {len(mat):,} caracteres (~{len(mat) // 3:,} tokens)\n")
    t0 = time.time()
    try:
        salida = limpiar(llamar(sistema, usuario, modelo, key, max_tokens))
    except Exception as e:
        log(f"  FALLA — {str(e)[:200]}")
        return 1
    destino = carpeta_producto(slug, producto) / "programador.md"
    destino.write_text(salida, encoding="utf-8")
    log(f"  ok  {len(salida):,} car en {time.time() - t0:.0f}s → {destino}")
    return 0


def main() -> None:
    p = argparse.ArgumentParser(
        description="Ejecuta los encargos de los especialistas contra la API de DeepSeek.")
    sub = p.add_subparsers(dest="cmd", required=True)

    v = sub.add_parser("revisar", help="paso 6b: programador revisa el build")
    v.add_argument("slug")
    v.add_argument("producto")
    v.add_argument("--modelo", default=MODELO_POR_DEFECTO)
    v.add_argument("--max-tokens", type=int, default=8000)
    v.add_argument("--dry-run", action="store_true")

    r = sub.add_parser("reproducir", help="lanza el protocolo REPRODUCIR, en tres olas")
    r.add_argument("slug", help="el caso de origen, del que se copia")
    r.add_argument("producto", help="carpeta del producto destino dentro de reproduccion/")
    r.add_argument("--ola", type=int, choices=[1, 2, 3],
                   help="solo esta ola (por defecto las tres, en orden)")
    r.add_argument("--modelo", default=MODELO_POR_DEFECTO)
    r.add_argument("--workers", type=int, default=4)
    r.add_argument("--max-tokens", type=int, default=8000)
    r.add_argument("--dry-run", action="store_true")

    e = sub.add_parser("extraer", help="lanza el protocolo EXTRAER")
    e.add_argument("slug")
    e.add_argument("--solo", help="lista separada por comas")
    e.add_argument("--excepto", help="lista separada por comas")
    e.add_argument("--modelo", default=MODELO_POR_DEFECTO,
                   help=f"deepseek-v4-pro | deepseek-v4-flash (por defecto {MODELO_POR_DEFECTO})")
    e.add_argument("--workers", type=int, default=4)
    e.add_argument("--max-tokens", type=int, default=8000)
    e.add_argument("--dry-run", action="store_true",
                   help="imprime el prompt del primer especialista y sale")

    a = p.parse_args()

    if a.cmd == "revisar":
        sys.exit(revisar(a.slug, a.producto, a.modelo, a.max_tokens, a.dry_run))
    if a.cmd == "reproducir":
        sys.exit(reproducir(a.slug, a.producto, a.ola, a.modelo, a.workers,
                            a.max_tokens, a.dry_run))

    quienes = ESPECIALISTAS
    if a.solo:
        quienes = [x.strip() for x in a.solo.split(",") if x.strip()]
    if a.excepto:
        fuera = {x.strip() for x in a.excepto.split(",")}
        quienes = [x for x in quienes if x not in fuera]

    desconocidos = [x for x in quienes if x not in ESPECIALISTAS]
    if desconocidos:
        sys.exit(f"Especialistas desconocidos: {', '.join(desconocidos)}\n"
                 f"Disponibles: {', '.join(ESPECIALISTAS)}")
    if not quienes:
        sys.exit("No queda ningún especialista que lanzar.")

    sys.exit(extraer(a.slug, quienes, a.modelo, a.workers, a.max_tokens, a.dry_run))


if __name__ == "__main__":
    main()
