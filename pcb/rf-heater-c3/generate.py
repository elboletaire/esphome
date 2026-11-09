#!/usr/bin/env python3
"""Generate the rf-heater-c3 carrier PCB (KiCad 10) from scratch.

Run with the interpreter bundled with KiCad:

    /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 -I generate.py

Steps: build the board (outline, footprints, nets, silkscreen, keepouts),
autoroute it with Freerouting through a Specctra DSN/SES round trip, add the
GND pours, save, then write the minimal project file, DRC report, Gerbers +
drill zip and renders. Coordinates are board-relative mm, y grows downward.
"""

import json
import os
import pathlib
import re
import shutil
import subprocess
import tempfile
import zipfile

import pcbnew as pn
from pcbnew import FromMM as mm
from pcbnew import VECTOR2I as V

HERE = pathlib.Path(__file__).resolve().parent
PROJECT = "rf-heater-c3"
PCB_PATH = HERE / f"{PROJECT}.kicad_pcb"
PRO_PATH = HERE / f"{PROJECT}.kicad_pro"
PRL_PATH = HERE / f"{PROJECT}.kicad_prl"
BUILD_DIR = HERE / "build"
FAB_ZIP = HERE / "fab" / f"{PROJECT}-gerbers.zip"
RENDER_TOP = HERE / "render-top.png"
RENDER_BOTTOM = HERE / "render-bottom.png"

KICAD_CLI = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
FOOTPRINT_LIBS = "/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints"
FREEROUTING_JAR = os.path.expanduser("~/.local/share/freerouting/freerouting-2.5.0.jar")
FREEROUTING_PASSES = 50

# Board and design rules (mm)
BOARD_W = 43.7
BOARD_H = 30.0
BOARD_DATE = "2026-11-09"
COPPER_EDGE_CLEARANCE = 0.3
CLEARANCE = 0.2
SIGNAL_TRACK = 0.3
POWER_TRACK = 0.5
VIA_DIAMETER = 0.6
VIA_DRILL = 0.3
SILK_TEXT = 1.0
SILK_LINE = 0.12
SILK_THICKNESS = 0.15

# ESP32-C3 Super Mini (U1): two 1x08 rows of THT pads, USB end at the top
C3_LEFT_X = 4.00
C3_RIGHT_X = 19.24
C3_FIRST_Y = 2.40
C3_PITCH = 2.54
C3_PAD = 1.7
C3_DRILL = 1.0
C3_OUTLINE = (2.62, 0.0, 20.62, 22.52)  # x0, y0, x1, y1
C3_ANT_KEEPOUT = (2.6, 18.5, 20.6, BOARD_H)  # x0, y0, x1, y1, ~4 mm above the C3 bottom
C3_LEFT_PINS = ["5V", "GND", "3V3", "GPIO4", "GPIO3", "GPIO2", "GPIO1", "GPIO0"]
C3_RIGHT_PINS = ["GPIO5", "GPIO6", "GPIO7", "GPIO8", "GPIO9", "GPIO10", "GPIO20", "GPIO21"]
C3_NETS = {
    "3V3": "3V3",
    "GND": "GND",
    "GPIO4": "SCK",
    "GPIO5": "MISO",
    "GPIO6": "MOSI",
    "GPIO7": "CSN",
    "GPIO10": "GDO0",
}
# Silkscreen pin labels: (text, x, y) for the pins that are used
C3_PIN_LABELS = [
    ("3V3", 6.6, C3_FIRST_Y + 2 * C3_PITCH),
    ("G", 6.6, C3_FIRST_Y + 1 * C3_PITCH),
    ("4", 6.6, C3_FIRST_Y + 3 * C3_PITCH),
    ("5", 16.6, C3_FIRST_Y + 0 * C3_PITCH),
    ("6", 16.6, C3_FIRST_Y + 1 * C3_PITCH),
    ("7", 16.6, C3_FIRST_Y + 2 * C3_PITCH),
    ("10", 16.6, C3_FIRST_Y + 5 * C3_PITCH),
]

