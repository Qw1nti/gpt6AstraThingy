# Version 0.3 implementation plan

User phone testing confirmed installation and basic UI, but reported choppy tracking and dense-scene/video struggles. Screenshots show Ultra, a 20% threshold, most categories enabled and a 64 ms last scan.

## Changes

- Reuse RGBA capture buffers and close each acquired image before inference. Ultra processes the newest available frame without an additional 100 ms throttle; browser scanning schedules from completion rather than busy-polling.
- Keep every post-NMS detection. Batch crowded overlay regions into at most 16 windows while drawing each exact region; reuse windows and skip unchanged layouts.
- Track same-category regions across frames, estimate bounded motion and hold a missed detection briefly. Reset on capture/layout/navigation changes. Short predictions are an approximation, not video tracking ground truth.
- Extend existing coverage preference to negative values, down to -40% per edge (20% original width/height), while preserving old positive settings.
- Append Custom image and Pixelated + border styles without renumbering existing preferences. Copy a bounded static image into private storage. Draw it over an opaque base; create real pixelation from a downsampled captured/source frame, then draw a configurable highlighted border.
- Use the same rendering for screen overlays, browser, preview and exported photos. Never save captured frames automatically.

## Verification

Run geometry tests plus dense-scene, contraction, grouping and motion regression tests. Build and lint on CI. Device checks remain required for measured FPS, video coverage, motion accuracy, custom-image persistence and exported pixelation.
