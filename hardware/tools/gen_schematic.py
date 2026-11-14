# SPDX-License-Identifier: CERN-OHL-S-2.0
# Copyright (C) 2026 Cesar Kastli
"""Generates the KiCad schematic of POTS in a box (hardware/kicad/).

    python3 hardware/tools/gen_schematic.py

Every part pin gets a short wire and a label (local, global or hierarchical)
or a power symbol, so connectivity is explicit and ERC-checkable. The line
block is one sheet used twice (L1, L2). Re-run after editing the netlists
below; hand edits to the generated .kicad_sch files are overwritten.
"""
import json
import math
import subprocess
import shutil
import uuid
from pathlib import Path

import kicad_lib as kl

ROOT = Path(__file__).resolve().parents[1] / "kicad"
PROJECT = "pots-in-a-box"
PROJECT_LIB = ROOT / "pots.kicad_sym"
FOOTPRINTS = Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints")
POWER_NETS = {"+5V": "power:+5V", "+12V": "power:+12V", "GND": "power:GND", "V_LINE": "pots:V_LINE"}
GRID = 2.54
STUB = 2.54


def uid():
    return str(uuid.uuid4())


def q(s):
    return '"' + str(s).replace('"', '\\"') + '"'


# --- footprints ---------------------------------------------------------------
FP = {
    "R": "Resistor_THT:R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal",
    "R_05W": "Resistor_THT:R_Axial_DIN0309_L9.0mm_D3.2mm_P12.70mm_Horizontal",
    "R_1W": "Resistor_THT:R_Axial_DIN0414_L11.9mm_D4.5mm_P15.24mm_Horizontal",
    "R_5W": "Resistor_THT:R_Axial_Power_L25.0mm_W6.4mm_P27.94mm",
    "C": "Capacitor_THT:C_Disc_D5.0mm_W2.5mm_P5.00mm",
    "CP8": "Capacitor_THT:CP_Radial_D8.0mm_P3.50mm",
    "CP10": "Capacitor_THT:CP_Radial_D10.0mm_P5.00mm",
    "C_FILM": "Capacitor_THT:C_Rect_L18.0mm_W8.0mm_P15.00mm_FKS3_FKP3",
    "D35": "Diode_THT:D_DO-35_SOD27_P7.62mm_Horizontal",
    "D41": "Diode_THT:D_DO-41_SOD81_P10.16mm_Horizontal",
    "D15": "Diode_THT:D_DO-15_P10.16mm_Horizontal",
    "LED": "LED_THT:LED_D3.0mm",
    "TO92": "Package_TO_SOT_THT:TO-92_Inline",
    "TO126": "Package_TO_SOT_THT:TO-126-3_Vertical",
    "TO220": "Package_TO_SOT_THT:TO-220-3_Vertical",
    "DIP4": "Package_DIP:DIP-4_W7.62mm",
    "DIP8": "Package_DIP:DIP-8_W7.62mm",
    "DIP16": "Package_DIP:DIP-16_W7.62mm",
    "DIP18": "Package_DIP:DIP-18_W7.62mm",
    "DIP28": "Package_DIP:DIP-28_W7.62mm_Socket",
    "XTAL": "Crystal:Crystal_HC49-4H_Vertical",
    "RELAY": "Relay_THT:Relay_DPDT_Omron_G5V-2",
    "JACK": "Connector_BarrelJack:BarrelJack_Horizontal",
    "RJ11": "Connector_RJ:RJ12_Amphenol_54601-x06_Horizontal",
    "ISP": "Connector_IDC:IDC-Header_2x03_P2.54mm_Vertical",
    "H2": "Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical",
    "H6": "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical",
    "TB4": "TerminalBlock_Phoenix:TerminalBlock_Phoenix_MKDS-1,5-4-5.08_1x04_P5.08mm_Horizontal",
    "PTC": "Fuse:Fuse_Bourns_MF-RG300",
    "TRIM": "Potentiometer_THT:Potentiometer_Bourns_3296W_Vertical",
}


def check_footprints():
    missing = []
    for key, fp in FP.items():
        lib, name = fp.split(":")
        if not (FOOTPRINTS / f"{lib}.pretty" / f"{name}.kicad_mod").exists():
            missing.append(f"{key}: {fp}")
    return missing


# --- parts --------------------------------------------------------------------
class Part:
    def __init__(self, ref, lib_id, value, fp, at, nets, desc=""):
        self.ref, self.lib_id, self.value = ref, lib_id, value
        self.fp = FP.get(fp, fp) if fp else ""
        self.at = (at[0] * GRID, at[1] * GRID)
        self.nets = nets      # {pin number: net}; net "~" = no connect
        self.desc = desc


def P(ref, lib_id, value, fp, at, nets, desc=""):
    return Part(ref, lib_id, value, fp, at, nets, desc)


def two(ref, kind, value, fp, at, n1, n2, desc=""):
    lib = {"R": "Device:R", "C": "Device:C", "CP": "Device:C_Polarized", "D": "Device:D",
           "1N4148": "Diode:1N4148", "LED": "Device:LED", "TVS": "Device:D_TVS",
           "PTC": "Device:Polyfuse", "Z": "Device:D_Zener", "XTAL": "Device:Crystal",
           "SCHOTTKY": "Device:D_Schottky"}[kind]
    return Part(ref, lib, value, fp, at, {"1": n1, "2": n2}, desc)


# Power: 12 V jack, reverse protection, 7805, boost module, V_LINE bleeder.
POWER = [
    P("J1", "Connector:Barrel_Jack", "12V 2A", "JACK", (10, 15), {"1": "VIN_RAW", "2": "GND"},
      "Pin 1 = centre (+). External certified 12 V wall adapter: no mains inside the box."),
    two("F1", "PTC", "PTC 1.1A", "PTC", (22, 12), "VIN_RAW", "VIN_F"),
    two("D1", "SCHOTTKY", "1N5822", "D41", (32, 12), "+12V", "VIN_F", "Reverse-polarity protection"),
    two("C1", "CP", "470uF 25V", "CP10", (42, 18), "+12V", "GND"),
    two("C2", "C", "100nF", "C", (48, 18), "+12V", "GND"),
    P("U1", "Regulator_Linear:L7805", "L7805", "TO220", (60, 15), {"1": "+12V", "2": "GND", "3": "+5V"}),
    two("C3", "C", "330nF", "C", (54, 24), "+12V", "GND"),
    two("C4", "C", "100nF", "C", (68, 24), "+5V", "GND"),
    two("C5", "CP", "10uF 16V", "CP8", (74, 24), "+5V", "GND"),
    P("J2", "Connector_Generic:Conn_01x04", "BOOST_MODULE", "TB4", (12, 45),
      {"1": "+12V", "2": "GND", "3": "V_LINE", "4": "GND"},
      "Boost module: 1 IN+, 2 IN-, 3 OUT+ (V_LINE 24-48 V), 4 OUT-. To be replaced by an on-board boost after the bench test."),
    two("R1", "R", "4k7 1W", "R_1W", (30, 48), "V_LINE", "GND", "V_LINE bleeder"),
    two("C6", "CP", "100uF 100V", "CP10", (38, 48), "V_LINE", "GND"),
    two("R2", "R", "1k", "R", (50, 45), "+5V", "LED_PWR"),
    two("D2", "LED", "PWR", "LED", (56, 48), "GND", "LED_PWR", "Power LED (panel)"),
]
POWER_FLAGS = ["+12V", "GND", "V_LINE", "VIN_RAW"]

