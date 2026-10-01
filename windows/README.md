# Veil for Windows

An independent Windows desktop implementation with local visual detection. Its dark interface follows the public Windows reference: black backgrounds, charcoal cards, thin borders, and red controls. Veil uses its own name, code, and artwork. The original commercial application is not bundled or required.

## Current scope (0.4)

- Local NudeNet 320n ONNX inference, using the same pinned model acquisition as the Android project.
- Dedicated, checksum-pinned YuNet ONNX face detection with rectangular inputs retaining native detail up to a 2560-pixel longest edge.
- Selected display or all-display capture, with click-through overlays excluded from supported screen capture paths.
- Category selections and saved profiles, confidence and coverage controls (−40% to +70%), reverse censoring.
- Solid, smooth blur, pixelated blur, labeled, outline-only and private custom-image styles.
- Import and permanently censor a local photo, preview, then export a PNG. Outline-only export leaves the underlying content visible.
- Body categories use whole-display and overlapping regional scans. Faces use a separate higher-resolution full-display pass. Large/multiple displays and enabling both models require more CPU inference work.
- Live style/category/confidence changes, a three-second overlay test, and bounded local diagnostics.
- Live scan-interval slider, measured scan rate and average scan work, with feedback when scan time exceeds the chosen interval.
- Capture-time motion prediction, animated masks between scans and brief tolerance for missed detections, with a Settings switch.

## Small faces and motion

On **Body Parts**, enable **Faces (all people)**. The detector covers faces
without assigning gender. Old profiles with either face category enabled migrate
to this combined selection; other filters stay selected. **Use faces only** is
an explicit shortcut that clears body filters and skips body-model inference.
Use it when you only want faces covered and want quicker updates.

The old 320-pixel body model missed small faces even with regional scans. The
new face path retains screen detail up to a 2560-pixel longest edge, downscaling
larger displays. This improves a reproduced fixture with roughly 11–21-pixel
faces on a 1920×1080 desktop, but does not guarantee detection of every tiny,
occluded, side-on or fast-moving face. Enabling both faces and body categories
runs both models; use Home's measured work/rate to compare on your PC.

**Motion prediction** is enabled by default in Settings. It associates recent
boxes using position, size and category, estimates velocity using capture
timestamps, and repaints masks about every 33 ms without running extra inference.
Prediction is limited to 120 ms and at most one box edge or 128 pixels per axis.
Missed boxes remain for 300–600 ms after their last result, depending on the scan
interval, then expire. Settings changes clear old tracks; an entirely unmatched
set of new detections clears old positions. A blank scene can retain a mask
briefly until expiry. Blur/pixelated patches use the last captured texture while
moving between scans. Outline mode still only marks regions.

Prediction cannot anticipate the first appearance of a face, and rapid changes
of direction or scene cuts can still cause errors. Turn it off if masks drift.
Very slow scan intervals may outlast the hold window; prediction is not a
substitute for fresh detections. Higher scan rates cannot recover detail lost
by the old model's input resolution.

## Scan speed and pixelated blur

Home has a **Scan frequency** slider: 0 means **Fastest available**, and other
values request that many milliseconds between the start of scans of every
selected display, up to 1,000 ms. For example, 100 ms requests up to 10 scans/sec,
200 ms up to 5, and 500 ms up to 2. The default is 150 ms. Existing Low/Medium/High/Ultra
profiles migrate to 350/150/66/0 ms respectively.

These are requested rates. Each capture/inference/effect pass must finish before
another starts, followed by at least a 5 ms yield; missed intervals do not queue
up. Home reports the achieved scan rate and average scan work over up to eight
passes. A slower pass limits the achieved rate even when a shorter interval is
selected. Timing covers all selected displays together and is not a CPU-usage
percentage or a guarantee of game/video performance.

There is no universal scan rate without performance impact. Start around 150–200
ms, compare your normal game/video performance, then try shorter intervals.
Use 250–500 ms if other work stutters. Fastest uses the most scanning time.
Sustained tests on the owner's PC are still needed to determine a suitable rate.

Choose **Pixelated Blur** under Censor Styles for block pixelation, adjustable
block size and a colored border; **Blur** remains the smooth blur effect. The old
Mosaic style migrates to Pixelated Blur, retaining its block size, border color
and coverage. Live effects, previews and photo export share this rendering.

Video export, screen recording, OBS virtual camera, achievements, animations, language packs, and GPU acceleration are not implemented. No performance or exact visual-parity claim is made. In particular, detection is asynchronous and cannot guarantee that content is hidden before it appears. Protected video, exclusive fullscreen surfaces and secure desktops may not be captured.

## Download on Windows

