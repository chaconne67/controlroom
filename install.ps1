# kmh-agent-kit installer for Windows PowerShell, Command Prompt, and Git Bash.
# Directories use junctions and files use hardlinks, so no Developer Mode is required.

[CmdletBinding()]
param(
    [string]$Agent,
    [string]$Gbrain,
    [string]$Project,
    [string]$ProfileName,
    [switch]$Help
)

$ErrorActionPreference = 'Stop'
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch { }

function Get-KitGitExecutable {
    $candidates = @()
    $command = Get-Command git.exe -ErrorAction SilentlyContinue
    if ($command -and $command.Source) { $candidates += $command.Source }
    if ($env:LOCALAPPDATA) {
        $candidates += (Join-Path $env:LOCALAPPDATA 'hermes\git\cmd\git.exe')
        $candidates += (Join-Path $env:LOCALAPPDATA 'hermes\git\bin\git.exe')
    }
    if ($env:ProgramFiles) { $candidates += (Join-Path $env:ProgramFiles 'Git\cmd\git.exe') }
    if (${env:ProgramFiles(x86)}) { $candidates += (Join-Path ${env:ProgramFiles(x86)} 'Git\cmd\git.exe') }

    foreach ($candidate in $candidates | Select-Object -Unique) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    throw '[error] Git을 찾지 못했습니다. kitpush에 Git이 필요합니다.'
}

function Invoke-BootstrapCheckout {
    param([hashtable]$ForwardedParameters)

    if (-not $env:USERPROFILE) { throw '[error] USERPROFILE이 없습니다.' }
    $checkout = Join-Path $env:USERPROFILE 'controlroom'
    $git = Get-KitGitExecutable
    if ((Test-Path -LiteralPath $checkout) -and
        -not (Test-Path -LiteralPath (Join-Path $checkout '.git') -PathType Container)) {
        throw "[error] 설치 경로가 이미 있지만 Git 저장소가 아닙니다: $checkout"
    }

    if (Test-Path -LiteralPath (Join-Path $checkout '.git') -PathType Container) {
        $dirty = & $git -C $checkout status --porcelain=v1 --untracked-files=normal
        if ($LASTEXITCODE -ne 0) { throw '[error] 기존 키트 상태 확인 실패' }
        if ($dirty) { throw "[error] 기존 키트에 로컬 변경이 있어 자동 설치를 중단합니다: $checkout" }
        & $git -C $checkout fetch --prune origin
        if ($LASTEXITCODE -ne 0) { throw '[error] origin 갱신 실패' }
        & $git -C $checkout show-ref --verify --quiet refs/remotes/origin/main
        if ($LASTEXITCODE -ne 0) { throw '[error] 원격 origin/main 브랜치가 없습니다.' }
        & $git -C $checkout show-ref --verify --quiet refs/heads/main
        if ($LASTEXITCODE -eq 0) {
            & $git -C $checkout checkout main
        } else {
            & $git -C $checkout checkout -b main --track origin/main
        }
        if ($LASTEXITCODE -ne 0) { throw '[error] main 브랜치 전환 실패' }
        & $git -C $checkout merge --ff-only origin/main
        if ($LASTEXITCODE -ne 0) { throw '[error] 기존 키트 fast-forward 실패' }
    } else {
        & $git clone --branch main --single-branch https://github.com/chaconne67/controlroom.git $checkout
        if ($LASTEXITCODE -ne 0) { throw '[error] kmh-agent-kit clone 실패' }
    }

    & (Join-Path $checkout 'install.ps1') @ForwardedParameters
    if (-not $?) { throw '[error] 체크아웃된 설치기 실행 실패' }
}

$forwardedParameters = @{}
foreach ($key in $PSBoundParameters.Keys) { $forwardedParameters[$key] = $PSBoundParameters[$key] }
$isRepositoryInstaller = $MyInvocation.MyCommand.Path -and $PSScriptRoot -and
    (Test-Path -LiteralPath (Join-Path $PSScriptRoot '.git') -PathType Container) -and
    (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'manifests\skills.json') -PathType Leaf)
if (-not $isRepositoryInstaller) {
    Invoke-BootstrapCheckout -ForwardedParameters $forwardedParameters
    return
}

$repoDir    = $PSScriptRoot
$homeDir    = $env:USERPROFILE
$claudeHome = if ($env:CLAUDE_HOME) { $env:CLAUDE_HOME } else { Join-Path $homeDir '.claude' }
$codexHome  = if ($env:CODEX_HOME)  { $env:CODEX_HOME }  else { Join-Path $homeDir '.codex' }
$agentsHome = Join-Path $homeDir '.agents'
$hermesHome = if ($env:HERMES_HOME) { $env:HERMES_HOME } elseif ($env:LOCALAPPDATA) { Join-Path $env:LOCALAPPDATA 'hermes' } else { Join-Path $homeDir '.hermes' }
$script:gitExe = Get-KitGitExecutable
$stamp      = Get-Date -Format 'yyyyMMdd-HHmmss'
$backupRoot = Join-Path $homeDir ".kmh-agent-kit-backup-$stamp"

