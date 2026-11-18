# SPDX-License-Identifier: CERN-OHL-S-2.0
# Copyright (C) 2026 Cesar Kastli
"""Copies part positions edited by hand in KiCad back into gen_pcb.py.

Workflow: run gen_pcb.py, open the board in KiCad, move or rotate parts, save,
then run (with KiCad's Python, like gen_pcb.py):

    /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \\
        hardware/tools/pull_layout.py

It generates a fresh board in a temporary file and compares it with the saved
one, part by part. Every part that moved is written back:

- a line part (L1 or L2) updates LINE_LAYOUT; the other lines follow it on the
  next run. If L1 and L2 were both moved differently, L1 wins, unless
  `--line L2` (or any line) is given: then only that line is read.
- a shared part updates its SHARED_LAYOUT entry, or gets a new one if it was
  placed automatically until now.
- parts on the panel edges (EDGE_PARTS) and mounting holes are only reported.

Tracks are ignored. Run it right after editing a board made by the current
gen_pcb.py: if the script changed since, the comparison is meaningless.
"""
import argparse
import re
import tempfile
from pathlib import Path

import pcbnew

import gen_pcb as g

SCRIPT = Path(g.__file__)
TOL = 0.5  # mil


def snapshot(path):
    """Origin (pad 1) in mil and rotation per ref, relative to the board outline
    (KiCad may move the whole board on the sheet when it is saved)."""
    board = pcbnew.LoadBoard(str(path))
    corners = [pt for d in board.GetDrawings() if d.GetLayer() == pcbnew.Edge_Cuts
               for pt in (d.GetStart(), d.GetEnd())]   # vertices, not the stroked bbox
    ox = pcbnew.ToMils(min(c.x for c in corners))
    oy = pcbnew.ToMils(min(c.y for c in corners))
    out = {}
    for fp in board.GetFootprints():
        p = fp.GetPosition()
        out[fp.GetReference()] = (round(pcbnew.ToMils(p.x) - ox, 1), round(pcbnew.ToMils(p.y) - oy, 1),
                                  round(fp.GetOrientationDegrees()) % 360)
    return out


def moved(a, b):
    return abs(a[0] - b[0]) > TOL or abs(a[1] - b[1]) > TOL or a[2] != b[2]


def num(v):
    """mil value as written in gen_pcb.py: whole mils, unless the part is off grid."""
    return f"{v:g}" if abs(v - round(v)) > 0.05 else f"{round(v)}"


def fmt_shared(x, y, rot):
    xs = f"SHARED_X + {num(x - g.SHARED_X)}" if x >= g.SHARED_X else num(x)
    ys = f"FRONT + {num(y - g.FRONT)}" if y >= g.FRONT else num(y)
    return f"({xs}, {ys}, {rot})"


def set_entry(src, table, ref, value):
    """Replaces "ref": (...) inside the given table, or appends it to the table."""
    start = src.index(f"\n{table} = {{")
    end = src.index("\n}", start)
    body = src[start:end]
    new, n = re.subn(rf'"{ref}": \([^()]*\)', f'"{ref}": {value}', body)
    if n == 0:
        new = body + f'\n    "{ref}": {value},   # placed by hand in KiCad'
    return src[:start] + new + src[end:]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--line", help="read line parts only from this line (L1, L2, ...)")
    ap.add_argument("--dry-run", action="store_true", help="report, don't write gen_pcb.py")
    args = ap.parse_args()
    line_idx = range(len(g.LINES))
    if args.line:
        line_idx = [g.LINES.index(f"line_{args.line.upper()}")]
    saved_path = g.ROOT / f"{g.PROJECT}.kicad_pcb"
    fresh_path = Path(tempfile.mkdtemp()) / "fresh.kicad_pcb"
    g.main(fresh_path)
    saved, fresh = snapshot(saved_path), snapshot(fresh_path)
    src = SCRIPT.read_text()
    changes, notes = [], []

    line_refs = set(g.LINE_LAYOUT)
    for ref in g.LINE_LAYOUT:
        picks = []
        for i in line_idx:
            r = g.line_ref(ref, i)
            if r in saved and moved(saved[r], fresh[r]):
                x, y, rot = saved[r]
                picks.append((r, x - g.line_x0(i), y, rot))
        if not picks:
            continue
        if len({p[1:] for p in picks}) > 1:
            notes.append(f"{ref}: lines moved differently, kept {picks[0][0]}")
        _, x, y, rot = picks[0]
        value = f"({num(x)}, {num(y)}, {rot})"
        src = set_entry(src, "LINE_LAYOUT", ref, value)
        changes.append(f"{ref} (line) -> {value}")
        off = [v for v in (x, y) if v % 50]
        if off:
            notes.append(f"{ref}: off the 50 mil grid (set KiCad's grid to 50 mil when moving parts)")

    copies = {g.line_ref(r, i) for r in line_refs for i in range(len(g.LINES))}
    edge = set()
    for r in g.EDGE_PARTS:  # line edge parts (J101) stand for every line
        is_line = re.fullmatch(r"[A-Z]+1\d\d", r)
        edge |= {g.line_ref(r, i) for i in range(len(g.LINES))} if is_line else {r}
    for ref in sorted(saved):
        if ref in copies or ref not in fresh or not moved(saved[ref], fresh[ref]):
            continue
        if ref in edge or ref.startswith("H"):
            notes.append(f"{ref}: moved, but edge parts and holes are set in EDGE_PARTS / code")
            continue
        value = fmt_shared(*saved[ref])
        src = set_entry(src, "SHARED_LAYOUT", ref, value)
        changes.append(f"{ref} (shared) -> {value}")

    if changes and not args.dry_run:
        SCRIPT.write_text(src)
    print("\n".join(changes) or "no moved parts")
    for n in notes:
        print("note:", n)


if __name__ == "__main__":
    main()
