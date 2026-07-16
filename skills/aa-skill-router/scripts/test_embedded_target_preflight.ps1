$ErrorActionPreference = "Stop"
$script = Join-Path $PSScriptRoot "embedded_target_preflight.ps1"
$temp = Join-Path ([IO.Path]::GetTempPath()) ("embedded-preflight-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Path $temp | Out-Null
try {
    $inventory = @(
        @{ FriendlyName = "ASR Modem Device (COM14)"; InstanceId = "USB\VID_2ECC&PID_3010\ASR"; Status = "OK"; Class = "Ports" },
        @{ FriendlyName = "USB Serial Device (COM13)"; InstanceId = "USB\VID_303A&PID_1001\ESP"; Status = "OK"; Class = "Ports" }
    )
    $inventoryPath = Join-Path $temp "inventory.json"
    $inventory | ConvertTo-Json | Set-Content -LiteralPath $inventoryPath -Encoding utf8
    $package = Join-Path $temp "firmware.zip"
    Set-Content -LiteralPath $package -Value "test" -Encoding ascii
    $sdkconfig = Join-Path $temp "sdkconfig"
    Set-Content -LiteralPath $sdkconfig -Value 'CONFIG_IDF_TARGET="esp32c5"' -Encoding ascii

    & $script -ExpectedFamily ASR -Port COM14 -Package $package -InventoryJson $inventoryPath | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "ASR match test failed" }
    & $script -ExpectedFamily ESP32-C5 -Port COM13 -ProjectDir $temp -InventoryJson $inventoryPath | Out-Null
    if ($LASTEXITCODE -ne 0) { throw "ESP32 match test failed" }
    & $script -ExpectedFamily ASR -Port COM13 -Package $package -InventoryJson $inventoryPath | Out-Null
    if ($LASTEXITCODE -eq 0) { throw "wrong-family test unexpectedly passed" }
    Write-Host "embedded target preflight tests passed"
} finally {
    Remove-Item -LiteralPath $temp -Recurse -Force -ErrorAction SilentlyContinue
}
