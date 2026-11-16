#!/usr/bin/env python3
"""
capture.py — captura un funnel a casos/<slug>/raw/

Una sola pasada de Playwright produce todo lo que necesitan los 11 especialistas.
El artefacto clave es elements.json: caja y estilos computados de cada elemento
visible. Desde ahí los analizadores de tools/analyze/ trabajan sin navegador.

Uso:
    python tools/capture.py https://ejemplo.com/oferta
    python tools/capture.py https://ejemplo.com --slug mi-caso --depth 2
    python tools/capture.py https://ejemplo.com --passes 3      # detectar A/B
    python tools/capture.py --lote funnels.txt

Por defecto NO envía formularios. Para pasar el opt-in hace falta permiso explícito:
    python tools/capture.py URL --submit-optin --email test@dominio.com
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse, urljoin

# La salida lleva flechas y acentos; la consola de Windows es cp1252 por defecto.
for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

try:
    from playwright.sync_api import sync_playwright, Page, TimeoutError as PWTimeout
except ImportError:
    sys.exit("Falta Playwright.  pip install playwright && playwright install chromium")

def _firma(html: str) -> str:
    """Huella del contenido visible, inmune a lo que cambia en cada carga.

    Comparar `len(html)` daba falsos negativos: dos variantes de copy con el
    mismo número de caracteres son indistinguibles, y ese es justo el caso
    típico de un test A/B. Y falsos positivos: un contador que avanza cambia el
    HTML en cada pasada sin que haya variante ninguna.

    Se hashea el texto sin marcado, sin scripts y sin dígitos — los dígitos se
    llevan por delante contadores, marcas de tiempo y nonces de sesión.
    """
    import hashlib

    t = re.sub(r"<(script|style|svg)[^>]*>.*?</\1>", " ", html, flags=re.S | re.I)
    t = re.sub(r"<[^>]+>", " ", t)          # marcado
    t = re.sub(r"\d+", "#", t)              # contadores, timestamps, nonces
    t = re.sub(r"\s+", " ", t).strip().lower()
    return hashlib.sha1(t.encode("utf-8", "replace")).hexdigest()[:16]


DESKTOP = {"width": 1440, "height": 900}
MOBILE = {"width": 390, "height": 844}
LOCALE = "es-419"
TZ = "America/Bogota"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36")

# Volcado de elementos: lo que alimenta a colors, typography, layout y attention.
DUMP_JS = r"""
() => {
  const out = [];
  const nodes = document.querySelectorAll('body *');
  for (const el of nodes) {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    const s = getComputedStyle(el);
    if (s.display === 'none' || s.visibility === 'hidden' || +s.opacity === 0) continue;
    const txt = Array.from(el.childNodes)
      .filter(n => n.nodeType === 3)
      .map(n => n.textContent.trim())
      .join(' ').trim();
    out.push({
      tag: el.tagName.toLowerCase(),
      id: el.id || null,
      cls: (typeof el.className === 'string' ? el.className : '') || null,
      box: {x: Math.round(r.x), y: Math.round(r.y + window.scrollY),
            w: Math.round(r.width), h: Math.round(r.height)},
      text: txt.slice(0, 300) || null,
      color: s.color,
      bg: s.backgroundColor,
      bgImage: s.backgroundImage !== 'none' ? s.backgroundImage.slice(0, 200) : null,
      font: s.fontFamily,
      size: s.fontSize,
      weight: s.fontWeight,
      lh: s.lineHeight,
      ls: s.letterSpacing,
      radius: s.borderRadius,
      shadow: s.boxShadow !== 'none' ? s.boxShadow : null,
      display: s.display,
      gap: s.gap !== 'normal' ? s.gap : null,
      cols: s.gridTemplateColumns !== 'none' ? s.gridTemplateColumns : null,
      pad: s.padding,
      margin: s.margin,
      z: s.zIndex,
      pos: s.position,
    });
  }
  return {
    elements: out,
    doc: {
      title: document.title,
      lang: document.documentElement.lang || null,
      h: document.documentElement.scrollHeight,
      metas: Array.from(document.querySelectorAll('meta')).map(m => ({
        name: m.getAttribute('name') || m.getAttribute('property'),
        content: (m.getAttribute('content') || '').slice(0, 300),
      })).filter(m => m.name),
      headings: Array.from(document.querySelectorAll('h1,h2,h3,h4')).map(h => ({
        level: +h.tagName[1], text: h.innerText.trim().slice(0, 200),
      })),
      forms: Array.from(document.querySelectorAll('form')).map(f => ({
        action: f.action || null, method: f.method || null,
        fields: Array.from(f.querySelectorAll('input,select,textarea')).map(i => ({
          name: i.name || null, type: i.type || i.tagName.toLowerCase(),
          required: i.required || false, hidden: i.type === 'hidden',
          value: i.type === 'hidden' ? (i.value || '').slice(0, 200) : null,
          placeholder: i.placeholder || null,
        })),
      })),
      links: Array.from(document.querySelectorAll('a[href]')).map(a => ({
        href: a.href, text: a.innerText.trim().slice(0, 120),
        external: a.hostname !== location.hostname,
      })),
      buttons: Array.from(document.querySelectorAll('button,[role=button],a.btn,input[type=submit]'))
        .map(b => ({text: (b.innerText || b.value || '').trim().slice(0, 120)}))
        .filter(b => b.text),
    },
  };
}
"""

STORAGE_JS = r"""
() => ({
  local: Object.fromEntries(Object.entries(localStorage).map(([k,v]) => [k, String(v).slice(0,300)])),
  session: Object.fromEntries(Object.entries(sessionStorage).map(([k,v]) => [k, String(v).slice(0,300)])),
})
"""

ACEPTAR = re.compile(
    r"(acept|permitir|entendido|de acuerdo|got it|allow all|accept|consent|"
    r"estoy de acuerdo|continuar)", re.I)


def slugify(url: str) -> str:
    h = urlparse(url).netloc.lower().replace("www.", "")
    return re.sub(r"[^a-z0-9]+", "-", h.rsplit(".", 1)[0]).strip("-") or "caso"


def _wait(page: Page) -> None:
    try:
        page.wait_for_load_state("networkidle", timeout=15000)
    except PWTimeout:
        pass


def _scroll(page: Page) -> None:
    """Recorre la página para disparar lazy-load y animaciones de entrada."""
    page.evaluate("""async () => {
        const step = window.innerHeight * 0.8;
        for (let y = 0; y < document.body.scrollHeight; y += step) {
            window.scrollTo(0, y);
            await new Promise(r => setTimeout(r, 250));
        }
        window.scrollTo(0, 0);
        await new Promise(r => setTimeout(r, 400));
    }""")


def _aceptar_cookies(page: Page) -> str | None:
    """Devuelve el texto del botón pulsado, o None si no había banner."""
    for sel in ("button", "[role=button]", "a"):
        for el in page.query_selector_all(sel):
            try:
                t = (el.inner_text() or "").strip()
            except Exception:
                continue
            if t and len(t) < 40 and ACEPTAR.search(t) and el.is_visible():
                try:
                    el.click(timeout=2500)
                    page.wait_for_timeout(1200)
                    return t
                except Exception:
                    pass
    return None


def capturar(url: str, raw: Path, depth: int, passes: int,
             submit_optin: bool, email: str | None) -> dict:
    raw.mkdir(parents=True, exist_ok=True)
    (raw / "estados").mkdir(exist_ok=True)
    red: list[dict] = []
    resumen: dict = {"url": url, "pasos": [], "ab": None}

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context(viewport=DESKTOP, locale=LOCALE,
                                  timezone_id=TZ, user_agent=UA)

        ctx.on("request", lambda r: red.append({
            "url": r.url[:400], "type": r.resource_type, "method": r.method}))

        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=45000)
        _wait(page)

        # 1. ANTES de tocar el banner de cookies: así lo ve el visitante real,
        #    y neuromarketing necesita saber cuánto hero tapa.
        page.screenshot(path=str(raw / "viewport-precookies.png"))

        boton = _aceptar_cookies(page)
        resumen["cookie_banner"] = boton
        _wait(page)
        _scroll(page)

        # 2. Estado limpio, con consentimiento dado: muchos píxeles no disparan antes.
        page.screenshot(path=str(raw / "viewport.png"))
        page.screenshot(path=str(raw / "full.png"), full_page=True)
        (raw / "page.html").write_text(page.content(), encoding="utf-8")

        dump = page.evaluate(DUMP_JS)
        (raw / "elements.json").write_text(
            json.dumps(dump, ensure_ascii=False, indent=1), encoding="utf-8")

        # 3. Hojas de estilo, para el análisis determinista de tipografía y layout.
        css = page.evaluate("""() => Array.from(document.styleSheets).map(s => {
            try { return Array.from(s.cssRules).map(r => r.cssText).join('\\n'); }
            catch(e) { return '/* cross-origin: ' + (s.href||'') + ' */'; }
        }).join('\\n')""")
        (raw / "styles.css").write_text(css, encoding="utf-8")

        # 4. Móvil.
        mob = ctx.new_page()
        mob.set_viewport_size(MOBILE)
        mob.goto(url, wait_until="domcontentloaded", timeout=45000)
        _wait(mob); _aceptar_cookies(mob); _scroll(mob)
        mob.screenshot(path=str(raw / "mobile.png"), full_page=True)
        mob.close()

        # 5. Popups y modales que aparezcan solos (tiempo, scroll, salida).
        page.wait_for_timeout(6000)
        page.mouse.move(700, 0)  # provoca exit-intent
        page.wait_for_timeout(2500)
        overlays = page.evaluate("""() => Array.from(document.querySelectorAll('body *'))
            .filter(e => {
                const s = getComputedStyle(e), r = e.getBoundingClientRect();
                return (s.position==='fixed'||s.position==='sticky')
                    && r.width>200 && r.height>150 && +s.zIndex>50;
            }).map(e => (e.innerText||'').trim().slice(0,300)).filter(Boolean)""")
        if overlays:
            page.screenshot(path=str(raw / "estados" / "overlay.png"))
        resumen["overlays"] = overlays

        # 6. Storage y cookies: temporizadores falsos y asignación de variante A/B.
        storage = page.evaluate(STORAGE_JS)
        (raw / "network.json").write_text(json.dumps({
            "requests": red,
            "cookies": ctx.cookies(),
            "storage": storage,
        }, ensure_ascii=False, indent=1), encoding="utf-8")

        # 7. Pasadas extra con sesión limpia: si el HTML cambia, hay A/B activo.
        if passes > 1:
            firmas = [_firma(page.content())]
            for i in range(passes - 1):
                c2 = browser.new_context(viewport=DESKTOP, locale=LOCALE,
                                         timezone_id=TZ, user_agent=UA)
                p2 = c2.new_page()
                p2.goto(url, wait_until="domcontentloaded", timeout=45000)
                _wait(p2)
                html = p2.content()
                firmas.append(_firma(html))
                (raw / "estados" / f"pasada-{i+2}.html").write_text(html, encoding="utf-8")
                c2.close()
            resumen["ab"] = {
                "firmas": firmas,
                "variantes_probables": len(set(firmas)) > 1,
                "metodo": "hash del texto visible, sin dígitos ni tokens volátiles",
            }

        # 8. Seguir el funnel: los CTA internos, hasta la profundidad pedida.
        vistos = {url}
        cola = [(url, 0)]
        while cola and depth > 0:
            actual, d = cola.pop(0)
            if d >= depth:
                continue
            for ln in dump["doc"]["links"]:
                nxt = ln["href"].split("#")[0]
                if ln["external"] or nxt in vistos or not nxt.startswith("http"):
                    continue
                vistos.add(nxt)
                try:
                    p3 = ctx.new_page()
                    p3.goto(nxt, wait_until="domcontentloaded", timeout=30000)
                    _wait(p3); _aceptar_cookies(p3); _scroll(p3)
                    nombre = re.sub(r"[^a-z0-9]+", "-", urlparse(nxt).path.lower()).strip("-") or "raiz"
                    p3.screenshot(path=str(raw / "estados" / f"paso-{nombre}.png"), full_page=True)
                    (raw / "estados" / f"paso-{nombre}.html").write_text(p3.content(), encoding="utf-8")
                    resumen["pasos"].append({"url": nxt, "nombre": nombre})
                    cola.append((nxt, d + 1))
                    p3.close()
                except Exception as e:
                    resumen["pasos"].append({"url": nxt, "error": str(e)[:120]})
                if len(resumen["pasos"]) >= 12:
                    break

        # 9. Opt-in. Solo con permiso explícito: envía datos a un sistema ajeno.
        if submit_optin:
            if not email:
                print("  ! --submit-optin sin --email: se omite", file=sys.stderr)
            else:
                try:
                    for f in page.query_selector_all("form"):
                        for i in f.query_selector_all("input"):
                            t = (i.get_attribute("type") or "text").lower()
                            if t == "email":
                                i.fill(email)
                            elif t in ("text", "tel") and i.is_visible():
                                i.fill("Prueba" if t == "text" else "3000000000")
                        f.evaluate("f => f.requestSubmit ? f.requestSubmit() : f.submit()")
                        page.wait_for_timeout(5000)
                        page.screenshot(path=str(raw / "estados" / "post-optin.png"), full_page=True)
                        (raw / "estados" / "post-optin.html").write_text(page.content(), encoding="utf-8")
                        resumen["optin"] = {"enviado": True, "url_final": page.url}
                        break
                except Exception as e:
                    resumen["optin"] = {"enviado": False, "error": str(e)[:200]}

        browser.close()

    (raw / "captura.json").write_text(
        json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8")
    return resumen


def main() -> None:
    ap = argparse.ArgumentParser(description="Captura un funnel a casos/<slug>/raw/")
    ap.add_argument("url", nargs="?")
    ap.add_argument("--slug")
    ap.add_argument("--depth", type=int, default=1, help="pasos internos a seguir (0 = solo la landing)")
    ap.add_argument("--passes", type=int, default=3, help="pasadas para detectar A/B")
    ap.add_argument("--submit-optin", action="store_true", help="rellena y envía el formulario")
    ap.add_argument("--email", help="correo a usar en el opt-in")
    ap.add_argument("--lote", help="archivo con una URL por línea")
    a = ap.parse_args()

    urls = []
    if a.lote:
        urls = [l.strip() for l in Path(a.lote).read_text(encoding="utf-8").splitlines()
                if l.strip() and not l.startswith("#")]
    elif a.url:
        urls = [a.url]
    else:
        ap.error("hace falta una URL o --lote")

    for u in urls:
        slug = a.slug if (a.slug and len(urls) == 1) else slugify(u)
        raw = Path("casos") / slug / "raw"
        print(f"→ {u}\n  destino: {raw}")
        r = capturar(u, raw, a.depth, a.passes, a.submit_optin, a.email)
        print(f"  banner cookies: {r.get('cookie_banner') or 'no había'}")
        print(f"  pasos seguidos: {len(r['pasos'])}")
        if r.get("ab"):
            print(f"  A/B probable:   {r['ab']['variantes_probables']}")
        print(f"  overlays:       {len(r.get('overlays') or [])}")


if __name__ == "__main__":
    main()
