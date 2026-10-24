"""Generate the neofetch-style ID card SVGs shown at the top of the profile README.

Run with GITHUB_TOKEN set so the GitHub stats can be fetched; without it the
stats section shows dashes.
"""

import datetime
import io
import json
import os
import urllib.request
from pathlib import Path
from xml.sax.saxutils import escape

from PIL import Image, ImageOps

USERNAME = "F-Loschi"
INATEL_START = datetime.date(2023, 2, 1)
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "assets"

ART_COLS = 40
ART_ROWS = 24
ART_RAMP = " .:-=+*#%@"
LINE_WIDTH = 58
CHAR_W = 9.6
LINE_H = 20
TEXT_X = 15 + ART_COLS * CHAR_W + 25
WIDTH = round(TEXT_X + LINE_WIDTH * CHAR_W + 20)

THEMES = {
    "dark": {
        "bg": "#161b22", "border": "#30363d", "text": "#c9d1d9",
        "key": "#ffa657", "value": "#a5d6ff", "dots": "#616e7f",
    },
    "light": {
        "bg": "#f6f8fa", "border": "#d0d7de", "text": "#24292f",
        "key": "#953800", "value": "#0a3069", "dots": "#c2cfde",
    },
}


def inatel_uptime(today):
    years = today.year - INATEL_START.year
    months = today.month - INATEL_START.month
    days = today.day - INATEL_START.day
    if days < 0:
        months -= 1
        prev_month_end = today.replace(day=1) - datetime.timedelta(days=1)
        days += prev_month_end.day
    if months < 0:
        years -= 1
        months += 12
    return f"{years} anos, {months} meses, {days} dias"


def inatel_semester(today):
    start = INATEL_START.year * 2 + (INATEL_START.month >= 8)
    now = today.year * 2 + (today.month >= 8)
    return now - start + 1


def graphql(token, query, variables):
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": variables}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.load(response)
    if "errors" in body:
        raise RuntimeError(body["errors"])
    return body["data"]


def fetch_stats(today):
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        return None

    user = graphql(token, """
        query($login: String!) {
          user(login: $login) {
            createdAt
            followers { totalCount }
            pullRequests { totalCount }
            issues { totalCount }
            repositories(ownerAffiliations: OWNER, privacy: PUBLIC, first: 100) {
              totalCount
              nodes { stargazerCount }
            }
          }
        }""", {"login": USERNAME})["user"]

    commits = 0
    created_year = int(user["createdAt"][:4])
    for year in range(created_year, today.year + 1):
        collection = graphql(token, """
            query($login: String!, $from: DateTime!, $to: DateTime!) {
              user(login: $login) {
                contributionsCollection(from: $from, to: $to) { totalCommitContributions }
              }
            }""", {
            "login": USERNAME,
            "from": f"{year}-01-01T00:00:00Z",
            "to": f"{year}-12-31T23:59:59Z",
        })
        commits += collection["user"]["contributionsCollection"]["totalCommitContributions"]

    repos = user["repositories"]
    return {
        "Repos": repos["totalCount"],
        "Stars": sum(node["stargazerCount"] for node in repos["nodes"]),
        "Commits": commits,
        "Followers": user["followers"]["totalCount"],
        "PRs": user["pullRequests"]["totalCount"],
        "Issues": user["issues"]["totalCount"],
    }


