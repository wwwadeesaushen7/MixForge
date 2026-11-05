# MixForge Studio

A local music workstation with a React + TypeScript + Vite frontend, Tailwind CSS, WaveSurfer.js, Web Audio metering, and a real Python/FastAPI + librosa/NumPy/SciPy/FFmpeg audio engine. No accounts, paid APIs, AI services, or music uploads to third parties are required. The hosted page provides the interface and application download; **audio processing runs in the downloaded local application**.

## Running from this GitHub repository

This repository contains the complete v1.3 source, tests, and original bundled sounds. Generated `dist`, imported music, saved projects, virtual environments, and credentials are excluded.

For a source checkout, install **Node.js 20.19+** along with **64-bit Python 3.11–3.13 and FFmpeg**, then clone/download this repository and run `setup-windows.bat`. Setup builds the interface when `dist` is missing. After setup, use `launch-windows.bat`; Node.js is not needed for each launch. Keep your existing `data` folder when updating an installation.

The application runs on your PC at `http://127.0.0.1:8000`. GitHub Pages or static hosting alone cannot run its Python/FFmpeg audio engine.

## Windows 10 / 11 setup

1. Use your existing **64-bit standard CPython 3.11, 3.12, or 3.13**. Setup checks the Python Launcher and PATH, and can use a PyCharm interpreter when you paste its full `python.exe` path. Another Python installation is not required when you already have a supported version.
2. The ZIP includes a prebuilt interface. **Node.js is optional** for normal setup; install Node.js 20.19+ or 22+ only if you want to rebuild or edit the interface.
3. Put **`ffmpeg.exe` and `ffprobe.exe`** beside `setup-windows.bat` or into a `bin` subfolder. An existing installation on PATH also works. Setup and launch add the private copies to their own process PATH without changing Windows settings. If you need the files, extract them from the FFmpeg essentials build at https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip.
4. Extract this archive to a writable folder, such as `Documents\MixForge-Studio`. Avoid opening it inside the ZIP, a protected system directory, or a OneDrive folder with files marked online-only.
5. Double-click **setup-windows.bat**. It finds a supported existing Python, creates or reuses the MixForge virtual environment, installs dependencies, and uses the prebuilt interface (or builds it when missing). Internet access is required for dependency installation.
6. Double-click **launch-windows.bat**. Your browser opens **http://127.0.0.1:8000** when the engine is ready. Keep the terminal window open; Ctrl+C stops it.

After setup, ordinary mixing and exporting work offline. Windows launch scripts are supplied but have not been executed on a Windows machine in this development environment. Use Chrome or Edge on Windows 10. On 8 GB systems, close memory-heavy applications while processing large files.

### Upgrading the Windows setup files

If an earlier installer rejected Python 3.13, extract **MixForge-Windows-Setup-Fix.zip into your existing MixForge-Studio folder**, allowing the setup/launch files to be replaced. Keep `tools` as a subfolder. Existing FFmpeg executables and the `data` folder remain in place. Run `setup-windows.bat` again. If prompted for PyCharm Python, copy its full interpreter path from Settings > Project > Python Interpreter. Setup uses it to create a separate MixForge environment; it does not install packages into your PyCharm project.

Setup reuses a compatible MixForge `.venv` on retries. It reports an incompatible/broken `.venv` without deleting it.

## Other platforms

Install Python 3.11/3.12/3.13, Node.js 20.19+, and FFmpeg. Run `sh launch.sh`. For development:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
npm ci
npm run build
.venv/bin/python launch.py
```

For hot frontend editing, start `.venv/bin/python -m backend.app` and `npm run dev` in separate terminals, then open `http://localhost:5173`. Vite proxies `/api` to port 8000. Production serves frontend and backend together on port 8000. Keep the backend bound to loopback; this is a personal workstation, not a multi-user Internet server.

## Version 1.3: track mixer and loop studio

Open **Track mixer** above the timeline to rename each used track, change volume and stereo balance, mute tracks, or solo one or several tracks. Settings affect actual previews and both export formats. Mute overrides solo. Center pan preserves both original channels; full left/right silences the opposite channel. Attached transition sounds use track 8.

Set **In** and **Out** in seconds, or select clips and choose **Use selection**. Press **L** to toggle repeated playback of that range. In Export, choose **Export loop range only** for a short WAV/MP3; leave it unchecked to export the whole remix. The range includes every audible track at its original timeline timing, including effects and automation. A range beyond the new mix end is shortened; a range wholly outside the mix gives an error to adjust it.

Mixer and loop settings save in project JSON, browser autosave and local saved sessions. Old projects open with neutral mixer defaults. Undo/redo includes these edits. Separate left/right RMS meters show actual channel levels on a −60 to 0 dBFS scale; master volume changes monitoring only.

