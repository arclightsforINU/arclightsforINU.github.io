# Builds the lcd-runner breadboard SVG/PNG: Uno from the earlier Fritzing export, 16x2 LCD from fritzing-parts, hand-drawn I2C backpack and four wires.
import subprocess
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SVG = "http://www.w3.org/2000/svg"
ET.register_namespace("", SVG)
Q = lambda t: f"{{{SVG}}}{t}"

LAB = Path(__file__).resolve().parents[1]
ROOT = LAB.parent
BASE = LAB / "led-pattern/assets/led-pattern-breadboard.svg"
LCD_SVG = ROOT / "_build/fritzing-parts/lcd-GDM1602K.svg"
OUT_DIR = LAB / "lcd-runner/assets"
SCRATCH = ROOT / "_build/lcd-runner"
FZ = "--fz" in sys.argv
FZ_LCD_SVG = ROOT / "_build/p5-slider/fzz/svg.breadboard.LCD1602-I2C_breadboard.svg"
SUFFIX = "-fz" if FZ else ""
OUT_SVG = OUT_DIR / f"lcd-runner-breadboard{SUFFIX}.svg"
OUT_PNG = OUT_DIR / f"lcd-runner-breadboard{SUFFIX}.png"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PNG_WIDTH = 2000

S = 1000 / 72
UNO_PIN_X = 100
UNO_Y = {"5V": 2256.66, "GND": 2356.66, "A4": 3156.66, "A5": 3256.66}
FZ_S = 3.25961 * 1000 / 329931
FZ_PIN_X, FZ_PIN_Y = 1012 * FZ_S, [20244 * FZ_S, 30365 * FZ_S, 40487 * FZ_S, 50609 * FZ_S]
FZ_CELL = (50201 * FZ_S, 48014 * FZ_S, (64297 - 50201) * FZ_S, (71241 - 48014) * FZ_S)
FZ_W, FZ_H = 3259.61, 1417.32
LX, LY = (-4160, 1950) if FZ else (-4010, 2000)
CELL = FZ_CELL if FZ else (27.79 * S, 34.154 * S, 10.027 * S, 16.522 * S)
HEADER_X0, HEADER_Y = LX + 1250, LY - 300
LANES = [LY - 950, LY - 820, LY - 690, LY - 560]
DESC_X = [-360, -480, -600, -720]
FZ_LEG = [LX - 130, LX - 250, LX - 250, LX - 130]
FZ_LANE = [LY - 110, LY - 240, LY + FZ_H + 240, LY + FZ_H + 110]
FZ_DESC = [-500, -380, -640, -760]
FS = 84

WIRES = [
    ("GND", "GND", "#000000", "#404040"),
    ("VCC", "5V", "#cc1414", "#ff2a2a"),
    ("SDA", "A4", "#1b5bb3", "#418dd9"),
    ("SCL", "A5", "#b39500", "#ffd400"),
]
UNO_LABEL = {"GND": "GND", "5V": "5V", "A4": "A4 (SDA)", "A5": "A5 (SCL)"}


def el(tag, attrs=None, parent=None, text=None):
    e = ET.Element(Q(tag), {k: str(v) for k, v in (attrs or {}).items()})
    if parent is not None:
        parent.append(e)
    if text is not None:
        e.text = text
    return e


def rounded(points, r):
    d = f"M{points[0][0]:.2f},{points[0][1]:.2f}"
    for i in range(1, len(points) - 1):
        (x0, y0), (x1, y1), (x2, y2) = points[i - 1], points[i], points[i + 1]
        l1 = ((x1 - x0) ** 2 + (y1 - y0) ** 2) ** 0.5
        l2 = ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
        k = min(r, l1 / 2, l2 / 2)
        a = (x1 + (x0 - x1) * k / l1, y1 + (y0 - y1) * k / l1)
        b = (x1 + (x2 - x1) * k / l2, y1 + (y2 - y1) * k / l2)
        d += f"L{a[0]:.2f},{a[1]:.2f}Q{x1:.2f},{y1:.2f} {b[0]:.2f},{b[1]:.2f}"
    return d + f"L{points[-1][0]:.2f},{points[-1][1]:.2f}"


def pill(parent, cx, cy, text):
    w = len(text) * FS * 0.62 + 56
    g = el("g", parent=parent)
    el("rect", {"x": cx - w / 2, "y": cy - 44, "width": w, "height": 88, "rx": 44,
                "fill": "#ffffff", "stroke": "#333333", "stroke-width": 5}, g)
    el("text", {"x": cx, "y": cy + FS * 0.35, "text-anchor": "middle", "font-size": FS, "font-weight": "bold",
                "font-family": "Arial, Helvetica, sans-serif", "fill": "#000000"}, g, text)


