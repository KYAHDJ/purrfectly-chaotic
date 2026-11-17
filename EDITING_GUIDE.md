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

- Build the not-yet-built tools: instant replay with "REPLAY" tag, rewind, hand-drawn circle/arrow, small stickers, cinema bars.
- Make Video button still uses the old auto planner; either port the hand workflow into it or keep the workflow in chat.
- Better voice (ElevenLabs-class) is still wanted; Edge Andrew is the best available free option so far.
- Clip search for more fresh clips (7 fresh clips already downloaded and unedited).
- 3D card-flip / picture-in-picture intro idea from the old videos (not built).
