# SPDX-License-Identifier: CERN-OHL-S-2.0
# Copyright (C) 2026 Cesar Kastli
"""Generates a first, unrouted placement of the POTS in a box PCB.

Run it with KiCad's own Python (it needs the pcbnew module):

    /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3 \\
        hardware/tools/gen_pcb.py

It exports the netlist from the schematic, loads every footprint, gives each pad
its net (so KiCad shows the ratsnest), and places the parts block by block:
connectors on the rear edge, LEDs and the AR/US switch header on the front edge,
mounting holes in the corners. Nothing is routed. The goal of this version is
the board size, the connector positions and the component heights, so the
enclosure can be chosen. Re-running overwrites hardware/kicad/pots-in-a-box.kicad_pcb.
"""
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

import pcbnew

ROOT = Path(__file__).resolve().parents[1] / "kicad"
PROJECT = "pots-in-a-box"
CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
FOOTPRINTS = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"

BOARD_W, BOARD_H = 160.0, 100.0   # mm; x = along the rear panel, y = towards the front
HOLE_INSET = 4.0                  # mounting-hole centre from each edge
HOLE_KEEPOUT = 8.0                # square kept free around each hole
GAP = 1.0                         # clearance between courtyards
STEP = 0.5                        # placement search grid

# Blocks: (x0, y0, x1, y1) in mm, origin at the rear-left corner. Rear edge = y 0.
REGIONS = {
    "line_L1": (0, 0, 58, 64),
    "power": (58, 0, 102, 42),
    "line_L2": (102, 0, 160, 64),
    "ring": (0, 64, 58, 100),
    "mcu": (58, 42, 102, 100),
    "link": (102, 64, 160, 100),
}
# Space kept free in the link block for the on-board boost that replaces the module.
BOOST_RESERVED = (127, 66, 158, 92)

# Parts with a fixed place: ref -> (edge, x centre, rotation). The part's front
# face (fab outline) touches that edge.
EDGE_PARTS = {
    "J101": ("rear", 22.0, 180),   # RJ11 line 1
    "J1": ("rear", 80.0, 270),     # 12 V jack
    "J201": ("rear", 138.0, 180),  # RJ11 line 2
    "D2": ("front", 66.0, 0),      # PWR LED
    "SW1": ("front", 80.0, 90),    # header to the AR/US panel switch
    "D10": ("front", 94.0, 0),     # CALL LED
}
EDGE_MARGIN = {"rear": 0.0, "front": 1.5}

SILK = [  # (text, x, y, size)
    ("L1", 22, 22, 2.0), ("12V", 80, 18, 2.0), ("L2", 138, 22, 2.0),
    ("PWR", 66, 91, 1.2), ("AR/US", 80, 90, 1.2), ("CALL", 94, 91, 1.2),
    ("POTS in a box", 139, 96, 1.8),
    ("future on-board boost", 142.5, 79, 1.2),
]

# The KiCad library has no 3D model for the RJ12 jack: a plain box stands in for it
# so the render shows its height. Box in footprint coordinates (mm): x, y, height.
RJ_BODY = ((-3.47, 9.83), (-1.28, 16.82), 11.7)
PLACEHOLDER_DIR = ROOT / "3d"


def mm(v):
    return pcbnew.FromMM(v)


def export_netlist():
    out = Path(tempfile.mkdtemp()) / "net.xml"
    subprocess.run([CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", str(out),
                    str(ROOT / f"{PROJECT}.kicad_sch")], check=True, capture_output=True)
    return ET.parse(out).getroot()


def block_of(comp):
    sheet = comp.find("sheetpath").get("names").strip("/")
    return sheet or "power"


def courtyard(fp):
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False)
    return [pcbnew.ToMM(v) for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())]


def fab_box(fp):
    xs, ys = [], []
    for g in fp.GraphicalItems():
        if g.GetLayer() == pcbnew.F_Fab and g.GetClass() == "PCB_SHAPE":
            b = g.GetBoundingBox()
            xs += [b.GetLeft(), b.GetRight()]
            ys += [b.GetTop(), b.GetBottom()]
    return [pcbnew.ToMM(v) for v in (min(xs), min(ys), max(xs), max(ys))]


