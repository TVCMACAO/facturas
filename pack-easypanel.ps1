# Empaqueta el proyecto en .zip para subir a Easypanel (fuente tipo "Upload").
# Uso:  .\pack-easypanel.ps1
#       .\pack-easypanel.ps1 -OutputDir "C:\Deploy"

param(
    [string]$OutputDir = "",
    [switch]$KeepStaging
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
if (-not $OutputDir) { $OutputDir = Join-Path $Root "dist" }

$Timestamp = Get-Date -Format "yyyyMMdd-HHmmss"
$GitCommit = "unknown"
try {
    Push-Location $Root
    $GitCommit = (git rev-parse --short HEAD 2>$null)
    if (-not $GitCommit) { $GitCommit = "unknown" }
} finally {
    Pop-Location
}

$ZipName = "cuentas-easypanel-$Timestamp-$GitCommit.zip"
$ZipPath = Join-Path $OutputDir $ZipName
$Staging = Join-Path $env:TEMP "cuentas-easypanel-pack-$Timestamp"

$ExcludeDirNames = @(
    ".git", ".venv", "venv", "env", "ENV", "__pycache__",
    ".pytest_cache", ".cursor", ".mypy_cache", "htmlcov", "dist",
    "instance", "node_modules", ".idea", ".vscode"
)

function Test-ExcludedFile {
    param([string]$RelativePath, [string]$FileName)
    if ($FileName -match '\.(pyc|pyo|log|db|sqlite3?)$') { return $true }
    if ($FileName -like ".env" -or $FileName -like ".env.*") { return $true }
    if ($FileName -like "debug-*.log") { return $true }
    if ($FileName -eq "Thumbs.db" -or $FileName -eq "desktop.ini") { return $true }
    if ($FileName -like "*.md" -and $FileName -ne "README.md") { return $true }
    return $false
}

function Copy-ProjectTree {
    param(
        [string]$SourceRoot,
        [string]$DestRoot,
        [string]$RelativePath = ""
    )
    $CurrentSource = if ($RelativePath) { Join-Path $SourceRoot $RelativePath } else { $SourceRoot }
    $CurrentDest = if ($RelativePath) { Join-Path $DestRoot $RelativePath } else { $DestRoot }

    foreach ($dir in Get-ChildItem -Path $CurrentSource -Directory -Force -ErrorAction SilentlyContinue) {
        if ($ExcludeDirNames -contains $dir.Name) { continue }
        $rel = if ($RelativePath) { Join-Path $RelativePath $dir.Name } else { $dir.Name }
        Copy-ProjectTree -SourceRoot $SourceRoot -DestRoot $DestRoot -RelativePath $rel
    }

    foreach ($file in Get-ChildItem -Path $CurrentSource -File -Force -ErrorAction SilentlyContinue) {
        $rel = if ($RelativePath) { Join-Path $RelativePath $file.Name } else { $file.Name }
        if (Test-ExcludedFile -RelativePath $rel -FileName $file.Name) { continue }
        $targetFile = Join-Path $DestRoot $rel
        $targetDir = Split-Path $targetFile -Parent
        if (-not (Test-Path $targetDir)) {
            New-Item -ItemType Directory -Path $targetDir -Force | Out-Null
        }
        Copy-Item -Path $file.FullName -Destination $targetFile -Force
    }
}

Write-Host ""
Write-Host "=== Empaquetado Easypanel ===" -ForegroundColor Cyan
Write-Host "Origen:  $Root"
Write-Host "Salida:  $ZipPath"
Write-Host "Commit:  $GitCommit"
Write-Host ""

if (Test-Path $Staging) { Remove-Item $Staging -Recurse -Force }
New-Item -ItemType Directory -Path $Staging -Force | Out-Null
New-Item -ItemType Directory -Path $OutputDir -Force | Out-Null
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }

Copy-ProjectTree -SourceRoot $Root -DestRoot $Staging

$SourceRev = "$(Get-Date -Format 'yyyy-MM-dd-HHmmss')-$GitCommit"
Set-Content -Path (Join-Path $Staging "SOURCE_REV") -Value $SourceRev -NoNewline -Encoding utf8

Add-Type -AssemblyName System.IO.Compression.FileSystem
[System.IO.Compression.ZipFile]::CreateFromDirectory($Staging, $ZipPath)

if (-not $KeepStaging) {
    Remove-Item $Staging -Recurse -Force
}

$SizeMB = [math]::Round((Get-Item $ZipPath).Length / 1MB, 2)
$HasDockerfile = Test-Path (Join-Path $Staging "Dockerfile") -ErrorAction SilentlyContinue
if (-not $KeepStaging) {
    # Verificar contenido del zip
    $zip = [System.IO.Compression.ZipFile]::OpenRead($ZipPath)
    $HasDockerfile = ($zip.Entries | Where-Object { $_.FullName -eq "Dockerfile" }).Count -gt 0
    $zip.Dispose()
}

Write-Host "Listo." -ForegroundColor Green
Write-Host "  Archivo:    $ZipPath"
Write-Host "  Tamano:     $SizeMB MB"
Write-Host "  SOURCE_REV: $SourceRev"
Write-Host "  Dockerfile: $(if ($HasDockerfile) { 'si' } else { 'NO - revisar' })"
Write-Host ""
Write-Host "En Easypanel:" -ForegroundColor Yellow
Write-Host "  1. Fuente -> Upload -> sube este .zip"
Write-Host "  2. Build -> Dockerfile en la raiz del zip"
Write-Host "  3. Build Arguments (opcional):"
Write-Host "       BUILD_COMMIT=$GitCommit"
Write-Host "       APP_BUILD_ID=2026-07-05-v4-deploy-fix"
Write-Host "  4. Variables de entorno (.env) van en Env, NO en el zip"
Write-Host ""
