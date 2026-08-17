import os
import sys
import subprocess
import threading
import time
from PIL import Image, ImageDraw
import pystray
from pystray import MenuItem as item, Menu

BOT_PROCESS = None
BOT_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "jarvis.log")
DIR_PATH = os.path.dirname(os.path.abspath(__file__))

def create_icon_image(status_color="blue"):
    """Create a sleek 64x64 icon for the system tray."""
    image = Image.new('RGBA', (64, 64), color=(0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    
    # Outer circle
    color_map = {
        "blue": (0, 180, 255, 255),
        "green": (0, 230, 100, 255),
        "red": (255, 60, 60, 255)
    }
    main_color = color_map.get(status_color, (0, 180, 255, 255))
    
    draw.ellipse((4, 4, 60, 60), fill=(20, 25, 35, 255), outline=main_color, width=3)
    # Inner glowing circle
    draw.ellipse((16, 16, 48, 48), fill=main_color)
    # Center dot
    draw.ellipse((26, 26, 38, 38), fill=(255, 255, 255, 255))
    return image

def is_bot_running():
    global BOT_PROCESS
    if BOT_PROCESS and BOT_PROCESS.poll() is None:
        return True
    
    # Check via powershell
    try:
        cmd = "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*main.py*' } | Select-Object -ExpandProperty ProcessId"
        out = subprocess.check_output(["powershell", "-NoProfile", "-Command", cmd], text=True).strip()
        return bool(out)
    except Exception:
        return False

def start_bot(icon=None):
    global BOT_PROCESS
    if is_bot_running():
        return
    
    # Start via pyw / pythonw in background
    cmd = ["pyw", "-3.12", BOT_SCRIPT]
    try:
        BOT_PROCESS = subprocess.Popen(
            cmd,
            cwd=DIR_PATH,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
    except Exception:
        BOT_PROCESS = subprocess.Popen(
            ["pythonw", BOT_SCRIPT],
            cwd=DIR_PATH,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        )
    
    if icon:
        icon.icon = create_icon_image("green")
        icon.title = "J.A.R.V.I.S. (Online)"

def stop_bot(icon=None):
    global BOT_PROCESS
    if BOT_PROCESS:
        try:
            BOT_PROCESS.terminate()
        except Exception:
            pass
        BOT_PROCESS = None
        
    try:
        cmd = "Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*main.py*' } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }"
        subprocess.run(["powershell", "-NoProfile", "-Command", cmd], check=False)
    except Exception:
        pass

    if icon:
        icon.icon = create_icon_image("red")
        icon.title = "J.A.R.V.I.S. (Stopped)"

def restart_bot(icon, item):
    stop_bot(icon)
    time.sleep(1)
    start_bot(icon)

def on_open_logs(icon, item):
    if os.path.exists(LOG_PATH):
        os.system(f'notepad "{LOG_PATH}"')
    else:
        os.system(f'notepad "{os.path.join(DIR_PATH, "jarvis.log")}"')

def on_open_folder(icon, item):
    os.system(f'explorer "{DIR_PATH}"')

def on_quit(icon, item):
    stop_bot(icon)
    icon.stop()

def get_status_text(item):
    return "🟢 Status: Online" if is_bot_running() else "🔴 Status: Offline"

def toggle_service(icon, item):
    if is_bot_running():
        stop_bot(icon)
    else:
        start_bot(icon)

def run_tray():
    # Start bot initially
    start_bot()

    menu = Menu(
        item(get_status_text, None, enabled=False),
        item('Toggle Start/Stop', toggle_service),
        item('Restart Jarvis', restart_bot),
        Menu.SEPARATOR,
        item('View Logs (jarvis.log)', on_open_logs),
        item('Open Jarvis Folder', on_open_folder),
        Menu.SEPARATOR,
        item('Exit Tray & Stop', on_quit)
    )

    icon = pystray.Icon(
        "jarvis_bot",
        create_icon_image("green" if is_bot_running() else "red"),
        "J.A.R.V.I.S. Telegram Bot",
        menu
    )
    icon.run()

if __name__ == "__main__":
    run_tray()
