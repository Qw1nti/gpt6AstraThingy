# Version 0.4 design and implementation plan

Requested 10 September 2026: simplify style settings and strengthen the original Android Beta Blocker theme.

## Scope

- Keep the established near-black plum background, rounded charcoal cards, hot-pink selection and lime primary actions, informed by the original public Home screenshot.
- Put an inline simulated censor preview and six explicit style choices first in Settings.
- Show only the selected style's color, image, pixelation or text options. Preserve stored values when switching styles.
- Move category selection and advanced detection tuning into expandable sections.
- Give coverage a clear zero point, one-percent adjustments and a reset to detected size.
- Retain the existing detection, tracking, screen capture, overlay rendering and model settings. No runtime optimization or new detector is part of this update.
- Keep the five-tab navigation and Veil identity. This is a reference-inspired UI update, not a claim of exact visual parity.

## Validation gate

Compile and lint the APK, retain the geometry/model/rendering suites, and exercise actual Settings views on Android: style-specific visibility, preference retention, live preview, precise coverage and recreation. Capture native screenshots for compact and expanded widths and review their layout before delivery. Existing phone success belongs to 0.3; 0.4 still needs owner confirmation.
