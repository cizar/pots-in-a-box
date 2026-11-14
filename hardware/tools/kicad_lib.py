# SPDX-License-Identifier: CERN-OHL-S-2.0
# Copyright (C) 2026 Cesar Kastli
"""Minimal KiCad symbol-library reader: s-expression parser, symbol
flattening (extends) and pin extraction. Used by gen_schematic.py."""
import re
from pathlib import Path

KICAD_SYMBOLS = Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols")
_TOKEN = re.compile(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+')


def parse(text):
    """Parse an s-expression into nested lists of str (quoted strings keep quotes)."""
    stack, cur = [], []
    for m in _TOKEN.finditer(text):
        t = m.group(0)
        if t == "(":
            stack.append(cur)
            cur = []
        elif t == ")":
            done, cur = cur, stack.pop()
            cur.append(done)
        else:
            cur.append(t)
    return cur[0]


def dump(node, indent=0):
    """Serialize nested lists back to s-expression text."""
    if not isinstance(node, list):
        return node
    if all(not isinstance(x, list) for x in node):
        return "(" + " ".join(node) + ")"
    pad = "\t" * (indent + 1)
    parts = []
    for x in node:
        parts.append(dump(x, indent + 1) if isinstance(x, list) else x)
    head = []
    rest = []
    for p, x in zip(parts, node):
        (rest if isinstance(x, list) else head).append(p)
    return "(" + " ".join(head) + "\n" + "\n".join(pad + r for r in rest) + "\n" + "\t" * indent + ")"


def unq(s):
    return s[1:-1] if s.startswith('"') else s


def find(node, key):
    return [x for x in node if isinstance(x, list) and x and x[0] == key]


_lib_cache = {}


def load_lib(path):
    path = Path(path)
    if path not in _lib_cache:
        root = parse(path.read_text())
        _lib_cache[path] = {unq(s[1]): s for s in find(root, "symbol")}
    return _lib_cache[path]


def flatten(lib, name):
    """Return a deep copy of symbol `name` with `extends` resolved."""
    import copy
    sym = copy.deepcopy(lib[name])
    ext = find(sym, "extends")
    if not ext:
        return sym
    parent = flatten(lib, unq(ext[0][1]))
    own_props = {unq(p[1]): p for p in find(sym, "property")}
    out = [x for x in parent if not (isinstance(x, list) and x[0] == "property")]
    out[1] = f'"{name}"'
    props = []
    for p in find(parent, "property"):
        props.append(own_props.pop(unq(p[1]), p))
    props += own_props.values()
    # Rename unit sub-symbols Parent_U_S -> Name_U_S.
    pname = unq(parent[1])
    for sub in find(out, "symbol"):
        sub[1] = '"' + unq(sub[1]).replace(pname, name, 1) + '"'
    # Insert properties right after the header items.
    idx = next(i for i, x in enumerate(out) if isinstance(x, list) and x[0] == "symbol")
    return out[:idx] + props + out[idx:]


def pins(sym):
    """{number: dict(name, type, x, y, angle, unit)} from a flattened symbol."""
    res = {}
    for sub in find(sym, "symbol"):
        unit = int(unq(sub[1]).rsplit("_", 2)[-2])
        for p in find(sub, "pin"):
            at = find(p, "at")[0]
            num = unq(find(p, "number")[0][1])
            res[num] = dict(name=unq(find(p, "name")[0][1]), type=p[1],
                            x=float(at[1]), y=float(at[2]), angle=float(at[3]), unit=unit)
    return res


def get(lib_id, project_lib=None):
    libname, name = lib_id.split(":")
    path = project_lib if libname == "pots" else KICAD_SYMBOLS / f"{libname}.kicad_sym"
    return flatten(load_lib(path), name)


if __name__ == "__main__":
    import sys
    for lib_id in sys.argv[1:]:
        s = get(lib_id)
        print(lib_id, {k: (v["name"], v["type"]) for k, v in sorted(pins(s).items(), key=lambda kv: kv[0].zfill(3))})
