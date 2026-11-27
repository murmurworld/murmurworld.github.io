import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

import refresh_holdings as funds


def held(ticker="AAPL", name="Apple", weight=100.0):
    return {"ticker": ticker, "name": name, "weight": weight}


def fixture(ticker, as_of="2026-10-31"):
    return {"ticker": ticker, "asOf": as_of, "source": "https://example.org/fund",
            "holdings": [held(weight=60), held("B", "B", 39.5)],
            "coverage": {"complete": True, "disclosedPositions": 3, "equityPositions": 2,
                         "sourceUrl": "https://example.org/data"}}


class IssuerSourceTests(unittest.TestCase):
    def test_vanguard_pagination_country_share_classes_and_tied_display_weights(self):
        def page(start, rows, more=False, date="2026-10-31"):
            stamp = date + "T00:00:00-04:00"
            data = {"size": 400, "asOfDate": stamp,
                    "fund": {"entity": [{"type": "portfolioHolding", "asOfDate": stamp, "longName": ticker,
                              "ticker": ticker, "cusip": f"00{slot:07}", "percentWeight": "0.25",
                              "marketValue": 402 - slot} for slot,ticker in rows]}}
            if more:
                data["next"] = {"href": "http://api.vanguard.com/rs/ire/01/ind/fund/VOO/portfolio-holding/stock?start=400&count=500"}
            return json.dumps(data).encode()

        ids = ["GOOGL", "GOOG", "BRK B"] + [f"ST{i}" for i in range(3, 400)]
        stock_rows = list(enumerate(ids))
        first, second = page(1, stock_rows[:-1], True), page(400, stock_rows[-1:])
        urls = []
        def fetch(url):
            urls.append(url)
            return [first, second][len(urls) - 1]
        got = funds.vanguard(fetch)
        self.assertEqual(urls[1], funds.VOO + "?start=400&count=500")
        self.assertEqual([r["ticker"] for r in got["holdings"][:3]], ["GOOGL", "GOOG", "BRK.B"])
        self.assertEqual(got["coverage"]["disclosedPositions"], 400)
        older = page(400, stock_rows[-1:], date="2026-09-30")
        with self.assertRaisesRegex(ValueError,"dates or totals"):
            funds.vanguard(lambda url: older if "?" in url else first)
        with self.assertRaisesRegex(ValueError,"duplicated VOO"):
            funds.vanguard(lambda url: page(400, stock_rows[:1]) if "?" in url else first)
        partial = json.loads(first)
        del partial["next"]
        with self.assertRaisesRegex(ValueError,"Incomplete"):
            funds.vanguard(lambda url: json.dumps(partial))

    def test_qqqm_counts_cash_but_ranks_only_equities_using_the_portfolio_business_day(self):
        def row(symbol, kind, weight):
            return {"ticker": symbol, "issuerName": symbol, "securityTypeCode": kind, "cusip": symbol,
                    "percentageOfTotalNetAssets": weight, "marketValueBase": 10}
        payload = {"cusip": "46138G649", "effectiveDate": "2026-11-26", "effectiveBusinessDate": "2026-11-25",
                   "totalNumberOfHoldings": 4,
                   "holdings": [row("USD","CURR",None),row("AAPL","COM",58),row("ASML","DRNY",40),
                                row("CME","IFUT",0.7)]}
        fetch = lambda url: json.dumps(payload)
        with patch.dict(funds.MINIMUM_EQUITIES, QQQM=2):
            result = funds.invesco(fetch)
            self.assertEqual(result["asOf"], "2026-11-25")
            self.assertEqual([h["ticker"] for h in result["holdings"]], ["AAPL","ASML"])
            self.assertEqual(result["coverage"]["disclosedPositions"],4)
            payload["totalNumberOfHoldings"] = 102
            with self.assertRaisesRegex(ValueError,"Incomplete"):
                funds.invesco(fetch)
            payload["totalNumberOfHoldings"] = 4
            payload["holdings"][0]["securityTypeCode"] = "unrecognized"
            with self.assertRaisesRegex(ValueError,"Unclassified"):
                funds.invesco(fetch)
            payload["cusip"] = "QQQ"
            with self.assertRaisesRegex(ValueError,"share class"):
                funds.invesco(fetch)

    def test_schwab_follows_exact_second_page_and_excludes_futures_and_cash(self):
        head = "".join(f"<th>{s}</th>" for s in ["Fund Name","CUSIP","Symbol","Quantity","% of Assets","Market Value"])
        def page(first,last,rows,day="11/25/26"):
            body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
            return (f"<h1>Schwab U.S. Dividend Equity ETF (SCHD)</h1><div>As of <b>{day}</b></div>"
                    f"<div>Displaying {first} - {last} of 77</div><table><tr>{head}</tr>{body}</table>"
                    "<a href='?page=1'>Next</a>").encode()
        rows = [["NAME",f"00{i:07}",f"ST{i}",1,"1.30%","$100.0"] for i in range(74)]
        rows.extend([["SCHWAB GOV MONEY", "912345670", "GVMXX",1,"3.00%","$3"],
                     ["S&P MID 400 EMINI DEC 26","ADI393HX1","FAZ6",12700,"0.00%","$0"],
                     ["DJIA MINI e-CBOT DEC 26","ADI396QN6","DMZ6",5090,"0.00%","$0"]])
        def get(url):
            return page(76,77,rows[75:]) if "?" in url else page(1,75,rows[:75])
        with patch.dict(funds.MINIMUM_EQUITIES, SCHD=70):
            result = funds.schwab(get)
            self.assertEqual(len(result["holdings"]),74)
            self.assertEqual(result["coverage"]["disclosedPositions"],77)
            with self.assertRaisesRegex(ValueError,"Inconsistent or incomplete"):
                funds.schwab(lambda u: page(76,77,rows[75:],"11/26/26") if "?" in u else get(u))
            with self.assertRaisesRegex(ValueError,"Incomplete SCHD page"):
                funds.schwab(lambda u: page(76,77,rows[75:-1]) if "?" in u else get(u))

    def test_rejects_partial_equity_weight_even_with_a_plausible_count(self):
        with patch.dict(funds.MINIMUM_EQUITIES, SCHD=2):
            with self.assertRaisesRegex(ValueError, "weights"):
                funds.complete_fund("SCHD","2026-11-25","a","a",200,[held(weight=5),held("B","B",4)])

    def test_invalid_redirects(self):
        for url in ["http://investor.vanguard.com/x","https://www.not-issuer.org/x",
                    "https://someone@investor.vanguard.com/x", "https://dng-api.invesco.com:9090/x"]:
            with self.assertRaises(ValueError):
                funds.safe_url(url)


