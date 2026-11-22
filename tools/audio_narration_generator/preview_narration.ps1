param(
    [string] $Voice,
    [ValidateRange(-10, 10)]
    [int] $Rate = 0,
    [switch] $ListVoices,
    [switch] $Sequence,
    [switch] $RenderSequence,
    [string] $OutputDirectory
)

$ErrorActionPreference = 'Stop'
$synthesizer = $null
$exitCode = 0

try {
    if ([Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
        throw 'Windows PowerShell and Windows SAPI are required.'
    }

    Add-Type -AssemblyName System.Speech
    $synthesizer = New-Object System.Speech.Synthesis.SpeechSynthesizer
    $voiceNames = @(
        $synthesizer.GetInstalledVoices() |
            Where-Object { $_.Enabled } |
            ForEach-Object { $_.VoiceInfo.Name } |
            Sort-Object -Unique
    )
    if ($voiceNames.Count -eq 0) {
        throw 'No enabled SAPI voices were found. Install or enable a Windows speech voice, then retry.'
    }

    if ($ListVoices) {
        $voiceNames | ForEach-Object { [Console]::Out.WriteLine($_) }
    }
    else {
        [Console]::InputEncoding = [System.Text.UTF8Encoding]::new($false)
        $spokenText = [Console]::In.ReadToEnd()
        if ([string]::IsNullOrWhiteSpace($spokenText)) {
            throw 'Preview text is empty.'
        }

        if ($Voice) {
            if ($voiceNames -notcontains $Voice) {
                throw "Voice '$Voice' is not installed or enabled. Run preview_narration.py --list-voices to see available voices."
            }
            $synthesizer.SelectVoice($Voice)
        }

        $synthesizer.Rate = $Rate
        if ($RenderSequence) {
            if (-not $OutputDirectory -or -not (Test-Path -LiteralPath $OutputDirectory -PathType Container)) {
                throw 'A valid temporary output directory is required to render a SAPI sequence.'
            }
            $beats = ConvertFrom-Json -InputObject $spokenText
            if ($beats -isnot [System.Array]) {
                $beats = @($beats)
            }
            if ($beats.Count -eq 0) {
                throw 'Preview sequence has no beats.'
            }
            for ($index = 0; $index -lt $beats.Count; $index++) {
                $beat = [string] $beats[$index]
                if ([string]::IsNullOrWhiteSpace($beat)) {
                    throw "Preview beat $($index + 1) is empty."
                }
                $file = Join-Path $OutputDirectory ('beat-{0:D4}.wav' -f $index)
                $synthesizer.SetOutputToWaveFile($file)
                $synthesizer.Speak($beat)
                $synthesizer.SetOutputToNull()
            }
        }
        elseif ($Sequence) {
            $synthesizer.SetOutputToDefaultAudioDevice()
            $beats = ConvertFrom-Json -InputObject $spokenText
            if ($beats -isnot [System.Array]) {
                $beats = @($beats)
            }
            if ($beats.Count -eq 0) {
                throw 'Preview sequence has no beats.'
            }
            for ($index = 0; $index -lt $beats.Count; $index++) {
                $beat = [string] $beats[$index]
                if ([string]::IsNullOrWhiteSpace($beat)) {
                    throw "Preview beat $($index + 1) is empty."
                }
                [Console]::Out.WriteLine("START $index")
                [Console]::Out.Flush()
                $synthesizer.Speak($beat)
                [Console]::Out.WriteLine("DONE $index")
                [Console]::Out.Flush()
            }
        }
        else {
            $synthesizer.SetOutputToDefaultAudioDevice()
            $synthesizer.Speak($spokenText)
        }
    }
}
catch {
    [Console]::Error.WriteLine("SAPI preview failed: $($_.Exception.Message)")
    $exitCode = 2
}
finally {
    if ($null -ne $synthesizer) {
        try {
            $synthesizer.SpeakAsyncCancelAll()
        }
        catch {
            # Disposal below still releases the audio resources if cancellation fails.
        }
        $synthesizer.Dispose()
    }
}

exit $exitCode
