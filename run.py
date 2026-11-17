"""The Run button: stats -> research -> report. A failed step doesn't stop the rest."""
import subprocess, sys

steps = [("Channel stats", "stats.py"), ("Market research", "research.py"), ("Report", "report.py")]
ok = {}
for name, script in steps:
    print(f"\n=== {name} ===")
    ok[name] = subprocess.run([sys.executable, script]).returncode == 0

print("\n=== Summary ===")
for name, good in ok.items():
    print(("OK    " if good else "FAILED"), name)
if ok.get("Report"):
    import datetime
    print(f"\nReport: reports\\{datetime.date.today().isoformat()}.md")
if "--no-pause" not in sys.argv:
    input("\nPress Enter to close...")
sys.exit(0 if all(ok.values()) else 1)
