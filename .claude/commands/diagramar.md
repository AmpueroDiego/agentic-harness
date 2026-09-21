---
description: Genera diagramas .drawio a partir de una especificación JSON, con layout calculado y validación anti-solapamientos. También audita los .drawio existentes.
---

# /diagramar

Produce diagramas `.drawio` para `AcmeOrg/` sin escribir coordenadas a mano.

**Regla dura: está prohibido escribir XML de draw.io a mano.** Ya se hizo una vez
(2026-09-09) y salieron 7 solapamientos en 3 páginas: etiquetas de flecha encima
de cajas ajenas y flechas atravesando nodos. El XML lo emite `generar.py`; el ojo
humano no mide texto y yo tampoco.

## Herramientas

Viven en `.claude/tools/drawio/`, todas Python 3 sin dependencias externas:

| Archivo | Qué hace |
|---|---|
| `metricas.py` | Mide y envuelve texto en Helvetica. Sobreestima a propósito. |
| `generar.py` | `spec.json` → `.drawio`. Calcula toda la geometría. |
| `secuencia.py` | Páginas `"tipo": "secuencia"`: lo llama `generar.py`, no se usa suelto. |
| `validar.py` | Audita cualquier `.drawio` y reporta lo que se pisa. |
| `previsualizar.py` | Renderiza el `.drawio` a **SVG** para poder mirarlo sin draw.io. |

## El ciclo, siempre en este orden

```bash
cd .claude/tools/drawio
python generar.py  ../../../contexto-negocio/diagramas/<nombre>/<nombre>.diagrama.json
python validar.py  ../../../contexto-negocio/diagramas/<nombre>/<nombre>.drawio
python previsualizar.py ../../../contexto-negocio/diagramas/<nombre>/<nombre>.drawio
#   -> escribe los SVG en la misma carpeta del .drawio, sin pasarle -o
```

1. Escribir/editar el `.diagrama.json` (la fuente de verdad).

   **Borrador delegado para un diagrama parecido a uno existente** *(agregado 2026-09-18, ver [`/shunt`](shunt.md))*: en vez de escribir el JSON a mano desde cero, `code-write.sh --reference <existente>.diagrama.json --target <nuevo>.diagrama.json --spec "<participantes/nodos/pasos/conexiones>"`. El `--spec` tiene que traer las decisiones de contenido reales — quién decide qué muestra el diagrama seguís siendo vos, `agy` solo lo codifica en el schema. Los pasos 2-6 de abajo siguen obligatorios sin cambios: ahí está la verificación real, no en este script.
2. `generar.py`.
3. `validar.py`. **Si sale distinto de `Total de errores: 0`, no se entrega.**
   Se ajusta el JSON — mover un nodo de celda, acortar una etiqueta — y se vuelve al paso 2.
4. `previsualizar.py` y **mirar el resultado**. Validar prueba que nada se pisa;
   no prueba que se entienda. Un SVG se abre en el navegador y en el teléfono.
5. **Los SVG se comitean junto al `.drawio`**, uno por página. Ver abajo.
6. Recién ahí se le pasa la ruta al usuario.

El `.diagrama.json` se comitea junto al `.drawio`: sin él, la próxima edición
vuelve a ser XML a mano.

### Los SVG se versionan, no se descartan

*(Práctica pedida por el responsable del repo, 2026-09-09.)* Cada vez que se regenera un
diagrama, los SVG de todas sus páginas se regeneran también y quedan
comiteados, con el nombre `<archivo>--<pagina>.svg`.

**Cada diagrama tiene su carpeta**, con todo lo suyo junto *(el responsable del repo,
2026-09-10; hasta ese día los SVG iban en un `svg/` aparte)*:

```
contexto-negocio/diagramas/<nombre>/
    <nombre>.diagrama.json     la fuente — se edita
    <nombre>.drawio            generado — se abre en draw.io
    <nombre>--<pagina>.svg     uno por página — se mira, no se edita
```

