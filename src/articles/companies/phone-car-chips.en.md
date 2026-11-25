---
title: "The Small Chips Inside Phones and Cars"
description: "Follow the jobs handled by a phone’s application processor, modem and RF parts, then see where microcontrollers, analog and power chips fit in a car and in company filings."
sector: semiconductors
order: 4
publishedOn: '2026-11-26'
---

Open a map on a phone and it draws the route while traffic updates come in over the cellular network. In an electric car, circuits read the voltage of individual battery cells while other chips control the motor. Following those jobs is a useful way into the businesses of Qualcomm, Texas Instruments and Analog Devices.

## A phone runs apps and keeps a signal

The **application processor**, or AP, runs the operating system and apps. Modern phones often put the CPU, graphics processor and other functions on a system-on-chip. In a navigation app, the CPU handles the application’s instructions and the GPU helps draw the map. A camera uses an image signal processor to turn sensor data into an image. The Snapdragon 8 Elite Gen 5 is one example of a platform with these functions. [Qualcomm’s platform specifications](https://www.qualcomm.com/smartphones/products/8-series/snapdragon-8-elite-gen-5)

A **modem** handles data according to the cellular standard so the phone can talk to a base station. The **RF front end** filters frequency bands and amplifies the outgoing signal. The processor and modem can be arranged differently from one phone to another. Qualcomm lists its X85 5G Modem-RF system with Snapdragon 8 Elite Gen 5. Apple’s iPhone Air uses the A19 Pro for apps and a separate C1X cellular modem. [Qualcomm’s X85 product page](https://www.qualcomm.com/modems/products/qualcomm-x85-5g-modem-rf) · [Apple’s iPhone Air announcement](https://www.apple.com/newsroom/2025/09/introducing-iphone-air-a-powerful-new-iphone-with-a-breakthrough-design/)

**How a phone sends data**

Application processor → cellular modem → RF circuits → antenna → base station

## A car reads signals and controls hardware

An electric car’s traction inverter turns DC from the battery into AC for the motor. Inside it, a **microcontroller**, or MCU, combines a processor, memory and input/output functions. It repeatedly reads current and rotation measurements and sends control signals. The **gate driver** uses those signals to turn the **power switches** on and off. A Texas Instruments design using its C2000 MCU shows all three parts. [Hyundai Motor Group’s EV driving primer](https://www.hyundaimotorgroup.com/ko/story/electric-vehicle-encyclopedia-ev-driving-principle) · [TI’s automotive traction inverter reference design](https://www.ti.com/tool/TIDM-02014)

- **Power to the motor** · Battery → power switches in the inverter → motor
- **Motor control signals** · Current and rotation measurements → MCU → gate driver → power switches

**Analog chips** can boost a sensor signal or turn a voltage into a number other chips can read. Analog Devices’ LTC6811-1 measures the individual voltages of several cells in a battery management system. A **power-management IC**, or PMIC, supplies and regulates the voltages needed by circuits such as controllers and sensors. [ADI’s battery monitor](https://www.analog.com/en/products/ltc6811-1.html) · [LX Semicon’s PMIC explainer](https://news.lxsemicon.com/9418)

## Where the three companies show up

| Company | What the filing shows | What the figure covers |
| --- | --- | --- |
| **Qualcomm (QCOM)** | About $24.1 billion in handset revenue and $6.0 billion in automotive revenue in fiscal 2026. Automotive includes products for connectivity and digital cockpits. [Qualcomm FY2026 Form 10‑K](https://www.sec.gov/Archives/edgar/data/804328/000080432826000128/qcom-20260927.htm) | Product markets within QCT. Patent licensing is reported separately in QTL. |
| **Texas Instruments (TXN)** | About $14.0 billion in Analog and $2.7 billion in Embedded Processing in fiscal 2025. Analog includes power and signal-chain products. Embedded Processing includes MCUs. [TI FY2025 Form 10‑K](https://www.sec.gov/Archives/edgar/data/97476/000009747626000059/txn-20251231.htm) | Business segment revenue from products sold across multiple markets. |
| **Analog Devices (ADI)** | Industrial accounted for 49% and automotive for 25% in fiscal 2026. ADI supplies precision converters, amplifiers and power-management parts. [ADI FY2026 Form 10‑K](https://www.sec.gov/Archives/edgar/data/6281/000000628126000089/adi-20261031.htm) | Shares of company-wide revenue by end market. |

## What to look for in the next filing

When a company reports automotive growth, look for the part of the car driving it. A cockpit processor, a battery monitor and a motor controller can end up in the same vehicle, with different purchasing decisions behind each. To track one company over time, find the same reporting category in its next filing. Qualcomm’s automotive figure sits within QCT, while ADI’s automotive share refers to company-wide revenue.
