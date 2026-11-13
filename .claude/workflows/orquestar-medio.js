export const meta = {
  name: 'orquestar-medio',
  description: 'El medio mecanico de /orquestar: por cada cambio del plan, coder -> QA + adversary -> fix, en pipeline',
  whenToUse: 'Cuando el plan ya esta cerrado y se parte en 2 o mas cambios con archivos disjuntos. El orquestador sigue decidiendo triage, rama, Trello, commits y run doc: esto solo corre el tramo repetitivo.',
  phases: [
    { title: 'Coder', detail: 'un agente por cambio, con su lista de archivos exclusiva' },
    { title: 'Revision', detail: 'QA y adversary sobre ese cambio, en paralelo' },
    { title: 'Fix', detail: 'el mismo tipo de coder cierra los hallazgos de su cambio' },
  ],
}

// Por que existe: hoy el orquestador espera en silencio a cada coder y recien
// cuando vuelven TODOS lanza QA. Dos costos reales, medidos en las corridas
// 0053-0055: el cambio A se queda quieto mientras B todavia escribe, y el
// silencio de una espera larga es lo que dispara el watchdog de 600 s (mato 5
// coders el 2026-09-21). pipeline() arranca la revision de A apenas A termina,
// y cada paso tiene un borde definido en vez de una espera abierta.

const ENTREGA = {
  type: 'object',
  properties: {
    resumen: { type: 'string', description: 'que cambiaste, en una o dos frases' },
    archivosTocados: { type: 'array', items: { type: 'string' } },
    buildVerde: { type: 'boolean' },
    buildDetalle: { type: 'string', description: 'vacio si paso; el error resumido si no' },
    archivosFueraDeLista: {
      type: 'array',
      items: { type: 'string' },
      description: 'archivos que abriste y el prompt no nombraba, con el por que. Vacio es lo normal.',
    },
    bloqueado: { type: 'string', description: 'vacio, o que no pudiste hacer porque el plan estaba mal' },
  },
  required: ['resumen', 'archivosTocados', 'buildVerde', 'archivosFueraDeLista'],
}

const HALLAZGOS = {
  type: 'object',
  properties: {
    veredicto: { type: 'string', enum: ['PASS', 'FINDINGS'] },
    hallazgos: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          archivo: { type: 'string' },
          linea: { type: 'number' },
          severidad: { type: 'string', enum: ['P1', 'P2', 'P3'] },
          problema: { type: 'string' },
          escenario: { type: 'string', description: 'entradas concretas -> resultado incorrecto' },
        },
        required: ['archivo', 'problema', 'escenario'],
      },
    },
  },
  required: ['veredicto', 'hallazgos'],
}

const cfg = args || {}
const cambios = cfg.cambios || []
const raiz = cfg.raiz || '.'
const build = cfg.comandoBuild || 'dotnet build'
const CICLOS_MAX = 2 // mismo presupuesto de reintentos que el Step 4 de orquestar.md

if (!cambios.length) {
  log('Sin cambios en args.cambios: no hay nada que correr.')
  return { cambios: [], nota: 'args.cambios vacio' }
}

log(`${cambios.length} cambio(s) sobre ${raiz}. Cada uno avanza por su cuenta: el primero que termina de codear ya entra a revision.`)

const listar = (xs) => (xs && xs.length ? xs.map((f) => `- ${f}`).join('\n') : '- (ninguno)')

function promptCoder(c) {
  return [
    `Trabajas sobre la raiz \`${raiz}\`. Toda ruta es relativa a ahi.`,
    '',
    `## Tarea`,
    c.instrucciones,
    '',
    `## Archivos del plan (los unicos que podes editar)`,
    listar(c.archivos),
    '',
    `## Para entender el patron (leelos enteros, no los edites)`,
    listar(c.referencia),
    '',
    `## Limites`,
    `- No abras el resto del feature para "tomar contexto". Si te falta un archivo, leelo y decilo en \`archivosFueraDeLista\` con el por que.`,
    `- Hay otros coders trabajando en paralelo sobre esta misma carpeta. Los archivos de arriba son tuyos en exclusiva; cualquier otro es de otro. Si necesitas que cambie algo fuera de tu lista, no lo toques: reportalo en \`bloqueado\`.`,
    `- Corre \`${build}\` y nada mas. La suite la corre QA despues, una sola vez.`,
  ].join('\n')
}

function promptRevision(c, entrega, lente) {
  const comun = [
    `Raiz: \`${raiz}\`. Cambio: "${c.titulo}".`,
    `El coder reporto: ${entrega.resumen}`,
    `Archivos tocados: ${(entrega.archivosTocados || []).join(', ') || '(no reporto)'}`,
    '',
    `Revisa **solo el diff de esos archivos**, no el repo entero.`,
  ]
  if (lente === 'qa') {
    return comun.concat([
      `Sos QA: correccion, desajustes contra el esquema real de la base, casos borde olvidados, y si el cambio hace lo que el plan pedia.`,
      `Corre la suite del repo una vez y contala en tu veredicto.`,
      `Un hallazgo sin \`archivo\`, sin escenario concreto y sin como reproducirlo no es un hallazgo: no lo reportes.`,
    ]).join('\n')
  }
  return comun.concat([
    `Sos el auditor adversarial: buscas lo que QA no ve. Manipulacion de estado, contradicciones logicas, datos sucios, concurrencia, fallos de red en el limite, mutantes de codigo que los tests no matan.`,
    `No repitas lo que un QA normal encontraria. Si no hay nada real, devolve PASS: un hallazgo inventado cuesta mas que uno que falta.`,
  ]).join('\n')
}