`previsualizar.py` escribe en la carpeta del `.drawio` por defecto: no hace
falta pasarle `-o`, y así la convención no depende de que alguien se acuerde.
Si una página se renombra, se borran los SVG de la carpeta antes de
regenerar, para que no quede el render de una página que ya no existe.

Por qué vale la pena:

- **GitHub los renderiza solo.** El diagrama se mira desde el navegador sin
  descargar nada ni instalar draw.io.
- **Se ven en el teléfono**, y se pegan en un chat o en un doc.
- **El diff cuenta algo.** Un `.drawio` que cambió es XML ilegible; al lado, el
  SVG deja ver qué se movió.
- **Obligan a mirar.** Si el SVG se regenera en cada corrida, el resultado se
  ve — que es como aparecieron los defectos que ninguna regla detectaba.

Son un **derivado**, nunca la fuente: se regeneran, no se editan a mano. Si el
SVG y el `.drawio` discrepan, manda el `.diagrama.json`.

## Páginas de secuencia

*(Agregado 2026-09-10, para migrar los `.puml` de api-core.)* Una página con
`"tipo": "secuencia"` no usa la grilla: declara participantes y pasos en orden,
y `secuencia.py` calcula el resto — la separación entre participantes según la
etiqueta más larga que tiene que pasar entre ellos, el apilado vertical, los
marcos anidados y la numeración.

```jsonc
{
  "nombre": "3 · Envío",
  "tipo": "secuencia",
  "titulo": "Envío de WhatsApp: intento inmediato",
  "participantes": [
    {"id": "agente", "titulo": "Agente", "forma": "actor"},
    {"id": "ctrl", "titulo": "WhatsAppController", "color": "apoyo"},
    {"id": "send", "titulo": "EnviarMensaje", "lineas": ["CommandHandler"], "color": "principal"},
    {"id": "db", "titulo": "CoreDb", "forma": "cilindro", "color": "neutro"}
  ],
  "pasos": [
    "[seccion Intento inmediato]",
    "agente -> ctrl: POST /api/WhatsApp/Enviar",
    "ctrl -> send: Handle(command)",
    "send -> send: Valida y normaliza",
    "[alt Envío confirmado]",
    "send -> db: Guarda Mensaje Enviado",
    "[else WAHA rechaza]",
    "send -> db: Guarda Mensaje + Outbox",
    "[end]",
    "send --> ctrl: MensajeViewModel"
  ]
}
```

| Paso | Qué dibuja |
|---|---|
| `A -> B: texto` | Llamada: línea continua, punta llena |
| `B --> A: texto` | Respuesta: línea punteada, punta abierta |
| `A -> A: texto` | Acción propia: bucle a la derecha de la línea de vida |
| `[alt cond]` `[else cond]` `[end]` | Marco con ramas separadas por línea punteada. También `opt`, `par`, `loop`, `break`, `group` |
| `[seccion título]` | Separador a lo ancho de la lámina; solo fuera de un bloque |

Los mensajes se numeran solos (`1 · texto`). Las notas no existen, igual que en
la grilla: el contexto va en `_apuntes_no_se_dibujan`. Si una página pasa de
~35 mensajes, se parte en dos por una sección natural (el envío de WhatsApp
quedó en "intento inmediato" y "procesamiento del Outbox").

Formas de participante: `caja` (default), `cilindro`, `actor`. El `titulo`
va en una línea y el detalle en `lineas`: la caja se mide por los dos.

Tres cosas que el validador sabe de estas páginas:

- Mensajes y líneas de vida son flechas **sin caja de origen ni destino**
  (`sourcePoint`/`targetPoint`). `validar.py` y `previsualizar.py` las leen.
- El texto de cada mensaje es una celda aparte marcada `etiquetaDe=<id>`: el
  validador la trata como parte de su flecha y no la reporta como roce.
