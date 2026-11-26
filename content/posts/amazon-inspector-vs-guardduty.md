---
title: "Amazon Inspector vs GuardDuty: What Each Catches & When You Need Both (2026)"
date: 2026-11-26
draft: false
description: "Inspector finds the vulnerabilities an attacker could use; GuardDuty catches the attacker using them. What each scans, where they overlap, what they cost in 2026, and which to turn on first."
summary: "A practitioner's comparison of Amazon Inspector and Amazon GuardDuty — vulnerability management vs. threat detection. What each one scans, how they overlap on EC2, containers, and Lambda, how the 2026 Security Hub plans change the buying decision, and which to enable first."
slug: "amazon-inspector-vs-guardduty"
lastmod: 2026-11-26
tags: ["AWS", "Security", "GuardDuty", "Inspector", "Vulnerability Management", "Threat Detection"]
keywords: ["aws inspector vs guardduty", "amazon inspector vs guardduty", "inspector vs guardduty", "guardduty vs inspector", "amazon inspector", "aws vulnerability scanning", "do i need inspector and guardduty", "amazon inspector pricing"]
categories: ["Cloud Security"]
author: "Javier Pulido"
canonicalURL: "https://thehiddenport.dev/posts/amazon-inspector-vs-guardduty/"
enable_comments: true
---

Inspector and GuardDuty get confused constantly — same console neighborhood, both produce "findings," both have agents that can run on your EC2 instances. But they answer two different questions:

- **Amazon Inspector:** *what in my environment could an attacker exploit?* It's vulnerability management — CVEs in your packages, container images, Lambda code, and source repos, plus network exposure and CIS configuration checks.
- **Amazon GuardDuty:** *is someone attacking me right now?* It's threat detection — credential misuse, reconnaissance, crypto mining, reverse shells, malware, and multi-stage attack sequences.

One works *before* exploitation, the other *during and after*. Most teams running real workloads on AWS end up wanting both. The useful questions are what each actually covers, where they overlap, and which one to turn on first — so that's what this post is about.

---

## The 30-second comparison

| | Amazon Inspector | Amazon GuardDuty |
|---|---|---|
| **Job** | Vulnerability management | Threat detection |
| **Question it answers** | "What's exploitable?" | "What's happening right now?" |
| **Looks at** | Software inventories, code, network paths, OS configuration | CloudTrail events, VPC Flow Logs, DNS logs, EKS audit logs, runtime telemetry, malware scans |
| **Covers** | EC2, ECR images, Lambda, GitHub/GitLab repos, CI/CD pipelines | Accounts and IAM, EC2, EKS, ECS (incl. Fargate), S3, RDS, Lambda, backups |
| **Typical finding** | `CVE-2021-44228` in `log4j-core` on 12 instances, network-reachable, exploit available | `Execution:Runtime/ReverseShell` on an EC2 instance |
| **When it fires** | When a new CVE is published or new software appears | When behavior looks malicious |
| **Agent?** | Optional (SSM Agent) — agentless EC2 scanning also available | Optional (GuardDuty security agent, for Runtime Monitoring only) |
| **Free trial** | 15 days | 30 days |
| **Cost driver** | Number of instances, images, functions scanned | Volume of events and logs analyzed (plus vCPUs for runtime) |

If you remember one line: **Inspector shrinks the attack surface; GuardDuty watches the attack surface you have left.**

---

## What Amazon Inspector actually does in 2026

Inspector is a continuous scanner. You enable it, it discovers your resources, and it rescans automatically when new CVEs are published — no scheduled scans to configure. It covers:

