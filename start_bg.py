import subprocess
import os
import sys

dir_path = os.path.dirname(os.path.abspath(__file__))
bridge_path = os.path.join(dir_path, "pc_bridge.py")

pythonw_exe = r"C:\Users\ROG\AppData\Local\Programs\Python\Python312\pythonw.exe"
if not os.path.exists(pythonw_exe):
    pythonw_exe = sys.executable.replace("python.exe", "pythonw.exe")

DETACHED_PROCESS = 0x00000008
CREATE_NEW_PROCESS_GROUP = 0x00000200

proc = subprocess.Popen(
    [pythonw_exe, bridge_path],
    cwd=dir_path,
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    creationflags=DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP,
    close_fds=True
)

print(f"✅ J.A.R.V.I.S. PC Bridge successfully started in background! (PID: {proc.pid})")
