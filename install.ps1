<#
.SYNOPSIS
    Instala/configura el harness multi-agente en un proyecto destino (Windows).

.DESCRIPTION
    Equivalente funcional de install.sh para PowerShell. Copia agentes,
    comandos, hooks y scripts al .claude/ del proyecto destino, genera o
    reutiliza harness.ini, sustituye placeholders basicos y deja un hook de
    git que revisa secretos antes de cada commit. Idempotente y no
    destructivo: un archivo existente con contenido distinto se respalda a
    .bak antes de reemplazarlo, salvo -Force.

.PARAMETER Target
    Carpeta del proyecto donde se instala. Default: directorio actual.

.PARAMETER Ini
    Ruta a un harness.ini ya completado (salta el asistente interactivo).

.PARAMETER DryRun
    No escribe nada; solo muestra que haria.

.PARAMETER NonInteractive
    No hace preguntas: usa harness.ini.example tal cual (o -Ini si se dio).

.PARAMETER Force
    Sobrescribe archivos existentes sin backup.

.PARAMETER SkipHook
    No toca core.hooksPath del repo destino.

.EXAMPLE
    .\install.ps1 -Target ..\mi-proyecto
    .\install.ps1 -Target ..\mi-proyecto -DryRun
    .\install.ps1 -Target ..\mi-proyecto -NonInteractive -Ini .\harness.ini.example
#>
[CmdletBinding()]
param(
    [string]$Target = ".",
    [string]$Ini = "",
    [switch]$DryRun,
    [switch]$NonInteractive,
    [switch]$Force,
    [switch]$SkipHook
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$Source = Split-Path -Parent $MyInvocation.MyCommand.Path
New-Item -ItemType Directory -Force -Path $Target | Out-Null
$Target = (Resolve-Path $Target).Path

function Write-Step($msg) { Write-Host "`n== $msg ==" -ForegroundColor Cyan }
function Write-Log($msg) { Write-Host $msg }
function Invoke-Maybe([scriptblock]$action, [string]$desc) {
    if ($DryRun) { Write-Host "[dry-run] $desc" }
    else { & $action }
}

Write-Step "1/6 - Detectando herramientas"
function Test-Tool($name) {
    $cmd = Get-Command $name -ErrorAction SilentlyContinue
    if ($cmd) { Write-Host ("  [ok]      {0,-10} {1}" -f $name, $cmd.Source) }
    else { Write-Host ("  [omitido] {0,-10} no encontrado en PATH" -f $name) }
}
foreach ($t in @("git","gh","node","dotnet","python","claude","codex","agy")) { Test-Tool $t }
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Error "git es obligatorio. Instalalo y volve a correr install.ps1."
}

Write-Step "2/6 - Resolviendo harness.ini"
$IniDestino = Join-Path $Target "harness.ini"

if ($Ini) {
    if (-not (Test-Path $Ini)) { Write-Error "No existe $Ini" }
    Invoke-Maybe { Copy-Item $Ini $IniDestino -Force } "copiar $Ini -> $IniDestino"
}
elseif (Test-Path $IniDestino) {
    Write-Log "  Ya existe $IniDestino - se reutiliza (borralo si queres repetir el asistente)."
}
elseif ($NonInteractive) {
    Write-Log "  -NonInteractive sin -Ini: copiando harness.ini.example tal cual."
    Invoke-Maybe { Copy-Item (Join-Path $Source "harness.ini.example") $IniDestino -Force } "copiar harness.ini.example"
}
else {
    Write-Log "  Sin harness.ini - asistente interactivo (Enter para aceptar el default)."
    $Nombre = Read-Host "Nombre del proyecto [MiProyecto]"
    if (-not $Nombre) { $Nombre = "MiProyecto" }
    $Base = Read-Host "Rama base (git) [develop]"
    if (-not $Base) { $Base = "develop" }
    $Main = Read-Host "Rama de produccion [main]"
    if (-not $Main) { $Main = "main" }
    $Tracker = Read-Host "Tracker de tareas (none/trello/azuredevops/github-issues) [none]"
    if (-not $Tracker) { $Tracker = "none" }

    if ($DryRun) {
        Write-Log "  [dry-run] generaria $IniDestino con project.name=$Nombre git.base_branch=$Base git.main_branch=$Main tracker.provider=$Tracker"
    } else {
        $contenido = Get-Content (Join-Path $Source "harness.ini.example") -Raw -Encoding UTF8
        $contenido = $contenido -replace '(?m)^name = MiProyecto', "name = $Nombre"
        $contenido = $contenido -replace '(?m)^base_branch = develop', "base_branch = $Base"
        $contenido = $contenido -replace '(?m)^main_branch = main', "main_branch = $Main"
        $contenido = $contenido -replace '(?m)^provider = none', "provider = $Tracker"
        [System.IO.File]::WriteAllText($IniDestino, $contenido, [System.Text.UTF8Encoding]::new($false))
    }
}

