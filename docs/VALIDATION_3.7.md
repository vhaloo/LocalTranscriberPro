# Validation 3.7.1

The English gallery uses eight actual Windows captures with demonstration data. The low-memory catalogue shows a simulated 4 GB profile.

The Windows source suite passed **307 tests**. The real Tk fixture checks reselecting a task, conditional translation controls, exact-code language selection, restoration of wizard modality, microphone review and retained preferences. The release check validates the eight gallery entries and all five download links. GitHub source checks cover Windows, macOS and Linux.

## Packages

The application and installer inputs are frozen at `0686f16f38b06dff5e9518dd03b0d7cda2f85816`.

| Build | Evidence | Runtime cases |
|---|---|---:|
| windows | [Run 42401553744](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/42401553744) | 6/6 |
| windows_cpu | [Run 42401563628](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/42401563628) | 6/6 |
| macos | [Run 42401574221](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/42401574221) | 6/6 |
| linux | [Run 42401587042](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/42401587042) | 6/6 |

Both Windows installers were installed and exercised in CI. The exact macOS DMG and Linux AppImage/archive passed their mounted or extracted runtime checks in [run 42405047589](https://github.com/vhaloo/LocalTranscriberPro/actions/runs/42405047589). **48 native checks** passed across build, installer and container checks. All five binary assets were verified by SHA-256 and the Ed25519 release manifest.

## Installed Windows update

The signed candidate installed once through the updater in the existing installation directory. The test used the release files through a local transport, with **63.0 seconds of real inactivity**, the installer wait for the previous process and the actual relaunch. The installed executable matches the one exercised by Windows CI. **7 runtime checks** passed on the installed copy, including offline automatic selection of Whisper large-v3 on CPU.

The update preserved 84 existing sessions, 279 output files, settings, recovery and shortcuts. SQLite integrity, logical records and timestamps were compared after relaunch.

macOS and Linux remain experimental for physical installation, microphones and GPU/display use. [Previous 3.7.0 validation](https://github.com/vhaloo/LocalTranscriberPro/blob/v3.7.0/docs/VALIDATION_3.7.md)
