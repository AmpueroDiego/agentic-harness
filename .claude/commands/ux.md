---
description: Revisión experta de UX/UI y accesibilidad de una pantalla de web-app con el agente ux-ui (mira la app viva, mide contraste y teclado, y propone cambios exactos). Modos auditar, deslop, accesibilidad y corregir.
argument-hint: [auditar|deslop|accesibilidad|corregir] <pantalla o flujo, ej. "panel central de la consola"> [--tab <id de pestaña abierta>]
---

# /ux

Pedido: $ARGUMENTS

Lanza el subagente **nombrado** `ux-ui` (`.claude/agents/ux-ui.md`, modelo Fable). Él revisa; **no implementa**. Lo que el responsable del repo apruebe se implementa con `/orquestar --en .worktrees/web-app--<slug> ...` usando la sección e) del reporte como plan (coder-web + tests), nunca editando en el chat.

## Modos

| Modo | Qué hace | Cuándo |
|---|---|---|
| `auditar` (por defecto) | Las 6 fases del agente sobre la pantalla o flujo: entorno vivo, walkthrough, inventario por zona, pulido, accesibilidad medida, robustez y principios | Una pantalla se ve cargada o confusa, o antes de cerrar un cambio visual grande |
| `deslop` | Solo busca ornamento sin función (bordes, tarjetas, badges, textos permanentes, colores, iconos de adorno) y propone quitarlo o colapsarlo, aplicando el paso 2 de `PRINCIPIOS-INGENIERIA-MINIMALISTA.md` | "Se ve cargado" y se quiere limpiar sin rediseñar |
| `accesibilidad` | Solo la fase 4 en profundidad en claro y oscuro: axe-core, contraste WCAG 2 + APCA de los pares de tokens, objetivos, teclado, foco, regiones vivas, forced-colors y movimiento reducido | Antes de un PR con cambios de UI, o cuando cambian tokens o temas |
| `corregir` | Toma los hallazgos que el responsable del repo aprobó de un reporte anterior y arma el plan para `/orquestar` (un coder-web por cambio independiente, en paralelo) | Después de un `auditar`, con la lista de números aprobados |

## Cómo lanzarlo

1. Si el responsable del repo tiene la consola abierta, pasa el `tabId` con `--tab` para que el agente trabaje sobre ella; recuérdale al agente que **no** puede enviar, guardar, crear, cerrar ni borrar nada en la app.
2. Prompt al agente: modo, pantalla o flujo, tema(s) a revisar, ancho(s) de ventana si el responsable del repo los indicó, y el foco del pedido con sus palabras.
3. Corre en segundo plano; mientras tanto no toques la pestaña que usa.

## Qué hacer con el reporte

- **Verifica 2–3 hallazgos al azar** contra la pantalla o el código antes de presentarlo (un agente de revisión también se equivoca).
- Preséntale al responsable del repo el diagnóstico, las victorias rápidas y los cambios estructurales **uno por uno en el orden del reporte**, con tu recomendación; que decida qué entra.
- Lo aprobado va a `corregir` → `/orquestar`. Lo que sea decisión de producto se registra en `TASKS.md` y, si aplica, en `contexto-negocio/web-app-DESIGN.md`.
- Si el agente propuso un borrador de `DESIGN.md`, se guarda recién cuando el responsable del repo lo apruebe.

## Herramientas

Usa lo que ya está conectado: claude-in-chrome (capturas, árbol accesible, `javascript_tool` para axe-core por CDN y medidas), y Figma MCP para tokens o para mandar una pantalla a Figma si el responsable del repo lo pide. Chrome DevTools MCP (Lighthouse y rendimiento) no está instalado; proponerlo solo si hace falta medir rendimiento, porque la máquina tiene poca memoria. Detalle en `contexto-negocio/ux-ui-herramientas-y-prompts.md`.
