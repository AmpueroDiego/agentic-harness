---
tipo: guia
fecha: 2026-09-21
tags: [guia, tablero, avance, prompt, gantt, kpi, trello]
---

> [!info] Para qué sirve
> Prompt listo para copiar y pegar, para que otra persona construya en su propio proyecto
> un tablero de avance como el del HITO 1 del Core
> ([Artifact](<url-artifact>), generado por
> `.claude/tools/trello/tablero-avance.py` + `plantilla_avance.py`).
> Nació el 2026-09-21, pedido del responsable para pasárselo a un colega con otro cronograma.
> Las tres advertencias que lleva adentro son errores reales que cometimos ese mismo día.

# Prompt: tablero de avance reutilizable

> 🏠 **Navegación:** [[Home|Home (Dashboard)]] · [[TASKS|TASKS (Registro Vivo)]] · [[docs/guias/ESTANDAR-ENTREGA-TRELLO-Y-GITHUB|Estándar de Entrega]] · [[docs/guias/PRINCIPIOS-INGENIERIA-MINIMALISTA|Principios de Ingeniería Minimalista]]

## Lecciones que el prompt ya incorpora

1. **Publicación desatendida.** `claude -p` en sesión no interactiva **no puede publicar
   Artifacts**. La tarea programada solo regenera el HTML local; republicar es manual.
2. **Doble descuento de la contingencia.** Si las horas ya llevan contingencia por riesgo
   (15/20/30%), aplicarles además un factor de foco del 70% cuenta dos veces el tiempo
   perdido en interrupciones.
3. **Sábados inflados.** Contar todos los sábados del período como días hábiles cuando
   solo se trabajan 2 al mes infla la capacidad. Se prorratean dentro de la jornada.

Un cuarto criterio, de forma: **nada de KPI de "eficiencia"**. Mide a la persona, no al
plan, y se interpreta en contra en los dos sentidos: alto sube la vara, bajo parece bajo
rendimiento aunque la culpa sea de la estimación.

---

## El prompt

````markdown
# Tablero de avance de proyecto — construir desde cero

Quiero que me construyas un tablero visual de avance de mi proyecto, publicado como
Artifact de Claude, que lea el estado real desde mi tablero de Trello y lo cruce con mi
cronograma de horas estimadas.

## Antes de escribir una línea de código, pregúntame esto

No asumas ninguna de estas respuestas. Pregúntamelas todas juntas, en una sola tanda, y
espera mi respuesta:

1. ¿De dónde sale el estado de las tareas: Trello, Jira, otra herramienta, o una planilla?
   Si es Trello: qué columnas tiene mi tablero y cuáles significan "entregado", "en curso"
   y "pendiente".
2. ¿Tengo un cronograma con horas estimadas por tarea? ¿En qué formato (Excel, Google
   Sheets, CSV)? ¿Las horas ya incluyen contingencia por riesgo, o son horas puras?
3. ¿Cuál es la fecha de inicio y la fecha de entrega comprometida?
4. ¿Cuántas horas trabajo por día y qué días de la semana? (Ojo: si trabajo algunos
   sábados al mes, no todos, hay que prorratearlos, no contarlos como días completos.)
5. ¿Mis tareas se agrupan en etapas o épicas? ¿Van una después de otra, o algunas corren
   en paralelo todo el proyecto (gestión, soporte, reuniones)?
6. ¿Tengo una reserva o colchón para imprevistos? ¿Está dentro de las horas estimadas o
   es margen aparte?
7. ¿Quién va a ver esta página: solo yo, o también mi jefe o el cliente?

## Qué construir

Tres piezas:

**1. Un archivo de datos local (CSV) con mi cronograma.**
Columnas: `fila, etapa, tarea, horas, riesgo, horas_con_contingencia, id_trello`.
El `id_trello` es el código corto de la tarjeta (el de `<card-id>`) y es lo
que une la estimación con el estado real. Las tareas sin tarjeta (reuniones, gestión)
van con esa columna vacía.
**Este archivo NO se versiona en git**: agrégalo al `.gitignore`.

**2. Un script de Python** que:
- Lea mi tablero vivo por la API (credenciales en un archivo fuera del repo, nunca dentro
  del código ni dentro de la página).
- Lea el CSV.
- Cruce ambos por el id de tarjeta y calcule todos los indicadores.
- Escriba un archivo HTML estático, autocontenido, listo para publicar.
- Solo lea: que no mueva, edite ni borre nada en Trello.

**3. El HTML publicado como Artifact**, con esta estructura de arriba hacia abajo:

- **Encabezado**: nombre del proyecto, fecha de corte, "día N de M", fecha de cierre.
- **Titular grande**: el estado en una frase — "3,2 días de ventaja", "1,5 días de
  atraso" o "En línea con el plan". Verde, ámbar o azul según el registro.
- **Bajada**: porcentaje entregado, porcentaje de plazo consumido y días hábiles que
  quedan.
