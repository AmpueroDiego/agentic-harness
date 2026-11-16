#!/usr/bin/env python3
"""
render.py — abre un build y lo fotografía en escritorio y móvil

El paso 6a de `orquestador/reproducir.md`. Existe porque un build puede cumplir
las once directivas sobre el papel y verse roto igualmente, y eso no lo detecta
ningún grep: hay que mirarlo.

Uso:
    python tools/render.py casos/<slug>/reproduccion/<producto>/build.html
    python tools/render.py <ruta> --ancho 1280 --movil 360

Deja `build-desktop.png` y `build-movil.png` junto al archivo, y avisa de lo
único que sí se puede medir sin ojos: desbordamiento horizontal.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    sys.exit("Falta Playwright.  pip install -r tools/requirements.txt")


def _medir(page) -> dict:
    """Lo poco que se puede comprobar sin mirar."""
    return page.evaluate("""() => {
      const d = document.documentElement;
      const desborda = [];
      document.querySelectorAll('body *').forEach(el => {
        const r = el.getBoundingClientRect();
        if (r.width > 0 && (r.right > d.clientWidth + 1 || r.left < -1)) {
          desborda.push({
            tag: el.tagName.toLowerCase(),
            cls: (typeof el.className === 'string' ? el.className : '') || null,
            derecha: Math.round(r.right)
          });
        }
      });
      return {
        ancho_viewport: d.clientWidth,
        ancho_documento: Math.round(d.scrollWidth),
        alto: Math.round(d.scrollHeight),
        scroll_horizontal: d.scrollWidth > d.clientWidth + 1,
        desbordan: desborda.slice(0, 8),
        accionables: document.querySelectorAll('a[href], button').length
      };
    }""")


def render(archivo: Path, ancho: int, movil: int) -> int:
    if not archivo.exists():
        sys.exit(f"No existe {archivo}")
    url = archivo.resolve().as_uri()
    salidas = []

    with sync_playwright() as p:
        nav = p.chromium.launch()
        for nombre, vp, escala in (
            ("desktop", {"width": ancho, "height": 900}, 1),
            ("movil", {"width": movil, "height": 844}, 2),
        ):
            ctx = nav.new_context(viewport=vp, device_scale_factor=escala,
                                  locale="es-419")
            page = ctx.new_page()
            page.goto(url, wait_until="load")
            page.wait_for_timeout(300)

            m = _medir(page)
            destino = archivo.with_name(f"{archivo.stem}-{nombre}.png")
            page.screenshot(path=str(destino), full_page=True)
            salidas.append((nombre, destino, m))
            ctx.close()
        nav.close()

    problemas = 0
    for nombre, destino, m in salidas:
        print(f"\n  {nombre}  ·  {m['ancho_viewport']}px  ·  alto {m['alto']}px")
        print(f"    {destino.name}")
        print(f"    accionables: {m['accionables']}")
        if m["scroll_horizontal"]:
            problemas += 1
            print(f"    ⚠ SCROLL HORIZONTAL — documento {m['ancho_documento']}px "
                  f"sobre viewport de {m['ancho_viewport']}px")
            for d in m["desbordan"]:
                print(f"        <{d['tag']}> {d['cls'] or ''} llega a {d['derecha']}px")
        else:
            print("    sin desbordamiento horizontal")

    print("\n  Lo demás se mira en las capturas: que el contenido esté centrado,")
    print("  que la medida de lectura aguante, que el CTA se distinga y que los")
    print("  huecos [FALTA: …] se vean. Eso no lo puede comprobar un script.\n")
    return 1 if problemas else 0


def main() -> None:
    p = argparse.ArgumentParser(description="Fotografía un build en escritorio y móvil.")
    p.add_argument("archivo")
    p.add_argument("--ancho", type=int, default=1440, help="viewport de escritorio")
    p.add_argument("--movil", type=int, default=390, help="viewport de móvil")
    a = p.parse_args()
    sys.exit(render(Path(a.archivo), a.ancho, a.movil))


if __name__ == "__main__":
    main()