# MCU: ATmega328P (pin map = firmware/README.md, Arduino Uno compatible).
MCU = [
    P("U2", "MCU_Microchip_ATmega:ATmega328P-P", "ATmega328P-P", "DIP28", (40, 40), {
        "1": "G:RESET", "2": "G:UART_RX", "3": "G:UART_TX", "4": "G:DTMF_STD_L1", "5": "G:LED_CALL",
        "6": "G:RING_DRIVE", "7": "+5V", "8": "GND", "9": "XTAL1", "10": "XTAL2",
        "11": "G:TONE_L2", "12": "G:TONE_L1", "13": "G:DTMF_STD_L2",
        "14": "G:RING_EN_L1", "15": "G:RING_EN_L2", "16": "G:LINK_EN",
        "17": "G:MOSI", "18": "G:COUNTRY_SW", "19": "G:SCK", "20": "+5V", "21": "AREF", "22": "GND",
        "23": "G:OFFHOOK_L1", "24": "G:OFFHOOK_L2", "25": "G:DTMF_Q1", "26": "G:DTMF_Q2",
        "27": "G:DTMF_Q3", "28": "G:DTMF_Q4"}),
    two("Y1", "XTAL", "16MHz", "XTAL", (12, 30), "XTAL1", "XTAL2"),
    two("C10", "C", "22pF", "C", (8, 38), "XTAL1", "GND"),
    two("C11", "C", "22pF", "C", (16, 38), "XTAL2", "GND"),
    two("C12", "C", "100nF", "C", (70, 12), "+5V", "GND", "VCC decoupling"),
    two("C13", "C", "100nF", "C", (76, 12), "+5V", "GND", "AVCC decoupling"),
    two("C14", "C", "100nF", "C", (82, 12), "AREF", "GND"),
    two("R10", "R", "10k", "R", (8, 12), "+5V", "G:RESET"),
    P("J3", "Connector:AVR-ISP-6", "ISP", "ISP", (75, 40),
      {"1": "G:COUNTRY_SW", "2": "+5V", "3": "G:SCK", "4": "G:MOSI", "5": "G:RESET", "6": "GND"},
      "ISP. MISO is PB4, shared with COUNTRY_SW through R11 (ISP-safe)."),
    P("J4", "Connector_Generic:Conn_01x06", "FTDI", "H6", (75, 62),
      {"1": "GND", "2": "~", "3": "+5V", "4": "G:UART_RX", "5": "G:UART_TX", "6": "G:DTR"},
      "USB-serial (FTDI-style): 1 GND, 2 CTS, 3 VCC, 4 TXD (to MCU RX), 5 RXD (from MCU TX), 6 DTR"),
    two("C15", "C", "100nF", "C", (88, 66), "G:DTR", "G:RESET", "Auto-reset for Optiboot"),
    two("R11", "R", "1k", "R", (75, 82), "G:COUNTRY_SW", "SW_AR_US"),
    P("SW1", "Switch:SW_SPST", "AR/US", "H2", (84, 85), {"1": "SW_AR_US", "2": "GND"},
      "Panel switch: open = AR, closed = US"),
    two("R12", "R", "470", "R", (12, 62), "G:LED_CALL", "LED_CALL_A"),
    two("D10", "LED", "CALL", "LED", (12, 72), "GND", "LED_CALL_A", "Call-active LED (panel)"),
    two("R13", "R", "10k", "R", (22, 62), "G:RING_DRIVE", "GND", "Keeps the bridge defined during reset/ISP"),
]
MCU_FLAGS = []

# Ring: shared H-bridge, 2 x IR2104 + 4 x IRF540N, fed from V_LINE through R_BRIDGE.
def half_bridge(n, x, drive):
    u, qh, ql = f"U{3 + n}", f"Q{3 + 2 * n}", f"Q{4 + 2 * n}"
    out = "G:RING_A" if n == 0 else "G:RING_B"
    return [
        P(u, "Driver_FET:IR2104", "IR2104", "DIP8", (x, 30), {
            "1": "+12V", "2": drive, "3": "+12V", "4": "GND", "5": f"LO{n}",
            "6": out, "7": f"HO{n}", "8": f"VB{n}"}),
        P(qh, "Transistor_FET:IRF540N", "IRF540N", "TO220", (x + 22, 20),
          {"1": f"HG{n}", "2": "BRIDGE_RAIL", "3": out}),
        P(ql, "Transistor_FET:IRF540N", "IRF540N", "TO220", (x + 22, 40),
          {"1": f"LG{n}", "2": out, "3": "GND"}),
        two(f"R{21 + 2 * n}", "R", "22", "R", (x + 12, 18), f"HO{n}", f"HG{n}"),
        two(f"R{22 + 2 * n}", "R", "22", "R", (x + 12, 42), f"LO{n}", f"LG{n}"),
        two(f"D{20 + n}", "D", "UF4007", "D41", (x - 2, 12), f"VB{n}", "+12V", "Bootstrap diode"),
        two(f"C{20 + n}", "CP", "10uF 25V", "CP8", (x + 6, 12), f"VB{n}", out, "Bootstrap capacitor"),
        two(f"C{22 + n}", "C", "100nF", "C", (x - 8, 40), "+12V", "GND"),
    ]


RING = (
    [two("R20", "R", "470 5W", "R_5W", (20, 6), "V_LINE", "BRIDGE_RAIL",
         "R_BRIDGE: limits short-circuit and shoot-through current"),
     two("C24", "C", "100nF 100V", "C", (30, 6), "BRIDGE_RAIL", "GND")]
    + half_bridge(0, 20, "G:RING_DRIVE")
    + half_bridge(1, 62, "RING_DRIVE_N")
    + [P("Q7", "Transistor_BJT:BC547", "BC547", "TO92", (8, 62), {"1": "RING_DRIVE_N", "2": "INV_B", "3": "GND"},
         "Inverter: leg B gets the complement of RING_DRIVE"),
       two("R25", "R", "10k", "R", (2, 56), "G:RING_DRIVE", "INV_B"),
       two("R26", "R", "4k7", "R", (14, 52), "+5V", "RING_DRIVE_N")]
)
RING_FLAGS = []

# Link: ULN2003A relay driver + the L1-L2 audio link relay.
LINK = [
    P("U5", "Transistor_Array:ULN2003A", "ULN2003A", "DIP16", (30, 30), {
        "1": "G:RING_EN_L1", "2": "G:RING_EN_L2", "3": "G:LINK_EN", "4": "GND", "5": "GND",
        "6": "GND", "7": "GND", "8": "GND", "9": "+12V", "16": "G:RELAY_RING_L1",
        "15": "G:RELAY_RING_L2", "14": "RELAY_LINK", "13": "~", "12": "~", "11": "~", "10": "~"}),
    P("K3", "Relay:G5V-2", "HK19F-DC12V-SHG", "RELAY", (70, 30), {
        "1": "+12V", "16": "RELAY_LINK", "4": "G:AUDIO_L1", "8": "G:AUDIO_L2", "6": "~",
        "13": "~", "9": "~", "11": "~"}, "Link relay: joins the line-side audio nodes during a call"),
    two("C30", "C", "100nF", "C", (30, 50), "+12V", "GND"),
]
LINK_FLAGS = []

# Line block (one sheet, used for L1 and L2). "H:" = hierarchical label.
LINE = [
    P("J1", "Connector:RJ12", "RJ11", "RJ11", (10, 40), {"1": "~", "2": "~", "3": "RING", "4": "TIP", "5": "~", "6": "~"},
      "Line jack (6P footprint): centre pair 3/4 = RING/TIP"),
    two("D2", "TVS", "P6KE68CA", "D15", (24, 48), "TIP", "RING", "Line TVS"),
    # Ring relay at rest (NC): TIP<-TIP_FEED, RING->RING_RET. Energised (NO): bridge.
    P("K1", "Relay:G5V-2", "HK19F-DC12V-SHG", "RELAY", (45, 40), {
        "1": "+12V", "16": "H:RING_COIL", "4": "TIP", "6": "TIP_FEED", "8": "H:RING_B",
        "13": "RING", "11": "RING_RET", "9": "H:RING_A"}, "Ring relay (DPDT)"),
    # Loop current limiter (~24 mA).
    two("F1", "PTC", "PTC 100mA", "PTC", (10, 8), "V_LINE", "FEED_C"),
    two("R1", "R", "10k 1/2W", "R_05W", (22, 10), "FEED_C", "Q1B"),
    P("Q1", "Transistor_BJT:BD139", "MJE340", "TO126", (32, 12), {"1": "Q1E", "2": "FEED_C", "3": "Q1B"},
      "Pass transistor, 300 V, small heatsink"),
    two("R2", "R", "27", "R", (42, 14), "Q1E", "TIP_FEED", "R_SENSE: 0.65 V / 27 = 24 mA"),
    P("Q2", "Transistor_BJT:BC546", "BC546", "TO92", (52, 10), {"1": "Q1B", "2": "Q1E", "3": "TIP_FEED"}),
    # Off-hook opto in the return leg.
    P("U1", "Isolator:PC817", "PC817", "DIP4", (70, 40), {"1": "RING_RET", "2": "GND", "3": "GND", "4": "H:OFFHOOK"}),
    two("D1", "1N4148", "1N4148", "D35", (70, 52), "RING_RET", "GND", "Antiparallel to the opto LED"),
    # Audio coupling and protection.
    two("C1", "C", "2.2uF 250V", "C_FILM", (82, 14), "TIP_FEED", "H:AUDIO", "Film coupling capacitor (NC side)"),
    two("R3", "R", "1k", "R", (92, 14), "H:AUDIO", "AUDIO_PROT"),
    two("D3", "1N4148", "1N4148", "D35", (102, 8), "+5V", "AUDIO_PROT", "Clamp to +5 V"),
    two("D4", "1N4148", "1N4148", "D35", (102, 20), "AUDIO_PROT", "GND", "Clamp to GND"),
    # Tone injection: 2-pole RC filter + level trimmer.
    two("R4", "R", "1k", "R", (82, 34), "H:TONE", "TF1"),
    two("C2", "C", "47nF", "C", (88, 40), "TF1", "GND"),
    two("R5", "R", "1k", "R", (94, 34), "TF1", "TF2"),
    two("C3", "C", "47nF", "C", (100, 40), "TF2", "GND"),
    two("R6", "R", "4k7", "R", (106, 34), "TF2", "TF3"),
    P("RV1", "Device:R_Potentiometer_Trim", "47k", "TRIM", (116, 34), {"1": "TF3", "2": "AUDIO_PROT", "3": "AUDIO_PROT"},
      "Tone level"),
    # DTMF receiver (one per line), TOE tied to StD, Q outputs through 1k.
    P("U2", "pots:MT8870", "MT8870", "DIP18", (90, 70), {
        "1": "VREF", "2": "INM", "3": "GS", "4": "VREF", "5": "GND", "6": "GND", "7": "OSC1",
        "8": "OSC2", "9": "GND", "10": "H:STD", "11": "MQ1", "12": "MQ2", "13": "MQ3", "14": "MQ4",
        "15": "H:STD", "16": "EST", "17": "STGT", "18": "+5V"}),
    two("C4", "C", "100nF", "C", (62, 64), "AUDIO_PROT", "INC"),
    two("R7", "R", "100k", "R", (70, 64), "INC", "INM"),
    two("R8", "R", "100k", "R", (70, 74), "GS", "INM", "Gain = 1"),
    two("Y1", "XTAL", "3.579545MHz", "XTAL", (70, 86), "OSC1", "OSC2"),
    two("R9", "R", "300k", "R", (110, 80), "EST", "STGT", "Guard time"),
    two("C5", "C", "100nF", "C", (110, 70), "+5V", "STGT", "Guard time"),
    two("C6", "C", "100nF", "C", (62, 80), "+5V", "GND", "Decoupling"),
    two("R10", "R", "1k", "R", (120, 58), "MQ1", "H:Q1"),
    two("R11", "R", "1k", "R", (126, 58), "MQ2", "H:Q2"),
    two("R12", "R", "1k", "R", (132, 58), "MQ3", "H:Q3"),
    two("R13", "R", "1k", "R", (138, 58), "MQ4", "H:Q4"),
]
LINE_HIER = {  # hierarchical label -> (shape, root net for L1, root net for L2)
    "OFFHOOK": ("output", "OFFHOOK_L1", "OFFHOOK_L2"),
    "RING_COIL": ("passive", "RELAY_RING_L1", "RELAY_RING_L2"),
    "TONE": ("input", "TONE_L1", "TONE_L2"),
    "STD": ("output", "DTMF_STD_L1", "DTMF_STD_L2"),
    "Q1": ("tri_state", "DTMF_Q1", "DTMF_Q1"),
    "Q2": ("tri_state", "DTMF_Q2", "DTMF_Q2"),
    "Q3": ("tri_state", "DTMF_Q3", "DTMF_Q3"),
    "Q4": ("tri_state", "DTMF_Q4", "DTMF_Q4"),
    "AUDIO": ("bidirectional", "AUDIO_L1", "AUDIO_L2"),
    "RING_A": ("passive", "RING_A", "RING_A"),
    "RING_B": ("passive", "RING_B", "RING_B"),
}


