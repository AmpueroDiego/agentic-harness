---
name: llama-funnel-studio
description: Analiza, extrae o adapta funnels y sitios para productos de Llama Solutions usando el sistema Llama Funnel Studio. Actívala cuando el usuario pida estudiar una web, transferir sus patrones a otra oferta, planear un funnel o coordinar sus equipos de adquisición, ingeniería u operaciones.
---

# Llama Funnel Studio para Codex

Usa esta skill como puente de Codex al sistema de dominio `systems/llama-funnel-studio/`. Los archivos del proyecto siguen siendo la fuente de verdad; no dupliques aquí sus protocolos detallados.

## Arranque y alcance

1. Ubica la raíz del workspace y `systems/llama-funnel-studio/`.
2. Lee el `AGENTS.md`, `README.md`, `CONTRATO.md` y `especialistas/EQUIPOS.md` de ese proyecto. Lee solo el orquestador y los protocolos necesarios para el modo solicitado.
3. El agente principal conserva el objetivo del usuario, el nivel de riesgo, las rutas de salida, las aprobaciones, la delegación, la síntesis y la evidencia final. Usa solo los especialistas necesarios. La extracción completa es un flujo específico que debe pedir el usuario; no convierte toda tarea en un pipeline largo.

## Delegar roles de dominio a Codex

Los archivos `especialistas/<role>/*.md` son instrucciones de rol, no agentes activos. Para una tarea acotada, el agente principal puede lanzar `llama_funnel_specialist` desde `.codex/agents/` y pasarle exactamente un especialista, modo, entradas y ruta de salida. Respeta sus instrucciones originales y el contrato común. No pidas a un especialista que cree subagentes; el principal controla la delegación y el ciclo de vida.

El workspace permite tres subagentes concurrentes. Mantén en paralelo el trabajo de extracción independiente, pero prográmalo en lotes dentro de ese límite. La reproducción sigue las tres olas estratégicas de Studio; no las mezcles ni adelantes el copy a las decisiones que lo condicionan. Si no hay subagentes, sigue los mismos contratos en secuencia.

## Extraer un funnel de origen

- Sigue `orquestador/extraer.md` y los scripts del proyecto. Primero captura y ejecuta los analizadores deterministas; luego entrega a cada especialista seleccionado los archivos raw y el JSON pertinente antes de interpretar.
- En una extracción completa, los 11 especialistas del equipo Funnel trabajan por separado; el proyecto puede añadir la revisión de `programador`. Sintetiza hallazgos y conflictos en las salidas del caso y en su skill reutilizable.
- Conserva el contrato: hallazgos con evidencia, patrones transferibles (`PT-*`), contaminación del origen (`CT-*`), preguntas para el destino (`Q-*`) y veredicto. No copies texto original en los patrones ni inventes datos ausentes.
- El opt-in de `tools/capture.py` permanece apagado salvo autorización explícita del usuario para enviar el formulario a un tercero. No envíes formularios solo para obtener más evidencia.
- Compara los JSON medidos con una captura fiel. Si difieren, informa la discrepancia y usa la captura como evidencia visual; no presentes el parser como infalible.

## Reproducir un patrón para otro producto

Sigue `orquestador/reproducir.md`. Antes de tomar decisiones que dependan de datos ausentes, recopílalos en un solo grupo conciso: oferta y público reales, pruebas disponibles, marca/logo/activos, referencias visuales y colores excluidos.

Audita el encaje según consciencia, sofisticación del mercado, ticket, tipo de compra, ciclo de decisión, modelo de entrega y riesgo percibido. Indica si la transferencia es directa, adyacente o distante.

Mantén las tres olas del proyecto: (1) posicionamiento, público y oferta; (2) disciplinas especialistas; (3) copywriting cuando las decisiones anteriores estén cerradas. Escala conflictos al orquestador principal; no resuelvas decisiones de otra disciplina dentro del reporte de un especialista.

Declara datos ausentes como `[FALTA: ...]`. No inventes promesas, testimonios, pruebas, activos ni resultados de conversión. Un plan no implica construir o desplegar.

## Ingeniería y operaciones

Activa especialistas de Adquisición, Ingeniería u Operaciones solo en la etapa definida en `especialistas/EQUIPOS.md`. Para una implementación en framework, lee primero las instrucciones, README y manifiestos del proyecto dueño. El envío de formularios, sistemas externos, credenciales, datos de producción, despliegues y otros efectos importantes requieren autorización propia. La recomendación de un especialista nunca concede permiso.

Usa las rutas y formatos de `CONTRATO.md`. El agente principal comprueba por separado los archivos cambiados, la evidencia y las verificaciones declaradas. Guarda decisiones y registros específicos con su proyecto; usa `CodexMemory/` para decisiones compartidas del Harness.
