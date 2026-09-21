# agentic-harness

> **English summary.** A production-grade multi-agent harness built on top of Claude Code: one orchestrator command (`/orquestar`) coordinates 11 specialised subagents (architect, planner, coder, coder-web, qa, adversary, plus five standalone ones) through fixed, verbatim hand-off contracts. It ships with production controls (bounded retry loops, a mandatory human checkpoint before schema changes, hooks that block dangerous git/PR operations and secrets in the stage, read-only database access through MCP), an Obsidian vault used as long-term memory (ADRs, one run doc per execution, golden tasks for replay), and two self-improvement agents (`retro` proposes prompt edits from run history, `system-auditor` audits the system's own source) that never edit anything without human approval. This is an anonymised copy of a system that processed 175 tasks in production over two months across six repositories; the client, its people and its infrastructure have been replaced by placeholders. MIT licensed.

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
Meta/                      documentación del sistema multiagente y de la configuración del vault
CLAUDE.md · AGENTS.md      reglas para cualquier sesión (AGENTS.md para herramientas que no leen CLAUDE.md)
Home.md                    tablero del vault (Dataview)
```

## Cómo adaptarlo a otro repo

1. **Clona esta carpeta como raíz de trabajo** y clona tus repos de código adentro (o al lado, ajustando `.gitignore`). Los agentes asumen que el repo destino es una carpeta hermana de `.claude/`.
2. **Renombra los repos.** Los placeholders son `api-core`, `api-contracts`, `api-people`, `api-auth`, `api-delivery`, `web-app`; un `grep -rl api-core .claude` te da los puntos de contacto. Los roles (BFF, IdP, frontend) sí importan: `coder` está escrito para .NET/EF Core y `coder-web` para React/TypeScript.
3. **Escribe tu "Visión de dominio" en `CLAUDE.md`.** Los seis agentes del pipeline la leen antes de diseñar; en esta versión está vacía a propósito.
4. **Conecta tus MCP de base de datos** con los nombres de `settings.json` (`core-db`, `contracts-db`, ...) o renómbralos ahí y en el `tools:` de `planner`/`analyst`. Deja la escritura en `ask` o `deny`.
5. **Instala los hooks de usuario.** `git-guard.sh`, `check-file-size.py`, `check-bash-read.py` y `revisar_secretos.py` se copian a `~/.claude/hooks/` y se registran en `~/.claude/settings.json`; `sh scripts/instalar-hooks.sh` configura el `pre-commit` de git.
6. **Vacía la memoria y empieza a llenarla.** Crea `docs/runs/INDEX.md`, `RETRO-LOG.md`, `GOLDEN-TASKS.md` y `docs/adr/` con tu primer ADR. El Step 5 de `/orquestar` escribe el run doc; corre `retro` cada 3-5 corridas y `system-auditor` cada ~10.
7. **Opcional:** Codex CLI y Antigravity CLI (`agy`) para los motores externos; sin ellos el pipeline corre solo con Claude y lo dice en el reporte final.

Detalles que conviene leer primero: `Meta/sistema-multiagente-supervisado.md` (por qué existe cada capa y qué pasó sin ella) y `.claude/commands/orquestar.md` (el protocolo completo, paso por paso).

## Sobre esta versión

Es una copia anonimizada de un sistema en uso. Se retiraron: el contexto de negocio del cliente (esquemas, reglas, marca, propuestas de proveedores), los ADRs, los run docs, el tablero de tareas y su skill, las guías de entrega y el playbook (cada regla citaba código del cliente), las colecciones de pruebas, credenciales de cualquier tipo y todo archivo que hablara del producto en vez del sistema de agentes. En una segunda pasada se reescribió en genérico todo lo que describía el rubro del cliente (esquemas de base, nombres de columnas, conceptos del negocio) y se quitaron los números de corrida y de PR; las fechas se conservan porque cuentan cómo evolucionó el sistema.

## Licencia

MIT. Ver [LICENSE](LICENSE). © 2026 Diego Ampuero.
