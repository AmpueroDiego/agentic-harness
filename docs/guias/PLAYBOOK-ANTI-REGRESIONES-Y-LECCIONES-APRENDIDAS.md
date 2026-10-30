---
tipo: guia-oficial
fecha: 2026-08-27
tags: [playbook, heuristica, produccion, anti-regresiones, gobernanza, best-practices]
---

# Playbook anti-regresiones y lecciones aprendidas

> Este documento es una versión **genérica y sanitizada** de un playbook que nació en un
> proyecto real: cada regla de acá evitó (o corrigió) un bug que ya pasó en producción o en
> revisión de código. Se quitaron los nombres de repos, fechas, números de corrida/PR y
> cualquier dato del negocio original — lo que queda es el patrón. Adáptalo: agrega tus propias
> reglas con el mismo formato (problema → regla → cómo se aplica) a medida que tu propio equipo
> las descubra.

Todo agente de IA, desarrollador o revisor de código debería validar sus soluciones contra este
catálogo antes de dar por terminada una tarea. Cítalo, no lo copies dentro de cada agente — es
la fuente única; una copia que diverge es peor que no tener la regla.

---

## Índice

1. [Fallback seguro ante placeholders de configuración](#1-fallback-seguro-ante-placeholders-de-configuración)
2. [Identidad propia por servicio, nunca credenciales prestadas](#2-identidad-propia-por-servicio-nunca-credenciales-prestadas)
3. [Compatibilidad multiplataforma: SSL y redirección HTTPS en desarrollo](#3-compatibilidad-multiplataforma-ssl-y-redirección-https-en-desarrollo)
4. [CORS resiliente y tolerante en desarrollo local](#4-cors-resiliente-y-tolerante-en-desarrollo-local)
5. [Enums con valor por defecto necesitan un sentinel explícito](#5-enums-con-valor-por-defecto-necesitan-un-sentinel-explícito)
6. [Ruido de logging de un worker en background no es un error](#6-ruido-de-logging-de-un-worker-en-background-no-es-un-error)
7. [Idempotencia en flujos compuestos](#7-idempotencia-en-flujos-compuestos)
8. [Configuración homogénea entre servicios, con fallback transparente](#8-configuración-homogénea-entre-servicios-con-fallback-transparente)
9. [UTF-8 en la CLI de Windows](#9-utf-8-en-la-cli-de-windows)
10. [JWT: usar los tipos modernos del handler, no los legados](#10-jwt-usar-los-tipos-modernos-del-handler-no-los-legados)
11. [Normalización de claims de rol entre convenciones distintas](#11-normalización-de-claims-de-rol-entre-convenciones-distintas)
12. [Ninguna API auto-migra](#12-ninguna-api-auto-migra)
13. [Defensas que no defienden: guardas, `catch` y estados inalcanzables](#13-defensas-que-no-defienden-guardas-catch-y-estados-inalcanzables)
14. [Fusión defensiva e independiente de campos al consolidar entidades](#14-fusión-defensiva-e-independiente-de-campos-al-consolidar-entidades)
15. [Semántica HTML y estandarización de placeholders en UI](#15-semántica-html-y-estandarización-de-placeholders-en-ui)
16. [Gobernanza de revisiones automatizadas de código](#16-gobernanza-de-revisiones-automatizadas-de-código)
17. [Nunca `ON DELETE CASCADE` hacia una tabla de catálogo](#17-nunca-on-delete-cascade-hacia-una-tabla-de-catálogo)
18. ["No hay dato" y "no pude preguntar" son estados distintos](#18-no-hay-dato-y-no-pude-preguntar-son-estados-distintos)
19. [Principios de diseño: KISS, YAGNI, DRY, SOLID — refactorizar antes de construir encima](#19-principios-de-diseño-kiss-yagni-dry-solid--refactorizar-antes-de-construir-encima)
20. [El SQL crudo de un test es invisible para el compilador](#20-el-sql-crudo-de-un-test-es-invisible-para-el-compilador)
21. [Un PR, un tema — el tamaño es una alarma, no una ley](#21-un-pr-un-tema--el-tamaño-es-una-alarma-no-una-ley)
22. [Un build incremental miente en local, no en CI](#22-un-build-incremental-miente-en-local-no-en-ci)
23. [Comentarios de código: el porqué, en 1-3 líneas](#23-comentarios-de-código-el-porqué-en-1-3-líneas)
24. [Una lista, una sola fuente — y los restos que deja un renombre](#24-una-lista-una-sola-fuente--y-los-restos-que-deja-un-renombre)
25. [Política Estricta de Consentimiento y Cero Eliminaciones](#25-política-estricta-de-consentimiento-y-cero-eliminaciones)
26. [Estándar Oficial de Entrega en Trello y GitHub PR](#26-estándar-oficial-de-entrega-en-trello-y-github-pr)
27. [Windows 11 Smart App Control (0x800711C7) y Binarios en Desarrollo](#27-windows-11-smart-app-control-0x800711c7-y-binarios-en-desarrollo)
28. [Gobernanza del Vault de Obsidian: Nomenclatura kebab-case, Cero Pipes Escapados y Frontmatters](#28-gobernanza-del-vault-de-obsidian-nomenclatura-kebab-case-cero-pipes-escapados-y-frontmatters)
29. [Agrupación de campos y formato de progreso en una vista agregada](#29-agrupación-de-campos-y-formato-de-progreso-en-una-vista-agregada)
30. [Lo que Codex encontró 260 veces: checklist antes de abrir el PR](#30-lo-que-codex-encontró-260-veces-checklist-antes-de-abrir-el-pr)
31. [Valores fijos: catálogo MAESTRO + enum, nunca texto libre](#31-valores-fijos-catálogo-maestro--enum-nunca-texto-libre)
32. [Lecciones operativas del 13/10: hilos sin responder, worktrees y datos de seguridad](#32-lecciones-operativas-del-1310-hilos-sin-responder-worktrees-y-datos-de-seguridad)
33. [Lecciones de los últimos 50 PRs de api-core y web-app (2026-10-16)](#33-lecciones-de-los-últimos-50-prs-de-api-core-y-web-app-2026-10-16)
34. [Tests de integración: un solo SQL Server y tests de migración de vida corta](#34-tests-de-integración-un-solo-sql-server-y-tests-de-migración-de-vida-corta)
35. [Las reglas de negocio no leen texto: deciden por códigos guardados (2026-10-28)](#35-las-reglas-de-negocio-no-leen-texto-deciden-por-códigos-guardados-2026-10-28)
36. [Reglas aprendidas en los PRs del 28/10 (api-core #111, web-app #147, #150, #130)](#36-reglas-aprendidas-en-los-prs-del-2810-api-core-111-web-app-147-150-130)
37. [Una sola migración por PR mientras no esté aplicada (2026-10-28)](#37-una-sola-migración-por-pr-mientras-no-esté-aplicada-2026-10-28)

---

## 1. Fallback seguro ante placeholders de configuración

**El problema:** por política de cero secretos versionados, los archivos de configuración
comiteados llevan cadenas vacías (`""`) o un placeholder (`"REPLACE_ME"`). En la mayoría de los
lenguajes esas cadenas **no son nulas en memoria**, así que un operador de coalescencia normal
nunca llega al fallback:

```csharp
// Mal: "" o "REPLACE_ME" ya son un valor no nulo, `??` no evalúa lo de la derecha.
var url = _config["Servicio:Url"] ?? _config["URL_SERVICIO_LEGACY"];
```

**La regla:** filtrar siempre con un validador explícito que trate como *ausentes* el `null`,
la cadena vacía/solo-espacios y el placeholder (case-insensitive), **antes** de evaluar
cualquier fallback:

```csharp
private static bool EsValorConfiguradoValido(string? valor) =>
    !string.IsNullOrWhiteSpace(valor) && !valor.Trim().Equals("REPLACE_ME", StringComparison.OrdinalIgnoreCase);
```

Aplica igual en cualquier stack: el placeholder textual que usa tu equipo (`REPLACE_ME`,
`CHANGEME`, `TODO`) tiene que tratarse como ausencia, no como un valor real.

---

## 2. Identidad propia por servicio, nunca credenciales prestadas

**El problema:** al copiar el patrón de autenticación M2M de un servicio hermano, es fácil
copiar también su identidad (client id, cuenta de servicio) en vez de registrar una propia.

**La regla:** cada servicio se autentica ante el emisor de identidad con **su propia
identidad registrada**, nunca prestando la de otro. Sin esto, los logs y auditorías de
seguridad no pueden distinguir qué servicio hizo cada llamada — todo aparece como si lo
hubiera hecho el dueño original de la credencial prestada.

---

## 3. Compatibilidad multiplataforma: SSL y redirección HTTPS en desarrollo

**El problema:** en macOS, Safari y Chrome rechazan certificados SSL autofirmados de forma
más estricta que en Windows (`ERR_CERT_AUTHORITY_INVALID`). Si la redirección HTTPS está
activa en modo desarrollo, las llamadas HTTP se redirigen, el navegador corta la conexión y el
frontend/Swagger fallan con un error que **parece CORS y no lo es** (`TypeError: Failed to
fetch`).

**La regla:** nunca forzar redirección HTTPS en desarrollo:

```csharp
if (!app.Environment.IsDevelopment())
{
    app.UseHttpsRedirection();
}
```

Si tu equipo decide conscientemente no aplicar esto en todos los servicios (deuda aceptada),
documéntalo explícitamente — de lo contrario cada persona que desarrolla en Mac lo va a
redescubrir como bug nuevo.

---

## 4. CORS resiliente y tolerante en desarrollo local

**El problema:** un origen vacío o en placeholder en la configuración de CORS bloquea las
llamadas del frontend local (Vite, webpack-dev-server) contra la API.

**La regla:**
1. No duplicar el registro de CORS.
2. En desarrollo, o si los orígenes configurados están vacíos/en placeholder, usar una política
   tolerante (`SetIsOriginAllowed(_ => true)`), nunca fuera de desarrollo.

```csharp
if (builder.Environment.IsDevelopment() || allowedOrigins.Length == 0)
{
    policyBuilder.SetIsOriginAllowed(_ => true).AllowAnyHeader().AllowAnyMethod().AllowCredentials();
}
```

**Cuidado con la condición `|| allowedOrigins.Length == 0` sin el `IsDevelopment()`:** si un
ambiente de QA/prod pierde su configuración de orígenes por un despliegue incompleto, esa
condición sola abre CORS a cualquier origen con credenciales en producción. Verifica que la
condición de "tolerante" nunca se cumpla sola en un ambiente que no sea desarrollo.

---

## 5. Enums con valor por defecto necesitan un sentinel explícito

**El problema (EF Core, pero el patrón aplica a cualquier ORM):** si una propiedad enum no
tiene un valor `0` y se mapea con un valor por defecto generado por la base, el ORM puede emitir
una advertencia de validación de modelo en el arranque.

**La regla:** toda propiedad enum con valor por defecto generado por la base declara su
**sentinel** explícito:

```csharp
builder.Property(p => p.Tipo)
    .IsRequired()
    .HasDefaultValue(Tipo.Valor)
    .HasSentinel((Tipo)0);
```

---

## 6. Ruido de logging de un worker en background no es un error

**El problema:** un worker en background (poller, job programado) que consulta la base cada
cierto intervalo genera logs de nivel `Information` en desarrollo, llenando la consola con
queries rutinarias que parecen (y no son) un problema.

**La regla:** es comportamiento normal, no saturación ni fuga. Silenciarlo localmente bajando
el nivel de log del componente de acceso a datos, sin tocar el nivel de errores:

```json
"Logging": { "LogLevel": { "Microsoft.EntityFrameworkCore.Database.Command": "Warning" } }
```

---

## 7. Idempotencia en flujos compuestos

**El problema:** un flujo que vincula/asocia una entidad a otra (p. ej. un mensaje entrante sin
asignar, a una entidad) puede fallar con una excepción cuando el reintento del usuario recae sobre
un vínculo que ya existe, en vez de responder OK de forma idempotente.

**La regla:**
1. Si el dato todavía no tiene dueño, se asocia automáticamente al registrar la operación.
2. Si el dato ya pertenece al mismo destino que se está pidiendo, la operación es idempotente:
   responde OK sin excepción. Solo se rechaza si pertenece a un destino **distinto**.

---

## 8. Configuración homogénea entre servicios, con fallback transparente

**El problema:** cada servicio de un ecosistema inventa su propio nombre de clave de
configuración (`ConexionSql` en uno, `MiBaseDb` en otro), lo que genera inconsistencias al
desplegar y hace más difícil copiar patrones entre servicios.

**La regla:**
1. Una convención transversal de nombres de `ConnectionStrings` (y de cualquier sección de
   configuración compartida) en todos los servicios del ecosistema.
2. Un fallback transparente hacia el nombre legado, para no romper ambientes preexistentes al
   migrar la convención:
   ```csharp
   var conexion = configuration.GetConnectionString("NombreNuevo");
   if (!EsValorConfiguradoValido(conexion)) conexion = configuration.GetConnectionString("NombreLegado");
   ```
3. Caché de tokens/credenciales de sistema **obligatorio** antes de cualquier llamada HTTP de
   autenticación repetida — evita sobrecargar al emisor de identidad.
4. Configuraciones de integraciones externas **anidadas en su propia sección**, nunca como
   claves sueltas en la raíz del archivo de configuración.

---

## 9. UTF-8 en la CLI de Windows

**El problema:** PowerShell 5.1 usa codificación OEM (`CP850`/`Windows-1252`) por defecto. Al
pasar texto con tildes o emojis por pipe o como argumento directo a herramientas de CLI (`gh`,
clientes de tracker), los emojis se corrompen a `??`, los acentos a `?` y los caracteres
diacríticos a caracteres de control.

**La regla:**
1. Nunca pasar texto largo con tildes/emojis por pipe o argumento directo.
2. Escribirlo siempre en un archivo temporal **UTF-8 sin BOM** y pasarlo por la opción de
   archivo de la herramienta (`--body-file`, etc.).
3. En scripts `.ps1`, fijar la codificación de consola al inicio:
   ```powershell
   [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
   ```
4. Sobriedad tipográfica: evitar emojis decorativos en títulos/cuerpos que vayan a terminales o
   salida de CI — son justamente lo más propenso a corromperse.

---

## 10. JWT: usar los tipos modernos del handler, no los legados

**El problema (.NET, patrón general: no mezclar dos generaciones de una misma librería):** un
handler de JWT moderno puede usar internamente un tipo de token distinto del legado. Si un
delegado de validación de firma personalizado crea o retorna el tipo legado, el pipeline puede
lanzar una excepción de casteo o de firma no encontrada.

**La regla:** en cualquier delegado de validación personalizado, instanciar y retornar
siempre el tipo que la versión moderna del handler espera — nunca mezclar generaciones de la
misma librería de tokens dentro del mismo delegado.

---

## 11. Normalización de claims de rol entre convenciones distintas

**El problema:** los tokens emitidos por distintos servicios (o por versiones distintas de un
mismo emisor) pueden serializar el claim de rol bajo convenciones distintas: el estándar OpenID
(`role`), una convención propia (`rol`), o un URI legado de otro estándar (SOAP/WS-*). Un filtro
de autorización que solo busque una de las tres rechaza con 403 a usuarios válidos.

**La regla:** todo filtro de autorización personalizado evalúa la **unión** de las convenciones
de claim de rol que tu ecosistema realmente emite, no solo una.

---

## 12. Ninguna API auto-migra

**El problema real y recurrente:** se asume que "la estructura de tablas la crea la app,
automático". Casi nunca es así: si ninguna app llama al método de aplicar migraciones al
arrancar, y ningún pipeline de CI/CD corre el comando de migración, **nada aplica la migración
en un ambiente nuevo** salvo que alguien lo haga explícitamente desde afuera del despliegue.

**Por qué "en desarrollo parece automático":** si el equipo desarrolla apuntando a una base de
desarrollo compartida (no local), aplicar la migración desde la propia máquina ya migra esa
base compartida. El paso "manual" ocurrió, solo que antes de lo que parece. En un ambiente
realmente nuevo (QA, producción), nadie lo hizo todavía.

**El riesgo concreto — el fallo silencioso:** si se despliega código que escribe en una tabla
que no existe en ese ambiente, el `INSERT` falla; si el código que escribe tiene un `try/catch`
defensivo alrededor, el error se absorbe sin romper nada visible. El resultado es peor que un
crash: parece que todo funciona, la tabla queda vacía, y no hay ningún log de error porque nunca
se generó ninguno.

**Antes de dar una feature por desplegada** cuando escribe en una tabla nueva: verificar que la
tabla exista **en ese ambiente específico**, no asumirlo por el código o por otro ambiente.

**Una migración se revisa distinto a cualquier otro archivo, porque es de una sola vez.** El
código se corrige y se redespliega; una migración ya aplicada no se edita — el único arreglo es
otra migración que corrija lo que hizo la primera, y a diferencia de un bug de código (que da un
error), una migración mal hecha puede **borrar datos** sin aviso. Los cinco puntos que se miran,
en este orden, antes de aprobar cualquier migración:

| Qué | Por qué |
|---|---|
| Qué destruye el paso de subida (`Up`) | Cualquier operación de borrado de columna/tabla es irreversible en la práctica |
| Si el dato sobrevive | Que rellene **antes** de borrar, nunca al revés |
| Si el paso de bajada (`Down`) reconstruye de verdad | Si no, no hay marcha atrás |
| Si falla segura | Que aborte entera en vez de dejar el cambio a medias |
| Si la siembra es determinista | Fechas/ids literales, nunca "ahora mismo" — si no, cada regeneración produce ruido |

**Mientras una migración no se aplicó en ningún ambiente, sigue siendo editable** — lo correcto
cuando el generador automático produce algo que perdería datos. Pero "aplicada" no es blanco o
negro entre ambientes: puede estar aplicada en desarrollo y no en QA/producción. Antes de editar
una migración existente, confirmar que no corrió en ningún ambiente — editarla después de que
corrió en uno rompe ese ambiente sin que nadie se entere hasta que falla.

---

## 13. Defensas que no defienden: guardas, `catch` y estados inalcanzables

**El problema:** una defensa que se lee correcta y no protege nada. No falla, no da error, no
aparece en ningún log — el camino que debía cubrir simplemente nunca se recorre. Los tests pasan
porque el escenario **no es alcanzable**, no porque esté cubierto.

**Patrón raíz que lo produce, una y otra vez:** un servicio que convierte cualquier fallo en un
resultado "vacío" en vez de propagar el fallo:
```csharp
return response.IsSuccess ? response.Result : new List<T>();
```
Eso borra la diferencia entre "no hay datos" y "no pude preguntar" **antes** de que nadie aguas
abajo pueda verla — por más estados que declare el código que llama, ya no tiene información
para distinguirlos.

**La regla:**
1. **Mutar para verificar.** Una defensa está probada solo si borrarla pone algún test en rojo.
   Si la borras y todo sigue verde, no está protegiendo — está decorando.
2. **Sospechar del servicio que convierte todo fallo en resultado vacío**, y si el consumidor
   necesita distinguir "vacío" de "no disponible", el servicio debe propagar esa distinción, no
   colapsarla.
3. **Un estado nuevo nace con el test que demuestra que ocurre** por el canal real de fallo, no
   solo por un mock que lo fuerza.
4. **Una desviación deliberada de un patrón hermano se comenta, con el porqué** — si no, alguien
   "empareja la inconsistencia" más adelante y reintroduce el bug.

**Lo que este patrón dice del proceso de revisión:** cuando un cambio depende del comportamiento
de un componente que esa tarea no toca directamente, ese componente entra en el alcance de la
revisión aunque no aparezca en el diff.

---

## 14. Fusión defensiva e independiente de campos al consolidar entidades

**El problema:** al agrupar/consolidar registros que vienen de distintas llamadas o distintas
entidades del backend (p. ej. la misma entidad en varias relaciones), los datos de contacto e
identidad suelen llegar fragmentados: un registro trae un campo, otro trae el campo faltante.
Condicionar la fusión al estado de un array completo, o limitarla a solo algunos campos, provoca
pérdida silenciosa de datos válidos que el API sí devolvió.

**La regla:**
1. **Fusión atómica e independiente por campo escalar**, nunca condicionada al tamaño de un
   array global (`existente.campo ||= nuevo.campo ?? ""`).
2. **Fusión de listas de pares clave-valor** evaluando cada etiqueta individualmente, sin
   sobreescribir ni condicionarse al tamaño de la lista completa.
3. **Cobertura de tests que simulen expresamente la fragmentación cruzada** entre múltiples
   fuentes — no solo el caso feliz donde un registro trae todo.

---

## 15. Semántica HTML y estandarización de placeholders en UI

**El problema:**
1. Usar elementos de lista de descripción (`<dt>`/`<dd>`) sin su contenedor semántico
   (`<dl>`) rompe la especificación HTML y las asociaciones de accesibilidad en lectores de
   pantalla.
2. Renderizar textos explicativos largos ("Información no disponible") en paneles angostos por
   cada dato ausente genera ruido visual y empuja el layout.

**La regla:**
1. Toda fila clave-valor con `<dt>`/`<dd>` va contenida en un `<dl>`.
2. Un dato individual ausente se representa con un centinela visual estándar y corto (p. ej. un
   guion largo), no con una frase.
3. Una sección completa sin registros usa un componente de mensaje breve dedicado, no
   encabezados y filas vacías.

---

## 16. Gobernanza de revisiones automatizadas de código

**El problema:** invocar manualmente a un revisor de código con IA (Codex, CodeRabbit, etc.) en
cada push chico agota la cuota mensual asignada al repositorio.

**La regla:**
1. No disparar revisiones manuales tras cada ajuste menor.
2. Dejar que el revisor automático procese en su ciclo reactivo normal, o pedirlo explícitamente
   solo cuando el equipo lo necesita.
3. Consolidar observaciones y correr la suite local completa antes de entregar, en vez de confiar
   en que la siguiente revisión automática las va a atrapar.

---

## 17. Nunca `ON DELETE CASCADE` hacia una tabla de catálogo

**El origen de esta regla no fue un incidente — fue contrastar la documentación contra el
esquema real de la base y encontrar que decía lo contrario de lo que había.**

**La regla:** una FK que apunta a una tabla de catálogo (tipos, estados, categorías) se declara
**siempre `NO ACTION`**. `CASCADE` se reserva para relaciones de pertenencia real, donde la fila
hija no tiene sentido sin la madre.

**Por qué:** un catálogo no es dueño de nada, es una etiqueta. Con `CASCADE`, borrar **una fila
del catálogo** borra en cadena **todas las filas de negocio que la usaban** — sin error, sin
rastro, y sin recuperación salvo restaurar un backup. Es lo opuesto al soft-delete (marcar
inactivo), que deja la fila y es reversible.

**Lo que esta regla no prohíbe:** el `CASCADE` de herencia *table-per-type* de un ORM, donde la
fila hija **es** la madre vista como subtipo y no puede sobrevivirla — ahí quitarlo sería el
error opuesto.

**Por qué una FK así puede llevar tiempo sin explotar:** si la convención del equipo es
soft-delete, nadie ejecuta `DELETE` físico habitualmente. Pero esa es una convención que las
personas recuerdan; el `CASCADE` es una instrucción que el motor ejecuta sin excepción. Cuando
chocan, gana el motor — y basta un script de limpieza puntual o un mantenimiento manual para que
choquen.

**Cómo aplicar:**
1. Código nuevo: toda FK hacia un catálogo, `NO ACTION` explícito — que un borrado equivocado
   sea ruidoso (excepción de FK) en vez de silencioso.
2. Antes de cualquier `DELETE` físico: verificar contra el catálogo de foreign keys real de la
   base (`sys.foreign_keys` en SQL Server o equivalente), nunca contra la documentación.
3. Las FK existentes que violen la regla se corrigen como tarea aparte, con evidencia
   (`archivo:línea` o el nombre de la constraint) registrada donde el equipo lleve su backlog.

---

## 18. "No hay dato" y "no pude preguntar" son estados distintos

**La regla:** todo dato que viene de otro servicio tiene **tres** estados posibles, y los tres
tienen que poder distinguirse de punta a punta — del servicio al handler, del handler al DTO, y
del DTO a la UI:

| Estado | Significa | Cómo se representa |
|---|---|---|
| **Valor** | El servicio respondió y el dato existe | El valor real, incluido `0`, `""` o una lista vacía |
| **Vacío legítimo** | El servicio respondió y el dato no existe | `null` en un tipo nullable, **nunca** un sentinel |
| **No disponible** | El servicio no respondió, dio timeout o falló | Un estado explícito, separado del valor |

**Por qué:** un sentinel es un valor real disfrazado de ausencia. `0` no significa "no vino":
significa cero. Colapsar los tres estados en uno hace que el sistema mienta con confianza, y la
mentira es indistinguible de la verdad aguas abajo — nadie puede recuperar la diferencia
después. El caso real que motivó esta regla: un handler usaba `campo > 0 ? resumen : detalle`
tratando el `0` como "no vino", pero un registro **al día** legítimamente tiene ese campo en
cero — y terminaba mostrando el dato equivocado.

**Cómo aplicar:**
1. En el DTO: un campo que puede faltar se declara nullable y se resuelve con coalescencia
   simple, nunca con `> 0 ?`, `!= 0 ?` ni `?? 0`.
2. En el handler: si una llamada saliente puede fallar sin invalidar toda la respuesta, se
   envuelve y se expone un estado — no se deja propagar como error 500 general. Que falte un
   dato secundario no puede borrar el registro entero.
3. En la UI: "sin dato" y "no disponible" se muestran **distinto**.
4. Al revisar: ante cualquier `> 0 ?`, `!= 0 ?`, `?? 0`, `?? ""` o `[0]` sobre un dato externo,
   preguntar cuál de los tres estados se está perdiendo.

---

## 19. Principios de diseño: KISS, YAGNI, DRY, SOLID — refactorizar antes de construir encima

### La regla que manda sobre las demás

**Si lo que vas a tocar está mal, se arregla primero y en un commit aparte; después se
construye encima.** Nunca sumar una funcionalidad sobre una base que ya se sabe que está rota:
el arreglo se vuelve más caro cada vez, y quien viene después hereda las dos cosas. Si el
arreglo no entra en el alcance de la tarea actual, se dice explícitamente en el reporte y se
registra en el backlog — nunca se deja pasar en silencio.

### Los cuatro principios, en su forma concreta

- **KISS** — la solución más simple que resuelve el caso real. Un componente que hace dos cosas
  distintas según una bandera son dos componentes. Varias banderas booleanas que describen un
  mismo flujo son un estado con varios valores.
- **YAGNI** — no se construye para un futuro que nadie pidió. Si una abstracción existe y nadie
  la usa, se borra.
- **DRY** — la regla vive en un solo lugar. Ojo con la variante peligrosa: la **misma regla
  partida entre dos capas** (validación en el controlador y en el handler, o en el frontend y en
  el backend) — es peor que duplicarla junta, porque cambiar una sola y nadie lo nota.
- **SOLID** — de los cinco, los que más muerden en la práctica: **responsabilidad única**
  (archivos gigantes que mezclan varios dominios) y **segregación de interfaces** (un
  repositorio que expone varias responsabilidades no relacionadas a la vez).

### Un catálogo se pide completo; el filtro por activo se aplica solo donde se elige

**El error, en una línea: filtrar un catálogo por su flag de activo una sola vez, y usar esa
lista filtrada para dos cosas distintas** — para que alguien **elija** un valor, y para
**resolver** el valor que un registro ya tiene.

Para elegir, el filtro es correcto: nadie debería poder asignar un valor dado de baja. Para leer
lo histórico es un bug: el registro viejo apunta a una fila que la lista filtrada ya no
contiene, y lo que sigue es siempre alguna forma de degradación silenciosa — puede llegar a
perderse el estado real de un registro, no solo un texto.

**Las dos reglas:**
1. **Quien resuelve un dato histórico recibe el catálogo completo**, no el filtrado por activo.
   En el frontend, el filtrado y el completo son **dos variables distintas** (una para el
   `<select>`, otra para resolver), no la misma lista reusada.
2. **Nunca decidir por la descripción.** Comparar contra el texto de un estado (`.includes(...)`)
   es el parche que aparece cuando lo de arriba falla, y trae su propio bug: el texto existe para
   que lo lea una persona, y cambia. Si el id no resuelve, la respuesta es arreglar el catálogo
   que se pasó, no adivinar por el nombre.

### La barra: coherencia diseño↔código y modelo de datos

De todo lo que se puede medir de un backend, estas dos preguntas son la barra, no un promedio a
compensar con otras métricas:

- **Coherencia:** ¿lo que el diseño dice que pasa es lo que el código realmente hace? ¿Quedó
  alguna tabla, columna o abstracción creada pero sin usar por el camino real?
- **Modelo:** ¿se guarda texto donde va una relación? ¿hay dos identidades distintas para la
  misma fila? ¿alguna columna significa cosas distintas según la tabla?

Si alguna de las dos falla en lo que se tocó: se arregla en la misma tarea, o se reporta
explícitamente con `archivo:línea` — nunca se deja pasar en silencio.

### La sustitución silenciosa: "el primero de la lista" como respuesta a "no encontré"

Buscar el valor de un registro en un catálogo filtrado y, al no encontrarlo, caer en el primer
elemento de la lista, **no es un problema de presentación**: el valor real del registro queda
reemplazado en el modelo antes de que se renderice ningún control.

**La regla: "el primero de la lista" nunca es la respuesta para el valor que un registro ya
tiene.** Si el id no resuelve, se conserva el id crudo — es preferible que la persona vea un
valor que no reconoce, a que vea uno con cara de correcto pero equivocado. Un literal inventado
como último recurso (`?? "valor_por_defecto_inventado"`) es la misma falla con otra forma.
`lista[0]` sí es legítimo para **elegir** un valor nuevo por defecto — la diferencia siempre es
la misma: elegir algo nuevo vs. resolver algo que ya existía.

### Un `<select>` controlado con un valor ausente no falla: muestra el primero

Comportamiento del navegador, no del framework: si un control de selección tiene un valor que no
existe entre sus opciones, se renderiza la primera opción de la lista sin ningún aviso. La
persona ve un valor que no es el del registro, y al guardar se escribe el que vio, no el que el
registro tenía realmente.

**El patrón obligatorio:** si el valor del registro no está en la lista de opciones activas, se
inyecta su propia opción de contingencia (con la etiqueta resuelta contra el catálogo completo),
sin agregarla como elegible — solo para mostrar lo que el registro ya tiene. Y cada contingencia
de este tipo lleva su propio test que se pone en rojo al borrarla.

### El frontend nunca conoce filas del catálogo

Tres niveles de acoplamiento entre frontend y catálogo, y solo el tercero es correcto:

| Nivel | Qué conoce la pantalla | Qué lo rompe |
|---|---|---|
| 1 | La **descripción** de una fila | Renombrar la fila |
| 2 | El **código** de una fila | Agregar una fila nueva: sin comportamiento hasta que se despliegue |
| 3 | Un **significado** chico y cerrado que la fila trae | Nada: la fila nueva llega completa |

El frontend puede conocer un vocabulario chico y cerrado de *significados* (comportamientos);
nunca las filas concretas del catálogo, que el negocio agrega cuando quiere. Sustituir el código
por el identificador único de la fila no arregla esto — sigue siendo conocer una fila concreta.

### Hacer alcanzable una deuda conocida es una regresión

Una deuda documentada y dormida no es inofensiva: es inofensiva **mientras nada la alcance**. Si
algo compara contra valores fijos en vez de leer una tabla, y estaba anotado como deuda sin
molestar porque el frontend solo ofrecía valores conocidos, el día en que el frontend ofrezca más
opciones (una mejora, no un bug) esa deuda se convierte en un bug de datos real. Al ampliar lo
que alguien puede elegir, revisar qué suponía el otro lado sobre ese conjunto.

### Los cinco síntomas que más aparecen en revisión

| Síntoma | Cómo se ve |
|---|---|
| **Fat controller** | El controlador valida, transforma, decide u orquesta en vez de solo enrutar |
| **Smart UI** | Reglas de negocio solo en el cliente; el backend acepta cualquier cosa |
| **Validación solo del lado del cliente** | Cualquiera que llame a la API directo la saltea |
| **Cajón de sastre** | Un archivo de utilidades que junta cosas sin relación entre sí |
| **Modelo ajeno filtrado hacia adentro** | El DTO de otra API circula por la lógica propia en vez de traducirse una sola vez en la frontera |

### Cómo se aplica en una tarea

1. Antes de escribir: buscar si la regla, el componente o el formato ya existen y si están bien
   ubicados. Si existen y están mal ubicados, ese es el primer commit.
2. Al escribir: si aparece el tercer duplicado de algo, se extrae. Dos veces todavía puede ser
   coincidencia.
3. Al revisar: estos cinco síntomas son un hallazgo, no un comentario de estilo.
4. Lo que no entra en el alcance se anota con evidencia (`archivo:línea` y qué cuesta) y va al
   backlog del equipo.

---

## 20. El SQL crudo de un test es invisible para el compilador

Una migración borró una columna. El build pasó, todos los tests unitarios pasaron, y CI falló
con un error de columna inválida. El culpable: un test insertaba una fila con SQL crudo (a
propósito, para probar un `DEFAULT` sin pasar por el ORM) y seguía nombrando la columna vieja.

**Por qué ninguna red barata lo atrapa:** el compilador no ve dentro de un string SQL; los tests
unitarios mockean el acceso a datos (no hay columna que pueda faltar); el snapshot de modelo del
ORM no se entera (ese INSERT no pasa por el modelo). La única verificación que lo ve es una que
corra contra una base real.

**La regla:** si la rama contiene una migración que borra o renombra una columna, los tests de
integración **dejan de ser opcionales**, aunque el último commit sea de una sola línea. El
criterio se juzga por lo que toca la rama entera, no por el último cambio.

**Corolario que vale más allá de este caso:** todo lo que se escribe como texto y se ejecuta en
otro motor —SQL crudo, nombres de columna en un ORM basado en strings, rutas en strings, claves
de configuración— queda fuera del alcance del compilador. Cuando una migración cambia el
esquema, esos usos hay que buscarlos con una búsqueda de texto, porque nada más los va a
encontrar.

---

## 21. Un PR, un tema — el tamaño es una alarma, no una ley

**La regla principal es de cohesión, no de tamaño:**

> Si no podés escribir qué hace el PR en una frase sin usar "y", son dos PRs.

El tamaño es el síntoma, no la causa: un tema bien acotado casi siempre cae solo por debajo de
cualquier umbral razonable; un PR grande casi siempre trae dos temas adentro. Partir por líneas
un PR que mezcla dos temas lo deja peor —dos mitades incompletas—, así que primero se separa por
tema y recién después se mira el número.

**El número, como referencia:** la investigación pública sobre revisión de código ubica el punto
óptimo alrededor de ~200 líneas y el techo práctico en ~400 — pasado eso, la detección de
defectos por parte de un revisor humano se desploma, porque la atención sostenida sobre un diff
tiene un límite.

**Medir el diff revisable, no el contador crudo del sistema de control de versiones:** el
conteo de líneas de una herramienta de PR suele sumar archivos autogenerados (migraciones,
snapshots, lockfiles). Medir por ese número puede llevar a partir un PR que en realidad tenía
muy pocas líneas de producción real. Corré el conteo real (excluyendo tests y autogenerado)
antes de abrir el PR:

```bash
git diff --numstat <base>...HEAD | awk '
  $3 !~ /Tests\// && $3 !~ /\.Designer\.cs$/ && $3 !~ /ModelSnapshot\.cs$/ {s+=$1}
  END {print s" lineas revisables"}'
```

**Cuando el tema es genuinamente grande:** se entrega **por partes que funcionen solas**, nunca
en mitades que no compilan. Una entrega parcial que pasa CI y no rompe nada es revisable; media
refactorización no lo es.

---

## 22. Un build incremental miente en local, no en CI

Un campo agregado a un objeto de test, por un error de script, quedó con una propiedad
duplicada. El build incremental local (que usa caché para saltarse lo que cree ya compilado):
limpio. Los tests locales: en verde. CI, con el árbol limpio desde cero: error de compilación
real.

**La causa no es que el build no mire los tests** — sí los mira: es que un build *incremental*
usa un archivo de estado para saltarse lo que cree ya compilado. En un árbol de trabajo que viene
compilando hace rato, un archivo puede quedar fuera de la pasada. CI arranca limpio y compila
todo, por eso ve lo que local no ve.

**Cómo verificar de verdad antes de subir un cambio:** correr la variante *sin caché* de tu
herramienta de build/typecheck (`tsc --noEmit` sin `-b`, un build limpio forzado, etc.), no la
incremental.

**La forma general:** una verificación con caché responde "no cambió nada desde la última vez",
no "esto está bien". Vale para cualquier herramienta incremental (compiladores, linters con
caché, tareas de build). Cuando el resultado va a alimentar una decisión de PR/deploy, la pasada
que cuenta es la que arranca de cero.

---

## 23. Comentarios de código: el porqué, en 1-3 líneas

Un análisis real de dos PRs encontró que **~19% de las líneas agregadas eran comentario**, con
bloques de 7 a 12 líneas explicando una función de una sola línea. El comentario era, en
realidad, la justificación para quien revisaba, y quedó para siempre en el código.

1. **Explica el porqué, no el qué.** Si el código ya dice lo que hace, el comentario sobra.
2. **Una a tres líneas.** Si necesita un párrafo, casi siempre falta un nombre mejor o una
   función aparte.
3. **Nada de historia en el código:** ni "antes de este cambio…", ni fechas, ni números de
   corrida/PR. Eso va al mensaje de commit o a la descripción del PR, donde queda fechado y
   ligado al cambio; en el código envejece y nadie lo corrige.
4. **Documentación de API pública (TSDoc/XMLDoc) solo en lo exportado:** qué recibe, qué
   devuelve, qué no es obvio — no para defender una decisión de diseño.
5. **Nunca nombres de personas** en comentarios, mensajes de commit ni PRs — se escribe la
   decisión, no quién la tomó.

```ts
// Mal: 9 líneas de historia y justificación para una línea de código.
// Bien:
// Sin código: "" no coincide con ningún valor real y cae al camino neutro.
function mapCodigoAValor(codigo: string | null | undefined): Valor {
  return codigo ?? "";
}
```

---

## 24. Una lista, una sola fuente — y los restos que deja un renombre

Después de unificar un valor al código de su catálogo, quedaron restos que nadie vio en la
revisión: funciones `switch` que devolvían exactamente lo mismo que recibían, la misma lista de
valores escrita por separado en tres lugares, y varias constantes que había que importar una por
una.

1. **Cada lista de valores se escribe una sola vez**, y de ella se derivan el tipo y la
   comprobación de pertenencia. Si la misma lista está en un tipo unión, en un arreglo y en una
   función de comparación manual, se desincronizan sin que el compilador avise.
   ```ts
   export const VALORES = [Codigos.A, Codigos.B, Codigos.C] as const;
   export type Valor = (typeof VALORES)[number];
   export const esValorValido = (v: string | null | undefined): v is Valor => VALORES.includes(v as Valor);
   ```
2. **Al cerrar un renombre, buscar las "traducciones" que quedaron vacías:** un `switch` o un
   mapa donde cada caso devuelve lo mismo que recibe. Ninguna herramienta automática lo detecta
   sola — lo atrapa la revisión humana.
3. **Un valor por defecto que asume algo se deja explícito y con test**, nunca escondido en un
   `default:` sin explicación ni cobertura.
4. **Los imports van arriba.** Una declaración en medio de los imports es casi siempre un resto
   de una edición mecánica.
5. **Dos funciones parecidas con nombres distintos no son sobrecarga**, y dos copias son
   coincidencia — se extrae recién al tercer duplicado (sección 19). Sobrecarga real es el mismo
   nombre con firmas distintas.

---

## 25. Política Estricta de Consentimiento y Cero Eliminaciones

* **NUNCA ELIMINAR NADA:** Prohibido purgar tarjetas de Trello, comentarios, adjuntos, ramas remotas, código, tablas o archivos sin instrucción explícita e inequívoca del usuario.
* **CONSENTIMIENTO PREVIO OBLIGATORIO:** Antes de ejecutar cualquier mutación en Trello (mover columna, modificar descripción, asignar miembros, adjuntar archivos) o cualquier acción destructiva en Git/BD, el agente debe presentar la propuesta exacta y esperar la aprobación expresa del usuario (*"procede"*, *"dale"*).

---

## 26. Estándar Oficial de Entrega en Trello y GitHub PR

1. **Títulos de Tarjetas:** El título de una tarjeta existente **se respeta al 100%** (prohibido renombrarla).
2. **Columna Destino:** Se mueven a **`En revisión (Revisor Principal)`** solo cuando el responsable lo pide expresamente; abrir el PR no mueve la tarjeta. Hay otra columna `En revisión (Revisor Secundario)`: resolver siempre por nombre exacto contra el tablero vivo.
3. **Miembros Obligatorios al entregar (2 personas):**
   * `<responsable>` (el responsable)
   * `<revisor-principal>` (Revisor Principal) — resolver por el identificador configurado del Revisor Principal, sin confundirlo con otros colaboradores.
4. **Etiquetas Oficiales:**
   * Backend: 🟢 **`Backend`** + 🔴 **`Migración`**
   * Frontend: 🔵 **`Frontend`**
5. **Integración GitHub:** Vincular el PR como **adjunto nativo del Power-Up de GitHub** (`#<num> <título>`). **PROHIBIDO poner comentarios redundantes con enlaces del PR** en la tarjeta; la integración del Power-Up es limpia y autosuficiente.
6. **Automatización:** Ejecutable con `gh pr create --base develop` y la skill `/trello` (`.claude/tools/trello/trello.py`). `scripts/trello.ps1` no conecta en la máquina del responsable.

---

## 27. Windows 11 Smart App Control (0x800711C7) y Binarios en Desarrollo

* **El Problema:** Al compilar código en Windows 11 con Smart App Control (SAC) en modo de aplicación o evaluación, Windows puede bloquear repentinamente DLLs recién emitidas por el compilador con la excepción:
  `System.IO.FileLoadException: Could not load file or assembly 'Rest.dll'. An Application Control policy has blocked this file. (0x800711C7)` (Evento 3077/3118 en `CodeIntegrity/Operational`).
* **La Regla de Oro:**
  1. No realizar ejecuciones agresivas de `dotnet clean` repetitivas que fuercen la reemisión de ensamblados en carpetas de depuración cuando la política de integridad de código esté activa.
  2. Para entornos de desarrollo en Windows, los desarrolladores deben activar **Modo de Desarrollador** en Windows Settings (`Configuración > Sistema > Para programadores > Modo de desarrollador`) o agregar exclusión de Defender sobre la ruta de repositorios.
  3. Reconstruir con `dotnet build` incremental preserva los hashes y minimiza bloqueos de Code Integrity.

---

## 28. Gobernanza del Vault de Obsidian: Nomenclatura kebab-case, Cero Pipes Escapados y Frontmatters

* **El Problema:**
  1. **Nombres con caracteres especiales y espacios** (`Terminado_Preparacin_de_Ambiente...`) generaron corrupciones con caracteres de reemplazo (`\ufffd`) y mojibake (`<texto-corrupto>`) en sistemas Windows.
  2. **Pipes escapados (`|`) en wikilinks** (`[[0001-integracion...|ADR-0001]]`) provocaron que Obsidian buscase archivos inexistentes terminados en `\`, rompiendo la resolución de aristas en el Graph View.
  3. **Notas sin frontmatter YAML** provocaron que Dataview en `Home.md` omitiera corridas y métricas de tokens.
  4. **Notas huérfanas** creadas sin enlazarse en los índices padre (`docs/adr/README.md`, `docs/trello/README.md`, `contexto-negocio/README.md`).

* **La Regla de Oro:**
  1. **Nomenclatura Estricta:** Todo archivo Markdown debe nombrarse en minúsculas con guiones (`kebab-case.md`), sin espacios, sin tildes y sin caracteres especiales.
  2. **Codificación UTF-8 sin BOM:** Todos los archivos deben escribirse explícitamente en UTF-8 sin BOM.
  3. **Sintaxis Nativa de Wikilinks:** Usar siempre `[[ruta/nota|Alias]]` sin escapar jamás la barra vertical (`|`).
  4. **Frontmatter YAML Obligatorio:** Toda nota debe iniciar con su bloque frontmatter (`tipo:`, `fecha:`, `tags:`).
  5. **Trazabilidad Continua:** Toda nota debe tener al menos un enlace entrante desde su índice correspondiente.
  6. **Validación Automática:** Ejecutar `python scripts/validar-vault.py` para asegurar 0 fallos de calidad antes de cerrar cualquier tarea documental.

---

## 29. Agrupación de campos y formato de progreso en una vista agregada

**El problema:** más de veinte campos en una lista plana ocultan la jerarquía del dominio.

**La regla:** agruparlos en tres secciones semánticas: datos de la entidad principal,
datos de una entidad relacionada y datos de su agrupación. La clasificación concreta
de los campos la define el dominio, nunca el agente por su cuenta.

Un indicador compuesto mantiene un formato uniforme:

`completados / total (pendientes)`

El texto entre paréntesis se resalta con el token de alerta del tema cuando
`pendientes < total`; si `pendientes == total` (cero completados), usa color neutro.
Los significados y el color se validan con el responsable del dominio antes de copiar
el ejemplo a otro producto. La agrupación y la fórmula no sustituyen los estados de
disponibilidad parcial o fallida de la sección 18.

## 30. Lo que Codex encontró 260 veces: checklist antes de abrir el PR

*(2026-10-02. Salió de leer los 260 hallazgos de Codex en 44 PRs de api-core y web-app: 74 P1, 179 P2, 7 P3. Se agruparon a mano por título; los conteos son aproximados. Casi todos eran de unas pocas familias que se repiten PR tras PR; web-app #63 sola sumó más de 35. Cada punto es lo que hay que comprobar **antes** de pedir revisión, no después.)*

### web-app

1. **Respuesta tardía: toda lectura o escritura asíncrona que toca el store compara, al volver, la sesión, el registro o la pestaña que tenía al lanzarse, y se descarta si cambió.** Es la familia más grande (~35: web-app #6, #12, #55, #56, #63). Incluye reintentos, refrescos, subidas de archivo y comandos en cola: se atan a la generación de sesión. Una prueba por familia: lanzar la operación, cambiar de registro/cuenta, resolverla, y comprobar que no pisó nada.
2. **Mientras hay un envío o una asignación en curso, el formulario y la tecla Enter quedan bloqueados.** Guardar con la versión vieja del recurso da 409 y el agente pierde lo que escribió (web-app #13, #14, #63).
3. **Un borrador no se borra hasta que el envío salió bien**, se conserva lo tipeado mientras se envía y se guarda por conversación o registro, no uno global (web-app #1, #4, #13).
4. **Orden de efectos: se guarda el id de lo creado antes del paso siguiente, y si el segundo paso falla se conserva y se reusa lo creado.** No se enlaza ni se marca nada hasta que la promoción terminó bien (web-app #4, #12). **Si el POST salió bien y la lectura posterior falla, la acción no se rehabilita**: se oculta, se avisa y se ofrece «Recargar», que nunca repite el POST (si no, el segundo clic da 409; web-app #73).
5. **Error no es vacío** (sección 18): una carga parcial o fallida no se muestra como "sin datos", y lo que sí llegó no se oculta (web-app #12, #61, #63). **Un estado «no disponible» (`contractsStatus === "NoDisponible"`) nunca se pinta igual que «no hay»**: etiqueta distinta en cada pantalla que lo muestre, no solo en la primera (web-app #73).
6. **URL y estado se sincronizan en cada transición**: abrir, cerrar la pestaña activa, cerrar la última, finalizar el registro y reemplazar un registro sintético por el real (web-app #6, #13, #14). **Todo camino que abre un registro, también el recién creado o convertido, termina en `goToView("console", id)` solo si la apertura salió bien**; antes de agregar un camino nuevo, buscar con `grep "abrirClientePorIdentificador("` quién más abre registros y comparar (web-app #73).
7. **Teclado y lectores de pantalla**: todo lo que se hace con mouse tiene su equivalente; el foco y la selección van juntos; si el elemento enfocado desaparece, el foco pasa a un destino válido (**un popup o lista que se cierra con Enter o Esc devuelve el foco a su botón disparador**, con un `ref`, como `AgentStatusMenu`; web-app #73); lo truncado se puede ver completo sin pasar el mouse; un popup se limita al contenedor que recorta y scrollea (web-app #13, #61, #63, #64, #65).
8. **Catálogos**: la etiqueta se resuelve contra todo el catálogo (también inactivos) para leer, y solo los activos se ofrecen para elegir; un código vacío nunca se resuelve (web-app #4, #50; ver sección 19).
9. **El repositorio mock hace lo mismo que el API.** Cada regla nueva del API se refleja en el mock en el mismo PR (web-app #4, #12, #13).
10. **Escalas y formatos se convierten en el borde**: calidad de cierre a la escala numérica del API, fechas sin corrimiento de zona horaria, `content type` del adjunto, valor cero distinto de ausente (web-app #4, #6, #8, #12).
11. **Un filtro por un campo opcional trata `null` y ausente como «sin restricción», nunca como «no coincide».** `item.campo === valor` sobre un campo que el API puede no mandar deja la lista vacía y el agente sin opciones. Se usa `== null ||` y hay una prueba con el campo ausente (web-app #73: clasificaciones sin `tipoServicioId`).
12. **Lo que es del cliente se actualiza en todas las pestañas del mismo cliente.** Registros y eventos pertenecen al identificador, no a la pestaña: al refrescar uno, se propagan a las demás entradas con ese identificador sin pisar su borrador ni su estado propio. Una prueba con dos pestañas del mismo identificador: guardar en una y ver el cambio en la otra (web-app #73).
13. **Si el contexto activo puede venir incompleto o sintetizado, al formulario se le pasa la versión resuelta, no el resultado de buscar en la colección incompleta.** Buscar solo en `registrosCliente` entrega `undefined` y el formulario pierde el filtro por servicio (web-app #73: `buildRegistroOptions` ya sintetizaba el registro activo).

*Qué falló en #73 (2026-10-07):* 7 hallazgos de Codex en un PR, y 4 ya estaban en esta lista (4, 5, 6 y 7). Leer la lista no alcanzó. Por eso el `## Coder Report` de `coder-web` lleva una sección «Checklist sección 30» con **evidencia por punto** (la prueba o «no aplica» y por qué), y QA marca como hallazgo propio el punto aplicable sin prueba.

### api-core

1. **El efecto externo va después de resolver y persistir** (regla 1 de `CLAUDE.md`): marcar el correo como visto solo tras guardar, reportar la entrega solo con el adjunto ya cargado, resolver la persona antes de enviar (api-core #14, #50).
2. **Varias escrituras relacionadas van en una transacción y se pueden reintentar sin duplicar**; las filas de la bandeja de salida se reclaman de forma atómica (api-core #9, #14, #50, #65).
3. **Una migración con datos preserva antes de reemplazar**: remapear antes de borrar un seed, deduplicar antes de un índice único, guardar la identidad antes de cambiar columnas, y dejar el despliegue aplicándola (sección 12; api-core #14, #21, #24, #26).
4. **Error de una dependencia no es ausencia**: se lanza, no se devuelve una lista vacía ni un "Ok" (sección 18; api-core #19, #20, #22, #64).
5. **Secretos y placeholders** (sección 1): un placeholder se rechaza, las credenciales no viven en el compose, el token de Sonar solo existe en los pasos del escáner, y en los logs no entran teléfonos ni GUID (api-core #14, #15, #55 a #58).
6. **Telemetría**: una cancelación normal no es un error, y el fallo que un proceso en segundo plano absorbe sí se registra, sin datos personales (api-core #56 a #58).
7. **Un comando sobre un recurso versionado devuelve la versión nueva y los campos ya poblados**, y revalida el estado antes de responder que no había nada que hacer (api-core #66).
8. **Toda búsqueda tiene un tope** que no depende de cuántos resultados se aceptaron (api-core #19).

## 31. Valores fijos: catálogo MAESTRO + enum, nunca texto libre

*(2026-10-06, a pedido del responsable. Salió de `Registro.ResultadoCierre`: un texto libre que obligó a traducir con un `switch` en api-core y otra vez en web-app.)*

Todos los repos hermanos (api-contracts, api-people, api-delivery, api-accounting) guardan sus
estados y tipos igual. Antes de agregar un campo con un conjunto cerrado de valores, elegir el
patrón por lo que el valor **es**:

| El valor es… | Patrón | Ejemplo en api-core |
|---|---|---|
| Estado o tipo de **negocio** que se guarda | Tabla `MAESTRO.<X>` + `<X>Enum` con `[Id]`/`[Detail]`/`[Code]` + FK `<X>Id` en la entidad. El seed sale del enum (`GetId()`, `GetDetail()`, `GetCode()`), así no hay Guid copiado a mano | `EstadoRegistro`, `Canal`, `Clasificacion`, `TipoServicio` (`EstadoRegistroConfiguration.cs`) |
| Código que el enum necesita como `const` (atributos, defaults) | Clase `<X>Codigos` que el enum referencia en su `[Code]`: es parte del patrón de arriba, no un reemplazo | `EstadoRegistroCodigos`, `CanalCodigos` |
| Catálogo de **otro servicio** | Solo sus Ids como constantes; la tabla vive en el dueño | `TipoParticipanteIds` (api-contracts) |
| **Plomería interna** que el negocio no lee | Enum guardado como `int` | Outbox, reintentos |
| Solo **viaja en la API**, no se guarda | Enum en el DTO | `EstadoSeccionEnum`, `TipoContenidoPlantilla` |

1. **Nunca texto libre para un valor de negocio.** Un `string` con "Manual"/"Registro" escrito en
   varios archivos acepta cualquier typo como valor nuevo y termina en un `switch` que traduce.
2. **La etiqueta vive en el catálogo**, no en un `switch` del backend ni repetida en el front.
3. **Deuda conocida (2026-10-06)**: `Registro.ResultadoCierre` (tarjeta <card-id>) e
   `Interaccion.Origen` (tarjeta <card-id>) son texto libre; `Interaccion.Tipo` es un enum de
   negocio guardado como `int` sin tabla; `Mensaje.Estado` es texto (mensajería, fuera del corte
   del 15/10). No se copia ninguno de estos como referencia.

## 32. Lecciones operativas del 13/10: hilos sin responder, worktrees y datos de seguridad

*(2026-10-13, a pedido del responsable, tras revisar el estado de `/supercodex` y arrancar la tarjeta <card-id>.)*

### Ninguna ronda nueva con un hilo sin responder

El 13/10 quedaron 11 hilos de Codex con **un solo comentario, el de Codex** (api-core #80; web-app #103, #107, #108). En #80 Codex repitió el mismo P2 en 3 revisiones sobre el mismo commit, y en #107 se pidió `@codex review` 27 segundos después de que llegara un hilo nuevo.

1. Antes de cada `@codex review`, contar los hilos abiertos **y** los comentarios de Codex sin respuesta nuestra. Si hay alguno, primero se corrige o se responde, y recién después se pide la ronda.
2. Pedir otra ronda sobre el mismo commit con un hallazgo abierto no lo limpia: Codex lo vuelve a encontrar.
3. Cada ronda se anota en `docs/agent-runs/supercodex-rondas.md` cuando se lee. El 13/10 el registro seguía en el 12/10 con 10 PRs rondando, y el estado hubo que reconstruirlo desde GitHub.

### `git -C <repo> worktree add` resuelve la ruta relativa desde el repo

`git -C api-core worktree add .worktrees/x` crea `api-core/.worktrees/x`, no `AcmeOrg/.worktrees/x`. La ruta del worktree siempre va **absoluta**. Si ya quedó mal, se arregla con `git worktree move <ruta-actual> <ruta-absoluta>`, nunca borrando la carpeta.

### Un traspaso o una nota se verifica antes de usarla

El traspaso de <card-id> nombraba `Common/TenantEnum.cs`, pero el archivo real es `Domain/Aggregates/Common/Enum/TenantEnum.cs`. Antes de pasarle una ruta a un agente se comprueba con `Glob`/`grep`.

### Roles y país en api-auth: mirar los datos antes de diseñar

- `UsuarioRepository.GetRolesRutasPermisosByUserId` trae los `PaisRol` vigentes del usuario de **todos los países y todas las aplicaciones**; `idAplicacion` solo filtra los permisos. Un claim derivado de ahí sin filtrar mezcla países.
- api-core autoriza `Roles = "Agente,Supervisor"`, pero en seguridad-db no existe ningún rol `Supervisor`, y el rol `Agente` solo tenía `PaisRol` en la región configurada. Antes de asumir que un rol o un país "ya está", hay que verlo en `Rol.Rol` y `PaisRol.PaisRol`.
- El MCP `seguridad-db` tiene `execute_query` deshabilitado: solo hay `sample_data`, con un máximo de 100 filas y sin joins. Lo que no se puede comprobar así se marca **NO VERIFICADO** en el plan. No se da por cierto.

## 33. Lecciones de los últimos 50 PRs de api-core y web-app (2026-10-16)

*(2026-10-16, aprobado por el responsable. Salió de leer los hallazgos de Codex en api-core #36–#85 (98: 21 P1, 75 P2) y web-app #60–#109 (244: 3 P1, 227 P2). Revisor Principal aprobó con «Ok» sin hallazgos en línea, así que todo viene de Codex.)*

Casi todo ya estaba escrito (§1, §7, §12, §18, §19, §30) y se volvió a romper: en api-core, los puntos 3, 5, 6 y 7 de §30 se violaron en PRs abiertos después del 02/10; en web-app, el mismo `aria-hidden` y el mismo `tabIndex` volvieron un PR después de corregirlos. Leer la lista no alcanza. Por eso cada regla de acá lleva su **control**: uno automático (test, lint o hook) o un punto de checklist que exige evidencia con nombre. Los controles automáticos marcados «pendiente: tarjeta» se implementan en tarjetas aparte, no en el PR que agrega esta sección.

### api-core

**A. Todo lo que guarda o publica un dato por país lleva el país: el `CoreDbContext` del scope, la clave de caché, el grupo de SignalR, la cabecera `X-Tenant` saliente y el scope de cada job. El país lo da solo `ITenantResolver` (hoy desde `X-Tenant`; con la tarjeta <card-id> pasa al claim del JWT): nadie lee la cabecera por su cuenta.**
- Por qué: api-core #79, #80 y #81 (13 hallazgos, 7 P1). En #80 un JWT de `Agente` elegía la base de RegionB mandando `X-Tenant: RegionB`; la caché de canales y el grupo `cliente-{personaId}` no tenían país (rompe también la regla 3 de `CLAUDE.md`).
- Cómo se verifica: el plan lista esos 5 lugares con su archivo; un test alterna la región configurada y RegionB en el mismo proceso y cubre caché, grupo y cabecera.
- Control: test de arquitectura (sin literales `"Core:"`/`"cliente-"` fuera de su helper con tenant; ningún `extraHeaders: null` en `Services/API/**`; todo `CreateScope()` de jobs fija el tenant), partiendo de `PersistenceRegistrationTenantTests` y `TenantResolverTests`. Pendiente: tarjeta.

**B. Todo comando que modifica un `Registro` o le cuelga algo recibe la `Version` que vio el agente: 409 si está vieja, 400 si falta. El request la declara obligatoria y la respuesta devuelve la nueva. Si solo inserta en una tabla hija, toma `BloquearFilaYVerificarCerrado` antes de validar.**
- Por qué: amplía §30 api-core 7, que se violó después de escrita en #71 (Reabrir sin `Version`, encontrado dos veces), #74 (interacción tras un cierre concurrente) y #82 (`Version` como `string?` en el request).
- Cómo se verifica: un test por comando: cargar V, cerrar y reabrir desde otro request, mandar V → 409.
- Control: test de arquitectura (todo `*Command` que hace `Update` sobre `Registro` declara `Version` obligatoria en su `*Request` (`[Required]` en el parámetro del record, no en la propiedad: ver la lección del record posicional en «Proceso»); todo handler que inserta una `Interaccion` sobre un registro existente llama a `BloquearFilaYVerificarCerrado`). Pendiente: tarjeta (encaja en `exigir-version-al-editar-registro`).

**C. Ningún cambio de estado borra historial: antes de poner en `null` o sobrescribir un campo de cierre, asignación o estado, se guarda una interacción con el valor anterior, en el mismo `Complete()`. Un dato heredado sin procedencia queda como desconocido; nunca se atribuye al usuario actual.**
- Por qué: prioridad 2 de `CLAUDE.md`, sin regla en el playbook. api-core #71 (P1: reabrir borraba `ResultadoCierre` y `NotaCierre` sin registro; 6 de los 13 re-hallazgos) y #55 (un mensaje de MensajeriaExterna con fecha fuera de rango se descartaba entero en vez de guardarse con ese campo vacío).
- Cómo se verifica: el test de cada transición comprueba que las interacciones del registro suben en 1 con el tipo correcto; con columnas de cierre `NULL` sembradas, no se inventa autor.
- Control: checklist de QA, con evidencia: toda asignación `= null`/`default` sobre `FechaCierre`, `IdUsuarioCierre`, `ResultadoCierreId` o `NotaCierre` sin un `Interaccion.Crear…` antes en el mismo handler es hallazgo. Si se repite, pasa a test de búsqueda sobre el fuente.

**D. Una migración se prueba contra una base con filas, y una tabla temporal se toca con el versionado apagado.** Amplía §12 con lo nuevo:
1. Un `DEFAULT ''` o de fecha mínima es solo para el backfill y se quita en la misma migración.
2. Ninguna guarda (`THROW`) que pida corregir datos dentro de la misma transacción: la columna en una migración, la restricción en otra.
3. `UPDATE` sobre una temporal con `SYSTEM_VERSIONING = OFF`, tocando la tabla y su `History`, y se reactiva una sola vez.
4. `PeriodStart` de las filas existentes es la fecha de la migración, no `0001-01-01`.
5. Un backfill que elige un ganador ordena por la fecha de vinculación; si no puede decidir, no siembra.
- Por qué: #43 (P1, el `THROW` revertía la columna), #70 (`PeriodStart = 0001-01-01`), #75 (el `UPDATE` con versionado activo dejó en `RegistroHistory` una edición que nadie hizo), #50. Todos posteriores a §12.
- Cómo se verifica: patrón `MigracionHistorica_FilasPreviasComienzanEnLaFechaDeMigracion`; en temporales, además, `COUNT(*)` de `*History` no cambia con el backfill.
- Control: hook `check-migraciones.py` (molde de `check-maxlength.py`) que avisa ante `defaultValue: ""` sin `AlterColumn` posterior, `new DateTime(1, 1, 1`, `THROW`/`RAISERROR` en `Sql(...)` y `UPDATE` sobre tabla temporal sin `SYSTEM_VERSIONING = OFF`. Pendiente: tarjeta.

**E. Ningún header sensible, id de proveedor ni token llega a un log, a la telemetría ni a un paso de CI que corre código del PR.** Ya está en §1 y §30 api-core 5; lo nuevo:
- La redacción de `Authorization`, `X-Api-Key`, `Cookie` y `Set-Cookie` vive en un solo helper que usan `ExceptionMiddleware` y `RequestResponseLoggingHandler`; un id de proveedor va con hash; una URL saliente se redacta por plantilla de ruta. Un workflow con secretos no se dispara por `pull_request_review` ni `pull_request_target`, y el secreto va en el `env` del paso, no del job.
- Por qué: #76 (P1, `TRELLO_TOKEN` y un `GITHUB_TOKEN` de escritura con `pull_request_review`) y #78 (P1 en código viejo: el bearer y la `X-Api-Key` de PROVEEDOR_MENSAJERIA guardados en `RequestResponseLog`); también #55, #56 y #58.
- Cómo se verifica: test unitario del helper con los 4 headers y test del handler con una respuesta 500 que mira la fila guardada.
- Control: test de arquitectura (nadie fuera del helper serializa `Headers`) y rechazo, en `revisar_secretos.py` o en un `check-workflows.py`, de `pull_request_review`, `pull_request_target` y `secrets.` en el `env:` del job. Pendiente: tarjeta.

**F. Un campo del relacion HTTP no se quita ni se renombra sin ventana de compatibilidad: el API se despliega antes que web-app, así que el campo viejo se sigue aceptando y traduciendo, o se rechaza con 400; nunca se ignora en silencio. Lo obligatorio en el comando también lo es en el request y en Swagger.**
- Por qué: #74 y #75 (2 P1 seguidos): `ResultadoCierre` pasó a `ResultadoCierreId`, el front vigente mandaba el viejo, Newtonsoft lo ignoró y el registro se cerró con resultado `null` y 200. También #82 y #71.
- Cómo se verifica: un test de endpoint que manda el JSON viejo y espera el dato guardado o un 400, nunca un 200 sin el dato.
- Control: checklist de planner y QA («¿el diff quita o renombra una propiedad pública de un `*Request` o `*Command`? → sección "Compatibilidad" en el PR»). El detector en `/supercodex` sobre `git diff` de `Rest/**/*Request*.cs`: pendiente: tarjeta.

**G. Una validación, un bloqueo o una normalización se aplica en todos los puntos de entrada que crean o modifican la misma entidad, en el dominio o en un validador compartido, no en un solo handler.** §30 web-app 6 ya pide el grep para el front; lo nuevo es el backend:
- Por qué: #74 (`RegistrarContacto` dejaba agregar contactos a registros cerrados; `ConvertirEnRegistro` no revalidaba el canal activo), #85 (`POST /api/Registro` directo saltaba `IdempotenciaRegistro.Normalizar`), #50 y #66. §13 ya avisaba que «el defecto no estaba en el diff».
- Cómo se verifica: el plan lista los puntos de entrada con la salida de `grep "Interaccion.Crear|new Registro|AgregarAlHistorial"` y QA comprueba un test por cada uno. Un comando interno que comparte el tipo del body público se separa, para que el cliente no pueda mandar `ClaveIdempotencia`.
- Control: sección obligatoria «Puntos de entrada» en el plan del `planner`, con la salida del grep. El test de arquitectura (`new Registro(` e `Interaccion.CrearGestion(` solo en `Domain` o en una fábrica, refactorizando antes si hoy no se cumple, §19): pendiente: tarjeta.

**H. Idempotencia de verdad: la clave es `nvarchar(450)` con collation `Latin1_General_100_BIN2` y se guarda con una huella inmutable del pedido; misma clave y misma huella devuelve lo creado, otra huella da 409, y un reintento nunca reaplica efectos secundarios.** Amplía §7, que cubre un solo registro:
- Por qué: #83 (el reintento se comparaba contra la nota actual, que es editable, y `Abcdefgh` chocaba con `abcdefgh`), #85 (clave reusada en otro modo de contacto) y #50 (P1: un reintento viejo movía el contacto al cliente anterior).
- Cómo se verifica: tres tests por endpoint: misma clave y payload → 200 idéntico; misma clave y otro payload → 409; claves que difieren solo en mayúsculas → dos registros.
- Control: test de arquitectura sobre el `IModel` de `CoreDbContext`: toda propiedad `ClaveIdempotencia*` tiene `MaxLength 450` y collation `BIN2`. Pendiente: tarjeta.

### web-app

**1. `?? []`, `?? null` o `?? ""` sobre un dato del API está prohibido fuera del borde del repositorio: el repositorio devuelve `undefined` si no pudo leer y la UI dice «no se pudo cargar». `NoDisponible` y `Parcial` se tratan igual en cada pantalla.** Amplía §18 y §30 web-app 5:
- Por qué: #73 (`client.registrosCliente ?? []` convertía «no se pudo cargar» en «no tiene registros» y la interacción se guardaba suelta), #100, #103 y #109. Hoy hay 65 `?? []` en código productivo.
- Cómo se verifica: en cada consumidor nuevo de `registrosCliente`, `eventosCliente` o `contracts`, una prueba con `undefined` y otra con `contractsStatus: "Parcial"` y lista vacía.
- Control: `no-restricted-syntax` en `eslint.config.js` sobre `src/features/agent-console/**` para `?? []`, en `warn` con línea base de 65 y en `error` al llegar a 0 (pendiente: tarjeta). Mientras tanto, QA pregunta «¿algún `?? []` nuevo en el diff?».

**2. Nada enfocable lleva `aria-hidden`; nada no interactivo lleva `tabIndex={0}`; solo la capa modal superior responde a Escape; un diálogo con todo deshabilitado conserva un destino de foco. El texto nuevo pasa por `core-theme.contrast.test.ts`.** Amplía §30 web-app 7:
- Por qué: #78 corrigió un `aria-hidden` en `WorkspaceTabs.tsx` y #88 lo volvió a meter; #103 puso `tabIndex={0}` en un `<li>` de `PendingView.tsx` y #104 otra vez. También #98 y #103 (Escape cerraba dos capas en `CaseViewDialog.tsx`). Son 40 hallazgos, y suben con la ola visual.
- Cómo se verifica: lint y test de contraste, sin revisión humana.
- Control: `eslint-plugin-jsx-a11y` (hoy no está instalado) con `no-aria-hidden-on-focusable`, `no-noninteractive-tabindex`, `interactive-supports-focus` y afines en `error`; el test de contraste con la tabla de pares texto/fondo que se usan en los dos temas y un regex que lea también hex de 3 dígitos (#94). Pendiente: tarjeta.

**3. Un formulario tiene un solo `estadoInicial(contexto)`, que usan `limpiar()`, el reinicio después de guardar y el cambio de registro; cada elección temporal queda atada al id del registro. Una validación de cierre u obligatoriedad lee lo persistido, nunca el borrador.** Amplía §30 web-app 3:
- Por qué: #103 (`useContactForm.ts` conservaba `clasificacionElegida` y `servicioCodigo` tras guardar, y el contacto siguiente salía con el subregistro anterior), #97 y #108; #71 y #90 (P1: no había forma de cerrar un registro sin clasificación porque se leía el borrador).
- Cómo se verifica: prueba `estadoTrasGuardar === estadoInicial(contexto)` y prueba «elijo en A, paso a B, vuelvo a A → se ve lo persistido de A».
- Control: checklist de coder-web, con evidencia: «¿el hook `use*Form` exporta `estadoInicial` y tiene el test de igualdad?». La versión con fast-check: pendiente: tarjeta.

**4. La generación de sesión y la clave de contexto (registro o identificador) se chequean después de cada `await`, no solo al empezar. Todo comando que escribe va por `agent-console-command-runner`; ningún componente ni hook llama directo a un repositorio que escribe.** Amplía §30 web-app 1 y la regla 6 de `CLAUDE.md`:
- Por qué: #107 (logout con `obtenerRegistroPorId` pendiente: el `PUT` siguiente modificó el registro del cliente anterior con el JWT de la cuenta nueva), ya visto en #63, #73 y #77; #102 (`LoginPage.tsx`). Desde que los comandos pasan por el runner, esta familia bajó de 8 a 2.
- Cómo se verifica: prueba con dos `await` y el logout entre el primero y el segundo.
- Control: `no-restricted-imports` que impida importar `**/data/*.repository` y `**/case-commands` desde `components/**` y `hooks/**` (pendiente: tarjeta). Adversary: «por cada `await` del diff, ¿qué pasa si entre medio hubo logout o cambio de pestaña?».

**5. Lo que se ve es lo que se envía y lo que el API acepta: un control editable termina en el request o se muestra como solo lectura; el esquema zod de una respuesta acepta todo lo que el request puede producir (`null` incluido); un mapper no tira campos sin un comentario; cada etiqueta usa el campo que dice su nombre.**
- Por qué: #108 (el selector de relacion era editable en «Registrar interacción única» pero `buildInput()` no lo mandaba: decía «guardado» y el relacion se perdía; `mapCoreRegistroToRegistroResumenDto` sin `relacionCodigo`), #73 (zod rechazaba `tipoServicioId: null` después de un POST exitoso), #103 (`registro.autor` mostrado como «Asignado a»), #104 y #107.
- Cómo se verifica: por cada campo del formulario, una prueba que lo cambia y lo encuentra en el request.
- Control: test de ida y vuelta con fast-check por mapper y test por esquema (`apiCoreRegistroSchema.parse` de la respuesta a un request con nulls). Pendiente: tarjeta.

**6. El «ocupado» de una acción compuesta abarca todos sus pasos (autoguardado + cierre, POST + recarga), y el bloqueo es un `<fieldset disabled>` sobre el bloque entero, como en `EventoStrip`.** Amplía §30 web-app 2 y 4:
- Por qué: #103 (`CloseCaseDialog.tsx`: con el borrador autoguardándose, un doble clic en «Guardar y cerrar» duplicó la interacción en la historial), #94, #73, #63 y #67.
- Cómo se verifica: prueba «doble clic con la promesa pendiente → una sola llamada al repositorio».
- Control: checklist de QA, con evidencia: cada diálogo con submit nombra ese test. El helper compartido `esperaUnaSolaLlamada(accion, mockRepo)`: pendiente: tarjeta.

**7. Toda función que recibe un `caseId` maneja el prefijo `busqueda-` con rama y test propios, y el resultado de una escritura que el agente necesita para recuperarse (id creado, 409, recarga fallida) vive en el store de la sesión, no en un `useState`.** Amplía §30 web-app 6, 12 y 13:
- Por qué: #67 (reabrir desde una ficha `busqueda-*` dejó una pestaña duplicada con el registro cerrado), #69, #73 (el id creado y el fallo de recarga se perdían al cambiar de pestaña), #103 y #63.
- Cómo se verifica: prueba que dispara la operación, cambia de pestaña, vuelve y ve el aviso.
- Control: tipo marcado `SyntheticCaseId` / `RealCaseId` que hace fallar `tsc`, y generador fast-check con ids `busqueda-*` en `AgentConsoleProvider.propiedades.test.tsx`. Pendiente: tarjeta.

**8. El filtro `esActivo` nunca va en el repositorio ni en un hook compartido: solo en el `useMemo` que arma las opciones de un `<select>` de alta.** Precisa §19 y §30 web-app 8, que no nombraban el repositorio:
- Por qué: #109 (`catalog.api-repository.ts` filtraba los subregistros inactivos y un registro viejo dejó de mostrar su clasificación), #103 (tipo de servicio desactivado → «Sin tipo de registro»), #67 y #73.
- Cómo se verifica: test del repositorio «devuelve también los inactivos».
- Control: ese test en `catalog.api-repository.test.ts` por catálogo y `no-restricted-syntax` sobre `.filter(` con `esActivo` en `src/features/catalogs/data/**`. Pendiente: tarjeta.

### Proceso

**P1. Se corrige la familia, no el hallazgo: antes de responder «corregido» a un hilo de Codex, se busca el mismo patrón en todo el repo y en los flujos hermanos, y la respuesta dice dónde se buscó («también en X e Y; no aplica en Z porque…»).** Se suma a §32.
- Por qué: 13 de los 98 hallazgos de api-core fueron Codex volviendo sobre el mismo punto con «evidencia nueva» (#71 sola, 6; también #50, #57, #76 y #80). En web-app, #98 se mergeó con 3 hilos sin responder.
- Cómo se verifica: la respuesta del hilo trae la línea «Dónde más se buscó».
- Control: campo «Dónde más se buscó» en la plantilla de respuesta de `/supercodex`, que no publica si está vacío, y chequeo de hilos abiertos en `/listo-para-merge`. Pendiente: tarjeta.

**P2. En un record posicional de ASP.NET Core, el atributo de validación va en el parámetro (`[Required] string X`), nunca con `[property: Required]`: con `[property:]` MVC lanza `InvalidOperationException` y todo el endpoint responde 502. Swashbuckle no lee el atributo del parámetro; lo resuelve `RequiredDeParametroDeRecordSchemaFilter`.**
- Por qué: api-core #82.
- Cómo se verifica: un test que llama de verdad al endpoint con el record (no solo al handler), y Swagger muestra el campo como obligatorio.
- Control: test de arquitectura que falla ante `[property: Required` (o cualquier `[property:` de `System.ComponentModel.DataAnnotations`) en un record de `Rest`. Pendiente: tarjeta.

**P3. Antes de aceptar, quitar o reponer un campo del relacion HTTP por un hallazgo de revisión, se lee el handler, no solo el record o el DTO.**
- Por qué: web-app #109. `ConvertirEnRegistro` tiene `RelacionCodigo` en el record solo para rechazarlo con 400; reponerlo en la web habría roto toda conversión.
- Cómo se verifica: la respuesta al hilo cita la línea del handler que usa (o rechaza) el campo.
- Control: checklist de QA y de la respuesta en `/supercodex`, con la cita `archivo:línea` del handler.

**P4. Un hallazgo de Codex que contradice un límite aceptado en un run doc o una regla de negocio vigente no se implementa: se responde en el hilo citando la decisión.**
- Por qué: «crear el registro ya cerrado» choca con la regla vigente de que el registro nuevo nace En atención; «restaurar las pestañas de búsqueda al recargar» era un límite aceptado en `docs/agent-runs/0122`, se implementó igual y generó 6 P2 en cadena hasta revertirlo.
- Cómo se verifica: antes de tocar código por un hallazgo, se busca en el run doc de la tarjeta y en `CLAUDE.md` si ya hay una decisión sobre ese punto.
- Control: checklist de `/supercodex`: cada hallazgo se marca «aplica» o «decisión previa: <ruta o regla>».

**P5. Partir un PR en una pila nunca separa una migración de la que la elimina o la reemplaza.**
- Por qué: api-core #85. Si A1 trae la migración X y A2 la borra, desplegar A1 solo deja X aplicada y bloquea A2. Se juntaron en un solo PR.
- Cómo se verifica: al armar la pila, `git log --stat -- Persistence/Migrations` por cada PR: ninguna migración aparece agregada en uno y borrada en otro.
- Control: checklist del plan cuando el cambio se parte en varios PRs (ver §21).

**P6. Un test inestable se registra y se estabiliza; no se reintenta a ciegas hasta que pase.**
- Por qué: `TrazabilidadHistoricaTests.Registro_TresVersiones_AsOfDevuelveCadaVersion` falló 1 vez y pasó 2 de 2 aislado (16/10).
- Cómo se verifica: el reporte dice «inestable conocido» con el nombre del test, no «verde tras reintento».
- Control: tarjeta para estabilizarlo. Pendiente: tarjeta.

**P7. Las suites de integración con Testcontainers corren de a una por máquina.**
- Por qué: el 16/10, tres en paralelo levantaron 19 contenedores de SQL Server y la máquina se quedó sin memoria.
- Cómo se verifica: antes de lanzar una suite, `docker ps --filter ancestor=mcr.microsoft.com/mssql/server` sale vacío.
- Control: checklist del orquestador al paralelizar coders y QA: el modo enjambre no paraleliza la integración.

**P8. Un script bash no se edita mientras corre: bash lo lee a medida que ejecuta y el cambio rompe la corrida en curso. Se copia a un archivo nuevo y se edita la copia.**
- Por qué: 16/10, al ajustar un script del flujo con una corrida viva.
- Cómo se verifica: antes de editar, comprobar que el script no está corriendo.
- Control: checklist; no tiene un control automático razonable.

---

## 34. Tests de integración: un solo SQL Server y tests de migración de vida corta

*(2026-10-23, api-core #104, aprobado por el responsable.)*

18 tests de migración levantaban cada uno su propio SQL Server en Docker. La integración tenía 109 tests y tardaba ~203 s. Además, 18 de esos tests probaban migraciones ya aplicadas en dev: no podían volver a fallar y se pagaban en cada corrida. El #104 pasó a un `ServidorSqlCompartido` (un contenedor perezoso para todo el ensamblado; `CrearBaseNuevaAsync` crea una base `mig_<guid>` por test), retiró los 18 tests muertos y el CI corre la integración solo si el PR toca la base. Quedó en 90 tests y ~57 s.

**I1. Un test de integración solo si lo probado necesita SQL Server real.**
- Por qué: concurrencia y bloqueos, índices únicos, SQL escrito a mano, tablas temporales o de historial, y una migración que transforma datos con filas previas. Todo lo demás es unitario y corre en milisegundos.
- Cómo se verifica: el plan dice cuál de los cinco motivos aplica a cada test de integración (`planner.md`, punto 6).
- Control: QA lo marca como hallazgo (`qa.md`); `flujo.sh gate` avisa cada archivo nuevo en `api-core.IntegrationTests/` y pide una línea de justificación en el run doc.

**I2. Nunca un contenedor nuevo por test o por clase.**
- Por qué: cada contenedor suma ~10 s de arranque y memoria; 18 de ellos eran la mayor parte de los 203 s.
- Cómo se verifica: `MsSqlBuilder` aparece solo en `DatabaseFixture.cs` (tests normales, colección `Integration`) y `ServidorSqlCompartido.cs` (tests de migración, `CrearBaseNuevaAsync`).
- Control: `flujo.sh gate` **bloquea** si el diff agrega `MsSqlBuilder` en otro archivo, antes de correr suites y revisores.

**I3. Un test de migración nace con fecha de retiro: se borra en el PR siguiente a aplicar su migración en todas las bases.**
- Por qué: una vez aplicada, la migración no vuelve a correr sobre datos reales; el test solo cuesta tiempo.
- Cómo se verifica: el test nombra la migración anterior a la que prueba (`"<14 dígitos>_<Nombre>"`); si después de ella hay 2 o más migraciones en el repo, o la probada tiene más de 14 días (`FLUJO_DIAS_TEST_MIGRACION`), casi seguro ya se aplicó.
- Control: `flujo.sh gate` lo avisa sin conectarse a ninguna base; se confirma en dev y se retira. Sigue vigente la regla del coder: una migración que agrega una columna a una tabla con filas se entrega con su test de integración (api-core #70); lo que cambia es que ese test también vence.

## 35. Las reglas de negocio no leen texto: deciden por códigos guardados (2026-10-28)

Complementa la sección 31. Origen: en api-core #111 el bloqueo de constancias del sistema decidía por el inicio del `Detalle` («Cierre de registro…», «Registro reabierto…»); la app comparaba distinguiendo mayúsculas y SQL Server no, así que un agente podía saltarse el bloqueo escribiendo en minúsculas y mover una interacción se rechazaba por error. el responsable decidió quitar toda regla por texto.

**T1. Ninguna decisión de negocio mira un texto legible.**
- Por qué: el texto lo escribe una persona o cambia con una traducción, un ajuste de redacción o el idioma; las mayúsculas, espacios y collation hacen que la misma regla dé distinto en memoria y en SQL.
- Qué cuenta como decisión: permisos, qué se puede editar, anular, cerrar o mover, qué se cuenta, qué se filtra, qué estado tiene algo.
- En su lugar: un código o id estable guardado (columna `Origen`, `EstadoRegistro.Codigo`, `Canal.Codigo`, enums con `[Code]`). Si no existe, se agrega la columna y se migra, no se infiere del texto.

**T2. Prohibido en reglas:** `StartsWith`/`Contains`/`Equals`/`==`/`includes`/regex sobre `Detalle`, `Descripcion`, `Comentario`, `Nota`, `Motivo`, nombres o etiquetas de catálogo; comparar contra literales en español («Cerrado», «MensajeriaExterna», «Supervisor»…); armar un texto en el back que el front vuelve a partir («anterior → nuevo»).
- Excepción única y temporal: un respaldo para filas viejas sin código, solo hasta migrarlas una vez con el texto exacto que generaba el sistema; la migración lleva su test y el respaldo se borra en el mismo PR o el siguiente.

**T3. Lo que el sistema genera nace con su código.**
- Cómo se verifica: toda constancia automática (asignación, cierre, reapertura, movimiento) se guarda con su `Origen` propio; solo `MANUAL` es gestión del agente. El texto es solo para mostrar.

**T4. El front decide por el código que manda el API.**
- Si el API no manda el código que hace falta, se pide al back; no se reconstruye desde la descripción.

- Control: el revisor (QA, Codex y adversary) marca como hallazgo cualquier regla nueva que compare texto; el checklist de `AGENTS.md` de api-core y web-app lo incluye.

## 36. Reglas aprendidas en los PRs del 28/10 (api-core #111, web-app #147, #150, #130)

Están también en el `AGENTS.md` de cada repo para que Codex y los revisores las marquen.

**web-app**
- **W1. Solo una lista completa confirma una retirada.** Recarga fallida o `Parcial`/`NoDisponible` → se usa la última lista completa; no se descarta un registro o relacion elegido (#147, 4 P2).
- **W2. Tras un 409 no se pierde lo escrito.** Campos no tocados toman lo nuevo, los cambiados se mantienen, el reintento usa la versión releída (#150).
- **W3. Respuesta perdida, nada afirmado.** Sin respuesta no se anuncia éxito ni fallo: se relee (#150, fila fantasma).
- **W4. Foco en tests con `waitFor`;** un test lento no se arregla solo subiendo el timeout (#130, Notes/EditNoteDialog).
- **W5. Test sin DOM → `.test.ts`** (#130).
- **W6. Archivos generados:** encabezado, `linguist-generated=true`, no se editan a mano.

**api-core**
- **A1. Situación esperada nunca es 500/502:** 400 validación, 404 no existe/anulado, 409 conflicto/cerrado/versión vieja, con mensaje en español (#111).
- **A2. Reglas propias antes que servicios externos;** nunca HTTP con una fila bloqueada (#111).
- **A3. Registro anulado: mismo aviso en todos los comandos** (#111).
- **A4. Texto libre con tope de largo** si se guarda, sobre todo si se replica o va al historial (#111, motivo 1000).
- **A5. Misma regla en memoria y en SQL** (mayúsculas, espacios, collation) (#111).

**Ambos**
- **B1. Un hallazgo que contradice un REQ, un ADR o una decisión anotada no se corrige:** se consulta al dueño del producto (el responsable, 2026-10-28).

## 37. Una sola migración por PR mientras no esté aplicada (2026-10-28)

Origen: api-core #111 llegó a ~11.900 líneas; 7.844 eran archivos `*.Designer.cs` autogenerados (uno de ~1.950 líneas por cada una de sus 4 migraciones). El código real eran 882 líneas.

**M1. Un PR lleva una sola migración.** Si durante el desarrollo se agregan varias, antes de pedir revisión se juntan en una (borrar las del PR y regenerar con `dotnet ef migrations add`), siempre que no se hayan aplicado en una base compartida (dev, QA, prod). Las bases locales y de Testcontainers no cuentan.
- Cómo se verifica: `git diff --name-only origin/develop... -- Persistence/Migrations/*.cs` muestra a lo sumo una migración nueva (más su Designer y el snapshot).
- Si ya se aplicó en una base compartida: no se junta; se deja como está y se anota en el PR.

**M2. Los archivos generados no cuentan como tamaño del PR, pero sí pesan:** van marcados `linguist-generated=true` (`*.Designer.cs` y `*ModelSnapshot.cs`) para que GitHub los colapse.

**M3. Un PR que pasa de ~3.000-4.000 líneas sin contar generados se parte** en PRs encadenados (modelo y migración primero, después cada flujo), cada uno con sus rondas de Codex.
