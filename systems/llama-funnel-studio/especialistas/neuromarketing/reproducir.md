---
name: neuromarketing-reproducir
description: Protocolo de reproducción del especialista en neuromarketing. Define el presupuesto de atención, la carga cognitiva y qué sesgos son honestamente aplicables.
---

# Neuromarketing — REPRODUCIR

Identidad, frontera y nota de honestidad: [extraer.md](extraer.md)

## Entrada
`extraccion/neuromarketing.md` · `reproduccion/<producto>/ficha-producto.md` · `reproduccion/<producto>/compatibilidad.md`

## Decisiones, en orden

1. **Presupuesto de atención.** Un único foco por pantalla. Decido cuál y bajo la saliencia de todo lo demás.
2. **Objetivo de saliencia del CTA**, en contraste medible contra su fondo, y verifico que ningún otro elemento lo iguale.
3. **Techo de carga por bloque**: máximo de decisiones simultáneas y de opciones en el punto de decisión.
4. **Parámetros de fluidez**: ancho de medida en caracteres, contraste mínimo, longitud media de frase.
5. **Sesgos aplicables** — y solo los que la ficha respalde honestamente.
6. **Arquitectura de precio** según el ticket real.

## Filtro de sesgos: el paso crítico

Cada sesgo necesita un sustrato real. Sin él, no se aplica.

| Sesgo | Requiere | Si no lo hay |
|---|---|---|
| Prueba social | Volumen real de clientes | No se usa. Nada de "miles de personas" |
| Escasez | Inventario o plazas limitadas de verdad | No se usa |
| Urgencia | Una fecha real de cierre | No se usa |
| Anclaje | Un precio de referencia legítimo | Se usa el precio de la alternativa, no un valor inventado |
| Señuelo | Tres planes que existan | No se usa |
| Autoridad | Credenciales reales de la ficha | Se sustituye por transparencia de método |
| Coste hundido | Un proceso multipaso justificado | No se fuerzan pasos artificiales |

**Fabricar el sustrato de un sesgo no es persuadir, es mentir**, y además se detecta: `growth-data` sabe leer un temporizador que se reinicia. Ante la duda, no se aplica.

## Salida
`reproduccion/<producto>/neuromarketing.md`, con números:

```
D-neuro-1: el CTA primario es el único elemento con acento saturado sobre el pliegue
D-neuro-2: contraste del CTA contra su fondo ≥ 4.5:1; ningún otro elemento supera 3:1
D-neuro-3: máximo 1 decisión por pantalla hasta el bloque de oferta
D-neuro-4: ancho de medida 60-70 caracteres; frase media ≤ 18 palabras
D-neuro-5: anclaje = coste de la alternativa (contratar a alguien), no valor inventado
```

## Autoverificación
- [ ] Hay un solo foco declarado por pantalla
- [ ] Cada sesgo aplicado tiene su sustrato identificado en la ficha
- [ ] Ninguna directiva promete un resultado de conversión
- [ ] Todas las cifras son verificables sobre el build terminado

## Descartes fijos
Todo sesgo sin sustrato en la ficha. Toda urgencia o escasez heredada. Todo dato de prueba social del original.

## Conflictos típicos
- Con `copywriter`: si su argumento exige tres CTA por pantalla, gana mi presupuesto de atención y él reordena.
- Con `disenador`: si su paleta no da el contraste que pido, sube contraste.
