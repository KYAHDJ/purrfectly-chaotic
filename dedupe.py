"""Delete duplicate clips (identical bytes under different rednote IDs) and fix the manifest."""
import hashlib, json, pathlib
clips = pathlib.Path("clips"); mp = clips / "manifest.json"
man = json.loads(mp.read_text(encoding="utf-8")); used_p = pathlib.Path("data/used_clips.json")
used = set(json.loads(used_p.read_text(encoding="utf-8"))) if used_p.exists() else set()
skip_p = pathlib.Path("data/skip_ids.json")
skip = set(json.loads(skip_p.read_text(encoding="utf-8"))) if skip_p.exists() else set()
seen, keep = {}, []
for m in man:
    f = clips / m["file"]
    if not f.exists(): continue
    h = hashlib.md5(f.read_bytes()).hexdigest()
    if h in seen:
        print("duplicate:", m["file"], "==", seen[h]); f.unlink(); skip.add(m["id"])
        if m["id"] in used: used.add(seen[h].split("rn_")[1][:24])
        continue
    seen[h] = m["file"]; m["hash"] = h; keep.append(m)
skip_p.parent.mkdir(exist_ok=True); skip_p.write_text(json.dumps(sorted(skip)), encoding="utf-8")
mp.write_text(json.dumps(keep, indent=2, ensure_ascii=False), encoding="utf-8")
used_p.write_text(json.dumps(sorted(used)), encoding="utf-8")
print("clips kept:", len(keep))