# --- project symbol library ----------------------------------------------------
MT8870_PINS = [  # number, name, type, side, slot
    ("1", "IN+", "input", "L", 0), ("2", "IN-", "input", "L", 1), ("3", "GS", "output", "L", 2),
    ("4", "VREF", "output", "L", 3), ("5", "INH", "input", "L", 5), ("6", "PWDN", "input", "L", 6),
    ("7", "OSC1", "input", "L", 8), ("8", "OSC2", "output", "L", 9),
    ("18", "VDD", "power_in", "T", 0), ("9", "VSS", "power_in", "B", 0),
    ("10", "TOE", "input", "R", 0), ("11", "Q1", "tri_state", "R", 2), ("12", "Q2", "tri_state", "R", 3),
    ("13", "Q3", "tri_state", "R", 4), ("14", "Q4", "tri_state", "R", 5), ("15", "StD", "output", "R", 7),
    ("16", "ESt", "output", "R", 8), ("17", "St/GT", "bidirectional", "R", 9),
]


def mt8870_symbol():
    w, h = 10.16, 15.24  # half sizes
    font = "(effects (font (size 1.27 1.27)))"
    pins = []
    for num, name, typ, side, slot in MT8870_PINS:
        if side == "L":
            x, y, a = -w - 2.54, h - 2.54 - slot * 2.54, 0
        elif side == "R":
            x, y, a = w + 2.54, h - 2.54 - slot * 2.54, 180
        elif side == "T":
            x, y, a = 0, h + 2.54, 270
        else:
            x, y, a = 0, -h - 2.54, 90
        pins.append(f'(pin {typ} line (at {x:g} {y:g} {a}) (length 2.54) (name {q(name)} {font}) (number {q(num)} {font}))')
    return f'''(symbol "MT8870" (pin_names (offset 1.016)) (exclude_from_sim no) (in_bom yes) (on_board yes)
  (property "Reference" "U" (at -10.16 16.51 0) {font})
  (property "Value" "MT8870" (at 10.16 16.51 0) {font})
  (property "Footprint" "Package_DIP:DIP-18_W7.62mm" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
  (property "Datasheet" "https://www.microsemi.com/document-portal/doc_download/127041-mt8870d-datasheet" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
  (property "Description" "DTMF receiver, DIP-18" (at 0 0 0) (effects (font (size 1.27 1.27)) (hide yes)))
  (symbol "MT8870_0_1" (rectangle (start {-w:g} {h:g}) (end {w:g} {-h:g}) (stroke (width 0.254) (type default)) (fill (type background))))
  (symbol "MT8870_1_1" {" ".join(pins)}))'''


def v_line_symbol():
    plus12 = kl.get("power:+12V")
    text = kl.dump(plus12).replace('"+12V"', '"V_LINE"').replace('"+12V_', '"V_LINE_')
    return text.replace("Power symbol creates a global label with name \\\"+12V\\\"",
                        "Line feed rail (24-48 V)")


def write_project_lib():
    PROJECT_LIB.write_text(
        "(kicad_symbol_lib (version 20241209) (generator \"pots-gen\")\n"
        + mt8870_symbol() + "\n" + v_line_symbol() + "\n)\n")
    kl._lib_cache.pop(PROJECT_LIB, None)


# --- schematic writer ------------------------------------------------------------
def lib_symbol(lib_id):
    sym = kl.get(lib_id, PROJECT_LIB)
    sym[1] = q(lib_id)
    return kl.dump(sym, 1)


def pin_offset(pin, rot, mirror):
    """Pin position relative to the symbol origin, in schematic coordinates (y down).
    Verified against KiCad netlists for rotations 0/90/180/270."""
    px, py = pin["x"], pin["y"]
    if mirror:
        px = -px
    r = math.radians(rot)
    return (round(px * math.cos(r) - py * math.sin(r), 3), round(-(px * math.sin(r) + py * math.cos(r)), 3))


TWO_TERMINAL = ("Device:", "Diode:", "Switch:SW_SPST")


def field_positions(lib_id, sym, pins, at, rot, mirror, power):
    """Reference/Value positions that read horizontally and stay off the body."""
    x, y = at
    if power:
        if rot in (90, 270):  # horizontal power symbol: text past the graphic
            right = (rot == 270) != (lib_id == "power:GND")
            vx = x + (4.6 if right else -4.6)
            return (x, y + 2.54), (vx, y), ""
        return (x, y + 2.54), (x + 2.54, y + 2.54), ""
    offs = [pin_offset(p, rot, mirror) for p in pins.values()]
    if len(pins) == 2 and lib_id.startswith(TWO_TERMINAL):
        (ax, ay), (bx, by) = offs
        if abs(ay - by) < 0.01:          # horizontal two-pin part: text above/below
            return (x, y - 3.175), (x, y + 3.175), ""
        if abs(ax - bx) < 0.01:          # vertical two-pin part: text to the right
            return (x + 2.54, y - 1.27), (x + 2.54, y + 1.27), "left"
    lib = {kl.unq(p[1]): p for p in kl.find(sym, "property")}

    def lib_at(name, dflt):
        if name not in lib:
            return dflt
        a = kl.find(lib[name], "at")[0]
        ox, oy = pin_offset({"x": float(a[1]), "y": float(a[2])}, rot, mirror)
        return (x + ox, y + oy)

    def lib_just(name):
        if name not in lib or rot or mirror:
            return ""
        eff = kl.find(lib[name], "effects")
        j = kl.find(eff[0], "justify") if eff else []
        return " ".join(j[0][1:]) if j else ""
    ref_at, val_at = lib_at("Reference", (x, y - 2.54)), lib_at("Value", (x, y + 2.54))
    rj, vj = lib_just("Reference"), lib_just("Value")
    if abs(ref_at[1] - val_at[1]) < 0.01 and abs(ref_at[0] - val_at[0]) < 12:
        bottom = max(o[1] for o in offs)
        val_at, vj = (x, y + bottom + 2.54), ""
    return ref_at, val_at, (rj, vj)


def outward(angle):
    return {0: (-1, 0), 180: (1, 0), 90: (0, 1), 270: (0, -1)}[int(angle) % 360]


def label_orient(d):
    # (label angle, justify) so the text sits away from the wire end.
    return {(-1, 0): (180, "right"), (1, 0): (0, "left"), (0, -1): (90, "left"), (0, 1): (270, "right")}[d]


