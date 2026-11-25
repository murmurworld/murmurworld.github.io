---
title: "What Cloud and Subscription Software Providers Sell"
description: "Follow an online shop to see what IaaS, PaaS, and SaaS providers manage and bill for. Then check what Amazon, Microsoft, Alphabet, Oracle, and Palantir count as cloud revenue."
sector: technology
publishedOn: '2026-11-26'
---

Imagine a small shop putting its orders online. It needs a computer to run the site and somewhere to keep orders and stock records. The staff might also share their rota through a separate email and document suite. The shop can reach all three services over the internet. It hands a different job to each provider.

## What does the shop manage itself?

A server you buy needs a place to sit, power and a network connection. A cloud provider lets you use computing power and storage in its data centres as needed. Renting a virtual computer this way is **infrastructure as a service (IaaS)**. The provider maintains the equipment and the shop manages the virtual machine’s operating system and order app. The shop can add capacity when orders surge, while a steady workload gives it reason to compare usage terms and longer commitments. [NIST definition of cloud computing](https://csrc.nist.gov/pubs/sp/800/145/final)

With **platform as a service (PaaS)**, the shop can hand over the job of running its code. It uploads its order app to Azure App Service and Microsoft operates the environment the code runs in. The shop still decides how orders are accepted and processed through the code and app settings. [Microsoft Learn, an App Service web app architecture](https://learn.microsoft.com/en-us/azure/architecture/web-apps/app-service/architectures/basic-web-app)

**Software as a service (SaaS)** gives you a finished app. When staff share documents in Microsoft 365 or Google Workspace, the provider runs the app and the shop manages staff accounts and document access. [NIST definition of SaaS](https://csrc.nist.gov/glossary/term/software_as_a_service)

<h2 id="cloud-services">Compare Services That Do the Same Job</h2>

<div class="guide-panel">
  <table aria-labelledby="cloud-services">
    <colgroup><col style="width: 29%"><col></colgroup>
    <thead><tr><th scope="col">The shop needs to</th><th scope="col">Service examples and who manages what</th></tr></thead>
    <tbody>
      <tr><th scope="row">Run an app on a server</th><td><strong>Amazon EC2 · Azure Virtual Machines</strong><br>The provider looks after the equipment. The shop manages the operating system and app.</td></tr>
      <tr><th scope="row">Deploy the app’s code</th><td><strong>Azure App Service · <a href="https://www.heroku.com/blog/simplifying-jvm-app-development-herokus-buildpack-magic/">Heroku</a></strong><br>The provider runs the environment. The shop manages the code and app settings.</td></tr>
      <tr><th scope="row">Store order records</th><td><strong><a href="https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/CHAP_PostgreSQL.html">Amazon RDS for PostgreSQL</a> · <a href="https://learn.microsoft.com/en-us/azure/postgresql/overview">Azure Database for PostgreSQL</a></strong><br>Both offer the same database engine. The provider handles tasks like backups and patching. The shop manages its data and access.</td></tr>
      <tr><th scope="row">Share documents and email</th><td><strong>Microsoft 365 · Google Workspace</strong><br>The provider runs the finished app. The shop sets up accounts and sharing permissions.</td></tr>
    </tbody>
  </table>
</div>

The Korean provider NHN Cloud offers managed PostgreSQL. Customers set the backup schedule and retention period, while the provider stores the backups and charges based on how much space they use. The retention setting tells the shop how far back it may be able to recover its order records. [NHN Cloud PostgreSQL user guide in Korean](https://docs.nhncloud.com/ko/Database/RDS%20for%20PostgreSQL/ko/db-instance/)

<h2 id="cloud-billing">What does the bill count?</h2>

<div class="guide-panel">
  <table aria-labelledby="cloud-billing">
    <colgroup><col style="width: 29%"><col></colgroup>
    <thead><tr><th scope="col">Service</th><th scope="col">Examples of billing units</th></tr></thead>
    <tbody>
      <tr><th scope="row">Virtual server</th><td><a href="https://aws.amazon.com/ec2/pricing/on-demand/">EC2 On-Demand</a> measures how long the instance runs.</td></tr>
      <tr><th scope="row">App runtime</th><td>On <a href="https://learn.microsoft.com/en-us/azure/app-service/overview-hosting-plans">Azure App Service</a> dedicated compute plans, the number of allocated instances matters.</td></tr>
      <tr><th scope="row">Database backup</th><td>NHN Cloud PostgreSQL counts the storage used by the backup.</td></tr>
      <tr><th scope="row">Subscription app</th><td>A collaboration app can count <a href="https://stripe.com/au/resources/more/saas-pricing-and-packaging-strategy">paid seats</a>. Another app can charge for feature usage.</td></tr>
    </tbody>
  </table>
</div>

## What can the shop do with its order records?

A database can tell you whether one order was paid. A **data analytics platform** can combine records to answer a broader question. Joining orders and stock records can show which products often ship late and give a team a list to work through. A company can run a database in Oracle Cloud and use Palantir Foundry to bring data from several systems into an operational workflow. [Oracle May 2026 10-K, Business](https://www.sec.gov/Archives/edgar/data/1341439/000119312526277521/orcl-20260531.htm) · [Palantir December 2025 10-K, Business](https://www.sec.gov/Archives/edgar/data/1321655/000132165526000011/pltr-20251231.htm)

## What Companies Count as Cloud Revenue

Companies can rent out similar virtual servers and still group different businesses under the same word in a filing. Start with what each product does, then look in the financial statement notes for what else goes into its revenue category.

- **Amazon** reports AWS as a segment. It spans computing, storage, databases and other services, so the AWS total covers more than EC2. [December 2025 10-K, financial statement Note 10](https://www.sec.gov/Archives/edgar/data/1018724/000101872426000004/amzn-20251231.htm)
- **Microsoft** grouped Azure with server products and cloud services in its June 2026 annual filing. Its broader Microsoft Cloud measure also includes offerings such as Microsoft 365 Commercial cloud and Dynamics 365. [June 2026 10-K, financial statement Note 18](https://www.sec.gov/Archives/edgar/data/789019/000119312526323660/msft-20260630.htm)
- **Alphabet** includes both Google Cloud Platform, which sells infrastructure and data services, and Google Workspace, which offers tools such as documents and email, in Google Cloud. [December 2025 10-K, Business and financial statement Note 15](https://www.sec.gov/Archives/edgar/data/1652044/000165204426000018/goog-20251231.htm)
- **Oracle** reports cloud, software licensing and support within its cloud and software segment. Its results discussion breaks out cloud infrastructure and cloud applications. [May 2026 10-K, results and financial statement Note 13](https://www.sec.gov/Archives/edgar/data/1341439/000119312526277521/orcl-20260531.htm)
- **Palantir** describes products such as Foundry and Gotham in its business overview. The financial statement note divides revenue by government and commercial customers. [December 2025 10-K, Business and financial statement Note 13](https://www.sec.gov/Archives/edgar/data/1321655/000132165526000011/pltr-20251231.htm)

To read two cloud disclosures side by side, check when each fiscal year ends and which server services and finished apps are included in each line.
