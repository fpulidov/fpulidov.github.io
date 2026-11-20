---
title: "How Credential Exposure Monitoring Works"
description: "A plain-English look at how continuous credential monitoring works — the two data sources (infostealer logs and breach data), why stolen sessions beat MFA, and what you actually get when something leaks."
layout: "single"
author: "Javier Pulido"
date: 2026-11-20
keywords: ["how credential monitoring works", "infostealer logs explained", "stolen session cookies", "dark web monitoring explained", "credential exposure monitoring"]
draft: false
hideConsultingCta: true
url: "/monitoring/how-it-works/"
enable_comments: false
---

Most "dark web monitoring" is sold as a black box with a scary dashboard. I'd rather you understand exactly how it works, because then you can judge whether it's worth it on the merits — not on the fear.

Here's the whole mechanism.

## It watches two different sources

Leaked credentials reach the open and criminal web two ways, and they look nothing alike. I watch both:

- **Infostealer logs.** When an employee's device gets infected with info-stealing malware, it quietly copies every password *and* active login session saved in their browser, then uploads the lot to criminal markets. These logs name the exact service each credential belongs to — Microsoft 365, your AWS console, the bank portal — and they're often **live**. This is the dangerous source.
- **Breach data.** When some *other* company gets breached, the leaked email/password list ends up circulating. If an employee reused a work password on that service, their work login is now in a public dump. I check every address on your domain against this wider breach index.

Free breach checkers only ever see the second source. The infostealer side — the live, service-specific one — is the part that actually catches intrusions before they happen, and it's the part you're paying for.

## Why a stolen *session* is worse than a stolen password

This is the detail most people miss. Infostealer malware grabs **session cookies** — the token your browser holds that says "this person already logged in and passed MFA." An attacker who replays that cookie walks straight into the account **without a password and without triggering MFA**, because as far as the service is concerned, the session is already authenticated.

So "we enforce MFA" doesn't close this door. A stolen session is a skeleton key that expires — which is exactly why catching it *fast* matters, and why an alert sitting unread in an inbox is worthless.

## The part that matters: a human reads it

Anyone can resell raw alerts. The value is what happens *after* a hit.

When something turns up on your domain, **it comes to me first.** I verify it isn't a false positive, work out how exposed you actually are (is the password current? is it a live session? which service?), and send you a short, plain-language report: what leaked, which accounts, how serious, and the specific steps to shut it down — reset this, revoke that session, check for this sign-in. You get a security advisor interpreting the finding, not an automated email landing cold at 3am.

If a finding is bad enough to need hands-on help, I can walk the remediation with you — see my [incident response guide](/posts/incident-response-aws-guide/) for how I approach that.

## Coverage: the whole domain, automatically

You give me one domain. Every address on it is covered — the new hire, the shared `billing@` inbox, the admin account someone made in 2012 and forgot. There's no employee list to maintain and nothing to install on anyone's machine. New addresses are picked up as they appear.

## How often it runs

Monitoring is continuous. New exposure is pulled near-real-time and triaged as it appears, so a critical finding reaches you in the window that matters — not in a monthly report. You also get a regular plain summary, so you can see the quiet months too.

## What it is *not*

- **It's not hacking anything.** The service only finds credentials that have *already* leaked publicly or into criminal markets.
- **It's alert-only.** I never log into any of your accounts, and leaked credentials are never used to access anything — they're surfaced so you can kill them.
- **It's not a replacement for your other controls.** It sits alongside your AWS monitoring and endpoint security — see [affordable AWS security monitoring](/posts/affordable-aws-security-monitoring/) for the rest of that stack. This closes the one specific gap of "a working login to your environment is already for sale and nobody knows."

---

Ready to see your own exposure? [**Run a free exposure check →**](/monitoring/free-exposure-check/) &nbsp;·&nbsp; read the [full FAQ](/monitoring/faq/) &nbsp;·&nbsp; see a [sample report](/monitoring/sample-report/).

[← Back to the monitoring service](/monitoring/)
