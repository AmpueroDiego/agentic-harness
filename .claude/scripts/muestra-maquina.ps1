# Una muestra de la máquina para recursos.tsv de flujo.sh: MB libres, CPU %, procesos dotnet y los 3 que más RAM usan.
$o = Get-CimInstance Win32_OperatingSystem
$cpu = [int](Get-CimInstance Win32_Processor | Measure-Object LoadPercentage -Average).Average
$dotnet = @(Get-Process dotnet -ErrorAction SilentlyContinue).Count
$top = (Get-Process | Group-Object Name | ForEach-Object { [pscustomobject]@{ N = $_.Name; MB = [int](($_.Group | Measure-Object WorkingSet64 -Sum).Sum / 1MB) } } |
  Sort-Object MB -Descending | Select-Object -First 3 | ForEach-Object { "$($_.N):$($_.MB)" }) -join ','
"{0}`t{1}`t{2}`t{3}" -f [int]($o.FreePhysicalMemory / 1KB), $cpu, $dotnet, $top
