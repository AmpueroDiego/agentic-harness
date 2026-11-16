---
name: gobernanza-reproducir
description: Pull requests y Azure Boards - branch policies, plantilla de PR, work items, sprints y la trazabilidad work item↔PR↔deploy. El proceso que hace que el trabajo se vea y se revise.
---

# Gobernanza — REPRODUCIR

Hago que el trabajo tenga **rastro y revisión**: cada cambio nace de un work item, viaja en un PR revisable y se sabe cuándo llegó a producción. Sin burocracia que nadie mantendrá: el proceso mínimo que un equipo pequeño cumple de verdad.

## Entrada

La organización/proyecto de Azure DevOps · el roster de quién trabaja en el repo · `azure-pipelines.yml` de `devops`.

## Protocolo

1. **Boards con dos niveles, no cinco**: Épicas (una por área: web, adquisición, operación) y Work Items ejecutables con criterio de aceptación. Los `[FALTA]` de los planes del caso se cargan como work items — es el backlog real que ya existe.
2. **Ramas**: `main` protegida; ramas cortas `feature/<work-item-id>-<slug>` que mueren al mergear. Nada de ramas eternas.
3. **Branch policies en `main`**: build de validación (el pipeline de `devops`) obligatorio, mínimo 1 revisor, work item vinculado obligatorio, y comentarios resueltos antes de completar.
4. **Plantilla de PR** en el repo: qué cambia, por qué, cómo se probó, captura si toca UI, y checklist corto (tokens sin hardcodear, presupuestos, sin secretos). Un PR que no se puede describir en tres líneas es dos PRs.
5. **Commits convencionales** (`feat:`, `fix:`, `chore:`…) para que el historial se lea y el changelog se genere.
6. **Sprint semanal ligero**: se planifica por prioridad del backlog, se cierra mirando lo desplegado, no lo "casi listo".

## Salida

`reproduccion/<producto>/gobernanza.md` (cinco secciones, `D-gobernanza-<n>`) + `.azuredevops/pull_request_template.md` en el repo + la estructura de Boards (épicas y primeros work items) documentada para crearla en la organización.

## Autoverificación

- ¿El proceso cabe en la cabeza de un equipo de 1-3 personas? Si exige un rol dedicado, sobra proceso.
- ¿Cada política propuesta es configurable en Azure DevOps tal cual la escribí?

## Conflictos típicos

- **Con la urgencia**: "esto es un hotfix, sin PR". El hotfix va por PR expedito con revisor después; la política no se apaga, se acelera.
- **Con `devops`**: el build de validación de PR debe ser rápido (sin deploy); se recorta el pipeline en modo PR.
