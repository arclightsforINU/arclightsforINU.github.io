# Renders the class PotButtonLCD.fz breadboard view and the assignment circuits built on it (SVG + PNG):
#   p5-led-slider  LED2 and its resistor added on D9
#   finger-led     LED1's wire moved from D13 to D9 (D13 has no PWM) and the LED drawn blue as on the real board
import re
import struct
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

LED2_COLOR = "Blue (470nm)"

SVG = "http://www.w3.org/2000/svg"
XLINK = "http://www.w3.org/1999/xlink"
ET.register_namespace("", SVG)
ET.register_namespace("xlink", XLINK)
Q = lambda t: f"{{{SVG}}}{t}"

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB.parent
FZZ = ROOT / "_build/p5-slider/fzz"
FZ = FZZ / "PotButtonLCD.fz"
PARTS = ROOT / "_build/fritzing-parts"
APP = ROOT / "_build/fritzing-app"
SCRATCH = ROOT / "_build/p5-slider"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PNG_WIDTH = 2000

DPI = 90
BREADBOARD = "0152b316-ca6e-11ee-a6fa-8be78db221f8BreadboardModuleID"
UNO = "arduino_Uno_Rev3(fix)"
LED = "3mmColorLEDModuleID"
RESISTOR = "SparkFun-Passives-RESISTOR-0402-ResistorModuleID"
WIRE = "WireModuleID"
KEEP_ATTRS = {"fill-rule", "clip-rule", "shape-rendering", "text-rendering", "image-rendering", "style"}
UNIT_IN = {"in": 1.0, "mm": 1 / 25.4, "cm": 1 / 2.54, "pt": 1 / 72, "pc": 1 / 6}

LED2_SHIFT_COLS = 9
LED2_GND_RAIL_PIN = "pin15X"
D9_CONNECTOR = "connector52"
D13_CONNECTOR = "connector56"
D9_CP = ((-24.0, -105.0), (-140.0, -170.0))


def el(tag, attrs=None, parent=None, text=None):
    e = ET.Element(Q(tag), {k: str(v) for k, v in (attrs or {}).items()})
    if parent is not None:
        parent.append(e)
    if text is not None:
        e.text = text
    return e


def local(tag):
    return tag.split("}")[-1]


def read_instances():
    out = []
    for inst in ET.parse(FZ).getroot().find("instances"):
        bv = inst.find("views/breadboardView")
        if bv is None:
            continue
        g = bv.find("geometry")
        d = {
            "module": inst.get("moduleIdRef"),
            "path": inst.get("path"),
            "index": inst.get("modelIndex"),
            "title": inst.findtext("title"),
            "props": {p.get("name"): p.get("value") for p in inst.findall("property")},
            "x": float(g.get("x")),
            "y": float(g.get("y")),
            "z": float(g.get("z")),
        }
        if d["module"] == WIRE:
            if int(g.get("wireFlags", "0")) & 64 == 0:
                continue
            extras = bv.find("wireExtras")
            bez = extras.find("bezier")
            d.update(
                p1=(float(g.get("x1")), float(g.get("y1"))),
                p2=(float(g.get("x2")), float(g.get("y2"))),
                color=extras.get("color"),
                mils=float(extras.get("mils")),
                opacity=float(extras.get("opacity", "1")),
                bezier=None if bez is None or bez.find("cp0") is None else (
                    (float(bez.find("cp0").get("x")), float(bez.find("cp0").get("y"))),
                    (float(bez.find("cp1").get("x")), float(bez.find("cp1").get("y")))),
            )
        out.append(d)
    return out


def part_files(inst):
    fzp = FZZ / f"part.{inst['path']}" if (FZZ / f"part.{inst['path']}").exists() else PARTS / "fzp" / inst["path"]
    layers = ET.parse(fzp).getroot().find("views/breadboardView/layers")
    image = layers.get("image")
    folder, name = image.split("/")
    svg = FZZ / f"svg.{folder}.{name}" if (FZZ / f"svg.{folder}.{name}").exists() else PARTS / "svg" / name
    return fzp, svg


