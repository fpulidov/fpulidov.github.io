---
title: "What an Exposure Report Looks Like (Sample)"
description: "An illustrative example of the credential-exposure report you receive — what leaked, which accounts, how serious it is, and the exact steps to close it. Sample data only, not a real company."
layout: "single"
author: "Javier Pulido"
date: 2026-11-20
keywords: ["credential exposure report example", "dark web monitoring report sample", "leaked credentials report"]
draft: false
hideConsultingCta: true
url: "/monitoring/sample-report/"
enable_comments: false
---

To show you what you'd actually receive, here's an **illustrative** exposure report — the format, the level of detail, and the tone. The data below is **invented for the example**: it is not a real company and not real credentials.

---

**Exposure report — `acme-example.com`**
*Prepared by Javier Pulido · illustrative sample*

## Summary

Your domain currently shows **14 exposed credentials** across 9 accounts. **3 are live, service-specific credentials** from infostealer logs (the urgent ones); the remaining 11 are older breach-data records. One live finding is a **Microsoft 365 session** — treat it as the priority.

| Priority | Account | Source | What leaked | Service |
|---|---|---|---|---|
| 🔴 Critical | j.doe@acme-example.com | Infostealer | Live session + password | Microsoft 365 |
| 🔴 Critical | admin@acme-example.com | Infostealer | Password (strong) | AWS console |
| 🟠 High | billing@acme-example.com | Infostealer | Password (weak) | Xero |
| 🟡 Medium | j.doe@acme-example.com | Breach data | Password (reused) | LinkedIn (2021) |
| ⚪ Low | *(8 more older records)* | Breach data | email / password | various |

*(In your real report, passwords are shown in full so you can confirm and rotate them. They're masked here because this is a public sample.)*

## What to do, in order

1. **j.doe@ — Microsoft 365, now.** A live session cookie can bypass MFA. **Revoke all active sessions** for this user and force re-authentication, then reset the password. Check sign-in logs for unfamiliar locations in the last 30 days.
2. **admin@ — AWS console, today.** Rotate the password and confirm MFA is enforced. If this is a shared admin login, it's a good moment to move to individual IAM users — [here's why and how](/posts/aws-iam-users-alternatives/).
3. **billing@ — Xero, this week.** Reset it, and stop reusing this weak password pattern elsewhere.
4. **Reused passwords (j.doe).** The LinkedIn-breach password matches a pattern seen in the live finding — enforce a reset and check for the same reuse across your stack.

## What I watch from here

Everything above now stays under continuous monitoring. If a new live credential appears, you hear from me the same day with a report like this one — not a dashboard alert you have to decode yourself.

---

That's the whole deliverable: what leaked, how serious it is, and the exact next step.

Want this for your real domain? [**Run a free exposure check →**](/monitoring/free-exposure-check/) &nbsp;·&nbsp; [How it works](/monitoring/how-it-works/) &nbsp;·&nbsp; [FAQ](/monitoring/faq/)

[← Back to the monitoring service](/monitoring/)
