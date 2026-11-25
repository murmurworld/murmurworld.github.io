---
title: "클라우드와 구독 소프트웨어는 무엇을 빌려줄까"
description: "작은 가게의 주문 사이트를 예로 IaaS·PaaS·SaaS가 맡는 일과 요금 기준을 비교한다. 아마존·마이크로소프트·알파벳·오라클·팔란티어의 공시에서 클라우드 매출도 읽는다."
sector: technology
publishedOn: '2026-11-26'
---

작은 가게가 온라인 주문 사이트를 만든다고 해보자. 사이트를 돌릴 컴퓨터가 필요하고, 주문과 재고를 저장할 곳도 있어야 한다. 직원들이 교대표를 공유하려면 메일이나 문서 앱을 따로 쓸 수 있다. 모두 인터넷으로 접속할 수 있지만, 가게가 공급자에게 맡기는 일은 각각 다르다.

## 가게는 어디까지 직접 관리할까

직접 서버를 사면 컴퓨터를 놓을 자리, 전기, 인터넷 연결부터 챙긴다. 클라우드에서는 공급자의 데이터센터에 있는 처리 능력과 저장 공간을 필요에 따라 쓸 수 있다. 서버처럼 쓸 가상 컴퓨터를 빌리는 방식이 <strong>서비스형 인프라(IaaS)</strong>다. 장비는 공급자가 관리하고, 가게는 가상 컴퓨터의 운영체제와 주문 앱을 관리한다. 주문이 몰리면 자원을 더 붙일 수 있고, 안정적으로 계속 쓰이는 작업이라면 사용량과 장기 약정 조건을 함께 보게 된다. [미국 국립표준기술연구소(NIST), 클라우드 정의](https://csrc.nist.gov/pubs/sp/800/145/final)

가게가 주문 앱 코드만 올리고 실행 환경까지 맡기면 <strong>서비스형 플랫폼(PaaS)</strong>을 쓰는 것이다. Azure App Service에 코드를 올리면 마이크로소프트가 앱이 돌아갈 환경을 운영한다. 주문을 어떻게 받고 처리할지는 가게가 코드와 설정으로 정한다. [Microsoft Learn, App Service 웹앱 구성](https://learn.microsoft.com/en-us/azure/architecture/web-apps/app-service/architectures/basic-web-app)

<strong>서비스형 소프트웨어(SaaS)</strong>는 완성된 앱을 쓰는 방식이다. 마이크로소프트 365나 구글 워크스페이스에서 문서를 공유할 때 공급자는 앱을 운영하고, 가게는 직원 계정과 문서 접근 권한을 관리한다. [NIST, SaaS 정의](https://csrc.nist.gov/glossary/term/software_as_a_service)

<h2 id="cloud-services">같은 일을 하는 서비스끼리 보기</h2>

<div class="guide-panel">
  <table aria-labelledby="cloud-services">
    <colgroup><col style="width: 29%"><col></colgroup>
    <thead><tr><th scope="col">가게에 필요한 일</th><th scope="col">서비스와 맡기는 범위</th></tr></thead>
    <tbody>
      <tr><th scope="row">서버에서 주문 앱 실행</th><td><strong>Amazon EC2 · Azure Virtual Machines</strong><br>공급자가 장비를 관리하고, 가게가 운영체제와 앱을 관리한다.</td></tr>
      <tr><th scope="row">코드로 주문 앱 배포</th><td><strong>Azure App Service · <a href="https://www.heroku.com/blog/simplifying-jvm-app-development-herokus-buildpack-magic/">Heroku</a></strong><br>공급자가 코드 실행 환경을 운영하고, 가게가 코드와 앱 설정을 관리한다.</td></tr>
      <tr><th scope="row">주문 기록 보관</th><td><strong><a href="https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html">Amazon RDS for PostgreSQL</a> · <a href="https://learn.microsoft.com/en-us/azure/postgresql/overview">Azure Database for PostgreSQL</a></strong><br>같은 데이터베이스 엔진을 쓴다. 공급자가 백업·패치 등의 기능을 제공하고, 가게가 데이터와 접근 권한을 관리한다.</td></tr>
      <tr><th scope="row">문서·메일 공유</th><td><strong>Microsoft 365 · Google Workspace</strong><br>공급자가 완성된 앱을 운영하고, 가게가 계정과 공유 권한을 관리한다.</td></tr>
    </tbody>
  </table>
</div>

국내 NHN Cloud의 관리형 PostgreSQL에서도 백업 주기와 보관 기간은 고객이 정한다. 공급자가 백업본을 보관하고 저장 용량을 기준으로 요금을 계산한다. 가게가 어떤 시점으로 주문 기록을 되돌릴 수 있는지 알고 싶다면 이 보관 조건을 보면 된다. [NHN Cloud PostgreSQL 사용자 가이드](https://docs.nhncloud.com/ko/Database/RDS%20for%20PostgreSQL/ko/db-instance/)

<h2 id="cloud-billing">청구서에서는 무엇을 셀까</h2>

<div class="guide-panel">
  <table aria-labelledby="cloud-billing">
    <colgroup><col style="width: 29%"><col></colgroup>
    <thead><tr><th scope="col">서비스</th><th scope="col">실제 청구 단위의 예</th></tr></thead>
    <tbody>
      <tr><th scope="row">가상 서버</th><td><a href="https://aws.amazon.com/ec2/pricing/on-demand/">EC2 온디맨드</a>는 인스턴스가 돌아간 시간을 센다.</td></tr>
      <tr><th scope="row">앱 실행 환경</th><td><a href="https://learn.microsoft.com/en-us/azure/app-service/overview-hosting-plans">Azure App Service</a>의 전용 컴퓨팅 요금제는 실행에 배정한 인스턴스 수를 본다.</td></tr>
      <tr><th scope="row">DB 백업</th><td>NHN Cloud PostgreSQL은 백업이 차지한 저장 용량을 센다.</td></tr>
      <tr><th scope="row">구독 앱</th><td>협업 앱은 직원이 쓰는 <a href="https://stripe.com/au/resources/more/saas-pricing-and-packaging-strategy">유료 좌석</a>을, 다른 앱은 기능 사용량을 청구 단위로 둘 수 있다.</td></tr>
    </tbody>
  </table>
</div>

## 쌓인 주문 기록으로 할 수 있는 일

데이터베이스가 한 주문의 결제 상태를 찾아준다면, **데이터 분석 플랫폼**은 여러 기록을 모아 질문에 답하는 데 쓰인다. 주문과 재고를 연결해서 어느 상품의 주문이 자꾸 밀리는지 보고, 담당자가 확인할 목록을 만드는 식이다. 오라클 클라우드에서 데이터베이스를 운영하는 일과 팔란티어 파운드리에서 여러 시스템의 데이터를 엮어 업무에 활용하는 일은 한 회사 안에서도 함께 쓰일 수 있다. [오라클 2026년 5월 결산 10-K, 사업 설명](https://www.sec.gov/Archives/edgar/data/1341439/000119312526277521/orcl-20260531.htm) · [팔란티어 2025년 12월 결산 10-K, 사업 설명](https://www.sec.gov/Archives/edgar/data/1321655/000132165526000011/pltr-20251231.htm)

## 공시의 ‘클라우드 매출’에 담긴 것

같은 종류의 서버를 빌려주는 회사도 공시에서는 서로 다른 사업을 한 항목에 묶는다. 제품의 용도를 확인한 다음, 재무제표 주석에서 그 제품과 함께 잡히는 사업을 본다.

- **아마존 AWS**는 별도 사업부문이다. 컴퓨팅 외에 저장, 데이터베이스 등 여러 서비스가 들어가므로 AWS 매출은 EC2 한 제품의 매출보다 범위가 넓다. [2025년 12월 결산 10-K, 재무제표 주석 10](https://www.sec.gov/Archives/edgar/data/1018724/000101872426000004/amzn-20251231.htm)
- **마이크로소프트**의 2026년 6월 결산서에서는 애저가 서버 제품 및 클라우드 서비스 항목에 들어간다. 별도 지표인 ‘Microsoft Cloud’에는 애저 외에 기업용 Microsoft 365 클라우드와 Dynamics 365 등도 포함된다. [2026년 6월 결산 10-K, 재무제표 주석 18](https://www.sec.gov/Archives/edgar/data/789019/000119312526323660/msft-20260630.htm)
- **알파벳 Google Cloud**에는 인프라와 데이터 서비스를 파는 Google Cloud Platform, 문서와 메일 등을 제공하는 Google Workspace가 함께 들어간다. [2025년 12월 결산 10-K, 사업 설명 및 재무제표 주석 15](https://www.sec.gov/Archives/edgar/data/1652044/000165204426000018/goog-20251231.htm)
- **오라클**의 사업부문 ‘클라우드 및 소프트웨어’에는 클라우드 외에 소프트웨어 라이선스와 지원도 들어간다. 경영진 실적 설명에서는 클라우드 인프라와 클라우드 앱 수치를 따로 볼 수 있다. [2026년 5월 결산 10-K, 실적 설명 및 재무제표 주석 13](https://www.sec.gov/Archives/edgar/data/1341439/000119312526277521/orcl-20260531.htm)
- **팔란티어**는 파운드리와 고담 같은 제품을 사업 설명에서 소개한다. 주석은 매출을 정부 고객과 민간 고객 부문으로 나눈다. [2025년 12월 결산 10-K, 사업 설명 및 재무제표 주석 13](https://www.sec.gov/Archives/edgar/data/1321655/000132165526000011/pltr-20251231.htm)

클라우드 공시의 숫자를 나란히 읽을 때는 먼저 결산일과 항목 이름을 보고, 그 아래에 서버 사용료와 완성된 앱 구독이 어디까지 들어 있는지 확인하면 된다.
