param(
    [string]$OutputRoot = "experiments/readonly",
    [string]$Serial = ""
)

$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
$probePath = Join-Path $repoRoot "scripts/probe_readonly.sh"

if (-not (Test-Path -LiteralPath $probePath -PathType Leaf)) {
    throw "Probe script not found: $probePath"
}

$adb = Get-Command adb -ErrorAction SilentlyContinue
if ($null -eq $adb) {
    throw "adb was not found in PATH. Install Android platform-tools before connecting the camera."
}

$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$outDir = Join-Path $repoRoot (Join-Path $OutputRoot "a6500_$stamp")
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$targetArgs = @()
if ($Serial) {
    $targetArgs += @("-s", $Serial)
}

function Invoke-AdbText {
    param([string[]]$Arguments)
    $psi = [Diagnostics.ProcessStartInfo]::new()
    $psi.FileName = $adb.Source
    foreach ($arg in $Arguments) {
        [void]$psi.ArgumentList.Add($arg)
    }
    $psi.UseShellExecute = $false
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $p = [Diagnostics.Process]::new()
    $p.StartInfo = $psi
    [void]$p.Start()
    $stdout = $p.StandardOutput.ReadToEnd()
    $stderr = $p.StandardError.ReadToEnd()
    $p.WaitForExit()
    if ($p.ExitCode -ne 0) {
        throw "adb $($Arguments -join ' ') failed: $stderr"
    }
    return $stdout
}

$state = Invoke-AdbText ($targetArgs + @("get-state")).Trim()
if ($state -ne "device") {
    throw "adb target is not ready: '$state'"
}

$probe = [IO.File]::ReadAllText($probePath)
$psi = [Diagnostics.ProcessStartInfo]::new()
$psi.FileName = $adb.Source
foreach ($arg in ($targetArgs + @("shell", "sh", "-s"))) {
    [void]$psi.ArgumentList.Add($arg)
}
$psi.UseShellExecute = $false
$psi.RedirectStandardInput = $true
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$proc = [Diagnostics.Process]::new()
$proc.StartInfo = $psi
[void]$proc.Start()
$proc.StandardInput.Write($probe)
$proc.StandardInput.Close()
$stdout = $proc.StandardOutput.ReadToEnd()
$stderr = $proc.StandardError.ReadToEnd()
$proc.WaitForExit()

[IO.File]::WriteAllText((Join-Path $outDir "probe.stdout.txt"), $stdout, [Text.UTF8Encoding]::new($false))
[IO.File]::WriteAllText((Join-Path $outDir "probe.stderr.txt"), $stderr, [Text.UTF8Encoding]::new($false))
$metadata = @(
    "host_time_utc=$(Get-Date -AsUTC -Format o)"
    "adb=$($adb.Source)"
    "serial=$(if ($Serial) { $Serial } else { '<default>' })"
    "probe=$probePath"
    "camera_command=adb shell sh -s"
    "camera_side_effects=none"
    "stdout=$(Join-Path $outDir 'probe.stdout.txt')"
    "stderr=$(Join-Path $outDir 'probe.stderr.txt')"
)
[IO.File]::WriteAllLines((Join-Path $outDir "host_metadata.txt"), $metadata, [Text.UTF8Encoding]::new($false))

if ($proc.ExitCode -ne 0) {
    throw "Read-only probe exited with code $($proc.ExitCode). See $(Join-Path $outDir 'probe.stderr.txt')"
}

Write-Output $outDir
