# Validation record

Created 2026-09-08.

## Executed successfully here

- Compiled the actual Android-independent `DetectionCore.java` and its Java test harness using the JDK 17 compiler module; executed the compiled classes. **18 assertions passed** covering coordinate conversion, landscape/portrait scaling, class filtering, thresholds, transposed output, non-maximum suppression, padding, clipping and invalid outputs.
- Parsed all **11 Java source files** with the JDK compiler parser. No syntax errors. This was parsing only; Android and ONNX Runtime symbols were not type-checked.
- Parsed all **4 Python scripts** with Python's AST parser.
- Parsed the Android manifest, theme and vector resource as XML.
- Parsed the GitHub Actions workflow as YAML.
- Exercised the model acquisition function with tampered bytes. Checksum verification rejected them before writing any files.
- Reviewed the capture lifecycle: one virtual display per consent token, resize of existing display, source reader identity check, stale-result generation guards, notification stop, visibility changes, worker-confined detector and ordered cleanup.

## Not executed / not established

- Android compilation, Gradle dependency resolution, Android lint and APK signing.
- Actual ONNX inference, model accuracy, preprocessing equivalence to upstream, and Android native runtime loading.
- Emulator or phone UI rendering, screen projection, censor alignment, touch behavior, battery/thermal performance, fold/unfold behavior and image export.
- GitHub Actions execution. The workflow is provided as source, not as evidence of a successful remote build.

The environment has Java compiler modules but no Android SDK or Gradle installation. A build dependency network request was blocked by environment approval restrictions. Therefore this delivery is an **uncompiled experimental source project**, not an installable or device-verified app. The model is acquired by the supplied build process and is not bundled in the source archive.

The completed checks validate specific source logic and file syntax. They do not establish reliable nudity filtering or complete compatibility with Beta Blocker. Follow `README.md` to build and `DEVICE_TESTS.md` to validate the actual app.

## Version 0.2 follow-up

- Re-executed the 18 original detection checks successfully.
- Compiled and ran the new `MaskRegions` Java implementation with its test harness: 861 geometry assertions plus 50 seeded randomized scenes and 400,000 point-coverage comparisons passed. These verify inverse masks are bounded, cover the complement and do not overlap under the tested inputs.
- Parsed all 13 Java files using the actual JDK syntax parser; no syntax errors. This is still not Android type checking.
- Parsed Python scripts, Android XML, workflow YAML and standalone preview JavaScript successfully.
- Audited cross-tab inference generation guards and kept the browser covered on an inference failure even after navigation/tab changes.
- Corrected photo output/status wording for outline-only mode, which does not hide content.
- Added a four-tab browser limit and a 64-window bound on inverse overlays.
- Looked for local Android SDK/Gradle/ONNX build artifacts; none were available. No APK was compiled and no native UI or model inference test ran.
- Attempted to inspect the standalone HTML design preview in the cloud browser. The connection first reset; after reconnecting, its local-file URL was rejected by browser security policy. No workaround was attempted. The preview has syntax validation only, not successful browser interaction or visual-layout validation.

The reference screenshots were successfully viewed. `UI_PREVIEW.html` is a manually authored design aid, not an Android screenshot or evidence of a running APK.