function Show-Usage {
    @'
Controlroom (Windows PowerShell·Command Prompt·Git Bash)

최초 설치 또는 재연결:
  .\install.ps1 -Agent <등록-이름>

프로젝트 프로필 연결:
  .\install.ps1 -Project "$HOME\projects\rndlog" -ProfileName rndlog

이후 동기화:
  kitpull
  kitpush "변경 설명"
'@ | Write-Host
}

function Assert-Name {
    param([string]$Name, [string]$Kind)
    if (-not $Name -or $Name -notmatch '^[a-z0-9]([a-z0-9-]{0,30}[a-z0-9])?$') {
        throw "[error] $Kind 이름은 영문 소문자·숫자·중간 하이픈으로 된 1~32자여야 합니다: $Name"
    }
}

function Invoke-KitGit {
    param([Parameter(ValueFromRemainingArguments = $true)][string[]]$Arguments)
    & $script:gitExe -C $repoDir @Arguments
    if ($LASTEXITCODE -ne 0) { throw "[error] git 명령 실패: git -C $repoDir $($Arguments -join ' ')" }
}

function Backup-Entry {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $backupRoot)) {
        New-Item -ItemType Directory -Path $backupRoot | Out-Null
    }
    $flat = if ($Path.StartsWith($homeDir, 'OrdinalIgnoreCase')) {
        $Path.Substring($homeDir.Length)
    } else {
        $Path -replace '^[A-Za-z]:', ''
    }
    $flat = $flat.TrimStart('\').Replace('\', '_')
    Move-Item -LiteralPath $Path -Destination (Join-Path $backupRoot $flat) -Force
    Write-Host "  backup: $Path"
}

function Resolve-ProfileTarget {
    param([string]$Entry)

    $item = Get-Item -LiteralPath $Entry -Force
    if ($item.LinkType -in 'SymbolicLink', 'Junction') {
        $target = @($item.Target)[0]
        if (-not [System.IO.Path]::IsPathRooted($target)) {
            $target = Join-Path (Split-Path $Entry -Parent) $target
        }
        return (Resolve-Path -LiteralPath $target).Path
    }
    if ($item.PSIsContainer) { return $item.FullName }
    if ($item.Length -ge 4096) { return $null }

    $text = (Get-Content -LiteralPath $Entry -Raw -Encoding UTF8).Trim()
    if (-not $text -or $text.Contains("`n") -or [System.IO.Path]::IsPathRooted($text)) { return $null }
    if (-not $text.StartsWith('..') -and $text -notin 'AGENTS.md', 'CLAUDE.md') { return $null }
    $resolved = Join-Path (Split-Path $Entry -Parent) $text
    if (Test-Path -LiteralPath $resolved) { return (Resolve-Path -LiteralPath $resolved).Path }
    return $null
}

function Get-LinkTargetPath {
    param([System.IO.FileSystemInfo]$Item)

    if ($Item.LinkType -notin 'SymbolicLink', 'Junction' -or -not $Item.Target) {
        return $null
    }
    $target = @($Item.Target)[0]
    if (-not [System.IO.Path]::IsPathRooted($target)) {
        $target = Join-Path $Item.DirectoryName $target
    }
    return [System.IO.Path]::GetFullPath($target)
}

function Remove-LinkEntry {
    param([System.IO.FileSystemInfo]$Item)

    if ($Item.LinkType -eq 'Junction' -or $Item.PSIsContainer) {
        [System.IO.Directory]::Delete($Item.FullName)
    } else {
        [System.IO.File]::Delete($Item.FullName)
    }
}

