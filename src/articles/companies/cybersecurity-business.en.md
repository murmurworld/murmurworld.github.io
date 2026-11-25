---
title: "Who protects the company laptop, network, and account?"
description: "Follow an employee opening a work document to see what device, network, and account products do, and how CrowdStrike, Palo Alto Networks, and Cisco report revenue and contracts."
sector: technology
publishedOn: '2026-11-26'
---

Imagine an employee at home opening a company document on a work laptop. The sign-in screen checks who they are. Network controls decide whether to allow a connection to the work service. The document app checks whether the employee can open that file. On the laptop, device security watches for unusual activity. Even a single document can involve several different checks. [NIST introduction to zero trust](https://www.nist.gov/news-events/news/2020/08/zero-trust-architecture-nist-publishes-sp-800-207)

<h2 id="defensive-layers">What does each security product protect?</h2>

A device such as a laptop that connects to a company service is an **endpoint**. A **network firewall** applies rules to the connections that carry data. **Multifactor authentication (MFA)** checks who is signing in using different kinds of evidence, such as a password and a security key. Access permissions determine which files that verified employee can open. [CIS guide to authentication and authorization](https://www.cisecurity.org/insights/blog/why-are-authentication-and-authorization-so-difficult)

<div class="guide-panel">
  <table aria-labelledby="defensive-layers">
    <colgroup><col style="width: 23%"><col></colgroup>
    <thead><tr><th scope="col">Area</th><th scope="col">Job and product examples</th></tr></thead>
    <tbody>
      <tr><th scope="row">Device</th><td>Detect suspicious activity on a laptop and help the team respond. <a href="https://www.crowdstrike.com/en-us/platform/endpoint-security/">CrowdStrike Falcon</a> · <a href="https://www.paloaltonetworks.com/cortex/cortex-xdr">Palo Alto Cortex XDR</a></td></tr>
      <tr><th scope="row">Network</th><td>Allow or block connections according to rules. <a href="https://www.cisco.com/site/us/en/products/security/firewalls/index.html">Cisco Secure Firewall</a> · <a href="https://www.paloaltonetworks.com/network-security/next-generation-firewall">Palo Alto NGFW</a></td></tr>
      <tr><th scope="row">Account</th><td>Use multiple checks to verify the person signing in. <a href="https://duo.com/about/duo-security-explainer">Cisco Duo</a> · <a href="https://www.okta.com/products/adaptive-multi-factor-authentication/">Okta Adaptive MFA</a></td></tr>
    </tbody>
  </table>
</div>

South Korea’s **AhnLab EDR** also gives security teams a record to review and act on when it detects suspicious device activity. A product such as Palo Alto Networks’ Cortex XDR can draw on signals from devices, networks and other sources. The device row compares the endpoint protection capabilities the products have in common. [AhnLab EDR guide in Korean](https://www.ahnlab.com/ko/contents/cybersecurity-101/what-is-edr) · [Cortex XDR product overview](https://www.paloaltonetworks.com/cortex/cortex-xdr)

## Why pay for security by subscription?

After installing a firewall, a company still needs fresh threat information and software updates. It may buy ongoing technical support with the hardware or software license. In the case of Palo Alto Networks, if a buyer purchases hardware and three years of support in one contract, the hardware portion is counted as revenue when the equipment ships. The support portion is counted as the service is provided. [Palo Alto Networks Form 10-K for the year ended July 2026, business and revenue recognition](https://www.sec.gov/Archives/edgar/data/1327567/000132756726000023/panw-20260731.htm)

<h2 id="security-metrics">What revenue, ARR and RPO tell you</h2>

<div class="guide-panel">
  <table aria-labelledby="security-metrics">
    <colgroup><col style="width: 29%"><col></colgroup>
    <thead><tr><th scope="col">Metric</th><th scope="col">What it measures</th></tr></thead>
    <tbody>
      <tr><th scope="row">Revenue</th><td>The amount recognized in a period such as a quarter or fiscal year.</td></tr>
      <tr><th scope="row">ARR</th><td>The value of subscription contracts at a given date expressed on a yearly basis. Check how the company treats renewals.</td></tr>
      <tr><th scope="row">RPO</th><td>The amount allocated to products or services still owed under signed contracts.</td></tr>
    </tbody>
  </table>
</div>

- **CrowdStrike** lists subscription and professional services revenue separately in its income statement. Its ARR calculation assumes that contracts due to expire in the next 12 months renew on their existing terms. [Form 10-K for the year ended January 2026, operating review and consolidated statement of operations](https://www.sec.gov/Archives/edgar/data/1535527/000153552726000010/crwd-20260131.htm)
- **Palo Alto Networks** reports how much of its remaining contracted work it expects to recognize as revenue over the next 12 months. Its consolidated income statement puts subscription and support revenue on one line. [Form 10-K for the year ended July 2026, consolidated statement of operations and Note 2](https://www.sec.gov/Archives/edgar/data/1327567/000132756726000023/panw-20260731.htm)
- **Cisco’s** Security product revenue covers several offerings, including network security, identity and access management, and cloud-delivered access security. This is the broader category that includes the firewall and Duo examples. [Form 10-K for the year ended July 2026, results by product category](https://www.sec.gov/Archives/edgar/data/858877/000085887726000132/csco-20260725.htm)
