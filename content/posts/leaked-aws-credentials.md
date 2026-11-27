---
title: "Leaked AWS Credentials: How Access Keys End Up for Sale (and How to Catch It Early)"
date: 2026-11-18
draft: false
description: "AWS access keys and console logins leak constantly — from Git commits, infected laptops, and reused passwords. Here's how they end up for sale, how attackers use them, and how to detect exposure before it turns into an incident."
summary: "A practitioner's walkthrough of how AWS credentials actually leak — public Git repos, infostealer logs, CI/CD output, password reuse — what attackers do with them, how to detect both the leak and its use (GuardDuty, CloudTrail, Access Analyzer), and how to shrink the blast radius."
slug: "leaked-aws-credentials"
lastmod: 2026-11-18
tags: ["AWS", "Security", "IAM", "Credentials", "Incident Response", "Threat Detection"]
keywords: ["leaked aws credentials", "aws access keys leaked", "exposed aws keys", "stolen aws credentials", "aws keys on github", "compromised aws access key", "aws credential exposure", "aws key leaked what to do"]
categories: ["Cloud Security"]
author: "Javier Pulido"
canonicalURL: "https://thehiddenport.dev/posts/leaked-aws-credentials/"
enable_comments: true
---

Most AWS incidents I get called about don't start with a clever exploit. They start with a credential that was already out there — an access key committed to a repo two years ago, a developer's laptop quietly infected, a password reused on some SaaS tool that got breached. The key sits in a list somewhere, and then one day someone runs it against your account and it works.

The uncomfortable part is the timeline. The credential is usually exposed *long* before it's used. That gap is the whole game — it's the window where you either find it or an attacker does. This post is about how AWS credentials actually leak, what happens to them once they're loose, and how to catch exposure early instead of reading about it in CloudTrail after the fact.

---

## How AWS credentials actually leak

Forget the Hollywood version. The real leak paths are mundane and repeat constantly:

- **Public Git repositories.** Long-lived IAM access keys (`AKIA…`) committed to code, often in a config file, a notebook, or a `.env` that was supposed to be gitignored. This is still the single most common one. Private repos aren't safe either — they get forked, cloned to laptops, and occasionally flipped public by mistake.
- **Infostealer malware on developer machines.** This is the one most teams underestimate. Infostealers scrape everything a browser and OS have saved — credentials, `~/.aws/credentials` files, environment variables, and *active session cookies*. A developer's home laptop you've never seen is enough. The stolen data gets bundled into "logs" and sold in bulk.
- **CI/CD and build output.** Keys echoed into pipeline logs, baked into container images, left in Terraform state, or pasted into a ticket while debugging. Anywhere plaintext credentials pass through a system that keeps history.
- **Password reuse → breach data.** An engineer reuses their work email and password on a third-party service. That service gets breached, the list leaks, and the pair gets tried against your AWS SSO / console login and everything else. One reused password is enough.
- **Over-shared console access.** Root credentials or IAM user passwords handed around in chat, stored in a shared note, or set to something guessable. (If you're still handing out IAM *users* at all, that's worth rethinking — see [Stop Using IAM Users](/posts/aws-iam-users-alternatives/).)

Notice how few of these require any skill. The attacker's hard work is already done by the time the credential is for sale.

## What happens after a key leaks

Exposed AWS keys don't sit untouched. The public-repo path in particular is heavily automated: bots continuously scan GitHub, pastebins, and public buckets, and a freshly committed `AKIA…` key is often picked up and tested **within minutes**. AWS itself watches for this — when it detects a key exposed publicly, it attaches a `AWSCompromisedKeyQuarantineV3` policy to throttle the damage — but that's a backstop, not a guarantee, and it does nothing for keys leaked through a laptop or a breach rather than a public repo.

Once a credential is validated as working, it has value, and it gets handled like inventory:

- **Validated and sorted.** Automated tooling confirms the key works and probes what it can do — list buckets, describe instances, check billing, enumerate IAM.
- **Priced by access.** A key into an account with admin or billing access is worth far more than a read-only one. This is exactly why least privilege matters as *damage control*, not just hygiene.
- **Sold or used.** It's either monetized directly (crypto mining on your EC2 quota, data theft, extortion) or bundled into a dataset and sold to someone who will.

A stolen **session** — a console session cookie or a cached SSO token — is worse than a stolen key, because it can walk straight past MFA. The attacker reuses an already-authenticated session; there's no second factor to prompt. That's the scenario infostealer logs quietly enable. ([Session Hijacking: How Stolen Cookies Bypass MFA](/posts/session-hijacking-mfa-bypass/) covers how it works and how to detect it, including in CloudTrail.)

## Why long-lived keys are the root problem

Almost every leak path above is more dangerous because of one thing: **the credential doesn't expire.** A long-lived `AKIA…` access key leaked in 2023 still works in 2026 unless someone rotated it. Attackers know this, which is why old keys in old repos are still worth scanning for.

The structural fix is to stop having long-lived credentials to leak in the first place:

- Use **temporary, role-based credentials** wherever you can — STS, instance roles, IRSA on EKS. They expire on their own, so a leaked one is usually dead by the time it's traded. ([Temporary Credentials in AWS](/posts/aws-temporary-credentials-security/) covers the patterns.)
- Move human access to **IAM Identity Center (SSO)** with short-lived sessions instead of standing IAM users and access keys. ([IAM Identity Center account access](/posts/iam-identity-center-account-access-optional/).)
- Where a long-lived key is genuinely unavoidable, scope it tightly and rotate it on a schedule.