function Link-Entry {
    param([string]$Target, [string]$Link)

    $target = (Get-Item -LiteralPath $Target -Force).FullName
    $targetIsDir = (Get-Item -LiteralPath $target -Force).PSIsContainer
    $existing = Get-Item -LiteralPath $Link -Force -ErrorAction SilentlyContinue
    if ($existing) {
        $existingTarget = Get-LinkTargetPath -Item $existing
        if ($existingTarget -and $existingTarget.TrimEnd('\') -eq $target.TrimEnd('\')) { return }

        if ($existing.LinkType -in 'SymbolicLink', 'Junction') {
            Remove-LinkEntry -Item $existing
        } elseif ($existing.LinkType -eq 'HardLink' -and -not $targetIsDir -and
                  [System.Linq.Enumerable]::SequenceEqual([byte[]][System.IO.File]::ReadAllBytes($Link), [byte[]][System.IO.File]::ReadAllBytes($target))) {
            # Git checkout은 원본 inode를 바꿀 수 있다. 내용이 같아도 매번 현재 원본에 다시 건다.
            [System.IO.File]::Delete($Link)
        } else {
            Backup-Entry -Path $Link
        }
    }

    $parent = Split-Path $Link -Parent
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    $type = if ($targetIsDir) { 'Junction' } else { 'HardLink' }
    New-Item -ItemType $type -Path $Link -Target $target | Out-Null
    Write-Host "  $type  $Link -> $target"
}

function Link-Profile {
    param([string]$Profile, [string]$Live, [switch]$PreserveExisting)

    if (-not (Test-Path -LiteralPath $Profile)) { return }
    if (-not (Test-Path -LiteralPath $Live)) {
        New-Item -ItemType Directory -Path $Live -Force | Out-Null
    }

    $skillsRoot = (Join-Path $repoDir 'skills').TrimEnd('\')
    $profileRoot = ([System.IO.Path]::GetFullPath($Profile)).TrimEnd('\')
    $skillsPrefix = $skillsRoot + [System.IO.Path]::DirectorySeparatorChar
    $profilePrefix = $profileRoot + [System.IO.Path]::DirectorySeparatorChar
    $linked = @{}
    foreach ($entry in Get-ChildItem -LiteralPath $Profile -Force) {
        $target = Resolve-ProfileTarget -Entry $entry.FullName
        if (-not $target) {
            Write-Warning "  skip (대상 해석 실패): $($entry.Name)"
            continue
        }
        $linkPath = Join-Path $Live $entry.Name
        if ($PreserveExisting -and (Test-Path -LiteralPath $linkPath)) {
            $existing = Get-Item -LiteralPath $linkPath -Force
            $existingTarget = Get-LinkTargetPath -Item $existing
            $managed = $existingTarget -and (
                $existingTarget.StartsWith($skillsPrefix, 'OrdinalIgnoreCase') -or
                $existingTarget.StartsWith($profilePrefix, 'OrdinalIgnoreCase'))
            if (-not $managed) {
                Write-Host "  Hermes 기존 스킬 유지: $linkPath"
                $linked[$entry.Name] = $true
                continue
            }
        }
        Link-Entry -Target $target -Link $linkPath
        $linked[$entry.Name] = $true
    }

    foreach ($liveEntry in Get-ChildItem -LiteralPath $Live -Force) {
        if ($liveEntry.LinkType -notin 'SymbolicLink', 'Junction' -or $linked.ContainsKey($liveEntry.Name)) { continue }
        $target = Get-LinkTargetPath -Item $liveEntry
        if ($target -and ($target.StartsWith($skillsPrefix, 'OrdinalIgnoreCase') -or
            $target.StartsWith($profilePrefix, 'OrdinalIgnoreCase'))) {
            Remove-LinkEntry -Item $liveEntry
            Write-Host "  remove stale: $($liveEntry.FullName)"
        }
    }
}

function Remove-KitSkillLinks {
    param([string]$Live)

    if (-not (Test-Path -LiteralPath $Live)) { return }
    $skillsRoot = (Join-Path $repoDir 'skills').TrimEnd('\')
    foreach ($entry in Get-ChildItem -LiteralPath $Live -Force) {
        if ($entry.LinkType -notin 'SymbolicLink', 'Junction') { continue }
        $target = Get-LinkTargetPath -Item $entry
        if ($target -and $target.StartsWith($skillsRoot, 'OrdinalIgnoreCase')) {
            Remove-LinkEntry -Item $entry
            Write-Host "  remove legacy Codex user skill: $($entry.FullName)"
        }
    }
}

function Move-LegacyGlobalSkillCopies {
    $sources = @(Get-ChildItem -LiteralPath (Join-Path $repoDir 'skills\common') -Directory)
    foreach ($domain in Get-ChildItem -LiteralPath (Join-Path $repoDir 'skills\domains') -Directory) {
        $sources += @(Get-ChildItem -LiteralPath $domain.FullName -Directory)
    }

    $liveRoots = @("$codexHome\skills", "$agentsHome\skills", "$claudeHome\skills") | Select-Object -Unique
    $managedRoots = @(
        (Join-Path $repoDir 'skills'),
        (Join-Path $repoDir 'codex\skills'),
        (Join-Path $repoDir 'claude\skills')
    )
    foreach ($liveRoot in $liveRoots) {
        foreach ($source in $sources | Sort-Object Name -Unique) {
            $legacyPath = Join-Path $liveRoot $source.Name
            $legacy = Get-Item -LiteralPath $legacyPath -Force -ErrorAction SilentlyContinue
            if (-not $legacy) { continue }

            $target = Get-LinkTargetPath -Item $legacy
            $managed = $false
            if ($target -and (Test-Path -LiteralPath $target)) {
                foreach ($root in $managedRoots) {
                    $prefix = $root.TrimEnd('\') + [System.IO.Path]::DirectorySeparatorChar
                    if ($target.StartsWith($prefix, 'OrdinalIgnoreCase')) {
                        $managed = $true
                        break
                    }
                }
            }
            if ($managed) {
                if ($liveRoot.TrimEnd('\') -eq "$codexHome\skills".TrimEnd('\')) {
                    Remove-LinkEntry -Item $legacy
                    Write-Host "  remove legacy Codex skill link: $legacyPath"
                }
                continue
            }

            Backup-Entry -Path $legacyPath
            Write-Host "  migrate legacy user skill: $legacyPath"
        }
    }
}

function Get-Python {
    foreach ($name in 'python', 'python3', 'py') {
        $cmd = Get-Command $name -ErrorAction SilentlyContinue
        if ($cmd -and $cmd.Source -and $cmd.Source -notmatch '\\WindowsApps\\') { return $cmd.Source }
    }
    return $null
}

function Convert-ToGitBashPath {
    param([string]$Path)

    $cygpath = Get-Command cygpath.exe -ErrorAction SilentlyContinue
    if ($cygpath) { return (& $cygpath.Source -u $Path).Trim() }
    $full = [System.IO.Path]::GetFullPath($Path)
    if ($full -match '^([A-Za-z]):(.*)$') {
        return '/' + $matches[1].ToLowerInvariant() + ($matches[2] -replace '\\', '/')
    }
    return ($full -replace '\\', '/')
}

function Write-Utf8NoBom {
    param([string]$Path, [string]$Content)
    if (Test-Path -LiteralPath $Path -PathType Leaf) {
        $existing = [System.IO.File]::ReadAllText($Path)
        if ($existing -ceq $Content) { return }
    }
    $parent = Split-Path $Path -Parent
    if (-not (Test-Path -LiteralPath $parent)) {
        New-Item -ItemType Directory -Path $parent -Force | Out-Null
    }
    [System.IO.File]::WriteAllText($Path, $Content, (New-Object System.Text.UTF8Encoding($false)))
}

function Add-ShellLine {
    param([string]$Path, [string]$Marker, [string]$Line)

    $content = if (Test-Path -LiteralPath $Path) {
        Get-Content -LiteralPath $Path -Raw -Encoding UTF8
    } else { '' }
    if ($content -match [regex]::Escape($Marker)) {
        $pattern = '(?m)(^# ' + [regex]::Escape($Marker) + '\r?\n)[^\r\n]*'
        $replacement = [regex]::Replace($content, $pattern, [System.Text.RegularExpressions.MatchEvaluator]{
            param($match) $match.Groups[1].Value + $Line
        })
        Write-Utf8NoBom -Path $Path -Content $replacement
        return
    }
    if ($content -and -not $content.EndsWith("`n")) { $content += "`r`n" }
    $content += "`r`n# $Marker`r`n$Line`r`n"
    Write-Utf8NoBom -Path $Path -Content $content
    Write-Host "  shell source: $Path"
}

function Get-GitBashExecutable {
    $candidates = @()
    if ($env:HERMES_GIT_BASH_PATH) { $candidates += $env:HERMES_GIT_BASH_PATH }
    $gitParent = Split-Path $script:gitExe -Parent
    $gitRoot = Split-Path $gitParent -Parent
    $candidates += (Join-Path $gitRoot 'bin\bash.exe')
    $candidates += (Join-Path $gitRoot 'usr\bin\bash.exe')
    if ($env:LOCALAPPDATA) {
        $candidates += (Join-Path $env:LOCALAPPDATA 'hermes\git\bin\bash.exe')
        $candidates += (Join-Path $env:LOCALAPPDATA 'hermes\git\usr\bin\bash.exe')
    }
    if ($env:ProgramFiles) {
        $candidates += (Join-Path $env:ProgramFiles 'Git\bin\bash.exe')
        $candidates += (Join-Path $env:ProgramFiles 'Git\usr\bin\bash.exe')
    }
    if (${env:ProgramFiles(x86)}) {
        $candidates += (Join-Path ${env:ProgramFiles(x86)} 'Git\bin\bash.exe')
    }
    $command = Get-Command bash.exe -ErrorAction SilentlyContinue
    if ($command -and $command.Source -and $command.Source -notmatch '\\System32\\') {
        $candidates += $command.Source
    }

    foreach ($candidate in $candidates | Select-Object -Unique) {
        if ($candidate -and (Test-Path -LiteralPath $candidate -PathType Leaf)) {
            return (Resolve-Path -LiteralPath $candidate).Path
        }
    }
    throw '[error] Git Bash의 bash.exe를 찾지 못했습니다.'
}

function Add-UserPathEntry {
    param([string]$Path)
    $current = [Environment]::GetEnvironmentVariable('Path', 'User')
    $entries = @($current -split ';' | Where-Object { $_ })
    if (-not ($entries | Where-Object { $_.TrimEnd('\') -eq $Path.TrimEnd('\') })) {
        $updated = (@($Path) + $entries) -join ';'
        [Environment]::SetEnvironmentVariable('Path', $updated, 'User')
    }
    if (-not (($env:Path -split ';') | Where-Object { $_.TrimEnd('\') -eq $Path.TrimEnd('\') })) {
        $env:Path = "$Path;$env:Path"
    }
}

function Install-ShellCommands {
    $bashRepo = Convert-ToGitBashPath -Path $repoDir
    $aliasLine = '[ -f "' + $bashRepo + '/shell/kit-aliases.sh" ] && . "' + $bashRepo + '/shell/kit-aliases.sh"'
    Add-ShellLine -Path (Join-Path $homeDir '.bashrc') -Marker 'kmh-agent-kit aliases' -Line $aliasLine
    Add-ShellLine -Path (Join-Path $homeDir '.bash_profile') -Marker 'load ~/.bashrc for kmh-agent-kit' -Line '[ -f "$HOME/.bashrc" ] && . "$HOME/.bashrc"'

    $commandDir = Join-Path $homeDir '.local\bin'
    if (-not (Test-Path -LiteralPath $commandDir)) {
        New-Item -ItemType Directory -Path $commandDir -Force | Out-Null
    }
    $bash = Get-GitBashExecutable
    $aliasScript = "$bashRepo/shell/kit-aliases.sh"
    $gitDir = Split-Path $script:gitExe -Parent
    foreach ($command in 'controlroom', 'kitpull', 'kitpush') {
        $action = if ($command -eq 'kitpull') { 'pull ' } elseif ($command -eq 'kitpush') { 'push ' } else { '' }
        $wrapperPath = Join-Path $commandDir "$command.cmd"
        $invocation = "`"$bash`" --noprofile --norc `"$aliasScript`" ${action}%*"
        $content = "@$invocation`r`n"
        if (Test-Path -LiteralPath $wrapperPath -PathType Leaf) {
            $existing = [System.IO.File]::ReadAllText($wrapperPath).Replace("`r`n", "`n").TrimEnd("`n")
            $escapedInvocation = [regex]::Escape($invocation)
            $knownWrapper = $existing -match (
                '^(?:@' + $escapedInvocation +
                '|@set "PATH=[^"\r\n]+;%PATH%"&&' + $escapedInvocation +
                '|@echo off\nset "PATH=[^"\r\n]+;%PATH%"\n' + $escapedInvocation + ')$'
            )
            if ($knownWrapper) { continue }
        }
        if (Test-Path -LiteralPath $wrapperPath) {
            Backup-Entry -Path $wrapperPath
        }
        Write-Utf8NoBom -Path $wrapperPath -Content $content
    }
    $legacyKit = Join-Path $homeDir 'kmh-agent-kit'
    if (-not (Test-Path -LiteralPath $legacyKit)) { Link-Entry -Target $repoDir -Link $legacyKit }
    $legacyDocs = Join-Path $homeDir 'projects\_control-docs'
    if (-not (Test-Path -LiteralPath $legacyDocs)) { Link-Entry -Target (Join-Path $repoDir 'projects') -Link $legacyDocs }
    Add-UserPathEntry -Path $commandDir
    Add-UserPathEntry -Path $gitDir
}

function Install-Global {
    Move-LegacyGlobalSkillCopies
    Remove-KitSkillLinks -Live "$codexHome\skills"
    Write-Host "[claude] $claudeHome\skills"
    Link-Profile -Profile "$repoDir\claude\skills" -Live "$claudeHome\skills"
    Write-Host "[codex] $agentsHome\skills"
    Link-Profile -Profile "$repoDir\codex\skills" -Live "$agentsHome\skills"
    Write-Host "[hermes] $hermesHome\skills"
    Link-Profile -Profile "$repoDir\codex\skills" -Live "$hermesHome\skills" -PreserveExisting

    Write-Host '[instructions]'
    Link-Entry -Target "$repoDir\claude\CLAUDE.md" -Link "$claudeHome\CLAUDE.md"
    Link-Entry -Target "$repoDir\codex\AGENTS.md" -Link "$codexHome\AGENTS.md"
    Install-ShellCommands

    $python = Get-Python
    if ($python) {
        $env:PYTHONIOENCODING = 'utf-8'
        & $python "$repoDir\scripts\check-skill-deps.py"
        if ($LASTEXITCODE -ne 0) { throw '[error] 스킬 의존성 검사 실패' }
    } else {
        Write-Warning 'python 미발견 — check-skill-deps.py 건너뜀'
    }
}

function Install-ProjectProfile {
    param([string]$ProjectPath, [string]$Profile)

    Assert-Name -Name $Profile -Kind '프로필'
    $profileDir = Join-Path $repoDir "projects\$Profile"
    if (-not (Test-Path -LiteralPath $profileDir -PathType Container)) {
        throw "[error] 프로젝트 프로필 없음: $profileDir"
    }
    if (-not (Test-Path -LiteralPath $ProjectPath -PathType Container)) {
        throw "[error] 프로젝트 경로 없음: $ProjectPath"
    }
    $projectPath = (Resolve-Path -LiteralPath $ProjectPath).Path
    $docsSource = Get-ControlRoomDocsSource -Profile $Profile
    $hasDocsSource = $docsSource -and (Test-Path -LiteralPath $docsSource -PathType Container)
    if ($hasDocsSource) {
        $docsPath = Join-Path $projectPath 'docs'
        $existingDocs = Get-Item -LiteralPath $docsPath -Force -ErrorAction SilentlyContinue
        if ($existingDocs -and $existingDocs.LinkType -notin 'SymbolicLink', 'Junction') {
            throw "[error] 기존 프로젝트 문서를 보존하여 연결을 중단합니다: $docsPath"
        }
    }

    Remove-KitSkillLinks -Live "$projectPath\.codex\skills"
    if (Test-Path -LiteralPath "$profileDir\skills") {
        Link-Profile -Profile "$profileDir\skills" -Live "$projectPath\.claude\skills"
        Link-Profile -Profile "$profileDir\skills" -Live "$projectPath\.agents\skills"
    }
    foreach ($file in 'CLAUDE.md', 'AGENTS.md') {
        $profileFile = "$profileDir\$file"
        if (-not (Test-Path -LiteralPath $profileFile)) { continue }
        $target = Resolve-ProfileTarget -Entry $profileFile
        if (-not $target) { $target = $profileFile }
        Link-Entry -Target $target -Link "$projectPath\$file"
    }
    if ($hasDocsSource) {
        Link-Entry -Target $docsSource -Link $docsPath
    }
    Write-Host "project '$Profile' linked into $projectPath"
}

function Register-ProjectProfile {
    param([string]$ProjectPath, [string]$Profile)
    $projectPath = (Resolve-Path -LiteralPath $ProjectPath).Path
    Invoke-KitGit config --local --replace-all "kmh-agent-kit.project.$Profile" $projectPath
    Write-Host "project '$Profile' registered at $projectPath"
}

function Get-ControlRoomProjects {
    $manifest = Join-Path $repoDir 'manifests\windows-control-projects.tsv'
    if (-not (Test-Path -LiteralPath $manifest -PathType Leaf)) {
        throw "[error] Windows 조정실 프로젝트 계약 없음: $manifest"
    }

    $lineNumber = 0
    foreach ($rawLine in Get-Content -LiteralPath $manifest -Encoding UTF8) {
        $lineNumber += 1
        $line = $rawLine.Trim()
        if (-not $line -or $line.StartsWith('#')) { continue }
        $columns = @($rawLine -split "`t")
        if ($columns.Count -ne 3) {
            throw "[error] 프로젝트 계약 형식 오류: $manifest ${lineNumber}행"
        }
        $directory, $kind, $target = @($columns | ForEach-Object { $_.Trim() })
        if ($directory -notmatch '^[A-Za-z0-9_-]+$') {
            throw "[error] 프로젝트 폴더는 단일 상대 폴더 이름이어야 합니다: $directory"
        }
        if ($kind -eq 'profile') {
            Assert-Name -Name $target -Kind '프로필'
        } elseif ($kind -eq 'git') {
            if ($target -notmatch '^https://github\.com/[^/]+/[^/]+\.git$') {
                throw "[error] 프로젝트 Git 주소는 GitHub HTTPS 주소여야 합니다: $target"
            }
        } else {
            throw "[error] 알 수 없는 프로젝트 복원 방식: $kind"
        }
        [pscustomobject]@{ Directory = $directory; Kind = $kind; Target = $target }
    }
}

function Get-ControlRoomProjectPath {
    param($Entry)

    if ($Entry.Kind -eq 'profile') {
        $savedPath = & $script:gitExe -C $repoDir config --local --get "kmh-agent-kit.project.$($Entry.Target)" 2>$null
        if ($LASTEXITCODE -eq 0 -and $savedPath) { return $savedPath.Trim() }
        if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 1) {
            throw "[error] 프로젝트 등록 정보 조회 실패: $($Entry.Target)"
        }
    }
    return Join-Path (Join-Path $homeDir 'projects') $Entry.Directory
}

function Get-ControlRoomDocsSource {
    param([string]$Profile)

    return Join-Path (Join-Path (Join-Path $repoDir 'projects') $Profile) 'docs'
}

function Restore-ControlRoomProjects {
    $bash = Get-GitBashExecutable
    $aliasScript = Convert-ToGitBashPath -Path (Join-Path $repoDir 'shell\kit-aliases.sh')
    $bashRepo = Convert-ToGitBashPath -Path $repoDir
    $bashHome = Convert-ToGitBashPath -Path $homeDir
    & $bash --noprofile --norc $aliasScript restore-repositories $bashRepo $bashHome
    if ($LASTEXITCODE -ne 0) { throw '[error] 조정실 저장소 복원 실패' }

    foreach ($entry in Get-ControlRoomProjects) {
        $projectPath = Get-ControlRoomProjectPath -Entry $entry
        if ($entry.Kind -eq 'git') {
            $skillsPath = Join-Path $projectPath 'skills'
            if (Test-Path -LiteralPath $skillsPath -PathType Container) {
                Link-Profile -Profile $skillsPath -Live "$projectPath\.claude\skills"
                Link-Profile -Profile $skillsPath -Live "$projectPath\.agents\skills"
            }
            continue
        }
        if (-not (Test-Path -LiteralPath $projectPath)) {
            New-Item -ItemType Directory -Path $projectPath -Force | Out-Null
            Write-Host "project folder created: $projectPath"
        } elseif (-not (Test-Path -LiteralPath $projectPath -PathType Container)) {
            throw "[error] 프로젝트 경로가 폴더가 아닙니다: $projectPath"
        }
        Register-ProjectProfile -ProjectPath $projectPath -Profile $entry.Target
    }
}

function Register-KnownProjects {
    param([string]$AgentName)

    if ($AgentName -eq 'windows-control') {
        Restore-ControlRoomProjects
    } elseif ($AgentName -eq 'main') {
        foreach ($profile in Get-ChildItem -LiteralPath "$repoDir\projects" -Directory) {
            $projectPath = Join-Path $homeDir "projects\$($profile.Name)"
            if (Test-Path -LiteralPath $projectPath -PathType Container) {
                Register-ProjectProfile -ProjectPath $projectPath -Profile $profile.Name
            }
        }
    } elseif ($AgentName -eq 'fundkeeper') {
        $projectPath = Join-Path $homeDir 'fundkeeper'
        if (Test-Path -LiteralPath $projectPath -PathType Container) {
            Register-ProjectProfile -ProjectPath $projectPath -Profile 'fundkeeper'
        }
    } else {
        $projectPath = Join-Path $homeDir $AgentName
        if ((Test-Path -LiteralPath "$repoDir\projects\$AgentName" -PathType Container) -and
            (Test-Path -LiteralPath $projectPath -PathType Container)) {
            Register-ProjectProfile -ProjectPath $projectPath -Profile $AgentName
        }
    }
}

function Install-RegisteredProjects {
    $rows = & $script:gitExe -C $repoDir config --local --get-regexp '^kmh-agent-kit\.project\.' 2>$null
    if ($LASTEXITCODE -ne 0 -and $LASTEXITCODE -ne 1) { throw '[error] 프로젝트 등록 정보 조회 실패' }
    foreach ($row in $rows) {
        if ($row -notmatch '^(\S+)\s+(.+)$') { continue }
        $profile = ($matches[1] -split '\.')[-1]
        $projectPath = $matches[2]
        if (-not (Test-Path -LiteralPath "$repoDir\projects\$profile" -PathType Container)) {
            Write-Warning "등록된 프로젝트 프로필이 없어 건너뜀: $profile"
            continue
        }
        if (-not (Test-Path -LiteralPath $projectPath -PathType Container)) {
            Write-Warning "등록된 프로젝트 경로가 없어 건너뜀: $projectPath"
            continue
        }
        Install-ProjectProfile -ProjectPath $projectPath -Profile $profile
    }
}

function Install-AgentCard {
    param([string]$AgentName)
    Assert-Name -Name $AgentName -Kind '등록'
    $card = Join-Path $repoDir "gbrain-cards\$AgentName.md"
    if (-not (Test-Path -LiteralPath $card -PathType Leaf)) {
        throw "[error] 등록되지 않은 에이전트: $AgentName"
    }
    Link-Entry -Target $card -Link (Join-Path $homeDir '.gbrain-agent.md')
    if ($AgentName -notin 'main', 'windows-control') {
        $commandDir = Join-Path $homeDir '.local\bin'
        $proxy = Join-Path $repoDir 'gbrain\bin\gbrain-remote-proxy'
        Link-Entry -Target $proxy -Link (Join-Path $commandDir "gbrain-$AgentName")
        $bash = Get-GitBashExecutable
        $bashProxy = Convert-ToGitBashPath -Path $proxy
        $content = "@echo off`r`n`"$bash`" --noprofile --norc `"$bashProxy`" $AgentName %*`r`n"
        Write-Utf8NoBom -Path (Join-Path $commandDir "gbrain-$AgentName.cmd") -Content $content
    }
}

function Assert-Install {
    param([string]$AgentName)

    foreach ($path in "$claudeHome\CLAUDE.md", "$codexHome\AGENTS.md") {
        $item = Get-Item -LiteralPath $path -Force
        if ($item.LinkType -ne 'HardLink') { throw "[error] 하드링크 검증 실패: $path" }
    }
    if ($AgentName) {
        $cardPath = Join-Path $homeDir '.gbrain-agent.md'
        $cardItem = Get-Item -LiteralPath $cardPath -Force
        if ($cardItem.LinkType -ne 'HardLink') { throw "[error] GBrain 카드 하드링크 검증 실패: $cardPath" }
        $savedAgent = (& $script:gitExe -C $repoDir config --local --get kmh-agent-kit.agent).Trim()
        if ($LASTEXITCODE -ne 0 -or $savedAgent -ne $AgentName) {
            throw "[error] 등록 이름 저장 검증 실패: $AgentName"
        }
        if ($AgentName -eq 'windows-control') {
            foreach ($entry in Get-ControlRoomProjects) {
                $projectPath = Get-ControlRoomProjectPath -Entry $entry
                if (-not (Test-Path -LiteralPath $projectPath -PathType Container)) {
                    throw "[error] 프로젝트 폴더 검증 실패: $projectPath"
                }
                if ($entry.Kind -eq 'git') {
                    $skillsPath = Join-Path $projectPath 'skills'
                    if (Test-Path -LiteralPath $skillsPath -PathType Container) {
                        foreach ($source in Get-ChildItem -LiteralPath $skillsPath -Directory) {
                            if (-not (Test-Path -LiteralPath (Join-Path $source.FullName 'SKILL.md'))) { continue }
                            foreach ($toolHome in '.claude', '.agents') {
                                $link = Get-Item -LiteralPath "$projectPath\$toolHome\skills\$($source.Name)" -Force
                                $target = Get-LinkTargetPath -Item $link
                                if (-not $target -or $target.TrimEnd('\') -ne $source.FullName.TrimEnd('\')) {
                                    throw "[error] 프로젝트 스킬 링크 검증 실패: $($link.FullName)"
                                }
                            }
                        }
                    }
                    continue
                }
                $savedPath = (& $script:gitExe -C $repoDir config --local --get "kmh-agent-kit.project.$($entry.Target)").Trim()
                $resolvedPath = (Resolve-Path -LiteralPath $projectPath).Path
                if ($LASTEXITCODE -ne 0 -or $savedPath -ne $resolvedPath) {
                    throw "[error] 프로젝트 등록 검증 실패: $($entry.Target)"
                }
                foreach ($file in 'CLAUDE.md', 'AGENTS.md') {
                    if (-not (Test-Path -LiteralPath (Join-Path $repoDir "projects\$($entry.Target)\$file") -PathType Leaf)) { continue }
                    $liveFile = Get-Item -LiteralPath (Join-Path $projectPath $file) -Force
                    if ($liveFile.LinkType -ne 'HardLink') {
                        throw "[error] 프로젝트 지침 링크 검증 실패: $($liveFile.FullName)"
                    }
                }
                $docsSource = Get-ControlRoomDocsSource -Profile $entry.Target
                if (-not $docsSource -or -not (Test-Path -LiteralPath $docsSource -PathType Container)) {
                    throw "[error] 프로젝트 문서 원본 없음: $($entry.Target)"
                }
                $docsPath = Join-Path $projectPath 'docs'
                $docsItem = Get-Item -LiteralPath $docsPath -Force
                $docsTarget = Get-LinkTargetPath -Item $docsItem
                $expectedDocsTarget = (Get-Item -LiteralPath $docsSource -Force).FullName
                if (-not $docsTarget -or $docsTarget.TrimEnd('\') -ne $expectedDocsTarget.TrimEnd('\')) {
                    throw "[error] 프로젝트 문서 링크 검증 실패: $docsPath"
                }
            }
            $gbrainHost = if ($env:GBRAIN_HOST) { $env:GBRAIN_HOST } else { 'chaconne@49.247.45.243' }
            & ssh $gbrainHost '/home/chaconne/.gbrain/bin/gbrain_with_google_env.sh get agent/gbrain-operating-protocol --source default' | Out-Null
            if ($LASTEXITCODE -ne 0) { throw '[error] GBrain 공용 문서 조회 검증 실패' }
        } elseif ($AgentName -ne 'main') {
            $wrapper = Join-Path $homeDir ".local\bin\gbrain-$AgentName"
            if ((Get-Item -LiteralPath $wrapper -Force).LinkType -ne 'HardLink') {
                throw "[error] GBrain 프록시 하드링크 검증 실패: $wrapper"
            }
            & "$wrapper.cmd" --source default get agent/gbrain-operating-protocol | Out-Null
            if ($LASTEXITCODE -ne 0) { throw '[error] GBrain 공용 문서 조회 검증 실패' }
        }
    }
}

if ($Help) {
    Show-Usage
    exit 0
}
if ($Gbrain) {
    if ($Agent -and $Agent -ne $Gbrain) { throw '[error] -Agent와 -Gbrain 값이 다릅니다.' }
    $Agent = $Gbrain
}
if ($Project -and -not $ProfileName) {
    throw 'usage: .\install.ps1 -Project <경로> -ProfileName <프로필명>'
}
if ($ProfileName -and -not $Project) {
    throw '[error] -ProfileName에는 -Project가 필요합니다.'
}
if ($Project -and $Agent) {
    throw '[error] 에이전트 설치와 프로젝트 연결은 한 번에 하나씩 실행하세요.'
}

Invoke-KitGit rev-parse --git-dir | Out-Null
if ($Project) {
    Install-ProjectProfile -ProjectPath $Project -Profile $ProfileName
    Register-ProjectProfile -ProjectPath $Project -Profile $ProfileName
} else {
    Install-Global
    if ($Agent) {
        Install-AgentCard -AgentName $Agent
        Invoke-KitGit config --local kmh-agent-kit.agent $Agent
        Register-KnownProjects -AgentName $Agent
        Install-RegisteredProjects
    }
    Assert-Install -AgentName $Agent
}

Write-Host 'kmh-agent-kit installed (Windows junction/hardlink mode).'
if ($Agent) { Write-Host "등록 이름 저장: $Agent (kitpull·kitpush가 자동 사용)" }
if (Test-Path -LiteralPath $backupRoot) { Write-Host "기존 파일 백업: $backupRoot" }
