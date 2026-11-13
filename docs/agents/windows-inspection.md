# Windows course inspection from WSL2

This project always runs under WSL2. Run the original course on the Windows
host using the checked-in helper `scripts/windows-course.ps1`. It provides
launch, window inspection, background screenshots, background clicks, and close.
No Wine, Linux desktop, or extra desktop-control service is needed.

## Tool execution

Run Windows PowerShell calls using `exec_command` with
`sandbox_permissions="require_escalated"` from the first attempt, retaining the
normal approval process. Without it, this environment produced:

```text
WSL ... ERROR: UtilBindVsockAnyPort:307: socket failed 1
```

The same invocation works outside the sandbox. Escaping the sandbox does not
require Windows administrator elevation. PowerShell runs in the signed-in
Windows user's desktop session.

Use the repo as the working directory and `wslpath -w` for paths. Windows can
read both the helper and executable directly through WSL UNC paths, and write
screenshots directly into WSL `/tmp`. Discover paths each time; do not hardcode
the distro name, display size, PID, or window handle.

## Launch and identify the course

```bash
powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass \
  -File "$(wslpath -w "$PWD/scripts/windows-course.ps1")" \
  -Action Launch -CourseExe "$(wslpath -w "$PWD/course.exe")"
```

`Launch` starts the course or reuses an existing matching process, and reports
the PID, visible window title, and bounds. Record whether this invocation started
or reused the instance. Startup can briefly show the title `course`; the settled
title is `A Short Course in Digital Audio`. Wait for startup to finish before
judging the initial screenshot.

**Director's reported main window is misleading.** `Process.MainWindowHandle`
can refer to a tiny launcher far offscreen. The helper enumerates top-level
windows owned by the matching course process, filters for visible windows that
intersect a display, and chooses the largest. This selects the actual course
stage. It refuses ambiguous multiple matching processes.

## Capture and view, without taking focus

```bash
powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass \
  -File "$(wslpath -w "$PWD/scripts/windows-course.ps1")" \
  -Action Capture -CourseExe "$(wslpath -w "$PWD/course.exe")" \
  -OutputPath "$(wslpath -w /tmp/syntrillium-course.png)"
```

Open `/tmp/syntrillium-course.png` with the agent's `view_image` tool. Capture
uses `PrintWindow` with full-content rendering. It works while another app covers
the course and does not request foreground focus. The user can continue using
other apps. Keep the course open and restored rather than minimized, on an
unlocked Windows desktop. Launching it initially can bring up its window.

**DPI matters.** Director's background rendering uses DPI-virtualized pixels.
The helper deliberately uses that coordinate space for background capture and
input. On the verified host, background captures were 506×404 while foreground
captures were 633×505. Making the capture process DPI-aware for `PrintWindow`
produced a scaled image with black padding; do not reintroduce that change.
Always obtain click coordinates from a fresh screenshot in the same capture mode.

Inspect actual images rather than treating a successful API return as proof of
correct rendering. Navigation includes animated transitions: an immediate image
can show partially positioned text. Allow roughly 1–2 seconds for menu transitions
and capture again if necessary. For lesson animations, capture successive states
and record when/where they were taken.

## Navigate with background clicks

```bash
powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass \
  -File "$(wslpath -w "$PWD/scripts/windows-course.ps1")" \
  -Action Click -CourseExe "$(wslpath -w "$PWD/course.exe")" -X 394 -Y 185
```

`X` and `Y` are relative to the top-left pixel of the latest window screenshot,
including its title bar. The helper recomputes window position, converts to
client coordinates, then posts mouse-move/down/up messages directly to the
course window. It neither calls `SetCursorPos` nor requests focus in background
mode. It rejects coordinates outside the window.

Verified navigation at the observed 506×404 background size:

| Starting screen | Target | X | Y | Result |
| --- | --- | --- | --- | --- |
| Main menu | Jump to topic | 394 | 185 | Topic menu |
| Topic menu | Sound Fundamentals | 394 | 110 | Lesson playback |

These are examples, not universal constants. Capture and inspect the current
screen before input, especially after resizing or changing display scaling.
After a click, capture again to confirm the intended transition.

To inspect accessibility, use the same invocation with `-Action Inspect` and
omit click/output arguments. The stage exposes **zero direct UI Automation
children** in the verified run: its navigation is drawn by Director. Use the
screenshot/message workflow rather than searching indefinitely for native buttons.

## Explicit foreground fallback

Add `-Foreground` to `Capture` or `Click` only when the background method fails
and the user is prepared for an interruption. This uses DPI-aware physical pixel
coordinates, `CopyFromScreen`, and actual cursor input. The helper brings the
course forward and verifies focus. Keep its window unobscured and fully onscreen.
Take a new foreground screenshot before selecting click coordinates; background
coordinates do not transfer to this mode.

Foreground capture, topic navigation, lesson playback, and pause were also
verified. At the observed 633×505 foreground size, the bottom-right pause button
was at approximately (555,473); clicking it changed the pause icon to a play icon.
Use background operation by default so the user can continue working.

## Close and clean up

```bash
powershell.exe -NoLogo -NoProfile -NonInteractive -ExecutionPolicy Bypass \
  -File "$(wslpath -w "$PWD/scripts/windows-course.ps1")" \
  -Action Close -CourseExe "$(wslpath -w "$PWD/course.exe")"
```

`Close` posts `WM_CLOSE` to the course window and waits up to five seconds for
process exit, reporting failure if it remains running. Close an instance started
for the inspection; ask before closing an instance that was already in use.
Keep exploratory screenshots in `/tmp`; preserve the original executable.

## Verification record

Exercised against this repository's original executable on 2026-11-12:

- Invoked Windows PowerShell 5.1 from WSL2 outside the sandbox.
- Read the executable and helper through WSL paths; wrote PNGs back into WSL.
- Launched the course, identified its real stage, and inspected its UI Automation
  tree. Resolved the hidden-main-window and DPI issues described above.
- Captured and visually opened the main menu, topic menu, and lesson content.
- Entered Sound Fundamentals and captured successive changing animation states.
- Tested background capture with a temporary covering window, and background
  navigation into the topic menu and lesson. In the menu-navigation test, the
  covering window retained foreground focus throughout. A concurrent user can
  change focus/cursor position; that alone does not indicate helper interference.
- Tested foreground navigation and pause, then implemented background operation
  as the default to avoid interfering with other apps.
- Closed the launched instance and confirmed process exit.

Selected visual evidence is stored under `docs/reference/windows-inspection/`:
[main menu](../reference/windows-inspection/main-menu.png),
[topic menu](../reference/windows-inspection/topics.png), and
[lesson animation](../reference/windows-inspection/lesson.png).
This workflow establishes visual inspection and navigation; listening to or
recording narration is a separate task.

## Bounded recovery

For the WSL socket error, check sandbox escalation before changing WSL settings.
For path failures, check `wslpath -w` conversion and Windows `Test-Path`.
For no visible window, inspect startup/dialog state and restore a minimized
course. For a partial transition image, allow the animation to settle and capture
again. If background rendering fails, try the explicit foreground fallback once;
avoid installing unrelated tools or repeatedly changing system configuration.
Report a persistent blocker with the exact bounded error and smallest next step.
