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

def get_screen_resolution() -> str:
    """Get the screen width and height in pixels."""
    try:
        width, height = pyautogui.size()
        pos_x, pos_y = pyautogui.position()
        return f"Screen Resolution: {width}x{height} pixels. Current Mouse Position: ({pos_x}, {pos_y})."
    except Exception as e:
        return f"Error getting screen size: {str(e)}"

MOUSEEVENTF_MOVE = 0x0001
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_RIGHTDOWN = 0x0008
MOUSEEVENTF_RIGHTUP = 0x0010
MOUSEEVENTF_MIDDLEDOWN = 0x0020
MOUSEEVENTF_MIDDLEUP = 0x0040
MOUSEEVENTF_ABSOLUTE = 0x8000

def win32_hardware_click(pixel_x: int, pixel_y: int, button: str = "left", clicks: int = 1):
    """Execute direct Windows kernel hardware mouse click via mouse_event MOUSEEVENTF_ABSOLUTE."""
    try:
        import ctypes
        ctypes.windll.user32.SetProcessDPIAware()
        width, height = pyautogui.size()
        norm_x = int(pixel_x * 65535 / max(width - 1, 1))
        norm_y = int(pixel_y * 65535 / max(height - 1, 1))
        
        # 1. Move cursor
        ctypes.windll.user32.mouse_event(MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_MOVE, norm_x, norm_y, 0, 0)
        time.sleep(0.04)
        
        # 2. Determine button flags
        btn = button.lower()
        if btn == "right":
            down_flag = MOUSEEVENTF_RIGHTDOWN
            up_flag = MOUSEEVENTF_RIGHTUP
        elif btn == "middle":
            down_flag = MOUSEEVENTF_MIDDLEDOWN
            up_flag = MOUSEEVENTF_MIDDLEUP
        else:
            down_flag = MOUSEEVENTF_LEFTDOWN
            up_flag = MOUSEEVENTF_LEFTUP
            
        # 3. Perform clicks
        for _ in range(clicks):
            ctypes.windll.user32.mouse_event(MOUSEEVENTF_ABSOLUTE | down_flag, norm_x, norm_y, 0, 0)
            time.sleep(0.04)
            ctypes.windll.user32.mouse_event(MOUSEEVENTF_ABSOLUTE | up_flag, norm_x, norm_y, 0, 0)
            if clicks > 1:
                time.sleep(0.08)
    except Exception:
        # Fallback to PyAutoGUI
        pyautogui.click(pixel_x, pixel_y, clicks=clicks, button=button.lower())

def mouse_move_and_click(x: int, y: int, button: str = "left", clicks: int = 1) -> str:
    """Move the mouse cursor to specific screen coordinates (x, y) and perform a click.
    
    Args:
        x: Horizontal pixel coordinate (0 to screen width).
        y: Vertical pixel coordinate (0 to screen height).
        button: Mouse button ('left', 'right', 'middle'). Default 'left'.
        clicks: Number of clicks (1 for single click, 2 for double click).
    """
    try:
        width, height = pyautogui.size()
        target_x = max(0, min(x, width - 1))
        target_y = max(0, min(y, height - 1))
        
        win32_hardware_click(target_x, target_y, button=button, clicks=clicks)
        return f"Mouse moved to ({target_x}, {target_y}) and performed {clicks} {button}-click(s)."
    except Exception as e:
        return f"Error executing mouse click: {str(e)}"

def mouse_scroll(amount: int) -> str:
    """Scroll the active window up or down with the mouse wheel.
    
    Args:
        amount: Number of scroll steps. Positive numbers scroll UP, negative numbers scroll DOWN (e.g. -500 to scroll down).
    """
    try:
        pyautogui.scroll(amount)
        direction = "UP" if amount > 0 else "DOWN"
        return f"Scrolled {direction} by {abs(amount)} steps."
    except Exception as e:
        return f"Error scrolling: {str(e)}"

def mouse_drag(start_x: int, start_y: int, end_x: int, end_y: int, duration: float = 0.5) -> str:
    """Drag the mouse with the left button held down from (start_x, start_y) to (end_x, end_y).
    
    Args:
        start_x: Starting X coordinate.
        start_y: Starting Y coordinate.
        end_x: Ending X coordinate.
        end_y: Ending Y coordinate.
        duration: Duration of drag in seconds (default 0.5).
    """
    try:
        pyautogui.moveTo(start_x, start_y)
        pyautogui.dragTo(end_x, end_y, duration=duration, button="left")
        return f"Dragged mouse from ({start_x}, {start_y}) to ({end_x}, {end_y})."
    except Exception as e:
        return f"Error dragging mouse: {str(e)}"

def search_chrome(query: str, search_engine: str = "google") -> str:
    """Open Google Chrome and search for a query or open a website URL.
    
    Args:
        query: Search query (e.g. 'latest AI news', 'weather today') or direct URL ('youtube.com', 'https://github.com').
        search_engine: 'google' or 'youtube' or 'bing' (default 'google').
    """
    import urllib.parse
    try:
        if query.startswith("http://") or query.startswith("https://"):
            url = query
        elif "." in query and " " not in query and not query.endswith("."):
            url = f"https://{query}"
        elif search_engine.lower() == "youtube":
            url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        elif search_engine.lower() == "bing":
            url = f"https://www.bing.com/search?q={urllib.parse.quote(query)}"
        else:
            url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"

        # Launch via powershell start or default browser
        run_powershell(f'Start-Process "chrome.exe" -ArgumentList "{url}" -ErrorAction SilentlyContinue; if (!$?) {{ Start-Process "{url}" }}')
        return f"Opened Chrome and navigated to: {url}"
    except Exception as e:
        return f"Error searching Chrome: {str(e)}"

