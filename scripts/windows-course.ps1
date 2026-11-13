param(
    [ValidateSet('Probe', 'Launch', 'Inspect', 'Capture', 'Click', 'Close')]
    [string]$Action = 'Probe',
    [Parameter(Mandatory = $true)][string]$CourseExe,
    [string]$OutputPath,
    [int]$X = -1,
    [int]$Y = -1,
    [switch]$Foreground
)
$ErrorActionPreference = 'Stop'
Add-Type @'
using System;
using System.Text;
using System.Runtime.InteropServices;
public static class CourseDesktop {
    public delegate bool Callback(IntPtr hwnd, IntPtr parameter);
    public struct RECT { public int Left, Top, Right, Bottom; }
    public struct POINT { public int X, Y; }
    [DllImport("user32.dll")] public static extern bool SetProcessDPIAware();
    [DllImport("user32.dll")] public static extern bool EnumWindows(Callback callback, IntPtr parameter);
    [DllImport("user32.dll")] public static extern uint GetWindowThreadProcessId(IntPtr hwnd, out uint processId);
    [DllImport("user32.dll")] public static extern bool IsWindowVisible(IntPtr hwnd);
    [DllImport("user32.dll")] public static extern bool IsIconic(IntPtr hwnd);
    [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr hwnd, out RECT rect);
    [DllImport("user32.dll", CharSet=CharSet.Unicode)] public static extern int GetWindowText(IntPtr hwnd, StringBuilder text, int count);
    [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hwnd);
    [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
    [DllImport("user32.dll")] public static extern bool SetCursorPos(int x, int y);
    [DllImport("user32.dll")] public static extern void mouse_event(uint flags, uint x, uint y, uint data, UIntPtr extra);
    [DllImport("user32.dll")] public static extern bool PostMessage(IntPtr hwnd, uint message, IntPtr wparam, IntPtr lparam);
    [DllImport("user32.dll")] public static extern bool PrintWindow(IntPtr hwnd, IntPtr hdc, uint flags);
    [DllImport("user32.dll")] public static extern bool ScreenToClient(IntPtr hwnd, ref POINT point);
}
'@
# Director renders PrintWindow in DPI-virtualized pixels. Match that coordinate
# space for background capture/input; use physical pixels for foreground capture.
if ($Foreground) { $null = [CourseDesktop]::SetProcessDPIAware() }
Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName UIAutomationClient
Add-Type -AssemblyName UIAutomationTypes
if (-not (Test-Path -LiteralPath $CourseExe)) { throw "Executable inaccessible: $CourseExe" }
if ($Action -eq 'Probe') {
    "PowerShell: $($PSVersionTable.PSVersion)"
    "Windows session: $([Diagnostics.Process]::GetCurrentProcess().SessionId)"
    "Primary display: $([Windows.Forms.Screen]::PrimaryScreen.Bounds)"
    return
}
$courseInstances = @(Get-Process -Name course -ErrorAction SilentlyContinue |
    Where-Object { $_.Path -eq $CourseExe })
if ($courseInstances.Count -gt 1) { throw 'Multiple matching course processes; resolve ambiguity first.' }
$course = $courseInstances | Select-Object -First 1
if (-not $course -and $Action -eq 'Launch') {
    $course = Start-Process -FilePath $CourseExe -WorkingDirectory (Split-Path -Parent $CourseExe) -PassThru
    try { $null = $course.WaitForInputIdle(10000) } catch {}
    "Started course PID: $($course.Id)"
} elseif (-not $course) {
    throw 'Launch the course first.'
} elseif ($Action -eq 'Launch') {
    "Reusing course PID: $($course.Id)"
}
$windows = [Collections.Generic.List[object]]::new()
$callback = [CourseDesktop+Callback]{ param($handle, $parameter)
    [uint32]$ownerPid = 0
    $null = [CourseDesktop]::GetWindowThreadProcessId($handle, [ref]$ownerPid)
    if ($ownerPid -eq $course.Id -and [CourseDesktop]::IsWindowVisible($handle)) {
        $rect = New-Object CourseDesktop+RECT
        $null = [CourseDesktop]::GetWindowRect($handle, [ref]$rect)
        $title = New-Object Text.StringBuilder 512
        $null = [CourseDesktop]::GetWindowText($handle, $title, 512)
        $bounds = [Drawing.Rectangle]::FromLTRB($rect.Left, $rect.Top, $rect.Right, $rect.Bottom)
        if ($bounds.Width -gt 0 -and $bounds.Height -gt 0 -and
            $bounds.IntersectsWith([Windows.Forms.SystemInformation]::VirtualScreen)) {
            $windows.Add([pscustomobject]@{
                Handle = $handle; Title = $title.ToString(); Bounds = $bounds
                Area = [long]$bounds.Width * $bounds.Height
            })
        }
    }
    return $true
}
$null = [CourseDesktop]::EnumWindows($callback, [IntPtr]::Zero)
$window = $windows | Sort-Object Area -Descending | Select-Object -First 1
if (-not $window) { throw 'No onscreen course window; check startup dialogs or restore its window.' }
"Course PID: $($course.Id); window: $($window.Title); bounds: $($window.Bounds)"
if ($Action -eq 'Launch') { return }
if ($Action -eq 'Inspect') {
    $root = [Windows.Automation.AutomationElement]::FromHandle($window.Handle)
    $root.Current | Select-Object Name, ClassName, BoundingRectangle
    $children = $root.FindAll([Windows.Automation.TreeScope]::Children, [Windows.Automation.Condition]::TrueCondition)
    "Direct UI Automation children: $($children.Count)"
    for ($index = 0; $index -lt [Math]::Min(30, $children.Count); $index++) {
        $children[$index].Current | Select-Object Name, AutomationId, ControlType, BoundingRectangle
    }
    return
}
if ($Action -eq 'Close') {
    if (-not [CourseDesktop]::PostMessage($window.Handle, 0x0010, [IntPtr]::Zero, [IntPtr]::Zero)) {
        throw 'Could not send WM_CLOSE.'
    }
    if (-not $course.WaitForExit(5000)) { throw 'Close sent, but course did not exit within 5 seconds.' }
    "Closed course PID: $($course.Id)"
    return
}
if ([CourseDesktop]::IsIconic($window.Handle)) { throw 'Restore the course window first.' }
if ($Foreground) {
    $null = [CourseDesktop]::SetForegroundWindow($window.Handle)
    Start-Sleep -Milliseconds 300
    if ([CourseDesktop]::GetForegroundWindow() -ne $window.Handle) {
        throw 'Course did not become foreground; bring it forward before retrying.'
    }
}
$currentRect = New-Object CourseDesktop+RECT
$null = [CourseDesktop]::GetWindowRect($window.Handle, [ref]$currentRect)
$bounds = [Drawing.Rectangle]::FromLTRB($currentRect.Left, $currentRect.Top, $currentRect.Right, $currentRect.Bottom)
if ($Action -eq 'Click') {
    if ($X -lt 0 -or $Y -lt 0 -or $X -ge $bounds.Width -or $Y -ge $bounds.Height) {
        throw 'X/Y must be within the latest screenshot, relative to its top-left pixel.'
    }
    if ($Foreground) {
        if (-not [CourseDesktop]::SetCursorPos($bounds.Left + $X, $bounds.Top + $Y)) { throw 'Cannot position cursor.' }
        [CourseDesktop]::mouse_event(0x0002, 0, 0, 0, [UIntPtr]::Zero)
        [CourseDesktop]::mouse_event(0x0004, 0, 0, 0, [UIntPtr]::Zero)
    } else {
        $point = New-Object CourseDesktop+POINT
        $point.X = $bounds.Left + $X
        $point.Y = $bounds.Top + $Y
        if (-not [CourseDesktop]::ScreenToClient($window.Handle, [ref]$point)) { throw 'Cannot map click to client coordinates.' }
        $position = [IntPtr](($point.Y -shl 16) -bor ($point.X -band 0xffff))
        foreach ($message in @(0x0200, 0x0201, 0x0202)) {
            $button = if ($message -eq 0x0201) { [IntPtr]1 } else { [IntPtr]::Zero }
            if (-not [CourseDesktop]::PostMessage($window.Handle, $message, $button, $position)) { throw 'Cannot post mouse message.' }
        }
    }
    "Clicked window-relative pixel: $X,$Y"
    return
}
if (-not $OutputPath) { throw 'Capture requires OutputPath.' }
$bitmap = New-Object Drawing.Bitmap($bounds.Width, $bounds.Height)
$graphics = [Drawing.Graphics]::FromImage($bitmap)
try {
    if ($Foreground) {
        $graphics.CopyFromScreen($bounds.Left, $bounds.Top, 0, 0, $bitmap.Size)
    } else {
        $deviceContext = $graphics.GetHdc()
        try {
            if (-not [CourseDesktop]::PrintWindow($window.Handle, $deviceContext, 2)) { throw 'PrintWindow failed.' }
        } finally {
            $graphics.ReleaseHdc($deviceContext)
        }
    }
    $bitmap.Save($OutputPath, [Drawing.Imaging.ImageFormat]::Png)
} finally {
    $graphics.Dispose()
    $bitmap.Dispose()
}
"Saved: $OutputPath"
