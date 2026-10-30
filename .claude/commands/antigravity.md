---
tipo: comando
tags: [sistema-multiagente]
description: Lo visual con el CLI de Antigravity (Gemini) — como revisor mira cómo se ve el resultado de un diff que toca UI, y como coder hace los cambios de estilo dentro del reparto de un coder por motor.
argument-hint: <ruta del worktree o repo> [rango de commits o "sin commitear"] [foco opcional]
---

# /antigravity

Tercer revisor, con un motor de otra casa. El responsable tiene el CLI instalado como **`agy`** (`<ruta-agy>/agy.exe`) y tiene modo sin interfaz, así que se puede orquestar igual que `/codex`.

**Su posición en el equipo es lo visual, en dos papeles.** Como revisor mira cómo se ve el resultado; también escribe los cambios de estilo (ver "Antigravity como coder" abajo). QA, `adversary` y Codex miran corrección; ninguno se pregunta si la pantalla quedó bien. Nació porque fue el único de cuatro revisores que notó que una limpieza de estilos había dejado un badge sin forma.

## Cuándo usarlo

- **El diff toca UI**: estilos, layout, componentes, tokens de tema, cualquier cosa que cambie lo que el agente ve.
- **Después de un cambio grande de estilos**, que es justo cuando se pierden cosas sin que ningún test se entere.
- **No** como primera opción para lógica de negocio, migraciones ni contratos de API: en un diff de backend puro acertó 3 de 7 hallazgos (ver "Segunda prueba" más abajo), y esa tasa todavía no lo justifica.

## Cómo lanzarlo

```bash
agy --model gemini-3.8-flash-high --effort high --mode plan --print="$(cat <prompt+diff>.txt)"
```

Cuatro trampas del CLI, las cuatro verificadas a los golpes:

1. **El prompt va pegado al flag** (`--print="..."`) y `--model` va **antes**. Si el prompt se pasa suelto al final, el CLI toma `--model` como el prompt, ignora el resto y **sale con código 0** — parece que funcionó y no revisó nada.
2. **`--mode plan`** es el modo revisor: razona sin tocar archivos. Sin eso puede intentar editar.
3. **El diff va dentro del prompt**, no como archivo en el worktree. Un archivo suelto ahí ensucia el `git status` de la corrida y se puede colar en un commit.
4. **En modo headless no puede pedir permisos, y sin ellos no produce NADA**. Su `settings.json` (`~/.gemini/antigravity-cli/settings.json`) guarda una lista de **comandos exactos** aprobados uno por uno en sesiones interactivas. Si necesita uno que no está en esa lista, en headless no hay a quién preguntarle: se auto-deniega, imprime `jetski: no output produced — a tool required the "command" permission...` y **sale con código 0**. Pasa aunque el prompt no requiera leer archivos (el permiso lo necesita para algo interno). La salida que funcionó: agregar `--dangerously-skip-permissions`, que en `--mode plan` es aceptable porque ese modo no edita archivos — pero **es un flag de auto-aprobar todo y se pide antes de usarlo**, no se asume. La alternativa sin ese flag es agregar la `allow-rule` en su `settings.json`, pero el error no dice qué comando quiere, así que hay que descubrirlo corriéndolo interactivo una vez.

Otras opciones útiles: `--json-schema` fuerza salida estructurada (severidad, archivo, línea) en vez de prosa — vale cuando el reporte se va a procesar en vez de leer; `--add-dir` acota el workspace; `agy models` lista los modelos disponibles.

## El patrón que comparten los tres motores externos

En una sola sesión fallaron tres veces, de tres formas distintas, **y las tres salieron con código de salida 0**:

| Motor | Falla | Qué imprime |
|---|---|---|
| Codex | Sin créditos | `ERROR: Your workspace is out of credits` |
| Codex | Su sandbox le bloquea `NuGet.Config`, no puede compilar ni testear | Lo reporta honestamente en su propio informe |
| Antigravity | Headless sin permisos | `jetski: no output produced — a tool required the "command" permission...` |

**La regla, entonces: ningún motor externo se da por corrido sin leer su salida.** El código de salida no sirve para nada acá — un orquestador que se fía de él reporta una revisión que nunca ocurrió, que es peor que no haberla corrido, porque nadie va a volver a mirar.

## Modelos

`agy models` al 2026-09-15: `gemini-3.1-pro-high/low`, `gemini-3.8/3.7/3.6-flash-high/medium/low`, `claude-sonnet-4-6`, `claude-opus-4-6-thinking`, `gpt-oss-120b-medium`.