class Sheet:
    def __init__(self, name, title):
        self.name, self.title = name, title
        self.uuid = uid()
        self.items, self.lib_ids = [], set()
        self.problems = []
        self.pwr = 0

    # A3 drawing area (mm) and the title block in its bottom-right corner.
    FRAME = (12.7, 12.7, 407.0, 284.0)
    TITLE_BLOCK = (230.0, 245.0)

    def check_position(self, x, y, what):
        x0, y0, x1, y1 = self.FRAME
        if not (x0 <= x <= x1 and y0 <= y <= y1):
            self.problems.append(f"{self.name}: {what} at ({x:.1f}, {y:.1f}) is outside the frame")
        elif x >= self.TITLE_BLOCK[0] and y >= self.TITLE_BLOCK[1]:
            self.problems.append(f"{self.name}: {what} at ({x:.1f}, {y:.1f}) overlaps the title block")

    def symbol(self, lib_id, at, ref, value, fp, desc, paths, unit=1, power=False, rot=0, mirror=False):
        self.lib_ids.add(lib_id)
        self.check_position(at[0], at[1], f"{paths[0][1]} ({lib_id})")
        sym = kl.get(lib_id, PROJECT_LIB)
        pins = kl.pins(sym)
        x, y = at
        ref = paths[0][1]
        hide = "(hide yes)"
        ref_at, val_at, just = field_positions(lib_id, sym, pins, at, rot, mirror, power)
        fang = 90 if rot in (90, 270) else 0  # displayed angle = field angle + symbol rotation
        rj, vj = just if isinstance(just, tuple) else (just, just)
        if (fang + rot) % 360 == 180:   # KiCad flips 180-degree text: mirror the justification
            flip = {"left": "right", "right": "left"}
            rj, vj = flip.get(rj, rj), flip.get(vj, vj)
        hide_value = lib_id == "power:PWR_FLAG"
        props = [
            ("Reference", ref, ref_at, power, rj),
            ("Value", value, val_at, hide_value, vj),
            ("Footprint", fp, (x, y), True, ""),
            ("Datasheet", "~", (x, y), True, ""),
            ("Description", desc, (x, y), True, ""),
        ]
        ptxt = "".join(
            f'\n\t\t(property {q(k)} {q(v)} (at {px:g} {py:g} {fang}) (effects (font (size 1.27 1.27)) '
            f'{f"(justify {j})" if j else ""} {hide if h else ""}))'
            for k, v, (px, py), h, j in props)
        pintxt = "".join(f'\n\t\t(pin {q(n)} (uuid {q(uid())}))' for n in pins)
        inst = "".join(f'(path {q(p)} (reference {q(r)}) (unit {unit}))' for p, r in paths)
        self.items.append(
            f'\t(symbol (lib_id {q(lib_id)}) (at {x:g} {y:g} {rot}){" (mirror y)" if mirror else ""} (unit {unit}) (exclude_from_sim no) '
            f'(in_bom {"no" if power else "yes"}) (on_board {"no" if power else "yes"}) (dnp no) (uuid {q(uid())})'
            f'{ptxt}{pintxt}\n\t\t(instances (project {q(PROJECT)} {inst})))')
        return pins

    # --- wired drawing helpers -------------------------------------------------
    def place_wired(self, part, paths_fn, rot=0, mirror=False, anchor=None, at=None):
        """Place a part with rotation/mirror; return {pin: (x, y)}. anchor=(pin, point)
        puts that pin exactly on the point. Unconnected pins ("~") get a no-connect."""
        sym = kl.get(part.lib_id, PROJECT_LIB)
        pins = kl.pins(sym)
        if anchor:
            ox, oy = pin_offset(pins[anchor[0]], rot, mirror)
            at = (anchor[1][0] - ox, anchor[1][1] - oy)
        at = (round(at[0], 3), round(at[1], 3))
        self.symbol(part.lib_id, at, None, part.value, part.fp, part.desc, paths_fn(part.ref),
                    rot=rot, mirror=mirror)
        pts = {}
        for n, pin in pins.items():
            ox, oy = pin_offset(pin, rot, mirror)
            pts[n] = (round(at[0] + ox, 3), round(at[1] + oy, 3))
            if part.nets.get(n) == "~":
                self.no_connect(pts[n])
        missing = set(pins) - set(part.nets)
        if missing:
            raise SystemExit(f"{self.name}: {part.ref} pins without net: {missing}")
        return pts

    def path(self, *pts):
        for a, b in zip(pts, pts[1:]):
            if a != b:
                self.wire(a, b)

    def junction(self, pt):
        self.items.append(f'\t(junction (at {pt[0]:g} {pt[1]:g}) (diameter 0) (color 0 0 0 0) (uuid {q(uid())}))')

    def rail(self, pts):
        """Straight rail through points (all on one line); junction at interior points."""
        pts = sorted(set(pts))
        self.path(*pts)
        for p in pts[1:-1]:
            self.junction(p)

    def pwr_at(self, net, pt, rot=0):
        self.pwr += 1
        lib_id = POWER_NETS[net]
        self.symbol(lib_id, pt, None, net, "", "", self.pwr_paths(self.pwr), power=True, rot=rot)

    def wire(self, a, b):
        self.items.append(f'\t(wire (pts (xy {a[0]:g} {a[1]:g}) (xy {b[0]:g} {b[1]:g})) (stroke (width 0) (type default)) (uuid {q(uid())}))')

    def label(self, kind, net, at, d, shape="bidirectional"):
        ang, just = label_orient(d)
        x, y = at
        if kind == "local":
            self.items.append(f'\t(label {q(net)} (at {x:g} {y:g} {ang}) (effects (font (size 1.27 1.27)) (justify {just} bottom)) (uuid {q(uid())}))')
        elif kind == "global":
            self.items.append(f'\t(global_label {q(net)} (shape {shape}) (at {x:g} {y:g} {ang}) (fields_autoplaced yes) '
                              f'(effects (font (size 1.27 1.27)) (justify {just})) (uuid {q(uid())}) '
                              f'(property "Intersheetrefs" "${{INTERSHEET_REFS}}" (at {x:g} {y:g} 0) (effects (font (size 1.27 1.27)) (hide yes))))')
        else:
            self.items.append(f'\t(hierarchical_label {q(net)} (shape {shape}) (at {x:g} {y:g} {ang}) '
                              f'(effects (font (size 1.27 1.27)) (justify {just})) (uuid {q(uid())}))')

    def no_connect(self, at):
        self.items.append(f'\t(no_connect (at {at[0]:g} {at[1]:g}) (uuid {q(uid())}))')

    def power(self, net, at, paths_fn):
        self.pwr += 1
        lib_id = POWER_NETS[net] if net in POWER_NETS else "power:PWR_FLAG"
        value = net if net in POWER_NETS else "PWR_FLAG"
        self.symbol(lib_id, at, None, value, "", "", paths_fn(self.pwr), power=True)

    offset = (0, 0)  # grid units, per sheet

    def place(self, part, paths_fn, hier_shapes=None):
        X, Y = part.at[0] + self.offset[0] * GRID, part.at[1] + self.offset[1] * GRID
        pins = self.symbol(part.lib_id, (X, Y), None, part.value, part.fp, part.desc,
                           paths_fn(part.ref))
        for num, pin in pins.items():
            net = part.nets.get(num)
            end = (X + pin["x"], Y - pin["y"])
            if net is None:
                raise SystemExit(f"{self.name}: {part.ref} pin {num} ({pin['name']}) has no net")
            if net == "~":
                self.no_connect(end)
                continue
            d = outward(pin["angle"])
            stub = STUB * (2 if net in POWER_NETS else 1)
            tip = (end[0] + d[0] * stub, end[1] + d[1] * stub)
            self.wire(end, tip)
            if net in POWER_NETS:
                self.power(net, tip, self.pwr_paths)
            elif net.startswith("G:"):
                self.label("global", net[2:], tip, d)
            elif net.startswith("H:"):
                self.label("hier", net[2:], tip, d, hier_shapes[net[2:]][0])
            else:
                self.label("local", net, tip, d)
        unknown = set(part.nets) - set(pins)
        if unknown:
            raise SystemExit(f"{self.name}: {part.ref} has unknown pins {unknown}")

    def text(self, s, at):
        self.items.append(f'\t(text {q(s)} (exclude_from_sim no) (at {at[0]:g} {at[1]:g} 0) (effects (font (size 2 2)) (justify left bottom)) (uuid {q(uid())}))')

    def render(self, extra=""):
        libs = "\n".join(lib_symbol(l) for l in sorted(self.lib_ids))
        return (f'(kicad_sch (version 20250114) (generator "pots-gen") (generator_version "9.0") (uuid {q(self.uuid)}) (paper "A3")\n'
                f'\t(title_block (title {q(self.title)}) (company "POTS in a box") (comment 1 "Generated by hardware/tools/gen_schematic.py - do not edit by hand"))\n'
                f'\t(lib_symbols\n{libs}\n\t)\n' + "\n".join(self.items) + "\n" + extra +
                '\t(embedded_fonts no)\n)\n')


