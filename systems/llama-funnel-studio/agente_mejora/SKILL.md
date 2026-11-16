---
name: agente-mejora
description: Registro de mejoras del sistema. Anota lo que se detecta trabajando, lo aplica cuando toca y deja constancia de dónde quedó. Úsalo cuando salga una observación sobre el propio sistema — un parser que miente, un prompt mejorable, una decisión de arquitectura — o cuando se quiera aplicar algo pendiente.
---

# Agente de mejora

El sistema se usa y, usándolo, se aprende de él. Este registro existe para que eso no se pierda entre conversaciones.

Vive fuera de `tools/` a propósito. `tools/` es la mitad determinista del pipeline de extracción; esto no extrae nada, es meta sobre el propio sistema.

## Frontera

**Sí:** defectos del sistema, artefactos de los parsers, mejoras de prompt, decisiones de arquitectura, propuestas descartadas y por qué, y errores de método que conviene no repetir.

**No:** hallazgos sobre un funnel analizado — eso va en `casos/<slug>/extraccion/`. Tampoco tareas de un caso concreto: si falta la ficha del producto, eso no es una mejora del sistema, es un paso pendiente del caso.

## Los archivos

| Archivo | Qué es |
|---|---|
| `agente_mejora.xlsx` | El registro. 10 columnas, una fila por observación |
| `mejoras.py` | Lo genera y lo actualiza. **Aditivo:** solo añade filas con ID nuevo, nunca pisa lo editado a mano |

## Estados

| Estado | Significa |
|---|---|
| `Pendiente` | Detectada, sin aplicar |
| `Aplicada` | Hecha. **La columna Constancia dice dónde**, o el estado no vale nada |
| `Decidida` | Se decidió un criterio o una forma de trabajar, no un cambio de código |
| `Descartada` | Se evaluó y no se hace. Se conserva **con su motivo**, para no volver a proponerlo dentro de tres meses |

## IDs

`M-<n>` para mejoras y defectos. `D-<n>` para decisiones y descartes. No se reutiliza un ID aunque su fila se descarte: el ID es la referencia estable desde una conversación o un commit.

---

## Procedimiento

### Anotar

Se anota **en el momento en que se detecta**, no al final. Una observación que espera al resumen se pierde o se anota mal.

Dos vías, ambas válidas:

- **En `mejoras.py`:** añadir una tupla a `REGISTRO` con un ID libre y correr `python agente_mejora/mejoras.py`. Es la vía preferente cuando la anota un agente, porque queda en texto y se revisa en diff.
- **Directamente en el Excel:** escribir la fila a mano. El script no la tocará.

Cada fila necesita las tres columnas que hacen el trabajo:

1. **Observación** — qué pasó, con el dato concreto. No "el parser falla" sino "reportó el 86,03% de superficie en `#FFFFFF` en una página oscura; `#FFFFFF` aparece 3 veces en todo el HTML".
2. **Mejora a aplicar** — qué hacer, ejecutable. No "mejorar la detección" sino "incluir `<button>`, `[role=button]` y `cursor:pointer` entre los candidatos a CTA".
3. **Por qué importa** — la consecuencia. Es lo que permite priorizar dentro de seis semanas, cuando ya no se recuerde el contexto.

### Aplicar

1. Filtrar por `Pendiente` y ordenar por prioridad.
2. Aplicar el cambio.
3. **Verificarlo de verdad.** Un parser corregido se comprueba volviendo a correr el análisis sobre un caso existente y mirando que el número cambió. Un prompt corregido, con `--dry-run`.
4. Cambiar `Estado` a `Aplicada` y **rellenar `Constancia`** con el sitio exacto: función, sección o comando que lo demuestra.

**Sin constancia no se marca como aplicada.** Una fila en verde que nadie puede verificar es peor que una fila pendiente, porque cierra el asunto en falso.

### Revisar

Al cerrar un caso, antes de dar el trabajo por terminado: repasar si algo de lo que salió merece fila. La mayoría de las mejores observaciones aparecen al verificar salidas y al resolver tensiones, que es cuando se ve dónde el sistema empuja al error.

---

## Reglas

1. **Se anota el dato, no la impresión.** Una observación sin cifra ni archivo no es accionable dentro de un mes.

2. **Lo descartado también se anota.** Con su motivo. Es lo que evita volver a discutir lo mismo.

3. **Un artefacto de parser es prioridad alta, siempre.** El principio del sistema es "los hechos antes que el modelo": `raw/analysis/*.json` se presenta como medición y nadie lo cuestiona. Un parser que miente no produce un error, produce un error que se propaga con autoridad.

4. **Si un conteo admite una lectura equivocada, la mejora no es dar mejor el número: es derivar la conclusión.** Salió de ver a diez especialistas pasar por alto un hecho que estaba delante en forma de conteo crudo.

5. **Una mejora se arregla para todos los casos futuros, no para el que la destapó.** El caso concreto es el síntoma; el sistema es el paciente. Dos consecuencias prácticas:

   - **Nada de heurísticas calcadas del documento que tienes delante.** Una lista de palabras clave en un idioma, sacada de los encabezados de una página, no clasifica: memoriza. En cuanto llega otra web —otro nicho, otra lengua, otro sector— devuelve etiquetas peores que no devolver ninguna. Se mide lo que es igual en cualquier página: estructura, conteos, geometría, relaciones. Si nombrar algo exige entender el texto, eso es interpretación y le toca al modelo, no al parser.
   - **Un caso ya extraído no se parchea a mano.** Sus archivos son la foto que sacaron las herramientas de entonces. Si la mejora cambia lo que habrían dicho, se vuelve a extraer; editar la prosa a mano deja el caso descuadrado con su propio `raw/`.

6. **Mejor null que una etiqueta inventada.** Un campo vacío se ve y se pregunta. Uno relleno con una suposición se cree.

7. **No duplicar lo que ya está en el repo.** Si el arreglo está hecho y visible en el código, la fila sobra salvo que explique un *porqué* que el código no cuenta.

8. **Una fila, una mejora.** Si al escribirla aparece un "y además", son dos filas.
