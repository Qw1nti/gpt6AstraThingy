# Veil Android

Independent implementation of local visual content filtering, inspired by the public feature description of Beta Blocker Android. No original APK, source, branding, graphics, or paid assets are used.

## Implementation plan

1. Native Android 15+ app, Java 17, Android Gradle Plugin 8.9.2, Gradle 8.11.1, target SDK 35.
2. NudeNet 3.4.2 320n ONNX detector through ONNX Runtime 1.21.0. Build-time model acquisition from a SHA-256-pinned PyPI wheel. Local-only inference.
3. Foreground MediaProjection service with a new consent token for every session, one virtual display per token, bounded frame sampling, resize callbacks, visibility handling and deterministic cleanup.
4. Single-app capture and opaque censor windows. Each region is a separate touchable window; Android's untrusted-touch protection makes a fully opaque, system-wide click-through overlay unsuitable. Scroll outside censor regions. Stop always remains available in the notification.
5. Browser uses an in-app capture loop drawing the WebView itself, excluding its sibling censor overlay. It supports up to four in-memory tabs, navigation and bookmarks. Hardware video surfaces are outside this path's guarantee.
6. Local photo import, detection, preview and explicitly requested censored PNG export.
7. Four sampling presets, class selection, confidence, padding, mask color/style and session counters.
8. Pure-Java detection geometry tests, Android build/lint workflow and an explicit real-device checklist.

## Boundaries

This is an initial implementation, not verified feature parity. No achievements, animation packs, incognito mode, ad-block lists, arbitrary imported models, or guaranteed zero-latency filtering. Version 0.2 adds inverse censoring, outline mode, editable labels, and a reference-led five-tab UI. Inverse masks use bounded rectangular subtraction, falling back to full coverage if more than 64 regions would be needed. Detection can miss content and can misclassify benign images. Screen-capture protection/DRM cannot be bypassed.

Cross-app mapping assumes the selected app is full screen. Capture APIs do not expose another app's screen origin; split screen and freeform windows are unsupported. A vertical calibration control is provided. Folding/rotation resizes the single existing virtual display and discards stale inference results. Samsung behavior still requires device testing.

## Privacy

The detector has no network operations. The INTERNET permission is used solely by the optional browser. Screen frames and imported originals remain in memory; no telemetry or automatic recording. Exports go only to a destination selected with Android's document picker. No accessibility service, boot receiver, device administrator or hidden restart behavior.

## Verification status

See the [validation record](validation.md) for completed build and model checks. Emulator and physical-device verification are pending.
