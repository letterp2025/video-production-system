param(
    [string] $Voice,
    [ValidateRange(-10, 10)]
    [int] $Rate = 0,
    [switch] $ListVoices
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
        $synthesizer.SetOutputToDefaultAudioDevice()
        $synthesizer.Speak($spokenText)
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