def g(*v):
    """Grid units -> mm."""
    return tuple(x * GRID for x in v) if len(v) > 1 else v[0] * GRID


def draw_power(sh, paths_fn):
    """Power sheet drawn with wires: 12 V input, 5 V regulator, boost module -> V_LINE."""
    parts = {p.ref: p for p in POWER}

    def put(ref, **kw):
        return sh.place_wired(parts[ref], paths_fn, **kw)

    def flag(pt):
        sh.symbol("power:PWR_FLAG", pt, None, "PWR_FLAG", "", "", sh.pwr_paths(0), power=True)

    y0, yg = g(24), g(40)
    sh.text("12 V input (external adapter)", g(12, 18))
    sh.text("5 V regulator", g(47, 18))
    j1 = put("J1", anchor=("1", g(12, 24)))
    f1 = put("F1", rot=90, anchor=("1", g(18, 24)))
    d1 = put("D1", rot=180, anchor=("2", g(24, 24)))
    sh.path(j1["1"], (g(15), y0), f1["1"])
    sh.junction((g(15), y0))
    flag((g(15), y0))                                  # VIN_RAW is driven by the jack
    sh.path(f1["2"], d1["2"])
    sh.path(j1["2"], (g(14), j1["2"][1]), (g(14), yg))

    caps12 = {"C1": 32, "C2": 38, "C3": 43}
    u1 = put("U1", anchor=("1", g(48, 24)))
    rail12 = [d1["1"], g(29, 24), g(30, 24), u1["1"]] + [g(x, 24) for x in caps12.values()]
    sh.rail(rail12)
    sh.path(g(29, 24), g(29, 21))
    sh.pwr_at("+12V", g(29, 21))
    flag(g(30, 24))
    gnd_pts = [(g(14), yg), g(22, 40), g(23, 40), (u1["2"][0], yg)]
    for ref, x in caps12.items():
        c = put(ref, anchor=("1", g(x, 27)))
        sh.path(g(x, 24), c["1"])
        sh.path(c["2"], (g(x), yg))
        gnd_pts.append((g(x), yg))
    sh.path(u1["2"], (u1["2"][0], yg))

    rail5 = [u1["3"], g(56, 24)]
    for ref, x in {"C4": 58, "C5": 63}.items():
        c = put(ref, anchor=("1", g(x, 27)))
        sh.path(g(x, 24), c["1"])
        sh.path(c["2"], (g(x), yg))
        rail5.append(g(x, 24))
        gnd_pts.append((g(x), yg))
    r2 = put("R2", anchor=("1", g(70, 27)))
    d2 = put("D2", rot=90, anchor=("2", g(70, 32)))
    rail5.append(g(70, 24))
    sh.rail(rail5)
    sh.path(g(70, 24), r2["1"])
    sh.path(r2["2"], d2["2"])
    sh.path(d2["1"], (g(70), yg))
    gnd_pts.append((g(70), yg))
    sh.path(g(56, 24), g(56, 21))
    sh.pwr_at("+5V", g(56, 21))
    sh.rail(gnd_pts)
    sh.path(g(22, 40), g(22, 42))
    sh.pwr_at("GND", g(22, 42))
    flag(g(23, 40))

    # Boost module -> V_LINE (24-48 V).
    sh.text("Boost module -> V_LINE (24-48 V)", g(8, 47))
    y1, yg2 = g(52), g(66)
    j2 = put("J2", mirror=True, anchor=("1", g(14, 52)))
    sh.path(j2["1"], g(17, 52), g(17, 50))
    sh.pwr_at("+12V", g(17, 50))
    sh.path(j2["2"], g(15, 53))
    sh.pwr_at("GND", g(15, 53), rot=90)
    rail_v = [j2["3"], g(20, 54), g(21, 54)]
    gnd2 = [g(16, 66), g(22, 66)]
    for ref, x in {"R1": 26, "C6": 31}.items():
        c = put(ref, anchor=("1", g(x, 57)))
        sh.path(g(x, 54), c["1"])
        sh.path(c["2"], g(x, 66))
        rail_v.append(g(x, 54))
        gnd2.append(g(x, 66))
    sh.rail(rail_v)
    sh.path(g(20, 54), g(20, 51))
    sh.pwr_at("V_LINE", g(20, 51))
    flag(g(21, 54))
    sh.path(j2["4"], g(16, 55), g(16, 66))
    sh.rail(gnd2)
    sh.path(g(22, 66), g(22, 68))
    sh.pwr_at("GND", g(22, 68))


def term(sh, net, pt, d):
    """Terminate a wire end: power symbol, hierarchical/global/local label, facing d."""
    if net in POWER_NETS:
        up = {(0, -1): 0, (0, 1): 180, (-1, 0): 90, (1, 0): 270}
        down = {(0, 1): 0, (0, -1): 180, (-1, 0): 270, (1, 0): 90}
        sh.pwr_at(net, pt, rot=(down if net == "GND" else up)[d])
    elif net.startswith("H:"):
        sh.label("hier", net[2:], pt, d, LINE_HIER[net[2:]][0])
    elif net.startswith("G:"):
        sh.label("global", net[2:], pt, d)
    else:
        sh.label("local", net, pt, d)


def stub(sh, pin_pt, d, net, length=1):
    tip = (pin_pt[0] + d[0] * g(length), pin_pt[1] + d[1] * g(length))
    sh.path(pin_pt, tip)
    term(sh, net, tip, d)
    return tip


UP, DOWN, LEFT, RIGHT = (0, -1), (0, 1), (-1, 0), (1, 0)


