# Orquestador de reproducción

Coge un super-skill de `casos/<slug>/` y lo convierte en una web para otro producto.

## Paso 1 — Ficha del producto

Leer `sintesis.md` §Preguntas al producto destino y pedirlas **en un solo mensaje agrupado**.

Mínimos innegociables, en dos bloques. **Los dos se preguntan en el paso 1, no después.**

**Negocio:** qué es, avatar concreto, dolor, promesa, mecanismo único, oferta con precio, **prueba disponible**, objeciones reales.

**Identidad visual.** Se pregunta aquí, nunca después.

**Preguntar por los colores no es opcional y se olvida siempre.** Si no se preguntan, `disenador` se inventa una paleta en la ola 2 y la declara como faltante — pero para entonces las once directivas ya se escribieron sobre esos valores, y cambiarlos después obliga a rehacer la mitad. Es la pregunta más barata del cuestionario y la que más caro sale saltarse.

### Cómo preguntarlo

**El usuario no es diseñador.** Preguntarle por su paleta, su escala tipográfica o si quiere tema claro u oscuro no obtiene respuesta útil: obtiene un "no sé" o un color elegido al azar. Hay que preguntar por lo que sí sabe, y explicar para qué sirve cada respuesta.

Estas cuatro, con su porqué delante:

1. **«¿Tienes logo o colores de marca ya definidos? Si tienes el logo a mano, pásamelo.»**
   Si los hay, se respetan. Si no, se elige y se dice claramente que se está eligiendo.

2. **«Enséñame dos o tres webs que te gusten, de cualquier sector.»**
   Es la pregunta que más rinde y la única que cualquiera puede contestar. De dos referencias se deduce el género visual, la temperatura y el nivel de sobriedad mejor que de cualquier descripción.

3. **«¿Cómo quieres que se sienta quien entre: en algo serio y formal, o en algo cercano y accesible?»**
   Traduce a tono visual sin usar una sola palabra técnica.

4. **«¿Hay algún color que no quieras ver, por lo que sea?»**
   Caza vetos —el color de un competidor, uno con mala connotación en su mercado— que aparecerían tarde y caros.

**Si no tiene nada de esto, también vale.** Se anota que no hay identidad previa y `disenador` propone una. Pero entonces es una decisión consciente y avisada, no un descuido: hay que decirle al usuario **«voy a elegir yo los colores, y cambiarlos luego cuesta rehacer parte del trabajo»** antes de seguir.

### Si el destino tiene más de una marca o producto, preguntar la arquitectura antes de repartir

Cuando la ficha revela **dos o más marcas, productos o audiencias** (una casa con sub-marcas, un B2B con una comunidad B2C al lado, dos ofertas con avatar distinto), hay una decisión que condiciona todo lo demás y que no puede tomarla el sistema solo:

**«¿Quieres webs separadas, una por marca, o una sola web que las reúna?»**

Se pregunta **aquí, en el paso 1**, no después de construir. Descubrirlo tarde obliga a rehacer fichas, planes y builds enteros, porque las dos opciones no comparten estructura:

| Opción | Qué produce | Consecuencia estructural |
|---|---|---|
| **Separadas** | Un `reproduccion/<producto>/` por marca | Cada web optimiza para su avatar, su consciencia y su conversión. Es lo mejor para convertir; cuesta mantener N webs |
| **Unificada** | Un `reproduccion/<producto>/` adicional para la web conjunta | La página necesita **arquitectura de enrutado**: un hero de casa que bifurca temprano hacia cada audiencia, y una **zona por marca** con su propio acento, tono y CTA. Las audiencias no se mezclan en un mismo bloque |

Reglas para la variante unificada:

- **Bifurcar temprano.** Dos avatares distintos no leen la misma página entera: el hero de la casa presenta la familia y enruta en el primer scroll. Cada zona funciona después como una mini-landing con su propio CTA.
- **Cada marca conserva su identidad dentro de su zona** — su acento, su registro y su conversión — y no se mezclan en un mismo lockup o bloque. Si el manual de marca del destino ya define esta separación, se respeta tal cual.
- **Las fichas y directivas por marca no se tiran:** la web unificada las consume. Lo que se añade es la decisión de arquitectura (orden de zonas, cuál domina, hero de casa) y su propia carpeta de producto.
- **Si los avatares son muy incompatibles** (ticket, consciencia y tono opuestos), avisar al usuario de que la unificada convierte peor que dos webs dedicadas, y dejar que decida informado.

