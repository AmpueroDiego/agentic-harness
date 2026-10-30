---
name: requisitos
description: "Redacta, confirma, versiona y marca obsoleto un REQ en la Biblioteca de requisitos (`requisitos/`) — la capa de specs de SDD. La IA redacta desde el chat, el responsable confirma antes de que el REQ alimente el pipeline."
tipo: skill
tags: [harness]
---
<!-- generado por .claude/scripts/generar-skills-codex.py; no editar a mano -->

# /requisitos

Leé completo `.claude/commands/requisitos.md` (ruta relativa a la raíz del proyecto) y seguilo al pie de la letra. Ese archivo es la única fuente; este es solo un puntero.
Para cambiar este skill, editá `.claude/commands/requisitos.md` y regenerá con `python .claude/scripts/generar-skills-codex.py`; no edites este archivo.

- `$ARGUMENTS` en ese archivo es lo que te pidió el usuario al invocar este skill.
- Donde diga lanzar un agente o subagente (`Agent`, `planner`, `qa`, `adversary`, `coder-web`…), usá `bash .claude/scripts/agente.sh <agente> <prompt.md> <salida.md>`.
- Donde diga invocar otro comando (`/trello`, `/supercodex`…), leé y seguí su `.claude/commands/<nombre>.md`.
- Equivalencias de herramientas de Claude y qué motor usar: `AGENTS.md` §3.
- Con varias sesiones abiertas, solo la coordinadora escribe los archivos compartidos de la raíz (`TASKS.md`, `CLAUDE.md`, `docs/runs/INDEX.md`…), sea del motor que sea (`CLAUDE.md`, «Flujo de trabajo»).
