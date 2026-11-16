# Contrato común de especialistas

Todos los especialistas de `especialistas/` cumplen este contrato. Es lo que permite que un orquestador los lance en paralelo sin conocer sus interioridades.

---

## Estructura de un caso

```
casos/<slug>/
├── SKILL.md              ← el super-skill generado (producto final del extraer)
├── raw/                  ← captura: html, screenshots, headers, cookies
├── extraccion/
│   └── <especialista>.md ← uno por especialista
├── sintesis.md           ← fusión de las 11 extracciones
└── reproduccion/
    └── <producto>/       ← una subcarpeta por producto destino
        ├── ficha-producto.md   ← lo que el producto nuevo tiene de propio
        ├── compatibilidad.md   ← la auditoría de los siete ejes
        ├── <especialista>.md   ← directivas de cada uno, once archivos
        ├── plan.md             ← el entregable: todo consolidado por bloque
        └── build.html          ← opcional, solo si se pide
```

`<slug>` = dominio sin TLD y en minúsculas. Ejemplo: `casos/mindvalley-masterclass/`.
`<producto>` = nombre corto del producto destino, en minúsculas. Ejemplo: `mi-curso-de-fotografia`.

**Un origen sirve a muchos productos.** Lo de arriba de `reproduccion/` es el activo generalizado y se extrae una sola vez: `SKILL.md`, `sintesis.md` y `extraccion/` no dependen de para quién se reproduzca. Lo de dentro de `reproduccion/<producto>/` es consumo de ese activo y es desechable.

Por eso la ficha del producto vive dentro de su subcarpeta y no en la raíz del caso: dos productos que reproduzcan el mismo funnel no comparten nada excepto lo que ya estaba extraído.

---

## Protocolo EXTRAER

**Entrada que recibe todo especialista:**
- Ruta a `casos/<slug>/raw/`
- Su propio SKILL.md

**Salida obligatoria:** `casos/<slug>/extraccion/<especialista>.md` con exactamente estas cinco secciones:

```markdown
# <Especialista> — <slug>

## 1. Hallazgos
Lo que observo, con evidencia. Cada afirmación apunta a algo concreto del raw.
Si algo no se puede observar, no se afirma.

## 2. Patrones transferibles
Lo que funcionaría para OTRO producto. Patrones, no contenido.
Formato: `PT-<esp>-<n>: <patrón> — <por qué funciona>`

## 3. Contaminación
Lo que NO transfiere: específico del original, de su marca o de su nicho.
Formato: `CT-<esp>-<n>: <elemento> — <por qué no transfiere>`

## 4. Preguntas al producto destino
Qué necesito saber del producto nuevo para poder reproducir mi parte.
Formato: `Q-<esp>-<n>: <pregunta>`

## 5. Veredicto
Un párrafo. Qué hace bien esta web desde mi disciplina, qué hace mal,
y si mi capa merece copiarse o rehacerse.
```

**Reglas de extracción, iguales para todos:**

1. **Observar, no suponer.** Sin evidencia en el raw, no hay hallazgo.
2. **No invadir otra disciplina.** Cada SKILL.md tiene su sección `Frontera`. Lo de fuera se remite al especialista que toca.
3. **Sin promesas de resultado.** Se reporta lo observado, nunca "esto sube la conversión un X%".
4. **Patrón, no copia.** En la sección 2 nunca va texto literal del original.

---

## Protocolo REPRODUCIR

**El protocolo completo de cada especialista vive en `especialistas/<especialista>/reproducir.md`**, no en su archivo de extracción. Ahí están sus reglas de decisión, su formato de salida, su autoverificación y sus conflictos típicos.

### Reproducir no es paralelo: va en tres olas

Extraer sí es paralelo — once lecturas independientes del mismo material. Reproducir no: unas decisiones condicionan a otras, y lanzarlas todas a la vez produce once decisiones incompatibles.

