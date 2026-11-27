"""Read a Korean issuer's published annual and interim statements from OpenDART's public viewer."""
from calendar import monthrange
from copy import deepcopy
from datetime import date
import re
from urllib.parse import parse_qs, urlencode, urlsplit

from lxml import html


ISSUERS = {
    "005930": ("00126380", "삼성전자"), "000660": ("00164779", "SK하이닉스"),
    "105560": ("00688996", "KB금융"), "055550": ("00382199", "신한지주"),
}
LIST = "https://opendart.fss.or.kr/disclosureinfo/fnltt/singl/list.do"
FSS = "https://dart.fss.or.kr"
FORMS = {3: ("11013", "분기보고서", "Quarterly report"), 6: ("11012", "반기보고서", "Half-year report"),
         9: ("11014", "분기보고서", "Quarterly report"), 12: ("11011", "사업보고서", "Annual report")}
METRICS = {
    "revenue": ("매출액", "Revenue", ("매출액", "수익(매출액)")),
    "interest": ("순이자이익", "Net interest income", ("순이자이익", "순이자손익")),
    "fees": ("순수수료이익", "Net fee and commission income", ("순수수료이익", "순수수료손익")),
    "operating": ("영업이익", "Operating profit", ("영업이익", "영업이익(손실)")),
    "net": ("연결순이익", "Consolidated net income", ("당기순이익", "반기순이익", "분기순이익",
            "당기순이익(손실)", "반기순이익(손실)", "분기순이익(손실)", "연결당기순이익", "연결분기순이익", "연결반기순이익")),
}
SEGMENTS = {
    "DX부문": ("DX 부문", "Device eXperience"), "DS부문": ("DS 부문", "Device Solutions"),
    "SDC": ("삼성디스플레이", "Samsung Display"), "Harman": ("하만", "Harman"),
    "TV,모니터등": ("TV·모니터 등", "TVs, monitors and related products"),
    "스마트폰등": ("스마트폰 등", "Smartphones and related products"), "메모리": ("메모리", "Memory"),
    "디스플레이패널": ("디스플레이 패널", "Display panels"),
    "은행부문": ("은행", "Banking"), "은행부문/기업금융": ("은행 · 기업금융", "Banking – corporate"),
    "은행부문/가계금융": ("은행 · 가계금융", "Banking – retail"), "은행부문/기타": ("은행 · 기타", "Banking – other"),
    "신용카드부문": ("신용카드", "Credit cards"), "증권부문": ("증권", "Securities"),
    "보험부문": ("보험", "Insurance"), "손해보험부문": ("손해보험", "Non-life insurance"),
    "생명보험부문": ("생명보험", "Life insurance"), "여신전문부문": ("여신전문", "Specialized credit finance"),
    "기타부문": ("기타 부문", "Other segments"),
}


def document(content):
    return html.fromstring(content.decode("utf-8-sig") if isinstance(content, bytes) else content)


def compact(text):
    return re.sub(r"\s+", "", text)


def read_number(text):
    raw = compact(text)
    if raw in {"", "-", "－"}:
        return None
    if not re.fullmatch(r"-?[\d,]+|\([\d,]+\)", raw):
        raise ValueError(f"Unrecognized monetary value: {text[:35]}")
    return int(raw.replace(",", "").replace("(", "-").replace(")", ""))


def make_row(key, ko, en, values, kind="leaf"):
    return dict(key=key, ko=ko, en=en, values=values, level=0, parent=None, kind=kind)


def make_table(key, title, source, periods, rows):
    return {"id":"dart-"+key,"titleKo":title[0],"titleEn":title[1],"currency":"KRW","unitKo":"백만원",
            "unitEn":"KRW million","measure":"financial-results","periods":periods,"rows":rows,"total":None,
            "notes":[],"notesEn":[],"marks":[],"compositionKeys":[],"compositionPeriods":[],
            "comparableFrom":periods[0]["label"],"source":source}