def write_box_wrl(path, xr, yr, h):
    """VRML 2 box (KiCad units: 1 = 0.1 inch; VRML y = -board y)."""
    u = 2.54
    xs, ys = [v / u for v in xr], [-v / u for v in yr]
    pts = [(x, y, z / u) for z in (0, h) for y in ys for x in xs]
    faces = "0,1,3,2,-1, 4,6,7,5,-1, 0,4,5,1,-1, 2,3,7,6,-1, 0,2,6,4,-1, 1,5,7,3,-1"
    coords = ", ".join(f"{x:.4f} {y:.4f} {z:.4f}" for x, y, z in pts)
    path.parent.mkdir(exist_ok=True)
    path.write_text(
        "#VRML V2.0 utf8\n"
        "Shape { appearance Appearance { material Material { diffuseColor 0.85 0.85 0.8 } }\n"
        f"  geometry IndexedFaceSet {{ coord Coordinate {{ point [ {coords} ] }}\n"
        f"    coordIndex [ {faces} ] }} }}\n")


def set_placeholder_model(fp, name):
    fp.Models().clear()
    m = pcbnew.FP_3DMODEL()
    m.m_Filename = "${KIPRJMOD}/3d/" + name
    fp.Models().push_back(m)


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


class Placer:
    def __init__(self):
        k = HOLE_KEEPOUT
        self.used = [(0, 0, k, k), (BOARD_W - k, 0, BOARD_W, k),
                     (0, BOARD_H - k, k, BOARD_H), (BOARD_W - k, BOARD_H - k, BOARD_W, BOARD_H),
                     BOOST_RESERVED]

    def move(self, fp, x, y):
        fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        box = courtyard(fp)
        self.used.append((box[0] - GAP / 2, box[1] - GAP / 2, box[2] + GAP / 2, box[3] + GAP / 2))

    def fit(self, fp, region):
        """First free spot scanning rows top to bottom, left to right."""
        fp.SetPosition(pcbnew.VECTOR2I(0, 0))
        l, t, r, b = courtyard(fp)
        w, h = r - l + GAP, b - t + GAP
        x0, y0, x1, y1 = region
        y = y0
        while y + h <= y1 + 1e-6:
            x = x0
            while x + w <= x1 + 1e-6:
                cand = (x, y, x + w, y + h)
                if not any(overlaps(cand, u) for u in self.used):
                    self.move(fp, x + GAP / 2 - l, y + GAP / 2 - t)
                    return True
                x += STEP
            y += STEP
        return False


def place_on_edge(placer, fp, edge, xc, rot):
    fp.SetOrientationDegrees(rot)
    fp.SetPosition(pcbnew.VECTOR2I(0, 0))
    l, t, r, b = fab_box(fp)
    x = xc - (l + r) / 2
    y = EDGE_MARGIN[edge] - t if edge == "rear" else BOARD_H - EDGE_MARGIN[edge] - b
    placer.move(fp, x, y)


def add_outline(board):
    pts = [(0, 0), (BOARD_W, 0), (BOARD_W, BOARD_H), (0, BOARD_H)]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pcbnew.VECTOR2I(mm(x0), mm(y0)))
        s.SetEnd(pcbnew.VECTOR2I(mm(x1), mm(y1)))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(mm(0.1))
        board.Add(s)
    x0, y0, x1, y1 = BOOST_RESERVED
    r = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_RECT)
    r.SetStart(pcbnew.VECTOR2I(mm(x0), mm(y0)))
    r.SetEnd(pcbnew.VECTOR2I(mm(x1), mm(y1)))
    r.SetLayer(pcbnew.F_SilkS)
    r.SetWidth(mm(0.12))
    board.Add(r)


