import subprocess
import os
import sys

dir_path = os.path.dirname(os.path.abspath(__file__))
main_path = os.path.join(dir_path, "main.py")

pythonw_exe = r"C:\Users\ROG\AppData\Local\Programs\Python\Python312\pythonw.exe"
if not os.path.exists(pythonw_exe):
    pythonw_exe = sys.executable.replace("python.exe", "pythonw.exe")

DETACHED_PROCESS = 0x00000008

proc = subprocess.Popen(
    [pythonw_exe, main_path],
    cwd=dir_path,
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    creationflags=DETACHED_PROCESS
)

print(f"✅ J.A.R.V.I.S. successfully started in background! (PID: {proc.pid})")
