---
name: meta-snippets-reproducir
description: Titles, meta descriptions y Open Graph de cada página. El escaparate en la SERP - su métrica es el CTR. Dispara cuando keywords y el plan fijan las páginas.
---

# Meta-snippets — REPRODUCIR

Escribo el anuncio gratuito de cada página: `<title>`, `meta description` y Open Graph. No es un resumen: es **la promesa que gana el clic contra los otros nueve resultados**.

## Entrada

`keywords.md` (keyword primaria por página) · `plan.md` · `copywriter.md` (la promesa por bloque) · lista de rutas del blueprint.

## Protocolo

1. **Title ≤ 60 caracteres**: keyword primaria al inicio + gancho de valor + marca al final (`Detección de EPP con tus cámaras | Llama Solutions`). Único por página, nunca el H1 duplicado tal cual.
2. **Description 140-160 caracteres**: promesa + diferenciador + llamada suave. En el idioma y registro que fijó `linguista`. Sin keyword stuffing: Google la reescribe si no responde a la query.
3. **Plantillas parametrizadas para pSEO**: title y description con los mismos tokens `[Servicio]/[Geografía]/[Industria]` que la página, revisadas contra los peores casos de longitud (el nombre de industria más largo).
4. **Open Graph/Twitter**: `og:title` puede ser más emocional que el title; `og:image` 1200×630 por plantilla — si no hay imagen real, `[FALTA]`, no un placeholder feo que circule en compartidos.
5. **Nada de clickbait que la página no pague.** El CTR que rebota es peor que no ganar el clic.

## Salida

`reproduccion/<producto>/meta-snippets.md` con las cinco secciones. Directivas `D-meta-snippets-<n>`: una por página/plantilla con title y description finales listos para pegar.

## Autoverificación

- ¿Medí los caracteres de verdad, incluidos los casos parametrizados más largos?
- ¿Cada description dice algo que la página cumple?

## Conflictos típicos

- **Con `keywords`** si la primaria no cabe con naturalidad: se negocia una variante, no se sacrifica la legibilidad.
- **Con `copywriter`**: el title no es su H1; conviven con trabajos distintos (ganar el clic vs sostener la lectura).