# CC1101 module (U2): frame origin is the module's top corner on the header edge
MOD_X = 23.5
MOD_BOTTOM = 20.5  # corner under pin 1
MOD_W = 18.9  # across the module, header edge to antenna edge
MOD_H = 17.4  # along the header edge
MOD_Y = MOD_BOTTOM - MOD_H  # top corner
HEADER_PITCH = 2.00
PIN1_FROM_CORNER = 1.6
PAD_LONG = 2.0  # perpendicular to the module edge (straddles it)
PAD_SHORT = 1.0
ANT_PAD_OFFSETS = (12.22, 9.68, 7.15)  # pads 9, 10, 11: measured from the pin 1 corner
ANT_PADS = (9, 10, 11)
ANT_PAD_NO_NET = 10
ANT_KEEPOUT_MARGIN = 3.0
ANT_SLOT_WIDTH = 0.9  # corridor for the GND stubs of pads 9 and 11
ANT_GND_PAD_WIDTH = 1.2  # along the antenna edge, wider for measurement tolerance
ANT_STUB_END_X = 38.8  # stubs end inside the GND pour, outside the keepout box
# C3 GND (U1 pin 2) runs over the top edge into the pour; stitching vias outside keepouts
C3_GND_TRACK_WIDTH = 0.6
C3_GND_RUN = ((C3_LEFT_X, C3_FIRST_Y + C3_PITCH), (2.3, C3_FIRST_Y + C3_PITCH),
              (2.3, 1.0), (21.0, 1.0))
GND_STITCH_VIAS = ((21.6, 25.0), (39.5, 21.5), (30.0, 17.0))
HEADER_NETS = {1: "3V3", 2: "GND", 3: "MOSI", 4: "SCK", 5: "MISO", 7: "GDO0", 8: "CSN"}
ANT_NETS = {9: "GND", 11: "GND"}
MODULE_OUTLINE = (1.2, 0.0, MOD_W - 1.2, MOD_H)  # frame coordinates, inset from pads
PIN1_DOT = (2.6, MOD_H - PIN1_FROM_CORNER)
MODULE_TEXT = ("CC1101", 9.45, 8.5)
ANT_TEXT = ("ANT →", 15.2, 4.0)

# Passives (through-hole), pad 1 target positions; pad 1 is + on C1
C1_PADS = ((31.0, 22.5), (31.0, 24.5))  # C1 is rotated -90 so GND sits below its 3V3 pad
C2_PADS = ((36.0, 22.5), (38.5, 22.5))

MOUNT_HOLES = ((25.3, 27.0), (40.7, 27.0))
BOARD_TEXT = [(f"{PROJECT} v1", 12.0, 25.6), (BOARD_DATE, 12.0, 27.4)]
# PCBWay prints its order number where this marker is (B.SilkS, mirrored).
PCBWAY_MARK = ("WayWayWay", 11.6, 26.5, 0.8)

POWER_NETS = ("3V3", "GND")
UNROUTED_NETS = ("GND",)  # poured instead of routed
NET_NAMES = ["3V3", "GND", "MOSI", "SCK", "MISO", "GDO0", "CSN"]


def lset(*layers):
    layer_set = pn.LSET()
    for layer in layers:
        layer_set.addLayer(layer)
    return layer_set


def header_pin_y(k):
    return MOD_BOTTOM - PIN1_FROM_CORNER - (k - 1) * HEADER_PITCH


def ant_pad_y(number):
    return MOD_BOTTOM - ANT_PAD_OFFSETS[ANT_PADS.index(number)]


def point(x, y):
    return V(mm(x), mm(y))


def add_segment(parent, layer, x1, y1, x2, y2, width):
    seg = pn.PCB_SHAPE(parent)
    seg.SetShape(pn.SHAPE_T_SEGMENT)
    seg.SetLayer(layer)
    seg.SetStart(point(x1, y1))
    seg.SetEnd(point(x2, y2))
    seg.SetWidth(mm(width))
    parent.Add(seg)


def add_rect(parent, layer, x0, y0, x1, y1, width):
    add_segment(parent, layer, x0, y0, x1, y0, width)
    add_segment(parent, layer, x1, y0, x1, y1, width)
    add_segment(parent, layer, x1, y1, x0, y1, width)
    add_segment(parent, layer, x0, y1, x0, y0, width)


