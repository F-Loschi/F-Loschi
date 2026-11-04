"""Generate the commit gym SVG shown in the profile README.

Each day of the contribution calendar becomes a barbell on the gym floor: the
more contributions, the heavier the load. An LED panel shows the personal
record, the current streak and the yearly volume. All the art is original and
drawn by this script. Requires GITHUB_TOKEN.
"""

import datetime
import json
import os
import urllib.request
from pathlib import Path

USERNAME = "F-Loschi"
BRAZIL_TZ = datetime.timezone(datetime.timedelta(hours=-3))
OUTPUT = Path(__file__).resolve().parent.parent / "assets" / "gym.svg"

PIXEL = 2
CELL = 16
MARGIN = 16
FIELD_Y = 128
BAR_H = 28

MONTH_NAMES = ["JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ"]
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}

# Window view by season (southern hemisphere)
SEASONS = {
    "spring": {"sky": "#8fd3f4", "tree": "#5aa83f"},
    "summer": {"sky": "#62bdf0", "tree": "#2f8a2b"},
    "autumn": {"sky": "#f4c98f", "tree": "#d9702a"},
    "winter": {"sky": "#c7dff0", "tree": "#7f9a6b"},
}

COLORS = {
    "F": "#343841", "f": "#292c33",  # rubber floor
    "b": "#c3c9d1",  # bar
    "p": "#8b93a0", "B": "#3f7fd1", "Y": "#f2c230", "R": "#d9443c",  # plates
    "w": "#6fc3e8", "W": "#e8eef3",  # bottle
    "t": "#d9dde3", "T": "#a9afb8",  # towel
}

SPRITES = {
    "floor": ["FFFFFFFF", "FFFFFFFF", "FFFfFFFF", "FFFFFFFF", "FFFFFFFF", "FFFFFfFF", "FFFFFFFF", "ffffffff"],
    "bottle": ["........", "...W....", "..www...", "..www...", "..WWW...", "..www...", "..www...", "........"],
    "towel": ["........", "........", "........", "..tttt..", ".tTttTt.", ".tttttt.", "........", "........"],
    "load1": ["........", "........", "........", ".p....p.", ".pbbbbp.", ".p....p.", "........", "........"],
    "load2": ["........", "........", ".BB..BB.", ".BB..BB.", ".BBbbBB.", ".BB..BB.", ".BB..BB.", "........"],
    "load3": ["........", ".YY..YY.", ".YY..YY.", ".YY..YY.", ".YYbbYY.", ".YY..YY.", ".YY..YY.", ".YY..YY."],
    "load4": ["RR....RR", "RR....RR", "RRY..YRR", "RRY..YRR", "RRYbbYRR", "RRY..YRR", "RRY..YRR", "RR....RR"],
}

ATHLETE_COLORS = {
    "H": "#2a1c14", "K": "#d9a066", "D": "#4a3020", "T": "#2c3e66",
    "A": "#c48f58", "S": "#16181d", "E": "#e8e8e8",
}
ATHLETE_STAND = [
    "....HHHHHH....", "...HHHHHHHH...", "...HKKKKKKH...", "...KKKKKKKK...", "...KKDKKDKK...",
    "...KDDDDDDK...", "....DDDDDD....", "..TTTTTTTTTT..", ".ATTTTTTTTTTA.", ".ATTTTTTTTTTA.",
    ".A.TTTTTTTT.A.", "...TTTTTTTT...", "...SSSSSSSS...", "...SSSSSSSS...", "...SSS..SSS...",
    "...KKK..KKK...", "...KKK..KKK...", "...KKK..KKK...", "...EEE..EEE...", "..EEEE..EEEE..",
]
ATHLETE_SQUAT = [
    "..............", "..............", "..............", "..............", "..............",
    "..............", "....HHHHHH....", "...HHHHHHHH...", "...HKKKKKKH...", "...KKKKKKKK...",
    "...KKDKKDKK...", "...KDDDDDDK...", "....DDDDDD....", "..TTTTTTTTTT..", ".ATTTTTTTTTTA.",
    ".ATTTTTTTTTTA.", "...SSSSSSSS...", ".SSSSSSSSSSSS.", ".KKK......KKK.", "EEEE......EEEE",
]