def lookup(issuer, year, month, fetch):
    form, label, label_en = FORMS[month]
    corp, name = ISSUERS[issuer]
    args = dict(textCrpCik=corp,textCrpNm=name,selectYear=year,reportCode=form,selectToc=0)
    result = document(fetch(LIST+"?"+urlencode(args)))
    frames = result.xpath("//iframe/@src")
    if not frames:
        # This is a successful form query without a matching filing, e.g. before the filing deadline.
        if not any(s in compact(result.text_content()) for s in ("없습니다","없어요","조회결과가없","검색결과가없")):
            raise ValueError("OpenDART statement index returned no recognizable result")
        return None
    url = urlsplit(frames[0])
    args = parse_qs(url.query)
    rec = args.get("rcpNo",[""])[0]
    if (url.hostname!="dart.fss.or.kr" or url.path.lstrip("/")!="report/viewer.do" or
            not re.fullmatch(r"\d{14}",rec)):
        raise ValueError("Unexpected OpenDART statement URL")
    main_url = FSS+"/dsaf001/main.do?rcpNo="+rec
    raw = fetch(main_url)
    body = raw.decode("utf-8-sig") if isinstance(raw,bytes) else raw
    title = document(body).xpath("string(//title)").strip()
    pattern = re.escape(name)+r"/(?:\[[^\]]+\])?"+label+r"/(\d{4})\.(\d\d)\.(\d\d)"
    match = re.fullmatch(pattern, compact(title))
    if not match:
        raise ValueError("DART issuer, filing type or filing date mismatch: "+title)
    end = date(year,month,monthrange(year,month)[1]).isoformat()
    src=dict(label=label,labelEn=label_en,url=main_url,filed="-".join(match.groups()),periodEnd=end)
    return src, document(fetch(FSS+"/report/viewer.do?"+url.query)), body


def dates(meta):
    ranges=re.findall(r"(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})\s*부터\s*(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})\s*까지",meta)
    return [(date(*map(int,r[:3])), date(*map(int,r[3:]))) for r in ranges]


def periods_for(ranges,quarter=False):
    periods=[]
    for start,end in reversed(ranges):
        if quarter:
            start=date(end.year,end.month-2,1)
        span=end.month-start.month+1
        periods.append(dict(label=f"{end.isoformat()} 종료 {span}개월",labelEn=f"{span} months to {end.isoformat()}",
                            start=start.isoformat(),end=end.isoformat()))
    return periods


def normalize_label(txt):
    txt=re.sub(r"^(?:[Ⅰ-Ⅹ]+\.|[IVX]+\.|\(\d+\))","",compact(txt))
    return re.sub(r"\(주(?:석)?[\d,~ㆍ.및-]+\)$","",txt)


def consolidated(body,source):
    tables=body.xpath("//table")
    for i,meta in enumerate(tables[:-1]):
        heading=compact(meta.text_content())
        if not heading.startswith(("연결손익계산서","연결포괄손익계산서")) or "(단위:백만원)" not in heading:
            continue
        ranges=dates(meta.text_content())
        if len(ranges)<2 or ranges[0][1].isoformat()!=source["periodEnd"]:
            continue
        table=tables[i+1]
        labels=[compact(th.text_content()) for th in table.xpath("./thead/tr[last()]/*[self::th or self::td]") if compact(th.text_content())]
        pairs=labels==["3개월","누적"]*len(ranges)
        amount_count=len(ranges)*(2 if pairs else 1)
        data={}
        for tr in table.xpath("./tbody/tr"):
            cells=[td.text_content() for td in tr.xpath("./td")]
            if len(cells)!=amount_count+1: continue
            tag=normalize_label(cells[0])
            for k,(_,_,aliases) in METRICS.items():
                if tag in aliases and k not in data:
                    values=[read_number(value) for value in cells[1:]]
                    if any(v is not None for v in values): data[k]=values
        if "operating" not in data or "net" not in data or not ({"revenue","interest"} & data.keys()): continue
        annual=ranges[0][1].month==12
        if not pairs and not annual and ranges[0][1].month>3 and len(labels)!=len(ranges):
            raise ValueError("Unknown interim comparison layout")
        results=[]
        for quarter in ([False,True] if pairs and ranges[0][1].month>3 else [False]):
            periods=periods_for(ranges,quarter)
            rows=[]
            for k,values in data.items():
                vals=values[int(not quarter)::2] if pairs else values
                rows.append(make_row(k,*METRICS[k][:2],list(reversed(vals))))
            titles=(("연결 손익 · 연간","Annual consolidated earnings") if annual else
                    ("연결 손익 · 분기 3개월","Consolidated quarterly earnings") if quarter else
                    ("연결 손익 · 같은 기간 누계","Consolidated year-to-date earnings"))
            key="annual" if annual else "quarter" if quarter else "ytd"
            results.append(make_table(key,titles,source,periods,rows))
        return results
    raise ValueError("Consolidated statement not recognized for "+source["url"])