def add_text(parent, text, x, y, layer=pn.F_SilkS, size=SILK_TEXT):
    item = pn.PCB_TEXT(parent)
    item.SetText(text)
    item.SetLayer(layer)
    item.SetMirrored(layer == pn.B_SilkS)
    item.SetPosition(point(x, y))
    item.SetTextSize(V(mm(size), mm(size)))
    item.SetTextThickness(mm(SILK_THICKNESS))
    parent.Add(item)


def add_dot(parent, x, y, radius):
    dot = pn.PCB_SHAPE(parent)
    dot.SetShape(pn.SHAPE_T_CIRCLE)
    dot.SetLayer(pn.F_SilkS)
    dot.SetCenter(point(x, y))
    dot.SetEnd(point(x + radius, y))
    dot.SetWidth(0)
    dot.SetFilled(True)
    parent.Add(dot)


def add_pad(fp, number, x, y, size, shape, attrib, layers, drill=None):
    pad = pn.PAD(fp)
    pad.SetNumber(str(number))
    pad.SetAttribute(attrib)
    pad.SetShape(shape)
    pad.SetPosition(point(x, y))
    pad.SetSize(V(mm(size[0]), mm(size[1])))
    if drill:
        pad.SetDrillSize(V(mm(drill), mm(drill)))
    pad.SetLayerSet(layers)
    fp.Add(pad)
    return pad


def rect_outline(zone, x0, y0, x1, y1):
    outline = zone.Outline()
    index = outline.NewOutline()
    for x, y in ((x0, y0), (x1, y0), (x1, y1), (x0, y1)):
        outline.Append(mm(x), mm(y), index)


def polygon_outline(zone, points):
    """One outline only: KiCad drops extra outlines of a zone on save."""
    outline = zone.Outline()
    index = outline.NewOutline()
    for x, y in points:
        outline.Append(mm(x), mm(y), index)


def keepout_polygon(x0, y0, x1, y1, corridors, x_end):
    """Single outline of the box minus corridors that run from x0 to x_end.

    corridors: (y_lo, y_hi) pairs. A corridor within 0.1 mm of the box top or
    bottom edge is opened to that edge, so no sliver of keepout is left.
    """
    spans = [(y0 if lo - y0 < 0.1 else lo, y1 if y1 - hi < 0.1 else hi)
             for lo, hi in sorted(corridors)]
    top_open = spans[0][0] == y0
    bottom_open = spans[-1][1] == y1
    points = [(x_end, y0) if top_open else (x0, y0), (x1, y0), (x1, y1)]
    if bottom_open:
        points.append((x_end, y1))
    else:
        points.append((x0, y1))
    for index in reversed(range(len(spans))):  # walk up from the bottom
        lo, hi = spans[index]
        if hi == y1:
            points += [(x_end, lo), (x0, lo)]
        elif index == 0 and top_open:
            points += [(x0, hi), (x_end, hi)]  # closes back on the top edge
        else:
            points += [(x0, hi), (x_end, hi), (x_end, lo), (x0, lo)]
    return points


def net_of(board, cache, name):
    if name not in cache:
        net = pn.NETINFO_ITEM(board, name)
        board.Add(net)
        cache[name] = net
    return cache[name]


def set_pad_net(fp, number, net):
    for pad in fp.Pads():
        if pad.GetNumber() == str(number):
            pad.SetNet(net)
            return
    raise KeyError(f"{fp.GetReference()} has no pad {number}")


def place_by_pad1(fp, target):
    pad1 = next(p for p in fp.Pads() if p.GetNumber() == "1")
    pos = pad1.GetPosition()
    delta = point(target[0], target[1]) - pos
    fp.SetPosition(V(fp.GetPosition().x + delta.x, fp.GetPosition().y + delta.y))


def load_lib(lib, name, ref, value, board):
    fp = pn.FootprintLoad(os.path.join(FOOTPRINT_LIBS, lib + ".pretty"), name)
    fp.SetReference(ref)
    fp.SetValue(value)
    board.Add(fp)
    return fp


