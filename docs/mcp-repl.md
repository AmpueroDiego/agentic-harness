---
tipo: guia
fecha: 2026-11-16
tags: [codex, mcp, repl, herramientas]
---

# MCP diferido y REPL persistente

Este documento distingue el código portable y las capacidades del entorno.
Consulta la [arquitectura](../LLAMA-HARNESS.md) y la [auditoría](harness-audit.md).

## Qué aporta cada capa

| Capa | Función | Responsable |
|---|---|---|
| Archivos del Harness | Declaran instrucciones, perfiles, controles y formatos | Repositorio |
| Herramientas nativas | Ejecutan acciones que el cliente admite | Cliente y entorno |
| Servidor MCP | Describe herramientas y atiende solicitudes | Propietario del servidor |
| Plugin | Agrupa una conexión y otras capacidades | Plataforma y propietario |
| Descubrimiento diferido | Expone herramientas cuando la tarea las necesita | Entorno |
| REPL persistente | Conserva variables entre llamadas | Entorno de ejecución |

Clonar este repositorio no instala servidores MCP ni concede acceso a servicios externos.
Cada usuario conecta los servicios que necesita mediante sus propios permisos.
OpenAI documenta las diferencias entre conexiones locales y plugins alojados en su [guía oficial de MCP](https://learn.chatgpt.com/docs/extend/mcp).

## Descubrir antes de ejecutar

Primero identifica la operación que necesita el usuario.
Busca herramientas por nombre y descripción.
Lee el esquema y las instrucciones antes de llamar una herramienta.
Comprueba que el destino y la operación coincidan con la autorización.
Usa la herramienta disponible que resuelva la tarea directamente.

Si el entorno ofrece `tool_search`, sigue su esquema y sus instrucciones.
Otros entornos ofrecen inventarios o mecanismos diferentes.
No supongas que todos los clientes incluyen las mismas APIs.

### Patrón observado en esta sesión

El entorno observado ofrece `functions.exec`, `ALL_TOOLS` y el objeto `tools`.
`ALL_TOOLS` contiene metadatos de herramientas disponibles.
El agente filtra esos metadatos antes de ejecutar una capacidad diferida.

```javascript
const candidates = ALL_TOOLS.filter(({ name, description }) =>
  /node_repl/.test(`${name} ${description}`)
);
text(candidates.map(({ name, description }) => ({ name, description })));
```

Después, el agente utiliza el nombre y el esquema que devolvió el entorno.
El siguiente ejemplo ilustra la llamada indirecta dentro de ese mismo entorno.
El código requiere una herramienta descubierta y argumentos previamente validados.

```javascript
const selected = candidates.find(({ name }) => name === expectedName);
if (!selected) throw new Error("La herramienta requerida no está disponible");
const result = await tools[selected.name](validatedArguments);
text(result);
```

Estos objetos pertenecen al entorno observado.
El repositorio documenta el patrón, pero no implementa esos objetos.
No uses estos ejemplos como código universal para cualquier cliente MCP.

### Recursos y herramientas

`list_mcp_resources` enumera recursos compartidos por servidores.
No sustituye el descubrimiento del catálogo de herramientas.
Un servidor puede ofrecer herramientas sin publicar recursos.
Para descubrir capacidades de Apps, utiliza el mecanismo de herramientas que proporcione el entorno.
No consultes recursos como alternativa automática al descubrimiento de Apps.

## Ejecutar lecturas independientes

Agrupa consultas independientes cuando sus herramientas admitan ejecución paralela.
Inspecciona todos los resultados, incluidos los fallos.
Mantén las acciones dependientes y las modificaciones en secuencia.

```javascript
const results = await Promise.allSettled([
  tools[firstReadName](firstReadArguments),
  tools[secondReadName](secondReadArguments),
]);

for (const result of results) {
  if (result.status === "fulfilled") text(result.value);
  else text({ status: "failed", reason: String(result.reason) });
}
```

Este ejemplo aplica a lecturas autorizadas cuyos resultados no contienen secretos.
Resume los errores sensibles sin imprimir credenciales ni datos privados.
El paralelismo reduce esperas únicamente cuando las tareas son independientes.

## Tres entornos JavaScript diferentes

| Entorno observado | Estado entre llamadas | Uso |
|---|---|---|
| `functions.exec` | Cada llamada crea un contexto nuevo | Coordinar herramientas y resumir resultados |
| `mcp__node_repl__js` | Conserva variables hasta `js_reset` | Trabajo persistente con Node.js |
| `mcp__cua_repl.js` | Conserva sus propias referencias | Control mediante las APIs de computadora disponibles |

No transfieras referencias de objetos entre estos entornos.
Una variable del REPL de Node no aparece automáticamente en el REPL de computadora.
Las instrucciones de cada herramienta definen sus APIs permitidas.

### Node REPL

El entorno observado admite `await` y cargas dinámicas de módulos.
`js_add_node_module_dir` incorpora una ruta absoluta a `node_modules` para resolver dependencias.
Consulta su esquema antes de añadir la ruta autorizada.

Dentro de `mcp__node_repl__js`, puedes cargar un módulo así:

```javascript
var fs = await import("node:fs/promises");
var entries = await fs.readdir(nodeRepl.cwd);
nodeRepl.write({ entryCount: entries.length });
```

Conserva referencias útiles durante una tarea.
Publica resúmenes breves mediante `nodeRepl.write`.
Usa la función de imágenes del entorno cuando necesites inspección visual.

`js_reset` elimina las variables del REPL.
El reinicio no sustituye el cierre de navegadores, procesos o servicios externos.
Cierra cada recurso mediante su API antes de perder su referencia.
La disponibilidad del módulo y sus permisos siguen dependiendo del entorno.

### Navegador

Reutiliza el REPL persistente y Playwright cuando el entorno los ofrezca.
Mantén los perfiles del navegador en directorios temporales aislados.
No conectes Playwright a un perfil personal.
Comprueba el resultado visible después de una acción.
Las herramientas de computadora requieren su propio flujo de observación y acción.

La [guía del navegador](../.codex/browser/README.md) describe los límites portables.
Este repositorio no incluye cookies, perfiles ni navegadores descargados.

## Evidencia y límites

La sesión de preparación utilizó comandos locales para archivos, Git y Docker.
También utilizó búsqueda web y control de navegador mediante CUA.
El agente consultó los metadatos del REPL de Node mediante descubrimiento diferido.
El agente ejecutó dos llamadas al REPL y comprobó que una variable conservaba su estado.
El registro de publicación debe indicar las comprobaciones que realmente ejecutó.

El uso de Git no demuestra una conexión MCP con GitHub.
El uso de Docker no demuestra una conexión MCP con una base de datos.
La presencia de una herramienta tampoco confirma acceso, autorización o funcionamiento.

Publica nombres de capacidades y ejemplos sin credenciales.
Conserva endpoints privados, tokens y configuraciones de autenticación fuera del repositorio.

## Fuente y alcance

La [documentación oficial de OpenAI](https://learn.chatgpt.com/docs/extend/mcp) describe MCP y sus opciones de conexión.
Los nombres `ALL_TOOLS`, `functions.exec` y `mcp__node_repl__js` corresponden a observaciones del entorno de preparación.
Comprueba las herramientas reales al iniciar cada instalación.