**Usar `gemini-3.8-flash-high`** *(2026-10-14: `gemini-3.1-pro` ya no aparece en `agy models`; Gemini 4 Argon solo con plan AI Ultra)*. El valor de este revisor es que sea de **otra familia**: pedirle Claude desde acá no aporta nada que el pipeline no tenga ya.

## Qué hacer con sus hallazgos

**Verificar cada uno antes de tocar nada.** No es desconfianza, es lo que pasó:

| Primera prueba (2026-09-15) | |
|---|---|
| Hallazgo real | **1** — el badge que quedó sin padding, radio ni borde tras una limpieza de estilos. **No lo vio nadie más** |
| Falsos positivos | **2** — afirmó que unos tokens no existían (existen, 4 definiciones cada uno) y que un contraste fallaba (mide 6,25:1 y 6,98:1) |
| Culpa del orquestador | **1** — "ausencia total de tests", porque se le pasó un diff que no los incluía |

**1 de 4.** Pero ese 1 era real y ningún otro motor lo encontró. Para un cambio visual, ese trueque conviene — siempre que cada hallazgo pase por un `grep` antes de convertirse en trabajo.

**Van tres muestras** (1 de 4, 3 de 7 fuera de lo visual, 7 de 9 en la corrida 0047). Si la tasa cae, hay que replantear si compensa. Anotar el resultado de cada uso acá mismo, para decidir con datos y no con impresiones.

**Segunda prueba como revisor fuera de lo visual (2026-09-22, corrida 0056):** **3 de 7 hallazgos reales** sobre un diff de backend puro — migraciones, contrato de API y lógica de mensajería, exactamente el terreno que esta skill dice evitar. Los 3 reales valían: dos no los tenía nadie (un campo que la API exigía y descartaba, y que la migración no tiene orden de despliegue seguro). Los otros 4: dos ciertos pero sin riesgo verificable contra la base, uno con el hecho bien y **la consecuencia inventada** ("bloquea el arranque de los pods" — ninguna API de este ecosistema auto-migra), y uno que era una decisión ya documentada en el código.

Lo más caro fue lo que **no** dijo: su única categoría con "sin hallazgos" era justo donde había un problema real, a veinte líneas del código que sí analizó. **El "sin hallazgos" de un revisor se verifica igual que sus hallazgos.**

## Lo que no hace

- No decide. Qué se corrige y qué se deja lo decidel responsable.
- No escribe lógica. Escribe solo cambios visuales y de estilo; la lógica con estado es de `coder-web`, y lo mecánico de [`/codex`](codex.md).

## Antigravity como coder

el responsable pidió repartir un coder de cada motor en paralelo (`/orquestar`, Step 3). A Antigravity le toca **lo visual y de estilo dentro de componentes**: clases, tokens, jerarquía, pasadas de color.

```bash
cd <worktree> && agy --model gemini-3.8-flash-high --effort high --mode accept-edits --print="$(cat <tarea>.md)"
```

- `--mode accept-edits` es el modo que escribe archivos, verificado en `agy --help`. `--mode plan` sigue siendo el de revisor.
- Mismas condiciones que un coder propio: **archivos con dueño exclusivo**, el prompt nombra los prohibidos, criterio verificable ("que no quede ninguna clase `app-violet` en estos archivos"), y su diff se contrasta contra `git status`.
- La tarea va desde un `.md` del scratchpad pegado al flag, por la trampa del prompt suelto descrita arriba.
- **Verificación con permisos acotados**: en modo sin interfaz no puede pedir permiso para correr comandos y se los niega solo. En `~/.gemini/antigravity-cli/settings.json` (`permissions.allow`) están habilitados **solo** estos tres, que se comparan exactos: `npx tsc -b`, `npm run lint` y `npx vitest run`. La tarea le tiene que pedir verificar **con esos comandos literales** (proyecto completo, no por archivo). Nunca usar `--dangerously-skip-permissions`.
- **Primera prueba como coder (2026-09-16, corrida 0047):** aplicó bien los 3 cambios de estilo en `CaseActions.tsx` y `WorkspaceTabs.tsx` respetando su alcance. No pudo verificar porque todavía no tenía las reglas de permiso; lo verificó el orquestador (`eslint` limpio, 15/15 tests). Como revisor visual en la misma corrida: **7 de 9 hallazgos reales**, frente a 1 de 4 en la primera prueba.
- No reemplaza a `qa` ni a `adversary`: mira otra cosa.

## Relacionado

- [`/codex`](codex.md) — el otro revisor externo, que además puede escribir código.
- [`/ux`](ux.md) — el agente `ux-ui`, que audita la app **viva** en Chrome con axe y mediciones reales. Antigravity revisa un diff; `/ux` revisa la pantalla. No se pisan.
- [`orquestar.md`](orquestar.md) Step 4 — dónde encaja en el pipeline.
