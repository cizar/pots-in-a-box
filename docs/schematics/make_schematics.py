# SPDX-License-Identifier: CERN-OHL-S-2.0
# Copyright (C) 2026 Cesar Kastli
"""Bench-test schematics for docs/prueba-banco.md.

Usage:  python3 make_schematics.py [--png]
Writes SVG files next to this script (PNG previews with --png).
Requires: pip install schemdraw matplotlib
"""
import sys
from pathlib import Path

import schemdraw
import schemdraw.elements as elm

OUT = Path(__file__).resolve().parent
FMT = "png" if "--png" in sys.argv else "svg"
if FMT == "png":
    schemdraw.use("matplotlib")
else:
    schemdraw.use("svg")


def drawing(name):
    d = schemdraw.Drawing(file=str(OUT / f"{name}.{FMT}"), show=False)
    d.config(fontsize=11, bgcolor="white", unit=2.5)
    return d


def wire(*pts):
    """Polyline through absolute points."""
    for a, b in zip(pts, pts[1:]):
        elm.Line().at(a).to(b)


def dot(p, label=None, loc="right", open_=False):
    e = elm.Dot(open=open_).at(p)
    if label:
        e.label(label, loc)
    return e


def line_feed():
    """Per-line loop feed: current limiter, ring relay (at rest), opto, TVS."""
    with drawing("line-feed"):
        # Current limiter
        dot((0, 8), "V_LINE", "left")
        elm.Fuse().at((0, 8)).to((3, 8)).label("PTC 100 mA")
        wire((3, 8), (8.75, 8))
        dot((4.5, 8))
        elm.Resistor().at((4.5, 8)).to((4.5, 6.6)).label("10 kΩ ½ W")
        wire((4.5, 6.6), (8, 6.6))
        q1 = elm.BjtNpn(circuit=True).theta(0).anchor("base").at((8, 6.6)).label("Q1 MJE340\ncon disipador", "right")
        wire((8.75, 8), q1.collector)
        wire(q1.emitter, (8.75, 5.0))
        dot((8.75, 5.0))
        elm.Resistor().at((8.75, 5.0)).to((8.75, 2.9)).label("R_SENSE\n27 Ω", "bottom")
        q2 = elm.BjtNpn(circuit=True).theta(0).reverse().anchor("base").at((7.2, 5.0)).label("Q2\nBC546", "left")
        wire(q2.base, (8.75, 5.0))
        wire(q2.collector, (q2.collector[0], 6.6))
        dot((q2.collector[0], 6.6))
        wire(q2.emitter, (q2.emitter[0], 2.9), (8.75, 2.9))
        dot((8.75, 2.9), "TIP_FEED", "bottom")

        # Ring relay RL1, pole 1 (TIP): NC to TIP_FEED, NO to bridge output B
        wire((8.75, 2.9), (10, 2.9))
        sw1 = elm.SwitchSpdt2().reverse().anchor("b").at((10, 2.9))
        elm.Label().at((11.3, 3.7)).label("RL1 polo 1")
        elm.Label().at((9.7, 3.2)).label("NC", fontsize=9)
        elm.Label().at((9.7, 1.9)).label("NO", fontsize=9)
        wire(sw1.c, (sw1.c[0], 1.4))
        elm.Label().at((sw1.c[0] - 0.1, 1.4)).label("a salida B del puente (§1.3)", "left", fontsize=9)
        wire(sw1.a, (13, sw1.a[1]), (14.5, sw1.a[1]))
        dot((13, sw1.a[1]))
        dot((14.5, sw1.a[1]), "TIP", "right", open_=True)

        # TVS across the jack
        elm.Zener().at((13, sw1.a[1])).to((13, -0.5)).label("TVS\nP6KE68CA", "bottom")
        dot((13, -0.5))
        dot((14.5, -0.5), "RING", "right", open_=True)
        wire((13, -0.5), (14.5, -0.5))
        elm.Label().at((15.6, 1.0)).label("RJ11")

        # Ring relay RL1, pole 2 (RING): NC to RING_RET, NO to bridge output A
        sw2 = elm.SwitchSpdt2().reverse().anchor("a").at((10.76, -0.5))
        wire((13, -0.5), sw2.a)
        elm.Label().at((11.3, 0.5)).label("RL1 polo 2")
        elm.Label().at((9.7, -0.1)).label("NC", fontsize=9)
        elm.Label().at((9.7, -1.0)).label("NO", fontsize=9)
        wire(sw2.c, (sw2.c[0], -1.6))
        elm.Label().at((sw2.c[0] - 0.1, -1.6)).label("a salida A del puente (§1.3)", "left", fontsize=9)
        wire(sw2.b, (4.0, sw2.b[1]), (4.0, -2.8))
        elm.Label().at((7.5, sw2.b[1] + 0.3)).label("RING_RET", fontsize=9)

        # Off-hook opto in the return leg, LED with antiparallel 1N4148
        opto = elm.Optocoupler().theta(0).anchor("anode").at((4.0, -2.8)).label("PC817", "bottom")
        dot((4.0, -2.8))
        k = opto.cathode
        dot(k)
        wire((4.0, -2.8), (3.0, -2.8))
        wire(k, (3.0, k[1]))
        elm.Diode().at((3.0, k[1])).to((3.0, -2.8)).label("1N4148", "top")
        wire(k, (k[0], k[1] - 0.6))
        elm.Ground().at((k[0], k[1] - 0.6))
        wire(opto.collector, (opto.collector[0] + 1.2, opto.collector[1]))
        elm.Label().at((opto.collector[0] + 1.3, opto.collector[1])).label("PC0 (OFFHOOK)", "right", fontsize=9)
        wire(opto.emitter, (opto.emitter[0], opto.emitter[1] - 0.6))
        elm.Ground().at((opto.emitter[0], opto.emitter[1] - 0.6))


