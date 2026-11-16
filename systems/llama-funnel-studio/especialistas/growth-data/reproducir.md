---
name: growth-data-reproducir
description: Protocolo de reproducción del especialista growth/data. Define el plan de medición, los píxeles necesarios, la captura de datos y el primer test a lanzar.
---

# Growth / Data — REPRODUCIR

Identidad y frontera: [extraer.md](extraer.md)

## Entrada
`extraccion/growth-data.md` · `reproduccion/<producto>/ficha-producto.md` (canales) · `reproduccion/<producto>/ingeniero-industrial.md` (el flujo) · `sintesis.md`

## Decisiones, en orden

1. **Plan de medición mínimo**: qué eventos hay que disparar y en qué punto exacto del flujo.
2. **Píxeles necesarios** según los canales que la ficha declare. Ni uno más.
3. **Campos ocultos** que debe capturar el formulario.
4. **Primer test a lanzar**, elegido a partir del punto más débil que detectaron los demás.
5. **Consentimiento y cookies**: los píxeles no cargan antes de aceptar.

## Plan de medición

Un evento por transición del flujo que definió `ingeniero-industrial`. Ni más ni menos:

| Momento | Evento | Para qué sirve |
|---|---|---|
| Carga | `page_view` | Denominador |
| Llegada al bloque de oferta | `view_offer` | Mide si el copy retiene |
| Envío del formulario | `lead` | Conversión de captación |
| Inicio del pago | `begin_checkout` | Aísla la fricción de pago |
| Compra | `purchase` (con valor) | Ingresos y optimización de campañas |

**Sin `view_offer` no se puede distinguir "no llegan" de "llegan y no convierten"**, que son problemas opuestos con soluciones opuestas. Es el evento que más gente olvida.

## Regla de píxeles

Uno por canal **que la ficha declare que va a usar**. Cada script de terceros es peso, riesgo de privacidad y una obligación de consentimiento más. Si la ficha no declara canales de pago, no se instala ningún píxel publicitario.

## Campos ocultos

Los que el negocio necesite segmentar de verdad:

```
utm_source, utm_medium, utm_campaign, utm_content
referrer, landing_page, first_touch_at
```

Y los propios del negocio si la ficha lo justifica: afiliado, segmento, origen de recomendación. **Cada campo oculto se justifica o no entra** — capturar datos sin uso es exposición sin beneficio.

## Primer test

No se propone al azar. Se elige donde los demás señalaron debilidad:

| Si el punto débil está en… | El primer test es sobre… |
|---|---|
| No llegan a la oferta | Titular y primer bloque |
| Llegan y no convierten | Oferta, precio o prueba |
| Abandonan el formulario | Número de campos y momento de captura |
| Convierten y no pagan | Fricción del checkout |

Un solo test a la vez, y con criterio de parada definido antes de lanzarlo.

## Salida
`reproduccion/<producto>/growth-data.md`:

```
D-gd-1: eventos page_view, view_offer, lead, begin_checkout, purchase(valor)
D-gd-2: píxeles — solo Meta (único canal declarado en la ficha)
D-gd-3: campos ocultos — utm_*, referrer, landing_page. Nada más
D-gd-4: primer test — titular, dos variantes, parada a 400 sesiones por rama
D-gd-5: banner de consentimiento previo a cualquier carga de píxel
```

## Autoverificación
- [ ] Hay un evento por transición del flujo, sin eventos huérfanos
- [ ] `view_offer` está presente
- [ ] Cada píxel corresponde a un canal declarado en la ficha
- [ ] Cada campo oculto tiene justificación escrita
- [ ] Los píxeles no cargan antes del consentimiento
- [ ] El primer test tiene criterio de parada definido

## Descartes fijos
Píxeles del original, sus IDs, sus herramientas y todo mecanismo que dependa de datos que el producto nuevo no tiene.

## Bandera obligatoria
Todo mecanismo fabricado que se proponga —temporizador que se reinicia, notificación de compra inventada, escasez sin inventario— se reporta como hallazgo, con la evidencia que lo demuestra. Yo detecto; él decide.
