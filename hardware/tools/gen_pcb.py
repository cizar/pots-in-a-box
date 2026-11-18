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
enclosure can be chosen. Each line is an identical column (same parts at the
same relative spot), so more lines are added by widening the board. Re-running overwrites hardware/kicad/pots-in-a-box.kicad_pcb.
"""
import math
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

# Layout seen from behind the box (looking at the rear panel), left to right:
#   12 V jack + shared blocks | line L1 | line L2 | (L3, L4... would continue here)
# Every line is the same module: a full-depth column whose parts sit at the same
# place in each column, so the RJ11 jacks share one pitch. In board (top view)
# coordinates the rear edge is y = 0 and x grows towards the shared end.
#
# Units: every length below is in mil (1/1000 inch), the grid of DIP parts.
# Parts are placed by their footprint origin (pad 1 for THT parts), so a DIP or
# a 400 mil resistor put on a 100 mil grid has all its pads on that grid. Rows
# of like parts use a 200 mil pitch. The column width is a multiple of 100 mil
# so every copied line stays on the grid too.
LINES = ["line_L1", "line_L2"]    # L1 next to the shared blocks
LINE_W = 1400                     # width of one line column (= RJ11 pitch), 35.56 mm
SHARED_W = 2700                   # power, ring, link and mcu; board = 5500 mil (enclosure limit)
BOARD_H = 3850                    # rear panel to front panel, 97.79 mm (enclosure limit)
BOARD_W = LINE_W * len(LINES) + SHARED_W
SHARED_X = LINE_W * len(LINES)    # left edge of the shared blocks
HOLE_INSET = 150                  # mounting-hole centre from each edge
HOLE_KEEPOUT = 300                # square kept free around each hole
GAP = 40                          # clearance between courtyards (~1 mm)
GRID = 50                         # grid for the origins of automatically placed parts
EDGE_KEEPOUT = 40                 # copper-free band along the board edge (~1 mm): no tracks,
                                  # vias or pours; the autorouter ignores the edge clearance
# Where the board's rear-left corner lands on the KiCad sheet: inside the A4
# frame, on the 50 mil grid. Everything above is relative to that corner; the
# grid origin is set there too, so a 25/50 mil snap in KiCad matches this script.
SHEET_ORIGIN = (1000, 1000)


def line_x0(i):
    """Left edge of line i's column (i = 0 is L1, next to the shared blocks)."""
    return SHARED_X - (i + 1) * LINE_W


# Blocks: (x0, y0, x1, y1), origin at the rear-left corner (top view).
# The line template is L1's column; the other lines copy it.
SPLIT = SHARED_X + 1600           # ring and link on the line side, power on the outer side
FRONT = 2450                      # mcu and link band from here to the front edge
LED_X = SHARED_X + 1450           # PWR LED; CALL LED 750 mil further out (moved by hand)
REGIONS = {
    "ring": (SHARED_X, 0, SPLIT, FRONT),
    "power": (SPLIT, 0, BOARD_W, FRONT),
    "link": (SPLIT, FRONT, BOARD_W, BOARD_H),     # outer half of the front band
    "mcu": (SHARED_X, FRONT, BOARD_W, BOARD_H),   # the ATmega lands next to L1, by the bus
}
PLACE_ORDER = ["line", "ring", "power", "link", "mcu"]