def avatar_ascii():
    with urllib.request.urlopen(f"https://github.com/{USERNAME}.png?size=400", timeout=30) as response:
        image = Image.open(io.BytesIO(response.read())).convert("L")
    # Crop to the on-screen aspect of the art block, since glyphs are taller than wide.
    aspect = (ART_COLS * CHAR_W) / (ART_ROWS * LINE_H)
    image = ImageOps.fit(image, (round(400 * aspect), 400)).resize((ART_COLS, ART_ROWS), Image.LANCZOS)
    # Inverted so the light photo background becomes empty space and the subject is drawn.
    image = ImageOps.invert(ImageOps.autocontrast(image, cutoff=2))
    pixels = image.load()
    last = len(ART_RAMP) - 1
    return [
        "".join(ART_RAMP[pixels[x, y] * last // 255] for x in range(ART_COLS))
        for y in range(ART_ROWS)
    ]


def info_lines(today, stats):
    def field(key, value, width=LINE_WIDTH):
        dots = width - len(key) - len(str(value)) - 5
        return [(". ", "text"), (key, "key"), (": ", "text"), ("." * dots, "dots"), (" " + str(value), "value")]

    def header(title):
        return [(title + " ", "text"), ("—" * (LINE_WIDTH - len(title) - 1), "dots")]

    def pair(left, right):
        half = LINE_WIDTH // 2
        return field(*left, width=half) + [(" | ", "text")] + field(*right, width=LINE_WIDTH - half - 1)[1:]

    blank = [(".", "text")]
    lines = [
        header("felipe@loschi"),
        blank,
        field("OS", "Windows 11"),
        field("Uptime", inatel_uptime(today)),
        field("Host", f"Inatel · Eng. de Software ({inatel_semester(today)}° período)"),
        field("Kernel", "Data Science | Machine Learning"),
        field("IDE", "VS Code, PyCharm, Jupyter"),
        blank,
        field("Languages.Programming", "Python, Java, C++, JavaScript"),
        field("Languages.Data", "Pandas, Scikit-learn, TensorFlow"),
        field("Languages.Real", "Português, Inglês"),
        blank,
        field("Hobbies.Software", "Data Science, Machine Learning"),
        field("Hobbies.Real", "Leitura, Futebol"),
        blank,
        header("— Contact"),
        field("Email", "felipe.loschi@ges.inatel.br"),
        field("LinkedIn", "felipe-silva-loschi"),
        field("GitHub", USERNAME),
        blank,
        header("— GitHub Stats"),
    ]
    stats = stats or dict.fromkeys(["Repos", "Stars", "Commits", "Followers", "PRs", "Issues"], "—")
    keys = list(stats)
    for i in range(0, len(keys), 2):
        lines.append(pair((keys[i], stats[keys[i]]), (keys[i + 1], stats[keys[i + 1]])))
    return lines


def render(theme, art, lines):
    colors = THEMES[theme]
    height = max(len(art), len(lines)) * LINE_H + 30
    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'font-family="Consolas, \'Courier New\', monospace" font-size="16px">',
        "<style>text, tspan { white-space: pre; }"
        + "".join(f" .{name} {{ fill: {colors[name]}; }}" for name in ("key", "value", "dots"))
        + "</style>",
        f'<rect width="{WIDTH}" height="{height}" rx="15" fill="{colors["bg"]}" '
        f'stroke="{colors["border"]}" stroke-width="1"/>',
        f'<text x="15" y="30" fill="{colors["text"]}">',
    ]
    for i, row in enumerate(art):
        out.append(f'<tspan x="15" y="{30 + i * LINE_H}">{escape(row).replace(" ", "&#160;")}</tspan>')
    out.append("</text>")
    out.append(f'<text x="{TEXT_X}" y="30" fill="{colors["text"]}">')
    for i, segments in enumerate(lines):
        spans = "".join(
            escape(text).replace(" ", "&#160;") if cls == "text"
            else f'<tspan class="{cls}">{escape(text).replace(" ", "&#160;")}</tspan>'
            for text, cls in segments
        )
        out.append(f'<tspan x="{TEXT_X}" y="{30 + i * LINE_H}">{spans}</tspan>')
    out.append("</text></svg>")
    return "\n".join(out) + "\n"


def main():
    today = datetime.date.today()
    lines = info_lines(today, fetch_stats(today))
    OUTPUT_DIR.mkdir(exist_ok=True)
    art = avatar_ascii()
    for theme in THEMES:
        (OUTPUT_DIR / f"id_card_{theme}.svg").write_text(render(theme, art, lines), encoding="utf-8")


if __name__ == "__main__":
    main()
