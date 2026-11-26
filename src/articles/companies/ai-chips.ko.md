---
title: 'AI 칩은 무엇을 할까? CPU·GPU·맞춤형 가속기'
description: 'AI 모델의 학습과 추론에서 CPU, GPU, 맞춤형 가속기와 네트워크가 맡는 일부터 제품과 공시를 비교하는 법까지.'
sector: semiconductors
publishedOn: '2026-11-26'
order: 2
video:
  id: eATdZCyw430
  title: 'What is a TPU?'
  channel: Google
  label: '영어'
  context: '구글이 자사 TPU를 예로 들어 머신러닝 연산에 맞춰 설계한 칩이 범용 CPU와 어떻게 다른지 설명한다.'
---

AI 챗봇에 질문을 보내면 서버는 요청을 받아 적절한 장비에 일을 배정하고, 모델은 계산을 거쳐 답을 만든다. 여러 장비가 하나의 모델을 나눠 처리할 때는 중간 결과도 주고받는다. 데이터센터가 무엇을 사는지 알려면 이 과정에서 어떤 장비가 어떤 일을 맡는지부터 보면 된다.

<figure class="guide-panel product-flow" aria-label="질문 하나가 답변이 되는 흐름">
  <ol>
    <li><strong>요청 받기</strong><span>CPU에서 서비스 실행과 요청 배정</span></li>
    <li><strong>첫 답 만들기</strong><span>가속기가 질문을 처리하고 첫 토큰 생성</span></li>
    <li><strong>이어 쓰기</strong><span>가속기가 다음 토큰을 차례로 계산</span></li>
  </ol>
  <figcaption>토큰은 모델이 읽고 쓰는 텍스트 조각이다. 첫 글자가 보이는 시간과 이후 답이 이어지는 속도를 따로 재는 이유다.</figcaption>
</figure>

## 모델을 만드는 학습, 답을 만드는 추론

