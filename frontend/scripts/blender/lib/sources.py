# A spec's sources: the list of everything used, and every citation of it. Plain Python (no
# bpy), so specs can be checked while researching, before anything is built.
#
# The spec's top-level "sources" lists each source once:
#   {"id": "nssdca", "title": ..., "url": ..., "licence": ..., "read": "2026-10-27",
#    "saved": "refs/<probe>/sources/nssdca.txt" (when the licence allows), optional "archive",
#    "credit": "line for the site's credits"}
# Everything else cites by id: "source": "nssdca" or "nssdca, p.83" (id, then where or how),
# a list of those, or "sources": [{"source": "nssdca", "quote": ...}, ...].
import os
import re

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ID = re.compile(r"[a-z0-9_]+")
FIXTURE_SOURCES = ("design value",)

def cited_id(citation):
    """The source id a citation string starts with ("nssdca, p.83" -> "nssdca")."""
    m = ID.match(citation)
    return m.group(0) if m else ""

def citations(spec):
    """(path, citation string) for every `source` in the spec, outside the source list."""
    out = []
    def walk(o, path):
        if isinstance(o, dict):
            for k, v in o.items():
                if path == "" and k == "sources":
                    continue
                if k == "source":
                    for c in (v if isinstance(v, list) else [v]):
                        out.append((f"{path}.source", c))
                else:
                    walk(v, f"{path}.{k}")
        elif isinstance(o, list):
            for i, v in enumerate(o):
                walk(v, f"{path}[{i}]")
    walk(spec, "")
    return out

def check(spec):
    """Problems with the spec's sources: [] when fine."""
    fixture = spec.get("fixture")
    problems = []
    listed = {}
    for i, s in enumerate(spec.get("sources", [])):
        sid = s.get("id", "")
        if not ID.fullmatch(sid):
            problems.append(f"sources[{i}]: id {sid!r} must be lowercase letters, digits and _")
            continue
        if sid in listed:
            problems.append(f"{sid}: listed twice")
        listed[sid] = s
        for field in ("title", "url", "licence"):
            if not s.get(field):
                problems.append(f"{sid}: no {field}")
        if s.get("saved") and not os.path.exists(os.path.join(HERE, s["saved"])):
            problems.append(f"{sid}: saved file {s['saved']} is missing")
    used = set()
    for path, c in citations(spec):
        if not isinstance(c, str):
            problems.append(f"{path}: citation is not a string")
            continue
        sid = cited_id(c)
        if sid in listed:
            used.add(sid)
        elif not (fixture and c.startswith(FIXTURE_SOURCES)):
            problems.append(f"{path}: cites {c[:40]!r}, not a listed source id")
    for sid in listed:
        if sid not in used:
            problems.append(f"{sid}: listed but never cited")
    ref = spec.get("reference_model") or {}
    if ref.get("url"):
        sid = cited_id(ref.get("source", ""))
        if sid not in listed:
            problems.append("reference_model: needs a source id")
        elif not listed[sid].get("credit"):
            problems.append(f"{sid}: the reference model shapes what ships, so it needs a credit")
    return problems

def credits(spec):
    """Credit lines of the sources that have one, in list order."""
    return [s["credit"] for s in spec.get("sources", []) if s.get("credit")]
