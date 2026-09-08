# Known issues

These findings are tracked separately from repository maintenance. No fixes below are implied by a passing build.

| Priority | Finding | Evidence / next check |
| --- | --- | --- |
| High | Crowded-scene detection accuracy and tracking performance need phone retesting. | Version 0.3 removes the 32-result cap and retains all 100 regions in a synthetic regression case. Overlay windows are grouped; this does not improve model recognition of tiny or missed subjects. |
| High | Browser sessions and unsaved photo work lack activity-state restoration. | Source review. Reproduce rotation, navigation away/back and process recreation on Android. |
| High | Masks may lag or misalign during scroll, resize or changes to app bounds. | Source-derived risk. Test actual capture placement, keyboard, rotation and fold/unfold. |
| Medium | Transparent gaps in crowded overlay groups can absorb touches. | Version 0.3 draws exact masks in at most 16 grouped windows. Scroll outside those windows; verify interaction on the phone. |
| Medium | Inverse-mask fragmentation can trigger full-screen coverage and block most touches. | Geometry fallback is tested; notification stop and interaction need Android testing. |
| Medium | Some browser controls and text are small; photo output is capped at 2,048 pixels on the longest edge. | Review accessibility and exported image quality on Android. |

The original-app feature and visual differences are in [UI comparison](ui-comparison.md). [Device tests](device-tests.md) cover the remaining runtime checks.

## Resolved build blockers

[Commit 37004e2](https://github.com/Qw1nti/gpt6AstraThingy/commit/37004e26c47c33a3ea4b50248f77b34d1d8ce8ec) corrected the unsupported dialog-builder call and the fixed-input-dimension checks. [Its CI run](https://github.com/Qw1nti/gpt6AstraThingy/actions/runs/34254473730) passed model checks, compilation and Android lint. Android detector initialization still needs runtime verification.
