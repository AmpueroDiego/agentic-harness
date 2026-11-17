# Llama Harness

**Llama Harness** es el sistema de trabajo compartido de Codex para los proyectos de Llama Solutions: instrucciones, agentes, skills, memoria, revisiones y controles. **Llama Funnel Studio** es su sistema de dominio para analizar funnels, transferir patrones a otro producto y, si se solicita, llevar el plan a una implementación real.

El Harness conecta los proyectos; no reemplaza sus fuentes. El código, contratos, reglas de marca, decisiones de producto y protocolos de cada proyecto siguen viviendo junto a ese proyecto.

## Qué hace especial a Llama Harness

**Especializado en productos digitales: ingeniería, UX, adquisición y conversión dentro de un mismo flujo.**

| Capacidad | Aplicación concreta |
|---|---|
| **Edge + Playwright** | Navegar, comprobar redirecciones y recoger errores JavaScript desde un REPL persistente con perfiles temporales. |
| **Diez perfiles de agentes** | Planificar, explorar, implementar y revisar código o arquitectura; auditar el Harness y estudiar fallos recurrentes. |
| **24 funciones de Funnel Studio** | Conectar oferta, psicología, diseño, copy, adquisición, ingeniería y operaciones mediante contratos de salida. |
| **Memoria con evidencia** | Conservar decisiones y resultados comprobados en Markdown, junto al proyecto que los produce. |
| **Herramientas según la tarea** | Descubrir capacidades disponibles y reutilizar sesiones de ejecución, sin asumir integraciones instaladas. |
| **Coordinación con límites** | Repartir archivos entre tareas independientes, sintetizar revisiones y limitar las rondas de reparación. |

### Del problema a una comprobación real

Si una pantalla del CRM no carga, el flujo puede revisar HTTP, seguir la redirección en Edge y recoger errores JavaScript.
En esta sesión se comprobó que la ruta local de Conversaciones redirige al login sin errores JavaScript.
La vista autenticada aún necesita su propia comprobación.

Si el objetivo es adaptar un funnel, Studio mide la referencia y organiza estrategia, especialistas y copy en tres olas.
Los faltantes del producto quedan explícitos; las directivas finales permiten pasar a implementación cuando se solicite.

### Qué está incluido y qué depende del entorno

Los perfiles, instrucciones y protocolos son archivos del Harness.
Edge, Playwright, el REPL, Computer Use y las conexiones MCP requieren disponibilidad y configuración en cada entorno.
La prueba local con Edge demuestra esa capacidad en este equipo; clonar el repositorio no la instala.
Los hooks requieren revisar y confiar su definición exacta antes de depender de ellos.

## Mapa del Harness

| Capa | Ubicación | Función |
|---|---|---|
| Reglas comunes | `AGENTS.md` | Clasificación de riesgo, revisión por pares, límites y reglas que aplican al workspace. |
| Runtime de Codex | `.codex/` | Roles TOML, hooks, configuración, notas del navegador y plantilla de registros. |
| Flujos reutilizables | `.agents/skills/` | `$align-to-spec` aclara tareas ambiguas; `$diagnosing-bugs` guía diagnósticos; `$ux-review` revisa interfaces; `$llama-funnel-studio` conecta Studio. |
| Memoria del Harness | `CodexMemory/` | Índice, ADRs del Harness, flujo operativo, escenarios de guardia y registros de trabajos importantes. |
| Fuente del proyecto | Carpeta de cada proyecto | Sus propios `AGENTS.md`, README, manifiestos, contratos, instrucciones y decisiones de producto. |

Para que Codex descubra de forma consistente los agentes y skills compartidos, abre Codex con la raíz del repositorio como raíz activa. Varios proyectos hijos tienen su propio repositorio Git; si abres uno de esos repositorios como proyecto independiente, el descubrimiento local puede detenerse antes de llegar al `.agents/skills` de la raíz. En ese modo, habría que instalar el skill en el espacio de usuario de Codex o añadirlo a ese repositorio.

## Cómo encaja con el Codex actual

