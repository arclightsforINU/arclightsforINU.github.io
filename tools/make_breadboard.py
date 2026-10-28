# Builds the domino-pot breadboard SVG by re-placing Fritzing part graphics from the earlier export and the core pot part.
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)

base, pot_svg, out = map(Path, sys.argv[1:4])
root = ET.parse(base).getroot()

ROW_A, ROW_E = 2088.88, 1688.88
col = lambda c: 3001.87 + (c - 6) * 100
D13, D10, D7 = 1896.67, 2196.67, 2556.67
P5V, PGND, PA0 = 2256.67, 2356.67, 2756.67

keep = {"18462100", "20360", "30010", "30020", "30040", "31010", "31020", "31030", "20380"}
shift = {"30040": -600}
parts, labels, legs = [], [], []
for g in list(root):
    pid = g.get("partID")
    root.remove(g)
    if pid is None:
        legs.append(g)
        continue
    items, legs = legs + [g], []
    if pid not in keep:
        continue
    if pid in shift:
        wrap = ET.Element("g", {"transform": f"translate({shift[pid]},0)"})
        wrap.extend(items)
        items = [wrap]
    (labels if g.get("id") == "partLabel" else parts).extend(items)

pot_root = ET.parse(pot_svg).getroot()
pot_body = pot_root.find(f"{{{SVG}}}g[@id='breadboard']")
leg1 = (74.618149 + 41.317371 / 2, 1160.5)
pot = ET.Element("g", {"partID": "40010"})
place = ET.SubElement(pot, "g", {"transform": f"translate({col(24) - leg1[0]:.2f},{ROW_E - leg1[1]:.2f})"})
place.append(pot_body)
parts.append(pot)


def wire(pid, d, outer, inner):
    g = ET.Element("g", {"partID": pid})
    for color, width in ((outer, "44.4444"), (inner, "22.2222")):
        ET.SubElement(g, "path", {"stroke-linecap": "round", "fill": "none", "stroke-width": width, "stroke": color, "d": d})
    return g


def to_row_a(x0, y0, c, sag):
    x1 = col(c)
    return f"M{x0},{y0}C{x0 + (x1 - x0) * 0.45},{y0 + sag} {x1 - 200},{ROW_A + 500} {x1},{ROW_A}"


def under_board(y0, c, lane, side):
    x1 = col(c)
    return (f"M100,{y0}C{side},{y0} {side},{lane} 900,{lane}"
            f"L{x1 - 700},{lane}C{x1 - 100},{lane} {x1},{lane - 400} {x1},{ROW_A}")


wires = [
    wire("32010", to_row_a(2000, D13, 6, 900), "#1b5bb3", "#418dd9"),
    wire("32020", to_row_a(2000, D10, 12, 700), "#cc1414", "#ff2a2a"),
    wire("32030", to_row_a(2000, D7, 18, 500), "#00a527", "#25cc35"),
    wire("32040", under_board(PGND, 24, 3640, -220), "#000000", "#404040"),
    wire("32050", under_board(PA0, 26, 3740, -110), "#b39500", "#ffd400"),
    wire("32060", under_board(P5V, 28, 3840, -330), "#c46a00", "#f08a24"),
]

pot_label = ET.Element("g", {"partID": "40010", "id": "partLabel"})
text_g = ET.SubElement(ET.SubElement(pot_label, "g", {"transform": f"translate({col(28) + 120:.2f},780)"}),
                       "g", {"font-size": "69.4444", "fill": "#000000", "font-family": "'DroidSans'"})
for i, line in enumerate(("VR1", "10kΩ")):
    ET.SubElement(text_g, "text", {"x": "0", "y": f"{52.0833 + 69.4444 * i:.4f}"}).text = line

for g in parts + wires + labels + [pot_label]:
    root.append(g)
root.set("viewBox", "-450 0 6050 3950")
root.set("width", "6.05in")
root.set("height", "3.95in")
ET.ElementTree(root).write(out, encoding="UTF-8", xml_declaration=True)
