param(
    [string]$ClashPath = "C:\software\Clash Verge\clash-verge.exe",
    [string]$Proxy = "http://127.0.0.1:7897",
    [string]$HostName = "127.0.0.1",
    [int]$Port = 7897,
    [string]$Controller = "http://127.0.0.1:9097",
    [string]$ControllerSecret = "set-your-secret",
    [int]$TimeoutSeconds = 20,
    [switch]$PreferAutoGroup,
    [switch]$StopIfStarted,
    [string]$CommandLine = ""
)

$ErrorActionPreference = "Stop"

function Test-Port {
    param([string]$TargetHost, [int]$TargetPort)
    try {
        $client = [System.Net.Sockets.TcpClient]::new()
        $async = $client.BeginConnect($TargetHost, $TargetPort, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne(500)) {
            $client.Close()
            return $false
        }
        $client.EndConnect($async)
        $client.Close()
        return $true
    } catch {
        return $false
    }
}

function Wait-Proxy {
    param([string]$TargetHost, [int]$TargetPort, [int]$Timeout)
    $deadline = (Get-Date).AddSeconds($Timeout)
    while ((Get-Date) -lt $deadline) {
        if (Test-Port -TargetHost $TargetHost -TargetPort $TargetPort) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

function Start-ClashIfNeeded {
    param([string]$ExePath)
    if (Test-Port -TargetHost $HostName -TargetPort $Port) {
        return $false
    }
    if (-not (Test-Path -LiteralPath $ExePath)) {
        throw "Clash Verge executable not found: $ExePath"
    }
    Start-Process -FilePath $ExePath -WindowStyle Hidden | Out-Null
    return $true
}

function Get-ControllerHeaders {
    if ([string]::IsNullOrWhiteSpace($ControllerSecret)) {
        return @{}
    }
    return @{ Authorization = "Bearer $ControllerSecret" }
}

function Select-AutomaticGroup {
    param([string]$ControllerUrl)
    try {
        $headers = Get-ControllerHeaders
        $data = Invoke-RestMethod -Method Get -Uri "$ControllerUrl/proxies" -Headers $headers -TimeoutSec 2
        $properties = @($data.proxies.PSObject.Properties)
        $autoTypes = @("URLTest", "Fallback", "LoadBalance")
        $auto = $properties |
            Where-Object { $autoTypes -contains $_.Value.type -and $_.Name -notmatch "^(DIRECT|REJECT)$" } |
            Sort-Object @{ Expression = { if ($_.Name -match "自动|auto|url") { 0 } else { 1 } } }, Name |
            Select-Object -First 1
        if (-not $auto) {
            Write-Output "[codex-clash-proxy] No automatic proxy group found via controller."
            return
        }

        $targetName = $auto.Name
        $selectors = $properties | Where-Object {
            $_.Value.type -eq "Selector" -and
            $_.Value.now -eq "DIRECT" -and
            @($_.Value.all) -contains $targetName
        }

        foreach ($selector in $selectors) {
            $encoded = [System.Uri]::EscapeDataString($selector.Name)
            $body = @{ name = $targetName } | ConvertTo-Json -Compress
            Invoke-RestMethod -Method Put -Uri "$ControllerUrl/proxies/$encoded" -Headers $headers -ContentType "application/json" -Body $body -TimeoutSec 2 | Out-Null
            Write-Output "[codex-clash-proxy] Selected '$targetName' for '$($selector.Name)'."
        }

        if (-not $selectors) {
            Write-Output "[codex-clash-proxy] Automatic group '$targetName' is available; no DIRECT selector needed switching."
        }
    } catch {
        Write-Output "[codex-clash-proxy] Automatic group switching skipped: $($_.Exception.Message)"
    }
}

$startedByScript = Start-ClashIfNeeded -ExePath $ClashPath

if (-not (Wait-Proxy -TargetHost $HostName -TargetPort $Port -Timeout $TimeoutSeconds)) {
    throw "Clash proxy did not become available at ${HostName}:${Port} within ${TimeoutSeconds}s."
}

if ($PreferAutoGroup) {
    Select-AutomaticGroup -ControllerUrl $Controller
}

if ([string]::IsNullOrWhiteSpace($CommandLine)) {
    Write-Output "[codex-clash-proxy] Proxy is ready at $Proxy."
    if ($startedByScript) {
        Write-Output "[codex-clash-proxy] Clash Verge was started by this script."
    }
    exit 0
}

$oldValues = @{}
$envNames = @(
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "GIT_CONFIG_COUNT",
    "GIT_CONFIG_KEY_0",
    "GIT_CONFIG_VALUE_0",
    "GIT_CONFIG_KEY_1",
    "GIT_CONFIG_VALUE_1"
)
foreach ($name in $envNames) {
    $oldValues[$name] = [Environment]::GetEnvironmentVariable($name, "Process")
}

try {
    $env:HTTP_PROXY = $Proxy
    $env:HTTPS_PROXY = $Proxy
    $env:ALL_PROXY = $Proxy
    $env:NO_PROXY = "localhost,127.0.0.1,::1"
    $env:GIT_CONFIG_COUNT = "2"
    $env:GIT_CONFIG_KEY_0 = "http.proxy"
    $env:GIT_CONFIG_VALUE_0 = $Proxy
    $env:GIT_CONFIG_KEY_1 = "https.proxy"
    $env:GIT_CONFIG_VALUE_1 = $Proxy

    Write-Output "[codex-clash-proxy] Running via ${Proxy}: $CommandLine"
    & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -Command $CommandLine
    $exitCode = if ($global:LASTEXITCODE -ne $null) { $global:LASTEXITCODE } else { if ($?) { 0 } else { 1 } }
    exit $exitCode
} finally {
    foreach ($name in $envNames) {
        if ($null -eq $oldValues[$name]) {
            Remove-Item -Path "Env:$name" -ErrorAction SilentlyContinue
        } else {
            Set-Item -Path "Env:$name" -Value $oldValues[$name]
        }
    }

    if ($StopIfStarted -and $startedByScript) {
        Get-Process -Name "clash-verge" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
        Get-Process -Name "verge-mihomo" -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
    }
}
