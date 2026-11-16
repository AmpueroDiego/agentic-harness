#!/usr/bin/env python3
"""
verificar.py — comprueba las salidas de los especialistas contra el contrato

No juzga si un hallazgo es bueno. Comprueba lo que sí es comprobable: que el
documento tenga la forma que el contrato exige, que sus identificadores sean
utilizables, que no haya colado texto literal del original y que las cifras que
afirma existan en el material.

Uso:
    python tools/verificar.py <slug>
    python tools/verificar.py <slug> --solo frontend,disenador
    python tools/verificar.py <slug> --modo reproducir
    python tools/verificar.py <slug> --detalle          # lista cada incidencia

Sale con código 1 si hay algún fallo grave. Los avisos no bloquean.

**Es un informe, no una aduana.** Solo son graves las cosas que rompen el
contrato de verdad: falta una sección, está vacía, no hay identificadores, o hay
copia literal repetida del original. Todo lo demás —numeración con huecos,
guiones raros, cifras derivadas, citas desactualizadas— se reporta y se sigue.
Perseguir la salida perfecta cuesta más de lo que vale.

## Por qué está escrito así

Nada aquí conoce este caso, este idioma ni este sector:

- **El eco del contrato se deriva de `CONTRATO.md`**, leyendo las líneas
  descriptivas de su plantilla. Si el contrato cambia, la comprobación cambia
  sola. Una lista de frases escrita a mano solo habría servido para su idioma.
- **Las frases literales se detectan por n-gramas** contra el texto capturado
  del caso, no contra un diccionario.
- **Las cifras se comprueban contra el material**, sin saber qué significan.

Lo que exige entender el texto —si un hallazgo invade otra disciplina, si un
patrón es realmente transferible— no se comprueba aquí. Eso es criterio, y este
script no lo tiene.
"""
from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

RAIZ = Path(__file__).resolve().parent.parent

ESPECIALISTAS = [
    "frontend", "disenador", "neuromarketing", "psicologo", "linguista",
    "copywriter", "mercadologo", "sociologo", "ingeniero-industrial",
    "administrador", "growth-data",
]

SECCIONES = {
    "extraer": ["Hallazgos", "Patrones transferibles", "Contaminación",
                "Preguntas al producto destino", "Veredicto"],
    "reproducir": ["Decisiones", "Directivas", "Descartes", "Faltantes", "Conflictos"],
}

GRAVE, AVISO = "GRAVE", "aviso"

# Guiones que no son ASCII. En prosa son correctos; dentro de un identificador
# lo rompen, porque nada que lo busque lo encuentra.
NO_ASCII = "‐‑‒–—"


class Informe:
    def __init__(self, esp: str):
        self.esp = esp
        self.items: list[tuple[str, str, str]] = []   # (nivel, prueba, detalle)

    def add(self, nivel: str, prueba: str, detalle: str) -> None:
        self.items.append((nivel, prueba, detalle))

    @property
    def graves(self) -> int:
        return sum(1 for n, _, _ in self.items if n == GRAVE)

    @property
    def avisos(self) -> int:
        return sum(1 for n, _, _ in self.items if n == AVISO)


# --------------------------------------------------------------------------- #
# Material del caso
# --------------------------------------------------------------------------- #

def texto_plano(page_html: str) -> str:
    s = re.sub(r"<(script|style|svg)[^>]*>.*?</\1>", " ", page_html, flags=re.S | re.I)
    s = html.unescape(re.sub(r"<[^>]+>", " ", s))
    return re.sub(r"\s+", " ", s).strip()


