"""Desktop app launcher: starts the local server if needed, opens the dashboard in its own window."""
import os, socket, subprocess, sys, time, pathlib, urllib.request

ROOT = pathlib.Path(__file__).parent.resolve()
PORT = 8765
URL = f"http://127.0.0.1:{PORT}"
NO_WINDOW = 0x08000000

def up():
    try:
        with socket.create_connection(("127.0.0.1", PORT), timeout=0.5):
            return True
    except OSError:
        return False

def find_browser():
    for p in [r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe"]:
        if os.path.exists(p):
            return p

started_server = False
if not up():
    py = ROOT / ".venv" / "Scripts" / "pythonw.exe"
    subprocess.Popen([str(py), str(ROOT / "server.py")], cwd=ROOT, creationflags=NO_WINDOW)
    started_server = True
    for _ in range(50):
        if up(): break
        time.sleep(0.2)

browser = find_browser()
if browser:
    # separate profile dir so this is its own window/process and we can wait for it to close
    # Don't wait for the window: Edge may hand off to an existing process and return at once.
    # The server shuts itself down a few minutes after the window is closed.
    subprocess.Popen([browser, f"--app={URL}", f"--user-data-dir={ROOT / 'appwin'}",
                      "--window-size=1250,880", "--no-first-run", "--disable-features=Translate"])
else:
    os.startfile(URL)
