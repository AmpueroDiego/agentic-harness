---
name: extraer-funnel
description: Extrae un funnel completo lanzando los 11 especialistas y genera el super-skill en casos/<slug>/. Úsalo cuando el usuario pida analizar, extraer o descomponer una web o funnel.
---
# Orquestador de extracción

Convierte una URL en un super-skill reutilizable. No analiza nada por su cuenta: captura, reparte y funde.

## Entrada

URL, archivo HTML o carpeta con screenshots. Opcionalmente un `<slug>`; si no, se deriva del dominio.

## Procedimiento

### Paso 1 — Capturar y medir

```bash
python tools/capture.py <url> --depth 1 --passes 3
python -m tools.analyze <slug>
```

La captura deja `casos/<slug>/raw/` y el análisis deja `raw/analysis/` con
cinco JSON de hechos: `design`, `attention`, `text`, `flow` y `trackers`.
Ver `tools/README.md` para las opciones.

**El opt-in no se envía sin permiso explícito del usuario** (`--submit-optin`), porque
mete datos en un sistema ajeno. Pero adviértele de lo que pierde si no lo autoriza:
sin pasar el formulario, `ingeniero-industrial` no puede medir el proceso,
`administrador` no ve el precio real y `growth-data` no ve los píxeles de conversión.

Si Playwright no está disponible, pide al usuario el HTML y las capturas. **No inventes
el contenido de la página.**

### Paso 2 — Repartir
Lanzar los 11 especialistas **en paralelo**, cada uno con este encargo:

```
Eres el especialista <esp>. Lee especialistas/<esp>/extraer.md y ejecuta
tu PROTOCOLO EXTRAER sobre casos/<slug>/raw/.
Respeta el contrato en CONTRATO.md.
Escribe tu salida en casos/<slug>/extraccion/<esp>.md y no toques nada más.
```

Lanzarlos como agentes independientes, uno por especialista. No hay subagentes
predefinidos: el encargo de abajo contiene todo lo que cada uno necesita saber.
`python tools/run.py plan <slug>` te los imprime ya montados.

**Cada especialista lee primero su JSON de `raw/analysis/`** — son hechos medidos, no estimaciones. Su trabajo empieza donde acaba el parser.

Especialistas: `frontend`, `disenador`, `neuromarketing`, `psicologo`, `linguista`, `copywriter`, `mercadologo`, `sociologo`, `ingeniero-industrial`, `administrador`, `growth-data`.

**Dos modos:**
- **Paralelo** (por defecto): 11 subagentes concurrentes. Rápido, más caro.
- **Secuencial**: se ejecutan los protocolos en línea, uno tras otro, en el contexto actual. Más barato, más lento. Usar cuando el usuario lo pida o cuando la web sea simple.

Si el usuario quiere solo algunas disciplinas, lanzar únicamente esas. Los 11 no son obligatorios.

### Paso 3 — Fundir
Leer las 11 extracciones y escribir `casos/<slug>/sintesis.md`:

```markdown
# Síntesis — <slug>

## Qué es
Tipo de interfaz, etapa del funnel, producto, avatar aparente.

## Esqueleto
Secuencia de bloques con el propósito de cada uno.

## Los 5 patrones que hacen que esto funcione
Los `PT-*` más potentes de todas las extracciones, con su origen.

## Contaminación consolidada
Todos los `CT-*`. Es la lista de lo que nunca debe aparecer en una reproducción.

## Preguntas al producto destino
Todas las `Q-*`, deduplicadas y agrupadas. Esto se convierte en la ficha a rellenar.

## Tensiones
Dónde los especialistas no coinciden en su lectura.

## Veredicto conjunto
¿Merece la pena usar esto como plantilla? ¿Para qué tipo de producto sí y para cuál no?
```

### Paso 4 — Generar el super-skill
Escribir `casos/<slug>/SKILL.md` a partir de `casos/_PLANTILLA.md`, incrustando el esqueleto, los patrones, la contaminación y las preguntas. Ese archivo es el entregable: a partir de él se puede reproducir el funnel para cualquier producto sin volver a analizar nada.

### Paso 5 — Reportar
Al usuario, en prosa y breve:
- Qué es el funnel y en qué etapa está
- Los 3 hallazgos más útiles de todo el conjunto
- Qué le falta al usuario para poder reproducirlo (las preguntas)
- Si algún especialista levantó bandera roja

## Reglas

- **No resumas las extracciones al usuario.** Están en disco; se le da el veredicto, no el volcado.
- **Si un especialista falla, sigue.** Anótalo como hueco en la síntesis; no bloquees el resto.
- **Nada de texto literal del original** en la síntesis ni en el super-skill.
