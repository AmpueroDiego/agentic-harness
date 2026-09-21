---
tipo: guia
fecha: 2026-09-16
tags: [guia, arquitectura, sdd, requisitos, conventional-commits, estructura-carpetas, buenas-practicas, multiagente, mcp, agentic-harness, grafo-conocimiento, harness, tokenmaxing, adversarial, chaos-engineering, mutation-testing, property-testing, contract-testing, system-auditor, worktrees, paralelismo, codex, ux-ui, minimalismo]
aliases:
  - Sistema Multiagente Supervisado con Aprendizaje Continuo
  - Sistema Multiagente Supervisado con Aprendizaje Continuo y Auditoría Adversarial
  - Arquitectura Multiagente
---

# Sistema Multiagente Supervisado

> **Un orquestador reparte el trabajo entre agentes especializados, les exige evidencia verificable y audita el resultado antes de que llegue a GitHub.** Desde mediados de septiembre además optimiza el tiempo de reloj, sin recortar las verificaciones que sostienen la calidad.

> [!info] Cómo leer esta nota
> Es el documento de diseño del sistema. Arriba, lo que hay que saber en dos minutos: resumen, cifras agregadas y qué cambió. Después, el detalle por capa: qué hace cada pieza y qué pasaba sin ella. Al final, riesgos y decisiones abiertas. Esta versión pública no incluye el historial de corridas ni los ADRs del cliente: donde el original citaba una corrida concreta, acá se describe el patrón que esa corrida enseñó.

---

## Resumen ejecutivo

**1. Corre software real, no una demo.** 47 corridas del orquestador sobre 6 repos (175 tareas contando fixes directos y sesiones de diseño), 17 ADRs y dos PRs grandes en revisión al momento de escribir esto. Encuentra lo que los tests con mocks no ven: en una corrida, `adversary` detectó `DROP COLUMN` metidos en una migración ya pusheada — EF Core compara el `MigrationId` y no el contenido, así que toda base que ya la había corrido se los habría salteado para siempre. El chequeo de Runtime/DI lleva 10 disparos, 6 hallazgos reales y ninguna falsa alarma.

**2. A mitad de septiembre cambió de objetivo: de gastar pocos tokens a tardar poco, con la misma calidad.** Son cinco palancas: olas de trabajo en worktrees, varios coders y revisores en paralelo por defecto, Nivel 0 real en el frontend, Codex como segundo revisor antes del push y un agente experto en UX. Lo medido: la corrida más grande bajó de ~40 a ~20 min al adelantar los coders, un cambio de UI de Nivel 0 toma 2-3 min en vez de 10-15, y `adversary` junto a QA ahorra 3-5 min por corrida. El precio: más tokens por corrida — la más cara del libro mayor rondó 1.7M.

**3. El riesgo principal ya no es que un agente ignore algo, sino que diga que lo verificó sin haberlo hecho.** En una misma corrida, `architect` y `planner` inventaron por separado la misma cita `archivo:línea` de un panel de UI que no existe. En otra, un coder listó como cambiado un archivo que nunca tocó. La retro lo cerró en cuatro agentes, y la regla quedó fija: **el reporte de un agente no es evidencia, ni siquiera cuando dos coinciden.**

**4. El conocimiento del sistema vive en un solo lugar.** Run docs, ADRs y maquetas salieron de los repos de código y quedaron en el vault (`docs/`), así que todas las sesiones y worktrees leen la misma copia. Con esa mudanza llegó también la etapa 1 de **Spec-Driven Development** (biblioteca de requisitos en borrador) y los commits pasaron a *conventional commits*.

