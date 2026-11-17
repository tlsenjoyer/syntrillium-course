# Distribute the Russian adaptation as a desktop app

Learners should be able to install the course, launch it from the desktop app menu, and use every available lesson offline, including narration, captions, and visualizations. The desktop app is the sole supported learner distribution, and it may reuse the existing player.

Distribute the first release and subsequent updates as direct downloads for Windows, macOS, and Linux. A learner can transfer the downloaded package to a disconnected computer, install it, and launch the course. Each package includes all course media and any runtime components its supported operating system does not supply. Store distribution is optional.

Target Windows 11 on x64, macOS on Apple Silicon and Intel, and x64 Linux desktops running Ubuntu LTS, the latest stable Debian release, or current Arch Linux. Package the existing player with Electron. Its bundled Chromium increases the download size and gives the course a consistent rendering engine for narration and SVG animation across targets.

Paid code signing is outside the scope of all releases. Direct downloads may trigger operating-system warnings about the publisher.

On each platform, disconnect before installation and verify installation, first launch, complete lesson playback, and course navigation.
