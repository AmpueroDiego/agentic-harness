#!/usr/bin/env python3
"""
trackers.py — infraestructura invisible → alimenta a `growth-data`

Píxeles, analítica, grabación de sesión, herramientas de test A/B, CRM,
pasarelas, campos ocultos, cookies y temporizadores fabricados.
Cero modelo: todo son consultas sobre el HTML y la red capturada.

Es el analizador con mejor relación valor/esfuerzo del sistema: por sí solo
te dice en qué plataformas compra tráfico el competidor y qué está testeando.

    python -m tools.analyze.trackers <slug>
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter

from ._common import raw_de, escribir

# firma -> (categoría, nombre)
FIRMAS = {
    # píxeles publicitarios: dicen dónde compran tráfico
    "connect.facebook.net": ("pixel", "Meta"),
    "fbevents.js": ("pixel", "Meta"),
    "analytics.tiktok.com": ("pixel", "TikTok"),
    "googleads.g.doubleclick": ("pixel", "Google Ads"),
    "googleadservices": ("pixel", "Google Ads"),
    "snap.licdn.com": ("pixel", "LinkedIn"),
    "ct.pinterest.com": ("pixel", "Pinterest"),
    "static.ads-twitter.com": ("pixel", "X/Twitter"),
    "sc-static.net": ("pixel", "Snapchat"),
    "redditstatic.com/ads": ("pixel", "Reddit"),
    # analítica
    "googletagmanager.com/gtag": ("analitica", "GA4"),
    "google-analytics.com": ("analitica", "Google Analytics"),
    "googletagmanager.com/gtm": ("tag manager", "Google Tag Manager"),
    "cdn.segment.com": ("tag manager", "Segment"),
    "plausible.io": ("analitica", "Plausible"),
    "cdn.usefathom": ("analitica", "Fathom"),
    "cdn.mxpnl.com": ("analitica", "Mixpanel"),
    "amplitude.com": ("analitica", "Amplitude"),
    "posthog.com": ("analitica", "PostHog"),
    "heap.io": ("analitica", "Heap"),
    # grabación de sesión: si está, están optimizando activamente
    "static.hotjar.com": ("grabacion", "Hotjar"),
    "clarity.ms": ("grabacion", "Microsoft Clarity"),
    "fullstory.com": ("grabacion", "FullStory"),
    "luckyorange": ("grabacion", "Lucky Orange"),
    "smartlook": ("grabacion", "Smartlook"),
    # tests A/B
    "optimizely.com": ("test ab", "Optimizely"),
    "visualwebsiteoptimizer": ("test ab", "VWO"),
    "convertexperiments": ("test ab", "Convert"),
    "abtasty.com": ("test ab", "AB Tasty"),
    # pasarelas
    "js.stripe.com": ("pago", "Stripe"),
    "paypal.com/sdk": ("pago", "PayPal"),
    "paddle.com": ("pago", "Paddle"),
    "hotmart": ("pago", "Hotmart"),
    "thrivecart": ("pago", "ThriveCart"),
    "samcart": ("pago", "SamCart"),
    "mercadopago": ("pago", "Mercado Pago"),
    # CRM y correo
    "activehosted.com": ("crm", "ActiveCampaign"),
    "convertkit.com": ("crm", "ConvertKit"),
    "klaviyo.com": ("crm", "Klaviyo"),
    "mailchimp.com": ("crm", "Mailchimp"),
    "hs-scripts.com": ("crm", "HubSpot"),
    "gohighlevel": ("crm", "GoHighLevel"),
    # chat
    "intercom.io": ("chat", "Intercom"),
    "crisp.chat": ("chat", "Crisp"),
    "tawk.to": ("chat", "Tawk"),
    "manychat": ("chat", "ManyChat"),
    # prueba social y urgencia fabricadas
    "provesrc": ("prueba fabricada", "ProveSource"),
    "fomo.com": ("prueba fabricada", "Fomo"),
    "useproof": ("prueba fabricada", "Proof"),
    "deadlinefunnel": ("urgencia", "Deadline Funnel"),
    # constructores
    "framer.com": ("constructor", "Framer"),
    "webflow.com": ("constructor", "Webflow"),
    "wp-content": ("constructor", "WordPress"),
    "shopify": ("constructor", "Shopify"),
    "clickfunnels": ("constructor", "ClickFunnels"),
    "kajabi": ("constructor", "Kajabi"),
    # consentimiento
    "cookiebot": ("consentimiento", "Cookiebot"),
    "onetrust": ("consentimiento", "OneTrust"),
}

EVENTOS = ["PageView", "ViewContent", "Lead", "InitiateCheckout", "AddToCart",
           "AddPaymentInfo", "Purchase", "CompleteRegistration", "Subscribe",
           "begin_checkout", "generate_lead", "sign_up", "purchase"]

UTM = re.compile(r"utm_(source|medium|campaign|content|term)|gclid|fbclid|ttclid", re.I)


def analizar(raw) -> dict:
    html = (raw / "page.html").read_text(encoding="utf-8", errors="ignore")
    net = json.loads((raw / "network.json").read_text(encoding="utf-8"))
    urls = " ".join(r["url"] for r in net.get("requests", []))
    heno = html + " " + urls

    # --- detección de herramientas -------------------------------------------
    hallado: dict[str, set] = {}
    for firma, (cat, nombre) in FIRMAS.items():
        if firma.lower() in heno.lower():
            hallado.setdefault(cat, set()).add(nombre)
    detectado = {k: sorted(v) for k, v in sorted(hallado.items())}

    # --- eventos disparados ---------------------------------------------------
    eventos = sorted({e for e in EVENTOS if re.search(rf"['\"]{e}['\"]", heno)})

    # --- campos ocultos: el modelo de datos del negocio ----------------------
    ocultos = []
    try:
        dump = json.loads((raw / "elements.json").read_text(encoding="utf-8"))
        for f in dump["doc"].get("forms", []):
            for c in f.get("fields", []):
                if c.get("hidden"):
                    ocultos.append({"name": c.get("name"),
                                    "value": (c.get("value") or "")[:80]})
    except Exception:
        pass

    # --- cookies y almacenamiento --------------------------------------------
    cookies = net.get("cookies", [])
    dominios = Counter(c.get("domain", "") for c in cookies)
    storage = net.get("storage", {})
    claves_storage = sorted(list(storage.get("local", {}).keys())
                            + list(storage.get("session", {}).keys()))

    # Temporizadores en localStorage: si el plazo vive en el navegador,
    # se reinicia al limpiar cookies y la urgencia es inventada.
    sospechosas = [k for k in claves_storage
                   if re.search(r"(deadline|countdown|timer|expir|urgen|offer_end)", k, re.I)]

    # --- variantes A/B --------------------------------------------------------
    ab = None
    cap = raw / "captura.json"
    if cap.exists():
        ab = json.loads(cap.read_text(encoding="utf-8")).get("ab")

    # --- terceros -------------------------------------------------------------
    externos = Counter()
    for r in net.get("requests", []):
        m = re.match(r"https?://([^/]+)", r["url"])
        if m and "framer" not in m.group(1):
            externos[m.group(1)] += 1

    return {
        "herramientas": detectado,
        "eventos_detectados": eventos,
        "campos_ocultos": ocultos,
        "utm_capturado": bool(UTM.search(heno)),
        "cookies": {
            "n": len(cookies),
            "dominios": dict(dominios.most_common(10)),
            "terceros": sum(1 for c in cookies if c.get("domain", "").startswith(".")),
        },
        "storage": {
            "claves": claves_storage[:40],
            "posibles_temporizadores": sospechosas,
        },
        "test_ab": ab,
        "terceros_por_peticiones": dict(externos.most_common(15)),
        "lectura_rapida": {
            "compra_trafico_en": detectado.get("pixel", []),
            "optimiza_activamente": bool(detectado.get("grabacion") or detectado.get("test ab")),
            "urgencia_posiblemente_fabricada": bool(sospechosas or detectado.get("urgencia")),
            "prueba_social_posiblemente_fabricada": bool(detectado.get("prueba fabricada")),
        },
    }


def main() -> None:
    if len(sys.argv) < 2:
        raise SystemExit("uso: python -m tools.analyze.trackers <slug>")
    raw = raw_de(sys.argv[1])
    f = escribir(raw, "trackers", analizar(raw))
    print(f"trackers → {f}")


if __name__ == "__main__":
    main()
