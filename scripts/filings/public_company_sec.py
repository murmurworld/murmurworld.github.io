"""Refresh published company packets using SEC submissions, companyfacts and filed XBRL.

The caller supplies an identified, rate-limited HTTP client. No API key or private
research files are used. Public reference: https://www.sec.gov/edgar/sec-api-documentation
"""
from collections import defaultdict
from copy import deepcopy
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import PurePosixPath
from urllib.parse import quote, urlsplit
from xml.etree import ElementTree
import re
from issuer_alphabet import alphabet_tables, segment_dimension


SEC = "https://data.sec.gov"
ARCHIVE = "https://www.sec.gov/Archives/edgar/data"
ANNUAL = {"10-K", "20-F", "40-F"}
INTERIM = {"10-Q"}
XL = "{http://www.xbrl.org/2003/instance}"
DIM = "{http://xbrl.org/2006/xbrldi}"
# Each choice has its own label; contract revenue can differ from total revenue.
REVENUES = [
    ("us-gaap", "Revenues", "매출", "Revenue"),
    ("us-gaap", "SalesRevenueNet", "순매출", "Net sales"),
    ("us-gaap", "RevenueFromContractWithCustomerExcludingAssessedTax",
     "고객 계약 매출(거래세 제외)", "Revenue from customer contracts, excluding assessed tax"),
    ("us-gaap", "RevenueFromContractWithCustomerIncludingAssessedTax",
     "고객 계약 매출(거래세 포함)", "Revenue from customer contracts, including assessed tax"),
    ("ifrs-full", "Revenue", "매출", "Revenue"),
]
MEASURES = [
    REVENUES,
    [("us-gaap","OperatingIncomeLoss","영업이익·손실","Operating income or loss"),
     ("ifrs-full","ProfitLossFromOperatingActivities","영업이익·손실","Operating profit or loss")],
    [("us-gaap","InterestIncomeExpenseNet","순이자수익","Net interest income")],
    [("us-gaap","NoninterestIncome","비이자수익","Noninterest income")],
    [("us-gaap","NetIncomeLoss","지배주주 귀속 순이익·손실","Profit or loss attributable to the parent"),
     ("ifrs-full","ProfitLossAttributableToOwnersOfParent","지배주주 귀속 순이익·손실","Profit or loss attributable to owners of the parent"),
     ("us-gaap","ProfitLoss","연결 순이익·손실","Consolidated profit or loss"),
     ("ifrs-full","ProfitLoss","연결 순이익·손실","Consolidated profit or loss")],
]
IX_AXIS = {"segments": {"StatementBusinessSegmentsAxis", "OperatingSegmentsAxis", "SegmentsAxis"},
           "products": {"ProductOrServiceAxis", "ProductsAndServicesAxis", "ProductAxis"}}
CURRENCIES = {"USD":"미 달러", "EUR":"유로", "CNY":"위안", "JPY":"엔", "TWD":"대만 달러",
              "DKK":"덴마크 크로네", "AUD":"호주 달러", "GBP":"영국 파운드", "KRW":"원"}


def sec_cik(report):
    if report["ticker"] == "XOM":
        # July 1, 2026 successor registrant. Earlier annual reports belong to CIK 34088.
        # https://www.sec.gov/Archives/edgar/data/2115436/000119312526291990/d71068d8k12b.htm
        return 2115436
    if report["ticker"] == "RIO":
        # Joint annual filing of Rio Tinto plc and Rio Tinto Ltd; RIO ADR is the plc.
        return 863064
    keys = set()
    for table in report["annual"] + report["interim"]:
        url = urlsplit(table["source"]["url"])
        match = re.match(r"/Archives/edgar/data/(\d+)/",url.path,re.I)
        if url.hostname in {"www.sec.gov","sec.gov"} and match:
            keys.add(int(match.group(1)))
    if len(keys)>1:
        raise ValueError("Ambiguous SEC issuer identifiers")
    return next(iter(keys),None)


def iso(value):
    try:
        return date.fromisoformat(value)
    except (ValueError,TypeError):
        return None


