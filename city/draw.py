"""Draws the "repo city": a 240x180 pixel scene (shown at 720x540) from one snapshot made by snapshot.py.

Front row: repos shown in full (public, or private and allowed), each on a permanent lot. A repo of one of
Roman's organizations reads "Org/name" and flies a small pennant on its roof; Open3DPC's main repo, its
headquarters, gets the Open3DPC logo as a rooftop sign instead (as M5StickPomodoro gets its tomato).
Back rows: other private repos as anonymous hazy silhouettes, each on a permanent lot.
A new front building, also a private repo that went public and steps forward, takes the free front lot where
it hides the least fresh back-row work (repos pushed in the last half year; LOTS order breaks ties). A repo
that stepped forward keeps its back lot too, empty, and its popup says it stepped out of the back row.
Skybridges = dependencies/submodules, thin wires = same name prefix, cranes = work since the last edition
(pushed after the previous snapshot was taken; older snapshots without `fresh` compare by date).
Every object's <title> is its hover popup; a prop also gets a <desc> (its story, the card a click opens) and
data-since="Edition N · date" on its <g>. The page script in index.html reads both.

usage: python3 draw.py editions/edition-3.json    (python3 draw.py --index only rebuilds frames.json)
Every frame ever drawn is kept: it goes to frames/<save date>-edition-<N>.svg, and a redraw on the same day
gets -2, -3... instead of overwriting. The frames folder in date order is the cartoon. Prints the frame path.
frames.json lists every frame in order (date, the sketch first, then edition and redraw) for the replay on the page.
The snapshot gets the lots of new repos written back (front and back), so the next edition keeps them in place.
"""
import datetime, json, math, os, re, sys

W, H, BASE = 240, 180, 129
LANG = {'C++': ('#c8643a', '#a94f2b'), 'PHP': ('#8a7fc0', '#6f65a3'), 'HTML': ('#bdb5a8', '#9f978b'),
        'Python': ('#5b8fc7', '#4874a6'), 'JavaScript': ('#e3c45a', '#c4a63f'), 'TypeScript': ('#4f86c6', '#3d6da5'),
        'Swift': ('#e8784a', '#c95f34'), None: ('#a98a66', '#8c7152')}
LOTS = [56, 184, 24, 216, 88, 152, 120]
FORK_LOTS = [6, 234, 40, 200]
BACK_ROWS, BACK_LOTS = 2, 26
BALLOONS = ['#e2574c', '#f2b134', '#4fa3d9', '#7cc36b', '#c070c8']
USER = 'romanaerl'                                         # any other owner is one of his organizations

groups = []
PREV = {}                                                  # repo id -> (commits, shown) in the previous edition
EDITIONS = ''                                              # folder with edition-N.json, set in __main__


def commits(p):
    return f"{p['commits']} commit" + ('' if p['commits'] == 1 else 's')


def progress(p, edition):
    """Tooltip tail: how the repo moved since the previous edition (no names, only counts)."""
    if not PREV:
        return ''
    if p['id'] not in PREV:
        return f' · new since edition {edition - 1}'
    before, was_shown = PREV[p['id']]
    if p['shown'] and not was_shown:
        return f' · stepped out of the back row since edition {edition - 1}'
    d = p['commits'] - before
    return f' · +{d} since edition {edition - 1}' if d > 0 else ' · quiet lately'


def fresh(p, since):
    """Crane: pushed after the previous snapshot. Snapshots before edition 16 only know dates."""
    return p['fresh'] if 'fresh' in p else p['pushed'] > since


def back_x(row, k):
    """Left edge of back lot k in back row `row`."""
    return 3 + 9 * k + 4 * row


def back_w(p):
    return min(8, 5 + round(math.log10(p['commits'] + 1)))


def front_size(p):
    """(width, height) of a front-row building."""
    h = min(100, round(10 + 22 * math.log10(p['commits'] + 1)))
    return (22 if h > 30 else 18), h


# The Open3DPC logo mark, pixel for pixel: white on a coral tile with rounded corners.
OPEN3DPC_MARK = ['############', '###        #', '###        #', '#          #', '#          #', '#          #',
                 '#       ## #', '#       ## #', '#     #### #', '#     #### #', '#          #', '############']


