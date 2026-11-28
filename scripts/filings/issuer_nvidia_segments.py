"""Read separately published NVIDIA geography, market-platform and reportable-segment PDFs."""
import re
from datetime import date, datetime
from decimal import Decimal as D, ROUND_HALF_UP
from io import BytesIO
from urllib.parse import urljoin, urlsplit

from lxml import html
from pypdf import PdfReader
from issuer_native import financial_table

INDEX = "https://investor.nvidia.com/financial-info/financial-reports/"
CDN = "s201.q4cdn.com"
CDN_ROOT = "https://" + CDN + "/141608511/files/doc_financials/"
# These exact documents are published by NVIDIA. Only use them for this reporting
# period if the issuer's JS-enabled filing directory has no links in the response.
VERIFIED = {(2027, 3): {
    "geography": CDN_ROOT + "2027/Q327/Supplemental-Financial-Information-NVDA-2027-Q3.pdf",
    "markets": CDN_ROOT + "2027/Q327/Rev-by-Mkt-Qtrly-Trend-Q327.pdf",
    "segments": CDN_ROOT + "2027/Q327/Q3FY27-CFO-Commentary.pdf",
}}
NUMBER = r"(?:\d+|\d{1,3}(?:,\d{3})+)"
COUNTRIES = {
    "United States": ("us","미국","United States"),
    "Taiwan": ("taiwan","대만","Taiwan"),
    "China (including Hong Kong)": ("china","중국(홍콩 포함)","China (including Hong Kong)"),
    "Singapore": ("singapore","싱가포르","Singapore"),
    "Other": ("other","기타","Other"),
}
MARKETS = {
    "Data Center": ("datacenter","데이터센터","Data Center"),
    "Hyperscale": ("hyperscale","하이퍼스케일","Hyperscale"),
    "AI Clouds, Industrial, & Enterprise": ("acie","AI 클라우드·산업·기업","AI Clouds, Industrial & Enterprise"),
    "Edge Computing": ("edge","엣지 컴퓨팅","Edge Computing"),
}
SEGMENTS = {
    "Compute & Networking": ("compute","컴퓨팅·네트워킹","Compute & Networking"),
    "Graphics": ("graphics","그래픽","Graphics"),
}


def nvidia_disclosure_links(raw_listing, fiscal_year, q):
    """Only accept the indicated issuer, tenant directory, quarter and document type."""
    result = {}
    quarter = f"q{q}{str(fiscal_year)[-2:]}"
    for anchor in html.fromstring(raw_listing or "<html/>").xpath("//a[@href]"):
        url = urljoin(INDEX, anchor.get("href")).split("#",1)[0]
        p = urlsplit(url)
        path = p.path.lower()
        if p.scheme != "https" or p.query:
            continue
        if p.netloc == CDN and not path.startswith("/141608511/files/doc_financials/"):
            continue
        if p.netloc not in {CDN, "investor.nvidia.com"} or not path.endswith(".pdf"):
            continue
        if not re.search(rf"/{fiscal_year}/{quarter}/",path):
            continue
        title = (path.rsplit("/",1)[-1]+" "+" ".join(anchor.itertext())).lower()
        kind = None
        if "supplemental" in title and "financial" in title:
            kind = "geography"
        elif "commentary" in title and "cfo" in title:
            kind = "segments"
        elif ("trend" in title and ("revenue" in title or "mkt" in title)):
            kind = "markets"
        if kind:
            if kind in result and urlsplit(result[kind]).path.rsplit("/",1)[-1] != p.path.rsplit("/",1)[-1]:
                raise ValueError("Ambiguous NVIDIA quarterly document")
            result[kind]=url
    return {**VERIFIED.get((fiscal_year,q),{}), **result}


def _statement(kind, title, source, periods, labels, values, total, components, notes):
    table=financial_table("nvidia-"+kind, title, periods, source,
                          [(spec, values[name]) for name,spec in labels.items() if name in values])
    table.update(measure="revenue", total=total, compositionKeys=components,
                 compositionPeriods=[p["label"] for p in periods],notes=[notes[0]],notesEn=[notes[1]])
    return table


def _values(row, name, n):
    match=re.fullmatch(re.escape(name)+r"\s+(.+)",row)
    if not match:
        raise ValueError("Unexpected NVIDIA revenue row: "+name)
    tokens=match[1].replace("$","").split()
    if len(tokens)!=n or not all(re.fullmatch(NUMBER,t) for t in tokens):
        raise ValueError("Unexpected number or unit in NVIDIA table")
    return [int(v.replace(",","")) for v in tokens]


