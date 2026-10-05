"""Collect Basketball Reference regular-season per-game statistics.

Run from the repository root:
    python algorithm/sources/stats.py --season 2025
    python algorithm/sources/stats.py --season 2025 --html saved-page.html

The argument is the season START year; Basketball Reference uses the end year.
Only the standard library is required. Blocked requests are never bypassed.
"""

import argparse
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from hashlib import sha256
from html.parser import HTMLParser
import json
import math
import os
from pathlib import Path
import re
import sqlite3
import tempfile
import time
from typing import Dict, List, Optional, Union
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PLAYER_DATA = Path(__file__).resolve().parents[1] / "player_data"
DEFAULT_DATABASE = PLAYER_DATA / "season_stats.db"
TABLE_IDS = {"per_game_stats", "per_game"}
# Support both older and newer semantic column attributes. Never rely on order.
COLUMNS = {
    "games": ("g", "games"),
    "games_started": ("gs", "games_started"),
    "minutes": ("mp_per_g", "mp", "minutes"),
    "points": ("pts_per_g", "pts", "points"),
    "rebounds": ("trb_per_g", "trb", "reb"),
    "assists": ("ast_per_g", "ast"),
    "steals": ("stl_per_g", "stl"),
    "blocks": ("blk_per_g", "blk"),
    "turnovers": ("tov_per_g", "tov"),
    "field_goals_made": ("fg_per_g", "fg"),
    "field_goals_attempted": ("fga_per_g", "fga"),
    "field_goal_pct": ("fg_pct",),
    "three_pointers_made": ("fg3_per_g", "fg3"),
    "three_pointers_attempted": ("fg3a_per_g", "fg3a"),
    "three_point_pct": ("fg3_pct",),
    "free_throws_made": ("ft_per_g", "ft"),
    "free_throws_attempted": ("fta_per_g", "fta"),
    "free_throw_pct": ("ft_pct",),
    "offensive_rebounds": ("orb_per_g", "orb"),
    "defensive_rebounds": ("drb_per_g", "drb"),
    "personal_fouls": ("pf_per_g", "pf"),
}
PERCENTAGES = {"field_goal_pct", "three_point_pct", "free_throw_pct"}
COUNTS = {"games", "games_started"}
PLAYER_LINK = re.compile(r"^/players/[a-z]/([a-z0-9]+)\.html$")


class ScrapeError(Exception):
    """A fetch, schema, or validation failure that must not replace good data."""


@dataclass
class Node:
    tag: str
    attrs: Dict[str, str] = field(default_factory=dict)
    children: List[Union["Node", str]] = field(default_factory=list)

    def walk(self, tag: Optional[str] = None):
        if tag is None or self.tag == tag:
            yield self
        for child in self.children:
            if isinstance(child, Node):
                yield from child.walk(tag)

    def text(self):
        return "".join(c.text() if isinstance(c, Node) else c for c in self.children).strip()


class PageParser(HTMLParser):
    """Small DOM parser, including tables embedded in HTML comments."""

    VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = Node("document")
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in self.VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in self.VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)

    def handle_comment(self, data):
        if "<table" in data.lower():
            parser = PageParser()
            parser.feed(data)
            self.stack[-1].children.extend(parser.root.children)


def number(text: str, column: str):
    if not text or text in {"-", "—", "–", "N/A"}:
        return None
    try:
        value = float(text.replace(",", ""))
    except ValueError:
        raise ScrapeError("Invalid numeric value in column " + column) from None
    if not math.isfinite(value) or value < 0:
        raise ScrapeError("Negative or nonfinite value in column " + column)
    if column in PERCENTAGES and value > 1:
        raise ScrapeError("Percentage outside 0–1 in column " + column)
    if column in COUNTS:
        if not value.is_integer():
            raise ScrapeError("Noninteger game count in column " + column)
        return int(value)
    return value


def validate_record(record):
    stats = record["stats"]
    if stats["games"] is None or stats["games"] < 1:
        raise ScrapeError("Missing or invalid games played for " + record["player_id"])
    for made, attempted in (
        ("field_goals_made", "field_goals_attempted"),
        ("three_pointers_made", "three_pointers_attempted"),
        ("free_throws_made", "free_throws_attempted"),
        ("games_started", "games"),
    ):
        if stats[made] is not None and stats[attempted] is not None and stats[made] > stats[attempted]:
            raise ScrapeError(made + " exceeds " + attempted + " for " + record["player_id"])


