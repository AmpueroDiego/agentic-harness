# -*- coding: utf-8 -*-
"""Plantilla HTML del tablero de avance del HITO 1. La llama tablero-avance.py.

Una sola verdad (el responsable, 21/10): la unidad es la tarjeta de Trello y la fecha
sale del ritmo real de cierre. Sin horas del Excel a la vista.
Formato de lamina de informe: sin tarjetas ni sombras; la jerarquia la dan el
tamano, las lineas finas y el espacio.
"""

import html as _h


def esc(s):
    return _h.escape(str(s), quote=True)


def fecha(d):
    return d.strftime("%d/%m") if d else "—"


def tarjetas(n):
    return "1 tarjeta" if n == 1 else "%d tarjetas" % n


def desvio_txt(r):
    if r["desvio"] is None:
        return "sin ritmo medido"
    if r["desvio"] > 0:
        return "%d días hábiles tarde" % r["desvio"]
    if r["desvio"] < 0:
        return "%d días hábiles antes" % -r["desvio"]
    return "a tiempo"


def barra(pct):
    return '<span class="mini"><span style="width:%.1f%%"></span></span>' % pct


def detalle(r):
    """Abiertas por estado, solo las que existen."""
    partes = [("%d en revisión" % r["revision"]) if r["revision"] else "",
              ("%d en curso" % r["curso"]) if r["curso"] else "",
              ("%d por hacer" % r["pendiente"]) if r["pendiente"] else ""]
    return " · ".join(p for p in partes if p) or "nada abierto"


def html(d):
    fin1 = d["fin1"].strftime("%d/%m")
    total, reciente = d["ritmos"]
    hito = d["hito"]

    # Titular: el ritmo de todo el periodo; el de 2 semanas va debajo.
    if total["cierre"] is None:
        titulo, tono = "Cierre proyectado: sin ritmo medido todavía", "neutro"
    else:
        titulo = "Cierre proyectado: %s (%s)" % (fecha(total["cierre"]), desvio_txt(total))
        tono = "alerta" if total["desvio"] > 0 else "bien"
    bajada = ("<b>%s abiertas</b> del HITO 1 ÷ <b>%.1f tarjetas cerradas por día hábil</b> "
              "(%d llegaron a DEV o Terminado en %.1f días hábiles desde el 21/09)."
              % (tarjetas(hito["abiertas"]), total["ritmo"], total["n"], total["dias"]))
    if reciente["cierre"]:
        bajada += (" Al ritmo de las últimas 2 semanas (%.1f/día) cierra el %s, %s."
                   % (reciente["ritmo"], fecha(reciente["cierre"]), desvio_txt(reciente)))
    # Revision de Revisor Principal/Revisor Secundario = casi hecha; la del responsable sigue en curso (regla del 02/10).
    rev_responsable = sum(1 for u in d["en_curso"] if u["columna"] == "En revisión (el responsable)")
    casi = ("De las %d abiertas, <b>%d en revisión de Revisor Principal/Revisor Secundario</b> (casi hechas, no cuentan como terminadas)"
            % (hito["abiertas"], hito["revision"]))
    casi += ("; las %d en revisión del responsable siguen en curso." % rev_responsable) if rev_responsable else "."

    # Ritmo por semana: barras horizontales, escala al maximo.
    tope = max([s["n"] for s in d["semanas"]] + [1])
    semanas = "".join(
        '<div class="sem"><span class="sem-n">%s <i>%s</i></span><span class="sem-b">'
        '<span style="width:%.1f%%"></span></span><span class="sem-v mono">%d</span></div>'
        % (esc(s["label"]), esc(s["inicio"]), s["n"] / tope * 100, s["n"]) for s in d["semanas"])

    plan = d["plan_total"]
    filas = "".join("""
      <div class="ep">
        <span class="ep-n">%s</span>
        %s
        <span class="ep-v mono">%d/%d · %.0f%%</span>
        <span class="ep-d">%s</span>
      </div>""" % (esc(e["nombre"]), barra(e["pct"]), e["terminada"], e["total"], e["pct"],
                   esc(detalle(e))) for e in d["plan"])

    ex = d["extras"]
    n_st = len(d["sin_tarjeta"])
    sin_tarjeta = ("<p class=\"nota\">%s del Excel ya no %s en el tablero: no se %s.</p>"
                   % (tarjetas(n_st), "está" if n_st == 1 else "están", "cuenta" if n_st == 1 else "cuentan")
                   ) if n_st else ""

    # Para llegar al 30/10: tarjetas abiertas contra las que caben al ritmo real.
    margen = total["capacidad"] - hito["abiertas"]
    llegar = ("Al ritmo real caben <b>%.0f tarjetas</b> en los %.1f días hábiles que quedan "
              "(%.1f/día). Hay <b>%d abiertas</b>: %s."
              % (total["capacidad"], d["restantes"], total["ritmo"], hito["abiertas"],
                 ("sobra lugar para %.0f más" % margen) if margen >= 0
                 else ("faltan %.0f" % -margen)))
    return TEMPLATE % {
        "actualizado": esc(d["actualizado"]), "dia": d["dia"], "plan_dias": d["plan_dias"],
        "fin1": fin1, "titulo": esc(titulo), "tono": tono, "bajada": bajada, "casi": casi,
        "semanas": semanas,
        "plan_term": plan["terminada"], "plan_total": plan["total"], "plan_pct": plan["pct"],
        "filas": filas,
        "ex_term": ex["terminada"], "ex_total": ex["total"], "ex_pct": ex["pct"],
        "ex_barra": barra(ex["pct"]), "ex_det": esc(detalle(ex)),
        "sin_tarjeta": sin_tarjeta,
        "g_barra": barra(100.0),
        "llegar": llegar,
    }