def add_dimension(board, a, b, offset):
    d = pcbnew.PCB_DIM_ALIGNED(board, pcbnew.PCB_DIM_ALIGNED_T)
    d.SetStart(pcbnew.VECTOR2I(mm(a[0]), mm(a[1])))
    d.SetEnd(pcbnew.VECTOR2I(mm(b[0]), mm(b[1])))
    d.SetHeight(mm(offset))
    d.SetLayer(pcbnew.Dwgs_User)
    board.Add(d)


def add_text(board, text, x, y, size):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
    t.SetLayer(pcbnew.F_SilkS)
    t.SetTextSize(pcbnew.VECTOR2I(mm(size), mm(size)))
    t.SetTextThickness(mm(size * 0.15))
    board.Add(t)


def main():
    write_box_wrl(PLACEHOLDER_DIR / "rj12_body.wrl", *RJ_BODY)
    root = export_netlist()
    board = pcbnew.CreateEmptyBoard()
    board.SetCopperLayerCount(2)

    nets = {}
    pad_net = {}
    for net in root.find("nets"):
        name = net.get("name")
        item = pcbnew.NETINFO_ITEM(board, name)
        board.Add(item)
        nets[name] = item
        for node in net.findall("node"):
            pad_net[(node.get("ref"), node.get("pin"))] = item

    blocks = {}
    for comp in root.find("components"):
        ref = comp.get("ref")
        lib, name = comp.findtext("footprint").split(":")
        fp = pcbnew.FootprintLoad(f"{FOOTPRINTS}/{lib}.pretty", name)
        fp.SetReference(ref)
        fp.SetValue(comp.findtext("value"))
        fp.SetFPIDAsString(f"{lib}:{name}")
        sheet = comp.find("sheetpath").get("tstamps")
        fp.SetPath(pcbnew.KIID_PATH(sheet + comp.findtext("tstamps")))
        for pad in fp.Pads():
            item = pad_net.get((ref, pad.GetNumber()))
            if item:
                pad.SetNet(item)
        if name.startswith("RJ12_"):
            set_placeholder_model(fp, "rj12_body.wrl")
        board.Add(fp)
        blocks.setdefault(block_of(comp), []).append(fp)

    placer = Placer()
    for i, (x, y) in enumerate([(HOLE_INSET, HOLE_INSET), (BOARD_W - HOLE_INSET, HOLE_INSET),
                                (HOLE_INSET, BOARD_H - HOLE_INSET),
                                (BOARD_W - HOLE_INSET, BOARD_H - HOLE_INSET)]):
        h = pcbnew.FootprintLoad(f"{FOOTPRINTS}/MountingHole.pretty", "MountingHole_3.2mm_M3")
        h.SetReference(f"H{i + 1}")
        h.SetValue("M3")
        h.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        board.Add(h)

    by_ref = {fp.GetReference(): fp for fps in blocks.values() for fp in fps}
    for ref, (edge, xc, rot) in EDGE_PARTS.items():
        place_on_edge(placer, by_ref[ref], edge, xc, rot)

    failed = []
    for block, fps in blocks.items():
        free = [fp for fp in fps if fp.GetReference() not in EDGE_PARTS]
        free.sort(key=lambda f: -((courtyard(f)[2] - courtyard(f)[0]) * (courtyard(f)[3] - courtyard(f)[1])))
        for fp in free:
            if not placer.fit(fp, REGIONS[block]):
                failed.append(f"{fp.GetReference()} ({block})")
    if failed:
        sys.exit("no room for: " + ", ".join(failed))

    add_outline(board)
    add_dimension(board, (0, 0), (BOARD_W, 0), 6)
    add_dimension(board, (BOARD_W, 0), (BOARD_W, BOARD_H), -6)
    for text in SILK:
        add_text(board, *text)

    out = ROOT / f"{PROJECT}.kicad_pcb"
    board.Save(str(out))
    print(f"{out.name}: {len(by_ref)} parts on {BOARD_W:g} x {BOARD_H:g} mm")


if __name__ == "__main__":
    main()
