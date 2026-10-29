# KiCad's file format: S-expressions. Parse to nested lists (atoms as str, quoted strings as Q), write back.
import re

class Q(str):
    """A quoted string atom."""

TOKEN = re.compile(r'\s*(?:(\()|(\))|"((?:[^"\\]|\\.)*)"|([^\s()"]+))')

def parse(text):
    stack, cur = [], []
    for m in TOKEN.finditer(text):
        if m.group(1): stack.append(cur); cur = []
        elif m.group(2): done = cur; cur = stack.pop(); cur.append(done)
        elif m.group(3) is not None: cur.append(Q(m.group(3).replace('\\"', '"').replace("\\\\", "\\")))
        elif m.group(4): cur.append(m.group(4))
    return cur

def dump(x, depth=0):
    if isinstance(x, list):
        simple = all(not isinstance(c, list) for c in x)
        if simple: return "(" + " ".join(dump(c) for c in x) + ")"
        head = [c for c in x if not isinstance(c, list)]
        body = "\n".join("\t" * (depth + 1) + dump(c, depth + 1) for c in x if isinstance(c, list))
        return "(" + " ".join(dump(c) for c in head) + "\n" + body + "\n" + "\t" * depth + ")"
    if isinstance(x, Q): return '"' + x.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return str(x)

def find(node, key):
    """Children of `node` that are lists starting with `key`."""
    return [c for c in node if isinstance(c, list) and c and c[0] == key]

def first(node, key, default=None):
    f = find(node, key)
    return f[0] if f else default