- **Banda de 5 o 6 KPIs**, separados por líneas finas verticales, sin recuadros.
- **Gantt por semanas**: una barra por etapa, columnas de semana con su fecha, grilla
  vertical, línea fina marcando "hoy" y línea punteada marcando la fecha comprometida.
  Las etiquetas de "hoy" y de la fecha van **debajo** del gráfico, nunca arriba, porque
  tapan los rótulos de semana.
- **Tabla de detalle por etapa**: nombre, fecha de fin, horas totales, entregadas, en
  curso, por hacer, porcentaje y una barra chica de avance. **Ordenada cronológicamente**,
  no por tamaño, o las fechas se ven desordenadas.
- **Pronóstico**: en qué fecha cerraría al ritmo real.
- **Lista de lo que está en curso ahora**, con enlace a cada tarjeta.

## Los indicadores, con sus fórmulas

- **Entregado**: horas de las tarjetas que ya están en columnas de "hecho".
- **En curso**: horas de las tarjetas en desarrollo o revisión, con el número de tarjetas.
- **Ritmo requerido**: horas pendientes ÷ días hábiles restantes. Cuánto hay que producir
  por día de acá en adelante.
- **Margen**: días libres entre el fin del trabajo planificado y la fecha comprometida.
  Verde con 3 días o más, ámbar por debajo de 1.
- **Horas ahorradas**: horas entregadas − (días transcurridos × horas por día). Si da
  negativo, el rótulo cambia a "Horas de retraso" y se pone ámbar.
- **Desvío posible**: si las tareas de riesgo alto se pasan otro 30%, cuántos días se
  estiraría el proyecto.

**Un indicador que NO quiero: "eficiencia"** (horas entregadas ÷ capacidad usada). Se lee
como un puntaje personal: si sale alto me suben la vara, si sale bajo parece que rindo
poco aunque la culpa sea de una mala estimación. "Horas ahorradas" dice lo mismo sin
puntuar a nadie.

## Reglas de cálculo que no se negocian

1. **No descontar dos veces.** Si mis horas ya llevan contingencia por riesgo, no le
   apliques además un factor de foco del 70%: ese tiempo perdido ya está contado.
   Pregúntame cuál de los dos aplica.
2. **Días hábiles reales.** Si trabajo 2 sábados al mes, no cuentes los 4 o 5 sábados del
   período como días completos: prorratea esas horas dentro de la jornada diaria y que el
   calendario cuente solo los días que realmente trabajo. Contar un sábado de más infla la
   capacidad y el tablero miente.
3. **La línea de "hoy" avanza con la jornada**, no de golpe a medianoche: a mediodía debe
   estar a la mitad del día.
4. **El pronóstico no proyecta con menos de 3 días hábiles de datos** (el ritmo es
   demasiado inestable), y si el ritmo real daría una fecha absurda, no inventa fecha:
   dice "a este ritmo no cierra" y cuántos días harían falta.
5. **Nunca pongas la clave de Trello dentro de la página publicada.** El HTML es estático:
   los datos se calculan antes y se escriben ya resueltos.

## La actualización diaria — leé esto antes de prometer nada

Quiero que se actualice una vez al día, de lunes a viernes. **Verificá cómo funciona de
verdad en mi entorno antes de dármelo por hecho.** Un dato comprobado: una sesión de
Claude en modo desatendido (`claude -p`) **no puede publicar Artifacts**; solo una sesión
abierta puede.

Entonces, propongo esto y decime si en mi registro hay algo mejor:
- Una tarea programada del sistema corre el script de Python una vez al día. Eso regenera
  el HTML local y **no gasta tokens de ningún modelo**.
- Republicar el Artifact queda como acción manual, cuando yo la pida.
- Si encontrás una forma de que el republicado también sea automático, mostrámela, pero
  probala de verdad antes de decirme que funciona.

## Estética

Formato de lámina de informe, estilo consultora: página blanca ancha (hasta 1120 px),
jerarquía por tamaño de letra y líneas finas, **sin tarjetas con sombra ni bordes
redondeados**. Una tipografía con carácter para títulos y una monoespaciada para todas las
cifras, con cifras de ancho fijo para que las columnas queden alineadas. Un solo color de
acento; verde para lo hecho, ámbar para las alertas. Que funcione en tema claro y oscuro,
y en pantalla de celular. **Todo texto chico con contraste suficiente** (mínimo 4,5:1
sobre el fondo): un gris claro de 11 px no se lee.

## Cómo quiero que trabajes

- Primero las preguntas, después el código.
- Si mi proyecto no tiene alguna de las partes (gestión, reserva de fixes, etapas en
  paralelo), **no la inventes**: dejá el tablero sin esa sección y decímelo.
- Si mis números no cierran (por ejemplo, el trabajo no entra en el plazo), **decímelo
  claro con las cifras**, no lo maquilles. Y mostrame las opciones concretas: mover la
  fecha, recortar alcance o poner más horas, cada una con su número.
- Al terminar, explicame en dos líneas cómo actualizarlo y qué mirar cada día.
````