# The line module, placed by hand rear to front following the signal. Values are
# the footprint origin (pad 1) in column coordinates (x from the L2-side edge of
# the column towards the shared blocks, y from the rear edge), in mil, and the
# rotation. Refs are L1's; every other line copies them. Arranged by hand in
# KiCad on L2, then squared to the 100 mil grid with 200 mil rows.
LINE_LAYOUT = {
    # entry: RJ11 (EDGE_PARTS) with the PTC fuse on its outer side, the TVS lying
    # right under the jack and the ring relay beside it. The relay is turned so
    # its ring contacts (RING_A/B, high voltage from the H bridge) face the rear
    # and its coil (+12V, ULN2003A) faces the logic side.
    "D102": (400, 875, 0), "F101": (175, 850, 90),
    "K101": (1300, 800, 180),
    # loop feed / current limiter: the transistors next to their resistors
    "R101": (100, 1050, 0), "Q101": (950, 1350, 90),
    "R102": (100, 1275, 0), "Q102": (650, 1175, 270),
    # coupling capacitor; off-hook optocoupler with its protection diode
    "C101": (100, 1600, 0), "U101": (1150, 1450, 90), "D101": (1000, 1000, 0),
    # audio to the MT8870: clamp diodes, level trimmer, input network
    "R103": (950, 1950, 90), "D103": (1100, 1900, 90), "D104": (1250, 1600, 270),
    "RV101": (350, 1950, 0), "C104": (550, 1950, 0),
    # tone filter from the ATmega and the MT8870 input resistor: one 160 mil row
    "C102": (350, 2200, 180), "C103": (350, 2400, 180),
    "R104": (600, 2500, 90), "R105": (760, 2500, 90), "R106": (920, 2500, 90),
    "R107": (1080, 2500, 90), "R108": (1240, 2500, 90),
    # MT8870 with its crystal on the OSC pins and its decoupling on VDD
    "Y101": (200, 2825, 90), "U102": (1250, 2625, 270),
    "C105": (1300, 3125, 180), "C106": (1300, 3325, 180),
    # under Q1..Q4 (pins 11-14): series resistors dropping onto the DTMF bus,
    # then the guard-time resistor, one 160 mil row
    "R109": (300, 3425, 90), "R110": (460, 3425, 90),
    "R111": (620, 3425, 90), "R112": (780, 3425, 90),
    "R113": (940, 3425, 90),
}
# Strip along the front of the line columns kept free for the bus to the ATmega:
# DTMF_Q1..Q4 shared by every line, plus each line's TONE, StD, OFFHOOK and relay.
BUS_H = 300
# Shared parts with a fixed place, same convention but in board coordinates.
SHARED_LAYOUT = {
    "R11": (SHARED_X + 2375, FRONT + 450, 270), 
    "K3": (SHARED_X + 1300, FRONT + 500, 90),             # link relay, pulled in towards L1
    "C22": (SHARED_X + 550, 1100, 90),   # moved by hand in KiCad
    "Q3": (SHARED_X + 150, 1000, 0),   # moved by hand in KiCad
    "Q4": (SHARED_X + 150, 1300, 0),   # moved by hand in KiCad
    "R26": (SHARED_X + 650, 1950, 0),   # moved by hand in KiCad
    "U5": (SHARED_X + 1300, FRONT + 950, 90),   # moved by hand in KiCad
    "SW1": (SHARED_X + 1875, FRONT + 1250, 270),   # header to the AR/US panel switch (wired)
    "C30": (SHARED_X + 2250, FRONT + 250, 0),   # +12V at ULN2003 COM (pin 9)
    "J4": (SHARED_X + 100, FRONT + 1200, 90),   # moved by hand in KiCad
    "R12": (SHARED_X + 2550, FRONT + 450, 270),   # moved by hand in KiCad
    "C1": (SHARED_X + 2350, 850, 0),   # moved by hand in KiCad
    "C2": (SHARED_X + 2200, 1200, 90),   # moved by hand in KiCad
    "C3": (SHARED_X + 1950, 1200, 90),   # moved by hand in KiCad
    "C4": (SHARED_X + 1700, 1200, 90),   # +5V bulk decoupling
    "C5": (SHARED_X + 1400, 750, 0),   # moved by hand in KiCad
    "C6": (SHARED_X + 1725, 1600, 0),   # moved by hand in KiCad
    "D1": (SHARED_X + 1850, 200, 180),   # moved by hand in KiCad
    "F1": (SHARED_X + 1750, 600, 90),   # moved by hand in KiCad
    "R1": (SHARED_X + 1525, 2150, 0),   # moved by hand in KiCad
    "R2": (SHARED_X + 2200, FRONT + 450, 270),   # moved by hand in KiCad
    "U1": (SHARED_X + 2050, 750, 180),   # moved by hand in KiCad
    "C20": (SHARED_X + 1050, 550, 0),   # moved by hand in KiCad
    "C21": (SHARED_X + 1050, 950, 0),   # moved by hand in KiCad
    "Q7": (SHARED_X + 750, 1000, 0),   # moved by hand in KiCad
    # H-bridge resistor rows, pinned where they were when the ATmega area was arranged
    "R21": (SHARED_X + 100, 1650, 0), "R22": (SHARED_X + 650, 1650, 0),
    "R23": (SHARED_X + 100, 1800, 0), "R24": (SHARED_X + 650, 1800, 0),
    "R25": (SHARED_X + 100, 1950, 0),
    # rest of the H bridge, pinned as it was (auto-placed until now)
    "C23": (SHARED_X + 1200, 1500, 0), "C24": (SHARED_X + 1200, 1650, 0),
    "D20": (SHARED_X + 100, 1500, 0), "D21": (SHARED_X + 650, 1500, 0),
    "Q5": (SHARED_X + 650, 1300, 0), "Q6": (SHARED_X + 1150, 1300, 0),
    "R20": (SHARED_X + 100, 200, 0), "U3": (SHARED_X + 100, 450, 0),
    "U4": (SHARED_X + 550, 450, 0),
    # panel LEDs, 100 mil behind the front edge (placed by hand)
    "D2": (LED_X, BOARD_H - 100, 90), "D10": (LED_X + 750, BOARD_H - 100, 90),
    "J2": (SHARED_X + 2500, 2000, 90),   # moved by hand in KiCad
    "U2": (SHARED_X + 500, FRONT + 1000, 180),   # ATmega: PC2..PC5 (pins 25-28) face the bus; 100 mil off L1 for C13/C14
    "C14": (SHARED_X + 50, FRONT + 50, 90),   # AREF, in the gap on the pin 15-28 side, by pin 21
    "C13": (SHARED_X + 50, FRONT + 200, 270),   # AVCC decoupling: +5V at pin 20, GND at pin 22
    "J3": (SHARED_X + 800, 2325, 90),   # ISP header, above the crystal
    "Y1": (SHARED_X + 725, FRONT + 400, 90),   # crystal right at XTAL2/XTAL1 (pins 10/9)
    "C11": (SHARED_X + 900, FRONT + 250, 0),   # crystal cap, XTAL2
    "C10": (SHARED_X + 900, FRONT + 400, 0),   # crystal cap, XTAL1
    "C12": (SHARED_X + 825, FRONT + 675, 180),   # VCC decoupling: +5V towards pin 7, GND with C10/C11
    "R13": (SHARED_X + 1100, FRONT + 550, 270),   # RING_DRIVE pull-down, by pin 6
    "R10": (SHARED_X + 950, FRONT + 550, 270),   # RESET pull-up, RESET end towards pin 1
    "C15": (SHARED_X + 825, FRONT + 875, 180),   # DTR auto-reset, J4 pin 6 -> RESET
}
# Parts that go wherever they fit in the shared area when their block is full.
FLOATING = {"J2"}   # boost module connector: wired to the module, any place will do

