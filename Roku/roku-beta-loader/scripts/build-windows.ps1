<#
.SYNOPSIS
    Build the roku-beta-loader CLI (all platforms) and GUI (Windows) on a Windows host.

.DESCRIPTION
    CLI prerequisites: Go 1.22+
    GUI prerequisites:
      WebView2 Runtime (usually already installed on Windows 10/11)
      go install github.com/wailsapp/wails/v2/cmd/wails@latest

.PARAMETER Version
    Version string stamped into the binary. Defaults to git describe, else "dev".

.PARAMETER OutputDir
    Output directory for CLI binaries. Defaults to "dist".

.PARAMETER NoGUI
    Skip the Wails GUI build; produce CLI binaries only.

.EXAMPLE
    pwsh scripts/build-windows.ps1

.EXAMPLE
    pwsh scripts/build-windows.ps1 -NoGUI

.EXAMPLE
    pwsh scripts/build-windows.ps1 -Version 1.2.3
#>
[CmdletBinding()]
param(
    [string]$Version,
    [string]$OutputDir = "dist",
    [switch]$NoGUI
)

$ErrorActionPreference = "Stop"

$ScriptDir  = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

# Resolve version
if (-not $Version) {
    try { $Version = (git -C $ProjectRoot describe --tags --always --dirty 2>$null) }
    catch { $Version = $null }
    if (-not $Version) { $Version = "dev" }
}
Write-Host "roku-beta-loader $Version"

# ── CLI: cross-compile for all platforms ─────────────────────────────────────
$Platforms = @(
    "linux/amd64", "linux/arm64",
    "darwin/amd64", "darwin/arm64",
    "windows/amd64", "windows/arm64"
)
$LdFlags = "-s -w -X main.version=$Version"

Write-Host ""
Write-Host "Building CLI → $OutputDir/"
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$origGoos   = $env:GOOS
$origGoarch = $env:GOARCH
$origCgo    = $env:CGO_ENABLED

try {
    foreach ($platform in $Platforms) {
        $parts = $platform.Split("/")
        $goos  = $parts[0]
        $goarch = $parts[1]
        $out   = Join-Path $OutputDir "roku-beta-loader-$goos-$goarch"
        if ($goos -eq "windows") { $out += ".exe" }

        Write-Host ("  {0,-24} {1}" -f "$goos/$goarch", $out)
        $env:CGO_ENABLED = "0"
        $env:GOOS   = $goos
        $env:GOARCH = $goarch
        go build -trimpath -ldflags $LdFlags -o $out ./cmd/roku-beta-loader
        if ($LASTEXITCODE -ne 0) { throw "build failed for $platform" }
    }
} finally {
    $env:GOOS        = $origGoos
    $env:GOARCH      = $origGoarch
    $env:CGO_ENABLED = $origCgo
}

$checksumFile = Join-Path $OutputDir "SHA256SUMS"
Get-ChildItem -Path $OutputDir -Filter "roku-beta-loader-*" |
    ForEach-Object { "{0}  {1}" -f (Get-FileHash $_.FullName -Algorithm SHA256).Hash.ToLower(), $_.Name } |
    Set-Content -Path $checksumFile -Encoding ascii
Write-Host "Checksums: $checksumFile"

# ── GUI: native Windows build via Wails ──────────────────────────────────────
if ($NoGUI) {
    Write-Host ""
    Write-Host "Done (CLI only)."
    exit 0
}

Write-Host ""
Write-Host "Building GUI (Windows)..."

if (-not (Get-Command wails -ErrorAction SilentlyContinue)) {
    Write-Warning "wails not found — skipping GUI build."
    Write-Host "  Install: go install github.com/wailsapp/wails/v2/cmd/wails@latest"
    Write-Host ""
    Write-Host "Done (CLI only)."
    exit 0
}

wails build -ldflags "-X main.version=$Version"
Write-Host "GUI binary: build\bin\roku-beta-loader-gui.exe"

Write-Host ""
Write-Host "Done."
