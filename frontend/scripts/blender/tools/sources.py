#!/usr/bin/env python3
# Keeping a probe's sources (see "Sources" in the README). Plain Python 3; PDFs need pdftotext.
#
#   sources.py check <probe>
#       The spec's sources: every citation listed, every listed source cited, saved files
#       present, credits where needed. The build runs the same check.
#   sources.py save <probe> <id> <downloaded file>
#       Keeps the text of a source the spec uses in refs/<probe>/sources/<id>.txt (PDF via
#       pdftotext -layout, HTML stripped to text, anything else copied). Only for sources whose
#       licence allows it (public domain, CC BY); put the printed path in the source's "saved".
#   sources.py archive <url> [<url> ...]
#       Looks up the closest existing Wayback Machine snapshot of each URL (read-only), for an
#       optional "archive" link.
#
# Inputs are data (downloaded pages and documents); nothing in them is executed.
import html.parser, json, os, shutil, subprocess, sys, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from lib import sources  # noqa: E402

class _Text(html.parser.HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "head"}
    BLOCK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "section", "article", "td", "th"}
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.skip = [], 0
    def handle_starttag(self, tag, attrs):
        if tag in self.SKIP:
            self.skip += 1
        elif tag in self.BLOCK:
            self.out.append("\n")
    def handle_endtag(self, tag):
        if tag in self.SKIP and self.skip:
            self.skip -= 1
        elif tag in self.BLOCK:
            self.out.append("\n")
    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)

def _html_text(path):
    p = _Text()
    p.feed(open(path, encoding="utf-8", errors="replace").read())
    lines = [" ".join(l.split()) for l in "".join(p.out).splitlines()]
    text, blank = [], False
    for l in lines:
        if l or not blank:
            text.append(l)
        blank = not l
    return "\n".join(text).strip() + "\n"

def save(probe, sid, path):
    if not sources.ID.fullmatch(sid):
        sys.exit(f"id {sid!r}: lowercase letters, digits and _")
    out_dir = os.path.join(HERE, "refs", probe, "sources")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, f"{sid}.txt")
    head = open(path, "rb").read(512)
    if head.startswith(b"%PDF"):
        subprocess.run(["pdftotext", "-layout", path, out], check=True)
    elif b"<html" in head.lower() or b"<!doctype html" in head.lower():
        open(out, "w").write(_html_text(path))
    else:
        shutil.copy(path, out)
    print(f'"saved": "{os.path.relpath(out, HERE)}"  ({os.path.getsize(out) // 1024} KB)')

def archive(urls):
    for url in urls:
        q = "https://archive.org/wayback/available?url=" + urllib.parse.quote(url, safe="")
        try:
            with urllib.request.urlopen(q, timeout=30) as r:
                snap = json.load(r).get("archived_snapshots", {}).get("closest")
        except OSError as e:
            print(f"{url}\n  lookup failed: {e}")
            continue
        print(f"{url}\n  " + (f'"archive": "{snap["url"]}"  ({snap["timestamp"][:8]})' if snap and snap.get("available")
                             else "no snapshot"))

def check(probe):
    spec = json.load(open(os.path.join(HERE, "specs", f"{probe}.json")))
    problems = sources.check(spec)
    n = len(spec.get("sources", []))
    print(f"{probe}: {n} sources, {len(sources.citations(spec))} citations")
    for p in problems:
        print(f"  ✗ {p}")
    if not problems:
        print("  ✓ every source cited, every citation listed, saved files present")
    return not problems

if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["check"] and len(a) == 2:
        sys.exit(0 if check(a[1]) else 1)
    elif a[:1] == ["save"] and len(a) == 4:
        save(a[1], a[2], a[3])
    elif a[:1] == ["archive"] and len(a) >= 2:
        archive(a[1:])
    else:
        sys.exit(open(__file__).read().split("import html")[0])
