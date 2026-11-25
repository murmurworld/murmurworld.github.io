---
title: "What Payment Networks and Banks Do When You Tap a Card"
description: "Trace a card payment from merchant to acquirer, network and issuer, then see what Visa, Mastercard and a Korean financial group actually report as revenue and costs."
sector: financials
order: 8
publishedOn: '2026-11-26'
---

Tap a card at a café and the terminal shows an approval a moment later. In that moment, a message has traveled between the café’s payment provider and the company that issued the card. Following the message and the money makes the respective businesses easier to understand.

## From approval to settlement

In a typical four-party card payment, the **authorization message** goes **merchant → acquirer → payment network → issuer**. The acquirer handles card acceptance for the merchant. The network routes the request to the issuer, which generally decides whether to approve it. The answer comes back the same way. [Visa’s authorization flow](https://africa.visa.com/content/VISA/cemea/regionalenglishmaster/en/content_library/modal/how-visa-transaction-works.html)

| Stage | What happens |
| --- | --- |
| **Authorization** | The issuer decides whether the payment can proceed. The terminal shows its answer. |
| **Capture** | The merchant submits the authorized payment to collect the amount. |
| **Clearing** | The issuer and acquirer exchange transaction details and determine what is owed. |
| **Settlement** | The institutions move the funds. The timing of the merchant’s payout depends on its payment agreement. |

[Stripe’s card payment walkthrough](https://stripe.com/resources/more/credit-card-payment-authorization-and-transaction-settlement-process) · [Mastercard’s guide to authorization, clearing and settlement](https://www.mastercard.com/eea/switching-services/our-technology/transaction.html)

In Korean online checkout, a merchant may use a payment gateway (PG) that relays an authorization request to the card company through a value-added network (VAN). The checkout provider and the company deciding whether to approve the payment can be separate. [Toss Payments’ guide to Korean card payments](https://docs.tosspayments.com/resources/glossary/card-payment)

## What goes into the merchant’s fee

The fee a merchant pays reflects several costs. In a typical four-party card transaction, the acquirer generally pays **interchange** to the issuer. The network can charge separately for access and transaction processing. Acquirers and payment providers also have their own service costs. The fee components and amounts depend on factors such as the market, card type and merchant agreement. [Mastercard FY2025 Form 10‑K on fees](https://www.sec.gov/Archives/edgar/data/1141391/000114139126000013/ma-20251231.htm) · [Visa FY2026 Form 10‑K on interchange](https://www.sec.gov/Archives/edgar/data/1403161/000140316126000134/v-20260930.htm)

## How Visa and Mastercard earn revenue

**Visa (V)** reports service, data processing, international transaction and other revenue in its fiscal 2026 filing. Client incentives reduce the total to arrive at net revenue. Payment volume, the number of processed transactions and cross-border activity help explain different parts of the business. [Visa FY2026 Form 10‑K](https://www.sec.gov/Archives/edgar/data/1403161/000140316126000134/v-20260930.htm)

**Mastercard (MA)** groups its 2025 net revenue into payment network and **value-added services and solutions**. Spending on its branded cards and the transactions it switches are drivers of its network business. Security, authentication and market insights are examples of the other services. Both companies operate networks and sell additional services to their customers. Their filings group the revenue differently. [Mastercard FY2025 Form 10‑K](https://www.sec.gov/Archives/edgar/data/1141391/000114139126000013/ma-20251231.htm)

## A Korean bank and card company in the same group

KB Financial Group’s fiscal 2025 filing lists **KB Kookmin Bank** and **KB Kookmin Card** separately. The bank takes deposits as a source of funding and earns interest on assets such as loans. Net interest income, net interest margin and provisions for loan losses matter. The card company issues cards and provides credit. Card spending, delinquency and funding costs help explain the economics of that business. [KB Financial Group FY2025 Form 20‑F](https://www.sec.gov/Archives/edgar/data/1445930/000119312526183398/d79770d20f.htm)

The price of the coffee counts toward the payment volume that went through the network. The network’s net revenue reflects the fees it earns for its services, with adjustments such as client incentives. In the filings, start with transaction counts and incentives for the networks, then look at interest, funding costs and credit losses for banks and card lenders.