def build_c3(board, nets):
    fp = pn.FOOTPRINT(board)
    fp.SetReference("U1")
    fp.SetValue("ESP32-C3 Super Mini")
    fp.SetFPIDAsString(f"{PROJECT}:ESP32-C3-SuperMini")
    thru = lset(pn.F_Cu, pn.B_Cu, pn.F_Mask, pn.B_Mask)
    pins = [(C3_LEFT_X, n, name) for n, name in enumerate(C3_LEFT_PINS)]
    pins += [(C3_RIGHT_X, n, name) for n, name in enumerate(C3_RIGHT_PINS)]
    for col, (x, row, name) in enumerate(pins):
        number = row + 1 + (8 if col >= 8 else 0)
        y = C3_FIRST_Y + row * C3_PITCH
        pad = add_pad(fp, number, x, y, (C3_PAD, C3_PAD), pn.PAD_SHAPE_CIRCLE,
                      pn.PAD_ATTRIB_PTH, thru, drill=C3_DRILL)
        if name in C3_NETS:
            pad.SetNet(nets[C3_NETS[name]])
        if name == "GND":
            # The top-edge 3V3 route cuts this pad's B.Cu pour off, so no thermal spokes there
            pad.SetLocalZoneConnection(pn.ZONE_CONNECTION_FULL)
    x0, y0, x1, y1 = C3_OUTLINE
    add_rect(fp, pn.F_SilkS, x0, y0, x1, y1, SILK_LINE)
    add_text(fp, "C3 Super Mini", 11.62, 13.5)
    fp.Reference().SetPosition(point(11.62, 17.5))
    add_text(fp, "USB ↑", 11.62, 1.6)
    for text, x, y in C3_PIN_LABELS:
        add_text(fp, text, x, y)
    board.Add(fp)
    return fp


def build_cc1101(board, nets):
    # Built in the module frame (header edge at x=0, antenna edge at x=MOD_W)
    # and moved to (MOD_X, MOD_Y) at the end.
    fp = pn.FOOTPRINT(board)
    fp.SetReference("U2")
    fp.SetValue("CC1101 868MHz")
    fp.SetFPIDAsString(f"{PROJECT}:CC1101_M115")
    smd = lset(pn.F_Cu, pn.F_Paste, pn.F_Mask)
    for k in range(1, 9):
        y = header_pin_y(k) - MOD_Y
        pad = add_pad(fp, k, 0.0, y, (PAD_LONG, PAD_SHORT), pn.PAD_SHAPE_RECT,
                      pn.PAD_ATTRIB_SMD, smd)
        if k in HEADER_NETS:
            pad.SetNet(nets[HEADER_NETS[k]])
    for number in ANT_PADS:
        width = ANT_GND_PAD_WIDTH if number in ANT_NETS else PAD_SHORT
        pad = add_pad(fp, number, MOD_W, ant_pad_y(number) - MOD_Y, (PAD_LONG, width),
                      pn.PAD_SHAPE_RECT,
                      pn.PAD_ATTRIB_SMD, smd)
        if number in ANT_NETS:
            pad.SetNet(nets[ANT_NETS[number]])
    x0, y0, x1, y1 = MODULE_OUTLINE
    add_rect(fp, pn.F_SilkS, x0, y0, x1, y1, SILK_LINE)
    add_dot(fp, PIN1_DOT[0], PIN1_DOT[1], 0.3)
    text, x, y = MODULE_TEXT
    add_text(fp, text, x, y)
    text, x, y = ANT_TEXT
    add_text(fp, text, x, y)
    fp.SetPosition(point(MOD_X, MOD_Y))
    board.Add(fp)
    return fp


def set_netclass_rules(netclass, track_width):
    netclass.SetTrackWidth(mm(track_width))
    netclass.SetClearance(mm(CLEARANCE))
    netclass.SetViaDiameter(mm(VIA_DIAMETER))
    netclass.SetViaDrill(mm(VIA_DRILL))


