---
title: "AWS Security Consulting — Sevilla, Spain"
description: "AWS security consultant based in Sevilla, Spain. Cloud security audits, GuardDuty and Security Hub deployment, IAM hardening, incident response, and ISO 27001 preparation. Remote engagements across Europe."
layout: "single"
author: "Javier Pulido"
searchHidden: true
url: "/consulting/"
---

I'm an **AWS security consultant based in Sevilla, Spain**, working remotely with clients across Europe and beyond. I take on a small number of engagements each quarter — typically startups and mid-size teams that need real security posture in place without hiring a full cloud security team.

If your team is dealing with unclear detection coverage, IAM sprawl, an upcoming audit, or an incident you're not sure how to prevent from repeating — that's where I can help.

> **¿Buscas un consultor de seguridad AWS en España?** Trabajo con empresas en toda Europa desde Sevilla. Español e inglés. [Reserva una llamada gratuita](https://calendly.com/javier-thehiddenport/30min).

## What I Do

**AWS Security Audits**
End-to-end review of an AWS environment: account structure, IAM, network exposure, logging, detection posture, and data protection. You get a prioritized findings report with concrete remediation steps, not a generic checklist. Typical scope: 1–5 AWS accounts, 1–2 weeks.

**Detection & Incident Response Engineering**
Deploy GuardDuty and Security Hub the right way — with severity-based routing, EventBridge automation to Slack/PagerDuty/your SIEM, and finding suppression that filters noise without hiding real threats. Build the IR playbook around it so the alerts actually get actioned.

**IAM Hardening**
Least-privilege refactor of existing IAM policies, migration from IAM users to Identity Center (SSO), cross-account access design with permission boundaries, and CloudTrail-based auditing of who's actually using what.

**Landing Zone & Governance**
Multi-account structure with Control Tower or custom AWS Organizations setup, secure baselines applied across accounts, guardrails via SCPs, and cost/access controls that don't slow down engineering.

**ISO 27001 Preparation**
Gap analysis against ISO 27001:2023 technical controls, automation of evidence collection (Config, CloudTrail, Security Hub), and remediation of AWS-side findings before your audit.

## Who I Work With

- **Startups** past product-market fit that need security posture in place before enterprise customers or auditors start asking questions
- **SMB and mid-size** engineering teams without a dedicated cloud security engineer, especially ones running on AWS with 1–20 accounts
- **DevOps or platform teams** that own security responsibilities alongside infrastructure and want a second pair of eyes or hands-on help implementing controls

I don't work with large enterprises with dedicated security teams — you're better served by a security consultancy with a full bench.

## How It Works

1. **Free 30-minute intro call** — [book a slot on Calendly](https://calendly.com/javier-thehiddenport/30min). You describe what you're dealing with, I ask questions, and we figure out whether it's a good fit.
2. **Scoped proposal** — fixed scope, fixed price, clear deliverables. No open-ended retainers unless you specifically want one.
3. **Engagement** — remote, async-friendly, with regular checkpoints. I work in your AWS accounts via cross-account role or in a shared environment, depending on your policy.
4. **Handover** — everything I build ships with documentation and Terraform code so your team can maintain it.

## What a Typical Security Audit Looks Like

Most first engagements are a full AWS security audit. Here's how a typical 2-week audit runs, so you know exactly what you're paying for:

**Week 1 — Discovery**

- Read-only access to your AWS accounts via a scoped cross-account role
- Automated inventory: accounts, regions in use, running resources, IAM footprint
- Baseline pull from Security Hub, GuardDuty, Config, and Access Analyzer if enabled
- Manual review of what the tools miss — CloudTrail logging gaps, root account usage, SCPs, network exposure, secret management, backup and encryption posture
- Short daily updates so you know what I'm finding as I find it, not just at the end

**Week 2 — Findings & Prioritization**

- Every finding categorized by severity, exploitability, and effort to fix
- Prioritized remediation list — the "fix this today" items separated from the "plan this quarter" ones
- Written report you can share with your team, your auditors, or your board
- Live walkthrough call to explain findings, answer questions, and align on what to fix first
- Concrete remediation code (Terraform, SCPs, IAM policies) for the high-priority items

**What you get at the end**

- A written audit report with all findings, evidence, and prioritized remediation
- Working Terraform or CLI examples for the priority fixes
- A follow-up path — you can implement the fixes yourself, or extend the engagement to have me implement the highest-priority items

**What I don't do**

- Generic checklist reports. Every finding ties to a specific resource in your environment, with the specific fix.
- Vendor pitches. I don't resell tools. If a paid product is genuinely the right call for your situation, I'll say so — but the default is native AWS services.
- Open-ended "we'll figure it out as we go" scopes. You get a fixed price and a defined deliverable before we start.

## Rates & Availability

Engagements are priced per project based on scope. Reach out with a short description of your situation and I'll come back with a proposal.

Availability is limited — I keep the consulting load small so it doesn't compromise the depth of the work.

## Get in Touch

**Book a free 30-minute call:** [calendly.com/javier-thehiddenport/30min](https://calendly.com/javier-thehiddenport/30min)

**Or email:** [javier@thehiddenport.dev](mailto:javier@thehiddenport.dev)

If emailing, please include:

- What you're currently dealing with (or want to prevent)
- Your rough AWS footprint (number of accounts, main services)
- Any deadline you're working against (audit date, launch date, etc.)

I typically respond within 48 hours. CET/CEST timezone; happy to accommodate other time zones for the intro call.

---

**In the meantime, some things you can read:**
- [AWS Security Checklist: 30-Minute Account Review](/posts/aws-security-checklist-2026/) — quick self-audit you can run today
- [AWS Misconfigurations I Find in Every Security Audit](/posts/aws-security-misconfigurations-guide/) — the recurring findings across environments
- [Real-World Phishing Incident Response](/posts/real-world-phishing-incident-response/) — a walkthrough of how I approach IR
