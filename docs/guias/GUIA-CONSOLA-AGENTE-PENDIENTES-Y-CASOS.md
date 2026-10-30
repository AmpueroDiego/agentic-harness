---
tipo: guia-funcional
fecha: 2026-09-11
estado: vigente
tags: [guia, consola, entidades, operaciones, web-app, api-core]
---

# Guía — Consola genérica: pendientes y ciclo de una entidad

> 🏠 **Navegación:** [[Home|Índice]] · [[docs/guias/PLAYBOOK-ANTI-REGRESIONES-Y-LECCIONES-APRENDIDAS|Playbook]]

Ejemplo funcional anonimizado de una consola para gestionar entidades y operaciones. Conserva el recorrido, los filtros y los defectos observados en la revisión original como escenarios de verificación; no describe el estado actual de una aplicación incluida en este repo.

---

## 0. Antes de empezar

| Servicio | Puerto | Cómo se verifica |
|---|---|---|
| `api-core` (Host) | `5182` | la consola hace `GET /api/Entidad/Pendientes` |
| `web-app` (Vite) | `5173` | abre `http://localhost:5173/` |

Si la consola carga pero todo sale vacío, el problema casi siempre es el `5182`, no el front.

**Con qué usuario:** esto importa más de lo que parece — la bandeja de Pendientes es **por usuario**, así que lo que ves depende de con quién entraste.

---

## 1. Los tres conceptos

```
TITULAR  (la persona/empresa — vive en api-people)
   │
   ├── ENTIDAD  (un problema con ciclo de vida: Abierto → Atendido → Cerrado)
   │      │
   │      └── OPERACIÓN  (cada gestión concreta dentro dla entidad)
   │
   └── ENTIDAD  (otro problema, independiente del anterior)
```

Tres reglas que salen de ahí:

1. **Un titular puede tener varias entidades abiertas a la vez.** Son problemas distintos, no se pisan. *(Ejemplo sintético: una entidad maestra con varias entidades activas.)*
2. **Una entidad puede tener N operaciones**, del mismo agente o de varios. La entidad es el expediente; las operaciones son lo que se hizo. *(Ejemplo sintético: `ENTIDAD-003` tiene 3 operaciones.)*
3. **Si el titular vuelve a escribir por lo mismo, NO se abre una entidad nueva** — se agrega una operación a la que ya existe. La UI lo dice: *"Toda nueva interacción se asocia a esta entidad (sin tickets duplicados)"*.

---

## 2. Por qué una entidad aparece (o no) en tus Pendientes

Llega a tu bandeja **solo si cumple las tres condiciones a la vez**:

| # | Condición | Dónde se decide |
|---|---|---|
| 1 | Entidad activa | `Entidad.EsActivo = 1` |
| 2 | Estado **no terminal** | `EstadoEntidad.EsTerminal = 0` → `Abierto` y `Atendido` sí; `Cerrado` no |
| 3 | **Asignado a ti**, con asignación viva | `EntidadAsignacion` con `FechaFin IS NULL` y `IdUsuarioAsignado` = tu usuario |

> **La condición 3 es la que sorprende.** Una entidad recién creada **no está asignada a nadie**, así que no aparece en la bandeja de nadie. No es que esté "sin leer": **es invisible**.

Hay un cuarto filtro, del lado del navegador (`PendingView.tsx:7`): oculta las entidades que **cerraste en esta misma sesión**, sin esperar a recargar.

**El síntoma típico:** dice "Pendientes 0" aunque sabes que hay entidades. En el escenario de prueba: **10 entidades no terminales** y la bandeja en cero, porque `Core.EntidadAsignacion` estaba **vacía**. Se resolvió asignando, sin tocar una línea de código.

> ⚠️ **No existe cola general.** `Pendientes` es "mis entidades asignadas", no "entidades por tomar". Ver la lista de verificaciones de esta guía.

---

## 3. Recorrido en pantalla

### Paso 1 — Entrar

`http://localhost:5173/`. Sin nada abierto verás **"No hay atenciones abiertas"** y el botón **Ver pendientes**.

