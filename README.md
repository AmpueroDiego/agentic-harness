---
tipo: indice
tags: [harness, codex, onboarding]
---

# Llama Agentic Harness

**Un sistema de trabajo para Codex que convierte una petición en decisiones claras, trabajo especializado y resultados comprobables.**

Llama Agentic Harness reúne agentes, skills, scripts y memoria para trabajar sobre proyectos reales.
Conecta el contexto del negocio con el código, las pantallas y las herramientas disponibles.
El agente principal coordina el trabajo y comprueba los resultados antes de cerrarlo.

Una tarea pequeña avanza directamente. Una tarea ambigua puede pasar por `$align-to-spec`.
Un fallo difícil puede usar `$diagnosing-bugs`. Un cambio sensible suma revisión de contratos y casos adversos.
Cada flujo se activa por la necesidad de la tarea; no hay que lanzar todos los agentes.

La comunicación sigue una regla concreta: **español sencillo, voz activa y explicaciones precisas**.
El Harness conserva las decisiones y registra qué se comprobó, qué cambió y qué sigue pendiente.

Versión propuesta: **2.0.0**. Consulta [VERSION](VERSION).

## Qué aporta

| Capacidad | Resultado práctico |
|---|---|
| **Grounding** | Hallazgos ligados a código, pantallas, fuentes o mediciones que puedes comprobar. |
| **Diez perfiles de agentes** | Planificación, investigación, implementación, QA y revisiones de contratos, seguridad y arquitectura según la tarea. |
| **39 entradas de skills** | Protocolos para alinear requisitos, diagnosticar fallos, UX/UI, diseño, investigación, código y coordinación. |
| **Edge y Playwright** | Inspección de interfaces, redirecciones y errores JavaScript con perfiles temporales. |
| **MCP y REPL persistente** | Conexión con herramientas externas y reutilización del contexto de ejecución cuando el entorno lo permite. |
| **Scripts reutilizables** | Validación del paquete, mantenimiento de adaptadores, revisión de texto y tareas de evaluación repetibles. |
| **Memoria Markdown y Obsidian** | Decisiones, ADRs y runs navegables sin depender de una base de datos propietaria. |
| **Retrospectivas con evidencia** | Detección de fallos repetidos y propuestas concretas para mejorar el proceso. |
| **Funnel Studio opcional** | Análisis y adaptación de ofertas y páginas de captación mediante protocolos y herramientas de medición. |

