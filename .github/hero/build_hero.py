"""Draws assets/hero.svg: a city at dusk built from the public contribution calendar."""
import datetime as dt, html, math, pathlib, random, re, sys, urllib.request
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

USER = "nosherwan537"
HERE = pathlib.Path(__file__).resolve().parent
TARGET = HERE.parent.parent / "assets" / "hero.svg"
INK, BONE, MUTED, ACCENT = "#0C1411", "#F1EADB", "#A9A99B", "#FF6A3D"
BLOCK_A, BLOCK_B, FAR = "#101A17", "#16211D", "#6E3324"
W, H, M = 1200, 760, 64
KERB, LANE, CAR_Y = 640, 706, 694
LOOP = 22  # seconds: 2 waiting, 18 driving, 2 holding the final score
START, END = -150, W + 150


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
start, end = min(days), max(days)
total = sum(days.values())
weeks = (end - start).days // 7 + 1
weekly = [0] * weeks
for d, c in days.items():
    weekly[(d - start).days // 7] += c
peak_day = max(sorted(days), key=days.get)
peak_week = (peak_day - start).days // 7
recent = sum(c for d, c in days.items() if (end - d).days < 7)
heat = sum(recent >= t for t in (1, 10, 25, 50, 100))
top = max(weekly)
bw = W / weeks
when = lambda x: .1 + .8 * (x - START) / (END - START)

# ---------- sky ----------
b = [f'<rect y="{y}" width="{W}" height="{h}" fill="{c}"/>' for y, h, c in
     ((360, 50, "#1D1C19"), (410, 50, "#432820"), (460, 60, "#853A26"), (520, 120, "#C9552F"))]
b.append(f'<circle cx="880" cy="540" r="92" fill="#FFB98A"/>')

# ---------- far skyline, then one building per week ----------
r = random.Random(7)
x, far = 0, f"M0 {KERB}"
while x < W:
    w = r.choice((34, 46, 58, 72))
    y = KERB - r.randint(50, 130)
    far += f"V{y}H{x + w}"
    x += w
b.append(f'<path d="{far}V{KERB}Z" fill="{FAR}"/>')

blocks, lit, static_lit, scores, times = [], [], [], [0], [0.0]
for j, v in enumerate(weekly):
    x = j * bw
    h = 34 + math.sqrt(v / top) * 196
    y = KERB - h
    blocks.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="{bw + .6:.1f}" height="{h:.1f}" fill="{BLOCK_B if j % 2 else BLOCK_A}"/>')
    rr = random.Random((start + dt.timedelta(weeks=j)).isoformat())
    d = ""
    for row in range(int((h - 16) // 15)):
        for col in range(3):
            if rr.random() < .55:
                d += f"M{x + 4 + col * 5.4:.1f} {y + 9 + row * 15:.1f}h3v7h-3z"
    if d:
        f = when(x + bw / 2)
        lit.append(f'<path d="{d}" fill="#FFD9A8" opacity="0"><animate attributeName="opacity" dur="{LOOP}s" '
                   f'repeatCount="indefinite" keyTimes="0;{f:.4f};{f + .004:.4f};.96;1" values="0;0;1;1;0"/></path>')
        static_lit.append(f'<path d="{d}" fill="#FFD9A8"/>')
    times.append(when(x + bw / 2))
    scores.append(sum(weekly[:j + 1]))
scores[-1] = total
times.append(1.0); scores.append(total)
kt = ";".join(f"{t:.4f}" for t in times)
b += blocks
b.append(f'<g class="m">{"".join(lit)}</g><g class="s">{"".join(static_lit)}</g>')

# Flag on the roof of the week holding the busiest day.
fx = (peak_week + .5) * bw
fy = KERB - (34 + math.sqrt(weekly[peak_week] / top) * 196)
hit = when(fx)
b.append(f'<g transform="translate({fx:.1f} {fy:.1f})"><path d="M0 0V-40" stroke="{ACCENT}" stroke-width="3"/>'
         f'<path d="M0 -40L{-24 if fx > W - 40 else 24} -32L0 -24Z" fill="{ACCENT}"/></g>')


def palm(x, h, lean):
    tx, ty = x + lean, KERB - h
    fronds = ""
    for dx, dy in ((-62, 14), (-48, -20), (-16, -38), (22, -36), (52, -16), (64, 16)):
        cx, cy = tx + dx * .55, ty + dy - 16
        ex, ey = tx + dx, ty + dy + 22
        fronds += f"M{tx} {ty}Q{cx:.0f} {cy:.0f} {ex} {ey}Q{cx:.0f} {cy + 15:.0f} {tx} {ty}Z"
    return (f'<path d="M{x - 5} {KERB}Q{x + lean * .2:.0f} {KERB - h * .55:.0f} {tx - 2} {ty}h4'
            f'Q{x + 7 + lean * .25:.0f} {KERB - h * .5:.0f} {x + 6} {KERB}Z{fronds}" fill="{INK}"/>')


b += [palm(214, 150, 14), palm(248, 104, -12), palm(1010, 132, -14)]

# ---------- street ----------
b.append(f'<rect y="{KERB}" width="{W}" height="{H - KERB}" fill="{INK}"/>'
         f'<path d="M0 {KERB + 1}H{W}" stroke="{BONE}" stroke-opacity=".55" stroke-width="2"/>')
b.append(f'<path class="m" d="M-80 {LANE}H{W + 80}" stroke="{BONE}" stroke-opacity=".3" stroke-width="3" stroke-dasharray="34 46">'
         f'<animate attributeName="stroke-dashoffset" from="80" to="0" dur=".8s" repeatCount="indefinite"/></path>')


def wheel(cx):
    return (f'<g transform="translate({cx} -7)"><circle r="7" fill="{INK}" stroke="{BONE}" stroke-width="2.5"/>'
            f'<path d="M-4 0H4M0 -4V4" stroke="{BONE}" stroke-width="1.5"><animateTransform attributeName="transform" '
            f'type="rotate" from="0" to="360" dur=".3s" repeatCount="indefinite"/></path></g>')


car = (f'<path d="M34 -15L135 -31V-1L34 -8Z" fill="url(#beam)"/>'
       f'<path d="M-34 -7V-15C-34 -18 -32 -20 -28 -21L-14 -23L-3 -32C-1 -34 2 -35 5 -35H15C18 -35 20 -34 22 -32L29 -22'
       f'C33 -21 36 -18 36 -14V-7Z" fill="{BONE}"/>'
       f'<path d="M-7 -24L0 -30C1 -31 3 -32 5 -32H8V-24ZM11 -24V-32H15C17 -32 18 -31 19 -30L24 -24Z" fill="{INK}"/>'
       f'<rect x="-34" y="-17" width="6" height="4" fill="{ACCENT}"/>{wheel(-20)}{wheel(22)}')
b.append(f'<g class="m"><g><g transform="scale(1.45)">{car}</g><animateMotion dur="{LOOP}s" repeatCount="indefinite" '
         f'calcMode="linear" keyPoints="0;0;1;1" keyTimes="0;.1;.9;1" path="M{START} {CAR_Y}H{END}"/></g></g>')
b.append(f'<g class="s" transform="translate(760 {CAR_Y}) scale(1.45)">{car}</g>')

# ---------- HUD ----------
pip = "".join(f'<path d="M{M + 92 + i * 26} 52l14 10l-14 10h-9l14 -10l-14 -10z" fill="{ACCENT if i < heat else "#34403A"}"/>' for i in range(5))
b += [text("HEAT", MONO5, 26, M, 72, MUTED, track=3), pip]
digits = f"{total}"
fs, lh = 30, 42
cw = MONO5.width("0", fs)
tail = " contributions"
tail_w = MONO.width(tail, fs)
comma_w = cw if len(digits) > 3 else 0
x = W - M - tail_w - comma_w - cw * len(digits)
defs = "".join(f'<path id="n{d}" d="{MONO5.path(str(d), fs, 0, 0)}"/>' for d in range(10))
score, final = [], []
for i in range(len(digits)):
    place = 10 ** (len(digits) - 1 - i)
    vals = ";".join(f"0 {-(v // place % 10) * lh}" for v in scores)
    strip = "".join(f'<use href="#n{d}" y="{d * lh}"/>' for d in range(10))
    score.append(f'<g transform="translate({x:.1f} 72)" clip-path="url(#dc)"><g fill="{BONE}">{strip}'
                 f'<animateTransform attributeName="transform" type="translate" calcMode="discrete" dur="{LOOP}s" '
                 f'repeatCount="indefinite" keyTimes="{kt}" values="{vals}"/></g></g>')
    final.append(text(digits[i], MONO5, fs, x, 72))
    x += cw
    if len(digits) - 1 - i == 3:
        comma = text(",", MONO5, fs, x, 72, MUTED)
        score.append(comma); final.append(comma)
        x += cw
b += [f'<g class="m">{"".join(score)}</g><g class="s">{"".join(final)}</g>', text(tail, MONO, fs, W - M, 72, MUTED, "end")]
size = 100 * (W - 2 * M) / SERIF.width("Nosherwan", 100)
b += [text("Nosherwan", SERIF, size, M - 6, 262),
      text("I build for the web and train the models behind it.", ITALIC, 46, M, 336)]

# Minimap: the blip runs the route in step with the car.
cx, cy, rad = M + 54, 664, 58
route = f"M{cx - 44} {cy + 18}H{cx - 14}V{cy - 16}H{cx + 16}V{cy + 10}H{cx + 44}"
streets = "".join(f'<path d="M{cx - 60} {cy + o}H{cx + 60}M{cx + o} {cy - 60}V{cy + 60}"/>' for o in (-34, -16, 10, 18, 40))
b.append(f'<circle cx="{cx}" cy="{cy}" r="{rad}" fill="{INK}"/><g clip-path="url(#mm)"><g stroke="{BONE}" stroke-opacity=".16" stroke-width="3">{streets}</g>'
         f'<path d="{route}" fill="none" stroke="{ACCENT}" stroke-width="3.5"/></g>'
         f'<circle cx="{cx}" cy="{cy}" r="{rad}" fill="none" stroke="{BONE}" stroke-width="3"/>'
         f'<circle class="s" cx="{cx + 16}" cy="{cy}" r="6" fill="{BONE}"/>'
         f'<g class="m"><circle r="6" fill="{BONE}"><animateMotion dur="{LOOP}s" repeatCount="indefinite" calcMode="linear" '
         f'keyPoints="0;0;1;1" keyTimes="0;.1;.9;1" path="{route}"/></circle></g>')

a = "Reach the busiest day: "
c = f"{days[peak_day]} on {peak_day.day} {peak_day:%b}"
sw = MONO.width(a, 28) + MONO5.width(c, 28)
sx = (W - sw) / 2 + 60
b += [text(a, MONO, 28, sx, H - 18, BONE), text(c, MONO5, 28, sx + MONO.width(a, 28), H - 18, ACCENT)]

css = (".s{display:none}@media (prefers-reduced-motion:reduce){.m{display:none}.s{display:inline}}")
title = "Nosherwan, software engineer"
desc = (f"A car drives through a city at dusk. Each building is one week of GitHub activity, {total:,} contributions in all, "
        "and its windows light up as the car passes.")
doc = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">'
       f'<title id="t">{html.escape(title)}</title><desc id="d">{html.escape(desc)}</desc><style>{css}</style><defs>{defs}'
       f'<clipPath id="c"><rect width="{W}" height="{H}" rx="20"/></clipPath>'
       f'<clipPath id="dc"><rect x="-1" y="-29" width="{cw + 2:.1f}" height="38"/></clipPath>'
       f'<clipPath id="mm"><circle cx="{cx}" cy="{cy}" r="{rad}"/></clipPath>'
       f'<linearGradient id="beam"><stop offset="0" stop-color="#FFD9A8" stop-opacity=".6"/><stop offset="1" stop-color="#FFD9A8" stop-opacity="0"/></linearGradient></defs>'
       f'<g clip-path="url(#c)"><rect width="{W}" height="{H}" fill="{INK}"/>{"".join(b)}</g></svg>')
TARGET.parent.mkdir(exist_ok=True)
TARGET.write_text(doc)
print(f"{total} contributions, heat {heat} ({recent} in 7 days), peak {days[peak_day]} on {peak_day}, {len(doc) / 1024:.0f} KB")
