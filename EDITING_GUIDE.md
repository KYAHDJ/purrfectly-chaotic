# Purrfectly Chaotic: Editing Guide

Everything learned while building the "Commentary Short" editing pipeline for the *Purrfectly Chaotic* cat channel (US audience, vertical 1080x1920, ~12-20 s videos).
Nothing here uploads anything: every render is reviewed by the channel owner first.

---

## 1. How a video gets made now (the real workflow)

The owner decided: **Claude (in chat) directs each edit by hand.** The dashboard's "Make Video" button still exists, but it uses the older auto planner (`plan_edit.py`) and is not the main path.

For every video:

1. **Get a clip**: `python rednote_fetch.py "<keyword>" 8` downloads rednote clips into `clips/` + `clips/manifest.json`. Used clip ids are in `data/used_clips.json`. Skip clips with burned-in text/subtitles and clips that are already in the owner's old videos.
2. **Study the clip**: extract a contact sheet with a coordinate grid (every 20 %) and a timestamp on each frame (ffmpeg `-ss`, PIL). Read focus points (x, y as fractions of the frame) and the exact times of the beats (hand enters, reaction, hit, scream).
3. **Decide the kit for THIS clip** (see section 6). Do not reuse the same effects by habit.
4. **Write `plan_e.json`** by hand: script lines anchored to clip times, events, per-video style keys.
5. **Render**: `CTA=meow|rate|none .venv\Scripts\python.exe make_edit.py` (output in `output/commentary_<date>_<time>.mp4`).
6. **Verify with frames** (contact sheet at the transitions, effects and endings). Claude cannot hear or watch motion; verify with frames, ASR timing (`asr_util.py`) and numbers.
7. **Send the mp4 to the owner**. They (and optionally Gemini, see 9) review it. Iterate.

Rules of the owner's working style: short casual replies, simple words, no lectures, one step at a time, **"talk to me first" before big builds**.

---

## 2. Files

| File | What it does |
|---|---|
| `make_edit.py` | The renderer. Reads `plan_e.json`, makes voice, time-warps the clip, adds captions/effects/transitions/sfx/music, masters audio, writes the mp4 + preview + thumb. |
| `plan_e.json` | The edit plan for the current video (hand-written). |
| `plan_edit.py` | Old auto planner (calls the Claude CLI). Used only by the Make Video button. Stops with `CLAUDE NOT REACHABLE` instead of making a generic video. |
| `voice.py` | TTS. Default engine **edge** (Microsoft neural voice, online), fallback David (Windows SAPI). Optional VoiceStudio engine. |
| `gl_trans.py` | CapCut-style transitions using the open-source **gl-transitions** GLSL shaders rendered with `moderngl`. |
| `assets/gl/*.glsl` | The shaders (downloaded from github.com/gl-transitions/gl-transitions). |
| `assets/memes/` | Meme sound effects (`*.wav`, edited) and swishes (`swish_N.wav`). `raw/` holds the original downloads from Myinstants. |
| `assets/sfx_*.wav` | Synthesized basic sfx (`sfx.py`): whoosh, pop, hit, click, scratch, beep, drop, meow. |
| `assets/music_loop.wav` | Synthesized music loop (`music.py`, 140 BPM, 28 bars). |
| `swoosh_gen.py` | Old synthesized swooshes (replaced by real recorded swishes, kept for reference). |
| `rednote_fetch.py` | Clip downloader (Playwright). |
| `asr_util.py` | faster-whisper word timestamps (audio decoded via ffmpeg). |
| `server.py`, `dashboard.html`, `run.py`, `make_run.py` | Dashboard, daily Run (stats/research/report) and Make Video. `server.py` `latest_video()` globs `commentary_*.mp4`. |
| `plan_commentary.py`, `make_commentary.py`, `plan_c.json` | Older single-template pipeline. Not wired in. |
| `data/yt/*.py` | YouTube Studio automation with the saved login: `upload.py` (private upload with title/description/tags/US settings), `sched2.py` (schedule 8 AM Manila), `set_country.py`, `list_content.py`, `drafts2.py` (draft cleanup). See section 16. |
| `data/refs/old/` | Analysis of the owner's 11 old successful videos (word timings, audio, end frames). |

Python: the project venv `.venv\Scripts\python.exe`. Needs ffmpeg/ffprobe on PATH. Extra packages used: `edge-tts`, `moderngl`, `faster-whisper`, `numpy`, `Pillow`, `playwright`.

