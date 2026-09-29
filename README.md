# agentic-harness

> **English summary.** A production-grade multi-agent harness built on top of Claude Code: one orchestrator command (`/orquestar`) coordinates 11 specialised subagents (architect, planner, coder, coder-web, qa, adversary, plus five standalone ones) through fixed, verbatim hand-off contracts. It ships with production controls (bounded retry loops, a mandatory human checkpoint before schema changes, hooks that block dangerous git/PR operations and secrets in the stage, read-only database access through MCP), an Obsidian vault used as long-term memory (ADRs, one run doc per execution, golden tasks for replay), and two self-improvement agents (`retro` proposes prompt edits from run history, `system-auditor` audits the system's own source) that never edit anything without human approval. A portable installer (`install.sh` / `install.ps1`) configures it for any project from a single `harness.ini` (git is the only mandatory integration; tracker, GitHub, Codex/Antigravity/DeepSeek, database MCP servers and the Obsidian vault are all optional and degrade gracefully), and `profiles/` ships example stack conventions (.NET, Node/TS, Python) the coder agents draw on. This is an anonymised copy of a system that processed 175 tasks in production over two months across six repositories; the client, its people and its infrastructure have been replaced by placeholders. MIT licensed.

Harness multiagente sobre Claude Code, usado en producción para desarrollar y mantener un ecosistema de seis repositorios (.NET 10 + React/TypeScript). Esta es una **versión anonimizada**: el cliente, las personas del equipo, los hosts, los identificadores de tableros y toda la lógica de negocio fueron reemplazados por placeholders (`AcmeOrg`, `api-core`, `<sql-host>`, `Revisor Principal`, etc.) o retirados. Lo que queda es el sistema: cómo se reparte el trabajo, cómo se verifica y cómo aprende.

**Dato real:** 175 tareas procesadas en 2 meses (corridas del orquestador, fixes directos y sesiones de diseño), con registro por corrida, retro periódica y auditorías del propio sistema.

## Qué es

- **Un orquestador y 11 subagentes.** El orquestador (`/orquestar`) nunca deja que dos agentes se hablen entre sí: cada salida es una plantilla markdown fija (`## Architect Report`, `## Plan`, `## Coder Report`, `## QA Verdict`, `## Adversarial Audit Report`) que se pasa **verbatim** al siguiente. Un hand-off malformado es un hallazgo, no algo que el orquestador arregla en silencio.
- **Flujo rápido vs. pipeline completo.** Tres niveles: *Nivel 0* (el orquestador edita directo con build verde: un literal, una etiqueta), *Nivel 1* (sin `architect`; el patrón ya está en el archivo que se toca) y *pipeline completo* (obligatorio para endpoints nuevos, esquema, auth, concurrencia). Cuando hay duda, se escala.
- **Controles de producción.**
  - Topes de reintento: 2 ciclos QA→coder→QA, 1 ronda `adversary`→coder→`adversary`, cada uno con su presupuesto; al agotarse se escala al humano en vez de seguir iterando.
  - Parada obligatoria (Step 2.5) cuando el plan marca escritura a bases ajenas, cambio de esquema, desvío de un ADR o una decisión de negocio bloqueante.
  - Hooks que **bloquean**: `git-guard.sh` (PR sin `--base develop` o contra `main`; secretos en el stage antes de cada `git commit`), `pr-base-guard.py` (mismo control para el MCP de GitHub), `check-file-size.py` / `check-bash-read.py` (lecturas completas de archivos grandes se desvían a un motor barato), `check-maxlength.py` (aviso sobre ids externos truncables). Los secretos los revisa `revisar_secretos.py`, compartido con un `pre-commit` de git real y cubierto por 23 tests.
  - Acceso a base de datos **solo lectura vía MCP**: `settings.json` permite `list_tables`/`describe_table`/`read_query`, pide confirmación para `execute_query`/`write_query` y deniega `drop`/`alter`/`create`. Los agentes declaran en su `tools:` exactamente qué conectores usan.
  - Verificación de primera mano: una cita `archivo:línea` solo vale si sale de un `grep`/`Read` de esa sesión; el orquestador contrasta cada `## Coder Report` contra `git status` antes de creerlo.
- **Memoria en un vault de Obsidian.** La carpeta es a la vez repo y vault: ADRs (`docs/adr/`), un run doc por corrida con tokens y ciclos (`docs/runs/NNNN-*.md`, indexados por tema en `INDEX.md`), tareas doradas (`GOLDEN-TASKS.md`) para hacer replay de un cambio de prompt antes de confiar en él, y un `pre-commit` que impide dejar notas huérfanas o wikilinks rotos. En esta versión pública esas carpetas viajan vacías; el mecanismo está documentado en `Home.md` y `Meta/`.
- **Agentes que mejoran el sistema, con aprobación humana.** `retro` lee los run docs, busca la misma corrección repetida en 2+ corridas y propone el texto exacto a cambiar en el `.md` del agente (nunca lo aplica: no tiene `Write`). `system-auditor` lee el fuente del sistema —instrucciones que el `tools:` de un agente no puede ejecutar, plantillas que divergieron, conteos desfasados, loops sin tope— y propone correcciones. Ninguno toca el control de flujo (topes, checkpoints) sin marcarlo como decisión mayor.
- **Tres motores.** Claude orquesta y hace la lógica con estado; Codex CLI revisa antes del push y ejecuta trabajo mecánico de un archivo; Antigravity CLI (Gemini) revisa lo visual y hace cambios de estilo. Cada hallazgo externo se verifica contra el código antes de convertirse en trabajo.

## El pipeline

```
tarjeta / tarea ─► Step 0: historial de corridas, ADRs, cadencia de retro/auditoría
                 ─► Step 0.7: Nivel 0 | Nivel 1 | pipeline completo
                 ─► architect ─► planner ─┬─► coder ─────┐   varios en paralelo,
                       (Step 2.5: parada   └─► coder-web ─┤   dueño exclusivo por archivo
                        humana si hay riesgo)             ▼
                                            checkpoint commit (Step 3.6)
                                                          ▼
              QA ∥ adversary ∥ security-review ∥ codex ∥ tests de integración   (gate de pre-PR)
                                                          ▼
              un solo paquete de hallazgos ─► coder (2 ciclos QA, 1 ronda adversary) ─► commit
                                                          ▼
              Step 4.7: push y PR solo con "sí" explícito ─► Step 5: run doc + INDEX (obligatorio)
```

Agentes independientes, fuera del pipeline: `analyst` (preguntas de datos, solo lectura), `ux-researcher` (referencias y maquetas HTML), `ux-ui` (auditoría de la app viva en Chrome: contraste, teclado, axe-core), `retro` y `system-auditor`.

## Mapa de carpetas

```
.claude/
├── agents/        11 subagentes (frontmatter: name, description, tools, model)
├── commands/      10 comandos: orquestar, worktree, codex, antigravity, ux,
│                  verificar-ramas, diagramar, auditar-vault, shunt, requisitos
├── hooks/         guardas PreToolUse/PostToolUse + revisar_secretos.py y sus tests
├── scripts/       shunt: bulk-read, code-write, gh-read-shunt
├── tools/         scripts deterministas sin dependencias: drawio/, vault/
├── settings.json  permisos (allow / ask / deny) y hooks del proyecto
└── launch.json    ejemplo de configuraciones de arranque del frontend
.agents/skills/security/   catálogo CWE/OWASP que carga la revisión de seguridad
scripts/                   pre-commit (secretos + vault), instalador de hooks, validar-vault.py
profiles/                  perfiles de stack (dotnet, node-ts, python) que alimentan coder/coder-ui
Meta/                      documentación del sistema multiagente y de la configuración del vault
CLAUDE.md · AGENTS.md      reglas para cualquier sesión (AGENTS.md para herramientas que no leen CLAUDE.md)
Home.md                    tablero del vault (Dataview)
install.sh · install.ps1   instalador/configurador (ver "Quick start" abajo)
harness.ini.example        plantilla de configuración; harness.ini real nunca se versiona
```

## Quick start — instalarlo en tu proyecto

```sh
git clone https://github.com/AmpueroDiego/agentic-harness.git
cd agentic-harness
./install.sh --target /ruta/a/tu-proyecto      # asistente interactivo
```

En Windows sin bash: `.\install.ps1 -Target C:\ruta\a\tu-proyecto`. Ambos son
equivalentes y aceptan `-DryRun`/`--dry-run` para ver qué harían sin escribir
nada, y `-NonInteractive`/`--non-interactive` para correr sin preguntas
(usa `harness.ini.example` tal cual, o el que le pases con `--ini`).

El instalador:
1. Detecta qué tenés instalado (`git`, `gh`, `node`, `dotnet`, `python`, `claude`, `codex`, `agy`) — nada de esto es obligatorio salvo `git`.
2. Genera (o reutiliza) `harness.ini` en tu proyecto — nunca se versiona, ver `harness.ini.example` para el formato y qué es obligatorio vs. opcional.
3. Copia `agents/`, `commands/`, `hooks/`, `scripts/`, `tools/` y `profiles/` a `.claude/` de tu proyecto, y `CLAUDE.md`/`AGENTS.md` a su raíz, con `AcmeOrg` ya sustituido por el nombre de tu proyecto (y la rama base, si no es `develop`). Un archivo existente y distinto se respalda a `.bak` en vez de perderse.
4. Instala un hook de `pre-commit` que revisa secretos antes de cada commit (`core.hooksPath` apunta a `.claude/hooks-git/`), salvo `--skip-hook` o si el destino ya tenía otro hook configurado.
5. Termina con un **doctor**: qué quedó activo y qué se omitió (tracker, motores, MCP de base de datos, vault).

Es idempotente (correr dos veces no cambia nada de más) y no destructivo
(nunca sobrescribe sin backup, salvo `--force`). Después de instalar, quedan
tres cosas manuales que el instalador no adivina por vos:
- **Los nombres reales de tus repos.** Los placeholders son `api-core`, `api-contracts`, `api-people`, `api-auth`, `api-delivery`, `web-app`; un `grep -rl api-core .claude` te da los puntos de contacto. Los roles (BFF, IdP, frontend) sí importan: `coder` trae de ejemplo convenciones .NET/EF Core y `coder-web` React/TypeScript — ver "Perfiles de stack" abajo para no reescribirlas a mano.
- **La sección "Visión de dominio" de `CLAUDE.md`.** Los seis agentes del pipeline la leen antes de diseñar; llega vacía a propósito — es lo único que de verdad no se puede genérica.
- **Vaciar y empezar a llenar la memoria**, si vas a usar el vault de Obsidian: `docs/runs/INDEX.md`, `RETRO-LOG.md`, `GOLDEN-TASKS.md`, `docs/adr/`. El Step 5 de `/orquestar` escribe el run doc; corré `retro` cada 3-5 corridas y `system-auditor` cada ~10.

Detalles que conviene leer primero: `Meta/sistema-multiagente-supervisado.md` (por qué existe cada capa y qué pasó sin ella) y `.claude/commands/orquestar.md` (el protocolo completo, paso por paso).

## Integraciones opcionales

Todo lo que no sea git es opcional y el sistema se degrada sin romperse si
falta — `harness.ini.example` documenta cada sección:

| Integración | Sección del ini | Si falta |
|---|---|---|
| Tracker de tareas (Trello / Azure DevOps / GitHub Issues) | `[tracker]` | `orquestar` pregunta la tarjeta a mano en vez de buscarla |
| GitHub | `[github]` | los PR se abren sin reviewer por defecto |
| Codex CLI | `[engines] codex_enabled` | se salta la segunda revisión antes del push |
| Antigravity CLI (Gemini) | `[engines] antigravity_enabled` | sin revisor visual ni shunt de lecturas grandes |
| MCP de base de datos | `[databases]` | `planner`/`analyst` trabajan solo con lo que puedan leer del código |
| Vault de Obsidian | `[vault]` | sin memoria de largo plazo entre corridas; `docs/adr`/`docs/runs` siguen sirviendo como markdown simple |

Los secretos de cada integración (tokens, PATs, API keys) nunca van en
`harness.ini`: el ini solo declara el *nombre* de la variable de entorno
(sufijo `_env`) que los contiene.

## Perfiles de stack

`profiles/` trae tres ejemplos (`dotnet.md`, `node-ts.md`, `python.md`) con
las convenciones y "hard rules" que un `coder`/`coder-ui` necesita para ese
stack. `harness.ini` declara `stack_profile = <nombre>` por repo; si tu
stack no está entre los tres, copiá `profiles/_plantilla.md` y escribí el
tuyo — ver `profiles/README.md`.

## Sobre esta versión

Es una copia anonimizada de un sistema en uso. Se retiraron: el contexto de negocio del cliente (esquemas, reglas, marca, propuestas de proveedores), los ADRs, los run docs, el tablero de tareas y su skill, las guías de entrega y el playbook (cada regla citaba código del cliente), las colecciones de pruebas, credenciales de cualquier tipo y todo archivo que hablara del producto en vez del sistema de agentes. En una segunda pasada se reescribió en genérico todo lo que describía el rubro del cliente (esquemas de base, nombres de columnas, conceptos del negocio) y se quitaron los números de corrida y de PR; las fechas se conservan porque cuentan cómo evolucionó el sistema.

## Licencia

MIT. Ver [LICENSE](LICENSE). © 2026 Diego Ampuero.