FONT = {
    "A": "01110 10001 10001 11111 10001 10001 10001", "B": "11110 10001 10001 11110 10001 10001 11110",
    "C": "01110 10001 10000 10000 10000 10001 01110", "D": "11110 10001 10001 10001 10001 10001 11110",
    "E": "11111 10000 10000 11110 10000 10000 11111", "F": "11111 10000 10000 11110 10000 10000 10000",
    "G": "01110 10001 10000 10111 10001 10001 01110", "H": "10001 10001 10001 11111 10001 10001 10001",
    "I": "01110 00100 00100 00100 00100 00100 01110", "J": "00111 00010 00010 00010 00010 10010 01100",
    "K": "10001 10010 10100 11000 10100 10010 10001", "L": "10000 10000 10000 10000 10000 10000 11111",
    "M": "10001 11011 10101 10101 10001 10001 10001", "N": "10001 11001 10101 10011 10001 10001 10001",
    "O": "01110 10001 10001 10001 10001 10001 01110", "P": "11110 10001 10001 11110 10000 10000 10000",
    "Q": "01110 10001 10001 10001 10101 10010 01101", "R": "11110 10001 10001 11110 10100 10010 10001",
    "S": "01111 10000 10000 01110 00001 00001 11110", "T": "11111 00100 00100 00100 00100 00100 00100",
    "U": "10001 10001 10001 10001 10001 10001 01110", "V": "10001 10001 10001 10001 10001 01010 00100",
    "W": "10001 10001 10001 10101 10101 11011 10001", "X": "10001 10001 01010 00100 01010 10001 10001",
    "Y": "10001 10001 01010 00100 00100 00100 00100", "Z": "11111 00001 00010 00100 01000 10000 11111",
    "0": "01110 10011 10101 10101 11001 10001 01110", "1": "00100 01100 00100 00100 00100 00100 01110",
    "2": "01110 10001 00001 00110 01000 10000 11111", "3": "11110 00001 00001 01110 00001 00001 11110",
    "4": "00010 00110 01010 10010 11111 00010 00010", "5": "11111 10000 11110 00001 00001 10001 01110",
    "6": "00110 01000 10000 11110 10001 10001 01110", "7": "11111 00001 00010 00100 01000 01000 01000",
    "8": "01110 10001 10001 01110 10001 10001 01110", "9": "01110 10001 10001 01111 00001 00010 01100",
    ":": "00000 00100 00100 00000 00100 00100 00000", " ": "00000 00000 00000 00000 00000 00000 00000",
}
ACCENTS = {"Ê": ("E", [(2, -3), (1, -2), (3, -2)])}


def season_of(day):
    md = (day.month, day.day)
    if (9, 22) <= md < (12, 21):
        return "spring"
    if (3, 20) <= md < (6, 21):
        return "autumn"
    if (6, 21) <= md < (9, 22):
        return "winter"
    return "summer"


