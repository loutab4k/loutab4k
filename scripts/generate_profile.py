#!/usr/bin/env python3
"""Generate light and dark GitHub profile cards from public GitHub data."""

from __future__ import annotations

import base64
import calendar
import html
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "profile.json"
API = "https://api.github.com"


def github_get(path: str) -> object:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "loutab4k-profile-generator",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(f"{API}{path}", headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def download_data_uri(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "loutab4k-profile-generator"})
    with urllib.request.urlopen(request, timeout=30) as response:
        content_type = response.headers.get_content_type()
        payload = base64.b64encode(response.read()).decode("ascii")
    return f"data:{content_type};base64,{payload}"


def file_data_uri(path: Path) -> str:
    media_types = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg"}
    media_type = media_types.get(path.suffix.lower())
    if media_type is None:
        raise ValueError(f"Unsupported portrait format: {path.suffix}")
    payload = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{media_type};base64,{payload}"


def account_age(created_at: str) -> str:
    start = datetime.fromisoformat(created_at.replace("Z", "+00:00")).date()
    today = datetime.now(timezone.utc).date()
    years = today.year - start.year
    anniversary_year = start.year + years
    anniversary_day = min(start.day, calendar.monthrange(anniversary_year, start.month)[1])
    anniversary = start.replace(year=anniversary_year, day=anniversary_day)
    if anniversary > today:
        years -= 1
        anniversary_year -= 1
        anniversary_day = min(start.day, calendar.monthrange(anniversary_year, start.month)[1])
        anniversary = start.replace(year=anniversary_year, day=anniversary_day)
    months = (today.year - anniversary.year) * 12 + today.month - anniversary.month
    month_year = anniversary.year + (anniversary.month - 1 + months) // 12
    month = (anniversary.month - 1 + months) % 12 + 1
    month_day = min(anniversary.day, calendar.monthrange(month_year, month)[1])
    month_mark = anniversary.replace(year=month_year, month=month, day=month_day)
    if month_mark > today:
        months -= 1
        month_year = anniversary.year + (anniversary.month - 1 + months) // 12
        month = (anniversary.month - 1 + months) % 12 + 1
        month_day = min(anniversary.day, calendar.monthrange(month_year, month)[1])
        month_mark = anniversary.replace(year=month_year, month=month, day=month_day)
    days = (today - month_mark).days
    return f"{years}y {months}m {days}d"


def collect_stats(username: str) -> dict[str, object]:
    user = github_get(f"/users/{urllib.parse.quote(username)}")
    repos = github_get(
        f"/users/{urllib.parse.quote(username)}/repos?per_page=100&type=owner&sort=updated"
    )
    if not isinstance(user, dict) or not isinstance(repos, list):
        raise ValueError("Unexpected GitHub API response")

    stars = 0
    forks = 0
    for repo in repos:
        if not isinstance(repo, dict) or repo.get("fork"):
            continue
        stars += int(repo.get("stargazers_count", 0))
        forks += int(repo.get("forks_count", 0))
    commits: int | None = None
    try:
        query = urllib.parse.quote(f"author:{username}")
        result = github_get(f"/search/commits?q={query}&per_page=1")
        if isinstance(result, dict):
            commits = int(result.get("total_count", 0))
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, ValueError):
        pass

    return {
        "user": user,
        "repo_count": len([repo for repo in repos if isinstance(repo, dict) and not repo.get("fork")]),
        "stars": stars,
        "forks": forks,
        "commits": commits,
    }


def fit(text: object, limit: int) -> str:
    value = str(text)
    return value if len(value) <= limit else f"{value[: limit - 1]}…"


def svg_text(x: int, y: int, value: object, css_class: str = "value") -> str:
    return f'<text x="{x}" y="{y}" class="{css_class}">{html.escape(str(value))}</text>'


def row(y: int, label: str, value: object, value_x: int = 690) -> str:
    dots = "·" * max(2, 29 - len(label))
    return (
        svg_text(405, y, label, "label")
        + svg_text(405 + len(label) * 9 + 10, y, dots, "dots")
        + svg_text(value_x, y, fit(value, 42), "value")
    )


