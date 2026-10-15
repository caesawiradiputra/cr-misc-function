<#
.SYNOPSIS
    Read-only report of a Windows development laptop: what is installed, what starts with
    Windows, what uses memory, and the settings that affect speed.

.DESCRIPTION
    Changes nothing. It writes one text report and a few CSV files into the output folder,
    so you can compare two laptops or decide what to remove. Steps that need an
    administrator (Defender exclusions, Windows optional features) say so in the report
    instead of failing; run the script from an elevated PowerShell to include them.

    Works on Windows PowerShell 5.1 and PowerShell 7.

.PARAMETER OutDir
    Folder for the report. Default: Documents\WSL-Migration\windows-report-<date>.

.PARAMETER IncludeFolderSizes
    Also measure the largest folders in the user profile (can take a few minutes).

.EXAMPLE
    .\scripts\powershell\dev-laptop-report.ps1
    .\scripts\powershell\dev-laptop-report.ps1 -OutDir D:\report -IncludeFolderSizes
#>
[CmdletBinding()]
param(
    [string]$OutDir = (Join-Path ([Environment]::GetFolderPath('MyDocuments')) ("WSL-Migration\windows-report-" + (Get-Date -Format 'yyyy-MM-dd'))),
    [switch]$IncludeFolderSizes
)

$ErrorActionPreference = 'Continue'
New-Item -ItemType Directory -Path $OutDir -Force | Out-Null
$report = Join-Path $OutDir 'windows-report.txt'
$isAdmin = ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)

# The report is built in memory and written once at the end: appending to the file many times
# can fail when a security agent scans it mid-write ("Stream was not readable").
$script:Buffer = New-Object System.Text.StringBuilder
function Add-Text {
    param([string]$Text)
    [void]$script:Buffer.AppendLine($Text)
}
function Write-Section {
    param([string]$Title)
    Add-Text ("`r`n==== " + $Title + " ====")
}
function Write-Lines {
    param($Object, [int]$Width = 200)
    $text = ($Object | Out-String -Width $Width).TrimEnd()
    if ($text) { Add-Text $text }
}
function Try-Section {
    param([string]$Title, [scriptblock]$Body)
    Write-Section $Title
    try { Write-Lines (& $Body) } catch { Add-Text ("(not available: " + $_.Exception.Message.Trim() + ")") }
}

Add-Text ("Windows dev laptop report, " + (Get-Date -Format 'yyyy-MM-dd HH:mm') + ", administrator: " + $isAdmin)

Try-Section 'System' {
    $os = Get-CimInstance Win32_OperatingSystem
    $cs = Get-CimInstance Win32_ComputerSystem
    $cpu = Get-CimInstance Win32_Processor | Select-Object -First 1
    [pscustomobject]@{
        OS = $os.Caption; Build = $os.BuildNumber; Architecture = $os.OSArchitecture
        Model = ($cs.Manufacturer + ' ' + $cs.Model); RAM_GB = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1)
        CPU = $cpu.Name; Cores = $cpu.NumberOfCores; Threads = $cpu.NumberOfLogicalProcessors
        # VirtualizationFirmwareEnabled reads False once a hypervisor runs (as with WSL 2), so use HypervisorPresent.
        HypervisorRunning = $cs.HypervisorPresent
        LastBoot = $os.LastBootUpTime
    } | Format-List
}

Try-Section 'Disks' {
    Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Used -ne $null } |
        Select-Object Name, @{n = 'Used_GB'; e = { [math]::Round($_.Used / 1GB) } }, @{n = 'Free_GB'; e = { [math]::Round($_.Free / 1GB) } } | Format-Table -AutoSize
}

Try-Section 'Power' { powercfg /getactivescheme }

Write-Section 'Installed applications (winget)'
try {
    $wg = winget list --accept-source-agreements 2>$null
    $wg | Set-Content -Path (Join-Path $OutDir 'winget-list.txt') -Encoding UTF8
    Add-Text ("winget-list.txt: " + $wg.Count + " lines")
} catch { Add-Text '(winget not available)' }

Try-Section 'Store (Appx) apps for this user' {
    $apps = Get-AppxPackage | Sort-Object Name
    $apps | Select-Object Name, Version, @{n = 'SizeMB'; e = { '' } } | Export-Csv -Path (Join-Path $OutDir 'appx-packages.csv') -NoTypeInformation -Encoding UTF8
    "$($apps.Count) packages, listed in appx-packages.csv"
}

Try-Section 'Programs installed more than once (same display name)' {
    $keys = 'HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*', 'HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\*', 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*'
    Get-ItemProperty $keys -ErrorAction SilentlyContinue | Where-Object { $_.DisplayName } |
        Group-Object { ($_.DisplayName -replace '\s[\d\.]+.*$', '').Trim() } | Where-Object { $_.Count -gt 1 } |
        ForEach-Object { $_.Name + '  x' + $_.Count + '  (' + (($_.Group | ForEach-Object { $_.DisplayVersion }) -join ', ') + ')' }
}

Try-Section 'Startup commands' {
    Get-CimInstance Win32_StartupCommand | Select-Object Name, Command, Location | Export-Csv -Path (Join-Path $OutDir 'startup.csv') -NoTypeInformation -Encoding UTF8
    Get-CimInstance Win32_StartupCommand | Select-Object Name, Location | Format-Table -AutoSize
}