### Los materiales visuales se piden aquí, no al final

Junto a la identidad, **hay que pedir los archivos**. No basta con saber que existen: hay que tenerlos, o saber cuántos hay y en qué estado.

- **El logo**, en el mejor formato que tenga. Con SVG o PNG grande se coloca de verdad; con una captura pequeña, se hace un wordmark tipográfico y se dice que es provisional.
- **Las capturas y fotos que sirven de prueba.** Cuántas hay, si se leen bien, si hay que tapar datos personales. El número decide si el bloque es una rejilla de ocho o una pieza única destacada.
- **Los testimonios tal cual están.** Capturas de conversación, audios, textos. Si son de mensajería, si traen foto de perfil.
- **Fotos del equipo, del local o del proceso**, si las hay.
- **Vídeo**, si lo hay. Casi nunca lo hay, y el funnel de origen suele apoyarse en él.

**Por qué aquí y no al construir.** El material visual no es decoración: decide la estructura. Un bloque de prueba con ocho capturas es una rejilla; con una, es una pieza a pantalla grande con su historia al lado; con ninguna, ese bloque no existe y hay que reordenar la página entera. `disenador` no puede dirigir el arte de algo que no sabe si existe, y descubrirlo en el paso 5 significa rehacer bloques ya escritos.

**Regla:** si el usuario dice que tiene material pero no lo entrega, se anota `[FALTA]` y se construye con hueco visible. **Nunca se rellena con fotografía de banco ni con imágenes generadas:** en una página cuya credibilidad se apoya en resultados reales, una foto de stock la destruye.

Guardar en `casos/<slug>/reproduccion/<producto>/ficha-producto.md`.

`<producto>` es un nombre corto en minúsculas. **Un mismo origen sirve a varios productos:** lo que está por encima de `reproduccion/` —`SKILL.md`, `sintesis.md`, `extraccion/`— se extrajo una vez y se comparte; cada producto solo aporta su ficha y consume el resto.

**Si falta la prueba disponible, insistir.** Es el campo que más condiciona la estructura: un producto sin testimonios no puede llevar el mismo esqueleto que uno con doscientos.

## Paso 2 — Auditoría de compatibilidad

**No se salta.** Repartir sin auditar produce una web que copia una estructura pensada para otro avatar. Comparar origen y destino en estos ocho ejes:

| Eje | Si no coincide |
|---|---|
| **Nivel de consciencia** (inconsciente → el más consciente) | Cambia el punto de entrada. Más consciente exige menos educación y CTA temprano; menos consciente exige empezar por el problema |
| **Sofisticación del mercado** (etapas 1-5 de Schwartz) | Si el origen está en etapa 2 y tu mercado en etapa 4, su titular directo te hunde: ahí ya no gana la promesa, gana el mecanismo |
| **Ticket** | 27 € y 5.000 € no comparten estructura. El segundo termina en llamada, no en checkout |
| **Tipo de compra** (impulso vs considerada) | Cambia longitud, densidad de prueba y objeciones a tratar |
| **Ciclo de decisión** (minutos vs semanas, único vs comité) | Ciclo largo exige captura de contacto, no venta directa |
| **Modelo de entrega** | Afecta a garantía, urgencia y expectativas |
| **Riesgo percibido** | A más riesgo, más inversión de riesgo y más prueba antes del CTA |

**El de sofisticación es el que más caro sale ignorar.** Copiar la estructura de un funnel que operaba en otra etapa produce algo que se ve bien y no convierte.

Determinar también el **grado de transposición**:

| Grado | Cuándo | Qué transfiere |
|---|---|---|
| 1 — Directa | Mismo nicho, mismo avatar, ticket similar | Casi todo |
| 2 — Adyacente | Nicho vecino o avatar desplazado | Esqueleto y mecanismos; se recalibran prueba, tono y densidad |
| 3 — Lejana | Otro sector, otro ticket, otro tipo de compra | Solo el esqueleto abstracto. Copy, prueba, ritmo y visual se rehacen |

**Si sale grado 3, avisar al usuario:** lo que se reutiliza es una plantilla de razonamiento, no una web. Quien esperaba un clon debe saberlo.

Salida en `casos/<slug>/reproduccion/<producto>/compatibilidad.md`: lista de desajustes con su consecuencia estructural, más el grado.