def parse_stats(html: str):
    parser = PageParser()
    parser.feed(html)
    tables = [node for node in parser.root.walk("table") if node.attrs.get("id") in TABLE_IDS]
    if len(tables) != 1:
        raise ScrapeError("Expected one per-game stats table; page may be blocked or its structure changed")
    records, identities = [], set()
    for row in tables[0].walk("tr"):
        cells = {cell.attrs["data-stat"]: cell for cell in row.walk()
                 if cell.tag in {"td", "th"} and "data-stat" in cell.attrs}
        player_cell = cells.get("name_display") or cells.get("player")
        if player_cell is None:
            continue
        if player_cell.text() in {"Player", "League Average", "League Averages"}:
            continue
        links = [(link, PLAYER_LINK.fullmatch(link.attrs.get("href", "")))
                 for link in player_cell.walk("a")]
        links = [(link, match) for link, match in links if match is not None]
        if not links:
            # Header and summary rows have no player link. A data row without
            # an identifier is rejected rather than silently disappearing.
            if any(key in cells for key in ("pts", "pts_per_g")) and player_cell.tag == "td":
                raise ScrapeError("Player row is missing a stable player link: " + player_cell.text())
            continue
        link, match = links[0]
        team_cell = cells.get("team_name_abbr") or cells.get("team_id") or cells.get("team")
        position_cell = cells.get("pos") or cells.get("position")
        if team_cell is None or position_cell is None or not team_cell.text():
            raise ScrapeError("Missing team or position column")
        team = team_cell.text().upper()
        player_id = match.group(1)
        if (player_id, team) in identities:
            raise ScrapeError("Duplicate player/team row: " + player_id + " / " + team)
        identities.add((player_id, team))
        stats = {}
        for column, aliases in COLUMNS.items():
            cell = next((cells[key] for key in aliases if key in cells), None)
            if cell is None:
                raise ScrapeError("Missing required stats column: " + column)
            stats[column] = number(cell.text(), column)
        name = link.text()
        if not name:
            raise ScrapeError("Missing player name")
        record = {"player_id": player_id, "name": name, "team": team,
                  "position": position_cell.text(),
                  "is_total": team == "TOT" or bool(re.fullmatch(r"\d+TM", team)),
                  "stats": stats}
        validate_record(record)
        records.append(record)
    if not records:
        raise ScrapeError("Stats table has no valid player rows; no snapshot saved")
    overall = {}
    for record in records:
        overall.setdefault(record["player_id"], []).append(record)
    for player_id, rows in overall.items():
        totals = [row for row in rows if row["is_total"]]
        if len(totals) > 1 or (len(rows) > 1 and len(totals) != 1):
            raise ScrapeError("Cannot identify one combined-season row for " + player_id)
    return records


def season_url(season: int):
    if not 1946 <= season <= 2100:
        raise ScrapeError("Season must be a start year between 1946 and 2100")
    return "https://www.basketball-reference.com/leagues/NBA_{}_per_game.html".format(season + 1)


def fetch_html(url: str, timeout: float = 30):
    request = Request(url, headers={"User-Agent": "ESPNFantasyHelper/0.1 (season stats collector)",
                                    "Accept": "text/html"})
    for attempt in range(3):
        try:
            with urlopen(request, timeout=timeout) as response:
                if "text/html" not in response.headers.get("Content-Type", ""):
                    raise ScrapeError("Source did not return an HTML page")
                raw = response.read(10_000_001)
                if len(raw) > 10_000_000:
                    raise ScrapeError("HTML response exceeds the size limit")
                return raw.decode(response.headers.get_content_charset() or "utf-8")
        except HTTPError as exc:
            if exc.code in {403, 429}:
                raise ScrapeError("HTTP {}: source blocked or rate-limited the request; stop and use a permitted data source or saved HTML".format(exc.code)) from None
            if exc.code < 500 or attempt == 2:
                raise ScrapeError("Source returned HTTP {}".format(exc.code)) from None
        except (URLError, TimeoutError, OSError):
            if attempt == 2:
                raise ScrapeError("Source connection failed or timed out") from None
        if attempt < 2:
            time.sleep(2 ** attempt)


