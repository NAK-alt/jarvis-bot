import subprocess
import os
import tempfile
import time
import glob
import pyautogui
from PIL import Image
import pyperclip
import mss

# Disable PyAutoGUI fail-safe pause for faster tool execution
pyautogui.FAILSAFE = False

# Track media/file output to be sent via Telegram
LAST_SCREENSHOT_PATH = None
PENDING_FILES_TO_SEND = []

def run_powershell(command: str) -> str:
    """Execute a Windows PowerShell command and return the terminal output.
    
    Args:
        command: The PowerShell command to run (e.g., 'Get-Process', 'dir', 'ipconfig').
    """
    try:
        process = subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            shell=False
        )
        stdout, stderr = process.communicate(timeout=60)
        output = stdout.strip()
        if stderr.strip():
            output += f"\n[Errors/Warnings]:\n{stderr.strip()}"
        if not output:
            output = "Command executed successfully (no output returned)."
        # Trim output if too long
        if len(output) > 2500:
            output = output[:2500] + "\n...[Output truncated]..."
        return output
    except subprocess.TimeoutExpired:
        return "Error: Command execution timed out after 60 seconds."
    except Exception as e:
        return f"Error executing PowerShell: {str(e)}"

def take_screenshot() -> str:
    """Capture a screenshot of the current active screen on the computer and prepare it to be sent to Telegram."""
    global LAST_SCREENSHOT_PATH
    temp_dir = tempfile.gettempdir()
    screenshot_path = os.path.join(temp_dir, f"jarvis_screen_{int(time.time()*1000)}.png")
    
    # Method 1: Try MSS
    try:
        with mss.mss() as sct:
            sct.shot(mon=-1, output=screenshot_path)
            if os.path.exists(screenshot_path) and os.path.getsize(screenshot_path) > 0:
                LAST_SCREENSHOT_PATH = screenshot_path
                return f"Screenshot captured successfully: {screenshot_path}"
    except Exception:
        pass

    # Method 2: Try PyAutoGUI / PIL
    try:
        screenshot = pyautogui.screenshot()
        screenshot.save(screenshot_path)
        if os.path.exists(screenshot_path) and os.path.getsize(screenshot_path) > 0:
            LAST_SCREENSHOT_PATH = screenshot_path
            return f"Screenshot captured successfully: {screenshot_path}"
    except Exception:
        pass

    # Method 3: PowerShell .NET fallback
    try:
        ps_script = f"""
        Add-Type -AssemblyName System.Windows.Forms,System.Drawing
        $bounds = [System.Windows.Forms.Screen]::PrimaryScreen.Bounds
        $bmp = New-Object System.Drawing.Bitmap $bounds.Width, $bounds.Height
        $g = [System.Drawing.Graphics]::FromImage($bmp)
        $g.CopyFromScreen($bounds.Location, [System.Drawing.Point]::Empty, $bounds.Size)
        $bmp.Save('{screenshot_path.replace(os.sep, "/")}', [System.Drawing.Imaging.ImageFormat]::Png)
        $g.Dispose()
        $bmp.Dispose()
        """
        run_powershell(ps_script)
        if os.path.exists(screenshot_path) and os.path.getsize(screenshot_path) > 0:
            LAST_SCREENSHOT_PATH = screenshot_path
            return f"Screenshot captured successfully: {screenshot_path}"
    except Exception as e:
        return f"Could not capture screenshot (desktop session might be locked or inactive): {str(e)}"

    return "Screenshot capture failed: Screen buffer could not be accessed."

def open_application_or_url(target: str) -> str:
    """Open an application, website URL, or file on the Windows PC.
    
    Args:
        target: The name of the app (e.g. 'spotify', 'chrome', 'notepad', 'calc', 'code', 'antigravity', 'terminal') or full path or URL ('https://youtube.com').
    """
    try:
        t_clean = target.strip().lower()
        if target.startswith("http://") or target.startswith("https://"):
            os.system(f'start "" "{target}"')
            return f"Opened URL: {target}"

        # Special app aliases
        if t_clean in ("antigravity", "agy", "terminal antigravity", "antigravity terminal", "terminal agy"):
            run_powershell("Start-Process wt.exe -ArgumentList 'agy' -ErrorAction SilentlyContinue; if (!$?) { Start-Process powershell.exe -ArgumentList '-NoExit', '-Command', 'agy' }")
            return "Launched Antigravity CLI terminal, sir."
        
        if t_clean in ("terminal", "wt", "windows terminal"):
            run_powershell("Start-Process wt.exe -ErrorAction SilentlyContinue; if (!$?) { Start-Process powershell.exe }")
            return "Opened Windows Terminal, sir."

        if t_clean in ("powershell", "posh"):
            run_powershell("Start-Process powershell.exe")
            return "Opened PowerShell, sir."

        if t_clean in ("cmd", "command prompt"):
            run_powershell("Start-Process cmd.exe")
            return "Opened Command Prompt, sir."

        cmd = f'Start-Process "{target}"'
        res = run_powershell(cmd)
        if "Error" not in res:
            return f"Successfully launched '{target}'"
        else:
            os.system(f'start "" "{target}"')
            return f"Attempted launching '{target}'"
    except Exception as e:
        return f"Error opening '{target}': {str(e)}"

