# Veil for Windows

An independent Windows desktop implementation with local visual detection. Its dark interface follows the public Windows reference: black backgrounds, charcoal cards, thin borders, and red controls. Veil uses its own name, code, and artwork. The original commercial application is not bundled or required.

## Current scope (0.2)

- Local NudeNet 320n ONNX inference, using the same pinned model acquisition as the Android project.
- Selected display or all-display capture, with click-through overlays excluded from supported screen capture paths.
- Category selections and saved profiles, confidence and coverage controls (−40% to +70%), reverse censoring.
- Solid, mosaic, blur, labeled, outline-only and private custom-image styles.
- Import and permanently censor a local photo, preview, then export a PNG. Outline-only export leaves the underlying content visible.
- Whole-display and overlapping regional scans retain more detail than shrinking a large desktop to one 320×320 input. Large/multiple displays require more CPU inference work; presets still control scan spacing.
- Live style/category/confidence changes, a three-second overlay test, and bounded local diagnostics.

Video export, screen recording, OBS virtual camera, achievements, animations, language packs, and GPU acceleration are not implemented. No performance or exact visual-parity claim is made. In particular, detection is asynchronous and cannot guarantee that content is hidden before it appears. Protected video, exclusive fullscreen surfaces and secure desktops may not be captured.

## Download on Windows

Open a successful [Windows workflow run](https://github.com/Qw1nti/gpt6AstraThingy/actions/workflows/windows.yml), download **Veil-Windows-portable**, extract the ZIP, then run `VeilWindows.exe` inside the extracted folder. Keep all extracted files together. GitHub sign-in may be required to download the artifact. Windows may warn about an unsigned test executable.

Requires 64-bit Windows 10 version 2004 or newer. Try a harmless static image first. Use the Home button to stop protection. Test overlay alignment and video behavior on the actual PC, especially with mixed DPI or multiple monitors.

## Blocking is on but nothing is covered

1. Press **Test overlay (3 seconds)** on Home. A labeled red rectangle should appear on each selected display. This stops an existing blocking session; press **Start Blocking** afterward.
2. For a harmless detection test, enable **Face (female)** and **Face (male)** on Body Parts and display a large clear portrait. Faces are not enabled by default; the default categories cover exposed nudity.
3. Check Home: increasing frame counts with **Scanning · no selected categories detected** mean inference is running but has found no selected matches. Lower confidence if appropriate. **Outline** marks regions without covering their content.
4. If the rectangle is invisible, alignment is wrong, or protection stops, check `%APPDATA%\Veil\diagnostics.log` for errors. Changing display layout or scaling stops protection; restart it to recreate aligned overlays.

Version 0.2 fixes a reproduced detail-loss failure: the original whole-desktop path missed a benign 512×512 portrait placed on a 1920×1080 background; regional scanning recognizes it. This is a confirmed test-case fix, not proof of the cause on the owner's PC or of general detection accuracy.

## Development

On Windows, with Python 3.11:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r windows\requirements.txt
.venv\Scripts\python.exe scripts\fetch_model.py
$env:PYTHONPATH = 'windows'
.venv\Scripts\python.exe windows\run.py
```

Run `python -m unittest discover -s windows/tests -p 'test_*.py' -v` with `PYTHONPATH=windows`. The GitHub workflow runs these checks, an offscreen UI smoke test, real portrait/desktop ONNX recognition, and `windows/tests/smoke_windows.py` on the native Windows desktop before packaging with PyInstaller. The native check exercises device mapping, window visibility/click-through styles, capture exclusion, detection-to-render delivery and live settings. It does not establish behavior on the owner's display/GPU configuration.

Validation on 2026-09-30: 13 regression checks, six-view construction and real portrait/desktop inference passed locally with Linux/offscreen Qt and on the Windows runner. The [Windows workflow](https://github.com/Qw1nti/gpt6AstraThingy/actions/runs/36725936026) passed the native blocking pipeline and packaged code commit `bf550b6`. [Download its portable build](https://github.com/Qw1nti/gpt6AstraThingy/actions/runs/36725936026/artifacts/11103340364). Mixed-DPI hardware, video and sustained latency/CPU use still need PC testing. The owner's reported failure is not yet confirmed resolved on their PC. Android runtime source was not changed.

Preferences, an imported custom mask and bounded diagnostic logs (256 KB each, two backups) are saved under `%APPDATA%\Veil`. Logs record operational errors and display geometry. Captured frames and source photos are not saved automatically. The Windows app does not use a browser or make network requests at runtime.
