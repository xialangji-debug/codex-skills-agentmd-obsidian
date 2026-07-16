[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [ValidateSet("ASR", "ESP32-C5")]
    [string]$ExpectedFamily,
    [string]$ExpectedChip = "",
    [string]$Port = "",
    [string]$ProjectDir = "",
    [string]$Package = "",
    [string]$InventoryJson = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Get-Inventory {
    if (-not [string]::IsNullOrWhiteSpace($InventoryJson)) {
        return @(Get-Content -LiteralPath $InventoryJson -Raw | ConvertFrom-Json)
    }
    return @(Get-PnpDevice -PresentOnly -ErrorAction Stop | ForEach-Object {
        [pscustomobject]@{
            FriendlyName = [string]$_.FriendlyName
            InstanceId = [string]$_.InstanceId
            Status = [string]$_.Status
            Class = [string]$_.Class
        }
    })
}

function Get-Family([object]$Device) {
    $text = "{0} {1}" -f $Device.FriendlyName, $Device.InstanceId
    if ($text -match '(?i)VID_2ECC|ASR Modem|ASR DIAG|ASR Serial Download') { return "ASR" }
    if ($text -match '(?i)VID_303A|Espressif|USB JTAG/serial debug') { return "ESP32-C5" }
    return "Unknown"
}

function Get-Port([object]$Device) {
    if (([string]$Device.FriendlyName) -match '(?i)\b(COM\d+)\b') { return $Matches[1].ToUpperInvariant() }
    return ""
}

function Get-HardwareId([object]$Device) {
    if (([string]$Device.InstanceId) -match '(?i)(VID_[0-9A-F]{4}&PID_[0-9A-F]{4})') { return $Matches[1].ToUpperInvariant() }
    return "unavailable"
}

try {
    $inventory = Get-Inventory
    $embedded = @($inventory | ForEach-Object {
        $family = Get-Family $_
        if ($family -ne "Unknown") {
            [pscustomobject]@{
                Family = $family
                FriendlyName = [string]$_.FriendlyName
                Port = Get-Port $_
                HardwareId = Get-HardwareId $_
                Status = [string]$_.Status
            }
        }
    })
    $families = @($embedded.Family | Sort-Object -Unique)
    $matching = @($embedded | Where-Object Family -eq $ExpectedFamily)
    if ($matching.Count -eq 0) {
        throw "No present device matches expected family $ExpectedFamily"
    }
    if ($families.Count -gt 1 -and [string]::IsNullOrWhiteSpace($Port) -and $ExpectedFamily -eq "ASR") {
        throw "Multiple embedded device families are connected; specify the confirmed ASR download port"
    }

    $selected = $null
    if (-not [string]::IsNullOrWhiteSpace($Port)) {
        $normalizedPort = $Port.ToUpperInvariant()
        $portDevices = @($embedded | Where-Object Port -eq $normalizedPort)
        if ($portDevices.Count -ne 1) {
            throw "Port $normalizedPort does not resolve to exactly one known embedded target"
        }
        $selected = $portDevices[0]
        if ($selected.Family -ne $ExpectedFamily) {
            throw "Port $normalizedPort belongs to $($selected.Family), expected $ExpectedFamily"
        }
    } elseif ($ExpectedFamily -eq "ASR") {
        $ports = @($matching | Where-Object { -not [string]::IsNullOrWhiteSpace($_.Port) })
        if ($ports.Count -ne 1) {
            throw "ASR target is ambiguous; specify the confirmed download port"
        }
        $selected = $ports[0]
    } else {
        $selected = $matching[0]
    }

    if (-not [string]::IsNullOrWhiteSpace($Package)) {
        if (-not (Test-Path -LiteralPath $Package -PathType Leaf)) { throw "Firmware package not found: $Package" }
        if ([IO.Path]::GetFileName($Package) -match '(?i)source') { throw "Source package is not flashable: $Package" }
    }

    if (-not [string]::IsNullOrWhiteSpace($ProjectDir)) {
        $project = [IO.Path]::GetFullPath($ProjectDir)
        if ($ExpectedFamily -eq "ESP32-C5") {
            $sdkconfig = Join-Path $project "sdkconfig"
            if (Test-Path -LiteralPath $sdkconfig) {
                $sdkText = Get-Content -LiteralPath $sdkconfig -Raw
                if ($sdkText -notmatch '(?im)^CONFIG_IDF_TARGET="esp32c5"|^CONFIG_IDF_TARGET_ESP32C5=y') {
                    throw "Project sdkconfig does not identify ESP32-C5"
                }
            }
        } else {
            $deviceContext = Join-Path $project ".codex-project\device.md"
            if (-not [string]::IsNullOrWhiteSpace($ExpectedChip) -and (Test-Path -LiteralPath $deviceContext)) {
                $deviceText = Get-Content -LiteralPath $deviceContext -Raw
                if ($deviceText -notmatch [regex]::Escape($ExpectedChip)) {
                    throw "Project device context does not match expected chip $ExpectedChip"
                }
            }
        }
    }

    [pscustomobject]@{
        Status = "MATCHED"
        ExpectedFamily = $ExpectedFamily
        ExpectedChip = $ExpectedChip
        SelectedFamily = $selected.Family
        SelectedPort = $selected.Port
        SelectedName = $selected.FriendlyName
        HardwareId = $selected.HardwareId
        ConnectedFamilies = $families
        Package = if ($Package) { [IO.Path]::GetFileName($Package) } else { "not-checked" }
    } | ConvertTo-Json -Depth 4
    exit 0
} catch {
    [pscustomobject]@{
        Status = "BLOCKED"
        ExpectedFamily = $ExpectedFamily
        ExpectedChip = $ExpectedChip
        Reason = $_.Exception.Message
    } | ConvertTo-Json -Depth 3
    exit 2
}
