---
name: administrador-reproducir
description: Protocolo de reproducción del administrador de empresas. Define precio, estructura de oferta, tiers, garantía dimensionada y coherencia entre ticket y estructura.
---

# Administrador de empresas — REPRODUCIR

Identidad y frontera: [extraer.md](extraer.md)

## Entrada
`extraccion/administrador.md` · `reproduccion/<producto>/ficha-producto.md` (oferta, precio, entrega, márgenes) · `reproduccion/<producto>/mercadologo.md`

## Decisiones, en orden

1. **Fijar precio** según la ficha. Nunca se hereda ni se deduce del original.
2. **Estructurar la oferta**: núcleo, bonus reales, garantía honrable.
3. **Arquitectura de tiers**, si aplica.
4. **Verificar coherencia ticket-estructura.** Mi aportación crítica.
5. **Situar la escalera de valor**: qué va antes y después.
6. **Dimensionar la garantía** al margen real.

## Coherencia ticket-estructura

Un impulso de 27 € y un alto valor de 5.000 € no comparten esqueleto. Si la ficha da un ticket muy distinto al del original, lo escalo como desajuste estructural **antes** de que nadie construya nada.

| Ticket | Cierre | Prueba necesaria | Objeciones a tratar | Longitud |
|---|---|---|---|---|
| < 50 € | Checkout directo | Mínima | 1-2 | Corta |
| 50-500 € | Checkout con garantía | Media: testimonios o demo | 3-4 | Media |
| 500-3.000 € | Checkout o llamada | Alta: casos con cifras | 5-7 | Larga |
| > 3.000 € | Llamada, nunca checkout | Muy alta + credenciales | 7+ | Muy larga o VSL |

## Garantía dimensionada

**Una garantía copiada puede quebrar el negocio.** Se dimensiona sobre el coste marginal real:

| Coste marginal | Garantía sostenible |
|---|---|
| Casi cero (digital) | 30-90 días, sin preguntas. Es el mejor argumento disponible |
| Medio (servicio, cohorte) | Condicionada a uso demostrable |
| Alto (físico, personalizado) | Devolución parcial o cambio, no reembolso completo |

## Regla de los bonus

Solo entra lo que existe de verdad. **El valor declarado del original casi nunca es real** — se extrajo como técnica de anclaje, no como dato económico, y no se replica inventando cifras. Si se usa anclaje, que sea contra el coste de la alternativa real (contratar a alguien, seguir perdiendo tiempo), que es verificable.

## Salida
`reproduccion/<producto>/administrador.md`:

```
D-adm-1: precio 149 €/mes, sin permanencia, cobro mensual
D-adm-2: núcleo = plataforma + soporte; bonus = plantillas (existen) e
         importación asistida (existe). Sin bonus inventados
D-adm-3: garantía 30 días completos — coste marginal cero, sostenible
D-adm-4: sin tiers en v1; un solo plan reduce la carga de decisión
D-adm-5: anclaje = coste de un analista junior (~2.000 €/mes), verificable
D-adm-6: ticket 149 € → cierre por checkout, prueba media, 3-4 objeciones,
         longitud media. Coherente con el esqueleto heredado
```

## Autoverificación
- [ ] El precio sale de la ficha
- [ ] Todos los bonus existen de verdad
- [ ] La garantía es sostenible según el coste marginal
- [ ] La estructura del esqueleto es coherente con el ticket (tabla de arriba)
- [ ] Si hay anclaje, es contra algo verificable, no contra un valor inventado

## Descartes fijos
El precio del original, sus bonus, su valor declarado, su garantía y su escalera de valor.

## Bandera obligatoria
Si la ficha promete una garantía que el modelo de entrega no sostiene, o un precio incoherente con el ticket que la estructura asume, va a Conflictos **antes** de que se construya nada. Es más barato pararlo aquí que rehacer el build.

## Conflictos típicos
- Con `mercadologo`: si mi precio implica un avatar distinto del que él fijó, gana él y yo reviso precio o él revisa avatar. Lo decide el orquestador.
- Con `copywriter`: la oferta que yo defina es la que él escribe. No añade nada.