# Parts with a fixed place: ref -> (edge, x centre, rotation). The part's front
# face (fab outline) touches that edge; its origin is then put on the GRID.
# Line parts are given for L1 only.
J1_X = 5000     # 12 V jack centre (moved by hand)
JACK_X = 600    # RJ11 centre in column coordinates (moved by hand towards the L2 side)
EDGE_PARTS = {
    "J101": ("rear", line_x0(0) + JACK_X, 180),  # RJ11, same spot in every line
    "J1": ("rear", J1_X, 270),                   # 12 V jack at the outer end
}
EDGE_MARGIN = {"rear": 0, "front": 60}

SILK = [  # (text, x, y, size), all in mil
    # connector labels sit on the connector body: visible in the preview only
    *[(f"L{i + 1}", line_x0(i) + JACK_X, 240, 80) for i in range(len(LINES))],
    ("12V", J1_X, 240, 80),
    ("PWR", LED_X, BOARD_H - 300, 50), ("CALL", LED_X + 750, BOARD_H - 300, 50),
    ("AR/US", SHARED_X + 1925, BOARD_H - 300, 50),
    ("POTS in a box", SHARED_X - 800, BOARD_H - 130, 70),
]

# The KiCad library has no 3D model for the RJ12 jack: a plain box stands in for it
# so the render shows its height. Box in footprint coordinates (mm): x, y, height.
RJ_BODY = ((-3.47, 9.83), (-1.28, 16.82), 11.7)
PLACEHOLDER_DIR = ROOT / "3d"


