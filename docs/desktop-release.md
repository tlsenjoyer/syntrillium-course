# Offline desktop release

Download the package for the classroom computer from
[GitHub Releases](https://github.com/tlsenjoyer/syntrillium-course/releases)
and copy it over before disconnecting. Electron and all nine lessons are
included. Install the package, then launch **Курс цифрового звука** from the
desktop app menu.

| Computer | Package | Offline installation |
| --- | --- | --- |
| Windows 11, x64 | `*-win-x64.exe` | Run the installer, then open the course from Start. |
| Mac, Apple Silicon | `*-mac-arm64.dmg` | Open the disk image, drag the app to Applications, and open it there. |
| Mac, Intel | `*-mac-x64.dmg` | Open the disk image, drag the app to Applications, and open it there. |
| Ubuntu LTS or Debian stable, x64 desktop | `*.deb` | From the package folder, run `sudo apt install --no-download ./syntrillium-course-*.deb`. |
| Arch Linux, x64 desktop | `*.pacman` | From the package folder, run `sudo pacman -U ./syntrillium-course-*.pacman`. |

Windows or macOS may show a publisher warning. Managed computers may require
administrator approval. Record any warning or block during release testing.
On macOS, after attempting to open the downloaded app, check **System Settings
→ Privacy & Security → Open Anyway** if Gatekeeper blocks it. See
[Apple's instructions](https://support.apple.com/en-us/102445).
Install updates by transferring and installing the later release for the same
platform and architecture.

The Linux packages rely on libraries supplied by the distribution. A fresh
Arch XFCE system can lack `nss`, which means the course package alone cannot
install there offline. Include the missing distribution packages in the
transfer and verify the full install on a clean desktop before publishing.

## Build the installers

Use Node.js 24 and run `npm ci`. For local review, use `npm start`. To build an
installer, run `npm run package --` with the matching arguments on its host OS.

| Build host | Arguments |
| --- | --- |
| Windows | `--win --x64` |
| Apple Silicon macOS | `--mac --arm64` |
| Intel macOS | `--mac --x64` |
| x64 Linux | `--linux --x64` |

The packages appear in `dist/`. The **Desktop packages** GitHub Actions workflow
builds the same files on demand and for `desktop-v*` tags. For a release,
update the version in `package.json` and `package-lock.json` with
`npm version <version> --no-git-tag-version`, commit it, and tag that commit
`desktop-v<version>`. Download the build artifacts, extract the installers, and
upload them as assets on a draft GitHub release for that tag. Publish the draft
after the transferred packages pass the checks below.

## Verify the transferred packages

Start each check on a fresh desktop with a sound output device and a clean
course profile. Disconnect before installing and stay offline through the
first launch from the app menu. Use the same files intended for release.

1. Open all nine lessons and play one complete lesson. Check audible Russian
   narration, caption visibility, diagram changes timed to the narration, and
   the final replay control. Test pause, seeking, and keyboard operation.
2. While lesson 2 plays, choose lesson 7 from the lesson list. Confirm lesson 2
   stops. **Назад** should return to lesson 2, **Вперёд** should revisit lesson 7,
   and **Предыдущий урок** should open lesson 6. Check the disabled course-order
   controls at lessons 1 and 9.
3. Record the exact OS version, architecture, installer filename, and each
   outcome in the release notes.

| Release check | Architecture | Result |
| --- | --- | --- |
| Windows 11 | x64 | Pending |
| macOS | arm64 | Pending |
| macOS | x64 | Pending |
| Ubuntu 26.04 LTS | x64 | Pending |
| Debian 13 stable | x64 | Pending |
| Current Arch Linux desktop | x64 | Pending |

### Local package check

On Omarchy 4.5.0 (Arch-based), kernel 7.2.15-1-omarchy, x64,
`syntrillium-course-0.1.0-linux-x64.pacman` installed into a temporary root
with only loopback networking. The check reused the host's dependency
database and skipped installer scriptlets. The installed desktop entry
launched the course. All nine lessons opened, and **Цифровой звук** played
through all three utterances at normal speed with an active audio stream.
Pause, seek, captions, keyboard operation, visualization changes, session
history, and course boundaries passed. The clean-desktop matrix above is
still pending.
