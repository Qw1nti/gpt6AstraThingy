# Validation record

## Verified build baseline

[Commit 37004e2](https://github.com/Qw1nti/gpt6AstraThingy/commit/37004e26c47c33a3ea4b50248f77b34d1d8ce8ec) passed [GitHub Actions run 34254473730](https://github.com/Qw1nti/gpt6AstraThingy/actions/runs/34254473730) on 8 September 2026:

| Check | Result |
| --- | --- |
| Detection geometry | 18 checks passed |
| Inverse masks | 861 assertions, 50 randomized scenes and 400,000 coverage samples passed |
| Pinned model acquisition | Download and checksum verification passed |
| ONNX model smoke test | Input/output contract and three synthetic inferences passed |
| Debug APK | Compiled successfully with JDK 17, SDK 35, AGP 8.9.2 and Gradle 8.11.1 |
| Android lint | Task passed; this is not a claim of zero warnings |
| Artifacts | Debug APK and lint reports uploaded to the run |

The model declares symbolic batch/height/width axes and accepts concrete float32 inputs of shape `[1, 3, 320, 320]`. The three synthetic outputs were finite and had shape `[1, 22, 2100]`. This verifies loading and execution on the Linux CI runner, not detection accuracy or Android native inference.

## Repository reorganization

The project now builds from the repository root using the standard Gradle wrapper. The workflow also runs from the root. Consult the [current CI runs](https://github.com/Qw1nti/gpt6AstraThingy/actions/workflows/android.yml) for the reorganization commit's result; the historical run above used the previous nested layout.

## Earlier source audit

The original source-only audit verified Java syntax, Python/XML/YAML parsing, geometry tests and rejection of tampered model bytes. Those checks could not establish an installable APK. Remote CI subsequently exposed and confirmed fixes for the dialog method and model-shape validation, superseding the earlier compilation limitation.

The independent dense-scene probe retained only 32 of 36 disjoint valid detections. Version 0.3 removed that cap, and the regression suite retains 100 disjoint detections. This historical probe is no longer an open cap defect.

## Pending runtime verification

- Complete native UI interaction coverage. Installation/basic operation are owner-reported, and four graphics/import tests passed on the Android emulator.
- Android ONNX runtime loading and model preprocessing/accuracy comparison.
- MediaProjection consent, overlays, alignment, scrolling, video and stop behavior.
- Activity/process recreation, photo export, keyboard, rotation and fold/unfold.
- Accessibility, latency, battery use and thermal behavior.
- Native screenshot comparison against the original app.

The HTML design preview is not a native Android test. Follow the [device checklist](device-tests.md); report observed results rather than marking untested behavior as passed.

## Version 0.3 results and owner feedback

[Commit 38144c5](https://github.com/Qw1nti/gpt6AstraThingy/commit/38144c59fd1b0543a647a6cd2a12ec8150f758e2) passed [CI run 34285010350](https://github.com/Qw1nti/gpt6AstraThingy/actions/runs/34285010350) on 8 September 2026. Both the APK job and Android rendering test job succeeded.

- Existing detection and inverse-mask geometry suites passed.
- All 216 dense-scene, grouping, box-contraction and motion checks passed.
- Model download/checksum, input/output checks and synthetic inferences passed.
- Debug APK compilation and Android lint passed.
- All four Android 15 instrumentation tests passed: pixelation/border rendering, opaque custom-image backing, bounded private image import and reusable ImageReader buffer colors.

The owner initially reported choppy tracking in 0.2. After installing 0.3, they reported: “It works very well now.” This supersedes the earlier request for an overall phone retest. It does not supply individual results for every style, fold/rotation transition, export operation or prolonged session. No new phone timing, battery or temperature measurements were provided.

The [improvement review](improvement-roadmap.md) uses this successful baseline and separates measured checks, owner feedback, source risks and optional proposals. This follow-up reviewed existing CI results and source; it did not run another APK build or benchmark.
