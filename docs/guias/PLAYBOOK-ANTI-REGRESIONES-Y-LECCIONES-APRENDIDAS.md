---
tipo: guia-oficial
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
asignar, a un caso) puede fallar con una excepción cuando el reintento del usuario recae sobre
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
entidades del backend (p. ej. la misma persona en varios contratos), los datos de contacto e
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
