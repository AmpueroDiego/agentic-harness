# Sistema de extracción y reproducción de funnels

Consulta el [catálogo de protocolos](catalogo.md) para acceder a cada especialista.
Esta distribución incluye las herramientas y los contratos reutilizables.
Cada proyecto crea su aplicación `web/` y sus casos locales cuando los necesita.
El registro Excel se genera localmente; el historial original no forma parte del paquete.

Once especialistas analizan una web cada uno por su lado, se funden sus lecturas en un super-skill reutilizable, y se reconstruye para el producto que tú quieras.

---

## Empieza aquí

**Si eres un LLM que acaba de entrar en esta carpeta, esto es lo único que necesitas para arrancar.**

Antes de diseñar, lee las reglas de marca del proyecto destino. Esta distribución no incluye decisiones privadas de marca.

### 1. Instalar y capturar

```bash
python -m venv .venv && .venv/Scripts/activate    # source .venv/bin/activate en Unix
pip install -r tools/requirements.txt

python tools/run.py extraer https://ejemplo.com/oferta
```

Configura un navegador autorizado antes de capturar. Usa perfiles temporales y respeta los controles del sistema.

### 2. Ejecutar los encargos

Lee **`orquestador/extraer.md`** desde el Paso 2 y lanza cada encargo. Son once lecturas independientes del mismo material: van en paralelo si tu entorno lo permite, en secuencia si no. El resultado es el mismo, solo más lento.

### 3. Reproducir para otro producto

Lee **`orquestador/reproducir.md`**. Pide la ficha del producto, audita compatibilidad y reparte en tres olas.

```bash
python tools/deepseek.py reproducir <slug>     # las tres olas, sin agentes
```

El entregable por defecto es `reproduccion/plan.md`, no la página. El `build.html` es el paso 5 y es opcional.

### Orden de lectura

| # | Archivo | Qué te da |
|---|---|---|
| 1 | `orquestador/extraer.md` o `reproducir.md` | El procedimiento paso a paso |
| 2 | `CONTRATO.md` | Formato de entrada y salida, olas, prelación de conflictos. **Sin esto las salidas no encajan entre sí** |
| 3 | `especialistas/<nombre>/extraer.md` | Quién es, qué mira, qué *no* mira |
| 4 | `especialistas/<nombre>/reproducir.md` | Solo al reproducir: sus reglas de decisión y autoverificación |

### El contrato en una frase

Al extraer, cada especialista escribe `casos/<slug>/extraccion/<nombre>.md` con cinco secciones: **Hallazgos**, **Patrones transferibles** (`PT-*`), **Contaminación** (`CT-*`), **Preguntas al producto destino** (`Q-*`) y **Veredicto**. Al reproducir escribe en `reproduccion/<nombre>.md` con **Decisiones**, **Directivas** (`D-*`), **Descartes**, **Faltantes** (`[FALTA: …]`) y **Conflictos**. El detalle en `CONTRATO.md`.

---

## Estructura

```
CONTRATO.md            el contrato que cumplen los 11: formato, olas, conflictos
README.md              esto

orquestador/           el procedimiento (la mitad dirigida por modelo)
├── extraer.md
└── reproducir.md

especialistas/         uno por carpeta, con sus dos mitades
├── frontend/
│   ├── extraer.md     identidad, frontera, cómo lee una web
│   └── reproducir.md  reglas de decisión, salida, autoverificación
├── disenador/
└── … (11)

tools/                 lo determinista (la mitad que sí es código)
├── run.py             EL ORQUESTADOR: captura, mide, reparte
├── capture.py         Playwright → raw/  (una pasada, vuelca elements.json)
├── analyze/           5 analizadores en Python puro → raw/analysis/*.json
├── deepseek.py        ejecuta los 11 encargos por API, sin agentes
├── verificar.py       comprueba las salidas contra el contrato
└── README.md

agente_mejora/         lo que se aprende usando el sistema, para no perderlo
├── SKILL.md           qué se anota, qué no, y cuándo se da por aplicada
├── mejoras.py         genera y actualiza el registro (aditivo, no pisa ediciones)
└── agente_mejora.xlsx el registro

casos/                 la salida, una carpeta por funnel analizado
├── README.md          índice autogenerado: qué URL de funnels.txt es qué carpeta
├── _PLANTILLA.md
└── <slug>/
    ├── SKILL.md       el super-skill: reproduce este funnel para cualquier producto
    ├── raw/           captura + analysis/
    ├── extraccion/    11 lecturas
    ├── sintesis.md    la fusión
    └── reproduccion/  directivas + build.html
```

