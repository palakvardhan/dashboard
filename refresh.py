"""
refresh.py — Pull live data from Metabase and update index.html

Usage:
  python refresh.py            # update index.html with fresh data
  python refresh.py --discover # list all Metabase cards to find missing IDs
"""
import urllib.request, json, re, datetime, sys

MB_KEY = 'mb_1dsbxsJfyROPsVyNpifJ8hTTlIDG85+qNKRo91KDnb4='
BASE   = 'https://metabase.wiom.in/api'
HTML   = 'C:/Users/Palak Vardhan/dashboard/index.html'

# ── Card IDs ─────────────────────────────────────────────────────────────────
# Run `python refresh.py --discover` to list all cards and fill in the Nones.
CARD_SUMMARY     = 10438   # Summary: D-1, D-2, D-3, MTD
CARD_RES_TREND   = 10446   # L2 Res% Trend — last 7 days
CARD_PARTNER_CAT = 10439   # Partner Category — D-1

CARD_TAT_TREND   = 10447   # Median TAT Trend — last 7 days
CARD_SUB_STATUS  = 10444   # Sub-Status Distribution — D-1
CARD_TOP_ISSUES  = 10442   # Top 15 Issues — Yesterday (L2 First)
CARD_BREAKDOWN   = 10448   # Issue Breakdown — last 7 days
CARD_PSAT        = 10449   # PSAT Calling Sheet — D-1

# ── Metabase helpers ─────────────────────────────────────────────────────────

def _req(path, method='GET', body=None):
    req = urllib.request.Request(f'{BASE}{path}', method=method)
    req.add_header('x-api-key', MB_KEY)
    req.add_header('Content-Type', 'application/json')
    if body is not None:
        req.data = body if isinstance(body, bytes) else body.encode()
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read())


def run_card(card_id):
    """Execute a card query; return (col_names, rows)."""
    data = _req(f'/card/{card_id}/query', method='POST', body=b'{}')
    cols = [c['name'] for c in data['data']['cols']]
    rows = data['data']['rows']
    return cols, rows


def discover_cards():
    print('Fetching card list from Metabase…')
    cards = _req('/card?f=all')
    print(f'\n{"ID":>8}  {"Name"}')
    print('─' * 72)
    for c in sorted(cards, key=lambda x: x['id']):
        print(f'{c["id"]:>8}  {c["name"][:64]}')
    print(f'\nTotal: {len(cards)} cards')

# ── Formatters ────────────────────────────────────────────────────────────────

def _v(v):
    """Python value → JS literal."""
    if v is None:
        return 'null'
    if isinstance(v, str):
        return json.dumps(v)
    if isinstance(v, bool):
        return 'true' if v else 'false'
    return str(v)


def _date_label(raw):
    """'2026-03-05' or date-like → '5 Mar'"""
    s = str(raw)[:10]
    try:
        dt = datetime.datetime.strptime(s, '%Y-%m-%d')
        return f'{dt.day} {dt.strftime("%b")}'
    except Exception:
        return s


def rows_to_js(rows):
    """List[list] → JS array literal."""
    inner = ',\n'.join('  [' + ', '.join(_v(v) for v in r) + ']' for r in rows)
    return f'[\n{inner}\n]'


def summary_js(rows):
    return rows_to_js(rows)


def res_trend_js(rows):
    # cols: Date, L2 Res%, L2 Res% <=24h
    labels   = [_date_label(r[0]) for r in rows]
    values   = [r[1] if r[1] is not None else 'null' for r in rows]
    values24 = [r[2] if r[2] is not None else 'null' for r in rows]
    return (
        '{\n'
        f'  labels: {json.dumps(labels)},\n'
        f'  values: [{", ".join(str(v) for v in values)}],\n'
        f'  values24h: [{", ".join(str(v) for v in values24)}]\n'
        '}'
    )


def tat_trend_js(rows):
    # cols: Date, Median TAT
    labels = [_date_label(r[0]) for r in rows]
    values = [r[1] if r[1] is not None else 'null' for r in rows]
    return (
        '{\n'
        f'  labels: {json.dumps(labels)},\n'
        f'  values: [{", ".join(str(v) for v in values)}]\n'
        '}'
    )

# ── HTML patcher ──────────────────────────────────────────────────────────────

def _replace_var(html, var_name, new_value):
    """
    Replace `const <var_name> = <array or object>;` in the HTML.
    Handles both [...] and {...} value forms.
    """
    # We match lazily so we stop at the first valid closing ] or }
    pattern = (
        r'(const ' + re.escape(var_name) + r'\s*=\s*)'
        r'(\[[\s\S]*?\]|\{[\s\S]*?\})'
        r'(\s*;)'
    )
    result, n = re.subn(pattern, r'\g<1>' + new_value.replace('\\', '\\\\') + r'\g<3>',
                        html, count=1)
    if n == 0:
        print(f'  WARNING: pattern not found for {var_name}')
    return result

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    if '--discover' in sys.argv:
        discover_cards()
        return

    with open(HTML, 'r', encoding='utf-8') as f:
        html = f.read()

    original = html
    skipped  = []

    def fetch_and_patch(card_id, var_name, builder, label):
        nonlocal html
        if card_id is None:
            skipped.append(var_name)
            return
        print(f'  [{card_id}] {label}…', end=' ', flush=True)
        try:
            cols, rows = run_card(card_id)
            print(f'{len(rows)} rows')
            html = _replace_var(html, var_name, builder(rows))
        except Exception as e:
            print(f'ERROR — {e}')

    print('Refreshing dashboard data from Metabase…\n')
    fetch_and_patch(CARD_SUMMARY,     'summaryData',    summary_js,   'Summary D-1/D-2/D-3/MTD')
    fetch_and_patch(CARD_RES_TREND,   'resTrendData',   res_trend_js, 'L2 Res% Trend')
    fetch_and_patch(CARD_PARTNER_CAT, 'partnerCatData', rows_to_js,   'Partner Category')
    fetch_and_patch(CARD_TAT_TREND,   'tatTrendData',   tat_trend_js, 'Median TAT Trend')
    fetch_and_patch(CARD_SUB_STATUS,  'subStatusData',  rows_to_js,   'Sub-Status Distribution')
    fetch_and_patch(CARD_TOP_ISSUES,  'topIssuesData',  rows_to_js,   'Top 15 Issues')
    fetch_and_patch(CARD_BREAKDOWN,   'breakdownData',  rows_to_js,   'Issue Breakdown')
    fetch_and_patch(CARD_PSAT,        'psatRaw',        rows_to_js,   'PSAT Calling Sheet')

    if skipped:
        print(f'\nSkipped (no card ID set): {", ".join(skipped)}')
        print('  → Run `python refresh.py --discover` to list all cards and fill in the IDs above.')

    if html != original:
        with open(HTML, 'w', encoding='utf-8') as f:
            f.write(html)
        print('\n✓ index.html updated.')
    else:
        print('\nNo changes written (data may be the same, or all cards were skipped).')


if __name__ == '__main__':
    main()