def iu(v):
    """mil -> KiCad internal units."""
    return pcbnew.FromMils(v)


def pt(x, y):
    return pcbnew.VECTOR2I(iu(x), iu(y))


def snap(v, grid=GRID):
    return round(v / grid) * grid


def export_netlist():
    out = Path(tempfile.mkdtemp()) / "net.xml"
    subprocess.run([CLI, "sch", "export", "netlist", "--format", "kicadxml", "-o", str(out),
                    str(ROOT / f"{PROJECT}.kicad_sch")], check=True, capture_output=True)
    return ET.parse(out).getroot()


def block_of(comp):
    sheet = comp.find("sheetpath").get("names").strip("/")
    return sheet or "power"


def line_ref(ref, i):
    """L1's reference for line i: R101 -> R201 for L2 (series 100 per line)."""
    head = ref.rstrip("0123456789")
    return f"{head}{(i + 1) * 100 + int(ref[len(head):]) % 100}"


def courtyard(fp):
    cy = fp.GetCourtyard(pcbnew.F_CrtYd)
    bb = cy.BBox() if cy.OutlineCount() else fp.GetBoundingBox(False)
    return [pcbnew.ToMils(v) for v in (bb.GetLeft(), bb.GetTop(), bb.GetRight(), bb.GetBottom())]


def fab_box(fp):
    xs, ys = [], []
    for g in fp.GraphicalItems():
        if g.GetLayer() == pcbnew.F_Fab and g.GetClass() == "PCB_SHAPE":
            b = g.GetBoundingBox()
            xs += [b.GetLeft(), b.GetRight()]
            ys += [b.GetTop(), b.GetBottom()]
    return [pcbnew.ToMils(v) for v in (min(xs), min(ys), max(xs), max(ys))]


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
    """Keeps the courtyards already used (mil) and puts footprints by origin."""

    def __init__(self):
        k = HOLE_KEEPOUT
        self.used = [(0, 0, k, k), (BOARD_W - k, 0, BOARD_W, k),
                     (0, BOARD_H - k, k, BOARD_H), (BOARD_W - k, BOARD_H - k, BOARD_W, BOARD_H),
                     (0, BOARD_H - BUS_H, SHARED_X, BOARD_H)]
        self.names = ["hole H1", "hole H2", "hole H3", "hole H4", "DTMF bus strip"]
        self.problem = ""

    @staticmethod
    def offsets(fp, rot):
        """Courtyard relative to the origin for that rotation."""
        fp.SetOrientationDegrees(rot)
        fp.SetPosition(pt(0, 0))
        return courtyard(fp)

    def move(self, fp, x, y):
        fp.SetPosition(pt(x, y))
        box = courtyard(fp)
        self.used.append((box[0] - GAP / 2, box[1] - GAP / 2, box[2] + GAP / 2, box[3] + GAP / 2))
        self.names.append(fp.GetReference())

    def place_at(self, fp, x, y, rot, ignore=()):
        """Puts the origin (pad 1) at (x, y); False if it hits something.
        Hand-made positions are trusted down to touching courtyards: the GAP/2
        margin every placed part reserves around itself is not enforced here."""
        l, t, r, b = self.offsets(fp, rot)
        box = (x + l, y + t, x + r, y + b)
        m = GAP / 2 - 0.5
        inner = (box[0] + m, box[1] + m, box[2] - m, box[3] - m)
        hits = [n for u, n in zip(self.used, self.names) if u not in ignore and overlaps(inner, u)]
        if not (0 <= box[0] and box[2] <= BOARD_W and 0 <= box[1] and box[3] <= BOARD_H):
            hits.insert(0, "board edge")
        self.problem = ", ".join(hits)
        self.move(fp, x, y)
        return not hits

    def fit(self, fp, region, ignore=()):
        """First free origin on the GRID, scanning rows rear to front, left to right;
        a part that finds no room lying flat is tried again turned 90 degrees."""
        return any(self.fit_rot(fp, region, rot, ignore) for rot in (0, 90))

    def fit_rot(self, fp, region, rot, ignore=()):
        l, t, r, b = self.offsets(fp, rot)
        x0, y0, x1, y1 = region
        g = GAP / 2
        y = math.ceil((y0 + g - t) / GRID) * GRID
        while y + b + g <= y1:
            x = math.ceil((x0 + g - l) / GRID) * GRID
            while x + r + g <= x1:
                cand = (x + l - g, y + t - g, x + r + g, y + b + g)
                if not any(overlaps(cand, u) for u in self.used if u not in ignore):
                    self.move(fp, x, y)
                    return True
                x += GRID
            y += GRID
        return False