Nada oculto y nada atado a una herramienta concreta: cualquier agente que sepa leer markdown y ejecutar Python puede correr esto.

---

## Dónde está el orquestador

Partido en dos mitades, porque solo una puede ser código:

| Mitad | Qué hace | Dónde |
|---|---|---|
| **Determinista** | Capturar, medir, montar carpetas, imprimir los 11 encargos | `tools/run.py` |
| **Dirigida por modelo** | Leer, interpretar, resolver conflictos, escribir | `orquestador/extraer.md` y `reproducir.md` |

Un script no puede decidir si el avatar es "consciente del problema". Pero sí puede capturar, medir y decirte exactamente qué encargo lanzar a cada especialista, con su tool ya resuelta.

```bash
python tools/run.py extraer <url>                     captura + mide + reparte
python tools/run.py estado <slug>                     qué falta por hacer
python tools/run.py plan <slug> --modo reproducir     el reparto en tres olas
python tools/run.py indice                            regenera casos/README.md
```

---

## Extraer es paralelo; reproducir va en olas

Extraer son once lecturas independientes del mismo material: se lanzan a la vez.

Reproducir no, porque unas decisiones condicionan a otras:

| Ola | Quién | Fija |
|---|---|---|
| 1 | `mercadologo`, `administrador` | Avatar, consciencia, sofisticación, precio |
| 2 | `psicologo`, `sociologo`, `ingeniero-industrial`, `disenador`, `linguista`, `frontend`, `growth-data`, `neuromarketing` | Su capa, con la ola 1 cerrada |
| 3 | `copywriter` | Escribe con todo lo anterior decidido |

Si `copywriter` escribe antes de que `mercadologo` fije el nivel de consciencia, escribe para el avatar equivocado y hay que rehacerlo entero.

---

## Los once

| Especialista | Ve | Su tool |
|---|---|---|
| `frontend` | DOM, CSS, layout, responsive, componentes, stack | `flow.json` |
| `disenador` | Paleta, tipografía, espaciado, género visual, arte | `design.json` |
| `neuromarketing` | Saliencia, atención, carga cognitiva, sesgos medibles | `attention.json` |
| `psicologo` | Motivación, emoción, identidad, resistencias | — |
| `linguista` | Registro, sintaxis, ritmo, campo semántico, microcopy | `text.json` |
| `copywriter` | Framework, titulares, oferta, objeciones, prueba, CTA | `text.json` |
| `mercadologo` | Avatar, nivel de consciencia, sofisticación, posicionamiento | — |
| `sociologo` | Códigos culturales, clase, estatus, tribu, normas del nicho | — |
| `ingeniero-industrial` | El funnel como proceso: pasos, fricción, cuellos de botella | `flow.json` |
| `administrador` | Precio, oferta, tiers, escalera de valor, garantía | `trackers.json` |
| `growth-data` | Píxeles, tracking, tests A/B, mecanismos ocultos | `trackers.json` |

Cada uno tiene una sección `Frontera` que dice qué **no** mira y a quién se lo remite. Es lo que evita que once especialistas escriban once párrafos sobre el mismo botón.

---

## Los hechos antes que el modelo