- Las líneas sin punta (`endArrow=none`: líneas de vida, separadores, `else`)
  no se revisan contra A1/A2: cruzan marcos y etiquetas a propósito.

Y un error nuevo que aplica a los dos tipos de página: **E1 recuadros que se
cruzan** sin que uno contenga al otro (marcos mal anidados, grupos que se invaden).

## Contenedores, carriles y cajas rellenas (roadmaps)

*(Agregado 2026-09-16 para el roadmap por semanas.)* Tres opciones, todas
opt-in: sin ellas, el generador sigue dibujando bandas planas y cajas blancas.

- **`"grupos_contenedores": true`** en la página (o `"contenedor": true` en un
  grupo, `false` para excluir uno) emite cada grupo como contenedor real de
  draw.io: colapsable con el `−`, y sus nodos cuelgan de él con coordenadas
  relativas, así que al mover o plegar la banda se mueve todo junto.
- **`"padre": "<id>"`** en un grupo lo vuelve un **carril** dentro de otro grupo
  (semana → Negocio / Lógica backend). El padre no tiene nodos propios: se
  dimensiona alrededor de sus carriles, y el corredor entre filas reserva su
  título y su padding. Un carril de un solo nodo sí se dibuja.
- **`"cajas_rellenas": true`** en la página pinta la caja entera con un tinte
  del acento y borde de 2px, sin barra superior; `"punteado": true` en un nodo
  la deja con borde discontinuo. Acentos de estado para esto: `hecho` (verde),
  `curso` (ámbar), `pendiente` (gris). En los grupos, `"relleno"` y
  `"titulo_color"` (hex) pisan el color de la banda y del rótulo.

Bug corregido el mismo día en `validar.py`: con dos niveles de anidación
(nodo → carril → semana) sumaba el desplazamiento del abuelo dos veces y
reportaba 47 solapamientos falsos. Ahora resuelve las coordenadas absolutas
sobre las relativas originales.

## Dos reglas que no se negocian

