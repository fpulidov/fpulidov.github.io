---
title: "AWS GuardDuty vs Security Hub: What Each Does and When You Need Both"
date: 2026-07-22
draft: false
description: "GuardDuty detects threats. Security Hub aggregates findings and checks compliance. Here's how they differ, where they overlap, and how to run them together without paying twice for the same data."
slug: "aws-guardduty-vs-security-hub"
tags: ["AWS", "Security", "GuardDuty", "Security Hub", "Threat Detection", "Compliance"]
keywords: ["guardduty vs security hub", "aws guardduty vs security hub", "aws security hub vs guardduty", "guardduty security hub difference", "aws threat detection vs compliance", "guardduty and security hub together"]
categories: ["Cloud Security"]
canonicalURL: "https://thehiddenport.dev/posts/aws-guardduty-vs-security-hub/"
enable_comments: true
---

GuardDuty and Security Hub show up in almost every AWS security architecture, but they solve fundamentally different problems. GuardDuty watches what's happening right now — threat detection. Security Hub checks whether your environment is configured correctly — posture management. They overlap in one specific area (findings), which is where the confusion starts.

This post breaks down what each service actually does, where they complement each other, and how to set them up together without redundant noise or wasted spend.

---

## What GuardDuty Does

GuardDuty is a **threat detection** service. It continuously analyzes data sources — CloudTrail logs, VPC Flow Logs, DNS queries, EKS audit logs, S3 data events — and generates findings when it detects suspicious activity.

Examples of what GuardDuty catches:

- An EC2 instance communicating with a known command-and-control server
- An IAM credential being used from an unusual geographic location
- S3 buckets being accessed from a Tor exit node
- Cryptocurrency mining activity on EC2
- Kubernetes API calls from an anonymous user in EKS

GuardDuty uses machine learning, anomaly detection, and threat intelligence feeds. You don't write detection rules — it's fully managed. You enable it, and it starts generating findings.

### Strengths

- **Zero configuration** — enable it and it works
- **Runtime threat detection** — catches active attacks, not just misconfigurations
- **Covers multiple data sources** in a single service (CloudTrail, VPC, DNS, S3, EKS, RDS, Lambda)
- **Severity-ranked findings** — Low, Medium, High, so you can prioritize

### Limitations

- **No compliance checking** — GuardDuty doesn't care whether your S3 bucket policy is too open or your IAM passwords lack rotation. It only fires when something suspicious actually happens.
- **No remediation** — it tells you about the problem, not how to fix it
- **No aggregation** — findings live in GuardDuty's own console per region/account

---

## What Security Hub Does

Security Hub is a **cloud security posture management (CSPM)** service. It does two things:

1. **Runs compliance checks** against security standards (CIS Benchmarks, AWS Foundational Security Best Practices, PCI DSS, NIST 800-53)
2. **Aggregates findings** from other AWS security services (GuardDuty, Inspector, Macie, Firewall Manager, IAM Access Analyzer) and third-party tools into a single pane

Examples of what Security Hub catches:

- CloudTrail is not enabled in all regions
- S3 buckets don't have server-side encryption enabled
- Root account doesn't have MFA
- Security groups allow unrestricted ingress on port 22
- IAM policies are overly permissive

These are **configuration problems** — things that are wrong right now, not active attacks.

### Strengths

- **Compliance scoring** — gives you a percentage score against each standard
- **Single pane of glass** — aggregates findings from GuardDuty, Inspector, Macie, and third-party tools
- **Cross-account, cross-region** — centralize findings from your entire organization
- **Automated checks** — runs continuously against your AWS Config rules

### Limitations

- **Requires AWS Config** — Security Hub's compliance checks rely on Config rules, which have their own per-rule cost
- **No threat detection** — it finds misconfigurations, not active attacks
- **Can be noisy** — enabling all standards at once generates hundreds of findings, most of which require context to prioritize

---

## Head-to-Head Comparison

| | GuardDuty | Security Hub |
|---|---|---|
| **Primary job** | Threat detection | Posture management + finding aggregation |
| **What it finds** | Active attacks, suspicious behavior | Misconfigurations, compliance violations |
| **Data sources** | CloudTrail, VPC Flow, DNS, S3, EKS, RDS, Lambda | AWS Config rules, other AWS services' findings |
| **Detection method** | ML, anomaly detection, threat intel | Config rule evaluation against standards |
| **Setup effort** | One click per region | Enable + choose standards + enable AWS Config |
| **Requires other services** | No | Yes (AWS Config) |
| **Compliance scoring** | No | Yes (CIS, FSBP, PCI, NIST) |
| **Cross-service aggregation** | No | Yes |
| **Cost model** | Per event volume analyzed | Per check per account/region + finding ingestion |

---

## Where They Overlap

The one area of genuine overlap: **both produce findings**.

