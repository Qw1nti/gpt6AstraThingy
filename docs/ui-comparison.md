# Reference-led UI rebuild, version 0.2

Inspected the four actual app screenshots linked from the public product page using web and browser tools. The promotional lavender headings on the itch.io page are not the in-app theme. The in-app screens use a near-black plum background, dark charcoal-purple cards, hot-pink accents and green protection buttons.

## Recreated visible structure

| Reference area | Implemented structure |
| --- | --- |
| Main navigation | Five fixed top tabs: Home, Settings, Browser, Help, Export; line icons; pink active underline |
| Home | Screen Capture Protection card, green Start/Stop action, AI Censoring card, checkboxes, outlined style selector, quick toggles, performance selector, session status |
| Settings | Two pink action buttons, language row, two-column category checkboxes, style/color selectors, custom text and detection sliders |
| Browser | Shared tab bar, browser settings card, address field, green Go button, compact navigation row and dark branded homepage |
| Help | Permissions and battery card with pink actions; guide, troubleshooting and privacy cards |
| Export | Shared navigation, local image selection and PNG export |

Approximate design constants in `Ui.java`: 16 dp exterior/card padding, 15 dp card radius, 68 dp top navigation, 12 dp card gap, 48 dp action buttons, 16 sp card titles and 12–13 sp supporting text. Palette: #11000F, #191521, #FF0095 and #B9F45A. These values were visually estimated, not extracted from original source code.

## Intentional or remaining differences

- Veil keeps its own name/icon. No paid source, APK, original wordmark or artwork is bundled.
- The original Effects and packs area advertises Popup Storm and Packs. Veil uses the same two-button layout for working censor previews and built-in style presets; it does not pretend to include those original subsystems.
- English is currently the only language. No fake language selection menu.
- The model lacks an eye-only label; that original experimental checkbox is omitted. Some body-part categories are grouped differently.
- Donation links and creator support destinations were not copied into this independent app.
- The screenshot gallery does not expose all states or the complete Export interface, so unshown parts are independently designed.
- This is a closer visual reconstruction, not a demonstrated pixel-identical clone. The owner has since supplied native phone screenshots and reports that version 0.3 works very well. Exact visual parity, accessibility and all folded/unfolded layouts have not been verified.

## Reference URLs

- Page: https://isla2d.itch.io/beta-blocker-mobile
- Home: https://img.itch.zone/aW1hZ2UvNDQxNDMxNi8yNzc4ODYxNS5wbmc=/original/cuyeng.png
- Settings: https://img.itch.zone/aW1hZ2UvNDQxNDMxNi8yNzc4ODYxNy5wbmc=/original/dRc1q0.png
- Browser: https://img.itch.zone/aW1hZ2UvNDQxNDMxNi8yNzc4ODYyMi5wbmc=/original/%2BDugwO.png
- Help: https://img.itch.zone/aW1hZ2UvNDQxNDMxNi8yNzc4ODYyNC5wbmc=/original/mpQynt.png

## Follow-up design proposals

See the [0.3 improvement review](improvement-roadmap.md) for proposed simpler style controls, precise coverage adjustment, larger targets and an adaptive Fold layout. These are documented ideas; they have not changed the app or this historical reference comparison.
