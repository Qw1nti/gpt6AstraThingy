# Windows pipeline review — version 0.6

The approved Windows 11 interface is retained. Android runtime source is
untouched. Models, thresholds, input detail limits, crop coverage and NMS policy
are unchanged. Optimizations do not skip selected displays or categories.

## Behavior fixes

- A completed display previously waited for all remaining displays before its
  masks reached the UI. Each display now publishes after its own capture,
  inference and effects finish. A bounded mailbox retains the newest result for
  each display, so a busy UI cannot discard another display's update.
- Live settings could leave an old scan in flight and wait out the old interval.
  Policy revisions now cancel obsolete work between inference calls, reject old
  results, and wake interval waits. Disabled categories and newly excluded
  confidence scores are removed from held masks immediately. An ONNX call
  already running must still finish; it is not forcibly interrupted.
- The old 300–600 ms hold expired between scans at a 1000 ms interval, creating
  periodic gaps even for a static face. Hold duration now accounts for requested
  interval and observed per-display result cadence, bounded to 300–1500 ms after
  the last matching result. This trades a longer possible lingering mask on slow
  scans for continuity. Prediction stays capped at 120 ms; it does not
  extrapolate over the whole hold window.
- Late callbacks without an active sender are ignored during shutdown.

## Reduced work

- Moving masks use a precise 16 ms timer instead of 33 ms, without adding model
  scans. Repaints cover old/new mask areas rather than requesting a full-display
  repaint. The dirty alpha region is explicitly cleared to avoid trails; labels
  are clipped to their mask, and fractional scaling rounds coverage outward.
  Policy/source changes still request a full redraw. Windows composition cost
  can differ from Qt paint region size.
- Crowded-scene association searches neighboring spatial cells within the same
  existing 128-pixel gate. Position, size, category, sorting and one-to-one rules
  remain; there is no detection-count cap.
- Live blur/pixelation renders only the needed patch, avoiding intermediate
  image copies. Custom masks reuse identical output sizes in an LRU cache
  limited to 8 MiB per worker. Changing the imported image invalidates it. No
  raw screen frames are cached for this optimization.
- RGB-to-QImage conversion avoids a redundant RGB copy while retaining an owned
  QImage before thread delivery. Face/body float inputs are reused; padding is
  cleared when required. Tests compare body tensors and effect pixels to the
  previous rendering/preprocessing path.
- Required model sessions initialize before the first capture, so loading does
  not make that image stale. Cold startup still takes time. Home's scan work
  covers capture/inference/effects, excluding initialization, GUI delivery and
  Windows composition. Timing uses completed cycles of all selected displays,
  even though delivery is incremental.

## Local measurements

Run `PYTHONPATH=windows python windows/tests/benchmark_pipeline.py`. The fixture
uses a synthetic 3840×2160 RGB frame, 54 regions of 320×240, an identical 512×512
custom mask, and a separate 300-track fixture. One warm-up precedes eight timed
passes; values are median milliseconds on this Linux environment. The same
script was run before and after the changes. These are isolated component
costs, not screen scan rates, game FPS or owner-PC measurements.

| Component | Version 0.5 | Version 0.6, initial pass |
| --- | ---: | ---: |
| 300-region tracker setup + association | 84.263 ms | 6.037 ms |
| 54 pixelated patches | 20.930 ms | 16.504 ms |
| 54 custom-image patches, repeated size, warm cache | 252.637 ms | 0.017 ms |
| 54 Gaussian-blur patches | 136.626 ms | 143.051 ms |

A follow-up run measured 5.313 / 17.514 / 0.016 / 134.413 ms respectively.
Blur shows no consistent improvement; filtering dominates. The large custom
mask gain depends on cache hits. Changed sizes, cold caches, inference, capture,
display count and Windows composition still cost time. Crowds whose objects all
occupy neighboring cells gain less from the spatial search.

## Validation and remaining PC checks

Regression coverage includes early per-display delivery, coalescing across
displays, stale-policy rejection, notifications, cache memory/invalidation,
image ownership, preprocessing padding, partial-paint alpha clearing,
fractional geometry, slow-interval hold/expiry and spatial-boundary association.
The Windows workflow also runs real inference and the native moving-face
pipeline, including slow-interval continuity and expiry on a blank scene.

Actual video accuracy, capture-to-visible-mask latency, rapid scrolling and
direction changes, mixed DPI/multiple physical displays, CPU use, GPU composition
and long sessions still need owner-PC testing. A new face needs its first
detection. Motion prediction can be disabled if masks drift.