def recent_filings(submissions,cik):
    if int(submissions["cik"])!=cik:
        raise ValueError("SEC submissions issuer mismatch")
    recent=submissions["filings"]["recent"]
    filings=[]
    for form,period,filed,accession,doc in zip(*(recent[k] for k in
            ("form","reportDate","filingDate","accessionNumber","primaryDocument")),strict=True):
        base=form.removesuffix("/A")
        if base not in ANNUAL|INTERIM|{"6-K"} or not iso(filed):
            continue
        if not re.fullmatch(r"\d{10}-\d{2}-\d{6}",accession):
            continue
        if not doc or PurePosixPath(doc).name!=doc or not re.fullmatch(r"[A-Za-z0-9_.-]+",doc):
            continue
        if not iso(period) and base!="6-K":
            continue
        url=f"{ARCHIVE}/{cik}/{accession.replace('-','')}/{quote(doc)}"
        filings.append({"label":form,"periodEnd":period if iso(period) else None,"filed":filed,
                        "url":url,"acc":accession,"base":base})
    def newest(forms, by_filed=False, ordinary_only=False):
        found=[f for f in filings if f["base"] in forms]
        if ordinary_only:
            found=[f for f in found if f["label"]==f["base"]]
        return max(found,key=lambda f:(f["filed"],f["acc"]) if by_filed else (f["periodEnd"],f["filed"],f["acc"]),default=None)
    # Nonfinancial /A filings (director details and exhibits) frequently have no
    # tagged financial statements. Keep their original filing as a numeric fallback.
    annual=newest(ANNUAL,ordinary_only=True)
    quarter=newest(INTERIM,ordinary_only=True)
    foreign=newest({"6-K"},True) if annual and annual["base"] in {"20-F","40-F"} else None
    amendments={}
    for section,original,forms in (("annual",annual,ANNUAL),("interim",quarter,INTERIM)):
        latest=newest(forms)
        if original and latest["label"].endswith("/A") and latest["periodEnd"]==original["periodEnd"]:
            amendments[section]=latest
    return annual,quarter,foreign,amendments


def citation(filing):
    return {k:filing[k] for k in ("label","url","filed","periodEnd")}


def usable_observations(facts,filing,currency):
    """Read only one accession and exact ISO currency; conflicting same-period facts are omitted."""
    found={}
    for choices in MEASURES:
        for taxonomy,tag,ko,en in choices:
            result=defaultdict(set)
            entries=facts.get(taxonomy,{}).get(tag,{}).get("units",{}).get(currency,[])
            for item in entries:
                if item.get("accn")!=filing["acc"] or item.get("form")!=filing["label"]:
                    continue
                start,end=iso(item.get("start")),iso(item.get("end"))
                value=item.get("val")
                if start and end and end>=start and isinstance(value,(int,float)):
                    numeric=Decimal(str(value))
                    if numeric.is_finite():
                        result[(start,end)].add(numeric)
            unique={p:next(iter(values)) for p,values in result.items() if len(values)==1}
            if unique:
                found[(taxonomy,tag,ko,en)]=unique
    return found


def windows(observations,filing):
    end=iso(filing["periodEnd"])
    spans=set().union(*(set(obs) for obs in observations.values()))
    duration=lambda p:(p[1]-p[0]).days+1
    if filing["base"] in ANNUAL:
        bands=[("annual",330,385)]
    else:
        bands=[("quarter",74,111),("half",166,201),("nine-months",250,293)]
    result=[]
    for frequency,low,high in bands:
        matches=[p for p in spans if p[1]==end and low<=duration(p)<=high]
        if len(matches)!=1:
            continue
        current=matches[0]
        periods=[]
        for delta in ([2,1] if frequency=="annual" else [1]):
            # No stitching data from other accessions or mixing short transition years.
            prior=[p for p in spans if abs((end-p[1]).days-delta*365.25)<=8
                   and abs(duration(p)-duration(current))<=8]
            if len(prior)==1:
                periods.append(prior[0])
        result.append((frequency,periods+[current]))
    return result


def table_base(id,ko,en,filing,currency,periods):
    dates=[{"start":a.isoformat(),"end":b.isoformat(),"label":b.isoformat(),"labelEn":b.isoformat()} for a,b in periods]
    return {"id":id,"titleKo":ko,"titleEn":en,"currency":currency,
            "unitKo":f"백만 {CURRENCIES[currency]}","unitEn":currency+" million",
            "periods":dates,"rows":[],"measure":"financial-results","total":None,
            "notes":[],"notesEn":[],"marks":[],"compositionKeys":[],"compositionPeriods":[],
            "comparableFrom":dates[0]["label"],"source":citation(filing)}


def amount(value):
    if value is None:
        return None
    value=value / Decimal(1_000_000)
    return int(value) if value==value.to_integral_value() else float(value)