def material(slug: str) -> tuple[str, str]:
    """Devuelve (texto de la página, todo el material que vio el especialista).

    El segundo se pide a `deepseek.material()`, que es quien monta el prompt.
    **Tiene que ser exactamente el mismo**: si el verificador mira menos, acusa
    de inventar cifras que el especialista sí tenía delante —los hechos del DOM
    se calculan al vuelo y no viven en ningún archivo de `raw/`.
    """
    raw = RAIZ / "casos" / slug / "raw"
    page = raw / "page.html"
    texto = texto_plano(page.read_text(encoding="utf-8", errors="replace")) if page.exists() else ""

    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        import deepseek
        return texto, deepseek.material(slug)
    except Exception:
        # Sin deepseek.py se comprueba con lo que hay en disco, y se avisa.
        partes = [texto]
        an = raw / "analysis"
        partes += [f.read_text(encoding="utf-8", errors="replace")
                   for f in sorted(an.glob("*.json"))] if an.exists() else []
        cap = raw / "captura.json"
        if cap.exists():
            partes.append(cap.read_text(encoding="utf-8", errors="replace"))
        return texto, " ".join(partes)


def frases_del_contrato() -> list[str]:
    """Las líneas con que CONTRATO.md describe cada sección de la plantilla.

    Se leen del contrato en vez de escribirse aquí: así la comprobación sigue
    al contrato cuando cambie, y no depende del idioma en que esté escrito.
    """
    f = RAIZ / "CONTRATO.md"
    if not f.exists():
        return []
    frases = []
    for bloque in re.findall(r"```markdown\n(.*?)```", f.read_text(encoding="utf-8"), re.S):
        for linea in bloque.splitlines():
            l = linea.strip()
            # Las descriptivas: no son encabezado, ni plantilla de formato, ni ruido.
            if l and not l.startswith(("#", "`", "-", "|")) and len(l) > 25:
                frases.append(l)
    return frases


def ngramas(texto: str, n: int = 8) -> set[str]:
    pal = re.findall(r"\w+", texto.lower())
    return {" ".join(pal[i:i + n]) for i in range(len(pal) - n + 1)}


# --------------------------------------------------------------------------- #
# Comprobaciones
# --------------------------------------------------------------------------- #

def c_estructura(inf: Informe, doc: str, modo: str) -> dict[int, str]:
    """Cinco secciones, en orden y con contenido. Devuelve el cuerpo de cada una."""
    esperadas = SECCIONES[modo]
    cuerpos: dict[int, str] = {}

    encontrados = [(int(m.group(1)), m.start()) for m in
                   re.finditer(r"^##\s*(\d)\.", doc, re.M)]
    numeros = [n for n, _ in encontrados]

    for i in range(1, 6):
        if i not in numeros:
            inf.add(GRAVE, "estructura", f"falta la sección {i} ({esperadas[i-1]})")

    if numeros != sorted(numeros):
        inf.add(GRAVE, "estructura", f"secciones desordenadas: {numeros}")

    for idx, (n, ini) in enumerate(encontrados):
        fin = encontrados[idx + 1][1] if idx + 1 < len(encontrados) else len(doc)
        cuerpo = doc[ini:fin]
        cuerpos[n] = cuerpo
        # Se mide por caracteres, no por líneas: el Veredicto es un solo párrafo
        # por contrato, y contar líneas lo daba por truncado en diez de once.
        util = " ".join(cuerpo.splitlines()[1:]).strip()
        if len(util) < 120:
            inf.add(GRAVE, "estructura",
                    f"sección {n} vacía o truncada ({len(util)} caracteres)")
    return cuerpos


