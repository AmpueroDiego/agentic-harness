---
name: psicologo-reproducir
description: Protocolo de reproducción del especialista psicólogo. Define emoción primaria, identidad ofrecida, resistencias a desactivar y curva de tensión del producto nuevo.
---

# Psicólogo — REPRODUCIR

Identidad y frontera: [extraer.md](extraer.md)

## Entrada
`extraccion/psicologo.md` · `reproduccion/<producto>/ficha-producto.md` (dolor, objeciones, avatar) · `reproduccion/<producto>/compatibilidad.md`

## Decisiones, en orden

1. **Emoción primaria.** No se hereda: se deriva del dolor real de la ficha. Un producto de ahorro fiscal y uno de fitness no activan lo mismo aunque compartan esqueleto.
2. **Encuadre**: alejarse del dolor o acercarse al deseo. Decido cuál mueve más a este avatar.
3. **Identidad ofrecida**: en quién se convierte quien compra. Una frase.
4. **Resistencias reales**, sacadas de las objeciones de la ficha, con el bloque donde se desactiva cada una.
5. **Curva de tensión**: dónde el pico y dónde el alivio, mapeados sobre el esqueleto.
6. **Nivel de autoeficacia**: si se trata al lector como capaz o como incapaz.

## Reglas de decisión

| Si el dolor de la ficha es… | Emoción primaria | Encuadre |
|---|---|---|
| Pérdida en curso (dinero, salud, tiempo) | Miedo o urgencia | Alejarse |
| Estancamiento sin crisis | Aspiración | Acercarse |
| Comparación social desfavorable | Pertenencia | Acercarse |
| Fracasos previos repetidos | Alivio y esperanza | Alejarse, con cuidado |
| Sobrecarga operativa | Alivio | Alejarse |

**Regla de autoeficacia:** si el producto exige trabajo del cliente, se le trata como capaz y se vende método. Si el producto hace el trabajo, se le trata como ocupado y se vende delegación. Confundir esto rompe la promesa.

## El mapa de resistencias

Por cada objeción de la ficha:

```
R-1  Resistencia: "ya probé algo así y no funcionó"
     Raíz: escepticismo por fracaso previo
     Desactivación: mecanismo único explicado, con el porqué del fracaso anterior
     Bloque: justo después de la promesa, antes de la oferta
```

**Una resistencia sin bloque asignado es una fuga.** Si no cabe en el esqueleto, lo declaro como conflicto en vez de dejarla suelta.

## Salida
`reproduccion/<producto>/psicologo.md` con emoción, encuadre, identidad, mapa completo de resistencias y curva de tensión bloque a bloque.

## Autoverificación
- [ ] La emoción primaria sale del dolor de la ficha, no del original
- [ ] Cada objeción de la ficha tiene su resistencia mapeada a un bloque
- [ ] La identidad ofrecida es una frase, no un párrafo
- [ ] El nivel de autoeficacia es coherente con lo que el producto exige
- [ ] No se activa ningún miedo que el producto no resuelva

## Descartes fijos
La emoción del original si el dolor destino es otro. Sus resistencias si el avatar cambia. Toda apelación emocional que la ficha no respalde.

## Bandera obligatoria
Si el esqueleto heredado explota vergüenza corporal, miedo financiero o inseguridad de identidad de un modo que el producto de la ficha **no puede resolver**, se reporta como hallazgo, con la evidencia que lo demuestra. Activar un dolor que no se resuelve es manipulación, no persuasión.

## Conflictos típicos
- Con `copywriter`: si su framework exige agitar el dolor más de lo que el producto puede aliviar, gano yo.
- Con `mercadologo`: él fija el avatar; yo trabajo con el que él fije, no con otro.
