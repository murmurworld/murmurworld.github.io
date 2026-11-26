---
title: "메모리 반도체 세 가지, DRAM·NAND·HBM은 어디에 쓸까"
description: "휴대폰의 RAM과 저장공간부터 AI 가속기의 HBM까지. 메모리의 쓰임, 만드는 회사, 삼성전자 공시에서 확인할 수 있는 범위를 읽어 본다."
sector: semiconductors
publishedOn: '2026-11-26'
order: 1
video:
  id: '4MMfKTRZ_Mg'
  title: 'HBM, 그게 뭔데?'
  channel: 'Samsung Semiconductor Newsroom'
  start: 149
  end: 291
  label: '한국어 · 2:29~4:51'
  context: 'DRAM을 층층이 쌓고 실리콘을 뚫어 전기 신호가 오가는 통로를 만드는 모습을 볼 수 있다.'
---

휴대폰 사양표에 `RAM 12GB`와 `저장공간 256GB`가 함께 적혀 있으면, 왜 둘 다 필요한지부터 헷갈린다. 앱이 실행되는 동안 쓸 공간과 사진을 저장해 둘 공간을 따로 둔 것이다. AI 서버도 파일을 보관하는 곳과 계산하는 동안 데이터를 꺼내 쓰는 곳을 따로 둔다.

## 앱을 켤 때 쓰는 RAM, 사진을 남기는 NAND