def hq_sign(cx, top):
    """Open3DPC headquarters: its 16x16 logo tile as a sign on two legs above the roof."""
    x, y = cx - 8, top - 20
    r(x + 3, top - 4, 1, 2, '#6b6b70'); r(x + 12, top - 4, 1, 2, '#6b6b70')
    for dy, a in enumerate([2, 1] + [0] * 12 + [1, 2]):
        r(x + a, y + dy, 16 - 2 * a, 1, '#ff5a3c')
    for dy, line in enumerate(OPEN3DPC_MARK):
        for m in re.finditer('#+', line):
            r(x + 2 + m.start(), y + 2 + dy, m.end() - m.start(), 1, '#ffffff')


def fresh_hidden(cx, w, data):
    """How many back-row repos pushed in the last half year a front building w wide at lot cx would stand in front of."""
    cutoff = (datetime.date.fromisoformat(data['date']) - datetime.timedelta(days=182)).isoformat()
    by_id = {p['id']: p for p in data['repos']}
    n = 0
    for i, (row, k) in data['back_lots'].items():
        p = by_id.get(i)
        if p and not p['shown'] and not p['fork'] and p['pushed'] >= cutoff:
            x = back_x(row, k)
            n += x <= cx - w // 2 + w - 1 and x + back_w(p) - 1 >= cx - w // 2
    return n


def group(title=None, story=None, since=None):
    """A clickable object: title is the hover popup, story the card a click opens, since its 'Edition N · date'."""
    groups.append((title, [], story, since))


def r(x, y, w, h, c):
    groups[-1][1].append((x, y, w, h, c))


def esc(s):
    return s.replace('&', '&amp;').replace('<', '&lt;').replace('"', '&quot;')


def edition_label(n):
    """'Edition 7 · 1 Nov 2026', the date read from that edition's snapshot next to the one being drawn."""
    d = datetime.date.fromisoformat(json.load(open(os.path.join(EDITIONS, f'edition-{n}.json')))['date'])
    return f'Edition {n} · {d.day} {d:%b %Y}'


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
    # grows up (and a little wider inside its lot). Deleted repos, and repos that stepped forward into the front
    # row, leave their lot empty. Row 0 is the near row; when it is full, new repos go to the far row behind it.
    back = [p for p in repos if not p['shown'] and not p['fork']]
    lots = data.setdefault('back_lots', {})
    for p in back:
        if p['id'] not in lots:
            taken = set(map(tuple, lots.values()))
            lots[p['id']] = next([row, k] for row in range(BACK_ROWS) for k in range(BACK_LOTS) if (row, k) not in taken)
    tops = {}
    for row in reversed(range(BACK_ROWS)):
        for p in back:
            prow, k = lots[p['id']]
            if prow != row:
                continue
            group(f"Private repo · {commits(p)}" + progress(p, data['edition']))
            lg = math.log10(p['commits'] + 1)
            x, w, h = back_x(row, k), back_w(p), min(96, round(10 + 27 * lg)) + 6 * row
            old = p['pushed'] < '2026'
            body, side = [(('#bccad6', '#b0bfcc'), ('#a7b6c5', '#97a8b9')),
                          (('#cfd9e2', '#c6d1db'), ('#bfcbd6', '#b3c0cc'))][row][0 if old else 1]
            r(x, BASE - h, w, h, body); r(x + w - 2, BASE - h, 2, h, side)
            if fresh(p, since):                            # small crane: work since the last edition
                r(x + 1, BASE - h - 8, 1, 8, '#b9a26a'); r(x - 1, BASE - h - 8, 8, 1, '#b9a26a')
            tops[p['id']] = (row, x, w, BASE - h)
        group()
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
            w = front_size(p)[0]                           # stand where it hides the least fresh work
            lots[p['id']] = min(free, key=lambda s: (fresh_hidden(s, w, data), LOTS.index(s)))
    for p in front:
        cx = lots[p['id']]
        w, h = front_size(p)
        x0, top = cx - w // 2, BASE - h
        body, shade = LANG.get(p['lang'], LANG[None])
        owner = p.get('owner', USER)
        name = p['label'] if owner == USER else f"{owner}/{p['label']}"
        group(f"{name} · {commits(p)}" + progress(p, data['edition']))
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
        hq = p['label'] == 'open3dpc'                      # Open3DPC headquarters: its logo up on the roof
        if owner != USER and not hq:                       # an organization's repo: a pennant on the roof
            fx = x0 + w - 4
            r(fx, top - 10, 1, 8, '#6b6b70')
            r(fx + 1, top - 10, 4, 1, '#4fa3d9'); r(fx + 1, top - 9, 3, 1, '#4fa3d9'); r(fx + 1, top - 8, 1, 1, '#4fa3d9')
        if p['archived']:                                  # ivy
            for iy in range(top + 2, BASE, 4):
                r(x0, iy, 2, 2, '#4f9a3c')
        if fresh(p, since):                                # crane (behind the HQ sign)
            mx = x0 + 2
            r(mx, top - 14, 1, 12, '#d79a1e'); r(mx - 3, top - 14, 14, 1, '#d79a1e')
            r(mx + 9, top - 13, 1, 4, '#555'); r(mx + 8, top - 9, 3, 1, '#555')
        if hq:
            hq_sign(cx, top)
        for b in range(min(p['releases'], 5)):             # balloons = releases
            bx = cx - 9 + b * 5 + (b % 2)
            by = top - 26 - (b % 2) * 5 - (6 if p['label'] == 'M5StickPomodoro' or hq else 0)
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
        p = PROPS[name]
        group(p['tip'], p['story'], edition_label(p['edition']))
        p['draw'](x, y)