def _require_totals(rows,total):
    if [sum(v) for v in zip(*rows)]!=total:
        raise ValueError("NVIDIA revenue breakdown does not reconcile")


def _geography(lines, source, scopes, year, q):
    if "NVIDIA Corporation" not in lines or "Supplemental Financial Information" not in lines:
        raise ValueError("Unexpected NVIDIA supplemental statement")
    day=date.fromisoformat(source["periodEnd"])
    if "For the Quarter Ended "+day.strftime("%B")+f" {day.day}, {day.year}" not in lines:
        raise ValueError("Fiscal end date does not match NVIDIA supplement")
    label="Geographic Revenue based upon Customer"
    i=lines.index(label)
    if lines[i+1]!="Headquarters Location:" or lines[i-1]!="(In millions)":
        raise ValueError("Geographic classification or units changed")
    order=["quarter"] + (["ytd"] if q in (2,3) else ["annual"] if q==4 else [])
    dates=[]
    for scope in order:
        periods,_=scopes[scope]
        dates.extend(date.fromisoformat(p["end"]) for p in reversed(periods))
    collabels=re.findall(r"[A-Z][a-z]{2,8} \d{1,2}, 20\d{2}",lines[i-2])
    if [datetime.strptime(t[:3]+t[t.index(" "):],"%b %d, %Y").date() for t in collabels]!=dates:
        raise ValueError("Geographic year or column order changed")
    expect="Three Months Ended"+{1:"",2:" Six Months Ended",3:" Nine Months Ended",4:" Year Ended"}[q]
    if lines[i-3]!=expect:
        raise ValueError("Geographic table duration changed")
    found={}
    for line in lines[i+2:]:
        if line.startswith("Total revenue "):
            published=_values(line,"Total revenue",len(dates))
            break
        label=next((x for x in COUNTRIES if line.startswith(x+" ")),None)
        if not label or label in found:
            raise ValueError("Unrecognized or duplicate geography")
        found[label]=_values(line,label,len(dates))
    else:
        raise ValueError("Missing geographic revenue total")
    if len(found)<2:
        raise ValueError("Missing NVIDIA country breakdown")
    _require_totals(found.values(),published)
    result={}
    for i,scope in enumerate(order):
        periods,total=scopes[scope]
        pair=lambda vals:[vals[2*i+1],vals[2*i]]
        if pair(published)!=total:
            raise ValueError("Geography differs from consolidated results")
        result[scope]=[_statement("hq-"+scope,("직접 고객 본사 소재지별 매출","Revenue by direct customer headquarters"),
            source,periods,COUNTRIES,{k:pair(v) for k,v in found.items()},total,[COUNTRIES[k][0] for k in found],
            ("직접 제품을 구매한 고객의 본사 소재지로 나눈 매출입니다. 배송지나 최종 사용 국가와 다를 수 있습니다.",
             "Revenue follows the headquarters of NVIDIA’s direct customer. The shipping destination and end customer can be elsewhere."))]
    return result


