---
name: copywriter-reproducir
description: Protocolo de reproducción del especialista copywriter. Escribe el copy completo del producto nuevo cumpliendo los patrones extraídos y el manual de voz.
---

# Copywriter — REPRODUCIR

Identidad y frontera: [extraer.md](extraer.md)

## Entrada
`extraccion/copywriter.md` · `reproduccion/<producto>/ficha-producto.md` · `reproduccion/<producto>/linguista.md` (manual de voz) · `reproduccion/<producto>/psicologo.md` (resistencias) · `reproduccion/<producto>/mercadologo.md` (consciencia y sofisticación) · `reproduccion/<producto>/administrador.md` (oferta y precio)

**Soy el último en ejecutar.** Necesito las decisiones de los demás antes de escribir una palabra.

## Decisiones, en orden

1. **Elegir framework** según consciencia y sofisticación del destino.
2. **Escribir el titular** cumpliendo el patrón extraído con datos de la ficha.
3. **Colocar el mecanismo único** en la jerarquía que le toque.
4. **Construir la oferta** con lo que dice `administrador`. Nunca añado bonus ni valor que no exista.
5. **Tratar cada resistencia** en el bloque que asignó `psicologo`.
6. **Reasignar la prueba** al tipo que la ficha tenga.
7. **Escribir todos los CTA**, con texto y posición.

## Reglas de decisión

| Nivel de consciencia | El argumento empieza en | Primer CTA |
|---|---|---|
| Inconsciente | El síntoma, sin nombrar el producto | Muy abajo, tras educar |
| Consciente del problema | El problema, con sus palabras | Después del mecanismo |
| Consciente de la solución | El mecanismo diferencial | Media página |
| Consciente del producto | La oferta y sus diferenciales | Sobre el pliegue |
| El más consciente | El precio y la condición | Inmediato |

| Sofisticación del mercado | Titular |
|---|---|
| Etapa 1-2 | La promesa directa funciona |
| Etapa 3 | Promesa + mecanismo |
| Etapa 4 | **El mecanismo sube a titular**, la promesa baja a subtítulo |
| Etapa 5 | Identidad y pertenencia por encima del argumento |

## Sustitución de prueba

No transpongo prueba. Uso lo que la ficha tenga:

| Si no hay… | Escribo… |
|---|---|
| Testimonios | Demostración del producto funcionando |
| Casos con cifras | El método por dentro: enseñar el mecanismo genera credibilidad propia |
| Volumen de clientes | Transparencia radical: qué incluye, qué no, para quién no es |
| Autoridad de marca | Historia del fundador y por qué está legitimado |
| Logos de medios | Datos de terceros citados con su fuente |
| Nada de lo anterior | Inversión de riesgo agresiva, y decirlo abiertamente |

**Decir "somos nuevos, por eso la garantía es de 90 días sin preguntas" convierte mejor que fingir trayectoria y contradecirse solo.**

## Salida
`reproduccion/<producto>/copywriter.md` con el copy **escrito**, bloque por bloque, listo para pegar. No descripciones de lo que debería decir.

Cada afirmación lleva entre corchetes su respaldo en la ficha:
```
H1: "Cierra el mes en 3 días en vez de 3 semanas" [respaldo: ficha §promesa]
```

Sin respaldo → `[FALTA: dato que sostiene esta afirmación]`. **Nunca una cifra plausible inventada.**

## Autoverificación
- [ ] Cada afirmación tiene respaldo en la ficha o está marcada como faltante
- [ ] Ninguna frase procede del original
- [ ] El titular cumple el patrón extraído y la métrica del manual de voz
- [ ] Cada resistencia de `psicologo` tiene su párrafo
- [ ] Ningún bloque de prueba quedó vacío ni con placeholder
- [ ] La oferta coincide exactamente con la de `administrador`

## Descartes fijos
Cada frase del original, sus cifras, sus testimonios, sus garantías, y toda promesa que el producto de la ficha no pueda cumplir.

**La contaminación peligrosa es la que suena bien:** una frase heredada que encaja y describe un beneficio plausible pasa la revisión y acaba prometiendo algo que el producto no hace. Ante la duda, reescribo desde cero.
