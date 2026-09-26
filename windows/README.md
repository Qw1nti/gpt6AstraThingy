# Veil for Windows

An independent Windows desktop implementation with local visual detection. Its dark interface follows the public Windows reference: black backgrounds, charcoal cards, thin borders, and red controls. Veil uses its own name, code, and artwork. The original commercial application is not bundled or required.

## Current scope (0.1)

- Local NudeNet 320n ONNX inference, using the same pinned model acquisition as the Android project.
- Selected display or all-display capture, with click-through overlays excluded from supported screen capture paths.
- Category selections and saved profiles, confidence and coverage controls (−40% to +70%), reverse censoring.
- Solid, mosaic, blur, labeled, outline-only and private custom-image styles.
- Import and permanently censor a local photo, preview, then export a PNG. Outline-only export leaves the underlying content visible.

Video export, screen recording, OBS virtual camera, achievements, animations, language packs, and GPU acceleration are not implemented. No performance or exact visual-parity claim is made. In particular, detection is asynchronous and cannot guarantee that content is hidden before it appears. Protected video, exclusive fullscreen surfaces and secure desktops may not be captured.

## Download on Windows

Open a successful [Windows workflow run](https://github.com/Qw1nti/gpt6AstraThingy/actions/workflows/windows.yml), download **Veil-Windows-portable**, extract the ZIP, then run `VeilWindows.exe` inside the extracted folder. Keep all extracted files together. GitHub sign-in may be required to download the artifact. Windows may warn about an unsigned test executable.

Requires 64-bit Windows 10 version 2004 or newer. Try a harmless static image first. Use the Home button to stop protection. Test overlay alignment and video behavior on the actual PC, especially with mixed DPI or multiple monitors.

## Development

On Windows, with Python 3.11:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install -r windows\requirements.txt
.venv\Scripts\python.exe scripts\fetch_model.py
$env:PYTHONPATH = 'windows'
.venv\Scripts\python.exe windows\run.py
```

Run `python -m unittest discover -s windows/tests -p 'test_*.py' -v` with `PYTHONPATH=windows`. The GitHub workflow runs these checks, an offscreen UI smoke test and an ONNX inference smoke test before packaging with PyInstaller. The Windows executable and overlay behavior still need real-device testing.

Preferences and an imported custom mask are saved under `%APPDATA%\Veil`. Captured frames and source photos are not saved automatically. The Windows app does not use a browser or make network requests at runtime.