**1. Nada de paneles de texto al costado.** Un diagrama muestra, no explica. Un
bloque de prosa flotando junto a las cajas ("De dónde sale este diagrama", "Tres
cosas que el diagrama esconde", "Detalle de cada contenedor") no es parte del
dibujo: es una nota al pie que se coló adentro, y es lo primero que hace ver
cargada una lámina. *(Regla del responsable del repo, 2026-09-09 — antes existía una clave
`notas` en el spec; se retiró.)*

Si el contexto hace falta, va en el `.diagrama.json` bajo una clave que empiece
con **guion bajo** (`_apuntes_no_se_dibujan`), que el generador ignora, o en el
documento que cita el diagrama. `generar.py` **aborta** si encuentra `notas`.

**2. Ninguna línea pasa pegada a una estructura.** Mínimo **18px** entre
cualquier tramo de flecha y cualquier caja o marco que no sea su origen o su
destino. *(Regla del responsable del repo, 2026-09-09: una flecha pasaba lamiendo el borde del
contenedor "Microservicios satélite".)*

El corredor por sí solo no alcanzaba: el recuadro de un grupo se mete
`PAD_GRUPO` hacia adentro del corredor, y `TITULO_GRUPO` por arriba, así que un
carril calculado sólo contra la fila caía sobre el marco del contenedor. Ahora
cada corredor reserva ese borde vedado antes de repartir carriles.

Cruzar el **propio** grupo sí vale: una flecha que sale de un nodo no tiene otra
forma de salir. Lo mismo con la barra de color, que es un hijo de la caja.

## Sistema visual

La regla que gobierna todo: **el color informa, no decora.** Una caja es blanca
con borde fino gris, y su categoría se lee en una barra de 4px arriba. Pintar el
relleno entero de color es lo que hacía ver denso el diagrama viejo.

- **Cuatro acentos, no siete.** `principal` (azul profundo, lo central) ·
  `apoyo` (azul apagado, lo que rodea) · `acento` (terracota, lo que hay que
  mirar) · `neutro` (gris azulado, lo secundario). Los nombres viejos (`azul`,
  `rojo`, `verde`…) siguen funcionando: se mapean solos.
- **Dos tamaños de letra por caja:** nombre en 13px negrita sobre tinta oscura,
  detalle en 11px gris. Eso da jerarquía sin necesidad de color de relleno.
- **Una sola línea de detalle por caja.** Si una caja necesita tres líneas para
  explicarse, el diagrama está contando dos cosas a la vez: el detalle va al
  documento que cita el diagrama, nunca dentro de la lámina (regla 1).
- **Altura uniforme por fila.** Todas las cajas de una misma fila miden lo mismo,
  aunque su texto sea más corto. Alturas dispares en una línea es lo que se lee
  como "descuadrado".
- **Grupos como banda clara**, sin línea punteada: un relleno `#F6F8F9` con el
  título en versalitas grises agrupa igual y no compite con las cajas.
- **Flechas de 1px en gris**, punta fina, etiqueta en 10px gris.

## Cómo se maqueta (para entender qué mover cuando falla)

Los nodos van en una **grilla** de celdas `(col, fila)`. Entre columna y columna,
y entre fila y fila, hay un **corredor vacío**: ninguna caja se dibuja ahí, y
**toda etiqueta de flecha vive en un corredor**, en su propio carril. Por eso una
etiqueta no puede caer sobre una caja: no hay cajas donde ella vive.

El alto de cada caja sale del texto ya envuelto, así que no puede desbordar.

Cuatro modos de flecha, elegidos solos según dónde estén origen y destino:

- **horizontal** — misma fila, columnas contiguas. Etiqueta en el corredor vertical.
- **vertical** — misma columna, filas contiguas. Etiqueta en el corredor horizontal.
- **lateral** — misma columna, filas salteadas (`Abierto → Cerrado`). Sale por un
  carril al costado de la grilla para no atravesar los nodos del medio.
- **ruteada** — el resto. Baja (o sube) a un carril del corredor, viaja horizontal
  y entra al destino.

**Un grupo de uno no se dibuja.** Un recuadro alrededor de una sola caja no
agrupa nada, sólo agrega ruido. Si el nombre del grupo decía algo que importa
(*"BFF / agregador"*), va en la línea de detalle de la caja.

**Los carriles se comparten cuando los tramos no se cruzan.** Cuatro flechas
que salen del mismo nodo hacia lados opuestos nunca se tocan; darle a cada una
su propia altura estiraba el corredor sin razón. Es coloreo de intervalos sobre
el rango horizontal de cada tramo, etiqueta incluida. Por eso las `x` se
resuelven **antes** que las `y`.

**El corredor de arriba aloja el título de la página Y el borde del primer
grupo.** Si no, la etiqueta del grupo cae justo debajo del título y se leen
encimadas — pasó, y el validador no lo veía porque excluía las celdas de texto.
Ahora las mide por su texto, no por su ancho declarado.

**Los puntos de anclaje se reparten por borde, mezclando salidas y entradas en la
misma serie, ordenados según dónde está el otro extremo.** *(El orden se agregó el
2026-09-10: en el orden del spec, una flecha hacia la izquierda podía salir por la
derecha y cruzar a sus vecinas; en el diagrama de contenedores bajó los cruces de
13 a 9.)* Calcularlos por separado fue un bug real (2026-09-09): las salidas
caían en 0.2/0.4/0.6/0.8 y las entradas en 0.333/0.667, y sobre una caja de 280px
el 0.4 y el 0.333 quedan a 19px — se leen como el mismo punto. Un borde, una sola
serie.

Si el borde es demasiado corto para separarlas (un actor mide 40px), se hace lo
contrario: **todas salen del centro y abren en abanico**, que se lee como
intencional en vez de como un error de dibujo.

## Formato del `.diagrama.json`

```jsonc
{
  "archivo": "salida.drawio",          // relativo a la carpeta del spec
  "paginas": [{
    "nombre": "1 · Contenedores",      // nombre de la pestaña
    "titulo": "Texto de encabezado",   // opcional
    "anchos_columna": { "0": 320 },    // opcional, por índice de columna
    "grupos": [ { "id": "sat", "titulo": "Microservicios satélite" } ],
    "nodos": [{
      "id": "crm", "col": 0, "fila": 2,
      "titulo": "api-core",
      "lineas": [".NET 10", "_texto en cursiva_"],   // _asi_ = cursiva
      "color": "rojo",
      "forma": "caja",
      "grupo": "bff",                  // opcional
      "ancho": 300                     // opcional, pisa el de la columna
    }],
    "flechas": [{
      "de": "crm", "a": "per",
      "etiqueta": "2 · REST",
      "tipo": "solida",                // solida | punteada | gruesa
      "color": "naranja",
      "bidireccional": false,
      "lado": "izq"                    // solo modo lateral: izq | der
    }],
    "_apuntes_no_se_dibujan": ["contexto que queda en el archivo fuente"]
  }]
}
```

Cualquier clave que empiece con `_` es documentación del spec y **nunca** llega
al diagrama. No existe una clave `notas`: ver la regla 1.

**formas:** `caja` (default) · `cilindro` (base de datos) · `entidad` (tabla, texto
arriba a la izquierda) · `estado` (máquina de estados) · `actor` · `inicio` · `fin`

**colores:** `principal` · `apoyo` · `acento` · `neutro`. Los nombres viejos
(`azul` `verde` `naranja` `amarillo` `rojo` `morado` `gris`) siguen aceptándose
y se mapean solos, para no reescribir specs ya hechos.

## Qué significa cada error del validador

| Código | Significado | Cómo se arregla |
|---|---|---|
| `E1` | Dos cajas se solapan | Mover un nodo a otra celda, o darle su propia fila |
| `E2` | El texto no entra en la caja | Acortar el texto o subir `ancho`. En un `.drawio` hecho a mano, agrandar la caja |
| `E3` | Etiqueta de flecha encima de una caja | Acortar la etiqueta; si persiste, es un bug del generador |
| `E4` | Dos flechas ancladas a menos de 24px en el mismo borde | Se leen como una sola. Lo resuelve el generador; en un `.drawio` a mano, separar los `exitY`/`entryY` |
| `A1` | Una flecha atraviesa una caja (**aviso**) | El ruteo final lo decide draw.io, así que se aproxima. Revisar a ojo; suele arreglarse moviendo el destino de columna |
| `A2` | Una flecha pasa a menos de 14px de una estructura ajena (**aviso**) | La regla 2. El generador ya reserva 18px; si aparece en un `.drawio` a mano, separar el trazo |

`E*` bloquea la entrega. `A1` no, pero se revisa.

## Auditar diagramas existentes

`validar.py` acepta varios archivos:

```bash
python validar.py ../../../contexto-negocio/diagramas/*/*.drawio
```

Sirve para los `.drawio` viejos hechos a mano. **Reporta, no toca nada.** Un
diagrama existente no se rehace sin que el responsable del repo lo pida: vale CLAUDE.md, "cero
eliminaciones y consentimiento previo".

Si una página sale como *comprimida*, el `.drawio` guarda el XML empaquetado.
Hay que abrirlo en draw.io y guardarlo con **Extras → Edit Diagram** para poder
auditarlo.

## Detalles de esta máquina

- Los scripts fuerzan UTF-8 en stdout: sin eso, un `⚠` en un reporte revienta el
  script contra la consola cp1252 de Windows. Ver CLAUDE.md, "UTF-8 en la CLI de
  Windows".
- El `.drawio` se escribe en UTF-8 sin BOM y con saltos `\n`.
- No hay Graphviz instalado. No hace falta: el layout es propio.
