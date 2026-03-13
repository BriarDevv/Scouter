param(
  [string]$Distro = "Ubuntu",
  [int]$Port = 11435,
  [int]$ProbeTimeoutSeconds = 5,
  [string]$OllamaExe = "$env:LOCALAPPDATA\Programs\Ollama\ollama.exe",
  [switch]$Json
)

$ErrorActionPreference = "Stop"

function Get-WslGatewayIp {
  param([string]$TargetDistro)
  $gateway = (& wsl -d $TargetDistro -- bash -lc "ip route show default | cut -d' ' -f3 | head -n1" 2>$null | Out-String).Trim()
  if (-not $gateway) {
    throw "No pude resolver el gateway IP de WSL para la distro '$TargetDistro'."
  }
  return $gateway
}

function Test-OllamaEndpoint {
  param(
    [string]$BaseUrl,
    [int]$TimeoutSeconds
  )

  try {
    $response = Invoke-RestMethod -Method Get -Uri "$BaseUrl/api/tags" -TimeoutSec $TimeoutSeconds
    $models = @($response.models).Count
    return [pscustomobject]@{
      ok = $true
      detail = "reachable:$models"
    }
  }
  catch {
    return [pscustomobject]@{
      ok = $false
      detail = $_.Exception.Message
    }
  }
}

function Emit-Result {
  param([pscustomobject]$Result)
  if ($Json) {
    $Result | ConvertTo-Json -Compress -Depth 6
  }
  else {
    if ($Result.ok) {
      Write-Host "[ensure-ollama-bridge] OK baseUrl=$($Result.base_url) gateway=$($Result.gateway_ip) started=$($Result.started) pid=$($Result.pid)"
    }
    else {
      Write-Error "[ensure-ollama-bridge] ERROR $($Result.error)"
    }
  }
}

$gatewayIp = Get-WslGatewayIp -TargetDistro $Distro
$baseUrl = "http://$gatewayIp`:$Port"

$existingListener = Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue | Where-Object {
  $_.LocalAddress -eq $gatewayIp -or $_.LocalAddress -eq "0.0.0.0"
} | Select-Object -First 1

$probe = Test-OllamaEndpoint -BaseUrl $baseUrl -TimeoutSeconds $ProbeTimeoutSeconds
if ($probe.ok) {
  Emit-Result ([pscustomobject]@{
    ok = $true
    gateway_ip = $gatewayIp
    base_url = $baseUrl
    started = $false
    pid = if ($existingListener) { $existingListener.OwningProcess } else { $null }
    probe = $probe.detail
  })
  exit 0
}

if (-not (Test-Path -LiteralPath $OllamaExe)) {
  Emit-Result ([pscustomobject]@{
    ok = $false
    gateway_ip = $gatewayIp
    base_url = $baseUrl
    error = "No encontré Ollama en $OllamaExe"
  })
  exit 1
}

$startInfo = New-Object System.Diagnostics.ProcessStartInfo
$startInfo.FileName = $OllamaExe
$startInfo.Arguments = "serve"
$startInfo.UseShellExecute = $false
$startInfo.CreateNoWindow = $true
$startInfo.Environment["OLLAMA_HOST"] = "$gatewayIp`:$Port"

$process = [System.Diagnostics.Process]::Start($startInfo)

$probeOk = $false
for ($i = 0; $i -lt 15; $i++) {
  Start-Sleep -Seconds 1
  $probe = Test-OllamaEndpoint -BaseUrl $baseUrl -TimeoutSeconds $ProbeTimeoutSeconds
  if ($probe.ok) {
    $probeOk = $true
    break
  }
}

if (-not $probeOk) {
  try {
    if ($process -and -not $process.HasExited) {
      Stop-Process -Id $process.Id -Force
    }
  }
  catch {}

  Emit-Result ([pscustomobject]@{
    ok = $false
    gateway_ip = $gatewayIp
    base_url = $baseUrl
    started = $true
    pid = if ($process) { $process.Id } else { $null }
    error = "No pude dejar Ollama reachable en $baseUrl ($($probe.detail))"
  })
  exit 1
}

Emit-Result ([pscustomobject]@{
  ok = $true
  gateway_ip = $gatewayIp
  base_url = $baseUrl
  started = $true
  pid = if ($process) { $process.Id } else { $null }
  probe = $probe.detail
})
exit 0