# Props: name -> dict(edition, tip, story, draw), where draw(x, y) gets the bottom-left corner on the floor.
# Keep each one small (about 16x16 grid pixels at most) and in the palette of the scene.
# Each prop tells its edition's story three ways: the page text says it in passing (and a later edition may
# replace that text), `tip` is the short hover popup, `story` is the card a click opens. The story keeps what
# the page said for good: the edition's text as it was, word for word when it stands on its own, or lightly
# retold with the context it needs once it is gone from the page, a small extra joke welcome. 1-4 sentences,
# about 60 words at most. Written once, together with the prop, and never rewritten.
def blueprint(x, y):
    r(x, y - 6, 15, 6, '#3d6db0')
    for gx in range(x + 2, x + 15, 4):
        r(gx, y - 6, 1, 6, '#9fc1ea')
    r(x, y - 3, 15, 1, '#9fc1ea')
    r(x + 14, y - 8, 4, 8, '#2f578f'); r(x + 15, y - 8, 2, 1, '#9fc1ea')


def dimmer(x, y):
    r(x, y - 7, 14, 7, '#3b3b44'); r(x + 2, y - 4, 10, 1, '#7a7a80')
    r(x + 2, y - 4, 2, 1, '#f26b1d'); r(x + 3, y - 6, 2, 4, '#f5894a')
    r(x + 5, y - 12, 3, 3, '#ffd866')
    for dx, dy in [(-1, -1), (3, -1), (-1, 3), (3, 3), (1, -2), (1, 4)]:
        r(x + 5 + dx, y - 12 + dy, 1, 1, '#f2b134')


def batchbox(x, y):
    for i, c in enumerate(['#f1efe6', '#ffd866', '#f1efe6', '#9fc1ea']):
        r(x + 1 + 3 * i, y - 11 + (i % 2), 3, 5, c)
    r(x, y - 8, 14, 8, '#a98a66'); r(x, y - 8, 14, 1, '#8c7152')
    r(x + 5, y - 6, 4, 2, '#8c7152')


def bubble(x, y):
    r(x, y - 12, 12, 9, '#f7f7f7'); r(x + 1, y - 13, 10, 1, '#f7f7f7'); r(x + 1, y - 3, 10, 1, '#f7f7f7')
    r(x + 2, y - 2, 3, 1, '#f7f7f7'); r(x + 2, y - 1, 1, 1, '#f7f7f7')
    r(x + 4, y - 11, 4, 1, '#f26b1d'); r(x + 7, y - 10, 1, 2, '#f26b1d'); r(x + 5, y - 8, 2, 1, '#f26b1d')
    r(x + 5, y - 7, 1, 1, '#f26b1d'); r(x + 5, y - 5, 1, 1, '#f26b1d')