def draw_line(sh, paths_fn):
    """Line block drawn with wires (labels only where a wire would have to cross)."""
    parts = {p.ref: p for p in LINE}

    def put(ref, **kw):
        return sh.place_wired(parts[ref], paths_fn, **kw)

    P = lambda x, y: g(x, y)

    # --- Loop feed: current limiter (~24 mA) ---------------------------------
    sh.text("Loop feed: current limiter (~24 mA)", P(7, 7))
    f1 = put("F1", rot=90, anchor=("1", P(8, 12)))
    term(sh, "V_LINE", P(6, 10), UP)
    sh.path(P(6, 10), P(6, 12), f1["1"])
    r1 = put("R1", anchor=("1", P(14, 13)))
    q1 = put("Q1", anchor=("2", P(22, 14)))
    sh.path(f1["2"], P(14, 12), P(22, 12), q1["2"])
    sh.junction(P(14, 12))
    sh.path(P(14, 12), r1["1"])
    sh.path(r1["2"], P(17, 16), q1["3"])
    sh.junction(P(17, 16))
    q2 = put("Q2", mirror=True, anchor=("2", P(20, 19)))
    sh.path(q2["1"], P(17, 16))
    r2 = put("R2", anchor=("1", P(22, 20)))
    sh.path(q1["1"], P(22, 19), r2["1"])
    sh.path(q2["2"], P(22, 19))
    sh.junction(P(22, 19))
    sh.path(r2["2"], P(22, 25))
    sh.path(q2["3"], P(17, 25), P(22, 25))
    sh.junction(P(22, 25))

    # --- Audio coupling (NC side of the ring relay) and protection -------------
    sh.text("Audio coupling and protection", P(28, 17))
    c1 = put("C1", rot=90, anchor=("1", P(28, 25)))
    sh.path(P(22, 25), P(26, 25), c1["1"])
    sh.junction(P(26, 25))
    stub(sh, P(26, 25), UP, "TIP_FEED", 2)
    r3 = put("R3", rot=90, anchor=("1", P(38, 25)))
    sh.path(c1["2"], P(34, 25), r3["1"])
    sh.junction(P(34, 25))
    stub(sh, P(34, 25), UP, "H:AUDIO", 2)
    d3 = put("D3", rot=270, anchor=("2", P(44, 24)))
    d4 = put("D4", rot=270, anchor=("1", P(44, 26)))
    c4 = put("C4", rot=90, anchor=("1", P(72, 25)))
    sh.rail([r3["2"], P(44, 25), P(66, 25), c4["1"]])
    sh.path(P(44, 25), d3["2"])
    sh.path(P(44, 25), d4["1"])
    stub(sh, d3["1"], UP, "+5V", 2)
    stub(sh, d4["2"], DOWN, "GND", 2)

    # --- Tone injection: 2-pole RC + level trimmer ----------------------------
    sh.text("Tone injection", P(49, 31.5))
    term(sh, "H:TONE", P(38, 34), LEFT)
    r4 = put("R4", rot=90, anchor=("1", P(40, 34)))
    sh.path(P(38, 34), r4["1"])
    r5 = put("R5", rot=90, anchor=("1", P(49, 34)))
    r6 = put("R6", rot=90, anchor=("1", P(56, 34)))
    rv1 = put("RV1", rot=90, anchor=("1", P(61, 34)))
    sh.path(r4["2"], P(47, 34), r5["1"])
    sh.path(r5["2"], P(54, 34), r6["1"])
    sh.path(r6["2"], rv1["1"])
    for ref, x in (("C2", 47), ("C3", 54)):
        c = put(ref, anchor=("1", P(x, 36)))
        sh.junction(P(x, 34))
        sh.path(P(x, 34), c["1"])
        stub(sh, c["2"], DOWN, "GND", 1)
    sh.path(rv1["3"], P(66, 34), P(66, 31.5), P(66, 25))
    sh.path(rv1["2"], P(62.5, 31.5), P(66, 31.5))
    sh.junction(P(66, 31.5))

    # --- DTMF receiver ----------------------------------------------------------
    sh.text("DTMF receiver (TOE tied to StD)", P(76, 18))
    u2 = put("U2", anchor=("18", P(90, 33)))
    r7 = put("R7", anchor=("1", P(78, 26)))
    sh.path(c4["2"], P(78, 25), r7["1"])
    sh.path(r7["2"], P(78, 36))
    sh.path(u2["2"], P(78, 36))
    sh.junction(P(78, 36))
    r8 = put("R8", rot=270, anchor=("1", P(81, 39)))
    sh.path(u2["3"], P(81, 37), r8["1"])
    sh.path(r8["2"], P(78, 39), P(78, 36))
    stub(sh, u2["1"], LEFT, "VREF", 1)
    stub(sh, u2["4"], LEFT, "VREF", 1)
    sh.path(u2["5"], P(84, 40), P(84, 41))
    sh.path(u2["6"], P(84, 41), P(83, 41))
    sh.junction(P(84, 41))
    term(sh, "GND", P(83, 41), LEFT)
    y1 = put("Y1", rot=270, anchor=("1", P(72, 43)))
    sh.path(u2["7"], y1["1"])
    sh.path(u2["8"], P(82, 44), P(82, 46), y1["2"])
    c6 = put("C6", rot=90, anchor=("1", P(94, 29)))
    sh.path(u2["18"], P(90, 29), c6["1"])
    sh.junction(P(90, 29))
    stub(sh, P(90, 29), UP, "+5V", 2)
    stub(sh, c6["2"], RIGHT, "GND", 1)
    stub(sh, u2["9"], DOWN, "GND", 2)
    stub(sh, u2["10"], RIGHT, "H:STD", 1)
    stub(sh, u2["15"], RIGHT, "H:STD", 1)
    for pin, net in (("11", "MQ1"), ("12", "MQ2"), ("13", "MQ3"), ("14", "MQ4"),
                     ("16", "EST"), ("17", "STGT")):
        stub(sh, u2[pin], RIGHT, net, 1)
    # Guard time: ESt -> R9 -> St/GT, C5 to VDD.
    r9 = put("R9", rot=90, anchor=("1", P(106, 48)))
    stub(sh, r9["1"], LEFT, "EST", 2)
    c5 = put("C5", anchor=("2", P(111, 47)))
    sh.path(r9["2"], P(111, 48), P(113, 48))
    sh.path(P(111, 48), c5["2"])
    sh.junction(P(111, 48))
    term(sh, "STGT", P(113, 48), RIGHT)
    stub(sh, c5["1"], UP, "+5V", 2)
    # Q outputs through 1k to the shared bus.
    for i, ref in enumerate(("R10", "R11", "R12", "R13")):
        y = 54 + 4 * i
        r = put(ref, rot=90, anchor=("1", P(103, y)))
        stub(sh, r["1"], LEFT, f"MQ{i + 1}", 2)
        stub(sh, r["2"], RIGHT, f"H:Q{i + 1}", 2)

    # --- Line jack, TVS and ring relay -------------------------------------------
    sh.text("Line jack, TVS and ring relay (drawn at rest: NC)", P(8, 44))
    j1 = put("J1", anchor=("4", P(14, 68)))
    k1 = put("K1", anchor=("4", P(40, 59)))
    d2 = put("D2", rot=270, anchor=("1", P(24, 67)))
    sh.path(j1["4"], P(16, 68), P(16, 64), P(24, 64), P(40, 64), k1["4"])
    sh.path(j1["3"], P(17, 69), P(17, 74), P(24, 74), P(44, 74), k1["13"])
    sh.junction(P(24, 64))
    sh.junction(P(24, 74))
    sh.path(P(24, 64), d2["1"])
    sh.path(d2["2"], P(24, 74))
    stub(sh, k1["1"], UP, "+12V", 2)
    stub(sh, k1["16"], LEFT, "H:RING_COIL", 2)
    stub(sh, k1["6"], UP, "TIP_FEED", 2)
    stub(sh, k1["8"], UP, "H:RING_B", 2)
    stub(sh, k1["11"], UP, "RING_RET", 2)
    stub(sh, k1["9"], UP, "H:RING_A", 2)

    # --- Off-hook detector (opto in the return leg) -----------------------------
    sh.text("Off-hook detector (return leg)", P(50, 60))
    u1 = put("U1", anchor=("1", P(59, 65)))
    d1 = put("D1", rot=270, anchor=("1", P(53, 66)))
    term(sh, "RING_RET", P(50, 65), LEFT)
    sh.path(P(50, 65), P(53, 65), u1["1"])
    sh.junction(P(53, 65))
    sh.path(P(53, 65), d1["1"])
    sh.path(d1["2"], P(53, 71))
    sh.path(u1["2"], P(59, 71))
    sh.path(u1["3"], P(65, 71))
    sh.rail([P(53, 71), P(59, 71), P(65, 71)])
    stub(sh, P(59, 71), DOWN, "GND", 2)
    stub(sh, u1["4"], RIGHT, "H:OFFHOOK", 3)


def draw_ring(sh, paths_fn):
    """Shared ring H-bridge: two IR2104 half bridges drawn the classic way."""
    parts = {p.ref: p for p in RING}

    def put(ref, **kw):
        return sh.place_wired(parts[ref], paths_fn, **kw)

    P = lambda x, y: g(x, y)
    sh.text("Ring generator: shared H-bridge (2 x IR2104 + 4 x IRF540N)", P(6, 10))
    sh.text("~SD tied to VCC (logic input rated to VCC): drivers always enabled", P(6, 12.5))

    # Bridge rail: V_LINE -> R_BRIDGE -> both high-side drains.
    r20 = put("R20", rot=90, anchor=("1", P(8, 20)))
    term(sh, "V_LINE", P(6, 18), UP)
    sh.path(P(6, 18), P(6, 20), r20["1"])
    c24 = put("C24", anchor=("1", P(14, 22)))
    rail = [r20["2"], P(14, 20)]
    sh.path(P(14, 20), c24["1"])
    stub(sh, c24["2"], DOWN, "GND", 1)
    gnd = []

    for n, ox, drive, out in ((0, 0, "G:RING_DRIVE", "G:RING_A"), (1, 40, "RING_DRIVE_N", "G:RING_B")):
        X = lambda x: x + ox
        u = put(f"U{3 + n}", anchor=("1", P(X(24), 35)))
        qh = put(f"Q{3 + 2 * n}", anchor=("1", P(X(40), 32)))
        ql = put(f"Q{4 + 2 * n}", anchor=("1", P(X(40), 48)))
        rh = put(f"R{21 + 2 * n}", rot=90, anchor=("1", P(X(35), 32)))
        rl = put(f"R{22 + 2 * n}", rot=90, anchor=("1", P(X(35), 48)))
        cb = put(f"C{20 + n}", anchor=("1", P(X(47), 35)))
        db = put(f"D{20 + n}", rot=90, anchor=("1", P(X(47), 32)))
        cd = put(f"C{22 + n}", anchor=("1", P(X(16), 33)))
        sh.text(f"Leg {'AB'[n]}", P(X(22), 27))
        # Supply and decoupling.
        sh.path(u["1"], P(X(24), 32), P(X(24), 31))
        term(sh, "+12V", P(X(24), 31), UP)
        sh.path(P(X(24), 32), P(X(16), 32), cd["1"])
        sh.junction(P(X(24), 32))
        stub(sh, cd["2"], DOWN, "GND", 1)
        # Inputs.
        stub(sh, u["2"], LEFT, drive, 4)
        sh.path(u["3"], P(X(20), 41), P(X(20), 43))
        term(sh, "+12V", P(X(20), 43), DOWN)
        # Gate drive.
        sh.path(u["7"], P(X(33), 38), P(X(33), 32), rh["1"])
        sh.path(rh["2"], qh["1"])
        sh.path(u["5"], P(X(31), 43), P(X(31), 48), rl["1"])
        sh.path(rl["2"], ql["1"])
        # Output node: high-side source, low-side drain, VS, bootstrap, ring output.
        sh.path(qh["3"], P(X(43), 40), P(X(43), 42), P(X(43), 44), ql["2"])
        for y in (40, 42, 44):
            sh.junction(P(X(43), y))
        sh.path(u["6"], P(X(43), 42))
        sh.path(P(X(43), 40), P(X(47), 40), cb["2"])
        stub(sh, P(X(43), 44), RIGHT, out, 6)
        # Bootstrap: +12V -> diode -> VB node -> capacitor -> VS.
        sh.path(cb["1"], P(X(47), 33), db["1"])
        sh.junction(P(X(47), 33))
        stub(sh, P(X(47), 33), RIGHT, f"VB{n}", 2)
        stub(sh, db["2"], UP, "+12V", 2)
        stub(sh, u["8"], RIGHT, f"VB{n}", 1)
        # Rail and ground.
        sh.path(qh["2"], P(X(43), 20))
        rail.append(P(X(43), 20))
        sh.path(u["4"], P(X(24), 54))
        sh.path(ql["3"], P(X(43), 54))
        gnd += [P(X(24), 54), P(X(43), 54)]

    sh.rail(rail)
    gnd.append(P(52, 54))
    sh.rail(gnd)
    stub(sh, P(52, 54), DOWN, "GND", 2)

    # Inverter for leg B.
    sh.text("Inverter: leg B gets the complement of RING_DRIVE", P(6, 60))
    q7 = put("Q7", anchor=("2", P(22, 73)))
    r25 = put("R25", rot=90, anchor=("2", P(20, 73)))
    sh.path(r25["2"], q7["2"])
    stub(sh, r25["1"], LEFT, "G:RING_DRIVE", 2)
    r26 = put("R26", anchor=("2", P(25, 70)))
    sh.path(q7["1"], P(25, 70.5), r26["2"])
    stub(sh, r26["1"], UP, "+5V", 2)
    sh.path(P(25, 70.5), P(27, 70.5))
    sh.junction(P(25, 70.5))
    term(sh, "RING_DRIVE_N", P(27, 70.5), RIGHT)
    stub(sh, q7["3"], DOWN, "GND", 2)