## Paso 3 — Repartir, en tres olas

**Reproducir no es paralelo.** Unas decisiones condicionan a otras; los once a la vez producen once decisiones incompatibles.

| Ola | Especialistas | Fija |
|---|---|---|
| 1 | `mercadologo`, `administrador` | Avatar, consciencia, sofisticación, precio |
| 2 | `psicologo`, `sociologo`, `ingeniero-industrial`, `disenador`, `linguista`, `frontend`, `growth-data`, `neuromarketing` | Su capa, con la ola 1 cerrada |
| 3 | `copywriter` | Escribe con todo lo anterior decidido |

Dentro de cada ola sí van en paralelo. Entre olas se espera.

Encargo:

```
Eres el especialista <esp>. Modo REPRODUCIR.
Lee CONTRATO.md, especialistas/<esp>/extraer.md
y especialistas/<esp>/reproducir.md, y ejecuta ese protocolo.
Entrada: casos/<slug>/extraccion/<esp>.md, reproduccion/<producto>/ficha-producto.md,
sintesis.md, reproduccion/<producto>/compatibilidad.md y las salidas de olas anteriores.
Pasa tu autoverificación antes de dar por buena la salida.
Escribe en casos/<slug>/reproduccion/<producto>/<esp>.md y no toques nada más.
```

**Si la ola 1 levanta un conflicto, se para ahí.** Es mucho más barato que dejar a los otros nueve construir sobre una premisa equivocada.

## Paso 4 — Resolver conflictos

1. **Faltantes:** juntar todos los `[FALTA: …]`. Si alguno es crítico, parar y preguntar antes de construir.
2. **Conflictos:** aplicar la prelación de `CONTRATO.md`. Aplicar la escala; el que manda en esa materia decide.
3. **Directivas:** consolidar todas las `D-*` en un plan único, ordenado por bloque.

Salida: `reproduccion/<producto>/plan.md`.

## Paso 5 — Construir  ·  **opcional, y no es el final por defecto**

**El entregable por defecto es `plan.md`, no la página.** Se para en el paso 4 salvo que el usuario pida explícitamente el build.

Por qué: el plan es lo que se revisa, se discute y se corrige barato. El HTML es una consecuencia mecánica de él. Montarlo antes de que el usuario valide la promesa, el precio y el copy es ponerse a pintar antes de decidir qué se dice.

Preguntar al cerrar el paso 4, no antes. Si el usuario lo pide:

`reproduccion/<producto>/build.html`: HTML autocontenido, sin dependencias externas, responsive, con el sistema visual de `disenador` y la estructura del plan.

## Paso 6a — Verificar que se ve

**Antes del barrido de contaminación, hay que mirar la página.** Un build que cumple todas las directivas sobre el papel puede verse roto, y eso no lo detecta ningún grep.

```bash
python tools/render.py casos/<slug>/reproduccion/<producto>/build.html
```

Deja dos capturas en la misma carpeta: escritorio a 1440 y móvil a 390. Se revisan las dos:

- [ ] **Móvil:** nada se desborda, las rejillas apilan, la tipografía baja de escala, los botones se pueden pulsar con el pulgar
- [ ] **Escritorio:** el contenido está centrado y no se estira a todo el ancho de la pantalla
- [ ] La medida de lectura se mantiene en 60-70 caracteres en ambos
- [ ] El CTA se distingue a simple vista de lo que no es accionable
- [ ] Los huecos `[FALTA: …]` se ven, no se disimulan

**Se mira la captura, no se deduce del código.** Es la misma regla que en extraer: si un número contradice lo que se ve, gana lo que se ve.

## Paso 6b — Revisión del build

```
Eres el especialista programador. Modo REPRODUCIR.
Lee especialistas/programador/reproducir.md y ejecuta ese protocolo.
Entrada: SOLO casos/<slug>/reproduccion/<producto>/build.html,
plan.md y las dos capturas. Nada más.
Escribe en casos/<slug>/reproduccion/<producto>/programador.md.
```

**`programador` es el especialista número doce y no funciona como los once.** No participa en extraer —revisar el código de un original que no se va a mantener no aporta nada— ni en las tres olas, porque cuando corren todavía no hay build. Se lanza aquí, una vez, y **solo con el build y el plan**: las once directivas ya vienen consolidadas y volver a pasarlas sueltas multiplica el prompt sin añadir nada.

