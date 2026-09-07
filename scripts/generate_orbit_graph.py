#!/usr/bin/env python3
import os, json, math, html, calendar, urllib.request, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

USER = os.environ.get('GITHUB_REPOSITORY_OWNER', 'UNKN0WN006')
TOKEN = os.environ['GITHUB_TOKEN']
OUT = Path('assets/github-solar-orbit.svg')
OUT.parent.mkdir(parents=True, exist_ok=True)

TZ = ZoneInfo('Asia/Kolkata')
today = datetime.datetime.now(TZ).date()
year = today.year
year_start = datetime.date(year, 1, 1)
days_in_year = 366 if calendar.isleap(year) else 365
day_number = (today - year_start).days + 1

query = '''
query($login:String!, $from:DateTime!, $to:DateTime!) {
  user(login:$login) {
    contributionsCollection(from:$from, to:$to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
'''

payload = json.dumps({
    'query': query,
    'variables': {
        'login': USER,
        'from': year_start.isoformat() + 'T00:00:00Z',
        'to': today.isoformat() + 'T23:59:59Z',
    }
}).encode()
req = urllib.request.Request(
    'https://api.github.com/graphql',
    data=payload,
    headers={
        'Authorization': f'Bearer {TOKEN}',
        'Content-Type': 'application/json',
        'User-Agent': 'github-solar-orbit'
    }
)
with urllib.request.urlopen(req, timeout=30) as r:
    data = json.loads(r.read().decode())
if data.get('errors'):
    raise RuntimeError(data['errors'])

counts_by_date = {}
for week in data['data']['user']['contributionsCollection']['contributionCalendar']['weeks']:
    for item in week['contributionDays']:
        dt = datetime.date.fromisoformat(item['date'])
        if year_start <= dt <= today:
            counts_by_date[dt] = int(item['contributionCount'])

all_days = []
for i in range(days_in_year):
    dt = year_start + datetime.timedelta(days=i)
    all_days.append((dt, counts_by_date.get(dt, 0)))

past_counts = [c for dt, c in all_days if dt <= today]
total = sum(past_counts)
active_days = sum(1 for c in past_counts if c > 0)
longest = run = 0
for c in past_counts:
    if c > 0:
        run += 1
        longest = max(longest, run)
    else:
        run = 0
current = 0
for c in reversed(past_counts):
    if c > 0:
        current += 1
    else:
        break
max_count = max(past_counts) if past_counts else 0

def level(c):
    if c <= 0:
        return 0
    if max_count <= 1:
        return 4
    ratio = c / max_count
    if ratio <= 0.20:
        return 1
    if ratio <= 0.45:
        return 2
    if ratio <= 0.70:
        return 3
    return 4

palette = {
    'future': '#1d2740',
    0: '#31415f',
    1: '#06b6d4',
    2: '#22c55e',
    3: '#8b5cf6',
    4: '#ec4899',
}

recent_rows = []
try:
    events_req = urllib.request.Request(
        f'https://api.github.com/users/{USER}/events/public?per_page=100',
        headers={
            'Authorization': f'Bearer {TOKEN}',
            'Accept': 'application/vnd.github+json',
            'User-Agent': 'github-solar-orbit'
        }
    )
    with urllib.request.urlopen(events_req, timeout=30) as r:
        events = json.loads(r.read().decode())

    for ev in events:
        created = ev.get('created_at')
        if not created:
            continue
        dt = datetime.datetime.fromisoformat(created.replace('Z', '+00:00')).astimezone(TZ).date()
        repo = ev.get('repo', {}).get('name', '').split('/')[-1] or 'github'
        et = ev.get('type', '')
        payload = ev.get('payload', {})
        notes = []
        if et == 'PushEvent':
            for c in payload.get('commits', [])[:2]:
                msg = (c.get('message') or 'commit').splitlines()[0].strip()
                if msg:
                    notes.append(msg)
        elif et == 'PullRequestEvent':
            title = (payload.get('pull_request', {}) or {}).get('title', '')
            action = payload.get('action', 'updated')
            if title:
                notes.append(f'{action} PR: {title}')
        elif et == 'IssuesEvent':
            title = (payload.get('issue', {}) or {}).get('title', '')
            action = payload.get('action', 'updated')
            if title:
                notes.append(f'{action} issue: {title}')
        elif et == 'CreateEvent':
            ref_type = payload.get('ref_type', 'repository')
            ref = payload.get('ref')
            notes.append(f'created {ref_type}' + (f': {ref}' if ref else ''))
        for note in notes:
            recent_rows.append((dt, repo, note[:88]))
    seen = set()
    deduped = []
    for row in recent_rows:
        if row not in seen:
            seen.add(row)
            deduped.append(row)
    recent_rows = deduped[:5]
except Exception:
    recent_rows = []

W, H = 1200, 760
cx, cy = 600, 285
rx, ry = 420, 165