Repairs: audio paths reconnect from the current data/sources folder after moving the application; interrupted analysis reports a retry; transition previews retain automation/effect timing; stale renders are discarded after timeline edits; solo/mute avoids fades toward inaudible clips; project saves use atomic replacement; autosave failures display a message. Keep a backup of your data folder. Python virtual environments are not portable and may require rerunning setup after moving the app.

Copy the update ZIP contents into your existing app folder, keeping data, .venv, and FFmpeg executables. The full ZIP includes setup/launch scripts and the prebuilt interface. No new dependencies are required.

## Version 1.2: mouse and touchpad timeline controls

Open **Mouse & touchpad** under the timeline toolbar, or the pointer button in the top bar, for the in-app guide. The timeline now has visible **Select, Cut, and Hand** tools, a zoom slider, Fit, Zoom to selection, Follow playhead, clearer trim targets, and a quick-action bar.

| Mouse or touchpad action | Result |
| --- | --- |
| Click a clip | Select and inspect it |
| Shift/Ctrl/Command + click | Add or remove a clip from the selection |
| Drag empty track space | Draw a selection box; hold Shift/Ctrl to add to the selection |
| Drag one selected clip | Move the selection together, retaining source ranges and relative timing/tracks |
| Drag a clip edge | Trim its source section; the left edge also moves the clip start |
| Drag a round upper fade handle | Change the real fade duration on an end without an enabled transition |
| Cut tool, then click a waveform | Split there; no timestamp entry required |
| Hand tool, then drag / middle-button drag | Pan the view without editing audio |
| Two-finger scroll | Pan horizontally/vertically when there is room |
| Shift + mouse wheel | Pan horizontally |
| Pinch / Ctrl or Command + wheel over timeline | Zoom around the pointer position |
| Drag the ruler or orange playhead handle | Scrub/seek the rendered remix |
| Right-click a clip or track area | Split here, copy/cut/paste, duplicate, mute, zoom to selection, delete |
| Hold Alt during a move/trim | Temporarily bypass clip-edge, playhead, and quarter-beat snapping |

Pinch is supported through the browser's Ctrl-wheel gesture events; touchpad/OS settings determine whether those events are sent. Ctrl+wheel and the zoom slider provide explicit alternatives. A snap guide displays the actual aligned time. Dragging near a viewport edge scrolls it, and Escape cancels an active edit. Each move/trim/fade gesture creates one undo step. Scroll, zoom, selection, and Hand-tool panning do not change the audio arrangement.

The selection inspector exposes group volume, duplicate, mute, copy, and delete, with a clip list for returning to an individual clip. Copy/paste uses an internal clip clipboard and preserves source references, clip effects, automation, relative positions, and transitions whose two clips were copied. It can paste into another project in the same running browser session while originals remain in the library. Normal Delete leaves other clips in place.

New keys: **V / B / H** choose Select/Cut/Hand; **Ctrl+A** selects all clips; **Ctrl+C / X / V** copies/cuts/pastes timeline clips. Existing Space, S, undo/redo, sound-pad, and project shortcuts remain available. The time ruler renders only nearby ticks and waveforms reuse their cached geometry while moving or playing.

## Version 1.1: faster editing and real sound effects

For an existing installation, stop the app, copy **all contents of MixForge-Studio-Update.zip** into the existing MixForge-Studio folder, replace application files, and run launch-windows.bat. Keep the data folder, virtual environment, and FFmpeg executables. No extra Python packages are required for this update. Press Ctrl+F5 if an old browser tab remains open. See UPDATE-INSTRUCTIONS.txt.

### Keyboard shortcuts

Open the keyboard button or press `?` for the in-app guide. Shortcuts leave text and numeric fields alone (Ctrl+S still saves).

| Keys | Action |
| --- | --- |
| Space | Play / pause |
| S | Split selected clip at playhead |
| Ctrl+D | Duplicate selected clip |
| Delete / Backspace | Remove selected clip |
| M / G | Mute selected clip / toggle beat snapping |
| Left / Right | Seek one beat |
| Shift+Left / Shift+Right | Nudge selected clip by a quarter beat |
| Home / End | Go to timeline start / end |
| [ / ] | Select previous / next clip |
| + / - / F | Zoom in / out / fit timeline |
| T / Shift+T | Auto Transition selected pair / all music pairs |
| Ctrl+Z / Ctrl+Y | Undo / redo (Ctrl+Shift+Z also redoes) |
| Ctrl+S / Ctrl+O / Ctrl+E | Save / open project / export |
| 1-8 | Audition a sound pad while Sound FX is open |
| Shift+1-8 | Add the pad sound to the timeline at the playhead |
| Esc | Stop pad auditions and deselect (or close a dialog) |