def build_board():
    board = pn.BOARD()
    # Net classes: signal defaults, and a wider class for 3V3 and GND
    net_settings = board.GetDesignSettings().m_NetSettings
    default = net_settings.GetDefaultNetclass()
    set_netclass_rules(default, SIGNAL_TRACK)
    net_settings.SetNetclass("Power", pn.NETCLASS("Power"))
    power = net_settings.GetNetClassByName("Power")
    set_netclass_rules(power, POWER_TRACK)

    nets = {}
    for name in NET_NAMES:
        net_of(board, nets, name)
    for name in POWER_NETS:
        nets[name].SetNetClass(power)

    # Board outline
    add_rect(board, pn.Edge_Cuts, 0.0, 0.0, BOARD_W, BOARD_H, 0.05)

    build_c3(board, nets)
    build_cc1101(board, nets)

    c1 = load_lib("Capacitor_THT", "CP_Radial_D5.0mm_P2.00mm", "C1", "10uF", board)
    c1.SetOrientationDegrees(-90)
    place_by_pad1(c1, C1_PADS[0])
    c1.Reference().SetPosition(point(34.0, 27.5))
    set_pad_net(c1, 1, nets["3V3"])
    set_pad_net(c1, 2, nets["GND"])

    c2 = load_lib("Capacitor_THT", "C_Disc_D3.0mm_W1.6mm_P2.50mm", "C2", "100nF", board)
    place_by_pad1(c2, C2_PADS[0])
    set_pad_net(c2, 1, nets["3V3"])
    set_pad_net(c2, 2, nets["GND"])
    c2.Reference().SetPosition(point(37.25, 25.2))

    for n, (x, y) in enumerate(MOUNT_HOLES, start=1):
        hole = load_lib("MountingHole", "MountingHole_3.2mm_M3", f"H{n}", "M3", board)
        hole.SetPosition(point(x, y))
        hole.Reference().SetVisible(False)

    for text, x, y in BOARD_TEXT:
        add_text(board, text, x, y)
    mark, mx, my, msize = PCBWAY_MARK
    add_text(board, mark, mx, my, layer=pn.B_SilkS, size=msize)

    # Keepouts. Rule areas go in before the zone fill so the pours respect them.
    x0, y0, x1, y1 = C3_ANT_KEEPOUT
    keepout = pn.ZONE(board)
    keepout.SetIsRuleArea(True)
    keepout.SetDoNotAllowTracks(True)
    keepout.SetDoNotAllowVias(True)
    keepout.SetDoNotAllowZoneFills(True)
    keepout.SetDoNotAllowFootprints(False)
    keepout.SetDoNotAllowPads(False)
    keepout.SetLayer(pn.F_Cu)
    keepout.SetLayerSet(lset(pn.F_Cu, pn.B_Cu))
    keepout.SetZoneName("C3 antenna keepout")
    rect_outline(keepout, x0, y0, x1, y1)
    board.Add(keepout)

    ant_x = MOD_X + MOD_W
    ant_y = ant_pad_y(ANT_PAD_NO_NET)
    corridors = []
    for number in ANT_NETS:
        y = ant_pad_y(number)
        corridors.append((y - ANT_SLOT_WIDTH / 2, y + ANT_SLOT_WIDTH / 2))
    antenna = pn.ZONE(board)
    antenna.SetIsRuleArea(True)
    antenna.SetDoNotAllowTracks(True)
    antenna.SetDoNotAllowVias(True)
    antenna.SetDoNotAllowZoneFills(True)
    antenna.SetDoNotAllowFootprints(False)
    antenna.SetDoNotAllowPads(False)
    antenna.SetLayer(pn.F_Cu)
    antenna.SetLayerSet(lset(pn.F_Cu, pn.B_Cu))
    antenna.SetZoneName("ANT pad keepout")
    polygon_outline(antenna, keepout_polygon(
        ant_x - ANT_KEEPOUT_MARGIN, ant_y - ANT_KEEPOUT_MARGIN, BOARD_W,
        ant_y + ANT_KEEPOUT_MARGIN, corridors, ant_x))
    board.Add(antenna)
    return board


