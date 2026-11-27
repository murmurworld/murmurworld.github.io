"""Read a filing and its inline XBRL from the issuer's own, publicly linked filing archive."""

from collections import defaultdict
from copy import deepcopy
from datetime import datetime
from decimal import Decimal, InvalidOperation
from io import BytesIO
from pathlib import PurePosixPath
import re
from urllib.parse import urljoin, urlsplit
from zipfile import BadZipFile, ZipFile

from lxml import etree, html
from issuer_alphabet import segment_dimension
from public_company_sec import CURRENCIES, MEASURES, citation, fresh_tables, iso, segment_tables, windows

# Published financial-filing filters on each company's own investor relations site.
DIRECTORIES = {
    "INTC": "https://www.intc.com/filings-reports/all-sec-filings",
    "AMD": "https://ir.amd.com/financial-information/sec-filings",
    "WMT": "https://stock.walmart.com/sec-filings/all-sec-filings",
    "XOM": "https://investor.exxonmobil.com/sec-filings/all-sec-filings",
    "KO": "https://investors.coca-colacompany.com/filings-reports/all-sec-filings",
    "KLAC": "https://ir.kla.com/sec-filings/all-sec-filings",
    "BAC": "https://investor.bankofamerica.com/regulatory-and-other-filings/select-sec-filings",
    "VZ": "https://www.verizon.com/about/investors/feed/sec-filings",
}
ISSUER_HOSTS = {urlsplit(url).hostname for url in DIRECTORIES.values()} | {"app.quotemedia.com"}
XL = "{http://www.xbrl.org/2003/instance}"
IX = "{http://www.xbrl.org/2013/inlineXBRL}"
DIM = "{http://xbrl.org/2006/xbrldi}"
KEYS = {(k[0], k[1]): k for choices in MEASURES for k in choices}
ACC = re.compile(r"/(\d{10}-\d{2}-\d{6})/([^/]+\.htm[l]?)$", re.I)


def listing(page, base, form):
    host = urlsplit(base).hostname
    matches = []
    for row in html.fromstring(page).xpath("//tr[td]"):
        cells = row.xpath("./td")
        if len(cells) < 3 or cells[1].text_content().strip() != form:
            continue
        main = next((a for a in row.xpath(".//a[@href]") if ACC.search(urlsplit(a.get("href")).path)), None)
        if main is None:
            continue
        href = urljoin(base, main.get("href"))
        accession = ACC.search(urlsplit(href).path)
        if not accession or urlsplit(href).hostname != host:
            continue
        day_text = cells[0].text_content().strip()
        try:
            filed = datetime.strptime(day_text, "%m/%d/%y").date().isoformat()
        except ValueError:
            continue
        archive = next(
            (urljoin(base, a) for a in row.xpath(".//a/@href") if urlsplit(a).path.endswith("-xbrl.zip")),
            None,
        )
        if archive and urlsplit(archive).hostname == host and accession[1] in urlsplit(archive).path:
            matches.append((filed, accession[1], href, archive, accession[2]))
    if not matches:
        raise ValueError("Issuer filing directory has no verifiable " + form + " archive")
    return max(matches)


def scaled_value(fact):
    value = "".join(fact.itertext()).strip()
    fmt = fact.get("format", "").split(":")[-1]
    if fact.get("{http://www.w3.org/2001/XMLSchema-instance}nil") in {"1", "true"}:
        return None
    if fmt in {"fixed-zero", "zerodash", "numdash"}:
        return Decimal(0)
    if fmt not in {"", "num-dot-decimal", "numdotdecimal"}:
        return None
    if not re.fullmatch(r"(?:\d+|\d{1,3}(?:,\d{3})+)(?:\.\d+)?", value):
        return None
    try:
        scale = int(fact.get("scale", "0"))
        if abs(scale) > 15 or fact.get("sign", "") not in {"", "-"}:
            return None
        return Decimal(value.replace(",", "")).scaleb(scale) * (-1 if fact.get("sign") == "-" else 1)
    except (InvalidOperation, ValueError):
        return None


def concept(fact, extracted):
    if extracted:
        name = etree.QName(fact)
        return name.namespace or "", name.localname
    prefix, _, name = fact.get("name", "").partition(":")
    return fact.nsmap.get(prefix, ""), name


def standard_value(fact):
    if fact.get("{http://www.w3.org/2001/XMLSchema-instance}nil") in {"1", "true"}:
        return None
    text = (fact.text or "").strip()
    # Values in the extracted instance already include inline scale and sign.
    if not re.fullmatch(r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)", text):
        return None
    value = Decimal(text)
    return value if value.is_finite() else None


