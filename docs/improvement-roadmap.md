# Improvement review after the successful 0.3 phone test

Reviewed 8 September 2026. Baseline: version 0.3.0, commit `38144c59fd1b0543a647a6cd2a12ec8150f758e2`.

The owner reports: “It works very well now.” Preserve this working baseline. The recommendations below are proposals for later consideration. This review changes documentation only and does not authorize implementation.

## What is working

| Area | Evidence | What the evidence does not establish |
| --- | --- | --- |
| Overall phone experience | Owner reports that 0.3 works very well after installing the update. | No separate result was supplied for every style, export flow, fold transition or long session. |
| Build and static checks | [CI run 34285010350](https://github.com/Qw1nti/gpt6AstraThingy/actions/runs/34285010350) passed compilation, lint and model contract checks. | No measured battery, temperature or recognition accuracy result. |
| Tracking and coverage geometry | 216 new checks cover dense detections, grouping, shrinking and motion, alongside the existing geometry and inverse-mask suites. | Synthetic boxes do not measure real-video detection accuracy. |
| New graphics paths | All four Android 15 instrumentation tests passed: pixelation/border, opaque custom-image backing, private bounded image import and reusable capture-buffer colors. | These tests do not cover the complete Settings UI or end-to-end screen projection. |
| Available features | Source includes negative coverage, one imported static image and pixelation with adjustable blocks and border color. | Persistence across every Android lifecycle transition has not been demonstrated. |

No new phone failure is claimed in this review. “Source risk” means behavior inferred from the code that needs targeted reproduction. “Proposal” means a possible improvement, not a defect.

## Recommended order

| Order | Recommendation | Why it is worthwhile | Effort / risk |
| --- | --- | --- | --- |
| 1 | Record a repeatable performance baseline and optional diagnostics. | Establish whether another optimization actually helps the Fold. | Medium / low if metrics stay local and opt-in. |
| 2 | Simplify style settings and add precise coverage controls. | The new options make Settings long and some controls apply only to particular styles. | Small to medium / low. |
| 3 | Restore browser and photo state across recreation. | Protect work during rotation, folding, navigation and Android process recovery. | Medium / medium. |
| 4 | Adapt the layout to folded and unfolded widths. | Use the Fold's inner display without stretching every card and button. | Medium / medium. |
| 5 | Add user-saved looks and better custom-image positioning. | Make favorite combinations easy to reuse. | Medium / medium. |
| 6 | Optimize only the bottleneck established by measurements. | Avoid disrupting tracking that now works well. | Depends on the measured issue. |

Effort estimates are relative, not delivery promises. Items 1–3 are the strongest candidates for the next small update if implementation is requested later.

## Optimization opportunities

### Measure visible delay, not just the last scan

**Source finding:** `ProtectionService.frame()` measures from frame acquisition through copy, inference and pixel-texture creation. `lastMs` stops before the main-thread overlay update and display presentation. It also excludes delay before acquisition. Therefore “64 ms last scan” is not a complete measure of what the viewer experiences.

**Proposal:** collect rolling median and 95th-percentile timings for capture/copy, inference, mask preparation and UI submission; track processed frames per second, pending results, active windows and allocation/GC activity. Keep submission timing distinct from actual display latency. An optional copyable diagnostics report could include app version, device, settings and timing summaries without captured images, browsing addresses or custom-image contents.

**Acceptance:** repeat the same benign static scene, moving-face clip and crowded clip with identical categories, confidence, style and coverage. Compare folded/unfolded screens and cold versus sustained sessions, with brightness and charging state held consistent. Record heat and battery observations separately from precise energy measurements. Android system tracing can help investigate UI jank [1]. No FPS or battery improvement is currently quantified.

### Keep only the newest pending overlay result, if a queue is observed

**Source risk:** every completed screen inference posts a new UI callback. The generation check rejects results from an old capture state but does not coalesce multiple results within the same generation. Under a busy UI thread, pending results could increase visible delay. No backlog has been measured on this phone.

**Proposal:** if traces confirm this, allow one pending render task whose payload is replaced by the latest result. Explicitly manage bitmap ownership and preserve stop/resize handling.

**Acceptance:** under intentional UI load, pending work stays bounded, the newest scene wins, and stop/resize never displays an old result. Compare coverage continuity as well as timing.

### Tune runtime work and allocations only after profiling

**Source finding:** `Detector` uses two inference threads, wraps a float array for each tensor and materializes model output as nested arrays. `MaskView` creates a coarse bitmap for each pixelated frame; tracking and grouping also allocate collections. Several large capture and preprocessing buffers are already reused.

**Proposal:** profile these sites before considering reusable direct tensor buffers, less output copying or texture pooling. Benchmark alternative CPU thread counts on the Fold. ONNX Runtime exposes threading controls, but additional threads are not an automatic speed improvement [2]. Any accelerator experiment needs a separate compatibility and output-parity check with the current model and runtime; no GPU/NPU speedup is assumed.

**Acceptance:** lower sustained latency or allocation pressure without changed boxes, lost masks, resource leaks or increased heat. Do not recycle textures while a view can still draw them.

### Consider an optional automatic performance mode

**Source finding:** Low/Medium/High/Ultra use fixed minimum scan intervals of 350/150/66/0 ms. The model input remains 320 × 320. These choices do not change model resolution, and Ultra does not impose an extra wait.

**Proposal:** only if long-session measurements justify it, add Auto pacing that adjusts gradually to processing time and thermal pressure. Preserve manual presets and explain the current behavior in plain language.

**Acceptance:** compare sustained sessions with Ultra and High. Auto should improve the chosen battery/heat objective without unacceptable extra delay or oscillating speed. Simply lowering capture resolution cannot be assumed to improve recognition, and increasing it does not increase the current model's input size.

## UI improvements

| Proposal | Current evidence | Completion check for a future change |
| --- | --- | --- |
| Show controls relevant to the selected style. | `MainActivity.settings()` always displays text, custom-image and pixelation controls. | Custom image shows thumbnail/replace/fit options; pixelation shows blocks/border; unrelated controls are hidden without losing their saved values. |
| Add a small inline style preview. | Preview currently opens a separate dialog. | Changes to color, blocks and image placement are immediately visible on a clearly labeled simulated region. It must not imply detection accuracy. |
| Add minus/plus buttons, numeric entry and Reset for coverage. | Both sliders support −40% to +70%, but touch dragging is the only adjustment method. | A user can set exactly 0% or a small negative value on the cover screen. Keep existing saved values compatible. |
| Explain coverage as box size. | Coverage is a margin on each side; −40% leaves 20% of the original width and height before clipping. | Show a simple size example or preview; avoid implying that −40% means a box is only 40% smaller. |
| Make Settings easier to scan. | Long stacked cards; English is a static single-language row. | Group into Detection, Appearance and Advanced; move single-language information to Help until language selection exists. Keep the plum/pink/lime identity. |
| Improve touch and text sizing. | Navigation labels are 11 sp, some supporting text is 12 sp and category controls have a 40 dp minimum height. | Larger targets, legible labels and no clipping at 100%, 130% and 150% font scale on both Fold screens. |
| Use a wider-screen layout when space permits. | The shared UI builds a single vertical content column and fixed five-item top navigation. | Keep the familiar compact layout on the cover display; consider settings beside the preview on the inner display. Adapt to actual window width [3]. |
| Clarify status and navigation effects. | Opening Browser or Export stops screen protection; Help still says the new styles need device testing. | Explain the switch in mode and report active, paused and stopped states consistently. Update Help wording in a later code change. |

Visual fidelity and usability are separate goals. Keep the established palette and familiar navigation by default. A new wide-screen layout or reorganized Settings would be an intentional design improvement, not evidence of closer pixel-for-pixel matching to the original app. The historical comparison remains in [UI comparison](ui-comparison.md).

## Reliability items to verify before larger features

| Source risk / known limitation | Recommended next action | Completion check |
| --- | --- | --- |
| `BrowserActivity` and `PhotoActivity` lack explicit restoration of their working session. | Preserve tab URLs/history as appropriate, selected tab, scroll state and a recoverable photo editing state. Use saved state for small identifiers and a deliberate persistence policy for image data [4]. | Rotate, fold/unfold, leave/return and recreate the process without unexpected loss; do not place full bitmaps in a saved-state bundle. |
| Dense groups contain transparent areas that still consume touches. | Reproduce impact on normal scrolling before changing the grouping algorithm. Evaluate smaller groups against the added window cost. | Improve interaction without missing masks or breaking Android overlay behavior. Do not assume transparent pixels automatically pass touches through. |
| Overlay placement assumes a centered full-screen captured area plus manual vertical adjustment. | Verify keyboard, orientation, app-bound changes and fold transitions. | Document supported layouts with observed alignment. Keep split-screen support a separate investigation. |
| The animation callback clears overlays after a runtime exception without reporting that exception to the service. | Add consistent failure reporting if this path is reproduced or addressed in a reliability pass. | A failed overlay cannot leave a misleading active status; recovery and Stop remain predictable. |
| Software capture of the built-in browser may omit hardware video or WebGL. | Retain clear routing to screen capture; investigate any browser-video feature separately. | Demonstrate representative supported playback. Do not promise support for protected video. |

## Optional features after the above

| Feature | Concrete scope | Tradeoff / future acceptance |
| --- | --- | --- |
| Saved looks | Name and recall combinations of categories, coverage, style, text, colors and custom image. | Start with local profiles; ensure profiles retain the intended image after the current image is replaced. Test save, rename, switch and delete. |
| Better custom-image controls | Thumbnail, crop/fit choice, focal-point adjustment and a small local image collection. | Preserve an opaque background, including for transparent images. Check tall, wide and small masks. |
| Border controls | Thickness, corner radius and optional border on custom-image masks. | Preview narrow boxes and cap geometry to avoid the border consuming the entire mask. |
| Per-category overrides | Optional size and style overrides for selected categories. | More settings and harder troubleshooting; inherit the global look unless explicitly overridden. |
| Manual photo corrections | Add, move, resize and remove regions before PNG export, with undo. | Keep the editing source and region model so corrections do not repeatedly degrade the image. Verify exported pixels match the preview. |
| Higher-quality photo export | Offer higher output resolution independently of detection input resolution. | The current decode cap is 2,048 px. Large exports need a memory budget; higher output size does not make the model more accurate. |
| Easier phone updates | Versioned releases and a consistent signing process, with clear update instructions. | Current delivery is a debug APK inside a CI artifact ZIP. Verify update-over-install preserves settings before promising seamless upgrades. |

Animated image masks, video-file export, a new detector and a language/framework rewrite are lower-priority ideas. They introduce substantially more processing or maintenance work than the immediate usability improvements. There is no evidence from this successful test that a Java-to-Kotlin rewrite is necessary.

## Evidence and boundaries

Source reviewed at the baseline commit: `MainActivity.java`, `Ui.java`, `Prefs.java`, `ProtectionService.java`, `Detector.java`, `OverlayController.java`, `BrowserActivity.java`, `PhotoActivity.java`, the existing rendering/tracking code and repository documentation. Local source hashes matched GitHub before this documentation edit. No new app build, phone session or performance benchmark was run for this review.

The owner report is evidence of a successful overall experience. It does not mark every item in [device tests](device-tests.md) as passed. Recommendations and effort estimates are engineering judgments based on the inspected implementation.

External references checked on 8 September 2026:

1. [Android: capture a system trace](https://developer.android.com/topic/performance/tracing/on-device) — investigation of UI and performance behavior.
2. [ONNX Runtime: thread management](https://onnxruntime.ai/docs/performance/tune-performance/threading.html) — configurable inference threading.
3. [Android: adaptive design with Views](https://developer.android.com/develop/ui/views/layout/responsive-adaptive-design-with-views) — layouts that respond to available space.
4. [Android: save UI states with Views](https://developer.android.com/topic/libraries/architecture/views/saving-states-views) — recovery after recreation and process death.
