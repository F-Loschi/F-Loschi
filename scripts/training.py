"""Generate the real gym SVG shown in the profile README, from Strava activities.

Only totals, best loads and which days had a workout reach the image. Activity
names, descriptions, locations and start times are read but never written out.
Requires STRAVA_CLIENT_ID, STRAVA_CLIENT_SECRET and STRAVA_REFRESH_TOKEN; without
them the script exits without touching the current image.
"""

import datetime
import json
import os
import re
import urllib.parse
import urllib.request
from pathlib import Path

from gym import (BAR_H, BRAZIL_TZ, CELL, COLORS, FIELD_Y, MARGIN, PIXEL, dumbbell_rack, led_panel, month_labels,
                 pixels_to_paths, rect, squat_rack, text)

OUTPUT = Path(__file__).resolve().parent.parent / "assets" / "training.svg"
API = "https://www.strava.com/api/v3"

RECORD_WINDOW_DAYS = 90
MIN_WORKOUT_SECONDS = 30 * 60
STRENGTH_SPORTS = {"WeightTraining", "Workout"}

# Hevy logged the exercises in English before switching to Portuguese
LIFTS = {
    "AGACHAMENTO": {"Agachamento (Barra)", "Squat (Barbell)"},
    "SUPINO RETO": {"Supino Reto (Halter)", "Bench Press (Dumbbell)"},
    "LEG PRESS": {"Leg Press 45º (Máquina)", "Leg Press (Machine)"},
    "PUXADA ALTA": {"Puxada Alta (Cabo)", "Lat Pulldown (Cable)"},
}

SPLITS = {"A": ("PEITO", "R"), "B": ("PERNA", "B"), "C": ("COSTAS", "Y"), "D": ("OMBROS", "G")}
TRAINING_COLORS = {**COLORS, "G": "#58b368", "S": "#58e06f", "s": "#e8eef3"}


def barbell(plate):
    return ["........", f".{plate}{plate}..{plate}{plate}.", f".{plate}{plate}..{plate}{plate}.",
            f".{plate}{plate}..{plate}{plate}.", f".{plate}{plate}bb{plate}{plate}.",
            f".{plate}{plate}..{plate}{plate}.", f".{plate}{plate}..{plate}{plate}.",
            f".{plate}{plate}..{plate}{plate}."]


SPRITES = {
    "floor": ["FFFFFFFF", "FFFFFFFF", "FFFfFFFF", "FFFFFFFF", "FFFFFFFF", "FFFFFfFF", "FFFFFFFF", "ffffffff"],
    "other": barbell("p"),
    "run": ["........", "........", "..SS....", "..SSS...", "..SSSSS.", ".SSSSSSS", ".ssssss.", "........"],
    **{letter: barbell(plate) for letter, (_, plate) in SPLITS.items()},
}


def request_json(url, data=None, token=None):
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def access_token(client_id, client_secret, refresh_token):
    body = urllib.parse.urlencode({
        "client_id": client_id,
        "client_secret": client_secret,
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }).encode()
    payload = request_json("https://www.strava.com/oauth/token", data=body)
    if payload["refresh_token"] != refresh_token:
        print("Strava issued a new refresh token: update the STRAVA_REFRESH_TOKEN secret.")
    return payload["access_token"]


def fetch_activities(token, since):
    activities = []
    page = 1
    after = int(datetime.datetime.combine(since, datetime.time(), BRAZIL_TZ).timestamp())
    while True:
        batch = request_json(f"{API}/athlete/activities?after={after}&per_page=200&page={page}", token=token)
        activities.extend(batch)
        if len(batch) < 200:
            return activities
        page += 1


def activity_date(activity):
    return datetime.date.fromisoformat(activity["start_date_local"][:10])


def split_letter(activity):
    match = re.match(r"Treino ([A-D])\b", activity["name"])
    return match.group(1) if match else None


