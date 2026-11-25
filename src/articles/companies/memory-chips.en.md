---
title: "DRAM, NAND and HBM: What Each Kind of Memory Does"
description: "From the RAM in a phone to the HBM beside an AI accelerator, learn what each kind of memory does, who makes it and what Samsung discloses about its memory business."
sector: semiconductors
publishedOn: '2026-11-26'
order: 1
video:
  id: '4MMfKTRZ_Mg'
  title: 'HBM, 그게 뭔데?'
  channel: 'Samsung Semiconductor Newsroom'
  start: 149
  end: 291
  label: 'Korean · 2:29–4:51'
  context: 'See the layers of DRAM and the tiny electrical paths that run through the silicon to connect them.'
---

A phone might list `12 GB RAM` and `256 GB storage` on the same spec sheet. They measure space for two different jobs. Apps need room to run, and your photos need somewhere to stay. An AI server also uses separate places to hold files and keep data available while it calculates.

## RAM for running an app, NAND for keeping a photo

When you open an app, the phone takes the data it needs from storage and loads it into **RAM**. The data you are editing sits in working memory. Once you save, the file lives in storage. A phone’s RAM is typically low-power DRAM, or LPDDR. Its built-in storage usually uses NAND flash. That is where the photo stays when you turn the phone off. [Samsung’s DRAM product families](https://semiconductor.samsung.com/dram/) · [Samsung’s SSD technical guide](https://download.semiconductor.samsung.com/resources/white-paper/Samsung_SSD_White_Paper.pdf)

| Name | What it does | Where you see it |
| --- | --- | --- |
| DRAM | Holds working data while power is on | LPDDR in phones, DDR in PCs and servers, HBM in accelerators |
| NAND | Keeps files after power is turned off | Built-in phone storage and SSDs |
| HBM | Uses stacked DRAM to move many bytes to a processor at once | Some AI and high-performance computing accelerators |

An **SSD** combines NAND with a controller that manages reading and writing. An **HDD** records data on spinning magnetic disks. A system can use SSDs where fast access matters and HDDs where it needs to store a lot of data. **NOR flash** has a different job again: it often stores small pieces of code a device reads as it starts. [Samsung SSD technical guide](https://download.semiconductor.samsung.com/resources/white-paper/Samsung_SSD_White_Paper.pdf) · [Seagate FY2026 10-K](https://www.sec.gov/Archives/edgar/data/1137789/000113778926000159/stx-20260703.htm) · [Micron’s NOR product family](https://www.micron.com/products/storage/nor-flash)

An “NVMe SSD” label describes a particular drive. **NAND** is where the data is stored. The **SSD** is the whole drive. **NVMe** is the interface standard the computer can use to send commands to it. [SNIA · SSDs and storage interfaces](https://www.snia.org/education/what-is-ssd)

## Why put HBM beside the processor?

An AI accelerator needs a steady supply of data as it runs calculations. HBM stacks several DRAM dies vertically and connects them through electrical paths between the layers. It sits beside the compute die in the same package. A wide connection lets a large amount of data move at once. **Capacity (GB)** tells you how much data you can hold. **Bandwidth (GB/s)** tells you how much can move every second. Look for the “/s” on a spec sheet. Replacing an SSD with a larger one leaves the bandwidth between the HBM and the compute die unchanged. [SK hynix’s HBM technology note](https://news.skhynix.com/en/tech-note-series-ep2/) · [TSMC 2025 Annual Report, CoWoS](https://investor.tsmc.com/sites/ir/annual-report/2025/2025%20TSMC%20Annual%20Report.E.pdf#page=52)

<figure class="guide-panel product-flow" aria-label="An example of how a server stores a file and reads some of its contents for computation">
  <ol>
    <li><strong>SSD</strong><span>Store the model file</span></li>
    <li><strong>System DRAM</strong><span>Prepare data to use</span></li>
    <li><strong>HBM ↔ compute die</strong><span>Read and calculate</span></li>
  </ol>
  <figcaption>One simplified path. The real path depends on the server and software.</figcaption>
</figure>

## Who sells the memory, and who puts it together?

Samsung, SK hynix and Micron sell DRAM and NAND and also make HBM. Accelerator makers comparing HBM from the same generation still care about capacity, bandwidth, heat and package compatibility. Sandisk focuses on NAND-based storage, while Seagate makes large-capacity hard drives. Their products can overlap in file storage. TSMC’s CoWoS technology connects the compute die and HBM in a package, a separate role from producing the memory itself. [Micron FY2026 10-K](https://www.sec.gov/Archives/edgar/data/723125/000072312526000023/mu-20260903.htm) · [Sandisk 10-Q for the quarter ended October 2026](https://www.sec.gov/Archives/edgar/data/2023554/000162828026068601/sndk-20261002.htm) · [Seagate FY2026 10-K](https://www.sec.gov/Archives/edgar/data/1137789/000113778926000159/stx-20260703.htm) · [TSMC 2025 Annual Report](https://investor.tsmc.com/static/annualReports/2025/english/index.html)

Demand and supply appear together in memory filings. Building capacity and getting it into production takes time, even when orders surge. By the time a plant expansion is ready, customers might be ordering less. Read `Memory and Storage Demand` alongside `Manufacturing` in Micron’s annual report to see how the company describes the gap between the two. [Micron FY2026 10-K](https://www.sec.gov/Archives/edgar/data/723125/000072312526000023/mu-20260903.htm)

## Looking for HBM in a Samsung filing

In Samsung’s Q3 2026 interim report, open **Business → Major Products and Services** to find DRAM and NAND flash. The **segment information** note to the consolidated financial statements shows Device Solutions revenue and a separate line for the Memory product category. HBM has no separate sales line in that table. Finding HBM in the business description doesn’t tell you how much of the Memory line came from it. The note also shows both the quarter and the January–September period, so check which period you are comparing before you read the numbers. [Samsung Q3 2026 interim report in Korean](https://images.samsung.com/kdp/ir/business-report/2026_3Q_Interim_Business_Report_kr.pdf#page=7) · [Q3 2026 consolidated financial statements in Korean](https://images.samsung.com/kdp/ir/financial-info/2026/2026_con_quarter03_all.pdf) · [Q3 2026 earnings in English](https://news.samsung.com/global/samsung-electronics-announces-third-quarter-2026-results)
