---
title: "Credential Monitoring — FAQ"
description: "Common questions about credential exposure monitoring: data handling and GDPR, whether it ever sees real passwords, how it compares to free breach checkers, MFA, alert speed, coverage and pricing."
layout: "single"
author: "Javier Pulido"
date: 2026-11-20
keywords: ["credential monitoring faq", "dark web monitoring gdpr", "leaked credentials monitoring", "credential exposure questions"]
draft: false
hideConsultingCta: true
url: "/monitoring/faq/"
enable_comments: false
---

Common questions about the [credential exposure monitoring](/monitoring/) service. Didn't find yours? [Email me](mailto:javier@thehiddenport.dev?subject=Monitoring%20question) or [book a call](https://calendly.com/javier-thehiddenport/30min).

## Do you ever see or touch our real passwords?

No. The service only surfaces credentials that have *already* leaked publicly or into criminal markets. I never log into any of your accounts, and a leaked credential is never used to access anything — it's shown to you so you can reset or revoke it. It's strictly alert-only.

## Is this GDPR-compliant? Where is the data handled?

Yes. You are the **data controller**; I act as your **processor** under a data-processing agreement, with the monitoring platform as **sub-processor**. Servers are in the US, covered by the **EU–US Data Privacy Framework**, with standard contractual clauses where a specific provider isn't certified. The underlying data sources only ever see the domain or email being searched. I'll walk you through the specifics and sign the DPA before anything starts.

## How is this different from a free breach checker?

Three ways. First, **infostealer-log coverage** — the live, service-specific credentials copied off infected machines, which free checkers don't have and which are the ones that actually get exploited. Second, **continuous monitoring** instead of a one-off lookup. Third, **me** — verifying each finding and telling you exactly what to do, rather than handing you a raw list. [More on how that works](/monitoring/how-it-works/).

## We already enforce MFA. Do we still need this?

Yes — and this is the uncomfortable part. Infostealer malware steals **session cookies**, not just passwords: an already-authenticated session an attacker can replay to walk past MFA entirely. MFA doesn't close that door; catching the leak early does.

## How fast will I hear about a new exposure?

New exposure is pulled near-real-time and triaged as it appears, so anything critical reaches you in the window that matters — not in a monthly report. You also get a regular summary covering the quiet periods.

## What exactly do I need to give you?

One domain. That's it. Every address on it is covered automatically — no employee list to maintain, nothing to install on anyone's device. New accounts are picked up as they appear.

## Can you watch specific people, like our executives?

Yes. Beyond the domain, I can monitor specific high-value addresses — a CEO, CFO, or admin account — more closely. Account-takeover of an executive is a different class of risk and is worth watching on its own. Ask me about it.

## What about employees' personal email addresses?

I monitor the domain you're responsible for. If an employee reused a work password on a personal service that later got breached, that *work* credential still shows up — which is the point. I don't monitor employees' personal accounts; those are theirs, not yours.

## What happens if nothing is found?

You get a clean report and the reassurance that goes with it — a perfectly good outcome. Exposure isn't constant; much of the value is knowing the moment it *changes*.

## Can I cancel anytime?

Yes. It's a simple per-domain subscription — no long contract and no minimum term. Current pricing is on the [main monitoring page](/monitoring/#pricing).

## Is this a reselling / white-label arrangement?

The monitoring runs on a specialist exposure-intelligence platform; I handle the setup, the interpretation, and the relationship with you. You deal with me, under my data-processing agreement — one point of contact who actually reads the findings and is accountable for them.

---

[**Run a free exposure check →**](/monitoring/free-exposure-check/) &nbsp;·&nbsp; [How it works](/monitoring/how-it-works/) &nbsp;·&nbsp; [Sample report](/monitoring/sample-report/)

[← Back to the monitoring service](/monitoring/)