def c_identificadores(inf: Informe, doc: str, esp: str, modo: str) -> None:
    prefijos = {"extraer": ("PT", "CT", "Q"), "reproducir": ("D",)}[modo]

    for p in prefijos:
        # Se acepta cualquier guion para detectar, y luego se exige ASCII.
        hallados = re.findall(rf"\b{p}[{NO_ASCII}-]{re.escape(esp)}[{NO_ASCII}-](\d+)", doc)
        if not hallados:
            inf.add(GRAVE, "identificadores", f"ningún `{p}-{esp}-<n>` en el documento")
            continue

        raros = re.findall(rf"\b{p}[{NO_ASCII}]{re.escape(esp)}|{p}-{re.escape(esp)}[{NO_ASCII}]", doc)
        if raros:
            inf.add(AVISO, "identificadores",
                    f"{len(raros)} identificadores `{p}` con guion no ASCII "
                    "(lo arregla `limpiar()` al regenerar)")

        nums = sorted({int(x) for x in hallados})
        if len(nums) != len(hallados):
            inf.add(AVISO, "identificadores", f"`{p}` con numeración repetida")
        huecos = [i for i in range(1, max(nums) + 1) if i not in nums]
        if huecos:
            inf.add(AVISO, "identificadores", f"`{p}` salta los números {huecos}")

    # Un especialista que numera con el nombre de otro suele ser copia-pega.
    ajenos = {m for m in re.findall(r"\b(?:PT|CT|Q|D)-([a-z-]+)-\d+", doc)
              if m != esp and m in ESPECIALISTAS}
    if ajenos:
        inf.add(GRAVE, "identificadores",
                f"usa identificadores de otro especialista: {', '.join(sorted(ajenos))}")


def c_eco(inf: Informe, doc: str, frases: list[str]) -> None:
    for f in frases:
        if f in doc:
            inf.add(AVISO, "eco del contrato", f"copia la instrucción «{f[:60]}…»")


def c_literal(inf: Informe, cuerpos: dict[int, str], texto: str, detalle: bool) -> None:
    """Frases del original coladas donde el contrato exige patrón, no copia."""
    cuerpo = cuerpos.get(2)
    if not cuerpo or not texto:
        return
    comunes = ngramas(cuerpo) & ngramas(texto)
    if not comunes:
        return
    # Una coincidencia suelta puede ser casualidad del idioma; varias, no.
    nivel = GRAVE if len(comunes) >= 3 else AVISO
    muestra = "; ".join(sorted(comunes)[:2])
    inf.add(nivel, "patrón, no frase",
            f"{len(comunes)} secuencias literales del original en Patrones"
            + (f": «{muestra}»" if detalle else ""))


def c_cifras(inf: Informe, doc: str, mat: str, detalle: bool) -> None:
    """Números afirmados que no aparecen en ninguna parte del material."""
    # Se ignoran los de los propios identificadores y los de una o dos cifras,
    # que casi siempre son enumeraciones del propio documento.
    limpio = re.sub(r"\b(?:PT|CT|Q|D)-[a-z-]+-\d+", " ", doc)
    limpio = re.sub(r"^#{1,6}\s*\d+\.", " ", limpio, flags=re.M)

    # Los separadores se quitan en ambos lados: el material puede escribir
    # `3,000` donde el documento escribe `3000` y son la misma cifra.
    sin_sep = lambda s: re.sub(r"(?<=\d)[.,](?=\d)", "", s)
    mat_norm = sin_sep(mat)

    huerfanas = []
    # Empieza y acaba en dígito: `1199.` no es una cifra, es un token cortado.
    for n in {x for x in re.findall(r"\b\d[\d.,]*\d\b", limpio) if len(x) >= 3}:
        # Dos o más separadores no es una cifra: es una secuencia — un rgba, una
        # versión, una lista. Compararla como número solo genera ruido.
        if len(re.findall(r"[.,]", n)) >= 2:
            continue
        if sin_sep(n) not in mat_norm:
            huerfanas.append(n)
    if huerfanas:
        inf.add(AVISO, "cifras sin respaldo",
                f"{len(huerfanas)} cifras que no están en el material"
                + (f": {', '.join(sorted(huerfanas)[:6])}" if detalle else ""))


# --------------------------------------------------------------------------- #