| Ola | Especialistas | Por qué aquí |
|---|---|---|
| **1** | `mercadologo`, `administrador` | Fijan avatar, consciencia, sofisticación y precio. Todo lo demás depende de esto |
| **2** | `psicologo`, `sociologo`, `ingeniero-industrial`, `disenador`, `linguista`, `frontend`, `growth-data`, `neuromarketing` | Paralelo. Cada uno decide lo suyo con la ola 1 ya fijada |
| **3** | `copywriter` | Escribe con el manual de voz, las resistencias, la oferta y el framework ya decididos |

Saltarse el orden es el error más caro del sistema: si `copywriter` escribe antes de que `mercadologo` fije el nivel de consciencia, escribe para el avatar equivocado y hay que rehacerlo entero.

**Entrada:**
- Su propia extracción (`extraccion/<especialista>.md`)
- `reproduccion/<producto>/ficha-producto.md` del producto destino
- `sintesis.md` (para saber qué decidieron los demás)

**Salida obligatoria:** `casos/<slug>/reproduccion/<producto>/<especialista>.md`:

```markdown
# <Especialista> — directivas de reproducción

## Decisiones
Qué decido para el producto nuevo, y por qué. Ejecutable, no teórico.

## Directivas
Instrucciones concretas para quien construye.
Formato: `D-<esp>-<n>: <instrucción>`

## Descartes
Qué del original decido NO reproducir, y por qué no aplica aquí.

## Faltantes
`[FALTA: <dato>]` por cada cosa que necesito y la ficha no tiene.
NUNCA se inventa un dato faltante.

## Conflictos
Dónde mi criterio choca con el de otro especialista. Lo resuelve el orquestador.
```

**Reglas de reproducción, iguales para todos:**

1. **Dato que falta se declara, no se inventa.** Es la regla más importante del sistema.
2. **Declarar conflictos, no resolverlos.** Un especialista no negocia con otro; escala.
3. **Nada literal del original.** Se aplica el barrido de contaminación del paso 6 de `orquestador/reproducir.md`.
4. **Directiva ejecutable.** "Mejorar la jerarquía" no vale. "H1 a 56px, H2 a 32px, sin pesos intermedios" sí.

---

## Resolución de conflictos

Cuando dos especialistas chocan, manda esta prelación:

| Prioridad | Especialista | Manda en |
|---|---|---|
| 1 | `mercadologo` | Posicionamiento, avatar, nivel de consciencia |
| 2 | `administrador` | Precio, oferta, modelo de monetización |
| 3 | `copywriter` | Argumento y jerarquía del mensaje |
| 4 | `neuromarketing` | Atención y carga cognitiva |
| 5 | `disenador` | Sistema visual |
| 6 | `frontend` | Implementación |
| — | resto | Asesoran; no deciden por sí solos |

El orquestador aplica esta escala cuando dos criterios chocan.

---

## Roster y fronteras

| Especialista | Ve | No ve (lo remite a) |
|---|---|---|
| `frontend` | DOM, CSS, layout, responsive, componentes, stack | Estética → `disenador` |
| `disenador` | Paleta, tipografía, espaciado, género visual, arte | Código → `frontend` |
| `neuromarketing` | Saliencia, atención, carga cognitiva, sesgos medibles | Motivación profunda → `psicologo` |
| `psicologo` | Motivación, emoción, identidad, resistencias | Atención visual → `neuromarketing` |
| `linguista` | Registro, sintaxis, ritmo, campo semántico, legibilidad | Persuasión → `copywriter` |
| `copywriter` | Fórmulas, titulares, argumento, framework | Cómo está escrito → `linguista` |
| `mercadologo` | Posicionamiento, avatar, consciencia, sofisticación | Precio → `administrador` |
| `sociologo` | Códigos culturales, clase, pertenencia, estatus | Psique individual → `psicologo` |
| `ingeniero-industrial` | El funnel como proceso: pasos, fricción, cuellos | Persuasión → `copywriter` |
| `administrador` | Modelo de negocio, precio, oferta, monetización | Mensaje → `mercadologo` |
| `growth-data` | Píxeles, tests, tracking, infraestructura oculta | Interpretación → `mercadologo` |