def segment_url(body,receipt):
    for block in re.findall(r"var node\d+\s*=\s*\{\};(.*?)\['atocId'\]",body,re.S):
        data=dict(re.findall(r"""\['(\w+)'\]\s*=\s*"([^"]+)" """.strip(),block))
        name=compact(data.get("text",""))
        if "부문" in name and name.endswith("(연결)") and data.get("rcpNo")==receipt:
            fields=("rcpNo","dcmNo","eleId","offset","length","dtd")
            if all(data.get(k,"").isdigit() for k in fields[:-1]) and re.fullmatch(r"dart\d+\.xsd",data.get("dtd","")):
                return FSS+"/report/viewer.do?"+urlencode({k:data[k] for k in fields})
    return None


def header_paths(table):
    """Build each value column's complete path, including grouped adjustment and subtotal headers."""
    grid={}
    for i,tr in enumerate(table.xpath("./thead/tr")):
        column=0
        for th in tr.xpath("./th|./td"):
            while (i,column) in grid: column+=1
            cols,rows=int(th.get("colspan","1")),int(th.get("rowspan","1"))
            if cols>150 or rows>20: raise ValueError("Invalid filing table span")
            for y in range(i,i+rows):
                for x in range(column,column+cols):
                    grid[y,x]=compact(th.text_content())
            column+=cols
    if not grid: return []
    return [tuple(dict.fromkeys(grid.get((y,x),"") for y in range(1+max(k[0] for k in grid)))) for x in range(1+max(k[1] for k in grid))]


def segment_values(table,metric,keys,core_total):
    paths=header_paths(table)
    for tr in table.xpath("./tbody/tr"):
        cells=tr.xpath("./td")
        if not cells or normalize_label(cells[0].text_content()) not in METRICS[metric][2]: continue
        values=[]
        for cell in cells:
            values.extend([cell.text_content()]*int(cell.get("colspan","1")))
        if len(paths)!=len(values): continue
        found={}
        for path,text in zip(paths,values):
            if any("조정" in s or "제거" in s for s in path) or "3개월" in path or not text.strip(): continue
            for k in keys:
                if all(tag in path for tag in k.split("/")):
                    if k in found: return None
                    found[k]=read_number(text)
        if set(found)!=set(keys) or any(v is None for v in found.values()):continue
        # If this table includes a grand total, reconcile against the same annual/YTD income statement.
        for path,text in zip(paths,values):
            if any(x.endswith("합계합계") or x=="기업전체총계합계" for x in path) and "3개월" not in path:
                if text.strip() and read_number(text)!=core_total:return None
        return found
    return None


