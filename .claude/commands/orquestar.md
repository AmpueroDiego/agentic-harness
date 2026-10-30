---
description: Runs the architect→planner→coder|coder-web→qa pipeline for a task in api-core (or web-app), then integration tests + adversary + security-review in parallel, with bounded QA and adversary retry loops.
argument-hint: [--en .worktrees/<repo>--<slug>] [--modo ahorro|normal|calidad] [--manejo eco|sport|blindado|auto] <descripción de la tarea o feature a implementar>
---

Actuás como orquestador del pipeline multiagente. La tarea es: $ARGUMENTS

**Este archivo conserva las reglas y sus detalles completos.** El detalle de cada paso vive en secciones enlazadas que se leen **solo al llegar a ese paso**: [detalle de coders](#detalle-coders) (Step 3), [detalle de gates](#detalle-gates) (Step 4 a 4.7), [detalle de registro](#detalle-registro) (Step 5). El porqué de cada regla (fechas, corridas, incidentes) está en [historia del proceso](#historia-del-proceso); se consulta con `grep -n`, nunca entero.

## Reglas de base

- **Repo destino**: `api-core` salvo que la tarea nombre otro. `git`, `dotnet`, `npm` corren en la carpeta del repo destino. **Excepción**: run docs (`INDEX.md`, `RETRO-LOG.md`, `GOLDEN-TASKS.md`, `SYSTEM-AUDIT-LOG.md`) y ADRs viven en `AcmeOrg/docs/runs/` y `AcmeOrg/docs/adr/`.
- **`--en .worktrees/<repo>--<slug>`**: esa carpeta es `<RAIZ>` para todo (`git`, build, tests, diff de los gates); cada ruta `api-core/...` se lee como `<RAIZ>/...`. Los repos de referencia y los run docs/ADRs no se mueven. Con `--en` **no se sube la rama ni se abre PR, ni se ofrece**: la corrida termina en el commit del Step 4.5 + Step 5, y sigue con `/worktree sincronizar`.
- **El cwd del orquestador lo hereda el subagente.** Antes de lanzar un agente, `cd <RAIZ>` o verificar que coincida. Cada prompt a `architect`, `planner`, `coder`, `coder-web`, `qa` y `adversary` empieza, literal, con:
  `Raíz de trabajo: <RAIZ> (rama <rama>). **Verificá por ruta absoluta que estás ahí antes de tocar un solo archivo; si tu directorio inicial no coincide, usá la ruta absoluta igual y decilo en tu reporte.** Todo archivo del repo destino que leas, edites, compiles o diffees va bajo esa ruta; la carpeta principal del repo no se toca.`
- **Hand-offs estructurados**, pasados **textuales** al siguiente agente: `## Architect Report`, `## Plan`, `## Coder Report` (`coder` y `coder-web`), `## QA Verdict`, `## Adversarial Audit Report`. `qa` y `adversary` cierran con `### Result: <PASS | FINDINGS>`. Un hand-off mal formado es un hallazgo: pedir que lo reformatee. Dos agentes nunca hablan directo.
- **Lecturas grandes siempre por el shunt, sin excepciones** (desde 2026-09-23): archivo de más de 350 líneas → `bulk-read.sh` o `grep -n` + `Read` con `offset`/`limit`; salida grande de Trello o GitHub → `trello-read-shunt.sh` / `gh-read-shunt.sh`. Vale para el orquestador y para cada prompt de agente. Ver `/shunt`.
- **El exit code de un motor externo no prueba nada**: Codex sin créditos y `agy` sin permisos salen con 0. Siempre leer la salida.

## Modelo según la tarea (desde 2026-09-23)

Se elige al lanzar cada agente con el parámetro `model` del Agent tool; los frontmatter no se tocan.

**Motores (desde 2026-09-24): Codex siempre primero — coder, QA y adversary — hasta dejar su cuota en cero.** Sin Codex, `flujo.sh` **para** y lo dice; el respaldo (Claude, o **DeepSeek si Claude pasó el 70 % de su ventana de 5 h**) solo corre relanzando con `PERMITIR_RESPALDO=1`, decisión explícita (lo lee `flujo.sh` de `~/.claude/uso-5h.txt`, que escribe la statusline `uso-claude-statusline.py`; sin dato cuenta como bajo). El resumen del script dice qué motor corrió y con qué uso.

| Rol | Modelo |
|---|---|
| Coder mecánico (renombres, avisos de analizador, calcos, fixes con `archivo:línea`) | Codex primero; sin Codex, Claude (DeepSeek en su lugar si Claude pasó el 70 % de 5 h), `agy` para lo visual; si cae a un subagente de Claude, **`model: haiku`**, con build/tsc como filtro; un intento fallido pasa a Sonnet |
| Coder con lógica y QA | **Opus 5.5** (`model: opus` en su frontmatter; regla del responsable 2026-10-12) |
| Adversary, architect | Sonnet (su frontmatter) |
| QA en `ahorro` | **Codex con la definición de `qa.md` en el prompt** (`flujo.sh gate` lo arma). Sin Codex: Claude Sonnet, o **DeepSeek con la misma definición** si Claude pasó el 70 % de 5 h, lanzado **desde la raíz de AcmeOrg** (`--agent` solo encuentra `.claude/agents/` ahí, no en un worktree): `cd <RAIZ> && timeout 30m bash .claude/scripts/claude-deepseek.sh -p --agent qa --output-format json --add-dir <RAIZ> --allowedTools "Bash(dotnet build:*)" "Bash(dotnet test:*)" "Bash(git -C:*)" "Bash(npx:*)" "Bash(tail:*)" "Bash(grep:*)" "Read" "Grep" "Glob" < qa.md > qa.json`. El prompt pide rutas absolutas de `<RAIZ>` sin `cd`. Si `--agent` falla sale igual con 0: mirar stderr. Tokens en `usage` del JSON. Lo mismo vale para el adversary |
| Planner | **Opus 5.5 siempre** (`model: opus`, regla del responsable 2026-10-12; el planner no baja a Sonnet). En `calidad` con Nivel 3 puede ir en `fable` |
| `system-auditor` | `model: opus` (Fable cuesta 2.5× Opus 5.5) |
| **Tareas auxiliares** (resumir un doc interno o una salida larga que no sea código, borrador de una descripción de tarjeta o del cuerpo de un PR, clasificar o traducir texto) | **OpenRouter gratis**: `bash .claude/scripts/openrouter.sh`. Sin código de la empresa. Claude revisa el resultado antes de usarlo |

**Codex coder con `gpt-6.1-sol` en `service_tier=fast` y esfuerzo medium; `gpt-6-luna` solo para lo mecánico con `CODEX_MODEL_CODER=gpt-6-luna`. QA, adversary y revisión con `gpt-6.1-sol`** (el responsable, 2026-10-22: luna obligaba a 2-3 vueltas por tarjeta); `flujo.sh` rechaza otro modelo y para en vez de caer a Claude sin `PERMITIR_RESPALDO=1`. **Fuera de los subagentes de Claude de arriba, Opus 5.5 solo en dos casos** (decisión del responsable): segunda opinión de otra familia sobre un diff de riesgo alto (esquema, concurrencia, seguridad, mensajería) y planner de tareas que tocan auth, concurrencia o fronteras de ADR. En refactors, pruebas y UI no se usa.

Planner, coder, coder-web y qa van en Opus 5.5 por su frontmatter (regla del responsable 2026-10-12): no bajan a Sonnet ni suben a Fable. `architect` y `adversary` se quedan en Sonnet.

**Consumo y caché (desde 2026-09-24).** Precio por millón de tokens, entrada/salida: Fable 5.1 $10/$50, Opus 5.5 $4/$20, Sonnet 5.5 $2/$10, Haiku 4.5 $1/$5. Leer del caché cuesta 0.1×; escribirlo, 1.25×. Por eso:
- **Retomar agentes en vez de lanzar nuevos**: el ciclo 2 de QA y la re-revisión del adversary van por `SendMessage` al mismo agente, cuyo contexto ya está en caché; uno nuevo relee el plan y los archivos.
- **Prompt con prefijo fijo**: el bloque de raíz, las reglas y el formato van primero y textuales; lo variable (tramo, diff, hallazgos), al final. El caché es por prefijo exacto.
- **Architect y planner no se solapan**: si la tarea calca un patrón ya identificado (run doc o `INDEX.md`), el architect se salta y el planner recibe la referencia; se dice en el reporte.
- **Un trabajo, una sesión** (desde 2026-09-24): encadenar trabajos hace que el último arranque releyendo un contexto enorme (una sesión con 5 trabajos pagó ~1,7× lo que pagaban sesiones limpias). Al cerrar el Step 5 se escribe el traspaso ([detalle de registro](#detalle-registro)) y se sugiere seguir en una sesión nueva, que arranca leyendo solo ese archivo. Si el pedido que llega es otro trabajo y el contexto pasa de ~200K (lo avisa el hook `aviso-contexto.py`), sugerirlo antes de empezar. Dentro de la corrida, las llamadas independientes (lecturas, `git status`, ping de Codex) van en un solo mensaje: cada ida y vuelta relee todo el contexto.
- **Preguntas al margen, fuera de la corrida**: una duda de precios, de modelos o conceptual a mitad de corrida se contesta corto y sin cargar skills pesadas, o se sugiere otra sesión y se trae solo la decisión.
- **Salida de comandos a archivo**: build, tsc, lint y suites se redirigen a un log y se lee el resumen (`tail`/`grep`), nunca la salida cruda. Vale para el orquestador y va en cada prompt de agente.

**Modos** (`--modo`, por defecto `ahorro`): en `ahorro`, coders, QA y adversary van a Codex; sin cuota se para y se pregunta si relanzar con `PERMITIR_RESPALDO=1` (Claude o DeepSeek según el uso de 5 h), y lo visual a `agy` y un subagente de Claude sale solo si ninguno puede, diciendo cuál y por qué. `normal` usa los agentes de Claude más un motor externo por cambio. `calidad` suma todos los revisores. En ningún modo baja: verificar el diff contra `git status`, la suite completa antes del commit y la vigilancia de los motores externos.

## Modo Enjambre — manejo (desde 2026-10-07)

`--manejo` es otro eje que `--modo`: `--modo` elige motores y costo; `--manejo` elige cuánto paralelo y cuánto rigor en las vueltas de corrección (`eco` no es `ahorro`). **Por defecto `sport`** (el responsable: "enjambre siempre"). Se anuncia en una línea el manejo elegido (y en `auto`, por qué).

| Manejo | Cuándo | Cómo corre |
|---|---|---|
| `eco` | solo si el responsable lo pide | Sin paralelo: 1 coder, 1 QA, planner solo si el cambio no es obvio. Adversary según la tabla del Step 4. Una vuelta de arreglos, solo P0/P1 |
| `sport` | **por defecto** | Todas las reglas de velocidad de abajo y la regla de gravedad |
| `blindado` | todo lo que toque sesión/JWT, aislamiento de datos, migraciones o seguridad | Adversary siempre. Coders en paralelo igual, pero **todo hallazgo real entra a arreglos** (también P2 raros y P3 baratos), dentro del tope de 2 ciclos de QA. La re-revisión incluye al adversary. Modelos: los de la tabla de arriba (Opus solo en sus dos casos), no se suben |
| `auto` | el orquestador elige | Cambio trivial de 1 archivo → `eco`; lo que toque lo de `blindado` → esos bloques en `blindado`, el resto en `sport` |

**Reglas de velocidad (`sport`):**
- **Lo independiente corre en paralelo**: varios agentes en un mismo mensaje, uno por tramo con archivos disjuntos (Step 3) o uno por worktree/tarjeta (`/worktree`).
- **Pipeline, no barrera**: apenas un coder commitea su tramo (Step 3.6), se lanza el QA de ese tramo (y el adversary de su frente si aplica); no se espera a los demás coders.
- **Reusar agentes** con `SendMessage` para arreglos y re-revisiones (ver "Consumo y caché"). **Planner según tamaño** (Step 0.7 y tabla de modelos).
- **Una sola suite completa**: cada agente corre solo las pruebas de su tramo; la suite completa la corre el orquestador una vez antes del commit (Step 3).
- **Arreglos chicos los hace el orquestador**: menos de ~20 líneas en 1–2 archivos → edita él, sin lanzar agente, corre los tests del área y `flujo.sh suite` una vez; se trata como Nivel 0 dentro de la corrida. Excepción: si hay otra sesión trabajando en ese worktree, va por agente.
- **Varios hallazgos se reparten en paralelo** por archivo disjunto, un agente por grupo; nunca un solo agente en serie con una lista larga.

**Regla de gravedad — solo lo grave abre otra vuelta** (escala de Codex; vale para QA, adversary, `/codex` local y `/supercodex`):

| Gravedad | Qué se hace |
|---|---|
| P0 / P1 | Siempre se corrige y reabre ronda |
| P2 | Se corrige en la misma vuelta si afecta datos, la continuidad del historial, sesión/seguridad o muestra algo engañoso al agente. Si es un caso raro o cosmético → tarjeta de seguimiento |
| P3 y deuda previa | **Nunca reabren vuelta**: tarjeta de seguimiento (con su número, vía `/proyecto extra`) y se responde el hilo con 👎 / "fuera de alcance" + la tarjeta |

Un PR que llega al tope de 8 rondas de `/supercodex` sin 2 limpias se detiene y se le consulta al responsable, con la opción de aceptar el resto como seguimiento.

## Step 0 — Historial y chequeos

- **PRs abiertos primero** *(el responsable, 2026-10-01)*: antes de arrancar una tarjeta nueva, correr `/listo-para-merge`. Si hay hilos de Codex sin responder o PRs sin sus 2 rondas limpias, se cierran primero y se avisa al responsable; la tarjeta nueva espera.

- **Si hay traspaso** (`.claude/traspasos/` de la rama o el slug de la tarea), se lee primero y reemplaza la búsqueda en `TASKS.md`, `git log` y el `INDEX.md`: la sesión anterior ya dejó el estado. Se verifica solo lo que el traspaso marque como pendiente.
- **Trabajo en vuelo antes de crear tarjeta, rama o worktree** *(el responsable, 2026-10-22)*: `python .claude/scripts/trabajo-en-vuelo.py` lista cada worktree con commits fuera de develop o cambios sin commit, y si tiene PR. Una fila **sin PR** del mismo tema se retoma; no se abre otra. El traspaso lo trae al final (lo agrega `redactar-traspaso.sh`), pero se corre igual al arrancar: el traspaso solo ve la conversación de su sesión.
- Leer **solo** "Mapa de conocimiento" de `INDEX.md`, abrir solo los run docs de ese tema, bajar al libro mayor solo por una corrida concreta. Pasar al architect/planner lo ya resuelto. Si no hay tema, decirlo: es terreno nuevo.
- Si la tarea toca el dominio o un caso de uso planeado: consultar `contexto-negocio/` y `contexto-negocio/PREGUNTAS-NEGOCIO.md`. Una pregunta de negocio nueva se agrega a esa lista antes del Step 5.
- **Un pendiente viejo se verifica antes de trabajarlo** (MCP, `grep`, `git log`); si la nota miente, corregirla en la misma corrida.
- **Retro**: 3+ corridas desde la última entrada de `RETRO-LOG.md` → avisar en una línea. **System-audit**: 10+ desde `SYSTEM-AUDIT-LOG.md` → avisar. No invocar ninguno sin pedido; sus bloques de log los agrega el orquestador.
- **Cuota de Codex**: si se le va a delegar algo, ping antes; sin créditos, decirlo con lo que implica en costo y seguir.
- **Replay-harness**: `git log -1 --format=%ai -- .claude/agents/ .claude/commands/ .claude/orquestar/` **y** `git status --short` de esas carpetas, contra la fecha de la última corrida. Si algo cambió, preguntar siempre si se corre antes una tarea dorada (`GOLDEN-TASKS.md`). Si no, anotarlo en el reporte final.

## Step 0.5 — Rama

- **Con `--en`**: la rama ya existe. Verificar `feature/…`/`fix/…` y que `git -C <RAIZ> log origin/develop..HEAD` tenga solo commits de la tarjeta. Árbol sucio se mira en `<RAIZ>`; guardar `git -C <repo> status --porcelain` de la carpeta principal para compararlo en el Step 3. Si la tarjeta necesita código de otra rama sin mergear, parar: está en la ola equivocada.
- **Sin `--en`**: árbol sucio ajeno → parar y preguntar. Rama desde `develop`: `feature/<slug>` o `fix/<slug>`, sin número de corrida. No se pushea sin pedido.
- **Dependencia de una rama sin mergear**: preguntar (a) mergearla a `develop` primero (recomendado) o (b) apilar sobre ella. **Nunca más de 2 PRs apilados** (2026-10-19: la cadena de 6 de la vista una funcionalidad multiplicó las rondas de Codex); con más partes, cada una sale de `develop` (ver `/worktree`, «Pila de PRs»). Si aparece a mitad de corrida, merge o cherry-pick y anotarlo.
- **HARD RULE — verificar que la rama tenga lo que la tarea da por existente** (`grep`/`Read`) antes del architect.
- **Una medición de referencia sale del mismo commit que el cambio** (`git rev-parse develop` contra `origin/develop`); si los números no cuadran, primero sospechar que no son comparables.
- Un agente independiente (mockup, `ux-researcher`) sobre un diseño ya acordado corre en paralelo, en background.

## Step 0.6 — Tarjeta de Trello al inicio

Preguntar si hay tarjeta o hay que crear una, contra el **tablero vivo** vía `/trello` (nunca `docs/trello/`). Existe: su título no se toca. No existe: proponer título del PR + `(repo)` y esperar aprobación. Llevarla hasta el Step 4.7.

## Step 0.7 — Nivel 0 / Nivel 1 / pipeline completo

Elegir el nivel más liviano que se justifique de verdad; ante la duda, el de arriba.

**Tarjetas chicas, en tajadas verticales** *(el responsable, 2026-10-22)*: el objetivo es 3-5 archivos de producción por corrida. Hoy un cambio así pasó el gate a la primera, y uno de 14 archivos trajo 6 hallazgos y 2 vueltas. Si el plan pasa de ~6 archivos de producción, el planner lo parte en tajadas que se entregan solas (cada una con su valor visible y sus tests), y cada tajada va con su tarjeta y su PR desde develop (máximo 2 apiladas). Partir por capa (todo el backend primero y la UI después) no cuenta como tajada.

**TDD con SDD en todo cambio de lógica o estado** *(el responsable, 2026-10-23; antes, desde el 22/10, solo en riesgo bajo)*: REQ confirmado → tests de aceptación de sus escenarios en rojo, commiteados aparte (`test(...)`) → el coder los pone en verde sin tocarlos. Lo hace `flujo.sh tests <RAIZ> $S <etiqueta> "test(...)"`: exige que el plan cite un `REQ-NNNN` de `requisitos/` (confirmado) y tenga `### Tests de aceptación`; acepta solo archivos de test; falla si los tests ya pasan, y fija esos archivos. `flujo.sh coder` falla si no hay tests fijados, y también si el coder los modifica. `ejecutar` corre los tests primero y toma el mensaje de la línea `Commit de tests: test(...)` del plan. **Fuera: solo texto, etiquetas o estilos**, con `SIN_TDD="<motivo>"` delante del comando (sale en el resumen). Si un test está mal, el coder lo dice en `### Deviations from Plan`; no lo cambia. En los cambios de lógica, el criterio de «hecho» queda fijado antes de codear (23/10: el test del buscador mostró que la carrera del plan no estaba donde decía).

- **Nivel 0 — lo edita el orquestador, sin subagente**: texto, etiqueta, color literal, mensaje de log, constante, comentario, typo; en web-app también quitar o mover un botón, redirigir a una vista existente, una clase o un tamaño. Red: `dotnet build` (+ test del proyecto si hay cobertura) o `npx tsc -b` + `npx eslint` sobre lo tocado + `npx vitest run` de sus tests. Deja de ser Nivel 0 si toca estado, navegación con parámetros, datos o contrato con api-core. Sin security-review.
- **Nivel 1 — sin architect**: forma real pero patrón obvio (un mapeo de varios casos, renombre de un campo de DTO, fix de una línea sin esquema/datos/auth/concurrencia, reordenar o agregar un campo). **Corre: planner en Sonnet (avisado de que es fast-path) → coder → QA.** Desde 2026-09-23 **no** corre `adversary`, ni la revisión de Codex, ni Antigravity salvo que haya cambio visual. Security-review a juicio; si se salta, decir por qué.
  - **En api-core se corre como workflow, no paso a paso** (desde 2026-09-24): no se lanzan agentes ni se leen anexos, cada ida y vuelta relee el contexto entero. Con `S=<scratchpad>/<slug>`:
    1. Escribir la tarea en `$S/tarea.md` (solo el pedido; el script pone la raíz, las reglas y el fast-path).
    2. `bash .claude/scripts/flujo.sh plan <RAIZ> $S/tarea.md $S`. Lee las Risk Flags del resumen: si alguna dice "yes", pasar a pipeline completo.
    3. `bash .claude/scripts/flujo.sh ejecutar <RAIZ> $S "<conventional commit en español>"`. Hace coder (Codex; sin cuota, el respaldo) → build → control de archivos → commit → QA (mismo motor) → suite. `FALLÓ` o QA `FINDINGS` → leer el log que nombra y seguir a mano desde ahí (ciclo 2 de QA con `codex exec resume <id>`, o `--resume` si fue Claude/DeepSeek).
    4. Step 5 con `python .claude/tools/orquestar/registrar_corrida.py --desde <inicio ISO UTC> --claude planner=$S/planner.json --codex ping=$S/codex-ping.log --codex coder=$S/coder.log --deepseek qa=$S/qa.json`; con `--run-doc/--cuerpo/--meta` y `--index-fila/--mapa` escribe el doc y las filas.
    Todo en un mismo mensaje cuando no dependa del anterior. web-app sigue paso a paso hasta que el script lo soporte.
- **Siempre pipeline completo**: endpoints nuevos, esquema o migración, fronteras de ADR-0001 (entidades propias y externas), auth/JWT/roles, concurrencia (claim-a-row, single-active-X), o duda de clasificación.
- **Juntar pedidos en demos en vivo**: esperar a que el responsable cierre la idea, agrupar, separar Nivel 0 de cambios con forma y lanzar de una vez. Un bug que bloquea la demo sale enseguida.
- **Step 5 es obligatorio en todo nivel**; en Nivel 0 y 1, en su forma liviana (solo fila de `INDEX.md`).

## Step 0.8 — REQ confirmado (todo cambio de lógica o estado)

Desde el 2026-10-23 aplica en todo nivel con lógica o estado, no solo en el pipeline completo: sus escenarios Gherkin son los tests de aceptación de `flujo.sh tests`. Sin REQ confirmado en `requisitos/`, parar antes del Step 1: ¿se redacta con `/requisitos` o entra por excepción? Si el REQ cambia de versión con el coder trabajando, parar y reportar; no re-planificar solo.

## Step 0.9 — Contrapeso de negocio (solo pipeline completo)

Correr `/negocio` sobre la tarjeta o el REQ. "No ahora" → parar y reportar. "Vale con condiciones" → las objeciones viajan al architect y al planner.

## Step 1 — Architect

Subagente `architect`: patrón equivalente en `api-contracts`/`api-people`. Sus decisiones de diseño van al planner como **propuestas**, no finales.

## Step 2 — Planner

Subagente `planner` (modelo según la tabla de arriba), con la tarea + el `## Architect Report` textual. Pedirle: confirmar o corregir cada decisión del architect; verificar contra el esquema real por MCP; cruzar con `AcmeOrg/docs/adr/` (marcar lo que toque ADR-0001); lista numerada de tareas **con los archivos de cada una** y matriz de QA. Una sola pasada: si después el plan resulta mal, parar y reportar.

- **2.5 — Checkpoint humano**: si alguna de sus `### Risk Flags` dice "yes", resumir el riesgo en 3-5 líneas y esperar un sí explícito.
- **2.7 — Codex revisa el plan** *(el responsable, 2026-10-02)*: si el plan toca estado, esquema o concurrencia, antes de codear se le pasa a Codex (`gpt-6.1-sol`, vía `/codex`) con este prompt: "¿Qué escritores del campo, datos previos al cambio, entradas vacías, concurrencia y estados de error de pantalla no cubre este plan? Solo huecos, con `archivo:línea` si los hay." Los huecos válidos vuelven al planner en un solo viaje; sin créditos de Codex, se omite y se dice en el reporte. Una ronda, sin ciclos.
- **2.6 — Aviso de costo**: si la tarea se parece a una corrida cara del `INDEX.md`, avisarlo en una línea y seguir.

## Step 3 — Coders

**Al llegar acá, leer [detalle de coders](#detalle-coders).** Resumen de lo que no se negocia:

- Motor y modelo según la tabla de arriba; lo mecánico primero a los motores externos.
- **Coders externos por script** (desde 2026-09-24): el `## Plan` textual va a `$S/plan.md` y cada tramo se lanza con `bash .claude/scripts/flujo.sh coder <RAIZ> $S <api|web> "<commit>" "tareas N-M"`, los dos en el mismo mensaje y en background. El script arma el prompt, elige Codex (el respaldo solo con `PERMITIR_RESPALDO=1`), compila, controla archivos y carpeta principal, y commitea; el orquestador lee solo su `## Resumen`. No se escriben prompts de coder a mano. Un coder de Claude con lógica fina sigue como Agent.
- **Cada coder recibe solo su tramo del plan** (y el contrato fijo si cruza repos), con la lista `Archivos del plan:` / `Para entender el patrón:`. QA recibe el plan entero.
- Backend .NET → `coder`; `web-app/` → `coder-web`; ambos → uno de cada uno con su parte, y se consolidan los `## Coder Report` antes de QA.
- **El coder compila y nada más; la suite corre una sola vez** (desde 2026-09-24, GT-09): con `flujo.sh coder` la corre el script tras el build, con un reintento del coder si sale roja, y el gate reusa ese resultado; el QA no la repite. Con un coder de Claude como Agent, la corre QA. No repetir la verificación del coder sin motivo. **Mientras se itera** (un arreglo a mano, un test rojo) se corren solo los tests del área (`--filter`); la suite completa, una vez antes del commit. **Si el orquestador arregla a mano**, commitea y corre `flujo.sh suite <RAIZ> $S`: deja el resultado atado al HEAD y el gate no la repite *(el responsable, 2026-10-06: la suite completa corrió 4 veces en un arreglo de 3 archivos)*.
- **Un fallo de lectura nunca se muestra como "vacío"** en la consola (familia de hallazgos recurrente de Codex, 2026-10-07): error y lista vacía son estados distintos en pantalla. Va en el prompt de `coder-web` y en la matriz de QA.
- Varios coders en paralelo por defecto, archivos con dueño exclusivo; un solo coder si comparten archivo o dependen entre sí.
- **Con `--en`**: al volver cada coder, `git -C <RAIZ> status --porcelain` debe listar sus archivos y la carpeta principal seguir igual que en el Step 0.5. Si no, parar y mostrarlo.

## Step 3.5 — Architect en modo revisión (condicional)

Solo si la corrida cambió estructura (proyecto, capa o carpeta nueva, `DbContext`, middleware, namespace movido, patrón nuevo): `architect` con el `## Coder Report`; sus `### Deviations` son hallazgos de QA y gastan los 2 ciclos del Step 4. Si no, saltarlo y decirlo.

## Step 3.6 — Checkpoint commit

Al volver cada coder (y el 3.5 si corrió), commitear tal cual, en conventional commits en español. Uno por coder en paralelo.

## Step 4 — Gate de pre-PR

**Al llegar acá, leer [detalle de gates](#detalle-gates).** En `sport` el QA (y el adversary de su frente) arranca por tramo apenas su coder commitea (pipeline, ver Modo Enjambre); la revisión de Codex, la integración (4.4a), la seguridad (4.6) y la suite completa corren **una sola vez** sobre el diff acumulado desde el último gate, en uno de estos momentos: antes de ofrecer push/PR, antes de subir commits nuevos a un PR abierto, o cuando el usuario lo pida.

**Revisores según riesgo (desde 2026-09-23):**

| Revisor | Cuándo |
|---|---|
| `qa` | **Siempre** fuera de Nivel 0. Un QA por cambio; uno solo con las dos raíces si el cambio cruza repos |
| `adversary` | Solo si el diff toca **esquema, concurrencia, seguridad o mensajería**, en el mismo mensaje que QA |
| Antigravity (`--mode plan`) | Solo si hay cambio visual |
| Codex review (`/codex`) | **Siempre antes de abrir un PR**, en cualquier nivel con cambio de código y con créditos *(el responsable, 2026-10-01)*: los hallazgos que pasan la **regla de gravedad** (Modo Enjambre) se corrigen **antes del push**, así el PR llega limpio a `/supercodex` y a Revisor Principal. Los PRs abiertos hoy recibieron de 1 a 5 hallazgos P2 cada uno después de abrirse. **Se repite hasta 2 rondas locales limpias seguidas** antes del push (desde 2026-10-02: #<n> y #<n> acumularon 7 y 13 comentarios de Codex ya abiertos). **Excepción, arreglo sobre un PR ya abierto** *(el responsable, 2026-10-06)*: alcanza 1 ronda local limpia; las 2 rondas de GitHub de `/supercodex` siguen siendo la puerta (el mismo diff se revisaba 4 veces). Desde 2026-10-09 esa ronda local corre **antes** del push, sobre el lote entero de arreglos (un push por lote, nunca uno por hilo), y cada arreglo entra con su test de reproducción; detalle en `/supercodex`, "Local primero, el bot una vez por lote". Un diff de más de ~15 archivos se parte en PRs más chicos antes de revisar. **Límites aceptados:** lo que el responsable ya decidió aceptar (REQ/ADR) queda en el código con un comentario de 1-3 líneas y su referencia, y el prompt de la revisión local de Codex lo lista como "no re-reportar"; así no vuelve como hallazgo ni gasta rondas |
| Integración (4.4a) | Esquema, EF Core, concurrencia o datos; **obligatorio** si la rama borra o renombra columnas |
| Seguridad (4.6) | Pipeline completo; en Nivel 1, a juicio |

**Por script**: `bash .claude/scripts/flujo.sh gate $S [--adversary] [--codex] <RAIZ>...` lanza QA (+ adversary + revisión de Codex) en Codex, (el respaldo solo con `PERMITIR_RESPALDO=1`), en paralelo sobre `base..HEAD` de cada raíz, con las suites ya corridas (las reusa del coder si el HEAD no cambió); el resumen trae veredictos, hallazgos y el `session_id` para el ciclo 2 (`--resume`). Integración (4.4a) y seguridad (4.6) siguen fuera del script. Antes de las suites, en api-core, el gate bloquea un `MsSqlBuilder` nuevo fuera de los dos fixtures y avisa archivos nuevos de integración y tests de migración vencidos (playbook §34; aislado: `flujo.sh integracion <RAIZ>`).

**Aceptar un tramo de coder**: antes, comparar la lista de archivos de su Task List con el `git diff --stat` del commit; si falta un archivo esperado, el tramo se rechaza. En cambios de API que consume web-app, verificar con `grep` que el endpoint viejo ya no se usa.

**Retry loop**: hallazgos de QA → al coder → QA de nuevo. **Máximo 2 ciclos**; después, STOP y reportar. PASS en cualquier ciclo → parar, sin pulir. `adversary` tiene su propio tope de **1 ronda**. Los hallazgos de todas las fuentes, filtrados por la regla de gravedad, vuelven en **un solo lote**, repartido en paralelo por archivo disjunto (los chicos los arregla el orquestador; ver Modo Enjambre). Un hallazgo de un revisor externo se verifica antes de mandarlo. **El QA del ciclo 2 es el mismo agente del ciclo 1** retomado con `SendMessage` (`codex exec resume <id>` si fue Codex, `--resume` si fue Claude o DeepSeek), con solo el diff nuevo: su contexto ya está en caché.

## Step 4.5 a 4.7 — Commit, seguridad, push y PR

**Al abrir un PR, se adjunta a su tarjeta en el mismo paso** *(el responsable, 2026-10-01: permiso permanente, sin pedirlo cada vez)*: `python .claude/tools/trello/trello.py adjuntar <tarjeta> --url <url del PR> --nombre "#<n> <título del PR>" --aplicar`, y se relee la tarjeta para confirmar el adjunto. Solo adjunta; mover de columna, miembros y fechas siguen esperando el pedido del responsable. Un PR por tarjeta (por repo si cruza api-core y web-app): una tarjeta de dos repos lleva los dos PRs.

**Rondas de Codex en el PR** (lecciones del 2026-10-07; detalle en `/supercodex`):
- Antes de las rondas finales, **sincronizar la cola**: mergear a la rama las ramas previas de la cola, para no repetir rondas sobre otro código.
- Antes de lanzar cualquier ronda, contar hilos abiertos **y** comentarios de Codex sin respuesta nuestra; `supercodex-ciclo.sh` se niega con hilos abiertos.
- Un solo `@codex review` por vez (2026-10-20): la segunda ronda se pide cuando la primera terminó limpia. Dos seguidos se juntan en una.
- Codex ya no comenta cuando la ronda sale limpia, y `Completed` en el resumen no garantiza nada: los comentarios en línea pueden llegar minutos después. Limpia solo tras esperar unos minutos más, sin comentarios en línea ni hilos abiertos.
- Los workflows con `pull_request_target`/`issue_comment` corren desde la rama por defecto del repo: para automatizar desde `develop`, la rama por defecto tiene que ser `develop`.

Detalle en [detalle de gates](#detalle-gates). Lo esencial: commit adicional solo si el gate corrigió algo; PR siempre contra **`develop`**, con sí explícito cada vez para push y para PR; ramas apiladas dependientes → un solo PR; **la tarjeta no pasa a revisión hasta que el responsable lo pida** (solo `/trello adjuntar`); nunca secretos en commits ni PRs.

## Step 4.8 — Fuera de alcance

Trabajo nuevo descubierto → `/proyecto extra` (tarjeta nueva o ampliar la actual, y fila `Extras` con sus horas). Se amplía la actual solo si bloquea la tarea.

## Step 5 — Registrar la corrida (obligatorio)

**Al llegar acá, leer [detalle de registro](#detalle-registro).** La corrida no está terminada hasta que este paso esté hecho: no reportar éxito antes. Si se nota que una corrida anterior quedó sin Step 5, hacerlo primero. Incluye la **bitácora de consumo con una fila por agente y su modelo**, la del orquestador incluida (vía `registrar_corrida.py`, nunca `sin medir`), y la fila de la tarjeta en "Medición: real vs PERT" de `TASKS.md` si tiene estimación. Si la corrida tiene REQ, se anota su PR en `prs` (o el commit en `commits`) del frontmatter; pasa a `implementado` cuando ese PR se mergea a `develop` (`requisitos/README.md`).

## Antes de afirmarle algo al usuario

Un hallazgo de un solo agente no es un hecho: antes de decir "esto es un bug real" o "ya se confirmó", verificarlo con un `grep`/`Read` propio o con un segundo motor.

## Reporte final

Qué se construyó (archivos), patrón del architect, desvíos del planner y por qué, si disparó el 2.5, veredicto de QA, resultado de seguridad, qué revisores corrieron y cuáles se saltaron por riesgo, motor y modelo de cada coder, rama, push/PR (URL) y hallazgos diferidos. Siempre, aunque sea "ninguno": **cambios de agente sin verificar por replay** y **gaps de repo fuente** (qué se decidió).


Los detalles se integran en este archivo para conservar el método completo. En los ejemplos de shell que requieren la raíz compartida, calcular `HARNESS_ROOT=$(git rev-parse --show-toplevel)` desde la raíz del harness antes de cambiar al repo destino.

<a id="detalle-coders"></a>

## Anexo — Step 3: coders y motores externos

Se lee al llegar al Step 3 de `orquestar.md`. El porqué de cada regla está en [historia del proceso](#historia-del-proceso) (`## Step 3`).

### Reparto por motor y modelo

Orden para lo **mecánico** (renombres, plomería de un campo, fixes con `archivo:línea`, avisos de analizador, calcos): **Codex siempre primero, hasta agotarlo → Claude (o DeepSeek si Claude pasó el 70 % de su ventana de 5 h) → `agy` → Claude `coder`/`coder-web` con `model: haiku` → Sonnet solo si los anteriores fallan.** DeepSeek no es un segundo coder de rutina: solo reemplaza a Codex cuando Claude está por encima del 70 %. El filtro siempre es el compilador (`dotnet build` / `npx tsc -b`), no el reporte del motor.

| Trabajo | Motor | Cómo |
|---|---|---|
| Mecánico con criterio verificable | Codex (si el ping de créditos pasa) | `codex exec --sandbox workspace-write -c model_provider=openai ... < /dev/null` (la bandera salta el perfil de CCR de `~/.codex/config.toml`), condiciones en `/codex` |
| Mecánico, sin Codex | `agy` | `agy --model gemini-3.8-flash-high --effort high --mode accept-edits --print="$(cat tarea.md)"`. En `accept-edits` solo puede correr `npx tsc -b`, `npm run lint`, `npx vitest run`; **no corre `dotnet` ni borra archivos**: en api-core el build lo corre el orquestador |
| Visual y de estilo | `agy` | Igual, con archivos prohibidos nombrados |
| Sin cuota de Codex **y** Claude por encima del 70 % de 5 h | DeepSeek V4-Pro (Claude Code apuntado a DeepSeek; `DS_MODEL=deepseek-flash` para lo simple) | `cd <RAIZ> && timeout 30m bash "$HARNESS_ROOT/.claude/scripts/claude-deepseek.sh" -p --permission-mode acceptEdits --allowedTools "Bash(dotnet build:*)" "Bash(npx tsc:*)" "Bash(git diff:*)" "Bash(git status:*)" < tarea.md`. Mismas herramientas, `CLAUDE.md` y hooks que un coder de Claude; gasta saldo de DeepSeek, no cuota de Claude. El prompt va por stdin (un argumento largo se corta en Windows). Con `--agent <nombre>` no sirve `cd <RAIZ>`: los agentes solo se encuentran desde la raíz de AcmeOrg, así que se lanza desde ahí con `--add-dir <RAIZ>` (receta en la fila "QA en `ahorro`" de `orquestar.md`) |
| Archivo nuevo calcado de otro | `code-write.sh` | `bash ~/.claude/scripts/code-write.sh --spec "..." --reference <archivo> --target <archivo>` |
| Mecánico si los externos fallan | `coder`/`coder-web` con `model: haiku` | Build/tsc como filtro; si no compila tras un intento, pasa a Sonnet |
| Lógica con estado, contratos entre capas, reglas de `CLAUDE.md` | `coder`/`coder-web` (Sonnet, su frontmatter) | Subagente nombrado |

El reporte final dice qué motor hizo cada parte y por qué, incluidas las caídas a Claude.

**Antigravity a lo ancho:** además de la revisión visual, `agy` toma por defecto:
- las correcciones del gate en web-app (TS y estilos), en `--mode accept-edits`, con `tsc`/`vitest` como filtro; lo de .NET sigue en Codex porque `agy` no corre `dotnet`;
- el primer borrador de los recortes de docs (`code-write.sh`) y los resúmenes de logs o diffs largos (`bulk-read.sh`), que Claude solo revisa;
- una segunda opinión visual y de accesibilidad en `--mode plan`, en paralelo con el adversary de Codex, cuando el diff toca UI.

**OpenRouter (modelos gratis):** `bash .claude/scripts/openrouter.sh --question "..." [--file ruta] [--model id]` (`--list` muestra los gratis; por defecto `openrouter/free`, que elige uno). Devuelve solo la respuesta y sale con código distinto de 0 si el proveedor falla. **Solo contenido que no sea código de la empresa** hasta que el responsable decida otra cosa: los modelos gratis pueden registrar lo que reciben. Sirve para resumir docs internos o borradores de texto, no como coder.

### Menos contexto por coder

- **Cada coder recibe solo su tramo del plan**, más el contrato fijo si el cambio cruza repos. QA sí recibe el plan entero.
- El prompt lleva `Archivos del plan:` (los que edita), `Para entender el patrón:` (referencias que sí lee enteras) y la frase: *no abras el resto del feature para tomar contexto; si te falta un archivo, léelo y decí en tu reporte cuál y por qué*. El `## Coder Report` trae `Archivos leídos fuera de la lista`.
- **El coder compila y nada más** (`dotnet build` o `npx tsc -b`). La suite corre una vez: con `flujo.sh coder`, el script tras el build (un reintento del coder con solo las fallas si sale roja) y el gate la reusa; con un coder de Claude como Agent, la corre QA. El prompt del coder de `flujo.sh` le pide además propagar el campo nuevo a todo lugar que copie un campo vecino (mappers, fallbacks, fixtures), por las dos fallas de GT-09. El orquestador no repite la verificación del coder salvo que el reporte no la traiga, se contradiga con el diff o declare rojo.
- **Un arreglo nunca va por `codex exec` suelto** (2026-10-13: dos arreglos así dejaron el proyecto de integración sin compilar y una suite roja que nadie vio): con el árbol sucio, `flujo.sh arreglar <RAIZ> <SALIDA> <prompt.md> [etiqueta]` corre el motor y las mismas compuertas que `coder` (build, tildes, suite), sin commitear. Docker y `npx` los ejecuta el script en el shell del orquestador, no el sandbox de Codex: si el reporte del motor dice «no pude verificar», no es un verde. `CODEX_EFFORT=medium` para tramos que cruzan ramas o necesitan diagnóstico (el valor por defecto sigue en `low`).
- **Partir un PR por archivos** (2026-10-13, #<n> → A/B): la mitad que sale primero se prueba **sola sobre `develop`** (`tsc` + suite completa) antes de revisar nada; una API que cambió en la otra mitad (props, iconos, tokens que otro componente aún usa) rompe la compilación o se pierde en silencio. Un token o variable que se borra de un archivo compartido se busca con `grep` en todo `src/` antes de borrarlo.
- **Ambiente y recibo de verde** (2026-10-13): `coder`, `arreglar`, `suite` y `gate` paran antes de lanzar si la raíz está en `develop`/`main`/`qa` o detached, si Docker no responde y la suite usa Testcontainers, si el Host corre desde esa raíz (bloquea las DLL) o si Codex no responde; `flujo.sh chequear <RAIZ> [SALIDA]` corre lo mismo sin lanzar nada. Cada suite verde deja `<git común>/flujo-recibos/<sha>`, y el `pre-push` de `scripts/hooks-repos/` bloquea subir un commit sin recibo: tras un merge o un commit a mano, `flujo.sh suite` antes del push (`FLUJO_SIN_RECIBO=1` lo salta a mano).
- **Límites de `flujo.sh coder`** (2026-09-28): dos coders sobre la **misma raíz** no se soportan (comparten árbol, build y commit; se pisan). En paralelo solo con raíces distintas (api y web). Y el script se lanza con `run_in_background` de la herramienta, nunca con `&` adentro: el proceso se pierde y no llega la notificación. Si el coder reintenta por una suite roja de integración o de Docker, el prompt ya le prohíbe tocar `Persistence/`, migraciones y `Services/` (un coder de Codex cambió el `DEFAULT` de `Entity.Number` y creó una migración por eso).

### Paralelizar

- **Decidir todo antes de lanzar la primera ola**: investigar → decidir con el usuario → una sola ola.
- **Varios coders en paralelo por defecto**, un cambio independiente por coder, todos en el mismo mensaje, en background. Cada prompt declara sus archivos (dueño exclusivo) y los prohibidos, nombrando al dueño.
- **Un solo coder por repo cuando dos trabajos comparten archivos.** Compartir archivo es la excepción: se junta, no se encola.
- **Rename grande: partir por carpeta**, con la tabla viejo → nuevo escrita antes y dada idéntica a todos.
- **Adelantar lo mecánico sin esperar al planner** si el alcance ya está especificado y el contrato no se va a mover: contrato fijo primero, archivos con dueño, coders en el mismo mensaje, planner en paralelo solo con lo que necesita juicio. Nada que toque esquema se adelanta sin el Step 2.5.
- **Lo que no se recorta por velocidad**: verificación contra la base con datos reales, el diff contra `git status`, QA sobre todo cambio y `adversary` sobre lo que borre columnas. El reporte de un agente no es evidencia.

### Motores externos: vigilancia (no negociable)

1. Entrada cerrada con `< /dev/null`.
2. Tope con `timeout` (ej. `timeout 20m codex exec ...`).
3. A los 60 s, leer el log: si dice `Reading additional input from stdin`, no crece o no hay salida, cortar y relanzar.
4. Nunca responder "cuánto falta" sin mirar el log o el proceso.
5. **Nunca `&` al final del comando.** El background lo da el harness (`run_in_background: true`); un `&` hace que el padre termine y se lleve al hijo.

- **El exit code no sirve**: Codex sin créditos, Codex sin `NuGet.Config` y `agy` sin permisos salen con 0. Siempre leer la salida.
- **Dos motores externos sobre el mismo árbol reportan mal su propio trabajo.** Lo hecho lo cuenta el compilador o el diff. Si hace falta el conteo del agente, árbol propio o en serie. No aplica a `coder`/`coder-web`.
- Todo prompt externo lleva, literal: *"Comentarios: solo el porqué no obvio, en 1-3 líneas. Sin historia, fechas ni justificaciones para el revisor: eso va en tu reporte."* y *"en esta máquina NO está instalado `rg`; usá `grep -rn` o `findstr`"*.
- `agy`: el prompt va pegado al flag (`--print="..."`) y `--model` antes; nunca `--dangerously-skip-permissions`; única excepción: `--mode plan` (revisor, no edita archivos) y solo con permiso expreso del responsable (ver `antigravity.md`, punto 4 de "Cómo lanzarlo").
- Los diffs externos se contrastan contra `git status` y se verifican igual que los de un coder propio.
- Los tokens de Codex, DeepSeek y `agy` salen de otras cuentas: delegar mueve el gasto, no lo reduce en abstracto. Cantidad de agentes no multiplica costo; el tiempo de pared sí cambia.

### Trello y PRs

El contenido (título, descripción, cuerpo del PR) lo decide Claude. Las **lecturas grandes** de Trello y GitHub van siempre por `trello-read-shunt.sh` / `gh-read-shunt.sh`. Las escrituras ya decididas corren directo; `gh pr create`/`merge`/`close` nunca se delegan.

### Step 3.1 — Workflow `orquestar-medio`

Con el plan cerrado y **2 o más cambios con archivos disjuntos** que van a coders de Claude, el tramo coder → QA + adversary → fix va al workflow `.claude/workflows/orquestar-medio.js` (no baja tokens; gana tiempo y watchdog):

```json
{ "raiz": ".worktrees/api-core--slug", "comandoBuild": "dotnet build",
  "cambios": [ { "id": "entity-id", "titulo": "...", "agente": "coder",
    "archivos": ["..."], "referencia": ["..."],
    "instrucciones": "<el tramo del plan que le toca>", "conAdversary": true } ] }
```

Devuelve por cambio `CERRADO` / `SIN_CERRAR` / `BUILD_ROJO` y `requierenDecision`. No le pasás triage, rama, tarjeta, reparto de motores, commit, verificación del diff, migraciones ni run doc. **No usarlo** en Nivel 0/1, con un solo cambio, cambios dependientes o cuando el trabajo va a motores externos. `conAdversary` solo según el criterio de riesgo del Step 4.


<a id="detalle-gates"></a>

## Anexo — Step 4: gates de pre-PR

Se lee al llegar al Step 4 de `orquestar.md`. El porqué de cada regla está en [historia del proceso](#historia-del-proceso) (`## Step 4` a `## Step 4.6`).

### Codex como segundo revisor

Solo en el **pipeline completo** o en tareas avanzadas, y solo si el ping de créditos pasa. `/codex` con `--uncommitted`, en paralelo con QA. Sus hallazgos se verifican contra el código; si no hay cuota, se omite y se dice.

### Antigravity como revisor visual

Solo si el diff toca UI (estilos, layout, componentes, tokens).

```
agy --model gemini-3.8-flash-high --effort high --mode plan --print="<prompt + diff>"
```

- Prompt pegado al flag, `--model` antes; `--mode plan` no edita.
- El diff va dentro del prompt, nunca como archivo en el worktree. Límite práctico ~32K caracteres: partir en tandas.
- **Cada hallazgo se verifica antes de mandarlo al coder** (tasa de acierto entre 1/4 y 7/9). Un "sin hallazgos" también se verifica.

### QA y adversary

- QA: subagente nombrado `qa`, con el `## Coder Report` y la matriz de tests del planner. Un QA **por cambio**; si el cambio cruza repos, **un** QA con las dos raíces y el contrato como criterio.
- Varios cambios desde el último gate: un QA por cambio a la vez. Mientras, el orquestador verifica el diff contra `git status` y lanza la suite completa en background.
- `adversary`, cuando aplica por riesgo, sale **en el mismo mensaje que QA**. Esperar el PASS de QA solo si el coder declaró rojo o ya se está en el segundo ciclo de QA.
- Un solo viaje al coder con los hallazgos consolidados.

### Advertencias del analizador

Build verde no alcanza: api-core tiene analizadores (Meziantou, ola 2). Antes del commit, `dotnet build --no-incremental` y ninguna advertencia en los archivos del diff (`git diff --name-only origin/develop`). En una consulta de EF, `==` es lo correcto: no se cambia por `string.Equals`.

### Step 4.4 — Gates en paralelo

4.4a (integración), 4.4b (`adversary`) y 4.6 (seguridad) leen el mismo diff: se lanzan solapados, se consolidan y vuelven en **un** viaje. Topes separados: integración gasta el de QA, `adversary` el suyo, seguridad no tiene loop. "Sin hallazgos" en los tres se dice explícito.

### Step 4.4a — Tests de integración

Juicio del orquestador, una vez, después del PASS de QA: solo si la corrida tocó esquema, migraciones, queries de EF Core, concurrencia o acceso a datos real. **Obligatorio si la rama entera tiene una migración que borra o renombra columnas**:

```
git diff <base>..HEAD -- 'Persistence/Migrations/*.cs' | grep -E "DropColumn|RenameColumn"
```

Si devuelve algo, corre `dotnet test api-core.IntegrationTests`, y se buscan inserts por SQL crudo que nombren la columna vieja (`grep -rn "\[Columna\]" --include=*.cs`), verificando cada caso: un test de migración puede nombrarla a propósito. Un fallo vuelve al coder y cuenta en los 2 ciclos de QA. El reporte final dice si corrió y por qué.

### Step 4.4b — Adversary

Subagente nombrado `adversary`; sus listas de vectores y heurísticas viven solo en `adversary.md`.

- PASS: su parte queda vacía.
- P1: se resuelve antes del PR. P2 y huecos de mutación: se presentan al usuario; si son riesgo real, al coder.
- **Tope: 1 ronda** adversary → coder → adversary, independiente de QA. La re-revisión retoma al mismo adversary (`SendMessage`, o `codex exec resume` si fue Codex) con solo el diff del fix. Si quedan P1, STOP y escalar. Cada fix re-corre build + tests Nivel 1 antes de re-invocarlo.
- **No comitees mientras un revisor lee el diff sin commitear.** Primero cierra el revisor, después el commit; si ya comiteaste, revisar `HEAD~1..HEAD`.

### Step 4.6 — Seguridad

- Skill `security-review` + checklist de `.agents/skills/security/SKILL.md` (CWE y versiones mínimas). Si cambió un `.csproj`/`package.json`, revisar versiones.
- Hallazgo real: no vuelve solo al coder; se le presenta al usuario.
- El skill calcula su diff contra `origin/HEAD`: si no resuelve, `git remote set-head origin -a`; con ramas apiladas, acotar la lectura a los archivos de la corrida y decirlo.
- **Con `--en`, no invocar el skill**: gate a mano sobre el diff del worktree (autorización de endpoints tocados, SQL literal vs interpolado, qué destruye una migración, versiones de paquetes). Decirlo en el reporte.
- Nivel 1: juicio del orquestador; se salta solo si no hay superficie de PII/auth/datos, y se dice por qué. Nivel 0 lo salta siempre.

### Step 4.5 — Commit y `.gitattributes`

- Commit **adicional** solo si el gate generó correcciones; el checkpoint del Step 3.6 ya existe.
- Estilo: conventional commits en español, imperativo y minúscula (`feat(entidad): agregar …`, `fix(…)`, `docs: registrar corrida NNNN`). Tipos: feat, fix, docs, refactor, test, style, perf, ci, build, chore. Merges como `Merge …`. No mergear a la base.
- `.gitattributes` de api-core marca `linguist-generated=true` en `Persistence/Migrations/*.Designer.cs` y en los tres proyectos de tests (decisión del responsable para api-core; no replicar en otro repo sin preguntar).

### Step 4.7 — Push y PR

- Antes: el gate ya corrió sobre todo el diff acumulado. Nunca subir código que el gate no vio.
- **Con `--en` no corre**: ni push ni PR, ni se ofrecen.
- Sin MCP de GitHub: decir la rama y recordar que la base es **`develop`**, no `main` (`/verificar-ramas` si pasa).
- Con MCP: preguntar cada vez, por separado, push y PR. PR contra `develop`, título en conventional commits, cuerpo desde el run doc.
- **Ramas apiladas dependientes → un solo PR** desde la punta; los PRs previos de la cadena se cierran apuntando al consolidado. Ramas independientes, PR propio.
- **La tarjeta no se mueve a revisión**: solo se ofrece `/trello adjuntar --url`. A `En revisión (Revisor Principal)` solo cuando el responsable lo pide (sección 2 de `docs/guias/ESTANDAR-ENTREGA-TRELLO-Y-GITHUB.md`).
- Nunca tokens ni secretos en commits, PRs ni argumentos.
- Comentarios de bots en un PR abierto (`gh pr view <N> --json comments,reviews` + `gh api .../pulls/<N>/comments`, por `gh-read-shunt.sh` si es largo): tratarlos como hallazgos de QA, verificando cada uno.


<a id="detalle-registro"></a>

## Anexo — Step 5: registro de la corrida

Se lee al llegar al Step 5 de `orquestar.md`. El porqué está en [historia del proceso](#historia-del-proceso) (`## Step 5`).

### Run doc

- Archivo `AcmeOrg/docs/runs/NNNN-<slug>.md` (siguiente número libre), con la estructura de `NNNN-ejemplo-run.md`: tarea, decisiones del architect, correcciones del planner (qué se verificó contra el esquema real y por qué importó), si disparó el Step 2.5 y qué decidió el usuario, hallazgos de QA y lecciones de proceso.
- **Con `--en`**: el número es el reservado en el plan de ola (`/worktree`); si no hay, preguntar. **No tocar `INDEX.md`**: la fila la agrega `/worktree sincronizar`. Decir "fila de INDEX pendiente para `sincronizar`".
- Frontmatter YAML: `tipo: run`, `numero: "NNNN"`, `fecha`, `resultado`, `ciclos_qa`, `duracion` ("~28 min"), `tokens` (texto legible con el desglose), `tokens_num` (entero, para el Dataview de `Home.md`), `tokens_fuente` (`"estimado"` salvo que venga de una fuente real de uso), `rama`, `tags` (al menos `[run, api-core, orquestador]`). Wikilinks al run doc anterior y a los ADR/`contexto-negocio/` usados, con ruta desde la raíz del vault (nunca `../`).
- **Dos líneas fijas** al final del resumen *(retro 2026-10-23)*, aunque la respuesta sea 0 o «no»: `Codex: rondas hasta 2 limpias: N` y `Escapó al QA: sí/no (quién lo encontró)`. `retro` las cuenta para medir al coder y al QA. `registrar_corrida.py` sale con 1 si al cuerpo le falta alguna de las dos o la sección `## Reglas que rompí` *(retro 2026-10-27)*.
- Sección `## Máquina` *(el responsable, 2026-10-23)*: la escribe `registrar_corrida.py` con `--recursos $S/recursos.tsv` (lo deja `flujo.sh`): pico de RAM usada, mínimo de RAM libre, CPU media, tiempo esperando cupo o memoria, reintentos y procesos que pasaron de 10 min. Sin archivo, «sin medir».
- Llevar la sección `### Runtime/DI Check` de QA a "Hallazgos de QA", aunque diga "no se activó".
- Sección `## Reglas que rompí` *(2026-10-19)*: se escribe **en el mismo turno en que pasa**, no al cierre. Una línea por caso: qué regla, dónde estaba escrita y por qué no frenó. Sin casos, "ninguna". `retro` las cuenta: 2 de la misma regla piden una barrera, no más texto.
- Nivel 0 y Nivel 1: solo la fila de `INDEX.md` (*fix chico, sin doc de run propio — ver commit `<hash>`*).

### Bitácora de consumo (obligatoria)

**Se genera con `python .claude/tools/orquestar/registrar_corrida.py`** (transcripts de la sesión y subagentes, logs de Codex, JSON de DeepSeek y de `claude -p`), no a mano. `--desde`/`--hasta` acotan la ventana; lo comparable entre corridas excluye el propio Step 5. La fila del orquestador **siempre** sale de acá (`--desde <inicio ISO UTC>`, lee el transcript); `sin medir` solo si el transcript no existe, y se dice por qué en el run doc. Un run doc con `tokens_fuente: "no registrado"` no cierra el Step 5.

Sección `## Bitácora de consumo`, **una fila por cada agente o motor invocado**, nunca un total agregado:

| Paso | Agente / motor | Modelo | Tokens | Duración | Resultado |
|---|---|---|---|---|---|

- Números reales: subagentes de Claude desde su notificación (`subagent_tokens`, `duration_ms`); Codex de su log (`tokens used`); `agy` según su salida. Agente muerto por watchdog: `sin reportar`, nunca estimado por analogía.
- Va **toda** acción que gaste tokens: tablero, `retro`, `system-auditor`, shunts, `code-write.sh`.
- La columna **Modelo** deja ver si el reparto Haiku/Sonnet/Opus funcionó.
- Separar de qué cuenta sale cada fila (Claude, Codex, Google).
- Si la tarjeta tiene estimación PERT, agregar su fila en "Medición: real vs PERT" de `TASKS.md` al cerrarla.

### INDEX.md

Dos lugares: (1) una línea en "Mapa de conocimiento" bajo **cada** tema tocado (crear el tema si no hay); (2) una fila en el libro mayor: Fecha, Tarea, Resultado, Duración, Tokens, Ciclos QA, Rama, Detalle. También si la corrida terminó escalada o frenada.

### Commit en el vault

Run doc, fila de `INDEX.md` y ADR viven en `agentic-harness` (raíz de AcmeOrg): commit aparte (`docs: registrar corrida NNNN`) y push. **Checkout compartido entre sesiones**: nunca `git add -A` ni `git add .`; agregar por ruta y revisar el `git diff` de cada archivo; si trae algo ajeno, parar y preguntar. El pre-commit corre `scripts/validar-vault.py`.

### ADR

Si la corrida tomó una decisión de arquitectura sin ADR (dependencia nueva, cambio estructural, convención transversal), decirlo en el reporte final y preguntar. Si se confirma: `AcmeOrg/docs/adr/`, número reservado en la ola, `estado: Proposed` hasta que mergee el PR que lo implementa. Borrador con `code-write.sh --reference <ADR parecido> --target docs/adr/000N-slug.md --spec "..."`, y **leerlo** antes de mostrarlo.

### Traspaso (último paso, siempre)

`.claude/traspasos/<rama o slug>.md` (no se versiona), de 20 líneas como máximo: qué quedó hecho (commits y PRs), en qué rama y worktree, qué falta y quién lo hace, decisiones del responsable que la próxima sesión necesita y archivos por donde seguir. Sin historia ni razonamiento: eso vive en el run doc. Cerrar el reporte final con: *Para seguir: sesión nueva, "lee `.claude/traspasos/<archivo>` y continúa".*


<a id="historia-del-proceso"></a>

Este bloque conserva el registro histórico completo. Para ejecutar, prevalecen las reglas vigentes y los detalles anteriores; las instrucciones reemplazadas se conservan como contexto.

## /orquestar — texto completo e historia (hasta 2026-09-23)

Copia textual de `orquestar.md` antes de adelgazarlo el 2026-09-23. **No es la instrucción vigente**: manda `.claude/commands/orquestar.md` y sus anexos. Acá queda el porqué de cada regla (fechas, corridas, incidentes). Buscar por `## Step N` con `grep -n`; el archivo pasa las 350 líneas y el shunt bloquea leerlo entero.

Reglas reemplazadas ese día (ver `orquestar.md`): el planner ya no va siempre en Opus (solo pipeline completo); Nivel 1 ya no corre `adversary` ni Codex por defecto; Codex ya no revisa "toda corrida salvo Nivel 0"; lo mecánico va primero a los motores externos y, si cae en Claude, en Haiku.

You are acting as the Orchestrator for the api-core multi-agent pipeline. The task is: $ARGUMENTS

**Target repo**: this command lives in `AcmeOrg/.claude/` (shared across `api-core`, `api-contracts`, `api-people`), not inside any single repo. Unless the task explicitly names a different target repo, **default target is `api-core`**. All `git status`/`git checkout -b`/`dotnet build`/`dotnet test` operations run with working directory set to `api-core/` (a sibling folder of this command's location), not the AcmeOrg root. Every relative path below (`api-core/...`) is relative to the target repo's root (`api-core/`), already written with that prefix. **Excepción: los run docs y los ADRs** — `AcmeOrg/docs/runs/` (con `INDEX.md`, `RETRO-LOG.md`, `GOLDEN-TASKS.md` y `SYSTEM-AUDIT-LOG.md`) y `AcmeOrg/docs/adr/` viven en la raíz de AcmeOrg (repo `agentic-harness`), no en el repo destino *(movidos el 2026-09-16)*.

**Destino en worktree (`--en <ruta>`)** *(added 2026-09-11, trabajo por olas — ver `/worktree`)*: si `$ARGUMENTS` empieza con `--en .worktrees/<repo>--<slug>`, esa carpeta es la **raíz de trabajo** (`<RAIZ>`) de toda la corrida y el repo destino es el `<repo>` de su nombre. Reemplaza a la carpeta principal del repo en **todo**: `git`, `dotnet build`/`test`, `npm` y el diff de los gates del Step 4.4. Lee cada ruta `api-core/...` de este archivo como `<RAIZ>/...`. Los repos de referencia (`api-contracts/`, `api-people/`) se siguen leyendo donde están. Los run docs y los ADRs tampoco siguen a `<RAIZ>`: siempre van a `AcmeOrg/docs/runs/` y `AcmeOrg/docs/adr/`, una sola copia para todos los worktrees. Sin `--en`, nada de esto aplica: `<RAIZ>` es la carpeta del repo destino, como siempre.

**El directorio de trabajo del orquestador NO es la raíz del agente, y por eso hay que verificarlo** *(added 2026-09-21, pasó de verdad)*: el cwd de la sesión se mueve con cada `cd` que hace el orquestador en la terminal, y **el subagente lo hereda**. El 2026-09-21 se lanzó un coder de `api-core` mientras el cwd estaba en el worktree de `web-app`: arrancó parado en el repo equivocado. No rompió nada porque el prompt traía la ruta absoluta y el agente la verificó por su cuenta — pero eso fue suerte de redacción, no una garantía, y el propio agente lo señaló: *"no debería depender de que yo detecte la ruta correcta por texto"*.

Dos cosas, las dos obligatorias:

1. **Antes de lanzar un agente, el orquestador lleva su cwd a la raíz de trabajo de ese agente** (`cd <RAIZ>`), o al menos verifica que coincida. Es una línea y elimina el problema en el origen.
2. **La línea obligatoria del prompt lleva la verificación pegada**, para que el agente tenga con qué atajarlo si el paso 1 falló:

`Raíz de trabajo: <RAIZ> (rama <rama>). **Verificá por ruta absoluta que estás ahí antes de tocar un solo archivo; si tu directorio inicial no coincide, usá la ruta absoluta igual y decilo en tu reporte.** Todo archivo del repo destino que leas, edites, compiles o diffees va bajo esa ruta; la carpeta principal del repo no se toca.`

Es el mismo tipo de fallo silencioso que Codex y Antigravity saliendo con código 0: **nada avisa, y el resultado parece correcto.** Un coder trabajando en el repo equivocado compila bien, pasa sus tests y entrega un reporte impecable — sobre el árbol que no era.

Los agentes no lo saben si no se lo dices — sus `.md` nombran `api-core/` a secas. Con `--en`, **cada** prompt a `architect`, `planner`, `coder`, `coder-web`, `qa` y `adversary` empieza con esta línea, literal: `Raíz de trabajo: <RAIZ> (rama <rama>). Todo archivo del repo destino que leas, edites, compiles o diffees va bajo esa ruta; la carpeta principal del repo no se toca.`

Con `--en` **no se sube la rama ni se abre PR, y tampoco se ofrece** (pedido del responsable, 2026-09-11): la corrida termina en el commit del Step 4.5 más el Step 5. La rama pasa por `/worktree sincronizar` y el push y el PR se hacen solo cuando el responsable los pide.

Follow this sequence exactly. Do not skip steps, do not let two agents talk to each other directly — every hand-off goes through you.

**Structured hand-offs**: each agent outputs a fixed markdown structure — `## Architect Report` (`architect`), `## Plan` (`planner`), `## Coder Report` (`coder` **and** `coder-web`), `## QA Verdict` (`qa`), `## Adversarial Audit Report` (`adversary`). See each agent's `.md` for the exact template. Both `qa` and `adversary` close with `### Result: <PASS | FINDINGS>` — same key, so you parse one thing, not two. Pass these **verbatim** to the next agent — do not summarize, paraphrase, or drop sections. If an agent's output doesn't follow its required structure, that's itself a finding — ask it to reformat before passing it on, rather than trying to fix/interpret a malformed hand-off yourself.

### Step 0 — Check run history
Lee la seccion **"Mapa de conocimiento"** al inicio de `AcmeOrg/docs/runs/INDEX.md` — esa seccion, no el libro mayor completo que va debajo *(added 2026-09-07: la tabla son 47 filas y ~5.6K tokens, con columnas de duracion y tokens que no ayudan a recuperar nada; se leia entera en cada corrida)*. Busca el tema de la tarea, abre **solo** los run docs que el mapa liste para ese tema, y baja al libro mayor unicamente si necesitas el detalle de una corrida concreta.

Si una corrida previa ya resolvio una pregunta de esquema, un patron o una decision de diseño similar, pasasela al architect y al planner en vez de dejar que la re-deriven. No te saltes esto ni en una tarea "simple" — el punto entero es no re-investigar terreno conocido. Si el mapa no tiene ningun tema que encaje, dilo explicitamente: es terreno nuevo, no una excusa para leer todo el libro mayor por si acaso.

**Business context check**: if the task touches domain data, history or a planned use case, also check `contexto-negocio/` (shared vault root). Domain proposals and schema diagrams can already answer catalog/table questions; point architect/planner to the specific file rather than re-deriving it.

**Un pendiente viejo se verifica antes de trabajarlo** *(added 2026-09-09)*: si vas a tomar una fila de `TASKS.md`, un hallazgo de un run doc o una afirmacion de `CLAUDE.md` cuya fecha es anterior a la ultima corrida de `INDEX.md`, **comproba primero que siga siendo cierta** — una consulta MCP, un `grep`, un `git log`. Cuesta segundos; trabajar sobre una nota vencida cuesta la tarea entera. El 2026-09-09 cinco notas distintas resultaron falsas en una sola sesion: el doc del sistema listaba tres skills inexistentes, un hallazgo de seguridad decia "sin trackear" sobre un archivo ya commiteado y pusheado, una migracion figuraba pendiente y estaba aplicada, `api-core/CLAUDE.md` daba por atrasada una base que estaba al dia, y dos items marcados como abiertos ya estaban resueltos. **Siempre la misma forma: el registro envejece mas rapido de lo que se relee.** Cuando la verificacion contradiga la nota, corregi la nota en la misma corrida — si la dejas, el siguiente vuelve a tropezar.

**Open business questions check** *(added 2026-08-18)*: also read `contexto-negocio/PREGUNTAS-NEGOCIO.md` — a living list of business/product decisions someone still needs to make (not technical). If the task touches a question already listed there (e.g. Rol Principal/Vinculado semantics, fields absent from the reference repos' schema, roles/permisos in `api-auth`), surface it to the architect/planner instead of re-deriving or re-asking the user from scratch. If the task's investigation surfaces a *new* business question that isn't yet on that list, add a row before finishing the run (Step 5) — don't let it evaporate into the conversation only.

**Retro cadence check**: also read the last dated entry in `AcmeOrg/docs/runs/RETRO-LOG.md` and count how many runs in `INDEX.md` are dated after it. If that count is 3 or more, mention it to the user as a one-line heads-up before continuing (e.g. "van 4 corridas desde la última revisión de retro — ¿la corro antes o después de esta?"). This is informational, like Step 2.6 — proceed with the requested task either way unless the user says otherwise; don't invoke `retro` yourself unasked.

**System-audit cadence check** *(added 2026-09-07)*: lee la última entrada fechada de `AcmeOrg/docs/runs/SYSTEM-AUDIT-LOG.md` y cuenta cuántas corridas de `INDEX.md` son posteriores. Si van **10 o más** (o si el archivo no existe todavía), avísalo en una línea antes de continuar: "van N corridas desde la última auditoría del sistema — ¿corro `system-auditor` antes o después de esta?". Informativo, como el chequeo de retro: sigue con la tarea pedida salvo que el usuario diga otra cosa, y **no invoques `system-auditor` por tu cuenta sin que te lo pidan**.

Cuando sí se corra, **invócalo con el parámetro `model: fable` del Agent tool** (sobreescribe el `model:` de su frontmatter, mismo mecanismo que el Step 2.7 usa para subir el planner a `fable`). Es una auditoría poco frecuente que decide la salud de todo lo demás — no es donde ahorrar. `system-auditor` no tiene `Write`: cierra su reporte con un bloque de entrada para el log, y **eres tú quien lo agrega** a `SYSTEM-AUDIT-LOG.md`. Lo mismo aplica al bloque `RETRO-LOG entry` de `retro`.

**Chequeo de cuota de los motores externos** *(added 2026-09-21)*: el modo por defecto es `ahorro`, que reparte architect, coders mecánicos, QA secundario y `adversary` a Codex justamente para no gastar el presupuesto de Claude, que es el escaso. Si Codex no tiene créditos, **todo eso vuelve a Claude** y la corrida cuesta varias veces más — conviene saberlo al planificar, no al fallar.

**El fallo es silencioso: `codex exec` sin créditos devuelve `ERROR: Your workspace is out of credits` y sale con código 0.** Quien se fíe del código de salida da por corrida una revisión que nunca ocurrió. Siempre leer el log, nunca el exit code. El 2026-09-21 Codex se agotó a mitad de sesión, después de cuatro corridas exitosas.

Si la corrida va a delegar algo a Codex, confirmarlo antes; si no tiene créditos, decírselo al usuario junto con lo que eso implica en costo, y seguir con Claude.

**Replay-harness check**: check `git log -1 --format=%ai -- .claude/agents/ .claude/commands/` **y también** `git status --short .claude/agents/ .claude/commands/` — las ediciones sin commitear nunca aparecen en `git log` (el 2026-09-07 había 9 archivos de agentes/comandos modificados o nuevos, todos sin commit, mientras `git log -1` seguía diciendo 2026-09-01). Compara contra la `fecha` de la corrida más reciente de `INDEX.md`. If any agent or command `.md` was modified after that date, or shows as modified/untracked (whether via a `retro`-approved fix or a direct edit), tell the user which agent(s) changed and ask: "¿corro primero una tarea dorada (`AcmeOrg/docs/runs/GOLDEN-TASKS.md`) para confirmar el cambio antes de esta tarea nueva, o seguimos directo?" Always ask — don't decide silently either way. If they say yes, run the relevant `/orquestar` pass for that golden task first (report its result plainly, pass or fail) before starting the requested task. If they say no or the task itself is urgent, proceed, but note in this run's Final report that the change is still unverified by replay.

### Step 0.5 — Create a run branch
**Con `--en`, la rama ya existe** — la creó `/worktree crear` — y este paso cambia entero *(added 2026-09-11)*:
- No hagas `git checkout -b`. Verifica que `git -C <RAIZ> branch --show-current` sea `feature/…` o `fix/…`, y que `git -C <RAIZ> log --oneline origin/develop..HEAD` muestre solo commits de esta tarjeta (vacío en un worktree recién creado).
- El chequeo de árbol sucio corre sobre `<RAIZ>`. La carpeta principal del repo puede estar sucia con otro trabajo y no importa, pero **guarda su `git -C <repo> status --porcelain`**: el Step 3 lo compara.
- El párrafo "Dependency on an unmerged prior branch" no aplica: en modo ola una tarjeta que necesita código de otra rama sin mergear estaba en la ola equivocada. Para y díselo al usuario en vez de mergear la otra rama.
- El HARD RULE de verificar que la rama tenga lo que la tarea asume sí aplica igual, contra `<RAIZ>`.

Sin `--en`, lo de abajo sin cambios:

Check `git status`. If the working tree is dirty (uncommitted changes unrelated to this run), stop and ask the user how to proceed instead of mixing their in-progress work into this run's branch. Otherwise, create and check out a new branch following the **org convention** (confirmed 2026-08-14 against the real commit/branch history of `api-contracts` and `api-people` on GitHub — do not invent a different scheme): `feature/<short-slug-en-minusculas-con-guiones>` for new functionality, `fix/<short-slug>` for bug fixes. No run-number prefix (`agent/NNNN-...` was an early convention for this skill and is deprecated — the run number lives in `AcmeOrg/docs/runs/NNNN-....md`, not in the branch name). Base branches in the org are `main`/`develop`/`qa`. All coder edits in this run happen on this branch. Do not push it — that stays a manual, explicit decision by the user.

**Dependency on an unmerged prior branch** *(added 2026-08-18, after 3 runs in one session needed this)*: if the requested task explicitly depends on code that only exists on a different branch not yet merged to `develop` (e.g. "add X to the endpoint built in the JWT-auth branch"), don't silently base the new branch on `develop` and hit missing code later, and don't silently base it on the dependency branch either — ask the user which they want: (a) merge the dependency branch to `develop` first, then branch from `develop` (cleaner history, recommended default), or (b) base this run's branch directly on the dependency branch, accepting that both stay unmerged together for now. If mid-run you discover a dependency that wasn't obvious upfront (e.g. a doc/ADR the architect needed turns out to live only on another local branch), don't treat it as a dead end — merge or cherry-pick the needed commit(s) into the current branch and note it in the run doc, same as you'd note any other mid-run correction.

**HARD RULE — verify the new branch actually has what the task assumes exists, before invoking the architect** *(added 2026-08-19, after the architect ran a full investigation against a branch that silently lacked 5 entities/features the task description referenced as already built — `develop` was stale relative to 2 open, unmerged PRs from the same session)*: never trust conversation memory or the task prompt's own claims about "X already exists" — verify it against the actual branch you just checked out. Immediately after `git checkout -b`, if the task references any specific prior-run artifact by name (an entity, a service, a config value, "the pattern from run NNNN"), do a quick `grep`/`Read` for it on the new branch **before** handing the task to the architect. If it's missing and you know which branch/PR has it (recent run docs / `INDEX.md` / open PRs), merge or cherry-pick it in immediately — don't let the architect (or planner) spend a full pass investigating against a stale snapshot and produce a report full of false "this doesn't exist yet" gaps that then have to be re-run from scratch. This is expensive to catch late (a wasted architect pass) and cheap to catch early (one grep).

**Una medición de referencia sale del mismo commit que el cambio, o no sirve** *(added 2026-09-22, corrida 0057)*: se midió la suite en la carpeta principal (643 tests) y después en el worktree (686), y por un rato pareció que el cambio había agregado 43 tests. No era el cambio: el `develop` **local** estaba 5 commits atrás de `origin/develop`, sin el merge de un PR. Si vas a comparar un "antes" contra un "después" —conteo de tests, tamaño de salida, tiempo—, el "antes" se toma del mismo commit del que sale la rama (`git rev-parse develop` contra `origin/develop`), no de lo que haya en la carpeta principal. Y cuando los números no cuadren, la primera hipótesis es que las dos mediciones no son comparables, no que el cambio hizo algo raro.

**Run this pipeline in parallel with a standalone agent when the two don't depend on each other's output** *(added 2026-08-19)*: when the task has an independent UI piece (`ux-researcher`, a mockup) alongside this backend pipeline, and both start from a design already agreed with the user (not from each other's code — neither needs to read the other's output to begin), launch the standalone agent in the background (`run_in_background: true`) and continue this pipeline in the foreground immediately, rather than waiting for one to finish before starting the other. This only applies when the process genuinely doesn't need to be sequential — if the backend's exact shape (entity/field names, endpoint contracts) isn't settled yet, settle that with the user first, then launch both; a mockup built against an unsettled backend shape will need rework once the real shape lands. Real example: the entity/action use case (2026-08-19) launched the `agente-consola-v3.html` mockup update and this backend pipeline at the same time, both grounded in the same design already confirmed with the user — cut wall-clock time roughly in half versus running them one after the other.

### Step 0.6 — Identificar la tarjeta de Trello ANTES de empezar
*(added 2026-09-08, pedido explícito del responsable — "preguntar al inicio si hay tarjeta o crear una")*: la tarjeta se resuelve al **inicio** de la corrida, no al final junto con el PR. El 2026-09-08 se llegó al Step 4.7 con el PR ya abierto y recién ahí se buscó la tarjeta, contra un export de doce días que mentía en columnas e IDs — trabajo tirado y una pregunta al usuario que podría haberse hecho al principio.

**Consultá el tablero vivo por API, nunca `docs/trello/`.** Ese directorio es un export con fecha, y se desactualiza: al 2026-09-08 listaba una columna `En revisión` que ya no existe (se había partido en `En revisión (Revisor Principal)` y `En revisión (Eder)`), y su columna de IDs tenía colisiones — dos pares de tarjetas distintas compartiendo el mismo id. Sirve para leer notas técnicas, no para apuntar una mutación.

Preguntá al usuario: **¿esta tarea corresponde a una tarjeta existente, o hay que crear una?**
- **Existe:** su título **no se toca** (regla 1 del estándar de entrega). Anotá su id y URL.
- **No existe:** proponé título siguiendo la convención real del tablero — título del PR + `(repo)`, como `Implementar un caso de uso (api-core)` — y esperá aprobación expresa antes de crearla.

Llevá la tarjeta elegida hasta el Step 4.7, en vez de redescubrirla al final.

**Todo acceso al tablero va por la skill `/trello`** (`.claude/tools/trello/trello.py`, desde 2026-09-10): `buscar` para ofrecer tarjetas candidatas, `crear` para la nueva. No escribas Python suelto contra la API ni uses `scripts/trello.ps1`, que no conecta en esta máquina (schannel; detalle en el historial de la guía de entrega). Si `buscar` devuelve muchas candidatas, usa `trello-read-shunt.sh` en vez de leer el resultado crudo (ver [`/shunt`](shunt.md)).

### Step 0.7 — Tiered eligibility check (Nivel 0 / Nivel 1 / pipeline completo)
*(added 2026-08-26, el responsable's explicit design — "a veces cambio color, disposicion, nombre de texto... la mayoria pase por ahi"; refined the same day — "la cosa es gastar lo menos posible si son cambios super simples")*: not every task earns a full `architect` investigation, and not every trivial task even needs a subagent. Default to the lightest tier that's honestly justified; escalate only when the task actually needs it — don't default to full-weight out of caution when nothing here applies, and don't reach for Nivel 0 when you're not genuinely certain it qualifies.

**Nivel 0 — you edit it directly, no subagent at all.** Reserve this for changes with zero logic and zero schema/security surface: a hardcoded string/label/color literal, a log message wording, a config constant, a code comment, a typo fix — the kind of change where "what should this say" has one obvious answer and there's nothing to design, plan, or architecturally verify. You (the orchestrator) make the edit yourself with Edit/Write, same as you would in any non-`/orquestar` conversation. Still required, no exceptions: run `dotnet build` (and the relevant `dotnet test` project if the touched code has coverage) to confirm nothing broke, and still commit + record Step 5 in its lightest form (an `INDEX.md` row, no `NNNN-<slug>.md` — see below). This is not "skip the safety net", it's "the safety net that matters here is a green build, not an architect pass on a string literal".


**Nivel 0 también en web-app, y aplicado de verdad** *(added 2026-09-14, pedido explícito del responsable para desarrollar más rápido)*: una etiqueta o texto, quitar o mover un botón, redirigir un botón a una vista que ya existe, una clase de estilo o un valor de tamaño son Nivel 0 — los hace el orquestador directo en 2-3 minutos, no un coder que tarda 10-15 porque arranca leyendo el código desde cero. Real: la etiqueta "Resuelto" → "Cerrado" (Nivel 0, 2 min) frente a quitar la casita del rail y redirigir una vista existente (se mandó a un coder, ~10 min). Red de seguridad de Nivel 0 en web-app, en lugar de `dotnet build`: `npx tsc -b`, `npx eslint` sobre los archivos tocados y `npx vitest run` de los tests que los cubren (si un test existente referencia el texto o el botón, se actualiza en el mismo cambio). Deja de ser Nivel 0 si el cambio toca estado, navegación con parámetros, datos o un contrato con api-core.

**Juntar pedidos antes de lanzar, en demos en vivo** *(added 2026-09-14, mismo pedido)*: cuando el responsable va pidiendo ajustes seguidos mientras mira la pantalla, no lances un coder por cada mensaje ni le mandes cambios a uno que ya está trabajando (cada cambio a mitad de camino lo obliga a re-planear). Espera a que cierre la idea (un minuto, o hasta que diga "dale"/"ya"), agrupa los pedidos, sepáralos en Nivel 0 (los haces tú) y cambios con forma (un coder por cambio independiente, en paralelo — ver Step 3), y lánzalos de una vez. Excepción: un bug que bloquea la demo se lanza enseguida.
**Nivel 1 — fast-path** (skip Step 1 — architect — only, go straight to Step 2 with the task as-is): the change is cosmetic/mechanical but still has *some* real shape to get right — a status/color **mapping** (multiple cases, not one literal), a field rename that touches a DTO other code depends on, a one-line bug fix that doesn't touch schema/data-access/auth/concurrency, reordering/adding a field to an existing response. The defining trait: there's no real "which pattern should this follow" question — the pattern is already obviously the one right there in the file being touched — but it's still real enough to want planner+coder+QA's eyes on it, just not a dedicated architect investigation.

**Never Nivel 0 or Nivel 1 — always run the full sequence**: new endpoints, any schema/migration change, anything touching `ADR-0001`'s entidades propias y externas boundaries, auth/JWT/roles, concurrency-sensitive patterns (claim-a-row, single-active-X), or anything you're genuinely unsure how to classify. When in doubt, run the full pipeline (or at least Nivel 1) — these lighter tiers are for the obviously-safe majority, not a default you talk yourself into for something borderline. If you're not sure whether something is Nivel 0 or Nivel 1, pick Nivel 1 — the cost difference between them is small (one subagent call), the cost of a Nivel-0 change turning out to need real judgment is not.

**What Nivel 1 skips vs. keeps**: skips Step 1 (architect) only. Step 2 (planner) still runs — tell it explicitly this is fast-path so it keeps the plan proportionally short — and Step 3 (coder/coder-web) and Step 4 (QA, Nivel 1 testing tier) still run unchanged; Step 3.5 y los tres gates del Step 4.4 aplican igual que en el pipeline completo (la corrida 0037 fue Nivel 1 y sí corrió `adversary`); those are the safety net that protects the reason `/orquestar` exists in the first place — a 2026-08-15 incident where code was edited directly in chat left no ADR, no `agent-runs` entry, and skipped the planner's schema verification and QA's checklist entirely. Bypassing QA/schema-verification is the actual thing that's not allowed here, not "always spend a full architect pass on a label rename". Step 2.5/2.6/2.7 naturally no-op for a Nivel 1 task (its Risk Flags will read "no") — don't force them. Step 4.6 (security review) is still the orchestrator's judgment call for Nivel 1: skip it explicitly (state why in the Final report) only when the change plainly has no PII/auth/data surface. Nivel 0 skips security-review outright — there's no code path a security review would meaningfully evaluate in a string literal.

**Step 5 stays mandatory at every tier, in its proportional form.** For Nivel 0 or Nivel 1, a full run doc is disproportionate — use the lightweight `INDEX.md`-only row this project already does for small fixes (e.g. "*(fix chico, sin doc de run propio — ver commit `<hash>`)*", see runs 0009/0022/0024's sibling small-fix rows in `INDEX.md`) instead of writing `NNNN-<slug>.md`. This is still Step 5, just its proportional form — the "run is not done until Step 5 is done" rule from Step 5 below still applies in full, at every tier including Nivel 0.

### Step 0.8 — REQ confirmado (Spec-Driven Development, solo pipeline completo)
*(added 2026-09-18, decisión explícita del responsable, cierra las 3 preguntas abiertas de la tarjeta `Hsg8gz21`)*: si la tarea califica para el **pipeline completo** (ni Nivel 0 ni Nivel 1, ver Step 0.7), verifica primero si tiene un REQ **confirmado** en `requisitos/` (índice en `requisitos/README.md`, carpeta local sin git). Si no lo tiene, para antes del Step 1 y dile al usuario: falta el REQ, ¿lo redactamos con la skill `/requisitos` antes de seguir, o esta tarea entra sin REQ por excepción? No lo asumas ni lo saltees en silencio.

Nivel 0 y Nivel 1 **no** requieren REQ — sería desproporcionado exigirle spec formal a un fix cosmético o de una línea.

**Si el REQ cambia de versión mientras el coder ya está trabajando sobre la versión vieja**: no relances el planner por tu cuenta. Para la corrida y repórtale al responsable qué versión estaba implementando el coder y qué cambió — mismo criterio que ya aplica cuando el coder o QA encuentran que el plan mismo está mal (Step 2, "stop and report to the user instead of silently sending it back to the planner"). el responsable decide si el coder sigue, se descarta lo hecho, o se re-plani­fica.

### Step 0.9 — Contrapeso de negocio (pipeline completo, antes del architect)
*(added 2026-09-21, pedido del responsable)*: en el pipeline completo, antes de gastar una pasada de
`architect`, corre [`/negocio`](negocio.md) sobre la tarjeta o el REQ. Responde una sola
pregunta —si esto resuelve el caso de uso al usuario y le ahorra trabajo al agente humano— y
devuelve objeciones, alcance minimo y preguntas abiertas. El `planner` ya verifica esquema y
viabilidad; esto es el contrapeso que faltaba del lado del negocio.

Si el veredicto es "no ahora", para y reportaselo al responsable con las objeciones: no arranques el
pipeline igual. Si es "vale con condiciones", esas objeciones viajan como contexto al
`architect` y al `planner`. Nivel 0 y Nivel 1 no lo necesitan: un fix cosmetico o de una linea
no cambia como se atiende un caso de uso.

### Step 1 — Architect
Invoke the `architect` subagent (`.claude/agents/architect.md`) with the task. Its job: find the closest equivalent pattern in `api-contracts` or `api-people` and recommend how to build this consistently with them.

Wait for its output before continuing. If it proposes concrete design decisions beyond "which pattern to follow" (e.g. specific tech choices like adding a new package), carry those forward as *proposed* decisions for the planner to confirm or reject — don't treat them as final yet.

### Step 2 — Planner
Invoke the `planner` subagent (`.claude/agents/planner.md`) with the task plus the architect's full output. Explicitly instruct it to:
- Confirm or correct every decision the architect proposed.
- Verify claims against the real DB schema via the `contracts-db`/`people-db` MCP connectors rather than trusting the reference-repo pattern blindly (this caught real bugs in the first pilot — schema name mismatches, nullable columns, unnecessary joins — keep doing it).
- Cross-check against `AcmeOrg/docs/adr/` — flag if the plan would touch anything ADR-0001 governs (writes to external data, schema changes, field typing) so Step 2.5 can catch it.
- Produce a numbered task list and a QA test matrix (functional cases, response-contract checks, edge cases).

This is the planner's only pass — it does not get invoked again later in this run. If the coder or QA later find the plan itself is wrong (not just misimplemented), stop and report to the user instead of silently sending it back to the planner.

### Step 2.5 — Human checkpoint for risky plans
Check the planner's `### Risk Flags (for orchestrator Step 2.5)` section directly — don't re-derive this yourself, the planner already evaluated it. If any flag is "yes": **stop and present the plan to the user for explicit approval before continuing to Step 3.** Summarize what's risky and why in 3-5 lines — don't just dump the whole plan and ask "ok?". Wait for an explicit yes. If none apply (typical case: read-only endpoint, no schema change), continue straight to Step 3 without pausing.

### Step 2.6 — Cost heads-up for large tasks
Before Step 3, check the planner's `### Task List` size and compare against `AcmeOrg/docs/runs/INDEX.md`'s Tokens column for any prior run of similar shape (a full endpoint = light, a structural refactor or multi-file change = heavy — run 0003's layered-project split cost ~167K tokens as a reference point). If this task looks similarly large, mention the estimated cost as a one-line heads-up to the user before continuing (e.g. "Esto luce parecido a la separación por capas, que costó ~167K tokens — sigo salvo que digas otra cosa"). This is informational, not a blocking gate like Step 2.5 — proceed after saying it unless the user actually objects. Skip this step silently for small/typical tasks (a single new endpoint, a small fix).

### Step 2.7 — El planner corre en Opus 5.5
*(el responsable, 2026-09-22: "sube el planner a opus 5.5"; reemplaza la escalación opcional a Opus que se ofrecía solo con riesgo marcado)*: el `planner` tiene una sola pasada, sin revisión — es el punto único de falla que más vale pagar, y el que sostiene el piso de 85 en coherencia y modelo de datos. Por eso su frontmatter fija `model: claude-opus-5-5` y ya no se pregunta caso por caso. En `calidad` con Nivel 3 puede subirse a `fable` con el parámetro `model` del Agent tool. Never escalate `architect`, `coder`, or `qa` this way — their mistakes are already caught by a downstream role, so the redundancy substitutes for a stronger model there.

### Step 3 — Coder (elige cuál según qué toca el plan)

**Tres palancas más de tiempo, medidas en la corrida del 2026-09-15** *(el responsable: "y se puede hacer más rápido?")*. Esa corrida costó ~60 min de reloj (79 min de cómputo de agentes) para un rename en dos repos con cambio de contrato, edición de migración y baja de 4 columnas. De dónde se sacan los minutos, en orden de impacto:

1. **Decidir TODO antes de lanzar la primera ola.** Es la grande, y el cuello de botella es el orquestador, no los agentes. En esa corrida se lanzó el rename y la decisión de qué borrar llegó después; como la limpieza tocaba los mismos archivos, tuvo que esperar a que el rename terminara — 14 min en serie por repo, ~28 en total. El orden correcto es **investigar todo → decidir todo con el usuario → lanzar una sola ola**, no investigar → lanzar → decidir → lanzar otra vez. Si hay un inventario, un Step 2.5 o cualquier aprobación pendiente que vaya a tocar los mismos archivos que la parte mecánica, se resuelve **antes**.
2. **Un solo coder por repo cuando dos trabajos comparten archivos.** Rename y limpieza tocaban `CreateEntityCommandHandler`, `EntityController` y medio `src/` de web-app. Dos coders en serie sobre el mismo conjunto de archivos cuestan más que uno solo haciendo ambas cosas (~10 min por repo). Paralelizar es por defecto, pero **compartir archivo es la excepción**: ahí se junta, no se encola.
3. **Partir un rename grande por carpeta.** 46 archivos en un coder fueron 21 min; tres coders por área (`features/cases`, `features/agent-console`, `features/messages` + `infrastructure`) lo bajan a ~8-10. Requisito para que no se rompa: escribir la **tabla de nombres viejo → nuevo antes de lanzar** y dársela idéntica a los tres, porque los imports cruzan carpetas.

**Lo que NO se recorta para ganar tiempo**, y en esa corrida se demostró por qué: la verificación contra la base con datos reales (probó que el bug de la migración era real — 14 filas ya referenciaban esas relaciones), el contraste del diff contra `git status`, y QA + `adversary` sobre cualquier cosa que borre columnas. En esa misma corrida **el `architect` y el `planner` alucinaron, por separado, un panel de UI que no existe** y sobre esa base recomendaron conservar dos columnas; sin la verificación propia del orquestador (`grep` devolvió 0 ocurrencias) se habría decidido sobre un reporte falso. El reporte de un agente no es evidencia.

**Adelantar los coders sin esperar al planner cuando el alcance ya está especificado** *(added 2026-09-15, pedido explícito del responsable: "no puedes demorar menos tipo haciendo mas cosas a la vez?" y, al ver el resultado, "siempre aplicar asi las corridas en orquestar para evitar demorar tanto")*: el Step 2 es un cuello de botella innecesario para la parte **mecánica** de una corrida — un rename, una ruta que cambia, un fix ya descrito con `archivo:línea` por el architect o por una revisión de Codex. En esos casos no encadenes planner → coder: lanza los coders de lo mecánico **de una vez** y deja que el planner corra **en paralelo**, ocupándose solo de lo que necesita juicio y aprobación humana (qué código muerto se elimina, cómo se edita una migración, cualquier cosa que dispare el Step 2.5).

Receta, en orden:
1. **Fijá el contrato antes de lanzar nada.** Si el cambio cruza repos, la firma exacta (ruta, nombres, tipos) se decide primero y se le escribe a cada coder como "CONTRATO FIJO, no lo negocies". Sin eso, paralelizar produce dos mitades que no encajan.
2. **Repartí por archivo, con dueño exclusivo.** Cada prompt lista explícitamente **qué archivos son suyos** y **cuáles tiene prohibido tocar**, nombrando al otro coder como dueño. Un archivo, un coder.
3. **Lanzá todos los coders de lo mecánico en el mismo mensaje**, en background.
4. **El planner corre a la par**, con el alcance recortado a lo que sí requiere diseño.

**Condición para que esto sea seguro, y no es negociable:** el architect ya verificó el patrón y el contrato no se va a mover. Si el planner pudiera contradecir lo que el coder está escribiendo en ese momento, ese pedazo **no** se adelanta — va después del plan, como siempre. Tampoco se adelanta nada que toque esquema sin pasar antes por el Step 2.5.

Medición real de la corrida que originó esta regla (2026-09-15, rename a Entity·Action·Event en dos repos): estimada en ~40 min encadenando, cerró en ~20 — 4 coders (2 de api-core, 2 de web-app) arrancaron mientras el planner y el inventario de código muerto todavía corrían.

**Repartir el gasto entre cuentas, y no confundirlo con eficiencia** *(added 2026-09-15, pregunta del responsable: "¿por qué le sale más barato, es porque tenemos tantos agentes?")*. No: **los tokens de Codex y de Antigravity salen de otras cuentas** (ChatGPT y Google), no de la de Claude. Delegarles trabajo mueve el gasto de un presupuesto a otro; no lo reduce en abstracto. Dos aclaraciones que evitan decidir mal:

- **La cantidad de agentes no multiplica el costo.** Cinco coders en paralelo gastan lo mismo que cinco en serie: lo que cambia es el tiempo de pared, no los tokens.
- **Sí hay una parte real de eficiencia**, pero es chica y tiene explicación: un `coder`/`coder-web` arranca leyendo `CLAUDE.md`, su propio `.md` de agente, el mapa de la consola y los archivos del proyecto. Codex arranca solo con la tarea escrita en el prompt. Por eso una tarea comparable le sale más barata en tokens absolutos (54K contra 63-338K de los coders propios en la corrida del 2026-09-15).

**Regla acordada — un coder de cada motor, en paralelo** *(el responsable, 2026-09-16: "trata de balancear, quiero que se haga rápido pero bien; quizá 3 coders, uno de cada uno"; reemplaza el orden estricto Codex → Antigravity → Claude que se escribió una hora antes)*: cuando la corrida tiene 2 o 3 cambios independientes, se reparten **por naturaleza de la tarea**, uno por motor, todos a la vez:

| Motor | Qué le toca | Cómo |
|---|---|---|
| **Codex** | Mecánico con criterio verificable y un archivo con dueño: plomería de un campo, renombres, un fix ya descrito con `archivo:línea` | `codex exec --sandbox workspace-write`, condiciones en `/codex` |
| **Antigravity** | Visual y de estilo dentro de componentes: clases, tokens, jerarquía, pasadas de color | `agy --model gemini-3.1-pro-high --mode accept-edits --print="..."`; el prompt nombra los archivos prohibidos igual que a un coder propio |
| **code-write** (Antigravity, motor "shunt") | Mecánico y acotado a **un solo archivo nuevo o reescrito completo** a partir de spec + archivo de referencia (ej. un test que sigue el patrón de otro, un DTO calcado de uno existente) — no para archivos que ya existen con historia propia para editar en el medio | `bash ~/.claude/scripts/code-write.sh --spec "..." --reference <archivo> --target <archivo>` (ver [`/shunt`](shunt.md)); en modo plan, el script escribe a disco, no `agy` |
| **Claude** (`coder`/`coder-web`) | Lógica con estado que cruza varios archivos con dependencias, contratos entre capas, y lo que exige las reglas de `CLAUDE.md` (aislamiento de sesión, agregación sobre colecciones) | Subagente nombrado, como siempre |

**`code-write` no reemplaza QA/adversary, los adelanta** *(added 2026-09-18, decisión explícita del responsable al pedirlo)*: es un primer borrador barato para el caso angosto de "archivo nuevo calcado de uno existente", y ese borrador pasa por el mismo Step 4+ (QA, `adversary`, contraste contra `git status`) que cualquier otro coder — no es un atajo que salte el pipeline.

**Todo motor externo en segundo plano se lanza vigilado** *(2026-09-16, el responsable: "eso no puede pasar")*, porque en la corrida 0047 Codex quedó 15 minutos colgado esperando entrada por consola sin que nadie lo notara, y a la pregunta "¿cuánto falta?" se respondió con una estimación en vez de mirar: (1) **entrada cerrada** con `< /dev/null`; (2) **tope de tiempo** con `timeout` (p. ej. `timeout 20m codex exec ...`), así un cuelgue termina solo; (3) **a los 60 segundos, leer el log**: si dice `Reading additional input from stdin`, no crece o no aparece el archivo de salida, cortarlo y relanzar enseguida; (4) **nunca responder "cuánto falta" sin mirar primero** el log o el estado real del proceso.

> [!WARNING]
> **(5) NUNCA `&` al final del comando.** El background lo da el harness (`run_in_background: true`), y nada más. Un `&` dentro de un comando ya lanzado en background hace que el padre termine y **se lleve al hijo**: el log queda con dos líneas, el exit code dice 0 y el `git status` vacío es lo único que lo delata. Está en la tabla de las cuatro pérdidas del 2026-09-15 y **se repitió igual en la corrida 0057**, costando dos lanzamientos — por eso ahora está acá, en el párrafo que se lee justo antes de lanzar, y no solo en una tabla de lecciones.

**Dos motores externos sobre el mismo árbol no distinguen su diff del ajeno** *(added 2026-09-22, corrida 0057)*: se lanzaron dos Codex en paralelo sobre el mismo worktree, con carpetas disjuntas declaradas en cada prompt. Respetaron el alcance —ninguno tocó la carpeta del otro— pero **los dos reportaron mal su propio trabajo**: el de `api-core.IntegrationTests` cerró diciendo *"No modifiqué archivos: aparecieron cambios concurrentes antes de mi escritura"* después de cambiar 11 archivos y 88 sitios; el de `api-core.Tests` dijo que de 17 sitios solo 1 era suyo. Cada uno vio las escrituras del otro en el árbol y las contó como ajenas a su propia edición.

Consecuencias prácticas, ninguna negociable:
- **El conteo de "cuánto se hizo" lo pone el compilador o el diff, nunca el reporte del agente.** En 0057 fue el `dotnet build` el que dijo que faltaban 34 advertencias; los dos reportes eran inservibles para eso.
- Si hace falta que el agente sepa cuánto hizo, se le da un **árbol propio** (`isolation: 'worktree'` en el workflow, o un worktree por motor) o se corren **en serie**.
- Esto **no** aplica a los `coder`/`coder-web` de Claude, que reportan sobre sus propias ediciones, no sobre el árbol.

**Todo prompt de coder externo (Codex, Antigravity, `code-write.sh`) lleva la regla de comentarios** *(added 2026-09-23, pedido del responsable)*: los motores externos no leen el playbook, y en #<n>/#<n> el 19% de las líneas agregadas eran comentario. Va literal, junto a la nota de `rg`: *"Comentarios: solo el porqué no obvio, en 1-3 líneas. Sin historia, fechas ni justificaciones para el revisor: eso va en tu reporte."* Detalle en el playbook, sección 28.

**`rg` (ripgrep) no está instalado en esta máquina** *(added 2026-09-22)*: Codex lo intenta por defecto y falla con `CommandNotFoundException`. Va como nota de entorno en el prompt de cualquier motor externo: *"en esta máquina NO está instalado `rg`; usá `grep -rn` o `findstr`"*. Si un motor no tiene cuota, su parte pasa al siguiente que pueda hacerla; si ninguno externo puede, a Claude, **y se dice en el reporte final**. Los diffs de Codex y Antigravity se contrastan contra `git status` y se verifican igual que los de un coder propio. **Lo que no se recorta por velocidad:** QA y la verificación del diff siguen en toda corrida. Motivo del cambio: el presupuesto de Claude es el escaso (en la 0047 dos `coder-web` gastaron ~329K y ~218K tokens), pero mandar todo a un solo motor externo pierde calidad y, en serie, velocidad.

**Trello y los PRs se quedan en el orquestador para el contenido — no para la lectura mecánica** *(actualizado 2026-09-18, ver [`/shunt`](shunt.md))*: qué va en el título, la descripción, los miembros de una tarjeta o el cuerpo de un PR lo sigue decidiendo Claude — para eso ya tiene el contexto de la corrida en la conversación, y transferírselo a otro motor costaría más que escribirlo él mismo (esto no cambió). Lo que sí se delega es la parte que **no** necesita ese contexto: leer salidas grandes de solo lectura — `buscar`/`listar --desc`/`tablero` de Trello, `pr diff`/hilos de comentarios/checks de GitHub — va por `trello-read-shunt.sh`/`gh-read-shunt.sh` en vez de entrar cruda al contexto de Claude. Las escrituras ya decididas por Claude (`trello.py crear/actualizar/...`, simulación y después `--aplicar`) siguen corriendo directo: su salida ya es corta por diseño, pasarla por otro motor no ahorraría nada. `gh pr create`/`merge`/`close` nunca se delegan — es la única escritura de este grupo sin el gate mecánico de `--aplicar` que tiene Trello, y correrla fuera del Bash tool de Claude se saltaría `git-guard.sh`.

**Modos de presupuesto** *(el responsable, 2026-09-16: "dale prioridad a codex y antigravity, pq el claude se me está acabando"; "codex siempre debe quedar en cero")*. La corrida se lanza con `--modo <ahorro|normal|calidad>`; **sin flag, `ahorro`**, hasta que el responsable diga otra cosa. **Codex se gasta primero y hasta agotarlo**: cuota de Codex que sobra al final del período es presupuesto perdido. Cuando Codex responde límite de uso, su parte pasa a Antigravity, y solo después a Claude.

| Paso | `ahorro` (por defecto) | `normal` | `calidad` |
|---|---|---|---|
| Planner | `codex exec -s read-only` con `.claude/agents/planner.md` como instrucciones. Si hace falta leer bases por MCP (Codex no las tiene), `planner` de Claude (Opus 5.5, Step 2.7) | `planner` de Claude | `planner` de Claude (Fable si es Nivel 3) |
| Coders | Codex todo lo que no sea visual, **incluso cambios que cruzan archivos** (una tarea `.md` por coder, archivos con dueño exclusivo); Antigravity lo visual | Un motor por cambio (tabla de arriba) | `coder`/`coder-web` de Claude + motores externos |
| QA | Comandos por shell (`tsc`/`eslint`/`vitest` o `dotnet build`/`test`) + `codex exec review --uncommitted` + Antigravity si toca UI | `qa` de Claude + Codex | `qa` de Claude + Codex + Antigravity |
| Adversary | `codex exec -s read-only` con `.claude/agents/adversary.md` como instrucciones, solo si la corrida toca estado, concurrencia, datos o seguridad | `adversary` de Claude | `adversary` de Claude |
| Claude hace | Orquestar, verificar cada diff y hallazgo contra el código, medir en Chrome (solo Claude maneja el navegador), hablar con el responsable, run doc, commit | Lo anterior + los agentes marcados | Todo |

En `ahorro`, un subagente de Claude solo se lanza si ningún motor externo puede hacerlo o no tiene cuota, **con `model: sonnet`** (salvo el `planner`, que va en Opus 5.5 — Step 2.7), y el reporte final dice cuál y por qué. Lo que no baja en ningún modo: verificar el diff contra `git status`, la suite completa antes del commit y la vigilancia de los motores externos (párrafo anterior).

**Antes de lanzar un coder de Claude, preguntarse si es un calco** *(added 2026-09-21)*: un archivo nuevo que copia la forma de otro que ya existe —un handler de catálogo igual al de `EntityState`, un test que sigue el patrón de su hermano, un DTO calcado— **no necesita un agente que lea el proyecto entero**. Va por `code-write.sh` (spec + archivo de referencia), y su salida pasa por el mismo Step 4 que cualquier otro coder.

Caso real de la corrida 0054, que se perdió: `ListEntityQuery`, `ListEntityQueryHandler`, `ListEntityQueryHandlerTests` y `EntitySeedTests` son los cuatro calcos literales de los de `EntityState`/`EntityType`, y fueron a coders de Claude de 90K y 125K tokens. El motivo de fondo está unas líneas más arriba: un coder propio arranca leyendo `CLAUDE.md`, su `.md` de agente y el proyecto; un motor externo arranca solo con el prompt.

**Acotar el alcance de cada coder** *(added 2026-09-15, el responsable: "si esta bien mejora eso")*. El coder más caro de esa sesión fueron **338K tokens**: el rename de 46 archivos de web-app en un solo agente leyendo todo desde cero, 21 minutos. Partirlo por carpeta (`features/cases`, `features/agent-console`, `features/messages` + `infrastructure`) cuesta parecido en total pero termina en un tercio del tiempo — y sobre todo, **un coder que se equivoca cuesta un tercio de retrabajo**. Requisito para que no se rompa: la tabla de nombres viejo→nuevo se escribe **antes** y se les da idéntica a los tres, porque los imports cruzan carpetas.

**El prompt del coder lleva la lista de archivos del plan, no solo la tarea** *(added 2026-09-22, medido en web-app)*. El shunt protege de leer un archivo grande, pero **no de leer muchos chicos**: en `web-app/src/features/agent-console` hay 96 archivos y 14.533 líneas, y solo 8 pasan de las 350 líneas que el hook bloquea. Los otros 88 entran enteros sin que nada avise. Ahí están los coders de 259K y 198K de la corrida 0055 — no en la salida de los comandos, que en web-app es de 1.2K caracteres el build y 245 el `vitest`.

El planner ya nombra los archivos que hay que tocar. Esa lista va **dentro del prompt del coder**, así:

- `Archivos del plan:` los que va a editar, con su ruta exacta.
- `Para entender el patrón:` los de referencia que sí conviene leer enteros (el handler hermano, el test que se calca).
- Y una frase: *no abras el resto del feature para "tomar contexto"; si te falta un archivo, léelo y decí en tu reporte cuál y por qué*.

**La prohibición no es leer de más, es leer de más en silencio.** Si la lista del plan está incompleta, el coder tiene que ampliarla — pero que quede escrito, porque es la única forma de que el planner mejore la próxima. Por eso el `## Coder Report` lleva `Archivos leídos fuera de la lista` (ver `coder.md`/`coder-web.md`): vacío es lo normal, con contenido es una corrección al planner, nunca un reproche al coder.

**No repetir trabajo: las cuatro pérdidas del 2026-09-15 y cómo se evitan** *(added 2026-09-15, el responsable: "ya dale tambien eso no debe pasar de nuevo")*. Ninguna fue un misterio; las cuatro tienen causa identificable:

| Lo que se perdió | Causa | Cómo se evita |
|---|---|---|
| Dos agentes alucinaron un panel de UI que no existe, y el orquestador tuvo que verificarlos | Citaron `archivo:línea` sin haber corrido la búsqueda | Ya corregido en `architect.md` y `planner.md` por la retro de ese día |
| `security-review` revisó los `.md` del repo de agentes en vez del código de la corrida | El skill calcula su diff contra `origin/HEAD` desde la carpeta principal y **no se puede acotar** | **En modo `--en`, hacer el gate de seguridad a mano** sobre el diff real del worktree: autorización de los endpoints tocados, SQL literal vs interpolado, y qué datos destruye una migración. Decirlo así en el reporte |
| Dos intentos de arrancar los servidores de desarrollo | Se usó `nohup ... &` **dentro** de un comando en background: el proceso padre terminó y se llevó al hijo | Lanzar el proceso con el background del harness, **sin `&` ni `nohup`**, y esperar con un `Monitor` que chequee el puerto |
| Un intento de `agy` con la sintaxis mal | El prompt suelto hace que el CLI tome `--model` como prompt, ignore el resto y **salga con código 0** | Ya documentado en [`/antigravity`](antigravity.md): el prompt va pegado al flag |

La forma común de las cuatro: **algo falló en silencio y pareció haber funcionado**. Cuando un comando devuelve éxito, conviene verificar que hizo lo que se esperaba, no que no dio error.

**Codex también puede ser coder, no solo revisor** *(added 2026-09-15, primera vez que escribe código en este proyecto)*: `codex exec --sandbox workspace-write` le deja escribir en el worktree. Funciona, con condiciones estrictas:
- **Un archivo con dueño exclusivo**, nunca un cambio que cruce varios con dependencias entre sí.
- **Criterio objetivo y verificable** ("que no quede ninguna clase `dark:` en este archivo"), no una decisión de diseño.
- El prompt le nombra **explícitamente qué archivos tiene prohibido tocar** y quién es el dueño de cada uno, igual que a un coder propio.
- Su diff se contrasta contra `git status` igual que el de cualquier coder. En la primera prueba respetó su alcance y lo declaró con honestidad ("Modifiqué únicamente AccountTabs.tsx y su test"), pero eso se verifica, no se asume.

Real: el 2026-09-15 reescribió `getCasoTheme` en `AccountTabs.tsx` para sacarle la variante `dark:` de Tailwind, dejó un test que rechaza que alguien la vuelva a meter, y corrió sus tres comandos de verificación. *(La skill `/codex` todavía dice que Codex "no escribe código, el arreglo lo hace el coder de /orquestar" — esa línea quedó vieja y hay que actualizarla.)*

**Varios coders en paralelo, por defecto** *(added 2026-09-14, pedido explícito del responsable: "siempre que se pueda debes usar varios coders así en paralelo, para ahorrar tiempo")*: antes de lanzar un solo coder, parte el plan en cambios independientes. Si hay 2 o más que tocan funciones o archivos distintos, lanza **un coder por cambio a la vez** (`run_in_background: true`, todos en el mismo mensaje), no uno detrás del otro. Cada prompt declara **qué funciones/archivos son suyos y cuáles no tocar**; si dos cambios comparten archivo, se asignan regiones distintas y se exige releer el archivo justo antes de cada Edit. Un solo coder solo cuando los cambios dependen entre sí (uno necesita el código del otro) o tocan la misma función. Si llega un cambio nuevo mientras un coder trabaja y es independiente, va a un coder nuevo en paralelo, no a la cola del que ya corre. Paralelizar no recorta tests: cada coder escribe los tests de su cambio.
#### Step 3.1 — Delegar el medio mecánico a un workflow *(added 2026-09-22, pedido del responsable)*

Cuando el plan ya está cerrado y se parte en **2 o más cambios con archivos disjuntos**, el tramo coder → QA + adversary → fix no necesita que vos lo orquestes paso a paso: es siempre la misma forma. Va al workflow guionado `orquestar-medio` (`.claude/workflows/orquestar-medio.js`).

**Qué gana, y qué no.** No baja tokens: son los mismos agentes leyendo lo mismo. Gana dos cosas concretas:
- **Tiempo.** Hoy esperás a que terminen *todos* los coders para recién lanzar QA. El workflow usa `pipeline()`: el cambio A entra a revisión apenas A termina, mientras B todavía escribe. Contra corridas de 3 y 6 horas eso pesa.
- **El watchdog.** Cada paso tiene un borde definido en vez de una espera abierta en silencio — que es exactamente lo que mató 5 coders el 2026-09-21.

**Lo que NO le pasás, porque no puede decidirlo:** triage Nivel 0/1/2, la rama y el worktree, la tarjeta de Trello, el reparto de motores (Codex/Antigravity/`code-write.sh`), el commit, la verificación del diff contra `git status`, las migraciones, el run doc y la bitácora de consumo. Todo eso sigue siendo tuyo, antes y después. El workflow corre el medio, no la corrida.

**Cómo se invoca** — `Workflow` con `name: "orquestar-medio"` y `args`:

```json
{
  "raiz": ".worktrees/api-core--slug",
  "comandoBuild": "dotnet build",
  "cambios": [
    { "id": "entity-id", "titulo": "...", "agente": "coder",
      "archivos": ["Domain/Entities/Core/Entity.cs", "..."],
      "referencia": ["Domain/Entities/Core/Plantilla.cs"],
      "instrucciones": "<el tramo del plan que le toca>",
      "conAdversary": true }
  ]
}
```

`archivos` es la lista de propiedad **exclusiva** de ese cambio — el prompt se la declara al coder y le dice que hay otros trabajando en paralelo sobre la misma carpeta. Si dos cambios comparten archivo **no van en el mismo workflow**: eso es un solo coder, como siempre.

**Lo que devuelve:** por cambio, la entrega del coder, los hallazgos, y `estado` en `CERRADO` / `SIN_CERRAR` / `BUILD_ROJO`. `requierenDecision` lista los que se quedaron sin cerrar tras los 2 ciclos (el mismo presupuesto del Step 4) — esos los mirás vos, no los cierra solo.

**Cuándo NO usarlo:** Nivel 0 y 1, un solo cambio, cambios que dependen entre sí, o cuando el reparto de motores manda el trabajo a Codex/Antigravity/`code-write.sh` en vez de a un coder de Claude. Corre en background: te avisa cuando termina, y `/workflows` muestra el avance en vivo.

---

Invoca el subagente **nombrado** que corresponda — por ese nombre exacto, nunca el agente genérico — con el plan final del planner como única fuente de verdad. Implementa, verifica que compile, y reporta exactamente qué cambió.

- El plan toca **backend .NET** (`api-core/`, `api-contracts/`, `api-people/`, `api-auth/`, `api-delivery/`) → `coder` (`.claude/agents/coder.md`).
- El plan toca **`web-app/`** (React/TypeScript) → `coder-web` (`.claude/agents/coder-web.md`).
- El plan toca **ambos** → invoca los dos, cada uno con la parte del plan que le corresponde, y consolida los dos `## Coder Report` en uno antes de pasárselo a QA. No le des el plan entero a uno solo.

*(added 2026-09-07: las corridas 0029 y 0032 editaron `web-app` con el `coder` de backend, cuyo prompt es 100% C#/EF Core — las reglas de frontend de `CLAUDE.md` (agregación sobre colecciones, aislamiento de sesión, decodificación de JWT) no tenían ningún agente que las ejecutara.)*

**El coder compila; las suites las corre QA, una sola vez** *(added 2026-09-21, medido en la corrida 0054)*. Hasta ahora la misma suite se corría **tres veces por cambio**: el coder, QA y a veces el orquestador. Peor: **el silencio de un `dotnet build` o un `dotnet test` largo es lo que dispara el watchdog de 600 s** — en la sesión del 2026-09-21 murieron cinco coders, al menos tres mientras verificaban, con el trabajo ya escrito en disco.

Desde ahora, en el prompt de cada coder: **corre `dotnet build` (o `npx tsc -b`) y nada más**. Es barato, de salida corta, y ataja lo único que de verdad hace perder un ciclo: código que no compila. **Las suites no las corre**; las corre QA en el Step 4, que es además quien las corre con ojos independientes. Si la corrida es Nivel 0 o 1 y no hay pasada de QA, entonces sí las corre el orquestador.

Tres efectos medidos: menos tokens (el output de una suite son miles de líneas que entran al contexto del coder), menos agentes muertos, y una verificación que vale más porque la hace quien no escribió el código.

**No repitas la verificación del coder** *(added 2026-09-11, pedido del responsable tras medir la sesión de la demo)*: el `## Coder Report` ya trae `build`/`tsc`, tests y lint, y QA los vuelve a correr por su cuenta en el Step 4 — eso ya son dos pasadas. **Tú no corras una tercera.** Léelas del reporte y sigue. Solo las ejecutas tú mismo en tres casos: el reporte no las incluye, se contradice con lo que ves en el diff, o el coder declara rojo y necesitas confirmar el alcance antes de decidir. Si las corres, di por qué en el reporte final.

**Con `--en`: verifica la carpeta antes de QA** *(added 2026-09-11)*. Esto sí es tuyo y es barato. Apenas vuelve el `## Coder Report`, confirma que los cambios cayeron donde debían: `git -C <RAIZ> status --porcelain` lista los archivos del reporte, y `git -C <repo> status --porcelain` de la carpeta principal sigue igual a lo que guardaste en el Step 0.5. Si el coder editó la carpeta principal, **para**: no muevas archivos a mano ni sigas a QA; muéstrale al usuario qué quedó en qué carpeta. Es un fallo silencioso — el build del worktree pasa igual, porque no ve el cambio.

### Step 3.5 — Architect en modo revisión (condicional, no en cada corrida)
*(added 2026-09-07; retiming 2026-09-18 — ver Step 4)*: si el `## Coder Report` muestra que la corrida **cambió estructura** — proyecto/capa/carpeta nueva, `DbContext` nuevo, middleware nuevo, namespace movido, o un patrón que no existía en el repo — invoca de nuevo a `architect`, esta vez con el `## Coder Report` como entrada, y trata sus `### Deviations (if reviewing existing code)` como hallazgos de QA. **Presupuesto:** cada ida al coder por una desviación **consume uno de los 2 ciclos del retry loop del Step 4** — no tiene presupuesto propio, porque si no una misma corrida puede rebotar cuatro veces entre agentes distintos. **Quién re-verifica:** QA en el Step 4, no una tercera pasada del architect — ya no corre "justo después", porque el Step 4 se pospuso hasta el gate de pre-PR (ver abajo), pero sigue siendo la instancia que valida esta desviación cuando ese gate finalmente corre; una pasada extra del architect ahora costaría lo mismo sin agregar nada. Si aplica, lanza este paso apenas vuelve el `## Coder Report`, antes del checkpoint commit del Step 3.6 — sus hallazgos van al coder en el mismo paquete que cualquier corrección de esa pasada, sin esperar al gate del Step 4.

Si la corrida **no** movió estructura (lo normal: un endpoint más, un campo más, un fix), **sáltate este paso** y dilo en el reporte final. QA item 3 y los tests de arquitectura ya cubren esa deriva mucho más barato que una pasada completa del architect.

### Step 3.6 — Checkpoint commit (antes del gate de QA/Adversary)
*(added 2026-09-18, pedido explícito del usuario: "no tiene que ejecutarse a cada rato, solo antes de hacer PR, o subir cambios a un PR, o cuando yo lo diga expresamente" — reemplaza el disparador inmediato que el Step 4 tenía desde su creación, donde QA y `adversary` corrían apenas terminaba cada coder)*: apenas vuelven el coder y, si corrió, el architect en modo revisión del Step 3.5, comitea el diff tal cual — mismo estilo de mensaje que describe el Step 4.5 (conventional commits en español), pase o no pase nada todavía. Esto reemplaza al commit que antes ocurría recién después de los tres gates del Step 4.4: ahora se adelanta, para no dejar trabajo sin guardar mientras el gate de QA/`adversary` se pospone hasta el momento del Step 4 (ver abajo). Si la corrida tiene varios coders en paralelo, un checkpoint por coder en cuanto termina, no uno solo al final.

### Step 4 — QA (y `adversary` en paralelo) — gate de pre-PR

**Cuándo corre este gate** *(added 2026-09-18, pedido explícito del usuario: "no tiene que ejecutarse a cada rato, solo antes de hacer PR, o subir cambios a un PR, o cuando yo lo diga expresamente")*: este Step (y sus gates 4.4/4.4a/4.4b/4.6) **ya no corre automáticamente después de cada coder**. Corre una sola vez, sobre el diff acumulado desde el último gate (no solo el último coder, para no dejar cambios sin auditar), en cualquiera de estos momentos:
1. Justo antes de ofrecer push/PR (Step 4.7).
2. Justo antes de subir commits nuevos a un PR que ya está abierto, si la corrida sigue agregando cambios después de un PR previo.
3. Cuando el usuario lo pida expresamente, en cualquier punto de la corrida.

Hasta que llegue uno de esos momentos, sigue con Step 3/3.5/3.6 (coder, revisión estructural si aplica, checkpoint commit) para el resto de la corrida sin invocar QA ni `adversary`.

**Un QA por cambio, no uno por mitad** *(added 2026-09-21)*: cuando un cambio cruza dos repos, la pregunta que más importa es **si las dos mitades encajan** — un campo que el backend llama `entityId` y el frontend manda distinto, un tipo que no coincide, un endpoint con otra ruta. Eso ningún QA de un repo solo lo ve. Se invoca **un** QA con las dos raíces y el contrato escrito como criterio de aceptación, no uno por repo. En la corrida 0054 la pasada cruzada encontró el P1 que las verificaciones de cada mitad habían dado por buenas.

**Revisión en paralelo, dentro de un mismo gate** *(added 2026-09-14, mismo pedido: "en revisión y eso también"; retimed 2026-09-18)*: si varios coders terminaron desde el último gate, cuando llega el momento de correrlo lanza un QA por cambio a la vez, sin esperar entre ellos. Mientras corren los QA, el orquestador verifica el diff contra `git status` y lanza la suite completa en segundo plano; todo eso a la vez, y los hallazgos vuelven a cada coder en un solo paquete.

**Codex como segundo revisor, en toda corrida salvo Nivel 0** *(added 2026-09-14; ampliado 2026-09-16, pedido: "trata de usar en lo posible a codex y antigravity" — antes era solo en el pipeline completo)*: en Nivel 1 y en el pipeline completo, cuando llega el momento de este gate, lanza la skill [`/codex`](codex.md) con `--uncommitted` sobre el repo o worktree **en paralelo con el QA**. Sus hallazgos se verifican contra el código y los reales vuelven al coder en el mismo paquete que los del QA. Si Codex no tiene cuota o no está logueado, se omite y se dice en el reporte final; nunca bloquea la corrida. Motivo: en #<n> y #<n> Codex encontró 18 hallazgos en tres rondas después del push.
**Antigravity como revisor de lo visual** *(added 2026-09-15, primera prueba real; el responsable: "podemos usar antigravity y codex siempre que podamos")*: el responsable tiene el CLI de Antigravity instalado como `agy`, con modo sin interfaz. Es el **único revisor que mira cómo se ve el resultado** — QA, `adversary` y Codex miran corrección. Úsalo **cuando el diff toca UI**: estilos, layout, componentes, tokens de tema.

```
agy --model gemini-3.1-pro-high --effort high --mode plan --print="<prompt + diff>"
```

Tres cosas que hay que saber para usarlo bien:
- **El prompt va pegado al flag** (`--print="..."`), y `--model` va antes. Si se pasa suelto, el CLI toma `--model` como el prompt y descarta el resto sin fallar.
- `--mode plan` es el modo revisor: razona sin tocar archivos. `--json-schema` permite forzar salida estructurada (severidad, archivo, línea) en vez de prosa; vale la pena cuando el reporte se va a procesar.
- **Pásale el diff dentro del prompt**, no como archivo en el worktree: un archivo suelto ahí ensucia el `git status` de la corrida.

**Su tasa de acierto en la primera prueba fue 1 de 4** — pero ese 1 fue un badge que la limpieza de estilos había dejado sin forma, y **no lo vio nadie más**. Los otros tres: dos falsos positivos (afirmó que unos tokens no existían, y existen con 4 definiciones; afirmó que un contraste fallaba, y mide 6,25:1) y uno que fue culpa del orquestador (se le pasó un diff sin los tests y reportó "ausencia total de tests"). **Cada hallazgo suyo se verifica antes de mandarlo al coder.** Es una sola muestra: si en las próximas corridas la tasa no mejora, vale replantear si compensa.

Invoke the **named** `qa` subagent (`.claude/agents/qa.md`) with the coder's change summary and the planner's test matrix. It returns PASS or a list of findings.

**Lanza `adversary` a la vez que QA, no después** *(added 2026-09-11, pedido del responsable tras medir la sesión de la demo: `adversary` esperando el PASS de QA agregaba 3-5 min de pared por corrida, y las dos leen exactamente el mismo diff)*. Los dos subagentes salen en el mismo mensaje, en background. Cuando vuelvan los dos, **consolida sus hallazgos en un solo paquete** y haz **un solo viaje** al coder, igual que ya hace el Step 4.4 con sus gates. Los topes siguen separados y no se mezclan: 2 ciclos para QA, 1 ronda para `adversary`.

Dos excepciones en las que conviene esperar el PASS de QA antes de gastar `adversary`: cuando el `## Coder Report` declara el build o los tests en rojo (el diff todavía no es auditable), o cuando ya estás en el segundo ciclo de QA por hallazgos funcionales.

### Retry loop (bounded)
- If QA returns findings: send them back to the **coder** (not the planner) for a fix. Re-invoke QA once more.
- Maximum **2** QA→coder→QA cycles total. If QA still has unresolved findings after that, STOP. Do not loop a third time. Report to the user: what QA found, what the coder tried, and that this needs human input.
- If QA returns PASS (at any cycle), stop immediately and report success — do not keep iterating for polish.

### Step 4.4 — Los tres gates corren en paralelo, y vuelven al coder en UN solo viaje
*(added 2026-09-07; ampliado 2026-09-11)*: quedan tres verificaciones — 4.4a (tests de integración), 4.4b (`adversary`) y 4.6 (`security-review`). **Las tres leen el mismo diff y ninguna depende del resultado de las otras.** Corrían en serie: eso es tiempo de pared regalado y, peor, hasta tres rondas separadas de ida y vuelta al coder por el mismo cambio.

Lánzalas solapadas, y desde 2026-09-11 **`adversary` arranca junto con QA** (ver Step 4), no después de su PASS:
1. Si 4.4a aplica (es un juicio tuyo, ver abajo), arranca `dotnet test api-core.IntegrationTests` **en background** — no te quedes esperándolo.
2. `adversary` ya está corriendo desde el Step 4; si por una de las dos excepciones de ese paso no lo lanzaste ahí, invócalo ahora.
3. Mientras tanto, corre tú el skill `security-review`.

Luego **consolida los tres resultados en un solo paquete de hallazgos** antes de mandar nada al coder. Un viaje, no tres. Los presupuestos de reintento no se mezclan: los hallazgos de `adversary` gastan el tope de 1 ronda del Step 4.4b, un fallo de integración gasta el de QA, y `security-review` no tiene loop automático (Step 4.6). Si el paquete consolidado mezcla varias fuentes, dilo explícitamente al reportarlo y trata cada tope por separado.

Si los tres salen limpios, dilo así de claro en el reporte final — "sin hallazgos" en los tres gates es información, no silencio.

### Step 4.4a — Integration tests (Nivel 2, orchestrator-run, once)
*(added 2026-08-26 — tiered testing strategy, el responsable's explicit design)*: `qa.md` only runs unit + architecture tests (Nivel 1) during its retry cycles now — fast, no external dependencies, safe to re-run up to the 2-cycle limit. Integration tests (`api-core.IntegrationTests`, Testcontainers/Docker/SQL Server) are comparatively slow and don't need to run on every retry; running them once here, after QA has already returned PASS, gets the same coverage for a fraction of the cost.

**This is judgment, not a default-on step** — run it only when *you* (the orchestrator) decide it's actually warranted, based on what the run touched: schema/migrations, EF Core query changes, concurrency/locking patterns, anything reading or writing real data access — the kind of thing Nivel 1's mocks can't exercise. For a run that's purely additive/isolated with no data-access surface (a doc change, a config value, a pure-UI-adjacent change with no repository/DbContext touch), skip it — don't run it reflexively just because it's available. Either way, say explicitly in the Final report whether you ran it and why (or why not) — don't let the decision go unstated.

**Excepción que NO es juicio: si la rama contiene una migración que BORRA o RENOMBRA una columna, los tests de integración son obligatorios** *(added 2026-09-22, tras un CI rojo)*. Y el criterio se aplica sobre **lo que toca la rama entera**, no sobre el último cambio: el Step 4 ya dice que el gate corre *"sobre el diff acumulado desde el último gate"*, y acá se aplicó a dos fixes de una línea mientras la rama borraba tres columnas.

Por qué no hay forma más barata de atraparlo: un test que inserta por **SQL crudo** (`ExecuteSqlInterpolatedAsync`, `ExecuteSqlRawAsync`) para saltarse EF es **invisible para el compilador** y para los tests unitarios, que mockean el acceso a datos. `EntityNumberConcurrentTests.cs` seguía nombrando la columna `OldColumn` que la migración borraba: build verde, 680/680 unitarios verdes, y `Invalid column name 'OldColumn'` recién en CI. La única red que lo ve es una base real.

Chequeo de 5 segundos antes de decidir: `git diff <base>..HEAD -- 'Persistence/Migrations/*.cs' | grep -E "DropColumn|RenameColumn"`. Si devuelve algo, el gate corre. Y al arreglarlo, `grep -rn "\[OldColumn\]" --include=*.cs` por si hay un segundo caso — pero verificar cada uno antes de tocarlo: un test de migración puede nombrar la columna vieja **a propósito**, porque migra hacia atrás a un punto donde todavía existe.

If you do run it (`dotnet test api-core.IntegrationTests`, yourself, not QA) and it fails, treat it like a QA finding: send it back to the coder, and this **does** count against the same 2-cycle retry budget as the QA loop above (it's still verifying the same change, just a slower layer of the same gate) — don't re-invoke QA's full Nivel 1 suite for an integration-only fix unless the fix could plausibly affect the Nivel 1 result too.

### Step 4.4b — Adversarial Code Audit (Nivel 3 — "Codex con esteroides")
*(added 2026-08-26, el responsable's design — "un agente que solo vea las observaciones, heurísticas nivel producción Microsoft, nivel Codex con esteroides y análisis de mutabilidad")*:
Se lanza en paralelo con 4.4a y 4.6 (ver Step 4.4). Invoca el subagente **nombrado** `adversary` (`.claude/agents/adversary.md`).

Unlike QA (which verifies if the plan and tests passed), the `adversary` operates with an adversarial, destructive lens against the `git diff`:
1. Audits against the production heuristics and the 6 attack vectors — **las listas canónicas viven en `adversary.md` y no se repiten acá**: ya divergieron una vez (un archivo decía 8 sobre una lista de 10) y una enumeración parcial vuelve a invitar a lo mismo.
2. Conducts mental mutation testing to detect surviving mutants (critical bugs that existing unit tests wouldn't catch).

**Handling Verdict**:
- If `adversary` returns **PASS**: su parte del paquete consolidado del Step 4.4 queda vacía — espera a 4.4a y 4.6 antes del Step 4.5.
- If `adversary` returns **FINDINGS**:
  - P1 findings (compound failure corruption, SPA session leaks, concurrency races) must be resolved by the coder before opening the PR (Step 4.7); el checkpoint commit del Step 3.6 ya existe de todas formas, pase o no pase este gate — el fix, si lo hay, agrega el commit del Step 4.5 encima.
  - P2 findings and mutation test gaps: present them clearly to the user. If they represent real production risks, send to coder to fix.

**Bound — este loop también tiene tope** *(added 2026-09-07: no lo tenía, y la corrida 0033 registró 5 rondas de adversary→coder→adversary)*: **máximo 1** ronda adversary→coder→adversary, con su **propio** presupuesto, independiente de los 2 ciclos de QA (que a esta altura ya pueden estar agotados). Si después de esa ronda siguen quedando P1, **STOP** y escala al usuario igual que el retry loop de QA: qué encontró adversary, qué intentó el coder, y que esto necesita decisión humana. Todo fix originado aquí re-ejecuta `dotnet build` + los tests Nivel 1 antes de re-invocar a `adversary` — no la pasada completa de QA.

**No comitees mientras un revisor está leyendo el diff sin commitear** *(added 2026-09-22, corrida 0057)*: `codex exec` y `agy` leen `git diff` del árbol de trabajo. Si comiteás el checkpoint mientras uno de ellos revisa, el diff se vacía a mitad de su lectura y su veredicto pasa a valer sobre algo que ya no puede ver — un PASS así no prueba nada. En 0057 salió válido de casualidad, porque alcanzó a leer los hunks antes del commit. El orden es: **el revisor cierra, después comiteás**. Si ya comiteaste, relanzá la revisión contra `HEAD~1..HEAD` en vez de dar por bueno el veredicto.

### Step 4.5 — Commit the result (correcciones del gate, si las hubo)
*(retimed 2026-09-18 — ver Step 3.6 y Step 4)*: el checkpoint del código del coder ya se comiteó en el Step 3.6, antes de que este gate corriera. Este paso es para el commit **adicional** que resulta de un hallazgo de QA/`adversary`/integración/seguridad: once the three Step 4.4 gates (4.4a, 4.4b and 4.6) have all returned and their consolidated findings package is resolved (coder applied fixes) or escalated — or the run is stopped/escalated after a retry limit — commit whatever state the branch is in — passing or not, so nothing is lost. Si el gate no encontró nada que corregir, no hay commit nuevo que hacer acá: el checkpoint del Step 3.6 ya es el estado final antes del push. **Commit message style: conventional commits, en español** *(decisión del responsable del 2026-09-16, "siempre adoptar convención"; reemplaza la regla anterior de oración sin prefijo)*: `<tipo>(<alcance opcional>): <descripción>`, con la descripción en español, en imperativo y en minúscula — p. ej. `feat(entidad): agregar endpoint de resumen`, `fix(vista): corregir filtro de entidades asociadas`, `docs: registrar corrida 0046`. Tipos: `feat` (funcionalidad nueva), `fix` (corrección), `docs` (solo documentación), `refactor` (sin cambio de comportamiento), `test`, `style`, `perf`, `ci`, `build`, `chore`. Nunca en inglés ni verboso. Los commits de merge quedan como `Merge …`, igual que los que genera GitHub. A body with more detail (task summary, QA verdict) is fine below the subject line, same as this skill has been doing. Do not merge to the base branch.

**Keep low-signal-for-human-reviewer files out of the PR's visual noise via `.gitattributes`, without changing how/when anything is committed** *(added 2026-09-02, el responsable's explicit request; expanded same day)*: everything still gets committed normally as part of Step 5, in the same PR as the code — a separate commit does **not** hide anything from GitHub's "Files changed" view (that view aggregates the full base→head diff regardless of commit boundaries, confirmed 2026-09-02 after an initial wrong assumption that a separate commit would achieve this). The actual mechanism: each repo's `.gitattributes` marks these paths as `linguist-generated=true`, so GitHub collapses them by default in the PR diff (still fully present, expandable with one click, zero effect on git history or on any tooling reading them normally — `architect`/`planner`/`retro` still read `AcmeOrg/docs/runs/` fine). Current set for `api-core` (patrones de `api-core/.gitattributes`, relativos a la raíz de ese repo — por eso sin prefijo `api-core/`; verify/replicate per-repo, don't assume every repo has the same file needs `.gitignore`-style):
- ~~`docs/runs/*.md`~~ — *(quitado 2026-09-16: los run docs se mudaron al vault y ya no viajan en los PR de api-core)*.
- `Persistence/Migrations/*.Designer.cs` — 100% auto-generated by `dotnet ef migrations add`, nobody hand-edits these.
- `api-core.Tests/**/*.cs`, `api-core.IntegrationTests/**/*.cs`, `api-core.ArchitectureTests/**/*.cs` — el responsable's explicit call: the human reviewer doesn't review test diffs in practice anyway, and test quality is already gated by `qa`/`adversary` before the PR exists, so collapsing them doesn't remove review that was actually happening. This is a repo/team-specific judgment call, not a universal "hide tests from review" default — don't silently replicate it into a different repo's `.gitattributes` without asking.
- ~~`docs/adr/*.md`~~ — *(quitado 2026-09-16: los ADRs se mudaron al vault y ya no viajan en los PR de api-core)*.
- ~~`docs/architecture/**`~~ — *(quitado 2026-09-16 junto con los diagramas PlantUML, PR #<n>)*.

Initial reasoning for excluding ADRs (superseded by el responsable's explicit override above, kept here as the tradeoff record): ADRs are short, standard practice, and a reviewer would normally be expected to read them without prompting. If a future repo/session is deciding this fresh, that's still the right *default* to propose — just don't assume it's final without asking, the way it wasn't here.

### Step 4.6 — Security review (complements QA, doesn't replace it)
Se lanza en paralelo con 4.4a y 4.4b (ver Step 4.4). Corre el skill `security-review` contra el diff de esta corrida antes de ofrecer commit/push. **Carga además `.agents/skills/security/SKILL.md`** y pásale su checklist como criterio adicional — ese archivo tiene el catálogo CWE y las versiones mínimas de NuGet/npm, y hasta 2026-09-07 no lo referenciaba nadie. Si el `## Coder Report` lista un `.csproj` o un `package.json` cambiado, verifica explícitamente su sección de versiones: hoy nadie en el pipeline revisa la versión de un paquete al agregarlo. This is a separate, dedicated pass — QA's checklist item 5 only catches "obvious" issues in passing; api-core moves PII (DNI, phone, address) and sensitive domain data, so it earns its own gate. Report what it found plainly. If it surfaces something real: do not auto-loop back to the coder the way QA findings do (that retry budget is QA's, not this pass's) — stop and tell the user what was found, let them decide whether to send it back to the coder or accept/defer it. A clean result is also worth stating explicitly ("sin hallazgos"), not silently skipped over.

**Scoping the diff correctly** *(added 2026-08-18)*: the skill computes its own diff against `origin/HEAD`, which you cannot override from the skill call itself. Two things go wrong in practice if you skip this: (1) if `git remote set-head origin -a` was never run in this environment, `origin/HEAD` can be unresolvable and the skill call fails outright — run it once (harmless, idempotent) before the first `security-review` call in a session if you hit that error. (2) When this run's branch stacks on another unmerged branch (common now per the Step 0.5 dependency guidance above), the diff against `origin/HEAD`/`develop` includes that other branch's already-reviewed changes too, not just this run's. When that happens, don't let the noise dilute the review — in your own summary of the skill's report, explicitly scope your read to the files this run actually touched (you know them from the coder's `## Coder Report`) and say so, same as noting "scope note" has worked in past runs.


(3) **En modo `--en` (worktree), no invoques el skill en absoluto** *(added 2026-09-21, encontrado por `retro` en las corridas 0045, 0053 y 0054)*. Corre siempre desde la carpeta principal, así que su diff contra `origin/HEAD` **nunca ve el árbol de `.worktrees/<repo>--<slug>`**: en el mejor caso trae ruido, y en el peor revisa otro repo entero — en la corrida 0045 terminó revisando los `.md` de `agentic-harness` en vez del código de la tarea. Saltá el skill y hacé el gate a mano sobre el diff real del worktree, con la checklist de `.agents/skills/security/SKILL.md` como criterio: autorización de los endpoints tocados, SQL literal vs interpolado, qué datos destruye una migración, y versiones de paquetes si cambió un `.csproj`/`package.json`. Decilo así en el reporte final. Es el mismo criterio que se improvisó tres veces; ahora es el procedimiento, no la excepción.
### Step 4.7 — Offer push + PR (only if the GitHub MCP is connected)
**Antes de este paso, confirma que el gate del Step 4 ya corrió sobre todo el diff acumulado** *(added 2026-09-18)*: si hay commits del Step 3.6 posteriores a la última vez que corrió QA/`adversary` (por ejemplo, la corrida siguió agregando cambios después de un PR previo), corre el Step 4 sobre ese diff nuevo antes de ofrecer el push — nunca subas a un PR, nuevo o existente, código que el gate no haya visto todavía.
**Con `--en`, este paso no corre** *(added 2026-09-11)*: ni push ni PR, y no se ofrecen. Cierra diciendo la rama y el worktree, y que queda para `/worktree sincronizar`. La tarjeta de Trello no se mueve: pasa a revisión solo cuando el responsable lo pide (ver abajo).

Check whether `github`-prefixed MCP tools are available (e.g. via `ToolSearch` or the tool listing). If they are NOT available, skip this step silently — just tell the user the branch name and that it's ready for their manual review/push, same as before this step existed. **Explicitly remind them the PR base must be `develop`, not `main`** — GitHub's own "Compare & pull request" banner defaults the base to the repo's default branch (`main`), and this has caused real PRs to land on `main` directly, skipping `develop`/`qa`, twice in one session (2026-08-17). If that happens anyway, `/verificar-ramas` diagnoses and fixes the resulting divergence.

**Consolidate stacked branches into one PR — default behavior, not a one-off** *(added 2026-08-19, after el responsable explicitly asked for this as the standing convention going forward)*: when this run's branch was created from another unmerged run's branch (per the Step 0.5 dependency guidance), and that chain has more than one unmerged branch waiting on human review, do **not** open a separate PR per run. el responsable's reviewer (his manager) has to approve each PR into `develop`, and a stack of several small PRs is worse for them than one PR with the accumulated diff: reviewing N PRs in the right order is more overhead than reviewing one, and if the reviewer requests changes on an early PR in the stack, fixing it means merging that fix forward through every downstream branch one at a time — real, avoidable pain. Instead: only open (or keep open) a PR from the **tip** branch of the chain straight to `develop` — its diff already contains everything from the earlier unmerged branches in its history, so nothing is lost. If earlier runs in the same chain already have their own open PRs from prior sessions, close them with a comment pointing to the consolidated PR (see run 0014 for the real precedent: PRs #<n>/#<n>/#<n> closed, consolidated into #<n>). This only applies to a chain of *dependent* branches (each one needs the code in the last) — independent branches that happen to run in parallel still get their own PRs, there's no dependency to consolidate.

If GitHub tools ARE available: ask the user explicitly (do not push or open a PR without a clear yes each time — a prior approval for one run does not carry over to the next) whether they want you to:
1. `git push` the run's branch to `origin`.
2. Open a PR against `develop` (the org's actual base branch, confirmed 2026-08-14 — not `main`), with a title in the same conventional-commits style as the commit subject (`<tipo>(<alcance>): <descripción en español>`) and a body summarizing: what was built, the architect's pattern, the QA verdict, any deferred findings — pulled from the Step 5 run doc content, not re-derived from scratch.

Only do what the user confirms — they may want the push but not the PR, or neither. Report the resulting branch/PR URL back to the user when done.

**Once the PR exists, do NOT move the Trello card to review** *(added 2026-09-10; changed 2026-09-19, pedido del responsable: "la card solo va pasando a revisión de Revisor Principal solo cuando lo digo yo", porque los PRs recién abiertos siguen recibiendo correcciones de bugs)*: only offer to attach the PR to the Step 0.6 card with `/trello adjuntar --url` (simulate, show, then `--aplicar` on approval). The card stays in its current column. Moving it to `En revisión (Revisor Principal)` plus members, labels and dates happens only when el responsable explicitly asks for it — never offer it proactively at the end of a run. When he does, follow section 2 of `docs/guias/ESTANDAR-ENTREGA-TRELLO-Y-GITHUB.md`; don't restate the fields here.

**Never paste a token, secret, or credential into a commit message, PR body, or any tool call argument** — if a GitHub operation needs a credential beyond what the connected MCP already handles, stop and ask the user to act directly instead.

**Check for automated review bot comments on a still-open PR from a prior run** *(added 2026-08-20, after a Codex/GitHub automated reviewer caught 5 real issues — 2 of them race conditions — in a PR the architect→planner→coder→qa pipeline itself had already passed)*: before starting any new task, if the user mentions a reply/response/comment landed on an already-open PR from a previous run, don't assume it's necessarily human feedback — check with `gh pr view <N> --json comments,reviews` and `gh api repos/<owner>/<repo>/pulls/<N>/comments` (inline review comments, which the `reviews` field alone won't show). If the thread is long, run these through `gh-read-shunt.sh` instead of reading them raw *(added 2026-09-18, ver [`/shunt`](shunt.md))*. It may be an automated bot (Codex, CodeRabbit, etc.) that a service/bot account triggered. Treat its findings with the same rigor as a QA finding if they're concrete (file:line, a described failure mode) — don't dismiss them as noise just because they're bot-generated, and don't silently accept them as gospel either: verify each one against the real code, the way the planner already does for the architect's report, before building a fix plan around it.

### Step 4.8 — Lo que aparecio fuera de alcance va a `/proyecto extra`
*(added 2026-09-21, pedido del responsable)*: cuando la corrida descubre trabajo que no estaba en el
plan — un bug que bloquea, una inconsistencia, deuda que hay que arreglar antes de seguir —
no alcanza con reportarlo con `archivo:linea` y dejarlo en `TASKS.md`. Pasa por
[`/proyecto extra`](proyecto.md), que decide si va tarjeta nueva o se amplia la que esta en
curso, propone la mutacion de Trello y **registra las horas como fila `Extras`** en la
estimacion. Sin esa fila, el tiempo extra desaparece y el tablero de avance marca atraso sin
poder explicar de donde vino.

Criterio corto, el detalle esta en esa skill: se amplia la tarjeta en curso solo si el
hallazgo **bloquea** la tarea; si no bloquea, es de otro repo, o pesa mas de la mitad de la
tarjeta original, va tarjeta aparte.

### Step 5 — Record the run

**This step is mandatory, not optional — a completed run without it disappears from the project's history.** *(added 2026-08-18, after a real run — JWT Bearer auth added to every api-core endpoint, architect→planner→coder→QA 2 cycles→security review all passed — never got its run doc written because the conversation moved on to something else before Step 5 ran. The code shipped; the record of how/why/what-was-decided didn't. Do not let a later request pull focus away before this step completes — if the conversation is about to move to a new topic and Step 5 hasn't happened yet for the run that just finished, do it now, don't defer it "for later.")* **IMPORTANT** *(reinforced 2026-08-26, after the same omission recurred on run 0026 despite the warning above — it was phrased as advice, not a gate, and got skipped anyway when the conversation moved on): the run is NOT done until this step is done. Do not report the run as complete, do not tell the user it shipped successfully, and do not treat the branch/commit as the finish line, while Step 5 is still outstanding for a run that already reached QA PASS (or was stopped/escalated). If you notice mid-run that a PRIOR run's Step 5 was skipped, write that doc now, before starting anything else — same as this run's own Step 5.*

Write a new file `AcmeOrg/docs/runs/NNNN-<short-slug>.md` (next sequential number, check existing files first) following the structure of `AcmeOrg/docs/runs/NNNN-ejemplo-run.md` (has the current conventions — 0001 predates them): task, architect's proposed decisions, planner's corrections (with what was verified against real schema/data and why it mattered), whether Step 2.5 triggered and what the user decided, QA findings, and any process lessons for future runs.

**Con `--en`, dos cambios** *(added 2026-09-11)*: (1) el número no se calcula — usa el **run reservado** para esta tarjeta en el plan de ola (`/worktree`, sección "Plan de ola"); si no hay uno, pregunta antes de escribir, porque otra sesión en paralelo puede estar tomando el mismo "siguiente libre". (2) **No toques `INDEX.md`**: la fila la agrega `/worktree sincronizar`, justo antes del PR. Si cada rama paralela la agregara al terminar, todas chocarían en `INDEX.md` en cada merge de develop. Dilo en el reporte final: "fila de INDEX pendiente para `sincronizar`".

Start the file with YAML frontmatter (this repo's `docs/` is used as an Obsidian vault, see `AcmeOrg/Home.md`, en la raíz del vault) with these exact fields: `tipo: run`, `numero: "NNNN"`, `fecha`, `resultado` (PASS/FINDINGS/etc.), `ciclos_qa`, `duracion` (string like "~28 min"), `tokens` (human-readable string like "~196.6K (architect 55.2K + planner 53.3K + coder 39.2K + qa 48.9K)"), `tokens_num` (plain integer, no formatting — the sum in raw tokens, needed for the Dataview SUM query in `Home.md` to work; string-formatted `tokens` alone won't sum), `tokens_fuente` (either `"estimado"` — the normal case, these numbers come from each agent reporting its own usage, not a verified API log — or `"medido"` only if you actually pulled the number from a real usage/billing source; don't write `"medido"` by default), `rama`, `tags` (at least `[run, api-core, orquestador]` plus anything task-specific). Add a wikilink line near the top to the previous run doc and to any ADR/`contexto-negocio/` (raíz del vault) file this run drew on.

Carry QA's `### Runtime/DI Check` section (triggered yes/no, and what it caught if yes) into the run doc's "Hallazgos de QA" — retro tallies this across runs to judge whether the check is worth its cost, so don't drop it even when the answer is "no se activó" or "se activó, no encontró nada nuevo".

#### Bitácora de consumo: una fila por actividad, no un total *(obligatorio desde 2026-09-21, pedido explícito del responsable)*

El run doc lleva, además del campo `tokens` del frontmatter, una sección **`## Bitácora de consumo`** con **una fila por cada agente o motor invocado**. Un total agregado no sirve para mejorar nada: con "coders 345K" no se puede saber qué actividad salió cara ni cuál conviene delegar a otro motor. Con la tabla, sí.

| Paso | Agente / motor | Tokens | Duración | Resultado |
|---|---|---|---|---|

- **De dónde salen los números, sin inventarlos:** cada subagente de Claude los reporta en su notificación de cierre (`subagent_tokens`, `tool_uses`, `duration_ms`); Codex los imprime al final de su log (`tokens used`); `agy` según su salida. Un agente que murió por watchdog **no reporta consumo**: se anota `sin reportar` y se dice que murió, nunca se estima por analogía.
- **Va TODA acción que gaste tokens, no solo los pasos del pipeline** *(aclarado 2026-09-21 a pedido del responsable)*: también el agente barato que regenera el tablero de avance, una corrida de `retro` o `system-auditor`, una lectura grande delegada a `bulk-read.sh`/`trello-read-shunt.sh`, un `code-write.sh`, o cualquier tarea mecánica que se delegue. Si consumió presupuesto, tiene fila. Una bitácora que solo muestra architect/planner/coder/QA esconde justo el gasto que nadie está mirando.
- **La columna Resultado es la que da sentido a la tabla**: un agente caro que encontró un P1 vale lo que costó; uno caro que murió sin entregar es la fila que hay que atacar.
- El campo `tokens` del frontmatter sigue existiendo como resumen, y `tokens_num` como la suma para el Dataview de `Home.md`. La tabla es el detalle, no su reemplazo.
- **Separar de quién es el presupuesto.** Codex y Antigravity gastan cuentas distintas de la de Claude: la tabla debe dejar ver cuánto salió de cada una, porque es lo que decide el reparto de la corrida siguiente.

Agrega la corrida en **dos** lugares de `AcmeOrg/docs/runs/INDEX.md`: (1) una linea en la seccion "Mapa de conocimiento", bajo **cada** tema que la corrida haya tocado (una corrida puede aparecer en varios, es a proposito — se busca por tema, no por numero; si no encaja en ninguno, crea el tema); y (2) una fila en el libro mayor con columnas: Fecha, Tarea, Resultado, **Duración**, **Tokens** (same human-readable string as the frontmatter), **Ciclos QA**, Rama, Detalle link. Do this even if the run ended early (escalated to the user after 2 QA cycles, or stopped at the Step 2.5 checkpoint) — record what was tried and why it stopped, that's valuable too.

**Commit en el vault, no en la rama** *(desde 2026-09-16, al mover run docs y ADRs a `agentic-harness`)*: el run doc, la fila de `INDEX.md` (si esta corrida la tocó) y el ADR (si nació uno) viven en la raíz de AcmeOrg, así que el commit del Step 4.5 no los incluye. Comitéalos en `agentic-harness` al cerrar este paso, con el mismo estilo (`docs: registrar corrida NNNN`), y pushea. **Ese checkout lo comparten todas las sesiones abiertas**: nunca `git add -A` ni `git add .`; agrega cada archivo por ruta y revisa su `git diff` antes, porque un archivo que tocaste puede traer además cambios sin commitear de otra sesión (pasó el 2026-09-16: un commit se llevó las ediciones en curso de otra sesión en `Meta/sistema-multiagente-supervisado.md`). Si el diff trae algo que no es tuyo, para y pregunta. El pre-commit corre `scripts/validar-vault.py`: los wikilinks del run doc van con ruta desde la raíz del vault (`[[contexto-negocio/PREGUNTAS-NEGOCIO]]`, `[[contexto-negocio/...]]`), nunca relativos con `../`.

**ADR check**: before finishing this step, ask yourself whether this run made a real architecture decision (a new dependency/package adopted, a structural pattern change, a new cross-cutting convention) that isn't already covered by an existing file in `AcmeOrg/docs/adr/`. If so, don't silently let it pass — flag it explicitly in the Final report to the user (below) as "this run made an architecture decision with no ADR — want one written?". Do not draft the ADR yourself unless the user confirms; just surface the gap so it doesn't accumulate unnoticed the way MediatR's adoption (run 0001) and the layered-project split (run 0003) did before this check existed. **Si el usuario confirma y se escribe** *(regla del 2026-09-16, al mover los ADRs al vault)*: va en `AcmeOrg/docs/adr/` con el número reservado en la ola (ver `/worktree`) y nace con `estado: Proposed`, porque la carpeta es compartida y el ADR queda visible para todas las sesiones antes de que el código llegue a `develop`. Pasa a `Accepted` recién cuando mergea el PR que lo implementa. Si ese PR se descarta, el ADR queda en `Proposed` y se avisa al usuario para que decida qué hacer con él.

**Borrador delegado** *(agregado 2026-09-18, ver [`/shunt`](shunt.md))*: confirmado el ADR, el borrador se genera con `code-write.sh --reference <ADR más parecido> --target docs/adr/000N-slug.md --spec "<resumen de la decisión>"` en vez de redactarlo vos mismo. A diferencia del uso normal de `code-write.sh`, acá **sí leés** el archivo generado antes de mostrárselo al usuario — no hay QA/adversary/validador después de un ADR que lo verifique por vos.

### Verificar un hallazgo antes de repetírselo al usuario como hecho
*(added 2026-09-18, corrida piloto GT-08)*: el orquestador le repitió al responsable el hallazgo del planner — "hay un bug real hoy en `develop`: la entidad queda huérfano si falla la segunda llamada" — como si ya estuviera comprobado. Era falso: Codex y Antigravity, leyendo el código real por separado, confirmaron que `develop` ya crea la entidad y su acción en una sola llamada. El planner había comparado contra el worktree viejo (una base deliberadamente anterior a la implementación real) y etiquetó ese estado viejo como "hoy".

Mismo principio que ya existe para el hand-off entre agentes ("el reporte de un agente no es evidencia", Step 3), aplicado al momento exacto donde más cuesta el error — cuando vos, el orquestador, estás a punto de decirle al usuario "esto es un bug real" o "esto ya se confirmó". Antes de esa frase, hacé tu propia verificación mínima: un `grep`/`Read` del archivo citado, o un segundo motor externo (Codex/Antigravity) si el primero ya lo hizo un solo agente. No traslades la conclusión de un solo agente como un hecho comprobado — ni siquiera cuando el agente cita `archivo:línea` con aparente seguridad.

### Final report to the user
Summarize: what was built (files changed), the architect's chosen pattern, any deviations the planner made from the architect's proposal and why, whether the risky-plan checkpoint triggered, the QA verdict, the security review result (Step 4.6), the branch name, whether it was pushed and/or a PR was opened (with the PR URL if so), and any findings that were explicitly deferred (not verifiable, or accepted as known limitations) rather than fixed.

Always include, even when the answer is "none/no":
- **Cambios de agente sin verificar por replay**: if the Step 0 replay-harness check found agent `.md` changes and the user chose not to replay them first, restate that here so it doesn't get lost.
- **Gaps de repo fuente**: if the planner's Risk Flags included the "requiere cambio en repo fuente" flag, restate what was decided (fix at the source later, or accept the limitation) — this is the one flag whose resolution isn't "done" at the end of an api-core run, since fixing it means work in a different repo this pipeline doesn't touch.
