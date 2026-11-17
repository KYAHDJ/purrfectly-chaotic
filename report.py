"""Step 2: read saved stats, ask Claude (headless CLI) for analysis + 3 ideas, save to reports/<date>.md."""
import datetime, pathlib, shutil, subprocess, sys

today = datetime.date.today().isoformat()
raw = pathlib.Path("data/raw") / today
log = pathlib.Path("data/stats_log.csv")
if not log.exists() or not raw.exists():
    sys.exit("No stats for today. Run stats.py first.")

def read(name, limit=6000):
    p = raw / f"{name}.txt"
    return p.read_text(encoding="utf-8")[:limit] if p.exists() else ""

import json
rp = pathlib.Path("data/research") / f"{today}.json"
research = ""
if rp.exists():
    rows = json.loads(rp.read_text(encoding="utf-8"))
    research = "\n".join(
        f"- {r['views']:,} views | {r['seconds']}s | {r['author']} | {r['published'][:10]} | {r['title']} | tags: {', '.join(r['tags'][:8])}"
        for r in rows)

notes = pathlib.Path("channel_notes.md")
notes_txt = notes.read_text(encoding="utf-8") if notes.exists() else ""

prompt = f"""You are the analyst for a US-audience YouTube channel about cats (narrated, edited compilation style).
Date: {today}

CHANNEL NOTES (goals, rules, reference videos):
{notes_txt}

STATS HISTORY (csv):
{log.read_text(encoding="utf-8")}

VIDEO LIST (Studio, today):
{read("videos")}

ANALYTICS CONTENT TAB (today):
{read("analytics_content")}

TOP CAT SHORTS ON YOUTUBE TODAY (market research, learn patterns, do not copy):
{research}

Write a SHORT report in markdown (casual, few words):
## Snapshot - key numbers + change vs previous days
## What worked - per video: views, CTR, retention, title/thumbnail. If there are no videos or not enough data, say so plainly; do not invent numbers.
## What to improve - max 3 bullets
## Market patterns - 3 bullets from the top Shorts list
## 3 new video ideas - each: working title, hook (first 5 sec), why it fits US viewers, format. Original takes, not copies of existing videos.
Rules: no downloading from YouTube; stay careful on copyright (original narration, transformative edits).
"""

claude = shutil.which("claude")
if not claude:
    sys.exit("claude CLI not found")
res = subprocess.run([claude, "-p", "--output-format", "text"], input=prompt,
                     capture_output=True, text=True, encoding="utf-8", timeout=600)
if res.returncode != 0:
    sys.exit("claude failed:\n" + res.stderr)
out = pathlib.Path("reports"); out.mkdir(exist_ok=True)
(out / f"{today}.md").write_text(res.stdout, encoding="utf-8")
print("saved reports/%s.md" % today)