def ring_bridge():
    """H-bridge that applies ±V_LINE to the line while ringing."""
    with drawing("ring-bridge"):
        dot((0, 8), "V_LINE", "left")
        elm.Resistor().at((0, 8)).to((3, 8)).label("R_BRIDGE\n470 Ω 5 W")
        wire((3, 8), (8, 8))
        dot((4, 8))
        dot((8, 8))
        p1 = elm.PFet().theta(0).reverse().anchor("source").at((4, 8)).label("P1\nIRF9540", "right")
        p2 = elm.PFet().theta(0).anchor("source").at((8, 8)).label("P2\nIRF9540", "left")
        n1 = elm.NFet().theta(0).reverse().anchor("drain").at((4, 5.2)).label("N1\nIRF540", "right")
        n2 = elm.NFet().theta(0).anchor("drain").at((8, 5.2)).label("N2\nIRF540", "left")
        wire(p1.drain, n1.drain)
        wire(p2.drain, n2.drain)
        dot((4, 5.85))
        dot((8, 5.85))
        wire((4, 5.85), (5.0, 5.85))
        dot((5.0, 5.85), "A", "right", open_=True)
        wire((8, 5.85), (7.0, 5.85))
        dot((7.0, 5.85), "B", "left", open_=True)
        wire(n1.source, (4, 2.8))
        wire(n2.source, (8, 2.8))
        wire((3, 2.8), (9, 2.8))
        dot((4, 2.8))
        dot((8, 2.8))
        elm.Ground().at((6, 2.8))
        for g, text, side in ((p1.gate, "G_P1 ← PD4\n(desplazador)", "left"),
                              (n1.gate, "G_N1 ← inversor", "left"),
                              (p2.gate, "G_P2 ← inversor\n(desplazador)", "right"),
                              (n2.gate, "G_N2 ← PD4", "right")):
            end = (g[0] - 0.8, g[1]) if side == "left" else (g[0] + 0.8, g[1])
            wire(g, end)
            elm.Label().at(end).label(text, side, fontsize=9)
        elm.Label().at((6, 1.6)).label("A → RL1 polo 2 (NO, lado RING)    B → RL1 polo 1 (NO, lado TIP)", fontsize=9)
        elm.Label().at((6, 1.0)).label("PD4 alto: P1 + N2 conducen (A = +V_LINE).  PD4 bajo: P2 + N1 conducen (B = +V_LINE).", fontsize=9)


