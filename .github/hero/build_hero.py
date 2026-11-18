"""Draws the profile art. The hero is an isometric city built from the public contribution calendar."""
import datetime as dt, html, math, pathlib, random, re, sys, urllib.request
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

USER = "nosherwan537"
HERE = pathlib.Path(__file__).resolve().parent
ASSETS = HERE.parent.parent / "assets"

# tokens
INK, BONE, MUTED, ACCENT = "#0A0D0C", "#F1EADB", "#A9A99B", "#FF6A3D"
HAIR, GRID, WARM, DIM_WIN = "#232A27", "#151C19", "#FFD9A8", "#6A5A42"
LOT, ROAD, PALM, FROND = "#111815", "#141B18", "#26362F", "#39524A"
W, H, M = 1200, 780, 64
A, B, OX, OY = 20.6, 9.9, -70, 730
LOOP = 24
C0, C1 = -10, 64


class Face:
    def __init__(self, name):
        p = HERE / "fonts" / name
        self.tt = TTFont(p)
        self.gs = self.tt.getGlyphSet()
        self.upem = self.tt["head"].unitsPerEm
        self.order = self.tt.getGlyphOrder()
        self.hb = hb.Font(hb.Face(hb.Blob.from_file_path(str(p))))

    def shape(self, s):
        b = hb.Buffer(); b.add_str(s); b.guess_segment_properties()
        hb.shape(self.hb, b, {"kern": True, "liga": True})
        return b.glyph_infos, b.glyph_positions

    def width(self, s, size, track=0):
        _, pos = self.shape(s)
        return sum(p.x_advance for p in pos) * size / self.upem + track * (len(pos) - 1)

    def path(self, s, size, x, y, track=0):
        k = size / self.upem
        pen = SVGPathPen(self.gs, ntos=lambda v: f"{v:.1f}".rstrip("0").rstrip("."))
        infos, pos = self.shape(s)
        for i, p in zip(infos, pos):
            self.gs[self.order[i.codepoint]].draw(TransformPen(pen, (k, 0, 0, -k, x + p.x_offset * k, y - p.y_offset * k)))
            x += p.x_advance * k + track
        return pen.getCommands()


SERIF = Face("fraunces-latin-300-normal.ttf")
ITALIC = Face("fraunces-latin-300-italic.ttf")
MONO = Face("ibm-plex-mono-latin-400-normal.ttf")
MONO5 = Face("ibm-plex-mono-latin-500-normal.ttf")


def text(s, face, size, x, y, fill=BONE, anchor="start", track=0):
    w = face.width(s, size, track)
    x -= {"start": 0, "middle": w / 2, "end": w}[anchor]
    return f'<path fill="{fill}" d="{face.path(s, size, x, y, track)}"/>'


def mix(a, b, t):
    pa, pb = [[int(h[i:i + 2], 16) for i in (1, 3, 5)] for h in (a, b)]
    return "#" + "".join(f"{round(x + (y - x) * t):02X}" for x, y in zip(pa, pb))


def poly(pts, fill, extra=""):
    return f'<path d="M' + "L".join(f"{x:.1f} {y:.1f}" for x, y in pts) + f'Z" fill="{fill}"{extra}/>'