function promptFix(c, hallazgos) {
  return [
    `Raiz: \`${raiz}\`. Cerra estos hallazgos sobre el cambio "${c.titulo}".`,
    '',
    hallazgos
      .map((h, i) => `${i + 1}. [${h.severidad || 'P2'}] ${h.archivo}${h.linea ? ':' + h.linea : ''} — ${h.problema}\n   Escenario: ${h.escenario}`)
      .join('\n'),
    '',
    `## Limites`,
    `- Segui siendo dueño solo de: ${(c.archivos || []).join(', ')}. Hay otros coders en paralelo.`,
    `- Si un hallazgo es falso, no lo "arregles": decilo en \`bloqueado\` con la evidencia que lo desmiente.`,
    `- Corre \`${build}\` al terminar.`,
  ].join('\n')
}

const resultados = await pipeline(
  cambios,

  // 1. Codear. Un agente por cambio, con sus archivos en exclusiva.
  (c) => agent(promptCoder(c), {
    label: `coder:${c.id}`,
    phase: 'Coder',
    schema: ENTREGA,
    agentType: c.agente || 'coder',
  }),

  // 2. Revisar ese cambio apenas esta listo, sin esperar a los otros.
  //    Barrera local a proposito: para decidir si hay que arreglar algo hacen
  //    falta los dos veredictos del MISMO cambio, no los de todos los cambios.
  async (entrega, c) => {
    if (!entrega) return null
    if (entrega.buildVerde === false) {
      log(`${c.id}: el build quedo rojo, no se manda a revisar. ${entrega.buildDetalle || ''}`)
      return { cambio: c, entrega, hallazgos: [], estado: 'BUILD_ROJO' }
    }
    if (entrega.archivosFueraDeLista && entrega.archivosFueraDeLista.length) {
      log(`${c.id}: leyo ${entrega.archivosFueraDeLista.length} archivo(s) fuera de la lista del plan — revisar la lista del planner.`)
    }

    const lentes = c.conAdversary === false ? ['qa'] : ['qa', 'adversary']
    const veredictos = await parallel(
      lentes.map((lente) => () =>
        agent(promptRevision(c, entrega, lente), {
          label: `${lente}:${c.id}`,
          phase: 'Revision',
          schema: HALLAZGOS,
          agentType: lente === 'qa' ? 'qa' : 'adversary',
        }))
    )
    const hallazgos = veredictos.filter(Boolean).flatMap((v) => v.hallazgos || [])
    const caidos = veredictos.filter((v) => !v).length
    if (caidos) log(`${c.id}: ${caidos} de ${lentes.length} revisores no devolvieron nada; se sigue con lo que hay.`)
    return { cambio: c, entrega, hallazgos, estado: hallazgos.length ? 'FINDINGS' : 'PASS' }
  },

  // 3. Arreglar, y volver a revisar solo si hizo falta arreglar. Acotado.
  async (rev, c) => {
    if (!rev || rev.estado !== 'FINDINGS') return rev
    let pendientes = rev.hallazgos
    let ciclos = 0
    const historia = []

    while (pendientes.length && ciclos < CICLOS_MAX) {
      ciclos++
      const fix = await agent(promptFix(c, pendientes), {
        label: `fix:${c.id}#${ciclos}`,
        phase: 'Fix',
        schema: ENTREGA,
        agentType: c.agente || 'coder',
      })
      historia.push({ ciclo: ciclos, fix })
      if (!fix) break

      const reve = await agent(promptRevision(c, fix, 'qa'), {
        label: `qa-verify:${c.id}#${ciclos}`,
        phase: 'Fix',
        schema: HALLAZGOS,
        agentType: 'qa',
      })
      if (!reve) break
      pendientes = reve.hallazgos || []
    }

    if (pendientes.length) {
      log(`${c.id}: quedan ${pendientes.length} hallazgo(s) despues de ${ciclos} ciclo(s). Corta aca por presupuesto: decide vos.`)
    }
    return Object.assign({}, rev, {
      estado: pendientes.length ? 'SIN_CERRAR' : 'CERRADO',
      ciclos,
      historia,
      pendientes,
    })
  }
)

const vivos = resultados.filter(Boolean)
const caidos = resultados.length - vivos.length
if (caidos) log(`${caidos} cambio(s) se cayeron sin resultado — miralos a mano antes del commit.`)

const sinCerrar = vivos.filter((r) => r.estado === 'SIN_CERRAR' || r.estado === 'BUILD_ROJO')
log(`Listo: ${vivos.length - sinCerrar.length} cambio(s) cerrados, ${sinCerrar.length} necesitan tu decision, ${caidos} caidos.`)

return {
  raiz,
  cambios: vivos,
  requierenDecision: sinCerrar.map((r) => ({ id: r.cambio.id, estado: r.estado, pendientes: r.pendientes || [] })),
  caidos,
  nota: 'El commit, el diff contra git status, la migracion, Trello y el run doc NO los hace este workflow: son del orquestador.',
}