def fetch_calendar():
    token = os.environ["GITHUB_TOKEN"]
    query = """
        query($login: String!) {
          user(login: $login) {
            contributionsCollection {
              contributionCalendar {
                totalContributions
                weeks { contributionDays { date weekday contributionLevel contributionCount } }
              }
            }
          }
        }"""
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": query, "variables": {"login": USERNAME}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        body = json.load(response)
    if "errors" in body:
        raise RuntimeError(body["errors"])
    return body["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def current_streak(days, today):
    """Consecutive days with contributions; today doesn't break it until the day is over."""
    streak = 0
    for day in sorted(days, key=lambda d: d["date"], reverse=True):
        if day["contributionCount"]:
            streak += 1
        elif day["date"] != today.isoformat():
            break
    return streak


def best_streak(days):
    best = streak = 0
    for day in sorted(days, key=lambda d: d["date"]):
        streak = streak + 1 if day["contributionCount"] else 0
        best = max(best, streak)
    return best


def rect(x, y, width, height, color):
    return f'<rect x="{x}" y="{y}" width="{width}" height="{height}" fill="{color}"/>'


def pixels_to_paths(rows, colors, scale):
    paths = {}
    for y, row in enumerate(rows):
        for x, char in enumerate(row):
            if char != ".":
                paths.setdefault(colors[char], []).append(
                    f"M{x * scale} {y * scale}h{scale}v{scale}h-{scale}z")
    return "".join(f'<path fill="{color}" d="{"".join(d)}"/>' for color, d in paths.items())


def text(string, x, y, color, scale=PIXEL):
    d = []
    cursor = x
    for char in string:
        base, marks = ACCENTS.get(char, (char, []))
        points = [(col, row) for row, bits in enumerate(FONT[base].split())
                  for col, bit in enumerate(bits) if bit == "1"] + marks
        d.extend(f"M{cursor + col * scale} {y + row * scale}h{scale}v{scale}h-{scale}z" for col, row in points)
        cursor += 6 * scale
    return f'<path fill="{color}" d="{"".join(d)}"/>'


def led_panel(rows):
    x, y, width, height = MARGIN, 12, 324, 100
    parts = [
        rect(x, y, width, height, "#14161a"), rect(x + 4, y + 4, width - 8, height - 8, "#07080a"),
        rect(x + width - 18, y + 10, 6, 6, "#ff4d3d").replace("<rect", '<rect class="led"'),
    ]
    for index, (label, value) in enumerate(rows):
        line_y = y + 18 + index * 26
        parts.append(text(label, x + 14, line_y, "#ffb000"))
        parts.append(text(value, x + 14 + (len(label) + 1) * 12, line_y, "#58e06f"))
    return "".join(parts)


def window(x, season):
    colors = SEASONS[season]
    return "".join([
        rect(x, 24, 76, 72, "#8a8f99"),
        rect(x + 4, 28, 68, 64, colors["sky"]),
        rect(x + 4, 76, 68, 16, "#6e7f5a"),
        rect(x + 38, 60, 6, 20, "#5b3a1e"),
        rect(x + 26, 44, 30, 22, colors["tree"]),
        rect(x + 36, 28, 4, 64, "#8a8f99"),
    ])


def mirror(x, width):
    parts = [rect(x, 20, width, 104, "#8a8f99"), rect(x + 4, 24, width - 8, 96, "#a9c0cf")]
    for step in range(8):
        parts.append(rect(x + 26 + step * 6, 96 - step * 8, 14, 8, "#c9dae4"))
        parts.append(rect(x + 92 + step * 6, 112 - step * 8, 8, 8, "#c9dae4"))
    return "".join(parts)


def athlete_frame(rows, bar_row, x, class_name):
    scale = 3
    bar_y = 64 + bar_row * scale
    return "".join([
        f'<g class="{class_name}">',
        f'<g transform="translate({x} 64)">{pixels_to_paths(rows, ATHLETE_COLORS, scale)}</g>',
        rect(x - 26, bar_y, 94, 4, "#c3c9d1"),
        rect(x - 26, bar_y - 12, 8, 28, "#d9443c"), rect(x - 16, bar_y - 8, 6, 20, "#f2c230"),
        rect(x + 60, bar_y - 12, 8, 28, "#d9443c"), rect(x + 52, bar_y - 8, 6, 20, "#f2c230"),
        "</g>",
    ])


def squat_rack(x):
    return "".join([
        rect(x, 24, 8, 100, "#4a4f5a"), rect(x + 96, 24, 8, 100, "#4a4f5a"),
        rect(x, 24, 104, 8, "#4a4f5a"),
        athlete_frame(ATHLETE_STAND, 7, x + 31, "stand"),
        athlete_frame(ATHLETE_SQUAT, 13, x + 31, "squat"),
    ])


def dumbbell_rack(x):
    colors = ["#3f7fd1", "#f2c230", "#d9443c"]
    parts = [rect(x, 44, 6, 80, "#4a4f5a"), rect(x + 66, 44, 6, 80, "#4a4f5a")]
    for level, y in enumerate((60, 88, 116)):
        parts.append(rect(x, y, 72, 4, "#4a4f5a"))
        for slot in range(3):
            left = x + 8 + slot * 20
            parts += [rect(left, y - 8, 4, 8, colors[level]), rect(left + 4, y - 6, 6, 3, "#c3c9d1"),
                      rect(left + 10, y - 8, 4, 8, colors[level])]
    return "".join(parts)


def scene(width, season, record, streak, best, volume):
    parts = [
        rect(0, 0, width, FIELD_Y, "#3a3f4b"),
        rect(0, 0, width, 12, "#2e323c"),
        rect(0, FIELD_Y - 4, width, 4, "#191b20"),
        rect(0, FIELD_Y - 18, width, 6, "#d9443c"),
        led_panel([
            ("PR:", f"{record} {'COMMIT' if record == 1 else 'COMMITS'} EM UM DIA"),
            ("SEQUÊNCIA:", f"{streak} {'DIA' if streak == 1 else 'DIAS'} MAX {best}"),
            ("VOLUME:", f"{volume} NO ANO"),
        ]),
        window(352, season),
        mirror(436, 200),
        squat_rack(652),
        dumbbell_rack(792),
    ]
    return "".join(parts)


def field(weeks, today, record):
    parts = []
    record_marked = False
    for week_index, week in enumerate(weeks):
        for day in week["contributionDays"]:
            date = datetime.date.fromisoformat(day["date"])
            x = MARGIN + week_index * CELL
            y = FIELD_Y + day["weekday"] * CELL
            parts.append(f'<use href="#floor" x="{x}" y="{y}"/>')
            level = LEVELS[day["contributionLevel"]]
            sprite = None
            if level:
                sprite = f"load{level}"
            elif date.toordinal() % 19 == 0:
                sprite = "bottle"
            elif date.toordinal() % 23 == 0:
                sprite = "towel"
            if sprite:
                parts.append(f'<use href="#{sprite}" x="{x}" y="{y}"/>')
            if record and day["contributionCount"] == record and not record_marked:
                record_marked = True
                parts.append(f'<rect class="record" x="{x + 1}" y="{y + 1}" width="{CELL - 2}" height="{CELL - 2}"/>')
            if date == today:
                parts.append(f'<rect class="today" x="{x + 1}" y="{y + 1}" width="{CELL - 2}" height="{CELL - 2}"/>')
    return "".join(parts)


def month_labels(weeks, y):
    parts = []
    previous = None
    for week_index, week in enumerate(weeks):
        month = datetime.date.fromisoformat(week["contributionDays"][0]["date"]).month
        if previous is not None and month != previous and week_index < len(weeks) - 2:
            parts.append(text(MONTH_NAMES[month - 1], MARGIN + week_index * CELL, y, "#c9d1d9"))
        previous = month
    return "".join(parts)


def legend(width, y):
    parts = [text("UMA BARRA POR DIA DE COMMITS", MARGIN, y + 7, "#c9d1d9")]
    sprites = [None, "load1", "load2", "load3", "load4"]
    x = width - MARGIN - 6 * 12 - 4 - len(sprites) * (CELL + 2) - 5 * 12
    parts.append(text("LEVE", x, y + 7, "#c9d1d9"))
    x += 5 * 12
    for sprite in sprites:
        parts.append(f'<use href="#floor" x="{x}" y="{y + 6}"/>')
        if sprite:
            parts.append(f'<use href="#{sprite}" x="{x}" y="{y + 6}"/>')
        x += CELL + 2
    parts.append(text("PESADO", x + 4, y + 7, "#c9d1d9"))
    return "".join(parts)


def render(calendar, today):
    weeks = calendar["weeks"]
    days = [day for week in weeks for day in week["contributionDays"]]
    record = max(day["contributionCount"] for day in days)
    streak = current_streak(days, today)

    width = MARGIN * 2 + len(weeks) * CELL
    months_y = FIELD_Y + 7 * CELL
    legend_y = months_y + BAR_H
    height = legend_y + BAR_H + 4

    defs = "".join(f'<g id="{name}">{pixels_to_paths(rows, COLORS, PIXEL)}</g>' for name, rows in SPRITES.items())
    style = """
    .stand { animation: stand 2.4s steps(1) infinite; }
    .squat { animation: squat 2.4s steps(1) infinite; }
    .led { animation: blink 1.2s steps(2) infinite; }
    .record { fill: none; stroke: #f2c230; stroke-width: 2; }
    .today { fill: none; stroke: #58e06f; stroke-width: 2; animation: blink 1.6s steps(2) infinite; }
    @keyframes stand { 0%, 49% { opacity: 1; } 50%, 100% { opacity: 0; } }
    @keyframes squat { 0%, 49% { opacity: 0; } 50%, 100% { opacity: 1; } }
    @keyframes blink { 50% { opacity: 0.2; } }
    @media (prefers-reduced-motion: reduce) {
      .stand, .squat, .led, .today { animation: none; }
      .squat { display: none; }
    }
    """
    return "".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'shape-rendering="crispEdges" role="img" aria-label="Academia de commits de {USERNAME}">',
        f"<style>{style}</style><defs>{defs}",
        f'<clipPath id="frame"><rect width="{width}" height="{height}" rx="8"/></clipPath></defs>',
        '<g clip-path="url(#frame)">',
        scene(width, season_of(today), record, streak, best_streak(days), calendar["totalContributions"]),
        rect(0, FIELD_Y, width, 7 * CELL, "#191b20"),
        field(weeks, today, record),
        rect(0, months_y, width, height - months_y, "#101216"),
        rect(0, months_y, width, 2, "#3a3f4b"),
        month_labels(weeks, months_y + 8),
        rect(0, legend_y, width, 2, "#3a3f4b"),
        legend(width, legend_y),
        "</g></svg>\n",
    ])


def main():
    today = datetime.datetime.now(BRAZIL_TZ).date()
    OUTPUT.parent.mkdir(exist_ok=True)
    OUTPUT.write_text(render(fetch_calendar(), today), encoding="utf-8")


if __name__ == "__main__":
    main()
