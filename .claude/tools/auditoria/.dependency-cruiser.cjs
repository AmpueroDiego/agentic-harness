// Reglas de dependencias de web-app, derivadas de docs/web-app/architecture.md.
// Solo auditoría: nada de esto corre en el CI de web-app todavía.
const NO_PRODUCCION = "\\.test\\.tsx?$|test-setup\\.ts$|^src/testing/|routeTree\\.gen\\.ts$";

module.exports = {
  forbidden: [
    {
      name: "dominio-puro",
      comment: "src/domain no depende de features, infraestructura, app, rutas ni React.",
      severity: "error",
      from: { path: "^src/domain/" },
      to: { path: "^src/(features|infrastructure|app|routes|di)/|^node_modules/react" },
    },
    {
      name: "infraestructura-sin-ui",
      comment: "src/infrastructure (HTTP, sesión) no conoce features, app ni rutas.",
      severity: "error",
      from: { path: "^src/infrastructure/" },
      to: { path: "^src/(features|app|routes)/" },
    },
    {
      name: "ui-sin-http",
      comment: "Componentes y páginas no usan el cliente HTTP ni un adapter API directo: van por el port/provider.",
      severity: "error",
      from: { path: "^src/features/[^/]+/(components|pages)/" },
      to: { path: "^src/infrastructure/http/|\\.api-repository\\.ts$" },
    },
    {
      name: "sin-ciclos",
      comment: "Un ciclo de imports acopla los módulos que lo forman: ninguno se entiende ni cambia solo.",
      severity: "error",
      from: {},
      to: { circular: true },
    },
    {
      name: "feature-ajeno-por-dentro",
      comment: "Un feature no entra a las carpetas internas (components/state/data) de otro feature.",
      severity: "warn",
      from: { path: "^src/features/([^/]+)/" },
      to: {
        path: "^src/features/([^/]+)/(components|state|data)/",
        pathNot: "^src/features/$1/",
      },
    },
  ],
  options: {
    exclude: { path: NO_PRODUCCION },
    doNotFollow: { path: "node_modules" },
    tsPreCompilationDeps: true,
    tsConfig: { fileName: "tsconfig.app.json" },
  },
};