Command can replace Ctrl on Mac. Pad audition plays immediately and does not add audio to an export. Shift+pad or the pad's plus button creates an editable, undoable Sound FX clip. Pad audition is limited to 12 simultaneous voices and respects playback volume.

### Sound effects and transition sounds

The Sound FX library includes eight **original synthesized audio files**: Whoosh up/down, Deep impact, Tension riser, Sub drop, DJ air horn, Vinyl stop, and Shimmer. They are generated from actual waveforms/noise, bundled with the application, and work offline. Uploaded/imported effects support up to 60 seconds. Their waveform/energy data is measured from audio; BPM and key are left unset rather than invented.

Standalone effects are editable clips on a Sound FX track, with normal position, trim, gain, effects, undo/redo, saving, and WAV/MP3 export. Auto Remix excludes effect sources and automatic transition planning connects music clips without treating effect clips as songs.

Click a transition region, then choose **Transition sound**, volume, and offset. Negative offsets start the sound before the crossfade, useful for risers. Sounds mix into real preview and export audio. Regenerating transitions preserves their sound choices. Disabling a transition or the global Auto Transitions switch bypasses attached sounds. Music sections, order, and positions remain unchanged. Effect tails are bounded by the remix duration. Use this sound on all transitions applies the selected sound settings to every existing transition.

### Myinstants

Search inside Sound FX, import a search result, or paste a public Myinstants sound-page/MP3 URL. The local backend uses the **official https://www.myinstants.com/api/v1/** endpoints and downloads the actual MP3 into the local source library. No account or paid service is required for anonymous access. The API advertises 10 anonymous calls per minute; search/detail responses are cached for five minutes and calls are bounded accordingly. Audio imports are limited to 12 MB and 60 seconds, validated with FFmpeg, and keep their Myinstants source link. No Myinstants sounds are redistributed in the application bundle.

Search/import needs an Internet connection. If the API, download, or request limit prevents import, browse Myinstants, use its Download MP3 button, and upload that file into Sound FX. Already imported sounds and original built-ins work offline. External imports use the local app's network, with HTTPS and Myinstants-only URL/redirect validation.

## Phase 1: manual remix, preview, export

- Import multiple audio files. FFmpeg validates the audio stream rather than trusting extensions. A SHA-256 content identifier reconnects duplicate files and projects. Originals are never modified.
- Analysis runs in a single background queue. Add a ready source with `+` or drag it onto a track. Multiple clips may reference the same song.
- Drag clips to position them or change tracks. Drag their left/right edges to trim. Quarter-beat snapping, time ruler, seek, zoom, fit, mute, clip gain, tempo, and source in/out controls are available.
- Place the playhead inside a selected clip and use Split. Duplicate creates another independent clip. Earlier/Later swap clip positions. Undo/redo keeps up to 60 edit snapshots. Ctrl+Z / Ctrl+Y, Space, Delete, and Ctrl+S shortcuts are supported.
- Play builds a genuine mixed WAV in the background and plays it. Preview and export share the exact renderer. Edits require a fresh render on the next play; this is **background-rendered preview, not zero-latency live DSP**. Clip waveforms use real cached peak data; WaveSurfer displays the source selection without decoding the full song in the browser.
- WAV export is 24-bit stereo PCM at 44.1 kHz. MP3 is 320 kbps stereo at 44.1 kHz. Enable loudness balancing for a −16 LUFS target with −1.5 dB true-peak headroom. A final limiter remains active with normalization disabled. MP3 lossy encoding can have small peak and duration differences.

## Phase 2: automatic remix engine

1. Open Auto Remix and choose sources, duration, Smooth/Party/High Energy/Chill style, transition length, optional target BPM, and whether to keep the listed song order.
2. librosa analyzes mono 11.025 kHz audio for onset strength, beat positions, RMS energy, chroma-based approximate key, and candidate musical sections. Analysis is cached by file hash on disk.
3. Sections start on estimated 16-beat phrase grids when usable beats are detected. Source selection uses section energy and controlled randomness. Beat-quantized overlaps connect clips.
4. FFmpeg `atempo` performs pitch-preserving tempo adjustment, bounded to ±6% for auto arrangements. Widely different songs may therefore retain different effective BPMs. The target is a preference, not a guarantee.
5. The arranger covers the requested duration and returns real clips to the manual editor. Generate Again uses a new random seed. `/api/arrange` accepts `seed` for reproducible choices.

Beat tracking and musical keys are estimates. Sixteen-beat grouping approximates phrase boundaries; it is not a learned downbeat detector, structural segmentation model, or stem separator. Weak rhythm, silence, changing tempo, and ambiguous harmony can reduce reliability. Such sources retain valid audio and safe fallbacks rather than fabricated metadata.

