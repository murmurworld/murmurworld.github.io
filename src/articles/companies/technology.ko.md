---
title: "빅테크·소프트웨어·IT"
description: "온라인 쇼핑몰이 클라우드에 올린 주문 한 건 뒤에는 서버, 저장장치, 보안 프로그램이 있다. 같은 주문을 불러온 광고 한 건은 또 다른 시장에서 팔린다."
studyCase:
  featured: AMZN
  title: 아마존에서 책 한 권과 서버 한 시간이 만드는 매출
  intro: 쇼핑몰에서는 물건값을, 클라우드에서는 컴퓨터를 쓴 시간을 결제한다. 이 돈이 아마존 매출표에 어떤 크기로 들어가는지 따라가면 매출 비중과 이익 비중이 왜 다른지도 보인다.
  lenses:
  - label: 같은 책을 팔아도 매출이 다른 이유는?
    body: 아마존이 사들인 책을 직접 팔면 판매액이 매출에 잡힌다. 외부 서점이 아마존 장터에서 팔면 아마존은 판매 수수료와 제공한 배송 서비스 등의 대가를 잡는다. 그래서 장터에서 고객이 결제한 총액과 아마존 매출은 서로 다른 수치다.
    source: https://www.sec.gov/Archives/edgar/data/1018724/000101872426000004/amzn-20251231.htm
  - label: 창고와 데이터센터는 각각 무엇을 공급하나?
    body: 물류센터는 상품을 보관하고 주문이 들어오면 골라서 포장한다. AWS 데이터센터는 서버를 설치해 두고 기업에 연산·저장 용량을 제공한다. AWS와 다른 클라우드를 비교할 때는 어느 회사의 어느 서비스가 같은 앱을 돌릴 수 있는지부터 좁혀야 한다.
    source: https://www.sec.gov/Archives/edgar/data/1018724/000101872426000004/amzn-20251231.htm
  - label: AWS의 매출 비중과 영업이익 비중은 얼마였나?
    body: 2025년 금액을 백만 달러로 맞추면 AWS 매출 비중은 128,725 ÷ 716,924로 약 18.0%다. 영업이익 비중은 45,606 ÷ 79,975로 약 57.0%다. 두 번째 숫자의 분모는 아마존 전체 영업이익이다. AWS 자체 영업이익률은 45,606 ÷ 128,725로 약 35.4%다.
    source: https://www.sec.gov/Archives/edgar/data/1018724/000101872426000004/amzn-20251231.htm
  - label: 서버를 먼저 사고 고객이 나중에 늘면?
    body: 데이터센터를 지을 때 쓴 현금은 투자활동에 먼저 보인다. 사용을 시작한 서버의 원가는 여러 해에 걸쳐 감가상각되고 고객이 실제 용량을 쓰면서 매출이 생긴다. 시차를 확인하려면 현금흐름표의 설비 투자와 AWS의 당기 매출·영업이익을 함께 보되, 아마존 전체 설비 투자에는 물류 설비도 포함된다는 점을 챙기자.
    source: https://www.sec.gov/Archives/edgar/data/1018724/000101872426000004/amzn-20251231.htm
  exercise:
    question: 가상의 서점이 아마존에서 100달러짜리 책을 팔고 아마존에 수수료 15달러만 낸다. 아마존 매출로 잡히는 금액은?
    answer: 외부 서점이 판매 주체라면 이 사례에서 아마존 매출은 15달러다. 아마존이 자기 재고를 같은 값에 직접 팔면 매출은 100달러이고 책을 사들인 원가는 비용에 들어간다. 어느 쪽의 이익이 더 큰지는 매출만으로 알 수 없다.
    source: https://www.sec.gov/Archives/edgar/data/1018724/000101872426000004/amzn-20251231.htm
  peers:
  - MSFT
  - GOOGL
  - ORCL
---

<p class="lead">온라인 쇼핑몰이 클라우드에 올린 주문 한 건 뒤에는 서버, 저장장치, 보안 프로그램이 있다. 같은 주문을 불러온 광고 한 건은 또 다른 시장에서 팔린다.</p>

<h2>누가 누구에게 파나</h2>

<figure class="map">

<div class="tier"><h3>기기·서버 부품·네트워크</h3><ul class="cos">

