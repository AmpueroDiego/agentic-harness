# Reglas de proyecto AcmeOrg para agentes

> **La fuente de verdad es [`CLAUDE.md`](CLAUDE.md), en esta misma carpeta. Léelo.**
> Este archivo existe porque algunas herramientas (Codex y similares) leen `AGENTS.md` y no `CLAUDE.md`. Hasta 2026-09-07 era una copia de 112 líneas de `CLAUDE.md`, y las dos versiones ya habían divergido. Ahora acá quedan solo dos cosas: los innegociables, por si no seguiste el link, y lo que es propio de este archivo (§2, gobernanza del vault).

## 1. Innegociables

Versión corta. El detalle, el porqué y todo lo demás están en `CLAUDE.md`.

- **Cero eliminaciones.** No borres nada — tarjetas del tablero, comentarios, adjuntos, ramas remotas, código, tablas, documentación — sin instrucción explícita e inequívoca. Antes de cualquier mutación en el tablero de tareas o acción destructiva en Git/BD, propone y espera aprobación expresa.
- **Todo apunta a `develop`, nunca a `main`.** Ramas desde `develop`, PRs contra `develop`. GitHub propone `main` por defecto: cámbialo a mano.
- **Nada de secretos versionados.** En todo `appsettings*.json` comiteado las claves sensibles van en `""` o `"REPLACE_ME"`. `appsettings.Development.json` nunca se comitea. Y como `""` y `"REPLACE_ME"` son strings no nulos, `??` jamás alcanza el fallback: trata vacío / solo-espacios / `REPLACE_ME` como ausente antes de evaluar.
- **URLs de servicios hermanos nunca estáticas** — se resuelven en runtime vía `IApiAuthService`.
- **Ninguna API auto-migra.** Una migración de EF Core no se aplica sola al desplegar, y el fallo es silencioso.
- **Azure SQL no soporta joins de 3 partes entre bases**, aunque compartan servidor. Dos queries separadas, correlacionadas por `Id`.
- **`api-core` tiene un solo `DbContext` (`CoreDbContext`).** Nunca `ApplyConfigurationsFromAssembly` ahí: en el mismo ensamblado quedan configuraciones de entidades ajenas sin usar y las metería en el modelo. Registra cada entidad explícita.
- **Identificadores de proveedores externos: `nvarchar(450)`**, nunca 100.
- **La tarjeta pasa a revisión solo cuando el responsable del repo lo pide**, nunca al abrir el PR.
- **Windows: PowerShell 5.1 corrompe tildes y emojis.** Cuerpos de PR a un `.md` en UTF-8 sin BOM y `--body-file`; nunca por pipe o argumento directo.

## 2. Estándar de Obsidian Vault y gobernanza de Markdown

Esto es propio de este archivo — `CLAUDE.md` no lo repite.

- **Nomenclatura estricta (`kebab-case`, sin excepciones):** minúsculas, números y guiones. Prohibidos espacios, tildes, caracteres especiales (`ñ`, `?`, `!`, `(`, `)`) y dobles guiones bajos.
- **UTF-8 puro sin BOM** en todo Markdown creado o modificado. En PowerShell o Python, codificación explícita (`-Encoding utf8`, `encoding='utf-8'`) para evitar mojibake y `�`.
- **Wikilinks nativos** `[[ruta/nota|Alias]]`. Prohibido escapar la barra vertical con backslash: el pipe va puro, o Obsidian no resuelve el enlace.
- **Frontmatter YAML obligatorio** en toda nota nueva (corrida, ADR, guía, contexto, tarjeta) con `tipo:`, `fecha:` si aplica y `tags: [...]`, para que Dataview y Graph View la indexen.
- **Cero notas huérfanas:** toda nota nueva se enlaza en su índice padre (`Home.md`, `docs/adr/README.md`, `contexto-negocio/README.md` o `docs/runs/INDEX.md`).
- **Validación:** `python scripts/validar-vault.py` antes de cerrar cualquier tarea de documentación. Falla (código 1) solo por nombres corruptos, mojibake, wikilinks con pipe escapado o huérfanas que deja el commit; los enlaces rotos y las huérfanas previas salen como aviso con código 0. **No revisa frontmatter ni `kebab-case`** (aunque su docstring lo diga): esas dos reglas se cumplen a mano.

## 3. Si te abrieron con Codex o Antigravity (no con Claude)

El sistema vive en `.claude/` y se orquesta igual con cualquier motor. Solo cambia cómo se llama a cada pieza.

| En Claude | Desde Codex o Antigravity |
|---|---|
| `/orquestar`, `/worktree`, `/codex`… | Skill del mismo nombre en `.agents/skills/`: cada uno apunta a su `.claude/commands/<nombre>.md`, la única fuente |
| Herramienta `Agent` con `planner`, `qa`, `adversary`… | `bash .claude/scripts/agente.sh <agente> <prompt.md> <salida.md> [raíz]` |
| Memoria del usuario | `~/.claude/projects/<carpeta-del-proyecto>/memory/MEMORY.md` y lo que aplique |
| Bases por MCP | Solo conectadas en Claude: `MOTOR=claude bash .claude/scripts/agente.sh analyst …` |
| Hook `git-guard.sh` | No corre fuera de Claude: cumplir sus reglas a mano (PR siempre contra la rama base, nunca push a la rama principal ni `--force`) |

**Motor por llamada:** `agente.sh` usa `MOTOR=claude|codex|agy`; sin `MOTOR` va con Codex, salvo agentes con herramientas MCP (van con Claude). Los agentes de solo lectura con Antigravity corren sobre una copia `git archive` temporal y necesitan una regla `autoMode.allow` del usuario.

**Al agregar o renombrar un comando** en `.claude/commands/` o un skill en `.claude/skills/`, correr `python .claude/scripts/generar-skills-codex.py`; nunca editar `.agents/skills/*` a mano. El `pre-commit` corre con cualquier motor: `verificar-sistema.py` bloquea si los skills de Codex quedaron viejos o un agente no tiene `name` (igual al archivo), `description` y `tools`.