---

## 3. The reference style (the owner's 11 old videos)

Verified by frame/ASR analysis of `Downloads\Catcompilationsinpast` (11 MP4s):

- **Narration**: male-sounding, fast, ~4.4 words/sec, conversational internet voice ("Bro...", "I have so many questions...", "Look at that side eye."). Written specifically for each clip.
- **Captions**: Impact, ALL CAPS, **small** (not giant), low on screen (about 78 % down), **2-3 word chunks**, thick black outline, one accent word per chunk coloured (cyan / yellow / green), the rest white. The caption style varies a little per video.
- **Picture**: clip fills the frame (zoomed/cropped 9:16), still and steady. Very few cuts: usually only 3-5 transitions per video, and they land when a new sentence starts.
- **Transitions seen**: fast zoom-in punch with motion blur, sideways blur streak, spinning blur whip. Opening of some videos was blur-in + white flash, but the owner later said: **never use fades unless needed** (moving transitions only).
- **Text/stickers**: no big meme text in the old videos. Stickers are rare, small, never on the face. (The owner liked a few meme texts, but too much made them feel sick: use at most one, only when it earns its place.)
- **Endings**: most end on the punchline. Only 3 of 11 have a subscribe/meow ending, 1 has "Rate this absolute genius from one to ten in the comments." The owner wants the ending to **vary per video**.
- **Sound**: music low, meme/sfx hits on the big moments, a swish on each transition.

---

## 4. `plan_e.json` format

```json
{
  "id": "<rednote id>", "file": "rn_<id>.mp4", "dur": 23.4, "w": 720, "h": 1280,
  "rhythm": false,
  "lines": [ {"say": "One sentence.", "at": 0.3, "pause": 0} ],
  "events": [ {"type": "push", "t": 2.3, "focus": [0.4, 0.42], "zoom": 1.3} ],
  "peaks": [], "cen": [],
  "trs": ["LensPush","DirectionalWarp","StretchSlide","WhipSpin"],
  "sw": [5,7,4,10,1,6],
  "acc": ["00D7FF","0080FF","9B6BFF"],
  "grade": "warm",
  "music": 0.07
}
```

- `lines[].at` = the **clip time** where that line's moment starts. The renderer time-warps the clip so every line lands on its moment: speed = clip-seconds / voice-seconds, clamped to 0.55x-2.4x (slow-mo when the script is short for the moment, time-lapse when long). The last line ping-pongs forward/back if the clip runs out (never a frozen end frame).
- `events[].t` = clip time (mapped to output time automatically). `focus` is `[x, y]` as fractions of the clip frame (0..1, origin top-left).
- `rhythm: false` turns off the automatic key-word punch-ins (use hand-placed events).
- Per-video style keys: `trs` (transition set), `sw` (order of swish sounds), `acc` (caption accent colours, ASS BGR hex), `grade` (`warm` | `cold`), `music` (volume, default 0.15).
- Ending is picked by env var `CTA`: `meow`, `rate`, or `none` (default is a seeded random pick from the clip id).
  - `meow`: "Hit subscribe and click the like button to watch it turn into a meow emoji." + subscribe pills + cursor click + meow sfx, over the last 2 s of the clip played forward/back.
  - `rate`: "Rate this absolute genius from one to ten in the comments."
  - `both`: subscribe + comment: "Hit subscribe for more chaos, and tell me in the comments what this cat should do next." Subscribe pills + cursor click, no meow sound. A plan can override the wording per clip with `cta_text` (e.g. "...tell me in the comments how many laps you would last.").
  - `none`: ends on the punchline, with a 0.8 s tail so the last word is never clipped.

### Event types