- **Riesgo proporcional:** cambios reversibles pequeños se hacen directamente; tareas no triviales reciben plan y revisión; seguridad, datos, producción y acciones externas tienen revisiones especializadas y un punto humano cuando corresponda.
- **Plan y Goal cumplen funciones distintas:** `/plan` ayuda a decidir el camino; `/goal` conserva el resultado esperado y su condición verificable entre turnos. Ninguno amplía permisos.
- **El agente principal orquesta:** los custom agents TOML definen perfiles que Codex puede lanzar como subagentes. El principal conserva el objetivo, decide qué tareas son independientes, recoge resultados y comprueba la evidencia.
- **Arquitectura con evidencia:** `architecture_reviewer` recibe un alcance y material del proyecto; devuelve hasta tres oportunidades justificadas sin editar código.
- **Trabajo asíncrono:** un comando largo e independiente puede correr en segundo plano mientras Codex sigue con otra tarea; el estado se consulta con `/ps` y se detiene con `/stop`. Un proceso de fondo conserva su salida/proceso; un subagente tiene además su propia tarea y contexto. Para trabajos de varias vueltas con cierre comprobable, usa `/goal`.
- **Automatización con frenos:** antes de conectar un disparador recurrente, define propietario, evento, deduplicación, límite de intentos, comprobación y punto de revisión humana. Una ejecución termina con estado y evidencia; la siguiente comienza por un evento nuevo.
- **Los subagentes heredan permisos:** reciben el sandbox y las aprobaciones del agente principal. Instrucciones de “solo lectura” dentro de un perfil no crean aislamiento real.
- **Skills bajo demanda:** Codex puede elegir una skill por su descripción o el usuario puede llamarla con `$nombre`. La skill de Studio enlaza a los protocolos originales; evita crear un segundo manual que se desactualice.
- **Auto-review no es un permiso:** revisa solicitudes elegibles que ya requieren aprobación. No agranda el sandbox, no elimina la red restringida ni convierte una aprobación en autorización para todo.
- **Hooks necesitan revisión:** el usuario debe inspeccionar y confiar la definición exacta en `/hooks`; un cambio de definición requiere revisarla de nuevo. Los hooks complementan los permisos del runtime.
- **Memoria con evidencia:** los Goals conservan el trabajo vivo; los run records guardan qué se cambió y qué se verificó. Las decisiones de cada producto se quedan en su propio proyecto.
- **Navegador y computadora:** reutiliza un REPL persistente y perfiles temporales. Consulta `.codex/browser/README.md` para el alcance portable.