def prepare_dsn(dsn):
    """Keep GND out of Freerouting: the pour connects it, plus the pad 9/11 stubs."""
    text = dsn.read_text()
    text = re.sub(r"    \(net GND\n.*?\n    \)\n", "", text, count=1, flags=re.S)
    dsn.write_text(text)
    split_power_class(dsn)


def split_power_class(dsn):
    """Move POWER_NETS into their own DSN net class with POWER_TRACK width.

    The KiCad 10 DSN exporter puts every net into kicad_default, so the
    Power net class never reaches Freerouting. Units are um (resolution 10).
    """
    text = dsn.read_text()
    start = text.index("    (class kicad_default")
    end = text.index("\n    )\n", start) + len("\n    )\n")
    block = text[start:end]
    nets = [n for n in block[len("    (class kicad_default"):block.index("(circuit")].split()
            if n not in UNROUTED_NETS]
    circuit = block[block.index("      (circuit"):block.index("      (rule")]

    def net_class(name, members, width):
        return (f"    (class {name} {' '.join(members)}\n{circuit}"
                f"      (rule\n        (width {width})\n        (clearance 200)\n      )\n    )\n")

    signals = [n for n in nets if n not in POWER_NETS]
    power = [n for n in nets if n in POWER_NETS]
    text = text[:start] + net_class("kicad_default", signals, 300) \
        + net_class("Power", power, round(POWER_TRACK * 1000)) + text[end:]
    dsn.write_text(text)


def export_dsn_and_route(board):
    BUILD_DIR.mkdir(exist_ok=True)
    dsn = BUILD_DIR / f"{PROJECT}.dsn"
    ses = BUILD_DIR / f"{PROJECT}.ses"
    if not pn.ExportSpecctraDSN(board, str(dsn)):
        raise RuntimeError("DSN export failed")
    prepare_dsn(dsn)
    java = os.environ.get("JAVA_BIN") or os.path.join(
        subprocess.check_output(["brew", "--prefix", "openjdk"], text=True).strip(), "bin", "java")
    subprocess.run([java, "-jar", FREEROUTING_JAR, "-de", str(dsn), "-do", str(ses),
                    "-mp", str(FREEROUTING_PASSES), "-l", "en"], cwd=BUILD_DIR, check=True)
    if not pn.ImportSpecctraSES(board, str(ses)):
        raise RuntimeError("SES import failed")
    add_gnd_stubs(board)
    add_c3_ground(board)


def add_c3_ground(board):
    gnd = board.FindNet("GND")
    for (x1, y1), (x2, y2) in zip(C3_GND_RUN, C3_GND_RUN[1:]):
        track = pn.PCB_TRACK(board)
        track.SetStart(point(x1, y1))
        track.SetEnd(point(x2, y2))
        track.SetWidth(mm(C3_GND_TRACK_WIDTH))
        track.SetLayer(pn.F_Cu)
        track.SetNet(gnd)
        board.Add(track)
    for x, y in GND_STITCH_VIAS:
        via = pn.PCB_VIA(board)
        via.SetPosition(point(x, y))
        via.SetWidth(mm(VIA_DIAMETER))
        via.SetDrill(mm(VIA_DRILL))
        via.SetNet(gnd)
        board.Add(via)


def add_gnd_stubs(board):
    """Short F.Cu stubs that tie GND pads to the pour, since GND is not routed.

    Pads 9 and 11 leave the antenna corridor to the left, away from pad 10.
    Pad 2 of U2 runs into the module, where the pour is open on F.Cu.
    """
    gnd = board.FindNet("GND")
    stubs = []
    for number in ANT_NETS:
        y = ant_pad_y(number)
        stubs.append(((MOD_X + MOD_W - 0.5, y), (ANT_STUB_END_X, y)))
    y = header_pin_y(2)
    stubs.append(((MOD_X, y), (MOD_X + 2.5, y)))
    for start, end in stubs:
        stub = pn.PCB_TRACK(board)
        stub.SetStart(point(*start))
        stub.SetEnd(point(*end))
        stub.SetWidth(mm(POWER_TRACK))
        stub.SetLayer(pn.F_Cu)
        stub.SetNet(gnd)
        board.Add(stub)


