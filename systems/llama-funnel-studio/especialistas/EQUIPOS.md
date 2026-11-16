# Equipos de especialistas

Lee las reglas de marca del proyecto destino antes de cambiar su estructura o navegación.

El sistema empezó con un solo equipo (el funnel). Cuando el entregable pasó de `build.html` a una web real con adquisición, código de producción y operación, se añadieron tres equipos más. **Cada equipo dispara en una fase distinta; ninguno reabre las decisiones del anterior.**

| Equipo | Especialistas | Cuándo dispara | Manda en |
|---|---|---|---|
| **Funnel** | mercadologo, administrador, psicologo, sociologo, ingeniero-industrial, disenador, linguista, frontend, growth-data, neuromarketing, copywriter (+ programador como revisor) | Olas de extraer/reproducir (pasos 2-4) | Estrategia, mensaje, diseño, conversión |
| **Adquisición** | keywords, seo-tecnico, geo, meta-snippets, search-console | Tras el `plan.md`, antes y después de construir | Cómo llega el tráfico orgánico y de motores generativos |
| **Ingeniería** | arquitecto-angular, performance, ab-testing, accesibilidad | Cuando el build deja de ser un mockup y se implementa en un framework | Cómo se construye, se mide y se hace usable por todos en producción |
| **Operaciones** | devops, devsecops, gobernanza | Cuando existe repo/pipeline/tablero de verdad | Cómo se entrega, se protege y se gestiona el trabajo |

## Reglas comunes

1. **Heredan el CONTRATO.md**: salida en cinco secciones (`Decisiones, Directivas, Descartes, Faltantes, Conflictos`), identificadores `D-<especialista>-<n>`, `[FALTA: …]` en vez de inventar.
2. **No reabren el funnel.** Si `seo-tecnico` cree que el H1 debería ser otro, va a Conflictos; el mensaje lo decidió el equipo funnel.
3. **Prelación entre equipos nuevos:** en tensión adquisición↔ingeniería, gana quien tenga la restricción más dura medible (una meta description no justifica romper el budget de performance; un lazy-load no justifica ocultar contenido indexable). Lo irresoluble lo decide el orquestador con el usuario.
4. **Los que preguntan, preguntan primero.** `arquitecto-angular` (infraestructura/framework) y `search-console` (accesos y propiedad) tienen cuestionario de entrada; se responde ANTES de que su equipo trabaje, igual que la ficha del paso 1.
5. **Salidas**: en reproducción, cada especialista escribe `reproduccion/<producto>/<especialista>.md`. Los artefactos de código (workspace Angular, pipelines) viven fuera de `casos/`, en `web/` y la raíz del repo.
