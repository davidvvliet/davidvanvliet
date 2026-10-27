# Is a published model (public/models/<probe>.glb) behind the repo? Exports differ byte for byte
# between identical builds, so approve records a fingerprint of what the build reads instead,
# in published.json (committed, so it is true for the repo):
#   specs/<probe>.json, probes/<probe>.py, build.py, blender.json, lib/*.py (but this file), and the files in
#   refs/<probe>/ (outside sources/) that the spec, probe script, build.py or lib/ name.
# Plain Python (no bpy). app/api/models/[...path]/route.ts reads the same file for the dashboard.
import glob, hashlib, json, os, re, time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RECORD = os.path.join(HERE, "published.json")

def _hash(path):
    return hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]

def inputs(probe):
    """{path relative to the harness: content hash} of everything the build of `probe` reads."""
    code = [f"specs/{probe}.json", f"probes/{probe}.py", "build.py", "blender.json"]
    code += sorted(os.path.relpath(p, HERE) for p in glob.glob(os.path.join(HERE, "lib", "*.py"))
                   if os.path.basename(p) != "published.py")
    code = [c for c in code if os.path.exists(os.path.join(HERE, c))]
    text = "\n".join(open(os.path.join(HERE, c), encoding="utf-8", errors="replace").read() for c in code)
    refs = []
    for p in sorted(glob.glob(os.path.join(HERE, "refs", probe, "*"))):
        name = os.path.basename(p)
        stem = os.path.splitext(name)[0]
        if os.path.isfile(p) and re.search(rf"\b{re.escape(stem)}\b", text):
            refs.append(os.path.relpath(p, HERE))
    return {c: _hash(os.path.join(HERE, c)) for c in code + refs}

def _read():
    try:
        return json.load(open(RECORD))
    except (OSError, ValueError):
        return {}

def record(probe):
    """Called by approve: the published model now matches these inputs."""
    rec = _read()
    rec[probe] = {"approved": time.strftime("%Y-%m-%d %H:%M"), "inputs": inputs(probe)}
    with open(RECORD, "w") as f:
        json.dump(dict(sorted(rec.items())), f, indent=1)
        f.write("\n")

def behind(probe):
    """None if never recorded, else the input paths changed, added or removed since approve."""
    rec = _read().get(probe)
    if rec is None:
        return None
    now, then = inputs(probe), rec["inputs"]
    return sorted(p for p in set(now) | set(then) if now.get(p) != then.get(p))

def own(probe, path):
    """True for the probe's own files; the rest is harness code every probe shares."""
    return path in (f"specs/{probe}.json", f"probes/{probe}.py") or path.startswith(f"refs/{probe}/")

if __name__ == "__main__":
    # For the dashboard: {probe: null (never approved) | {"own": [...], "shared": [...]}}.
    out = {}
    for probe in sorted(_read()):
        changed = behind(probe)
        out[probe] = {"own": [c for c in changed if own(probe, c)], "shared": [c for c in changed if not own(probe, c)]}
    print(json.dumps(out))