def c_referencias(slug: str, base: Path, detalle: bool) -> Informe:
    """Que sintesis.md y SKILL.md no citen identificadores inexistentes.

    Regenerar una extracción renumera sus identificadores, y las citas de la
    síntesis quedan apuntando al vacío sin que nada falle. Esto solo detecta las
    citas rotas; **el peligro de verdad es la que sigue existiendo con otro
    significado**, y eso no lo puede ver un script: tras regenerar a alguien,
    hay que releer lo que la síntesis decía de él.
    """
    inf = Informe("· sintesis y SKILL")
    existen = set()
    for f in base.glob("*.md"):
        existen |= set(re.findall(r"\b((?:PT|CT|Q|D)-[a-z-]+-\d+)\b",
                                  f.read_text(encoding="utf-8")))
    if not existen:
        return inf

    caso = RAIZ / "casos" / slug
    for nombre in ("sintesis.md", "SKILL.md"):
        f = caso / nombre
        if not f.exists():
            continue
        citados = set(re.findall(r"\b((?:PT|CT|Q|D)-[a-z-]+-\d+)\b",
                                 f.read_text(encoding="utf-8")))
        rotos = sorted(citados - existen)
        if rotos:
            inf.add(AVISO, "referencias",
                    f"{nombre} cita {len(rotos)} identificadores que ya no existen"
                    + (f": {', '.join(rotos[:6])}" if detalle else ""))
    return inf


def verificar(slug: str, quienes: list[str], modo: str, detalle: bool) -> int:
    base = RAIZ / "casos" / slug / ("extraccion" if modo == "extraer" else "reproduccion")
    if not base.exists():
        sys.exit(f"No existe {base}")

    texto, mat = material(slug)
    frases = frases_del_contrato()
    if not texto:
        print("  aviso: sin page.html; se omite la comprobación de frases literales\n")

    informes = []
    for esp in quienes:
        f = base / f"{esp}.md"
        inf = Informe(esp)
        if not f.exists():
            inf.add(GRAVE, "archivo", "no existe")
            informes.append(inf)
            continue
        doc = f.read_text(encoding="utf-8")
        cuerpos = c_estructura(inf, doc, modo)
        c_identificadores(inf, doc, esp, modo)
        c_eco(inf, doc, frases)
        if modo == "extraer":
            c_literal(inf, cuerpos, texto, detalle)
        c_cifras(inf, doc, mat, detalle)
        informes.append(inf)

    ref = c_referencias(slug, base, detalle)
    if ref.items:
        informes.append(ref)

    print(f"  {slug} · modo {modo} · {len(quienes)} especialistas\n")
    for inf in informes:
        marca = "FALLA" if inf.graves else ("aviso" if inf.avisos else "ok   ")
        resumen = (f"{inf.graves} graves, {inf.avisos} avisos"
                   if inf.items else "sin incidencias")
        print(f"  {marca} {inf.esp:22} {resumen}")
        for nivel, prueba, det in inf.items:
            print(f"          {'!' if nivel == GRAVE else '·'} [{prueba}] {det}")

    graves = sum(i.graves for i in informes)
    avisos = sum(i.avisos for i in informes)
    limpios = sum(1 for i in informes if not i.items)
    print(f"\n  {limpios}/{len(informes)} sin incidencias · {graves} graves · {avisos} avisos")
    if graves:
        malos = [i.esp for i in informes if i.graves]
        print(f"  Regenera: python tools/deepseek.py {modo} {slug} --solo {','.join(malos)}")
    return 1 if graves else 0


def main() -> None:
    p = argparse.ArgumentParser(
        description="Comprueba las salidas de los especialistas contra el contrato.")
    p.add_argument("slug")
    p.add_argument("--solo", help="lista separada por comas")
    p.add_argument("--modo", choices=["extraer", "reproducir"], default="extraer")
    p.add_argument("--detalle", action="store_true", help="muestra cada incidencia")
    a = p.parse_args()

    quienes = ([x.strip() for x in a.solo.split(",") if x.strip()]
               if a.solo else ESPECIALISTAS)
    desconocidos = [x for x in quienes if x not in ESPECIALISTAS]
    if desconocidos:
        sys.exit(f"Especialistas desconocidos: {', '.join(desconocidos)}")

    sys.exit(verificar(a.slug, quienes, a.modo, a.detalle))


if __name__ == "__main__":
    main()
