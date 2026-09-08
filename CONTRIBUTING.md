# Contributing

Keep changes small and tie fixes to a reproducible failure or a clearly described feature request.

## Workflow

1. Read the [architecture](docs/architecture.md) and [known issues](docs/known-issues.md).
2. Create a branch from current `main` and make a focused change.
3. Run `python3 scripts/test_core.py` for geometry changes. Run the model smoke test when model loading or preprocessing changes.
4. Run `./gradlew :app:assembleDebug :app:lintDebug` after fetching the model. On Windows use `.\gradlew.bat`.
5. Open a pull request explaining the problem, change and actual validation. Let CI finish before merging.

Use JDK 17, Gradle 8.11.1 through the wrapper, and Android SDK 35. See [README.md](README.md) for setup. CI model dependencies live in `requirements-ci.txt`.

## Change boundaries

- Preserve model checksum verification and upstream notices.
- Do not commit APKs, model weights, local SDK paths, IDE state or signing keys. Generated model assets and build outputs are ignored.
- Keep app behavior changes separate from repository/tooling maintenance when possible.
- Do not describe parser checks, desktop model inference or APK compilation as successful device testing.
- For UI and lifecycle fixes, document the tested Android version, device/emulator, orientation and relevant screenshots or logs. Update the [validation record](docs/validation.md) when verification advances.

## Reporting bugs

Use the bug-report template. Include the commit or build-run URL, reproduction steps, expected and actual behavior, Android version and sanitized logs. Benign fixtures or synthetic detector outputs are preferred when they reproduce the issue. Omit personal browsing data and private images.
