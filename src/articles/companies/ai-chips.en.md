---
title: 'What Do AI Chips Do? CPUs, GPUs, and Custom Accelerators'
description: 'See what CPUs, GPUs, custom accelerators, and networks do for AI training and inference, then compare products and company filings.'
sector: semiconductors
publishedOn: '2026-11-26'
order: 2
video:
  id: eATdZCyw430
  title: 'What is a TPU?'
  channel: Google
  label: 'English'
  context: 'Google uses its own TPU to explain how a chip designed for machine learning differs from a general-purpose CPU.'
---

When you ask a chatbot a question, a server receives the request and assigns work to the hardware. The model runs calculations to produce an answer. If several devices share the job, they exchange intermediate results along the way. Each step gives a data center operator a different reason to buy hardware.

<figure class="guide-panel product-flow" aria-label="One question on its way to an answer">
  <ol>
    <li><strong>Receive</strong><span>The CPU runs the service and dispatches the request</span></li>
    <li><strong>Start the reply</strong><span>The accelerator processes the input and produces the first token</span></li>
    <li><strong>Keep going</strong><span>The accelerator generates more tokens in sequence</span></li>
  </ol>
  <figcaption>Tokens are the pieces of text a model reads and writes. The wait before an answer begins and the speed of the words that follow measure different things.</figcaption>
</figure>

## Training builds a model. Inference uses it.

**Training** adjusts a model’s internal values, called weights, based on data. **Inference** uses trained weights to classify a new input or generate an answer. For training, buyers look at time to train under defined conditions and how efficiently the job scales across devices. For inference, they care about time to the first response, throughput under load, and cost per answer. The same accelerator can serve both workloads. [NVIDIA reference architecture](https://docs.nvidia.com/enterprise-reference-architectures/white-paper/latest/reference-architectures-deep-dive.html) · [Google Cloud inference documentation](https://docs.cloud.google.com/tpu/docs/tpu-inference)

## Where CPUs, GPUs, and custom chips fit

- **CPUs** run the operating system and service code and coordinate requests, data, and devices. Intel Xeon and AMD EPYC are server CPUs a buyer could compare for that job.
- **GPUs** are suited to running many calculations in parallel. NVIDIA data center GPUs and AMD Instinct accelerate training and inference. A buyer also checks whether the intended model and software tools run on the platform.
- **Custom accelerators** are designed for particular calculations. Google’s TPU is one example built for machine learning. In its filing, Broadcom calls its custom accelerator products XPUs and also lists Ethernet switch chips for data centers. One product performs computations and the other moves data between devices. [Google Cloud TPU documentation](https://docs.cloud.google.com/tpu/docs/intro-to-tpu) · [Broadcom FY2025 filing](https://www.sec.gov/Archives/edgar/data/1730168/000173016825000121/avgo-20251102.htm)

A research team can buy servers for its own site or rent computing capacity. AWS EC2’s P6 family offers instances with NVIDIA GPUs. Google Cloud offers access to TPUs. Hardware manufacturers and cloud providers earn revenue at different points. A cloud customer pays for access to usable computing resources and the environment to run a model. [AWS EC2 P6](https://aws.amazon.com/ec2/instance-types/p6/) · [Google Cloud TPU](https://cloud.google.com/tpu)

## Compare eight GPUs under the same conditions

NVIDIA HGX B200 and the AMD Instinct MI355X platform each connect eight GPUs, giving you a comparable starting configuration. Check whether published memory capacity refers to one GPU or the whole baseboard. When a manufacturer claims a speedup, look for the model, numerical precision, number of simultaneous requests, and input and output lengths used in the test. For inference, compare throughput at the same response-time target. Product documentation establishes the hardware configuration. A performance comparison needs test results with matching conditions. [NVIDIA HGX B200 configuration](https://docs.nvidia.com/enterprise-reference-architectures/hgx-ai-factory-h100-h200-b200/latest/components.html) · [AMD MI355X platform configuration](https://www.amd.com/en/products/accelerators/instinct/mi350/mi355x/platform.html)

| What you are comparing | What to match in the test |
| --- | --- |
| Time until an answer starts | Model, input length and simultaneous requests |
| Throughput during a rush | Same response-time target and number of GPUs |
| Space for a model | Memory per GPU versus memory for the whole system |

When reading MLPerf’s data center inference results, start with entries in the same test category and latency conditions. [MLCommons inference benchmark](https://mlcommons.org/benchmarks/inference-datacenter/)

## More servers need more connections and power

When GPUs share a job, the speed of exchanging results matters as well as the speed of computation. Buyers check links between GPUs inside a server and the network that carries traffic across servers. They also check how much electricity each rack can draw and whether the facility can remove the heat it produces. A room can have space for more equipment while a delayed grid connection or a rack power limit restricts what the operator can run. [NVIDIA HGX network configuration](https://docs.nvidia.com/enterprise-reference-architectures/hgx-ai-factory-h100-h200-b200/latest/components.html) · [IEA analysis of grid connections](https://www.iea.org/reports/energy-and-ai/ai-and-energy-security)

**kW** measures the power a rack draws at a given moment. **kWh** measures the energy used over time. A rack’s power rating helps an operator size its infrastructure. To know the actual energy used by the building, the operator also needs measurements that include cooling. [IEA · Energy demand from AI](https://www.iea.org/reports/energy-and-ai/energy-demand-from-ai)

## Read what each company groups together

Start with the business description in the 10-K. Then check the segment tables to see which products are grouped as revenue. Look at the fiscal year-end date as well as its label.

- **NVIDIA** reports a Compute & Networking segment and a separate Data Center market view in its FY2026 filing, for the year ended January 25, 2026. [NVIDIA 10-K](https://www.sec.gov/Archives/edgar/data/1045810/000104581026000021/nvda-20260125.htm)
- **AMD** includes EPYC CPUs and Instinct GPUs in Data Center in its FY2025 filing, for the year ended December 27, 2025. [AMD 10-K](https://www.sec.gov/Archives/edgar/data/2488/000000248826000018/amd-20251227.htm)
- **Broadcom** separates Semiconductor Solutions and Infrastructure Software in its FY2025 filing, for the year ended November 2, 2025. Custom accelerators and Ethernet products fall under the semiconductor business. [Broadcom 10-K](https://www.sec.gov/Archives/edgar/data/1730168/000173016825000121/avgo-20251102.htm)
- **Intel** reports Xeon within Data Center and AI and manufacturing within Intel Foundry in its FY2025 filing, for the year ended December 27, 2025. Foundry results include sales to other Intel businesses, so read the reconciliation to consolidated results. [Intel 10-K](https://www.sec.gov/Archives/edgar/data/50863/000005086326000011/intc-20251227.htm)