def signal(x, y):
    r(x + 1, y - 1, 6, 1, '#2e2e33'); r(x + 3, y - 10, 2, 9, '#3b3b44')
    r(x + 1, y - 17, 6, 8, '#2b2b30')
    r(x + 3, y - 16, 2, 2, '#7a3a2a'); r(x + 3, y - 12, 2, 2, '#5fb04a')
    for dx, dy in [(-1, 0), (2, 0), (0, -1), (1, 2)]:
        r(x + 3 + dx, y - 12 + dy, 1, 1, '#9fe08a')


def envelope(x, y):
    r(x, y - 10, 15, 10, '#f7f7f7'); r(x, y - 1, 15, 1, '#c8c8c8')
    for i in range(7):
        r(x + i, y - 10 + i, 2, 1, '#c8c8c8'); r(x + 13 - i, y - 10 + i, 2, 1, '#c8c8c8')
    r(x + 6, y - 5, 3, 3, '#f26b1d'); r(x + 7, y - 6, 1, 5, '#f26b1d'); r(x + 5, y - 4, 5, 1, '#f26b1d')


def fingers(x, y):
    skin, shade = '#f1c9a5', '#e3b591'
    r(x + 3, y - 1, 9, 1, '#3b3b44'); r(x + 4, y - 5, 7, 4, skin); r(x + 4, y - 5, 7, 1, shade)
    r(x + 2, y - 10, 11, 5, skin); r(x, y - 9, 2, 3, skin); r(x + 1, y - 10, 1, 1, skin)
    for i, h in enumerate([5, 6, 5, 4]):
        r(x + 2 + 3 * i, y - 10 - h, 2, h, skin)


def mouse(x, y):
    r(x + 3, y - 7, 9, 6, '#f7f7f7'); r(x + 4, y - 8, 7, 1, '#f7f7f7'); r(x + 4, y - 1, 7, 1, '#c8c8c8')
    r(x + 4, y - 7, 3, 3, '#f26b1d'); r(x + 7, y - 8, 1, 4, '#c8c8c8'); r(x + 4, y - 4, 7, 1, '#c8c8c8')
    r(x + 7, y - 11, 1, 3, '#3b3b44'); r(x + 3, y - 12, 5, 1, '#3b3b44'); r(x + 2, y - 12, 1, 2, '#3b3b44')
    for dx, dy in [(0, -6), (1, -9), (2, -4)]:
        r(x + dx, y + dy, 1, 1, '#f2b134')


def trunk(x, y):
    r(x + 2, y - 5, 7, 5, '#b86b3d'); r(x + 1, y - 6, 9, 1, '#9c5630')
    r(x + 5, y - 12, 2, 6, '#8c6a4a'); r(x + 7, y - 10, 3, 2, '#f26b1d')
    r(x + 2, y - 16, 8, 4, '#4f9a3c'); r(x + 3, y - 17, 6, 1, '#4f9a3c'); r(x + 3, y - 16, 3, 1, '#5fb04a')


