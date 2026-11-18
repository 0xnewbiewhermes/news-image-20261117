#!/usr/bin/env python3
"""Draws the 17 November 2026 world-news front page (1024x1024) from data/stories.jsonl.

Flat-vector drawing with Pillow only: rendered at 2x, downsampled with LANCZOS,
quantized to a palette PNG. Deterministic. Usage: python gen_news.py [out.png]
"""
import json, math, os, sys
from PIL import Image, ImageDraw, ImageFont

S = 2
W = H = 1024
FD = "C:/Windows/Fonts/"
FONTS = {"gb": "georgiab.ttf", "g": "georgia.ttf", "sb": "segoeuib.ttf", "s": "segoeui.ttf"}
_fc = {}


def font(name, px):
    key = (name, round(px * S))
    if key not in _fc:
        _fc[key] = ImageFont.truetype(FD + FONTS[name], key[1])
    return _fc[key]


def tw(name, px, s):
    return font(name, px).getlength(s) / S


PAPER = "#f3ead3"
INK = "#17130e"
RULE = "#8c8068"
SOFT = "#5b5242"
REG = {
    "Europe": "#1f4e9e",
    "Middle East": "#b4560a",
    "Asia": "#0f7a5b",
    "North America": "#b0202c",
    "Africa": "#6c3a9b",
    "Oceania": "#0b86a8",
    "South America": "#8a8a00",
}
REG_ORDER = ["Europe", "Middle East", "Asia", "North America", "Africa", "Oceania", "South America"]
CONT = {"Europe": "Europe", "Middle East": "Asia", "Asia": "Asia", "North America": "North America",
        "Africa": "Africa", "Oceania": "Oceania", "South America": "South America"}

CHECKS = []   # (label, (x0,y0,x1,y1), container)


def load():
    rows = [json.loads(l) for l in open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "stories.jsonl"), encoding="utf-8") if l.strip()]
    return rows