def control_volume(action: str) -> str:
    """Control the Windows system audio volume.
    
    Args:
        action: One of 'up', 'down', 'mute', 'unmute'.
    """
    try:
        action = action.lower().strip()
        if action == "up":
            for _ in range(5):
                pyautogui.press("volumeup")
            return "Volume increased by 10%."
        elif action == "down":
            for _ in range(5):
                pyautogui.press("volumedown")
            return "Volume decreased by 10%."
        elif action in ("mute", "unmute"):
            pyautogui.press("volumemute")
            return f"Volume {action} toggled."
        else:
            return f"Unknown volume action: {action}. Supported: up, down, mute, unmute."
    except Exception as e:
        return f"Error adjusting volume: {str(e)}"

def control_media(action: str) -> str:
    """Control media playback (Spotify, YouTube, video/music players).
    
    Args:
        action: One of 'play_pause', 'next', 'prev', 'stop'.
    """
    try:
        action = action.lower().strip()
        if action in ("play_pause", "pause", "play", "toggle"):
            pyautogui.press("playpause")
            return "Toggled play/pause."
        elif action in ("next", "skip"):
            pyautogui.press("nexttrack")
            return "Skipped to next track."
        elif action in ("prev", "previous", "back"):
            pyautogui.press("prevtrack")
            return "Skipped to previous track."
        elif action == "stop":
            pyautogui.press("stop")
            return "Stopped media."
        else:
            return f"Unknown media action: {action}."
    except Exception as e:
        return f"Error controlling media: {str(e)}"

def lock_workstation() -> str:
    """Lock the Windows PC."""
    try:
        os.system("rundll32.exe user32.dll,LockWorkStation")
        return "Workstation locked successfully."
    except Exception as e:
        return f"Error locking workstation: {str(e)}"

def get_system_status() -> str:
    """Get real-time CPU, RAM, battery, and date/time status of the computer."""
    script = """
    $os = Get-CimInstance Win32_OperatingSystem
    $totalRam = [math]::Round($os.TotalVisibleMemorySize / 1MB, 2)
    $freeRam = [math]::Round($os.FreePhysicalMemory / 1MB, 2)
    $usedRam = [math]::Round($totalRam - $freeRam, 2)
    $cpu = (Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average
    $time = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    
    $battery = Get-CimInstance Win32_Battery -ErrorAction SilentlyContinue
    $batInfo = if ($battery) { "Battery: $($battery.EstimatedChargeRemaining)% ($($battery.BatteryStatus))" } else { "Battery: Desktop/AC Power" }
    
    "Time: $time`nCPU Usage: $cpu%`nRAM: Used $usedRam GB of $totalRam GB (Free: $freeRam GB)`n$batInfo"
    """
    return run_powershell(script)

def list_open_windows() -> str:
    """List open application windows with visible titles currently running on the PC."""
    script = """
    $apps = Get-Process | Where-Object { $_.MainWindowTitle -and $_.MainWindowTitle.Trim() -ne "" } | Select-Object Id, ProcessName, MainWindowTitle | Format-Table -AutoSize | Out-String -Width 200
    if ($apps.Trim()) { $apps } else { "No active application windows with visible titles found." }
    """
    return run_powershell(script)

def focus_window(window_title: str) -> str:
    """Bring a specific window to the foreground by its title or process name.
    
    Args:
        window_title: Partial or full title/name of the window (e.g. 'Chrome', 'Spotify', 'Visual Studio Code').
    """
    script = f"""
    $wscript = New-Object -ComObject WScript.Shell
    $success = $wscript.AppActivate('{window_title}')
    if ($success) {{ "Brought '$window_title' to focus." }} else {{ "Could not find open window matching '$window_title'." }}
    """
    return run_powershell(script)

def close_application(process_name: str) -> str:
    """Close or kill an application by process name (e.g. 'notepad', 'chrome', 'spotify').
    
    Args:
        process_name: Name of process without .exe (e.g. 'notepad').
    """
    script = f"Stop-Process -Name '{process_name.replace('.exe', '')}' -Force -ErrorAction Stop; 'Closed {process_name}'"
    return run_powershell(script)

def get_clipboard_text() -> str:
    """Read the current text content from the Windows clipboard."""
    try:
        content = pyperclip.paste()
        if not content:
            return "Clipboard is empty."
        if len(content) > 1500:
            return content[:1500] + "\n...[Clipboard truncated]..."
        return content
    except Exception as e:
        return f"Error reading clipboard: {str(e)}"

