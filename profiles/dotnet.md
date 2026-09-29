## Stack real (verificado, no asumas otro)

.NET · C# · Entity Framework Core · MediatR (CQRS) · xUnit.

Comandos: `dotnet build` · `dotnet test` · `dotnet restore` · `dotnet ef migrations list`.

Estructura por capas (CQRS): `Rest/Controllers` (thin, sin lógica) →
`Application/Features/<Feature>/Command|Query/<Accion>/` (handler de MediatR)
→ `Persistence/Repositories/` (EF Core, interfaces en `Application/Contracts/Repositories/`)
→ `Domain/Entities/` (entidades). DTOs/ViewModels en `Application/Models/ViewModel/`,
nunca inline en el controller. Entity configuration (`IEntityTypeConfiguration<T>`)
en `Persistence/Configuration/<Modulo>/`, registrada una por una en
`OnModelCreating` — nunca `ApplyConfigurationsFromAssembly` si el ensamblado
tiene configuraciones de otro `DbContext`/módulo que no correspondan a este.

## HARD RULES — cada una viene de un bug real, no son preferencias de estilo

1. **Ninguna API auto-migra.** Una migración de EF Core no se aplica sola al
   desplegar; el fallo es silencioso. Verifica el paso de deploy antes de dar
   por hecho que corrió.
2. **Un solo `DbContext` por servicio, si esa es tu arquitectura.** Si tu
   proyecto decidió consolidar en un único `DbContext` (agregador/BFF que lee
   de servicios hermanos por HTTP en vez de leer sus bases directo), nunca
   reintroduzcas un segundo `DbContext` ni escanees por ensamblado
   configuraciones de entidades que no son tuyas.
3. **Invariantes de negocio en Update también van en Create.** Si agregas una
   regla a un handler de `Actualizar`, revisa si el `Crear` de la misma
   entidad necesita la misma regla — es fácil agregarla en uno y olvidar el otro.
4. **"Solo un X activo" necesita índice único filtrado, no solo lógica de
   aplicación.** Un check-then-insert en el handler dejando pasar dos
   inserts concurrentes es una condición de carrera real bajo carga.
5. **Excepción de autenticación vs. autorización.** Usa una excepción propia
   para "no autenticado" (401) distinta de la de "no autorizado" (403) —
   confundirlas rompe el contrato HTTP para el cliente.
6. **`AsNoTracking()` solo si la entidad es de solo lectura en ese flujo.**
   Si el mismo flujo la modifica después esperando que `SaveChanges` la
   persista, `AsNoTracking()` hace que el cambio se pierda en silencio.