> [!important] Decisiones abiertas para el responsable del repo
> 1. **Convertir el Step 5 en un gate real.** Dos corridas quedaron sin run doc desde que se reforzó la advertencia; la retro recomienda endurecerlo si pasa una tercera vez.
> 2. **Cerrar el "modo demo" con auditoría.** Dos corridas terminaron sin `adversary` por pedido expreso; la regla dice que se acumula al cierre, pero ninguna corrida registra ese cierre.
> 3. **Reescribir una tarea dorada** que ya no se puede reproducir: el fix en que se basa ya existe en el código.
> 4. **Confirmar los REQ en borrador** y las 3 decisiones abiertas de SDD (ver [[#Spec-Driven Development]]).

---

## Estado (cifras agregadas al 2026-09-16)

| Métrica | Valor | Nota |
|---|---|---|
| Corridas | **47** | Un run doc por corrida en `docs/runs/`, indexadas por tema en `INDEX.md` |
| Agentes | **11** | 6 en el pipeline + 5 independientes (`analyst`, `ux-researcher`, `ux-ui`, `retro`, `system-auditor`) |
| Comandos | **10** | `orquestar`, `worktree`, `codex`, `antigravity`, `ux`, `verificar-ramas`, `diagramar`, `auditar-vault`, `shunt`, `requisitos` |
| Motores | **3** | Claude (pipeline propio), Codex CLI (revisor en toda corrida y coder de lo mecánico), Antigravity CLI / Gemini (revisor y coder de lo visual). Se reparte un coder de cada motor en paralelo |
| Guardas automáticas | **4 hooks** + `pre-commit` de git (secretos y vault) | `git-guard.sh`, `pr-base-guard.py`, `check-appsettings.py`, `check-maxlength.py`; los secretos los revisa `revisar_secretos.py`, compartido por `git-guard.sh` y el `pre-commit` |
| Herramientas deterministas | **2** en esta versión | `.claude/tools/`: `drawio`, `vault`. La del tablero de tareas se retiró de la versión pública |
| ADRs | **17** | En `docs/adr/`, una sola copia; nacen `Proposed` y pasan a `Accepted` cuando mergea el PR que los implementa |
| Requisitos | **7** en borrador | `requisitos/`, local y fuera de git. Ningún agente los lee todavía |
| Tareas doradas | **7** | Una pendiente de reescribir |
| Conectores MCP | **7** de ingeniería | 5 bases de datos + `github` + `azure`; `ux-ui` usa además Chrome y Figma |
| Cadencia | retro cada 3-5 corridas · auditoría del sistema cada ~10 | El orquestador avisa en el Step 0 cuando se vence |

---

## Situación, complicación, resolución

**Situación.** La mayoría de los sistemas multiagente son un prompt partido en roles: sin memoria, sin forma de saber si mejoran y sin nada que impida repetir un error. Este tiene las tres cosas: memoria de dominio, auditoría antes del PR y agentes que revisan al propio sistema.

**Complicación.** Con la calidad resuelta, el cuello de botella pasó a ser el reloj. En una demo en vivo el responsable del repo esperaba 30-40 min por cambios chicos: cada planner → coder corría en serie y con la suite completa. Además, al ganar autonomía los agentes empezaron a fabricar evidencia, que es más peligroso que no saber algo, porque una cita falsa parece prueba.

**Resolución.** Dos movimientos que se sostienen entre sí:
- **Paralelizar lo independiente**, siempre con una interfaz fijada antes de lanzar y un dueño exclusivo por archivo.
- **Exigir evidencia de primera mano**: una cita solo vale si sale de una búsqueda hecha en esa sesión, y el orquestador contrasta cada reporte contra `git status` y contra la base con datos reales.

Lo primero sin lo segundo sería velocidad sin control.

---

## La arquitectura en una página

Es una variante del patrón **orchestrator–worker** (o *supervisor pattern*), el mismo que usa el sistema de investigación multiagente de Anthropic. El patrón base no trae gratis las seis capas que este proyecto le agregó encima:

| Capa | Qué garantiza | Pieza concreta | Qué pasó sin ella |
|---|---|---|---|
| **1. Especialización** | Cada rol hace una sola cosa y solo con las herramientas que necesita | `.claude/agents/*.md`, `tools:` por agente | El coder de C# editó el frontend y ninguna regla de React se aplicó |
| **2. Coordinación con topes** | Nadie se habla directo, todo pasa por el orquestador, y cada loop tiene límite | `/orquestar`: niveles 0/1/completo, 2 ciclos de QA, 1 ronda de `adversary` | 5 rondas de adversary → coder en una sola corrida antes de existir el tope |
| **3. Grounding** | Cada afirmación sale de la base real, del código o de un grep | 5 MCP de BD, verificación propia del orquestador | Dos agentes citaron un panel inexistente y el grep devolvió 0 |
| **4. Memoria** | No se re-investiga terreno conocido | ADRs, run docs, mapa de `INDEX.md`, vault de Obsidian | Leer el libro mayor entero costaba ~5.6K tokens por corrida |
| **5. Auditoría antes del PR** | Se rompe el código antes de GitHub, no después | QA + `adversary` + `security-review` + `/codex`, en paralelo | 18 hallazgos de un bot en tres rondas después del push |
| **6. Mejora continua** | El sistema se corrige a sí mismo con evidencia | `retro`, `system-auditor`, tareas doradas | Evidencia fabricada en tres corridas seguidas, cerrada por la retro |

```
tarjeta del tablero ─► architect ─► planner ─┬─► coder ─────┐
 (Step 0.6)                                  └─► coder-web ─┤   ← varios en paralelo, dueño por archivo
                                                             ▼
                              QA ∥ adversary ∥ security-review ∥ codex ∥ tests de integración
                                                             ▼
                              un solo paquete de hallazgos ─► coder (con topes) ─► commit ─► run doc
```

> [!tip] Contraste con la investigación publicada de Anthropic *(2026-08-24)*
> Se comparó contra tres fuentes primarias: [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents), [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) y [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents). Todo cae en dos categorías: **harness**, la arquitectura del proceso, que decide si el trabajo sale bien (capas 1, 2, 3, 5 y 6), y **tokenmaxing**, cómo se gasta el contexto, que decide si sale barato (capa 4 y el aislamiento por subagente). El único gap real (pocas tareas doradas) se cerró ese mismo día. No se agregaron agentes sin evidencia de que hicieran falta: "resistir la sobre-ingeniería" es un principio de la propia Anthropic.

---

## Dónde vive cada cosa

`AcmeOrg/` es a la vez **vault de Obsidian** y **repo `agentic-harness`**. Adentro están clonados los repos de código, cada uno con su propio git; `agentic-harness` los ignora.

```
AcmeOrg/                      ← repo agentic-harness + vault de Obsidian
├── CLAUDE.md · AGENTS.md      reglas para cualquier sesión
├── TASKS.md                   un pedido = una fila, se agrega al empezar
├── Home.md · Meta/            dashboard y notas del sistema (esta)
├── .claude/
│   ├── agents/                11 agentes     (junction agentes-pipeline/ para Obsidian)
│   ├── commands/              10 comandos    (junction comandos-pipeline/)
│   ├── hooks/                 guardas de git, appsettings, maxlength y secretos
│   ├── scripts/               shunt: bulk-read, code-write, gh-read-shunt
│   └── tools/                 scripts deterministas: drawio, vault
├── docs/
│   ├── runs/                  run docs, INDEX, RETRO-LOG, GOLDEN-TASKS, SYSTEM-AUDIT-LOG
│   ├── adr/                   decisiones de arquitectura (única copia)
│   ├── mockups/               maquetas HTML
│   └── guias/                 playbook anti-regresiones y principios (retirados de la versión pública)
├── contexto-negocio/          dominio, mapas para coders, investigaciones, propuestas (retirado)
├── scripts/                   validar-vault.py, pre-commit e instalador de hooks
├── requisitos/                REQ de SDD            ── local, fuera de git
├── .worktrees/<repo>--<slug>  una rama por tarjeta   ── fuera de git
└── api-core/ · web-app/ · api-contracts/ · api-people/ · api-auth/ · api-delivery/
                               repos de código, cada uno con su git (ignorados)
```

**Regla de ubicación:** lo que describe *cómo trabaja el sistema* o *por qué se decidió algo* (agentes, run docs, ADRs, requisitos, guías) vive en el vault; en los repos de código queda el código y su `CLAUDE.md`. Así una rama o un worktree nunca ve una versión vieja de una decisión.

> [!warning] El checkout del vault lo comparten todas las sesiones
> Dos sesiones abiertas en `AcmeOrg/` escriben sobre los mismos archivos. Ya pasó que una sesión commiteó cambios de otra. Antes de commitear: stagear por ruta **y** leer el diff de cada archivo.

---

## Spec-Driven Development

**Qué es:** escribir *qué* debe hacer el sistema y *cómo se prueba* antes de programar, y que cada test y cada commit apunten a ese requisito. Cerca del 80 % ya existía (constitución = `CLAUDE.md` y playbook; plan = `planner`; tareas y gates = el pipeline). Faltaba la capa de specs y la trazabilidad por criterio.

```
decisión del responsable ─► /requisitos redacta REQ ─► confirmación ─► /orquestar lee el REQ (Step 0.8)
                             (requisitos/propuestas/)                  planner: columna REQ/escenario
                                                                       QA: cada escenario con test o UNVERIFIED
                                                                       Step 5: REQ implementado; humano marca verificado
```

| Pieza | Estado |
|---|---|
| Biblioteca `requisitos/`: README, plantilla (EARS + Gherkin con id `REQ-0002/E1`), 7 REQ en borrador | ✅ etapa 1 |
| Skill `/requisitos` | ✅ redacta, confirma, versiona y marca obsoleto |
| Step 0.8 en `orquestar.md`, columna en `planner.md`, ítem de cobertura en `qa.md` | ⬜ exige replay de tarea dorada |
| Cambio de spec a mitad de corrida (tope 1 por corrida) y run doc que se escribe durante la corrida | ⬜ |
| Piloto con una tarea dorada contra una implementación hecha sin REQ | ⬜ |
| Overlay Alt+R en el frontend | Diferido hasta 3 corridas con REQ |

**Decisiones abiertas:** ¿REQ obligatorio en todo pipeline completo? ¿Un cambio de spec re-planifica solo lo afectado o reinicia la corrida? ¿Quién marca `verificado`?

---

## Qué cambió a mitad de septiembre

| Cambio | Qué hace | Por qué nació | Efecto |
|---|---|---|---|
| **Olas en worktrees** (`/worktree`, `/orquestar --en`) | Una tarjeta = una rama = un worktree en `.worktrees/<repo>--<slug>`. `sincronizar` mergea develop y corre build y tests sobre el código combinado. `--bd-docker` le da a cada rama con migración su propia base | Varias tarjetas a la vez sin que una sesión pise a otra; las ramas con migraciones distintas se rompían entre sí sobre la misma base | Trabajo en paralelo real. Push y PR solo cuando el responsable los pide |
| **`adversary` junto con QA** | Los dos leen el mismo diff: salen en el mismo mensaje y vuelven al coder en un solo viaje, con topes separados | Esperar el PASS de QA agregaba tiempo de reloj sin información nueva | −3 a 5 min por corrida |
| **Sin triple verificación** | El orquestador no repite build y tests que ya corrieron el coder y QA | Eran tres pasadas iguales | Menos espera, igual cobertura |
| **Varios coders y QA en paralelo, por defecto** | Un coder por cambio independiente, cada uno con sus archivos y los prohibidos declarados; un QA por cambio apenas termina su coder | Pedido del responsable del repo: "siempre que se pueda, varios coders en paralelo" | ~40 → ~20 min en una sesión de demo |
| **Coders adelantados al planner** | Lo mecánico (renames, rutas, fixes con `archivo:línea`) arranca con **interfaz fija**; el planner corre a la vez, solo con lo que pide juicio | El planner era un cuello de botella para trabajo ya especificado | ~40 → ~20 min con 4 coders |
| **Tres palancas de tiempo** | (1) Decidir todo antes de la primera ola. (2) Un solo coder por repo si dos trabajos comparten archivos. (3) Partir un rename grande por carpeta con la tabla viejo → nuevo fijada | Una corrida costó ~60 min: la decisión de qué borrar llegó tarde y encoló ~28 min | Rename de 46 archivos: 21 → ~8-10 min estimados |
| **Nivel 0 real en el frontend** | Textos, botones, estilos y redirecciones a vistas existentes los hace el orquestador directo, con `tsc` + `eslint` + `vitest` de lo tocado | Un coder tarda 10-15 min porque arranca leyendo desde cero | 2-3 min por cambio |
| **Pedidos agrupados en demos** | Se espera a que el usuario cierre la idea, se separa Nivel 0 de lo que tiene forma, y todo sale junto | Cambiar el pedido a mitad de camino obliga al coder a re-planear | Menos re-trabajo |
| **Un coder de cada motor, en paralelo** | Los cambios independientes se reparten por naturaleza: **Codex** lo mecánico con un archivo con dueño, **Antigravity** lo visual y de estilo (`agy --mode accept-edits`), **Claude** la lógica con estado que cruza archivos. Sin crédito, la parte pasa al siguiente motor y se dice en el reporte | El presupuesto de Claude es el escaso: en una corrida dos `coder-web` gastaron ~329K y ~218K tokens. Mandar todo a un solo motor externo pierde calidad y, en serie, velocidad | Rápido y bien: QA y la verificación de cada diff no se recortan |
| **Motores externos vigilados** | Todo Codex o Antigravity en segundo plano se lanza con la entrada cerrada (`< /dev/null`), tope de tiempo (`timeout`) y lectura del log al minuto; a "¿cuánto falta?" se responde mirando el proceso, nunca estimando | Codex quedó 15 minutos colgado esperando entrada por consola, y se respondió con una estimación en vez de mirar | Un cuelgue se detecta en un minuto, no en quince |
| **Modos de presupuesto** | `/orquestar --modo ahorro\|normal\|calidad`, por defecto `ahorro`: Codex hace planner, coders no visuales, revisión y adversary hasta agotar su crédito; Antigravity lo visual; Claude solo orquesta, verifica, mide en Chrome y habla con el usuario | El presupuesto de Claude se estaba acabando y el crédito de Codex sin usar se pierde | Claude deja de gastar en lo que otro motor puede hacer, sin bajar la verificación del diff ni la suite |
| **Antigravity con permisos acotados** | Sin interfaz no puede pedir permiso para comandos: se le habilitaron solo `npx tsc -b`, `npm run lint` y `npx vitest run`. **Nunca** `--dangerously-skip-permissions` | Editó bien pero no pudo verificar; en la tarea siguiente se cortó antes de editar por pedir un comando de búsqueda no habilitado | Verifica solo; para tareas que requieren explorar, la tarea le nombra archivo y línea exactos |
| **`/codex` antes del push** | Codex CLI revisa `--uncommitted` en paralelo con QA, en toda corrida salvo Nivel 0 y si hay crédito; nunca bloquea | En dos PRs grandes, 18 hallazgos en tres rondas después del push | Las rondas se adelantan a antes del PR |
| **`ux-ui` + `/ux`** | Agente con el modelo más capaz que revisa la consola viva: contraste WCAG 2.2 + APCA, teclado, foco, ornamento sin función. No escribe código | La consola se veía cargada y no había revisión experta fundamentada | Hallazgos con propuesta exacta para `coder-web` |
| **Principios minimalistas en el pipeline** | Planner con `Requisitos con dueño`, `Borrado / Reusado` y puerta de 1 o 2 vías; coder con cambios quirúrgicos; QA en dos pasadas (¿solo lo del plan? ¿calidad?) | El algoritmo de 5 pasos aplicado también al propio sistema | Menos código que sobra |
| **Retro contra la evidencia fabricada** | `architect` y `planner` no citan `archivo:línea` sin una búsqueda de esa sesión; "ratificado" exige re-verificar; el coder lista solo lo que editó y cómo probó cada mutación | Tres corridas seguidas con citas o reportes falsos (ver Resumen ejecutivo) | Se restituye la redundancia architect ↔ planner |
| **Causa raíz antes del fix** | `coder` y `coder-web` identifican por qué falla antes de editar, no parchan el síntoma y paran si un enfoque falló dos veces; nueva sección `### Causa raíz` en el reporte. QA comprueba que lo que fallaba falle sin el fix y pase con él | Disciplina `root-cause-first`: era la única de 9 que no aparecía en ningún agente | Sin medir todavía: falta replay con una tarea de fix |

> [!warning] Lo que no se recorta para ganar tiempo
> - Verificar el diff contra `git status` antes de dar algo por hecho.
> - Verificar en la base **con datos reales**. Una migración se "probó" sobre una base vacía; la prueba con datos mostró que 14 filas ya referenciaban los valores que se iban a borrar.
> - QA + `adversary` sobre cualquier cambio que borre columnas.
> - El checkpoint humano ante cambios de esquema.
> - Los tests del comportamiento nuevo. Saltear QA no es saltear tests: un coder entregó 384/384 en verde sin un solo test de lo que había agregado.

---

## Capa 1 — Roles y modelos

**Pipeline `/orquestar`:** [[agentes-pipeline/architect|architect]] → [[agentes-pipeline/planner|planner]] → [[agentes-pipeline/coder|coder]] / [[agentes-pipeline/coder-web|coder-web]] → [[agentes-pipeline/qa|qa]] ∥ [[agentes-pipeline/adversary|adversary]].

**Agentes independientes:** [[agentes-pipeline/analyst|analyst]] (preguntas de datos contra las BD), [[agentes-pipeline/ux-researcher|ux-researcher]] (referencias y maquetas), [[agentes-pipeline/ux-ui|ux-ui]] (revisión experta de la consola viva), [[agentes-pipeline/retro|retro]] (patrones repetidos en las corridas) y [[agentes-pipeline/system-auditor|system-auditor]] (el sistema auditado contra su propio fuente).

> [!warning] Estos enlaces pasan por el junction `agentes-pipeline/`
> Obsidian no indexa carpetas que empiezan con punto. El junction `agentes-pipeline/` → `.claude/agents/` las hace visibles; es local y no se versiona. En otra máquina hay que recrearlo: la receta está en [[Meta/Graph-View-Config|Graph View Config §4]].

**Regla para elegir modelo:** no se pregunta "¿es complejo?", sino **"¿hay una red de seguridad después de este paso?"**. Donde otro rol re-verifica, alcanza Sonnet; el modelo más capaz se reserva para donde nadie revisa después.

| Agente | Modelo | Por qué |
|---|---|---|
| `architect` | Sonnet | Compara contra los repos hermanos y el planner re-verifica todo lo que dice |
| `planner` | Sonnet, escalable a Opus (Step 2.7) | Tiene una sola pasada; Opus solo si el Step 2.5 o el 2.6 ya marcaron riesgo o tamaño |
| `coder` / `coder-web` | Sonnet | Ejecutan un plan cerrado y QA revisa después. `coder-web` existe desde que dos corridas editaron React con el coder de C# |
| `qa` | Sonnet | Mucho trabajo procedural; en el razonamiento fino rindió bien |
| `adversary` | Sonnet | Auditor destructivo sobre el diff: 6 vectores de ataque y mutación mental |
| `retro` | Sonnet | Nunca aplica nada solo; todo pasa por aprobación humana |
| `analyst` | Sonnet | Responde directo al usuario sin revisor; por eso subió desde Haiku |
| `ux-researcher` | Sonnet | Independiente; la síntesis visual necesita más que comparar patrones |
| `ux-ui` | **Fable** | Revisión experta con medición real (axe, contraste, teclado); nadie la revisa antes del responsable del repo |
| `system-auditor` | Opus en el frontmatter, **Fable forzado** por el orquestador | Decide la salud de todo lo demás cada ~10 corridas, y nadie audita al auditor |

---

### Tres motores, tres posiciones

El pipeline dejó de ser solo Claude. Los tres se usan por lo que **cada uno ve distinto**, no por costo:

| Motor | Posición | Evidencia |
|---|---|---|
| **Claude** | Orquestar, escribir en paralelo, decidir el reparto | Encontró que una decisión de producto no existía en producción: el arreglo obvio tocaba una función que en modo API ni se ejecuta, y cinco lugares reponían el valor |
| **Codex CLI** | Revisor antes del push · coder de trabajo mecánico | Como revisor halló 2 P2 reales que el pipeline dejó pasar, y **nada** en el código que sí pasó por los gates. Como coder reescribió un archivo con test anti-regresión y declaró su alcance con honestidad. En otra corrida encontró 2 hallazgos reales en un flujo de reintento, uno grave: cambiar un parámetro antes de reintentar creaba un registro duplicado |
| **Antigravity CLI** (Gemini) | Revisor de lo visual (`--mode plan`) · coder de estilos (`--mode accept-edits`) | 7 de 9 hallazgos reales como revisor y 3 cambios de estilo bien aplicados como coder; en la tarea siguiente no llegó a editar por un permiso. En su primera prueba había sido **1 de 4 hallazgos reales** — pero ese 1 fue un badge que una limpieza de estilos dejó sin forma, y no lo vio ningún otro motor |

**De dónde sale el gasto, sin confusión:** los tokens de Codex y Antigravity salen de otras cuentas, no de la de Claude. Delegarles trabajo **reparte** el gasto, no lo reduce. Y la cantidad de agentes **no** multiplica el costo: cinco coders en paralelo gastan lo mismo que cinco en serie — lo que cambia es el tiempo de pared.

Sí hay una eficiencia real y chica, con explicación: un coder propio arranca leyendo `CLAUDE.md`, su `.md` de agente y el mapa del proyecto; Codex arranca solo con la tarea escrita. Por eso una tarea comparable le salió 54K contra los 63–338K de los coders propios.

**La regla que vale para los tres: ninguno es evidencia por sí solo.** El mismo día Antigravity falló dos de cuatro, y el `architect` y el `planner` —los dos de Claude, por separado— afirmaron que un panel de UI existía citando `archivo:línea`, y un `grep` devolvió cero. Lo que cambia el resultado no es qué motor se use: es que alguien corra la búsqueda.

### Cuatro pérdidas de una misma sesión, y su forma común

Todas se podían evitar y ninguna fue un misterio: dos agentes alucinando una cita, el `security-review` revisando el repo equivocado porque calcula su diff contra `origin/HEAD` y no se puede acotar, dos arranques de servidor muertos por lanzar `nohup &` dentro de un comando en background, y un `agy` que tomó `--model` como prompt.

**Las cuatro tienen la misma forma: algo falló en silencio y pareció haber funcionado.** El comando devolvió código 0 y no hizo nada. De ahí la regla que quedó en `orquestar.md`: cuando algo devuelve éxito, hay que verificar que **hizo lo que se esperaba**, no que no dio error.

## Capa 2 — Coordinación

| Técnica | Qué hace | Sin esto |
|---|---|---|
| **Orquestador central** | Todo pasa por `/orquestar`; los agentes no dialogan entre sí | No hay un punto donde auditar o pausar |
| **Handoffs fijos y literales** | `## Architect Report`, `## Plan`, `## Coder Report`, `## QA Verdict`, `## Adversarial Audit Report`, pasados sin resumir | El orquestador resume y se pierden detalles críticos |
| **Niveles 0 / 1 / completo** (Step 0.7) | Nivel 0: edición directa con build verde. Nivel 1: sin architect. Completo: esquema, auth, concurrencia, endpoints nuevos | Un texto cambiado paga cinco agentes |
| **Tarjeta del tablero al inicio** (Step 0.6) | Se resuelve contra el tablero vivo antes de codificar | Se buscó la tarjeta con el PR ya abierto, contra un export de doce días |
| **Checkpoints humanos** (Steps 2.5 y 4.7) | Aprobación explícita ante riesgo de esquema o datos, y antes de push o PR | Operaciones irreversibles sin supervisión |
| **Topes de reintento** | 2 ciclos de QA; 1 ronda de `adversary` con presupuesto propio; `security-review` sin loop automático | 5 rondas de adversary en una corrida |
| **Gates en paralelo, un viaje al coder** (Step 4.4) | QA, `adversary`, `security-review`, `/codex` y los tests de integración se consolidan en un solo paquete | Hasta tres idas y vueltas por el mismo cambio |
| **Architect en modo revisión, condicional** (Step 3.5) | Solo si la corrida cambió estructura; consume un ciclo de QA | Antes era código muerto que nadie invocaba |
| **Reglas duras en cascada** | La misma prohibición la verifican planner, coder y QA, cada uno por su lado | Un solo descuido llega al código |
| **`UNVERIFIED` en vez de citas inventadas** | Lo que no se comprobó se marca; una cita solo vale si sale de una búsqueda de esa sesión | Una cita falsa pasó dos filtros porque parecía prueba |
| **Taxonomía de patrones** (`architect`) | STANDARD / KEEP / IMPROVE / REMOVE / NEW / DEFER, con `archivo:línea` obligatorio | El repo de referencia siempre ganaba: se heredó un `[Authorize]` pelado |
| **Negocio separado de lo técnico** (`planner`) | "El campo no existe" es un gap; "¿debería existir?" va a una sección propia y a los Risk Flags | Las preguntas de negocio se evaporaban al final de la corrida |
| **Pendiente viejo, verificado antes** (Step 0) | Toda nota anterior a la última corrida se comprueba con MCP, grep o `git log` | Cinco notas falsas en una sola sesión |

---

## Capa 3 — Grounding y conectores

| Conector / técnica | Qué hace | Sin esto |
|---|---|---|
| **5 MCP de Azure SQL** (`contracts-db`, `people-db`, `core-db`, `auth-db`, `delivery-db`) | Lectura del esquema y los datos reales en `<sql-host>`. El `planner` tiene 3 en su `tools:` | Se planifica sobre tablas y campos supuestos |
| **Sin queries cruzados de 3 partes** | Azure SQL no los soporta (`Error 40515`): dos queries correlacionadas por `Id` | Un join que compila "en la cabeza" y falla en Azure |
| **Verificación propia del orquestador** | `grep`, `git status` y la base con datos antes de repetir lo que dice un reporte | Un archivo "cambiado" que nadie tocó; un panel inexistente |
| **GitHub** (MCP y `gh`) | PRs contra `develop`, cuerpos en UTF-8 con `--body-file`, lectura de comentarios de bots | PRs en `main` y descripciones corruptas en Windows |
| **Herramienta del tablero de tareas** | Simula antes de escribir, resuelve nombres contra el tablero vivo y relee cada cambio *(retirada de la versión pública)* | Mutaciones apuntadas a ids de un export viejo |
| **HTTP antes que la BD** | Se consumen las APIs de los servicios hermanos antes de leer sus tablas | Acoplarse a tablas internas y saltarse su lógica |
| **Chrome y Figma** (`ux-ui`) | Revisar la app viva sin enviar, guardar ni borrar nada | Opiniones de UX sin medición |

> [!danger] Cero eliminaciones y consentimiento previo
> No se elimina ninguna tarjeta, comentario, adjunto, rama remota, código ni tabla sin una instrucción explícita e inequívoca del responsable del repo. Antes de cualquier mutación o acción destructiva se presenta la propuesta exacta y se espera aprobación.

---

## Capa 4 — Memoria y conocimiento

> [!info] Obsidian como grafo de conocimiento agéntico
> El vault `AcmeOrg/` no es documentación al margen: es memoria activa. Cada nota (agente, corrida, ADR, pregunta de negocio) es un nodo y cada wikilink una arista. El orquestador lo lee en el Step 0 antes de actuar.

| Técnica | Qué hace | Sin esto |
|---|---|---|
| **Mapa de conocimiento** (`INDEX.md`) | Se leen solo los run docs del tema de la tarea, no el libro mayor entero | ~5.6K tokens de columnas irrelevantes en cada corrida |
| **ADRs** (`docs/adr/`) | Contexto, decisión y consecuencias, citables | Se reabren debates ya zanjados |
| **Run docs con métricas honestas** | Duración y tokens por agente; `tokens_fuente: estimado` salvo medición real | Conjeturas presentadas como datos |
| **Memoria de referencia precomputada** | Esquemas y convenciones en markdown | Re-explorar el esquema en cada corrida, o montar un RAG innecesario |
| **Mapas para coders** (`contexto-negocio/web-app-mapa.md`) | El coder sabe dónde está cada pieza sin leer todo `src/` | 10-15 min de exploración por coder |
| **`.claude/` centralizado** | Una sola fuente de agentes, comandos y hooks para los 6 repos | Copias divergentes por repo |
| **Vault validado en cada commit** (`scripts/validar-vault.py`) | Corta el commit si deja una nota huérfana o un wikilink roto | Dos huérfanas en un día cuando solo avisaba |
| **Biblioteca de requisitos** (`requisitos/`) | Cada decisión de negocio queda como REQ con requisitos EARS y escenarios Gherkin con id (`REQ-0002/E1`). Estados `propuesto → confirmado → implementado → verificado`. **Local y fuera de git** por decisión del responsable del repo. **Todavía ningún agente la lee**: eso llega con el Step 0.8 | Las decisiones quedan repartidas entre el chat y `TASKS.md`, y llegan tarde, con coders ya lanzados |
| **Herramientas deterministas** (`.claude/tools/`) | Lo que un modelo hace mal a ojo lo calcula un script: geometría de diagramas, grafo del vault | XML de draw.io a mano: 7 solapamientos en 3 páginas |

---

## Capa 5 — Auditoría antes del PR

Nació de una lección concreta: un revisor automático en GitHub encontró más de 20 fallas sutiles (escrituras compuestas a medias, fuga de estado entre usuarios en la SPA, fallbacks con `[0]`, N+1, carreras) que los tests con mocks nunca vieron. Los mocks no tienen latencia, no simulan un timeout a mitad de una transacción y no guardan estado.

| Técnica | Qué hace | Sin esto |
|---|---|---|
| **`adversary`** | Auditor destructivo del diff: 6 vectores de ataque, 10 heurísticas de producción y mutación mental | Las fallas sutiles las descubre un bot después del push |
| **`security-review`** + checklist CWE | Secretos, JWT, PII y versiones de paquetes | Fugas de datos que no rompen ningún test funcional |
| **`/codex`** | Segunda opinión de otro modelo antes del push | 18 hallazgos en tres rondas después del push, en dos PRs grandes |
| **Tests de integración** (Testcontainers) | SQL Server real en Docker, cuando el cambio toca acceso a datos | Queries que pasan con mocks y fallan en la base |
| **Property-based testing** (FsCheck, fast-check) | Invariantes contra cientos de entradas aleatorias: políticas de reintento, normalizadores de ids, repositorios del frontend | Tres ejemplos felices y ninguna combinación rara |

Las listas completas de vectores y heurísticas viven solo en [[agentes-pipeline/adversary]], su único dueño según `CLAUDE.md`. Una copia ya divergió una vez ("un archivo decía 8 sobre una lista de 10").

---

## Capa 6 — Mejora continua

| Técnica | Qué hace | Estado |
|---|---|---|
| **`retro`** | Busca en los run docs la misma corrección repetida y propone el texto exacto para aprobar | Última: 12 corridas revisadas, 4 agentes corregidos, 2 incidentes descartados por aparecer una sola vez |
| **Regression Watch** | Comprueba si los fixes anteriores se sostuvieron | Detectó una corrida que quedó sin registro |
| **Costo/beneficio de los chequeos caros** | Cuenta cuántas fallas reales atrapa cada chequeo | Runtime/DI: 10 disparos, 6 reales, 0 falsas alarmas; las dos últimas activaciones, sin hallazgos |
| **Consolidación de reglas** | Fusiona reglas duplicadas para que los prompts no crezcan sin fin | QA: un ítem se fusionó en la Pasada 1 |
| **`system-auditor`** | Lee el fuente del sistema: instrucciones que el `tools:` no permite ejecutar, plantillas divergentes, conteos desfasados, modos muertos, loops sin tope. Nunca edita | 1ª auditoría: 1 P1, 9 P2, 9 P3; 32 de 38 memorias estaban en el slug equivocado |
| **Tareas doradas** | 7 tareas fijas para probar un cambio de prompt antes de confiar en él | Una no se puede reproducir |
| **Replay antes de confiar** (Step 0) | Si un `.md` de agente cambió (incluso sin commit), se ofrece correr una tarea dorada | Mira `git status` además de `git log` |
| **Revisores externos como insumo** | Cada hallazgo de un bot se verifica y, si es patrón, se vuelve regla o vector de `adversary` | Así nacieron `adversary` y varias reglas del playbook |
| **Prueba A/B de un advisor** | El mismo `planner` sobre una tarea dorada, sin y con un modelo más capaz como advisor, contra una rúbrica fijada antes de ver resultados | **Sin advisor:** HTTP ✅, reuso 🟡 (endpoint nuevo sin evaluar la vista existente), campos financieros ❌ (decidió no consultar al responsable), titular y lista vacía ✅, **0 de 9 citas falsas**, 131.7K tokens, ~6.6 min. **Con advisor:** marca los campos financieros como **decisión de negocio bloqueante**; HTTP, titular y citas igual de bien; el reuso sigue 🟡; 165.3K tokens (+25 %) y ~9.3 min. Queda **activado** para todos los agentes (n=1: orienta, no demuestra) |

`retro` y `system-auditor` miran fuentes distintas: uno el comportamiento en las corridas, el otro la coherencia del fuente. Confundirlos lleva a arreglos opuestos: "el agente se equivoca seguido" no es lo mismo que "el agente tiene una instrucción imposible de cumplir".

---

## Técnicas de ingeniería aplicadas

1. **Outbox transaccional.** El mensaje se persiste en la misma transacción que la entidad; un job de Quartz reclama lotes con `ROWLOCK, READPAST, UPDLOCK` para que las réplicas no se pisen.
2. **Descubrimiento de servicios.** Ninguna URL fija: se resuelven en runtime contra `api-auth` y se cachean con `IMemoryCacheService` (Redis con fallback a memoria).
3. **Identidad propia por servicio.** `api-core` se autentica como `<identidad-servicio>@<dominio>`, nunca con credenciales prestadas.
4. **Chats de WhatsApp con `@lid`.** `ChatIdNormalizer` preserva el LID de WAHA y el handler de entrantes no lo trata como teléfono.
5. **UTF-8 en la CLI de Windows.** Textos largos siempre por archivo UTF-8 sin BOM (`--body-file`), nunca por argumento.
6. **Build limpio.** Se detiene el Host antes de `dotnet build` para evitar DLLs bloqueadas.

---

## Comandos y skills

Un agente es *quién* hace algo; un skill es *cómo* se hace, reusable por cualquiera. Todos viven en `.claude/commands/` y se ven en el vault por el junction `comandos-pipeline/`:

- [[comandos-pipeline/orquestar|/orquestar]]: el pipeline completo, con los niveles, las palancas de paralelismo y los gates.
- [[comandos-pipeline/worktree|/worktree]]: olas en paralelo (crear, listar, sincronizar con develop, cerrar), con base de datos propia opcional en Docker.
- [[comandos-pipeline/codex|/codex]]: Codex CLI como revisor antes del push en toda corrida salvo Nivel 0, y también como coder para trabajo mecánico de un solo archivo.
- [[comandos-pipeline/antigravity|/antigravity]]: Antigravity CLI (`agy`, Gemini) para lo visual: como revisor es el único que se pregunta cómo se ve el resultado, y también como coder de estilos.
- [[comandos-pipeline/ux|/ux]]: revisión con `ux-ui` en cuatro modos (auditar, deslop, accesibilidad, corregir); lo aprobado se implementa con `/orquestar`.
- [[comandos-pipeline/shunt|/shunt]]: lecturas grandes y salidas de comandos desviadas a un motor barato; `code-write.sh` para archivos mecánicos calcados de una referencia.
- [[comandos-pipeline/requisitos|/requisitos]]: redactar, confirmar, versionar y marcar obsoleto un REQ de la biblioteca de requisitos.
- [[comandos-pipeline/verificar-ramas|/verificar-ramas]]: la topología `main`/`develop`/`qa` y los PRs que cayeron en el target equivocado.
- [[comandos-pipeline/diagramar|/diagramar]]: `.drawio` desde JSON con layout calculado. Escribir el XML a mano está prohibido desde que produjo 7 solapamientos en 3 páginas.
- [[comandos-pipeline/auditar-vault|/auditar-vault]]: salud del grafo, grupos de color y junctions; solo propone.

> [!warning] Corrección 2026-09-09
> Versiones anteriores listaban `/plan`, `/grill-me` y `explain-usage`. No existen. `retro` y `system-auditor` son agentes, no skills.

---

## Riesgos y deuda abierta

| Riesgo | Evidencia | Mitigación hoy | Qué falta |
|---|---|---|---|
| **Evidencia fabricada** | Tres corridas seguidas | Reglas en 4 agentes (retro) y verificación propia del orquestador | Probarlo con una tarea dorada: ninguna corrida lo ejercitó todavía |
| **Registro que se salta** | Una corrida sin run doc ni fila en `INDEX.md` | Advertencia fuerte en el Step 5 | Convertirlo en gate si hay una tercera vez (decide el responsable del repo) |
| **Modo demo sin auditoría** | Dos corridas cerraron sin `adversary` | La regla dice acumular y auditar al cierre | Registrar ese cierre en el run doc |
| **Paralelismo sobre archivos compartidos** | Dos trabajos sobre los mismos archivos encolaron ~28 min | Dueño exclusivo por archivo, interfaz fija, un coder por repo si se comparte | Nada: queda documentado en el Step 3 |
| **Más tokens por corrida** | La corrida más cara: ~1.7M (coders 1.15M) | Decisión consciente: se prioriza el reloj | Seguir la serie por si el costo se dispara sin ganar tiempo |
| **Dependencia de el crédito de Codex** | Se quedó sin crédito en plena sesión | `/codex` se omite sin bloquear | Codex todavía no tiene los MCP de BD configurados |
| **Pruebas de regresión del propio sistema** | Una tarea dorada no se puede reproducir | — | Reescribirla |
| **Mejoras pendientes al auditor** | 10 puntos de ejecutabilidad de la 1ª auditoría | — | Aplicarlos a `system-auditor.md` |
| **Costo del advisor, sin medir fuera del planner** | Todos los subagentes lo heredan; la corrida más cara gastó 1.15M tokens solo en coders | Se desactiva con `/advisor off` | Medirlo en el próximo `/orquestar` completo; el frontmatter del run doc no tiene campo para consultas al advisor |
| **Tarea dorada con resultado esperado vencido** | Dice "Risk Flags todos en no", pero el plan correcto de hoy marca una decisión de negocio | — | Actualizar su texto (espera aprobación del responsable) |
| **Requisitos sin respaldo** | `requisitos/` está en `.gitignore`: sin historial y solo en una máquina | — | Si se vuelve fuente del pipeline, decidir respaldo (copia a la nube) |
| **Sesiones que se pisan en el vault** | Commits con trabajo de otra sesión | Stagear por ruta y leer el diff | Nada automático lo impide |
| **Conventional commits sin validar** | Adoptado a mitad de septiembre | Instrucción en `orquestar.md` | Un hook, si empieza a fallar |

---

## Opciones evaluadas

| Opción | Estado | Por qué |
|---|---|---|
| **RAG semántico** sobre la documentación | Descartado por ahora | El corpus es chico y está ordenado: grep y la memoria precomputada resuelven lo mismo, más barato y de forma determinista. Conviene reevaluarlo con cientos de corridas y fallas de búsqueda por vocabulario |
| **Biblioteca de requisitos / Spec-Driven Development** (`requisitos/`, skill `/requisitos`, overlay Alt+R en el frontend) | **Etapa 1 hecha:** README, plantilla y 7 REQ como borradores en `requisitos/propuestas/`. Falta: confirmarlos y los cambios al pipeline. Overlay Alt+R diferido hasta 3 corridas con REQ | Trazabilidad requisito → test → PR, con ids de escenario que planner, coder y QA citan y verifican |
| **Pipeline propio para los servicios hermanos** | Especulativo | Tiene sentido cuando el checkpoint de "arreglar en la fuente" acumule suficientes casos de "sí" |
| **Feedback desde producción** | Especulativo | Hoy nada cierra el loop después del deploy; requiere observabilidad |
| **Automatizar según la confianza** | No se hará en silencio | El valor de un checkpoint humano es que no depende de cómo salió la última vez |
| ~~Lint de los `.md` de agentes~~ | Hecho | Lo cubre `system-auditor`, y va más lejos que un lint |

---

## Glosario

| Término | En una línea |
|---|---|
| **Harness** | La arquitectura del proceso: roles, checkpoints, reglas en cascada. Decide si sale bien |
| **Tokenmaxing** | Cómo se gasta el contexto dentro de ese proceso. Decide si sale barato |
| **Ola** | Un grupo de tarjetas trabajadas en paralelo, cada una en su worktree y su rama |
| **Interfaz fija** | Firma exacta (ruta, nombres, tipos) decidida antes de lanzar coders en paralelo, para que las mitades encajen |
| **Nivel 0 / Nivel 1** | Edición directa del orquestador con build verde / pipeline sin architect |
| **Evidencia de primera mano** | Una afirmación respaldada por una búsqueda hecha en esa sesión, no reconstruida de un nombre |
| **MCP** | Protocolo que le da a un agente acceso a un sistema externo como herramienta, con permisos acotados |
| **Handoff** | La entrega entre agentes, siempre en una estructura fija y sin resumir |
| **ADR** | Registro corto de una decisión de arquitectura: contexto, decisión, consecuencias |
| **Grounding** | Que lo que dice un agente esté respaldado por la base, el código o un grep reales |
| **Skill** | Un procedimiento reusable, independiente de cualquier rol |
| **REQ** | Un requisito de negocio escrito antes de programar, con criterios que se pueden probar (`requisitos/`) |
| **EARS / Gherkin** | Formatos del REQ: frases "Cuando…, el sistema deberá…" y escenarios "Dado / Cuando / Entonces" |

---

*Ver `docs/runs/RETRO-LOG.md` para la mejora continua, `SYSTEM-AUDIT-LOG.md` para las auditorías del sistema y `GOLDEN-TASKS.md` para las tareas de replay (vacíos en esta versión pública).*