| type | What it does | When to use it |
|---|---|---|
| `punch` | Hard zoom-in (1.25-1.6x) on `focus` for `dur` s. | A reveal or a reaction. Rare. |
| `circle` | Magnifier circle. `inplace: true` puts it right over the spot, `src` = source crop px (smaller = stronger magnification), `d` = circle diameter, `exact: true` skips motion-blending. Ring + mask. | Only when a small detail is the joke (a paw in a jaw, a tiny object, the eyes). |
| `push` | Slow push-in on `focus` up to `zoom`, holds until the next cut. | Tension, a stare, a long beat. |
| `spot` | Spotlight: dims everything except around `focus` (radius `r` px). | Something enters the scene (a second cat, a reveal). |
| `freeze` | B&W high-contrast freeze frame for `dur` s + record scratch. | The big comedic hit. |
| `damage` | Short camera shake + red vignette edges + red/blue colour split (about 0.4 s). | **Only** when something gets hurt (a slap, bite, fall, scream). |
| `text` | One meme text (Impact, bounces in), `pos`, `size`, `rot`, `fill`. Drawn last so punch-ins never cover it. | At most one per video. |
| `text` + `until` | Any event can take `until` (clip time): its duration becomes the output time until that moment. Used for a small sports-style tag (e.g. `LAP 1`..`LAP 4`, size 64, top-left) that stays on for each lap: a consistent broadcast-style device instead of random meme words. | When the clip has a repeating structure. |
| `sfx` | Plays a sound: `name` (`vineboom`, `bruh`, `airhorn`, `violin`, `scratch`, `badumtss`, `waitwhat`, `bonk`, `womp`, `crickets`, `laugh`, `gasp`, `ding`, `sheesh`, or a base sfx), `g` = gain. | Match the moment. Avoid stacking sounds on the final line. |
| `shake` | Only plays the hit sound (screen shake was removed: viewers got dizzy). | Rare. |
| `flash` | White flash (also keep rare; owner dislikes fade/flash looks). | Avoid. |

### Hard "no" list from the owner
- No constant screen shake/wobble or zoom creep (made viewers dizzy). Picture stays still. Shake only as the short `damage` hit.
- No fade transitions (fade, flash fade, cross dissolve). Transitions must **move** (slide, zoom, whip, spin, stretch).
- No red "reboot / system error" effect (hated).
- No generic/template script. Every script is written for the specific clip. Banned stock phrases: "not a cat", "scientists believe", "system error", "rebooting", "plotting his revenge", "tiny lawyer", "what you are looking at".
- No reusing the same effect kit across videos "because it is available". Effects must be needed by the clip.

---

## 5. Transitions (gl-transitions via `gl_trans.py`)

`gl_trans.apply(src, dst, [(t0, "Name", duration), ...])` renders the transition by holding a still of the last frame of the old shot and transitioning the live new shot in over 0.15-0.25 s, at the start of a new sentence. `make_edit.py` puts one at 0:00 and then one at least every 3 s on a sentence start (usually 3-4 per video), each with its own real swish sound.

Moving-only kit (all verified visually): `WhipPan`, `ZoomInOut`, `TangentMotionBlur`, `WhipSpin`, `StretchSlide`, `LensPush`, `DirectionalWarp` (others downloaded: `CrossZoom`, `SimpleZoom`, `GlitchDisplace`, ...; `CrossZoom`/`Overexposure`/`FlashFade`/`FadeColor` are blends/fades: avoid).
Pick a **family per video** via `trs` (e.g. spins and zoom pulls for one video, slides and whips for another).

The shader names in the repo are listed at https://github.com/gl-transitions/gl-transitions/tree/master/transitions. Download a `.glsl` into `assets/gl/`; uniform defaults written as `// = value` are converted automatically.

---

## 6. Deciding the edit per clip (the "kit")

1. Find the joke and the 2-4 moments that matter.
2. Use effects only where a moment calls for one. 2-4 effects per video, not 6.
3. Give the video its own signature: transition family, caption accent colours, music level, ending, colour mood.
4. Spare tools I can use instead of the usual ones: slow-mo + freeze with scratch, instant replay of the best second (not built yet), slow push-in, spotlight, hand-drawn circle/arrow (not built yet), small sticker, speed ramp, rewind (not built yet), colour mood (`grade`), cinema bars (not built yet), no music or a different track.

Examples already made:
- **Croc bite clip**: magnifier in place on the paw in the jaw, two damage hits (snap and scream), vine boom + scratch on "No!", meow ending.
- **Snack-guard cat vs tabby**: slow push-in on the stare, spotlight on the intruder, B&W freeze + scratch on the slap, warm grade, almost no music, rate ending. No magnifier, no damage hit (nobody gets hurt).

---

## 7. Voice

