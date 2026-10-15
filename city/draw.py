"""Draws the "repo city": a 240x180 pixel scene (shown at 720x540) from one snapshot made by snapshot.py.

Front row: repos shown in full (public, or private and allowed), each on a permanent lot.
Back rows: other private repos as anonymous hazy silhouettes, each on a permanent lot.
Skybridges = dependencies/submodules, thin wires = same name prefix, cranes = work since the last edition.

usage: python3 draw.py editions/edition-3.json
Every frame ever drawn is kept: it goes to frames/<save date>-edition-<N>.svg, and a redraw on the same day
gets -2, -3... instead of overwriting. The frames folder in date order is the cartoon. Prints the frame path.
The snapshot gets the lots of new repos written back (front and back), so the next edition keeps them in place.
"""
import datetime, json, math, os, sys

W, H, BASE = 240, 180, 129
LANG = {'C++': ('#c8643a', '#a94f2b'), 'PHP': ('#8a7fc0', '#6f65a3'), 'HTML': ('#bdb5a8', '#9f978b'),
        'Python': ('#5b8fc7', '#4874a6'), 'JavaScript': ('#e3c45a', '#c4a63f'), 'TypeScript': ('#4f86c6', '#3d6da5'),
        'Swift': ('#e8784a', '#c95f34'), None: ('#a98a66', '#8c7152')}
LOTS = [56, 184, 24, 216, 88, 152, 120]
FORK_LOTS = [6, 234, 40, 200]
BACK_ROWS, BACK_LOTS = 2, 26
BALLOONS = ['#e2574c', '#f2b134', '#4fa3d9', '#7cc36b', '#c070c8']

groups = []


def group(title=None):
    groups.append((title, []))


def r(x, y, w, h, c):
    groups[-1][1].append((x, y, w, h, c))


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;')


