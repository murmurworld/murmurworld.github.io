"""Read issuer filings from EDGAR and OpenDART for Murmurworld's monthly publication."""
import argparse
import json
import math
import re
import shutil
import sys
import time
from contextlib import ExitStack
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from zipfile import BadZipFile, ZipFile

from public_company_korea import ISSUERS, refresh_korea
from public_company_sec import refresh_sec, sec_cik

ALLOWED = {"www.sec.gov", "data.sec.gov", "dart.fss.or.kr", "opendart.fss.or.kr"}
SEC_BULK = {
    "submissions": "https://www.sec.gov/Archives/edgar/daily-index/bulkdata/submissions.zip",
    "companyfacts": "https://www.sec.gov/Archives/edgar/daily-index/xbrl/companyfacts.zip",
}


class FilingReader:
    def __init__(self, stack, bulk):
        self.temp = Path(stack.enter_context(TemporaryDirectory()))
        self.stack = stack
        self.bulk = bulk
        self.archives = {}
        self.last_request = 0

    def open(self, url):
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.hostname not in ALLOWED:
            raise ValueError("Unexpected filing data host")
        time.sleep(max(0, self.last_request + 0.35 - time.monotonic()))
        self.last_request = time.monotonic()
        req = Request(url, headers={"User-Agent": "Murmurworld financial filings (https://github.com/murmurworld/murmurworld.github.io)", "Accept-Encoding": "identity"})
        return urlopen(req, timeout=45)

    def bytes(self, url):
        for attempt in range(2):
            try:
                with self.open(url) as response:
                    result = response.read(64_000_001)
                if len(result) > 64_000_000:
                    raise ValueError("Filing exceeds size limit")
                return result
            except HTTPError as exc:
                if attempt or exc.code not in {429, 500, 502, 503, 504}:
                    raise
                time.sleep(min(30, int(exc.headers.get("Retry-After", 3)) if str(exc.headers.get("Retry-After", "")).isdigit() else 3))

    def bulk_json(self, group, name):
        if group not in self.archives:
            self.archives[group] = None
            path = self.temp / (group + ".zip")
            print("Using official SEC bulk distribution for " + group, flush=True)
            with self.open(SEC_BULK[group]) as response, path.open("wb") as out:
                shutil.copyfileobj(response, out, length=1024*1024)
            self.archives[group] = self.stack.enter_context(ZipFile(path))
        archive = self.archives[group]
        if archive is None:
            raise OSError("SEC bulk archive unavailable")
        with archive.open(name) as src:
            return json.load(src)

    def json(self, url):
        path = urlsplit(url).path
        group = "submissions" if path.startswith("/submissions/") else "companyfacts"
        filename = path.rsplit("/", 1)[-1]
        matching = urlsplit(url).hostname=="data.sec.gov" and re.fullmatch(r"CIK\d{10}\.json", filename)
        if self.bulk and matching and self.archives.get(group):
            return self.bulk_json(group, filename)
        try:
            return json.loads(self.bytes(url))
        except (OSError, ValueError):
            if not self.bulk or not matching:
                raise
            return self.bulk_json(group, filename)


def validate(original, updated, status):
    for field in ("ticker", "slug", "easy"):
        if updated[field] != original[field]:
            raise ValueError("Issuer or editorial content changed")
    if not status["latest"]:
        raise ValueError("No verified filing")
    for item in status["latest"]:
        if urlsplit(item["url"]).hostname not in ALLOWED or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",item["filed"]):
            raise ValueError("Incomplete filing reference")
    for section in ("annual", "interim"):
        for table in updated[section]:
            size = len(table["periods"])
            if not size or not table["rows"]:
                raise ValueError("Empty disclosure table")
            vectors = [row["values"] for row in table["rows"]]
            if table["total"] is not None:
                vectors.append(table["total"])
            if any(len(v) != size or any(x is not None and not math.isfinite(x) for x in v) for v in vectors):
                raise ValueError("Invalid filing amount or period")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", type=Path, default=Path("public/data/company-reports"))
    parser.add_argument("--only", nargs="+", help="Check only these tickers")
    parser.add_argument("--sec-bulk", action="store_true", help="Use official nightly bulk files if an individual SEC API is unavailable")
    args = parser.parse_args()
    checked_at = datetime.now(timezone.utc).date().isoformat()
    success = 0
    failed = []
    with ExitStack() as stack:
        reader = FilingReader(stack, args.sec_bulk)
        for path in sorted(args.reports.glob("*.json")):
            original = json.loads(path.read_bytes())
            ticker = original["ticker"]
            if args.only and ticker not in args.only:
                continue
            try:
                if ticker in ISSUERS:
                    provider = "DART"
                    updated, status = refresh_korea(original, reader.json, reader.bytes)
                else:
                    provider = "SEC"
                    cik = sec_cik(original)
                    if not cik:
                        raise ValueError("Missing SEC issuer identifier")
                    updated, status = refresh_sec(original, cik, reader.json, reader.bytes)
                validate(original, updated, status)
                updated["filingCheck"] = {"provider": provider, "checked": checked_at, "latest": status["latest"]}
                if updated != original:
                    tmp = path.with_suffix(".tmp")
                    tmp.write_text(json.dumps(updated, ensure_ascii=False, allow_nan=False, separators=(",", ":"))+"\n", encoding="utf-8")
                    tmp.replace(path)
                success += 1
                print(f"{ticker}: {provider} verified", *status.get("warnings", []), flush=True)
            except (OSError, ValueError, TypeError, KeyError, IndexError, RuntimeError, BadZipFile) as exc:
                failed.append(ticker)
                print(f"{ticker}: retained prior snapshot ({type(exc).__name__}: {exc})", flush=True)
    print(f"Verified {success} issuers. Retained prior snapshot for {len(failed)}: {', '.join(failed)}", flush=True)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