<li><a class="co" href="/blog/companies/technology/apple/"><b>애플</b><small>아이폰·맥·서비스</small></a></li>

<li><a class="co" href="/blog/companies/technology/seagate/"><b>씨게이트</b><small>하드디스크</small></a></li>

<li><a class="co" href="/blog/companies/technology/cisco/"><b>시스코</b><small>네트워크 장비</small></a></li>

</ul><p>애플은 완성된 기기를, 씨게이트는 데이터를 오래 보관하는 디스크를, 시스코는 장비 사이로 데이터를 보내는 스위치와 라우터를 판다. 세 회사가 서로에게 직접 납품한다는 뜻은 아니다.</p></div>

<div class="flow"><span>↓ 장비로 클라우드 인프라를 구성한다</span></div>

<div class="tier"><h3>컴퓨팅을 빌려주는 곳</h3><ul class="cos">

<li><a class="co" href="/blog/companies/technology/amazon/"><b>아마존</b><small>온라인 쇼핑·AWS</small></a></li>

<li><a class="co" href="/blog/companies/technology/microsoft/"><b>마이크로소프트</b><small>클라우드·오피스 구독</small></a></li>

<li><a class="co" href="/blog/companies/technology/alphabet/"><b>알파벳</b><small>검색 광고·유튜브·클라우드</small></a></li>

<li><a class="co" href="/blog/companies/technology/oracle/"><b>오라클</b><small>데이터베이스·클라우드</small></a></li>

<li><a class="co" href="/blog/companies/technology/ionq/"><b>아이온큐</b><small>양자컴퓨터</small></a></li>

</ul><p>서버와 저장공간을 시간이나 사용량 단위로 빌릴 수 있다. 아이온큐는 양자컴퓨터를 클라우드 마켓플레이스에서도 쓰게 한다.</p></div>

<div class="flow"><span>↓ 호스팅이나 마켓플레이스를 제공한다</span></div>

<div class="tier"><h3>구독 소프트웨어와 보안</h3><ul class="cos">

<li><a class="co" href="/blog/companies/technology/crowdstrike/"><b>크라우드스트라이크</b><small>보안 구독</small></a></li>

<li><a class="co" href="/blog/companies/technology/palo-alto-networks/"><b>팔로알토 네트웍스</b><small>방화벽·보안</small></a></li>

<li><a class="co" href="/blog/companies/technology/palantir/"><b>팔란티어</b><small>데이터 분석 소프트웨어</small></a></li>

</ul><p>회사는 노트북·계정의 보안 신호를 살피거나 여러 시스템의 데이터를 연결하기 위해 소프트웨어 이용료를 낸다.</p></div>

<div class="flow"><span>↳ 별도 수입원 · 광고주가 노출과 행동에 비용을 낸다</span></div>

<div class="tier"><h3>광고를 파는 곳</h3><ul class="cos">

<li><a class="co" href="/blog/companies/technology/meta/"><b>메타</b><small>소셜 앱 광고</small></a></li>

<li><a class="co" href="/blog/companies/technology/applovin/"><b>앱러빈</b><small>앱 광고 플랫폼</small></a></li>

</ul><p>메타는 자기 앱의 광고 자리를, 앱러빈은 광고주와 앱 지면 등을 연결하는 기술을 판다. 위의 알파벳도 검색과 유튜브 광고를 판다.</p></div>

<div class="flow"><span>↓ 섹터 밖 고객과 유통·계약으로 연결된다</span></div>

<div class="tier out"><h3>섹터 밖의 거래 상대</h3><p>기업 IT 부서는 클라우드 사용료나 이용자별 구독료를 내고, 광고주는 잠재 고객을 만나는 데 돈을 쓴다. 칩 공급사는 <a href="/blog/companies/semiconductors/nvidia/">엔비디아</a>처럼 반도체 섹터에 있다.</p></div>

<figcaption>화살표는 서비스가 전달되는 대표 경로다. 이름이 확인된 납품·서비스 계약은 아래 표에 따로 모았다.</figcaption></figure>

<h2>보안 구독료 한 건은 어디로 가나</h2>

