# tools/

Las herramientas que alimentan a los especialistas. **Nada que un parser pueda medir se le pregunta a un modelo.**

Un parser te dice que el acento es `#E4572E` con certeza absoluta y que ocupa el 2,1% de la superficie. Un modelo de visión te dirá "naranja terracota" y a veces fallará el tono. Al modelo se le pregunta lo que el parser no puede saber: por qué está ahí ese naranja y a quién le habla ese titular.

---

## Instalación

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows;  source .venv/bin/activate en Unix
pip install -r tools/requirements.txt
playwright install chromium
```

---

## Uso

```bash
python tools/run.py extraer https://ejemplo.com/oferta   # todo de una
python tools/run.py estado <slug>                        # qué falta
python tools/run.py plan <slug> --modo reproducir        # el reparto en olas
python tools/run.py indice                               # regenerar casos/README.md
```

O por piezas, si quieres control fino:

```bash
python tools/capture.py https://ejemplo.com/oferta
python -m tools.analyze <slug>
```

Después de eso, `casos/<slug>/raw/analysis/` tiene cinco JSON de hechos y los especialistas ya pueden leerlos.

---

## run.py — el orquestador

**La orquestación tiene dos mitades y solo una es código.**

| Mitad | Qué hace | Dónde vive |
|---|---|---|
| **Determinista** | Capturar, medir, montar carpetas, imprimir quién hace qué | `tools/run.py` |
| **Dirigida por modelo** | Leer, interpretar, resolver conflictos, escribir | `orquestador/extraer.md` y `reproducir-funnel/SKILL.md` |

`run.py extraer` deja el caso listo y te imprime los 11 encargos, con la tool de cada especialista ya resuelta desde su frontmatter. La segunda mitad la ejecuta el agente que lea el SKILL.md.

`run.py estado <slug>` te dice qué falta: qué análisis se generaron, qué extracciones existen, si hay síntesis, ficha y build.

`run.py indice` regenera `casos/README.md`, la tabla que liga cada URL de `funnels.txt` con su carpeta y su fase. Corre sola al final de cada `extraer`, así que rara vez hace falta invocarla a mano. **El emparejamiento se hace por la URL de `raw/captura.json`, no por el nombre de la carpeta** — el slug sigue siendo el dominio sin TLD que define `CONTRATO.md`. Un caso analizado con la URL suelta, sin pasar por la cola, aparece igualmente pero con `—` en la columna del número.

---

## deepseek.py — ejecutar los encargos sin agentes

`run.py` imprime los 11 encargos; esto los ejecuta. Misma mitad determinista, pero en vez de dejar el trabajo a un agente lo manda a la API de DeepSeek y escribe las salidas en disco.

```bash
python tools/deepseek.py extraer <slug>                        # los 11
python tools/deepseek.py extraer <slug> --solo frontend,disenador
python tools/deepseek.py extraer <slug> --excepto growth-data
python tools/deepseek.py extraer <slug> --modelo deepseek-v4-flash --workers 5
python tools/deepseek.py extraer <slug> --dry-run              # imprime el prompt y sale