def uno_group():
    root = ET.parse(BASE).getroot()
    return next(g for g in root if g.get("partID") == "18462100")


def lcd_group():
    body = ET.parse(LCD_SVG).getroot().find(Q("g"))
    g = el("g", {"transform": f"translate({LX},{LY}) scale({S:.6f})"})
    g.append(body)
    return g


def fz_lcd_group():
    body = ET.parse(FZ_LCD_SVG).getroot().find(Q("g"))
    g = el("g", {"transform": f"translate({LX},{LY}) scale({FZ_S:.8f})", "fill-rule": "evenodd", "clip-rule": "evenodd"})
    g.append(body)
    return g


def backpack():
    g = el("g")
    x0, x1, y0, y1 = LX + 130, LX + 1900, LY - 420, LY + 130
    el("rect", {"x": x0, "y": y0, "width": x1 - x0, "height": y1 - y0, "rx": 28, "fill": "#2a5db0",
                "stroke": "#1b3f7a", "stroke-width": 8}, g)
    for hx, hy in ((x0 + 50, y0 + 50), (x1 - 50, y0 + 50), (x0 + 50, y1 - 50), (x1 - 50, y1 - 50)):
        el("circle", {"cx": hx, "cy": hy, "r": 24, "fill": "#e8e8e8", "stroke": "#9a916c", "stroke-width": 10}, g)
        el("circle", {"cx": hx, "cy": hy, "r": 12, "fill": "#ffffff"}, g)
    for i in range(16):
        px = LX + (19.43 + 7.2 * i) * S
        el("circle", {"cx": px, "cy": LY + 3.468 * S, "r": 34, "fill": "#c9c9c9", "stroke": "#8a8a8a", "stroke-width": 6}, g)
    ic_x, ic_y, ic_w, ic_h = LX + 520, LY - 300, 520, 240
    el("rect", {"x": ic_x, "y": ic_y, "width": ic_w, "height": ic_h, "rx": 10, "fill": "#1a1a1a"}, g)
    for i in range(8):
        for yy in (ic_y - 34, ic_y + ic_h):
            el("rect", {"x": ic_x + 36 + i * 62, "y": yy, "width": 28, "height": 34, "fill": "#bdbdbd"}, g)
    el("text", {"x": ic_x + ic_w / 2, "y": ic_y + ic_h / 2 + 14, "text-anchor": "middle", "font-size": 46,
                "font-family": "Arial, Helvetica, sans-serif", "fill": "#d0d0d0"}, g, "PCF8574")
    px, py = LX + 250, LY - 300
    el("rect", {"x": px, "y": py, "width": 160, "height": 160, "rx": 8, "fill": "#1d6fd1", "stroke": "#0f4a94",
                "stroke-width": 6}, g)
    el("circle", {"cx": px + 80, "cy": py + 80, "r": 52, "fill": "#e6e6e6", "stroke": "#9a9a9a", "stroke-width": 6}, g)
    el("rect", {"x": px + 74, "y": py + 34, "width": 12, "height": 92, "fill": "#8a8a8a"}, g)
    hx0, hy = HEADER_X0, HEADER_Y
    el("rect", {"x": hx0 - 70, "y": hy - 60, "width": 440, "height": 120, "rx": 8, "fill": "#262626"}, g)
    for i, (name, *_rest) in enumerate(WIRES):
        cx = hx0 + 100 * i
        el("rect", {"x": cx - 24, "y": hy - 24, "width": 48, "height": 48, "fill": "#d9b94a", "stroke": "#8a7424",
                    "stroke-width": 5}, g)
        el("text", {"x": cx, "y": hy + 110, "text-anchor": "middle", "font-size": 40, "font-weight": "bold",
                    "font-family": "Arial, Helvetica, sans-serif", "fill": "#ffffff"}, g, name)
    return g