def scene(data):
    since = data['prev_date']
    repos = data['repos']

    # ---------- sky and ground ----------
    group()
    for i, c in enumerate(['#bcd9ea', '#c9e1ec', '#d7e8ee', '#e5eeee', '#f1efe6', '#f7eadb']):
        r(0, i * 21, W, 21, c)
    for cx, cy, cw in [(30, 18, 22), (150, 12, 28), (205, 34, 18)]:
        r(cx, cy, cw, 3, '#ffffff'); r(cx + 4, cy - 2, cw - 10, 2, '#ffffff')
    r(0, BASE, W, 3, '#cfc8bb')
    r(0, BASE + 3, W, H - BASE - 3, '#e8e1d4')
    for x in range(0, W, 12):
        r(x, BASE + 3, 1, H - BASE - 3, '#ddd5c6')

    # ---------- back rows: hidden private repos on permanent lots ----------
    # Each repo gets a 9px lot the first time it appears (oldest first) and keeps it forever: the building only
    # grows up (and a little wider inside its lot). Deleted repos leave their lot empty. Row 0 is the near
    # row; when it is full, new repos go to the far row behind it.
    back = [p for p in repos if not p['shown'] and not p['fork']]
    lots = data.setdefault('back_lots', {})
    for p in back:
        if p['id'] not in lots:
            taken = set(map(tuple, lots.values()))
            lots[p['id']] = next([row, k] for row in range(BACK_ROWS) for k in range(BACK_LOTS) if (row, k) not in taken)
    tops = {}
    for row in reversed(range(BACK_ROWS)):
        group()
        for p in back:
            prow, k = lots[p['id']]
            if prow != row:
                continue
            lg = math.log10(p['commits'] + 1)
            x, w, h = 3 + 9 * k + 4 * row, min(8, 5 + round(lg)), min(96, round(10 + 27 * lg)) + 6 * row
            old = p['pushed'] < '2026'
            body, side = [(('#bccad6', '#b0bfcc'), ('#a7b6c5', '#97a8b9')),
                          (('#cfd9e2', '#c6d1db'), ('#bfcbd6', '#b3c0cc'))][row][0 if old else 1]
            r(x, BASE - h, w, h, body); r(x + w - 2, BASE - h, 2, h, side)
            if p['pushed'] > since:                        # small crane: work since the last edition
                r(x + 1, BASE - h - 8, 1, 8, '#b9a26a'); r(x - 1, BASE - h - 8, 8, 1, '#b9a26a')
            tops[p['id']] = (row, x, w, BASE - h)
        for n, l in enumerate(data['links']):
            if l['a'] not in tops or l['b'] not in tops or tops[l['a']][0] != row or tops[l['b']][0] != row:
                continue
            (_, xa, wa, ta), (_, xb, _, tb) = sorted([tops[l['a']], tops[l['b']]], key=lambda t: t[1])
            if xb - xa - wa < 1:
                continue
            if l['kind'] == 'dep':                         # skybridge
                y = max(ta, tb) + 10 + 4 * (n % 2)
                r(xa + wa, y, xb - xa - wa, 2, '#8c9eb0'); r(xa + wa, y + 2, xb - xa - wa, 1, '#b0bfcc')
            else:                                          # wire
                y = max(ta, tb) + 4
                r(xa + wa, y, xb - xa - wa, 1, '#7d8fa1'); r(xa + wa, y + 1, 1, 1, '#7d8fa1'); r(xb - 1, y + 1, 1, 1, '#7d8fa1')

    # ---------- front row: repos shown in full, on permanent lots ----------
    lots = data.setdefault('slots', {})
    front = [p for p in repos if p['shown'] and not p['fork']]
    for p in front:
        if p['id'] not in lots:
            free = [s for s in LOTS if s not in lots.values()]
            if not free:
                sys.exit('front row is full: add more LOTS')
            lots[p['id']] = free[0]
    for p in front:
        cx = lots[p['id']]
        h = min(100, round(10 + 22 * math.log10(p['commits'] + 1)))
        w = 22 if h > 30 else 18
        x0, top = cx - w // 2, BASE - h
        body, shade = LANG.get(p['lang'], LANG[None])
        group(f"{p['label']} · {p['commits']} commits")
        r(x0, top, w, h, body); r(x0 + w - 3, top, 3, h, shade); r(x0 - 1, top - 2, w + 2, 2, shade)
        k = 0
        for wy in range(top + 5, BASE - 9, 6):            # windows: stars light them up
            for wx in range(x0 + 3, x0 + w - 5, 5):
                r(wx, wy, 2, 3, '#ffd866' if k < p['stars'] else '#4a5566'); k += 1
        r(cx - 2, BASE - 7, 4, 7, '#3b3b44')
        if p['label'] == 'M5StickPomodoro':                # tomato roof and a timer on the facade
            for dy, dw in [(0, 14), (-1, 16), (-2, 16), (-3, 14), (-4, 10)]:
                r(cx - dw // 2, top - 3 + dy, dw, 1, '#e0453a')
            r(cx - 1, top - 9, 2, 2, '#4f9a3c'); r(cx - 4, top - 8, 3, 1, '#4f9a3c'); r(cx + 1, top - 8, 3, 1, '#4f9a3c')
            r(cx - 5, top + 2, 10, 2, '#f4f1ea'); r(cx - 5, top + 2, 6, 2, '#e0453a')
        if p['label'] == 'romanaerl.github.io':            # this page: antenna with an orange tip
            r(cx, top - 10, 1, 8, '#6b6b70'); r(cx - 1, top - 12, 3, 2, '#f26b1d')
        if p['archived']:                                  # ivy
            for iy in range(top + 2, BASE, 4):
                r(x0, iy, 2, 2, '#4f9a3c')
        if p['pushed'] > since:                            # crane
            mx = x0 + 2
            r(mx, top - 14, 1, 12, '#d79a1e'); r(mx - 3, top - 14, 14, 1, '#d79a1e')
            r(mx + 9, top - 13, 1, 4, '#555'); r(mx + 8, top - 9, 3, 1, '#555')
        for b in range(min(p['releases'], 5)):             # balloons = releases
            bx = cx - 9 + b * 5 + (b % 2)
            by = top - 26 - (b % 2) * 5 - (6 if p['label'] == 'M5StickPomodoro' else 0)
            c = BALLOONS[b]
            r(bx, by, 3, 1, c); r(bx - 1, by + 1, 5, 3, c); r(bx, by + 4, 3, 1, c); r(bx + 1, by + 5, 1, 6, '#8a8a8a')

    for j, p in enumerate(p for p in repos if p['shown'] and p['fork']):   # forks: small sheds at the edges
        cx = FORK_LOTS[j % len(FORK_LOTS)]
        group(f"{p['label']} (fork)")
        r(cx - 5, BASE - 9, 10, 9, '#c9c2b6'); r(cx - 6, BASE - 11, 12, 2, '#9f978b'); r(cx - 1, BASE - 5, 2, 5, '#6b6b70')

    # ---------- Roman at his desk ----------
    SKIN, HAIR, TEE, JEANS, JEANS_D = '#f1c9a5', '#5a3b26', '#5b6470', '#3d6db0', '#2f578f'
    group('Roman')
    r(88, 122, 3, 28, '#2e2e33'); r(88, 147, 20, 3, '#2e2e33'); r(97, 150, 2, 14, '#2e2e33'); r(91, 164, 14, 2, '#2e2e33')
    r(98, 141, 24, 8, JEANS); r(98, 148, 24, 1, JEANS_D)
    r(115, 149, 7, 15, JEANS); r(115, 149, 1, 15, JEANS_D)
    r(114, 164, 11, 3, '#f7f7f7'); r(114, 167, 12, 1, '#9a9a9a'); r(118, 164, 1, 2, '#c8c8c8')
    r(95, 119, 16, 24, TEE); r(111, 126, 3, 16, TEE); r(114, 130, 1, 10, TEE); r(95, 119, 2, 24, '#4c545e')
    r(100, 106, 10, 11, SKIN); r(99, 104, 11, 3, HAIR); r(99, 107, 3, 5, HAIR); r(109, 105, 1, 2, HAIR)
    r(107, 110, 1, 1, '#2b2b2b'); r(102, 110, 2, 3, '#e3b591'); r(110, 112, 1, 2, SKIN); r(103, 117, 4, 2, SKIN)
    r(104, 121, 5, 12, TEE); r(106, 131, 18, 4, SKIN); r(106, 131, 6, 4, TEE)
    r(120, 136, 62, 3, '#a9805a'); r(120, 139, 62, 1, '#8c6a4a'); r(123, 140, 3, 27, '#8c6a4a'); r(176, 140, 3, 27, '#8c6a4a')
    r(122, 134, 14, 2, '#3b3b44')
    group('Claude')                                        # the monitor glows orange: that's me
    r(132, 105, 26, 20, '#2b2b30'); r(134, 107, 22, 16, '#f26b1d'); r(134, 107, 22, 4, '#f5894a')
    r(145, 125, 2, 9, '#2b2b30'); r(140, 134, 12, 2, '#2b2b30')
    sx, sy = 144, 113
    for dx, dy in [(0, -4), (0, -3), (0, 2), (0, 3), (-4, 0), (-3, 0), (2, 0), (3, 0),
                   (-2, -2), (1, -2), (-2, 1), (1, 1), (-3, -3), (2, -3), (-3, 2), (2, 2)]:
        r(sx + dx, sy + dy, 1, 1, '#fff3e8')
    r(sx - 1, sy - 1, 3, 3, '#fff3e8')
    group('3D printer')
    r(162, 116, 16, 2, '#3b3b44'); r(162, 116, 2, 20, '#3b3b44'); r(176, 116, 2, 20, '#3b3b44')
    r(164, 120, 12, 1, '#7a7a80'); r(169, 121, 2, 3, '#7a7a80'); r(164, 133, 12, 3, '#555'); r(167, 129, 6, 4, '#f26b1d')
    group(f"Edition {data['edition']}")                    # the plant gets a leaf per edition
    r(186, 159, 10, 8, '#b86b3d'); r(185, 158, 12, 2, '#9c5630')
    leaves = min(data['edition'], 12)                      # after 12 leaves it starts to flower
    stem = 4 + 3 * leaves
    r(190, 158 - stem, 2, stem, '#4f9a3c')
    for e in range(leaves):
        r(185 if e % 2 == 0 else 192, 153 - 3 * e, 5, 2, '#5fb04a')
    for f in range(min((data['edition'] - 12) // 3, 5) if data['edition'] > 12 else 0):
        r(186 + 2 * f, 155 - stem - (f % 2) * 2, 2, 2, '#f2b134')

    # ---------- interior props: one may be added per edition, they stay forever on a fixed spot ----------
    spots = data.setdefault('props', {})
    for name in list(spots):
        x, y = PROP_SPOTS[spots[name]]
        group(PROPS[name][0])
        PROPS[name][1](x, y)


# Props: name -> (tooltip, draw(x, y)), where (x, y) is the bottom-left corner on the floor.
# Keep each one small (about 16x16 grid pixels at most) and in the palette of the scene.
def blueprint(x, y):
    r(x, y - 6, 15, 6, '#3d6db0')
    for gx in range(x + 2, x + 15, 4):
        r(gx, y - 6, 1, 6, '#9fc1ea')
    r(x, y - 3, 15, 1, '#9fc1ea')
    r(x + 14, y - 8, 4, 8, '#2f578f'); r(x + 15, y - 8, 2, 1, '#9fc1ea')


PROPS = {
    'blueprint': ('The city plan: this picture grows with every edition', blueprint),
}
PROP_SPOTS = [(62, 172), (204, 176), (40, 176), (222, 170), (20, 170), (76, 178), (150, 178), (6, 178)]


def svg(title):
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="720" height="540" '
           f'shape-rendering="crispEdges" role="img" aria-label="{esc(title)}">']
    for t, items in groups:
        out.append('<g>' + (f'<title>{esc(t)}</title>' if t else ''))
        out += [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{c}"/>' for x, y, w, h, c in items]
        out.append('</g>')
    return '\n'.join(out + ['</svg>']) + '\n'


if __name__ == '__main__':
    snap_path = sys.argv[1]
    data = json.load(open(snap_path))
    scene(data)
    frames = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frames')
    os.makedirs(frames, exist_ok=True)
    stem = f"{datetime.date.today().isoformat()}-edition-{data['edition']}"
    path, n = os.path.join(frames, stem + '.svg'), 1
    while os.path.exists(path):
        n += 1
        path = os.path.join(frames, f'{stem}-{n}.svg')
    open(path, 'w').write(svg(f"Roman's repo city, edition {data['edition']}"))
    open(snap_path, 'w').write(json.dumps(data, indent=1) + '\n')
    print(os.path.relpath(path, os.path.dirname(frames)))