def xy_for_index(index):
    theta = -math.pi / 2 + (2 * math.pi * index / days_in_year)
    x = cx + rx * math.cos(theta)
    y = cy + ry * math.sin(theta)
    return x, y

markers = []
for i, (dt, count) in enumerate(all_days):
    x, y = xy_for_index(i)
    future = dt > today
    fill = palette['future'] if future else palette[level(count)]
    opacity = 0.33 if future else (0.58 if count == 0 else 1.0)
    radius = 2.1 if future else (2.5 if count == 0 else 3.8 + min(1.8, level(count) * 0.45))
    tooltip = f"{dt.isoformat()} - {count} contribution{'s' if count != 1 else ''}"
    markers.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius:.2f}" fill="{fill}" opacity="{opacity:.2f}"><title>{html.escape(tooltip)}</title></circle>')

months = []
for month in range(1, 13):
    dt = datetime.date(year, month, 1)
    idx = (dt - year_start).days
    x, y = xy_for_index(idx)
    dx = x - cx
    dy = y - cy
    norm = (dx * dx + dy * dy) ** 0.5 or 1
    lx = x + 30 * dx / norm
    ly = y + 22 * dy / norm
    months.append(f'<text x="{lx:.2f}" y="{ly:.2f}" text-anchor="middle" fill="#8cb4ff" font-family="monospace" font-size="12" font-weight="700">{dt.strftime("%b").upper()}</text>')

earth_x, earth_y = xy_for_index(day_number - 1)

activity_lines = []
if recent_rows:
    for i, (dt, repo, note) in enumerate(recent_rows):
        y = 644 + i * 18
        activity_lines.append(f'<text x="66" y="{y}" fill="#f59e0b" font-family="monospace" font-size="11" font-weight="700">{dt.strftime("%b %d").upper()}</text>')
        activity_lines.append(f'<text x="146" y="{y}" fill="#38bdf8" font-family="monospace" font-size="11">{html.escape(repo[:18])}</text>')
        activity_lines.append(f'<text x="302" y="{y}" fill="#dbeafe" font-family="monospace" font-size="11">{html.escape(note[:92])}</text>')
else:
    activity_lines.append('<text x="66" y="650" fill="#64748b" font-family="monospace" font-size="11">Recent public event details are limited; the orbit itself still uses real contribution-calendar data.</text>')

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
  <linearGradient id="topline" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="#22d3ee"/>
    <stop offset="25%" stop-color="#22c55e"/>
    <stop offset="50%" stop-color="#f59e0b"/>
    <stop offset="75%" stop-color="#8b5cf6"/>
    <stop offset="100%" stop-color="#ec4899"/>
  </linearGradient>
  <radialGradient id="sunFill" cx="50%" cy="50%" r="55%">
    <stop offset="0%" stop-color="#fff7b0"/>
    <stop offset="35%" stop-color="#fbbf24"/>
    <stop offset="72%" stop-color="#f97316"/>
    <stop offset="100%" stop-color="#b91c1c"/>
  </radialGradient>
  <radialGradient id="sunHalo" cx="50%" cy="50%" r="70%">
    <stop offset="0%" stop-color="#f59e0b" stop-opacity="0.60"/>
    <stop offset="60%" stop-color="#f97316" stop-opacity="0.18"/>
    <stop offset="100%" stop-color="#f97316" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="earthFill" cx="35%" cy="30%" r="80%">
    <stop offset="0%" stop-color="#93c5fd"/>
    <stop offset="55%" stop-color="#2563eb"/>
    <stop offset="100%" stop-color="#172554"/>
  </radialGradient>
  <filter id="softGlow" x="-50%" y="-50%" width="200%" height="200%">
    <feGaussianBlur stdDeviation="10" result="g"/>
    <feMerge><feMergeNode in="g"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
</defs>
<rect width="{W}" height="{H}" rx="24" fill="#080d18"/>
<rect x="18" y="18" width="{W-36}" height="{H-36}" rx="20" fill="#0f172a" stroke="#334155" stroke-width="2"/>
<rect x="18" y="18" width="{W-36}" height="4" rx="2" fill="url(#topline)"/>

<text x="48" y="58" fill="#f8fafc" font-family="monospace" font-size="22" font-weight="700">GITHUB SOLAR ORBIT / {year}</text>
<text x="1138" y="58" text-anchor="end" fill="#22d3ee" font-family="monospace" font-size="15" font-weight="700">DAY {day_number} / {days_in_year}</text>
<text x="48" y="83" fill="#64748b" font-family="monospace" font-size="12">one marker = one calendar day | Earth = today | future days stay dim</text>

<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="none" stroke="#45608b" stroke-width="2.6" opacity="0.88"/>
<ellipse cx="{cx}" cy="{cy}" rx="{rx-24}" ry="{ry-10}" fill="none" stroke="#23314f" stroke-width="1.2" stroke-dasharray="6 8" opacity="0.85"/>
{''.join(months)}
{''.join(markers)}

