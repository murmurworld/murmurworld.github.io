"""Read issuer filings from EDGAR and OpenDART for Murmurworld's monthly publication."""

import argparse
import json
import math
import os
import re
import shutil
import ssl
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
from issuer_filings import DIRECTORIES, ISSUER_HOSTS, refresh_issuer
from issuer_international import INTERNATIONAL_HOSTS, INTERNATIONAL_TICKERS, refresh_international
from issuer_native import NATIVE_HOSTS, NATIVE_TICKERS, refresh_native
from issuer_q4 import DIRECTORIES as Q4_DIRECTORIES, HOSTS as Q4_HOSTS, refresh_q4
from issuer_berkshire import HOST as BERKSHIRE_HOST, refresh_berkshire
from issuer_additional import ADDITIONAL_HOSTS, ADDITIONAL_TICKERS, refresh_additional
from issuer_technology import TECHNOLOGY_HOSTS, TECHNOLOGY_TICKERS, refresh_technology
from issuer_novo import HOST as NOVO_HOST, refresh_novo
from issuer_shell import HOST as SHELL_HOST, refresh_shell
from issuer_electronics import ELECTRONICS_HOSTS, ELECTRONICS_TICKERS, refresh_electronics
from issuer_mining import MINING_HOSTS, MINING_TICKERS, refresh_mining
from issuer_unitedhealth import HOST as UNITEDHEALTH_HOST, refresh_unitedhealth

ALLOWED = (
    {"www.sec.gov", "data.sec.gov", "dart.fss.or.kr", "opendart.fss.or.kr", BERKSHIRE_HOST, NOVO_HOST, SHELL_HOST}
    | ISSUER_HOSTS
    | Q4_HOSTS
    | NATIVE_HOSTS
    | INTERNATIONAL_HOSTS
    | ADDITIONAL_HOSTS
    | TECHNOLOGY_HOSTS
    | ELECTRONICS_HOSTS
    | MINING_HOSTS
    | {UNITEDHEALTH_HOST}
)
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
        self.denied_groups = set()
        self.last_request = 0
        self.last_ti_request = 0
        self.context = ssl.create_default_context()
        # Some Windows installations lack public roots shipped in common Linux bundles.
        try:
            import certifi
        except ImportError:
            pass
        else:
            self.context.load_verify_locations(cafile=certifi.where())

    def open(self, url):
        parts = urlsplit(url)
        if parts.scheme != "https" or parts.hostname not in ALLOWED:
            raise ValueError("Unexpected filing data host")
        ready = self.last_request + 0.35
        if parts.hostname == "www.ti.com":
            ready = max(ready, self.last_ti_request + 1)  # TI's public crawl delay is one second.
        time.sleep(max(0, ready - time.monotonic()))
        self.last_request = time.monotonic()
        if parts.hostname == "www.ti.com":
            self.last_ti_request = self.last_request
        agent = "Murmurworld financial filings (https://github.com/murmurworld/murmurworld.github.io)"
        contact = os.environ.get("SEC_CONTACT_EMAIL", "")
        if parts.hostname in {"www.sec.gov", "data.sec.gov"} and re.fullmatch(
            r"[^\s@<>]+@[^\s@<>]+\.[A-Za-z]{2,}", contact
        ):
            agent = "Murmurworld financial filings " + contact
        req = Request(url, headers={"Accept-Encoding": "identity"})
        # A redirected request should never forward the site's private contact address.
        req.add_unredirected_header("User-Agent", agent)
        return urlopen(req, timeout=45, context=self.context)

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
                time.sleep(
                    min(
                        30,
                        (
                            int(exc.headers.get("Retry-After", 3))
                            if str(exc.headers.get("Retry-After", "")).isdigit()
                            else 3
                        ),
                    )
                )

    def bulk_json(self, group, name):
        if group not in self.archives:
            self.archives[group] = None
            path = self.temp / (group + ".zip")
            print("Using official SEC bulk distribution for " + group, flush=True)
            with self.open(SEC_BULK[group]) as response, path.open("wb") as out:
                shutil.copyfileobj(response, out, length=1024 * 1024)
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
        matching = urlsplit(url).hostname == "data.sec.gov" and re.fullmatch(r"CIK\d{10}\.json", filename)
        if self.bulk and matching and self.archives.get(group):
            return self.bulk_json(group, filename)
        if matching and group in self.denied_groups:
            if self.bulk:
                return self.bulk_json(group, filename)
            raise OSError("SEC " + group + " API declined access during this run")
        try:
            return json.loads(self.bytes(url))
        except (OSError, ValueError) as exc:
            if matching and isinstance(exc, HTTPError) and exc.code == 403:
                self.denied_groups.add(group)
                print(
                    "SEC "
                    + group
                    + " declined this runner (HTTP 403); similar requests paused for this run.",
                    flush=True,
                )
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
        dated = item.get("filed") or item.get("published") or item.get("authorized") or item.get("datasetAsOf") or ""
        if urlsplit(item["url"]).hostname not in ALLOWED or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", dated):
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


