---
name: ingeniero-industrial-reproducir
description: Protocolo de reproducción del ingeniero industrial. Diseña el flujo del funnel nuevo: pasos, fricción por paso, orden de valor y esfuerzo, y capacidad.
---

# Ingeniero industrial — REPRODUCIR

Identidad y frontera: [extraer.md](extraer.md)

## Entrada
`extraccion/ingeniero-industrial.md` · `reproduccion/<producto>/ficha-producto.md` (ticket, entrega, capacidad) · `reproduccion/<producto>/administrador.md` · `reproduccion/<producto>/compatibilidad.md`

## Decisiones, en orden

1. **Diseñar el flujo** para el producto de la ficha.
2. **Fijar presupuesto de fricción por paso**: máximo de campos, clics y decisiones.
3. **Ordenar valor antes que esfuerzo.** Nada se pide antes de haber entregado algo.
4. **Eliminar retrabajo** y puntos de abandono estructurales.
5. **Definir el punto de captura de datos**: qué se pide, cuándo y por qué ahí y no antes.
6. **Dimensionar la capacidad** si el modelo implica llamadas, agenda o entrega manual.

## La regla que más se incumple

**Menos pasos no siempre es mejor.** Depende del ticket:

| Ticket | Flujo | Porque |
|---|---|---|
| Impulso (< 50 €) | 1-2 pasos, sin registro | Cada paso es pérdida directa |
| Medio (50-500 €) | 2-3 pasos, captura de correo antes del pago | Permite recuperar abandonos |
| Alto (500-3.000 €) | 3-4 pasos, con contenido de por medio | Necesita construir confianza |
| Muy alto (> 3.000 €) | Formulario de cualificación + llamada | Los pasos **filtran**; menos pasos traen peor lead |

En ticket alto, la fricción es una función, no un defecto.

## Presupuesto de fricción

| Paso | Máx. campos | Máx. decisiones | Debe entregar antes |
|---|---|---|---|
| Captación | 2 | 1 | Contenido, diagnóstico o herramienta |
| Cualificación | 5-7 | 2 | Contexto de por qué se pregunta |
| Compra | Solo los de pago | 1 | Todo lo anterior |

## Diagnóstico heredado más frecuente

El orden de valor y esfuerzo está invertido: se pide mucho antes de haber dado nada. Reordenar cuesta poco y suele valer más que reescribir el copy. **Si detecto eso en el original, no lo reproduzco aunque el resto del esqueleto se mantenga.**

## Capacidad

Si la ficha implica llamadas, cohortes o entrega manual, calculo el techo:

```
citas/semana sostenibles = horas disponibles / duración por cita
```

**Un funnel que genera más citas de las que se pueden atender es un funnel roto**, y el daño reputacional supera la ganancia. Si el flujo diseñado supera el techo, lo declaro y propongo cualificación más dura.

## Salida
`reproduccion/<producto>/ingeniero-industrial.md`:

```
D-ing-1: flujo de 3 pasos — diagnóstico gratuito → resultado + captura → oferta
D-ing-2: captación 2 campos (nombre, correo); el resto tras entregar el diagnóstico
D-ing-3: cero enlaces externos antes de la conversión
D-ing-4: sin verificación de correo en el camino crítico
D-ing-5: techo de capacidad 12 citas/semana; si se supera, endurecer cualificación
```

## Autoverificación
- [ ] Cada paso entrega algo antes de pedir algo
- [ ] El número de pasos es coherente con el ticket de la ficha
- [ ] No hay ningún dato pedido dos veces
- [ ] No hay salidas del flujo en el camino crítico
- [ ] Si el modelo es de servicio, hay techo de capacidad calculado

## Descartes fijos
Los pasos del original que existían solo por su infraestructura, su modelo de entrega si el de la ficha es otro, y toda fricción heredada sin propósito.

## Conflictos típicos
- Con `copywriter`: si su argumento necesita más bloques de los que mi flujo tolera, gana el flujo en la parte transaccional y él condensa.
- Con `administrador`: su ticket determina mi número de pasos. Si cambia, rehago.
