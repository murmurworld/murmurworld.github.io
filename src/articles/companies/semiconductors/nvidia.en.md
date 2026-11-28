---
title: "NVIDIA"
description: "NVIDIA sells GPUs for training and running AI models, together with the networking needed to connect many accelerators. It also sells graphics products for games."
study:
  question: Does adding GPUs make an AI server proportionately faster?
  answer: When several GPUs share a model, they spend time exchanging intermediate results. NVIDIA supplies NVLink interconnects and switches alongside the processors to reduce the time those chips spend waiting for data.
  source: https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm
---

NVIDIA sells GPUs for training and running AI models, together with the networking needed to connect many accelerators. It also sells graphics products for games.

| Basic information | Details |
| --- | --- |
| Principal office | Santa Clara, CA |
| Operations | Chip architecture and platform design; outside foundry, assembly and test partners |
| Listing and symbol | Nasdaq · NVDA |
| Reported business lines | Compute and Networking · Graphics |
| Annual reporting date | 2026-01-25 |
| Annual consolidated revenue | 2026-01-25 · 215.938 USD billion |
| Fiscal year-to-date consolidated revenue | 2026-01-26 – 2026-10-25 · 293.681 USD billion |
| Shares issued | 24,304,000,000 · 2026-01-25 · [Filing](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm) |
| Shares outstanding | 24,100,000,000 · 2026-08-21 · [Filing](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000075/nvda-20260726.htm) |
| Filing | [10-K](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm) |

## What it sells

| Product or service | Use and users |
| --- | --- |
| Data center GPUs and systems | Blackwell and Rubin combine accelerators, CPUs and interconnects into systems. A GPU performs many arithmetic operations in parallel during model training or inference. |
| Networking | Switches, network adapters and interconnects let a cluster of accelerator servers exchange data. Bandwidth between machines can constrain a workload even when the GPU itself is fast. |
| CUDA and AI software | CUDA gives developers libraries and tools to write programs for the GPUs. Enterprise software supports building, deploying and maintaining applications. |
| GeForce and professional graphics | GeForce serves gaming PCs. Professional graphics products serve workstation users who render scenes, simulate objects or run visual applications. NVIDIA also sells automotive and embedded computing platforms. |

| Reporting period | Company operating update |
| --- | --- |
| FY2027 Q3 | Data Center generated USD 107.6 billion, about 93% of revenue. [Company results or filing](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000088/q3fy27pr.htm) |

<h3 id="memory-suppliers">Who makes the memory in an NVIDIA GPU?</h3>

NVIDIA names Samsung Electronics, SK hynix and Micron as memory suppliers in its annual filing. To match one of them to a particular GPU, look for the board version and what the supplier actually disclosed. A production announcement and a photograph of an assembled board answer different questions. [NVIDIA annual filing, manufacturing and supply](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm)