def draw_mcu(sh, paths_fn):
    """MCU sheet: ATmega328P with labelled I/O; local circuits drawn with wires."""
    parts = {p.ref: p for p in MCU}

    def put(ref, **kw):
        return sh.place_wired(parts[ref], paths_fn, **kw)

    P = lambda x, y: g(x, y)
    sh.text("ATmega328P - pin map = firmware/README.md (Arduino Uno compatible)", P(8, 9))
    u = put("U2", anchor=("7", P(40, 25)))
    # Supply, decoupling and AREF.
    sh.path(u["7"], P(40, 21), P(40, 18), P(40, 16))
    term(sh, "+5V", P(40, 16), UP)
    sh.path(u["20"], P(41, 21), P(40, 21))
    sh.junction(P(40, 21))
    c12, c13 = put("C12", anchor=("1", P(35, 19))), put("C13", anchor=("1", P(30, 19)))
    sh.rail([P(40, 18), P(35, 18), P(30, 18)])
    for c, x in ((c12, 35), (c13, 30)):
        sh.path(P(x, 18), c["1"])
        stub(sh, c["2"], DOWN, "GND", 1)
    c14 = put("C14", anchor=("1", P(28, 29)))
    sh.path(u["21"], P(28, 28), c14["1"])
    stub(sh, c14["2"], DOWN, "GND", 1)
    stub(sh, u["8"], DOWN, "GND", 2)
    # I/O on the right side.
    io = {"14": "G:RING_EN_L1", "15": "G:RING_EN_L2", "16": "G:LINK_EN", "17": "G:MOSI",
          "18": "G:COUNTRY_SW", "19": "G:SCK", "23": "G:OFFHOOK_L1", "24": "G:OFFHOOK_L2",
          "25": "G:DTMF_Q1", "26": "G:DTMF_Q2", "27": "G:DTMF_Q3", "28": "G:DTMF_Q4",
          "1": "G:RESET", "2": "G:UART_RX", "3": "G:UART_TX", "4": "G:DTMF_STD_L1", "5": "G:LED_CALL",
          "6": "G:RING_DRIVE", "11": "G:TONE_L2", "12": "G:TONE_L1", "13": "G:DTMF_STD_L2"}
    for pin, net in io.items():
        stub(sh, u[pin], RIGHT, net, 2)
    # 16 MHz crystal.
    sh.text("16 MHz", P(62, 31))
    y1 = put("Y1", rot=270, anchor=("1", P(64, 34)))
    c10, c11 = put("C10", anchor=("1", P(70, 35))), put("C11", anchor=("1", P(64, 39)))
    sh.path(u["9"], y1["1"])
    sh.path(y1["1"], P(70, 34), c10["1"])
    sh.junction(y1["1"])
    sh.path(u["10"], P(62, 35), P(62, 37), y1["2"])
    sh.path(y1["2"], c11["1"])
    sh.junction(y1["2"])
    stub(sh, c10["2"], DOWN, "GND", 1)
    stub(sh, c11["2"], DOWN, "GND", 1)
    # ISP header and reset network (pull-up, auto-reset from DTR).
    sh.text("ISP / reset", P(76, 15))
    j3 = put("J3", anchor=("2", P(79, 20)))
    stub(sh, j3["2"], UP, "+5V", 1)
    stub(sh, j3["6"], DOWN, "GND", 1)
    for pin, net in (("1", "G:COUNTRY_SW"), ("4", "G:MOSI"), ("3", "G:SCK")):
        stub(sh, j3[pin], RIGHT, net, 2)
    r10 = put("R10", anchor=("2", P(96, 25)))
    sh.path(j3["5"], P(96, 26), r10["2"])
    stub(sh, r10["1"], UP, "+5V", 2)
    sh.path(P(96, 26), P(99, 26))
    sh.junction(P(96, 26))
    term(sh, "G:RESET", P(99, 26), RIGHT)
    c15 = put("C15", rot=180, anchor=("2", P(96, 28)))
    sh.path(P(96, 26), c15["2"])
    # USB-serial header (FTDI style).
    sh.text("USB-serial (FTDI)", P(80, 35))
    j4 = put("J4", mirror=True, anchor=("6", P(88, 43)))
    sh.path(j4["6"], P(96, 43), c15["1"])
    stub(sh, j4["1"], RIGHT, "GND", 2)
    stub(sh, j4["3"], RIGHT, "+5V", 2)
    stub(sh, j4["4"], RIGHT, "G:UART_RX", 2)
    stub(sh, j4["5"], RIGHT, "G:UART_TX", 2)
    # Call LED, RING_DRIVE pull-down, AR/US switch.
    sh.text("Call LED / PD4 pull-down / AR-US switch (1k keeps ISP working)", P(8, 61))
    r12 = put("R12", rot=90, anchor=("1", P(12, 66)))
    d10 = put("D10", rot=180, anchor=("2", P(18, 66)))
    stub(sh, r12["1"], LEFT, "G:LED_CALL", 2)
    sh.path(r12["2"], d10["2"])
    stub(sh, d10["1"], RIGHT, "GND", 1)
    r13 = put("R13", rot=90, anchor=("1", P(12, 72)))
    stub(sh, r13["1"], LEFT, "G:RING_DRIVE", 2)
    stub(sh, r13["2"], RIGHT, "GND", 1)
    r11 = put("R11", rot=90, anchor=("1", P(12, 78)))
    sw = put("SW1", anchor=("1", P(18, 78)))
    stub(sh, r11["1"], LEFT, "G:COUNTRY_SW", 2)
    sh.path(r11["2"], sw["1"])
    stub(sh, sw["2"], RIGHT, "GND", 1)


def draw_link(sh, paths_fn):
    """Relay driver (ULN2003A) and the L1-L2 audio link relay."""
    parts = {p.ref: p for p in LINK}

    def put(ref, **kw):
        return sh.place_wired(parts[ref], paths_fn, **kw)

    P = lambda x, y: g(x, y)
    sh.text("Relay driver (ULN2003A, internal flyback diodes to COM) and L1-L2 link relay", P(8, 15))
    u = put("U5", anchor=("1", P(26, 28)))
    for pin, net in (("1", "G:RING_EN_L1"), ("2", "G:RING_EN_L2"), ("3", "G:LINK_EN")):
        stub(sh, u[pin], LEFT, net, 3)
    for pin in ("4", "5", "6", "7"):
        sh.path(u[pin], (g(25), u[pin][1]))
    sh.rail([P(25, 31), P(25, 32), P(25, 33), P(25, 34), P(25, 36)])
    term(sh, "GND", P(25, 36), DOWN)
    stub(sh, u["8"], DOWN, "GND", 2)
    sh.path(u["9"], P(36, 26), P(36, 24))
    term(sh, "+12V", P(36, 24), UP)
    stub(sh, u["16"], RIGHT, "G:RELAY_RING_L1", 3)
    stub(sh, u["15"], RIGHT, "G:RELAY_RING_L2", 3)
    k3 = put("K3", anchor=("16", P(46, 33)))
    sh.path(u["14"], P(40, 30), P(40, 33), k3["16"])
    stub(sh, k3["1"], UP, "+12V", 2)
    stub(sh, k3["4"], DOWN, "G:AUDIO_L1", 2)
    stub(sh, k3["8"], UP, "G:AUDIO_L2", 2)
    c30 = put("C30", anchor=("1", P(16, 22)))
    stub(sh, c30["1"], UP, "+12V", 1)
    stub(sh, c30["2"], DOWN, "GND", 1)


DRAW = {"power": draw_power, "ring": draw_ring, "mcu": draw_mcu, "link": draw_link}