Arriba, dos contadores:

| Contador | Qué cuenta |
|---|---|
| **Pendientes** | entidades asignadas a ti, sin cerrar |
| **Historial** | entidades cerradas… ⚠️ ver §6 |

### Paso 2 — Ver la cola

| ENTIDAD | TITULAR | SERVICIO | CANAL | TIEMPO EN COLA |
|---|---|---|---|---|
| ENTIDAD-001 | TITULAR-001 | Gestionar una operación | ● Mensajería | *(vacío)* |
| ENTIDAD-002 | TITULAR-001 | Consultar una entidad | ● Mensajería | *(vacío)* |

> **Detalle:** `ENTIDAD-002` está en **Atendido**, no `Abierto`, y aun así está en la cola. Correcto: el filtro es *"no terminal"*, no *"solo abierto"*. Una entidad atendida **sigue siendo tuya** hasta que la cierres.

> ⚠️ **TITULAR** muestra el identificador en vez del nombre, y **TIEMPO EN COLA** está siempre vacía.

### Paso 3 — Abrir una entidad

Clic en **Abrir entidad** → se convierte en **pestaña de trabajo** y la pantalla se parte en tres:

| Columna | Qué tiene |
|---|---|
| **Izquierda — CONTACTO** | identificador, nombre, celular, correo, domicilio y las **notas** del titular |
| **Centro — la atención** | conversación del canal, plantillas de respuesta y el formulario **REGISTRAR INTERACCIÓN** |
| **Derecha — CUENTA** | Resumen / Estado / Alertas, y Registro · Entidades relacionadas · Operaciones |

**Abrir una entidad no la saca de Pendientes.** El contador no baja. Solo el cierre la saca.

### Paso 4 — El Registro

Es la historia completa del titular: **todas sus entidades**, no solo la abierta.

```
[ Todos ]  [ Mensajería 3 ]  [ Llamada 2 ]  [ Correo 1 ]  [ Presencial 1 ]
```

Solo aparecen los canales con entidades. Los conteos se calculan sobre el total, así que no mienten al filtrar.

### Paso 5 — Leer una tarjeta

```
● Gestionar una operación   ENTIDAD-001   Mensajería        ●  ← estado
  Asesor: Persona A                            11 set. 2026, 05:04 p.m.
  Consultó los próximos pasos de una operación…
  ✓ OPERACIONES / ACTIVIDADES (1)
      ● Completar una operación    4★    11 set. 2026, 05:04 p.m.
```

| Elemento | Significado |
|---|---|
| Badge de color izq. | tipo de servicio — verde = consultas, rojo = quejas/reclamos, blanco = información |
| `ENTIDAD-XXXX` | número de expediente |
| Chip de canal | por dónde entró |
| **● punto derecho** | **estado: 🟢 abierto, 🔴 cerrado** |
| `Asesor:` + fecha | quién lo abrió y cuándo |
| `OPERACIONES / ACTIVIDADES (n)` | cuántas gestiones lleva |
| `4★` | calificación de esa operación |

**Regla del punto:** rojo **solo** si el estado contiene "cerrad". Todo lo demás verde — `Atendido` incluido, porque sigue siendo trabajo vivo. El estado en texto está en el `title` y disponible para lectores de pantalla.

> ⚠️ El "Asesor" sale de `Entidad.Autor`, **texto libre** — no de la asignación. Si se transfiere la entidad, el nombre no cambia.

---

## 4. Registrar una operación

**Dónde:** panel central, **REGISTRAR INTERACCIÓN**.

| Campo | Qué es | Nota |
|---|---|---|
| **Servicio** | el "qué" general | 3 opciones |
| **Actividad** | el "qué" específico | **hijo del Servicio** — cambia según lo de arriba. "Gestionar una operación" tiene 8 |
| **Entidad(es) relacionada(s)** | a qué entidad relacionada aplica | |
| **Estado** | Abierto / Atendido / Cerrado | |
| **Fecha compromiso** | si quedaste en responder | opcional · ⚠️ hoy no se muestra en ninguna parte |