Es el encargo más barato del sistema. Por eso se puede repetir después de cada corrección sin pensárselo, que es justo lo que lo hace útil.

**Lo que revisa, por orden:** composición —lo que más se cuela y lo único que exige mirar la captura—, directivas cumplidas, lo que se rompe en silencio, y que los huecos declarados sigan visibles.

Sus `D-programador-*` se aplican al build y se vuelve a lanzar. Cuando devuelva cero hallazgos graves, se pasa al barrido.

## Paso 6 — Barrido de contaminación

Contra el build y contra la lista `CT-*` de la síntesis. Cualquier coincidencia se corrige **antes** de entregar.

- [ ] Ninguna frase literal del original
- [ ] Ningún nombre de marca, producto o persona del original
- [ ] Ninguna cifra que no pertenezca al producto destino
- [ ] Ningún testimonio, logo ni credencial ajena
- [ ] Ninguna jerga del nicho origen que no exista en el destino
- [ ] Ninguna promesa que el producto no pueda cumplir
- [ ] Ninguna garantía copiada que el negocio no vaya a honrar
- [ ] Ninguna urgencia heredada sin motivo real
- [ ] Ninguna objeción que el avatar destino no tenga
- [ ] Ningún asset del original
- [ ] Ningún bloque de prueba vacío ni con placeholder

**La contaminación peligrosa es la que suena bien:** una frase heredada que encaja y describe un beneficio plausible pasa la revisión y acaba prometiendo algo que el producto no hace.

## Paso 7 — Entregar

Criterios de aceptación:

| Criterio | Umbral |
|---|---|
| Similitud estructural con el plan | ≥ 0.80 |
| Contaminación detectada | 0 |
| Parámetros sin dato | 0 sin declarar |
| Afirmaciones sin respaldo en la ficha | 0 |

Al usuario: dónde está el build, el grado de transposición y por qué, los ajustes que obligó la auditoría, los `[FALTA: …]` sin resolver.

## Paso 8 — Producción  ·  **solo si el usuario pide web real, no mockup**

Cuando el entregable deja de ser `build.html` y pasa a ser una aplicación desplegada, entran los tres equipos de `especialistas/EQUIPOS.md`. **Ninguno reabre lo decidido por el funnel**; lo llevan a producción.

Orden de disparo:

1. **Cuestionarios primero** — `arquitecto-angular` (infraestructura, framework, despliegue) y `search-console` (propiedad, dominio, accesos) preguntan ANTES de que nadie trabaje. Misma lógica que la ficha del paso 1: descubrirlo tarde cuesta rehacer.
2. **Adquisición** — `keywords` → (`seo-tecnico` ∥ `geo` ∥ `meta-snippets`). Keywords va primero porque los otros tres consumen su mapa.
3. **Ingeniería** — `arquitecto-angular` genera el workspace consumiendo `plan.md` + directivas de adquisición; `performance` fija presupuestos que el CI hace cumplir; `ab-testing` deja el backlog de experimentos (no corre tests sin tráfico).
4. **Operaciones** — `devops` (pipeline), `devsecops` (compuertas de seguridad), `gobernanza` (PRs, Boards). Los `[FALTA]` del plan se cargan como work items: son el backlog real.
5. **Ciclo continuo** — con la web desplegada, `search-console` alimenta de datos a keywords, meta-snippets y performance cada mes. Es el único paso que no termina.

Las salidas `.md` de cada especialista van a `reproduccion/<producto>/`, con las cinco secciones del contrato. Los artefactos (workspace, YAML de pipeline, plantillas) van al repo, fuera de `casos/`.

## Cuándo no reproducir

Señales de que el origen es mala base, por bien que le funcione a su dueño:

- **Su ventaja no es estructural** — convierte por marca, lista de años o un coste de adquisición que tú no tienes.
- **Su urgencia o su prueba son fabricadas** — si `growth-data` detectó temporizadores que se reinician o notificaciones inventadas, su conversión no viene de la estructura: viene del engaño, y eso no se puede replicar sin replicar el engaño.
- **Opera en otra etapa de sofisticación.**
- **Su prueba es su producto** — un volumen de casos irreplicable a corto plazo.
- **Está en test activo** — si `growth-data` detectó variantes, ni su dueño lo ha validado.

En estos casos: extraer principios, descartar la estructura.
