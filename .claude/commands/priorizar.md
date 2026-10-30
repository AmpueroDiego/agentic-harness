---
description: Prioriza el trabajo pendiente para entregar una versión básica y el primer hito completo en sus fechas objetivo. Solo lectura: propone, no mueve nada.
tipo: comando
fecha: 2026-10-30
tags: [harness]
---

# /priorizar

Dice **qué hacer primero** para llegar a cada fecha y **qué se cae** si no cabe. No mueve tarjetas, no edita archivos, no escribe en Trello: cualquier cambio va aparte por `/trello`, con propuesta y aprobación.

## Metas (definidas por el responsable)

- **Primer corte: versión básica del dominio.** Usa la fecha, el presupuesto y el alcance confirmados por el responsable.
- **Segundo corte: primer hito completo.** Lo que no entre en el primer corte sigue hacia esa fecha.
- **Fuera del primer corte:** las integraciones y funciones complementarias que el responsable haya excluido explícitamente.

## Datos (leer, no inventar)

1. Tablero vivo: `python .claude/tools/trello/trello.py listar --columna "<columna>"` para Backlog, En desarrollo y las dos En revisión. **DEV, Listo para PROD y Terminado ya están hechos: no cuentan.** Lectura grande por `trello-read-shunt.sh`.
2. Horas: `contexto-negocio/estimacion-backlog-pert.csv` (columna `horas_cont`, con contingencia). Tarjeta viva sin fila en el CSV = 4.8 h por defecto, y se dice cuáles son.
3. Capacidad: `.claude/tools/trello/tablero-pendiente.py` ya calcula días hábiles restantes, sábados (4 h) y las dos jornadas (11.9 h del plan, 9.35 h real). Reusar esas constantes; no duplicarlas.
4. Si el responsable pide refrescar el PERT desde el Google Sheet, usarlo con el conector de Drive y avisar qué filas cambiaron. El CSV no se versiona.

## Cómo se clasifica cada tarjeta pendiente

| Clase | Qué es | Cuándo sale |
|---|---|---|
| **A — caso de uso principal** | Operar una entidad de punta a punta, con sus validaciones, historial, login y roles | Primer corte |
| **B — soporte directo de A** | Bugs y estabilidad de lo que A usa (sesión, errores, regresiones). Si sin esto A se rompe o no se puede operar | Primer corte |
| **C — funciones complementarias** | Extensiones del dominio, marca, administración, refactors, observabilidad y calidad | Segundo corte |
| **D — alcance excluido** | Lo de la lista "fuera" de arriba | No entra |

Orden de desempate dentro de A: 1) completar el caso de uso sin fricción, 2) conservar el historial y la continuidad, 3) reducir los pasos del operador. **Si una tarjeta es dudosa, no se decide: se lista con la pregunta exacta para el responsable.** Gestión (demos, configuración de producción, soporte) cuenta siempre, y se muestra aparte.

## Qué entrega

En lenguaje simple, sin vueltas:

1. **¿Llegamos al primer corte?** Horas de A + B + Gestión del corte contra la capacidad hasta la fecha del primer corte, a 11.9 h y a 9.35 h por día. Margen o atraso en días.
2. **Lista priorizada** por ola (qué se hace primero), con horas y tarjeta. Las que ya están en desarrollo o revisión, marcadas.
3. **Lo que queda fuera del primer corte** si no cabe, ordenado de lo más prescindible a lo menos, como propuesta.
4. **Huecos:** qué falta para operar el caso de uso principal de punta a punta y hoy no tiene tarjeta. Verificar contra el código antes de afirmarlo.
5. **Dudosas:** tarjetas sin clase clara, con la pregunta para el responsable.

Sin SLA ni campos nuevos por iniciativa propia (regla del dominio). Si aparece una oportunidad real, va como sugerencia.