Referencias oficiales actuales: [skills](https://learn.chatgpt.com/docs/build-skills), [subagentes](https://learn.chatgpt.com/docs/agent-configuration/subagents), [Goals](https://learn.chatgpt.com/docs/long-running-work), [background commands](https://learn.chatgpt.com/docs/developer-commands?surface=cli), [hooks](https://learn.chatgpt.com/docs/hooks) y [Auto-review](https://learn.chatgpt.com/docs/sandboxing/auto-review).

La [revisión de ramas de `mattpocock/skills`](docs/mattpocock-branches.md) registra qué ideas experimentales pueden adaptarse y sus límites.

## Llama Funnel Studio

### Qué contiene

Studio no es solo un grupo de prompts para generar páginas. Es un proceso de inteligencia de funnels con cuatro equipos, herramientas deterministas, contratos de salida y reglas para adaptar lo aprendido a otro producto. Su fuente está en [`systems/llama-funnel-studio/README.md`](systems/llama-funnel-studio/README.md).

| Equipo | Especialistas | Cuándo interviene |
|---|---|---|
| **Funnel** | `mercadologo`, `administrador`, `psicologo`, `sociologo`, `ingeniero-industrial`, `disenador`, `linguista`, `frontend`, `growth-data`, `neuromarketing`, `copywriter`; `programador` revisa | Análisis y reproducción de estrategia, oferta, mensaje, diseño y conversión. |
| **Adquisición** | `keywords`, `seo-tecnico`, `geo`, `meta-snippets`, `search-console` | Tras el plan, para el descubrimiento en buscadores y motores generativos. |
| **Ingeniería** | `arquitecto-angular`, `performance`, `ab-testing`, `accesibilidad` | Cuando el plan pasa a una implementación en framework que debe medirse y funcionar en producción. |
| **Operaciones** | `devops`, `devsecops`, `gobernanza` | Cuando hay repositorio, pipeline, despliegue o proceso operativo real. |

Son 24 funciones documentadas; no significa que las 24 deban entrar en cada tarea. Studio define sus fronteras: quién decide cada aspecto, quién asesora y cómo escalar un conflicto.

### Analizar un funnel de origen

1. **Capturar y medir:** `tools/capture.py` obtiene los materiales; los analizadores producen JSON de `design`, `attention`, `text`, `flow` y `trackers`.
2. **Separar medición e interpretación:** los parsers reportan lo medible; los especialistas interpretan el significado. Si un JSON contradice la captura visual, no se trata como verdad absoluta: se investiga y se usa la evidencia de la página.
3. **Extraer patrones transferibles:** cada especialista registra hallazgos, patrones (`PT-*`), contaminación específica del origen (`CT-*`), preguntas para el destino (`Q-*`) y veredicto.
4. **Sintetizar:** el orquestador agrupa los patrones, las preguntas y las tensiones. Puede generar un `SKILL.md` específico para ese caso, que empaqueta el patrón reutilizable.

### Adaptar el patrón a otro producto

Primero se recoge la oferta real, el público, la prueba disponible, los activos de marca, referencias visuales y colores vetados. Luego se audita la compatibilidad: consciencia, sofisticación del mercado, ticket, tipo de compra, ciclo de decisión, modelo de entrega y riesgo percibido. El resultado declara si la adaptación es directa, adyacente o distante.

La reproducción va en tres olas porque las decisiones se condicionan:

1. **Base de negocio:** `mercadologo` y `administrador` fijan público, posicionamiento, consciencia y oferta.
2. **Capas especialistas:** diseño, psicología, cultura, proceso, lenguaje, frontend, datos y atención trabajan sobre esa base.
3. **Copywriting:** `copywriter` redacta después de que estrategia, oferta y demás capas estén decididas.

El plan final reúne decisiones, directivas ejecutables (`D-*`), elementos descartados, faltantes explícitos (`[FALTA: ...]`) y conflictos pendientes. Construir una web es opcional; una web real activa los equipos de ingeniería y operaciones según el pedido.

### Por qué es tan sólido: ejemplos concretos

- **Mide color en vez de describirlo al tanteo.** `design.py` mide paleta, frecuencia/superficie, tipo y escala tipográfica, espaciado, radios y sombras. El diseñador decide qué significa esa paleta para el género visual.
- **Detecta cuando una cifra convincente está equivocada.** El proyecto registra un caso donde el parser atribuyó 86% de una página oscura al blanco porque ignoró los gradientes en `background-image`. La regla resultante es potente: si el JSON y la captura chocan, gana la captura y se corrige el analizador; no se propaga el número falso.
- **Aprende sin clonar al competidor.** `PT-*` conserva el mecanismo que puede transferirse; `CT-*` identifica lo que solo funciona por la marca o el nicho de origen. La copia literal no pasa a la síntesis.
- **Evita decisiones visuales tardías.** Pide logo, pruebas reales, fotos disponibles, referencias y vetos de color antes de construir. Si falta un testimonio, deja `[FALTA]`; no inventa uno ni lo reemplaza con una foto de stock.
- **Reduce el retrabajo ordenando dependencias.** No deja que copywriting fije el mensaje antes del posicionamiento ni que los demás construyan sobre un precio pendiente. Si dos marcas necesitan sitios distintos, pregunta la arquitectura antes de repartir trabajo.
- **Es selectivo.** Para una revisión de interfaz puede bastar `$ux-review`; una extracción total, una implementación Angular o un pipeline DevOps solo se activa cuando el usuario realmente lo pide.

### Los especialistas como agentes de Codex

Los Markdown de `especialistas/` son **instrucciones de rol**, no procesos autónomos. El perfil Codex `llama_funnel_specialist` puede ejecutar uno de esos roles cuando el agente principal le entrega exactamente el rol, modo, entradas y archivo de salida. Por ejemplo, Codex puede lanzar varias instancias del perfil para revisar diseño, copy y frontend en paralelo si sus tareas son independientes.

El agente de diseño no crea por sí mismo un agente frontend. **Codex —el runtime dirigido por el agente principal— crea y administra los subagentes**; el perfil solo define cómo trabaja cada instancia. El principal sintetiza y decide qué sigue. El límite configurado aquí es tres subagentes concurrentes, así que una extracción completa de 11 disciplinas se agenda en lotes; las tres olas de reproducción se mantienen separadas. Si el runtime no ofrece subagentes, se sigue el mismo contrato en secuencia.

### Límites que importan

- El opt-in de captura permanece apagado salvo autorización explícita para enviar el formulario a un tercero.
- No inventar hechos del producto, testimonios, pruebas, métricas de conversión ni contenido ausente.
- No desplegar, enviar formularios, escribir en producción, usar credenciales o contactar terceros solo porque un especialista lo recomiende.
- Los resultados de revisión son consultivos; el agente principal comprueba paths, evidencia y verificaciones antes de cerrar.
- Las habilidades compartidas son más fáciles de descubrir si la sesión de Codex se abre desde la raíz la raíz del repositorio; el run record documenta el límite cuando se abre un repo hijo por separado.

## Cómo usarlo

- **Analizar:** `$llama-funnel-studio` + URL o captura + profundidad deseada.
- **Adaptar:** `$llama-funnel-studio` + producto destino + oferta y evidencia real disponible.
- **Revisar una sola interfaz:** `$ux-review`, sin lanzar todo Studio.
- **Construir o desplegar:** primero lee las instrucciones y manifiestos del proyecto dueño; activa solo los roles de ingeniería u operaciones que correspondan.

## Documentación oficial de Codex

- [Skills y descubrimiento](https://learn.chatgpt.com/docs/build-skills)
- [Custom agents y subagentes](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Goals para trabajos largos](https://learn.chatgpt.com/docs/long-running-work)
- [Comandos y tareas de fondo](https://learn.chatgpt.com/docs/developer-commands?surface=cli)
- [Hooks y revisión de confianza](https://learn.chatgpt.com/docs/hooks)
- [Auto-review, permisos y límites](https://learn.chatgpt.com/docs/sandboxing/auto-review)
