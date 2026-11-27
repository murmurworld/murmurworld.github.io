from datetime import date
from unittest import TestCase, main

from issuer_native import microsoft_listing, microsoft_statement, ti_listing, ti_statement


URL="https://www.ti.com/en-us/about-ti/newsroom/news-releases/2026/2026-01-27-ti-reports-q4-2025-and-2025-financial-results-and-shareholder-returns"
ENTRY=(2025,4,date(2026,1,27),URL)


def table(rows):
    return "<table><tbody>"+"".join("<tr>"+"".join("<td>"+s+"</td>" for s in r)+"</tr>" for r in rows)+"</tbody></table>"


def fixture():
    income=[
        ["TEXAS INSTRUMENTS INCORPORATED AND SUBSIDIARIES"],
        ["Consolidated Statements of Income","For Three Months Ended December 31,","For Years Ended December 31,"],
        ["(In millions, except per-share amounts)","2025","2024","2025","2024"],
        ["Revenue","100","90","420","410"],["Gross profit","20","15","80","70"],
        ["Operating profit","5","4","18","17"],["Net income","(1)","3","16","14"],
    ]
    def segments(period,values):
        return table([["(In millions)",*period,"Change"]]+
                     [r for name,pair in zip(["Analog:","Embedded Processing:","Other:"],values)
                      for r in [[name],["Revenue",*pair,"1 %"]]])
    return ('<html><head><meta property="article:published_time" content="2026-01-27"/></head>'
            '<h1>TI reports Q4 2025 and 2025 financial results and shareholder returns</h1>'+
            table(income)+segments(["Q4 2025","Q4 2024"],[["70","60"],["20","20"],["10","10"]])+
            segments(["2025","2024"],[["350","340"],["50","50"],["20","20"]])+"</html>").encode()


class NativeDisclosuresTest(TestCase):
    def test_trusts_only_public_issuer_release_links(self):
        xml=f"<urlset><url><loc>{URL}</loc></url><url><loc>{URL.replace('www.ti.com','example.com')}</loc></url></urlset>"
        self.assertEqual(ti_listing(xml.encode()),[ENTRY])

    def test_fourth_quarter_is_separate_from_full_year(self):
        annual,at=ti_statement(fixture(),ENTRY,"annual")
        interim,it=ti_statement(fixture(),ENTRY,"interim")
        self.assertEqual(at[0]["total"],[410,420])
        self.assertEqual(it[0]["total"],[90,100])
        self.assertEqual(it[1]["rows"][-1]["values"],[3,-1])
        self.assertEqual(it[1]["periods"][-1]["start"],"2025-10-01")
        for source in [annual,interim]:
            self.assertEqual(source["published"],"2026-01-27")
            self.assertNotIn("filed",source)

    def test_disagreed_totals_are_not_published(self):
        with self.assertRaisesRegex(ValueError,"reconcile"):
            ti_statement(fixture().replace(b"<td>350</td>",b"<td>351</td>"),ENTRY,"annual")

    def test_rejects_conflicting_publication_date_or_units(self):
        for old,new in [(b'content="2026-01-27"',b'content="2026-01-26"'),
                        (b"(In millions, except per-share amounts)",b"(In thousands)")]:
            with self.assertRaises(ValueError):
                ti_statement(fixture().replace(old,new),ENTRY,"annual")