def chrome_action(action: str) -> str:
    """Execute standard browser navigation actions on Google Chrome / active browser.
    
    Args:
        action: One of 'new_tab', 'close_tab', 'next_tab', 'prev_tab', 'reopen_tab', 'refresh', 'back', 'forward', 'zoom_in', 'zoom_out', 'fullscreen', 'address_bar'.
    """
    action = action.lower().strip()
    try:
        if action in ("new_tab", "tab"):
            pyautogui.hotkey("ctrl", "t")
            return "Opened new browser tab."
        elif action in ("close_tab", "close"):
            pyautogui.hotkey("ctrl", "w")
            return "Closed current browser tab."
        elif action in ("next_tab", "next"):
            pyautogui.hotkey("ctrl", "tab")
            return "Switched to next tab."
        elif action in ("prev_tab", "previous"):
            pyautogui.hotkey("ctrl", "shift", "tab")
            return "Switched to previous tab."
        elif action in ("reopen_tab", "undo_close"):
            pyautogui.hotkey("ctrl", "shift", "t")
            return "Reopened last closed tab."
        elif action in ("refresh", "reload"):
            pyautogui.hotkey("ctrl", "r")
            return "Refreshed browser page."
        elif action == "back":
            pyautogui.hotkey("alt", "left")
            return "Navigated back."
        elif action == "forward":
            pyautogui.hotkey("alt", "right")
            return "Navigated forward."
        elif action in ("address_bar", "url_bar"):
            pyautogui.hotkey("ctrl", "l")
            return "Focused address bar."
        elif action == "fullscreen":
            pyautogui.press("f11")
            return "Toggled fullscreen mode."
        else:
            return f"Unknown browser action: {action}."
    except Exception as e:
        return f"Error executing browser action '{action}': {str(e)}"

def type_and_press_enter(text: str) -> str:
    """Type a string into the currently focused input box or application and press the Enter key.
    
    Args:
        text: The text to type before pressing Enter.
    """
    try:
        pyautogui.typewrite(text, interval=0.02)
        time.sleep(0.1)
        pyautogui.press("enter")
        return f"Typed '{text}' and pressed Enter."
    except Exception as e:
        return f"Error typing and pressing Enter: {str(e)}"

def press_hotkey_or_type(text: str = "", hotkey: str = "") -> str:
    """Type keyboard text or execute a keyboard hotkey shortcut.
    
    Args:
        text: Text string to type.
        hotkey: Hotkey combination, e.g. 'ctrl+c', 'ctrl+v', 'alt+f4', 'alt+tab', 'enter', 'esc', 'win+d'.
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

def click_ui_element(x_percent: float, y_percent: float, button: str = "left", clicks: int = 1) -> str:
    """Click a visual UI element on screen using percentage coordinates (0.0 to 100.0) from a screenshot.
    
    Args:
        x_percent: Horizontal percentage across the screen (0.0 = far left, 50.0 = middle, 100.0 = far right).
        y_percent: Vertical percentage down the screen (0.0 = top, 50.0 = middle, 100.0 = bottom).
        button: 'left', 'right', or 'middle' (default 'left').
        clicks: Number of clicks (1 for single click, 2 for double click).
    """
    try:
        width, height = pyautogui.size()
        pixel_x = int((max(0.0, min(100.0, float(x_percent))) / 100.0) * width)
        pixel_y = int((max(0.0, min(100.0, float(y_percent))) / 100.0) * height)
        
        win32_hardware_click(pixel_x, pixel_y, button=button, clicks=clicks)
        return f"Clicked at screen coordinate ({pixel_x}, {pixel_y}) [{x_percent:.1f}%, {y_percent:.1f}%]."
    except Exception as e:
        return f"Error clicking UI element: {str(e)}"

def play_youtube_video(query: str) -> str:
    """Search YouTube on Chrome and automatically open/play the video.
    
    Args:
        query: Name of the video, song, artist, or topic to play (e.g. 'Interstellar theme', 'lo-fi beats').
    """
    import urllib.parse
    try:
        url = f"https://www.youtube.com/results?search_query={urllib.parse.quote(query)}"
        run_powershell(f'Start-Process "chrome.exe" -ArgumentList "{url}" -ErrorAction SilentlyContinue; if (!$?) {{ Start-Process "{url}" }}')
        
        # Focus Chrome and wait for page load
        time.sleep(2.0)
        focus_window("Chrome")
        time.sleep(0.5)

        width, height = pyautogui.size()
        # Typical first YouTube video thumbnail location
        first_video_x = int(width * 0.38)
        first_video_y = int(height * 0.35)
        win32_hardware_click(first_video_x, first_video_y, clicks=1)
        
        return f"Opened YouTube and triggered playback for: '{query}'."
    except Exception as e:
        return f"Error playing YouTube video: {str(e)}"

def press_key(key_name: str) -> str:
    """Press a single keyboard key (e.g. 'enter', 'space', 'esc', 'tab', 'k', 'f', 'm', 'up', 'down').
    
    Args:
        key_name: Name of key to press.
    """
    try:
        pyautogui.press(key_name.lower().strip())
        return f"Pressed '{key_name}'."
    except Exception as e:
        return f"Error pressing key '{key_name}': {str(e)}"

AVAILABLE_TOOLS = [
    run_powershell,
    take_screenshot,
    get_screen_resolution,
    mouse_move_and_click,
    click_ui_element,
    mouse_scroll,
    mouse_drag,
    search_chrome,
    play_youtube_video,
    chrome_action,
    type_and_press_enter,
    press_key,
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