def fresh_tables(observations,filing,currency,spans):
    ends={"annual":("연간","Annual"),"quarter":("분기","Quarter"),
          "half":("6개월 누계","Six months"),"nine-months":("9개월 누계","Nine months")}
    outputs=[]
    for freq,periods in spans:
        ko,en=ends[freq]
        table=table_base("sec-consolidated-"+freq,"SEC 연결 실적 · "+ko,"SEC consolidated results · "+en,filing,currency,periods)
        for choices in MEASURES:
            for key in choices:
                data=observations.get(key,{})
                if periods[-1] not in data:
                    continue
                taxonomy,tag,ko,en=key
                table["rows"].append({"key":taxonomy+":"+tag,"ko":ko,"en":en,"kind":"leaf","level":0,"parent":None,
                                      "values":[amount(data.get(p)) for p in periods]})
                break
        if table["rows"]:
            outputs.append(table)
    return outputs


def segment_observations(xml,cik,currency):
    """Public dimensional instance. Reject compound dimensions, derived units and other co-filers."""
    if not xml or len(xml)>64_000_000 or b"<!DOCTYPE" in xml or b"<!ENTITY" in xml:
        raise ValueError("Invalid XBRL instance")
    doc=ElementTree.fromstring(xml)
    if doc.tag!=XL+"xbrl":
        raise ValueError("Not an extracted XBRL instance")
    units={u.get("id") for u in doc.findall(XL+"unit") if len(u)==1 and u[0].tag==XL+"measure"
           and (u[0].text or "").split(":")[-1]==currency}
    contexts={}
    for ctx in doc.findall(XL+"context"):
        entity=ctx.findtext(XL+"entity/"+XL+"identifier","")
        if not entity.isdigit() or int(entity)!=cik:
            continue
        members=ctx.findall(".//"+DIM+"explicitMember")
        dimension = segment_dimension(members, cik)
        if not dimension or ctx.find(".//"+DIM+"typedMember") is not None:
            continue
        a,b=iso(ctx.findtext(XL+"period/"+XL+"startDate")),iso(ctx.findtext(XL+"period/"+XL+"endDate"))
        if a and b:
            contexts[ctx.get("id")]=((a,b), *dimension)
    data=defaultdict(lambda:defaultdict(set))
    for fact in doc:
        where=contexts.get(fact.get("contextRef"))
        if not where or fact.get("unitRef") not in units or fact.text is None:
            continue
        uri,_,name=fact.tag.removeprefix("{").partition("}")
        taxonomy="us-gaap" if re.fullmatch(r"https?://(?:fasb.org|xbrl.us)/us-gaap/[^/]+",uri) else "ifrs-full" if "xbrl.ifrs.org/taxonomy/" in uri and uri.endswith("/ifrs-full") else ""
        if not any((taxonomy,name)==k[:2] for k in REVENUES):
            continue
        try:
            value=Decimal(fact.text.strip())
        except InvalidOperation:
            continue
        if value.is_finite():
            span,axis,member=where
            data[(taxonomy,name,axis,span)][member].add(value)
    return data


def segment_tables(report,filing,currency,spans,consolidated,dimensional):
    """Publish comparable known business/product slices only if every column ties to its filing total."""
    if report["ticker"] == "GOOGL":
        detailed = alphabet_tables(report, filing, currency, spans, consolidated, dimensional, amount, table_base)
        if detailed:
            return detailed
    results=[]
    for category,axes in IX_AXIS.items():
        reference=next((t for t in report["annual"] if t["id"]==category and t["measure"]=="revenue"),None)
        if not reference:
            continue
        labels={r["key"]:r for r in reference["rows"] if not r["level"] and r["key"].endswith("Member") and not r.get("legacy")}
        if len(labels)<2:
            continue
        for freq,periods in spans:
            for concept in REVENUES:
                total=consolidated.get(concept,{})
                if not all(p in total and total[p]>0 for p in periods):
                    continue
                for axis in sorted(axes):
                    slices=[dimensional.get((*concept[:2],axis,p),{}) for p in periods]
                    if not slices:
                        continue
                    members=set(slices[-1])
                    if len(members)<2 or not members<=labels.keys() or any(set(s)!=members for s in slices):
                        continue
                    if any(len(v)!=1 or min(v)<0 for s in slices for v in s.values()):
                        continue
                    values=[{key:next(iter(v)) for key,v in s.items()} for s in slices]
                    # A subset, hierarchy, amendment with changed members, or unexplained difference isn't a full mix.
                    if any(sum(column.values())!=total[p] for column,p in zip(values,periods)):
                        continue
                    categoryKo,categoryEn=("사업부문별","Business segments") if category=="segments" else ("제품·서비스별","Products and services")
                    periodKo,periodEn={"quarter":("분기","quarter"),"half":("6개월","six months"),"nine-months":("9개월","nine months"),"annual":("연간","annual")}[freq]
                    table=table_base("sec-"+category+"-"+freq,categoryKo+" 매출 · "+periodKo,categoryEn+" revenue · "+periodEn,filing,currency,periods)
                    for key,r in labels.items():
                        if key in members:
                            table["rows"].append({"key":key,"ko":r["ko"],"en":r["en"],"kind":"leaf","level":0,"parent":None,
                                                  "values":[amount(s[key]) for s in values]})
                    table.update(measure="revenue",total=[amount(total[p]) for p in periods],
                                 compositionKeys=[r["key"] for r in table["rows"]],compositionPeriods=[p["label"] for p in table["periods"]])
                    results.append(table)
                    break
                else:
                    continue
                break
    return results