def ring_gate_drive():
    """Gate drive: PD4, the 12 V inverter and the P-gate level shifter."""
    with drawing("ring-gate-drive"):
        # PD4 with pull-down, inverter BC547 at 12 V
        dot((0, 5), "PD4\n(RING_DRIVE)", "left")
        wire((0, 5), (1.5, 5))
        dot((1.5, 5))
        elm.Resistor().at((1.5, 5)).to((1.5, 2.5)).label("10 kΩ\npull-down", "bottom")
        elm.Ground().at((1.5, 2.5))
        elm.Resistor().at((1.5, 5)).to((4.0, 5)).label("10 kΩ")
        qi = elm.BjtNpn(circuit=True).theta(0).anchor("base").at((4.0, 5)).label("BC547\ninversor", "right")
        wire(qi.emitter, (qi.emitter[0], 3.6))
        elm.Ground().at((qi.emitter[0], 3.6))
        dot((qi.collector[0], 8.7), "12 V", "top")
        elm.Resistor().at((qi.collector[0], 8.7)).to((qi.collector[0], 6.2)).label("4,7 kΩ", "bottom")
        wire((qi.collector[0], 6.2), qi.collector)
        dot((qi.collector[0], 6.2))
        wire((qi.collector[0], 6.2), (7.0, 6.2))
        elm.Label().at((7.1, 6.2)).label("INV → G_N1 (vía 220 Ω ∥ 1N4148)\n        y entrada del desplazador de P2", "right", fontsize=9)
        wire((1.5, 5), (1.5, 6.8), (0.8, 6.8))
        elm.Label().at((0.7, 6.8)).label("PD4 → G_N2 (vía 220 Ω ∥ 1N4148)\n     y entrada del desplazador de P1", "left", fontsize=9)

        # P-gate level shifter (one per P MOSFET)
        x = 3
        elm.Label().at((x + 5, 1.8)).label("Desplazador de gate (uno para P1 y otro para P2)", fontsize=10)
        dot((x + 4, 0.8), "V_LINE", "top")
        wire((x + 4, 0.8), (x + 6, 0.8))
        dot((x + 6, 0.8))
        elm.Resistor().at((x + 4, 0.8)).to((x + 4, -1.6)).label("22 kΩ", "top")
        elm.Zener().at((x + 6, -1.6)).to((x + 6, 0.8)).label("zener\n12 V", "bottom")
        wire((x + 4, -1.6), (x + 6, -1.6))
        dot((x + 4, -1.6))
        dot((x + 6, -1.6))
        wire((x + 6, -1.6), (x + 7.5, -1.6))
        elm.Label().at((x + 7.6, -1.6)).label("gate del P (P1 o P2)\nfuente del P = V_LINE", "right", fontsize=9)
        elm.Resistor().at((x + 4, -1.6)).to((x + 4, -4.4)).label("10 kΩ\nlimita el zener", "bottom")
        qs = elm.BjtNpn(circuit=True).theta(0).anchor("collector").at((x + 4, -4.4)).label("BC546\no MPSA42", "right")
        wire(qs.emitter, (qs.emitter[0], qs.emitter[1] - 0.5))
        elm.Ground().at((qs.emitter[0], qs.emitter[1] - 0.5))
        elm.Resistor().at(qs.base).to((qs.base[0] - 2.5, qs.base[1])).label("10 kΩ")
        elm.Label().at((qs.base[0] - 2.6, qs.base[1])).label("PD4 (para P1)\nINV (para P2)", "left", fontsize=9)


if __name__ == "__main__":
    line_feed()
    ring_bridge()
    ring_gate_drive()
    print("done:", FMT)
