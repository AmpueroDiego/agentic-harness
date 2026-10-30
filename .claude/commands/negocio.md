---
tipo: comando
tags: [sistema-multiagente]
description: Contrapeso de negocio antes de planificar — revisa una tarjeta, un REQ o una idea contra los criterios del dominio configurados en el proyecto y devuelve objeciones, no diseño técnico.
argument-hint: <shortLink de Trello | ruta de un REQ | la idea en texto>
---

# /negocio

El `planner` verifica esquema y viabilidad técnica; nadie hacía el contrapeso de negocio.
Esta skill responde una sola pregunta: **¿esto resuelve el caso de uso de la persona usuaria y le ahorra
trabajo a quien opera el sistema, o solo queda elegante puertas adentro?**

Corre **antes** del `architect`/`planner`, o cuando el responsable quiera una segunda opinión sobre
una tarjeta del backlog. No diseña la solución: si el veredicto es que vale la pena, el
diseño lo hace el pipeline.

## Entrada

Cualquiera de estas tres:
- un shortLink de Trello (`/negocio <card-id>`) — léela con `/trello ver`;
- la ruta de un REQ de `requisitos/`;
- la idea en texto, tal como la dijo el responsable.

## Los tres criterios, en este orden

Se toman de la visión de dominio de `CLAUDE.md`; si aún no está configurada, pide al responsable que la defina. Como ejemplo genérico, el orden importa: si el primero falla, los otros dos no rescatan
la propuesta.

1. **Resolución del caso de uso.** ¿La persona puede completar su objetivo sin
   fricción? ¿O lo obliga a salir del sistema, a pedir algo por otro canal, a esperar a alguien?
2. **Historial y continuidad.** ¿Queda registrado de forma que otra persona retome el trabajo sin
   volver a preguntarle todo a la persona usuaria? Lo que no queda en el registro, se pierde.
3. **Facilidad para el agente.** Entre dos diseños igual de correctos, gana el de menos
   clics. Cuenta también para las APIs: ¿la pantalla arma su vista con una llamada, o la
   obliga a encadenar tres?

## Qué devolver

Corto, en este orden:

1. **Veredicto en una línea**: vale la pena / vale con condiciones / no ahora, y por qué.
   Equivalen a **seguir / aclarar / parar** *(desde 2026-10-07, evaluación de ideas de Spec Kit)*:
   «vale con condiciones» es «aclarar» y nombra qué falta saber antes de seguir.
2. **Objeciones**, la más grave primero, cada una con el criterio que incumple y el escenario
   concreto ("se finaliza una operación y quien retoma el trabajo no ve el motivo"). **Cada una cita
   su evidencia** (`archivo:línea`, tarjeta, dato del esquema) o se marca «supuesto, sin
   evidencia»: una objeción sin evidencia no puede ser la que decide un «parar».
3. **Alcance mínimo que sí resuelve el problema.** Casi siempre hay una versión más chica que
   entrega el 80% del valor; nómbrala.
4. **Preguntas abiertas para el responsable**, si las hay. Una decisión de negocio no se inventa: se
   pregunta.

## Reglas

- **Verificar antes de afirmar.** Si vas a decir "hoy esto no existe" o "esto ya está
  resuelto", compruébalo primero con `grep`/`Read` sobre el código o con `/trello ver`, y cita
  `archivo:línea`. Un hallazgo sin verificar cuesta más que no decir nada.
- **Restricciones vigentes del dominio.** Lee las decisiones documentadas antes de proponer
  plazos, vencimientos, aprobaciones o nuevos campos. No conviertas una posibilidad técnica
  en una regla de negocio inventada.
- **Cierre de una entidad.** Comprueba quién puede finalizarla y qué registro exige el
  proyecto; no inventes aprobación de supervisor ni confirmación de otra persona.
- **Campos excluidos deliberadamente.** Si el proyecto dejó datos fuera de una vista o de
  una API, no los propongas de vuelta sin confirmarlo con el responsable.
- **No diseñes la tabla ni el endpoint.** Si la propuesta pasa, el `architect` y el `planner`
  deciden el cómo.
- **No opines de estética**: eso es de [`/ux`](ux.md).

## Después

- Si el veredicto es "vale la pena": el pipeline sigue con [`/orquestar`](orquestar.md), y las
  objeciones que no bloquean viajan como contexto al `planner`.
- Si aparece trabajo nuevo que no estaba en el plan:
  [`/proyecto extra`](proyecto.md).
- Si la conclusión es "no ahora": que la tarjeta baje a `Backlog del Backlog` con
  [`/trello`](trello.md), con una línea de por qué — propuesta y aprobación, como siempre.
