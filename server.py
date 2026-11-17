"""Local dashboard server. Serves dashboard.html + JSON of your saved data; runs RUN pipeline on demand."""
import json, pathlib, subprocess, sys, threading, os, csv, time, re
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler

ROOT = pathlib.Path(__file__).parent.resolve()
PORT = 8765
HOST = f"127.0.0.1:{PORT}"
state = {"kind": None, "running": False, "log": [], "started": None, "ended": None, "ok": None}
lock = threading.Lock()
seen = [time.time()]  # last time the dashboard asked for anything

def latest(folder, pattern):
    files = sorted((ROOT / folder).glob(pattern))
    return files[-1] if files else None

def collect():
    stats = []
    log = ROOT / "data" / "stats_log.csv"
    if log.exists():
        with log.open(encoding="utf-8", newline="") as fh:
            stats = list(csv.DictReader(fh))
    r = latest("data/research", "*.json")
    research = json.loads(r.read_text(encoding="utf-8")) if r else []
    rep = latest("reports", "*.md")
    with lock:
        run = dict(state, log=state["log"][-400:])
    return {"stats": stats, "research": research, "research_date": r.stem if r else None,
            "report": rep.read_text(encoding="utf-8") if rep else "", "report_date": rep.stem if rep else None,
            "run": run, "video": latest_video()}

def latest_video():
    outd = ROOT / "output"
    vids = sorted(outd.glob("commentary_*.mp4"), key=lambda p: p.stat().st_mtime) if outd.exists() else []
    if not vids:
        return None
    v = vids[-1]; stem = v.stem
    return {"name": stem, "video": f"/output/{v.name}",
            "thumb": f"/output/{stem}_thumb.jpg" if (outd / f"{stem}_thumb.jpg").exists() else None,
            "sheet": f"/output/{stem}_preview.jpg" if (outd / f"{stem}_preview.jpg").exists() else None,
            "made": v.stat().st_mtime}

def run_pipeline(script="run.py", kind="daily"):
    py = ROOT / ".venv" / "Scripts" / "python.exe"
    env = dict(os.environ, PYTHONUNBUFFERED="1", PYTHONIOENCODING="utf-8")
    with lock:
        state.update(kind=kind, running=True, log=[], started=time.time(), ended=None, ok=None)
    try:
        p = subprocess.Popen([str(py), "-u", script, "--no-pause"], cwd=ROOT, env=env,
                             stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                             encoding="utf-8", errors="replace", creationflags=0x08000000)
        for line in p.stdout:
            with lock:
                state["log"].append(line.rstrip())
        p.wait()
        ok = p.returncode == 0
    except Exception as e:
        with lock:
            state["log"].append(f"ERROR: {e}")
        ok = False
    with lock:
        state.update(running=False, ended=time.time(), ok=ok)

class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def _ok_origin(self):
        if self.headers.get("Host") != HOST:
            return False
        o = self.headers.get("Origin")
        return o is None or o == f"http://{HOST}"

    def _send(self, code, body, ctype="application/json"):
        b = body if isinstance(body, bytes) else body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype + "; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if not self._ok_origin():
            return self._send(403, "{}")
        seen[0] = time.time()
        if self.path == "/":
            return self._send(200, (ROOT / "dashboard.html").read_bytes(), "text/html")
        if self.path == "/api/data":
            return self._send(200, json.dumps(collect(), ensure_ascii=False))
        if self.path.startswith("/output/"):
            return self._serve_output(self.path[len("/output/"):].split("?")[0])
        self._send(404, "{}")

    def _serve_output(self, name):
        f = (ROOT / "output" / name).resolve()
        if f.parent != (ROOT / "output").resolve() or not f.is_file():
            return self._send(404, "{}")
        ctype = {".mp4": "video/mp4", ".jpg": "image/jpeg"}.get(f.suffix.lower(), "application/octet-stream")
        size = f.stat().st_size
        start, end, code = 0, size - 1, 200
        rng = self.headers.get("Range")
        if rng:
            m = re.match(r"bytes=(\d*)-(\d*)", rng)
            if m:
                if m.group(1): start = int(m.group(1))
                if m.group(2): end = min(int(m.group(2)), size - 1)
                code = 206
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Length", str(end - start + 1))
        if code == 206:
            self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
        self.end_headers()
        with f.open("rb") as fh:
            fh.seek(start); left = end - start + 1
            while left > 0:
                chunk = fh.read(min(65536, left))
                if not chunk: break
                try: self.wfile.write(chunk)
                except Exception: break
                left -= len(chunk)

    def do_POST(self):
        if not self._ok_origin():
            return self._send(403, "{}")
        if self.path == "/api/run":
            with lock:
                busy = state["running"]
            if not busy:
                threading.Thread(target=run_pipeline, daemon=True).start()
            return self._send(200, json.dumps({"started": not busy}))
        if self.path == "/api/make":
            with lock:
                busy = state["running"]
            if not busy:
                threading.Thread(target=run_pipeline, args=("make_run.py", "make"), daemon=True).start()
            return self._send(200, json.dumps({"started": not busy}))
        if self.path == "/api/quit":
            with lock:
                busy = state["running"]
            self._send(200, json.dumps({"quit": not busy}))
            if not busy:
                threading.Thread(target=lambda: (time.sleep(0.3), os._exit(0))).start()
            return
        self._send(404, "{}")

def watchdog():
    """Exit when the dashboard window has been gone for a while (and no run is active)."""
    time.sleep(90)  # grace period for first load
    while True:
        time.sleep(10)
        with lock:
            busy = state["running"]
        if not busy and time.time() - seen[0] > 180:
            os._exit(0)

if __name__ == "__main__":
    threading.Thread(target=watchdog, daemon=True).start()
    ThreadingHTTPServer(("127.0.0.1", PORT), H).serve_forever()
