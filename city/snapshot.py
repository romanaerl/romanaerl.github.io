"""Snapshot of romanaerl's GitHub for the city picture (needs a logged-in `gh`).

The city holds Roman's own repos and the repos of his organizations (ORGS). Repos are identified by their
numeric GitHub ID: it survives renames and transfers (a repo moved into an org keeps its lot) and says
nothing about the name. A real name and owner are kept only for repos shown in full: public ones and
private ones listed in allow-private.txt. Other private repos keep only numbers: commits, dates, links.
Push times stay out of the file (they would show the hours Roman works): the snapshot keeps only the time it
was taken itself and, per repo, `fresh`: whether it was pushed after the previous snapshot was taken.

usage: python3 snapshot.py --edition 3 --date 2026-10-20 --prev editions/edition-2.json --out editions/edition-3.json
"""
import argparse, base64, datetime, json, os, re, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
USER = 'romanaerl'
ORGS = ['Open3DPC']
OWNERS = [USER] + ORGS
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


def listing(path):
    raw = subprocess.run(['gh', 'api', '--paginate', path, '--jq', '.[]'],
                         capture_output=True, text=True, check=True).stdout
    return [json.loads(l) for l in raw.splitlines() if l.strip()]


def all_repos():
    """Roman's own repos plus every repo of his orgs (private ones stay hidden like his own), by ID."""
    found = {r['id']: r for r in listing('user/repos?affiliation=owner&per_page=100')}
    for org in ORGS:
        found.update((r['id'], r) for r in listing(f'orgs/{org}/repos?type=all&per_page=100'))
    return sorted(found.values(), key=lambda r: r['created_at'])


def is_allowed(r, allow):
    """allow-private.txt names a repo by its name or by owner/name."""
    return r['name'].lower() in allow or r['full_name'].lower() in allow


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--edition', type=int, required=True)
    ap.add_argument('--date', required=True)
    ap.add_argument('--prev')
    ap.add_argument('--since', help='date of the previous edition, when there is no --prev snapshot')
    ap.add_argument('--out', required=True)
    ap.add_argument('--prev-taken', help='UTC time the --prev snapshot was taken, e.g. 2026-11-25T11:02:43Z, '
                                         'for an old --prev file without "taken"')
    args = ap.parse_args()
    prev = json.load(open(args.prev)) if args.prev else {}
    taken = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    prev_taken = prev.get('taken') or args.prev_taken

    repos = all_repos()
    allow = allowed_private()
    by_full = {r['full_name'].lower(): r for r in repos}
    by_name = {}
    for r in repos:
        by_name.setdefault(r['name'].lower(), []).append(r)

    def resolve(owner, ref):
        """owner/ref from a manifest -> our repo; an old owner/ref of a repo moved into an org still finds it."""
        hit = by_full.get(f'{owner}/{ref}'.lower())
        same = by_name.get(ref.lower(), [])
        return hit or (same[0] if len(same) == 1 else None)

    ref_re = re.compile(r'\b(' + '|'.join(OWNERS) + r')/([A-Za-z0-9._-]+?)(?:\.git)?(?=[\s"\'#@/]|$)', re.M | re.I)
    out_repos, links = [], set()
    for r in repos:
        full, name = r['full_name'], r['name']
        shown = not r['private'] or is_allowed(r, allow)
        rec = {'id': str(r['id']), 'shown': shown, 'fork': r['fork'], 'archived': r['archived'],
               'created': r['created_at'][:10], 'pushed': r['pushed_at'][:10],
               'commits': 0 if r['fork'] else count(f'repos/{full}/commits')}
        if prev_taken:                                     # crane: pushed after the previous snapshot
            rec['fresh'] = r['pushed_at'] > prev_taken
        if shown:
            rec.update(label=name, owner=r['owner']['login'], lang=r['language'], stars=r['stargazers_count'],
                       releases=count(f'repos/{full}/releases'))
        out_repos.append(rec)
        if r['fork']:
            continue
        # dependency links: submodules and manifests that point at another repo of Roman or his orgs
        text = '\n'.join(file_text(full, m) for m in MANIFESTS)
        for owner, ref in ref_re.findall(text):
            other = resolve(owner, ref)
            if other and other['id'] != r['id']:
                links.add((*sorted([str(r['id']), str(other['id'])]), 'dep'))

    # family links: same name prefix before the first '-' (4+ letters), chained in creation order. Shown and
    # hidden repos are chained apart: a wire from a named repo to a hidden one would give away how the hidden
    # one's name starts.
    families = {}
    for r, rec in zip(repos, out_repos):
        head = r['name'].lower().split('-')[0]
        if len(head) >= 4 and not r['fork']:
            families.setdefault((head, rec['shown']), []).append(str(r['id']))
    for members in families.values():
        for a, b in zip(members, members[1:]):
            links.add((*sorted([a, b]), 'family'))

    snap = {'edition': args.edition, 'date': args.date, 'taken': taken,
            'prev_date': prev.get('date', args.since or args.date),
            'repos': out_repos, 'links': [{'a': a, 'b': b, 'kind': k} for a, b, k in sorted(links)],
            'slots': prev.get('slots', {}), 'back_lots': prev.get('back_lots', {}),
            'props': prev.get('props', {})}
    text = json.dumps(snap, indent=1)
    # self-check: no hidden private name may end up in the file
    for r in repos:
        if r['private'] and not is_allowed(r, allow):
            assert r['name'].lower() not in text.lower(), 'a private name leaked into the snapshot'
    open(args.out, 'w').write(text + '\n')


if __name__ == '__main__':
    main()