def best_loads(description):
    """Heaviest load per tracked lift in a Hevy description."""
    loads = {}
    for block in (description or "").replace("\r", "").split("\n\n"):
        name = block.split("\n")[0].strip()
        for lift, aliases in LIFTS.items():
            if name in aliases:
                weights = re.findall(r"(\d+(?:[.,]\d+)?) kg x \d+", block)
                if weights:
                    loads[lift] = max(loads.get(lift, 0), max(float(w.replace(",", ".")) for w in weights))
    return loads


def fetch_records(token, activities, today):
    since = today - datetime.timedelta(days=RECORD_WINDOW_DAYS)
    records = {lift: 0 for lift in LIFTS}
    for activity in activities:
        if split_letter(activity) and activity_date(activity) >= since:
            # Descriptions only come with the per-activity endpoint
            detail = request_json(f"{API}/activities/{activity['id']}", token=token)
            for lift, load in best_loads(detail.get("description")).items():
                records[lift] = max(records[lift], load)
    return records


def summarize_days(activities):
    """Reduce activities to one kind per day; a session often logs twice (watch and Hevy)."""
    days = {}
    seconds = {}
    for activity in activities:
        day = activity_date(activity)
        letter = split_letter(activity)
        sport = activity.get("sport_type")
        is_strength = sport in STRENGTH_SPORTS and activity["moving_time"] >= MIN_WORKOUT_SECONDS
        if letter:
            days[day] = letter
        elif is_strength and days.get(day) not in SPLITS:
            days[day] = "other"
        elif sport == "Run" and day not in days:
            days[day] = "run"
        if letter or is_strength:
            seconds[day] = max(seconds.get(day, 0), activity["moving_time"])
    return days, seconds


def week_streak(workout_days, today):
    """Consecutive weeks with a workout; the current week doesn't break it until it's over."""
    weeks = {day - datetime.timedelta(days=day.weekday()) for day in workout_days}
    current = today - datetime.timedelta(days=today.weekday())
    if current not in weeks:
        current -= datetime.timedelta(days=7)
    streak = 0
    while current in weeks:
        streak += 1
        current -= datetime.timedelta(days=7)
    return streak


def calendar_weeks(today):
    """Same shape as GitHub's contribution calendar: weeks start on Sunday."""
    start = today - datetime.timedelta(days=364)
    start -= datetime.timedelta(days=(start.weekday() + 1) % 7)
    weeks = []
    day = start
    while day <= today:
        week = []
        for _ in range(7):
            if day <= today:
                week.append({"date": day.isoformat(), "weekday": (day.weekday() + 1) % 7})
            day += datetime.timedelta(days=1)
        weeks.append({"contributionDays": week})
    return weeks


def record_board(records):
    x, y, width, height = 352, 12, 290, 112
    parts = [rect(x, y, width, height, "#8a8f99"), rect(x + 4, y + 4, width - 8, height - 8, "#f3f4f1"),
             text(f"MELHORES CARGAS {RECORD_WINDOW_DAYS} DIAS", x + 8, y + 10, "#d9443c")]
    for index, (lift, load) in enumerate(records.items()):
        line_y = y + 30 + index * 19
        value = f"{load:g} KG" if load else "-"
        parts.append(text(lift, x + 8, line_y, "#22252b"))
        parts.append(text(value, x + width - 8 - len(value) * 12, line_y, "#22252b"))
    return "".join(parts)


def field(weeks, days, today):
    parts = []
    for week_index, week in enumerate(weeks):
        for day in week["contributionDays"]:
            date = datetime.date.fromisoformat(day["date"])
            x = MARGIN + week_index * CELL
            y = FIELD_Y + day["weekday"] * CELL
            parts.append(f'<use href="#floor" x="{x}" y="{y}"/>')
            if date in days:
                parts.append(f'<use href="#{days[date]}" x="{x}" y="{y}"/>')
            if date == today:
                parts.append(f'<rect class="today" x="{x + 1}" y="{y + 1}" width="{CELL - 2}" height="{CELL - 2}"/>')
    return "".join(parts)


