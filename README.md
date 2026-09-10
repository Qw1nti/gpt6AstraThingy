# Veil Android

[![Build and test Android](https://github.com/Qw1nti/gpt6AstraThingy/actions/workflows/android.yml/badge.svg)](https://github.com/Qw1nti/gpt6AstraThingy/actions/workflows/android.yml)

An experimental Android 15+ app for on-device visual content filtering. Veil combines a screen-capture overlay, a basic filtered browser and local photo export. Inference uses NudeNet 320n through ONNX Runtime; no API key or subscription is required.

This is an independent project inspired by [Beta Blocker Android](https://isla2d.itch.io/beta-blocker-mobile), not the original app or an affiliated product.

## Status

Version **0.4.0** refreshes the style settings with an inline preview, six direct choices, contextual controls, precise coverage adjustments and expandable detection settings. It retains the working 0.3 tracking and detection pipeline. See the [0.4 change plan](docs/changes-0.4.md) and the current CI run before downloading. The owner reported that 0.3 worked very well; 0.4 still needs phone confirmation. Historical checks are in the [validation record](docs/validation.md), and future proposals are in the [improvement review](docs/improvement-roadmap.md).

## Download a test build

1. Open [Build and test Android](https://github.com/Qw1nti/gpt6AstraThingy/actions/workflows/android.yml).
2. Select a **successful** run for `main`.
3. Download **Veil-Android-debug-APK** from its artifacts and extract `app-debug.apk`.

GitHub sign-in may be needed to download artifacts. These are debug builds for testing, not production releases. Android 15 or newer is required. The model is included in the APK by the build; it is downloaded during development, not on first launch.

## Build locally

Install **JDK 17**, **Python 3.10+** and the **Android SDK** with API 35 and Build-Tools 35.0.0. CI uses Python 3.12. Android Studio's SDK Manager can install the SDK packages. Put `java`, `javac` and Python on your PATH; use `ANDROID_HOME` for a custom SDK location.

```sh
git clone https://github.com/Qw1nti/gpt6AstraThingy.git
cd gpt6AstraThingy
```

On macOS/Linux:

```sh
./build.sh
```

On Windows, including PowerShell:

```powershell
python scripts/build_android.py
```

The launcher fetches and verifies the model, runs geometry tests and invokes the checked-in Gradle wrapper to compile and lint. Gradle **8.11.1** is downloaded automatically and checked against its pinned SHA-256. No system Gradle installation is required.

Output: `app/build/outputs/apk/debug/app-debug.apk`.

### Android Studio or direct Gradle

Open the **repository root** in Android Studio and select JDK 17 for Gradle. Fetch the model before building:

```sh
python3 scripts/fetch_model.py
./gradlew :app:assembleDebug :app:lintDebug
```

On Windows use `python` and `.\gradlew.bat`. Android Studio may create `local.properties`; it is intentionally ignored by Git.

## Tests

Geometry tests need Python and a JDK, without Android dependencies:

```sh
python3 scripts/test_core.py
```

Model smoke tests additionally need the downloaded model and Python dependencies. Use a virtual environment for local installs:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-ci.txt
python scripts/fetch_model.py
python scripts/check_model.py
```

On Windows, use `.venv\Scripts\python.exe` in place of `python` after creating the environment. Activation is optional.

CI runs these checks, APK compilation, Android lint and Android 15 emulator rendering tests on pushes to `main`/`master`, pull requests and manual runs. [Device checks](docs/device-tests.md) are maintained separately.

## Features and limits

- Single-app capture with overlay masks and a notification stop action.
- Solid, patterned, labeled, outline, custom-image and pixelated-with-border styles; inverse masking; adjustable categories, confidence and box shrinking/expansion.
- HTTPS browser with up to four tabs and saved bookmarks.
- Local photo selection, censor preview and PNG export.

Filtering happens after capture and may miss or misclassify content. Outline mode does not conceal content. Screen alignment, video coverage, browser state restoration and export behavior require further testing. There is no incognito mode, ad blocker, translation system or direct censored browser download. Read [usage and limitations](docs/usage.md) before testing.

## Repository layout

| Path | Purpose |
| --- | --- |
| `app/` | Android application, resources and Gradle configuration |
| `gradle/`, `gradlew`, `gradlew.bat` | Pinned Gradle wrapper |
| `scripts/` | Model acquisition, build launcher and test entry points |
| `tests/` | Android-independent Java geometry tests |
| `docs/` | Architecture, validation, usage, known issues and UI reference |
| `.github/` | CI workflow and contribution templates |

See [CONTRIBUTING.md](CONTRIBUTING.md) for the development workflow and [architecture](docs/architecture.md) for implementation details. The [HTML preview](docs/ui-preview.html) is a design mockup, not a running Android app.

## License

Original project code is [MIT licensed](LICENSE). Model, runtime and build-tool terms are documented in [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