- Engine: `edge-tts` (`pip install edge-tts`), voice `en-US-AndrewNeural` (alternatives: `GuyNeural` energetic, `BrianNeural` casual). Env overrides: `EDGE_VOICE`, `EDGE_RATE` (default `+40%`), `EDGE_PITCH` (default `+2Hz`).
- It is an online service: only the script text is sent. It occasionally drops the connection, so `voice.py` retries up to 6 times (1.2 s backoff) before falling back to the offline David voice. **If a render says "edge voice failed, using David", re-run it**: do not ship a mixed-voice video.
- ASR check: 3-6 % word error at every speed from +25 % to +45 %, so speed is not what makes words unclear. Clarity comes from: short words, no stacking sfx under the narration, and the voice chain below.
- Voice chain in the mix: high-pass 90 Hz, +3 dB presence at 3 kHz, light compression, then music is ducked by sidechain compression under the voice. sfx volume 1.2, music 0.15 (or the plan's `music`). Final `loudnorm` I=-11.
- Line pitch lift of 4 %/2 % on "!"/"?" lines. Gaps between lines about 0.04 s (pause per line is possible).
- Other engines tried and rejected: VoiceStudio KittenTTS (one 226 Hz voice, `voice` param ignored), pitch-shifted versions (user: "ugly"), David (robotic but a fallback).

### Script writing
- One sentence per line, 5-8 lines, ~60-65 words for a ~14 s video. Casual "Bro..." internet voice, specific jokes about what really happens in the frames, a hook that starts mid-action, a twist at the biggest moment, a short punchline ending.
- Split a joke across two lines when the punchline word must land on the cut ("And then the crocodile said," / "No!").
- Words per second at +40 % is roughly 4.4.

---

## 8. Captions

One chunk = up to 3 words (break at punctuation, at most 14 characters). Impact 84 px, outline 5, shadow 2, bottom margin 380 px. The accent word is the longest non-filler word. Pop animation (86 % -> 100 %, 70 ms).
Timing is **not** from speech recognition (its word starts ran late). Each line's speech start/end is known exactly (silence trimmed), so the words are spread across the line by letter count.

---

## 9. Verification and review

- **Frames**: after every render, extract frames at each transition, effect and the ending into a contact sheet and look at them. Check the effect landed on the right thing.
- **ASR**: `asr_util.words(wav)` gives word timestamps to verify caption/voice alignment.
- **Gemini** (the owner's Gemini Plus website, no API) acts as an external video/audio reviewer: the owner uploads the render and pastes feedback. Treat its advice as input, not truth: it was occasionally contradictory or hallucinated; check against the real old videos and measured numbers.
- Claude cannot hear audio. Say so when sending and ask the owner to check the sound.

---

## 10. Sound library (Myinstants, owner-approved)

Sources: myinstants.com/media/sounds/ (`vine-boom-sound-meme`, `bruh-sound-effect_WstdzdM`, `dj-airhorn-sound-effect`, `00010-sadviolin`, `cartoon-record-scratch`, `ba-dum-tss_zeVX10M`, `waitwhat_VRiHZKX`, `bonk-meme`, `wompwomp_m1ikbT9`, `crickets-chirping`, `sitcom-laughing-1_vKbjyT8`, `gasp_SJHmiqB`, `ding-sound-effect_2`, `original-sheesh`; swishes `swoosh-sound-effects`, `fast-swoosh`, `swish-woosh`, `fast-swish`, `single-swish-01`, `fast-whoosh`, `transitionswoosh`, `woosh_s21KzKN`, `woosh-sfx`, `woosh_CgcHxGh`, ...).
Each was trimmed to the useful 0.3-1.5 s (swishes: 0.38 s centred on their loudest moment, 10 ms fade in, 120 ms fade out), loudness-normalised, and slightly sped/pitched so it fits the beat.

**Copyright note**: editing a sound does not make it Content-ID-proof. Only use very short, widely used meme stingers (vine boom, bruh, airhorn, scratch, swishes). Avoid anything from songs, movie lines or TV themes.

---

## 11. Gotchas (things that broke before)

- **ffmpeg filter graph**: `scale ... eval=frame` with `t` in the expression works; overlay `enable='between(t,a,b)'`; the `ass` filter must run with `cwd=TMP` and fonts copied into TMP (`fontsdir=.`).
- Editing Python with heredocs: use `chr(10)` for newlines inside generated strings; ASS override tags (`\1c`, `\fscx`) must be in raw strings or built with `chr(92)`. A normal string turns `\f`/`\t`/`\1` into control characters and silently breaks the captions (all white, no pop).
- `make_edit.py` punch-ins are overlays: text must be drawn **after** them (already sorted last).
- `moderngl` uniforms that a shader does not use are optimized away: only set uniforms that exist (`if name in program`).
- Python in the Claude sandbox sees a virtualized `%APPDATA%\npm`, so the Claude CLI shim is not found from Python (PowerShell can run it). The user's real environment is expected to work but is unverified.
- Windows paths: pass `PYTHONIOENCODING=utf-8` when printing manifest titles (Chinese characters crash cp1252).
- `rednote_fetch.py` skips clips >60 s and ids in `data/skip_ids.json`; all ~16 older clips are in `data/used_clips.json`.

---

## 12. Open items / ideas

- Build the not-yet-built tools: instant replay with a "REPLAY" tag, rewind, hand-drawn circle/arrow, small stickers, cinema bars.
- Make Video button still uses the old auto planner; either port the hand workflow into it or keep the workflow in chat (current choice: chat).
- Better voice (ElevenLabs-class) is still wanted; Edge Andrew (+40%) is the best free option so far.
- Raw clips and old renders were moved to the Recycle Bin on 2026-11-17; fetch fresh clips with `rednote_fetch.py` when making the next video.
- After the first scheduled video publishes, pull the first stats (views and subscribers) and decide the next topic from what works.
- 3D card-flip / picture-in-picture intro idea from the old videos (not built).

---

## 13. Keeping this guide current

This file is the saved record of everything learned. Update it **every time** something new is learned or applied (a new effect, a rule from the owner, a fix, a sound source, a workflow change). Commit and push only when the owner asks.

---

## 14. Trigger words and the daily routine

Standalone messages **"daily"**, **"purr"**, **"chaos"** or **"go"** start the full routine:
1. Check channel stats and compare to last time.
2. Fetch fresh rednote clips if few are left.
3. Pick the best clip, write the script, edit and render (sections 1-9).
4. Show a dashboard: stats, today's video, to-do list, clips left.
5. Prepare the YouTube upload (title, description, tags, thumbnail) **and the Facebook Reel** (caption + hashtags, section 17). Both are scheduled for 8:00 AM Manila after the owner's yes.

Then **stop and wait**: nothing is published without the owner's clear yes in chat for that video. The owner signs in to YouTube themselves in the browser pane; the password is never entered by Claude.
Natural phrases also work: "create a new video" (steps 2-4), "status" (dashboard), "upload it" / "post it" (fill YouTube Studio, confirm once before publishing), "how are we doing" (stats and what is working). "go" only counts when it is the whole message.
Dashboard (decided): an inline page in the chat. Headline numbers are **views and subscribers** (from `data/stats_log.csv`, written by `stats.py`), plus videos ready to review, fresh clips left and a to-do list. Be honest when the data is stale or has a single point (no made-up trends).


---

## 15. Log of what was applied (newest last)

- 2026-11-17: moved all raw clips and edited videos to the Recycle Bin (kept code, guide, sounds, shaders, the 11 old reference videos) and reset `clips/manifest.json`. Videos made so far are NOT kept; rebuild from `plan_e.json` ideas in this guide if needed.
- 2026-11-17: picked the clip by **likes** from rednote (query `搞笑猫咪`, top was 272.8K likes). Rules for picking a viral clip: no burned-in text (skip clips with Chinese/English subtitles), real cats (skip AI-generated cartoon videos), never an already-famous YouTube video (copyright risk, and the channel rule is no YouTube downloads), 10-25 s long.
- 2026-11-17: zoomies/bean-bag clip edited as a sports commentary with a lap counter, a bonk on the first crash, an airhorn on the last lap, one punch-in on the first flop. No damage hit, no magnifier, no freeze: its own kit.
- Transition spacing fix: transitions are skipped within 0.5 s of a punch/flash/damage/freeze event (they fought each other); text events no longer block transitions because text is drawn last.
- 2026-11-17: the owner noticed the zoomies video had no ending. Rule: **every video ends with a call to action unless the punchline is deliberately the ending**, and the CTA should vary (`meow`, `rate`, `both`, or custom `cta_text`). Added the `both` (subscribe + comment) mode.
- 2026-11-17: GitHub repo is https://github.com/KYAHDJ/purrfectly-chaotic . The owner wants every save to be a **force push of the current files only, no old files** (`git push --force`). The repo ignores clips/output/profile (see `.gitignore`).

---

## 16. YouTube upload (Studio automation, saved login)

Scripts in `data/yt/`: `yt_lib.py` (opens Studio with the saved login in `profile/` via Playwright + installed Chrome), `upload.py <meta.json>` (uploads a video **as Private, never publishes**), `set_country.py`, `list_content.py`. **Close every Chrome window that uses `profile/` before running them.** Meta file example: `data/yt/zoomies_meta.json` (`video`, `title`, `description`, `tags`).

Owner's upload rules (2026-11-17):
- **Title**: starts with "Cat Shorts", short hook, emoji, **max 3 hashtags in the title** (e.g. `Cat Shorts: 3 PM Zoomies, 4 Laps of Chaos <emoji> #cat #zoomies #funnycats`).
- **Description**: written by Claude: one funny line about the video, the subscribe/comment ask, 3 hashtags at the end.
- **Tags**: use the maximum YouTube allows, all related to the video. YouTube counts a multi-word tag as length + 2 (quotes) plus commas, so keep `sum(len+2 if it has a space) + commas <= 500` (aim for about 470; 448 plain characters of tags was rejected as over the limit).
- **US-based**: channel country of residence set to **United States** (Settings > Channel > Basic info), channel keywords added, and on every video: **Video language = English (United States)** and **Video location = United States** (pick the first plain "United States" suggestion, not a place). Audience = "No, it's not made for kids". Do not tick TV/other restrictions.
- **Visibility**: always upload **Private** first. Never publish without the owner's yes. **Publishing time rule (decided 2026-11-17): always schedule for 8:00 AM Manila time** (the owner is in Manila, UTC+8). In US winter time that is 7 PM US Eastern / 4 PM Pacific. When US daylight saving starts (March) the same 7 PM Eastern becomes 7:00 AM Manila, so move the slot to 7:00 AM Manila then. In Studio: Content > the video > Visibility > Schedule; check the time zone shows `(GMT+0800) Local Time`; pick the date and `8:00 AM`; press Schedule (script: `data/yt/sched2.py confirm`). Scheduling publishes automatically, so only do it with the owner's yes.

How the automation works / gotchas:
- Dashboard "Upload videos" button, then `expect_file_chooser` on "Select files" to attach the mp4. Title/description boxes are `#title-textarea #textbox` / `#description-textarea #textbox`; type with the keyboard (hashtag suggestions pop up: click an empty area to dismiss, never press Escape, it closes the dialog).
- Tags must be **typed** (`keyboard.type` with commas), not `fill()`, or they do not become chips.
- Language dropdown is a long list: `tp-yt-paper-item:has-text('English (United States)')`, scroll into view and `click(force=True)`.
- "Next" is `#next-button`; wait until the footer no longer says "Uploading" before clicking it; at Visibility click the "Private" radio, then "Save".
- Do not drive Chrome through `connect_over_cdp` on a manually started Chrome: it hung. Launching Playwright's persistent context with `channel="chrome"` (as `yt_lib.py` does) works.
- Every failed run that gets past the file chooser leaves a **Draft** in Studio. Check Content and remove leftovers.
- First upload done: the zoomies video, Private, "Checks complete. No issues found."
- 2026-11-17: cleaned up 7 leftover drafts with `data/yt/drafts2.py delete` (selects only rows marked Draft, then More actions > Delete forever, and has a safety check that exactly 7 of 8 rows are drafts). Only do this with the owner's yes. Content now shows just the one Private zoomies video.
- 2026-11-17: the zoomies video was **scheduled for Nov 18, 2026, 8:00 AM Manila** (7 PM Eastern Nov 17). Studio shows it as Scheduled.

---

## 17. Facebook Reels (Meta Business Suite)

Script: `data/yt/fb_reel.py <meta.json> [confirm]` (same saved login in `profile/`; the owner signed in to Facebook once in that profile). Without `confirm` it fills everything and stops at the Share step; with `confirm` it presses the final Schedule button. Close every Chrome window using `profile/` first.

- Page: `mochineko` (0 followers when connected). Business Suite URL: `https://business.facebook.com/latest/reels_composer` (needs about 20 s to load; wait before clicking).
- Flow: "Add Video" (file chooser) > caption in the `contenteditable` box (`meta["fb_caption"]`, 3-4 hashtags; click an empty area, not Escape, to dismiss hashtag suggestions) > wait until the upload shows 100% > Next > Next > Share step > "Schedule" tab > date field (click the date box, pick the day in the calendar) > time field segments (click hour, type `08`; click minutes, type `00`; click AM/PM, type `A`) > press the bottom-right Schedule button. Facebook shows the time zone as `Asia/Shanghai`, which is the same UTC+8 as Manila.
- Same rule as YouTube: **8:00 AM Manila** (7 PM US Eastern in winter), only after the owner's yes.
- Facebook runs its own copyright check on the video ("Your video is safe to publish! No copyright issues were found." for the zoomies video).
- **US audience on Facebook**: there is no free country targeting for organic Reels. Use US English captions and the same US evening slot; true US-only targeting would be a paid ad (ask the owner first).
- 2026-11-17: the zoomies Reel was scheduled for **Nov 18, 2026, 8:00 AM Manila** ("Reel scheduled").

---

## 18. Current state (2026-11-17)

- First video (zoomies / bean-bag clip, 272.8K-like rednote clip, sports-commentary edit) is **scheduled on both YouTube and Facebook for Nov 18, 2026, 8:00 AM Manila** (7 PM US Eastern Nov 17). YouTube: private upload scheduled, title starts "Cat Shorts", 3 title hashtags, 32 tags, English (US), location United States, channel country United States. Facebook: Reel on the `mochineko` Page (the owner has not confirmed this is the intended Page name; they were told to say so if wrong).
- Local raw clips and old renders are in the Recycle Bin; `clips/manifest.json` is empty; `data/used_clips.json` keeps used ids.
- GitHub (`KYAHDJ/purrfectly-chaotic`, branch `main`) is always force pushed with the current files only.
- Next steps: after the first video publishes, pull stats (views, subscribers) with the daily routine; make the next video with the hand workflow (sections 1-9) and pick a different effects kit.

---

## 19. Video 2 (standing cat) and first stats, 2026-11-18

- **First video results (4.5 h after 8 AM Manila):** YouTube 437 views, 34 subs; Facebook Reel 252 views, 59 three-second views, avg play about 3 s, no reactions. Lesson: viewers leave early, so open with the funniest line or visual in the first second. Stats scripts: `stats.py` (YouTube) and `data/yt/fb_stats.py` (Meta Content tab).
- **Video 2:** clip `6add7f04...` (cat held upright by his paws, dead stare). Kit: circle on the held paw, slow push on the face, freeze on the wink with scratch, sfx waitwhat and crickets, `both` CTA. Transitions StretchSlide, LensPush, WhipSpin, ZoomInOut; accents orange/cyan/yellow. Output `output/standing_cat.mp4`, metadata `data/yt/standing_meta.json`. Waiting for the owner's yes before upload.
- **Gotchas:** run the renderer with `.venv/Scripts/python.exe` (system python has no `moderngl`); set `PYTHONIOENCODING=utf-8` when printing emoji; ffmpeg `drawtext` crashes here (no fontconfig), so use tile grids without text.
- Skipped clips: `6a4e1b82` (AI-generated cats in litter boxes) and `6a4e6daf` (parkour cat, has a burned-in Chinese label at caption height).

---

## 20. Learning loop (data from every video)

After each video, record its numbers in `data/video_log.csv` (one row per video) and write what it taught us here. Pull data with `.venv/Scripts/python.exe data/yt/yt_video_stats.py` (YouTube: views, viewed vs swiped away, how viewers found it) and `data/yt/fb_stats.py` (Facebook). Check at about 4 h and again at 24 h and 72 h, since Shorts keep growing. The next video's hook, length and kit must use the last rows.

**Video 1 (zoomies), 4.5 h in:** 583 YouTube views (127 of the last hour from the Shorts feed, 4 from search), 24.6% stayed to watch and 75.4% swiped away, 3 likes, 0 comments, 0 subscribers, about 4.3 s average view on a 19 s Short. Facebook: 252 views, 59 three-second views (23%), about 3 s average play.
- Both platforms agree: about 3 in 4 people leave in the first seconds. Fix the hook before anything else.
- Zero subscribers and comments: the ending CTA is only reached by a few. Put a light CTA or a question earlier, and keep the end short.
- Hook rule from now on: the funniest or most striking frame and a punchy first line inside the first 1 s (cold open), then the story.
- "Viewed vs swiped away" is the number to beat: target 40%+ stayed.

**Video 2 redone with the hook rule (2026-11-18):** cut the 4 s nap, so it opens on the pickup (cat's face and paws in motion in frame 1, hook line "Human picked him up mid nap. No warning. No consent."). Now 14.8 s. Compare its stayed-to-watch % with video 1 (24.6%) when it has data.

**Video 2 scheduled (2026-11-18):** YouTube Short "Cat Shorts: Forced Slow Dance, Zero Blinks" and the mochineko Facebook Reel, both Nov 19, 2026, 8:00 AM Manila. `fb_reel.py` now takes the day as a third argument (default 19): `fb_reel.py <meta.json> confirm <day>`. Check its numbers at about 4 h, 24 h and 72 h and fill `data/video_log.csv`.

**Day 2 check (2026-11-19, 22:20 Manila):** channel 35 subs, 1.6K views in 28 d, 2.3 h watch time.
- Video 1 (zoomies, 48 h): 1,083 YT views (1.0K from the Shorts feed, 18 from search), 28.4% stayed, 4 likes, +1 subscriber. Facebook 259 views, 61 three-second views.
- Video 2 (standing cat, 14 h): 576 YT views, 22.5% stayed (worse than video 1 even with the cold open), 12 likes (3x video 1), 0 subs. Facebook 80 three-second views, avg play 4 s.
- **Audience:** video 1's views are 36% Philippines and only 14% United States. The 8 AM Manila slot reaches the Shorts feed in the Philippines, so the US-prime-time plan is not translating into US viewers yet. Worth testing a different slot or accepting the PH audience.
- Lessons: a calm clip with a slow hold loses people even with a cold open; people like it more but do not stay for it. Pick clips with big, readable motion in the first second.

**Video 3 (croc dentist cat, 2026-11-19):** clip `689db55f`, 13.4 s. Hook per the day-2 lessons: motion in frame 1, short runtime, a clear setup and snap. Kit: slow push on the paw, damage on the snap (something really gets hurt), violin then vineboom. Transitions DirectionalWarp, TangentMotionBlur; accents green/amber. Output `output/croc_cat.mp4`, metadata `data/yt/croc_meta.json`. Waiting for the owner's yes.

**Video 3 scheduled (2026-11-19):** YouTube Short "Cat Shorts: Cat vs Crocodile Dentist, He Lost" and the mochineko Reel, both Nov 20, 2026, 8:00 AM Manila (verified on screen). Gotcha: `fb_reel.py <meta> confirm <day>` needs the day as the third argument (default 19), otherwise Facebook rejects the past time; always check `data/clipsheets/fb_d5.png` shows the right date. Check its numbers at about 4 h, 24 h, 72 h.

## 21. Day 3 check (2026-11-20, 21:13 Manila)

Channel: 37 subs (+2), 2.5K views in 28 d, 3.7 h watch.
- **Video 3 (croc dentist cat, 13 h): 600 views, 50.6% stayed to watch (about double the others), +2 subscribers.** Facebook shows 0 so far (Meta reports late; it is published).
- Video 2 (standing cat, 37 h): 787 views, 27.3% stayed, 14 likes, 0 subs, 67% Philippines.
- Video 1 (zoomies, 61 h): about 1.2K views, 29.1% stayed, +2 subs overall, geography 34% US / 31% Philippines.
- **What worked in video 3:** motion in frame 1, short (13 s), a clear setup then a real hurt moment (snap) with the damage effect, one slow push for tension. Calm hold clips (video 2) do not retain. Keep: big readable motion, short, a payoff before 8 s.

**Video 4 (bottle-pack cat, 2026-11-20):** clip `68db5ecc` (357.8K likes, 15 s). Rejected: parkour cat (AI-looking, morphing limbs, burned label) and a compilation of different cats. Hook: spotlight on the stuck head in frame 1. Kit: spot, bonk on the fall, punch on the innocent stare, cold grade, WhipPan/ZoomInOut; accents amber/magenta/cyan. Output `output/bottle_cat.mp4`, metadata `data/yt/bottle_meta.json`. New clips fetched with `rednote_fetch.py "猫猫 翻车 搞笑" 8` (action-focused search works). Waiting for the owner's yes.

**Video 4 scheduled (2026-11-20):** YouTube Short "Cat Stuck in a Bottle Pack, Zero Plan" and the mochineko Reel, both Nov 21, 2026, 8:00 AM Manila (verified on screen). `fb_reel.py` now has a date guard: it only presses Schedule when the form shows the right day (reads the input values, since the date is not in the page text) and prints `date ok: True/False`. Check numbers at about 4 h, 24 h, 72 h.