| NVIDIA product | Memory and supplier | What the companies disclosed |
| --- | --- | --- |
| H100 SXM | SK hynix HBM3 | SK hynix announced volume production for the H100. NVIDIA lists 80 GB of memory per H100 SXM GPU. [SK hynix announcement](https://news.skhynix.com/en/sk-hynix-to-supply-industrys-first-hbm3-dram-to-nvidia/) |
| H200 SXM | Micron HBM3E | Micron’s eight-high stack for the H200 holds 24 GB. NVIDIA specifies 141 GB of memory per H200 SXM GPU. [Micron announcement](https://investors.micron.com/news/press-release/2024/Micron-Commences-Volume-Production-of-Industry-Leading-HBM3E-Solution-to-Accelerate-the-Growth-of-AI-02-26-2024/default.aspx) · [NVIDIA SXM specifications](https://docs.nvidia.com/enterprise-reference-architectures/hgx-ai-factory-h100-h200-b200/latest/components.html) |
| Vera Rubin | Samsung Electronics HBM4 | Samsung said it was mass-producing HBM4 designed for the Rubin platform. It displayed the next generation, HBM4E, at the same event. [Samsung at GTC](https://news.samsung.com/global/samsung-unveils-hbm4e-showcasing-comprehensive-ai-solutions-nvidia-partnership-and-vision-at-nvidia-gtc-2026) |
| Vera Rubin | SK hynix HBM4 and SOCAMM2 | On the board SK hynix exhibited, its 12-high, 36 GB HBM4 sat next to the Rubin GPU. Its 96 GB SOCAMM2 module served the Vera CPU. [Photograph and component identification](https://news.skhynix.com/en/tsmc-oip-conference-2026/) |
| Vera Rubin | Micron HBM4 | Micron reported volume shipments of its 12-high, 36 GB stack designed for Rubin in the first quarter of 2026. [Micron shipment announcement](https://investors.micron.com/news/press-release/2026/Micron-in-High-Volume-Production-of-HBM4-Designed-for-NVIDIA-Vera-Rubin-PCIe-Gen6-SSD-and-SOCAMM2-03-16-2026/default.aspx) |
| GeForce RTX 3090 | Micron GDDR6X | This gaming GPU reads graphics data such as textures from GDDR6X. The 24 GB specification is the total graphics memory on one card. [Supplier announcement and card specifications](/en/stocks/?company=NVDA&case=micron-geforce-gddr6x#case-micron-geforce-gddr6x) |

Follow the connections from memory to the server board. In TSMC’s CoWoS-S packaging, a silicon interposer carries dense wiring between GPU and HBM. Beneath it, the package substrate carries connections out to the board. Samsung Electro-Mechanics announced a contract for package substrates; Samsung Electronics makes HBM that holds the data. The substrate announcement does not name the H200. [TSMC packaging cross-section](https://3dfabric.tsmc.com/english/dedicatedFoundry/technology/cowos.htm) · [Samsung Electro-Mechanics agreement](https://www.samsungsem.com/global/newsroom/news/view.do?id=10614)

## Who buys it

Cloud operators, server manufacturers, enterprise buyers and PC graphics partners use different parts of the platform.

Three direct customers accounted for 16%, 15% and 13% of first-half FY2027 revenue. The filing leaves their identities undisclosed. [10-Q](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000075/nvda-20260726.htm)

### Revenue by geography

| USD billion | 2024-01-28 | 2025-01-26 | 2026-01-25 |
| --- | --- | --- | --- |
| US | 31.533 | 77.482 | 149.617 |
| TW | 14.912 | 23.6 | 42.345 |
| China Including Hong Kong | 12.33 | 25.048 | 19.677 |
| Other Countries | 2.147 | 4.367 | 4.299 |

[10-K](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm)

## The numbers

### Annual consolidated results

| USD billion | 2024-01-28 | 2025-01-26 | 2026-01-25 |
| --- | --- | --- | --- |
| Revenue | 60.922 | 130.497 | 215.938 |
| Operating income | 32.972 | 81.453 | 130.387 |
| Operating margin (calculated) | 54.1% | 62.4% | 60.4% |
| Net income attributable to the parent | 29.76 | 72.88 | 120.067 |

### Reported business lines

| USD billion | 2024-01-28 | 2025-01-26 | 2026-01-25 |
| --- | --- | --- | --- |
| Compute and Networking | 47.405 | 116.193 | 193.479 |
| Graphics | 13.517 | 14.304 | 22.459 |

### Products and services

| USD billion | 2024-01-28 | 2025-01-26 | 2026-01-25 |
| --- | --- | --- | --- |
| Data Center | 47.525 | 115.186 | 193.737 |
| Compute | 38.95 | 102.196 | 162.361 |
| Networking | 8.575 | 12.99 | 31.376 |
| Gaming | 10.447 | 11.35 | 16.042 |
| Professional Visualization | 1.553 | 1.878 | 3.191 |
| Automotive | 1.091 | 1.694 | 2.349 |
| OEM and Other | 0.306 | 0.389 | 0.619 |

### Consolidated results for individual quarters

| USD billion | 2025-04-27 | 2025-07-27 | 2025-10-26 | 2026-01-25 | 2026-04-26 | 2026-07-26 | 2026-10-25 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Revenue | 44.062 | 46.743 | 57.006 | 68.127* | 81.615 | 96.221 | 115.844 |
| Operating income | 21.638 | 28.44 | 36.01 | 44.299* | 53.536 | 63.734 | 77.52 |
| Operating margin (calculated) | 49.1% | 60.8% | 63.2% | 65.0% | 65.6% | 66.2% | 66.9% |
| Net income attributable to the parent | 18.775 | 26.422 | 31.91 | 42.96* | 58.321 | 59.688 | 65.287 |

\* A marked quarter was calculated by subtracting the earlier cumulative amount.

### Annual consolidated cash flow

| USD billion | 2024-01-28 | 2025-01-26 | 2026-01-25 |
| --- | --- | --- | --- |
| Cash from operations | 28.09 | 64.089 | 102.718 |
| Capital expenditure | 1.069 | 3.236 | 6.042 |
| Share repurchases | 9.533 | 33.706 | 40.086 |
| Cash dividends | 0.395 | 0.834 | 0.974 |

### Consolidated year-to-date comparison

| USD billion | 2025-01-27 – 2025-10-26 | 2026-01-26 – 2026-10-25 |
| --- | --- | --- |
| Revenue | 147.811 | 293.681 |
| Operating income | 86.088 | 194.791 |
| Net income attributable to the parent | 77.107 | 183.297 |
| Cash from operations | 66.53 | 122.675 |
| Capital expenditure | 4.758 | 8.856 |
| Share repurchases | 36.271 | 61.166 |
| Cash dividends | 0.732 | 12.316 |

## Its place in the sector

NVIDIA, AMD and Qualcomm outsource wafer production. Broadcom relies principally on external foundries but also operates some manufacturing facilities.

Companies in this group · [AMD](/en/blog/companies/semiconductors/amd/) · [Broadcom](/en/blog/companies/semiconductors/broadcom/) · [Qualcomm](/en/blog/companies/semiconductors/qualcomm/)

Buyer NVIDIA · Supplier TSMC and Samsung. Manufacturing semiconductor wafers [NVIDIA FY2026 10-K](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm)

Buyer NVIDIA · Supplier SK hynix, Micron and Samsung. Memory purchases. NVIDIA identifies its suppliers without assigning a volume to each. [NVIDIA FY2026 10-K](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm)

Data-center accelerators · NVIDIA, AMD and Intel. NVIDIA also names cloud operators designing their own chips.. [NVIDIA FY2026 10-K](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm)

## Where to look in the filing

- **10-K, Item 1** · Business and customers
- **Item 7** · Management’s explanation of changes in results
- **Item 8** · Consolidated statements and segment notes
- **10-Q** · Compare the start and end dates to distinguish a quarter from fiscal year to date

Subtotals may include the product lines below them. The same sales can appear by segment, product and region.

## Sources

- [10-K](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm) · 2026-02-25
- [10-Q](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000075/nvda-20260726.htm) · 2026-08-26
- [Interim results](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000088/q3fy27pr.htm) · 2026-11-17
- [Filing cover](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000073/nvda-20260826.htm)
- [10-K](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/0001045810-26-000021-index.htm) · 2026-02-25
- [10-Q](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000052/0001045810-26-000052-index.htm) · 2026-05-20
- [10-Q](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000075/0001045810-26-000075-index.htm) · 2026-08-26
- [10-Q](https://www.sec.gov/Archives/edgar/data/1045810/000104581025000230/0001045810-25-000230-index.htm) · 2025-11-19
- [SEC company facts (XBRL)](https://data.sec.gov/api/xbrl/companyfacts/CIK0001045810.json)

Original sources checked November 26, 2026 · [1](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm) · [2](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000075/nvda-20260726.htm) · [3](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000088/q3fy27pr.htm)