def read_instance(data, cik, form, currency):
    parser = etree.XMLParser(resolve_entities=False, load_dtd=False, no_network=True)
    try:
        doc = etree.fromstring(data, parser)
    except etree.XMLSyntaxError as error:
        raise ValueError("The filing has no readable XBRL document") from error
    if doc.getroottree().docinfo.internalDTD is not None:
        raise ValueError("Unexpected DTD in inline XBRL")
    extracted = doc.tag == XL + "xbrl"
    standard_facts = doc.findall("*[@contextRef]") if extracted else ()
    contexts = {}
    for ctx in doc.iter(XL + "context"):
        issuer = ctx.findtext(XL + "entity/" + XL + "identifier", "")
        if not issuer.isdigit() or int(issuer) != cik:
            continue
        start = iso(ctx.findtext(XL + "period/" + XL + "startDate"))
        end = iso(ctx.findtext(XL + "period/" + XL + "endDate"))
        members = list(ctx.iter(DIM + "explicitMember"))
        if (
            not start
            or not end
            or end < start
            or ctx.find(".//" + DIM + "typedMember") is not None
        ):
            continue
        axis = segment_dimension(members, cik)
        if members and not axis:
            continue
        if axis is None and (
            ctx.find(XL + "entity/" + XL + "segment") is not None or ctx.find(XL + "scenario") is not None
        ):
            continue
        contexts[ctx.get("id")] = ((start, end), axis)
    units = set()
    for unit in doc.iter(XL + "unit"):
        if len(unit) != 1 or unit[0].tag != XL + "measure":
            continue
        prefix, _, code = (unit[0].text or "").partition(":")
        if unit[0].nsmap.get(prefix) == "http://www.xbrl.org/2003/iso4217" and code == currency:
            units.add(unit.get("id"))
    dei = defaultdict(set)
    for fact in standard_facts if extracted else doc.iter(IX + "nonNumeric"):
        namespace, tag = concept(fact, extracted)
        if not re.fullmatch(r"https?://xbrl.sec.gov/dei/\d{4}(?:-\d{2}-\d{2})?", namespace):
            continue
        if fact.get("contextRef") not in contexts:
            continue
        value = " ".join("".join(fact.itertext()).split())
        if tag in {"DocumentType", "EntityCentralIndexKey"}:
            dei[tag].add(value)
        if tag == "DocumentPeriodEndDate":
            parsed = iso(value)
            for mask in ("%B %d, %Y", "%b %d, %Y", "%m/%d/%Y"):
                if parsed:
                    break
                try:
                    parsed = datetime.strptime(value, mask).date()
                except ValueError:
                    pass
            if parsed and parsed == contexts[fact.get("contextRef")][0][1]:
                dei[tag].add(parsed.isoformat())
    if (
        dei["DocumentType"] != {form}
        or len(dei["EntityCentralIndexKey"]) != 1
        or not all(v.isdigit() and int(v) == cik for v in dei["EntityCentralIndexKey"])
        or len(dei["DocumentPeriodEndDate"]) != 1
    ):
        raise ValueError("Issuer identity, financial form or reporting period does not match")
    simple = defaultdict(lambda: defaultdict(set))
    dimensional = defaultdict(lambda: defaultdict(set))
    for fact in standard_facts if extracted else doc.iter(IX + "nonFraction"):
        ctx = contexts.get(fact.get("contextRef"))
        if not ctx or fact.get("unitRef") not in units:
            continue
        ns, tag = concept(fact, extracted)
        taxonomy = (
            "us-gaap"
            if re.fullmatch(r"https?://(?:fasb.org|xbrl.us)/us-gaap/[^/]+", ns)
            else (
                "ifrs-full"
                if ns.startswith("https://xbrl.ifrs.org/taxonomy/") and ns.endswith("/ifrs-full")
                else ""
            )
        )
        key = KEYS.get((taxonomy, tag))
        if not key:
            continue
        val = standard_value(fact) if extracted else scaled_value(fact)
        if val is None:
            continue
        span, axis = ctx
        if axis:
            dimensional[(taxonomy, tag, axis[0], span)][axis[1]].add(val)
        else:
            simple[key][span].add(val)
    observations = {
        k: {p: next(iter(v)) for p, v in periods.items() if len(v) == 1} for k, periods in simple.items()
    }
    return next(iter(dei["DocumentPeriodEndDate"])), observations, dimensional