def segment_tables(ticker,body,source,base):
    if ticker=="000660": return []  # SK hynix reports a single operating segment.
    configs={
        "005930":[("segments","부문별 매출","Segment revenue","revenue",["DX부문","DS부문","SDC","Harman"]),
                  ("products","주요 제품별 매출","Revenue from selected products","revenue",["TV,모니터등","스마트폰등","메모리","디스플레이패널"])],
        "055550":[("segments","부문별 순이익","Segment net income","net",["은행부문","신용카드부문","증권부문","보험부문","여신전문부문","기타부문"])],
        "105560":[("segments","부문별 순이익","Segment net income","net",["은행부문/기업금융","은행부문/가계금융","은행부문/기타","증권부문","손해보험부문","신용카드부문","생명보험부문","기타부문"])],
    }
    result=[]
    tables=body.xpath("//table")
    for key,ko,en,metric,keys in configs[ticker]:
        totals=next((r["values"][-2:] for r in base["rows"] if r["key"]==metric),None)
        if not totals or None in totals: continue
        found={}
        for i,table in enumerate(tables[1:],1):
            prefix=compact(tables[i-1].text_content())
            if "(단위:백만원)" not in prefix:continue
            term=re.search(r"(당|전)(?:기|분기|반기)(?:누적)?\(단위:백만원\)",prefix)
            if not term:continue
            index=1 if term[1]=="당" else 0
            values=segment_values(table,metric,keys,totals[index])
            if values:
                if index in found and found[index]!=values:
                    found={};break
                found[index]=values
        if len(found)!=2:continue
        rows=[make_row(k,*SEGMENTS[k],[found[0][k],found[1][k]]) for k in keys]
        balance=[totals[i]-sum(row["values"][i] for row in rows) for i in range(2)]
        if any(balance):
            rows.append(make_row("difference","표시 항목과 연결 합계의 차이","Difference from the consolidated total",balance,"residual"))
        periods=base["periods"][-2:]
        out=make_table(key,(ko,en),source,periods,rows)
        out["total"]=totals
        out["measure"]="net-income" if metric=="net" else "revenue"
        if key=="segments" and metric=="revenue" and all(min(found[i].values())>=0 for i in range(2)):
            out.update(compositionKeys=keys,compositionPeriods=[p["label"] for p in periods])
        if key=="products":
            out["notes"]=["공시가 따로 표시한 주요 제품입니다. 표의 차이에는 미표시 제품과 연결 조정 등이 포함될 수 있습니다."]
            out["notesEn"]=["The filing lists selected major products. The difference may include unlisted products and consolidation adjustments."]
        result.append(out)
    return result


def refresh_korea(report,fetch_json,fetch_filing):
    ticker=report["ticker"]
    if ticker not in ISSUERS: raise ValueError("No DART issuer mapping for "+ticker)
    today=date.today()
    candidates=[(year,month) for year in range(today.year,today.year-3,-1) for month in (12,9,6,3)
                if date(year,month,monthrange(year,month)[1])<=today]
    output=deepcopy(report)
    latest=[]
    for group in ("annual","interim"):
        selected=None
        for year,month in candidates:
            if (month==12)!=(group=="annual"):continue
            selected=lookup(ticker,year,month,fetch_filing)
            if selected:break
        if not selected:raise ValueError(f"No current DART {group} statement for {ticker}")
        source,statement,main=selected
        latest.append(source)
        prior=output[group]
        # A half-year filing may restate a prior full year. Compare the data periods,
        # since the publishing document can be newer than the annual figures it cites.
        recent=max((p.get("end") or "" for t in prior for p in t["periods"]),default="")
        if source["periodEnd"]<recent: raise ValueError("DART returned an older fiscal period for "+ticker)
        tables=consolidated(statement,source)
        receipt=source["url"].split("=")[-1]
        section=segment_url(main,receipt)
        if section and ticker!="000660":
            segments=segment_tables(ticker,document(fetch_filing(section)),{**source,"url":section},tables[0])
        else: segments=[]
        fresh=segments+tables
        refreshed={t["id"] for t in fresh}
        # Keep verified segment history if the issuer changes how a new note is laid out.
        output[group]=fresh+[t for t in prior if t["id"] not in refreshed]
    return output,{"latest":latest,"provider":"DART"}
