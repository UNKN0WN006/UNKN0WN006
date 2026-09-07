#!/usr/bin/env python3
import os, json, math, html, calendar, urllib.request, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

USER = os.environ.get('GITHUB_REPOSITORY_OWNER', 'UNKN0WN006')
TOKEN = os.environ['GITHUB_TOKEN']
OUT = Path('assets/github-solar-orbit.svg')
OUT.parent.mkdir(parents=True, exist_ok=True)

today = datetime.datetime.now(ZoneInfo('Asia/Kolkata')).date()
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
        weeks { contributionDays { date contributionCount } }
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
        'to': today.isoformat() + 'T23:59:59Z'
    }
}).encode()

req = urllib.request.Request(
    'https://api.github.com/graphql', data=payload,
    headers={
        'Authorization': f'Bearer {TOKEN}',
        'Content-Type': 'application/json',
        'User-Agent': 'sushar-solar-orbit'
    }
)
with urllib.request.urlopen(req, timeout=30) as r:
    gql = json.loads(r.read().decode())
if gql.get('errors'):
    raise RuntimeError(gql['errors'])

counts_by_date = {}
for week in gql['data']['user']['contributionsCollection']['contributionCalendar']['weeks']:
    for item in week['contributionDays']:
        dt = datetime.date.fromisoformat(item['date'])
        if year_start <= dt <= today:
            counts_by_date[dt] = int(item['contributionCount'])

all_days = []
for i in range(days_in_year):
    dt = year_start + datetime.timedelta(days=i)
    all_days.append((dt, counts_by_date.get(dt, 0)))

past_counts = [c for d,c in all_days if d <= today]
total_contributions = sum(past_counts)
active_days = sum(1 for c in past_counts if c > 0)

longest_streak = run = 0
for c in past_counts:
    if c > 0:
        run += 1
        longest_streak = max(longest_streak, run)
    else:
        run = 0
current_streak = 0
for c in reversed(past_counts):
    if c > 0:
        current_streak += 1
    else:
        break

max_count = max(past_counts) if past_counts else 0

def intensity(c):
    if c <= 0: return 0
    if max_count <= 1: return 4
    r = c/max_count
    if r <= .20: return 1
    if r <= .45: return 2
    if r <= .70: return 3
    return 4

palette = {'future':'#182235', 0:'#263247', 1:'#0e7490', 2:'#10b981', 3:'#8b5cf6', 4:'#ec4899'}

# Best-effort recent public activity detail.
recent_rows = []
notes_by_date = {}
try:
    ev_req = urllib.request.Request(
        f'https://api.github.com/users/{USER}/events/public?per_page=100',
        headers={
            'Authorization': f'Bearer {TOKEN}',
            'Accept': 'application/vnd.github+json',
            'User-Agent': 'sushar-solar-orbit'
        }
    )
    with urllib.request.urlopen(ev_req, timeout=30) as r:
        events = json.loads(r.read().decode())

    for event in events:
        created = event.get('created_at')
        if not created: continue
        event_date = datetime.datetime.fromisoformat(created.replace('Z','+00:00')).astimezone(ZoneInfo('Asia/Kolkata')).date()
        repo = event.get('repo',{}).get('name','').split('/')[-1] or 'github'
        typ = event.get('type','')
        payload2 = event.get('payload',{})
        summaries = []
        if typ == 'PushEvent':
            for commit in payload2.get('commits',[])[:3]:
                msg = (commit.get('message') or 'commit').splitlines()[0].strip()
                if msg: summaries.append(msg)
        elif typ == 'PullRequestEvent':
            pr = payload2.get('pull_request',{})
            summaries.append(f"{payload2.get('action','')} PR: {(pr.get('title') or 'pull request').strip()}")
        elif typ == 'IssuesEvent':
            issue = payload2.get('issue',{})
            summaries.append(f"{payload2.get('action','')} issue: {(issue.get('title') or 'issue').strip()}")
        elif typ == 'CreateEvent':
            ref_type = payload2.get('ref_type','repository')
            ref = payload2.get('ref')
            summaries.append('created ' + ref_type + (f': {ref}' if ref else ''))
        for summary in summaries:
            summary = summary[:82]
            notes_by_date.setdefault(event_date, []).append(f'{repo}: {summary}')
            recent_rows.append((event_date, repo, summary))
    seen=set(); ded=[]
    for row in recent_rows:
        key=(row[0],row[1],row[2])
        if key not in seen:
            seen.add(key); ded.append(row)
    recent_rows = ded[:5]
except Exception:
    recent_rows = []

W,H = 1200,690
cx,cy = 600,302
rx,ry = 450,188

def xy(i, ax=rx, ay=ry):
    theta = -math.pi/2 + 2*math.pi*i/days_in_year
    return cx + ax*math.cos(theta), cy + ay*math.sin(theta), theta