<p>회사가 직원 노트북을 보호하려고 팰컨을 구독하면, 돈을 받는 곳은 <a href="/blog/companies/technology/crowdstrike/">크라우드스트라이크</a>다. 설치된 센서가 보내는 신호를 모아 분석하는 플랫폼도 어딘가에서 돌아가야 한다. 크라우드스트라이크는 외부 데이터센터 가운데 AWS를 지목하고, 임차한 시설에서 자체 시스템도 운영한다고 밝힌다.</p>

<p>고객이 지불한 구독료는 크라우드스트라이크 매출이지만, 서버를 빌리는 비용은 그 회사의 비용이다. 반면 무료 앱에 뜬 광고 한 건은 광고주가 광고비를 낸다. 지면 경매에서는 입찰가와 예상 반응 등으로 어느 광고를 보여 줄지 정한다. 메타 공시의 광고 노출 수와 광고당 평균 가격은 클라우드 사용량과 전혀 다른 지표다.</p>

<p class="src"><a href="https://www.sec.gov/Archives/edgar/data/1535527/000153552726000031/crwd-20260731.htm">CrowdStrike 2026-07 10-Q</a> · <a href="https://www.sec.gov/Archives/edgar/data/1326801/000162828026025534/meta-12312025x10kars.htm">Meta 2025 Annual Report</a> · <a href="https://www.sec.gov/Archives/edgar/data/1824920/000119312526071562/ionq-20251231.htm">IonQ 2025 10-K</a></p>

<h2>공시에 이름이 나온 거래</h2>

<div class="tw" role="region" tabindex="0" aria-label="사는 회사 / 공시 근거"><table><thead><tr><th scope="col">사는 회사</th><th scope="col">파는 회사</th><th scope="col">거래 내용</th><th scope="col">공시 근거</th></tr></thead><tbody><tr><th scope="row"><a href="/blog/companies/technology/crowdstrike/">크라우드스트라이크</a></th><td><a href="/blog/companies/technology/amazon/">아마존</a> · AWS</td><td>팰컨 호스팅에 사용하는 외부 데이터센터 서비스. 자체 시설과 병행한다.</td><td><a href="https://www.sec.gov/Archives/edgar/data/1535527/000153552726000031/crwd-20260731.htm">CrowdStrike 2026-07 10-Q</a></td></tr><tr><th scope="row">오픈AI</th><td><a href="/blog/companies/technology/microsoft/">마이크로소프트</a></td><td>2026년 9월 분기 공시는 오픈AI와의 상업 계약 매출을 별도로 밝힌다. 수익 배분금이 포함돼 전부를 Azure 사용료로 볼 수 없다.</td><td><a href="https://www.sec.gov/Archives/edgar/data/789019/000119312526436133/msft-20260930.htm">Microsoft 2026-09 10-Q</a></td></tr></tbody></table></div>

<h2>같은 물건을 두고 경쟁하는 회사</h2>

<div class="tw" role="region" tabindex="0" aria-label="제품·서비스 / 근거"><table><thead><tr><th scope="col">제품·서비스</th><th scope="col">경쟁하는 회사</th><th scope="col">근거</th></tr></thead><tbody><tr><th scope="row">기업용 클라우드·소프트웨어</th><td><a href="/blog/companies/technology/oracle/">오라클</a>은 <a href="/blog/companies/technology/amazon/">아마존</a>, <a href="/blog/companies/technology/microsoft/">마이크로소프트</a>, <a href="/blog/companies/technology/alphabet/">알파벳</a> 등을 일부 제품에서 경쟁하는 회사로 적는다.</td><td><a href="https://www.sec.gov/Archives/edgar/data/1341439/000119312526277521/orcl-20260531.htm">Oracle FY2026 10-K</a></td></tr><tr><th scope="row">보안·컴플라이언스 플랫폼</th><td>퀄리스는 <a href="/blog/companies/technology/crowdstrike/">크라우드스트라이크</a>와 <a href="/blog/companies/technology/palo-alto-networks/">팔로알토 네트웍스</a>를 경쟁사로 열거한다. 방화벽, 엔드포인트 보호 등 개별 품목의 범위는 다르다.</td><td><a href="https://www.sec.gov/Archives/edgar/data/1107843/000110784326000044/qlys-20260930.htm">Qualys 2026-09 10-Q</a></td></tr></tbody></table></div>

<h2>이 섹터의 회사 13곳</h2>

