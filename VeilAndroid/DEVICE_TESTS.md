# Device acceptance checks — not yet executed

Use benign test images containing faces or hands/feet and enable the corresponding category. Synthetic style preview tests rendering only; it does not validate detection. Never use lack of boxes as proof that content is safe.

- [ ] Build and Android lint finish successfully; install APK on Android 15 or 16.
- [ ] Launch with model bundled, airplane mode on. Open a benign local photo; enable face detection and verify boxes. Compare with the upstream detector on the same image.
- [ ] Deny overlay access; verify no session starts and the instruction is clear.
- [ ] Deny notification permission; capture can still be stopped from Veil/system indicator.
- [ ] Cancel capture picker; no service or notification remains.
- [ ] Choose a single full-screen app. Check portrait boxes against known subjects, then landscape.
- [ ] Confirm Veil overlays are excluded from the single-app capture. Static detections should remain stable rather than alternate on/off.
- [ ] Fold/unfold a Z Fold while active; confirm resize without reusing the token or creating a second virtual display.
- [ ] Switch away from the selected app; masks disappear. Return; scanning resumes.
- [ ] Open keyboard and dismiss it; inspect alignment. Document unsupported layouts.
- [ ] Tap/swipe outside boxes; interaction reaches the app. Inside boxes touches are absorbed.
- [ ] Stop from notification, app, system capture indicator, and lock screen. No masks persist.
- [ ] Start/stop rapidly at least ten times; no orphan workers, overlays or projection sessions.
- [ ] Revoke overlay access while running; session ends cleanly.
- [ ] Run each performance preset for five minutes. Measure latency, thermal behavior and battery usage.
- [ ] Read a benign image-heavy page in the browser; verify capture is of WebView only and masks do not feed back.
- [ ] Navigate, scroll, rotate, background and return to browser while inference is pending; no stale result appears on another page/layout.
- [ ] Browser HTTP/mixed-content and non-web schemes are rejected; camera/microphone requests denied.
- [ ] Import a rotated JPEG, PNG, large photo and corrupt file. Verify orientation, size cap and clear errors.
- [ ] Save PNG; reopen externally and confirm opaque censor pixels are baked in. Cancel export without changing the original.
- [ ] Close photo tool during processing/export; no crashes or recycled-bitmap access.
- [ ] Confirm no image data is written automatically to private storage or sent over network by inference code.

Unmet cross-app alignment or self-capture checks block any claim of reliable cross-app filtering. Model benchmark comparison and APK/device tests are still required before production use.

## Version 0.2 additional checks — not yet executed on Android

- [ ] All five navigation tabs route correctly; Browser/Export do not accumulate duplicate activities.
- [ ] Compare Home, Settings, Browser and Help against reference screenshots at 412 dp and on folded/unfolded screens.
- [ ] Start/Stop button reflects service state after switching tabs.
- [ ] Category grid toggles each intended model class; grouped face/feet/armpit options select both relevant labels.
- [ ] Outline mode leaves content visible and displays the outline-only export warning.
- [ ] Inverse mode covers only the complement of detections. With no detections it covers the whole capture.
- [ ] An overly complex inverse scene falls back to full coverage; notification Stop remains reachable.
- [ ] Custom censor text, colors and style presets persist across relaunches.
- [ ] Open, switch and close four browser tabs. No stale inference results leak between tabs; inactive tabs pause.
- [ ] Simulate inference failure, then navigate/switch tabs; the browser remains covered and reports failure.
- [ ] Verify text scaling at 100%, 130% and 150%; no controls overlap or become unreachable.
