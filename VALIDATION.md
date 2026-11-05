# MixForge Studio validation

Validated on Linux with Python 3.12, Node.js 24, FFmpeg, and Chromium. Windows scripts are supplied but have not been run on a Windows host.

## Results

- Backend: **38 tests passed** (`python -m pytest backend/tests -q`).
- Frontend: **19 tests passed** (`npm test`).
- TypeScript and Vite production build: **passed** (`npm run build`).
- Upstream Starlette emitted one test-client deprecation warning; execution succeeded.

Checks cover sample-accurate trimming, stereo channels, silence/timeline placement, pitch preservation, equal-power curves, WAV/MP3 decoding, peak limits, effects, automation, relative gain under normalization, source bounds, automatic duration, deterministic seeds, default manual preservation, opt-in beat matching, beat-aligned fade timing, corrupt uploads, real analysis, upload caching, project round-trips, validation, missing sources, cross-origin rejection, and unchanged originals.

## End-to-end audio

Generated three original 48-second demo songs and analyzed their actual audio with librosa. Rendered an 82-second manual remix to WAV and MP3. Generated and rendered a 30-second automatic arrangement. Saved and reopened projects through the API.

The synthesis tempos were 120/124/118 BPM; analysis estimated approximately 117.45/123.05/117.45 BPM. Estimates were measured from audio rather than copied from synthesis parameters.

## Browser

Chromium tests at desktop and 390-pixel mobile width passed: real waveforms; actual playback with advancing media time; dragging; duplicate/undo; Bass Swap regeneration; generated 30-second playback; downloadable WAV and MP3 exports. No JavaScript page errors or page-level mobile horizontal overflow were observed.

## Resource observation

An 82-second stereo demo rendered in approximately 3.77 seconds in this container; Python peak resident memory was approximately 205 MiB. This is a short-demo observation, not a Windows performance guarantee. Long sources and analysis need more RAM. The engine uses one background worker, bounded native math threads, sequential clip decoding, compact cached peaks, and a disk-backed timeline.

## Limits

The hosted static interface provides the application download. Processing requires the downloaded local Python/FFmpeg app. Preview is rendered in the background before playback, rather than zero-latency live DSP. Keys and 16-beat phrase boundaries are approximate. Echo/reverb uses delay networks confined to timeline duration. The UI provides a volume-ramp preset; arbitrary automation points are supported in project JSON. Project JSON references audio hashes and does not embed source files. Back up the data folder with projects. See README.md for complete setup, resource limits, and behavior.

## Windows Python detection fix

The installer now detects 64-bit standard CPython 3.11, 3.12, and 3.13, reuses a compatible MixForge virtual environment, checks the Python Launcher/PATH, and accepts an existing PyCharm interpreter path when needed. It uses the supplied prebuilt interface, so Node.js is only required for rebuilding. FFmpeg/FFprobe can remain beside the launch scripts or in a bin folder. Process PATH changes do not modify Windows settings. The setup patch replaces setup/launch files and adds tools/setup-windows.ps1; it excludes music, project data, and FFmpeg binaries.

Compatibility validation: all 17 backend tests passed in a newly provisioned Python 3.13.5 environment. Dependency resolution for CPython 3.13 on Windows x86-64 succeeded with binary wheels only. The installer interpreter probe executed successfully under Python 3.12.14 and 3.13.5. The PowerShell script passed a grammar-based syntax check. The Windows launcher itself has not been executed on a Windows machine.

## Version 1.1 sound and keyboard update

All 32 backend tests pass under Python 3.13, with 9 frontend tests passing. New checks cover eight actual deterministic stereo effect files, effect analysis without fabricated BPM/key, transition-sound timing in WAV and MP3, bypass/removal behavior, preserving music and sound choices on transition regeneration, missing sound errors, public-host restrictions, official API response mapping/cache, real-audio import through an external-fetch test fixture, project persistence, and shortcut/modifier/repeat behavior. The official Myinstants API and its response schema were inspected through web access. Live audio download from Myinstants was not executed in this build environment; the integration is tested using real audio with the external response supplied as a fixture.

Browser verification for version 1.1 passed: eight real pads; immediate audio playback from the bundled WAVs; Shift+pad placement; split/undo shortcuts; no shortcut triggering in text inputs; attached transition sound and real 12-second preview; unchanged music timestamps/positions; 20-row shortcut guide; zero JavaScript page errors and no horizontal overflow at 390-pixel width.

## Version 1.2 pointer editing

Current checks: 32 backend tests and 19 frontend tests pass; TypeScript and Vite builds pass. Additional timing/interaction tests cover anchored wheel zoom and wheel units, rectangle selection, moving groups while retaining spacing and source ranges, timeline/track bounds, edge snapping and Alt bypass, source/tempo trim math, automation continuity after split/trim, copy/paste with new clip/transition identifiers and preserved sound settings, deletion cleanup, and clip-count limits.

Chromium browser checks passed for Ctrl/Shift selection, selection boxes, multi-clip dragging and one-step undo, context-menu copy and group paste, Ctrl-wheel zoom anchored under the pointer, Shift-wheel and Hand-tool panning, middle-button panning, dragging the time ruler, click-to-cut, cancelling a drag with Escape, real fade/trim handle edits, keyboard Fit, project schema validation after edits, and context-menu placement within a 390-pixel viewport. Scrolling and zooming left the project unchanged. The edited project rendered genuine 82-second WAV and MP3 files and played successfully. No JavaScript page errors or mobile page overflow were observed.

Physical Windows touchpad hardware was not available. Pinch support is implemented through browser Ctrl-wheel events, which were exercised in Chromium; the explicit zoom slider and Ctrl-wheel path remain available if an OS/browser does not send pinch events. Windows installation scripts are unchanged from the previous update.

## Version 1.3

38 backend tests pass on Python 3.12.14 in the restored build environment. New real-audio checks cover track gain, stereo balance, solo/mute silence, fades without muted partners, exact WAV range equivalence with effects and automation, MP3 range timing, mixer/loop persistence, and source reconnection after moving directories. Upstream AnyIO/Starlette test deprecation warnings do not affect results.

Range rendering retains full clip processing history before cropping and skips clips wholly outside the range. The timeline buffer remains disk-backed. Preview renders before playback; it is not zero-latency live DSP. Windows scripts are unchanged and have not been executed on Windows hardware.

The restored frontend passes all 19 tests and the production TypeScript/Vite build. Chromium checks passed at 1512px desktop and 390px mobile: mixer controls, loop playback across its boundary with correct timeline offset, WAV and MP3 range download, project save, and settings restored after reload. No JavaScript page errors or page-level horizontal overflow were observed. The downloaded files were independently decoded with FFmpeg: WAV duration 2.000000s; MP3 container duration 2.037551s (encoder padding); both 44.1kHz stereo with the expected silent right channel at full-left pan and nonzero left-channel audio.