def legend(y):
    items = [(letter, name) for letter, (name, _) in SPLITS.items()] + [("other", "OUTRO"), ("run", "CORRIDA")]
    parts = []
    x = MARGIN
    for sprite, label in items:
        parts.append(f'<use href="#floor" x="{x}" y="{y + 6}"/><use href="#{sprite}" x="{x}" y="{y + 6}"/>')
        parts.append(text(label, x + CELL + 4, y + 7, "#c9d1d9"))
        x += CELL + 4 + len(label) * 12 + 16
    return "".join(parts)


def render(activities, records, today):
    since = today - datetime.timedelta(days=364)
    days, seconds = summarize_days([a for a in activities if activity_date(a) >= since])
    workout_days = [day for day, kind in days.items() if kind != "run"]
    hours = round(sum(seconds.values()) / 3600)
    streak = week_streak(workout_days, today)

    weeks = calendar_weeks(today)
    width = MARGIN * 2 + len(weeks) * CELL
    months_y = FIELD_Y + 7 * CELL
    legend_y = months_y + BAR_H
    height = legend_y + BAR_H + 4

    defs = "".join(f'<g id="{name}">{pixels_to_paths(rows, TRAINING_COLORS, PIXEL)}</g>'
                   for name, rows in SPRITES.items())
    style = """
    .stand { animation: stand 2.4s steps(1) infinite; }
    .squat { animation: squat 2.4s steps(1) infinite; }
    .led { animation: blink 1.2s steps(2) infinite; }
    .today { fill: none; stroke: #58e06f; stroke-width: 2; animation: blink 1.6s steps(2) infinite; }
    @keyframes stand { 0%, 49% { opacity: 1; } 50%, 100% { opacity: 0; } }
    @keyframes squat { 0%, 49% { opacity: 0; } 50%, 100% { opacity: 1; } }
    @keyframes blink { 50% { opacity: 0.2; } }
    @media (prefers-reduced-motion: reduce) {
      .stand, .squat, .led, .today { animation: none; }
      .squat { display: none; }
    }
    """
    panel_rows = [
        ("TREINOS:", f"{len(workout_days)} NO ANO"),
        ("SEMANAS:", f"{streak} {'SEGUIDA' if streak == 1 else 'SEGUIDAS'}"),
        ("TEMPO:", f"{hours} HORAS NO ANO"),
    ]
    return "".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        'shape-rendering="crispEdges" role="img" aria-label="Resumo dos treinos de academia do último ano">',
        f"<style>{style}</style><defs>{defs}",
        f'<clipPath id="frame"><rect width="{width}" height="{height}" rx="8"/></clipPath></defs>',
        '<g clip-path="url(#frame)">',
        rect(0, 0, width, FIELD_Y, "#3a3f4b"),
        rect(0, 0, width, 12, "#2e323c"),
        rect(0, FIELD_Y - 4, width, 4, "#191b20"),
        rect(0, FIELD_Y - 18, width, 6, "#d9443c"),
        led_panel(panel_rows),
        record_board(records),
        squat_rack(652),
        dumbbell_rack(792),
        rect(0, FIELD_Y, width, 7 * CELL, "#191b20"),
        field(weeks, days, today),
        rect(0, months_y, width, height - months_y, "#101216"),
        rect(0, months_y, width, 2, "#3a3f4b"),
        month_labels(weeks, months_y + 8),
        rect(0, legend_y, width, 2, "#3a3f4b"),
        legend(legend_y),
        "</g></svg>\n",
    ])


def main():
    credentials = [os.environ.get(name) for name in
                   ("STRAVA_CLIENT_ID", "STRAVA_CLIENT_SECRET", "STRAVA_REFRESH_TOKEN")]
    if not all(credentials):
        print("Strava credentials not set: keeping the current image.")
        return
    today = datetime.datetime.now(BRAZIL_TZ).date()
    token = access_token(*credentials)
    activities = fetch_activities(token, today - datetime.timedelta(days=364))
    records = fetch_records(token, activities, today)
    OUTPUT.write_text(render(activities, records, today), encoding="utf-8")


if __name__ == "__main__":
    main()
