[CmdletBinding()]
param(
    [Parameter(Position = 0)]
    [string]$PackagePath,

    [string]$CommitMessage = "Website update",

    [switch]$Yes
)

$ErrorActionPreference = 'Stop'

function Stop-WithMessage {
    param([string]$Message)
    Write-Host ""
    Write-Host "ERROR: $Message" -ForegroundColor Red
    exit 1
}

function Run-Git {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Args)

    & git @Args
    if ($LASTEXITCODE -ne 0) {
        Stop-WithMessage "Git command failed: git $($Args -join ' ')"
    }
}

Write-Host ""
Write-Host "Crux Resolve Website Update" -ForegroundColor Cyan
Write-Host "---------------------------" -ForegroundColor DarkGray

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Stop-WithMessage "Git is not installed or is not available in PATH."
}

$RepoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $RepoRoot

$TempDir = $null

try {
    $InsideRepo = (& git rev-parse --is-inside-work-tree 2>$null).Trim()
    if ($LASTEXITCODE -ne 0 -or $InsideRepo -ne 'true') {
        Stop-WithMessage "This script is not running from inside the website Git repository."
    }

    $CurrentBranch = (& git branch --show-current).Trim()
    if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($CurrentBranch)) {
        Stop-WithMessage "Could not determine the current Git branch."
    }

    $ExistingChanges = @(& git status --porcelain)
    if ($LASTEXITCODE -ne 0) {
        Stop-WithMessage "Could not read Git status."
    }

    if ($ExistingChanges.Count -gt 0) {
        Write-Host ""
        Write-Host "The repository already has local changes:" -ForegroundColor Yellow
        $ExistingChanges | ForEach-Object { Write-Host "  $_" }
        Stop-WithMessage "Commit, stash, or discard those changes before applying a website update package."
    }

    Write-Host "Repository: $RepoRoot"
    Write-Host "Branch:     $CurrentBranch"
    Write-Host ""
    Write-Host "Updating local branch..."
    Run-Git pull --ff-only

    if ([string]::IsNullOrWhiteSpace($PackagePath)) {
        $PackagePath = Read-Host "Paste the full path to the update ZIP or folder"
    }

    if ([string]::IsNullOrWhiteSpace($PackagePath)) {
        Stop-WithMessage "No update package was provided."
    }

    $PackagePath = $PackagePath.Trim('"')
    if (-not (Test-Path -LiteralPath $PackagePath)) {
        Stop-WithMessage "Package not found: $PackagePath"
    }

    $ResolvedPackage = (Resolve-Path -LiteralPath $PackagePath).Path
    $PackageItem = Get-Item -LiteralPath $ResolvedPackage

    if ($PackageItem.PSIsContainer) {
        $SourceRoot = $ResolvedPackage
    }
    elseif ($PackageItem.Extension -ieq '.zip') {
        $TempDir = Join-Path ([System.IO.Path]::GetTempPath()) ("crux-site-update-" + [guid]::NewGuid().ToString('N'))
        New-Item -ItemType Directory -Path $TempDir | Out-Null
        Write-Host "Extracting update package..."
        Expand-Archive -LiteralPath $ResolvedPackage -DestinationPath $TempDir -Force
        $SourceRoot = $TempDir
    }
    else {
        Stop-WithMessage "The update package must be a ZIP file or a folder."
    }

    # If the package contains one wrapper folder named site-update, use its contents.
    $TopItems = @(Get-ChildItem -LiteralPath $SourceRoot -Force)
    if ($TopItems.Count -eq 1 -and $TopItems[0].PSIsContainer -and $TopItems[0].Name -ieq 'site-update') {
        $SourceRoot = $TopItems[0].FullName
    }

    $ManifestPath = Join-Path $SourceRoot 'site-update.json'
    if (Test-Path -LiteralPath $ManifestPath) {
        try {
            $Manifest = Get-Content -LiteralPath $ManifestPath -Raw | ConvertFrom-Json
            if ($Manifest.commitMessage -and $CommitMessage -eq 'Website update') {
                $CommitMessage = [string]$Manifest.commitMessage
            }
        }
        catch {
            Stop-WithMessage "site-update.json exists but could not be read: $($_.Exception.Message)"
        }
    }

    $Files = @(Get-ChildItem -LiteralPath $SourceRoot -Recurse -File -Force | Where-Object {
        $_.FullName -ne $ManifestPath -and $_.Name -ne 'README.txt'
    })

    if ($Files.Count -eq 0) {
        Stop-WithMessage "The update package does not contain any files to install."
    }

    Write-Host ""
    Write-Host "Installing $($Files.Count) file(s)..."

    foreach ($File in $Files) {
        $RelativePath = $File.FullName.Substring($SourceRoot.Length).TrimStart('\', '/')

        if ([string]::IsNullOrWhiteSpace($RelativePath)) {
            continue
        }

        if ($RelativePath -match '(^|[\\/])\.git([\\/]|$)') {
            Stop-WithMessage "The package contains a .git path, which is not allowed."
        }

        $Destination = Join-Path $RepoRoot $RelativePath
        $DestinationFull = [System.IO.Path]::GetFullPath($Destination)
        $RepoFull = [System.IO.Path]::GetFullPath($RepoRoot + [System.IO.Path]::DirectorySeparatorChar)

        if (-not $DestinationFull.StartsWith($RepoFull, [System.StringComparison]::OrdinalIgnoreCase)) {
            Stop-WithMessage "Unsafe package path detected: $RelativePath"
        }

        $DestinationDirectory = Split-Path -Parent $DestinationFull
        if (-not (Test-Path -LiteralPath $DestinationDirectory)) {
            New-Item -ItemType Directory -Path $DestinationDirectory -Force | Out-Null
        }

        Copy-Item -LiteralPath $File.FullName -Destination $DestinationFull -Force
        Write-Host "  $RelativePath"
    }

    # Optional package manifest can request removals using repo-relative paths.
    if ($Manifest -and $Manifest.delete) {
        foreach ($DeletePath in @($Manifest.delete)) {
            $DeleteRelative = ([string]$DeletePath).TrimStart('\', '/')
            if ([string]::IsNullOrWhiteSpace($DeleteRelative)) { continue }

            $DeleteFull = [System.IO.Path]::GetFullPath((Join-Path $RepoRoot $DeleteRelative))
            $RepoFull = [System.IO.Path]::GetFullPath($RepoRoot + [System.IO.Path]::DirectorySeparatorChar)
            if (-not $DeleteFull.StartsWith($RepoFull, [System.StringComparison]::OrdinalIgnoreCase)) {
                Stop-WithMessage "Unsafe delete path detected: $DeleteRelative"
            }

            if (Test-Path -LiteralPath $DeleteFull) {
                Remove-Item -LiteralPath $DeleteFull -Recurse -Force
                Write-Host "  DELETE $DeleteRelative" -ForegroundColor Yellow
            }
        }
    }

    $Changes = @(& git status --short)
    if ($LASTEXITCODE -ne 0) {
        Stop-WithMessage "Could not read Git status after installing the package."
    }

    if ($Changes.Count -eq 0) {
        Write-Host ""
        Write-Host "No website files changed. Nothing to publish." -ForegroundColor Yellow
        exit 0
    }

    Write-Host ""
    Write-Host "Changes ready to publish:" -ForegroundColor Green
    $Changes | ForEach-Object { Write-Host "  $_" }

    if (-not $Yes) {
        Write-Host ""
        $Answer = Read-Host "Commit and push these changes to '$CurrentBranch'? (Y/N)"
        if ($Answer -notmatch '^(y|yes)$') {
            Write-Host ""
            Write-Host "Nothing was committed or pushed. The copied files remain in your local repo." -ForegroundColor Yellow
            exit 0
        }
    }

    Write-Host ""
    Write-Host "Publishing..."
    Run-Git add -A
    Run-Git commit -m $CommitMessage
    Run-Git push origin $CurrentBranch

    Write-Host ""
    Write-Host "Website update pushed successfully." -ForegroundColor Green
    Write-Host "GitHub Pages may take a minute or two to publish the new build."
}
finally {
    if ($TempDir -and (Test-Path -LiteralPath $TempDir)) {
        Remove-Item -LiteralPath $TempDir -Recurse -Force -ErrorAction SilentlyContinue
    }
    Pop-Location
}
