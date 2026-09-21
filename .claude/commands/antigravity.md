---
description: Lo visual con el CLI de Antigravity (Gemini) — como revisor mira cómo se ve el resultado de un diff que toca UI, y como coder hace los cambios de estilo dentro del reparto de un coder por motor.
argument-hint: <ruta del worktree o repo> [rango de commits o "sin commitear"] [foco opcional]
---

# /antigravity

Tercer revisor, con un motor de otra casa. El responsable del repo tiene el CLI instalado como **`agy`** (`<ruta-a-agy>\agy.exe`) y tiene modo sin interfaz, así que se puede orquestar igual que `/codex`.

**Su posición en el equipo es lo visual, en dos papeles.** Como revisor mira cómo se ve el resultado; desde el 2026-09-16 también escribe los cambios de estilo (ver "Antigravity como coder" abajo). QA, `adversary` y Codex miran corrección; ninguno se pregunta si la pantalla quedó bien. Nació el 2026-09-15, cuando fue el único de cuatro revisores que notó que una limpieza de estilos había dejado un badge sin forma.

## Cuándo usarlo

- **El diff toca UI**: estilos, layout, componentes, tokens de tema, cualquier cosa que cambie lo que el agente ve.
- **Después de un cambio grande de estilos**, que es justo cuando se pierden cosas sin que ningún test se entere.
- **No** para lógica de negocio, migraciones ni interfaces de API: ahí no está probado y su tasa de acierto todavía no lo justifica.

## Cómo lanzarlo

```bash
agy --model gemini-3.1-pro-high --effort high --mode plan --print="$(cat <prompt+diff>.txt)"
```

Tres trampas del CLI, las tres verificadas a los golpes:

1. **El prompt va pegado al flag** (`--print="..."`) y `--model` va **antes**. Si el prompt se pasa suelto al final, el CLI toma `--model` como el prompt, ignora el resto y **sale con código 0** — parece que funcionó y no revisó nada.
2. **`--mode plan`** es el modo revisor: razona sin tocar archivos. Sin eso puede intentar editar.
3. **El diff va dentro del prompt**, no como archivo en el worktree. Un archivo suelto ahí ensucia el `git status` de la corrida y se puede colar en un commit.

Otras opciones útiles: `--json-schema` fuerza salida estructurada (severidad, archivo, línea) en vez de prosa — vale cuando el reporte se va a procesar en vez de leer; `--add-dir` acota el workspace; `agy models` lista los modelos disponibles.

## Modelos

`agy models` al 2026-09-15: `gemini-3.1-pro-high/low`, `gemini-3.8/3.7/3.6-flash-high/medium/low`, `claude-sonnet-4-6`, `claude-opus-4-6-thinking`, `gpt-oss-120b-medium`.

**Usar `gemini-3.1-pro-high`.** El valor de este revisor es que sea de **otra familia**: pedirle Claude desde acá no aporta nada que el pipeline no tenga ya.

## Qué hacer con sus hallazgos

**Verificar cada uno antes de tocar nada.** No es desconfianza, es lo que pasó:

| Primera prueba (2026-09-15) | |
|---|---|
| Hallazgo real | **1** — el badge que quedó sin padding, radio ni borde tras una limpieza de estilos. **No lo vio nadie más** |
| Falsos positivos | **2** — afirmó que unos tokens no existían (existen, 4 definiciones cada uno) y que un contraste fallaba (mide 6,25:1 y 6,98:1) |
| Culpa del orquestador | **1** — "ausencia total de tests", porque se le pasó un diff que no los incluía |

**1 de 4.** Pero ese 1 era real y ningún otro motor lo encontró. Para un cambio visual, ese trueque conviene — siempre que cada hallazgo pase por un `grep` antes de convertirse en trabajo.

**Es una sola muestra.** Si en las próximas corridas la tasa no mejora, hay que replantear si compensa. Anotar el resultado de cada uso acá mismo, para decidir con datos y no con impresiones.

## Lo que no hace

- No decide. Qué se corrige y qué se deja lo decide el responsable del repo.
- No escribe lógica. Escribe solo cambios visuales y de estilo; la lógica con estado es de `coder-web`, y lo mecánico de [`/codex`](codex.md).

## Antigravity como coder *(agregado 2026-09-16)*

El responsable del repo pidió repartir un coder de cada motor en paralelo (`/orquestar`, Step 3). A Antigravity le toca **lo visual y de estilo dentro de componentes**: clases, tokens, jerarquía, pasadas de color.

```bash
cd <worktree> && agy --model gemini-3.1-pro-high --effort high --mode accept-edits --print="$(cat <tarea>.md)"
```

- `--mode accept-edits` es el modo que escribe archivos, verificado en `agy --help` el 2026-09-16. `--mode plan` sigue siendo el de revisor.
- Mismas condiciones que un coder propio: **archivos con dueño exclusivo**, el prompt nombra los prohibidos, criterio verificable ("que no quede ninguna clase `crm-violet` en estos archivos"), y su diff se contrasta contra `git status`.
- La tarea va desde un `.md` del scratchpad pegado al flag, por la trampa del prompt suelto descrita arriba.
- **Verificación con permisos acotados** *(2026-09-16)*: en modo sin interfaz no puede pedir permiso para correr comandos y se los niega solo. En `~/.gemini/antigravity-cli/settings.json` (`permissions.allow`) están habilitados **solo** estos tres, que se comparan exactos: `npx tsc -b`, `npm run lint` y `npx vitest run`. La tarea le tiene que pedir verificar **con esos comandos literales** (proyecto completo, no por archivo). Nunca usar `--dangerously-skip-permissions`.
- **Primera prueba como coder (2026-09-16, corrida 0047):** aplicó bien los 3 cambios de estilo en `CaseActions.tsx` y `WorkspaceTabs.tsx` respetando su alcance. No pudo verificar porque todavía no tenía las reglas de permiso; lo verificó el orquestador (`eslint` limpio, 15/15 tests). Como revisor visual en la misma corrida: **7 de 9 hallazgos reales**, frente a 1 de 4 en la primera prueba.
- No reemplaza a `qa` ni a `adversary`: mira otra cosa.

## Relacionado

- [`/codex`](codex.md) — el otro revisor externo, que además puede escribir código.
- [`/ux`](ux.md) — el agente `ux-ui`, que audita la app **viva** en Chrome con axe y mediciones reales. Antigravity revisa un diff; `/ux` revisa la pantalla. No se pisan.
- [`orquestar.md`](orquestar.md) Step 4 — dónde encaja en el pipeline.