def issuer_tables(report, cik, section, form, filed, accession, permalink, raw):
    """Parse one source-verified annual or interim XBRL filing from any supported issuer."""
    if not iso(filed) or (accession and not re.fullmatch(r"\d{10}-\d{2}-\d{6}", accession)):
        raise ValueError("Invalid filing date or accession")
    currency = report[section][0]["currency"]
    if currency not in CURRENCIES:
        raise ValueError("Issuer currency unidentified")
    expected_cik = 34088 if report["ticker"] == "XOM" and filed < "2026-07-01" else cik
    end, obs, dim = read_instance(raw, expected_cik, form, currency)
    filing = {
        "label": form,
        "base": form,
        "periodEnd": end,
        "filed": filed,
        "url": permalink,
        "acc": accession,
    }
    if end > filed:
        raise ValueError("Report period ends after submission")
    original = report[section]
    last = max((p.get("end") or "" for t in original for p in t["periods"]), default="")
    # A lagging investor site cannot certify a later period or a newer same-period amendment.
    if end < last or any(
        t["source"].get("periodEnd") == end and (t["source"].get("filed") or "") > filed for t in original
    ):
        raise ValueError("Issuer filing directory lags the published report")
    spans = windows(obs, filing)
    fresh = segment_tables(report, filing, currency, spans, obs, dim) + fresh_tables(
        obs, filing, currency, spans
    )
    if not fresh:
        raise ValueError("No verified financial observations in issuer XBRL")
    ids = {t["id"] for t in fresh}
    return {**citation(filing), "kind": section}, fresh + [t for t in original if t["id"] not in ids]


def verizon_filing(base, page, form, fetch):
    # The issuer links to an XBRL document index for each of its two latest periodic reports.
    rows = [
        r
        for r in html.fromstring(page).xpath("//tr[td]")
        if "Latest " + form in [c.text_content().strip() for c in r.xpath("./td|./th")]
    ]
    if len(rows) != 1:
        raise ValueError("No unique latest Verizon " + form)
    row = rows[0]
    filed = datetime.strptime(row.xpath("./th|./td")[0].text_content().strip(), "%m/%d/%Y").date().isoformat()
    urls = [
        urljoin(base, a.get("href")) for a in row.xpath(".//a[@href]") if a.text_content().strip() == "XBRL"
    ]
    if len(urls) != 1 or urlsplit(urls[0]).hostname != "www.verizon.com":
        raise ValueError("No issuer-linked XBRL filing index")
    links = [
        a.get("href")
        for a in html.fromstring(fetch(urls[0])).xpath('//*[@id="xbrl_documents"]//a[@href]')
        if re.fullmatch(r"vz-\d{8}\.htm", a.text_content().strip())
    ]
    if len(links) != 1 or urlsplit(links[0]).hostname != "app.quotemedia.com":
        raise ValueError("The issuer did not link a primary filing")
    wrapper = etree.fromstring(
        fetch(links[0]), etree.XMLParser(load_dtd=False, resolve_entities=False, no_network=True)
    )
    document = wrapper.findtext("filing/document[@type='HTML']")
    if (
        wrapper.tag != "xbrl_filing"
        or not document
        or wrapper.findtext("filing_info/form") != form
        or wrapper.findtext("filing_info/date_filed") != filed.replace("-", "")
    ):
        raise ValueError("Filed date, form or primary document missing from download")
    return filed, "", urls[0], document.encode("utf-8")


def eqs_filing(base, form, fetch):
    filed, acc, url, zipurl, document = listing(fetch(base + "?form_type=" + form), base, form)
    with ZipFile(BytesIO(fetch(zipurl))) as archive:
        info = archive.getinfo(PurePosixPath(document).name)
        if info.file_size > 50_000_000:
            raise ValueError("Issuer report exceeds size limit")
        return filed, acc, url, archive.read(info)


def refresh_issuer(report, cik, fetch):
    base = DIRECTORIES[report["ticker"]]
    packet = deepcopy(report)
    latest, warnings = [], []
    verizon = fetch(base) if report["ticker"] == "VZ" else None
    for section, form in (("annual", "10-K"), ("interim", "10-Q")):
        try:
            filed, acc, url, raw = (
                verizon_filing(base, verizon, form, fetch) if verizon else eqs_filing(base, form, fetch)
            )
            item, packet[section] = issuer_tables(report, cik, section, form, filed, acc, url, raw)
            latest.append(item)
        except (OSError, ValueError, KeyError, BadZipFile, etree.Error) as exc:
            warnings.append(section + "-unavailable (" + str(exc) + ")")
    if not latest:
        raise ValueError("; ".join(warnings))
    return packet, {"latest": latest, "warnings": warnings}
