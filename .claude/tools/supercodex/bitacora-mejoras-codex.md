---
tipo: bitacora
fecha: 2026-10-30
tags: [codex, proceso, mejoras]
---

# Bitácora de mejoras a Codex y al proceso de revisión

Una fila por cambio, **con la fecha en que entró en vigor**, para medir en `rondas-codex.tsv` y `hallazgos-codex-historico.tsv` qué cambio bajó (o no) los hallazgos. La columna «prompt» del registro de rondas nombra la versión del contexto que recibió Codex.

| Fecha | Cambio | Qué se espera que baje | Dónde / evidencia |
|---|---|---|---|
| 2026-09-14 | Codex CLI instalado como segundo revisor local (`/codex`) antes del push | Hallazgos que llegan al bot del PR | memoria `project_codex_cli_segundo_revisor` |
| 2026-09-24 | Codex primero como coder, QA y adversary en `/orquestar` (DeepSeek solo con Claude >70 %) | — (reparto de motores) | commit «chore(orquestar): Codex primero en coder, QA y adversary» |
| 2026-09-26 | Codex solo con luna (coder) y sol (revisión/lógica difícil); revisión de tildes tras cada coder | Errores de coder barato | commit «build(flujo): Codex solo luna y sol…», memoria `project_reparto_de_modelos_codex_opus` |
| 2026-09-28 | `AGENTS.md` con guía de revisión para el bot (api-core y web-app); 29/09 compara contra la rama base real | Ruido del bot (falsos positivos, diff contra la base equivocada) | `git log -- AGENTS.md` en api-core y web-app |
| 2026-09-29 | `/supercodex`: rondas registradas por PR y 2 rondas limpias antes de pasar a Revisor Principal | Hallazgos que llegan a la revisión humana | commit «chore(supercodex): rondas registradas, script a-revision.sh y métricas» |
| 2026-10-01 | Puerta de `/codex` local antes de abrir el PR | Hallazgos en la 1.ª ronda del bot | commit «feat(skills): /listo-para-Revisor Principal y puerta de /codex local…» |
| 2026-10-02 | Reglas en coder, coder-web, qa y planner nacidas de hallazgos de Codex (#<n>, #<n>, web #<n>); Codex revisa el plan antes de codear; Codex revisa en español | Temas repetidos (estado, validación) | commits «docs(agentes): reglas nacidas de los hallazgos de Codex…», «docs(orquestar): …Codex revisa el plan» |
| 2026-10-07 | Dos pasadas locales de Codex antes del PR; regla de gravedad P0–P3 en Modo Enjambre | Hallazgos en el bot | commits «feat(orquestar): …dos pasadas locales de Codex antes del PR», «docs(orquestar): Modo Enjambre con regla de gravedad P0–P3» |
| 2026-10-09 | Revisión local de Codex antes de cada push y el bot una vez por lote | Rondas del bot por PR | commit «docs(supercodex): revisión local de Codex antes del push y el bot una vez por lote» |
| 2026-10-16 | `AGENTS.md`: «Las reglas que más se repiten en las revisiones de Codex» (api y web); Codex en `service_tier fast`, revisión con sol high | Temas repetidos (versión/409, tenant, historial) | `git log -- AGENTS.md` en api-core y web-app; memoria `feedback_codex_service_tier_fast` |
| 2026-10-19 | Revisión local de UI pregunta adónde va el foco al desmontar un control; solo bloquean P1/P2 de datos o flujo; tema que da 2 vueltas sale a tarjeta | Hallazgos de foco/UI; rondas por PR | commits «chore(codex): la revisión local de UI pregunta adónde va el foco…», «docs(supercodex): 1 ronda tras un arreglo puntual…» |
| 2026-10-20 | Un solo `@codex review` por vez en cada PR | Rondas duplicadas y cuota | commit «chore(harness): un solo @codex review por vez…», memoria `feedback_un_solo_codex_review_por_vez` |
| 2026-10-21 | Opus en planner, coder y qa de Claude; Codex `gpt-6.1-sol` | Errores de lógica que llegan a Codex | commit «chore(agentes): propuestas de la retro del 21/10…» |
| 2026-10-22 | Codex local primero (2 limpias en local) y bot solo como segunda mirada; PR en borrador hasta las 2 limpias; coder de Codex con sol por defecto; tarjetas chicas (3-5 archivos) con TDD | Hallazgos en el bot y vueltas por PR | memorias `feedback_codex_local_primero_sin_actions`, `feedback_tarjetas_chicas_tdd_y_a_tope`; commits del 22/10 |
| 2026-10-23 | TDD + SDD obligatorio en todo cambio de lógica o estado (REQ confirmado → tests rojos → coder) | Hallazgos de validación/negocio y estado | memoria `feedback_tarjetas_chicas_tdd_y_a_tope` |
| 2026-10-27 | Rondas de Codex de una por vez por PR (la 2.ª solo si la 1.ª sale limpia) | Cuota gastada en rondas inútiles | memoria `feedback_rondas_codex_una_por_vez` |
| 2026-10-27 | Coder de Codex `gpt-6.1-sol` en esfuerzo **high** para estado y concurrencia de web-app, con el chequeo «¿respuesta tardía, reintento o cambio de sesión a mitad?» en cada tarea | Hallazgos de concurrencia/respuesta tardía en web | commit `<sha>`, `.claude/commands/codex.md` |
| 2026-10-27 | Agente `adversary` de Claude pasa de sonnet a **opus** | Casos borde de concurrencia que llegan a Codex | commit `<sha>`, `.claude/agents/adversary.md` |
| 2026-10-27 | Regla de rondas: 2 limpias seguidas sobre el HEAD final; hasta 5 rondas normal, 8 techo; merge de develop sin conflictos no reinicia | Rondas por tarjeta | memoria `feedback_una_ronda_limpia_basta` |
| 2026-10-27 | Registro de rondas locales `rondas-codex.tsv`; línea base con prompt `base-diff+foco` (31 rondas, 7 bloqueantes, 4 no bloqueantes) | — (medición) | commit `<sha>` |
| pendiente | Pasar el **REQ de la tarjeta** a cada revisión y arreglo de Codex (prompt `+REQ`) | Hallazgos de «decisión ya tomada», requisitos faltantes | `codex-revisar.sh`, `flujo.sh arreglar` |
| pendiente | **Decisiones del responsable** en una sección del REQ, no solo en el chat (prompt `+REQ+decisiones`) | Decisiones que el agente o Codex desconocen | `requisitos/REQ-*.md` |
| pendiente | `AGENTS.md`: web «toda respuesta tardía verifica que su intento siga vigente»; api «orden de validaciones: existe/borrado 409 → versión 409 → responsable 403» | Concurrencia web; choques al mezclar ramas en api | `AGENTS.md` de web-app y api-core (también lo lee el bot de GitHub) |

Al aplicar una fila «pendiente», reemplazar «pendiente» por la fecha real y anotar el commit.