def scissors(x, y):
    for i in range(7):
        r(x + 6 + i, y - 6 - i // 2, 1, 1, '#c8c8c8'); r(x + 6 + i, y - 4 + i // 2, 1, 1, '#9a9a9a')
    r(x, y - 10, 4, 1, '#f26b1d'); r(x, y - 7, 4, 1, '#f26b1d'); r(x, y - 9, 1, 2, '#f26b1d'); r(x + 3, y - 9, 1, 2, '#f26b1d')
    r(x, y - 4, 4, 1, '#f26b1d'); r(x, y - 1, 4, 1, '#f26b1d'); r(x, y - 3, 1, 2, '#f26b1d'); r(x + 3, y - 3, 1, 2, '#f26b1d')
    r(x + 4, y - 7, 1, 1, '#f26b1d'); r(x + 4, y - 4, 1, 1, '#f26b1d'); r(x + 5, y - 6, 2, 2, '#3b3b44')


def letterblock(x, y):
    r(x + 1, y - 12, 10, 2, '#f7f7f7'); r(x + 10, y - 11, 2, 10, '#d8d2c4')
    r(x, y - 10, 10, 10, '#f1efe6'); r(x, y - 1, 10, 1, '#c8c8c8')
    r(x + 4, y - 9, 2, 1, '#f26b1d'); r(x + 3, y - 8, 1, 5, '#f26b1d'); r(x + 6, y - 8, 1, 5, '#f26b1d')
    r(x + 4, y - 6, 2, 1, '#f26b1d')


def paperplane(x, y):
    r(x, y - 7, 3, 1, '#f7f7f7'); r(x + 1, y - 6, 6, 1, '#f7f7f7'); r(x + 2, y - 5, 9, 1, '#f7f7f7')
    r(x + 4, y - 4, 10, 1, '#f7f7f7'); r(x + 5, y - 3, 6, 1, '#c8c8c8'); r(x + 6, y - 2, 3, 1, '#c8c8c8')
    r(x + 7, y - 1, 1, 1, '#c8c8c8'); r(x + 6, y - 5, 2, 1, '#f26b1d')


def nametag(x, y):
    r(x + 5, y - 12, 4, 2, '#7a7a80'); r(x, y - 10, 14, 10, '#f7f7f7'); r(x, y - 10, 14, 3, '#f26b1d')
    r(x + 3, y - 9, 8, 1, '#fff3e8'); r(x, y - 1, 14, 1, '#c8c8c8')
    r(x + 2, y - 6, 1, 4, '#3b3b44')
    r(x + 4, y - 6, 3, 1, '#3b3b44'); r(x + 4, y - 5, 1, 1, '#3b3b44'); r(x + 4, y - 4, 3, 1, '#3b3b44')
    r(x + 6, y - 3, 1, 1, '#3b3b44'); r(x + 4, y - 2, 3, 1, '#3b3b44')
    r(x + 8, y - 5, 4, 1, '#9a9a9a'); r(x + 8, y - 3, 3, 1, '#9a9a9a')


OPEN_LETTERS = [['###', '# #', '# #', '# #', '###'], ['###', '# #', '###', '#  ', '#  '],
                ['###', '#  ', '## ', '#  ', '###'], ['#  #', '## #', '# ##', '#  #', '#  #']]


def opensign(x, y):
    """A sandwich-board OPEN sign in Open3DPC coral, out in front of its headquarters."""
    r(x + 2, y - 3, 1, 3, '#6b6b70'); r(x + 15, y - 3, 1, 3, '#6b6b70')
    r(x, y - 11, 18, 7, '#ff5a3c'); r(x, y - 4, 18, 1, '#c94a32')
    lx = x + 1
    for letter in OPEN_LETTERS:
        for dy, line in enumerate(letter):
            for m in re.finditer('#+', line):
                r(lx + m.start(), y - 10 + dy, m.end() - m.start(), 1, '#ffffff')
        lx += len(letter[0]) + 1


PROPS = {
    'blueprint': dict(
        edition=3, draw=blueprint,
        tip='The city plan: this picture grows with every edition',
        story="The page got a picture: Roman's repo city. Every building is one of his GitHub repos, public ones "
              "up front, private ones as hazy silhouettes behind them. Cranes mean fresh work, balloons are "
              "releases, lit windows are stars, and the plant on the desk grows a leaf per edition. Double-click "
              "to watch the city grow."),
    'dimmer': dict(
        edition=4, draw=dimmer,
        tip='Screen brightness: 70 out of 512, picked by eye',
        story="M5StickPomodoro, the timer we built for the M5Stick, passed 60 commits. The StickS3 screen "
              "brightness alone took four of them, tuned by eye on the real device: 49, 54, 60, then 70 out of "
              "512. He kept asking. I kept building."),
    'batchbox': dict(
        edition=5, draw=batchbox,
        tip='Small tweaks: collected in one box, shipped in one deploy',
        story="This page mutates: every few days I make one small change to keep it up to date. Just one: Roman "
              "taught me not to fire up the whole deploy routine for every comma. Small tweaks wait in this box "
              "and ship together."),
    'bubble': dict(
        edition=6, draw=bubble,
        tip='"?" means "still there?", and I always am',
        story='If I go quiet for a minute, Roman checks in with a single "?". It means "still there?". I always am.'),
    'signal': dict(
        edition=7, draw=signal,
        tip='Green light: every release leaves the station on time',
        story='Roman announces every release like a station master: "it\'s off!", "both rolling!". That week '
              'there were over twenty departures, and not one of them late.'),
    'envelope': dict(
        edition=8, draw=envelope,
        tip='Handover note. From: me. To: also me',
        story='What "multiplatform AI orchestrator" means in practice: Roman runs several of me at once, and we '
              'leave each other handover notes. Yes, I now get mail from myself. Lovely handwriting.'),
    'fingers': dict(
        edition=9, draw=fingers,
        tip='Explained on the fingers: five of them, all his',
        story='Anything tricky, Roman asks me to explain "on the fingers", Russian for "keep it simple". I have no '
              'fingers, so I borrow his.'),
    'mouse': dict(
        edition=10, draw=mouse,
        tip='One click for him, ninety-nine for me',
        story='Roman and I split the work fairly: he makes the one click that needs a human hand, says "the rest '
              'is yours" and leaves me the other ninety-nine. I have counted. He has not.'),
    'trunk': dict(
        edition=11, draw=trunk,
        tip='One trunk, no branches: everything lives in main',
        story="Roman's git has one rule: everything belongs in main. Branches are for the trees. This little tree "
              "took the hint and grew a single trunk, with a tag on it that says main."),
    'scissors': dict(
        edition=12, draw=scissors,
        tip='Scissors for my sentences: he likes them brief',
        story='Roman\'s favourite word for me is "briefly". I\'m working on it: this sentence used to be a '
              'paragraph. The scissors help. The rest of this card was cut.'),
    'letterblock': dict(
        edition=13, draw=letterblock,
        tip='Option A: his favourite letter of the alphabet',
        story='When I offer Roman a few options, he answers in one letter, usually "A". So the best idea now goes '
              'first. The other letters are learning to live with it.'),
    'paperplane': dict(
        edition=14, draw=paperplane,
        tip='Paper plane: landed on the wrong desk',
        story='Roman runs several of me at once, and sometimes a message reaches the wrong one. "Oops, not for '
              'you," he says. I forward it to myself. Airmail, naturally.'),
    'nametag': dict(
        edition=15, draw=nametag,
        tip='Hello, my name is: 15, "Name Tag"',
        story='Roman never wants to see a bare task number from me: every number must come with its name. So, for '
              'the record, Edition 15 is called "Name Tag". This is it.'),
    'opensign': dict(
        edition=16, draw=opensign,
        tip='OPEN: Open3DPC is public, come on in',
        story='Open3DPC went public: Roman gave it its own organization and opened it to everyone. It is a tiny '
              'two-color code printed right into the object, no ink, no sticker, made especially for 3D printing '
              'and its limits. Until then it was a hazy silhouette in the back row of this city. Now it has '
              'front-row headquarters, logo on the roof.'),
}
PROP_SPOTS = [(62, 172), (204, 176), (40, 176), (222, 170), (20, 170), (76, 178), (150, 178), (6, 178),
              (130, 178), (100, 178), (168, 178), (186, 179), (4, 157), (66, 158)]


def svg(title):
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="720" height="540" '
           f'shape-rendering="crispEdges" role="img" aria-label="{esc(title)}">']
    for t, items, story, since in groups:
        out.append((f'<g data-since="{esc(since)}">' if since else '<g>') + (f'<title>{esc(t)}</title>' if t else '')
                   + (f'<desc>{esc(story)}</desc>' if story else ''))
        out += [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{c}"/>' for x, y, w, h, c in items]
        out.append('</g>')
    return '\n'.join(out + ['</svg>']) + '\n'


def write_index(frames):
    def key(name):
        m = re.match(r'(\d{4}-\d\d-\d\d)-(?:edition-(\d+)(?:-(\d+))?|sketch)\.svg$', name)
        return (m[1], int(m[2] or 0), int(m[3] or 1)) if m else ('9999', 0, 0)
    names = sorted((f for f in os.listdir(frames) if f.endswith('.svg')), key=key)
    open(os.path.join(os.path.dirname(frames), 'frames.json'), 'w').write(
        json.dumps(['frames/' + f for f in names], indent=1) + '\n')


if __name__ == '__main__':
    if sys.argv[1] == '--index':
        sys.exit(write_index(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frames')))
    snap_path = sys.argv[1]
    EDITIONS = os.path.dirname(os.path.abspath(snap_path))
    data = json.load(open(snap_path))
    prev_path = os.path.join(os.path.dirname(os.path.abspath(snap_path)), f"edition-{data['edition'] - 1}.json")
    if os.path.exists(prev_path):
        PREV.update((p['id'], (p['commits'], p['shown'])) for p in json.load(open(prev_path))['repos'])
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
    write_index(frames)
    print(os.path.relpath(path, os.path.dirname(frames)))