You can't leak what doesn't exist. Every long-lived key you remove is one fewer thing for a scanner to find.

## How to detect a leaked key being used

Even with good hygiene, assume some credential will leak. The next line of defense is noticing when one gets *used*:

- **GuardDuty** is the fastest win here. It flags anomalous IAM behavior and credential misuse out of the box — finding types like `UnauthorizedAccess:IAMUser/MaliciousIPCaller`, `UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration` (an EC2 role's credentials being used from outside the instance), and `Recon:IAMUser/*` for the enumeration that usually comes right after a key is validated. If you haven't turned it on, start there — [GuardDuty setup](/posts/aws-guardduty-setup/).
- **CloudTrail** is where the story lives in detail: a credential suddenly calling from a new country, a new ASN, at an odd hour, or doing enumeration it's never done before. This is the signal GuardDuty rides on, and it's what you'll pull during an investigation — [analyzing CloudTrail logs](/posts/aws-cloudtrail-log-analysis/).
- **IAM Access Analyzer** and unused-access findings help you spot the over-permissioned, dormant credentials that make a leak catastrophic — the ones worth cleaning up *before* they leak. ([IAM Access Analyzer deep dive](/posts/iam-access-analyzer-least-privilege/).)
- **Watch for privilege escalation.** A validated low-privilege key is often just step one; the next move is trying to escalate. [Detecting privilege escalation in AWS](/posts/aws-detecting-privilege-escalation/) covers the patterns to alert on.

The catch: all of these fire when the credential is *already in your account*. That's detection, and it's essential — but it's reactive by definition.

## Shrink the blast radius before it happens

Detection buys you nothing if a single leaked key owns everything. Limit what any one credential can do:

- **Enforce least privilege** so a leaked key is boring, not catastrophic ([Enforcing Least Privilege](/posts/aws-enforcing-least-privilege/)).
- **Use permission boundaries** to cap what roles can grant themselves ([IAM Permission Boundaries](/posts/aws-iam-permission-boundaries/)).
- **Set org-wide guardrails with SCPs** so even a compromised admin can't leave the fence ([SCP Best Practices](/posts/aws-scp-best-practices/)).

None of this prevents the leak. It makes the leak survivable.

## The gap: detecting use is already late

Here's the limitation worth sitting with. Everything above detects a leaked credential *once it touches your account*. But remember the timeline — the credential is usually exposed weeks or months before it's used. Verizon's breach research consistently puts stolen credentials among the top initial-access vectors, and in a large share of cases the victim's details were sitting in infostealer logs or breach dumps well before the intrusion.

So the earliest possible signal isn't in CloudTrail at all. It's the moment your domain's credentials — an employee's reused password, an AWS console login, a session cookie — show up in an infostealer log or a breach dump, *before anyone uses them*. If you're only watching your AWS account, you can't see that. You find out when the key gets used, which is the point you were trying to get ahead of.

That outside-in view — monitoring for your team's leaked credentials and stolen sessions across infostealer logs and breach data — is a different data source from anything inside AWS, and it's exactly the early-warning layer most teams are missing. It's the service I run at [**The Hidden Port Monitoring**](/monitoring/): you give me a domain, I watch it continuously, and when something turns up I tell you what leaked and what to do about it. If you want to know where you stand right now, a [free exposure check](/monitoring/) will show you what's already out there.

This applies well beyond AWS keys — it's every login your team uses. For the company-wide version (breach data vs. infostealer logs, what free tools like Have I Been Pwned cover, and how to check a whole domain), see [How to Check If Your Company's Credentials Are Already Leaked](/posts/check-company-credentials-leaked/).

## If a key just leaked: the first hour

If you're reading this because a key is already exposed, move in this order:

1. **Deactivate, then delete the key.** Deactivate first so you can still audit what it was doing; don't just rotate and move on.
2. **Pull CloudTrail for that credential.** Every call it made, from where, over what window. Establish whether it was used before you killed it.
3. **Assume session theft if a laptop was involved.** Rotate the key *and* revoke active sessions/tokens — a stolen session outlives a rotated password.
4. **Check for persistence.** New IAM users, access keys, roles, or trust policy changes created while the credential was live.
5. **Contain by blast radius.** If it had broad access, treat it as an account-level incident.

If you don't have this muscle memory yet, build it before you need it — [incident response scenarios](/posts/aws-incident-response-scenarios/) and the [IR toolkit](/posts/aws-ir-toolkit/) walk through the playbook, and [IR for small teams](/posts/incident-response-aws-guide/) covers doing it without a SOC.

---

## The short version

AWS credentials leak constantly, through paths that take no skill to exploit, and the credential is almost always exposed long before it's used. Three things keep that from becoming an incident:

1. **Fewer long-lived credentials** — temporary, role-based access expires before it's traded.
2. **Detection inside AWS** — GuardDuty and CloudTrail catch a leaked credential being *used*, and least privilege keeps that use contained.
3. **Early warning outside AWS** — monitoring for leaked credentials and stolen sessions catches exposure *before* it's used, in the window where you can still act.

Get the first two right and most leaks become non-events. Add the third and you stop being surprised. If you'd rather have the early-warning layer handled for you, that's what [continuous exposure monitoring](/monitoring/) is for — start with a free check and see what's already out there.