def issuer_fallback(ticker):
    for directory, read in (
        (DIRECTORIES, refresh_issuer),
        (Q4_DIRECTORIES, refresh_q4),
        (NATIVE_TICKERS, refresh_native),
        (INTERNATIONAL_TICKERS, refresh_international),
        ({"BRK.B"}, refresh_berkshire),
        (ADDITIONAL_TICKERS, refresh_additional),
        (TECHNOLOGY_TICKERS, refresh_technology),
        ({"NVO"}, refresh_novo),
        ({"SHEL"}, refresh_shell),
        (ELECTRONICS_TICKERS, refresh_electronics),
        (MINING_TICKERS, refresh_mining),
        ({"UNH"}, refresh_unitedhealth),
    ):
        if ticker in directory:
            return read
    return None


def source_provider(sources):
    channels = {"openapi.twse.com.tw": "TWSE", "www.prnewswire.com": "Issuer release"}
    providers = {channels.get(urlsplit(s["url"]).hostname, "Issuer IR") for s in sources}
    return " + ".join(sorted(providers)) or "Issuer IR"


def supplement_sec(packet, status, read, cik, fetch):
    """Use genuine issuer statements if EDGAR could verify the index but not the figures."""
    if not read:
        return packet, status, "SEC"
    missing = status.get("warnings", [])
    latest = {item["kind"]: item for item in status["latest"]}
    if not (missing or (packet["ticker"] in INTERNATIONAL_TICKERS | MINING_TICKERS | {"NVO", "SHEL"} and "foreign-report" in latest)):
        return packet, status, "SEC"
    try:
        candidate, checked = read(packet, cik, fetch)
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, BadZipFile):
        return packet, {**status, "warnings": [*missing, "issuer-statement-unavailable"]}, "SEC"
    accepted = set()
    segments = set()
    sources = []
    combined = {**packet}
    for source in checked["latest"]:
        section = source["kind"]
        if section not in {"annual", "interim"}:
            continue
        dated = source.get("filed") or source.get("published") or source.get("authorized") or source.get("datasetAsOf") or ""
        regulator = latest.get(section, {})
        period, required = source.get("periodEnd", ""), regulator.get("periodEnd") or ""
        if not period or period < required:
            continue
        if period == required and regulator.get("label", "").endswith("/A") and dated < regulator["filed"]:
            continue
        verified = [t for t in candidate[section] if t["source"]["url"] == source["url"]]
        if not verified:
            continue
        combined[section] = candidate[section]
        accepted.add(section)
        if any(t["measure"] != "financial-results" for t in verified):
            segments.add(section)
        if source["url"] != regulator.get("url"):
            sources.append(source)
    if not accepted:
        return packet, status, "SEC"
    required = {key for key in latest if key in {"annual", "interim"}}
    warnings = []
    for reason in missing:
        section = reason.split("-", 1)[0]
        recovered = section in (segments if "segment" in reason else accepted)
        if reason == "companyfacts-unavailable":
            recovered = bool(required) and required <= accepted
        if not recovered:
            warnings.append(reason)
    warnings.extend(checked.get("warnings", []))
    return combined, {"latest": [*status["latest"], *sources], "warnings": warnings}, "SEC + " + source_provider(sources)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reports", type=Path, default=Path("public/data/company-reports"))
    parser.add_argument("--only", nargs="+", help="Check only these tickers")
    parser.add_argument(
        "--sec-bulk",
        action="store_true",
        help="Use official nightly bulk files if an individual SEC API is unavailable",
    )
    args = parser.parse_args()
    checked_at = datetime.now(timezone.utc).date().isoformat()
    counts = {}
    failed = []
    unavailable_by_provider = {}
    warnings = []
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
                    fallback = issuer_fallback(ticker)
                    try:
                        updated, status = refresh_sec(original, cik, reader.json, reader.bytes)
                    except (OSError, BadZipFile):
                        if not fallback:
                            raise
                        provider = "SEC + Issuer IR"
                        updated, status = fallback(original, cik, reader.bytes)
                        provider = source_provider(status["latest"])
                    else:
                        updated, status, provider = supplement_sec(
                            updated, status, fallback, cik, reader.bytes
                        )
                validate(original, updated, status)
                updated = {
                    **updated,
                    "filingCheck": {"provider": provider, "checked": checked_at, "latest": status["latest"]},
                }
                if status.get("warnings"):
                    updated["filingCheck"]["warnings"] = [w.split(" (", 1)[0] for w in status["warnings"]]
                updated.pop("filingAttempt", None)
                counts[provider] = counts.get(provider, 0) + 1
                if status.get("warnings"):
                    warnings.append(ticker + " (" + provider + "): " + ", ".join(status["warnings"]))
                print(f"{ticker}: {provider} verified", *status.get("warnings", []), flush=True)
            except (OSError, ValueError, TypeError, KeyError, IndexError, RuntimeError, BadZipFile) as exc:
                failed.append(ticker)
                unavailable_by_provider.setdefault(provider, []).append(ticker)
                updated = {**original, "filingAttempt": {"date": checked_at, "status": "unavailable"}}
                print(
                    f"{ticker}: {provider} unavailable, retained prior snapshot ({type(exc).__name__}: {exc})",
                    flush=True,
                )
            if updated != original:
                tmp = path.with_suffix(".tmp")
                tmp.write_text(
                    json.dumps(updated, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n",
                    encoding="utf-8",
                    newline="\n",
                )
                tmp.replace(path)
    summary = " · ".join(f"{provider}: {n}" for provider, n in counts.items()) or "0 verified"
    print(
        f"Verified {sum(counts.values())} issuers ({summary}). Retained prior snapshot for {len(failed)}: {', '.join(failed)}",
        flush=True,
    )
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf8") as stream:
            print("### Monthly issuer filing checks\n\n" + checked_at + " · " + summary + "\n", file=stream)
            print(f"Unavailable: {len(failed)}\n", file=stream)
            for provider, tickers in unavailable_by_provider.items():
                print(f"- {provider} ({len(tickers)}): " + ", ".join(tickers), file=stream)
            if warnings:
                print(
                    "Latest filings verified with partial table coverage:\n\n"
                    + "\n".join("- " + w for w in warnings),
                    file=stream,
                )
    if failed and os.environ.get("GITHUB_ACTIONS"):
        annotation = "notice" if counts else "warning"
        print(
            f"::{annotation}::{len(failed)} issuer checks unavailable. Their previously verified data is retained.",
            flush=True,
        )
    # Preserve the date of a real, unsuccessful attempt even during a full provider outage.
    # A missing directory / unmatched --only is a configuration failure and has no data to publish.
    return 0 if counts or failed else 1


if __name__ == "__main__":
    sys.exit(main())