TEMPLATE = u"""<title>Avance HITO 1 AcmeOrg</title>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Libre+Franklin:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
  :root {
    --papel: #ffffff; --fondo: #f1f0ed; --tinta: #101319; --tinta-2: #4a505b; --tinta-3: #64696f;
    --linea: #d9d7d2; --linea-2: #ecebe7;
    --azul: #0f4c81; --verde: #157f5c; --ambar: #b9741a; --gris: #cbc8c2;
  }
  @media (prefers-color-scheme: dark) {
    :root:not([data-theme="light"]) {
      --papel: #16181d; --fondo: #0d0f13; --tinta: #f0f1f3; --tinta-2: #b3b8c2; --tinta-3: #9aa0ab;
      --linea: #2c2f36; --linea-2: #23262c;
      --azul: #74aede; --verde: #35b98c; --ambar: #e0983f; --gris: #3c3f47;
    }
  }
  :root[data-theme="dark"] {
    --papel: #16181d; --fondo: #0d0f13; --tinta: #f0f1f3; --tinta-2: #b3b8c2; --tinta-3: #9aa0ab;
    --linea: #2c2f36; --linea-2: #23262c;
    --azul: #74aede; --verde: #35b98c; --ambar: #e0983f; --gris: #3c3f47;
  }
  body { background: var(--fondo); color: var(--tinta); margin: 0;
    font-family: "Libre Franklin", system-ui, sans-serif; line-height: 1.45; }
  .lamina { max-width: 1120px; margin: 0 auto; background: var(--papel); padding: 16px; padding-block: 44px; }
  @media (min-width: 900px) { .lamina { padding-inline: 60px; } }
  .mono { font-family: "IBM Plex Mono", monospace; font-variant-numeric: tabular-nums; }

  .kicker { font-family: "IBM Plex Mono", monospace; font-size: 12px; letter-spacing: 0.16em;
    text-transform: uppercase; color: var(--tinta-2); font-weight: 500; display: flex; justify-content: space-between;
    gap: 16px; flex-wrap: wrap; padding-bottom: 12px; border-bottom: 2px solid var(--tinta); }
  h1 { font-size: clamp(28px, 4.6vw, 44px); line-height: 1.08; letter-spacing: -0.8px;
    font-weight: 700; margin: 28px 0 12px; text-wrap: balance; }
  h1.bien { color: var(--verde); } h1.alerta { color: var(--ambar); } h1.neutro { color: var(--azul); }
  .bajada { color: var(--tinta-2); font-size: 16px; max-width: 70ch; margin: 0 0 8px; }
  .bajada b { color: var(--tinta); font-weight: 600; }

  h2 { font-size: 12px; letter-spacing: 0.16em; text-transform: uppercase; color: var(--tinta-2);
    font-weight: 600; margin: 0 0 18px; padding-bottom: 8px; border-bottom: 1px solid var(--linea);
    display: flex; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
  h2 .mono { letter-spacing: 0; text-transform: none; color: var(--tinta); }
  section { margin-bottom: 40px; }
  section:first-of-type { margin-top: 36px; }
  .nota { color: var(--tinta-2); font-size: 13px; margin: 10px 0 0; max-width: 80ch; }

  .sem { display: grid; grid-template-columns: 96px 1fr 40px; gap: 12px; align-items: center; margin-bottom: 8px; }
  .sem-n { font-size: 14px; font-weight: 500; color: var(--tinta-2); }
  .sem-n i { font-family: "IBM Plex Mono", monospace; font-style: normal; font-size: 11px; color: var(--tinta-3); }
  .sem-b { height: 14px; background: var(--linea-2); border-radius: 2px; }
  .sem-b span { display: block; height: 14px; background: var(--azul); border-radius: 2px; }
  .sem-v { text-align: right; font-size: 14px; }

  .ep { display: grid; grid-template-columns: 150px 1fr 120px; gap: 6px 16px; align-items: center;
    padding: 12px 0; border-bottom: 1px solid var(--linea-2); }
  .ep-n { font-weight: 600; }
  .ep-v { text-align: right; font-size: 14px; white-space: nowrap; }
  .ep-d { grid-column: 2 / 4; font-size: 12.5px; color: var(--tinta-3); }
  .mini { display: block; height: 8px; background: var(--linea-2); border-radius: 4px; }
  .mini span { display: block; height: 8px; background: var(--verde); border-radius: 4px; }

  .grande { font-family: "IBM Plex Mono", monospace; font-size: 30px; font-weight: 500;
    letter-spacing: -1px; margin: 0 0 10px; }
  .grande small { font-size: 14px; letter-spacing: 0; color: var(--tinta-2); font-family: "Libre Franklin", sans-serif; }
  .linea { margin: 10px 0 0; color: var(--tinta-2); }
  .linea b { color: var(--tinta); font-weight: 600; }

  a:focus-visible { outline: 2px solid var(--azul); outline-offset: 3px; }
  footer { border-top: 1px solid var(--linea); padding-top: 14px; font-size: 12.5px; color: var(--tinta-3); }
  @media (max-width: 620px) {
    .ep { grid-template-columns: 1fr auto; }
    .ep .mini { grid-column: 1 / 3; grid-row: 2; }
    .ep-d { grid-column: 1 / 3; }
    .sem { grid-template-columns: 84px 1fr 32px; gap: 8px; }
  }
</style>

<div class="lamina">
  <div class="kicker">
    <span>AcmeOrg &middot; HITO 1 &middot; cierre plan %(fin1)s</span>
    <span class="mono">d&iacute;a %(dia)s de %(plan_dias)s &middot; actualizado %(actualizado)s</span>
  </div>

  <h1 class="%(tono)s">%(titulo)s</h1>
  <p class="bajada">%(bajada)s</p>
  <p class="bajada">%(casi)s</p>

  <section>
    <h2><span>Tarjetas cerradas por semana</span></h2>
    %(semanas)s
  </section>

  <section>
    <h2><span>Plan original</span><span class="mono">%(plan_term)s de %(plan_total)s tarjetas &middot; %(plan_pct).0f%%</span></h2>
    %(filas)s
  </section>

  <section>
    <h2><span>Trabajo agregado (extras)</span><span class="mono">%(ex_term)s de %(ex_total)s tarjetas &middot; %(ex_pct).0f%%</span></h2>
    %(ex_barra)s
    <p class="linea">Abiertas: <b>%(ex_det)s</b>.</p>
    %(sin_tarjeta)s
  </section>

  <section>
    <!-- Gestion ya se consumio entera (el responsable, 21/10): 100 %%, no resta en la proyeccion. -->
    <h2><span>Gesti&oacute;n y cierre</span><span class="mono">consumido &middot; 100%%</span></h2>
    %(g_barra)s
  </section>

  <section>
    <h2><span>Para llegar al %(fin1)s</span></h2>
    <p class="linea">%(llegar)s</p>
  </section>


  <footer>M&eacute;todo: una tarjeta es la unidad. Terminada = DEV, Listo para PROD o Terminado; en revisi&oacute;n (Revisor Principal/Revisor Secundario) es casi hecha y sigue abierta.
  Ritmo = tarjetas que llegaron por primera vez a una columna terminada (fecha del movimiento en Trello) por d&iacute;a h&aacute;bil.
  Cierre = abiertas &divide; ritmo. No cuenta tarjetas que se agreguen despu&eacute;s ni el tama&ntilde;o de cada una.
  Fuera: &laquo;Backlog del Backlog&raquo; y tarjetas sin movimiento desde el 21/09.</footer>
</div>
"""