<div class="roster">

<div><h3>기기·서버 부품·네트워크</h3><ul>

<li><b><a href="/blog/companies/technology/apple/">애플</a><small>AAPL</small></b><span>아이폰·맥·아이패드·워치 같은 기기를 팔고, 앱스토어·아이클라우드·애플뮤직 같은 서비스로도 번다.</span></li>

<li><b><a href="/blog/companies/technology/seagate/">씨게이트</a><small>STX</small></b><span>하드디스크(HDD)를 만드는 회사다. 데이터센터와 기업용 대용량 하드디스크가 중심이다.</span></li>

<li><b><a href="/blog/companies/technology/cisco/">시스코</a><small>CSCO</small></b><span>회사·통신사 네트워크의 길을 정하는 라우터·스위치를 만들고, 보안·화상회의(웹엑스)·시스템 감시(스플렁크) 소프트웨어도 판다.</span></li>

</ul></div>

<div><h3>컴퓨팅을 빌려주는 곳</h3><ul>

<li><b><a href="/blog/companies/technology/amazon/">아마존</a><small>AMZN</small></b><span>소비자에게 상품을 팔고 입점 판매자에게 서비스를 제공한다. AWS는 기업에 서버·저장공간·데이터베이스를 빌려준다.</span></li>

<li><b><a href="/blog/companies/technology/microsoft/">마이크로소프트</a><small>MSFT</small></b><span>기업이 빌려 쓰는 클라우드(애저)와 오피스 구독(마이크로소프트 365), 윈도를 판다. 게임(엑스박스)과 검색 광고도 한다.</span></li>

<li><b><a href="/blog/companies/technology/alphabet/">알파벳</a><small>GOOGL</small></b><span>구글 검색과 유튜브에 붙는 광고가 가장 큰 수입이다. 구글 클라우드, 안드로이드·크롬, AI 모델 제미나이도 만든다.</span></li>

<li><b><a href="/blog/companies/technology/oracle/">오라클</a><small>ORCL</small></b><span>기업에 데이터베이스와 업무용 소프트웨어를 공급한다. 자사 클라우드에서도 인프라와 애플리케이션을 이용할 수 있다.</span></li>

<li><b><a href="/blog/companies/technology/ionq/">아이온큐</a><small>IONQ</small></b><span>양자컴퓨터와 컴퓨팅 이용권을 판다. 클라우드 서비스에서 원격으로 양자 연산을 실행할 수 있다.</span></li>

</ul></div>

<div><h3>구독 소프트웨어와 보안</h3><ul>

<li><b><a href="/blog/companies/technology/crowdstrike/">크라우드스트라이크</a><small>CRWD</small></b><span>노트북·서버·클라우드를 해킹에서 지키는 보안 소프트웨어(팰컨)를 구독으로 판다.</span></li>

<li><b><a href="/blog/companies/technology/palo-alto-networks/">팔로알토 네트웍스</a><small>PANW</small></b><span>회사 네트워크 입구를 지키는 방화벽과, 클라우드·보안 운영·계정 보안 소프트웨어를 한 묶음으로 파는 보안 회사다.</span></li>

<li><b><a href="/blog/companies/technology/palantir/">팔란티어</a><small>PLTR</small></b><span>정부와 기업이 흩어진 데이터를 한곳에 모아 판단과 작업에 쓰게 하는 소프트웨어를 만든다. 정부용과 기업용 두 갈래다.</span></li>

</ul></div>

<div><h3>광고를 파는 곳</h3><ul>

<li><b><a href="/blog/companies/technology/meta/">메타</a><small>META</small></b><span>페이스북·인스타그램·왓츠앱을 무료로 쓰게 하고, 그 안의 광고 자리를 팔아 번다. VR 기기와 AI 안경도 만든다.</span></li>

<li><b><a href="/blog/companies/technology/applovin/">앱러빈</a><small>APP</small></b><span>모바일 앱·게임 안의 광고 자리를 광고주와 이어 주는 광고 플랫폼 회사다. 어떤 광고를 누구에게 보일지 AI 추천 엔진이 고른다.</span></li>

</ul></div>

</div>

<p class="note">거래·경쟁 표와 본문에 연결한 공시·제품 자료를 2026년 11월 26일에 확인했다.</p>