def load_part_svg(svg_path):
    text = svg_path.read_text(encoding="utf-8")
    root = ET.fromstring(text)
    dpi = 72 if "Adobe Illustrator" in text else DPI
    vb = [float(v) for v in root.get("viewBox").replace(",", " ").split()]
    size = []
    for key in ("width", "height"):
        m = re.fullmatch(r"\s*([0-9.eE+-]+)\s*([a-z%]*)\s*", root.get(key))
        val, unit = float(m[1]), m[2]
        size.append(val * UNIT_IN[unit] * DPI if unit in UNIT_IN else val * DPI / dpi)
    return root, vb, size


def led_colors():
    prop = next(p for p in ET.parse(APP / "properties.xml").getroot() if p.get("name") == "color")
    return {m.get("value"): m.get("adjunct") for m in prop.findall("menuItem")}


def wire_shadows():
    view = next(v for v in ET.parse(APP / "ratsnestcolors.xml").getroot() if v.get("name") == "breadboardView")
    out = {}
    for c in view:
        for node in [c, *c.findall("obsolete")]:
            out.setdefault(node.get("wire").lower(), node.get("shadow"))
    return out


def prefix_ids(root, prefix):
    ids = {e.get("id") for e in root.iter() if e.get("id")}
    ref = re.compile(r"url\(\s*['\"]?#([^)'\"\s]+)['\"]?\s*\)")
    for e in root.iter():
        for k, v in list(e.attrib.items()):
            if k == "id":
                e.set(k, prefix + v)
                continue
            nv = ref.sub(lambda m: f"url(#{prefix}{m[1]})" if m[1] in ids else m[0], v)
            if k.endswith("href") and v.startswith("#") and v[1:] in ids:
                nv = "#" + prefix + v[1:]
            if nv != v:
                e.set(k, nv)


def part_group(inst, color_hex=None):
    fzp, svg_path = part_files(inst)
    root, vb, size = load_part_svg(svg_path)
    if color_hex:
        for e in root.iter():
            if (e.get("id") or "").startswith("color_"):
                e.set("fill", color_hex)
    for e in list(root.iter()):
        for child in list(e):
            if local(child.tag) in ("metadata", "namedview", "desc", "title"):
                e.remove(child)
    prefix_ids(root, f"p{inst['index']}-")
    nested = el("svg", {"x": f"{inst['x']:.4f}", "y": f"{inst['y']:.4f}", "width": f"{size[0]:.4f}", "height": f"{size[1]:.4f}",
                        "viewBox": " ".join(f"{v:g}" for v in vb), "preserveAspectRatio": "none", "overflow": "visible",
                        "id": f"part-{inst['title']}"})
    for k, v in root.attrib.items():
        if k in KEEP_ATTRS:
            nested.set(k, v)
    for child in root:
        nested.append(child)
    return nested, (inst["x"], inst["y"], size[0], size[1])


def breadboard_holes(bb):
    _, svg_path = part_files(bb)
    root = ET.parse(svg_path).getroot()
    holes = {}

    def shift(node):
        m = re.search(r"translate\(([-0-9.e]+)[ ,]+([-0-9.e]+)\)", node.get("transform", ""))
        return (float(m[1]), float(m[2])) if m else (0.0, 0.0)

    for outer in root.iter(Q("g")):
        ox, oy = shift(outer)
        for g in outer:
            if (g.get("id") or "").startswith("pin") and local(g.tag) == "g":
                gx, gy = shift(g)
                c = g.find(Q("circle"))
                holes[g.get("id")] = (bb["x"] + ox + gx + float(c.get("cx")), bb["y"] + oy + gy + float(c.get("cy")))
    return holes


def uno_pin(uno, connector):
    _, svg_path = part_files(uno)
    root, vb, size = load_part_svg(svg_path)
    node = next(e for e in root.iter() if e.get("id") == f"{connector}pin")
    return (uno["x"] + float(node.get("cx")) * size[0] / vb[2], uno["y"] + float(node.get("cy")) * size[1] / vb[3])


def bezier_points(w, n=40):
    p0, p3 = w["p1"], w["p2"]
    pts = []
    for i in range(n + 1):
        t = i / n
        if w["bezier"]:
            c0, c1 = w["bezier"]
            pts.append(tuple(
                w[a] + (1 - t) ** 3 * p0[k] + 3 * (1 - t) ** 2 * t * c0[k] + 3 * (1 - t) * t ** 2 * c1[k] + t ** 3 * p3[k]
                for k, a in enumerate("xy")))
        else:
            pts.append(tuple(w[a] + p0[k] + t * (p3[k] - p0[k]) for k, a in enumerate("xy")))
    return pts