python tools/deepseek.py reproducir <slug>                     # las tres olas, en orden
python tools/deepseek.py reproducir <slug> --ola 2             # reintenta una suelta
```

**Extraer es paralelo; reproducir va en olas.** El subcomando `reproducir` respeta el orden del contrato: primero `mercadologo` y `administrador`, después los ocho de la ola 2, y `copywriter` el último. Dentro de cada ola sí van a la vez; entre olas se espera. Si una ola falla, se para ahí: una ola incompleta condiciona a todas las siguientes.

Necesita `ficha-producto.md` —el paso 1 de `orquestador/reproducir.md`— y avisa si falta `reproduccion/compatibilidad.md`.

**A las olas posteriores solo se les pasan las secciones `Decisiones` y `Directivas` de las anteriores**, no el documento entero. Descartes, Faltantes y Conflictos son material del orquestador: quien construye encima necesita saber *qué* se decidió, no cómo razonó cada especialista para decidirlo. Con el documento completo, el prompt de la ola 3 llegaba a 58K tokens y el modelo se quedaba sin sitio para responder.

La clave se lee de `DEEPSEEK_API_KEY`, como variable de entorno o desde el `.env` de la raíz. Sin dependencias nuevas: usa `urllib` de la librería estándar.

**Por qué material curado y no `raw/` entero.** `elements.json` son 156K y `page.html` 108K: no caben junto al contrato y el protocolo en ninguna ventana asumible. Lo que se manda son los cinco JSON de `raw/analysis/`, `captura.json`, el texto plano de la página en orden de lectura y un bloque de hechos del DOM contados por el propio script — colores, gradientes, radios, conteo de etiquetas, media queries. Unos 7K tokens de material, 10K de prompt total.

**El bloque `diagnostico_de_cableado` merece explicación.** Los conteos crudos no se interpretan solos: en la primera pasada de este caso, diez de los once especialistas pasaron por alto que la página tenía ocho `<button>` y cero enlaces, formularios o handlers, y uno llegó a leerlo como un diseño deliberado de un solo paso. El script ahora deriva el hecho y lo nombra con una advertencia explícita en vez de dejar los números sueltos. **Es la regla general al añadir hechos al prompt: si un conteo admite una lectura equivocada, hay que derivar la conclusión, no confiar en que el modelo la saque.**

**Verifica siempre lo que devuelva.** En este caso las salidas fueron sólidas en estructura y casi siempre exactas en los números, pero hubo tres inferencias no observables, dos frases literales del original coladas en la sección de patrones, y un especialista que construyó un hallazgo sobre un artefacto de parser sin contrastarlo con la captura. Nada de eso lo detecta el script. Un barrido útil, y barato:

```bash
# ¿cumplen las cinco secciones y los prefijos?
grep -c "^## [1-5]\." casos/<slug>/extraccion/*.md
# ¿se coló texto literal del original en Patrones transferibles?
# ¿afirman cosas que el raw no contiene?
```

---

## verificar.py — el contrato, comprobado

```bash
python tools/verificar.py <slug>                 # los 11
python tools/verificar.py <slug> --detalle       # con cada incidencia
python tools/verificar.py <slug> --modo reproducir
```

Comprueba lo que sí es comprobable: que estén las cinco secciones y tengan contenido, que los identificadores existan y sean localizables, que no se haya colado el texto instructivo del contrato, que no haya frases literales del original donde el contrato exige patrón, y que las cifras afirmadas estén en el material. Sale con código 1 si hay algo grave.

**Es un informe, no una aduana.** Solo son graves las cosas que rompen el contrato de verdad. Numeración con huecos, guiones tipográficos, cifras derivadas por el propio modelo o citas desactualizadas se reportan y se sigue: perseguir la salida perfecta cuesta más de lo que vale.

Tres decisiones de diseño que lo mantienen general:

- **Los patrones de eco se derivan de `CONTRATO.md`**, leyendo las líneas descriptivas de su plantilla. Si el contrato cambia, la comprobación cambia sola. Una lista escrita a mano solo habría servido para su idioma.
- **Las frases literales se detectan por n-gramas** contra el texto capturado del caso, no contra un diccionario.
- **El material se pide a `deepseek.material()`**, para comprobar contra exactamente lo que vio el especialista. Mirando menos, acusaba de inventar cifras que sí tenía delante.

Lo que exige entender el texto —si un hallazgo invade otra disciplina, si un patrón transfiere de verdad— no se comprueba aquí. Eso es criterio.

---

## grafico.py — datos de gráfico para el blog, sin inventar cifras

No dibuja nada: eso lo hace `ui-grafico`
(`web/src/app/ui/molecules/grafico.ts`), un componente Angular interactivo
(hover/click/teclado, estilo editorial McKinsey/Gartner — una sola tinta de
acento en rampa monocromática, nunca colores nuevos fuera de los tokens de
marca). Este script resuelve solo la parte tediosa: llegar al JSON exacto que
`DatosGrafico` espera.

**Dos modos:**

```bash
# Investiga: busca en la web datos recientes sobre un tema
python tools/grafico.py --tema "abandono de proyectos de IA"
python tools/grafico.py --tema "adopcion de agentes de IA en empresas" --tipo dona --n 8

# Extrae: ya tienes el texto/tabla con los números
python tools/grafico.py texto-con-datos.txt
python tools/grafico.py texto-con-datos.txt --out casos/grafico-x.json
echo "..." | python tools/grafico.py -
```

**Modo `--tema` (el agente de investigación).** Busca en DuckDuckGo (HTML
público, sin API key — POST al formulario real de `/html/`, GET solo dispara
su reto anti-bot) y le pide a DeepSeek que extraiga cifras SOLO de los
fragmentos devueltos, nunca de su conocimiento previo. `fuente` en la salida
lleva la URL exacta del resultado usado, así el dato es verificable. Si dos
resultados chocan, no promedia: usa el más reciente/autorial y explica la
discrepancia en `nota`, o declara el error si no puede decidir.

**Misma regla dura que el resto del sistema, en ambos modos:** si no hay una
cifra explícita y reciente respaldada por una URL o un texto citado, el
script lo declara — nunca redondea, estima ni pone una fuente genérica. Sin
dato numérico responde `{"error": "..."}`; sin fuente citable (modo texto),
`fuente` queda como `"[FALTA: fuente no citada en el texto]"` y el script
sale con código 1 para que no se publique por accidente.

El JSON resultante se pega a mano en `graficos` del post en
`web/src/app/data/blog.data.ts`, con un id, y ese mismo id se marca en el
`contenidoHtml` como `<!--grafico:ese-id-->` en el punto donde debe aparecer.
Pegarlo a mano — no automático — es a propósito: sigue habiendo un humano que
lee la fuente antes de publicarla, misma disciplina de `verificar.py` con el
resto del sistema.

---

## capture.py

Una sola pasada de Playwright. Produce:

| Archivo | Qué es |
|---|---|
| `page.html` | HTML renderizado, después de aceptar cookies |
| `elements.json` | **El artefacto clave.** Caja y estilos computados de cada elemento visible, más formularios, enlaces, encabezados y botones |
| `full.png` · `viewport.png` · `mobile.png` | Capturas a 1440×900 y 390×844 |
| `viewport-precookies.png` | Antes de tocar el banner: así lo ve el visitante real |
| `styles.css` | Hojas de estilo accesibles |
| `network.json` | Peticiones, cookies, localStorage y sessionStorage |
| `estados/` | Overlays, popups, pasos siguientes del funnel, pasadas extra para A/B |
| `captura.json` | Resumen: banner, pasos seguidos, señal de A/B |

**Opciones:**

```
--depth N          pasos internos a seguir (0 = solo la landing, por defecto 1)
--passes N         pasadas con sesión limpia para detectar A/B (por defecto 3)
--slug NOMBRE      carpeta destino
--lote archivo.txt una URL por línea
--submit-optin     rellena y envía el formulario  ← requiere permiso explícito
--email X          correo a usar en el opt-in
```

**El opt-in está apagado por defecto** porque envía datos a un sistema ajeno. Pero sin pasarlo te quedas en la landing, y ahí se pierde lo que más vale: `ingeniero-industrial` no puede medir el proceso, `administrador` no ve el precio real y `growth-data` no ve los píxeles de conversión, que solo disparan al enviar.

**Decisiones que toma solo:** locale `es-419`, zona horaria LATAM, captura el banner de cookies antes y después de aceptar (muchos píxeles no cargan hasta el consentimiento), hace scroll completo para disparar lazy-load y animaciones de entrada, y provoca exit-intent para cazar popups.

---

## analyze/

Python puro, sin navegador. Leen `raw/` y escriben `raw/analysis/*.json`.

| Módulo | Escribe | Alimenta a | Qué mide |
|---|---|---|---|
| `design.py` | `design.json` | `disenador` | Paleta por superficie ocupada, acento en accionables, escala tipográfica con su razón, jerarquía real, unidad de espaciado, radios, sombras, **veredicto de consistencia** |
| `attention.py` | `attention.json` | `neuromarketing` | Saliencia del CTA en delta-E y contraste WCAG, **competencia de atención**, above-the-fold, ley de Hick, ancho de medida en caracteres |
| `text.py` | `text.json` | `linguista`, `copywriter` | Longitud media de frase y desviación, densidad léxica, campo semántico, persona gramatical, titular con su métrica, microcopy |
| `flow.py` | `flow.json` | `ingeniero-industrial`, `frontend` | Esqueleto de secciones, layout y breakpoints, formularios con su fricción, decisiones por pantalla, salidas del camino crítico |
| `trackers.py` | `trackers.json` | `growth-data`, `administrador` | Píxeles, analítica, grabación de sesión, tests A/B, pasarelas, CRM, campos ocultos, cookies, **temporizadores fabricados** |

Cada uno corre suelto si solo quieres una lectura:

```bash
python -m tools.analyze.trackers <slug>
```

---

## Los tres análisis que más valen

**`trackers.json` es el de mejor relación valor/esfuerzo de todo el sistema.** No usa modelo, no necesita screenshots, y por sí solo responde en qué plataformas compra tráfico el competidor, si está optimizando activamente (grabación de sesión y tests A/B presentes), qué pasarela y qué CRM usa, y qué captura en sus campos ocultos — que es su estrategia de segmentación escrita en el HTML.

**La competencia de atención de `attention.json`.** No basta con que el CTA sea llamativo: si hay otros seis elementos igual de salientes sobre el pliegue, la atención se reparte y no gana ninguno. Se mide, casi nadie lo mide, y sale gratis.

**El veredicto de consistencia de `design.json`.** Si una web usa once tamaños de texto distintos, no tiene escala tipográfica: tiene improvisación. Saberlo evita que la reproducción invente un rigor sistemático que el original nunca tuvo.

---

## Reglas para quien añada o arregle tools

**1. Un analizador nuevo solo se justifica si mide algo que hoy le estamos preguntando a un modelo.** Si el dato ya está en un JSON y el especialista sigue adivinándolo, el problema no es que falte una tool: es que falta conectarla en su `SKILL.md`.

**2. Un parser mide lo que es igual en cualquier página; lo que exige entender el texto es del modelo.**

Estructura, conteos, geometría, color y relaciones entre elementos son iguales en una landing de infoproducto en español y en una de SaaS B2B en alemán. El *significado* de un bloque no. En cuanto un analizador necesita una lista de palabras clave para decidir algo, ha dejado de medir y ha empezado a memorizar el documento que tenía delante quien lo escribió.

Pasó aquí: el clasificador de secciones de `flow.py` se escribió con las frases de una página concreta y devolvió `precio` en 7 de 14 bloques, porque el importe aparecía en todos sus CTA. Se sustituyó por rasgos contables — encabezados, accionables, campos, vídeos, imágenes, palabras, rejilla, cifras destacadas — y ahora el especialista nombra el bloque con ellos.

**3. Mejor `null` que una etiqueta inventada.** Un campo vacío se ve y se pregunta. Uno relleno con una suposición se cree. `tipo_declarado` solo se rellena si el marcado lo declara.

**4. Si un conteo admite una lectura equivocada, no basta con dar mejor el número: hay que derivar la conclusión.** Diez de once especialistas pasaron por alto que una página tenía ocho botones y cero destinos, porque el dato estaba en forma de conteo crudo. Uno llegó a leerlo como diseño deliberado. Los hechos que se prestan a error se nombran, no se dejan sueltos.

**5. Antes de dar un JSON por bueno, contrástalo con la captura.** `raw/analysis/*.json` se presenta como medición y por eso nadie lo cuestiona: un parser que miente no produce un error, produce un error con autoridad. Dos ejemplos reales del mismo caso, ambos por leer `background-color` e ignorar `background-image`: `attention.json` dijo que no había ningún CTA en una página con ocho, y `design.json` dio el 86 % de la superficie a `#FFFFFF` en una página negra.

**6. Arregla la raíz, no el síntoma.** Esos dos fallos eran el mismo bug. Se resolvió con una función en `_common.py` que sirve a los cinco analizadores, no con dos parches.

**7. Un caso ya extraído no se parchea a mano.** Sus archivos son la foto que sacaron las herramientas de entonces. Si la mejora cambia lo que habrían dicho, se vuelve a extraer: editar la prosa deja el caso descuadrado con su propio `raw/`.
