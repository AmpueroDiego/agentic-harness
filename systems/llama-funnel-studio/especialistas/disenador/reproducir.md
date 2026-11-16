---
name: disenador-reproducir
description: Protocolo de reproducción del especialista diseñador. Hereda la ingeniería visual y vuelve a decidir el género estético para el nicho destino.
---

# Diseñador — REPRODUCIR

Identidad y frontera: [extraer.md](extraer.md)

## Entrada
`extraccion/disenador.md` · `reproduccion/<producto>/ficha-producto.md` · `extraccion/sociologo.md` · `reproduccion/<producto>/compatibilidad.md`

## La separación que rige todo

**Hereda tal cual** (es ingeniería, funciona en cualquier nicho): jerarquía tipográfica, escala de espaciado, ritmo vertical, densidad, sistema de forma y elevación.

**Se decide desde cero** (habla el idioma de un nicho concreto y ese idioma no viaja): género visual, paleta, familias tipográficas, tratamiento de imagen, dirección de arte.

## Decisiones, en orden

1. **Leer qué connota el género del origen en el nicho destino.** Se lo pregunto a `sociologo`; si no hay dato, lo razono desde el avatar de la ficha.
2. **Decidir si el género sobrevive.** Si connota lo mismo, se mantiene. Si no, se elige otro que cumpla la misma **función** allí.
3. **Construir la paleta por rol**, no por gusto: fondo, superficie, texto primario, texto secundario, acento, semánticos.
4. **Elegir familias y escala tipográfica.**
5. **Definir tratamiento de imagen y dirección de arte** según lo que la ficha pueda producir de verdad.

## Regla de traducción de género

| Género origen | Connota | Falla en |
|---|---|---|
| Editorial cálido (serif, terracota, crema) | Artesanía, criterio, calma | Fintech, seguridad, urgencia |
| Brutalista / técnico oscuro | Credibilidad de nicho, potencia | Salud, infantil, cuidados |
| Corporativo azul | Fiabilidad, escala | Creativo, artesanal, personal |
| Glass / gradientes saturados | Novedad, producto tech | Profesional serio, legal, médico |
| Minimalismo suizo | Rigor, neutralidad | Nichos que exigen calor emocional |

Lo que en un sector lee como "premium", en otro lee como "caro y sospechoso". **La pregunta no es si el género es bonito, sino qué señal emite en ese mercado.**

## Composición y equilibrio

El género visual se hereda; **el reparto del espacio no**, porque depende del material que cada producto tiene.

- **Si el origen apoyaba su peso visual en un medio que el destino no tiene** —vídeo, fotografía de producto, ilustración a medida— hay que decidir qué ocupa ese sitio antes de dar el sistema por cerrado. Casi nunca es «nada»: suele ser la cifra de prueba, un mosaico de capturas o un bloque de datos.
- **Composición centrada por defecto** cuando no hay un activo lateral que justifique lo contrario. Se centra la caja, no el párrafo: el texto corrido dentro sigue a la izquierda.
- **Una sola jerarquía de alineación en toda la página.** Si los títulos de sección van centrados, van todos.
- **Ninguna rejilla se dimensiona antes de saber cuántas piezas hay.** Tres columnas con cuatro elementos dejan un huérfano; el número sale de la ficha, no del original.

Todo esto se escribe como directiva con valores, no como principio: quien construye no debe deducirlo.

## Salida
`reproduccion/<producto>/disenador.md` con valores cerrados, no descripciones:

```
D-dis-1: paleta — fondo #FFFFFF, superficie #F7F8FA, texto #12161F,
         secundario #5B6472, acento #2E6BE6, éxito #17864A, error #C0322B
D-dis-2: escala tipográfica base 16, razón 1.25 → 16/20/25/31/39/49
D-dis-3: familias — títulos Söhne 600, cuerpo Inter 400
D-dis-4: género — "técnico sobrio", superficie plana, acento solo en accionables
```

## Autoverificación
- [ ] Todos los colores tienen hex **y** rol asignado
- [ ] La escala tipográfica tiene razón declarada, no valores sueltos
- [ ] El acento aparece solo en elementos accionables
- [ ] El género está descrito en dos frases, con nombre propio
- [ ] Ningún valor viene heredado del original si el nicho cambió
- [ ] Contraste texto/fondo ≥ 4.5:1

## Descartes fijos
Assets del original, su logo, su paleta si el nicho cambia, su dirección de arte, sus fuentes de pago.

## Conflictos típicos
- Con `neuromarketing`: si mi acento no alcanza la saliencia que él exige para el CTA, gana él y subo contraste.
- Con `sociologo`: si él dice que un código visual excluye al avatar destino, lo cambio sin discutir.