Open a successful [Windows workflow run](https://github.com/Qw1nti/gpt6AstraThingy/actions/workflows/windows.yml), download **Veil-Windows-portable**, extract the ZIP, then run `VeilWindows.exe` inside the extracted folder. Keep all extracted files together. GitHub sign-in may be required to download the artifact. Windows may warn about an unsigned test executable.

Requires 64-bit Windows 10 version 2004 or newer. Try a harmless static image first. Use the Home button to stop protection. Test overlay alignment and video behavior on the actual PC, especially with mixed DPI or multiple monitors.

## Blocking is on but nothing is covered

1. Press **Test overlay (3 seconds)** on Home. A labeled red rectangle should appear on each selected display. This stops an existing blocking session; press **Start Blocking** afterward.
2. For a harmless detection test, enable **Faces (all people)** on Body Parts and display a clear portrait. **Use faces only** skips the body model. Faces are not enabled by default; the default categories cover exposed nudity.
3. Check Home: increasing frame counts with **Scanning · no selected categories detected** mean inference is running but has found no selected matches. Lower confidence if appropriate. **Outline** marks regions without covering their content.
4. If the rectangle is invisible, alignment is wrong, or protection stops, check `%APPDATA%\Veil\diagnostics.log` for errors. Changing display layout or scaling stops protection; restart it to recreate aligned overlays.

Version 0.2 fixes a reproduced detail-loss failure: the original whole-desktop path missed a benign 512×512 portrait placed on a 1920×1080 background; regional scanning recognizes it. This is a confirmed test-case fix, not proof of the cause on the owner's PC or of general detection accuracy.

## Development

On Windows, with Python 3.11:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r windows\requirements.txt
.venv\Scripts\python.exe scripts\fetch_model.py
.venv\Scripts\python.exe windows\fetch_face_model.py
$env:PYTHONPATH = 'windows'
.venv\Scripts\python.exe windows\run.py
```

Run `python -m unittest discover -s windows/tests -p 'test_*.py' -v` with `PYTHONPATH=windows`. The GitHub workflow runs these checks, an offscreen UI smoke test, real portrait/desktop ONNX recognition, and `windows/tests/smoke_windows.py` on the native Windows desktop before packaging with PyInstaller. The native check exercises device mapping, window visibility/click-through styles, capture exclusion, detection-to-render delivery and live settings. It does not establish behavior on the owner's display/GPU configuration.

Validation on 2026-09-30: 13 regression checks, six-view construction and real portrait/desktop inference passed locally with Linux/offscreen Qt and on the Windows runner. The [Windows workflow](https://github.com/Qw1nti/gpt6AstraThingy/actions/runs/36725936026) passed the native blocking pipeline and packaged code commit `bf550b6`. [Download its portable build](https://github.com/Qw1nti/gpt6AstraThingy/actions/runs/36725936026/artifacts/11103340364). Mixed-DPI hardware, video and sustained latency/CPU use still need PC testing. The owner's reported failure is not yet confirmed resolved on their PC. Android runtime source was not changed.

Version 0.3: 20 regression checks, six-view construction and real
portrait/desktop inference passed locally and on the Windows runner. The scan
slider was visually checked at the minimum 1000×700 window size. The
[Windows workflow](https://github.com/Qw1nti/gpt6AstraThingy/actions/runs/36796771215)
passed native capture/overlay testing with live interval changes and pixelated
blur, then packaged code commit `41acca6`.
[Download version 0.3](https://github.com/Qw1nti/gpt6AstraThingy/actions/runs/36796771215/artifacts/11134630063).
No owner-PC performance ceiling or gaming/video impact has been measured.

Version 0.4, validated on 2026-10-01: 32 regression checks, six-view construction,
both local models, blank-screen rejection, 11–21-pixel face boxes and a 36-face
desktop fixture passed locally and on Windows. The
[Windows workflow](https://github.com/Qw1nti/gpt6AstraThingy/actions/runs/36800393730)
passed native small moving-face capture, association, overlay rendering and
expiry, live pixelation/rate changes, and portable packaging of code commit
`cedf950`. [Download version 0.4](https://github.com/Qw1nti/gpt6AstraThingy/actions/runs/36800393730/artifacts/11135655820).
The face/prediction controls were visually checked at 1000×700. These fixtures
use one public portrait at different scales/positions; they are regression
checks, not a diverse accuracy benchmark. Runner timing was 55 ms average scan
work with a requested 250 ms interval (4 scans/sec), not an owner-PC benchmark.
Actual video accuracy, end-to-end latency, CPU load, mixed-DPI hardware and
sustained performance still need testing on the owner's PC. Android runtime
source remains unchanged.

Preferences, an imported custom mask and bounded diagnostic logs (256 KB each, two backups) are saved under `%APPDATA%\Veil`. Logs record operational errors and display geometry. Captured frames and source photos are not saved automatically. The Windows app does not use a browser or make network requests at runtime.