# ---------------------------------------------------------------- drawing helpers
class Cv:
    """Scaled drawing wrapper: coordinates in design units, k = units->1x px."""

    def __init__(self, im, k=1.0, ox=0.0, oy=0.0):
        self.im = im
        self.d = ImageDraw.Draw(im)
        self.k = k * S
        self.ox, self.oy = ox * S, oy * S

    def P(self, x, y):
        return (self.ox + x * self.k, self.oy + y * self.k)

    def rect(self, x0, y0, x1, y1, fill=None, outline=None, w=1):
        a, b = self.P(x0, y0), self.P(x1, y1)
        self.d.rectangle([a, b], fill=fill, outline=outline, width=max(1, round(w * self.k)) if outline else 0)

    def rrect(self, x0, y0, x1, y1, r, fill=None, outline=None, w=1):
        a, b = self.P(x0, y0), self.P(x1, y1)
        self.d.rounded_rectangle([a, b], radius=r * self.k, fill=fill, outline=outline,
                                 width=max(1, round(w * self.k)) if outline else 0)

    def poly(self, pts, fill=None, outline=None, w=1):
        pp = [self.P(x, y) for x, y in pts]
        self.d.polygon(pp, fill=fill)
        if outline:
            self.d.line(pp + [pp[0]], fill=outline, width=max(1, round(w * self.k)), joint="curve")

    def ell(self, x0, y0, x1, y1, fill=None, outline=None, w=1):
        a, b = self.P(x0, y0), self.P(x1, y1)
        self.d.ellipse([a, b], fill=fill, outline=outline, width=max(1, round(w * self.k)) if outline else 0)

    def circ(self, x, y, r, fill=None, outline=None, w=1):
        self.ell(x - r, y - r, x + r, y + r, fill, outline, w)

    def line(self, pts, fill, w=1):
        pp = [self.P(x, y) for x, y in pts]
        self.d.line(pp, fill=fill, width=max(1, round(w * self.k)), joint="curve")

    def dashed(self, p0, p1, fill, w=1, dash=6, gap=4):
        x0, y0 = p0
        x1, y1 = p1
        L = math.hypot(x1 - x0, y1 - y0)
        n = int(L // (dash + gap)) + 1
        for i in range(n):
            a = i * (dash + gap) / L
            b = min(1.0, (i * (dash + gap) + dash) / L)
            if a >= 1:
                break
            self.line([(x0 + (x1 - x0) * a, y0 + (y1 - y0) * a), (x0 + (x1 - x0) * b, y0 + (y1 - y0) * b)], fill, w)

    def text(self, x, y, s, fname, px, fill, anchor="la"):
        self.d.text(self.P(x, y), s, font=font(fname, px * self.k / S), fill=fill, anchor=anchor)


def rot(pts, cx, cy, ang):
    c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    return [(cx + (x - cx) * c - (y - cy) * s, cy + (x - cx) * s + (y - cy) * c) for x, y in pts]


def star(cx, cy, r1, r2, n, a0=-90):
    pts = []
    for i in range(n * 2):
        r = r1 if i % 2 == 0 else r2
        a = math.radians(a0 + i * 180 / n)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def smoke(c, x, y, n, r0, grow, dx, dy, cols):
    for i in range(n):
        r = r0 + grow * i
        c.circ(x + dx * i, y + dy * i, r, cols[i % len(cols)])


def pole(c, x, y0, y1, col="#4a4338"):
    c.rect(x - 0.9, y0, x + 0.9, y1, col)
    c.circ(x, y0, 1.8, "#d9b43a")


def f_usa(c, x, y, w=36, h=24):
    c.rect(x, y, x + w, y + h, "#ffffff")
    for i in range(7):
        c.rect(x, y + i * h / 7 * 1.0, x + w, y + i * h / 7 + h / 14, "#b22234")
    c.rect(x, y, x + w * 0.42, y + h * 0.54, "#3c3b6e")
    for i in range(3):
        for j in range(2):
            c.circ(x + w * (0.08 + 0.12 * i), y + h * (0.12 + 0.2 * j) + 0.5, 1.1, "#ffffff")


def f_jp(c, x, y, w=36, h=24):
    c.rect(x, y, x + w, y + h, "#fdfdfd", "#b8b2a4", 0.5)
    c.circ(x + w / 2, y + h / 2, h * 0.3, "#bc002d")


def f_in(c, x, y, w=36, h=24):
    c.rect(x, y, x + w, y + h / 3, "#ff9933")
    c.rect(x, y + h / 3, x + w, y + 2 * h / 3, "#ffffff")
    c.rect(x, y + 2 * h / 3, x + w, y + h, "#138808")
    c.circ(x + w / 2, y + h / 2, h * 0.11, None, "#000080", 0.9)


def f_au(c, x, y, w=36, h=24):
    c.rect(x, y, x + w, y + h, "#00247d")
    c.rect(x, y, x + w * 0.5, y + h * 0.5, "#1d3b8f")
    c.line([(x, y), (x + w * .5, y + h * .5)], "#ffffff", 1.6)
    c.line([(x + w * .5, y), (x, y + h * .5)], "#ffffff", 1.6)
    c.line([(x + w * .25, y), (x + w * .25, y + h * .5)], "#ffffff", 2.4)
    c.line([(x, y + h * .25), (x + w * .5, y + h * .25)], "#ffffff", 2.4)
    c.line([(x + w * .25, y), (x + w * .25, y + h * .5)], "#cf142b", 1.2)
    c.line([(x, y + h * .25), (x + w * .5, y + h * .25)], "#cf142b", 1.2)
    for sx, sy in [(.25, .78), (.72, .25), (.82, .55), (.65, .82), (.9, .85)]:
        c.circ(x + w * sx, y + h * sy, 1.3, "#ffffff")


def f_ht(c, x, y, w=36, h=24):
    c.rect(x, y, x + w, y + h / 2, "#00209f")
    c.rect(x, y + h / 2, x + w, y + h, "#d21034")
    c.rect(x + w * .38, y + h * .36, x + w * .62, y + h * .64, "#ffffff")
    c.circ(x + w / 2, y + h / 2, h * .08, "#2a8a2a")


def f_sv(c, x, y, w=36, h=24):
    c.rect(x, y, x + w, y + h, "#0f47af")
    c.rect(x, y + h / 3, x + w, y + 2 * h / 3, "#ffffff")
    c.circ(x + w / 2, y + h / 2, h * .08, "#8aa63a")


def f_mn(c, x, y, w=36, h=24):
    c.rect(x, y, x + w, y + h, "#da2032")
    c.rect(x + w / 3, y, x + 2 * w / 3, y + h, "#0066b3")
    c.circ(x + w / 6, y + h * .5, h * .12, "#ffd900")


def waves(c, W_, y0, y1, col, step=14):
    for i in range(int(W_ // step) + 1):
        for yy in range(int(y0), int(y1), 9):
            off = (yy // 9 % 2) * step / 2
            c.line([(i * step + off, yy), (i * step + off + step / 2, yy - 1.5), (i * step + off + step, yy)], col, 0.9)


# ---------------------------------------------------------------- scenes (design H=100, W varies)
def sc_bridge(c, W_):
    cx = W_ / 2
    c.rect(0, 0, W_, 100, "#34466a")
    c.rect(0, 0, W_, 45, "#3d5078")
    c.rect(0, 62, W_, 100, "#13233a")
    c.rect(0, 58, W_, 63, "#53638a")  # haze horizon
    waves(c, W_, 74, 100, "#2b4468")
    # left span, standing
    y = 55
    for px in range(int(cx - 170), int(cx - 20), 28):
        c.rect(px, y + 4, px + 5, 90, "#8a8f9c")
        c.rect(px - 2, 84, px + 7, 90, "#6b7080")
    c.rect(cx - 175, y, cx - 22, y + 5, "#aeb3bf")
    c.line([(cx - 175, y), (cx - 22, y)], "#d9dce3", 1.2)
    # arch over left part
    for i in range(0, 6):
        a = cx - 160 + i * 25
        c.line([(a, y), (a + 12, y - 12), (a + 25, y)], "#8a8f9c", 1.4)
    # collapsed span: tilted slabs into water
    c.poly([(cx - 22, y), (cx - 22, y + 5), (cx - 2, 86), (cx + 6, 80)], "#aeb3bf")
    c.poly([(cx + 40, y), (cx + 40, y + 5), (cx + 22, 84), (cx + 14, 79)], "#aeb3bf")
    c.line([(cx - 2, 84), (cx + 8, 79), (cx + 22, 85)], "#6b7080", 2)
    c.ell(cx - 8, 86, cx + 26, 94, "#9fb4d4")  # splash foam
    c.ell(cx - 2, 88, cx + 20, 93, "#cddcf0")
    # right span standing
    for px in range(int(cx + 52), int(cx + 170), 28):
        c.rect(px, y + 4, px + 5, 90, "#8a8f9c")
        c.rect(px - 2, 84, px + 7, 90, "#6b7080")
    c.rect(cx + 40, y, cx + 175, y + 5, "#aeb3bf")
    for i in range(0, 5):
        a = cx + 45 + i * 25
        c.line([(a, y), (a + 12, y - 12), (a + 25, y)], "#8a8f9c", 1.4)
    # smoke
    smoke(c, cx + 9, 48, 7, 5, 1.4, 3, -3.4, ["#4b4f5c", "#5d616e", "#3b3f4c"])
    c.poly(star(cx + 9, 56, 11, 5, 8), "#f59e1b")
    c.poly(star(cx + 9, 56, 6, 3, 8), "#ffe27a")
    # missiles from left
    for (yy, x0) in [(40, cx - 150), (50, cx - 125)]:
        c.dashed((x0 - 40, yy), (x0, yy), "#e9e3d0", 1.3, 5, 3)
        c.poly([(x0, yy - 2.5), (x0 + 16, yy - 2.5), (x0 + 24, yy), (x0 + 16, yy + 2.5), (x0, yy + 2.5)], "#e8e4d6")
        c.poly([(x0, yy - 2.5), (x0 - 5, yy - 6), (x0 + 3, yy - 2.5)], "#d8403a")
        c.poly([(x0, yy + 2.5), (x0 - 5, yy + 6), (x0 + 3, yy + 2.5)], "#d8403a")
        c.poly([(x0 + 24, yy), (x0 + 16, yy - 2.5), (x0 + 16, yy + 2.5)], "#d8403a")


def drone(c, x, y, ang=0, sc=1.0, col="#2b2f3a"):
    pts = [(x - 6 * sc, y), (x + 4 * sc, y - 3 * sc), (x + 8 * sc, y), (x + 4 * sc, y + 3 * sc)]
    c.poly(rot(pts, x, y, ang), col)
    c.poly(rot([(x - 3 * sc, y), (x - 2 * sc, y - 9 * sc), (x + 2 * sc, y - 9 * sc), (x + 3 * sc, y)], x, y, ang), col)
    c.poly(rot([(x - 3 * sc, y), (x - 2 * sc, y + 9 * sc), (x + 2 * sc, y + 9 * sc), (x + 3 * sc, y)], x, y, ang), col)


def sc_bahrain(c, W_):
    cx = W_ / 2
    c.rect(0, 0, W_, 100, "#9fcbe6")
    c.rect(0, 0, W_, 50, "#b8dcf0")
    c.rect(0, 74, W_, 100, "#2f7fb0")
    waves(c, W_, 80, 100, "#5aa3cf")
    # island coast
    c.poly([(cx - 90, 100), (cx - 80, 76), (cx - 40, 70), (cx + 30, 70), (cx + 85, 76), (cx + 95, 100)], "#e3cf9a")
    c.poly([(cx - 70, 100), (cx - 62, 84), (cx + 70, 84), (cx + 82, 100)], "#d3bd84")
    # base
    c.rect(cx - 55, 58, cx - 20, 72, "#8e96a3")
    c.rect(cx - 55, 55, cx - 20, 59, "#6c7482")
    c.rect(cx - 48, 62, cx - 40, 72, "#3e4452")
    c.rect(cx - 34, 63, cx - 27, 68, "#cfe7f7")
    c.rect(cx - 12, 62, cx + 14, 72, "#a2a9b4")
    c.rect(cx - 12, 60, cx + 14, 63, "#6c7482")
    # radar dish
    c.rect(cx + 33, 56, cx + 36, 72, "#5a6070")
    c.rect(cx + 28, 70, cx + 41, 73, "#5a6070")
    c.poly([(cx + 24, 46), (cx + 46, 50), (cx + 44, 56), (cx + 30, 55)], "#e8ebf0", "#5a6070", 1)
    c.line([(cx + 35, 52), (cx + 39, 44)], "#5a6070", 1.4)
    c.circ(cx + 39, 43, 1.8, "#d8403a")
    c.line([(cx + 47, 46), (cx + 53, 40)], "#d8403a", 1)
    c.line([(cx + 50, 52), (cx + 59, 48)], "#d8403a", 1)
    # palm
    c.line([(cx + 70, 82), (cx + 72, 66)], "#7a5a32", 2)
    for a in (-60, -20, 20, 60, 100):
        e = (cx + 72 + 10 * math.cos(math.radians(a - 90)) * 1.4, 64 + 8 * math.sin(math.radians(a - 90)) * 1.1)
        c.line([(cx + 72, 66), e], "#2f7a3a", 2)
    # drones with dashed paths
    for (x, y, ex, ey) in [(cx + 130, 36, cx + 20, 56), (cx + 95, 30, cx - 20, 54), (cx + 150, 52, cx + 40, 60)]:
        c.dashed((x, y), (ex, ey), "#33393f", 1, 5, 4)
    drone(c, cx + 134, 35, 160, 1.0)
    drone(c, cx + 98, 29, 150, 1.0)
    drone(c, cx - 60, 40, 20, 0.9, "#555b66")
    # interception bursts
    for (x, y, r) in [(cx + 70, 46, 9), (cx - 4, 42, 8)]:
        c.poly(star(x, y, r, r * .45, 9), "#f58a1b")
        c.poly(star(x, y, r * .55, r * .25, 9), "#fff3a0")
    # tiny flag (Bahrain red/white)
    c.rect(cx - 70, 48, cx - 69, 72, "#4a4338")
    c.rect(cx - 69, 48, cx - 52, 56, "#ffffff")
    c.rect(cx - 69, 48, cx - 63, 56, "#ce1126")


def sc_jericho(c, W_):
    cx = W_ / 2
    c.rect(0, 0, W_, 100, "#e9cfa5")
    c.rect(0, 0, W_, 40, "#efdcb8")
    c.poly([(0, 62), (60, 48), (130, 58), (200, 44), (W_, 58), (W_, 100), (0, 100)], "#cfb07c")
    c.rect(0, 80, W_, 100, "#b8955f")
    houses = [(-130, 66, 30, 22), (-92, 60, 34, 28), (-44, 68, 28, 20), (60, 62, 34, 26), (104, 68, 30, 20), (-8, 70, 24, 16)]
    for hx, hy, hw, hh in houses:
        x0 = cx + hx
        c.rect(x0, hy, x0 + hw, hy + hh + 14, "#d9c196")
        c.rect(x0, hy, x0 + hw, hy + 3, "#a98c5c")
        c.rect(x0 + hw * .3, hy + hh * .4, x0 + hw * .3 + 6, hy + hh * .4 + 10, "#5f4a2c")
        c.rect(x0 + hw * .7, hy + 6, x0 + hw * .7 + 5, hy + 12, "#5f4a2c")
        for i in range(3):
            c.line([(x0, hy + 6 + i * 6), (x0 + hw, hy + 6 + i * 6)], "#c4aa7c", 0.7)
    # olive trees
    for tx, ty in [(-108, 86), (-60, 90), (22, 88), (50, 90), (140, 86)]:
        c.rect(cx + tx - 1, ty - 12, cx + tx + 1, ty, "#5b4326")
        c.circ(cx + tx, ty - 15, 7, "#7d8a5a")
        c.circ(cx + tx - 5, ty - 11, 5, "#6e7b4e")
        c.circ(cx + tx + 5, ty - 11, 5, "#8a966a")
    # smoke plume from house
    smoke(c, cx + 76, 58, 8, 4, 1.6, 2.2, -4, ["#6f6a62", "#857f74", "#5c5851"])
    c.poly(star(cx + 76, 66, 6, 3, 7), "#e0782a")


def sc_quad(c, W_):
    cx = W_ / 2
    c.rect(0, 0, W_, 100, "#c9dbe8")
    c.rect(0, 0, W_, 40, "#dce9f2")
    c.rect(0, 88, W_, 100, "#8e8f94")
    c.rect(0, 86, W_, 88, "#7b7c82")
    xs = [cx - 150, cx - 105, cx - 60, cx - 15]
    fl = [f_usa, f_jp, f_in, f_au]
    for x, f in zip(xs, fl):
        pole(c, x, 36, 90)
        f(c, x + 1, 38, 40, 26)
    # ore pile
    cols = ["#6a4aa8", "#8d6ad0", "#4a8fb0", "#5fb1c9", "#a78be0"]
    base = [(cx + 30, 92), (cx + 50, 74), (cx + 68, 66), (cx + 88, 72), (cx + 114, 92)]
    c.poly(base, "#5d5a63")
    for (x, y, h, wd, i) in [(cx + 44, 86, 24, 8, 0), (cx + 60, 86, 34, 10, 1), (cx + 76, 86, 26, 9, 2),
                              (cx + 90, 86, 20, 8, 3), (cx + 54, 70, 18, 7, 4), (cx + 72, 64, 20, 8, 1), (cx + 100, 86, 14, 7, 2)]:
        c.poly([(x - wd / 2, y), (x - wd / 3, y - h * .8), (x, y - h), (x + wd / 3, y - h * .75), (x + wd / 2, y)], cols[i], "#2d2a40", 0.7)
        c.line([(x, y - h), (x - wd * .05, y)], "#ffffff", 0.6)
    c.circ(cx + 20, 90, 3, "#5d5a63")


def sc_measles(c, W_):
    cx = W_ / 2
    c.rect(0, 0, W_, 100, "#d7e6ef")
    c.rect(0, 0, W_, 100, "#d7e6ef")
    # Americas silhouette (coarse)
    na = [(-35, 6), (-22, 0), (-6, 1), (8, 4), (16, 10), (10, 15), (4, 18), (0, 22), (4, 28), (-2, 26), (-8, 21), (-16, 17), (-26, 14), (-33, 11)]
    ca = [(-4, 25), (2, 27), (6, 31), (10, 34), (6, 35), (0, 30)]
    sa = [(8, 33), (18, 33), (27, 40), (26, 50), (20, 58), (15, 64), (12, 56), (8, 46)]
    ox = cx - 40
    T = lambda p: (ox + p[0] * 1.0, 37 + p[1] * 0.97)
    for poly_ in (na, ca, sa):
        c.poly([T(p) for p in poly_], "#e8dfc4", "#8e8468", 0.9)
    # hotspots US, Mexico, Bolivia
    for (x, y) in [(-12, 9), (-12, 19), (17, 48)]:
        px_, py_ = T((x, y))
        c.circ(px_, py_, 6, "#b0202c", "#ffffff", 0.9)
        c.circ(px_, py_, 2.4, "#f3c9c4")
    # virus particle (left)
    vx, vy = cx - 120, 62
    for i in range(14):
        a = math.radians(i * 360 / 14)
        c.line([(vx + 15 * math.cos(a), vy + 15 * math.sin(a)), (vx + 22 * math.cos(a), vy + 22 * math.sin(a))], "#7a1620", 2)
        c.circ(vx + 23 * math.cos(a), vy + 23 * math.sin(a), 2.8, "#b0202c")
    c.circ(vx, vy, 16, "#b0202c")
    c.circ(vx - 5, vy - 5, 3, "#d94b55")
    c.circ(vx + 6, vy + 4, 2.4, "#8f1823")
    # syringe (right, diagonal)
    sx, sy = cx + 70, 44
    parts = [
        ([(-34, -4), (-6, -4), (-6, 4), (-34, 4)], "#f2f4f7"),
        ([(-6, -2), (12, -0.6), (12, 0.6), (-6, 2)], "#9aa3ad"),
        ([(-34, -4), (-34, 4), (-38, 4), (-38, -4)], "#7e8794"),
        ([(-38, -7), (-35, -7), (-35, 7), (-38, 7)], "#7e8794"),
        ([(-30, -2.6), (-14, -2.6), (-14, 2.6), (-30, 2.6)], "#d9323c"),
        ([(-8, -6), (-8, 6), (-5, 6), (-5, -6)], "#7e8794"),
        ([(-45, -1), (-38, -1), (-38, 1), (-45, 1)], "#7e8794"),
    ]
    for pts, col in parts:
        c.poly(rot([(sx + x, sy + y) for x, y in pts], sx, sy, -35), col, "#4a5360", 0.6)


def sc_alaska(c, W_):
    cx = W_ / 2
    c.rect(0, 0, W_, 100, "#274a7a")
    c.rect(0, 0, W_, 100, "#2c5588")
    for r in range(0, 4):
        c.line([(0, 40 + r * 18), (W_, 40 + r * 18)], "#3a669c", 0.5)
    ak = [(0, 10), (8, 4), (22, 2), (36, 3), (40, 12), (38, 20), (42, 27), (52, 34), (58, 44), (55, 47), (48, 42), (40, 36), (34, 32), (30, 36), (24, 34), (20, 38), (12, 33), (8, 28), (2, 26), (-4, 22), (0, 16)]
    ox, oy = cx - 100, 36
    c.poly([(ox + x * 1.45, oy + y * 1.2) for x, y in ak], "#ece3c6", "#14243b", 1)
    for (x, y) in [(-8, 44), (-16, 47), (-24, 49)]:
        c.circ(ox + x * 1.45, oy + y * 1.2, 2.4, "#ece3c6")
    c.poly(star(ox + 24 * 1.45, oy + 14 * 1.2, 5, 2.2, 5), "#2c5588")
    # ballot box
    bx = cx + 60
    c.rect(bx - 28, 62, bx + 28, 94, "#eee8d6", "#10203a", 1.2)
    c.rect(bx - 28, 62, bx + 28, 70, "#c92a35")
    c.rect(bx - 14, 66, bx + 14, 68, "#10203a")
    c.rect(bx - 17, 40, bx + 17, 62, "#ffffff", "#10203a", 1)
    c.line([(bx - 11, 46), (bx + 11, 46)], "#9aa3b2", 1.2)
    c.line([(bx - 11, 51), (bx + 5, 51)], "#9aa3b2", 1.2)
    c.line([(bx - 8, 56), (bx - 3, 61), (bx + 12, 44)], "#14933e", 3.2)
    c.poly(star(bx, 82, 7, 3, 5), "#f3e9c3")


def sc_serbia(c, W_):
    cx = W_ / 2
    c.rect(0, 0, W_, 100, "#d3dde8")
    c.rect(0, 0, W_, 40, "#e2eaf1")
    c.rect(0, 92, W_, 100, "#8e8f94")
    # parliament building (left): steps, columns, pediment, drum and dome
    bx = cx - 120
    c.rect(bx - 74, 88, bx + 74, 92, "#a9a69c")
    c.rect(bx - 68, 84, bx + 68, 88, "#bdb9ad")
    c.rect(bx - 62, 66, bx + 62, 84, "#eee7d6", "#6f6a5c", 0.7)
    for i in range(9):
        x = bx - 56 + i * 14
        c.rect(x, 69, x + 5, 84, "#fbf7ec", "#8a8470", 0.5)
    c.poly([(bx - 66, 66), (bx, 55), (bx + 66, 66)], "#e4dcc6", "#6f6a5c", 0.8)
    c.rect(bx - 15, 52, bx + 15, 61, "#e9e2d0", "#6f6a5c", 0.7)
    c.poly([(bx - 16 + 32 * i / 12, 52 - 12 * math.sin(math.pi * i / 12)) for i in range(13)] + [(bx + 16, 52), (bx - 16, 52)], "#7c8aa3", "#4a5568", 0.8)
    c.rect(bx - 0.8, 36, bx + 0.8, 42, "#4a4338")
    # hemicycle (right): 140 student-list seats vs 103 others
    ax, ay = cx + 95, 97
    c.poly([(ax + 60 * math.cos(math.pi * i / 40), ay - 60 * math.sin(math.pi * i / 40)) for i in range(41)], "#26324d")
    radii = [17 + 5.4 * i for i in range(8)]
    total = 243
    counts = [round(total * r / sum(radii)) for r in radii]
    counts[-1] += total - sum(counts)
    seats = []
    for r, n in zip(radii, counts):
        for k in range(n):
            seats.append((math.pi * (1 - k / (n - 1)), r))
    seats.sort(key=lambda t: (-round(t[0], 4), t[1]))
    assert len(seats) == 243
    for i, (ang, r) in enumerate(seats):
        c.circ(ax + r * math.cos(ang), ay - r * math.sin(ang), 1.7, "#f2b705" if i < 140 else "#9fb0d0")
    c.rect(ax - 13, ay - 10, ax + 13, ay - 3, "#6a7898")  # speaker's desk


def sc_plane(c, W_):
    cx = W_ / 2
    c.rect(0, 0, W_, 100, "#aab6c4")
    c.rect(0, 0, W_, 55, "#b9c4d0")
    c.poly([(0, 78), (50, 70), (110, 76), (170, 68), (W_, 76), (W_, 100), (0, 100)], "#e8eef2")
    # pines
    import random
    rnd = random.Random(7)
    for i in range(34):
        x = rnd.uniform(0, W_)
        y = rnd.uniform(80, 97)
        h = rnd.uniform(11, 18)
        c.poly([(x, y - h), (x - h * .35, y), (x + h * .35, y)], "#2f5a44")
        c.poly([(x, y - h), (x - h * .17, y - h * .45), (x + h * .17, y - h * .45)], "#eef3f5")
    # smoke trail
    smoke(c, cx + 40, 44, 7, 3, 0.9, -9, -3.2, ["#5e5f66", "#74757c", "#4c4d54"])
    # plane (top-down, tilted nose-down)
    px, py = cx + 62, 64
    pl = []
    ang = 28

    def add(pts, col, ol=None):
        c.poly(rot([(px + x, py + y) for x, y in pts], px, py, ang), col, ol, 0.6)
    add([(-34, -3), (24, -3.4), (34, 0), (24, 3.4), (-34, 3)], "#e9ecef", "#4a5360")  # fuselage
    add([(-8, -3), (-12, -33), (-3, -33), (6, -3)], "#d5dae0", "#4a5360")  # wings
    add([(-8, 3), (-12, 33), (-3, 33), (6, 3)], "#d5dae0", "#4a5360")
    add([(-34, -2), (-38, -12), (-30, -12), (-26, -2)], "#d5dae0", "#4a5360")  # tail
    add([(-34, 2), (-38, 12), (-30, 12), (-26, 2)], "#d5dae0", "#4a5360")
    add([(24, -2), (30, -1.2), (30, 1.2), (24, 2)], "#4b5563")
    for off in (-27, -16, 16, 27):
        add([(-2, off - 1.6), (-6, off - 1.6), (-6, off + 1.6), (-2, off + 1.6)], "#6b7280")
        for (cx_, cy_) in [rot([(px - 7, py + off)], px, py, ang)[0]]:
            c.circ(cx_, cy_, 5, None, "#3b4350", 1)
    add([(-10, -33), (-3, -33), (-3, -31), (-10, -31)], "#d94a3a")
    # fire at tail
    tx, ty = rot([(px - 36, py)], px, py, ang)[0]
    c.poly(star(tx, ty, 7, 3, 7), "#f08a24")
    c.poly(star(tx, ty, 3.6, 1.6, 7), "#ffe58a")


def person(c, x, y, h, col, sign=None):
    c.circ(x, y - h * .82, h * .13, col)
    c.rrect(x - h * .17, y - h * .68, x + h * .17, y - h * .22, h * .1, col)
    c.rect(x - h * .13, y - h * .3, x - h * .02, y, col)
    c.rect(x + h * .02, y - h * .3, x + h * .13, y, col)


def sc_bangladesh(c, W_):
    cx = W_ / 2
    c.rect(0, 0, W_, 100, "#d9d2b6")
    c.rect(0, 0, W_, 45, "#e6e0c8")
    c.rect(0, 88, W_, 100, "#8e8b83")
    # factory
    fx = cx - 165
    c.rect(fx, 44, fx + 96, 90, "#a8553a")
    for i in range(4):
        c.poly([(fx + i * 24, 44), (fx + i * 24, 34), (fx + i * 24 + 24, 44)], "#8d4630")
    c.rect(fx + 100, 26, fx + 112, 90, "#8d4630")
    c.rect(fx + 98, 24, fx + 114, 28, "#5e2d1d")
    smoke(c, fx + 106, 22, 5, 4, 1.0, 5, -3, ["#8c8a86", "#a09d98"])
    for i in range(4):
        c.rect(fx + 8 + i * 22, 58, fx + 22 + i * 22, 70, "#f0dca0")
    # sewing machine icon on wall
    c.circ(fx + 48, 79, 7.5, "#f3ead3")
    c.rect(fx + 42, 80, fx + 54, 82, "#3b3b3b")
    c.rect(fx + 42, 74, fx + 45, 82, "#3b3b3b")
    c.rect(fx + 42, 74, fx + 53, 76, "#3b3b3b")
    c.rect(fx + 52, 74, fx + 53.4, 79, "#3b3b3b")
    # crowd
    cols = ["#2a2622", "#3b3631", "#2a2622", "#463e36"]
    xs = [-52, -34, -18, 0, 20, 40, 58, 76, 94, 112, 130]
    for i, x in enumerate(xs):
        person(c, cx + x, 94, 36 + (i % 3) * 3, cols[i % 4])
    # signs
    c.line([(cx + 20, 94 - 36), (cx + 20, 52)], "#6b5a3e", 1.4)
    c.rrect(cx - 7, 36, cx + 54, 54, 2, "#fffdf2", "#2a2622", 1)
    c.text(cx + 23.5, 45.2, "30,000", "sb", 14, "#b0202c", "mm")
    c.line([(cx - 34, 94 - 33), (cx - 34, 62)], "#6b5a3e", 1.4)
    c.rrect(cx - 52, 52, cx - 18, 66, 2, "#fffdf2", "#2a2622", 1)
    c.line([(cx - 47, 57), (cx - 24, 57)], "#2a2622", 1.4)
    c.line([(cx - 47, 61), (cx - 30, 61)], "#2a2622", 1.4)
    c.line([(cx + 94, 94 - 35), (cx + 94, 66)], "#6b5a3e", 1.4)
    c.rrect(cx + 78, 54, cx + 112, 68, 2, "#fffdf2", "#2a2622", 1)
    c.line([(cx + 83, 59), (cx + 106, 59)], "#2a2622", 1.4)
    c.line([(cx + 83, 63), (cx + 98, 63)], "#2a2622", 1.4)


def sc_mongolia(c, W_):
    cx = W_ / 2
    c.rect(0, 0, W_, 100, "#8fc0e3")
    c.rect(0, 0, W_, 40, "#a9d1ee")
    c.circ(cx + 140, 40, 7, "#fff0b0")
    c.poly([(0, 70), (60, 58), (140, 66), (230, 56), (W_, 66), (W_, 100), (0, 100)], "#7aa65a")
    c.rect(0, 84, W_, 100, "#6a9650")
    # state building
    bx = cx + 15
    c.rect(bx, 62, bx + 90, 90, "#e9e2d0", "#6f6a5c", 0.8)
    c.poly([(bx - 4, 62), (bx + 45, 46), (bx + 94, 62)], "#d9d1bb", "#6f6a5c", 0.8)
    for i in range(6):
        c.rect(bx + 6 + i * 14, 64, bx + 10 + i * 14, 88, "#bdb59e")
    c.rect(bx + 38, 74, bx + 52, 90, "#6f5a3c")
    pole(c, bx + 45, 24, 46)
    f_mn(c, bx + 46, 25, 22, 14)
    # ger
    gx = cx - 95
    c.rect(gx - 30, 66, gx + 30, 90, "#f2eddf", "#8a8372", 0.8)
    c.poly([(gx - 34, 66), (gx, 44), (gx + 34, 66)], "#fbf8ee", "#8a8372", 0.8)
    c.rect(gx - 7, 74, gx + 7, 90, "#b0202c")
    c.line([(gx - 7, 82), (gx + 7, 82)], "#d9b43a", 1)
    c.line([(gx - 30, 71), (gx + 30, 71)], "#2f5ea8", 1.4)
    c.circ(gx, 44, 3, "#2f5ea8")
    # envelope icon
    ex, ey = cx - 22, 70
    c.rect(ex - 24, ey - 3, ex + 24, ey + 25, "#fffdf2", "#2a2622", 1.2)
    c.line([(ex - 24, ey - 3), (ex, ey + 12), (ex + 24, ey - 3)], "#2a2622", 1.2)
    c.circ(ex, ey + 12, 4.2, "#b0202c")


def sc_haiti(c, W_):
    cx = W_ / 2
    c.rect(0, 0, W_, 100, "#f0d9a8")
    c.rect(0, 0, W_, 38, "#f7e6c0")
    # hills + buildings
    c.poly([(0, 58), (50, 46), (120, 56), (190, 44), (W_, 56), (W_, 100), (0, 100)], "#b9b77c")
    for i, x in enumerate(range(-150, 160, 24)):
        c.rect(cx + x, 60 - (i * 7 % 9), cx + x + 20, 82, ["#d9a98a", "#c98d70", "#e6c08a", "#b87a5f"][i % 4])
        c.rect(cx + x + 4, 66, cx + x + 8, 71, "#6b4a38")
    c.rect(0, 86, W_, 100, "#6b6256")
    # marchers
    cols = ["#2a2622", "#3b3631", "#463e36"]
    xs = [-110, -88, -66, -44, -22, 0, 22, 44, 66, 88, 110, 132]
    for i, x in enumerate(xs):
        person(c, cx + x, 96, 38 + (i % 3) * 3, cols[i % 3])
    # banners
    c.line([(cx - 96, 58), (cx - 96, 82)], "#6b5a3e", 1.4)
    c.line([(cx - 10, 58), (cx - 10, 82)], "#6b5a3e", 1.4)
    c.rrect(cx - 98, 50, cx - 8, 66, 2, "#fffdf2", "#2a2622", 1)
    c.line([(cx - 90, 55), (cx - 20, 55)], "#2a2622", 1.6)
    c.line([(cx - 90, 61), (cx - 40, 61)], "#2a2622", 1.6)
    # flags held up
    pole(c, cx + 36, 34, 70)
    f_ht(c, cx + 37, 36, 36, 24)
    pole(c, cx + 100, 38, 70)
    f_sv(c, cx + 101, 40, 36, 24)


def sc_court(c, W_):
    cx = W_ / 2
    c.rect(0, 0, W_, 100, "#d5cdbb")
    c.rect(0, 0, W_, 45, "#e3dccb")
    c.rect(0, 90, W_, 100, "#9a9484")
    bx = cx - 10
    # courthouse
    c.poly([(bx - 52, 50), (bx, 33), (bx + 52, 50)], "#f1ece0", "#5a5546", 1)
    c.rect(bx - 52, 50, bx + 52, 55, "#e4ddcc", "#5a5546", 0.8)
    for i in range(6):
        x = bx - 46 + i * 18.4
        c.rect(x, 55, x + 7, 84, "#f7f3e8", "#8a8470", 0.6)
    c.rect(bx - 56, 84, bx + 56, 88, "#e4ddcc", "#5a5546", 0.8)
    c.rect(bx - 60, 88, bx + 60, 92, "#d7d0be", "#5a5546", 0.8)
    c.circ(bx, 46, 3.5, "#d9b43a")
    # scales (left)
    sx = cx - 120
    c.rect(sx - 1, 52, sx + 1, 86, "#3a342a")
    c.rect(sx - 8, 86, sx + 8, 90, "#3a342a")
    c.line([(sx - 22, 54), (sx + 22, 54)], "#3a342a", 2)
    for dx in (-22, 22):
        c.line([(sx + dx, 54), (sx + dx - 8, 70)], "#3a342a", 0.8)
        c.line([(sx + dx, 54), (sx + dx + 8, 70)], "#3a342a", 0.8)
        c.poly([(sx + dx - 11, 70), (sx + dx + 11, 70), (sx + dx + 6, 75), (sx + dx - 6, 75)], "#d9b43a", "#3a342a", 0.8)
    c.circ(sx, 52, 3, "#d9b43a")
    # gavel (right)
    gx, gy = cx + 112, 78
    c.rrect(gx - 22, 90, gx + 24, 95, 1.5, "#5e3d22")
    c.poly(rot([(gx - 14, gy - 24), (gx + 6, gy - 24), (gx + 6, gy - 10), (gx - 14, gy - 10)], gx, gy, 25), "#7a4e2a", "#3a2412", 0.8)
    c.poly(rot([(gx - 6, gy - 10), (gx - 2, gy - 10), (gx - 2, gy + 14), (gx - 6, gy + 14)], gx, gy, 25), "#9a6a3a", "#3a2412", 0.8)
    c.poly(rot([(gx - 17, gy - 26), (gx - 14, gy - 26), (gx - 14, gy - 8), (gx - 17, gy - 8)], gx, gy, 25), "#b8892e")
    c.poly(rot([(gx + 6, gy - 26), (gx + 9, gy - 26), (gx + 9, gy - 8), (gx + 6, gy - 8)], gx, gy, 25), "#b8892e")


# (scene fn, plate1, plate1 pos, plate2, plate2 pos)
SCENES = {
    1: (sc_bridge, "CRIMEAN BRIDGE: SPAN DOWN", "tl", None, None),
    2: (sc_bahrain, "BAHRAIN SAYS: DRONES STOPPED", "tl", None, None),
    3: (sc_jericho, "JERICHO: 1 KILLED, 10 WOUNDED", "tl", None, None),
    4: (sc_quad, "QUAD: CRITICAL MINERALS", "tl", None, None),
    5: (sc_measles, "MEASLES: STATUS LOST", "tl", "US - MEXICO - BOLIVIA", "br"),
    6: (sc_alaska, "PELTOLA WINS", "tl", None, None),
    7: (sc_serbia, "STUDENT LIST: 140 OF 250", "tl", None, None),
    8: (sc_plane, "19 KILLED", "tl", None, None),
    9: (sc_bangladesh, "WAGE PROTEST", "tr", None, None),
    10: (sc_mongolia, "PRESIDENT RESIGNS", "tl", None, None),
    11: (sc_haiti, "MARCH FOR SALVADORAN TROOPS", "tl", None, None),
    12: (sc_court, "OPPOSITION LEADER ON TRIAL", "tl", None, None),
}


def draw_plate(im, w, h, text, pos, px):
    c = Cv(im, 1.0)
    f = font("sb", px)
    tww = f.getlength(text) / S
    pw, ph = tww + 10, px + 5
    assert pw <= w - 8, ("plate too wide", text, pw, w)
    x = 4 if pos[1] == "l" else w - 4 - pw
    y = 4 if pos[0] == "t" else h - 4 - ph
    c.rrect(x, y, x + pw, y + ph, 3, "#fffaf0", "#17130e", 1.2)
    c.d.text(((x + 5) * S, (y + ph / 2) * S + 1), text, font=f, fill="#17130e", anchor="lm")
    CHECKS.append(("plate:" + text, (x, y, x + pw, y + ph), (0, 0, w, h)))  # panel-local coordinates


def make_panel(story, w, h, k_plate_px):
    im = Image.new("RGB", (round(w * S), round(h * S)), "#ffffff")
    k = h / 92.0
    c = Cv(im, k, 0, -8 * k)
    fn, p1, pos1, p2, pos2 = SCENES[story["id"]]
    fn(c, w / k)
    draw_plate(im, w, h, p1, pos1, k_plate_px)
    if p2:
        draw_plate(im, w, h, p2, pos2, k_plate_px)
    return im


# ---------------------------------------------------------------- text fitting
def wrap(text, fname, px, width):
    words = text.split()
    lines, cur = [], ""
    for wd in words:
        t = (cur + " " + wd).strip()
        if tw(fname, px, t) <= width or not cur:
            cur = t
        else:
            lines.append(cur)
            cur = wd
    if cur:
        lines.append(cur)
    return lines


def fit_head(text, width, sizes, maxlines, fname="gb"):
    for px in sizes:
        lines = wrap(text, fname, px, width)
        if len(lines) <= maxlines and all(tw(fname, px, l) <= width for l in lines):
            return px, lines
    raise AssertionError(("headline cannot fit", text, width, sizes[-1], maxlines))


def fit_sub(text, width, sizes, room):
    """Largest size whose whole text fits `room` px of height; else the leading whole sentences;
    else nothing. Returns (px, lines); lines == [] drops the sub line (the headline stays)."""
    sents = [text[:i + 1] for i, ch in enumerate(text) if ch == "." and (i + 1 == len(text) or text[i + 1] == " ")]
    for cand in [text] + list(reversed(sents[:-1])):
        for px in sizes:
            ml = int(room // (px * 1.17))
            if ml >= 1:
                lines = wrap(cand, "s", px, width)
                if len(lines) <= ml:
                    return px, lines
    return sizes[-1], []


SUBLOG = []


# ---------------------------------------------------------------- map
MAPBOX = (-170.0, -58.0, 180.0, 78.0)  # lon0, lat0, lon1, lat1
LAND = {
    "na": [(-168, 66), (-157, 71), (-140, 70), (-120, 70), (-95, 72), (-82, 70), (-78, 62), (-90, 58), (-94, 60), (-82, 52), (-78, 56), (-70, 60), (-62, 58), (-56, 52), (-66, 45), (-70, 42), (-75, 38), (-76, 35), (-81, 31), (-80, 25), (-83, 29), (-89, 30), (-94, 29), (-97, 26), (-97, 21), (-92, 18), (-90, 21), (-87, 21), (-88, 16), (-83, 15), (-83, 10), (-78, 8), (-80, 7), (-86, 11), (-92, 14), (-97, 16), (-105, 20), (-110, 24), (-112, 29), (-117, 33), (-121, 35), (-124, 40), (-124, 47), (-128, 51), (-134, 58), (-140, 60), (-150, 60), (-155, 57), (-162, 55), (-165, 60)],
    "gl": [(-55, 60), (-45, 60), (-20, 70), (-20, 78), (-60, 78), (-72, 76), (-58, 70)],
    "sa": [(-80, 8), (-72, 12), (-62, 10), (-52, 5), (-50, 0), (-35, -6), (-39, -14), (-41, -22), (-48, -26), (-54, -34), (-58, -38), (-65, -41), (-66, -47), (-69, -52), (-72, -54), (-75, -50), (-73, -40), (-71, -30), (-70, -18), (-76, -14), (-81, -5), (-80, -1), (-77, 4)],
    "eu": [(-10, 36), (-9, 43), (-2, 44), (-5, 48), (2, 51), (5, 54), (8, 57), (11, 56), (12, 54), (20, 55), (24, 59), (30, 60), (22, 66), (28, 70), (40, 67), (60, 70), (80, 73), (100, 77), (115, 74), (140, 72), (160, 70), (180, 68), (180, 65), (170, 60), (160, 58), (156, 51), (142, 55), (140, 48), (135, 43), (129, 41), (129, 35), (126, 35), (125, 40), (121, 40), (122, 37), (118, 38), (121, 31), (120, 26), (110, 21), (108, 16), (109, 11), (105, 9), (101, 13), (100, 8), (103, 1.3), (100, 6), (98, 10), (98, 16), (94, 17), (92, 22), (88, 22), (80, 15), (77, 8), (73, 16), (72, 21), (67, 24), (62, 25), (57, 26), (56, 24), (51, 25), (48, 30), (50, 26), (56, 24), (58, 22), (52, 16), (45, 13), (43, 15), (39, 22), (35, 28), (34, 31), (36, 36), (30, 36), (27, 37), (26, 40), (23, 40), (24, 37), (22, 36), (20, 40), (16, 38), (12, 42), (8, 44), (3, 43), (-2, 37)],
    "af": [(-17, 21), (-13, 28), (-6, 36), (10, 37), (11, 33), (20, 32), (32, 31), (33, 27), (37, 21), (43, 12), (51, 12), (44, 0), (40, -8), (40, -16), (35, -24), (32, -29), (27, -34), (19, -35), (15, -27), (12, -17), (13, -8), (9, -1), (9, 4), (5, 5), (-8, 4), (-13, 8), (-17, 14)],
    "mg": [(44, -25), (48, -14), (50, -15), (47, -25)],
    "au": [(114, -22), (122, -18), (130, -12), (136, -12), (142, -11), (146, -19), (153, -26), (150, -37), (141, -38), (135, -34), (129, -31), (115, -34)],
    "nz": [(172, -35), (178, -38), (175, -41), (172, -43), (168, -46), (171, -41)],
    "jp": [(130, 31), (135, 34), (140, 36), (142, 40), (141, 45), (145, 44), (140, 41), (136, 37)],
    "ph": [(120, 18), (122, 18), (125, 12), (126, 7), (122, 7), (120, 13)],
    "su": [(95, 5), (104, -2), (106, -6), (100, -2)],
    "bo": [(109, 2), (117, 7), (119, 1), (116, -4), (110, -3)],
    "jv": [(105, -6), (114, -8), (106, -7)],
    "uk": [(-5, 50), (1, 51), (2, 53), (-2, 56), (-3, 58), (-6, 58), (-5, 54), (-3, 53)],
    "ie": [(-10, 52), (-6, 52), (-6, 55), (-9, 54)],
    "ic": [(-24, 64), (-14, 64), (-14, 66), (-22, 66)],
}


def proj(lon, lat, box):
    x0, y0, x1, y1 = box
    lo0, la0, lo1, la1 = MAPBOX
    return x0 + (lon - lo0) / (lo1 - lo0) * (x1 - x0), y0 + (la1 - lat) / (la1 - la0) * (y1 - y0)


# ---------------------------------------------------------------- main render
def render():
    CHECKS.clear()
    SUBLOG.clear()
    rows = load()
    ids = [r["id"] for r in rows]
    assert len(ids) == len(set(ids)), "ids not unique"
    leads = sorted([r for r in rows if r["lead"]], key=lambda r: r["id"])
    briefs = sorted([r for r in rows if not r["lead"]], key=lambda r: r["id"])
    N = len(rows)
    conts = {CONT[r["region"]] for r in rows if r.get("pin")}
    C = len(conts)
    F = len({r["field"] for r in rows})
    assert len(leads) == 12
    regcount = {k: sum(1 for r in rows if r["region"] == k) for k in REG_ORDER}
    assert sum(regcount.values()) == N

    im = Image.new("RGB", (W * S, H * S), PAPER)
    c = Cv(im, 1.0)
    M = 24
    CW = W - 2 * M
    PAGE = (0, 0, W, H)

    def put(label, s, fname, px, x, y, anchor="la", box=None):
        """draw text and register bbox against page or given container"""
        f = font(fname, px)
        c.d.text((x * S, y * S), s, font=f, fill=put.fill, anchor=anchor)
        b = c.d.textbbox((x * S, y * S), s, font=f, anchor=anchor)
        CHECKS.append((label, (b[0] / S, b[1] / S, b[2] / S, b[3] / S), box or PAGE))
        return b[2] / S - b[0] / S
    put.fill = INK

    # ---- masthead
    c.rect(M, 8, W - M, 10, INK)
    kick = "THE DAY'S WORLD NEWS IN ONE PICTURE"
    x = M
    put.fill = SOFT
    kf = font("sb", 12)
    track = 1.6
    for ch in kick:
        c.d.text((x * S, 13 * S), ch, font=kf, fill=SOFT)
        x += kf.getlength(ch) / S + track
    CHECKS.append(("kicker", (M, 13, x, 28), (M, 0, W - M, 34)))
    put.fill = INK
    hl = "Tuesday 17 November 2026"
    hp = 40
    while tw("gb", hp + 1, hl) <= CW:
        hp += 1
    put("headline-date", hl, "gb", hp, M - 1, 19, "la", (M - 2, 0, W - M + 2, 110))
    rowy = int(19 + hp * 1.07) + 5
    # legend (full width) ; count line shares the kicker row on the right
    lx = M
    for rg in REG_ORDER:
        c.rect(lx, rowy + 3, lx + 10, rowy + 13, REG[rg])
        lab = f"{rg} {regcount[rg]}"
        put.fill = INK
        wlab = put("legend " + rg, lab, "sb", 12, lx + 14, rowy, "la", (M, rowy - 2, W - M, rowy + 20))
        lx += 14 + wlab + 14
    assert lx - 14 <= W - M, ("legend too wide", lx)
    cnt = f"{N} stories · {C} continents · {F} fields · all from Tuesday"
    put.fill = INK
    put("count line", cnt, "sb", 14.5, W - M, 11, "ra", (M, 0, W, 34))
    # tally bar
    by = rowy + 17
    bx = M
    for rg in REG_ORDER:
        wseg = CW * regcount[rg] / N
        c.rect(bx, by, bx + wseg - 1.5, by + 7, REG[rg])
        bx += wseg
    c.rect(M, by + 10, W - M, by + 11, INK)
    top_tiles = by + 15

    # ---- footer
    foot = "Every story happened or was first reported on Tuesday 17 November 2026; disputed claims are attributed. Sources: BBC, AP, Al Jazeera and others. Original drawings."
    fpx = 11.5
    while tw("s", fpx, foot) > CW and fpx > 9:
        fpx -= 0.25
    c.rect(M, H - 22, W - M, H - 21, INK)
    put.fill = SOFT
    put("footer", foot, "s", fpx, W / 2, H - 19, "ma", (M, H - 22, W - M, H))

    # ---- bottom band geometry: map + field list (left), briefs in two columns (right)
    BPX = 12
    ROWH = 13.6
    nrows = (len(briefs) + 1) // 2
    maxw = max(tw("s", BPX, b_["head"]) for b_ in briefs)
    colw = 19 + maxw + 8
    map_w = CW - 2 * colw - 16
    assert map_w >= 280, ("map too small", map_w)
    band_h = 18 + nrows * ROWH + 4
    band_top = H - 24 - band_h
    c.rect(M, band_top - 4, W - M, band_top - 3, INK)

    # ---- tiles
    G = 6
    tw_ = (CW - 2 * G) / 3
    big_h = 170
    avail = band_top - 9 - top_tiles - big_h - 3 * G
    small_h = avail / 3
    for i, st in enumerate(leads):
        if i < 3:
            col, row, th = i, 0, big_h
            y0 = top_tiles
        else:
            col, row, th = (i - 3) % 3, 1 + (i - 3) // 3, small_h
            y0 = top_tiles + big_h + G + (row - 1) * (small_h + G)
        x0 = M + col * (tw_ + G)
        big = i < 3
        reg = REG[st["region"]]
        tile = (x0, y0, x0 + tw_, y0 + th)
        # panel
        SH = 17 if big else 16
        ph = 74 if big else 68
        pimg = make_panel(st, round(tw_), ph, 12)
        im.paste(pimg, (round(x0 * S), round(y0 * S)))
        c.rect(x0, y0 + ph, x0 + tw_, y0 + ph + SH, reg)
        c.rect(x0, y0, x0 + tw_, y0 + th, None, "#a99d82", 0.8)
        # number badge + label strip
        br = 7.2
        c.circ(x0 + 6 + br, y0 + ph + SH / 2, br, "#ffffff")
        put.fill = reg
        put(f"badge {st['id']}", str(st["id"]), "sb", 11.5, x0 + 6 + br, y0 + ph + SH / 2 + 0.5, "mm", tile)
        put.fill = "#ffffff"
        lab = f"{st['region'].upper()} · {st['beat']}"
        put(f"label {st['id']}", lab, "sb", 11, x0 + 6 + 2 * br + 6, y0 + ph + SH / 2 + 0.5, "lm", tile)
        ty_ = y0 + ph + SH + 3
        # headline (whole, wrapped by words, never truncated)
        inner = tw_ - 12
        if big:
            try:
                hpx, hlines = fit_head(st["head"], inner, [21, 20, 19, 18, 17.5, 17], 2)
            except AssertionError:
                hpx, hlines = fit_head(st["head"], inner, [19, 18, 17.5, 17], 3)
        else:
            hpx, hlines = fit_head(st["head"], inner, [15, 14.5, 14], 2)
        lh = hpx * 1.1
        put.fill = INK
        for j, ln in enumerate(hlines):
            put(f"head {st['id']}.{j}", ln, "gb", hpx, x0 + 6, ty_ + j * lh, "la", tile)
        ty_ += len(hlines) * lh + 1.5
        # sub: whole text, else leading whole sentences, else dropped (never an ellipsis, never < 10.5 px)
        sp, slines = fit_sub(st["sub"], inner, [11.5, 11, 10.5], (y0 + th - 2.5) - ty_)
        put.fill = SOFT
        for j, ln in enumerate(slines):
            put(f"sub {st['id']}.{j}", ln, "s", sp, x0 + 6, ty_ + j * sp * 1.17, "la", tile)
        SUBLOG.append((st["id"], len(slines)))

    # ---- map
    put.fill = INK
    box = (M, band_top + 18, M + map_w, band_top + 18 + map_w * (MAPBOX[3] - MAPBOX[1]) / (MAPBOX[2] - MAPBOX[0]))
    put("map title", "WHERE IT HAPPENED", "sb", 12, M, band_top, "la", (M, band_top - 3, M + map_w, band_top + 16))
    c.rect(M + 150, band_top + 7, M + map_w, band_top + 8, "#a99d82")
    c.rect(*box, "#dfe8e6", "#8c8068", 0.8)
    mb = box
    for nm, pts in LAND.items():
        c.d.polygon([(proj(lo, la, mb)[0] * S, proj(lo, la, mb)[1] * S) for lo, la in pts], fill="#cbc09f", outline="#9d9172")
    for lon in (-120, -60, 0, 60, 120):
        px_, _ = proj(lon, 0, mb)
        c.line([(px_, mb[1]), (px_, mb[3])], "#cfd9d6", 0.5)
    pins = {}
    for rr in rows:
        lon, lat = rr["pin"]
        assert MAPBOX[0] <= lon <= MAPBOX[2] and MAPBOX[1] <= lat <= MAPBOX[3], ("pin outside map", rr["id"])
        pins[rr["id"]] = proj(lon, lat, mb)
    # briefs are dots; nudge a dot away only where it would hide under another marker
    LEADR = 7.2
    lead_pts = [pins[r_["id"]] for r_ in leads]
    dots = []
    for rr in briefs:
        ox_, oy_ = pins[rr["id"]]
        x_, y_ = ox_, oy_
        for step in range(60):
            if all(math.hypot(x_ - qx, y_ - qy) >= LEADR + 3.4 for qx, qy in lead_pts) and \
               all(math.hypot(x_ - qx, y_ - qy) >= 6.6 for qx, qy in dots):
                break
            ang = math.radians(137.5 * (step + 1) + rr["id"] * 40)
            x_ = ox_ + 0.5 * (step + 1) * math.cos(ang)
            y_ = oy_ + 0.5 * (step + 1) * math.sin(ang)
        x_ = min(max(x_, mb[0] + 4), mb[2] - 4)
        y_ = min(max(y_, mb[1] + 4), mb[3] - 4)
        pins[rr["id"]] = (x_, y_)
        dots.append((x_, y_))
        c.circ(x_, y_, 3.0, REG[rr["region"]], "#ffffff", 0.8)
    for rr in leads:
        x_, y_ = pins[rr["id"]]
        c.circ(x_, y_, LEADR, REG[rr["region"]], "#ffffff", 1.2)
        put.fill = "#ffffff"
        put(f"pin {rr['id']}", str(rr["id"]), "sb", 10, x_, y_ + 0.4, "mm", mb)
    ky = box[3] + 5
    put.fill = SOFT
    n1, n2 = briefs[0]["id"], briefs[-1]["id"]
    notes = wrap(f"Numbered circle = lead story, same number as its tile. Small dot = brief ({n1}-{n2}), listed at right. Colour = region.", "s", 12, map_w)
    for j, ln in enumerate(notes):
        put(f"map note {j}", ln, "s", 12, M, ky + j * 14, "la", (M, ky - 2, M + map_w + 2, ky + 14 * (j + 1) + 2))
    fy = ky + 14 * len(notes) + 8
    # fields tally
    fcount = {}
    for r_ in rows:
        fcount[r_["field"]] = fcount.get(r_["field"], 0) + 1
    put.fill = INK
    put("fields title", "STORIES BY FIELD", "sb", 12, M, fy, "la", (M, fy - 2, M + map_w, fy + 16))
    c.rect(M + 112, fy + 7, M + map_w, fy + 8, "#a99d82")
    fx, fy2 = M, fy + 17
    put.fill = SOFT
    for fld, n_ in sorted(fcount.items(), key=lambda kv: (-kv[1], kv[0])):
        item = f"{fld} {n_}"
        iw = tw("s", 12, item)
        if fx + iw > M + map_w:
            fx, fy2 = M, fy2 + 14
        put(f"field {fld}", item, "s", 12, fx, fy2, "la", (M, fy - 2, M + map_w + 2, band_top + band_h))
        fx += iw + 11
    # ---- briefs
    rx = M + map_w + 16
    put.fill = INK
    put("briefs title", "ALSO ON TUESDAY 17 NOVEMBER", "sb", 12, rx, band_top, "la", (rx, band_top - 3, W - M, band_top + 16))
    c.rect(rx + 215, band_top + 7, W - M, band_top + 8, "#a99d82")
    for i, b in enumerate(briefs):
        colx = rx + (i // nrows) * colw
        yy = band_top + 18 + (i % nrows) * ROWH
        put.fill = REG[b["region"]]
        put(f"brief num {b['id']}", str(b["id"]), "sb", BPX, colx, yy, "la", (colx, yy - 1.5, colx + colw, yy + ROWH + 3.5))
        put.fill = INK
        put(f"brief {b['id']}", b["head"], "s", BPX, colx + 19, yy, "la", (colx, yy - 1.5, colx + colw - 2, yy + ROWH + 3.5))
    return im, dict(N=N, C=C, F=F, leads=len(leads), briefs=len(briefs), rows=rows)


def self_check(info):
    # header count equals items drawn
    assert info["N"] == info["leads"] + info["briefs"], "header count != items drawn"
    for label, (x0, y0, x1, y1), (cx0, cy0, cx1, cy1) in CHECKS:
        assert x0 >= cx0 - 0.6 and y0 >= cy0 - 0.6 and x1 <= cx1 + 0.6 and y1 <= cy1 + 0.6, \
            ("text exceeds container", label, (round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)), (cx0, cy0, cx1, cy1))
    # no two text boxes overlap
    boxes = [(l, b) for l, b, _ in CHECKS if not l.startswith("plate:")]
    for i in range(len(boxes)):
        for j in range(i + 1, len(boxes)):
            (la, a), (lb, b) = boxes[i], boxes[j]
            ox = min(a[2], b[2]) - max(a[0], b[0])
            oy = min(a[3], b[3]) - max(a[1], b[1])
            assert not (ox > 0.4 and oy > 0.4), ("text boxes overlap", la, lb)
    return len(CHECKS)


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), "entry.png")
    im, info = render()
    n = self_check(info)
    small = im.resize((W, H), Image.LANCZOS)
    pal = small.quantize(colors=256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)
    pal.save(out, format="PNG", optimize=True)
    print(f"ok: {info['N']} stories, {info['C']} continents, {n} text boxes checked -> {out} ({os.path.getsize(out)} bytes)")


if __name__ == "__main__":
    main()