> 🔎 **Dato interno:** lo que la UI llama **"Actividad"**, en la base es la tabla **`Clasificacion`**.

**Cómo:** Servicio → Actividad → Resumen/Comentario → **Agregar a Registro**.

Eso crea una operación nueva en la misma entidad. **Un agente puede agregar las que quiera** — es el uso normal.

> ⚠️ **La tarjeta no se actualiza al guardar.** Sigue mostrando el conteo viejo hasta recargar. El dato se guarda bien; falla el refresco.

---

## 5. Cerrar una entidad

**Botón:** `✓ Finalizar atención`. Son **dos pasos**.

### Paso 1 — confirmación

Muestra Servicio / Estado / Actividad y una **Nota de cierre (opcional)**.

> ⚠️ Muestra **GUIDs crudos** en vez de los nombres.
> ⚠️ La nota es **opcional**: se puede cerrar una entidad sin explicar nada.

### Paso 2 — resultado

| Campo | Opciones |
|---|---|
| **Resultado dla entidad** | Resuelto · Requiere seguimiento · No resuelto |
| **Últimas atenciones de este titular** | referencia, no editable |

*(La calificación por colores Verde/Amarillo/Rojo se retira: la reemplazan las estrellas por operación.)*

### Qué pasa al confirmar

| Efecto | Verificado |
|---|---|
| `EstadoEntidad` → **Cerrado** (`EsTerminal = 1`) | ✅ |
| La nota se guarda en `Entidad.Resumen` | ✅ |
| **Se crea una operación extra de cierre** | ✅ de 2 pasó a 3 |
| **Pendientes** baja | ✅ 3 → 2 |
| **Historial** sube | ✅ 0 → 1 |

---

## 6. ¿Dónde queda la entidad cerrada?

| Lugar | ¿Aparece? |
|---|---|
| **Registro del titular** | ✅ **Sí, permanente**, con punto 🔴 y todas sus operaciones |
| **Pendientes** | ❌ No — correcto |
| **Historial** | ❌ ⚠️ **Roto** |

**El Historial es falso.** Vive en una variable del navegador (`localClosedHistory`), no en la API: se borra al recargar y al cerrar sesión. **Escenario de reproducción** — mostró la entidad cerrada, se recargó la página y volvió a 0.

Un agente **no puede ver mañana lo que cerró hoy**.

**En la práctica: el único lugar confiable donde vive la historia de una entidad cerrada es el registro del titular.**

---

## 7. Transferir a otro agente

**El modelo lo soporta bien.** `AsignarEntidadCommandHandler` hace reasignación real:

```
asignación anterior →  FechaFin = ahora, EstaReasignado = true
nueva asignación    →  IdUsuarioAsignado = destino, AsignadoPor = del JWT
```

Queda **historial completo** de por qué manos pasó, y una restricción única impide dos activas a la vez.

> ⚠️ **El botón "Transferir" de la UI está muerto.** `transferTargets: []` está hardcodeado vacío; sale el toast *"No hay un equipo de transferencia disponible"*. No hay selector de agente ni endpoint que los liste.

---

## 8. Lo que viene: eventos al mismo nivel que la entidad

Ejemplo de evolución del modelo: registrar eventos independientes de una entidad.

Hoy toda gestión exige una entidad, así que *"se realizó una visita"* no tiene dónde vivir. Eso cambia:

```
┌ ● Gestionar una operación  ENTIDAD-001  Mensajería    🔴 ┐
│   ✓ OPERACIONES / ACTIVIDADES (3)
└──────────────────────────────────────────────────────────────────┘

  ▎ Cita presencial · Presencial          10 set. 2026, 09:15 a. m.   ← celeste
    Consultó presencialmente por una operación · Persona B
```

**Caja = expediente vivo. Franja celeste = algo que ya pasó.**

El evento no tiene estado, ni operaciones adentro, ni cierre, ni entra a Pendientes. Es un hecho, no un problema a resolver.