class Iso:
    def lit(self, c, r, w, d, h, seed):
        rr, o = random.Random(seed), ""
        for row in range(int((h - 10) // 11)):
            z = 7 + row * 11
            for s0 in (.14, .42, .7):
                if rr.random() < .62:
                    x, y = self.p(c, r + d * s0, z)
                    k = d * .17
                    o += f"M{x:.1f} {y:.1f}l{self.a * k:.1f} {self.b * k:.1f}v-5.5l{-self.a * k:.1f} {-self.b * k:.1f}z"
                if rr.random() < .62:
                    x, y = self.p(c + w * s0, r + d, z)
                    k = w * .17
                    o += f"M{x:.1f} {y:.1f}l{self.a * k:.1f} {-self.b * k:.1f}v-5.5l{-self.a * k:.1f} {self.b * k:.1f}z"
        return f'<path d="{o}" fill="{WARM}"/>'

    def tower(self, c, r, w, d, h, top, left, right, seed):
        return self.box(c, r, w, d, 0, h, top, left, right) + self.lit(c, r, w, d, h, seed)

    def __init__(self, ox, oy, a, b):
        self.ox, self.oy, self.a, self.b = ox, oy, a, b

    def p(self, c, r, z=0):
        return self.ox + (c + r) * self.a, self.oy - (c - r) * self.b - z

    def box(self, c, r, w, d, z0, h, top, left, right):
        p = self.p
        z1 = z0 + h
        out = [poly([p(c, r, z0), p(c, r + d, z0), p(c, r + d, z1), p(c, r, z1)], left),
               poly([p(c, r + d, z0), p(c + w, r + d, z0), p(c + w, r + d, z1), p(c, r + d, z1)], right),
               poly([p(c, r, z1), p(c, r + d, z1), p(c + w, r + d, z1), p(c + w, r, z1)], top)]
        return "".join(out)


def fetch_days():
    req = urllib.request.Request(f"https://github.com/users/{USER}/contributions", headers={"User-Agent": "profile-hero"})
    page = urllib.request.urlopen(req, timeout=30).read().decode()
    ids = {b: a for a, b in re.findall(r'id="([^"]+)"[^>]*data-date="([\d-]+)"', page)} or dict(
        re.findall(r'data-date="([\d-]+)"[^>]*id="([^"]+)"', page))
    tips = dict(re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>(.*?)</tool-tip>', page, re.S))
    days = {}
    for d, i in ids.items():
        m = re.match(r"\s*(\d+) contribution", tips.get(i, ""))
        days[dt.date.fromisoformat(d)] = int(m[1]) if m else 0
    heading = re.search(r"([\d,]+)\s+contributions?\s+in the last year", page)
    if len(days) < 360 or not sum(days.values()) or not heading or int(heading[1].replace(",", "")) != sum(days.values()):
        sys.exit("Calendar did not parse cleanly, keeping the current hero.")
    return days


days = fetch_days()
start = min(days)
end = max(days)
total = sum(days.values())
top = max(days.values())
recent = sum(c for d, c in days.items() if (end - d).days < 7)
heat = sum(recent >= t for t in (1, 10, 25, 50, 100))
cells = {((d - start).days // 7, (d.weekday() + 1) % 7): c for d, c in days.items()}
weeks = max(c for c, _ in cells) + 1
city = Iso(OX, OY, A, B)
P = city.p
when = lambda c: .1 + .8 * (c - C0) / (C1 - C0)
height = lambda n: 14 + math.sqrt(n / top) * 132

# ---------- backdrop ----------
b = []
rs = random.Random(5)
b.append("".join(f'<circle cx="{rs.uniform(0, W):.0f}" cy="{rs.uniform(0, 330):.0f}" r="{rs.choice((1, 1, 1.5))}" fill="{BONE}" opacity="{rs.uniform(.15, .5):.2f}"/>' for _ in range(70)))
grid = "".join(f"M{P(c, -30)[0]:.0f} {P(c, -30)[1]:.0f}L{P(c, 40)[0]:.0f} {P(c, 40)[1]:.0f}" for c in range(-20, 90, 4))
grid += "".join(f"M{P(-30, r)[0]:.0f} {P(-30, r)[1]:.0f}L{P(90, r)[0]:.0f} {P(90, r)[1]:.0f}" for r in range(-40, 44, 4))
b.append(f'<path d="{grid}" stroke="{GRID}" stroke-width="1.5" fill="none"/>')
b.append(f'<circle cx="930" cy="205" r="150" fill="url(#sun)"/>')

# ---------- city: one building per day, painted back to front ----------
defs, city_parts, tops = [], [], {}
for (c, r), n in sorted(cells.items(), key=lambda kv: (-(kv[0][0] - kv[0][1]), kv[0][0])):
    x, y, s = c + .1, r + .1, .8
    if not n:
        city_parts.append(poly([P(x, y), P(x, y + s), P(x + s, y + s), P(x + s, y)], LOT))
        continue
    h = height(n)
    t = math.sqrt(n / top)
    roof = ACCENT if n >= top * .45 else mix("#25332D", "#7C8A7E", t)
    city_parts.append(city.box(x, y, s, s, 0, h, roof, mix("#111A17", "#1B2925", t), mix("#1D1613", "#4A2719", t)))
    tops[(c, r)] = (P(x + s / 2, y + s / 2, h), h)
    rr = random.Random(f"{start + dt.timedelta(days=c * 7 + r)}")
    d = ""
    for row in range(int((h - 8) // 9)):
        z = 5 + row * 9
        for s0 in (.16, .54):
            if rr.random() < .6:  # left face
                q = P(x, y + s * s0, z)
                d += f"M{q[0]:.1f} {q[1]:.1f}l{A * s * .22:.1f} {B * s * .22:.1f}v-4.5l{-A * s * .22:.1f} {-B * s * .22:.1f}z"
            if rr.random() < .6:  # right face
                q = P(x + s * s0, y + s, z)
                d += f"M{q[0]:.1f} {q[1]:.1f}l{A * s * .22:.1f} {-B * s * .22:.1f}v-4.5l{-A * s * .22:.1f} {B * s * .22:.1f}z"
    if d:
        wid = f"w{c}_{r}"
        f = when(c + .5)
        defs.append(f'<path id="{wid}" d="{d}"/>')
        city_parts.append(f'<use href="#{wid}" fill="{DIM_WIN}"/><use class="m" href="#{wid}" fill="{WARM}" opacity="0">'
                          f'<animate attributeName="opacity" dur="{LOOP}s" repeatCount="indefinite" keyTimes="0;{f:.4f};{f + .004:.4f};.96;1" values="0;0;1;1;0"/></use>')
b += city_parts

# ---------- avenue ----------
b.append(poly([P(C0, 7.2), P(C0, 8.8), P(C1, 8.8), P(C1, 7.2)], ROAD))
for r in (7.2, 8.8):
    a1, a2 = P(C0, r), P(C1, r)
    b.append(f'<path d="M{a1[0]:.1f} {a1[1]:.1f}L{a2[0]:.1f} {a2[1]:.1f}" stroke="{BONE}" stroke-opacity=".28" stroke-width="1.5"/>')
a1, a2 = P(C0, 8), P(C1, 8)
b.append(f'<path d="M{a1[0]:.1f} {a1[1]:.1f}L{a2[0]:.1f} {a2[1]:.1f}" stroke="{BONE}" stroke-opacity=".3" stroke-width="2" stroke-dasharray="14 16"/>')


def car(iso, tint=1):
    q = lambda c, r, z=0: (( c + r) * iso.a, -(c - r) * iso.b - z)
    beam = poly([q(1.05, -.32), q(5.4, -1.0), q(5.4, 1.0), q(1.05, .32)], "url(#beam)")
    box = lambda c0, c1, r0, r1, z0, z1, t, l, s: (
        poly([q(c0, r0, z0), q(c0, r1, z0), q(c0, r1, z1), q(c0, r0, z1)], l)
        + poly([q(c0, r1, z0), q(c1, r1, z0), q(c1, r1, z1), q(c0, r1, z1)], s)
        + poly([q(c0, r0, z1), q(c0, r1, z1), q(c1, r1, z1), q(c1, r0, z1)], t))
    tail = poly([q(-1.05, .05, 4), q(-1.05, .3, 4), q(-1.05, .3, 6.5), q(-1.05, .05, 6.5)], ACCENT)
    tail2 = poly([q(-1.05, -.3, 4), q(-1.05, -.05, 4), q(-1.05, -.05, 6.5), q(-1.05, -.3, 6.5)], ACCENT)
    wheels = "".join(f'<ellipse cx="{q(w, .4, 2.6)[0]:.1f}" cy="{q(w, .4, 2.6)[1]:.1f}" rx="3.4" ry="2.8" fill="{INK}"/>' for w in (-.62, .62))
    return (beam + box(-1.05, 1.05, -.4, .4, 1.5, 7.5, BONE, "#A9A394", "#D3CCBC") + tail + tail2 + wheels
            + box(-.5, .42, -.32, .32, 7.5, 12.5, BONE, "#1B2522", "#26332E"))


small = (f'<rect x="-8" y="-5" width="16" height="6" rx="2" fill="#3C4A44"/><circle cx="-8" cy="-1" r="1.8" fill="{WARM}"/>'
         f'<circle cx="-4" cy="1" r="1.8" fill="{WARM}"/>')
for dur, off in ((15, 0), (21, -8), (27, -17)):
    s, e = P(C1, 7.6, 0), P(C0, 7.6, 0)
    b.append(f'<g class="m"><g>{small}<animateMotion dur="{dur}s" begin="{off}s" repeatCount="indefinite" path="M{s[0]:.1f} {s[1]:.1f}L{e[0]:.1f} {e[1]:.1f}"/></g></g>')
s, e = P(C0, 8.42), P(C1, 8.42)
b.append(f'<g class="m"><g>{car(city)}<animateMotion dur="{LOOP}s" repeatCount="indefinite" calcMode="linear" keyPoints="0;0;1;1" '
         f'keyTimes="0;.1;.9;1" path="M{s[0]:.1f} {s[1]:.1f}L{e[0]:.1f} {e[1]:.1f}"/></g></g>')
q = P(25, 8.42)
b.append(f'<g class="s" transform="translate({q[0]:.1f} {q[1]:.1f})">{car(city)}</g>')


def palm(x, y, h, lean=8):
    tx, ty = x + lean, y - h
    fr = ""
    for dx, dy in ((-30, 7), (-23, -10), (-7, -18), (11, -17), (25, -8), (31, 8)):
        cx, cy = tx + dx * .55, ty + dy - 8
        fr += f"M{tx:.1f} {ty:.1f}Q{cx:.1f} {cy:.1f} {tx + dx:.1f} {ty + dy + 11:.1f}Q{cx:.1f} {cy + 7:.1f} {tx:.1f} {ty:.1f}Z"
    return (f'<path d="M{x - 2.5:.1f} {y:.1f}Q{x + lean * .2:.1f} {y - h * .55:.1f} {tx - 1:.1f} {ty:.1f}h2'
            f'Q{x + 3.5 + lean * .25:.1f} {y - h * .5:.1f} {x + 3:.1f} {y:.1f}Z" fill="{PALM}"/><path d="{fr}" fill="{FROND}"/>')


for c in range(-2, 52, 7):
    x, y = P(c, 9.5)
    b.append(palm(x, y, 56 + (c % 3) * 6, 8 if c % 2 else -7))

# ---------- project locations on the map ----------
places = [("1", "NPC_AWARE", 4, 11), ("2", "npm-guardian", 13, 19), ("3", "Wait a Minute", 21, 26),
          ("4", "Hope in Roman Urdu", 28, 33), ("5", "githide", 35, 41)]
for num, name, c0, c1 in places:
    opts = [(k, v) for k, v in tops.items() if c0 <= k[0] <= c1 and k[1] <= 2]
    (k, ((x, y), h)) = max(opts, key=lambda kv: kv[1][1]) if opts else (None, (P((c0 + c1) / 2, 1, 14), 14))
    ty = y - 46
    w = MONO5.width(name, 21) + 54
    lx = min(x - 14, W - M - w)
    b.append(f'<path d="M{x:.1f} {y:.1f}V{ty:.1f}" stroke="{ACCENT}" stroke-width="1.5"/><circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{ACCENT}"/>'
             f'<rect x="{lx:.1f}" y="{ty - 32:.1f}" width="{w:.1f}" height="32" rx="4" fill="{INK}" stroke="{HAIR}"/>'
             f'<circle cx="{lx + 17:.1f}" cy="{ty - 16:.1f}" r="10" fill="{ACCENT}"/>'
             + text(num, MONO5, 15, lx + 17, ty - 11, INK, "middle") + text(name, MONO5, 21, lx + 36, ty - 9))

# ---------- title ----------
size = 100 * 660 / SERIF.width("Nosherwan", 100)
b += [text("Nosherwan", SERIF, size, M - 3, 150),
      text("AI and Web Engineer", ITALIC, 46, M, 214),
      text("Local AI. Real-time systems.", MONO, 22, M, 256, MUTED)]

# ---------- HUD ----------
hx = W - M - 424
b.append(text("HEAT", MONO5, 22, hx, 612, MUTED, track=3))
b.append("".join(f'<path d="M{hx + 78 + i * 22} 596l12 9l-12 9h-8l12 -9l-12 -9z" fill="{ACCENT if i < heat else HAIR}"/>' for i in range(5)))
times, scores = [0.0], [0]
for c in range(weeks):
    times.append(when(c + .5))
    scores.append(sum(n for (k, _), n in cells.items() if k <= c))
scores[-1] = total
times.append(1.0); scores.append(total)
kt = ";".join(f"{t:.4f}" for t in times)
digits = f"{total}"
fs, lh = 56, 72
cw = MONO5.width("0", fs)
defs += [f'<path id="n{d}" d="{MONO5.path(str(d), fs, 0, 0)}"/>' for d in range(10)]
x, score, final = hx, [], []
for i, ch in enumerate(digits):
    place = 10 ** (len(digits) - 1 - i)
    vals = ";".join(f"0 {-(v // place % 10) * lh}" for v in scores)
    strip = "".join(f'<use href="#n{d}" y="{d * lh}"/>' for d in range(10))
    score.append(f'<g transform="translate({x:.1f} 672)" clip-path="url(#dc)"><g fill="{BONE}">{strip}'
                 f'<animateTransform attributeName="transform" type="translate" calcMode="discrete" dur="{LOOP}s" repeatCount="indefinite" keyTimes="{kt}" values="{vals}"/></g></g>')
    final.append(text(ch, MONO5, fs, x, 672))
    x += cw
    if len(digits) - 1 - i == 3:
        comma = text(",", MONO5, fs, x - 6, 672, MUTED)
        score.append(comma); final.append(comma)
        x += cw * .62
b += [f'<g class="m">{"".join(score)}</g><g class="s">{"".join(final)}</g>',
      text("contributions", MONO, 22, x + 16, 650, BONE), text("last 12 months", MONO, 22, x + 16, 676, MUTED)]
for (c, r), n in cells.items():
    t = math.sqrt(n / top) if n else 0
    fill = ACCENT if n >= top * .45 else mix(HAIR, BONE, t * .85) if n else "#141A18"
    b.append(f'<rect x="{hx + c * 8:.0f}" y="{696 + r * 6}" width="7" height="5" fill="{fill}"/>')
b.append(f'<rect class="m" y="692" width="2" height="46" fill="{BONE}"><animate attributeName="x" dur="{LOOP}s" repeatCount="indefinite" '
         f'keyTimes="0;.1;.9;1" values="{hx};{hx};{hx + 424};{hx + 424}"/></rect>')

css = ".s{display:none}@media (prefers-reduced-motion:reduce){.m{display:none}.s{display:inline}}"
desc = (f"An isometric city at dusk where each building is one day of GitHub activity, {total:,} contributions in all. "
        "A car drives the avenue and windows light up as it passes.")
doc = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">'
       f'<title id="t">Nosherwan, AI and Web Engineer</title><desc id="d">{html.escape(desc)}</desc><style>{css}</style><defs>{"".join(defs)}'
       f'<clipPath id="c"><rect width="{W}" height="{H}" rx="16"/></clipPath>'
       f'<clipPath id="dc"><rect x="-1" y="-48" width="{cw + 2:.1f}" height="60"/></clipPath>'
       f'<linearGradient id="sun" x2="0" y2="1"><stop offset="0" stop-color="#FFC39A"/><stop offset=".55" stop-color="{ACCENT}" stop-opacity=".75"/><stop offset="1" stop-color="{ACCENT}" stop-opacity="0"/></linearGradient>'
       f'<linearGradient id="beam" gradientUnits="userSpaceOnUse" x1="20" y1="-10" x2="120" y2="-58"><stop offset="0" stop-color="{WARM}" stop-opacity=".55"/><stop offset="1" stop-color="{WARM}" stop-opacity="0"/></linearGradient></defs>'
       f'<g clip-path="url(#c)"><rect width="{W}" height="{H}" fill="{INK}"/>{"".join(b)}</g></svg>')
ASSETS.mkdir(exist_ok=True)
(ASSETS / "hero.svg").write_text(doc)

# ---------- location cards ----------
CW, CH = 1000, 200
T, L, R = "#7C8A7E", "#18231F", "#4A2719"


def card(name, num, title, line, tag, art):
    assert ITALIC.width(line, 30) < 690, line
    body = [f'<circle cx="58" cy="50" r="17" fill="{ACCENT}"/>', text(num, MONO5, 21, 58, 57, INK, "middle"),
            text(tag, MONO, 21, 88, 57, MUTED), text(title, SERIF, 54, 40, 122), text(line, ITALIC, 30, 40, 166), art]
    s = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CW} {CH}" width="{CW}" height="{CH}" role="img" aria-label="{html.escape(title + ". " + line)}">'
         f'<rect x=".75" y=".75" width="{CW - 1.5}" height="{CH - 1.5}" rx="16" fill="{INK}" stroke="{HAIR}" stroke-width="1.5"/>{"".join(body)}</svg>')
    (ASSETS / f"{name}.svg").write_text(s)


v = Iso(800, 150, 17, 8.2)
ground = lambda: poly([v.p(-.5, -2), v.p(-.5, 4), v.p(6.5, 4), v.p(6.5, -2)], LOT)
dots = "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="{f}"/>' for x, y, r, f in
               ((905, 42, 4, BONE), (930, 62, 3, BONE), (948, 38, 3, BONE), (884, 66, 3, BONE), (925, 30, 5, ACCENT)))
card("loc-npc", "1", "NPC_AWARE", "Game characters that remember you, offline.", "Rust / Qdrant / Three.js",
     ground() + v.tower(3.4, .5, 1.4, 1.4, 34, T, L, R, 1) + v.tower(1, 0, 2, 2, 70, T, L, R, 2) + dots)
card("loc-guardian", "2", "npm-guardian", "Stops malicious npm packages before install.", "TypeScript / CLI",
     ground() + v.box(4.2, .6, 1, 1, 0, 14, ACCENT, "#B34A2A", "#D85A33") + v.tower(1, -1, 1.1, 1.1, 58, T, L, R, 3)
     + v.box(1.3, .1, .4, 2, 44, 8, ACCENT, "#B34A2A", "#D85A33") + v.tower(1, 2, 1.1, 1.1, 58, T, L, R, 4))
cx, cy = v.p(2.5, 1, 86)
card("loc-wait", "3", "Wait a Minute", "One key turns the last minute of video into a note.", "TypeScript / Chrome extension",
     ground() + v.tower(1.6, .1, 1.8, 1.8, 66, T, L, R, 5)
     + f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="21" fill="{INK}" stroke="{BONE}" stroke-width="3"/><path d="M{cx:.1f} {cy:.1f}V{cy - 15:.1f}" stroke="{ACCENT}" stroke-width="3"/><path d="M{cx:.1f} {cy:.1f}h10" stroke="{BONE}" stroke-width="3"/>')
card("loc-hope", "4", "Hope in Roman Urdu", "An open dataset and model for detecting hope.", "PyTorch / XLM-RoBERTa",
     ground() + v.tower(.6, -1.2, 1.5, 1.5, 62, T, L, R, 6) + v.box(1, .3, .7, 1.6, 40, 7, ACCENT, "#B34A2A", "#D85A33") + v.tower(.6, 1.9, 1.5, 1.5, 62, T, L, R, 7))
d1, d2 = v.p(3.3, 2.6, 2), v.p(4.3, 2.6, 24)
card("loc-githide", "5", "githide", "Encrypted .env sharing: server and dashboard.", "Contributor / TypeScript",
     ground() + v.tower(1.5, .2, 3.6, 2.4, 34, T, L, R, 8)
     + poly([v.p(2.8, 2.6, 0), v.p(3.9, 2.6, 0), v.p(3.9, 2.6, 22), v.p(2.8, 2.6, 22)], ACCENT))

stack = [("AI", 40, ["PyTorch  Transformers  RAG", "llama.cpp  Qdrant  LangChain"]),
         ("Web", 520, ["TypeScript  React  Next.js", "Node.js  FastAPI  PostgreSQL"])]
body = [f'<path d="M500 32V148" stroke="{HAIR}" stroke-width="1.5"/>']
for t, x, lines in stack:
    body.append(text(t, SERIF, 50, x, 76))
    body += [text(l, MONO, 25, x, 116 + i * 34, MUTED) for i, l in enumerate(lines)]
(ASSETS / "stack.svg").write_text(
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {CW} 180" width="{CW}" height="180" role="img" aria-label="AI: PyTorch, Transformers, RAG, llama.cpp, Qdrant, LangChain. Web: TypeScript, React, Next.js, Node.js, FastAPI, PostgreSQL.">'
    f'<rect x=".75" y=".75" width="{CW - 1.5}" height="178.5" rx="16" fill="{INK}" stroke="{HAIR}" stroke-width="1.5"/>{"".join(body)}</svg>')
print(f"{total} contributions, heat {heat}, hero {len(doc) / 1024:.0f} KB")