def park(placer, fp, y):
    """Leaves a part that found no room to the right of the board, stacked down."""
    l, t, r, b = placer.offsets(fp, 0)
    fp.SetPosition(pt(BOARD_W + 200 - l, y - t))
    return y + (b - t) + 100


def block_of_ref(ref, blocks):
    return next(b for b, fps in blocks.items() if any(f.GetReference() == ref for f in fps))


def place_on_edge(placer, fp, edge, xc, rot):
    fp.SetOrientationDegrees(rot)
    fp.SetPosition(pt(0, 0))
    l, t, r, b = fab_box(fp)
    x = snap(xc - (l + r) / 2)
    y = EDGE_MARGIN[edge] - t if edge == "rear" else BOARD_H - EDGE_MARGIN[edge] - b
    placer.move(fp, x, y)


def add_outline(board):
    pts = [(0, 0), (BOARD_W, 0), (BOARD_W, BOARD_H), (0, BOARD_H)]
    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1]):
        s = pcbnew.PCB_SHAPE(board, pcbnew.SHAPE_T_SEGMENT)
        s.SetStart(pt(x0, y0))
        s.SetEnd(pt(x1, y1))
        s.SetLayer(pcbnew.Edge_Cuts)
        s.SetWidth(pcbnew.FromMM(0.1))
        board.Add(s)


def add_edge_keepout(board):
    """Rule areas along the four edges, on both copper layers. Footprint pads may
    sit in them (the panel connectors do); tracks, vias and pours may not."""
    k = EDGE_KEEPOUT
    layers = pcbnew.LSET()
    layers.AddLayer(pcbnew.F_Cu)
    layers.AddLayer(pcbnew.B_Cu)
    for x0, y0, x1, y1 in [(0, 0, BOARD_W, k), (0, BOARD_H - k, BOARD_W, BOARD_H),
                           (0, k, k, BOARD_H - k), (BOARD_W - k, k, BOARD_W, BOARD_H - k)]:
        z = pcbnew.ZONE(board)
        z.SetIsRuleArea(True)
        z.SetDoNotAllowTracks(True)
        z.SetDoNotAllowVias(True)
        z.SetDoNotAllowZoneFills(True)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        z.SetLayerSet(layers)
        z.SetZoneName("edge keepout")
        poly = z.Outline()
        poly.NewOutline()
        for x, y in [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]:
            poly.Append(iu(x), iu(y))
        board.Add(z)


def add_dimension(board, a, b, offset):
    d = pcbnew.PCB_DIM_ALIGNED(board, pcbnew.PCB_DIM_ALIGNED_T)
    d.SetStart(pt(*a))
    d.SetEnd(pt(*b))
    d.SetHeight(iu(offset))
    d.SetLayer(pcbnew.Dwgs_User)
    board.Add(d)


def add_text(board, text, x, y, size):
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetPosition(pt(x, y))
    t.SetLayer(pcbnew.F_SilkS)
    t.SetTextSize(pt(size, size))
    t.SetTextThickness(iu(size * 0.15))
    board.Add(t)


