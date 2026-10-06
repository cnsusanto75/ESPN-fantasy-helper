"""Print the latest official NBA injury report published on a given day.

No files or database records are written. Output is unformatted PDF text and
may include tomorrow's games, rest, and teams that have not submitted reports.
"""

import argparse
from datetime import date, datetime
from html.parser import HTMLParser
from io import BytesIO
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen


REPORT_NAME = re.compile(
    r"Injury-Report_(\d{4}-\d{2}-\d{2})_(\d{2})(?:_(\d{2}))?(AM|PM)\.pdf$",
    re.IGNORECASE,
)


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


def scrape_injuries(day=None, report_url=None, timeout=20):
    """Return (source_url, full_report_text); keep every report page."""
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
    return report_url, extract_report_text(download(report_url, timeout))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", type=date.fromisoformat, help="Report publication date, YYYY-MM-DD; defaults to today")
    parser.add_argument("--report-url", help="Direct official NBA PDF URL; skips link discovery")
    parser.add_argument("--timeout", type=float, default=20)
    args = parser.parse_args()
    try:
        url, text = scrape_injuries(args.date, args.report_url, args.timeout)
    except (InjuryScrapeError, UnicodeError) as exc:
        print("Unable to collect injury report: " + str(exc), file=sys.stderr)
        return 1
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    print("Source: " + url)
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
