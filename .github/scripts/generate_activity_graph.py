"""Generate a local blue-green SVG from GitHub's public contribution calendar."""
from datetime import datetime, timedelta, timezone
from html import escape
from html.parser import HTMLParser
from pathlib import Path
import math
import re
from urllib.request import Request, urlopen

USERNAME = "tokimeki-marinosuke"
OUTPUT = Path(__file__).resolve().parents[2] / "profile/activity-blue-green.svg"


class Calendar(HTMLParser):
    def __init__(self):
        super().__init__()
        self.dates = {}
        self.counts = {}
        self.target = None
        self.text = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "td" and attrs.get("data-date"):
            self.dates[attrs["id"]] = attrs["data-date"]
        if tag == "tool-tip":
            self.target = attrs.get("for")
            self.text = []

    def handle_data(self, text):
        if self.target:
            self.text.append(text)

    def handle_endtag(self, tag):
        if tag == "tool-tip" and self.target:
            text = "".join(self.text).strip()
            match = re.match(r"(No|[\d,]+) contributions? on ", text)
            if match:
                self.counts[self.target] = (
                    0 if match[1] == "No" else int(match[1].replace(",", ""))
                )
            self.target = None


def generate():
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(days=29)
    url = f"https://github.com/users/{USERNAME}/contributions?from={start}&to={today}"
    request = Request(url, headers={"User-Agent": "GitHub-Profile-Activity-Graph", "Accept-Language": "en"})
    with urlopen(request, timeout=30) as response:
        document = response.read().decode("utf-8")
    calendar = Calendar()
    calendar.feed(document)
    values = {
        day: calendar.counts[key]
        for key, day in calendar.dates.items()
        if key in calendar.counts
    }
    days = [start + timedelta(days=i) for i in range(30)]
    missing = [str(day) for day in days if str(day) not in values]
    if missing:
        raise ValueError(f"Missing contribution counts for: {', '.join(missing)}")
    counts = [values[str(day)] for day in days]
    maximum = max(4, math.ceil(max(counts) / 4) * 4)
    left, right, top, bottom = 64, 944, 76, 244
    points = [
        (left + i * (right - left) / 29, bottom - value * (bottom - top) / maximum)
        for i, value in enumerate(counts)
    ]
    path = " ".join(f"{'M' if i == 0 else 'L'} {x:.2f} {y:.2f}" for i, (x, y) in enumerate(points))
    svg = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="980" height="310" viewBox="0 0 980 310" role="img" aria-labelledby="title description">',
        '<title id="title">GitHub activity — last 30 days</title>',
        f'<desc id="description">{USERNAME}: {sum(counts)} contributions from {start} to {today}. Generated from GitHub public contribution data.</desc>',
        '<rect x="0.5" y="0.5" width="979" height="309" rx="6" fill="#040f0f" stroke="#2f97c1" stroke-opacity="0.5"/>',
        '<g font-family="Segoe UI, Arial, sans-serif">',
        '<text x="28" y="34" fill="#2f97c1" font-size="20" font-weight="600">GitHub activity — last 30 days</text>',
        f'<text x="28" y="55" fill="#0cf574" font-size="12">{sum(counts)} contributions · {start} — {today} (UTC)</text>',
    ]
    for i in range(5):
        value = maximum * i / 4
        y = bottom - i * (bottom - top) / 4
        svg.extend([
            f'<path d="M {left} {y:.2f} H {right}" stroke="#2f97c1" stroke-opacity="0.18"/>',
            f'<text x="{left - 12}" y="{y + 4:.2f}" text-anchor="end" font-size="12" fill="#0cf574">{value:g}</text>',
        ])
    svg.append(f'<path d="{path} L {right} {bottom} L {left} {bottom} Z" fill="#2f97c1" fill-opacity="0.14"/>')
    svg.append(f'<path d="{path}" fill="none" stroke="#2f97c1" stroke-width="2.5" stroke-linejoin="round"/>')
    for day, count, (x, y) in zip(days, counts, points):
        svg.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3" fill="#0cf574"><title>{day}: {count} contributions</title></circle>')
    for i in [0, 5, 10, 15, 20, 25, 29]:
        x = points[i][0]
        label = days[i].strftime("%b %d")
        svg.append(f'<text x="{x:.2f}" y="270" text-anchor="middle" font-size="12" fill="#0cf574">{escape(label)}</text>')
    svg.extend(['</g>', '</svg>'])
    OUTPUT.write_text("\n".join(svg) + "\n", encoding="utf-8")
    print(f"Generated {OUTPUT.name}: {len(days)} days, {sum(counts)} contributions, maximum {max(counts)}/day")


if __name__ == "__main__":
    generate()