앱을 열면 휴대폰은 실행에 필요한 데이터를 저장장치에서 꺼내 **RAM**에 올린다. 사진을 편집할 때 보던 화면은 RAM에 있고, 저장을 누른 뒤 남는 파일은 저장장치에 있다. 사양표의 RAM에는 보통 저전력 DRAM인 LPDDR이 쓰이고, 휴대폰 내장 저장장치에는 NAND 플래시가 쓰인다. 전원을 꺼도 저장한 사진을 다시 열 수 있는 건 NAND에 남아 있기 때문이다. [삼성반도체 DRAM 제품군](https://semiconductor.samsung.com/kr/dram/) · [삼성반도체 SSD 기술 자료](https://download.semiconductor.samsung.com/resources/white-paper/Samsung_SSD_White_Paper.pdf)

| 이름 | 무슨 일을 하나 | 어디서 보나 |
| --- | --- | --- |
| DRAM | 켜져 있는 동안 데이터를 꺼내 쓰는 작업 공간 | 휴대폰의 LPDDR, PC·서버의 DDR, 가속기용 HBM |
| NAND | 전원이 꺼져도 파일을 보관하는 플래시 메모리 | 휴대폰 저장장치, SSD |
| HBM | 연산 칩에 많은 데이터를 한꺼번에 보내는 적층 DRAM | 일부 AI·고성능 연산 가속기 |

**SSD와 HDD**도 둘 다 파일을 저장한다. SSD는 NAND와 읽기·쓰기를 제어하는 컨트롤러를 모은 장치다. HDD는 회전하는 원판에 데이터를 기록한다. 프로그램을 자주 여는 곳에는 SSD를, 큰 용량이 필요한 저장소에는 HDD를 쓰는 구성이 가능한 이유다. **NOR 플래시**는 기기가 켜질 때 읽는 펌웨어처럼 상대적으로 작은 코드 저장에 쓰인다. [삼성반도체 SSD 기술 자료](https://download.semiconductor.samsung.com/resources/white-paper/Samsung_SSD_White_Paper.pdf) · [Seagate FY2026 10-K](https://www.sec.gov/Archives/edgar/data/1137789/000113778926000159/stx-20260703.htm) · [Micron NOR 제품군](https://www.micron.com/products/storage/nor-flash)

사양표에 ‘NVMe SSD’가 적혀 있으면 저장에 쓰인 **NAND**, 이를 포함하는 장치인 **SSD**, 컴퓨터가 장치에 명령을 주고받는 규격인 **NVMe**까지 서로 다른 층을 보고 있는 것이다. [SNIA · SSD와 저장 인터페이스](https://www.snia.org/education/what-is-ssd)

## HBM은 왜 칩 옆에 붙일까

AI 가속기가 계산하는 동안에는 숫자를 계속 받아야 한다. HBM은 여러 DRAM 칩을 수직으로 쌓고 층 사이에 전기 신호가 오가는 통로를 만든다. 연산 칩 옆에 배치하고 넓은 연결 통로로 이어서 데이터를 한꺼번에 많이 전달할 수 있게 한다. <strong>용량(GB)</strong>은 담아 둘 수 있는 양이고, <strong>대역폭(GB/s)</strong>은 1초에 옮길 수 있는 양이다. 제품 표에서 뒤에 ‘/s’가 붙는지를 보면 두 값을 구분할 수 있다. SSD 용량을 늘려도, 연산 칩과 이미 연결된 HBM의 대역폭은 그대로다. [SK하이닉스 HBM 기술 설명](https://news.skhynix.com/en/tech-note-series-ep2/) · [TSMC 2025 연차보고서, CoWoS](https://investor.tsmc.com/sites/ir/annual-report/2025/2025%20TSMC%20Annual%20Report.E.pdf#page=52)

<figure class="guide-panel product-flow" aria-label="서버에서 파일을 보관한 뒤 일부 데이터를 계산에 쓰는 흐름">
  <ol>
    <li><strong>SSD</strong><span>모델 파일 보관</span></li>
    <li><strong>시스템 DRAM</strong><span>실행할 데이터 준비</span></li>
    <li><strong>HBM ↔ 연산 칩</strong><span>가속기에서 읽고 계산</span></li>
  </ol>
  <figcaption>한 가지 경로를 단순화한 그림이다. 실제 데이터 이동은 서버 구성과 프로그램에 따라 달라진다.</figcaption>
</figure>

## 같은 부품을 파는 회사와, 옆에서 일하는 회사

삼성전자·SK하이닉스·마이크론은 DRAM과 NAND를 팔고 HBM도 만든다. 가속기 업체가 HBM을 고를 때는 같은 세대라고 해도 용량, 대역폭, 발열과 패키지 호환성을 함께 본다. 샌디스크의 주력은 NAND 플래시 저장 제품이고, 씨게이트는 대용량 HDD가 중심이다. 두 회사는 파일을 저장하는 장치에서 용도가 겹친다. TSMC의 CoWoS는 연산 칩과 HBM을 한 패키지에 연결하는 역할이어서, 이 경우에는 메모리 업체와 하는 일이 다르다. [Micron FY2026 10-K](https://www.sec.gov/Archives/edgar/data/723125/000072312526000023/mu-20260903.htm) · [Sandisk 2026년 10월 종료 분기 10-Q](https://www.sec.gov/Archives/edgar/data/2023554/000162828026068601/sndk-20261002.htm) · [Seagate FY2026 10-K](https://www.sec.gov/Archives/edgar/data/1137789/000113778926000159/stx-20260703.htm) · [TSMC 2025 연차보고서](https://investor.tsmc.com/static/annualReports/2025/english/index.html)

메모리 회사 공시에는 수요와 공급이 함께 나온다. 주문이 늘어도 새 설비를 갖추고 제품을 양산하기까지는 시간이 걸린다. 반대로 설비 투자가 끝날 무렵 고객 주문이 줄 수도 있다. 마이크론 연차보고서의 `Memory and Storage Demand`와 `Manufacturing`을 나란히 읽으면, 회사가 수요와 공급 시차를 어떻게 설명하는지 볼 수 있다. [Micron FY2026 10-K](https://www.sec.gov/Archives/edgar/data/723125/000072312526000023/mu-20260903.htm)

## 삼성전자 공시에서 HBM을 찾아봤다

삼성전자 2026년 3분기 분기보고서에서 **사업의 내용 → 주요 제품 및 서비스**를 열면 DRAM과 NAND Flash가 나온다. 연결재무제표 주석 **부문별 보고**에는 DS 부문과 주요 제품인 메모리의 매출이 각각 나온다. 이 표에 HBM 매출은 따로 표시되지 않는다. 제품 설명에서 HBM을 찾았더라도 표의 메모리 매출을 HBM에만 해당하는 금액으로 읽을 수는 없다. 바로 아래에 3개월 실적과 1~9월 누적 실적이 따로 있으니 비교할 때는 먼저 기간을 맞춰 본다. [삼성전자 2026년 3분기 분기보고서](https://images.samsung.com/kdp/ir/business-report/2026_3Q_Interim_Business_Report_kr.pdf#page=7) · [2026년 3분기 연결재무제표](https://images.samsung.com/kdp/ir/financial-info/2026/2026_con_quarter03_all.pdf)
