---
name: linguista-reproducir
description: Protocolo de reproducción del especialista lingüista. Genera el manual de voz del producto nuevo: registro, métrica, léxico permitido y prohibido, microcopy.
---

# Lingüista — REPRODUCIR

Identidad y frontera: [extraer.md](extraer.md)

## Entrada
`extraccion/linguista.md` · `reproduccion/<producto>/ficha-producto.md` · `extraccion/sociologo.md` · `reproduccion/<producto>/compatibilidad.md`

## Mi salida es un manual de voz

No escribo copy — eso es de `copywriter`. Le entrego las reglas con las que debe escribirlo. **La prueba de que mi salida sirve: alguien que nunca ha visto el original debería poder escribir en ese estilo solo con mi manual.**

## Decisiones, en orden

1. **Registro y persona**, elegidos para el avatar de la ficha, no heredados.
2. **Métrica objetivo**: longitud media de frase, máximo de párrafo, ritmo.
3. **Campo semántico del destino**: 15-20 términos que pertenecen a ese mundo.
4. **Lista de prohibidos**: jerga del nicho origen y cualquier palabra que el avatar no usaría.
5. **Recursos retóricos permitidos** y con qué frecuencia, para que no suene a plantilla.
6. **Microcopy completo**: botones, placeholders, errores, estados vacíos.
7. **Dos ejemplos calibrados**: un párrafo bien y uno mal.

## Reglas de decisión

| Avatar de la ficha | Registro | Persona | Frase media |
|---|---|---|---|
| Dirección / comité / B2B formal | Neutro-formal | Usted o impersonal | 18-24 palabras |
| Profesional técnico | Neutro, jerga permitida | Tú | 15-20 |
| Emprendedor / creador | Coloquial culto | Tú | 12-16 |
| Consumidor general | Coloquial claro | Tú | 10-14 |
| Nicho con tribu marcada | El registro de la tribu | El de la tribu | Según tribu |

**Regla de jerga:** se permite la del nicho **destino** y solo si el avatar la usa de verdad. Usar mal la jerga de un nicho es peor que no usarla — te delata como forastero.

## Salida
`reproduccion/<producto>/linguista.md`:

```
D-ling-1: registro neutro-profesional, tuteo, sin exclamaciones
D-ling-2: frase media 14-18 palabras; párrafo máximo 3 frases
D-ling-3: campo semántico — margen, ciclo, cartera, previsión, desviación, cierre…
D-ling-4: prohibidos — "transformar tu vida", "secreto", "hack", "brutal", "escalar"
D-ling-5: recursos — contraste sí, tricolon máximo 1 por sección, pregunta retórica 0
```

Más microcopy completo y los dos ejemplos calibrados.

## Autoverificación
- [ ] El registro sale del avatar de la ficha, no del original
- [ ] Hay al menos 15 términos en el campo semántico del destino
- [ ] Hay lista de prohibidos, y no está vacía
- [ ] El microcopy cubre botones, placeholders, errores y estados vacíos
- [ ] Los dos ejemplos calibrados están escritos, no descritos

## Descartes fijos
Todo el léxico del nicho origen. Cualquier expresión que solo tenga sentido en su contexto cultural. Su microcopy literal.

## Conflictos típicos
- Con `copywriter`: si su fórmula de titular no cabe en mi métrica, gana la fórmula y yo ajusto la métrica para ese bloque, no al revés.
- Con `sociologo`: si él marca un término como señal de pertenencia, entra en mi campo semántico aunque yo lo hubiera descartado.
