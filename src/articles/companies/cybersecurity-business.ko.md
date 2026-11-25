---
title: "회사의 노트북·네트워크·계정은 누가 지킬까"
description: "직원이 회사 문서를 여는 장면으로 기기·네트워크·계정 보안을 구분하고, 크라우드스트라이크·팔로알토 네트웍스·시스코의 구독 매출과 계약 지표를 읽는다."
sector: technology
publishedOn: '2026-11-26'
---

재택근무 중인 직원이 회사 노트북으로 문서를 연다고 해보자. 로그인 화면은 직원 본인이 맞는지 확인하고, 네트워크는 업무 서비스와 연결을 허용할지 판단한다. 문서 앱은 직원에게 그 자료를 열 권한이 있는지 본다. 노트북에서는 기기 보안 제품이 이상 동작을 살핀다. 한 파일을 여는 짧은 순간에도 확인하는 대상은 여러 가지다. [NIST 제로트러스트 안내](https://www.nist.gov/news-events/news/2020/08/zero-trust-architecture-nist-publishes-sp-800-207)

<h2 id="defensive-layers">보안 제품은 어디를 지키나</h2>

노트북처럼 회사 서비스에 연결되는 기기를 보안 업계에서는 **엔드포인트**라고 부른다. **네트워크 방화벽**은 어디에서 어디로 데이터가 오갈 수 있는지 규칙을 적용한다. <strong>다중 인증(MFA)</strong>은 로그인할 사람이 맞는지 확인할 때 비밀번호와 보안 키 같은 서로 다른 수단을 함께 쓴다. 확인된 직원이 어떤 문서를 열 수 있는지는 접근 권한에서 정한다. [CIS 인증·접근 권한 설명](https://www.cisecurity.org/insights/blog/why-are-authentication-and-authorization-so-difficult)

<div class="guide-panel">
  <table aria-labelledby="defensive-layers">
    <colgroup><col style="width: 23%"><col></colgroup>
    <thead><tr><th scope="col">지키는 곳</th><th scope="col">맡는 일과 제품 예</th></tr></thead>
    <tbody>
      <tr><th scope="row">기기</th><td>노트북에서 의심스러운 동작을 감지하고 대응을 돕는다. <a href="https://www.crowdstrike.com/en-us/platform/endpoint-security/">크라우드스트라이크 Falcon</a> · <a href="https://www.paloaltonetworks.com/cortex/cortex-xdr">팔로알토 Cortex XDR</a></td></tr>
      <tr><th scope="row">네트워크</th><td>정해진 규칙에 따라 연결을 허용하거나 막는다. <a href="https://www.cisco.com/site/us/en/products/security/firewalls/index.html">시스코 Secure Firewall</a> · <a href="https://www.paloaltonetworks.com/network-security/next-generation-firewall">팔로알토 NGFW</a></td></tr>
      <tr><th scope="row">계정</th><td>로그인하는 사람이 본인인지 여러 수단으로 확인한다. <a href="https://duo.com/about/duo-security-explainer">시스코 Duo</a> · <a href="https://www.okta.com/products/adaptive-multi-factor-authentication/">옥타 Adaptive MFA</a></td></tr>
    </tbody>
  </table>
</div>

국내 **안랩 EDR**도 기기에서 의심스러운 동작이 감지되면 보안 담당자가 기록을 확인하고 대응하도록 돕는다. 팔로알토 네트웍스의 Cortex XDR처럼 기기와 네트워크 등 여러 곳의 신호를 모으는 제품도 있다. 표의 ‘기기’ 행은 이때 공통으로 맡는 기기 보호를 비교한 것이다. [안랩 EDR 안내](https://www.ahnlab.com/ko/contents/cybersecurity-101/what-is-edr) · [Cortex XDR 제품 안내](https://www.paloaltonetworks.com/cortex/cortex-xdr)

## 왜 보안을 구독으로 사나

방화벽을 들여놓은 뒤에도 새 위협 정보와 소프트웨어 업데이트가 필요하다. 장비나 라이선스와 함께 기술 지원을 기간제로 사는 이유다. 팔로알토 네트웍스의 예에서 장비와 지원을 3년 계약으로 함께 사면, 장비에 배정된 매출은 장비를 출하할 때 잡고 지원에 배정된 매출은 지원을 제공하는 동안 나눠 잡는다. [팔로알토 네트웍스 2026년 7월 결산 10-K, 사업 설명과 매출 인식](https://www.sec.gov/Archives/edgar/data/1327567/000132756726000023/panw-20260731.htm)

<h2 id="security-metrics">매출, ARR, RPO가 각각 말해 주는 것</h2>

<div class="guide-panel">
  <table aria-labelledby="security-metrics">
    <colgroup><col style="width: 29%"><col></colgroup>
    <thead><tr><th scope="col">공시에서 보이는 말</th><th scope="col">어느 시점의 무엇을 보나</th></tr></thead>
    <tbody>
      <tr><th scope="row">매출</th><td>지난 분기나 올해처럼 정해진 기간에 인식한 금액.</td></tr>
      <tr><th scope="row">ARR</th><td>특정 날짜의 구독 계약 규모를 1년치로 환산한 운영 지표. 계약 갱신을 어떻게 가정하는지 회사 설명을 본다.</td></tr>
      <tr><th scope="row">RPO</th><td>이미 맺은 계약에서 앞으로 제품이나 서비스를 제공해야 할 부분에 배정한 금액.</td></tr>
    </tbody>
  </table>
</div>

- **크라우드스트라이크**는 손익계산서에 구독과 전문 서비스 매출을 따로 표시한다. ARR을 계산할 때 향후 12개월 안에 끝나는 계약은 기존 조건으로 갱신된다고 가정한다. [2026년 1월 결산 10-K, 실적 설명과 연결 손익계산서](https://www.sec.gov/Archives/edgar/data/1535527/000153552726000010/crwd-20260131.htm)
- **팔로알토 네트웍스**는 RPO 중 향후 12개월에 매출로 인식할 것으로 예상하는 부분을 따로 보여 준다. 연결 손익계산서에는 구독과 지원이 한 줄에 함께 들어간다. [2026년 7월 결산 10-K, 연결 손익계산서 및 재무제표 주석 2](https://www.sec.gov/Archives/edgar/data/1327567/000132756726000023/panw-20260731.htm)
- **시스코**의 ‘Security’ 제품 매출에는 네트워크 보안, 신원 확인과 접근 관리, 클라우드 기반 접속 보안 등이 함께 들어간다. 앞의 표에서 본 방화벽과 Duo가 속하는 범위를 이 항목으로 확인할 수 있다. [2026년 7월 결산 10-K, 제품별 실적 설명](https://www.sec.gov/Archives/edgar/data/858877/000085887726000132/csco-20260725.htm)
