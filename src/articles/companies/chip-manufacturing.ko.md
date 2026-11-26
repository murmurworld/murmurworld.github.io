---
title: '반도체는 누가 만들까? 파운드리와 제조 장비'
description: '팹리스 설계가 웨이퍼 위 회로가 되기까지, TSMC·ASML·어플라이드 머티어리얼즈·램리서치·KLA가 맡는 일을 살펴본다.'
sector: semiconductors
publishedOn: '2026-11-26'
order: 3
video:
  id: bcQCYsItVjM
  title: 'Holistic lithography'
  channel: ASML
  label: '영어'
  context: 'ASML이 웨이퍼에 패턴을 옮기는 장비와 측정·검사가 양산에서 어떻게 이어지는지 보여 준다.'
---

반도체 공장이 받아 드는 웨이퍼는 표면을 매끈하게 연마한 실리콘 원판이다. SUMCO 같은 소재 업체가 실리콘 덩어리를 얇게 잘라 원판을 만들고, 파운드리가 고객의 설계에 따라 그 위에 회로를 만든다. ASML 같은 장비 업체는 그 공장에서 쓸 기계를 공급한다. 공장에 들어오기 전후로 같은 웨이퍼에 어떤 일이 일어나는지 보면 회사들의 역할이 보인다. [SUMCO 웨이퍼 생산 공정](https://www.sumcosi.com/english/products/process/)

## 팹리스는 설계하고 파운드리는 생산한다

팹은 웨이퍼를 가공하는 반도체 공장이다. NVIDIA 같은 **팹리스**는 칩을 설계하고 웨이퍼 생산 등을 외부에 맡긴다. **파운드리**인 TSMC는 고객 설계를 받아 웨이퍼 위에 구현하고, 고급 패키징 서비스도 제공한다. 예를 들어 CoWoS는 연산 칩과 고대역폭 메모리인 HBM을 한 패키지 안에서 연결하는 방법이다. 고객이 위탁생산을 검토할 때는 삼성전자 파운드리도 비교 대상이 될 수 있다. 같은 세대 이름이 붙어 있어도 설계 지원, 납기, 수율, 패키징 조건을 따로 확인한다. [NVIDIA FY2026 공시의 Manufacturing](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm) · [TSMC 2025 연차보고서의 CoWoS](https://investor.tsmc.com/sites/ir/annual-report/2025/2025%20TSMC%20Annual%20Report.E.pdf#page=52) · [삼성전자 파운드리](https://semiconductor.samsung.com/kr/foundry/)

## 웨이퍼에 한 층을 만드는 장비들

한 층을 만드는 방법 중 하나는 **재료를 입히고 → 빛으로 패턴을 옮기고 → 필요한 부분을 남기고 → 결과를 확인하는** 순서다. 이런 작업을 반복해 여러 층을 쌓는다. 공정에 따라 화학 반응과 연마를 함께 써서 다음 층을 만들 표면을 평평하게 다듬기도 한다. 이 단계의 이름이 CMP다. [ASML 제조 공정 안내](https://www.asml.com/en/technology/all-about-microchips/how-microchips-are-made) · [어플라이드 머티어리얼즈 CMP 설명](https://www.appliedmaterials.com/in/en/semiconductor/products/shape/cmp.html)

- **증착**은 웨이퍼 위에 필요한 재료를 얇게 입히는 작업이다. 어플라이드 머티어리얼즈(Applied Materials)는 증착부터 연마·식각·측정까지 여러 공정의 장비를 판매한다. [어플라이드 머티어리얼즈 FY2025 10-K](https://www.sec.gov/Archives/edgar/data/6951/000162828025056742/amat-20251026.htm)
- **노광**은 빛으로 회로 패턴을 감광재에 옮기는 작업이다. ASML은 심자외선을 쓰는 DUV와 극자외선을 쓰는 EUV 장비를 공급한다. 이 단계에서 정해진 패턴은 뒤이어 재료의 일부를 제거하는 데 쓰인다. [ASML 노광 원리](https://www.asml.com/en/technology/lithography-principles)
- **식각**은 패턴에 맞춰 필요한 부분만 남도록 재료를 제거하는 작업이다. 램리서치(Lam Research)는 식각 외에 증착·세정 장비도 판매한다. 어플라이드와 겹치는 영역이 있어도 구매자는 같은 공정과 재료에 맞는 장비끼리 평가한다. [램리서치 FY2026 10-K](https://www.sec.gov/Archives/edgar/data/707549/000070754926000037/lrcx-20260628.htm)
- **검사·계측**은 층을 가공하는 여러 시점에 패턴의 크기와 위치를 재고 결함을 찾는 일이다. KLA는 검사·계측 장비와 공정 데이터를 분석하는 소프트웨어를 공급한다. 이 단계에서 얻은 정보는 다음 웨이퍼의 공정을 조정하는 데도 쓰인다. [KLA FY2026 10-K](https://www.sec.gov/Archives/edgar/data/319201/000031920126000027/klac-20260630.htm)

## 노광 장비를 같은 공정에서 비교하기

ASML TWINSCAN NXT:2100i와 니콘 NSR-S636E는 둘 다 ArF 광원을 쓰는 DUV 액침 노광 장비다. 사양표의 **오버레이**는 새 패턴이 앞선 층의 기준 위치에서 얼마나 어긋났는지 나타낸다. 공장은 필요한 정렬 정밀도를 만족하는 조건에서 시간당 웨이퍼를 몇 장 처리하는지 본다. 두 제조사의 최고 처리량을 나란히 놓을 때는 웨이퍼 크기와 노광 조건, 정렬 오차를 측정한 기준도 확인한다. [ASML 제품 사양](https://www.asml.com/en/products/duv-lithography-systems/twinscan-nxt2100i) · [니콘 제품 발표](https://www.nikon.com/company/news/2023/1206_01/)

## 공장에서 지출한 돈은 누구의 매출일까?

TSMC는 2025년 연차보고서에서 <strong>3나노 공정이 전체 웨이퍼 매출의 24%</strong>였다고 밝혔다. 이 비중은 공정 세대를 기준으로 집계한 숫자다. 스마트폰과 고성능 컴퓨팅(HPC) 등 응용처별 비중은 플랫폼 표에서 따로 확인한다. [TSMC 2025 연차보고서](https://investor.tsmc.com/static/annualReports/2025/english/index.html)

ASML은 2025년 공시에서 장비 판매와 **설치 장비의 서비스·현장 옵션 매출**을 따로 보여 준다. 램리서치도 2026년 6월 28일 종료 회계연도에서 신규 시스템 매출과 고객 지원 관련 매출을 구분한다. 램리서치의 고객 지원에는 정비·부품·업그레이드와 함께 일부 장비 판매도 포함된다. 장비 주문, 장비 판매 매출, 고객 지원 매출을 구분해 읽으면 공장이 새로 사는 장비와 기존 생산라인을 가동하며 쓰는 비용을 이해하기 쉽다. [ASML 2025 연차보고서](https://www.sec.gov/Archives/edgar/data/937966/000162828026011377/asml-2025xannualxreportx.htm) · [램리서치 FY2026 10-K](https://www.sec.gov/Archives/edgar/data/707549/000070754926000037/lrcx-20260628.htm)
