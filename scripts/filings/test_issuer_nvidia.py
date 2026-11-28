import unittest
from datetime import date
from unittest.mock import patch

from issuer_nvidia import (
    INDEX,
    IR,
    NEWS,
    METRICS,
    ORDINAL,
    archive,
    check_regulatory_revenue,
    read_income,
    refresh_nvidia,
    report_tables,
)


def url(q, fy):
    return f"{NEWS}/news/nvidia-announces-financial-results-for-{ORDINAL[q].lower()}-quarter-{'and-' if q==4 else ''}fiscal-{fy}"


def make_release(q, fy, ends, published):
    dates = ends * (2 if q != 1 else 1)
    labels = ["Three Months Ended"] + (
        [{2: "Six Months Ended", 3: "Nine Months Ended", 4: "Twelve Months Ended"}[q]] if q != 1 else []
    )
    values = [
        [100, 20, 80, 10, 5, 15, 65, 70, 10, 60],
        [90, 25, 65, 9, 5, 14, 51, 53, 7, 46],
        [300, 80, 220, 30, 12, 42, 178, 185, 30, 155],
        [265, 65, 200, 27, 10, 37, 163, 170, 22, 148],
    ]
    rows = [
        ["NVIDIA CORPORATION"],
        ["CONDENSED CONSOLIDATED STATEMENTS OF INCOME"],
        ["(In millions, except per share data)"],
        ["(Unaudited)"],
        labels,
        [d.strftime("%B") + " " + str(d.day) + "," for d in dates],
        [str(d.year) for d in dates],
    ]
    rows += [[name] + [str(p[i]) for p in values[: len(dates)]] for i, name in enumerate(METRICS)]

    def tr(items):
        return "<tr>" + "".join("<td>" + x + "</td>" for x in items) + "</tr>"

    title = f"NVIDIA Announces Financial Results for {ORDINAL[q]} Quarter {'and ' if q==4 else ''}Fiscal {fy}"
    return (
        f'<h1>{title}</h1><div class="article-date">{published}</div><table>'
        + "".join(map(tr, rows))
        + "</table>"
    )


class NvidiaReleases(unittest.TestCase):
    q3 = make_release(3, 2027, [date(2026, 10, 25), date(2025, 10, 26)], "November 17, 2026")
    q2 = make_release(2, 2027, [date(2026, 7, 26), date(2025, 7, 27)], "August 26, 2026")
    annual = make_release(4, 2026, [date(2026, 1, 25), date(2025, 1, 26)], "February 25, 2026")

    def test_report_dates_derive_from_actual_prior_quarter_and_prior_fiscal_year(self):
        release = read_income(self.q3, 2027, 3, url(3, 2027))
        previous = read_income(self.q2, 2027, 2, url(2, 2027))
        annual = read_income(self.annual, 2026, 4, url(4, 2026))
        scopes, tables = report_tables(release, previous[1], annual[1], 3)
        self.assertEqual(scopes["quarter"][0][1]["start"], "2026-07-27")
        self.assertEqual(scopes["ytd"][0][1]["start"], "2026-01-26")
        self.assertEqual(scopes["ytd"][1], [265, 300])
        self.assertEqual(tables["quarter"]["rows"][0]["values"], [90, 100])
        self.assertEqual(release[0]["published"], "2026-11-17")
        self.assertNotIn("filed", release[0])

    def test_prevent_rounded_non_gaap_or_inconsistent_figures(self):
        for source in (
            self.q3.replace("STATEMENTS OF INCOME", "NON-GAAP RESULTS"),
            self.q3.replace("100</td>", "101</td>"),
            self.q3.replace("Nine Months", "Six Months"),
            self.q3.replace("November 17, 2026", "October 12, 2026"),
        ):
            with self.subTest(source=source[:55]), self.assertRaises(ValueError):
                read_income(source, 2027, 3, url(3, 2027))

    def test_first_and_fourth_quarters_preserve_official_fiscal_boundaries(self):
        first = make_release(1, 2027, [date(2026, 4, 26), date(2025, 4, 27)], "May 20, 2026")
        q1 = read_income(first, 2027, 1, url(1, 2027))
        q4 = read_income(self.annual, 2026, 4, url(4, 2026))
        scopes, _ = report_tables(q1, q4[1], q4[1], 1)
        self.assertEqual(set(scopes), {"quarter"})
        self.assertEqual(scopes["quarter"][0][1]["start"], "2026-01-26")
        annual_scopes, _ = report_tables(
            q4, [date(2024, 10, 27), date(2025, 10, 26)], [date(2024, 1, 28), date(2025, 1, 26)], 4
        )
        self.assertEqual(annual_scopes["quarter"][0][1]["start"], "2025-10-27")
        self.assertEqual(annual_scopes["annual"][0][1]["start"], "2025-01-27")

    def test_only_official_archive_entries_and_public_pagination(self):
        release = url(3, 2027)
        pg = INDEX + "&page=2"
        raw = f'<a href="{release}">Q3</a><a href="https://other.example{release[ len(NEWS): ]}">Mirror</a><a href="{pg}">Next</a>'
        entries, more = archive(raw, INDEX)
        self.assertEqual(entries, {(2027, 3): release})
        self.assertEqual(more, pg)

    def test_current_amended_regulatory_figure_is_not_overridden(self):
        periods = [{"start": "2026-07-27", "end": "2026-10-25"}]
        data = {
            "source": {"filed": "2026-11-25"},
            "measure": "financial-results",
            "periods": periods,
            "rows": [{"key": "us-gaap:Revenues", "values": [88]}],
        }
        with self.assertRaises(ValueError):
            check_regulatory_revenue({"interim": [data]}, {"quarter": (periods, [90])})

    def test_issuer_refresh_keeps_audited_year_and_prior_filing(self):
        links = [url(3, 2027), url(2, 2027), url(4, 2026)]
        fixtures = {
            INDEX: "".join(f'<a href="{u}">Earnings</a>' for u in links),
            IR: b"<html></html>",
            links[0]: self.q3,
            links[1]: self.q2,
            links[2]: self.annual,
        }
        base = {
            "ticker": "NVDA",
            "annual": [{"id": "audited-original"}],
            "interim": [
                {
                    "id": "sec-consolidated-quarter",
                    "source": {"filed": "2026-08-26", "periodEnd": "2026-07-26"},
                    "periods": [{"start": "2026-04-27", "end": "2026-07-26"}],
                }
            ],
        }
        with patch("issuer_nvidia_segments.nvidia_disclosure_links", return_value={}):
            result, status = refresh_nvidia(base, 1045810, fixtures.__getitem__)
        self.assertEqual(result["annual"], base["annual"])
        self.assertEqual(len(base["interim"]), 1)
        self.assertEqual(
            [t["id"] for t in result["interim"]],
            ["nvidia-gaap-quarter", "nvidia-gaap-ytd", "sec-consolidated-quarter"],
        )
        self.assertEqual(status["latest"][0]["kind"], "interim")
        self.assertEqual(len(status["warnings"]), 3)
