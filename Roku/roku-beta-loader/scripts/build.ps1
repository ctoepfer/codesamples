<#
.SYNOPSIS
    Cross-compile the roku-beta-loader CLI for Linux, Windows, and macOS.

.DESCRIPTION
    PowerShell equivalent of scripts/build.sh for Windows hosts.

.PARAMETER Platforms
    One or more GOOS/GOARCH targets (e.g. windows/amd64 linux/amd64).
    Defaults to the full matrix.

.PARAMETER Version
    Version string stamped into the binary. Defaults to `git describe`, else "dev".

.PARAMETER OutputDir
    Output directory. Defaults to "dist".

.EXAMPLE
    pwsh scripts/build.ps1

.EXAMPLE
    pwsh scripts/build.ps1 -Platforms windows/amd64,darwin/arm64
#>
[CmdletBinding()]
param(
    [string[]]$Platforms,
    [string]$Version,
    [string]$OutputDir = "dist"
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

$BinName = "roku-beta-loader"
$Pkg = "./cmd/roku-beta-loader"

$DefaultPlatforms = @(
    "linux/amd64",
    "linux/arm64",
    "darwin/amd64",
    "darwin/arm64",
    "windows/amd64",
    "windows/arm64"
)

if (-not $Platforms -or $Platforms.Count -eq 0) {
    $Platforms = $DefaultPlatforms
}

if (-not $Version) {
    try {
        $Version = (git -C $ProjectRoot describe --tags --always --dirty 2>$null)
    } catch {
        $Version = $null
    }
    if (-not $Version) { $Version = "dev" }
}

$LdFlags = "-s -w -X main.version=$Version"

Write-Host "Building $BinName $Version"
Write-Host "Output: $OutputDir/"
Write-Host ""

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

# Preserve the caller's Go env so we can restore it afterward.
$origGoos = $env:GOOS
$origGoarch = $env:GOARCH
$origCgo = $env:CGO_ENABLED

try {
    foreach ($platform in $Platforms) {
        $parts = $platform.Split("/")
        if ($parts.Count -ne 2 -or -not $parts[0] -or -not $parts[1]) {
            Write-Warning "Skipping malformed platform '$platform' (expected GOOS/GOARCH)"
            continue
        }
        $goos = $parts[0]
        $goarch = $parts[1]

        $out = Join-Path $OutputDir "$BinName-$goos-$goarch"
        if ($goos -eq "windows") { $out += ".exe" }

        Write-Host "  -> $goos/$goarch"
        $env:CGO_ENABLED = "0"
        $env:GOOS = $goos
        $env:GOARCH = $goarch
        go build -trimpath -ldflags $LdFlags -o $out $Pkg
        if ($LASTEXITCODE -ne 0) { throw "build failed for $platform" }
    }
}
finally {
    $env:GOOS = $origGoos
    $env:GOARCH = $origGoarch
    $env:CGO_ENABLED = $origCgo
}

Write-Host ""
Write-Host "Done. Artifacts in $OutputDir/:"
Get-ChildItem -Path $OutputDir -Filter "$BinName-*" | Select-Object -ExpandProperty Name

# Generate a checksums file.
$checksumFile = Join-Path $OutputDir "SHA256SUMS"
Get-ChildItem -Path $OutputDir -Filter "$BinName-*" |
    ForEach-Object { "{0}  {1}" -f (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower(), $_.Name } |
    Set-Content -Path $checksumFile -Encoding ascii
Write-Host "Checksums: $checksumFile"
