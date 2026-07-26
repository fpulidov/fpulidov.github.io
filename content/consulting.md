---
title: "Consulting"
description: "AWS security consulting — audits, GuardDuty and Security Hub deployment, IAM hardening, incident response, and ISO 27001 preparation."
layout: "single"
author: "Javier Pulido"
searchHidden: true
url: "/consulting/"
---

I take on a small number of AWS security consulting engagements each quarter. If your team is dealing with unclear detection coverage, IAM sprawl, an upcoming audit, or an incident you're not sure how to prevent from repeating — that's where I can help.

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

1. **Initial call (free, 30 minutes)** — you describe what you're dealing with, I ask questions, and we figure out whether it's a good fit
2. **Scoped proposal** — fixed scope, fixed price, clear deliverables. No open-ended retainers unless you specifically want one
3. **Engagement** — remote, async-friendly, with regular checkpoints. I work in your AWS accounts via cross-account role or in a shared environment, depending on your policy
4. **Handover** — everything I build ships with documentation and Terraform code so your team can maintain it

## Rates & Availability

Engagements are priced per project based on scope. Reach out with a short description of your situation and I'll come back with a proposal.

Availability is limited — I keep the consulting load small so it doesn't compromise the depth of the work.

## Get in Touch

Email: [javierpulidovergara@gmail.com](mailto:javierpulidovergara@gmail.com)

Include:

- What you're currently dealing with (or want to prevent)
- Your rough AWS footprint (number of accounts, main services)
- Any deadline you're working against (audit date, launch date, etc.)

I typically respond within 48 hours.

---

**In the meantime, some things you can read:**
- [AWS Security Checklist: 30-Minute Account Review](/posts/aws-security-checklist-2026/) — quick self-audit you can run today
- [AWS Misconfigurations I Find in Every Security Audit](/posts/aws-security-misconfigurations-guide/) — the recurring findings across environments
- [Real-World Phishing Incident Response](/posts/real-world-phishing-incident-response/) — a walkthrough of how I approach IR
