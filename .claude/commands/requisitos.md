---
description: Redacta, confirma, versiona y marca obsoleto un REQ en la Biblioteca de requisitos (`requisitos/`) — la capa de specs de SDD. La IA redacta desde el chat, el responsable del repo confirma antes de que el REQ alimente el pipeline.
argument-hint: nuevo "<qué se decidió>" | confirmar REQ-NNNN | cambiar REQ-NNNN "<qué cambió>" | obsoleto REQ-NNNN "<por qué>" | listar [estado]
---

# /requisitos

Maneja los archivos `REQ-NNNN-slug.md` de `requisitos/` — el "qué y por qué" que la propuesta de SDD definió como capa de specs. Las reglas base (estados, formato EARS/Gherkin, dónde vive cada cosa) están en [`requisitos/README.md`](../../requisitos/README.md) — no las repitas acá, citalas. Si esta skill y el README dicen cosas distintas, manda el README.

**Esta skill no toca `/orquestar`.** Hoy ningún agente lee un REQ: el Step 0.8 (leer el REQ en vez de la prosa de `$ARGUMENTS`) es la etapa 2 de la propuesta, todavía sin construir — a propósito, según el principio 8 (automatizar al final), después de probar la biblioteca a mano. Esta skill solo gestiona los archivos.

`requisitos/` es local y está fuera de git (decisión del responsable del repo, 2026-09-16): no lo enlaces desde un PR ni una tarjeta del tablero.

## `/requisitos nuevo "<qué se decidió y por qué>"`

1. **Id siguiente**: buscar el máximo `REQ-NNNN` entre `requisitos/*.md` y `requisitos/propuestas/*.md` (incluye obsoletos — un id nunca se reusa) y sumar 1.
2. **Redactar sobre [`_plantilla-REQ.md`](../../requisitos/_plantilla-REQ.md)**, con la decisión real que se discutió en el chat, no una genérica:
   - **Enunciado**: qué se necesita y por qué, 2-3 líneas, sin solución técnica.
   - **Requisitos (EARS)**: cada uno como *siempre* (R1: "El sistema deberá…"), *evento* ("Cuando…, el sistema deberá…"), *estado* ("Mientras…") o *no deseado* ("Si…, entonces…") — el que corresponda, no fuerces las cuatro formas si no aplican.
   - **Criterios (Gherkin)**: un escenario por comportamiento observable, con id `REQ-NNNN/E1`, `E2`... Dado/Cuando/Entonces.
   - **Preguntas abiertas**: lo que quedó sin decidir en la conversación. Vacío si no hay.
   - **Cambios**: fila única, versión 1, fecha de hoy, "Versión inicial", quién lo decidió.
   - **Frontmatter**: `dueno` es el responsable del repo salvo que se diga otro; `origen` cita de dónde sale (ADR, fila de `TASKS.md`, la conversación misma); `modulo` los repos que toca; `adrs`/`prs`/`commits`/`trello`/`pantallas` vacíos si todavía no existen — no inventar valores.
3. **Mostrar el contenido completo en el chat y esperar aprobación** antes de escribir — un REQ va a dirigir trabajo de agentes más adelante, no se escribe a ciegas. (`estado: propuesto` ya marca que nadie lo aprobó todavía; esto es sobre el *contenido*, no sobre el estado.)
4. **Escribir** en `requisitos/propuestas/REQ-NNNN-slug.md`.
5. **Actualizar el índice** de `requisitos/README.md` (agregar la fila bajo "Todos en `propuestas/`, estado `propuesto`").

## `/requisitos confirmar REQ-NNNN`

El responsable del repo aprobó el borrador. 1) Mover el archivo de `requisitos/propuestas/` a `requisitos/` (raíz). 2) `estado: propuesto` → `confirmado` en el frontmatter. 3) Actualizar el índice del README: sacarlo de la lista de propuestos: si no existe todavía una sección de confirmados, crearla.

## `/requisitos cambiar REQ-NNNN "<qué cambió>"`

Un REQ **no se reescribe** — versiona. 1) Leer el REQ (en `propuestas/` o en la raíz). 2) Mostrar en el chat qué Requisito/Criterio cambia, antes/después. 3) Con aprobación: subir `version` en el frontmatter, editar las secciones afectadas, agregar una fila nueva en **Cambios** (versión, fecha de hoy, qué cambió, quién decidió). 4) Si el cambio es sustancial (cambia un escenario Gherkin existente, no solo agrega uno), revisar si algún PR/commit ya listado en el frontmatter quedó desalineado y decirlo.

Si esto se invoca **durante una corrida de `/orquestar`** que ya usó su cambio de spec permitido (tope de 1 por corrida, pieza (c) de la propuesta), avisar y no aplicar un segundo — eso es del orquestador, no de esta skill, pero la skill no lo ignora si se lo dicen.

## `/requisitos obsoleto REQ-NNNN "<por qué, y qué lo reemplaza si aplica>"`

Solo el responsable del repo decide esto (ver tabla de estados del README). 1) `estado: obsoleto`. 2) Fila nueva en **Cambios** explicando qué pasó y, si hay un REQ que lo reemplaza, enlazarlo (y viceversa: el reemplazo cita al obsoleto en su `origen` si no lo hace ya). 3) **No se borra** — cero eliminaciones, mismo criterio que el resto del repo. 4) En el README, sacarlo del índice activo sin borrar la línea (marcarla o moverla a una sección "Obsoletos").

## `/requisitos listar [estado]`

Recorre `requisitos/*.md` y `requisitos/propuestas/*.md`, arma una tabla id · título · estado · módulo. Con un estado como argumento (`propuesto`, `confirmado`, etc.), filtra.

## Relacionado

- [`contexto-negocio/propuesta-sdd-en-orquestar-2026-09.md`](../../contexto-negocio/propuesta-sdd-en-orquestar-2026-09.md) — la propuesta completa, incluida la etapa 2 (integración a `/orquestar`) todavía sin construir.
- [`requisitos/README.md`](../../requisitos/README.md) — estados, reglas de formato, índice vivo.
- [`orquestar.md`](orquestar.md) — donde algún día se engancha el Step 0.8. No lo toques desde acá sin que la propuesta lo apruebe explícitamente (necesita replay de tarea dorada primero).
