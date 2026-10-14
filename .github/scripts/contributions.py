"""Builds assets/contributions.svg from the public GitHub contribution calendar.

The public calendar already includes private contributions when
"Private contributions" is enabled on the profile, so no token is needed.
"""
import datetime
import json
import os
import re
import urllib.request

USER = os.environ.get("GH_USER", "PabloDev24")
OUT = "assets/contributions.svg"


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8")


def total_in(html):
    m = re.search(r"([\d,]+)\s+contributions?\s+in", html)
    return int(m.group(1).replace(",", "")) if m else 0


def daily_counts(html):
    ids = {}
    for td in re.findall(r"<td[^>]*data-date=[^>]*>", html):
        d = re.search(r'data-date="([\d-]+)"', td)
        i = re.search(r'id="([^"]+)"', td)
        if d and i:
            ids[i.group(1)] = d.group(1)
    days = {}
    for target, text in re.findall(r'<tool-tip[^>]*for="([^"]+)"[^>]*>([^<]*)</tool-tip>', html):
        if target in ids:
            m = re.match(r"\s*(\d+)", text)
            days[ids[target]] = int(m.group(1)) if m else 0
    return dict(sorted(days.items()))


def streaks(days):
    values = list(days.values())
    longest = run = 0
    for v in values:
        run = run + 1 if v > 0 else 0
        longest = max(longest, run)
    current = 0
    tail = values[:]
    if tail and tail[-1] == 0:
        tail = tail[:-1]  # today may still be empty
    for v in reversed(tail):
        if v == 0:
            break
        current += 1
    return current, longest


last_year_html = get(f"https://github.com/users/{USER}/contributions")
last_year = total_in(last_year_html)
days = daily_counts(last_year_html)
current, longest = streaks(days)
best_day = max(days.values()) if days else 0

this_year = datetime.date.today().year
all_time = 0
for y in range(this_year, 2007, -1):
    c = total_in(get(f"https://github.com/users/{USER}/contributions?from={y}-01-01&to={y}-12-31"))
    all_time += c
    if c == 0 and y < this_year - 3:
        break


def fmt(n):
    return f"{n:,}"


stats = [
    (fmt(last_year), "Contributions", "last 12 months"),
    (fmt(all_time), "All-time", "public + private")
    if all_time > last_year
    else (fmt(best_day), "Best day", "contributions in one day"),
    (f"{current} days", "Current streak", ""),
    (f"{longest} days", "Longest streak", "last 12 months"),
]

W, H = 850, 190
col = W / len(stats)
cells = []
for i, (value, label, sub) in enumerate(stats):
    x = col * i + col / 2
    cells.append(f'''
  <g transform="translate({x:.0f},0)" class="fade" style="animation-delay:{i * 0.15:.2f}s">
    <text y="92" text-anchor="middle" class="value">{value}</text>
    <text y="124" text-anchor="middle" class="label">{label}</text>
    <text y="146" text-anchor="middle" class="sub">{sub}</text>
  </g>''')
    if i:
        cells.append(f'<line x1="{col * i:.0f}" y1="58" x2="{col * i:.0f}" y2="150" stroke="#21262D"/>')

updated = datetime.datetime.utcnow().strftime("%b %d, %Y")
svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{fmt(last_year)} contributions in the last year">
  <style>
    .title {{ font: 600 16px 'Segoe UI', Ubuntu, sans-serif; fill: #58A6FF; }}
    .value {{ font: 700 34px 'Segoe UI', Ubuntu, sans-serif; fill: #FFFFFF; }}
    .label {{ font: 600 14px 'Segoe UI', Ubuntu, sans-serif; fill: #58A6FF; }}
    .sub {{ font: 400 12px 'Segoe UI', Ubuntu, sans-serif; fill: #8B949E; }}
    .foot {{ font: 400 11px 'Segoe UI', Ubuntu, sans-serif; fill: #6E7681; }}
    .fade {{ opacity: 0; animation: in .6s ease forwards; }}
    @keyframes in {{ to {{ opacity: 1; }} }}
  </style>
  <defs>
    <linearGradient id="bar" x1="0" x2="1">
      <stop offset="0" stop-color="#0B3D91"/><stop offset=".6" stop-color="#1F6FEB"/><stop offset="1" stop-color="#00B4FF"/>
    </linearGradient>
  </defs>
  <rect width="{W}" height="{H}" rx="10" fill="#0D1117"/>
  <rect width="{W}" height="4" rx="2" fill="url(#bar)"/>
  <text x="24" y="36" class="title">GitHub activity (includes private work)</text>
  {''.join(cells)}
  <text x="{W - 24}" y="{H - 14}" text-anchor="end" class="foot">Updated {updated} · best day: {best_day}</text>
</svg>
'''

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(svg)
print(json.dumps({"last_year": last_year, "all_time": all_time, "current": current, "longest": longest}))