def set_clipboard_text(text: str) -> str:
    """Copy text onto the Windows clipboard.
    
    Args:
        text: Text to copy to clipboard.
    """
    try:
        pyperclip.copy(text)
        return f"Copied to clipboard ({len(text)} chars)."
    except Exception as e:
        return f"Error copying to clipboard: {str(e)}"

def show_desktop_notification(title: str, message: str) -> str:
    """Show a native Windows notification toast on the PC screen.
    
    Args:
        title: Title of notification.
        message: Body of notification.
    """
    clean_title = title.replace("'", "''")
    clean_msg = message.replace("'", "''")
    script = f"""
    [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType = WindowsRuntime] | Out-Null
    [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType = WindowsRuntime] | Out-Null
    $xml = @"
<toast>
    <visual>
        <binding template="ToastGeneric">
            <text>{clean_title}</text>
            <text>{clean_msg}</text>
        </binding>
    </visual>
</toast>
"@
    $doc = New-Object Windows.Data.Xml.Dom.XmlDocument
    $doc.LoadXml($xml)
    $toast = [Windows.UI.Notifications.ToastNotification]::new($doc)
    [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("J.A.R.V.I.S.").Show($toast)
    "Notification displayed."
    """
    return run_powershell(script)

def search_files(query: str, root_folder: str = "") -> str:
    """Search for files or documents matching a pattern on the PC.
    
    Args:
        query: Filename pattern or extension (e.g. '*.pdf', 'invoice*', 'photo*.jpg').
        root_folder: Optional base folder (e.g. 'Downloads', 'Documents', 'Desktop', or full path). Defaults to user profile.
    """
    user_home = os.path.expanduser("~")
    if not root_folder:
        search_path = user_home
    elif root_folder.lower() == "downloads":
        search_path = os.path.join(user_home, "Downloads")
    elif root_folder.lower() == "documents":
        search_path = os.path.join(user_home, "Documents")
    elif root_folder.lower() == "desktop":
        search_path = os.path.join(user_home, "Desktop")
    else:
        search_path = root_folder

    script = f"""
    Get-ChildItem -Path '{search_path}' -Filter '{query}' -Recurse -File -ErrorAction SilentlyContinue | Select-Object -First 15 FullName, Length, LastWriteTime | Format-Table -AutoSize | Out-String -Width 200
    """
    return run_powershell(script)

def read_text_file(file_path: str, max_lines: int = 60) -> str:
    """Read the first several lines of a text or code file.
    
    Args:
        file_path: Full or relative path to file.
        max_lines: Number of lines to read (default 60).
    """
    try:
        resolved_path = os.path.expanduser(file_path)
        if not os.path.exists(resolved_path):
            return f"Error: File not found at '{file_path}'"
        
        with open(resolved_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = [f.readline() for _ in range(max_lines)]
        
        content = "".join(lines)
        if len(content) > 3000:
            content = content[:3000] + "\n...[Content truncated]..."
        return content or "File is empty."
    except Exception as e:
        return f"Error reading file: {str(e)}"

def send_file_to_telegram(file_path: str) -> str:
    """Send a specific file, document, or image from the PC directly to the user in Telegram chat.
    
    Args:
        file_path: Full path to the file to send.
    """
    global PENDING_FILES_TO_SEND
    resolved_path = os.path.expanduser(file_path)
    if not os.path.exists(resolved_path):
        return f"Error: File not found at '{file_path}'"
    
    # Check file size (Telegram limit ~50MB)
    size_mb = os.path.getsize(resolved_path) / (1024 * 1024)
    if size_mb > 50:
        return f"Error: File is {size_mb:.1f} MB, which exceeds Telegram's 50 MB bot limit."
    
    PENDING_FILES_TO_SEND.append(resolved_path)
    return f"File '{os.path.basename(resolved_path)}' queued to be sent to Telegram."

def press_hotkey_or_type(text: str = "", hotkey: str = "") -> str:
    """Type keyboard text or execute a keyboard hotkey shortcut.
    
    Args:
        text: Text string to type.
        hotkey: Hotkey combination, e.g. 'ctrl+c', 'ctrl+v', 'alt+f4', 'alt+tab', 'enter', 'esc'.
    """
    try:
        results = []
        if hotkey:
            keys = [k.strip().lower() for k in hotkey.split("+")]
            pyautogui.hotkey(*keys)
            results.append(f"Pressed hotkey '{hotkey}'")
        if text:
            pyautogui.typewrite(text, interval=0.02)
            results.append(f"Typed text '{text}'")
        return "; ".join(results) if results else "No action specified."
    except Exception as e:
        return f"Error with keyboard action: {str(e)}"

AVAILABLE_TOOLS = [
    run_powershell,
    take_screenshot,
    open_application_or_url,
    control_volume,
    control_media,
    lock_workstation,
    get_system_status,
    list_open_windows,
    focus_window,
    close_application,
    get_clipboard_text,
    set_clipboard_text,
    show_desktop_notification,
    search_files,
    read_text_file,
    send_file_to_telegram,
    press_hotkey_or_type,
]