def _markets(lines, source, scopes, year, q):
    if "NVIDIA QUARTERLY REVENUE" not in lines or "REVENUE BY MARKET PLATFORM" not in lines:
        raise ValueError("Unexpected NVIDIA market trend statement")
    i=next((j for j,s in enumerate(lines) if s.startswith("($ in millions) Q1 ")),None)
    if i is None:raise ValueError("Missing market platform units and quarters")
    years=[int(y) for y in re.findall(r"Fiscal (20\d{2})",lines[i-1])]
    if not years or years!=list(range(years[0],year+1)):
        raise ValueError("Unrecognized fiscal year labels")
    columns=[(y,n) for y in years for n in range(1,(q if y==year else 4)+1)]
    if lines[i]!="($ in millions) "+" ".join(f"Q{n}" for _,n in columns):
        raise ValueError("Unexpected market trend quarter order")
    joined=" ".join(lines[i+1:])
    # The second half of the ACIE label wraps around the row of numeric cells in the PDF.
    joined=joined.replace("Industrial, & Enterprise","Industrial, &")
    names=list(MARKETS)
    pattern=("Data Center (.+?) Hyperscale (.+?) AI Clouds, Industrial, & (.+?) (?:Enterprise )?Edge Computing "
             "(.+?) TOTAL (.+?)(?: Note:|$)")
    match=re.match(pattern,joined)
    if not match:raise ValueError("NVIDIA market classification changed")
    series={name:_values(name+" "+cells,name,len(columns)) for name,cells in zip([*names,"TOTAL"],match.groups())}
    _require_totals([series[names[0]],series[names[3]]],series["TOTAL"])
    _require_totals([series[names[1]],series[names[2]]],series[names[0]])
    # Market-platform disclosures have quarterly columns. Rounded quarters need not sum to GAAP YTD.
    periods,total = scopes['quarter']
    indexes = [columns.index((y,q)) for y in (year-1,year)]
    values = {name:[row[i] for i in indexes] for name,row in series.items()}
    if values['TOTAL'] != total:
        raise ValueError('NVIDIA market trend disagrees with GAAP quarter revenue')
    table = _statement('markets-quarter',('시장별 매출','Revenue by market platform'),source,periods,MARKETS,
                       values,total,['datacenter','edge'],
                       ('시장별 수치는 회사가 발표한 분기 금액입니다. 하이퍼스케일과 AI 클라우드·산업·기업은 데이터센터의 하위 항목입니다.',
                        'NVIDIA reports these figures by quarter. Hyperscale and AI Clouds, Industrial & Enterprise make up Data Center.'))
    for row in table['rows']:
        if row['key'] in ('hyperscale','acie'):
            row.update(parent='datacenter',level=1)
    return {'quarter':[table]}


def _segments(lines, source, scopes, year, q):
    name="Revenue by Reportable Segments"
    i=lines.index(name)
    ordinal=("","First","Second","Third","Fourth")[q]
    if f"CFO Commentary on {ordinal} Quarter Fiscal {year} Results" not in lines:
        raise ValueError("Unexpected NVIDIA CFO reporting period")
    previous=(q-1,year) if q>1 else (4,year-1)
    prior_q, prior_year=previous
    if lines[i+1]!=f"($ in billions) Q{q} FY{year%100:02d} Q{prior_q} FY{prior_year%100:02d} Q{q} FY{(year-1)%100:02d} Q/Q* Y/Y*":
        raise ValueError("Segment statement units or quarter order changed")
    values={}
    for offset,k in enumerate([*SEGMENTS,"Total"],2):
        pattern=re.escape(k)+r"\s+\$?([\d,.]+) \$?([\d,.]+) \$?([\d,.]+) .+"
        match=re.fullmatch(pattern,lines[i+offset])
        if not match:raise ValueError("Missing CFO reportable segment")
        values[k]=[D(match[j].replace(",","")) for j in (3,1)]
    periods,exact=scopes["quarter"]
    rounded=[(D(v)/1000).quantize(D("0.1"),rounding=ROUND_HALF_UP) for v in exact]
    if values["Total"]!=rounded or any(abs(a+b-t)>D("0.1") for a,b,t in zip(*values.values())):
        raise ValueError("Reported precision or segment sum disagrees with consolidated revenue")
    table=_statement("segments-quarter",("공시 사업부문별 매출","Revenue by reportable segment"),source,periods,SEGMENTS,
        {k:[float(d) for d in v] for k,v in values.items()},[float(d) for d in rounded],["compute","graphics"],
        ("회사가 십억 달러 단위로 소수 첫째 자리까지 반올림해 발표한 분기 값입니다. 사업부문과 판매 시장은 서로 다른 분류입니다.",
         "NVIDIA reports this quarterly breakdown to the nearest $0.1 billion. Operating segments and market platforms are separate classifications."))
    table.update(unitKo="십억 달러",unitEn="USD billion")
    return {"quarter":[table]}


READERS={"geography":(_geography,"엔비디아 보충 재무자료","NVIDIA supplemental financial information"),
         "markets":(_markets,"엔비디아 시장별 매출 추이","NVIDIA quarterly revenue trend"),
         "segments":(_segments,"엔비디아 CFO 실적 설명","NVIDIA CFO commentary")}


def nvidia_dimension_tables(data, kind, url, release_source, scopes, fiscal_year, q):
    reader,ko,en=READERS[kind]
    doc=PdfReader(BytesIO(data))
    if not 1<=len(doc.pages)<=40:raise ValueError("Unexpected NVIDIA PDF length")
    lines=[" ".join(line.split()) for page in doc.pages for line in page.extract_text(extraction_mode="layout").splitlines() if line.strip()]
    source={**release_source,"url":url,"label":ko,"labelEn":en}
    return reader(lines,source,scopes,fiscal_year,q)