def main(out=None):
    """Generates the board; out defaults to the project's .kicad_pcb."""
    write_box_wrl(PLACEHOLDER_DIR / "rj12_body.wrl", *RJ_BODY)  # noqa: the model path is project-relative
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
        h.SetPosition(pt(x, y))
        board.Add(h)

    by_ref = {fp.GetReference(): fp for fps in blocks.values() for fp in fps}
    line_dx = [line_x0(i) - line_x0(0) for i in range(len(LINES))]
    fixed = set()
    for ref, (edge, xc, rot) in EDGE_PARTS.items():
        n = len(LINES) if block_of_ref(ref, blocks) == "line_L1" else 1
        for i in range(n):
            r = line_ref(ref, i) if n > 1 else ref
            place_on_edge(placer, by_ref[r], edge, xc + line_dx[i], rot)
            fixed.add(r)

    def area(f):
        l, t, r, b = courtyard(f)
        return (r - l) * (b - t)

    failed = []
    park_y = 0
    for block in PLACE_ORDER:
        if block == "line":
            rest = {f.GetReference() for f in blocks["line_L1"]} - fixed - set(LINE_LAYOUT)
            assert not rest, f"line parts without a place: {sorted(rest)}"
            for ref, (x, y, rot) in LINE_LAYOUT.items():
                for i in range(len(LINES)):
                    fp = by_ref[line_ref(ref, i)]
                    if not placer.place_at(fp, line_x0(i) + x, y, rot):
                        failed.append(f"{fp.GetReference()}: {placer.problem}")
            continue
        for fp in blocks[block]:
            ref = fp.GetReference()
            if ref in SHARED_LAYOUT:
                if not placer.place_at(fp, *SHARED_LAYOUT[ref]):
                    failed.append(f"{ref}: {placer.problem}")
                fixed.add(ref)
        free = sorted((fp for fp in blocks[block] if fp.GetReference() not in fixed),
                      key=area, reverse=True)
        for fp in free:
            if not placer.fit(fp, REGIONS[block]) and not (
                    # parts without a fixed place may go anywhere in the shared area
                    fp.GetReference() in FLOATING
                    and placer.fit(fp, (SHARED_X, 0, BOARD_W, BOARD_H))):
                failed.append(f"{fp.GetReference()}: no room in {block}, parked off the board")
                park_y = park(placer, fp, park_y)
    off = [f.GetReference() for f in board.GetFootprints()
           if (lambda c: c[0] < -1 or c[1] < -60 or c[2] > BOARD_W + 1 or c[3] > BOARD_H + 1)(courtyard(f))]
    if failed or off:
        # The board is still written, so the parts can be fixed by hand in KiCad.
        print("WARNING, to fix by hand:")
        for f in failed:
            print("  ", f)
        if off:
            print("  outside the board outline:", ", ".join(sorted(off)))

    add_outline(board)
    add_edge_keepout(board)
    add_dimension(board, (0, 0), (BOARD_W, 0), 240)
    add_dimension(board, (BOARD_W, 0), (BOARD_W, BOARD_H), -240)
    for text in SILK:
        add_text(board, *text)

    # Move the whole board inside the sheet frame and put the grid origin (and the
    # drill/place origin) on its corner.
    shift = pt(*SHEET_ORIGIN)
    for item in list(board.GetFootprints()) + list(board.GetDrawings()) + list(board.Zones()):
        item.Move(shift)
    board.GetDesignSettings().SetGridOrigin(shift)
    board.GetDesignSettings().SetAuxOrigin(shift)

    out = Path(out) if out else ROOT / f"{PROJECT}.kicad_pcb"
    # BOARD.Save() also rewrites the project file next to the board with default
    # settings, which would wipe the net classes and design rules kept there.
    project = out.with_suffix(".kicad_pro")
    kept = project.read_bytes() if project.exists() else None
    board.Save(str(out))
    if kept is not None and project.read_bytes() != kept:
        project.write_bytes(kept)
    print(f"{out.name}: {len(by_ref)} parts on {BOARD_W} x {BOARD_H} mil"
          f" ({BOARD_W * 0.0254:.2f} x {BOARD_H * 0.0254:.2f} mm)")


if __name__ == "__main__":
    main()