## Phase 3: transitions, effects, projects

- Auto Transition works on the selected clip and the next clip in timeline order; Auto Transition All visits consecutive pairs. Styles: Smart, Smooth, DJ Beat Match, Echo/Reverb, Bass Swap.
- Defaults preserve selected source sections, source ordering, clip tempo, and timeline positions. An explicit opt-in can adjust the incoming clip's tempo by at most 6%, keeping its selected section and start position fixed. Existing overlap is used and durations are constrained to available audio. Without overlap, short boundary fades are applied and the limitation is shown; clips are never secretly moved or extended into unselected source audio.
- Smart uses BPM, estimated key distance, energy, and existing overlap. DJ Beat Match chooses a beat-aware transition duration; source cut points and speeds remain yours by default. The fade start aligns with a reliable incoming beat when that fits the overlap. Enable modest tempo adjustment or use the clip tempo control for closer manual beat matching. Auto Remix can adjust speed automatically.
- Equal-power sine/cosine envelopes, real low-band EQ exchange for Bass Swap, echo/reverb textures, loudness matching, and final limiting are rendered into audio. Echo/reverb uses FFmpeg delay networks. Effects remain inside the selected timeline and are truncated at its end to preserve timing.
- Click a transition region to edit its duration/style, toggle it, remove it, or preview the surrounding audio. The global Auto Transitions switch bypasses transition processing without discarding settings.
- Clip effects include three-band EQ, echo, reverb, fade durations, and a volume automation ramp. The project format supports arbitrary `[local_time_seconds, gain_db]` automation points with linear interpolation in dB. The UI supplies a preset editable through project JSON.
- Save Project writes JSON into `data/projects`. Projects can be reopened from the Projects dialog or downloaded/imported as JSON. Current work is also autosaved in browser localStorage. Project JSON includes source hashes, section timestamps, positions, tracks, gain, tempo, EQ/effects, automation, crossfades, name, BPM, and requested length. **JSON does not embed audio.** Back up the entire `data` folder and project files together, or re-import the exact original audio files on another computer.
- Open Demo Session creates three original synthesized instrumental songs and sends them through the real analyzer. No analysis or exports are simulated.

## Resource and reliability limits

- 500 MB and 30 minutes per source; 30-minute timeline; 128 clips; 64 source references; 8 audio tracks. The automatic arranger reports when 128 clips cannot cover the requested length.
- One analysis/render worker limits concurrency and peak RAM. Analysis uses downsampled mono audio; the browser receives only 1600 peak bins per source. Clips are decoded sequentially. The mixed timeline is a disk-backed float32 memmap, not a full in-memory session. A long individual clip can still need hundreds of megabytes during processing.
- At 44.1 kHz stereo float32, a 30-minute intermediate is roughly 635 MB. Keep several GB of free disk space for large projects. Cached originals, analysis, previews, and exports remain in `data`; delete unused files there while the app is stopped. No automatic deletion of user audio occurs.
- FFmpeg subprocess arguments use argument lists, never shell interpolation. Media paths are server controlled. Inputs use bounded Pydantic models. Cross-origin writes are rejected. The job queue is bounded and reports failures. Projects and original content are durable on disk, but running jobs are not resumed after restart.
- Unsupported or corrupt files return a useful error. Failed analysis is visible in the library and can be retried by re-importing. A missing project source is shown as missing and rendering fails safely.

## Checks

```sh
.venv/bin/python -m pytest backend/tests -q
npm test
npm run build
```

On Windows replace `.venv/bin/python` with `.venv\Scripts\python.exe`. Tests exercise trim sample counts, stereo distinction, silence placement, pitch preservation, equal-power curves, WAV/MP3 validity, peak limits, effects, automatic arrangement coverage, source bounds, deterministic seeds, and preservation of manual arrangements. API tests exercise unsupported media, cached uploads, saved projects, validation, and real background render downloads. Frontend tests cover timeline time/tempo math and clip defaults.

## Layout

- `src/`: React workstation, WaveSurfer source view, project history, and API integration.
- `backend/models.py`: bounded, documented project and request schemas.
- `backend/engine.py`: analysis, arrangement, transition planning, and real audio rendering.
- `backend/app.py`: upload, jobs, cached renders, project storage, and frontend serving.
- `backend/demo.py`: original synthesized demonstration songs.
- `data/`: generated at runtime; originals, cache, project JSON, renders.
- `dist/`: prebuilt browser application, also rebuilt by setup.

The project is intentionally independent of paid APIs and cloud AI. Third-party software retains its own license; FFmpeg distributions vary in enabled codecs and licensing.
