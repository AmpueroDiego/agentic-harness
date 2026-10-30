---
tipo: dashboard
tags: [dashboard, meta]
---

# AcmeOrg — Panel de conocimiento

> Vault a nivel de `AcmeOrg/`, cubre los repos de código hermanos (`api-core`, `api-contracts`, `api-people`, `api-auth`, `api-delivery`, `web-app`) y el pipeline multiagente en un solo lugar. Requiere el plugin **Dataview** (Settings → Community plugins → Dataview) — las tablas se generan solas leyendo el frontmatter de cada nota, no hace falta mantenerlas a mano.
>
> 🌟 **Arquitectura Central:** [[Meta/sistema-multiagente-supervisado|🤖 Sistema Multiagente Supervisado]]
> 📋 **Control de Tareas y Memoria:** `TASKS.md` (backlog) · `docs/runs/INDEX.md` (historial de corridas) · `docs/runs/RETRO-LOG.md` (bitácora de mejora continua)
> 🛡️ **Gobernanza:** catálogo de ADRs en `docs/adr/` · contexto de dominio en `contexto-negocio/` · [[Meta/Graph-View-Config|🎨 Graph View Config]]

## Agentes (`.claude/agents`)

> Los agentes viven en la raíz (repo `agentic-harness`), compartidos por los repos hermanos. **Nota técnica:** Obsidian no indexa carpetas que empiezan con punto, así que Dataview no puede leer `.claude/agents` directo (daba "No results"). Se creó un junction de Windows `agentes-pipeline/` → `.claude/agents/` (mismos archivos, no una copia) solo para que Dataview pueda indexarlos — la consulta de abajo apunta ahí. El junction es local (no se versiona, ver `.gitignore`); si el vault se clona en otra máquina hay que recrearlo (ver `Meta/Graph-View-Config.md`).

```dataview
TABLE
    description AS "Rol",
    tools AS "Herramientas"
FROM "agentes-pipeline"
SORT file.name ASC
```

## Corridas del orquestador

```dataview
TABLE
    fecha AS "Fecha",
    resultado AS "Resultado",
    duracion AS "Duración",
    tokens AS "Tokens",
    ciclos_qa AS "Ciclos QA",
    rama AS "Rama"
FROM "docs/runs"
WHERE tipo = "run"
SORT fecha ASC
```

**Total de tokens acumulado** (solo corridas con `tokens_num` registrado):

```dataview
TABLE WITHOUT ID
    round(sum(rows.tokens_num)) AS "Total tokens",
    length(rows) AS "Corridas contadas"
FROM "docs/runs"
WHERE tipo = "run" AND tokens_num
GROUP BY true
```

## ADRs

```dataview
TABLE
    fecha AS "Fecha",
    estado AS "Estado"
FROM "docs/adr"
WHERE tipo = "adr"
SORT fecha ASC
```

## Carpetas que no viajan en la versión pública

> Las consultas Dataview de arriba apuntan a `docs/runs/` y `docs/adr/`, que en esta versión pública están vacías (contenían corridas y decisiones del cliente). Se dejan como documentación del mecanismo: cada corrida y cada ADR es una nota con frontmatter que el tablero indexa solo.

## Guías y mantenimiento

- [[tasks|Registro de tareas]]
- [[docs/guias/PENDIENTES-CONSOLA-AGENTE-2026-09-11|Ejemplo de traspaso de pendientes]]
- [[docs/guias/PREPARACION-DEFENSA-CODE-REVIEW|Preparación de una revisión de código]]
- [[docs/guias/PRINCIPIOS-INGENIERIA-MINIMALISTA|Principios de ingeniería minimalista]]
- [[.claude/commands/cola|Cola de PRs]]

## Mantenimiento y guías

- [[tasks|Registro de tareas]]
- [[docs/guias/GUIA-CONSOLA-AGENTE-PENDIENTES-Y-CASOS|Guía genérica de consola y ciclo de trabajo]]
- [[docs/guias/DETECCION-CODE-SMELLS|Detección de code smells]]
- [[.claude/commands/practicas|Auditoría de prácticas]]
- [[.claude/commands/negocio|Contrapeso de dominio]]

## Todo lo demás en este vault, por tag

```dataview
TABLE tags
FROM ""
WHERE tipo != "dashboard"
SORT fecha DESC
```

## Mantenimiento del harness

- [[TASKS|Registro de tareas]]
- [[.claude/skills/antislop-copywriting/SKILL|antislop-copywriting]]
- [[.claude/commands/diagramar|diagramar]]
- [[docs/guias/OBSERVACIONES-2026-09-03-INCIDENTES-Y-AUDITORIA|OBSERVACIONES-2026-09-03-INCIDENTES-Y-AUDITORIA]]
- [[.claude/agents/planner|planner]]
- [[docs/guias/CHECKLIST-DESPLIEGUE-OUTBOX-API-CORE|CHECKLIST-DESPLIEGUE-OUTBOX-API-CORE]]
- [[.claude/agents/ux-ui|ux-ui]]
- [[.claude/commands/proyecto|proyecto]]
- [[.claude/commands/levantar-proyecto|levantar-proyecto]]
- [[docs/guias/CI-CD-GITHUB-API-CORE-Y-WEB-APP|CI-CD-GITHUB-API-CORE-Y-WEB-APP]]
- [[.claude/commands/listo-para-merge|listo-para-merge]]
- [[.claude/commands/priorizar|priorizar]]
- [[.claude/agents/analyst|analyst]]

## Guías y herramientas sincronizadas

- [[docs/guias/PLAYBOOK-ANTI-REGRESIONES-Y-LECCIONES-APRENDIDAS|Playbook anti-regresiones]]
- [[docs/guias/AUDITORIA-VAULT-VS-CODIGO-2026-09-11|Auditoría del vault frente al código]]
- [[docs/guias/ESTANDAR-ENTREGA-TRELLO-Y-GITHUB|Estándar de entrega]]
- [[docs/guias/PROMPT-TABLERO-AVANCE-REUTILIZABLE|Prompt reutilizable del tablero de avance]]
- [[docs/guias/RETRO-VISTA-CLIENTE-CONSOLA|Retrospectiva de una consola de trabajo]]
- [[.claude/commands/supercodex|Revisión continua con Codex]]
- [[.claude/commands/trello|Conector del tablero]]
- [[.claude/skills/antislop-code/SKILL|Revisión de mantenibilidad]]
- [[.claude/tools/supercodex/bitacora-mejoras-codex|Bitácora de mejoras de revisión]]