GuardDuty generates threat findings. Security Hub generates compliance findings. When you integrate GuardDuty with Security Hub (which happens automatically once both are enabled), GuardDuty's findings flow into Security Hub.

This creates a single view where you can see both "your S3 bucket is publicly accessible" (Security Hub compliance check) and "someone from a Tor exit node just accessed that S3 bucket" (GuardDuty threat finding) in the same console.

That's the design intent — they're meant to work together, not compete.

---

## When You Need GuardDuty Only

If your primary concern is **detecting active threats** and you already have a SIEM or central logging solution, GuardDuty standalone makes sense. Common scenarios:

- Small team, limited budget, want threat detection without the Config cost overhead
- Already using a third-party CSPM tool (Prowler, Wiz, etc.) for compliance
- Routing findings directly to Slack/PagerDuty via EventBridge — don't need the Security Hub aggregation layer

---

## When You Need Security Hub Only

Rare in practice. If you have no threat detection needs and only care about compliance posture (audit preparation, governance requirements), Security Hub alone works. But most environments that care enough about compliance to enable Security Hub also need threat detection.

---

## When You Need Both (Most Teams)

For most AWS environments, the answer is both. The setup is straightforward:

1. **Enable GuardDuty** in all regions (it's one click)
2. **Enable AWS Config** with recording turned on
3. **Enable Security Hub** and choose your compliance standards
4. GuardDuty findings automatically flow into Security Hub

### Cost Optimization Tips

Running both doesn't mean paying double. A few things to watch:

- **Security Hub finding ingestion** — GuardDuty findings imported into Security Hub are free for the first 10,000/month per account/region. After that, $0.00003 per finding. For most accounts, this stays within free tier.
- **AWS Config costs** — this is often the surprise. Config charges per rule evaluation. If you enable all Security Hub standards, you might have 200+ rules evaluating across hundreds of resources. Start with AWS Foundational Security Best Practices only, then add CIS if needed.
- **GuardDuty protection plans** — S3 protection, EKS protection, RDS protection, Lambda protection are separate charges. Enable them selectively based on what you actually run.

### Recommended Architecture

```
┌──────────────────────────────────────────────────┐
│                  Security Hub                     │
│          (aggregation + compliance)               │
│                                                   │
│  ┌─────────────┐  ┌──────────┐  ┌─────────────┐ │
│  │  GuardDuty   │  │Inspector │  │   Macie     │ │
│  │  (threats)   │  │ (vulns)  │  │  (data)     │ │
│  └──────┬──────┘  └────┬─────┘  └──────┬──────┘ │
│         │              │               │         │
│         └──────────────┼───────────────┘         │
│                        ▼                         │
│              EventBridge Rule                    │
│         ┌──────────┬──────────┐                  │
│         ▼          ▼          ▼                  │
│      Slack      Lambda     SIEM                  │
│    (alerts)   (auto-fix)  (archive)              │
└──────────────────────────────────────────────────┘
```

The key integration point is **EventBridge**. Set up rules that:

- Route HIGH severity GuardDuty findings to Slack/PagerDuty immediately
- Route CRITICAL/HIGH Security Hub compliance failures to a remediation queue
- Send everything to your SIEM for long-term storage and correlation

---

## Common Mistakes

**1. Enabling Security Hub with all standards at once**

You'll get 300+ findings on day one, most of which are informational. Start with **AWS Foundational Security Best Practices** — it's the most actionable. Add CIS Benchmarks after you've triaged the first batch.

**2. Ignoring GuardDuty because "nothing is happening"**

GuardDuty's value is that it's watching when you're not. The first time it catches a compromised credential at 2am on a Saturday, it pays for itself.

**3. Not setting up EventBridge routing**

Both services generate findings. If nobody sees them, they're worthless. At minimum, route HIGH/CRITICAL findings to a notification channel.

**4. Running both without understanding the cost model**

GuardDuty charges by event volume. Security Hub charges by compliance checks (via Config rules). Monitor both with Cost Explorer for the first month to avoid surprises.

---

## Quick Decision Framework

Ask yourself three questions:

1. **Do I need to detect active attacks?** → Enable GuardDuty
2. **Do I need compliance scoring against a standard?** → Enable Security Hub
3. **Do I want all security findings in one place?** → Enable Security Hub as the aggregator

Most teams answer yes to all three.

---

**Related guides:**
- [AWS GuardDuty Setup: Route Findings to Slack & Your SIEM in 10 Minutes](/posts/aws-guardduty-setup/) — step-by-step GuardDuty deployment with EventBridge and Terraform
- [AWS Security Monitoring Without the Enterprise Price Tag](/posts/affordable-aws-security-monitoring/) — build a full monitoring stack on a small budget
- [AWS Misconfigurations I Find in Every Security Audit](/posts/aws-security-misconfigurations-guide/) — the findings Security Hub catches automatically
- [AWS Security Checklist: 30-Minute Account Review](/posts/aws-security-checklist-2026/) — run through all critical controls in one pass