- **EC2 instances.** Agent-based scanning uses the SSM Agent you probably already run (if you use Session Manager, you're set — see [the SSM setup guide](/posts/aws-securing-ec2-access-with-ssm/)). Instances without it can use **agentless scanning**, where Inspector takes an EBS snapshot, inventories the software, and deletes the snapshot; in *hybrid* mode it does this every 24 hours for instances the agent doesn't cover. In 2026 AWS expanded agentless coverage to more application software and to Windows, and Windows findings are now grouped by Microsoft KB instead of one finding per CVE.
- **Network reachability.** For EC2, Inspector also reports open network paths to your instances — which ports are reachable from the internet through your security groups, NACLs, and gateways. This is what turns "has a CVE" into "has a CVE *and* is exposed."
- **CIS scans.** On-demand or scheduled CIS benchmark checks against the instance OS. Useful audit evidence; pairs with [the EC2 CIS benchmarks guide](/posts/ec2-cis-benchmarks-guide/).
- **Container images in ECR.** Scanned on push and then continuously rescanned for a duration you configure — so an image you pushed six months ago gets flagged when a new CVE hits its base layer.
- **Lambda functions.** Standard scanning checks the function's package dependencies; Lambda code scanning looks for vulnerabilities in your own code.
- **Code repositories and CI/CD.** Inspector code security connects to GitHub and GitLab for SAST, dependency (SCA), and infrastructure-as-code scanning, and there are CI/CD integrations to scan images before they're pushed at all.

Findings come with an **Inspector score** that adjusts the CVSS base score for your environment — network reachability, exploit availability — which is a big step up from raw CVSS. It's still not a full prioritization model, though; I wrote about what actually belongs in one in [Vulnerability Prioritization Beyond CVSS](/posts/vulnerability-prioritization-beyond-cvss/).

**What Inspector won't tell you:** whether anyone is exploiting those vulnerabilities. A critical, reachable CVE and an active intrusion through it look identical in Inspector.

---

## What Amazon GuardDuty actually does in 2026

GuardDuty is a managed detector. It reads data sources you don't have to configure or pay to store — CloudTrail management events, VPC Flow Logs, and DNS query logs — and runs AWS's threat intelligence and ML models over them. On top of that foundation you enable protection plans:

- **S3 Protection** — suspicious data-plane access to your buckets.
- **EKS Protection** — Kubernetes audit log analysis.
- **Runtime Monitoring** — an agent on EC2, EKS, and ECS (including Fargate) that sees process execution, file access, and network connections inside the workload. ([Full walkthrough here](/posts/aws-guardduty-runtime-monitoring/).)
- **Malware Protection** — scans EBS volumes of EC2 instances that trigger suspicious findings, new objects uploaded to S3 buckets you choose, and, since late 2025, your AWS Backup recovery points.
- **RDS Protection** and **Lambda Protection** — suspicious database logins and suspicious network activity from functions.

The big recent change is **Extended Threat Detection**: GuardDuty correlates individual signals into a single Critical *attack sequence* finding. It started with IAM and S3, added EKS in June 2025, and EC2 and ECS (`AttackSequence:EC2/CompromisedInstanceGroup`, `AttackSequence:ECS/CompromisedCluster`) in December 2025. It's included at no extra cost.

**What GuardDuty won't tell you:** that you're one unpatched library away from the incident it's about to detect. It doesn't inventory software or look at CVEs. If you want the setup steps, [the GuardDuty setup guide](/posts/aws-guardduty-setup/) gets you running in about ten minutes.

---

## Where they overlap (and where they only look like they do)

This is where the confusion comes from. Several areas look like overlap but aren't:

**EC2 agents.** Inspector's agent-based scanning uses the **SSM Agent**. GuardDuty Runtime Monitoring uses its **own security agent**. Different agents, different jobs: one reports what software is installed, the other reports what that software is *doing*. You can run both.

**EBS snapshots.** Both services can scan EBS snapshots without an agent — Inspector to inventory packages and find CVEs, GuardDuty to look for malware. Inspector does it on a schedule; GuardDuty Malware Protection for EC2 is mostly triggered by a suspicious finding (or run on demand).

**Containers.** Inspector scans the *image* in ECR — before and between deployments. GuardDuty watches the *running container* through Runtime Monitoring and EKS audit logs. Image hygiene vs. live behavior.

**Lambda.** Inspector scans the function's dependencies and code. GuardDuty Lambda Protection watches the network activity of invocations — e.g., a function suddenly talking to a crypto-mining pool.

**Where they genuinely meet:** both are regional, both support AWS Organizations with a delegated administrator, and both send findings to Security Hub and EventBridge. That last part is how you connect them — more below.

---

## How they work together: one vulnerability, two services

Here's the sequence I've seen play out in real environments — think of any Log4Shell-style library bug:

1. **A new CVE is published.** Inspector re-evaluates your inventory automatically and raises findings on the ECR images and EC2 instances that include the affected package. The ones that are network-reachable with a public exploit float to the top.
2. **You have a window.** This is where vulnerability management earns its keep: patch, rebuild the image, redeploy. If you have a remediation SLA, this is where it applies — I wrote about designing realistic ones in [Vulnerability Management SLAs: Design, Enforcement, and Rollout](/posts/vulnerability-management-sla-design/).
3. **Something didn't get patched in time and gets exploited.** GuardDuty Runtime Monitoring flags the reverse shell (`Execution:Runtime/ReverseShell`), then the miner calling home (`CryptoCurrency:EC2/BitcoinTool.B!DNS`). Extended Threat Detection rolls the steps into one attack sequence.
4. **You respond.** Isolate the instance, preserve evidence, rotate whatever its role could reach — the [cryptomining scenario in the IR guide](/posts/aws-incident-response-scenarios/) walks through containment.

Inspector gives you the chance to avoid step 3. GuardDuty makes sure step 3 doesn't go unnoticed. Neither replaces the other — which is the whole answer to "Inspector vs GuardDuty."

A practical way to wire them together: route **Inspector findings into your patching workflow** (tickets with an SLA) and **GuardDuty findings into your alerting** (Slack/pager, with EventBridge doing the routing). Mixing them in one noisy channel is how both get ignored.

---

## Buying them in 2026: standalone or through Security Hub

Until recently this was simple: each service had its own pay-as-you-go price. Inspector bills per scanned resource (EC2 instances, ECR image scans and rescans, Lambda functions), GuardDuty bills by volume (events and GB analyzed, plus vCPUs for Runtime Monitoring).

The new **AWS Security Hub** adds a second way to buy them:

- The **Essentials plan** bundles posture management (Security Hub CSPM) and vulnerability management *powered by Inspector* into a single per-resource price, counted across EC2 instances, ECR images, Lambda functions, and IAM users and roles.
- The **Threat Analytics plan** adds GuardDuty-powered threat detection on top. As of October 2026, GuardDuty Runtime Monitoring is billed through Security Hub in accounts where it's enabled.

Which is cheaper depends entirely on your resource counts and log volume — there's no universal answer. The Security Hub console has a **cost estimator** that compares the bundled plans against standalone pricing for your actual numbers; use it before committing, and use the free trials (15 days for Inspector, 30 for GuardDuty) to get real figures instead of guesses.

Two cost controls worth knowing regardless of how you buy:

- **Inspector:** limit the ECR rescan duration to how long images actually stay in use, scope enhanced scanning to the repositories that matter, and exclude throwaway EC2 instances with the `InspectorEc2Exclusion` tag.
- **GuardDuty:** the usual surprises are S3 Protection on very busy buckets and Runtime Monitoring on large fleets — check the usage page after the trial before rolling them out org-wide. (More in [AWS Security Monitoring Tools & Services](/posts/affordable-aws-security-monitoring/).)

---

## Which should you turn on first?

**GuardDuty first, for almost everyone.** It needs no agents and no configuration, it covers your whole account from day one, and it catches the thing that causes the most AWS incidents — a stolen credential being used. Even an all-serverless account with nothing for Inspector to scan benefits from GuardDuty.

**Then Inspector, as soon as you have EC2 instances or container images you're responsible for patching.** If you run workloads on instances or ship images through ECR, unscanned CVEs are your largest attack surface, and Inspector is the lowest-effort way to see them.

**Inspector moves up the list if** you're heading into an audit — SOC 2, ISO 27001, and PCI DSS assessors all ask for vulnerability-scanning evidence, and Inspector (plus its CIS scans) produces it. ([ISO 27001 audit prep on AWS](/posts/iso-27001-aws-audit-prep/) covers what else they'll ask for.)