Las skills incluyen cuatro entradas nuevas de Codex, 34 adaptadores generados y un catálogo de seguridad heredado.
La sección de [compatibilidad](#compatibilidad-y-reutilización) explica sus diferencias.

## Empezar

1. Clona el repositorio y abre su raíz en Codex.
2. Lee [AGENTS.md](AGENTS.md) y el [mapa de arquitectura](LLAMA-HARNESS.md).
3. Revisa los modelos seleccionados en [.codex/agents/](.codex/agents/) según tu cuenta.
4. Indica el proyecto, el resultado esperado y las restricciones relevantes.
5. Prepara navegador o conexiones MCP cuando la tarea los necesite.
6. Revisa y confía los hooks mediante `/hooks`, si tu cliente admite esa función.

Puedes empezar con una petición como esta:

```text
Trabaja en [proyecto] para resolver [problema].
Lee sus instrucciones y comprueba el estado real antes de proponer cambios.
Usa especialistas si la complejidad lo justifica.
Entrega el cambio y la evidencia de las comprobaciones realizadas.
```

La configuración local habilita agentes y limita su concurrencia.
Los permisos globales y las integraciones externas se configuran en cada instalación.
Los instaladores existentes preparan el sistema anterior de Claude; Codex descubre las instrucciones al abrir la raíz.

## Por qué existe

| Problema frecuente | Respuesta del Harness |
|---|---|
| La petición admite varias interpretaciones | `$align-to-spec` delimita resultado, alcance y decisiones que faltan. |
| Un bug se corrige sin conocer su causa | `$diagnosing-bugs` busca una señal reproducible y contrasta hipótesis. |
| El agente afirma que algo funciona sin observarlo | QA separa resultados ejecutados, observaciones e inferencias. |
| Una tarea larga pierde decisiones entre sesiones | Goals conservan el objetivo; ADRs y runs guardan decisiones y evidencia. |
| Un cambio sensible cruza contratos o permisos | Revisores especializados examinan el diff; el sandbox mantiene sus límites. |

La secuencia es sencilla: entender el proyecto, elegir el flujo, hacer el cambio y revisar la evidencia.
El agente principal conserva la responsabilidad del resultado en cada paso.

## Grounding: trabajar desde hechos comprobables

El grounding vincula una afirmación con la fuente que permite comprobarla.
Aquí se aplica al contexto del proyecto, los hallazgos de UX y las comprobaciones del trabajo.

| Situación | Evidencia esperada |
|---|---|
| Entender un proyecto | Sus instrucciones, README, manifiestos, contratos y código existente. |
| Reportar un defecto | Ruta, comportamiento observado y condición que lo reproduce. |
| Revisar una interfaz | Pantalla real, captura fiel o preview, con el elemento y su impacto identificados. |
| Hablar de contraste o accesibilidad | Medición o comprobación del criterio correspondiente; lo pendiente se declara. |
| Explicar un dato externo | Fuente consultada y fecha cuando su actualidad importa. |
| Cerrar una implementación | Diff revisado y resultados de las comprobaciones que realmente se ejecutaron. |

Por ejemplo, una respuesta HTTP correcta solo confirma esa respuesta.
Una página de login visible confirma la navegación inicial; la vista autenticada necesita su propia comprobación.
El Harness pide separar observaciones, inferencias y decisiones para que puedas evaluar cada conclusión.

La skill [ux-review](.agents/skills/ux-review/SKILL.md) concreta este enfoque para interfaces.
Las [reglas de trabajo](AGENTS.md) lo aplican a las fuentes y al cierre de tareas.

## Agentes especializados y coordinación

Los perfiles nativos viven en [.codex/agents/](.codex/agents/).
El principal asigna alcance, entradas y archivos; después recoge resultados y verifica la evidencia.
Las tareas independientes pueden avanzar en paralelo con responsabilidades separadas.

| Perfil | Responsabilidad |
|---|---|
| `planner` | Definir plan, alcance, aceptación, riesgos y puntos de revisión. |
| `code_explorer` | Investigar rutas de código y convenciones antes de implementar. |
| `implementer` | Ejecutar un cambio delimitado sobre los archivos asignados. |
| `qa_reviewer` | Contrastar la implementación con el plan y las comprobaciones disponibles. |
| `contract_reviewer` | Revisar contratos, compatibilidad y límites de datos. |
| `adversarial_reviewer` | Buscar fallos de borde, abuso, concurrencia y recuperación en cambios sensibles. |
| `architecture_reviewer` | Proponer hasta tres mejoras de arquitectura con evidencia y tradeoffs; no modifica código. |
| `retro` | Detectar problemas repetidos en los runs y proponer mejoras verificables. |
| `system_auditor` | Revisar perfiles, referencias, handoffs, hooks y límites del propio Harness. |
| `llama_funnel_specialist` | Ejecutar un rol acotado del módulo Funnel Studio. |

El [flujo por riesgo](CodexMemory/workflow.md) evita sobredimensionar cambios pequeños.
Las tareas relevantes reciben plan y revisión; los cambios sensibles añaden controles especializados.
Los revisores entregan `PASS` o `FINDINGS`; el principal conserva la decisión final.
Las reparaciones de los mismos hallazgos se limitan normalmente a dos rondas.

## Elegir el flujo adecuado

La descripción de cada skill indica cuándo Codex puede seleccionarla. También puedes pedirla por nombre.
El agente principal decide si necesita especialistas y les entrega alcance, archivos y evidencia.

| Si necesitas… | Usa | Resultado visible |
|---|---|---|
| Aclarar una petición importante | [`$align-to-spec`](.agents/skills/align-to-spec/SKILL.md) | Una especificación breve con alcance, decisiones pendientes y condición de cierre. |
| Encontrar la causa de un fallo difícil | [`$diagnosing-bugs`](.agents/skills/diagnosing-bugs/SKILL.md) | Señal reproducible, hipótesis descartadas y causa respaldada por evidencia. |
| Evaluar una pantalla real | [`$ux-review`](.agents/skills/ux-review/SKILL.md) | Hallazgos localizados, impacto y propuestas concretas. |
| Revisar fricción arquitectónica | `architecture_reviewer` | Hasta tres oportunidades justificadas, con riesgos y tradeoffs; sin cambios automáticos. |
| Adaptar un funnel | [`$llama-funnel-studio`](.agents/skills/llama-funnel-studio/SKILL.md) | Mediciones, decisiones de oferta y directivas para el producto destino. |

Por ejemplo: «El formulario del CRM falla solo después de volver desde login».
Codex puede reunir la ruta, la respuesta HTTP y el error del navegador antes de tocar código.
Si la causa sigue incierta, `$diagnosing-bugs` organiza la investigación.
Si el cambio afecta autenticación, `contract_reviewer` revisa el diff antes del cierre.

Este mapa toma como referencia la separación entre flujos y prácticas del [repositorio de skills de Matt Pocock](https://github.com/mattpocock/skills).
Los protocolos de Llama conservan sus propios permisos, roles y fuentes de proyecto.

## Skills de UX, UI y diseño

El catálogo cubre investigación, dirección visual, componentes, implementación y revisión de pantallas.
Puedes elegir una skill para una necesidad concreta o combinar varias por etapas.

### Investigación y evaluación

| Skill | Para qué sirve |
|---|---|
| [`$ux-review`](.agents/skills/ux-review/SKILL.md) | Auditar una interfaz con evidencia visible, prioridades y cambios propuestos. |
| [`$user-research`](.agents/skills/user-research/SKILL.md) | Preparar investigación centrada en las personas y sus tareas. |
| [`$research-synthesis`](.agents/skills/research-synthesis/SKILL.md) | Organizar hallazgos de investigación en temas y recomendaciones. |
| [`$design-critique`](.agents/skills/design-critique/SKILL.md) | Revisar usabilidad, jerarquía y coherencia de una propuesta visual. |
| [`$accessibility-review`](.agents/skills/accessibility-review/SKILL.md) | Revisar barreras de accesibilidad con criterios explícitos. |

### Dirección visual e implementación

| Skill | Para qué sirve |
|---|---|
| [`$visual-direction`](.agents/skills/visual-direction/SKILL.md) | Explorar direcciones visuales ligadas al público, producto y restricciones. |
| [`$color-system`](.agents/skills/color-system/SKILL.md) | Definir tokens semánticos, paletas, estados, temas y contraste medido. |
| [`$design-system`](.agents/skills/design-system/SKILL.md) | Trabajar sobre componentes y criterios compartidos del sistema visual. |
| [`$crm-ux-patterns`](.agents/skills/crm-ux-patterns/SKILL.md) | Diseñar tablas, filtros y flujos de trabajo propios de un CRM. |
| [`$image-to-code`](.agents/skills/image-to-code/SKILL.md) | Llevar una captura o mockup al stack existente y comparar el resultado renderizado. |
| [`$ux-copy`](.agents/skills/ux-copy/SKILL.md) | Redactar textos de interfaz que ayuden a completar tareas. |
| [`$design-qa`](.agents/skills/design-qa/SKILL.md) | Comparar diseño aprobado e implementación en estados y tamaños equivalentes. |
| [`$design-handoff`](.agents/skills/design-handoff/SKILL.md) | Preparar la entrega de diseño a desarrollo. |

Un recorrido posible es investigación → síntesis → dirección visual → componentes → implementación → QA visual.
Cada etapa utiliza el contexto y los componentes del proyecto destino.
Las comprobaciones de accesibilidad requieren medidas reales; invocar una skill no certifica conformidad.

### Calidad de código y escritura

[`$antislop-code`](.agents/skills/antislop-code/SKILL.md) revisa comentarios genéricos conservando los que aportan contexto técnico.
[`$antislop-copywriting`](.agents/skills/antislop-copywriting/SKILL.md) ayuda a quitar fórmulas vacías y redacción artificial.
[`$thermo-nuclear-code-quality-review`](.agents/skills/thermo-nuclear-code-quality-review/SKILL.md) aporta una revisión exigente de estructura y mantenibilidad.

El catálogo también incluye entradas para requisitos, priorización, worktrees, diagramas y coordinación de proyectos.
Consulta todas las entradas en [.agents/skills/](.agents/skills/).
Algunas conservan referencias a herramientas o repositorios del sistema anterior y necesitan adaptación al destino.

### Procedencia y atribución

Siete skills de diseño proceden del paquete de Anthropic: accesibilidad, crítica, handoff, sistemas, síntesis, investigación y UX copy.
El [aviso de terceros](.claude/skills/_third-party/NOTICE.md) identifica los archivos y su licencia Apache-2.0.
Consulta el [repositorio de origen](https://github.com/anthropics/knowledge-work-plugins/tree/main/design) y la [licencia conservada](.claude/skills/_third-party/LICENSE-APACHE-2.0.txt).

Las skills anti-slop atribuyen su origen a `miqdadbadjuber/anti-slop` y conservan su [licencia MIT](.claude/skills/antislop-code/LICENSE).
La revisión de calidad conserva otra [licencia MIT con atribución a Cursor](.claude/skills/thermo-nuclear-code-quality-review/LICENSE).
Cada componente mantiene su procedencia; el catálogo combina material propio y reutilizado.

## Español sencillo y preciso

[AGENTS.md](AGENTS.md) pide español sencillo, voz activa, una idea por oración y un máximo de 20 palabras por oración.
La explicación empieza por el resultado y añade el detalle necesario para evaluarlo.
Los términos técnicos se conservan cuando ayudan a evitar ambigüedades.

Ejemplo de un cierre útil:

> Conversaciones redirige al login. El servidor responde y la carga inicial no registra errores JavaScript.
> Falta comprobar la pantalla después de iniciar sesión.

Las fuentes externas conservan su idioma original.
Las skills de escritura complementan estas instrucciones; la regla del proyecto sigue siendo la referencia.

## Navegador con Edge y ejecución persistente

Playwright permite abrir páginas, observar navegación, recoger errores y contrastar la interfaz renderizada.
El REPL persistente conserva referencias al navegador, contexto y página durante la investigación.
Cada tarea utiliza un perfil temporal aislado del perfil personal.

El workspace de preparación comprobó navegación local con Microsoft Edge y Playwright desde el REPL.
El repositorio incluye la [guía y un ejemplo de Edge](.codex/browser/README.md) para preparar otra instalación.
Playwright, Edge y el REPL dependen del equipo y del cliente disponibles.

Computer Use aporta otro camino cuando la tarea requiere observar o manejar aplicaciones compatibles.
Su disponibilidad depende del entorno; cada herramienta conserva su propio flujo de observación y acción.

## Conectar MCP y herramientas externas

MCP permite acercar fuentes y acciones externas al trabajo del agente.
Puedes conectar documentación, diseño, gestión de tareas o datos mediante servidores compatibles y autorizados.
El Harness documenta cómo descubrir las herramientas disponibles y elegir las pertinentes para cada tarea.

En Codex CLI puedes registrar servidores, consultar su estado y autenticar los que utilizan OAuth.
Los siguientes comandos son plantillas; sustituye el nombre y la URL por los de tu servidor:

```sh
codex mcp add mi-servidor --url https://mcp.example.com/mcp
codex mcp list
codex mcp login mi-servidor
```

El último comando aplica cuando el servidor requiere OAuth.
Consulta la [documentación oficial de MCP](https://learn.chatgpt.com/docs/extend/mcp?surface=cli) para las opciones de tu cliente.
La [guía del Harness](docs/mcp-repl.md) explica descubrimiento diferido, sesiones persistentes y separación entre MCP, plugins y herramientas nativas.

Configurar un servidor y comprobar que sus herramientas responden son pasos distintos.
Las credenciales y conexiones personales permanecen fuera del repositorio.
Clonar el Harness aporta sus protocolos; cada instalación prepara sus conexiones.

## Memoria, Obsidian, ADRs y runs

[CodexMemory/](CodexMemory/README.md) guarda el conocimiento compartido en archivos Markdown enlazados.
Puedes abrir esa carpeta como vault de Obsidian o trabajar directamente con los archivos.
Obsidian es opcional; la memoria se puede leer y versionar con herramientas normales.

| Pieza | Qué conserva | Ubicación |
|---|---|---|
| **Índice** | Entradas al flujo, las decisiones y los registros. | [INDEX.md](CodexMemory/INDEX.md) |
| **ADR** | Contexto, decisión, alternativas, consecuencias y condición para revisarla. | [Plantilla ADR](CodexMemory/adr/TEMPLATE.md) |
| **Run record** | Objetivo, cierre esperado, cambios, decisiones, comprobaciones y pendientes de una ejecución relevante. | [Plantilla de run](.codex/templates/run-record.md) |
| **Runs del Harness** | Evidencia de trabajos sobre este sistema. | [Registros](CodexMemory/runs/) |
| **Memoria del producto** | Decisiones y registros propios de cada aplicación. | Dentro del proyecto dueño. |

Un ADR responde «¿por qué elegimos esta arquitectura?».
Un run responde «¿qué se hizo y qué evidencia quedó?».
El objetivo activo conserva el estado del trabajo cuando la herramienta de Goals está disponible.
Las tareas pequeñas conservan un flujo directo; los registros se reservan para trabajo relevante.

La distribución ofrece una plantilla de ADR lista para completar.
El [panel anterior](Home.md) conserva consultas y recetas de Obsidian; sus dashboards requieren configuración y datos propios.
El vault nuevo funciona sin instalar ese panel ni sus plugins.

### El agente retro y la mejora del proceso

[`retro`](.codex/agents/retro.toml) revisa runs y decisiones relacionadas para encontrar problemas recurrentes.
Exige al menos dos ocurrencias antes de proponer una regla general.
Su propuesta incluye el texto, la ubicación, el beneficio, el coste y una comprobación futura.

El ciclo es **ejecución → evidencia → retrospectiva → propuesta de mejora → decisión del responsable**.
El agente propone; las instrucciones se cambian mediante una decisión explícita.
[`system_auditor`](.codex/agents/system_auditor.toml) complementa esa revisión buscando inconsistencias en la configuración del Harness.

## Scripts que sostienen el sistema

Los scripts convierten comprobaciones repetidas en operaciones concretas.
La tabla distingue validadores locales, mantenimiento y herramientas del sistema anterior.

| Script o herramienta | Función | Alcance |
|---|---|---|
| [`validate_codex_harness.py`](scripts/validate_codex_harness.py) | Validar TOML, hooks portables, entradas nativas principales, sintaxis Python y límites del paquete. | Local, sin servicios externos. |
| [`generar-skills-codex.py`](.claude/scripts/generar-skills-codex.py) | Generar adaptadores desde las fuentes originales; `--verificar` comprueba su vigencia sin escribir. | Catálogo compartido. |
| [`revisar-tildes.py`](.claude/scripts/revisar-tildes.py) | Detectar corrupción de tildes, eñes y UTF-8 en cambios y archivos nuevos. | Diff de Git. |
| [`replay_golden_tasks.py`](scripts/replay_golden_tasks.py) | Imprimir escenarios y criterios para evaluación manual repetible. | Imprime tareas; no ejecuta evaluaciones. |
| [`validar-vault.py`](scripts/validar-vault.py) | Revisar enlaces y problemas de codificación en Markdown. | Validador heredado con convenciones propias. |
| [`pre_tool_use_guard.cjs`](.codex/hooks/pre_tool_use_guard.cjs) | Detectar determinados patrones destructivos o de secretos antes de comandos Bash. | Hook revisable, con cobertura limitada. |
| [Scripts de coordinación](.claude/scripts/) | Conservar herramientas para agentes, PRs, traspasos y trabajo en curso. | Flujo anterior; revisar configuración y efectos. |
| [Herramientas de Studio](systems/llama-funnel-studio/tools/README.md) | Capturar, analizar y comprobar contratos de casos de funnels. | Módulo opcional con dependencias propias. |

Ejemplos desde la raíz del repositorio, con Python instalado:

```sh
python scripts/validate_codex_harness.py
python .claude/scripts/generar-skills-codex.py --verificar
python scripts/replay_golden_tasks.py --id GT-01
```

Para regenerar adaptadores, edita primero la fuente en `.claude/` y ejecuta el generador sin `--verificar`.
Conserva las entradas escritas a mano y evita mantener dos copias del mismo protocolo.
Los validadores estructurales comprueban archivos; la calidad de una implementación requiere sus propias comprobaciones.

## Funnel Studio como módulo opcional

[Funnel Studio](systems/llama-funnel-studio/README.md) aporta 24 funciones documentadas entre funnel, adquisición, ingeniería y operaciones.
Es útil para estudiar una oferta, extraer mecanismos transferibles y adaptarlos a otro producto.
Combina captura y análisis con protocolos de interpretación y contratos de salida.

Su adaptación evalúa público, oferta, ticket, ciclo de decisión, marca y evidencia disponible.
La reproducción ordena tres etapas: estrategia de negocio, capas especialistas y copywriting.
El entregable habitual es un plan; construir una página es un paso adicional.

| Necesidad | Entrada recomendada |
|---|---|
| Mejorar una pantalla interna del CRM | `$ux-review`, `$crm-ux-patterns`, `$color-system` o `$design-qa`, según el caso. |
| Definir una identidad visual de producto | `$visual-direction` y `$design-system`. |
| Analizar una landing y adaptar su estrategia | `$llama-funnel-studio`. |
| Resolver un bug o cambiar arquitectura | Perfiles técnicos y reglas del proyecto. |

Puedes usar únicamente las disciplinas pertinentes cuando el objetivo lo permita.
La extracción completa de once especialidades corresponde a un pedido específico.
Convertir Studio en un protocolo general para cualquier producto exigiría revisar sus contratos y criterios de negocio.
Los hechos, activos y pruebas ausentes se marcan como faltantes.

## Compatibilidad y reutilización

Las entradas [`ux-review`](.agents/skills/ux-review/SKILL.md), [`llama-funnel-studio`](.agents/skills/llama-funnel-studio/SKILL.md), [`align-to-spec`](.agents/skills/align-to-spec/SKILL.md) y [`diagnosing-bugs`](.agents/skills/diagnosing-bugs/SKILL.md) contienen protocolos nuevos para Codex.
Los 34 adaptadores generados apuntan a comandos y skills originales en `.claude/`.
La entrada [`security`](.agents/skills/security/SKILL.md) conserva un catálogo heredado con referencias de ejemplo a AcmeOrg y .NET/React.
Ese catálogo necesita contextualización antes de aplicarlo a otro proyecto.

Los adaptadores preservan sus fuentes y utilizan las equivalencias de [AGENTS.md, sección 3](AGENTS.md#3-compatibilidad-con-claude).
Algunos flujos requieren Bash, herramientas conectadas o configuración del sistema anterior.
Su presencia en el catálogo permite descubrirlos; cada uso debe comprobar sus dependencias.

Los [perfiles de stack](profiles/README.md) conservan ejemplos para .NET, Node/TypeScript y Python.
El instalador anterior los utiliza para preparar agentes de Claude.
En Codex sirven como referencia; las convenciones reales de cada proyecto siguen siendo la fuente principal.

Consulta [README.claude.md](README.claude.md), [CLAUDE.md](CLAUDE.md) y [AGENTS.claude.md](AGENTS.claude.md) para ese flujo.

## Límites operativos

Los agentes heredan permisos; un perfil revisor no crea aislamiento de seguridad.
Los hooks requieren confianza explícita y el matcher incluido cubre Bash.
El navegador, las herramientas de computadora y los servidores MCP dependen de cada instalación.
Las acciones externas, despliegues y cambios sensibles siguen la autorización y las reglas del proyecto.
Los registros públicos excluyen credenciales, datos privados y contexto de clientes.

Consulta los [escenarios de control](CodexMemory/guardrail-scenarios.md) y la [auditoría del paquete](docs/harness-audit.md).

## Mapa del repositorio

| Ruta | Contenido |
|---|---|
| [AGENTS.md](AGENTS.md) | Instrucciones de trabajo, idioma y coordinación. |
| [LLAMA-HARNESS.md](LLAMA-HARNESS.md) | Arquitectura compartida y detalle de Studio. |
| [.codex/README.md](.codex/README.md) | Perfiles, configuración y hooks de Codex. |
| [.agents/skills/](.agents/skills/) | Catálogo de skills y adaptadores. |
| [.claude/](.claude/) | Fuentes y herramientas del sistema anterior. |
| [CodexMemory/INDEX.md](CodexMemory/INDEX.md) | Memoria, ADRs y runs del Harness. |
| [docs/mcp-repl.md](docs/mcp-repl.md) | Descubrimiento de herramientas y ejecución persistente. |
| [docs/mattpocock-branches.md](docs/mattpocock-branches.md) | Ideas contrastadas con las ramas públicas de `mattpocock/skills`. |
| [scripts/](scripts/) | Validadores y herramientas auxiliares. |
| [profiles/](profiles/) | Convenciones de stack reutilizables. |
| [systems/](systems/) | Módulos de dominio opcionales. |

Los cambios para publicación utilizan una rama y un pull request.
Licencia general: [MIT](LICENSE). Los componentes de terceros conservan sus licencias y atribuciones.
