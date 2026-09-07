Set-StrictMode -Version Latest

function Convert-ToAsrMsysPath {
    param([Parameter(Mandatory = $true)][string]$PathValue)

    if ([string]::IsNullOrWhiteSpace($PathValue)) {
        throw 'ASR360x build path cannot be empty.'
    }

    $resolved = [System.IO.Path]::GetFullPath($PathValue).Replace('\', '/')
    if ($resolved -match '^([A-Za-z]):/(.*)$') {
        return ('/{0}/{1}' -f $Matches[1].ToLowerInvariant(), $Matches[2]).TrimEnd('/')
    }
    if ($resolved.StartsWith('//')) {
        return $resolved.TrimEnd('/')
    }
    if ($resolved.StartsWith('/')) {
        return $resolved.TrimEnd('/')
    }
    throw "Cannot convert path to MSYS format: $PathValue"
}

function Get-AsrMsysBuildPathArguments {
    param([Parameter(Mandatory = $true)][string]$RepoPath)

    $msysRoot = Convert-ToAsrMsysPath -PathValue $RepoPath
    return @("ROOT_DIR=$msysRoot", "OUT=$msysRoot/out")
}

function Add-AsrMsysBuildPathsToCommand {
    param(
        [Parameter(Mandatory = $true)][string]$CommandText,
        [Parameter(Mandatory = $true)][string]$RepoPath
    )

    if ([string]::IsNullOrWhiteSpace($CommandText)) {
        throw 'ASR360x build command cannot be empty.'
    }

    # Replace caller-supplied path assignments so the last run cannot leak a
    # Windows path into MSYS. Product-specific build arguments stay untouched.
    $withoutPaths = [regex]::Replace(
        $CommandText,
        '(?i)(?<!\S)(?:ROOT_DIR|OUT)=(?:"[^"]*"|''[^'']*''|\S+)',
        ''
    )
    $withoutPaths = $withoutPaths.Trim()
    $pathArguments = @(Get-AsrMsysBuildPathArguments -RepoPath $RepoPath | ForEach-Object {
        if ($_ -match '\s') { '"' + $_ + '"' } else { $_ }
    })
    $effective = ($withoutPaths + ' ' + ($pathArguments -join ' ')).Trim()

    if ($effective -match '(?i)(?:ROOT_DIR|OUT)=[^\r\n]*\\') {
        throw "ASR360x build command still contains a Windows path: $effective"
    }
    return $effective
}
