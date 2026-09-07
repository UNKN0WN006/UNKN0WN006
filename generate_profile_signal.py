#!/usr/bin/env python3
import os, json, urllib.request, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

USER = os.environ.get('GITHUB_REPOSITORY_OWNER', 'UNKN0WN006')
TOKEN = os.environ['GITHUB_TOKEN']
OUT_DARK = Path('profile/developer-signal-dark.svg')
OUT_LIGHT = Path('profile/developer-signal-light.svg')
OUT_DARK.parent.mkdir(parents=True, exist_ok=True)

TZ = ZoneInfo('Asia/Kolkata')
today = datetime.datetime.now(TZ).date()
start = today - datetime.timedelta(days=364)

query = '''
query($login:String!, $from:DateTime!, $to:DateTime!) {
  user(login:$login) {
    followers { totalCount }
    following { totalCount }
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false, first: 100) {
      totalCount
      nodes { stargazerCount }
    }
    contributionsCollection(from:$from, to:$to) {
      totalCommitContributions
      totalPullRequestContributions
      totalIssueContributions
      totalRepositoryContributions
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
        'from': start.isoformat() + 'T00:00:00Z',
        'to': today.isoformat() + 'T23:59:59Z',
    }
}).encode()
req = urllib.request.Request(
    'https://api.github.com/graphql',
    data=payload,
    headers={
        'Authorization': f'Bearer {TOKEN}',
        'Content-Type': 'application/json',
        'User-Agent': 'developer-signal'
    }
)
with urllib.request.urlopen(req, timeout=30) as r:
    data = json.loads(r.read().decode())
if data.get('errors'):
    raise RuntimeError(data['errors'])

u = data['data']['user']
cc = u['contributionsCollection']
days = []
for week in cc['contributionCalendar']['weeks']:
    for item in week['contributionDays']:
        dt = datetime.date.fromisoformat(item['date'])
        if start <= dt <= today:
            days.append((dt, int(item['contributionCount'])))
days.sort()
counts = [c for _, c in days]
active_days = sum(1 for c in counts if c > 0)
longest = run = 0
for c in counts:
    if c > 0:
        run += 1
        longest = max(longest, run)
    else:
        run = 0
current = 0
for c in reversed(counts):
    if c > 0:
        current += 1
    else:
        break

followers = u['followers']['totalCount']
following = u['following']['totalCount']
public_repos = u['repositories']['totalCount']
stars = sum((n.get('stargazerCount', 0) or 0) for n in u['repositories']['nodes'])
contributions = cc['contributionCalendar']['totalContributions']
commits = cc['totalCommitContributions']
prs = cc['totalPullRequestContributions']
issues = cc['totalIssueContributions']
repo_contribs = cc['totalRepositoryContributions']
recent = counts[-28:] if len(counts) >= 28 else counts
max_recent = max(recent) if recent else 1
if max_recent <= 0:
    max_recent = 1


def render(theme='dark'):
    dark = theme == 'dark'
    bg = '#0f172a' if dark else '#f8fafc'
    panel = '#101827' if dark else '#ffffff'
    border = '#334155' if dark else '#cbd5e1'
    text = '#f8fafc' if dark else '#0f172a'
    muted = '#94a3b8' if dark else '#64748b'
    sub = '#dbeafe' if dark else '#1e293b'
    spark_bg = '#1f2937' if dark else '#e2e8f0'
    spark_fill = '#fb923c' if dark else '#f97316'
    bars = []
    for i, c in enumerate(recent):
        h = 10 + (c / max_recent) * 42
        x = 70 + i * 16
        y = 295 - h
        bars.append(f'<rect x="{x}" y="{y:.1f}" width="10" height="{h:.1f}" rx="2" fill="{spark_fill}"/>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="360" viewBox="0 0 1200 360">
<defs>
  <linearGradient id="top" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="#fb7185"/>
    <stop offset="25%" stop-color="#facc15"/>
    <stop offset="50%" stop-color="#67e8f9"/>
    <stop offset="75%" stop-color="#a78bfa"/>
    <stop offset="100%" stop-color="#60a5fa"/>
  </linearGradient>
</defs>
<rect width="1200" height="360" rx="22" fill="{bg}"/>
<rect x="18" y="18" width="1164" height="324" rx="18" fill="{panel}" stroke="{border}" stroke-width="2"/>
<rect x="18" y="18" width="1164" height="5" rx="2.5" fill="url(#top)"/>
<text x="48" y="62" fill="{text}" font-family="monospace" font-size="22" font-weight="700">{USER.upper()} / DEVELOPER SIGNAL</text>
<text x="1140" y="62" text-anchor="end" fill="{muted}" font-family="monospace" font-size="12">{start.isoformat()} -> {today.isoformat()}</text>

<text x="56" y="112" fill="#22d3ee" font-family="monospace" font-size="56" font-weight="700">{contributions}</text>
<text x="56" y="138" fill="{sub}" font-family="monospace" font-size="12">CONTRIBUTIONS / PAST 365 DAYS</text>

<text x="56" y="180" fill="{text}" font-family="monospace" font-size="18" font-weight="700">{active_days}</text>
<text x="98" y="180" fill="{muted}" font-family="monospace" font-size="12">active days</text>
<text x="208" y="180" fill="{text}" font-family="monospace" font-size="18" font-weight="700">{current}</text>
<text x="242" y="180" fill="{muted}" font-family="monospace" font-size="12">current streak</text>
<text x="392" y="180" fill="{text}" font-family="monospace" font-size="18" font-weight="700">{longest}</text>
<text x="432" y="180" fill="{muted}" font-family="monospace" font-size="12">longest streak</text>

<rect x="52" y="214" width="500" height="96" rx="14" fill="{spark_bg}" opacity="0.45"/>
<text x="70" y="236" fill="{muted}" font-family="monospace" font-size="11">RECENT 28-DAY ACTIVITY</text>
<line x1="70" y1="300" x2="530" y2="300" stroke="{border}" opacity="0.55"/>
{''.join(bars)}

<rect x="592" y="88" width="168" height="64" rx="12" fill="#082f49" stroke="#0891b2"/>
<text x="608" y="113" fill="{muted}" font-family="monospace" font-size="11">COMMITS</text>
<text x="608" y="138" fill="#67e8f9" font-family="monospace" font-size="28" font-weight="700">{commits}</text>

<rect x="780" y="88" width="168" height="64" rx="12" fill="#052e16" stroke="#16a34a"/>
<text x="796" y="113" fill="{muted}" font-family="monospace" font-size="11">PULL REQUESTS</text>
<text x="796" y="138" fill="#86efac" font-family="monospace" font-size="28" font-weight="700">{prs}</text>

<rect x="968" y="88" width="168" height="64" rx="12" fill="#3b0764" stroke="#8b5cf6"/>
<text x="984" y="113" fill="{muted}" font-family="monospace" font-size="11">ISSUES</text>
<text x="984" y="138" fill="#ddd6fe" font-family="monospace" font-size="28" font-weight="700">{issues}</text>

<rect x="592" y="174" width="168" height="64" rx="12" fill="#4c0519" stroke="#e11d48"/>
<text x="608" y="199" fill="{muted}" font-family="monospace" font-size="11">FOLLOWERS</text>
<text x="608" y="224" fill="#fda4af" font-family="monospace" font-size="28" font-weight="700">{followers}</text>

<rect x="780" y="174" width="168" height="64" rx="12" fill="#1f2937" stroke="#64748b"/>
<text x="796" y="199" fill="{muted}" font-family="monospace" font-size="11">FOLLOWING</text>
<text x="796" y="224" fill="{text}" font-family="monospace" font-size="28" font-weight="700">{following}</text>

<rect x="968" y="174" width="168" height="64" rx="12" fill="#422006" stroke="#f59e0b"/>
<text x="984" y="199" fill="{muted}" font-family="monospace" font-size="11">PUBLIC REPOS</text>
<text x="984" y="224" fill="#fcd34d" font-family="monospace" font-size="28" font-weight="700">{public_repos}</text>

<rect x="592" y="260" width="544" height="44" rx="12" fill="{spark_bg}" opacity="0.5"/>
<text x="610" y="287" fill="{muted}" font-family="monospace" font-size="11">PUBLIC FOOTPRINT</text>
<text x="760" y="287" fill="{text}" font-family="monospace" font-size="13">stars {stars}</text>
<text x="870" y="287" fill="{text}" font-family="monospace" font-size="13">repos touched {repo_contribs}</text>
<text x="1046" y="287" fill="{text}" font-family="monospace" font-size="13">timezone IST</text>

<text x="54" y="330" fill="{muted}" font-family="monospace" font-size="10">Custom GitHub GraphQL dashboard. Language composition remains below.</text>
</svg>'''

OUT_DARK.write_text(render('dark'), encoding='utf-8')
OUT_LIGHT.write_text(render('light'), encoding='utf-8')
