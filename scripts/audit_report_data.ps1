param(
    [string]$EvidenceDirectory = (Join-Path $PSScriptRoot '../evidencias/practica4')
)
$ErrorActionPreference = 'Stop'
$serial = Get-Content -Raw -Encoding utf8 -LiteralPath (Join-Path $EvidenceDirectory 'LOG DE 15 MIN.md')
$rows = @(Import-Csv -LiteralPath (Join-Path $EvidenceDirectory 'selected.csv'))
$published = @([regex]::Matches($serial, 'PUBLISH id=(p4-[a-f0-9]{24}-[1-9][0-9]*)') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique)
$acked = @([regex]::Matches($serial, 'SHADOW_ACK id=(p4-[a-f0-9]{24}-[1-9][0-9]*)') | ForEach-Object { $_.Groups[1].Value } | Sort-Object -Unique)
$times = @([regex]::Matches($serial, 'PIR t=(\d+) ms') | ForEach-Object { [long]$_.Groups[1].Value })
$latencies = @($rows | ForEach-Object { [double]$_.storageLatencyMs } | Sort-Object)
$mean = ($latencies | Measure-Object -Average).Average
$n = $latencies.Count
$median = if ($n % 2) { $latencies[[int][math]::Floor($n / 2)] } else { ($latencies[$n / 2 - 1] + $latencies[$n / 2]) / 2 }
$variance = ($latencies | ForEach-Object { [math]::Pow($_ - $mean, 2) } | Measure-Object -Average).Average
$events = @($rows | Where-Object { $_.event } | ForEach-Object {
    $event = $_.event | ConvertFrom-Json
    [pscustomobject]@{ id = $_.messageId; observedAtMs = [long]$_.observedAtMs; actuator = $event.actuator.S; from = $event.from.S; to = $event.to.S; origin = $event.origin.S }
})
[ordered]@{
    sources = @('LOG DE 15 MIN.md', 'selected.csv')
    publishedUnique = $published.Count
    ackUnique = $acked.Count
    acknowledgedPublished = @($published | Where-Object { $_ -in $acked }).Count
    firstPirMs = $times[0]
    lastPirMs = $times[-1]
    timedSpanMs = $times[-1] - $times[0]
    cycleStarts = [regex]::Matches($serial, 'Inicio ciclo:').Count
    cycleCompletions = [regex]::Matches($serial, 'Servo: ciclo terminado').Count
    csvRows = $n
    csvUniqueIds = @($rows.messageId | Sort-Object -Unique).Count
    csvIntersection = @($published | Where-Object { $_ -in $rows.messageId }).Count
    serialIds = $published
    preWriteLatency = [ordered]@{ minimumMs = $latencies[0]; maximumMs = $latencies[-1]; meanMs = [math]::Round($mean, 2); medianMs = $median; populationStdDevMs = [math]::Round([math]::Sqrt($variance), 2); p95NearestRankMs = $latencies[[math]::Ceiling(0.95 * $n) - 1]; atMost5000Ms = @($latencies | Where-Object { $_ -le 5000 }).Count }
    events = $events
    rows = @($rows | ForEach-Object { [pscustomobject]@{ id = $_.messageId; observedAtMs = [long]$_.observedAtMs; latencyMs = [long]$_.storageLatencyMs; droppedRecords = [long]$_.droppedRecords; color = $_.ledColor; kind = $_.recordKind } })
} | ConvertTo-Json -Depth 8