def add_gnd_pours(board):
    gnd = board.FindNet("GND")
    for layer in (pn.F_Cu, pn.B_Cu):
        zone = pn.ZONE(board)
        zone.SetNet(gnd)
        zone.SetLayer(layer)
        zone.SetAssignedPriority(0)
        zone.SetPadConnection(pn.ZONE_CONNECTION_THERMAL)
        zone.SetMinThickness(mm(0.25))
        zone.SetZoneName("GND")
        rect_outline(zone, 0.0, 0.0, BOARD_W, BOARD_H)
        board.Add(zone)
    pn.ZONE_FILLER(board).Fill(board.Zones())


def write_project():
    settings = {
        "meta": {"filename": PRO_PATH.name, "version": 1},
        "board": {
            "design_settings": {
                "rules": {
                    "min_clearance": CLEARANCE,
                    "min_copper_edge_clearance": COPPER_EDGE_CLEARANCE,
                    "min_track_width": 0.2,
                },
            },
        },
        "net_settings": {
            "classes": [
                {"name": "Default", "clearance": CLEARANCE, "track_width": SIGNAL_TRACK,
                 "via_diameter": VIA_DIAMETER, "via_drill": VIA_DRILL},
                {"name": "Power", "clearance": CLEARANCE, "track_width": POWER_TRACK,
                 "via_diameter": VIA_DIAMETER, "via_drill": VIA_DRILL},
            ],
            "netclass_assignments": {name: "Power" for name in POWER_NETS},
        },
    }
    PRO_PATH.write_text(json.dumps(settings, indent=2) + "\n")


def run_drc():
    report = BUILD_DIR / "drc.json"
    subprocess.run([KICAD_CLI, "pcb", "drc", "--format", "json", "--severity-all",
                    "--output", str(report), str(PCB_PATH)], check=True)
    data = json.loads(report.read_text())
    violations = data.get("violations", [])
    unconnected = data.get("unconnected_items", [])
    errors = [v for v in violations if v.get("severity") == "error"]
    warnings = [v for v in violations if v.get("severity") != "error"]
    print(f"DRC: {len(errors)} errors, {len(unconnected)} unconnected items, "
          f"{len(warnings)} warnings")
    for v in warnings:
        print(f"  warning: {v.get('description')} @ {v.get('items', [{}])[0].get('description', '')}")
    for v in errors + unconnected:
        print(f"  error: {v.get('description')}")
    return report


def export_fab():
    with tempfile.TemporaryDirectory(dir=BUILD_DIR) as tmp:
        layers = "F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,F.Paste,B.Paste,Edge.Cuts"
        subprocess.run([KICAD_CLI, "pcb", "export", "gerbers", "--output", tmp,
                        "--layers", layers, "--no-protel-ext", str(PCB_PATH)], check=True)
        subprocess.run([KICAD_CLI, "pcb", "export", "drill", "--output", tmp,
                        "--format", "excellon", "--excellon-units", "mm",
                        "--excellon-separate-th",
                        str(PCB_PATH)], check=True)
        FAB_ZIP.parent.mkdir(exist_ok=True)
        with zipfile.ZipFile(FAB_ZIP, "w", zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(pathlib.Path(tmp).iterdir()):
                zf.write(path, path.name)
    print(f"Wrote {FAB_ZIP}")


def render():
    for side, out in (("top", RENDER_TOP), ("bottom", RENDER_BOTTOM)):
        subprocess.run([KICAD_CLI, "pcb", "render", "--side", side, "--width", "1600",
                        "--height", "1200", "--quality", "high", "--background", "opaque",
                        "--output", str(out), str(PCB_PATH)], check=True)


def main():
    board = build_board()
    export_dsn_and_route(board)
    add_gnd_pours(board)
    board.Save(str(PCB_PATH))
    write_project()
    run_drc()
    export_fab()
    render()
    PRL_PATH.unlink(missing_ok=True)
    shutil.rmtree(BUILD_DIR, ignore_errors=True)


if __name__ == "__main__":
    main()