<circle cx="{cx}" cy="{cy}" r="78" fill="url(#sunHalo)" filter="url(#softGlow)"/>
<circle cx="{cx}" cy="{cy}" r="42" fill="url(#sunFill)" filter="url(#softGlow)"/>
<circle cx="{cx}" cy="{cy}" r="58" fill="none" stroke="#f59e0b" stroke-width="1.3" opacity="0.28"/>
<circle cx="{cx}" cy="{cy}" r="66" fill="none" stroke="#fb7185" stroke-width="0.8" opacity="0.18"/>
<text x="{cx}" y="{cy+78}" text-anchor="middle" fill="#fbbf24" font-family="monospace" font-size="12" font-weight="700">SUN / YEAR {year}</text>

<g filter="url(#softGlow)">
  <circle cx="{earth_x:.2f}" cy="{earth_y:.2f}" r="19" fill="url(#earthFill)" stroke="#dbeafe" stroke-width="2"/>
  <path d="M {earth_x-11:.2f} {earth_y-4:.2f} q 8 -8 16 -2 q -3 6 0 10 q -10 4 -16 -1z" fill="#22c55e" opacity="0.92"/>
  <path d="M {earth_x+2:.2f} {earth_y+6:.2f} q 8 -5 12 1 q -4 7 -11 7z" fill="#4ade80" opacity="0.82"/>
</g>
<line x1="{earth_x:.2f}" y1="{earth_y+22:.2f}" x2="{earth_x:.2f}" y2="{earth_y+48:.2f}" stroke="#38bdf8" stroke-width="1.2"/>
<text x="{earth_x:.2f}" y="{earth_y+64:.2f}" text-anchor="middle" fill="#bae6fd" font-family="monospace" font-size="11" font-weight="700">EARTH / {today.strftime('%b %d').upper()}</text>

<g>
  <rect x="78" y="480" width="240" height="80" rx="14" fill="#082f49" stroke="#06b6d4"/>
  <text x="198" y="518" text-anchor="middle" fill="#67e8f9" font-family="monospace" font-size="28" font-weight="700">{total}</text>
  <text x="198" y="540" text-anchor="middle" fill="#dbeafe" font-family="monospace" font-size="11">CONTRIBUTIONS / YTD</text>

  <rect x="338" y="480" width="240" height="80" rx="14" fill="#052e16" stroke="#22c55e"/>
  <text x="458" y="518" text-anchor="middle" fill="#86efac" font-family="monospace" font-size="28" font-weight="700">{active_days}</text>
  <text x="458" y="540" text-anchor="middle" fill="#dcfce7" font-family="monospace" font-size="11">ACTIVE DAYS / {day_number}</text>

  <rect x="598" y="480" width="240" height="80" rx="14" fill="#3b0764" stroke="#8b5cf6"/>
  <text x="718" y="518" text-anchor="middle" fill="#ddd6fe" font-family="monospace" font-size="28" font-weight="700">{longest}</text>
  <text x="718" y="540" text-anchor="middle" fill="#ede9fe" font-family="monospace" font-size="11">LONGEST STREAK</text>

  <rect x="858" y="480" width="240" height="80" rx="14" fill="#4c0519" stroke="#e11d48"/>
  <text x="978" y="518" text-anchor="middle" fill="#fda4af" font-family="monospace" font-size="28" font-weight="700">{current}</text>
  <text x="978" y="540" text-anchor="middle" fill="#ffe4e6" font-family="monospace" font-size="11">CURRENT STREAK</text>
</g>

<text x="78" y="585" fill="#64748b" font-family="monospace" font-size="11">ACTIVITY</text>
<circle cx="152" cy="581" r="5" fill="#31415f"/><text x="164" y="585" fill="#64748b" font-family="monospace" font-size="10">0</text>
<circle cx="196" cy="581" r="5" fill="#06b6d4"/><circle cx="218" cy="581" r="5" fill="#22c55e"/><circle cx="240" cy="581" r="5" fill="#8b5cf6"/><circle cx="262" cy="581" r="5" fill="#ec4899"/>
<text x="277" y="585" fill="#94a3b8" font-family="monospace" font-size="10">MORE</text>
<text x="1088" y="585" text-anchor="end" fill="#64748b" font-family="monospace" font-size="11">leap-aware | {days_in_year} positions</text>

<line x1="48" y1="602" x2="1152" y2="602" stroke="#334155"/>
<text x="66" y="624" fill="#f8fafc" font-family="monospace" font-size="13" font-weight="700">LATEST ORBIT LOG / RECENT PUBLIC ACTIVITY</text>
{''.join(activity_lines)}
<text x="66" y="736" fill="#64748b" font-family="monospace" font-size="10">The orbit is the main view. The log below is best-effort from GitHub's recent public events feed.</text>
</svg>'''
OUT.write_text(svg, encoding='utf-8')
