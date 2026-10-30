# Nodos de MSBuild y vitest cuyo padre ya terminó: nadie los usa. Imprime cuántos cerró.
$all = Get-CimInstance Win32_Process; $ids = @{}
$all | ForEach-Object { $ids[[int]$_.ProcessId] = 1 }
$h = @($all | Where-Object {
  (($_.Name -eq 'dotnet.exe' -and $_.CommandLine -match 'nodeReuse|nodemode:') -or ($_.Name -eq 'node.exe' -and $_.CommandLine -match 'vitest')) -and
  -not $ids.ContainsKey([int]$_.ParentProcessId) })
$h | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
$h.Count
