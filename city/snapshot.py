"""Snapshot of romanaerl's GitHub for the city picture (needs a logged-in `gh`).

Repos are identified by their numeric GitHub ID: it survives renames and says nothing about the name.
A real name is kept only for repos shown in full: public ones and private ones listed in
allow-private.txt. Other private repos keep only numbers: commits, dates, links.

usage: python3 snapshot.py --edition 3 --date 2026-10-20 --prev editions/edition-2.json --out editions/edition-3.json
"""
import argparse, base64, json, os, re, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
OWNER = 'romanaerl'
MANIFESTS = ['.gitmodules', 'package.json', 'composer.json', 'requirements.txt', 'pyproject.toml', 'go.mod',
             'Cargo.toml', 'platformio.ini', 'Gemfile', 'Podfile', 'Package.swift', 'build.gradle', 'pubspec.yaml']


def gh(path, headers=False):
    p = subprocess.run(['gh', 'api', path] + (['-i'] if headers else []), capture_output=True, text=True)
    return p.stdout if p.returncode == 0 else None


def count(path):
    """Number of items behind a list endpoint, read from the pagination header."""
    out = gh(path + ('&' if '?' in path else '?') + 'per_page=1', headers=True)
    if out is None:
        return 0
    m = re.search(r'[?&]page=(\d+)>; rel="last"', out)
    return int(m.group(1)) if m else int(out.rstrip().endswith('}]'))


def file_text(full, path):
    out = gh(f'repos/{full}/contents/{path}')
    try:
        return base64.b64decode(json.loads(out)['content']).decode('utf-8', 'replace') if out else ''
    except (ValueError, KeyError):
        return ''


def allowed_private():
    path = os.path.join(HERE, 'allow-private.txt')
    if not os.path.exists(path):
        return set()
    lines = (l.strip() for l in open(path, encoding='utf-8'))
    return {l.lower() for l in lines if l and not l.startswith('#')}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--edition', type=int, required=True)
    ap.add_argument('--date', required=True)
    ap.add_argument('--prev')
    ap.add_argument('--since', help='date of the previous edition, when there is no --prev snapshot')
    ap.add_argument('--out', required=True)
    args = ap.parse_args()
    prev = json.load(open(args.prev)) if args.prev else {}

    raw = subprocess.run(['gh', 'api', '--paginate', 'user/repos?affiliation=owner&per_page=100', '--jq', '.[]'],
                         capture_output=True, text=True, check=True).stdout
    repos = sorted((json.loads(l) for l in raw.splitlines() if l.strip()), key=lambda r: r['created_at'])
    allow = allowed_private()
    by_name = {r['name'].lower(): r for r in repos}

    out_repos, links = [], set()
    for r in repos:
        full, name = r['full_name'], r['name']
        shown = not r['private'] or name.lower() in allow
        rec = {'id': str(r['id']), 'shown': shown, 'fork': r['fork'], 'archived': r['archived'],
               'created': r['created_at'][:10], 'pushed': r['pushed_at'][:10],
               'commits': 0 if r['fork'] else count(f'repos/{full}/commits')}
        if shown:
            rec.update(label=name, lang=r['language'], stars=r['stargazers_count'],
                       releases=count(f'repos/{full}/releases'))
        out_repos.append(rec)
        if r['fork']:
            continue
        # dependency links: submodules and manifests that point at another romanaerl repo
        text = '\n'.join(file_text(full, m) for m in MANIFESTS)
        for ref in re.findall(OWNER + r'/([A-Za-z0-9._-]+?)(?:\.git)?(?=[\s"\'#@/]|$)', text, re.M):
            if ref.lower() in by_name and ref.lower() != name.lower():
                links.add((*sorted([str(r['id']), str(by_name[ref.lower()]['id'])]), 'dep'))

    # family links: same name prefix before the first '-' (4+ letters), chained in creation order
    families = {}
    for r in repos:
        head = r['name'].lower().split('-')[0]
        if len(head) >= 4 and not r['fork']:
            families.setdefault(head, []).append(str(r['id']))
    for members in families.values():
        for a, b in zip(members, members[1:]):
            links.add((*sorted([a, b]), 'family'))

    snap = {'edition': args.edition, 'date': args.date, 'prev_date': prev.get('date', args.since or args.date),
            'repos': out_repos, 'links': [{'a': a, 'b': b, 'kind': k} for a, b, k in sorted(links)],
            'slots': prev.get('slots', {}), 'back_lots': prev.get('back_lots', {}),
            'props': prev.get('props', {})}
    text = json.dumps(snap, indent=1)
    # self-check: no hidden private name may end up in the file
    for r in repos:
        if r['private'] and r['name'].lower() not in allow:
            assert r['name'].lower() not in text.lower(), 'a private name leaked into the snapshot'
    open(args.out, 'w').write(text + '\n')


if __name__ == '__main__':
    main()