**학습**은 데이터를 보며 모델의 내부 값인 가중치를 조정하는 과정이다. **추론**은 학습된 가중치를 사용해 새 입력을 분류하거나 답을 생성하는 과정이다. 학습 장비를 고를 때는 일정한 조건에서 모델을 만드는 데 걸리는 시간과 여러 장비를 함께 썼을 때의 효율을 본다. 추론 서비스라면 첫 답이 나오기까지 걸리는 시간, 요청이 몰렸을 때 처리할 수 있는 양, 답변 하나를 만드는 데 드는 비용이 중요하다. 같은 가속기를 두 작업에 쓸 수도 있다. [NVIDIA 시스템 설계 자료](https://docs.nvidia.com/enterprise-reference-architectures/white-paper/latest/reference-architectures-deep-dive.html) · [Google Cloud 추론 문서](https://docs.cloud.google.com/tpu/docs/tpu-inference)

## CPU, GPU, 맞춤형 칩의 자리

- **CPU**는 운영체제와 서비스 코드를 실행하고 요청·데이터·장치를 관리하는 범용 프로세서다. 서버 CPU를 찾는 구매자는 인텔 Xeon과 AMD EPYC를 같은 용도에서 비교할 수 있다.
- **GPU**는 많은 연산을 동시에 수행하는 데 적합하다. NVIDIA의 데이터센터 GPU와 AMD Instinct는 모델 학습과 추론에 쓰이는 가속기다. 모델과 실행 도구가 지원하는지도 구매 판단에 들어간다.
- **맞춤형 가속기**는 특정한 계산에 맞춰 설계한다. 구글 TPU가 머신러닝용 사례다. 브로드컴은 공시에서 고객 맞춤형 가속기 제품을 XPU라고 부르며, 데이터센터용 이더넷 스위치 칩 등도 공급한다고 설명한다. 맞춤형 칩의 연산 기능과 네트워크 칩의 연결 기능은 구매 목적이 다르다. [Google Cloud TPU 문서](https://docs.cloud.google.com/tpu/docs/intro-to-tpu) · [브로드컴 FY2025 공시](https://www.sec.gov/Archives/edgar/data/1730168/000173016825000121/avgo-20251102.htm)

연구팀이 가속기를 쓰려면 서버 장비를 직접 들이거나 클라우드에서 빌릴 수 있다. 예를 들어 AWS의 EC2 P6 계열은 NVIDIA GPU가 든 가상 서버를, Google Cloud는 TPU 사용 환경을 제공한다. 칩 제조사와 클라우드 회사는 서로 다른 단계에서 돈을 받는다. 후자는 모델을 돌릴 수 있는 컴퓨팅 자원과 운영 환경을 고객에게 제공한다. [AWS EC2 P6](https://aws.amazon.com/ec2/instance-types/p6/) · [Google Cloud TPU](https://cloud.google.com/tpu)

## GPU 여덟 개를 같은 조건에서 비교하기

NVIDIA HGX B200과 AMD Instinct MI355X 플랫폼은 각각 GPU 여덟 개를 연결하는 시스템 구성이라 비교 범위를 맞추기 좋다. 스펙에서 메모리 용량이 GPU 한 개 기준인지 여덟 개의 합인지 확인한다. 제조사가 ‘몇 배 빠르다’고 제시하면 같은 모델·수치 정밀도·동시 요청 수·입출력 길이에서 시험했는지 본다. 추론 용도라면 같은 응답 지연 목표를 만족할 때 초당 얼마나 처리하는지도 필요하다. 제품 페이지에서 구성은 확인할 수 있고, 성능 차이는 해당 조건을 공개한 시험으로 판단한다. [NVIDIA HGX B200 구성](https://docs.nvidia.com/enterprise-reference-architectures/hgx-ai-factory-h100-h200-b200/latest/components.html) · [AMD MI355X 플랫폼 구성](https://www.amd.com/en/products/accelerators/instinct/mi350/mi355x/platform.html)

| 비교하려는 것 | 보고서에서 맞춰 볼 조건 |
| --- | --- |
| 첫 답이 나오는 속도 | 같은 모델, 같은 입력 길이, 같은 동시 요청 수 |
| 요청이 몰릴 때 처리량 | 같은 응답 지연 목표와 동일한 GPU 수 |
| 모델을 올릴 수 있는 공간 | GPU 한 개 용량과 시스템 전체 합계를 구분 |

MLPerf의 데이터센터 추론 결과를 볼 때도 먼저 같은 시험 유형과 지연 조건 아래 있는 항목을 찾는다. [MLCommons 추론 벤치마크](https://mlcommons.org/benchmarks/inference-datacenter/)

## 서버가 늘어나면 연결과 전력도 필요하다

GPU 여러 개가 작업을 나누면 각 장치가 빠르게 계산하는 것만큼 결과를 주고받는 속도도 중요하다. 서버 안에서 GPU를 잇는 연결과 서버 사이에서 데이터를 나르는 네트워크는 구매할 때 따로 살펴볼 부분이다. 데이터센터 운영자는 가동 중인 랙에 필요한 전력을 공급하고, 발생한 열을 냉각 설비로 빼낼 수 있는지도 확인한다. 장비를 들일 자리가 있어도 전력망 연결이 늦어지거나 랙당 전력 한도가 낮으면 계획한 규모로 바로 가동하기 어렵다. [NVIDIA HGX 연결 구성](https://docs.nvidia.com/enterprise-reference-architectures/hgx-ai-factory-h100-h200-b200/latest/components.html) · [IEA 전력망 연결 분석](https://www.iea.org/reports/energy-and-ai/ai-and-energy-security)

랙이 한순간에 끌어 쓰는 전력은 **kW**, 일정 시간 동안 쓴 전기 에너지는 **kWh**로 표시한다. 칩이나 랙의 전력 사양은 설비가 감당해야 할 크기를 가늠하는 데 쓰고, 실제 건물의 사용량을 보려면 냉각 설비까지 포함해 측정한 값이 필요하다. [IEA · 데이터센터 전력 수요](https://www.iea.org/reports/energy-and-ai/energy-demand-from-ai)

## 공시에서 매출의 범위를 찾기

먼저 10-K의 사업 설명에서 어떤 제품을 판매하는지 읽고, 사업부문 표에서 어떤 제품을 묶어 매출을 공시하는지 본다. 두 회사의 회계연도 이름이 같아도 결산일이 다를 수 있어 기간까지 확인한다.

- **NVIDIA**는 2026년 1월 25일 종료 FY2026 공시에서 Compute & Networking 사업부문과 Data Center 시장별 매출을 따로 보여 준다. [NVIDIA 10-K](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm)
- **AMD**는 2025년 12월 27일 종료 FY2025 공시에서 Data Center에 EPYC CPU와 Instinct GPU 등을 포함한다. [AMD 10-K](https://www.sec.gov/Archives/edgar/data/2488/000000248826000018/amd-20251227.htm)
- **브로드컴**은 2025년 11월 2일 종료 FY2025 공시에서 Semiconductor Solutions와 Infrastructure Software를 구분한다. 맞춤형 가속기와 이더넷 제품은 반도체 사업 안의 제품이다. [브로드컴 10-K](https://www.sec.gov/Archives/edgar/data/1730168/000173016825000121/avgo-20251102.htm)
- **인텔**은 2025년 12월 27일 종료 FY2025 공시에서 Xeon이 속한 Data Center and AI와 제조 사업인 Intel Foundry를 구분한다. 파운드리 숫자에는 인텔 내부 사업과의 거래도 들어가므로 연결 조정표를 함께 본다. [인텔 10-K](https://www.sec.gov/Archives/edgar/data/50863/000005086326000011/intc-20251227.htm)