def refresh_sec(report,cik,fetch_json,fetch_filing=None):
    cik=int(cik)
    subs=fetch_json(f"{SEC}/submissions/CIK{cik:010d}.json")
    symbols={s.upper().replace(".","-") for s in subs.get("tickers",[]) if isinstance(s,str)}
    if symbols and report["ticker"].upper().replace(".","-") not in symbols:
        raise ValueError("SEC ticker does not match the report issuer")
    annual,quarter,foreign,amendments=recent_filings(subs,cik)
    if not annual and not quarter and not foreign:
        raise ValueError("No identifiable SEC filing in recent submissions")
    packet=deepcopy(report)
    status={"latest":[],"warnings":[]}
    if foreign:
        status["latest"].append({**citation(foreign),"kind":"foreign-report"})
    pending=[]
    for section,filing in (("annual",annual),("interim",quarter or foreign)):
        if not filing:
            continue
        if filing is not foreign:
            status["latest"].append({**citation(amendments.get(section,filing)),"kind":section})
        stages=[filing]+([amendments[section]] if section in amendments else [])
        # Only advance verified tables. A newer 6-K can simply be an AGM notice.
        if not filing["periodEnd"]:
            continue
        regular=packet[section]
        last=max((p.get("end") or "" for t in regular for p in t["periods"]),default="")
        for stage in stages:
            existing=[t for t in regular if t["id"].startswith("sec-") and t["source"]["url"]==stage["url"]]
            original=[t for t in regular if not t["id"].startswith("sec-") and t["source"]["url"]==stage["url"]
                      and t["source"].get("filed")==stage["filed"]]
            same_newer=any(t["id"].startswith("sec-") and t["source"].get("periodEnd")==stage["periodEnd"]
                           and (t["source"].get("filed") or "")>stage["filed"] for t in regular)
            if stage["periodEnd"]<last or same_newer or (original and stage["periodEnd"]==last):
                continue
            segment_candidate=fetch_filing and any(t["id"] in IX_AXIS and any(r["key"].endswith("Member") for r in t["rows"]) for t in report["annual"])
            if existing and (not segment_candidate or any(t["id"].startswith(("sec-segments-","sec-products-")) for t in existing)):
                continue
            pending.append((section,stage))
    if not pending:
        return packet,status
    try:
        facts=fetch_json(f"{SEC}/api/xbrl/companyfacts/CIK{cik:010d}.json")
    except (OSError,ValueError,RuntimeError):
        status["warnings"].append("companyfacts-unavailable")
        return packet,status
    if int(facts["cik"])!=cik:
        raise ValueError("SEC companyfacts issuer mismatch")
    for section,filing in pending:
        currency=packet[section][0].get("currency")
        if currency not in CURRENCIES:
            status["warnings"].append(section+"-currency-unconfirmed")
            continue
        observations=usable_observations(facts["facts"],filing,currency)
        spans=windows(observations,filing)
        tables=fresh_tables(observations,filing,currency,spans)
        if not tables:
            status["warnings"].append(section+"-figures-unconfirmed")
            continue
        if fetch_filing and any(t["id"] in IX_AXIS and any(r["key"].endswith("Member") for r in t["rows"]) for t in report["annual"]):
            try:
                url=filing["url"].rsplit(".",1)
                instance=url[0]+"_"+url[1]+".xml"
                dimens=segment_observations(fetch_filing(instance),cik,currency)
                tables=segment_tables(report,filing,currency,spans,observations,dimens)+tables
            except (OSError,ValueError,RuntimeError,ElementTree.ParseError):
                status["warnings"].append(section+"-segment-source-unavailable")
        # Each supplemental view has its own dated citation. Retain reviewed historical tables.
        ids={t["id"] for t in tables}
        packet[section]=tables+[t for t in packet[section] if t["id"] not in ids]
    return packet,status
