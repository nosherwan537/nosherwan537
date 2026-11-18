"""Draws assets/hero.svg from the public GitHub contribution calendar."""
import datetime as dt, html, math, pathlib, re, sys, urllib.request
import uharfbuzz as hb
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

USER = "nosherwan537"
HERE = pathlib.Path(__file__).resolve().parent
TARGET = HERE.parent.parent / "assets" / "hero.svg"
INK, BONE, MUTED, ACCENT = "#0C1411", "#F1EADB", "#A9A99B", "#FF6A3D"
W, H, M, N = 1200, 790, 64, 420
LOOP = 20  # seconds: 2 waiting, 16 driving, 2 holding the final score


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


def smooth(v, r):
    return [sum(v[max(0, i - r):i + r + 1]) / len(v[max(0, i - r):i + r + 1]) for i in range(len(v))]


def poly(p):
    return "M" + " ".join(f"{x:.1f} {y:.1f}" for x, y in p)


days = fetch_days()
start, end = min(days), max(days)
total = sum(days.values())
weeks = (end - start).days // 7 + 1
grid = [[0.0] * weeks for _ in range(7)]
for d, c in days.items():
    grid[(d.weekday() + 1) % 7][(d - start).days // 7] = c
top = max(max(r) for r in grid)
peak_day = max(sorted(days), key=days.get)
week_of = lambda x: -3 + x / W * (weeks + 5)
x_of = lambda wk: (wk + 3) / (weeks + 5) * W


def ridge(row):
    out = []
    for i in range(N + 1):
        t = -3 + i / N * (weeks + 5)
        out.append(sum(math.sqrt(row[j] / top) * math.exp(-((t - j) ** 2) / (2 * .72 ** 2)) for j in range(weeks)))
    return out


base, gap, amp = 566, 25, 152
curves = [ridge(r) for r in grid]
norm = max(max(c) for c in curves)
lines = [[(i / N * W, base + k * gap - v / norm * amp) for i, v in enumerate(c)] for k, c in enumerate(curves)]

# The road is the skyline of all seven ridges, eased so a car can drive it.
sky = smooth(smooth([min(l[i][1] for l in lines) for i in range(N + 1)], 5), 4)
road = [(-90, sky[0])] + [(i / N * W, y) for i, y in enumerate(sky)][::2] + [(W + 90, sky[-1])]
lengths = [0.0]
for a, b in zip(road, road[1:]):
    lengths.append(lengths[-1] + math.dist(a, b))


def at(frac):
    goal = frac * lengths[-1]
    for i in range(1, len(road)):
        if lengths[i] >= goal:
            k = (goal - lengths[i - 1]) / (lengths[i] - lengths[i - 1] or 1)
            return (road[i - 1][0] + k * (road[i][0] - road[i - 1][0]),
                    road[i - 1][1] + k * (road[i][1] - road[i - 1][1]))
    return road[-1]


def tilt(frac, span=30, limit=24):
    """Body angle measured across the wheelbase, capped so the car stays upright."""
    d = span / lengths[-1]
    a, c = at(max(0, frac - d)), at(min(1, frac + d))
    return max(-limit, min(limit, math.degrees(math.atan2(c[1] - a[1], c[0] - a[0]))))


# Score: real running total as the car passes each week.
weekly = [sum(r[w] for r in grid) for w in range(weeks)]
samples = 64
times, scores, tilts = [0.0], [0], [tilt(0)]
for i in range(samples + 1):
    s = i / samples
    wk = week_of(at(s)[0])
    n = sum(v for w, v in enumerate(weekly) if w <= wk)
    times.append(.1 + .8 * s)
    scores.append(int(n))
    tilts.append(tilt(s))
scores[-1] = total
times.append(1.0); scores.append(total); tilts.append(tilts[-1])
kt = ";".join(f"{t:.4f}" for t in times)

digits = f"{total}"
fs, lh = 28, 40
cw = MONO5.width("0", fs)
tail = " contributions, last 12 months"
tail_w = MONO.width(tail, fs)
comma_w = cw if len(digits) > 3 else 0
x = W - M - tail_w - comma_w - cw * len(digits)
defs = "".join(f'<path id="n{d}" d="{MONO5.path(str(d), fs, 0, 0)}"/>' for d in range(10))
score, final = [], []
for i in range(len(digits)):
    place = 10 ** (len(digits) - 1 - i)
    vals = ";".join(f"0 {-(v // place % 10) * lh}" for v in scores)
    strip = "".join(f'<use href="#n{d}" y="{d * lh}"/>' for d in range(10))
    score.append(f'<g transform="translate({x:.1f} 78)" clip-path="url(#dc)"><g fill="{BONE}">{strip}'
                 f'<animateTransform attributeName="transform" type="translate" calcMode="discrete" dur="{LOOP}s" '
                 f'repeatCount="indefinite" keyTimes="{kt}" values="{vals}"/></g></g>')
    final.append(text(digits[i], MONO5, fs, x, 78))
    x += cw
    if len(digits) - 1 - i == 3:
        comma = text(",", MONO5, fs, x, 78, MUTED)
        score.append(comma); final.append(comma)
        x += cw

b = [text("SOFTWARE ENGINEER", MONO, 28, M, 78, MUTED, track=3),
     f'<g class="m">{"".join(score)}</g><g class="s">{"".join(final)}</g>',
     text(tail, MONO, fs, W - M, 78, MUTED, "end")]
size = 100 * (W - 2 * M) / SERIF.width("Nosherwan", 100)
b += [text("Nosherwan", SERIF, size, M - 6, 274),
      text("I build for the web and train the models behind it.", ITALIC, 46, M, 350)]

tones = ["#101915", "#101A16", "#111B17", "#121C18", "#121D19", "#131E1A", "#141F1B"]
for k, p in enumerate(lines):
    d = poly(p)
    b.append(f'<path d="{d} L{W} {H} L0 {H}Z" fill="{tones[k]}"/>')
    b.append(f'<path class="r" style="animation-delay:{k * .11:.2f}s" pathLength="1" d="{d}" fill="none" '
             f'stroke="{BONE}" stroke-opacity="{.26 + .4 * k / 6:.2f}" stroke-width="1.75"/>')
road_d = poly(road)
b.append(f'<path class="r" style="animation-delay:.7s" pathLength="1" d="{road_d}" fill="none" stroke="{BONE}" stroke-width="3" stroke-linejoin="round"/>')

# Checkpoint flag at the busiest day. The ring fires as the car arrives.
px = x_of((peak_day - start).days // 7)
i = min(range(len(road)), key=lambda n: abs(road[n][0] - px))
px, py = road[i]
hit = .1 + .8 * lengths[i] / lengths[-1]
b.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="8" fill="none" stroke="{ACCENT}" stroke-width="3" opacity="0" class="m">'
         f'<animate attributeName="r" dur="{LOOP}s" repeatCount="indefinite" keyTimes="0;{hit:.4f};{hit + .05:.4f};1" values="8;8;46;46"/>'
         f'<animate attributeName="opacity" dur="{LOOP}s" repeatCount="indefinite" keyTimes="0;{hit - .001:.4f};{hit:.4f};{hit + .05:.4f};1" values="0;0;1;0;0"/></circle>')
b.append(f'<g transform="translate({px:.1f} {py:.1f})"><path d="M0 0V-46" stroke="{ACCENT}" stroke-width="3"/>'
         f'<path d="M0 -46L26 -37L0 -28Z" fill="{ACCENT}"/></g>')


def wheel(cx):
    return (f'<g transform="translate({cx} -7)"><circle r="7" fill="{INK}" stroke="{BONE}" stroke-width="2.5"/>'
            f'<path d="M-4 0H4M0 -4V4" stroke="{BONE}" stroke-width="1.5"><animateTransform attributeName="transform" '
            f'type="rotate" from="0" to="360" dur=".35s" repeatCount="indefinite"/></path></g>')


car = (f'<path d="M34 -14L150 -46V8L34 -7Z" fill="url(#beam)"/>'
       f'<path d="M-34 -7V-15C-34 -18 -32 -20 -28 -21L-14 -23L-3 -32C-1 -34 2 -35 5 -35H15C18 -35 20 -34 22 -32L29 -22'
       f'C33 -21 36 -18 36 -14V-7Z" fill="{BONE}"/>'
       f'<path d="M-7 -24L0 -30C1 -31 3 -32 5 -32H8V-24ZM11 -24V-32H15C17 -32 18 -31 19 -30L24 -24Z" fill="{INK}"/>'
       f'<rect x="-34" y="-17" width="6" height="4" fill="{ACCENT}"/>{wheel(-20)}{wheel(22)}')
spin = ";".join(f"{a:.1f}" for a in tilts)
b.append(f'<g class="m"><g><g>{car}<animateTransform attributeName="transform" type="rotate" dur="{LOOP}s" '
         f'repeatCount="indefinite" keyTimes="{kt}" values="{spin}"/></g><animateMotion dur="{LOOP}s" repeatCount="indefinite" '
         f'calcMode="linear" keyPoints="0;0;1;1" keyTimes="0;.1;.9;1" path="{road_d}"/></g></g>')
parked = max(0, lengths[i] / lengths[-1] - 70 / lengths[-1])
sx, sy = at(parked)
b.append(f'<g class="s" transform="translate({sx:.1f} {sy:.1f}) rotate({tilt(parked):.1f})">{car}</g>')

b.append(f'<rect y="{H - 66}" width="{W}" height="66" fill="{tones[-1]}"/>')
b.append(text("One ridge per weekday, one step per week.", MONO, 28, M, H - 24, MUTED))
b.append(text(f"Peak: {days[peak_day]} on {peak_day.day} {peak_day:%b}", MONO5, 28, W - M, H - 24, ACCENT, "end"))

css = (".r{stroke-dasharray:1;stroke-dashoffset:1;animation:d 1.7s cubic-bezier(.3,.7,.2,1) forwards}.s{display:none}"
       "@keyframes d{to{stroke-dashoffset:0}}"
       "@media (prefers-reduced-motion:reduce){.r{animation:none;stroke-dashoffset:0}.m{display:none}.s{display:inline}}")
title = "Nosherwan, software engineer"
desc = f"A small car drives over a mountain range drawn from {total:,} GitHub contributions, past a flag on the busiest day."
doc = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">'
       f'<title id="t">{html.escape(title)}</title><desc id="d">{html.escape(desc)}</desc><style>{css}</style><defs>{defs}'
       f'<clipPath id="c"><rect width="{W}" height="{H}" rx="20"/></clipPath>'
       f'<clipPath id="dc"><rect x="-1" y="-27" width="{cw + 2:.1f}" height="36"/></clipPath>'
       f'<linearGradient id="beam"><stop offset="0" stop-color="{BONE}" stop-opacity=".42"/><stop offset="1" stop-color="{BONE}" stop-opacity="0"/></linearGradient></defs>'
       f'<g clip-path="url(#c)"><rect width="{W}" height="{H}" fill="{INK}"/>{"".join(b)}</g></svg>')
TARGET.parent.mkdir(exist_ok=True)
TARGET.write_text(doc)
print(f"{total} contributions, peak {days[peak_day]} on {peak_day}, {len(doc) / 1024:.0f} KB")