Try-Section 'Scheduled tasks that run at logon (non-Microsoft)' {
    Get-ScheduledTask | Where-Object { $_.State -ne 'Disabled' -and $_.TaskPath -notlike '\Microsoft\*' -and ($_.Triggers | Where-Object { $_.CimClass.CimClassName -eq 'MSFT_TaskLogonTrigger' }) } |
        Select-Object TaskName, TaskPath, State | Format-Table -AutoSize
}

Try-Section 'Automatic services that are running (non-Microsoft)' {
    Get-CimInstance Win32_Service | Where-Object { $_.StartMode -eq 'Auto' -and $_.State -eq 'Running' -and $_.PathName -notmatch 'Windows|Microsoft' } |
        Select-Object Name, DisplayName | Sort-Object DisplayName | Format-Table -AutoSize
}

Try-Section 'Top 15 processes by memory' {
    Get-Process | Group-Object ProcessName | ForEach-Object {
        [pscustomobject]@{ Name = $_.Name; Count = $_.Count; Memory_MB = [math]::Round((($_.Group | Measure-Object WorkingSet64 -Sum).Sum) / 1MB) }
    } | Sort-Object Memory_MB -Descending | Select-Object -First 15 | Format-Table -AutoSize
}

Try-Section 'Settings that affect speed (current user)' {
    function Get-Reg { param($Path, $Name) try { (Get-ItemProperty -Path $Path -Name $Name -ErrorAction Stop).$Name } catch { 'not set' } }
    [pscustomobject]@{
        TransparencyEffects = Get-Reg 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Themes\Personalize' 'EnableTransparency'
        AnimationEffects_MinAnimate = Get-Reg 'HKCU:\Control Panel\Desktop\WindowMetrics' 'MinAnimate'
        GameModeAuto = Get-Reg 'HKCU:\Software\Microsoft\GameBar' 'AutoGameModeEnabled'
        WidgetsButton_TaskbarDa = Get-Reg 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Explorer\Advanced' 'TaskbarDa'
        StorageSense = Get-Reg 'HKCU:\Software\Microsoft\Windows\CurrentVersion\StorageSense\Parameters\StoragePolicy' '01'
        BackgroundAppsAllowed_GlobalUserDisabled = Get-Reg 'HKCU:\Software\Microsoft\Windows\CurrentVersion\BackgroundAccessApplications' 'GlobalUserDisabled'
        SearchIndexerService = (Get-Service WSearch -ErrorAction SilentlyContinue).Status
    } | Format-List
}

Try-Section 'Microsoft Defender' {
    $st = Get-MpComputerStatus
    [pscustomobject]@{ RealTimeProtection = $st.RealTimeProtectionEnabled; AntivirusEnabled = $st.AntivirusEnabled; TamperProtection = $st.IsTamperProtected } | Format-List
    if ($isAdmin) { 'Exclusion paths:'; (Get-MpPreference).ExclusionPath; 'Exclusion processes:'; (Get-MpPreference).ExclusionProcess }
    else { '(run as Administrator to list exclusions; they are usually managed by IT)' }
}

Try-Section 'Windows features needed for WSL' {
    if ($isAdmin) {
        Get-WindowsOptionalFeature -Online -FeatureName Microsoft-Windows-Subsystem-Linux, VirtualMachinePlatform, Microsoft-Hyper-V-All -ErrorAction SilentlyContinue | Select-Object FeatureName, State | Format-Table -AutoSize
    } else { '(run as Administrator to read the optional features; WSL itself is checked below)' }
}

Try-Section 'WSL' {
    'wsl --version:'; (wsl --version) -replace "`0", ''
    'wsl -l -v:'; (wsl -l -v) -replace "`0", ''
    $cfg = Join-Path $env:USERPROFILE '.wslconfig'
    if (Test-Path $cfg) { '.wslconfig:'; Get-Content $cfg } else { '.wslconfig: not present' }
}

Try-Section 'Proxy and network (what WSL autoProxy follows)' {
    $ie = Get-ItemProperty 'HKCU:\Software\Microsoft\Windows\CurrentVersion\Internet Settings'
    [pscustomobject]@{ AutoConfigURL = $ie.AutoConfigURL; ProxyEnable = $ie.ProxyEnable; ProxyServer = $ie.ProxyServer; ProxyOverride = $ie.ProxyOverride } | Format-List
    'winhttp:'; netsh winhttp show proxy
}

if ($IncludeFolderSizes) {
    Try-Section 'Largest folders in the user profile' {
        Get-ChildItem $env:USERPROFILE -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object {
            $size = (Get-ChildItem $_.FullName -Recurse -File -Force -ErrorAction SilentlyContinue | Measure-Object Length -Sum).Sum
            [pscustomobject]@{ Folder = $_.Name; Size_GB = [math]::Round($size / 1GB, 2) }
        } | Sort-Object Size_GB -Descending | Select-Object -First 15 | Format-Table -AutoSize
    }
}

[IO.File]::WriteAllText($report, $script:Buffer.ToString(), (New-Object System.Text.UTF8Encoding($false)))
Write-Host "Report written to $OutDir"
