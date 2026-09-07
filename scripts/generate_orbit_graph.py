#!/usr/bin/env python3
import os, json, urllib.request, datetime, html
from pathlib import Path

USER = os.environ.get("GITHUB_REPOSITORY_OWNER", "UNKN0WN006")
TOKEN = os.environ["GITHUB_TOKEN"]
OUT = Path("assets/orbit-contributions.svg")

today = datetime.datetime.now(datetime.timezone.utc).date()
start = today - datetime.timedelta(days=364)

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
    "query": query,
    "variables": {
        "login": USER,
        "from": start.isoformat() + "T00:00:00Z",
        "to": today.isoformat() + "T23:59:59Z"
    }
}).encode()

req = urllib.request.Request(
    "https://api.github.com/graphql",
    data=payload,
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
        "User-Agent": "profile-orbit-action"
    }
)

with urllib.request.urlopen(req, timeout=30) as r:
    data = json.loads(r.read().decode())

if "errors" in data:
    raise RuntimeError(data["errors"])

days = []
for week in data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]:
    for d in week["contributionDays"]:
        dt = datetime.date.fromisoformat(d["date"])
        if start <= dt <= today:
            days.append((dt, int(d["contributionCount"])))
days.sort()

counts = [c for _, c in days]
total = sum(counts)
active = sum(1 for c in counts if c > 0)

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

mx = max(counts) if counts else 0

def level(c):
    if c <= 0:
        return 0
    if mx <= 1:
        return 4
    ratio = c / mx
    if ratio <= .20:
        return 1
    if ratio <= .45:
        return 2
    if ratio <= .70:
        return 3
    return 4

palette = ["#1e293b", "#164e63", "#0e7490", "#7c3aed", "#db2777"]

first = days[0][0]
offset = first.weekday()
grid = [(None, 0)] * offset + days

rects = []
for i, (dt, c) in enumerate(grid):
    if dt is None:
        continue
    week = i // 7
    dow = i % 7
    x = 52 + week * 19
    y = 126 + dow * 19
    rects.append(
        f'<rect x="{x}" y="{y}" width="13" height="13" rx="3" fill="{palette[level(c)]}">'
        f'<title>{dt.isoformat()}: {c} contributions</title></rect>'
    )

labels = []
seen = set()
for i, (dt, c) in enumerate(grid):
    if dt is None:
        continue
    key = (dt.year, dt.month)
    if key not in seen and dt.day <= 7:
        seen.add(key)
        x = 52 + (i // 7) * 19
        labels.append(
            f'<text x="{x}" y="111" fill="#64748b" font-family="monospace" font-size="11">{dt.strftime("%b").upper()}</text>'
        )

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="315" viewBox="0 0 1200 315">
<defs>
  <linearGradient id="top" x1="0" y1="0" x2="1" y2="0">
    <stop stop-color="#22d3ee"/><stop offset=".33" stop-color="#22c55e"/>
    <stop offset=".66" stop-color="#a855f7"/><stop offset="1" stop-color="#fb7185"/>
  </linearGradient>
</defs>
<rect width="1200" height="315" rx="22" fill="#0b1020"/>
<rect x="18" y="18" width="1164" height="279" rx="18" fill="#101827" stroke="#334155"/>
<rect x="18" y="18" width="1164" height="4" rx="2" fill="url(#top)"/>
<text x="45" y="57" fill="#f8fafc" font-family="monospace" font-size="21" font-weight="700">365-DAY ORBIT</text>
<text x="45" y="83" fill="#94a3b8" font-family="monospace" font-size="12">{html.escape(start.isoformat())} to {html.escape(today.isoformat())}</text>
<text x="1150" y="57" text-anchor="end" fill="#22d3ee" font-family="monospace" font-size="14">{total} contributions</text>
<text x="1150" y="80" text-anchor="end" fill="#a78bfa" font-family="monospace" font-size="12">{active} active days · longest streak {longest} · current {current}</text>
{''.join(labels)}
{''.join(rects)}
<text x="45" y="283" fill="#64748b" font-family="monospace" font-size="11">color intensity is relative to the busiest day in this 365-day window</text>
</svg>'''

OUT.write_text(svg, encoding="utf-8")
print(f"Wrote {OUT}")