class MicrosoftDisclosuresTest(TestCase):
    url = "https://www.microsoft.com/en-us/investor/earnings/fy-2026-q4/press-release-webcast"

    def release(self):
        header = [["Three Months Ended June 30,","Twelve Months Ended June 30,"], ["2026","2025","2026","2025"]]
        income = [["Total revenue","12","10","430","380"], ["Gross margin","8","6","220","205"],
                  ["Operating income","4","3","100","80"], ["Net income","3","2","90","70"]]
        segments = [["First"],["Revenue","$5","$4","$160","$150"],
                    ["Second"],["Revenue","7","6","270","230"],
                    ["Total"],["Revenue","12","10","430","380"]]
        def statement(caption, rows):
            return table(header+rows).replace("<table>","<table><caption>"+caption+"</caption>")
        prefix = ("<html><head><title>FY26 Q4 - Press Releases - Investor Relations - Microsoft</title></head>"
                  "<body><p>REDMOND, Wash. - July 29, 2026 - Microsoft Corp. today announced the following results "
                  "for the quarter ended June 30, 2026, as compared to the corresponding period of last fiscal year:</p>")
        return (prefix+statement("MICROSOFT CORPORATION INCOME STATEMENTS (In millions, except per share amounts) (Unaudited)", income)+
                statement("SEGMENT RESULTS (In millions) (Unaudited)",segments)+"</body></html>").encode()

    def test_featured_quarter_discovers_the_last_completed_fiscal_year(self):
        current=self.url.replace("2026-q4","2027-q1")
        index=f'<a href="{current}">Press release</a><a href="{current.replace("www.microsoft.com","example.org")}">other</a>'
        listing=microsoft_listing(index.encode())
        self.assertEqual(listing["interim"],(2027,1,current))
        self.assertEqual(listing["annual"][:2],(2026,4))
        self.assertEqual(listing["annual"][2].lower(),self.url)

    def test_annual_uses_july_start_without_confusing_q4(self):
        entry=(2026,4,self.url)
        source, annual=microsoft_statement(self.release(),entry,"annual")
        _, quarterly=microsoft_statement(self.release(),entry,"interim")
        self.assertEqual((source["published"],source["periodEnd"]),("2026-07-29","2026-06-30"))
        self.assertNotIn("filed",source)
        self.assertEqual(annual[0]["periods"][-1]["start"],"2025-07-01")
        self.assertEqual(quarterly[0]["periods"][-1]["start"],"2026-04-01")
        self.assertEqual(annual[0]["total"],[380,430])
        self.assertEqual(quarterly[0]["total"],[10,12])

    def test_bad_unit_comparative_or_reconciliation_does_not_overwrite_saved_results(self):
        for before,after in [(b"millions",b"thousands"),(b"ended June 30, 2026",b"ended June 29, 2026"),
                             (b"<td>270</td>",b"<td>271</td>"),(b"<td>2025</td>",b"<td>2024</td>")]:
            data=self.release().replace(before,after)
            with self.assertRaises(ValueError):
                microsoft_statement(data,(2026,4,self.url),"annual")

    def test_older_markup_and_nine_months_are_read_independently(self):
        released=self.release().replace(b"FY26 Q4",b"FY26 Q3").replace(b"June 30",b"March 31")
        released=released.replace(b"July 29",b"April 29").replace(b"Twelve Months",b"Nine Months")
        for cap, lines in [
            (b"MICROSOFT CORPORATION INCOME STATEMENTS (In millions, except per share amounts) (Unaudited)",
             [b"MICROSOFT CORPORATION",b"INCOME STATEMENTS",b"(In millions, except per share amounts) (Unaudited)"]),
            (b"SEGMENT RESULTS (In millions) (Unaudited)", [b"SEGMENT RESULTS",b"(In millions) (Unaudited)"]),
        ]:
            released=released.replace(b"<caption>"+cap+b"</caption><tbody>",
                b"<tbody>"+b"".join(b"<tr><td>"+line+b"</td></tr>" for line in lines))
        _,tables=microsoft_statement(released,(2026,3,self.url.replace("q4","q3")),"interim")
        by_id={table["id"]:table for table in tables}
        self.assertEqual(by_id["msft-segments-interim"]["total"],[10,12])
        self.assertEqual(by_id["msft-segments-ytd"]["total"],[380,430])
        self.assertEqual(by_id["msft-segments-ytd"]["periods"][-1]["start"],"2025-07-01")


if __name__=="__main__":
    main()
