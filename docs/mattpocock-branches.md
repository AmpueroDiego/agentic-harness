# Ramas de `mattpocock/skills` revisadas el 17 de noviembre de 2026

Se compararon las 154 referencias de rama del repositorio público con `main` mediante su historial Git. `main` y otras 108 ramas no tienen commits propios por delante. Las 45 restantes sí tienen commits adicionales; muchas están desfasadas respecto de `main` y parecen propuestas o experimentos. Una rama no equivale a una función publicada.

## Ideas que pueden mejorar Llama Harness

| Ramas | Hallazgo | Adaptación recomendada |
|---|---|---|
| [`constrain-skill`](https://github.com/mattpocock/skills/tree/constrain-skill) | Define una superficie permitida para un SDK o API y la comprueba con reglas de lint. | Adaptado en `$constrain-api`: un límite por proyecto, con reglas del stack existente cuando se solicite implementarlo. |
| [`code-review-standards-on-disk`](https://github.com/mattpocock/skills/tree/code-review-standards-on-disk), [`fix/573-code-review-leaf-reviewers`](https://github.com/mattpocock/skills/tree/fix/573-code-review-leaf-reviewers) | La revisión busca estándares reales del repo y separa revisores de alcance limitado. | Adaptado en QA: el principal adjunta estándares reales y diff; QA separa hallazgos de Spec y Standards. |
| [`subagents-fresh-context`](https://github.com/mattpocock/skills/tree/subagents-fresh-context), [`implementer-fresh-per-ticket`](https://github.com/mattpocock/skills/tree/implementer-fresh-per-ticket) | Los especialistas reciben un contexto fresco y acotado para una tarea. | Adaptado en los handoffs: contexto fresco cuando se admita, con instrucciones y evidencia precisas; el principal conserva el objetivo. |
| [`research-findings-file-early`](https://github.com/mattpocock/skills/tree/research-findings-file-early) | Una investigación larga abre su registro antes de buscar fuentes y lo actualiza con citas. | Usar notas de investigación para trabajos de varias sesiones; responder en chat cuando la investigación sea breve. |
| [`software-factory-skill`](https://github.com/mattpocock/skills/tree/software-factory-skill), [`chief-of-staff-wayfinder`](https://github.com/mattpocock/skills/tree/chief-of-staff-wayfinder) | Distinguen tareas, disparadores, ejecuciones, memoria y frenos antes de automatizar. | Antes de añadir un disparador automático, definir dueño, deduplicación, límite de intentos, comprobación y punto de revisión humana. |
| [`chief-of-staff-wiki`](https://github.com/mattpocock/skills/tree/chief-of-staff-wiki), [`chief-of-staff-shared-wiki-procedures`](https://github.com/mattpocock/skills/tree/chief-of-staff-shared-wiki-procedures) | Memoria fechada y ligada a commits; revisión por muestra de sesiones. | En runs importantes, enlazar commits y decisiones. Revisar patrones con `retro` cuando haya evidencia repetida. |

## Ramas evaluadas sin adopción inmediata

- `animatic-config` y `animatic-skill`: producción de vídeo; corresponde a un módulo de medios, no al Harness general.
- `spawn-skill`: prototipo antiguo de lanzamiento de agentes. Los perfiles nativos actuales ya cubren esa capacidad.
- `npm-publish`, `changeset-release/main`, `docs/per-agent-install` y `docs/install-flag-and-page-fixes`: distribución propia de este repositorio. Llama necesita decidir primero si empaqueta un plugin.
- `intake/issue-forms`, `tracker-attach-files`, `setup-tracker-template-fixes`, `setup-gitlab-output-and-verbatim-seeds` y `triage-out-of-scope-fence`: útiles solo al elegir un tracker y un contrato de intake para Llama.
- `tdd-bug-red-reproduces`, `codebase-design-check-facts`, `improve-codebase-architecture-mermaid-labels`, `grilling-number-across-rounds`, `glossary-triage-role-label`, `to-tickets-parent-sub-issue`, `wayfinder-tracker-and-research-fixes`, `retro-lazy-writing-for-agents` y `out-of-scope-retro-lazy-load`: mejoras puntuales de skills; se valoran cuando ese flujo esté activo en Llama.
- Las ramas `chief-of-staff-brief-block`, `chief-of-staff-shared-wiki-procedures`, `docs/per-agent-install`, `fix/research-530-no-nested-agent`, `fix/573-code-review-leaf-reviewers`, `issue-80-separate-content-from-backend`, `pr-credits-show-me-link`, `setup-ts-deep-modules-scan-and-bun`, `teach-asset-script-tags`, `wizard-bash32-apostrophe` y `wizard-template-fixes-2` contienen cambios de alcance específico o antiguo.
- `flatten-skills-tree`, `task/plugin-skills-dir-form`, `v1` y `wayfinder/research-inline` parten de bases muy antiguas; no conviene tratar su diff completo como propuesta actual.

La tabla de prioridades se basa en los commits y archivos distintos respecto de `main`. Se leyeron en profundidad `constrain` y `software-factory`; las demás ramas se clasificaron por su historial, archivos cambiados y propósito declarado. Antes de implementar una idea concreta, hay que abrir su diff completo y compararlo con la versión actual de `main`.