def wire_group(w, shadows):
    p1x, p1y = w["x"] + w["p1"][0], w["y"] + w["p1"][1]
    p2x, p2y = w["x"] + w["p2"][0], w["y"] + w["p2"][1]
    if w["bezier"]:
        (c0x, c0y), (c1x, c1y) = w["bezier"]
        d = (f"M{p1x:.3f},{p1y:.3f} C{w['x'] + c0x:.3f},{w['y'] + c0y:.3f} "
             f"{w['x'] + c1x:.3f},{w['y'] + c1y:.3f} {p2x:.3f},{p2y:.3f}")
    else:
        d = f"M{p1x:.3f},{p1y:.3f} L{p2x:.3f},{p2y:.3f}"
    width = w["mils"] * DPI / 1000
    g = el("g", {"id": f"wire-{w['title']}", "fill": "none", "stroke-linecap": "round", "stroke-linejoin": "round",
                 "opacity": w["opacity"]})
    el("path", {"d": d, "stroke": shadows.get(w["color"].lower(), w["color"]), "stroke-width": f"{width + 2:g}"}, g)
    el("path", {"d": d, "stroke": w["color"], "stroke-width": f"{width:g}"}, g)
    return g


def add_led2(insts, holes, uno):
    led1 = next(i for i in insts if i["module"] == LED)
    r2 = next(i for i in insts if i["module"] == RESISTOR)
    dx = holes[f"pin{2 + LED2_SHIFT_COLS}J"][0] - holes["pin2J"][0]
    top_z = max(i["z"] for i in insts)
    led2 = dict(led1, index="led2", title="LED2", x=led1["x"] + dx, props=dict(led1["props"], color=LED2_COLOR))
    r3 = dict(r2, index="r3", title="R3", x=r2["x"] + dx)
    d9 = uno_pin(uno, D9_CONNECTOR)
    start = holes[f"pin{7 + LED2_SHIFT_COLS}J"]
    gnd_from = holes[f"pin{2 + LED2_SHIFT_COLS}F"]
    gnd_to = holes[LED2_GND_RAIL_PIN]
    wires = [
        dict(module=WIRE, index="wire-d9", title="Wire-D9", x=start[0], y=start[1], z=top_z + 0.00001,
             p1=(0.0, 0.0), p2=(d9[0] - start[0], d9[1] - start[1]), color="#25cc35", mils=22.2222, opacity=1.0,
             bezier=D9_CP),
        dict(module=WIRE, index="wire-gnd2", title="Wire-GND2", x=gnd_to[0], y=gnd_to[1], z=top_z + 0.00002,
             p1=(0.0, 0.0), p2=(gnd_from[0] - gnd_to[0], gnd_from[1] - gnd_to[1]), color="#404040", mils=22.2222,
             opacity=1.0, bezier=None),
    ]
    return [led2, r3, *wires]


def move_led1_to_d9(insts, holes, uno):
    # The class file's D13 wire ends at the Uno; move that end four pins along to D9 and carry the
    # curve's near control point with it, so the wire keeps its shape.
    led1 = next(i for i in insts if i["module"] == LED)
    led1["props"] = dict(led1["props"], color=LED2_COLOR)
    d13 = uno_pin(uno, D13_CONNECTOR)
    d9 = uno_pin(uno, D9_CONNECTOR)
    wire = next(w for w in insts if w["module"] == WIRE
                and abs(w["x"] + w["p2"][0] - d13[0]) < 0.5 and abs(w["y"] + w["p2"][1] - d13[1]) < 0.5)
    dx, dy = d9[0] - d13[0], d9[1] - d13[1]
    (c0, c1) = wire["bezier"]
    wire.update(p2=(wire["p2"][0] + dx, wire["p2"][1] + dy), bezier=(c0, (c1[0] + dx, c1[1] + dy)))
    return []