@contextmanager
def database_connection(path: Path):
    # sqlite3's own context manager commits/rolls back but does not close.
    # Always release handles so refreshes and tests work on Windows too.
    db = sqlite3.connect(str(path))
    try:
        with db:
            yield db
    finally:
        db.close()


def create_stats_table(db, table_name="season_player_stats"):
    # Names come from our fixed schema, never external HTML or CLI input.
    stat_columns = ",\n".join(
        '"{}" {}'.format(name, "INTEGER" if name in COUNTS else "REAL")
        for name in COLUMNS
    )
    db.execute("""CREATE TABLE {} (
        snapshot_id INTEGER NOT NULL REFERENCES stat_snapshots(id),
        source_player_id TEXT NOT NULL,
        player_name TEXT NOT NULL,
        team TEXT NOT NULL,
        position TEXT NOT NULL,
        is_total INTEGER NOT NULL CHECK (is_total IN (0,1)),
        {},
        PRIMARY KEY (snapshot_id, source_player_id, team)
    )""".format(table_name, stat_columns))


def insert_stats(db, rows, table_name="season_player_stats"):
    columns = ["snapshot_id", "source_player_id", "player_name", "team", "position", "is_total"] + list(COLUMNS)
    db.executemany("INSERT INTO {} ({}) VALUES ({})".format(
        table_name, ",".join(columns), ",".join("?" for _ in columns)
    ), rows)


def migrate_json_stats(db):
    """Replace the old JSON table atomically, retaining every snapshot and row."""
    rows = db.execute("""SELECT snapshot_id,source_player_id,player_name,team,
                         position,is_total,stats_json FROM season_player_stats""").fetchall()
    converted = []
    for row in rows:
        try:
            values = json.loads(row[6])
            if not isinstance(values, dict) or set(values) != set(COLUMNS):
                raise ValueError("Unexpected stat keys")
            values = {key: number(str(value), key) if value is not None else None
                      for key, value in values.items()}
            validate_record({"player_id": row[1], "stats": values})
        except (ValueError, TypeError, ScrapeError):
            raise ScrapeError("Cannot migrate invalid stats_json for " + row[1]) from None
        converted.append(tuple(row[:6]) + tuple(values[name] for name in COLUMNS))
    create_stats_table(db, "season_player_stats_columns")
    insert_stats(db, converted, "season_player_stats_columns")
    db.execute("DROP VIEW IF EXISTS latest_season_stats")
    db.execute("DROP TABLE season_player_stats")
    db.execute("ALTER TABLE season_player_stats_columns RENAME TO season_player_stats")


