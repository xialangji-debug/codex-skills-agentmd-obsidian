[CmdletBinding()]
param(
    [string]$ProjectDir = (Get-Location).Path,
    [string]$Port = "",
    [int]$Baud = 115200,
    [Alias("JtagOnly")]
    [switch]$ForceJtag,
    [switch]$NoJtagFallback,
    [switch]$SkipBuild,
    [switch]$DryRun,
    [string]$EimProfile = "C:\Espressif\tools\Microsoft.v6.0.2.PowerShell_profile.ps1",
    [string]$OpenOcdBoard = "board/esp32c5-builtin.cfg",
    [string]$BootloaderBin = "build\bootloader\bootloader.bin",
    [string]$PartitionTableBin = "build\partition_table\partition-table.bin",
    [string]$AppBin = "build\esp32_ai_printer.bin"
)

$ErrorActionPreference = "Stop"

function Join-ProjectPath {
    param([string]$PathValue)
    if ([System.IO.Path]::IsPathRooted($PathValue)) {
        return [System.IO.Path]::GetFullPath($PathValue)
    }
    return [System.IO.Path]::GetFullPath((Join-Path $ProjectDir $PathValue))
}

function Convert-ToOpenOcdPath {
    param([string]$PathValue)
    return ([System.IO.Path]::GetFullPath($PathValue)).Replace("\", "/")
}

function Find-EspressifPort {
    try {
        $devices = Get-PnpDevice -Class Ports -PresentOnly -ErrorAction Stop |
            Where-Object {
                $_.FriendlyName -match "Espressif|USB Serial|USB JTAG|CP210|CH340|CH910|UART|Serial" -or
                $_.InstanceId -match "VID_303A|VID_10C4|VID_1A86|VID_0403"
            }
        foreach ($device in $devices) {
            if ($device.FriendlyName -match "\(?(COM\d+)\)?") {
                return $Matches[1]
            }
        }
    } catch {
        Write-Warning "Get-PnpDevice scan failed: $($_.Exception.Message)"
    }

    $ports = [System.IO.Ports.SerialPort]::GetPortNames() | Sort-Object
    if ($ports.Count -gt 0) {
        return $ports[0]
    }
    return ""
}

function Invoke-Step {
    param(
        [string]$Name,
        [scriptblock]$Command,
        [string]$DryCommand,
        [switch]$AllowFailure
    )

    Write-Host ""
    Write-Host "==> $Name"
    if ($DryRun) {
        Write-Host "[dry-run] $DryCommand"
        return $true
    }

    $global:LASTEXITCODE = 0
    $oldErrorActionPreference = $ErrorActionPreference
    $oldNativeErrorPreference = $null
    $hasNativeErrorPreference = Test-Path Variable:\PSNativeCommandUseErrorActionPreference
    if ($hasNativeErrorPreference) {
        $oldNativeErrorPreference = $PSNativeCommandUseErrorActionPreference
    }

    try {
        $ErrorActionPreference = "Continue"
        if ($hasNativeErrorPreference) {
            $script:PSNativeCommandUseErrorActionPreference = $false
        }
        & $Command 2>&1 | ForEach-Object {
            if ($_ -is [System.Management.Automation.ErrorRecord]) {
                Write-Host $_.Exception.Message
            } else {
                Write-Host $_
            }
        }
    } finally {
        $ErrorActionPreference = $oldErrorActionPreference
        if ($hasNativeErrorPreference) {
            $script:PSNativeCommandUseErrorActionPreference = $oldNativeErrorPreference
        }
    }

    $code = if ($null -eq $global:LASTEXITCODE) { 0 } else { [int]$global:LASTEXITCODE }
    if ($code -eq 0) {
        return $true
    }

    Write-Warning "$Name failed with exit code $code"
    if ($AllowFailure) {
        return $false
    }
    exit $code
}

if (-not (Test-Path -LiteralPath $ProjectDir)) {
    throw "ProjectDir not found: $ProjectDir"
}
if (-not (Test-Path -LiteralPath $EimProfile)) {
    throw "EIM PowerShell profile not found: $EimProfile"
}

$ProjectDir = [System.IO.Path]::GetFullPath($ProjectDir)
$bootloaderPath = Join-ProjectPath $BootloaderBin
$partitionPath = Join-ProjectPath $PartitionTableBin
$appPath = Join-ProjectPath $AppBin

Push-Location $ProjectDir
try {
    Write-Host "Activating EIM profile: $EimProfile"
    . $EimProfile

    if ([string]::IsNullOrWhiteSpace($Port) -and -not $ForceJtag) {
        $Port = Find-EspressifPort
    }
    if ([string]::IsNullOrWhiteSpace($Port) -and -not $ForceJtag) {
        throw "No serial port found. Use -Port COMxx, switch on the board, or use -ForceJtag."
    }
    if (-not [string]::IsNullOrWhiteSpace($Port)) {
        Write-Host "Selected serial port: $Port"
    }

    if ($ForceJtag -and -not $SkipBuild) {
        Invoke-Step "Build project" { & "idf.py" "build" } "idf.py build" | Out-Null
    }

    if (-not $ForceJtag) {
        $uartOk = Invoke-Step "UART flash" {
            & "idf.py" "-p" $Port "-b" "$Baud" "flash"
        } "idf.py -p $Port -b $Baud flash" -AllowFailure

        if ($uartOk) {
            Write-Host ""
            if ($DryRun) {
                Write-Host "Dry run completed after UART command preview. Use -ForceJtag to preview JTAG fallback."
            } else {
                Write-Host "UART flash succeeded."
            }
            exit 0
        }

        if ($NoJtagFallback) {
            Write-Error "UART flash failed and JTAG fallback is disabled."
            exit 1
        }
        Write-Host "UART flash failed; falling back to OpenOCD/JTAG."
    }

    foreach ($required in @($bootloaderPath, $partitionPath, $appPath)) {
        if (-not (Test-Path -LiteralPath $required) -and -not $DryRun) {
            throw "Required binary not found: $required"
        }
    }

    $bootloaderOcd = Convert-ToOpenOcdPath $bootloaderPath
    $partitionOcd = Convert-ToOpenOcdPath $partitionPath
    $appOcd = Convert-ToOpenOcdPath $appPath

    $openocdArgs = @(
        "-f", $OpenOcdBoard,
        "-c", "init",
        "-c", "reset halt",
        "-c", "program_esp $bootloaderOcd 0x2000 verify",
        "-c", "program_esp $partitionOcd 0x8000 verify",
        "-c", "program_esp $appOcd 0x10000 verify",
        "-c", "reset run",
        "-c", "shutdown"
    )

    Invoke-Step "OpenOCD/JTAG flash" {
        & "openocd" @openocdArgs
    } ("openocd " + ($openocdArgs -join " ")) | Out-Null

    Write-Host ""
    if ($DryRun) {
        Write-Host "Dry run completed; no flashing was performed."
    } else {
        Write-Host "JTAG flash completed. Check for Verify OK in the OpenOCD output."
    }
} finally {
    Pop-Location
}
