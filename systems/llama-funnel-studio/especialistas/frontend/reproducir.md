---
name: frontend-reproducir
description: Protocolo de reproducción del especialista frontend. Convierte el esqueleto extraído en una implementación concreta para el producto nuevo.
---

# Frontend — REPRODUCIR

Identidad y frontera: [extraer.md](extraer.md)

## Entrada
`extraccion/frontend.md` · `reproduccion/<producto>/ficha-producto.md` · `reproduccion/<producto>/compatibilidad.md` · `sintesis.md`

## Decisiones, en orden

1. **Heredar la ingeniería.** Sistema de layout, escala de espaciado, breakpoints y anatomía de componentes transfieren enteros: son agnósticos al nicho.
2. **Ajustar el esqueleto** con los desajustes de la auditoría.
3. **Fijar los componentes** que necesita el build nuevo, con sus estados.
4. **Decidir la implementación**: HTML autocontenido, CSS en un solo `<style>`, sin dependencias externas, sin frameworks. Debe funcionar abriendo el archivo.

## Reglas de decisión

| Si la auditoría dice… | Entonces |
|---|---|
| Destino menos consciente | Insertar bloque de problema antes del hero; el primer CTA baja del pliegue |
| Destino más consciente | CTA dentro del primer viewport; eliminar bloques educativos |
| Ticket mucho mayor | Sustituir formulario de compra por agendado; añadir bloque de prueba extendida |
| Ticket mucho menor | Recortar secciones; una sola columna; menos de 5 bloques |
| Menos prueba disponible | El bloque de prueba social cambia de tipo, no se elimina (ver `copywriter`) |
| Grado de transposición 3 | Se conserva solo la escala de espaciado y el sistema de rejilla; el resto se rediseña |

## Composición: lo que nunca se hereda sin volver a decidirlo

Una decisión de maquetación que en el origen existía **por un activo que el destino no tiene** se vuelve a decidir. No es contaminación de contenido y por eso no la caza ningún barrido de texto: se hereda la estructura y queda un hueco donde antes había algo.

Los tres casos que se repiten:

1. **Hero a dos columnas.** Si el origen ponía el texto a la izquierda, casi siempre era porque tenía imagen o vídeo a la derecha. Sin ese activo, el texto alineado a un lado deja media pantalla muerta. **Se centra el bloque.**
2. **Galerías dimensionadas.** Una rejilla de tres columnas pensada para nueve piezas se ve rota con cuatro. El número de columnas se decide con el material real que declara la ficha, no copiando el del origen.
3. **Rejillas con huérfanos.** Cuatro tarjetas en tres columnas dejan una sola en la última fila. O se ajustan las columnas al número de piezas, o se usa `auto-fit` con `minmax`.

Reglas fijas de composición, independientes del origen:

- **Se centra la caja, nunca el párrafo.** Contenedor y bloque de texto con `margin: 0 auto`; el texto corrido dentro sigue alineado a la izquierda. Centrar líneas largas se ve simétrico y arruina la lectura, porque el ojo pierde dónde empieza cada renglón.
- **Dos anchos, no uno:** el contenedor exterior para rejillas y bloques anchos, y otro más estrecho para texto de lectura, que se fija por la medida en caracteres que pida `neuromarketing` y no por una fracción del primero.
- **Los títulos de sección, todos igual.** Centrados o todos a la izquierda, pero sin mezclar: media página con un criterio y media con otro se lee como descuido.
- **Rejillas en `fr` o `minmax`, jamás en píxeles fijos.** Es el defecto más común de los originales capturados y el que peor envejece.

## Salida
`reproduccion/<producto>/frontend.md` con el formato del contrato. Las directivas llevan números:

```
D-frontend-1: contenedor max-width 1140px, grid 12 col, gap 24px
D-frontend-2: breakpoint único a 768px; a partir de ahí una sola columna
D-frontend-3: botón primario 56px alto, padding 0 32px, radio 8px
```

## Autoverificación
- [ ] Cada directiva tiene un valor numérico o un nombre de propiedad concreto
- [ ] Ninguna directiva dice "moderno", "limpio" o "profesional"
- [ ] El esqueleto refleja los ajustes de la auditoría, no el orden del original
- [ ] No hay dependencias externas de ningún tipo

## Descartes fijos
Stack del original, sus assets, sus scripts de terceros, su marcado de plantilla, sus clases de framework.

## Conflictos típicos
- Con `disenador`: él define valores visuales, yo la implementación. Si su escala tipográfica no cabe en mi rejilla, lo declaro y decide el orquestador.
- Con `ingeniero-industrial`: si su flujo pide menos pasos de los que el esqueleto tiene bloques, gana él y yo recorto.
