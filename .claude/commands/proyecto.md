---
description: Gestión del proyecto sistema — estado del HITO 1, hallazgos fuera de alcance (tarjeta + horas extra) y actualización del tablero de avance.
argument-hint: estado | extra "<qué apareció>" [horas] [riesgo] | tablero
tipo: comando
fecha: 2026-10-30
tags: [harness]
---

# /proyecto

Un solo lugar para las tres cosas que se hacen seguido al llevar el proyecto: mirar cómo va,
registrar lo que aparece fuera del plan, y dejar el tablero al día.

No reemplaza a [`/trello`](trello.md) ni a [`/orquestar`](orquestar.md): los usa. Trello se
sigue tocando con su skill (simula, aprueba, aplica); el código sigue pasando por el pipeline.

**Piezas que maneja:**
- `.claude/tools/trello/tablero-avance.py` + `plantilla_avance.py` — generan el HTML.
- `contexto-negocio/estimacion-backlog-pert.csv` — horas estimadas por tarea. **No se versiona.**
- Artifact del tablero: <url-tablero>

---

## `estado`

Resumen corto, sin publicar nada:

```
python .claude/tools/trello/tablero-avance.py
```

Reporta en 4 o 5 líneas: días transcurridos y restantes, porcentaje entregado, margen,
reserva consumida y el pronóstico. Si el pronóstico se aleja de la fecha objetivo, dilo **una vez**,
con los números, sin insistir: respeta las decisiones de alcance y fecha registradas por el responsable.

## `tablero`

Regenera y republica el Artifact, **misma ruta de archivo** para conservar el enlace.

**Hazlo en la sesión abierta, nunca delegando a un subagente**: el primer intento con Haiku
costó 53.7K tokens porque el agente arranca leyendo `CLAUDE.md` y su skill antes de correr
dos comandos. En sesión son 1-2K. Y `claude -p` en modo desatendido **no puede publicar
Artifacts** (probado el 2026-09-21): la tarea programada de Windows solo regenera el HTML
local, que es gratis.

## `extra "<qué apareció>" [horas] [riesgo]`

Para el trabajo que **no estaba en el plan** y salió mientras se hacía otra cosa.

### Primero: ¿tarjeta nueva o se amplía la que está en curso?

**Se amplía la tarjeta en curso** solo si el hallazgo **bloquea** la tarea: sin arreglarlo,
lo que se está haciendo queda mal o no cierra. Va en un commit aparte dentro del mismo PR
(regla del playbook: *si lo que vas a tocar ya está mal, se arregla primero*).

**Tarjeta nueva** si se cumple cualquiera de estas:
- no bloquea: la tarea original cierra igual sin eso;
- es de otro repo u otra área;
- pesa más de la mitad de la tarjeta original (4 h de tarea + 6 h de hallazgo ⇒ aparte, o la
  estimación deja de explicar nada).

### Después, en los dos casos

1. **Trello.** Si va tarjeta nueva, propónla con `/trello crear` (simulada, con título,
   columna, etiquetas y descripción) y espera aprobación. Si se amplía una existente,
   propón `actualizar --desc-archivo` sumando una línea: *"se sumó X (+N h)"*. El título de
   una tarjeta existente no se toca.
2. **CSV.** Agrega una fila con `epica = Extras`, las horas con contingencia y el
   `id_trello`. Si el trabajo va dentro de una tarjeta que ya existe, **repite ese mismo
   id**: el script lo maneja y esas horas se marcan como hechas cuando la tarjeta se cierre.
   Sin esta fila, el tiempo extra desaparece y el tablero dirá que hubo atraso sin explicar
   por qué.
3. **`TASKS.md`.** Una fila con fecha, repo, qué apareció y el link a la tarjeta.
4. **Tablero.** Regenera (`tablero`) para que se vea la barra ámbar de Extras y cuánta
   reserva queda.

### Qué mirar después

Las horas de `Extras` salen de la **reserva de fixes**, no del plazo. El KPI "Reserva
consumida" es el aviso real: al pasar el 70% se pone en ámbar, y al llegar a 100% cualquier
imprevisto nuevo ya empuja la fecha. Ese es el momento de hablar de alcance, no antes.

---

## Reglas que no se negocian

- **Nada se crea ni se mueve en Trello sin propuesta previa y aprobación** (CLAUDE.md).
- **El CSV no se versiona** y las credenciales de Trello viven fuera del repo.
- El script **solo lee** Trello: no mueve, edita ni borra tarjetas.
- **No inventar horas.** Si no hay estimación para lo que apareció, pídela; una fila `Extras`
  sin horas no sirve para nada.