def label_group(text, pos):
    w = len(text) * 5.3 + 12
    x, y = pos
    g = el("g", {"id": "pin-label"})
    el("rect", {"x": f"{x - w / 2:.1f}", "y": y - 7.5, "width": f"{w:.1f}", "height": 15, "rx": 7.5, "fill": "#ffffff",
                "stroke": "#555555", "stroke-width": 0.8}, g)
    el("text", {"x": x, "y": y + 3.4, "text-anchor": "middle", "font-size": 9, "font-weight": "bold",
                "font-family": "Arial, Helvetica, sans-serif", "fill": "#222222"}, g, text)
    return g


def build(change, label):
    insts = read_instances()
    bb = next(i for i in insts if i["module"] == BREADBOARD)
    uno = next(i for i in insts if i["module"] == UNO)
    holes = breadboard_holes(bb)
    if change:
        insts += change(insts, holes, uno)
    insts.sort(key=lambda i: i["z"])
    shadows = wire_shadows()
    colors = led_colors()
    body = el("g", {"id": "fritzing-breadboard"})
    xs, ys = [], []
    for inst in insts:
        if inst["module"] == WIRE:
            body.append(wire_group(inst, shadows))
            for px, py in bezier_points(inst):
                xs.append(px)
                ys.append(py)
            continue
        hexcolor = colors[inst["props"]["color"]] if inst["module"] == LED else None
        grp, (x, y, w, h) = part_group(inst, hexcolor)
        body.append(grp)
        xs += [x, x + w]
        ys += [y, y + h]
    if label:
        text, pos = label
        body.append(label_group(text, pos))
        xs += [pos[0] - 60, pos[0] + 60]
        ys += [pos[1] - 12]
    return body, (min(xs) - 20, min(ys) - 20, max(xs) + 20, max(ys) + 20)


def write(body, bounds, svg_path, png_path, title, desc):
    minx, miny, maxx, maxy = bounds
    w, h = maxx - minx, maxy - miny
    svg = ET.Element(Q("svg"), {"version": "1.1", "width": f"{w:.2f}", "height": f"{h:.2f}",
                                "viewBox": f"{minx:.2f} {miny:.2f} {w:.2f} {h:.2f}"})
    el("title", parent=svg, text=title)
    el("desc", parent=svg, text=desc)
    el("rect", {"x": minx, "y": miny, "width": w, "height": h, "fill": "#ffffff"}, svg)
    svg.append(body)
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(svg).write(svg_path, encoding="UTF-8", xml_declaration=True)
    ph = round(PNG_WIDTH * h / w)
    page = SCRATCH / f"render-{png_path.stem}.html"
    page.write_text(f'<!doctype html><html><body style="margin:0;background:#fff"><img src="{svg_path.as_uri()}" '
                    f'width="{PNG_WIDTH}" height="{ph}" style="display:block"></body></html>')
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    f"--window-size={PNG_WIDTH},{ph}", f"--screenshot={png_path}", page.as_uri()],
                   check=True, capture_output=True)
    with open(png_path, "rb") as f:
        size = struct.unpack(">II", f.read(24)[16:24])
    print(svg_path, png_path, size)


CREDIT = ("Breadboard, Arduino Uno (Rev3), potentiometer, pushbutton, LED and resistor graphics are from Fritzing "
          "(fritzing-parts), CC BY-SA 3.0. The LCD1602-I2C graphic is the custom part in the class's PotButtonLCD.fzz.")

# name -> (change to the class circuit, pin label (text, position), output stem, title)
VARIANTS = {
    "class": (None, None, SCRATCH / "class-original", "PotButtonLCD breadboard (class file)"),
    "p5-led-slider": (add_led2, ("LED2 · D9 (PWM)", (398.0, 22.0)), LAB / "p5-led-slider/assets/p5-led-slider-breadboard",
                      "Arduino Uno LED slider breadboard wiring: LED2 on D9 added"),
    "finger-led": (move_led1_to_d9, ("LED · D9 (PWM)", (330.0, 22.0)), LAB / "finger-led/assets/finger-led-breadboard",
                   "Arduino Uno finger dimmer breadboard wiring: the LED moved from D13 to D9"),
}


def main():
    SCRATCH.mkdir(parents=True, exist_ok=True)
    for change, label, stem, title in VARIANTS.values():
        body, bounds = build(change, label)
        write(body, bounds, stem.with_suffix(".svg"), stem.with_suffix(".png"), title,
              CREDIT + " Rendered from the class Fritzing file. " + title + ".")


if __name__ == "__main__":
    main()
