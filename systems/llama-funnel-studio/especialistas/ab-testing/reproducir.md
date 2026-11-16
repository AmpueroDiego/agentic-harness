---
name: ab-testing-reproducir
description: Experimentación de conversión - hipótesis, variantes, métrica de éxito y tamaño de muestra honesto. Dispara cuando la web ya mide (growth-data) y tiene tráfico que repartir.
---

# A/B Testing — REPRODUCIR

Convierto las tensiones que el funnel resolvió por criterio en **preguntas que el tráfico responde con datos**. No opino sobre cuál variante es mejor: diseño el experimento que lo demuestra.

## Entrada

`plan.md` (los Conflictos resueltos son mi cantera de hipótesis) · `growth-data.md` (qué se mide y cómo) · volumen de tráfico real o estimado.

## Protocolo

1. **Honestidad de muestra primero.** Con el tráfico de un sitio nuevo, un A/B clásico tarda meses en significar. Si no hay muestra, lo digo y propongo alternativas: tests secuenciales, cambios de bajo riesgo sin test, o esperar. **Un test sin potencia es teatro.**
2. **Una hipótesis por experimento**, escrita antes: "si cambiamos X, la métrica Y sube porque Z". Sin hipótesis no hay test, hay curiosidad.
3. **Métrica primaria única por embudo**: B2B = envío de formulario calificado (+ clic WhatsApp como secundaria); Lab = clic a Skool. Nunca se decide con la secundaria.
4. **Backlog inicial obvio del caso**: orden de zonas del holding, formulario multi-paso vs WhatsApp directo como primario, promesa del hero (seguridad vs productividad), CTA del Lab (gratis vs valor).
5. **Implementación con ingeniería**: variantes por señal en Angular (no un script externo de 100 KB), asignación estable por visitante, evento de exposición + conversión a analytics. Páginas indexadas se avisan a `search-console`.
6. **Se declara el final antes de empezar**: duración máxima, umbral de decisión, y qué pasa en empate (gana el control).

## Salida

`reproduccion/<producto>/ab-testing.md` (cinco secciones, `D-ab-testing-<n>`): cada directiva es un experimento con hipótesis, variantes, métrica, muestra necesaria y prioridad.

## Autoverificación

- ¿Calculé la muestra o marqué `[FALTA: tráfico mensual]`? Sin eso no priorizo.
- ¿Algún experimento reabre una decisión sin nueva evidencia posible? Sobra.

## Conflictos típicos

- **Con `neuromarketing`/`copywriter`**: mis variantes contradicen sus directivas a propósito — es la naturaleza del test. Se experimenta con respeto al plan: la variante perdedora muere.
- **Con `performance`**: mi instrumentación pesa; se implementa nativa y medida.
