# Veil Android 0.2 — experimental source build

An independent Android content filter inspired by the public description of Beta Blocker Android. This project contains original app code and uses the separately acquired NudeNet detector. It is not the original product and is not affiliated with Isla2D.

**This ZIP is source code, not an installable APK. Android compilation and physical-device testing have not been completed in the creation environment.** The environment lacks the Android SDK and its build dependency download was blocked. See `VALIDATION.md` for what was actually checked.

## What is implemented

- Android 15+ native interface rebuilt around the reference’s dark purple cards, pink accents, lime buttons and five-tab navigation.
- Local NudeNet 320n detection with 18 selectable categories.
- Single-app screen capture service, notification stop action, resize and visibility callbacks.
- Solid, striped, labeled and outline styles; inverse censoring; custom label text; four colors; adjustable threshold and padding. Outline mode leaves content visible.
- Four frame-sampling presets. They are targets, not guaranteed frame rates.
- Basic HTTPS browser with up to four tabs, navigation, saved bookmarks and on-device page-image filtering.
- Photo selection, censored preview and PNG export with masks baked into pixels.
- Local session frame count and last inference duration.
- Build script and GitHub Actions workflow to produce a debug APK.

## Get an APK

### Option A — GitHub Actions

1. Create a GitHub repository and upload the **contents** of `VeilAndroid` to its root, including `.github/workflows/android.yml`. If using a file manager that hides dot folders, enable hidden files. Do not upload just the ZIP or nest the project under another folder.
2. Open the repository's **Actions** tab, choose **Build Android APK**, then **Run workflow**. A push to `main` or `master` also triggers it.
3. After a successful run, download **Veil-Android-debug-APK** from that run's artifacts.
4. Extract the artifact ZIP. Transfer `app-debug.apk` to your Android phone and tap it.
5. If prompted, permit that browser/file manager to install unknown apps, then finish installation.

The build downloads the model from a checksum-pinned package and includes it inside the APK. No API key, model subscription, or model download is needed on the phone. This workflow has been written but has not been executed here. Any failed build should be fixed using its actual log before treating the app as installable.

### Option B — your computer

Install **JDK 17**, **Python 3**, and **Android Studio**. In Android Studio's SDK Manager install Android 15 / API 35 and Android SDK Build-Tools 35.0.0. Make `java`, `javac` and Python available in your terminal.

macOS/Linux, from this folder:

```bash
chmod +x build.sh
./build.sh
```

Windows PowerShell, from this folder (no PowerShell execution-policy change needed):

```powershell
python scripts/build_android.py
```

The script locates the Android SDK, downloads and checks Gradle 8.11.1, fetches the pinned model, runs the geometry tests, and invokes APK compilation and lint. Set `ANDROID_HOME` if your SDK is in a custom location.

Successful output: `app/build/outputs/apk/debug/app-debug.apk`.

Android Studio can also open this directory as a Gradle project. Use Gradle 8.11.1, run `python scripts/fetch_model.py` first, and build the `app` module. A standard Gradle wrapper JAR is not included; the Python build launcher bootstraps the verified distribution.

## Use it on your phone

1. Open **Veil** and tap **Start protection**.
2. Enable **Appear on top** for Veil when directed, then return and tap Start again.
3. Allow notifications so the Stop action is readily available.
4. In Android's capture picker choose **one app**, then the app to filter. Keep that app full screen.
5. Scroll outside censor boxes. The boxes consume touches because they are opaque Android overlay windows.
6. Stop from the notification, the Android capture indicator, or Veil's **Stop protection** button.

Start with Balanced performance and the default categories. Lower the detection threshold to catch more regions at the cost of more false positives. Use vertical adjustment only if boxes are consistently offset. Cross-app alignment on Samsung and fold/rotation changes requires device verification.

For the in-app browser or photo tool, use the buttons on Veil's home screen; these stop an existing cross-app session. They do not require screen capture or overlay permission.

## Practical limitations

- This is an initial implementation, not a verified one-to-one replacement for the commercial app.
- Detection occurs **after** a frame is visible. It cannot guarantee no exposure, no false positives, or no missed regions.
- Select **one app**, not the entire screen. Entire-screen mode can see the masks themselves and produce feedback/flicker. Android does not provide a reliable public flag identifying the user's selected mode to reject it after consent.
- Split screen, freeform windows, unusual insets, keyboards and some edge-to-edge layouts can misalign cross-app masks. Capture gives image dimensions, not another app's screen origin.
- Apps can hide overlays. Secure/DRM video and protected windows cannot be scanned. A black captured frame is not proof of safe content.
- The built-in browser draws WebView page content for detection. Hardware-backed video, WebGL and fullscreen media may not appear in that bitmap. It is a basic browser, not a guaranteed safe browser.
- No incognito mode, ad blocker, achievements, popup storms, custom image packs, eye-specific detection, translations, or direct censored browser downloads are included.
- Photo exports are limited to a longest edge of 2048 pixels to bound memory usage. Review output before sharing.
- Locking the phone, revoking permission, Android stopping capture, or an inference failure ends screen protection. There is no hidden automatic restart.
- A debug APK is for personal testing. Different build machines may use different debug signing keys; installing one over another can fail. Keep the same signing key for stable future updates. Do not uninstall a prior build without exporting anything you need from it.

## Privacy

Inference is local. The model is bundled by the build. The detector never sends frames to a server. There is no telemetry, automatic screenshot saving, background recording, accessibility service, startup receiver, or device-administrator permission.

The optional browser uses the Internet and visits your requested sites; those sites can receive normal browser traffic and store cookies. It is not incognito. Android WebView Safe Browsing is enabled. Photos and captured frames are kept in memory; an exported PNG is written only to the destination you choose.

## Development

`UI_PREVIEW.html` is a standalone interactive design mockup; it does not run Android, load websites or detect images. Its JavaScript syntax was checked, but browser rendering was blocked in this environment. `UI_MATCH.md` records the reference screens and remaining differences.

`Architecture.md` describes implementation choices. `scripts/test_core.py` runs Java-only geometry tests without Android dependencies. `scripts/check_model.py` checks the actual ONNX model in CI. `DEVICE_TESTS.md` contains the uncompleted hardware acceptance checks.

References:

- Product feature description: https://isla2d.itch.io/beta-blocker-mobile
- Android capture lifecycle: https://developer.android.com/media/grow/media-projection
- Android overlay rules: https://developer.android.com/reference/android/view/WindowManager.LayoutParams
- NudeNet 3.4.2: https://pypi.org/project/nudenet/3.4.2/
- ONNX Runtime Android: https://onnxruntime.ai/docs/install/

Inverse masking bounds overlay complexity to 64 rectangles; if that limit would be exceeded, it covers the whole capture area. Use the notification to stop. Browser tabs are kept in memory and are not restored after activity recreation.
