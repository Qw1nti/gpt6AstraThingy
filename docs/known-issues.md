# Known issues

These findings are tracked separately from repository maintenance. No fixes below are implied by a passing build.

| Priority | Finding | Evidence / next check |
| --- | --- | --- |
| High | Detection results are capped at 32 regions. | A synthetic test of the actual parser retained 32 of 36 valid, disjoint detections. Define overflow handling and add a regression case. |
| High | Browser sessions and unsaved photo work lack activity-state restoration. | Source review. Reproduce rotation, navigation away/back and process recreation on Android. |
| High | Masks may lag or misalign during scroll, resize or changes to app bounds. | Source-derived risk. Test actual capture placement, keyboard, rotation and fold/unfold. |
| Medium | Browser activity teardown does not explicitly detach the selected WebView before destroying it. | Source review; no crash or leak reproduced. |
| Medium | Inverse-mask fragmentation can trigger full-screen coverage and block most touches. | Geometry fallback is tested; notification stop and interaction need Android testing. |
| Medium | Some browser controls and text are small; photo output is capped at 2,048 pixels on the longest edge. | Review accessibility and exported image quality on Android. |

The original-app feature and visual differences are in [UI comparison](ui-comparison.md). [Device tests](device-tests.md) cover the remaining runtime checks.

## Resolved build blockers

[Commit 37004e2](https://github.com/Qw1nti/gpt6AstraThingy/commit/37004e26c47c33a3ea4b50248f77b34d1d8ce8ec) corrected the unsupported dialog-builder call and the fixed-input-dimension checks. [Its CI run](https://github.com/Qw1nti/gpt6AstraThingy/actions/runs/34254473730) passed model checks, compilation and Android lint. Android detector initialization still needs runtime verification.