def render(config: dict[str, object], stats: dict[str, object], theme: str) -> str:
    user = stats["user"]
    assert isinstance(user, dict)
    username = str(config["username"])
    display_name = str(config.get("display_name") or user.get("name") or username)
    portrait_value = str(config.get("portrait", "")).strip()
    portrait_path = ROOT / portrait_value if portrait_value else None
    avatar = (
        file_data_uri(portrait_path)
        if portrait_path is not None and portrait_path.is_file()
        else download_data_uri(str(user["avatar_url"]))
    )
    operating_systems = ", ".join(map(str, config.get("operating_systems", []))) or "—"
    programming = ", ".join(map(str, config.get("languages_programming", []))) or "—"
    other_languages = ", ".join(map(str, config.get("languages_other", []))) or "—"
    spoken = ", ".join(map(str, config.get("languages_spoken", []))) or "—"
    interests = config.get("interests", {})
    if not isinstance(interests, dict):
        interests = {}
    role = str(config.get("role") or user.get("bio") or "Developer")
    website = str(config.get("website") or user.get("blog") or f"github.com/{username}")
    commits = stats["commits"] if stats["commits"] is not None else "n/a"

    palette = {
        "dark": {"bg": "#0d1117", "card": "#161b22", "border": "#30363d", "text": "#c9d1d9", "muted": "#7d8590", "accent": "#58a6ff", "warm": "#f0883e"},
        "light": {"bg": "#ffffff", "card": "#f6f8fa", "border": "#d0d7de", "text": "#1f2328", "muted": "#656d76", "accent": "#0969da", "warm": "#bc4c00"},
    }[theme]

    lines = [
        row(72, "User", f"{username}@github"),
        row(98, "Role", role),
        row(124, "OS", operating_systems),
        row(150, "IDE", config.get("ide", "—")),
        row(176, "Editor", config.get("editor", "—")),
        row(202, "Languages.Programming", programming),
        row(228, "Languages.Other", other_languages),
        row(254, "Languages.Real", spoken),
        row(280, "Account age", account_age(str(user["created_at"]))),
        svg_text(405, 318, "─ Contact " + "─" * 37, "section"),
        row(348, "Email", config.get("email", "—")),
        row(374, "Discord", config.get("discord", "—")),
        svg_text(405, 414, "─ Interests " + "─" * 35, "section"),
        row(444, "Mindset", interests.get("mindset", "—")),
        row(470, "Systems", interests.get("systems", "—")),
        row(496, "Learning", interests.get("learning", "—")),
        svg_text(405, 536, "─ GitHub stats " + "─" * 32, "section"),
        row(566, "Repositories", stats["repo_count"]),
        row(592, "Commits", commits),
        row(618, "Stars / Forks", f'{stats["stars"]} / {stats["forks"]}'),
        row(644, "Followers / Following", f'{user.get("followers", 0)} / {user.get("following", 0)}'),
    ]

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="690" viewBox="0 0 1100 690" role="img" aria-labelledby="title desc">
  <title id="title">{html.escape(display_name)} — GitHub profile</title>
  <desc id="desc">Developer profile and live public GitHub statistics for {html.escape(username)}.</desc>
  <defs>
    <clipPath id="avatarClip"><circle cx="200" cy="210" r="116"/></clipPath>
    <filter id="shadow" x="-10%" y="-10%" width="120%" height="130%"><feDropShadow dx="0" dy="8" stdDeviation="14" flood-opacity=".18"/></filter>
  </defs>
  <style>
    text {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace; font-size: 15px; fill: {palette["text"]}; }}
    .name {{ font-size: 28px; font-weight: 700; fill: {palette["text"]}; }}
    .handle {{ font-size: 16px; fill: {palette["muted"]}; }}
    .label {{ fill: {palette["warm"]}; }}
    .value {{ fill: {palette["accent"]}; }}
    .dots {{ fill: {palette["muted"]}; opacity: .55; }}
    .section {{ fill: {palette["muted"]}; }}
  </style>
  <rect width="1100" height="690" rx="18" fill="{palette["bg"]}"/>
  <rect x="18" y="18" width="1064" height="654" rx="14" fill="{palette["card"]}" stroke="{palette["border"]}" filter="url(#shadow)"/>
  <circle cx="200" cy="210" r="120" fill="none" stroke="{palette["accent"]}" stroke-width="2" opacity=".8"/>
  <image href="{avatar}" x="84" y="94" width="232" height="232" preserveAspectRatio="xMidYMid slice" clip-path="url(#avatarClip)"/>
  {svg_text(200, 374, display_name, "name").replace('x="200"', 'x="200" text-anchor="middle"')}
  {svg_text(200, 403, '@' + username, "handle").replace('x="200"', 'x="200" text-anchor="middle"')}
  {svg_text(200, 440, fit(website, 32), "value").replace('x="200"', 'x="200" text-anchor="middle"')}
  <line x1="365" y1="54" x2="365" y2="636" stroke="{palette["border"]}"/>
  {''.join(lines)}
</svg>'''


def main() -> int:
    config = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    username = str(config.get("username", "")).strip()
    if not username:
        print("profile.json: username is required", file=sys.stderr)
        return 2
    stats = collect_stats(username)
    for theme in ("dark", "light"):
        (ROOT / f"profile-{theme}.svg").write_text(render(config, stats, theme), encoding="utf-8")
    print(f"Generated profile SVGs for {username}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