def build():
    parts = el("g")
    parts.append(uno_group())
    if FZ:
        parts.append(fz_lcd_group())
    else:
        parts.append(lcd_group())
        parts.append(backpack())

    wires = el("g")
    labels = el("g")
    for i, (hdr, uno, outer, inner) in enumerate(WIRES):
        hx = HEADER_X0 + 100 * i
        ty = UNO_Y[uno]
        pts = [(hx, HEADER_Y), (hx, LANES[i]), (DESC_X[i], LANES[i]),
               (DESC_X[i], ty), (UNO_PIN_X, ty)]
        if FZ:
            py = LY + FZ_PIN_Y[i]
            pts = [(LX + FZ_PIN_X + 35, py), (FZ_LEG[i], py), (FZ_LEG[i], FZ_LANE[i]), (FZ_DESC[i], FZ_LANE[i]),
                   (FZ_DESC[i], ty), (UNO_PIN_X, ty)]
        d = rounded(pts, 80)
        g = el("g", parent=wires)
        for color, width in ((outer, "44.4444"), (inner, "22.2222")):
            el("path", {"stroke-linecap": "round", "stroke-linejoin": "round", "fill": "none", "stroke-width": width,
                        "stroke": color, "d": d}, g)
        if FZ:
            pill(labels, FZ_LEG[i] + 330, FZ_LANE[i], hdr)
            pill(labels, -190 if uno in ("5V", "GND") else -300, ty, UNO_LABEL[uno])
        else:
            pill(labels, hx + 210 + (35 if hdr in ("GND", "VCC") else 0), LANES[i], hdr)
            pill(labels, -190 - (80 if uno in ("A4", "A5") else 0), ty, UNO_LABEL[uno])
    return parts, wires, labels


def main():
    parts, wires, labels = build()
    minx, miny, maxx, maxy = (-4540, 440, 2300, 3720) if FZ else (-4110, 440, 2300, 3720)
    ox, oy = -minx, -miny
    w, h = maxx - minx, maxy - miny
    svg = ET.Element(Q("svg"), {"version": "1.2", "baseProfile": "tiny", "width": f"{w / 1000}in", "height": f"{h / 1000}in",
                                "viewBox": f"0 0 {w} {h}"})
    el("title", parent=svg, text="Arduino Uno and I2C 16x2 LCD wiring")
    desc = ("Arduino Uno (Rev3) graphic is from Fritzing (fritzing-parts), CC BY-SA 3.0. LCD1602-I2C graphic is from "
            "the class Fritzing file (part by Stephen Lilley). Wires drawn separately.") if FZ else (
        "Arduino Uno (Rev3) and 16x2 LCD (lcd-GDM1602K) graphics are from Fritzing "
        "(fritzing-parts), CC BY-SA 3.0. I2C backpack and wires drawn separately.")
    el("desc", parent=svg, text=desc)
    main_g = el("g", {"transform": f"translate({ox},{oy})"}, svg)
    el("rect", {"x": minx, "y": miny, "width": w, "height": h, "fill": "#ffffff"}, main_g)
    for g in (parts, wires, labels):
        main_g.append(g)
    el("rect", {"id": "lcd-first-cell", "x": f"{LX + CELL[0] + ox:.2f}", "y": f"{LY + CELL[1] + oy:.2f}",
                "width": f"{CELL[2]:.2f}", "height": f"{CELL[3]:.2f}", "fill": "none", "stroke": "none"}, svg)
    cx, cy, pw, ph_ = LX + CELL[0] + ox, LY + CELL[1] + oy, CELL[2] / 5, CELL[3] / 8
    runner = el("g", {"id": "lcd-runner-pose", "fill": "#1d2b22", "fill-opacity": "0.88"}, svg)
    for r, row in enumerate([0b00011, 0b00011, 0b00100, 0b01110, 0b10101, 0b00110, 0b01001, 0b10000]):
        for c in range(5):
            if row >> (4 - c) & 1:
                el("rect", {"x": f"{cx + c * pw + pw * 0.06:.2f}", "y": f"{cy + r * ph_ + ph_ * 0.06:.2f}",
                            "width": f"{pw * 0.88:.2f}", "height": f"{ph_ * 0.88:.2f}"}, runner)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    SCRATCH.mkdir(parents=True, exist_ok=True)
    ET.ElementTree(svg).write(OUT_SVG, encoding="UTF-8", xml_declaration=True)

    ph = round(PNG_WIDTH * h / w)
    page = SCRATCH / "render.html"
    page.write_text(f'<!doctype html><html><body style="margin:0;background:#fff"><img src="{OUT_SVG.as_uri()}" '
                    f'width="{PNG_WIDTH}" height="{ph}" style="display:block"></body></html>')
    subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--force-device-scale-factor=1",
                    f"--window-size={PNG_WIDTH},{ph}", f"--screenshot={OUT_PNG}", page.as_uri()],
                   check=True, capture_output=True)
    with open(OUT_PNG, "rb") as f:
        head = f.read(24)
    print(OUT_SVG, OUT_PNG, struct.unpack(">II", head[16:24]))
    print("first cell (svg units):", LX + CELL[0] + ox, LY + CELL[1] + oy, CELL[2], CELL[3])
    print("scale px/unit:", PNG_WIDTH / w)


main()