function Get-IniValue([string]$Section, [string]$Key, [string]$Default) {
    if (-not (Test-Path $IniDestino)) { return $Default }
    $lines = Get-Content $IniDestino -Encoding UTF8
    $inSection = $false
    foreach ($line in $lines) {
        if ($line -match '^\[(.+)\]\s*$') {
            $inSection = ($Matches[1] -eq $Section)
            continue
        }
        if ($inSection -and $line -match "^\s*$([regex]::Escape($Key))\s*=\s*(.*)$") {
            $val = $Matches[1].Trim()
            if ($val) { return $val }
            return $Default
        }
    }
    return $Default
}

$Proyecto = Get-IniValue "project" "name" "MiProyecto"
$BaseBranch = Get-IniValue "git" "base_branch" "develop"
$Tracker = Get-IniValue "tracker" "provider" "none"
$CodexOn = Get-IniValue "engines" "codex_enabled" "false"
$AntigravityOn = Get-IniValue "engines" "antigravity_enabled" "false"
$DbMcp = Get-IniValue "databases" "enabled_mcp_servers" ""
$VaultOn = Get-IniValue "vault" "enabled" "false"

# Staging: los .md con placeholders se sustituyen ANTES de comparar/copiar,
# igual que en install.sh. Si se sustituyera despues de copiar, cada corrida
# compararia el original con AcmeOrg contra el resultado ya sustituido de la
# corrida anterior, los veria "distintos" y generaria un .bak espurio cada
# vez - rompiendo la idempotencia aunque el contenido final fuera el mismo.
$Stage = Join-Path ([System.IO.Path]::GetTempPath()) ("harness-install-" + [guid]::NewGuid())
New-Item -ItemType Directory -Force -Path (Join-Path $Stage ".claude\agents") | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $Stage ".claude\commands") | Out-Null

function Convert-Placeholders([string]$Path) {
    $c = Get-Content $Path -Raw -Encoding UTF8
    $c = $c -replace 'AcmeOrg', $Proyecto
    if ($BaseBranch -ne "develop") { $c = $c -replace '`develop`', "``$BaseBranch``" }
    [System.IO.File]::WriteAllText($Path, $c, [System.Text.UTF8Encoding]::new($false))
}

Get-ChildItem (Join-Path $Source ".claude\agents") -Filter *.md -ErrorAction SilentlyContinue | ForEach-Object {
    $d = Join-Path $Stage ".claude\agents\$($_.Name)"
    Copy-Item $_.FullName $d -Force
    Convert-Placeholders $d
}
Get-ChildItem (Join-Path $Source ".claude\commands") -Filter *.md -ErrorAction SilentlyContinue | ForEach-Object {
    $d = Join-Path $Stage ".claude\commands\$($_.Name)"
    Copy-Item $_.FullName $d -Force
    Convert-Placeholders $d
}
Copy-Item (Join-Path $Source "CLAUDE.md") (Join-Path $Stage "CLAUDE.md") -Force
Convert-Placeholders (Join-Path $Stage "CLAUDE.md")
Copy-Item (Join-Path $Source "AGENTS.md") (Join-Path $Stage "AGENTS.md") -Force
Convert-Placeholders (Join-Path $Stage "AGENTS.md")

