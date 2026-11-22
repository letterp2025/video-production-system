[CmdletBinding()]
param(
    [Parameter(Mandatory)][string]$Project,
    [Parameter(Mandatory)][string]$Composition,
    [Parameter(Mandatory)][string]$VideoProjectRoot,
    [Parameter(Mandatory)][ValidatePattern('^[a-zA-Z0-9][a-zA-Z0-9_-]*$')][string]$BaseName,
    [Parameter(Mandatory)][ValidateSet('HIGH','LOW')][string]$Tier,
    [Parameter(Mandatory)][string]$SectionsPath,
    [Parameter(Mandatory)][ValidateRange(1,240)][int]$Fps,
    [Parameter(Mandatory)][ValidateRange(1,16384)][int]$Width,
    [Parameter(Mandatory)][ValidateRange(1,16384)][int]$Height,
    [Parameter(Mandatory)][ValidateRange(1,9223372036854775807)][long]$MaxTempBytes,
    [Parameter(Mandatory)][ValidateRange(0,9223372036854775807)][long]$ReserveBytes,
    [string]$EffectCraft = 'effectcraft-cli.exe',
    [string]$FFmpeg = 'ffmpeg.exe',
    [string]$FFprobe = 'ffprobe.exe',
    [ValidateSet('hevc_nvenc','libx265')][string]$Encoder = 'hevc_nvenc',
    [ValidateRange(1,1000000)][int]$BitrateKbps = 8000,
    [string]$Audio,
    [switch]$KeepPng,
    [switch]$Replace,
    [switch]$Resume,
    [ValidateRange(0,1000000)][int]$TestFailBeforeSection = 0
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$culture = [Globalization.CultureInfo]::InvariantCulture

function Resolve-ExistingFile([string]$value) {
    $command = Get-Command $value -ErrorAction SilentlyContinue
    if ($command -and $command.Source) { return (Resolve-Path -LiteralPath $command.Source).Path }
    if (-not (Test-Path -LiteralPath $value -PathType Leaf)) { throw "File not found: $value" }
    return (Resolve-Path -LiteralPath $value).Path
}
function Quote-Argument([string]$value) {
    # Windows CommandLineToArgvW quoting, including trailing backslashes.
    return '"' + ([regex]::Replace($value, '(\\*)"', '$1$1\"') -replace '(\\+)$', '$1$1') + '"'
}
function Start-LoggedProcess([string]$exe, [string[]]$arguments, [string]$logPath) {
    $psi = New-Object Diagnostics.ProcessStartInfo
    $psi.FileName = $exe
    $psi.Arguments = ($arguments | ForEach-Object { Quote-Argument $_ }) -join ' '
    $psi.UseShellExecute = $false
    $psi.CreateNoWindow = $true
    $psi.RedirectStandardOutput = $true
    $psi.RedirectStandardError = $true
    $process = New-Object Diagnostics.Process
    $process.StartInfo = $psi
    if (-not $process.Start()) { throw "Could not start $exe" }
    $outTask = $process.StandardOutput.ReadToEndAsync()
    $errTask = $process.StandardError.ReadToEndAsync()
    return [pscustomobject]@{ Process=$process; Out=$outTask; Err=$errTask; Log=$logPath; Started=[datetime]::UtcNow }
}
function Write-ProcessLog($job) {
    $job.Process.WaitForExit()
    $stdout = $job.Out.GetAwaiter().GetResult()
    $stderr = $job.Err.GetAwaiter().GetResult()
    [IO.File]::WriteAllText($job.Log, "COMMAND: $($job.Process.StartInfo.FileName) $($job.Process.StartInfo.Arguments)`r`n$stdout`r`n$stderr")
}
function Complete-LoggedProcess($job) {
    Write-ProcessLog $job
    $result = [pscustomobject]@{ ExitCode=$job.Process.ExitCode; Seconds=([datetime]::UtcNow - $job.Started).TotalSeconds }
    $job.Process.Dispose()
    return $result
}
function Stop-LoggedProcess($job) {
    try {
        if (-not $job.Process.HasExited) {
            $job.Process.Kill()
            $job.Process.WaitForExit()
        }
    } catch { }
    try { Write-ProcessLog $job } finally { $job.Process.Dispose() }
}
function Get-ToolVersion([string]$exe) {
    $output = @(& $exe -version 2>&1)
    if ($LASTEXITCODE -ne 0 -or $output.Count -eq 0) { throw "Could not read version from $exe" }
    return [string]$output[0]
}
function Probe-Video([string]$path, [int]$frames) {
    Assert-FreeSpace $script:workRoot
    Assert-StorageBudget $script:workRoot | Out-Null
    $json = & $script:probeExe -v error -select_streams v:0 -count_frames -show_entries 'stream=codec_name,profile,width,height,pix_fmt,avg_frame_rate,nb_read_frames,color_range,color_space,color_transfer,color_primaries,start_time,duration' -show_entries 'format=duration' -of json $path
    if ($LASTEXITCODE -ne 0) { throw "ffprobe failed: $path" }
    $data = ($json -join "`n") | ConvertFrom-Json
    if (-not $data.streams -or $data.streams.Count -ne 1) { throw "Expected one video stream: $path" }
    $s = $data.streams[0]
    $expected = @{
        codec_name='hevc'; profile='Main'; width=$Width; height=$Height; pix_fmt='yuv420p';
        color_range='tv'; color_space='bt709'; color_transfer='bt709'; color_primaries='bt709';
        nb_read_frames=[string]$frames; avg_frame_rate="$Fps/1"
    }
    foreach ($key in $expected.Keys) {
        if ([string]$s.$key -ne [string]$expected[$key]) { throw "Invalid $key in $path`: got '$($s.$key)', expected '$($expected[$key])'" }
    }
    $start = [double]::Parse([string]$s.start_time, $culture)
    if ([math]::Abs($start) -gt (1.0 / $Fps)) { throw "Invalid video start time in $path`: $start" }
    $duration = [double]::Parse([string]$data.format.duration, $culture)
    if ([math]::Abs($duration - $frames / $Fps) -gt (1.0 / $Fps + 0.002)) { throw "Invalid duration in $path`: $duration" }
    & $script:ffmpegExe -v error -xerror -i $path -map 0:v:0 -f null NUL
    if ($LASTEXITCODE -ne 0) { throw "Decode failed: $path" }
    Assert-FreeSpace $script:workRoot
    Assert-StorageBudget $script:workRoot | Out-Null
    return [pscustomobject]@{ Start=$start; Duration=$duration; FrameCount=$frames }
}
function Parse-InvariantDouble([string]$value, [string]$label) {
    $parsed = 0.0
    if (-not [double]::TryParse($value, [Globalization.NumberStyles]::Float, $culture, [ref]$parsed) -or [double]::IsNaN($parsed) -or [double]::IsInfinity($parsed)) {
        throw "Missing or invalid ${label}: '$value'"
    }
    return $parsed
}
function Get-AudioInfo([string]$path) {
    Assert-FreeSpace $script:workRoot
    Assert-StorageBudget $script:workRoot | Out-Null
    $json = & $script:probeExe -v error -select_streams a:0 -show_entries 'stream=codec_name,start_time,duration,duration_ts,time_base,sample_rate' -show_entries 'format=start_time' -of json $path
    if ($LASTEXITCODE -ne 0) { throw "ffprobe failed to inspect audio: $path" }
    $data = ($json -join "`n") | ConvertFrom-Json
    if (-not $data.streams -or $data.streams.Count -ne 1) { throw "Expected an audio stream: $path" }
    $stream = $data.streams[0]
    $startProperty = $stream.PSObject.Properties['start_time']
    if ($startProperty -and [string]$startProperty.Value -ne 'N/A') {
        $start = Parse-InvariantDouble ([string]$startProperty.Value) 'audio start time'
    } else {
        $formatStart = $data.format.PSObject.Properties['start_time']
        $start = if ($formatStart -and [string]$formatStart.Value -ne 'N/A') { Parse-InvariantDouble ([string]$formatStart.Value) 'audio start time' } else { 0.0 }
    }
    $durationProperty = $stream.PSObject.Properties['duration']
    if ($durationProperty -and [string]$durationProperty.Value -ne 'N/A') {
        $duration = Parse-InvariantDouble ([string]$durationProperty.Value) 'audio duration'
    } else {
        $durationTicks = $stream.PSObject.Properties['duration_ts']
        $timeBase = $stream.PSObject.Properties['time_base']
        if (-not $durationTicks -or -not $timeBase) { throw "Missing audio duration metadata: $path" }
        $parts = [string]$timeBase.Value -split '/'
        if ($parts.Count -ne 2) { throw "Invalid audio time base: $($timeBase.Value)" }
        $duration = ([double]$durationTicks.Value * [double]$parts[0]) / [double]$parts[1]
    }
    $sampleRate = [int]$stream.sample_rate
    if ($duration -le 0 -or $sampleRate -le 0) { throw "Invalid audio duration or sample rate: $path" }
    $tolerance = (1.0 / $Fps) + (1024.0 / $sampleRate) + 0.002
    Assert-FreeSpace $script:workRoot
    Assert-StorageBudget $script:workRoot | Out-Null
    return [pscustomobject]@{ Codec=$stream.codec_name; Start=$start; Duration=$duration; End=($start+$duration); SampleRate=$sampleRate; Tolerance=$tolerance }
}
function Assert-AudioSource([string]$path, [double]$expectedDuration) {
    $audio = Get-AudioInfo $path
    if ([math]::Abs($audio.Start) -gt $audio.Tolerance) {
        throw "Audio must start near zero; got $($audio.Start) seconds in $path"
    }
    if ($audio.End -lt ($expectedDuration - $audio.Tolerance)) {
        throw "Audio ends at $($audio.End) seconds, before the $expectedDuration-second video (tolerance $($audio.Tolerance) seconds)"
    }
    return $audio
}
function Assert-AudioMatchesVideo([string]$path, [double]$videoStart, [double]$videoDuration) {
    $audio = Get-AudioInfo $path
    if ($audio.Codec -ne 'aac') { throw "Expected AAC audio in $path; got '$($audio.Codec)'" }
    if ([math]::Abs($audio.Start-$videoStart) -gt $audio.Tolerance) {
        throw "Audio starts at $($audio.Start) seconds but video starts at $videoStart seconds"
    }
    $videoEnd = $videoStart + $videoDuration
    if ([math]::Abs($audio.End-$videoEnd) -gt $audio.Tolerance) {
        throw "Audio ends at $($audio.End) seconds but video ends at $videoEnd seconds (tolerance $($audio.Tolerance) seconds)"
    }
    return $audio
}
function Commit-FinalOutput([string]$source, [string]$destination, [bool]$replace) {
    if (Test-Path -LiteralPath $destination -PathType Leaf) {
        if (-not $replace) { throw "Final output appeared during run: $destination" }
        $sourceRoot = [IO.Path]::GetPathRoot($source)
        $destinationRoot = [IO.Path]::GetPathRoot($destination)
        if (-not [string]::Equals($sourceRoot,$destinationRoot,[StringComparison]::OrdinalIgnoreCase)) {
            throw 'Atomic replacement requires the work file and final export to be on the same volume'
        }
        if (-not ('EffectCraftAtomicFile' -as [type])) {
            $sourceCode = @'
using System.Runtime.InteropServices;
public static class EffectCraftAtomicFile {
    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    public static extern bool MoveFileEx(string existingFileName, string newFileName, int flags);
}
'@
            Add-Type -TypeDefinition $sourceCode
        }
        # Same-volume replacement is a single Windows rename operation. If it fails,
        # the old destination remains in place and the validated work file stays available.
        $replaced = [EffectCraftAtomicFile]::MoveFileEx($source,$destination,(0x1 -bor 0x8))
        if (-not $replaced) {
            $win32Error = [Runtime.InteropServices.Marshal]::GetLastWin32Error()
            throw (New-Object ComponentModel.Win32Exception($win32Error))
        }
        return
    }
    [IO.File]::Move($source, $destination)
}
function Save-State($state, [string]$path) {
    $json = $state | ConvertTo-Json -Depth 12
    $json | Set-Content -LiteralPath $path -Encoding UTF8
    if ($script:performancePath) {
        $performanceRoot = Split-Path -Parent $script:performancePath
        New-Item -ItemType Directory -Force -Path $performanceRoot | Out-Null
        $temporaryPath = "$($script:performancePath).tmp"
        [IO.File]::WriteAllText($temporaryPath, $json, (New-Object Text.UTF8Encoding($false)))
        if (Test-Path -LiteralPath $script:performancePath -PathType Leaf) {
            $backupPath = "$($script:performancePath).bak"
            if (Test-Path -LiteralPath $backupPath -PathType Leaf) { Remove-Item -LiteralPath $backupPath }
            [IO.File]::Replace($temporaryPath, $script:performancePath, $backupPath)
            if (Test-Path -LiteralPath $backupPath -PathType Leaf) { Remove-Item -LiteralPath $backupPath }
        } else {
            [IO.File]::Move($temporaryPath, $script:performancePath)
        }
    }
}
function Png-Files([string]$folder, [string]$prefix) {
    return ,@(Get-ChildItem -LiteralPath $folder -Filter "${prefix}_*.png" -File | Sort-Object Name)
}
function Assert-FreeSpace([string]$path) {
    $root = [IO.Path]::GetPathRoot($path)
    $free = (New-Object IO.DriveInfo($root)).AvailableFreeSpace
    if ($free -le $ReserveBytes) { throw "Free-space reserve reached: $free bytes free, reserve $ReserveBytes" }
}
function Measure-WorkDirectory([string]$folder) {
    $total = [long]0
    $png = [long]0
    foreach ($path in [IO.Directory]::EnumerateFiles($folder,'*',[IO.SearchOption]::AllDirectories)) {
        $file = New-Object IO.FileInfo($path)
        $length = [long]$file.Length
        $total += $length
        if ([IO.Path]::GetExtension($path) -ieq '.png') { $png += $length }
    }
    return [pscustomobject]@{ TotalBytes=$total; PngBytes=$png }
}
function Assert-StorageBudget([string]$folder) {
    $usage = Measure-WorkDirectory $folder
    if ($usage.TotalBytes -gt $script:state.peakWorkBytes) { $script:state.peakWorkBytes = $usage.TotalBytes }
    if ($usage.PngBytes -gt $script:state.peakPngBytes) { $script:state.peakPngBytes = $usage.PngBytes }
    if ($usage.TotalBytes -gt $MaxTempBytes) {
        throw "Temporary work-storage limit reached: $($usage.TotalBytes) bytes in run folder exceeds $MaxTempBytes bytes"
    }
    return $usage
}
function Invoke-MonitoredProcess([string]$exe, [string[]]$arguments, [string]$logPath, [string]$workFolder) {
    Assert-FreeSpace $workFolder
    Assert-StorageBudget $workFolder | Out-Null
    $job = Start-LoggedProcess $exe $arguments $logPath
    $finished = $false
    try {
        while (-not $job.Process.WaitForExit(200)) {
            Assert-FreeSpace $workFolder
            Assert-StorageBudget $workFolder | Out-Null
        }
        $result = Complete-LoggedProcess $job
        $finished = $true
        Assert-FreeSpace $workFolder
        Assert-StorageBudget $workFolder | Out-Null
        if ($result.ExitCode -ne 0) { throw "Process failed ($($result.ExitCode)); see $($job.Log)" }
        return $result
    } catch {
        if (-not $finished) {
            try { Stop-LoggedProcess $job } catch { }
            # Include the kill diagnostic and partial output in the storage accounting.
            try { Assert-StorageBudget $workFolder | Out-Null } catch { }
        }
        throw
    }
}
function Assert-Pngs([string]$folder, [string]$prefix, [int]$start, [int]$end) {
    $files = Png-Files $folder $prefix
    if ($files.Count -ne $end-$start) { throw "PNG count mismatch in $folder`: $($files.Count), expected $($end-$start)" }
    $bytes = [long]0
    for ($i=0; $i -lt $files.Count; $i++) {
        $n = $start+$i
        if ($files[$i].Name -ne ('{0}_{1:D5}.png' -f $prefix,$n) -or $files[$i].Length -eq 0) { throw "Missing, extra, or empty PNG at frame $n" }
        $fs = [IO.File]::OpenRead($files[$i].FullName)
        try {
            $header = New-Object byte[] 26
            if ($fs.Read($header,0,26) -ne 26) { throw "Short PNG: $($files[$i].Name)" }
            $w = [int]([uint32]$header[16] -shl 24 -bor ([uint32]$header[17] -shl 16) -bor ([uint32]$header[18] -shl 8) -bor $header[19])
            $h = [int]([uint32]$header[20] -shl 24 -bor ([uint32]$header[21] -shl 16) -bor ([uint32]$header[22] -shl 8) -bor $header[23])
            if ($w -ne $Width -or $h -ne $Height -or $header[24] -ne 8 -or $header[25] -ne 2) { throw "Wrong PNG dimensions or RGB8 format: $($files[$i].Name)" }
        } finally { $fs.Dispose() }
        $bytes += $files[$i].Length
    }
    return $bytes
}

$projectPath = Resolve-ExistingFile $Project
$sectionsFile = Resolve-ExistingFile $SectionsPath
$effectExe = Resolve-ExistingFile $EffectCraft
$ffmpegExe = Resolve-ExistingFile $FFmpeg
$probeExe = Resolve-ExistingFile $FFprobe
$script:ffmpegExe = $ffmpegExe
$script:probeExe = $probeExe
$audioPath = if ($Audio) { Resolve-ExistingFile $Audio } else { $null }
$videoRoot = [IO.Path]::GetFullPath($VideoProjectRoot)
if (-not (Test-Path -LiteralPath $videoRoot -PathType Container)) { throw "Video project root not found: $videoRoot" }
$sectionData = Get-Content -LiteralPath $sectionsFile -Raw | ConvertFrom-Json
$sections = @($sectionData.sections)
if ($sections.Count -eq 0) { throw 'Manifest has no sections' }
$next = 0
foreach ($section in $sections) {
    if ($null -eq $section.startFrame -or $null -eq $section.endFrame) { throw 'Each section needs startFrame and endFrame' }
    if ((($section.startFrame -isnot [int]) -and ($section.startFrame -isnot [long])) -or (($section.endFrame -isnot [int]) -and ($section.endFrame -isnot [long]))) { throw 'Section frame values must be integers' }
    $start = [int]$section.startFrame; $end = [int]$section.endFrame
    if ($start -ne $next -or $end -le $start) { throw "Sections must be adjacent, nonempty, and start at frame 0; got [$start,$end), expected start $next" }
    $next = $end
}
$total = $next
$tierLower = $Tier.ToLowerInvariant()
$renderRoot = Join-Path $videoRoot "render\$Tier"
$finalPath = Join-Path $renderRoot "${BaseName}_${tierLower}.mp4"
if ((Test-Path -LiteralPath $finalPath) -and -not $Replace) { throw "Final output exists; use -Replace to overwrite: $finalPath" }
$projectHash = (Get-FileHash -LiteralPath $projectPath -Algorithm SHA256).Hash
$scriptPath = (Resolve-Path -LiteralPath $PSCommandPath).Path
$scriptHash = (Get-FileHash -LiteralPath $scriptPath -Algorithm SHA256).Hash
$effectHash = (Get-FileHash -LiteralPath $effectExe -Algorithm SHA256).Hash
$ffmpegHash = (Get-FileHash -LiteralPath $ffmpegExe -Algorithm SHA256).Hash
$probeHash = (Get-FileHash -LiteralPath $probeExe -Algorithm SHA256).Hash
$ffmpegVersion = Get-ToolVersion $ffmpegExe
$probeVersion = Get-ToolVersion $probeExe
$audioHash = if ($audioPath) { (Get-FileHash -LiteralPath $audioPath -Algorithm SHA256).Hash } else { $null }
$toolchain = [ordered]@{
    scriptPath=$scriptPath; scriptSha256=$scriptHash
    effectCraftPath=$effectExe; effectCraftSha256=$effectHash
    ffmpegPath=$ffmpegExe; ffmpegSha256=$ffmpegHash; ffmpegVersion=$ffmpegVersion
    ffprobePath=$probeExe; ffprobeSha256=$probeHash; ffprobeVersion=$probeVersion
}
$identity = [ordered]@{ projectHash=$projectHash; composition=$Composition; sections=@($sections | ForEach-Object { @([int]$_.startFrame,[int]$_.endFrame) }); fps=$Fps; width=$Width; height=$Height; encoder=$Encoder; bitrateKbps=$BitrateKbps; audioHash=$audioHash; toolchain=$toolchain }
$identityJson = $identity | ConvertTo-Json -Depth 8 -Compress
$sha = [Security.Cryptography.SHA256]::Create()
try { $id = ([BitConverter]::ToString($sha.ComputeHash([Text.Encoding]::UTF8.GetBytes($identityJson)))).Replace('-','').Substring(0,12).ToLowerInvariant() } finally { $sha.Dispose() }
$workRoot = Join-Path $renderRoot ".effectcraft-sections\${BaseName}_${id}"
$statePath = Join-Path $workRoot 'run.json'
$performanceRoot = Join-Path $renderRoot 'performance'
$script:performancePath = Join-Path $performanceRoot "${BaseName}_${tierLower}_${id}.performance.json"
if ((Test-Path -LiteralPath $workRoot) -and -not ($Resume -or $Replace)) { throw "Run folder exists; use -Resume, or choose a new output name: $workRoot" }
if ($Resume -and -not (Test-Path -LiteralPath $statePath)) {
    $runsRoot = Join-Path $renderRoot '.effectcraft-sections'
    $otherRuns = @()
    if (Test-Path -LiteralPath $runsRoot) {
        $otherRuns = @(Get-ChildItem -LiteralPath $runsRoot -Directory -Filter "${BaseName}_*" | Where-Object { $_.FullName -ne $workRoot })
    }
    if ($otherRuns.Count -gt 0) {
        throw "No resumable run matches the current project, settings, script, and tool fingerprints. Existing run '$($otherRuns[0].FullName)' has a different identity; use its original inputs or choose a new base name."
    }
    throw "No resumable run: $statePath"
}
if ((Test-Path -LiteralPath $workRoot) -and $Replace -and -not (Test-Path -LiteralPath $statePath)) { throw "No prior run state for replacement: $statePath" }
New-Item -ItemType Directory -Force -Path $workRoot | Out-Null
$script:workRoot = $workRoot
Assert-FreeSpace $workRoot
$state = if (Test-Path -LiteralPath $statePath) { Get-Content -LiteralPath $statePath -Raw | ConvertFrom-Json } else {
    [pscustomobject]@{
        identity=$identityJson; project=$projectPath; sectionsFile=$sectionsFile; output=$finalPath
        performanceRecord=$script:performancePath
        script=$scriptPath; scriptSha256=$scriptHash
        effectCraft=$effectExe; effectCraftExeSha256=$effectHash
        ffmpeg=$ffmpegExe; ffmpegExeSha256=$ffmpegHash; ffmpegVersion=$ffmpegVersion
        ffprobe=$probeExe; ffprobeExeSha256=$probeHash; ffprobeVersion=$probeVersion
        maxTempBytes=$MaxTempBytes; reserveBytes=$ReserveBytes; keepPng=[bool]$KeepPng
        createdUtc=[datetime]::UtcNow.ToString('o'); sectionResults=@()
        peakPngBytes=[long]0; peakWorkBytes=[long]0; status='running'; error=$null; failedUtc=$null
        joinSeconds=$null; finalBytes=$null; finalSha256=$null; completedUtc=$null
    }
}
if ($state.identity -ne $identityJson) { throw 'Run identity changed; start a new run' }
$state | Add-Member -NotePropertyName performanceRecord -NotePropertyValue $script:performancePath -Force
$script:state = $state
Save-State $state $statePath

try {
    $expectedDuration = [double]$total / $Fps
    if ($audioPath) {
        $audioSourceInfo = Assert-AudioSource $audioPath $expectedDuration
        Write-Host ("Audio source: {0}, start {1:0.000}s, end {2:0.000}s" -f $audioSourceInfo.Codec,$audioSourceInfo.Start,$audioSourceInfo.End)
    }
    for ($index=0; $index -lt $sections.Count; $index++) {
        $section = $sections[$index]
        $start = [int]$section.startFrame; $end = [int]$section.endFrame; $count=$end-$start
        $tag = 'section_{0:D3}_{1:D5}-{2:D5}' -f ($index+1),$start,($end-1)
        $folder = Join-Path $workRoot $tag
        $prefix = 'frame'
        $movie = Join-Path $workRoot "${tag}.mp4"
        $partial = Join-Path $workRoot "${tag}.partial.mp4"
        if ($TestFailBeforeSection -eq $index+1) { throw "Simulated failure before section $($index+1)" }
        if (($Resume -or $Replace) -and (Test-Path -LiteralPath $movie)) {
            Probe-Video $movie $count | Out-Null
            $recordedSection = @($state.sectionResults | Where-Object { $_.tag -eq $tag }) | Select-Object -First 1
            $movieHash = (Get-FileHash -LiteralPath $movie -Algorithm SHA256).Hash
            if ($recordedSection -and $recordedSection.sha256 -ne $movieHash) {
                throw "Saved section hash does not match run state for $tag; preserve the file for diagnosis and start a new run."
            }
            if (-not $recordedSection) {
                # Recover a section that was atomically renamed just before an interrupted state update.
                $state.sectionResults += [pscustomobject]@{ tag=$tag; startFrame=$start; endFrame=$end; pngBytes=0; renderSeconds=0; encodeSeconds=0; mp4Bytes=(Get-Item -LiteralPath $movie).Length; sha256=$movieHash }
                Save-State $state $statePath
                Assert-StorageBudget $workRoot | Out-Null
            }
            Write-Host "Reused validated $tag"
            continue
        }
        New-Item -ItemType Directory -Force -Path $folder | Out-Null
        $pngs = Png-Files $folder $prefix
        if ($pngs.Count -eq $count) {
            $pngBytes = Assert-Pngs $folder $prefix $start $end
            $renderSeconds = 0
            Write-Host "Reused existing PNGs for $tag"
            Assert-StorageBudget $workRoot | Out-Null
        } elseif ($pngs.Count -eq 0) {
            $startSeconds = ([double]$start/$Fps).ToString('0.################', $culture)
            $endSeconds = ([double]$end/$Fps).ToString('0.################', $culture)
            $renderArgs = @('--project',$projectPath,'render','--comp',$Composition,'--out',(Join-Path $folder $prefix),'--format','png','--start',$startSeconds,'--end',$endSeconds,'--fps',[string]$Fps,'--resolution','full','--quality','best')
            $renderResult = Invoke-MonitoredProcess $effectExe $renderArgs (Join-Path $workRoot "${tag}_render.log") $workRoot
            $renderSeconds = $renderResult.Seconds
            $pngBytes = Assert-Pngs $folder $prefix $start $end
            Assert-StorageBudget $workRoot | Out-Null
        } else { throw "Incomplete PNGs in $folder; retained for diagnosis. Remove only this run's partial section frames before resuming." }
        Save-State $state $statePath
        Assert-StorageBudget $workRoot | Out-Null
        $filter = 'scale=in_range=full:out_range=limited:out_color_matrix=bt709,format=yuv420p'
        $metadata = 'hevc_metadata=video_full_range_flag=0:colour_primaries=1:transfer_characteristics=1:matrix_coefficients=1'
        $encodeArgs = @('-hide_banner','-loglevel','info','-nostats','-y','-framerate',[string]$Fps,'-start_number',[string]$start,'-i',(Join-Path $folder 'frame_%05d.png'),'-frames:v',[string]$count,'-an','-vf',$filter,'-c:v',$Encoder)
        if ($Encoder -eq 'hevc_nvenc') { $encodeArgs += @('-preset','p5','-tune','hq','-b:v',"${BitrateKbps}k",'-profile:v','main','-g',[string](2*$Fps)) }
        else { $encodeArgs += @('-preset','medium','-b:v',"${BitrateKbps}k",'-profile:v','main','-x265-params',"keyint=$(2*$Fps):min-keyint=$(2*$Fps):scenecut=0") }
        $encodeArgs += @('-color_range','tv','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-bsf:v',$metadata,$partial)
        $encodeResult = Invoke-MonitoredProcess $ffmpegExe $encodeArgs (Join-Path $workRoot "${tag}_encode.log") $workRoot
        Probe-Video $partial $count | Out-Null
        Move-Item -LiteralPath $partial -Destination $movie
        $state.sectionResults += [pscustomobject]@{ tag=$tag; startFrame=$start; endFrame=$end; pngBytes=$pngBytes; renderSeconds=$renderSeconds; encodeSeconds=$encodeResult.Seconds; mp4Bytes=(Get-Item -LiteralPath $movie).Length; sha256=(Get-FileHash -LiteralPath $movie -Algorithm SHA256).Hash }
        Save-State $state $statePath
        if (-not $KeepPng) {
            foreach ($file in (Png-Files $folder $prefix)) { Remove-Item -LiteralPath $file.FullName }
            if (@(Get-ChildItem -LiteralPath $folder -Force).Count -eq 0) { Remove-Item -LiteralPath $folder }
        }
        Assert-StorageBudget $workRoot | Out-Null
        Write-Host "Validated $tag ($count frames, $pngBytes PNG bytes)"
    }
    $concatFile = Join-Path $workRoot 'sections.ffconcat'
    $lines = @('ffconcat version 1.0')
    for ($index=0; $index -lt $sections.Count; $index++) {
        $start=[int]$sections[$index].startFrame; $end=[int]$sections[$index].endFrame
        $tag='section_{0:D3}_{1:D5}-{2:D5}' -f ($index+1),$start,($end-1)
        $path=(Join-Path $workRoot "${tag}.mp4").Replace("'", "'\''")
        $lines += "file '$path'"
    }
    [IO.File]::WriteAllLines($concatFile, $lines, (New-Object Text.UTF8Encoding($false)))
    $joined = Join-Path $workRoot 'joined.partial.mp4'
    $concatArgs = @('-hide_banner','-loglevel','info','-nostats','-y','-f','concat','-safe','0','-i',$concatFile,'-map','0:v:0','-c','copy','-an',$joined)
    $joinResult = Invoke-MonitoredProcess $ffmpegExe $concatArgs (Join-Path $workRoot 'concat.log') $workRoot
    Probe-Video $joined $total | Out-Null
    $assembled = $joined
    if ($audioPath) {
        $withAudio = Join-Path $workRoot 'with_audio.partial.mp4'
        $duration = $expectedDuration.ToString('0.################',$culture)
        $audioArgs = @('-hide_banner','-loglevel','info','-nostats','-y','-i',$joined,'-i',$audioPath,'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','aac','-b:a','192k','-af','apad','-t',$duration,$withAudio)
        Invoke-MonitoredProcess $ffmpegExe $audioArgs (Join-Path $workRoot 'audio.log') $workRoot | Out-Null
        $videoInfo = Probe-Video $withAudio $total
        Assert-AudioMatchesVideo $withAudio $videoInfo.Start $videoInfo.Duration | Out-Null
        $assembled = $withAudio
    }
    Assert-FreeSpace $workRoot
    Assert-StorageBudget $workRoot | Out-Null
    Commit-FinalOutput $assembled $finalPath ([bool]$Replace)
    $state.status='complete'; $state | Add-Member -NotePropertyName error -NotePropertyValue $null -Force; $state | Add-Member -NotePropertyName failedUtc -NotePropertyValue $null -Force; $state | Add-Member -NotePropertyName joinSeconds -NotePropertyValue $joinResult.Seconds -Force; $state | Add-Member -NotePropertyName finalBytes -NotePropertyValue (Get-Item -LiteralPath $finalPath).Length -Force; $state | Add-Member -NotePropertyName finalSha256 -NotePropertyValue (Get-FileHash -LiteralPath $finalPath -Algorithm SHA256).Hash -Force; $state | Add-Member -NotePropertyName completedUtc -NotePropertyValue ([datetime]::UtcNow.ToString('o')) -Force
    Save-State $state $statePath
    Write-Host "Completed $finalPath ($total frames, peak work bytes $($state.peakWorkBytes), peak PNG bytes $($state.peakPngBytes))"
} catch {
    $state.status='failed'; $state | Add-Member -NotePropertyName error -NotePropertyValue ([string]$_) -Force; $state | Add-Member -NotePropertyName failedUtc -NotePropertyValue ([datetime]::UtcNow.ToString('o')) -Force
    Save-State $state $statePath
    throw
}
