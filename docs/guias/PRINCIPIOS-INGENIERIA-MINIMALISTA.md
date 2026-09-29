---
tipo: guia-oficial
tags: [principios, minimalismo, ingenieria, pipeline, gobernanza]
---

# Principios de ingeniería minimalista

> Versión genérica: se quitaron las fechas y el nombre del proyecto original. Investigación con
> fuentes primarias; lo que es atribución popular sin fuente confirmada se marca como tal.

Cuestionar requisitos, borrar partes o procesos, optimizar solo lo esencial, acelerar el ritmo y
automatizar al final — y después volver al primer paso. Aplica a cada feature **y al propio
pipeline de agentes**.

## Cómo se llama esta mentalidad

Es **"el algoritmo"** de 5 pasos que describió **Elon Musk** en la entrevista de Starbase con Tim
Dodd (Everyday Astronaut, agosto de 2021), y que Walter Isaacson formaliza en el capítulo "The
Algorithm" de su biografía (2023). Su base es el **razonamiento desde primeros principios**:
partir de lo que es fundamentalmente cierto, no de la analogía ("siempre se hizo así").

No es un método académico: es una heurística de la industria. Lo que la hace sólida es que
**cada paso tiene respaldo independiente** en literatura seria (sección 3).

- [Entrevista Starbase 2021](https://everydayastronaut.com/starbase-tour-and-interview-with-elon-musk/)
- [Texto de Isaacson](https://www.corporate-rebels.com/blog/musks-algorithm-to-cut-bureaucracy)

## 1. El lazo de 5 pasos

```
[1 Cuestionar] → [2 Borrar] → [3 Simplificar] → [4 Acelerar] → [5 Automatizar] ─┐
     ▲                                                                            │
     └────────────────────────────────────────────────────────────────────────────┘
```

| Paso | Regla | Pregunta de control |
|---|---|---|
| **1. Cuestionar el requisito** | Todo requisito lleva **el nombre de una persona** y su razón, nunca "lo pidió el área". Los que vienen de gente muy capaz son los más peligrosos, porque nadie los cuestiona | ¿Quién lo pidió, por nombre, y qué pasa si no se hace? |
| **2. Borrar la parte o el proceso** | Si nunca terminas volviendo a agregar algo (Musk habla de ~10 %), no borraste suficiente. El sesgo natural es dejar cosas "por si acaso" | ¿Qué paso, campo, pantalla o agente puede desaparecer? |
| **3. Simplificar y optimizar lo que quedó** | "El error más común de un ingeniero capaz es optimizar algo que no debería existir." El orden importa | De lo que queda, ¿qué medición justifica optimizar? ¿Es simple o solo es familiar? |
| **4. Acelerar el ciclo** | Solo después de 1–3: acelerar algo que se iba a borrar es esfuerzo perdido | ¿Cuál es el lote más chico que entrega valor y se puede revertir? |
| **5. Automatizar** | Al final. Musk admitió que en la línea del Model 3 automatizó demasiado y en el orden inverso ("los humanos están subestimados", abril de 2018) | ¿Ya corrió estable a mano? Cuando falle, ¿se detiene y avisa o sigue de largo? |

Después del paso 5 se vuelve al 1: lo automatizado también se cuestiona.

## 2. Diez principios aplicados a un pipeline de agentes

Cada uno con su regla, cómo aplicarlo en una feature o PR, un antiejemplo y la fuente.

1. **Requisito con nombre**
   - **Regla:** ningún requisito entra sin persona y razón.
   - **Aplicar:** el planner anota "pedido por X porque Y" en el plan y en el run doc.
   - **Antiejemplo:** "lo pidió negocio".
   - **Fuente:** Isaacson 2023; Brooks, *No Silver Bullet* (1987): la complejidad esencial nace de los requisitos.
2. **Sustracción primero**
   - **Regla:** antes de diseñar, listar qué se puede quitar.
   - **Aplicar:** sección obligatoria **"Qué quitamos"** en el plan. Si nunca volvemos a agregar nada, no quitamos suficiente.
   - **Antiejemplo:** un endpoint o un campo "por si acaso".
   - **Fuente:** Adams et al., *Nature* 592 (2021): la gente pasa por alto sistemáticamente los cambios que restan, salvo que se le indique, así que hay que forzarlo con checklist. Fowler, YAGNI (el costo de construir, retrasar, cargar y reparar lo presuntivo).
3. **La cerca de Chesterton**
   - **Regla:** solo se borra lo que se entiende.
   - **Aplicar:** `git blame`, dueño y razón antes de quitar código, una validación o una regla.
   - **Antiejemplo:** quitar un guard de seguridad porque "parece redundante".
   - **Fuente:** Chesterton, *The Thing* (1929).
4. **Optimizar solo lo que sobrevivió, midiendo**
   - **Regla:** nada se optimiza sin medición.
   - **Aplicar:** un PR de rendimiento trae el antes y el después.
   - **Antiejemplo:** poner caché a una consulta que se iba a eliminar.
   - **Fuente:** Knuth (1974): olvidar el 97 % de las microeficiencias, no el 3 % crítico, que se encuentra **midiendo**. Goldratt, *The Goal* (1984): optimizar fuera del cuello de botella es ilusión.
5. **Simple no es lo mismo que fácil**
   - **Regla:** preferir piezas que no se entrelazan y módulos profundos (mucha función detrás de una interfaz chica).
   - **Aplicar:** un DTO por caso de uso, sin herencia "por comodidad".
   - **Antiejemplo:** un helper genérico que todos tocan.
   - **Fuente:** Hickey, *Simple Made Easy* (2011); Ousterhout, *A Philosophy of Software Design* (2018): la complejidad es incremental.
6. **Lotes chicos y poco trabajo en curso**
   - **Regla:** una tarjeta = una rama = un worktree, con PRs pequeños.
   - **Aplicar:** dividir el PR si mezcla migración, refactor y feature.
   - **Antiejemplo:** un PR con 3 temas y muchas rondas de revisión.
   - **Fuente:** Reinertsen (2009); *Accelerate*/DORA (2018); Beck, *Tidy First?* (2023).
7. **Puertas de una y de dos vías**
   - **Regla:** lo reversible se decide rápido; lo irreversible (una migración de datos, un contrato público de API) se delibera.
   - **Aplicar:** el plan marca cuál es.
   - **Antiejemplo:** tratar un cambio de etiqueta como si fuera una migración destructiva, o al revés.
   - **Fuente:** Bezos, carta a los accionistas de 2015.
8. **Automatizar al final, con parada**
   - **Regla:** solo se automatiza un proceso ya simplificado y estable. El automatismo **se detiene y avisa** ante un problema (jidoka).
   - **Aplicar:** un hook o agente nuevo recién después de varias corridas manuales exitosas, con gates humanos en lo irreversible.
   - **Antiejemplo:** auto-merge cuando el QA pasa, sin revisión.
   - **Fuente:** Bainbridge, *Ironies of Automation* (1983): automatizar deja al humano vigilando lo que ya no practica, justo cuando más se lo necesita. Toyota, jidoka.
9. **Velocidad con estabilidad**
   - **Regla:** el tiempo de ciclo se mide junto con la tasa de fallos y el tiempo de recuperación.
   - **Aplicar:** contar las rondas de corrección por PR, no solo cuánto tardó.
   - **Antiejemplo:** celebrar PRs rápidos que vuelven con varias rondas de hallazgos.
   - **Fuente:** DORA; Goodhart y Strathern (cuando una medida se vuelve objetivo, deja de ser buena medida).
10. **El pipeline copia a su organización**
    - **Regla:** los traspasos entre agentes se notan en el código.
    - **Aplicar:** si el código sale inconsistente, revisar primero las plantillas de traspaso entre agentes.
    - **Fuente:** Conway (1968), con evidencia empírica en MacCormack, Rusnak y Baldwin, *Research Policy* (2012).

## 3. Respaldo por paso (fuentes)

- **Cuestionar:**
  - Brooks, [No Silver Bullet](https://dl.acm.org/doi/10.1109/MC.1987.1663532): complejidad esencial vs accidental.
  - Fowler, [YAGNI](https://www.martinfowler.com/bliki/Yagni.html).
  - **Cuidado:** el "64 % de las features casi nunca se usan" (Standish, 2002) es una **atribución con base débil**: salió de 4 aplicaciones internas ([Mike Cohn](https://www.mountaingoatsoftware.com/blog/are-64-of-features-really-rarely-or-never-used)). No usarlo como evidencia.
- **Borrar:**
  - Adams, Converse, Hales y Klotz, ["People systematically overlook subtractive changes"](https://www.nature.com/articles/s41586-021-03380-y), *Nature* 2021.
  - Klotz, *Subtract* (2021).
  - Taleb, *via negativa* (*Antifragile*, 2012).
  - Poppendieck, [las 7 mudas del software](https://www.infoq.com/news/2009/08/seven-wastes-intro), entre ellas las **features extra**.
  - Gall, *Systemantics* (1975): un sistema complejo que funciona evolucionó de uno simple que funcionaba.
  - Gabriel, [Worse is Better](https://www.dreamsongs.com/WorseIsBetter.html) (1991).
  - Saint-Exupéry, *Terre des hommes* (1939), cita **verificada**: la perfección se alcanza cuando ya no queda nada por quitar.
  - Dijkstra, "la simplicidad es prerrequisito de la confiabilidad": **atribución dudosa**; úsese como "atribuida a".
- **Simplificar:**
  - Knuth (1974), [la cita completa](https://probablydance.com/2025/06/19/revisiting-knuths-premature-optimization-paper/).
  - Ousterhout (2018).
  - Hickey, [transcripción](https://github.com/matthiasn/talk-transcripts/blob/master/Hickey_Rich/SimpleMadeEasy.md).
  - Goldratt, teoría de restricciones: identificar, explotar, subordinar, elevar y repetir.
- **Acelerar:**
  - *Accelerate* / [las 4 métricas de DORA](https://cloud.google.com/blog/products/devops-sre/using-the-four-keys-to-measure-your-devops-performance): en los datos, velocidad y estabilidad no se contraponen.
  - Reinertsen: lotes chicos y límite de trabajo en curso.
  - Boyd: el ciclo OODA.
  - Beck, *Tidy First?*: cambios de estructura separados de cambios de comportamiento.
- **Automatizar:**
  - Bainbridge, [Ironies of Automation](https://www.sciencedirect.com/science/article/abs/pii/0005109883900468) (1983).
  - [Toyota TPS / jidoka](https://global.toyota/en/company/vision-and-philosophy/production-system/).
  - [Tuit de Musk, 2018](https://x.com/elonmusk/status/984882630947753984).
  - "Automatizar una operación ineficiente magnifica la ineficiencia" (Gates): **atribución popular** sin fuente primaria encontrada.
- **Otros:**
  - [Chesterton's fence](https://www.chesterton.org/taking-a-fence-down/).
  - [Bezos 2015](https://s2.q4cdn.com/299287126/files/doc_financials/annual/2015-Letter-to-Shareholders.PDF).
  - [Conway 1968](https://melconway.com/Home/pdf/committees.pdf).
  - "Make it work, make it right, make it fast", [Kent Beck](https://newsletter.kentbeck.com/p/make-it-run-make-it-right-ii), que la atribuye a su abuelo.
  - KISS, Pareto y la filosofía Unix son heurísticas de oficio sin paper canónico.

## 4. Límites: cuándo NO borrar ni acelerar

- **Seguridad, regulación, accesibilidad y auditoría:** antes de borrar un requisito de este tipo se encuentra a su dueño (paso 1). Si no tiene dueño identificable, se trata como puerta de una vía.
- **Cuestionar sin faltar el respeto a la regla de negocio:** la pregunta es "¿quién lo pidió y por qué?", no "esto está mal". El requisito puede ser malo sin que la persona lo sea.
- **Goodhart:** si el paso 4 se mide solo por velocidad, se manipula. Siempre va emparejado con estabilidad.
- **Humano en el lazo:** en un pipeline de agentes, automatizar QA, revisión adversarial o el merge sin gates humanos reproduce la ironía de Bainbridge. Los agentes se detienen y avisan, nunca actúan de forma irreversible sin aprobación.
- **El 10 % de reagregado** es una regla de hardware, donde agregar cuesta material. En software volver a agregar es barato, así que el sesgo a no borrar puede ser mayor.

## 5. Cómo entra en un pipeline de agentes

- **planner:** plan con "Requisito con nombre", **"Qué quitamos"** y la marca de puerta de una o dos vías.
- **coder / coder-web:** no agregar abstracciones, campos ni opciones que el plan no pide (YAGNI); separar cambios de estructura de cambios de comportamiento.
- **qa:** además de correctitud, revisa "¿qué del diff sobra?".
- **ux-ui:** aplica el paso 2 a las pantallas: antes de agregar un elemento, qué se puede quitar o colapsar.
- **retro / system-auditor:** cada tanto, revisar qué agente, paso o regla del propio pipeline se puede borrar o fusionar.

## 6. Cómo lo codifican otros agentes de IA (referencia, no exhaustivo)

Estrellas aproximadas al momento de investigar, **no verificadas a mano** — sirven de referencia
de mercado, no de recomendación de instalación directa.

| Repo | Qué lo hace efectivo | Qué tomar |
|---|---|---|
| [anthropics/claude-plugins-official → `code-simplifier`](https://github.com/anthropics/claude-plugins-official/blob/main/plugins/code-simplifier/agents/code-simplifier.md) (oficial de Anthropic) | Conserva el comportamiento, **toca solo el código recién modificado**, prohíbe lo "ingenioso" (ternarios anidados, one-liners) y prefiere lo explícito a lo breve. No elimina abstracciones útiles | Su lista de "no hacer" como guardarraíl para el coder |
| [forrestchang/andrej-karpathy-skills](https://github.com/forrestchang/andrej-karpathy-skills) (interpretación de un post de Karpathy, no un texto suyo) | 4 reglas en una pantalla: pensar antes de codear, simplicidad primero, **cambios quirúrgicos** (el código muerto ajeno se menciona, no se borra) y criterio de éxito verificable antes de empezar | "Menciona, no borres" para el coder; "criterio de éxito antes de codear" para el planner |
| [obra/superpowers](https://github.com/obra/superpowers) | Lluvia de ideas obligatoria con 2–3 enfoques antes de codear, planes con YAGNI explícito y **revisión en dos etapas: primero cumplimiento del plan, después calidad** | Revisión del QA en dos pasadas |
| [EveryInc/compound-engineering-plugin → `code-simplicity-reviewer`](https://github.com/EveryInc/compound-engineering-plugin) | Revisor final dedicado solo a minimalismo: violaciones de YAGNI, sobreabstracción y redundancia | Separar el checklist de minimalismo del de corrección |
| [wezendy/elon-musk-algorithm-skills](https://github.com/wezendy/elon-musk-algorithm-skills) | Una skill por paso con **gate**: no se pasa al siguiente sin cerrar el anterior; cada requisito con originador humano con nombre | El gate por paso y el campo "dueño del requisito" |

**Patrón común de los que funcionan:** reglas **cortas y negativas** ("no X"), ámbito acotado al diff, separar "¿cumple el plan?" de "¿tiene calidad?" y preguntar antes de asumir.

### Cómo se integran al pipeline, en la práctica

- **[planner]** Cada requisito lleva **dueño con nombre** y una línea de por qué. Si nadie lo defiende con nombre, va a "a confirmar", no a "a implementar".
- **[planner]** Antes de agregar, listar qué se puede **quitar o reutilizar**. El plan incluye la sección "Borrado/Reusado" aunque quede vacía, para contrarrestar el sesgo aditivo (*Nature* 2021).
- **[coder]** Mínimo código que resuelve lo pedido: sin abstracciones de un solo uso, sin opciones configurables especulativas y sin manejo de errores para casos imposibles.
- **[coder]** Cambios quirúrgicos: se toca solo lo que la tarea exige. El código muerto o raro ajeno se **menciona en el reporte, no se borra** (Chesterton).
- **[qa]** Dos pasadas: (1) ¿hace exactamente lo del plan **y nada más**?; (2) calidad. Todo lo que sobra respecto del plan es un hallazgo, aunque funcione.
- **[qa]** Simplificar solo el diff sin cambiar el comportamiento: nada "ingenioso", explícito antes que breve, sin quitar abstracciones que ya pagan su costo.