markers=[]
for i,(dt,count) in enumerate(all_days):
    x,y,_ = xy(i)
    future = dt > today
    fill = palette['future'] if future else palette[intensity(count)]
    opacity = .35 if future else (.52 if count==0 else 1)
    radius = 2.1 if future or count==0 else 3.5 + min(2.4, intensity(count)*.55)
    note = ''
    if dt in notes_by_date:
        note = ' | ' + ' ; '.join(notes_by_date[dt][:2])
    tooltip = html.escape(f"{dt.isoformat()} — {count} contribution{'s' if count != 1 else ''}{note}")
    markers.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{radius:.2f}" fill="{fill}" opacity="{opacity:.2f}"><title>{tooltip}</title></circle>')

months=[]
for month in range(1,13):
    dt=datetime.date(year,month,1)
    idx=(dt-year_start).days
    x,y,_=xy(idx,rx+48,ry+30)
    months.append(f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="middle" fill="#94a3b8" font-family="monospace" font-size="12" font-weight="700">{dt.strftime("%b").upper()}</text>')

earth_x,earth_y,_=xy(day_number-1)

activity=[]
if recent_rows:
    for idx,(dt,repo,summary) in enumerate(recent_rows):
        y=558+idx*24
        activity.append(f'<text x="60" y="{y}" fill="#f59e0b" font-family="monospace" font-size="12" font-weight="700">{dt.strftime("%b %d").upper()}</text>')
        activity.append(f'<text x="145" y="{y}" fill="#22d3ee" font-family="monospace" font-size="12">{html.escape(repo[:24])}</text>')
        activity.append(f'<text x="360" y="{y}" fill="#cbd5e1" font-family="monospace" font-size="12">{html.escape(summary[:88])}</text>')
else:
    activity.append('<text x="60" y="575" fill="#64748b" font-family="monospace" font-size="12">No recent public event details were available during this refresh.</text>')

orbit_path=f'M {cx-rx} {cy} a {rx} {ry} 0 1 0 {2*rx} 0 a {rx} {ry} 0 1 0 {-2*rx} 0'

svg=f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{W}" height="{H}" viewBox="0 0 {W} {H}">
<defs>
  <radialGradient id="sun" cx="45%" cy="40%"><stop offset="0%" stop-color="#fff7ae"/><stop offset="35%" stop-color="#fbbf24"/><stop offset="70%" stop-color="#f97316"/><stop offset="100%" stop-color="#991b1b"/></radialGradient>
  <radialGradient id="earth" cx="35%" cy="30%"><stop offset="0%" stop-color="#93c5fd"/><stop offset="55%" stop-color="#2563eb"/><stop offset="100%" stop-color="#172554"/></radialGradient>
  <linearGradient id="topline" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stop-color="#22d3ee"/><stop offset="25%" stop-color="#10b981"/><stop offset="50%" stop-color="#f59e0b"/><stop offset="75%" stop-color="#8b5cf6"/><stop offset="100%" stop-color="#ec4899"/></linearGradient>
  <filter id="sunGlow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="13" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <filter id="earthGlow" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="5" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
  <path id="orbitPath" d="{orbit_path}"/>
</defs>
<rect width="{W}" height="{H}" rx="24" fill="#080d18"/>
<rect x="18" y="18" width="{W-36}" height="{H-36}" rx="19" fill="#101827" stroke="#334155" stroke-width="2"/>
<rect x="18" y="18" width="{W-36}" height="4" rx="2" fill="url(#topline)"/>
<text x="48" y="58" fill="#f8fafc" font-family="monospace" font-size="22" font-weight="700">GITHUB SOLAR ORBIT / {year}</text>
<text x="1150" y="58" text-anchor="end" fill="#22d3ee" font-family="monospace" font-size="14">DAY {day_number} / {days_in_year}</text>
<text x="48" y="82" fill="#64748b" font-family="monospace" font-size="12">one marker = one calendar day · Earth = today · future days stay dim</text>
<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="none" stroke="#334155" stroke-width="1.5"/>
<ellipse cx="{cx}" cy="{cy}" rx="{rx-25}" ry="{ry-11}" fill="none" stroke="#1e293b" stroke-width="1" stroke-dasharray="4 7"/>
{''.join(months)}
{''.join(markers)}
<circle cx="{cx}" cy="{cy}" r="63" fill="#f59e0b" opacity=".14" filter="url(#sunGlow)"/>
<circle cx="{cx}" cy="{cy}" r="48" fill="url(#sun)" filter="url(#sunGlow)"/>
<circle cx="{cx-14}" cy="{cy-11}" r="8" fill="#fde68a" opacity=".65"/>
<path d="M {cx-24} {cy+5} Q {cx-5} {cy-8} {cx+18} {cy+4} T {cx+32} {cy+18}" fill="none" stroke="#7c2d12" stroke-width="4" opacity=".42"/>
<text x="{cx}" y="{cy+83}" text-anchor="middle" fill="#fbbf24" font-family="monospace" font-size="12" font-weight="700">YEAR / {year}</text>
<g filter="url(#earthGlow)"><circle cx="{earth_x:.2f}" cy="{earth_y:.2f}" r="20" fill="url(#earth)" stroke="#bae6fd" stroke-width="2"/><path d="M {earth_x-12:.2f} {earth_y-5:.2f} q 9 -10 17 -2 q -4 5 -1 10 q -10 4 -18 -1z" fill="#22c55e" opacity=".88"/><path d="M {earth_x+1:.2f} {earth_y+7:.2f} q 8 -5 13 1 q -4 8 -12 8z" fill="#4ade80" opacity=".8"/></g>
<line x1="{earth_x:.2f}" y1="{earth_y+23:.2f}" x2="{earth_x:.2f}" y2="{earth_y+47:.2f}" stroke="#38bdf8" stroke-width="1"/>
<text x="{earth_x:.2f}" y="{earth_y+64:.2f}" text-anchor="middle" fill="#bae6fd" font-family="monospace" font-size="11" font-weight="700">{today.strftime('%b %d').upper()}</text>
<g><circle cx="0" cy="0" r="5" fill="#f8fafc"/><path d="M -10 0 L -20 -5 L -18 5 Z" fill="#f59e0b"/><animateMotion dur="22s" repeatCount="indefinite" rotate="auto"><mpath xlink:href="#orbitPath"/></animateMotion></g>
<rect x="80" y="420" width="230" height="70" rx="12" fill="#082f49" stroke="#0e7490"/><text x="195" y="448" text-anchor="middle" fill="#67e8f9" font-family="monospace" font-size="24" font-weight="700">{total_contributions}</text><text x="195" y="471" text-anchor="middle" fill="#bae6fd" font-family="monospace" font-size="11">CONTRIBUTIONS / YTD</text>
<rect x="330" y="420" width="230" height="70" rx="12" fill="#052e16" stroke="#16a34a"/><text x="445" y="448" text-anchor="middle" fill="#86efac" font-family="monospace" font-size="24" font-weight="700">{active_days}</text><text x="445" y="471" text-anchor="middle" fill="#bbf7d0" font-family="monospace" font-size="11">ACTIVE DAYS / {day_number}</text>
<rect x="580" y="420" width="230" height="70" rx="12" fill="#3b0764" stroke="#9333ea"/><text x="695" y="448" text-anchor="middle" fill="#d8b4fe" font-family="monospace" font-size="24" font-weight="700">{longest_streak}</text><text x="695" y="471" text-anchor="middle" fill="#e9d5ff" font-family="monospace" font-size="11">LONGEST STREAK</text>
<rect x="830" y="420" width="230" height="70" rx="12" fill="#4c0519" stroke="#e11d48"/><text x="945" y="448" text-anchor="middle" fill="#fda4af" font-family="monospace" font-size="24" font-weight="700">{current_streak}</text><text x="945" y="471" text-anchor="middle" fill="#fecdd3" font-family="monospace" font-size="11">CURRENT STREAK</text>
<text x="80" y="518" fill="#64748b" font-family="monospace" font-size="11">ACTIVITY</text><circle cx="150" cy="514" r="5" fill="#263247"/><text x="162" y="518" fill="#64748b" font-family="monospace" font-size="10">0</text><circle cx="195" cy="514" r="5" fill="#0e7490"/><circle cx="217" cy="514" r="5" fill="#10b981"/><circle cx="239" cy="514" r="5" fill="#8b5cf6"/><circle cx="261" cy="514" r="5" fill="#ec4899"/><text x="276" y="518" fill="#94a3b8" font-family="monospace" font-size="10">MORE</text>
<text x="1130" y="518" text-anchor="end" fill="#64748b" font-family="monospace" font-size="11">leap-aware · {days_in_year} positions</text>
<line x1="48" y1="535" x2="1152" y2="535" stroke="#334155"/>
<text x="60" y="555" fill="#f8fafc" font-family="monospace" font-size="13" font-weight="700">LATEST ORBIT LOG / RECENT PUBLIC ACTIVITY</text>
{''.join(activity)}
<text x="60" y="676" fill="#64748b" font-family="monospace" font-size="10">event detail comes from GitHub's recent public events feed; orbital markers come from the contribution calendar</text>
</svg>'''

OUT.write_text(svg, encoding='utf-8')
print(f'Wrote {OUT}')