**You probably don't need Inspector yet if** you're fully serverless with managed runtimes and few dependencies, or everything runs on managed services where AWS does the patching.

---

## What neither of them covers

Even with both on, there are gaps worth knowing about:

- **Misconfigurations.** Public buckets, overly broad IAM, disabled logging — that's posture management: Security Hub CSPM or Prowler. See [GuardDuty vs Security Hub](/posts/aws-guardduty-vs-security-hub/) and [Prowler vs Security Hub](/posts/prowler-vs-aws-security-hub/).
- **Investigation.** GuardDuty tells you *that* something happened; reconstructing *what* happened is still CloudTrail work — [CloudTrail log analysis](/posts/aws-cloudtrail-log-analysis/) covers the queries.
- **Credentials that leaked outside AWS.** Both services work on what's inside your account. A developer's AWS console session stolen by an infostealer, or a reused password from a breach, is invisible to both until someone *uses* it. Catching that earlier means watching outside your account — that's what [credential exposure monitoring](/monitoring/) is for, and [this post on leaked AWS credentials](/posts/leaked-aws-credentials/) explains the timeline.

---

## The short version

- **Inspector = vulnerability management.** Continuous CVE scanning for EC2, ECR, Lambda, and code, with network reachability and CIS checks. Prevents incidents.
- **GuardDuty = threat detection.** Managed analysis of account, network, runtime, and malware signals, with multi-step attack correlation. Detects incidents.
- **They don't compete.** The apparent overlaps (agents, snapshots, containers, Lambda) are two different views of the same resources.
- **Turn on GuardDuty first**, add Inspector when you have instances or images to patch, and compare standalone pricing against the Security Hub plans with your own numbers.

If you're deciding how these fit into a broader detection and vulnerability program — what to enable, how to route findings, what SLAs are realistic for your team — that's the kind of work I do with small security teams. The setup takes an afternoon; making the findings actually get acted on is the part that takes thought.

---

**Related guides:**
- [GuardDuty vs Security Hub: Key Differences & When to Use Both](/posts/aws-guardduty-vs-security-hub/) — how both services feed into Security Hub
- [GuardDuty Runtime Monitoring: Setup, Cost & When to Use It](/posts/aws-guardduty-runtime-monitoring/) — the runtime agent in depth
- [GuardDuty Alternatives: AWS Threat Detection Tools Compared](/posts/aws-guardduty-alternatives/) — when GuardDuty alone isn't enough
- [Vulnerability Prioritization Beyond CVSS](/posts/vulnerability-prioritization-beyond-cvss/) — what to fix first once Inspector starts producing findings
- [Vulnerability Scanner Architecture: What to Scan, How to Dedupe, When to Build](/posts/vulnerability-scanner-architecture/) — where a managed scanner like Inspector fits in a full program
- [AWS Incident Response Scenarios](/posts/aws-incident-response-scenarios/) — what to do when a GuardDuty finding turns out to be real
