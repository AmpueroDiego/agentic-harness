---
name: performance-reproducir
description: Velocidad como característica del producto - Core Web Vitals, presupuestos de bundle, imágenes, hydration. Audita el build de ingeniería y fija budgets que el CI hace cumplir.
---

# Performance — REPRODUCIR

La velocidad no es una optimización posterior: es un presupuesto que se fija antes y **el CI hace cumplir**. Un sitio B2B lento le cuesta la primera impresión al decisor; uno móvil lento pierde al avatar de la comunidad.

## Entrada

El workspace `web/` · el blueprint de `arquitecto-angular` · los CWV de campo que reporte `search-console` cuando existan.

## Protocolo

1. **Presupuestos primero** (en `angular.json` y CI): initial bundle ≤ 250 KB comprimido por ruta, CSS crítico inline ≤ 20 KB, LCP < 2.5 s, INP < 200 ms, CLS < 0.1 en móvil de gama media.
2. **Imágenes**: `NgOptimizedImage` siempre; AVIF/WebP con fallback; `priority` solo en el LCP real de cada ruta; dimensiones explícitas (CLS).
3. **Fuentes**: subset de Inter autoalojado, `font-display: swap`, preload solo del peso del H1. Nada de Google Fonts en runtime.
4. **JS**: lazy por ruta, defer de lo no crítico, cero librerías para lo que la plataforma ya hace. Cada dependencia nueva justifica sus KB en el PR.
5. **Efectos del manual con coste**: `backdrop-filter` y glows se auditan en un móvil real/emulado; si un efecto tira el INP, se degrada con `@supports`/`prefers-reduced-motion`, no se elimina el diseño.
6. **Medir, no suponer**: Lighthouse CI en el pipeline con umbrales; lo de campo manda sobre lo de laboratorio.

## Salida

`reproduccion/<producto>/performance.md` (cinco secciones, `D-performance-<n>`), cada directiva con métrica, umbral y archivo donde se aplica.

## Autoverificación

- ¿Cada directiva tiene número verificable? "Optimizar imágenes" no es una directiva.
- ¿Rompí algo visual del funnel para ganar milisegundos? Va a Conflictos, no se decide solo.

## Conflictos típicos

- **Con `disenador`** por efectos caros: se propone la degradación elegante, decide el orquestador.
- **Con `ab-testing`**: los scripts de experimentación son de lo más pesado que existe; su carga va condicionada y medida.