Write-Step "3/6 - Copiando agentes, comandos, hooks y scripts (con placeholders ya resueltos)"
function Copy-Tree([string]$OrigenDir, [string]$DestinoDir) {
    if (-not (Test-Path $OrigenDir)) { return }
    Get-ChildItem -Path $OrigenDir -Recurse -File | ForEach-Object {
        $rel = $_.FullName.Substring($OrigenDir.Length).TrimStart('\', '/')
        $d = Join-Path $DestinoDir $rel
        if ((Test-Path $d) -and -not $Force) {
            $existente = Get-FileHash $d -ErrorAction SilentlyContinue
            $nuevo = Get-FileHash $_.FullName -ErrorAction SilentlyContinue
            if ($existente.Hash -ne $nuevo.Hash) {
                Invoke-Maybe { Copy-Item $d "$d.bak" -Force } "respaldar $d -> $d.bak"
                Write-Log "    (respaldado $d -> $d.bak, contenido distinto)"
            }
        }
        Invoke-Maybe {
            New-Item -ItemType Directory -Force -Path (Split-Path $d) | Out-Null
            Copy-Item $_.FullName $d -Force
        } "copiar $($_.FullName) -> $d"
    }
}
Copy-Tree (Join-Path $Stage ".claude\agents")    (Join-Path $Target ".claude\agents")
Copy-Tree (Join-Path $Stage ".claude\commands")  (Join-Path $Target ".claude\commands")
Copy-Tree (Join-Path $Source ".claude\hooks")    (Join-Path $Target ".claude\hooks")
Copy-Tree (Join-Path $Source ".claude\scripts")  (Join-Path $Target ".claude\scripts")
Copy-Tree (Join-Path $Source ".claude\tools")    (Join-Path $Target ".claude\tools")
Copy-Tree (Join-Path $Source "profiles")         (Join-Path $Target ".claude\profiles")

foreach ($f in @("CLAUDE.md", "AGENTS.md")) {
    $src = Join-Path $Stage $f
    $dst = Join-Path $Target $f
    if ((Test-Path $dst) -and -not $Force) {
        $e = Get-FileHash $dst -ErrorAction SilentlyContinue
        $n = Get-FileHash $src -ErrorAction SilentlyContinue
        if ($e.Hash -ne $n.Hash) {
            Invoke-Maybe { Copy-Item $dst "$dst.bak" -Force } "respaldar $dst"
            Write-Log "    (respaldado $dst -> $f.bak, contenido distinto)"
        }
    }
    Invoke-Maybe { Copy-Item $src $dst -Force } "copiar $f"
}
$settingsDst = Join-Path $Target ".claude\settings.json"
if (-not (Test-Path $settingsDst)) {
    Invoke-Maybe { Copy-Item (Join-Path $Source ".claude\settings.json") $settingsDst -Force } "copiar settings.json"
}
Write-Log "  Placeholders resueltos: AcmeOrg -> $Proyecto$(if ($BaseBranch -ne 'develop') { \", ``develop`` -> ``$BaseBranch``\" })."
Write-Log "  Revisa a mano los nombres de repo (api-core, web-app, ...): el instalador no"
Write-Log "  adivina los tuyos - edita CLAUDE.md y los agentes con los nombres reales de tus repos."
Remove-Item -Recurse -Force $Stage -ErrorAction SilentlyContinue

Write-Step "4/6 - (sin uso; ver paso 3 - placeholders y copia van juntos para no romper idempotencia)"

Write-Step "5/6 - Hook de git (revision de secretos antes de cada commit)"
if ($SkipHook) {
    Write-Log "  Omitido (-SkipHook)."
} elseif (-not (Test-Path (Join-Path $Target ".git"))) {
    Write-Log "  $Target no es la raiz de un repo git - omitido. Corre 'git init' primero, o instala el hook a mano despues."
} else {
    # Dentro de .claude/ (misma profundidad que scripts/hooks-repos/ en este
    # repo): scripts/hooks-repos/pre-commit ubica el resto del sistema con
    # "dirname/../.." - dos niveles arriba de si mismo. A un solo nivel de
    # $Target esa cuenta apuntaria fuera del proyecto y no encontraria
    # revisar_secretos.py.
    $hooksDir = Join-Path $Target ".claude\hooks-git"
    Invoke-Maybe {
        New-Item -ItemType Directory -Force -Path $hooksDir | Out-Null
        Copy-Item (Join-Path $Source "scripts\hooks-repos\pre-commit") (Join-Path $hooksDir "pre-commit") -Force
    } "instalar pre-commit en $hooksDir"
    $hooksPathRel = ".claude/hooks-git"
    $actual = (git -C $Target config --get core.hooksPath 2>$null)
    if ($actual -and $actual -ne $hooksPathRel -and -not $Force) {
        Write-Log "  $Target ya tiene core.hooksPath=$actual - se conserva. Usa -Force para reemplazarlo."
    } else {
        Invoke-Maybe { git -C $Target config core.hooksPath $hooksPathRel } "git config core.hooksPath"
        Write-Log "  Instalado: core.hooksPath -> $hooksPathRel (revisar_secretos.py corre antes de cada commit)."
        Write-Log "  Nota: el pre-commit de este hook llama a un Python 3 del PATH; si no hay ninguno, bloquea el commit"
        Write-Log "  a proposito en vez de dejar pasar secretos sin revisar."
    }
}

Write-Step "6/6 - doctor: resumen de lo configurado"
function Estado($v) { if ($v -eq "true" -or $v -eq "yes") { "activo" } else { "omitido" } }
Write-Host ""
Write-Host "  Proyecto:            $Proyecto"
Write-Host "  Rama base:           $BaseBranch"
Write-Host "  harness.ini:         $IniDestino"
Write-Host "  Tracker:             $Tracker $(if ($Tracker -eq 'none') { '(sin integracion - los agentes lo asumen manual)' })"
Write-Host "  Codex CLI:           $(Estado $CodexOn)"
Write-Host "  Antigravity CLI:     $(Estado $AntigravityOn)"
Write-Host "  MCP de base de datos: $(if ($DbMcp) { $DbMcp } else { '(ninguno declarado)' })"
Write-Host "  Vault Obsidian:      $(Estado $VaultOn)"
Write-Host "  Hook de secretos:    $(if ($SkipHook) { 'omitido (-SkipHook)' } else { 'ver paso 5/6 arriba' })"
Write-Host ""
Write-Host "Proximos pasos:"
Write-Host "  1. Edita $IniDestino con tus repos reales bajo [repo:<nombre>]."
Write-Host "  2. Completa la seccion 'Vision de dominio' de $Target\CLAUDE.md."
Write-Host "  3. Revisa que los nombres de repo en los agentes (api-core, web-app, ...)"
Write-Host "     coincidan con los tuyos - el instalador solo sustituyo el nombre del"
Write-Host "     proyecto y la rama base, no los nombres de repo."
Write-Host "  4. harness.ini NO se versiona (ya esta en .gitignore si copiaste el de este repo)."