def initialize_database(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with database_connection(path) as db:
        db.execute("PRAGMA foreign_keys = ON")
        # Explicit transaction also covers schema changes. Avoid executescript,
        # which commits implicitly and would prevent migration rollback.
        db.execute("BEGIN IMMEDIATE")
        db.execute("""
            CREATE TABLE IF NOT EXISTS stat_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                season_start INTEGER NOT NULL,
                season_end INTEGER NOT NULL,
                source TEXT NOT NULL,
                source_url TEXT NOT NULL,
                input_origin TEXT NOT NULL,
                collected_at TEXT NOT NULL,
                saved_at TEXT NOT NULL,
                html_sha256 TEXT NOT NULL,
                row_count INTEGER NOT NULL
            )
        """)
        existing = {row[1] for row in db.execute("PRAGMA table_info(season_player_stats)")}
        if not existing:
            create_stats_table(db)
        elif "stats_json" in existing:
            migrate_json_stats(db)
        elif not set(COLUMNS).issubset(existing):
            raise ScrapeError("Unexpected season_player_stats database schema")
        db.execute("CREATE INDEX IF NOT EXISTS snapshot_season ON stat_snapshots(season_start,id)")
        db.execute("""CREATE VIEW IF NOT EXISTS latest_season_stats AS
                SELECT s.season_start, s.season_end, s.collected_at, s.source_url,
                       p.* FROM season_player_stats p JOIN stat_snapshots s ON s.id=p.snapshot_id
                WHERE s.id=(SELECT MAX(id) FROM stat_snapshots WHERE season_start=s.season_start)
                AND (p.is_total=1 OR NOT EXISTS (
                    SELECT 1 FROM season_player_stats other
                    WHERE other.snapshot_id=p.snapshot_id AND other.source_player_id=p.source_player_id
                    AND other.is_total=1
                ))
        """)


def save_snapshot(database: Path, season: int, records, html: str,
                  collected_at: datetime, origin: str):
    initialize_database(database)
    with database_connection(database) as db:
        db.execute("PRAGMA foreign_keys = ON")
        cursor = db.execute("""INSERT INTO stat_snapshots
            (season_start,season_end,source,source_url,input_origin,collected_at,saved_at,html_sha256,row_count)
            VALUES (?,?,?,?,?,?,?,?,?)""", (
                season, season + 1, "basketball_reference", season_url(season), origin,
                collected_at.isoformat(), datetime.now(timezone.utc).isoformat(),
                sha256(html.encode("utf-8")).hexdigest(), len(records),
            ))
        snapshot_id = cursor.lastrowid
        insert_stats(db, [
                (snapshot_id, r["player_id"], r["name"], r["team"], r["position"],
                 int(r["is_total"])) + tuple(r["stats"][name] for name in COLUMNS)
                for r in records
            ])
    return snapshot_id


def scrape_season(season: int, database: Path = DEFAULT_DATABASE,
                  html_file: Optional[Path] = None, refresh: bool = False,
                  cache_hours: float = 24, timeout: float = 30):
    url = season_url(season)
    if cache_hours < 0 or timeout <= 0:
        raise ScrapeError("Cache hours must be nonnegative and timeout must be positive")
    database = Path(database)
    initialize_database(database)
    now = datetime.now(timezone.utc)
    cache_file = database.parent / "html_cache" / "NBA_{}_per_game.json".format(season + 1)
    html, collected_at, origin = None, now, "network"
    if html_file is not None:
        html_file = Path(html_file)
        html = html_file.read_text(encoding="utf-8-sig")
        collected_at = datetime.fromtimestamp(html_file.stat().st_mtime, timezone.utc)
        origin = "file"
    elif not refresh and cache_file.exists():
        try:
            cache = json.loads(cache_file.read_text(encoding="utf-8"))
            cached_at = datetime.fromisoformat(cache["collected_at"])
            if cache["url"] == url and timedelta(0) <= now - cached_at < timedelta(hours=cache_hours):
                html, collected_at, origin = cache["html"], cached_at, "cache"
        except (ValueError, KeyError, TypeError):
            # A corrupt cache never becomes database data. Fetch again normally.
            pass
    if html is None:
        html = fetch_html(url, timeout)
        collected_at = datetime.now(timezone.utc)
    records = parse_stats(html)
    snapshot_id = save_snapshot(database, season, records, html, collected_at, origin)
    if origin == "network":
        cache_file.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=str(cache_file.parent),
                                         suffix=".tmp", delete=False) as stream:
            json.dump({"url": url, "collected_at": collected_at.isoformat(), "html": html}, stream)
            temporary = stream.name
        try:
            os.replace(temporary, str(cache_file))
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    return {"snapshot_id": snapshot_id, "season_start": season, "season_end": season + 1,
            "rows": len(records), "players": len({r["player_id"] for r in records}),
            "input_origin": origin, "collected_at": collected_at.isoformat(),
            "database": str(database.resolve())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--season", type=int, required=True, help="Start year: 2025 for 2025–26")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE)
    parser.add_argument("--html", type=Path, help="Parse a locally saved season page, without network access")
    parser.add_argument("--refresh", action="store_true", help="Ignore cached HTML")
    parser.add_argument("--cache-hours", type=float, default=24)
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args()
    try:
        result = scrape_season(args.season, args.database, args.html, args.refresh,
                               args.cache_hours, args.timeout)
    except (ScrapeError, OSError, sqlite3.Error, UnicodeError) as exc:
        print(json.dumps({"status": "failed", "error": str(exc)}))
        return 1
    print(json.dumps({"status": "success", **result}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