Nada que un parser pueda medir se le pregunta a un modelo. `tools/analyze/` deja cinco JSON en `raw/analysis/` y cada especialista los lee **antes** de mirar nada.

Un parser dice `#E4572E` con certeza y te da su porcentaje exacto de superficie; un modelo de visión dice "naranja terracota" y a veces falla el tono. Al modelo se le pregunta lo que el parser no puede saber: por qué está ahí ese naranja.

**Con una advertencia que se paga cara si se olvida:** un parser es exacto midiendo lo que sabe medir, y silencioso cuando la página no encaja con lo que asume. Los cinco JSON se leen como hechos y por eso nadie los cuestiona — un parser que miente no produce un error, produce un error con autoridad. **Si un número contradice lo que se ve en `full.png`, gana la captura.**

Pasó dos veces en la primera extracción real, y ninguna era detectable sin mirar: el detector de CTA dijo que no había ninguno en una página con ocho, y el de color dio el 86 % de la superficie a blanco en una página negra. Los dos por la misma causa — leer `background-color` e ignorar `background-image`, que es donde vive un gradiente. El registro local puede documentar estos casos; esta distribución no publica historiales privados.

Detalle en [tools/README.md](tools/README.md).

**Por qué las tools no viven en la carpeta de cada especialista:** tres de las cinco sirven a dos — `text.py` a `linguista` y `copywriter`, `flow.py` a `ingeniero-industrial` y `frontend`, `trackers.py` a `growth-data` y `administrador` — y las cinco comparten la matemática de color de `_common.py`. Repartirlas significaría duplicar archivos que se separan al primer arreglo. El vínculo es visible igualmente: cada especialista declara su tool en el frontmatter de su `extraer.md`.

---

## Las cuatro reglas que sostienen todo

1. **Un dato que falta se declara, no se inventa.** Cuando a un modelo le falta un dato lo rellena con algo plausible, y así acaban las páginas prometiendo cosas que el producto no hace. Los especialistas escriben `[FALTA: …]`. Un parser, `null`: mejor un campo vacío, que se ve y se pregunta, que uno relleno con una suposición, que se cree.

2. **Patrón sí, frase no.** Se extrae "titular de promesa cuantificada con plazo, 8-12 palabras", nunca la frase del original.

3. **Cada disciplina manda en lo suyo.** Cuando dos chocan, resuelve la prelación de `CONTRATO.md`.

4. **Se mide lo que es igual en cualquier página; lo que exige entender el texto es del modelo.** Estructura, conteos, geometría y color son iguales en una landing de infoproducto en español y en una de SaaS B2B en alemán. El significado de un bloque no. En cuanto una herramienta necesita una lista de palabras clave para decidir algo, ha dejado de medir y ha empezado a memorizar el documento de quien la escribió — y en la siguiente web devuelve etiquetas peores que no devolver ninguna.

   Lo mismo vale al arreglar: **una mejora se arregla para todos los casos futuros, no para el que la destapó.** El caso concreto es el síntoma; el sistema es el paciente. Detalle en [tools/README.md](tools/README.md).

---

## Coste

Once agentes es rápido y no es barato. Alternativas:

- **Otro modelo por API:** `python tools/deepseek.py extraer <slug>` ejecuta los 11 encargos contra DeepSeek y escribe las extracciones directamente. Sin agentes, en paralelo con hilos, y elegible por especialista. Detalle en [tools/README.md](tools/README.md). Verifica lo que devuelva: un modelo barato acierta los números y falla las inferencias.
- **Secuencial:** ejecuta los protocolos en línea, sin lanzar agentes.
- **Subconjunto:** solo las disciplinas que interesen. Los 11 no son obligatorios.
- **Solo `growth-data`:** casi todo son consultas al DOM, sin modelo, y ya te dice en qué plataformas compra tráfico el competidor, qué está testeando ahora y cuántos pasos tiene su funnel de verdad.
