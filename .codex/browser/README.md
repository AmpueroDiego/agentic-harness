# Navegador para automatización

Esta carpeta no incluye navegadores, perfiles, cookies ni dependencias instaladas.

Cuando un proyecto requiera automatización web, instala Playwright localmente.
Usa un navegador autorizado y compatible con tu sistema.
Mantén cada perfil de trabajo en un directorio temporal aislado.
No conectes la automatización a un perfil personal.

Reutiliza la sesión Node REPL y el módulo Playwright entre llamadas.
Resuelve la dependencia desde el proyecto que la instaló.
Respeta las instrucciones del navegador integrado cuando esa herramienta esté disponible.

## Microsoft Edge con Playwright

El workspace de preparación comprobó navegación local con Microsoft Edge instalado y un perfil temporal de Playwright.
Esta opción utiliza un navegador del sistema y mantiene separado el perfil personal.
Requiere instalar Playwright en el proyecto y disponer del REPL de Node.

Después de registrar el directorio `node_modules` mediante la herramienta del REPL, carga la dependencia y abre Edge:

```javascript
var { createRequire } = await import("node:module");
// Sustituye esta ruta por el package.json del proyecto que tiene Playwright.
var requireBrowser = createRequire("C:/ruta/al/proyecto/package.json");
var playwright = requireBrowser("playwright");
var browser = await playwright.chromium.launch({ channel: "msedge", headless: true });
var context = await browser.newContext();
var page = await context.newPage();
var errors = [];
page.on("pageerror", error => errors.push(error.message));
await page.goto("http://localhost:3001/conversations", { waitUntil: "domcontentloaded" });
console.log({ url: page.url(), title: await page.title(), errors });
```

El puerto y la ruta son ejemplos; usa el destino autorizado de tu proyecto.
La sesión comprobada utilizó `executablePath` hacia Edge; el ejemplo usa el canal `msedge` para evitar rutas específicas del equipo.
Conserva las referencias mientras investigas y ejecuta `await browser.close()` al terminar.
Una navegación correcta no comprueba las vistas protegidas ni los flujos posteriores al login.

Los controles de seguridad del sistema deben permanecer activos.
Si el antivirus bloquea un navegador, consulta al administrador o utiliza otro navegador autorizado.
