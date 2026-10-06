"""Save player names, statuses, and reasons from an official NBA report as JSON.

Report publication date may differ from game date. Non-injury absences are
retained, and teams that have not submitted a report are not player entries.
"""

import argparse
from datetime import date, datetime
from html.parser import HTMLParser
from io import BytesIO
import json
import os
from pathlib import Path
import re
import sys
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen


REPORT_NAME = re.compile(
    r"Injury-Report_(\d{4}-\d{2}-\d{2})_(\d{2})(?:_(\d{2}))?(AM|PM)\.pdf$",
    re.IGNORECASE,
)
PLAYER_DATA = Path(__file__).resolve().parents[1] / "player_data"
STATUSES = {"Available", "Probable", "Questionable", "Doubtful", "Out"}


class InjuryScrapeError(Exception):
    """Report unavailable, request blocked, or unreadable report."""


class ReportLinks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)


def report_timestamp(url):
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname != "ak-static.cms.nba.com"
            or not parsed.path.startswith("/referee/injury/")):
        raise InjuryScrapeError("Expected an official NBA injury-report PDF URL")
    match = REPORT_NAME.fullmatch(parsed.path.rsplit("/", 1)[-1])
    if not match:
        raise InjuryScrapeError("Unrecognized injury-report filename")
    day, hour, minute, period = match.groups()
    try:
        if not 1 <= int(hour) <= 12 or not 0 <= int(minute or "0") <= 59:
            raise ValueError("Invalid report time")
        report_day = date.fromisoformat(day)
        hour24 = int(hour) % 12 + (12 if period.upper() == "PM" else 0)
        return datetime(report_day.year, report_day.month, report_day.day, hour24, int(minute or "0"))
    except ValueError:
        raise InjuryScrapeError("Invalid date or time in report filename") from None


def index_url(day):
    season = day.year if day.month >= 10 else day.year - 1
    return "https://official.nba.com/nba-injury-report-{}-{:02d}-season/".format(
        season, (season + 1) % 100
    )


def find_latest_report(html, page_url, day):
    parser = ReportLinks()
    parser.feed(html)
    candidates = []
    for href in set(parser.links):
        url = urljoin(page_url, href)
        try:
            timestamp = report_timestamp(url)
        except InjuryScrapeError:
            continue
        if timestamp.date() == day:
            candidates.append((timestamp, url))
    if not candidates:
        raise InjuryScrapeError(
            "No official report links found for {}. The report may not be published, "
            "or the page may no longer list that date. Supply --report-url for an existing PDF."
            .format(day.isoformat())
        )
    return max(candidates)[1]


def download(url, timeout=20):
    request = Request(url, headers={"User-Agent": "ESPNFantasyHelper/0.1 (NBA injury reports)"})
    try:
        with urlopen(request, timeout=timeout) as response:
            content = response.read(20_000_001)
            if len(content) > 20_000_000:
                raise InjuryScrapeError("Response exceeds the 20 MB size limit")
            return content
    except HTTPError as exc:
        if exc.code in {403, 429}:
            raise InjuryScrapeError("HTTP {}: request blocked or rate-limited; no bypass attempted".format(exc.code)) from None
        if exc.code == 404:
            raise InjuryScrapeError("HTTP 404: official page or report is not available") from None
        raise InjuryScrapeError("NBA source returned HTTP {}".format(exc.code)) from None
    except (URLError, TimeoutError, OSError):
        raise InjuryScrapeError("NBA source connection failed or timed out") from None


def extract_report_text(content):
    if not content.startswith(b"%PDF-"):
        raise InjuryScrapeError("NBA source did not return a PDF")
    try:
        from pypdf import PdfReader
    except ImportError:
        raise InjuryScrapeError("Install the PDF dependency with: python -m pip install 'pypdf>=4,<6'") from None
    try:
        reader = PdfReader(BytesIO(content))
        text = "\n\n".join(page.extract_text(extraction_mode="layout") or "" for page in reader.pages)
    except Exception as exc:
        raise InjuryScrapeError("Could not extract PDF text ({})".format(type(exc).__name__)) from None
    if not text.strip() or not re.search(r"Injury\s*Report", text, re.IGNORECASE):
        raise InjuryScrapeError("PDF contains no recognizable injury-report text")
    return text


def resolve_report_url(day=None, report_url=None, timeout=20):
    if timeout <= 0:
        raise InjuryScrapeError("Timeout must be positive")
    if report_url:
        timestamp = report_timestamp(report_url)
        if day is not None and timestamp.date() != day:
            raise InjuryScrapeError("Report publication date does not match --date")
    else:
        # Defaults to the user's computer's local calendar date.
        day = day or date.today()
        page_url = index_url(day)
        html = download(page_url, timeout).decode("utf-8-sig")
        report_url = find_latest_report(html, page_url, day)
    return report_url


def scrape_injuries(day=None, report_url=None, timeout=20):
    """Return (source_url, full_report_text) for callers needing the raw text."""
    url = resolve_report_url(day, report_url, timeout)
    return url, extract_report_text(download(url, timeout))


def join_words(words):
    return " ".join(word["text"] for word in sorted(words, key=lambda w: (round(w["top"] / 2), w["x0"])))