class PublicationTests(unittest.TestCase):
    def test_partial_failure_previous_snapshot_older_data_and_idempotent_archives(self):
        with tempfile.TemporaryDirectory() as temp:
            dst = Path(temp) / "etf-holdings.json"
            base = [fixture(t) for t in funds.PROVIDERS]
            funds.write_json(dst,base)
            def denied(_):
                raise HTTPError(funds.SCHD,403,"Forbidden",{},None)
            get = {"VOO": lambda _: fixture("VOO", "2026-11-25"),
                   "QQQM": lambda _: fixture("QQQM","2026-10-28"),"SCHD":denied}
            summary = funds.refresh(dst,lambda _:None,date(2026,11,27),get)
            self.assertIn("updated",summary[0])
            self.assertIn("predates",summary[1])
            self.assertIn("403",summary[2])
            new = json.loads(dst.read_bytes())
            self.assertEqual(new[1:],base[1:])
            archives=dst.with_name("etf-holdings-history")
            self.assertEqual(sorted(p.name for p in (archives / "VOO").glob("*.json")), ["2026-10-31.json","2026-11-25.json"])
            mtime = dst.stat().st_mtime_ns
            summary = funds.refresh(dst,lambda _:None,date(2026,11,27),get)
            self.assertIn("verified",summary[0])
            self.assertEqual(mtime,dst.stat().st_mtime_ns)
            self.assertEqual(json.loads((archives / "VOO/2026-10-31.json").read_bytes()),base[0])
            get["VOO"] = lambda _: fixture("VOO","2026-12-01")
            self.assertIn("future",funds.refresh(dst,lambda _:None,date(2026,11,27),get)[0])

    def test_preserves_existing_rows_if_same_date_differs_and_refuses_unverified_seed(self):
        with tempfile.TemporaryDirectory() as temp:
            dst = Path(temp) / "etf-holdings.json"
            baseline = [fixture(t) for t in funds.PROVIDERS]
            funds.write_json(dst, baseline)
            altered = fixture("VOO"); altered["holdings"][0]["name"]="Changed"
            providers = {t: (lambda _, t=t: altered if t=="VOO" else fixture(t)) for t in funds.PROVIDERS}
            self.assertIn("revision requires review", funds.refresh(dst,None,date(2026,11,27),providers)[0])
            self.assertEqual(json.loads(dst.read_bytes()),baseline)
            baseline[2]["coverage"]["complete"] = False
            funds.write_json(dst,baseline)
            with self.assertRaisesRegex(ValueError,"Unverified"):
                funds.refresh(dst,None,date(2026,11,27),providers)


if __name__ == "__main__":
    unittest.main()