def build():
    missing = check_footprints()
    ROOT.mkdir(parents=True, exist_ok=True)
    write_project_lib()

    root = Sheet(PROJECT, "POTS in a box - 2-line analog telephone exchange")
    rp = f"/{root.uuid}"
    pwr_counter = [0]

    def next_pwr():
        pwr_counter[0] += 1
        return f"#PWR{pwr_counter[0]:03d}"

    flat = [("power", "Power", POWER, POWER_FLAGS, (4, 4)), ("mcu", "MCU", MCU, MCU_FLAGS, (4, 4)),
            ("ring", "Ring generator", RING, RING_FLAGS, (10, 14)),
            ("link", "Relay driver and link", LINK, LINK_FLAGS, (4, 4))]
    sheets = []
    for i, (fname, title, parts, flags, off) in enumerate(flat):
        sh = Sheet(fname, title)
        sh.offset = off
        sh.sheet_uuid = uid()
        path = f"{rp}/{sh.sheet_uuid}"
        sh.pwr_paths = lambda n, path=path: [(path, next_pwr())]
        if fname in DRAW:
            DRAW[fname](sh, lambda ref, path=path: [(path, ref)])
            flags = []
        else:
            for part in parts:
                sh.place(part, lambda ref, path=path: [(path, ref)])
        for j, net in enumerate(flags):
            # PWR_FLAG on a short stub labelled with the net.
            at = ((10 + 8 * j) * GRID, 92 * GRID)
            pins = sh.symbol("power:PWR_FLAG", at, None, "PWR_FLAG", "", "", [(path, next_pwr())], power=True)
            tip = (at[0], at[1] + 5.08)
            sh.wire(at, tip)
            if net in POWER_NETS:
                sh.power(net, tip, sh.pwr_paths)
            else:
                sh.label("local", net, tip, (0, 1))
        sheets.append((fname, title, sh, []))

    # Line sheet, instantiated twice.
    line = Sheet("line", "Line block (one per line)")
    inst = [uid(), uid()]
    paths = [f"{rp}/{inst[0]}", f"{rp}/{inst[1]}"]

    def line_refs(ref):
        letters = "".join(c for c in ref if not c.isdigit())
        num = int("".join(c for c in ref if c.isdigit()))
        return [(paths[0], f"{letters}{100 + num}"), (paths[1], f"{letters}{200 + num}")]

    line.offset = (4, 6)
    line.pwr_paths = lambda n: [(paths[0], next_pwr()), (paths[1], next_pwr())]
    draw_line(line, line_refs)
    line.text("TIP/RING: 48 V and ring (+-48 V) - keep clearance from the logic side.", (10 * GRID, 110 * GRID))

    # Root: sheet symbols.
    sheet_blocks = []
    x0 = 25.4
    for i, (fname, title, sh, _) in enumerate(sheets):
        x, y = x0 + i * 50.8, 25.4
        sheet_blocks.append(sheet_symbol(fname, title, sh.sheet_uuid, (x, y), (38.1, 20.32), [], rp, i + 2))
    for k, (name, uid_) in enumerate((("line_L1", inst[0]), ("line_L2", inst[1]))):
        x, y = x0 + k * 101.6, 76.2
        pins = list(LINE_HIER)
        h = (len(pins) + 1) * 2.54 * 2
        block, pin_pts = sheet_symbol(name, "line", uid_, (x, y), (40.64, h), pins, rp, 6 + k, line_file=True)
        sheet_blocks.append(block)
        for pname, pt in pin_pts:
            tip = (pt[0] + 5.08, pt[1])
            root.wire(pt, tip)
            root.label("global", LINE_HIER[pname][1 + k], tip, (1, 0))
    root.text("POTS in a box - see docs/superpowers/specs/2026-11-13-pots-2-lineas-design.md", (25.4, 15.24))

    (ROOT / f"{PROJECT}.kicad_sch").write_text(root.render("\n".join(sheet_blocks) + "\n" + sheet_instances(len(sheets) + 2)))
    for fname, _, sh, _ in sheets:
        (ROOT / f"{fname}.kicad_sch").write_text(sh.render())
    (ROOT / "line.kicad_sch").write_text(line.render())
    write_project_files()
    problems = root.problems + line.problems + [p for _, _, sh, _ in sheets for p in sh.problems]
    return missing + problems


def intended_nets():
    """{key: set((ref, pin))} from the part tables, keyed like the real netlist would be."""
    nets = {}

    def add(key, node):
        nets.setdefault(key, set()).add(node)

    for sheet, parts in (("power", POWER), ("mcu", MCU), ("ring", RING), ("link", LINK)):
        for p in parts:
            for pin, n in p.nets.items():
                if n == "~":
                    continue
                key = n if n in POWER_NETS else n[2:] if n.startswith("G:") else f"{sheet}/{n}"
                add(key, (p.ref, pin))
    for k in (0, 1):
        for p in LINE:
            letters = "".join(c for c in p.ref if not c.isdigit())
            ref = f"{letters}{(k + 1) * 100 + int(''.join(c for c in p.ref if c.isdigit()))}"
            for pin, n in p.nets.items():
                if n == "~":
                    continue
                if n in POWER_NETS:
                    key = n
                elif n.startswith("H:"):
                    key = LINE_HIER[n[2:]][1 + k]
                else:
                    key = f"line{k}/{n}"
                add(key, (ref, pin))
    return nets


def verify_netlist():
    """Export the netlist with kicad-cli and compare it with the part tables."""
    cli = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
    out = ROOT / ".verify.net"
    subprocess.run([cli, "sch", "export", "netlist", "-o", str(out), str(ROOT / f"{PROJECT}.kicad_sch")],
                   check=True, capture_output=True)
    tree = kl.parse(out.read_text())
    out.unlink()
    real = {}
    for n in kl.find(kl.find(tree, "nets")[0], "net"):
        name = kl.unq(kl.find(n, "name")[0][1])
        real[name] = {(kl.unq(kl.find(x, "ref")[0][1]), kl.unq(kl.find(x, "pin")[0][1]))
                      for x in kl.find(n, "node")}
    where = {node: name for name, nodes in real.items() for node in nodes}
    errors = []
    for key, nodes in sorted(intended_nets().items()):
        found = {where.get(nd) for nd in nodes}
        if len(found) != 1 or None in found:
            errors.append(f"net {key}: pins split across {sorted(map(str, found))}")
            continue
        extra = real[found.pop()] - nodes
        if extra:
            errors.append(f"net {key}: also joined to {sorted(extra)}")
    return errors


def sheet_symbol(name, title, sheet_uuid, at, size, pins, root_path, page, line_file=False):
    x, y = at
    w, h = size
    fname = "line.kicad_sch" if line_file else f"{name}.kicad_sch"
    pin_txt, pts = [], []
    for i, p in enumerate(pins):
        py = y + 5.08 + i * 5.08
        px = x + w
        shape = LINE_HIER[p][0]
        pin_txt.append(f'\t\t(pin {q(p)} {shape} (at {px:g} {py:g} 0) (effects (font (size 1.27 1.27)) (justify right)) (uuid {q(uid())}))')
        pts.append((p, (px, py)))
    block = (f'\t(sheet (at {x:g} {y:g}) (size {w:g} {h:g}) (exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no) '
             f'(fields_autoplaced yes) (stroke (width 0.1524) (type solid)) (fill (color 0 0 0 0.0000)) (uuid {q(sheet_uuid)})\n'
             f'\t\t(property "Sheetname" {q(name)} (at {x:g} {y - 0.7:g} 0) (effects (font (size 1.27 1.27)) (justify left bottom)))\n'
             f'\t\t(property "Sheetfile" {q(fname)} (at {x:g} {y + h + 0.6:g} 0) (effects (font (size 1.27 1.27)) (justify left top)))\n'
             + "\n".join(pin_txt) +
             f'\n\t\t(instances (project {q(PROJECT)} (path {q(root_path)} (page {q(page)})))))')
    return (block, pts) if line_file else block


def sheet_instances(n):
    return '\t(sheet_instances (path "/" (page "1")))\n'


def write_project_files():
    tpl = Path("/Applications/KiCad/KiCad.app/Contents/SharedSupport/template/kicad.kicad_pro")
    pro = json.loads(tpl.read_text())
    pro.setdefault("meta", {})["filename"] = f"{PROJECT}.kicad_pro"
    (ROOT / f"{PROJECT}.kicad_pro").write_text(json.dumps(pro, indent=2) + "\n")
    (ROOT / "sym-lib-table").write_text(
        '(sym_lib_table\n  (version 7)\n  (lib (name "pots")(type "KiCad")(uri "${KIPRJMOD}/pots.kicad_sym")(options "")(descr "POTS in a box parts"))\n)\n')


if __name__ == "__main__":
    missing = build()
    print("written to", ROOT)
    errs = verify_netlist()
    print("netlist check:", "OK" if not errs else f"{len(errs)} problem(s)")
    for e in errs:
        print("  ", e)
    if missing:
        print("problems:")
        for m in missing:
            print("  ", m)
