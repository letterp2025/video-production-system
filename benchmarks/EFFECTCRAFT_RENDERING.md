# EffectCraft Rendering Benchmark

**Status:** Tested, summarized for public reuse. This is a single-workstation study, not a general performance guarantee.

## Test setup

A 30-second vector-graphics composition was exported at 3840 × 2160 and 60 fps (1,800 frames). The external workflow rendered PNG sections with EffectCraft and encoded the result with FFmpeg using NVIDIA NVENC HEVC Main, 8-bit yuv420p, BT.709 limited range, and an 8,000 kbps target. Audio was AAC-LC, 192 kbps, stereo, 48 kHz.

The comparison used one continuous section and six five-second sections. A separate native EffectCraft GPU export was attempted with the same project and delivery target.

## Results

| Workflow | Elapsed time | What the run establishes |
|---|---:|---|
| FFmpeg, one 30-second section | 291.831 s (4:51.831) | Completed export |
| FFmpeg, six five-second sections, run 1 | 280.76 s (4:40.76) | Completed export |
| FFmpeg, six five-second sections, run 2 | 315.57 s (5:15.57) | Completed export |
| Native EffectCraft GPU export | Stopped after 646.588 s (10:46.588), at 384/1,800 frames (21.3%) | Incomplete export; the live estimate then showed 2,364.9 s (about 39 minutes) remaining |

The sectioned FFmpeg runs took about the same time as the one-section run. Sectioning did not produce a meaningful speed-up in this test. It did reduce peak temporary storage from about 716 MB to about 143 MB and allowed completed sections to be reused after interruption.

The native export did not finish. Its remaining-time display is an estimate, not a measured total export duration. The defensible comparison is that FFmpeg completed in about 4 minutes 52 seconds while the native export was still running after 10 minutes 46 seconds, with 21% of frames completed.

## Limits and privacy

- One 30-second project and one workstation were tested. Other compositions, effects, hardware, encoder builds, and project lengths may behave differently.
- The scene used mostly vector graphics; it does not represent every workload.
- The original run records did not retain the CPU model, GPU model, or system memory. Those details are therefore omitted rather than inferred.
- The public summary contains no machine name, username, local paths, project files, voice material, or raw run receipt.
- The 60-second extension and a production audio source were not part of this measured comparison.

## Practical takeaway

Use sectioning to bound temporary storage and recover work after interruption. Do not describe it as the reason the FFmpeg encode was faster. In this test, the major practical difference was completing the export with the external FFmpeg workflow while the native export remained incomplete at the ten-minute checkpoint.

The detailed test method and raw records remain in the private study workspace and are not included here.