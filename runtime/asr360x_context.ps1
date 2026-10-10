function Resolve-AsrBranchBuildProfile {
    [CmdletBinding()]
    param(
        [Parameter(Mandatory)][string]$RepoPath,
        [string]$AdapterPath,
        [switch]$ReadOnly
    )
    $defaultPath = [System.IO.Path]::GetFullPath((Join-Path $RepoPath '.codex-project\asr3602-build-profile.json'))
    if ([string]::IsNullOrWhiteSpace($AdapterPath)) { $AdapterPath = $defaultPath }
    if (-not [System.IO.Path]::IsPathRooted($AdapterPath)) { $AdapterPath = Join-Path $RepoPath $AdapterPath }
    $AdapterPath = [System.IO.Path]::GetFullPath($AdapterPath)
    if (-not $AdapterPath.Equals($defaultPath, [System.StringComparison]::OrdinalIgnoreCase)) {
        # An explicitly selected immutable adapter remains the caller's input.
        # Its schema, target, and live binding are checked by the owner's preflight.
        if (-not (Test-Path -LiteralPath $AdapterPath -PathType Leaf)) { throw "Explicit build adapter is missing: $AdapterPath" }
        $inputProfile = Get-Content -LiteralPath $AdapterPath -Raw -Encoding UTF8 | ConvertFrom-Json
        if ($inputProfile.schemaVersion -eq 2) {
            $expandArgs = @((Join-Path $env:USERPROFILE '.codex\scripts\asr360x_profile_store.py'), 'expand', '--repo', $RepoPath, '--adapter', $AdapterPath)
            if ($ReadOnly) { $expandArgs += '--read-only' }
            $expandedText = & python -X utf8 @expandArgs
            if ($LASTEXITCODE -ne 0) { throw "Cannot expand explicit profile: $expandedText" }
            $expanded = ($expandedText -join [Environment]::NewLine) | ConvertFrom-Json
            if (-not (Test-Path -LiteralPath $expanded.expandedPath -PathType Leaf)) { throw 'Explicit compact adapter needs preparation before a read-only release preview' }
            return [string]$expanded.expandedPath
        }
        return $AdapterPath
    }
    $storeScript = Join-Path $env:USERPROFILE '.codex\scripts\asr360x_profile_store.py'
    $operation = if ($ReadOnly) { 'check' } else { 'prepare' }
    $resultText = & python -X utf8 $storeScript $operation --repo $RepoPath
    if ($LASTEXITCODE -ne 0) { throw "Branch configuration is not ready: $($resultText -join [Environment]::NewLine)" }
    $result = ($resultText -join [Environment]::NewLine) | ConvertFrom-Json
    Write-Host "branch_configuration: $($result.status) source=$($result.source) record=$($result.recordPath)"
    if (-not (Test-Path -LiteralPath $result.expandedPath -PathType Leaf)) {
        throw "Expanded configuration needs preparation: run project_onboard.py --repo <repo> --prepare"
    }
    return [string]$result.expandedPath
}