def parse_page_injuries(words, page_height, columns=None, lines=None, previous_record=None):
    """Use PDF columns and row positions to attach wrapped reasons correctly."""
    headers = {}
    for word in words:
        if word["text"] in {"Player", "Current", "Reason"}:
            headers.setdefault(word["text"], word)
    if set(headers) == {"Player", "Current", "Reason"}:
        name_x, status_x, reason_x = (headers[key]["x0"] for key in ("Player", "Current", "Reason"))
        header_y = max(word["top"] for word in headers.values())
    elif columns is not None:
        # Official PDFs sometimes print column headings only on the first page.
        name_x, status_x, reason_x = columns
        header_y = max((word["top"] + 8 for word in words if word["text"] == "Report:"), default=60)
    else:
        raise InjuryScrapeError("Injury report column headers are missing or changed")
    body = [word for word in words if header_y + 5 < word["top"] < page_height - 30]
    notice_rows = set()
    for word in body:
        if word["text"] == "NOT":
            same_line = [w for w in body if abs(w["top"] - word["top"]) <= 2]
            if "NOT YET SUBMITTED" in join_words(same_line):
                notice_rows.add(word["top"])
    body = [word for word in body if not any(abs(word["top"] - y) <= 2 for y in notice_rows)]
    edges = sorted({line["top"] for line in (lines or [])
                    if abs(line["top"] - line["bottom"]) < 1
                    and line["x0"] <= reason_x < line["x1"]})
    anchors = sorted([word for word in body if status_x <= word["x0"] < reason_x
                      and word["text"] in STATUSES], key=lambda w: w["top"])
    records = []
    if anchors and edges and previous_record is not None:
        first_lower = max((edge for edge in edges if edge < anchors[0]["top"]), default=header_y + 5)
        continuation = join_words([w for w in body if w["x0"] >= reason_x and w["top"] < first_lower])
        if continuation:
            previous_record["injury_type"] += " " + continuation
    for index, anchor in enumerate(anchors):
        y = anchor["top"]
        names = [word for word in body if name_x <= word["x0"] < status_x
                 and abs(word["top"] - y) <= 3]
        raw_name = join_words(names)
        if "," not in raw_name:
            raise InjuryScrapeError("Cannot match a player name to a reported status")
        last, first = (part.strip() for part in raw_name.split(",", 1))
        if not first or not last:
            raise InjuryScrapeError("Incomplete player name in report")
        # Descriptions can begin above the player's baseline and continue below
        # it. Midpoints separate adjacent player rows, including multiline cells.
        lower = (anchors[index - 1]["top"] + y) / 2 if index else header_y + 5
        upper = (y + anchors[index + 1]["top"]) / 2 if index + 1 < len(anchors) else page_height - 30
        if edges:
            # Use drawn row separators when present; they also isolate reasons
            # continued from the previous page and non-player team notices.
            lower = max((edge for edge in edges if edge < y), default=lower)
            upper = min((edge for edge in edges if edge > y), default=upper)
        reasons = [word for word in body if word["x0"] >= reason_x and lower <= word["top"] < upper]
        reason = join_words(reasons)
        if not reason:
            raise InjuryScrapeError("Missing injury reason for " + first + " " + last)
        records.append({"name": first + " " + last, "status": anchor["text"], "injury_type": reason})
    return records


def extract_injury_records(content):
    if not content.startswith(b"%PDF-"):
        raise InjuryScrapeError("NBA source did not return a PDF")
    try:
        import pdfplumber
    except ImportError:
        raise InjuryScrapeError("Install the PDF parser with: python -m pip install 'pdfplumber>=0.11,<0.12'") from None
    try:
        with pdfplumber.open(BytesIO(content)) as pdf:
            records = []
            columns = None
            for page in pdf.pages:
                # A small x tolerance restores spaces between the PDF's words.
                words = page.extract_words(x_tolerance=1, y_tolerance=2)
                headers = {word["text"]: word["x0"] for word in words
                           if word["text"] in {"Player", "Current", "Reason"} and word["top"] < 120}
                if set(headers) == {"Player", "Current", "Reason"}:
                    columns = tuple(headers[key] for key in ("Player", "Current", "Reason"))
                records.extend(parse_page_injuries(words, page.height, columns, page.lines,
                                                  records[-1] if records else None))
    except InjuryScrapeError:
        raise
    except Exception as exc:
        raise InjuryScrapeError("Could not parse injury PDF ({})".format(type(exc).__name__)) from None
    if not records:
        raise InjuryScrapeError("No player entries could be extracted; existing JSON was not replaced")
    return records


def save_injury_report(url, records, output=None):
    report_day = report_timestamp(url).date().isoformat()
    destination = Path(output) if output else PLAYER_DATA / ("injuries_" + report_day + ".json")
    payload = {"report_date": report_day, "source_url": url, "injuries": records}
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=str(destination.parent),
                                     suffix=".tmp", delete=False) as stream:
        temporary = stream.name
        json.dump(payload, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")
    try:
        os.replace(temporary, str(destination))
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", type=date.fromisoformat, help="Report publication date, YYYY-MM-DD; defaults to today")
    parser.add_argument("--report-url", help="Direct official NBA PDF URL; skips link discovery")
    parser.add_argument("--timeout", type=float, default=20)
    parser.add_argument("--output", type=Path, help="JSON output path; defaults to player_data/injuries_YYYY-MM-DD.json")
    args = parser.parse_args()
    try:
        url = resolve_report_url(args.date, args.report_url, args.timeout)
        records = extract_injury_records(download(url, args.timeout))
        destination = save_injury_report(url, records, args.output)
    except (InjuryScrapeError, UnicodeError, OSError) as exc:
        print("Unable to collect injury report: " + str(exc), file=sys.stderr)
        return 1
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print("Source: " + url)
    print("Saved {} player entries to {}".format(len(records), destination.resolve()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
