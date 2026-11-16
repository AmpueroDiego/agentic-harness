---
name: funnel-<slug>
description: Super-skill del funnel <slug>. Contiene el análisis de los 11 especialistas y permite reproducir su estructura para cualquier producto. Úsalo cuando el usuario quiera construir algo con la lógica de <slug>.
---

# Funnel <slug>

> Plantilla. El orquestador de extracción la rellena y la deja en `casos/<slug>/SKILL.md`.
> Todo lo que va entre `<…>` se sustituye. Nada de esto se escribe a mano.

## Qué es

<Tipo de interfaz, etapa del funnel, producto, avatar aparente, nicho. Tres o cuatro frases.>

**Extraído el:** <fecha>
**Origen:** <url>
**Grado de confianza:** <alto / medio / bajo — según lo completo que fuera el raw>

## Veredicto

<Un párrafo del orquestador: qué hace bien esto, qué hace mal, y para qué tipo de producto sirve como plantilla y para cuál no.>

## Esqueleto

| # | Bloque | Propósito | Notas |
|---|---|---|---|
| 1 | <tipo> | <qué trabajo hace> | <de qué especialista viene la observación> |

## Los patrones que lo hacen funcionar

<Los `PT-*` más potentes de las 11 extracciones. Patrón y por qué funciona. Nunca texto literal del original.>

| ID | Patrón | Por qué funciona |
|---|---|---|

## Contaminación

<Todos los `CT-*` consolidados. Esta lista es la checklist del barrido de reproducción: nada de aquí puede aparecer en un build.>

| ID | Elemento | Por qué no transfiere |
|---|---|---|

## Preguntas al producto destino

<Todas las `Q-*` deduplicadas y agrupadas. El orquestador de reproducción convierte esto en la ficha que se le pide al usuario.>

**Imprescindibles:**
- <…>

**Recomendadas:**
- <…>

## Perfil de compatibilidad del origen

Contra esto se compara cualquier producto destino, en los ocho ejes del paso 2 de `orquestador/reproducir.md`.

| Eje | Valor en el origen |
|---|---|
| Nivel de consciencia | <…> |
| Sofisticación del mercado | <etapa 1-5> |
| Ticket | <…> |
| Tipo de compra | <…> |
| Ciclo de decisión | <…> |
| Modelo de entrega | <…> |
| Riesgo percibido | <…> |

## Banderas

<Cualquier aviso de `psicologo`, `sociologo` o `growth-data`. Si está vacío, decirlo explícitamente.>

## Extracciones completas

| Especialista | Archivo |
|---|---|
| frontend | `extraccion/frontend.md` |
| disenador | `extraccion/disenador.md` |
| neuromarketing | `extraccion/neuromarketing.md` |
| psicologo | `extraccion/psicologo.md` |
| linguista | `extraccion/linguista.md` |
| copywriter | `extraccion/copywriter.md` |
| mercadologo | `extraccion/mercadologo.md` |
| sociologo | `extraccion/sociologo.md` |
| ingeniero-industrial | `extraccion/ingeniero-industrial.md` |
| administrador | `extraccion/administrador.md` |
| growth-data | `extraccion/growth-data.md` |

## Cómo reproducir esto

Invocar `orquestador/reproducir.md` con este `<slug>`. Pedirá la ficha del producto destino a partir de las preguntas de arriba, auditará compatibilidad y lanzará a los 11 especialistas en modo reproducir.
