# Usage and limitations

## Use it on your phone

1. Open **Veil** and tap **Start protection**.
2. Enable **Appear on top** for Veil when directed, then return and tap Start again.
3. Allow notifications so the Stop action is readily available.
4. In Android's capture picker choose **one app**, then the app to filter. Keep that app full screen.
5. Scroll outside censor boxes. The boxes consume touches. Crowded scenes batch boxes into shared windows, whose transparent gaps can also consume touches.
6. Stop from the notification, the Android capture indicator, or Veil's **Stop protection** button.

Start with Medium performance and the default categories. Lower the detection threshold to catch more regions at the cost of more false positives. Ultra removes the old 100 ms scan throttle; detection speed still limits updates. Use vertical adjustment only if boxes are consistently offset. Cross-app alignment on Samsung and fold/rotation changes requires device verification.

For the in-app browser or photo tool, use the Browser and Export navigation tabs; these stop an existing cross-app session. They do not require screen capture or overlay permission.

## Practical limitations

- This is an initial implementation, not a verified one-to-one replacement for the commercial app.
- Detection occurs **after** a frame is visible. It cannot guarantee no exposure, no false positives, or no missed regions.
- Select **one app**, not the entire screen. Entire-screen mode can see the masks themselves and produce feedback/flicker. Android does not provide a reliable public flag identifying the user's selected mode to reject it after consent.
- Split screen, freeform windows, unusual insets, keyboards and some edge-to-edge layouts can misalign cross-app masks. Capture gives image dimensions, not another app's screen origin.
- Apps can hide overlays. Secure/DRM video and protected windows cannot be scanned. A black captured frame is not proof of safe content.
- The built-in browser draws WebView page content for detection. Hardware-backed video, WebGL and fullscreen media may not appear in that bitmap. It is a basic browser, not a guaranteed safe browser.
- No incognito mode, ad blocker, achievements, popup storms, custom image packs, eye-specific detection, translations, or direct censored browser downloads are included.
- Photo exports are limited to a longest edge of 2048 pixels to bound memory usage. Review output before sharing.
- Locking the phone, revoking permission, Android stopping capture, or an inference failure ends screen protection. There is no hidden automatic restart.
- A debug APK is for personal testing. Different build machines may use different debug signing keys; installing one over another can fail. Keep the same signing key for stable future updates. Do not uninstall a prior build without exporting anything you need from it.

## Privacy

Inference is local. The model is bundled by the build. The detector never sends frames to a server. There is no telemetry, automatic screenshot saving, background recording, accessibility service, startup receiver, or device-administrator permission.

The optional browser uses the Internet and visits your requested sites; those sites can receive normal browser traffic and store cookies. It is not incognito. Android WebView Safe Browsing is enabled. Photos and captured frames are kept in memory; an exported PNG is written only to the destination you choose.


## Version 0.3 styles and coverage

Select **Custom image** or **Pixelated + border** under Settings → Censor Style. **Choose custom image** imports a static image (up to 512 px on its longest edge) into app-private storage and selects that style. Replace/remove controls manage it. Transparent artwork is drawn over black so it cannot create holes in the mask.

Pixelated style uses a coarse copy of the captured frame or imported photo, with a highlighted border. Increase **Pixel block size** for coarser blocks and choose **Pixelated border color** independently from the standard mask color. If a pixelated frame is unavailable, the region is filled black with its border. WebView hardware video still requires the screen-capture path for testing.

Coverage now ranges from **−40% to +70% per edge**. At 0%, the original detected box is used. At −40%, its width and height are each 20% of the detected size. Shrinking intentionally reveals more around the center; inspect the result. Existing saved coverage values and style indexes remain valid.

Short motion prediction is bounded to 80 ms and 20% of box size. Brief missed detections may remain visible for up to 120 ms after their capture timestamp. These approximations may overshoot sudden direction changes and do not provide guaranteed video censoring.
