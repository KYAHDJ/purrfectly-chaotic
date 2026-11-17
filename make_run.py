"""Make Video button: find clips -> pick clip + write commentary script -> render a Commentary Short. Never uploads."""
import subprocess, sys, datetime

kw = ["funny cat", "cat fails", "chaotic cat", "cat reaction", "cute cat funny"]
word = kw[datetime.date.today().toordinal() % len(kw)]
steps = [("Find clips", ["rednote_fetch.py", word, "8"]), ("Plan the edit", ["plan_edit.py"]), ("Render video", ["make_edit.py"])]
ok = {}
for name, args in steps:
    print(f"\n=== {name} ===", flush=True)
    good = subprocess.run([sys.executable, "-u", *args]).returncode == 0
    ok[name] = good
    if name == "Find clips" and not good:
        print("Clip search failed, trying with clips already downloaded.", flush=True)
    elif not good:
        break
print("\n=== Summary ===")
for name, good in ok.items():
    print(("OK    " if good else "FAILED"), name)
sys.exit(0 if ok.get("Render video") else 1)
