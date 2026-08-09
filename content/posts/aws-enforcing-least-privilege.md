---
title: "IAM Least Privilege in AWS: Access Analyzer Guide"
description: "Audit and tighten IAM permissions using Access Analyzer, CloudTrail, and service last-accessed data. Step-by-step workflows for enforcing least privilege."
summary: "How to audit and refine IAM permissions using Access Analyzer, CloudTrail, and service access history — enforcing least privilege the right way in AWS."
date: 2025-06-09
tags: ["AWS", "IAM", "Least Privilege", "Access Analyzer", "Security"]
keywords: ["iam least privilege", "aws access analyzer", "iam policy generator", "least privilege aws", "iam access analyzer guide"]
categories: ["Cloud Security"]
canonicalURL: "https://thehiddenport.dev/posts/aws-enforcing-least-privilege/"
lastmod: 2026-07-29
enable_comments: true
---

The principle of least privilege is foundational in securing AWS environments, yet in practice, most IAM roles are over-permissioned by default. This article walks through how to actually **enforce** least privilege in AWS using tools like IAM Access Analyzer, service access reports, CloudTrail, and real-time alerting.

---

## Why Least Privilege Is So Hard in AWS

IAM in AWS is extremely flexible — and that's exactly the problem. Roles are often created in a rush, permissions are copied from other roles, and nobody circles back to audit them. Over time, permissions accumulate and expose your environment to unnecessary risk.

Common issues include:
- Roles with wildcards like `s3:*`, `iam:*`, or `ec2:*`
- Stale roles that no longer serve a purpose
- Unused permissions that could be safely revoked
- Lack of insight into what permissions are *actually being used*

You can’t fix what you can’t see — so let’s start by turning on the lights.

---

## Step 1: Use Access Analyzer to Audit External Access

IAM Access Analyzer helps you detect resource-based policies that grant access to external entities — like sharing an S3 bucket publicly or exposing a KMS key to a different account.

```bash
aws accessanalyzer create-analyzer \
  --type ACCOUNT \
  --name security-audit
```

Once active, it scans all supported resources and generates findings like:

* "S3 bucket is shared with the public"
* "KMS key accessible to another AWS account"

This is your first pass: shut down **explicit external access** that violates least privilege.

[Read more in my Access Analyzer deep dive](/posts/iam-access-analyzer-least-privilege/)

---

## Step 2: Generate Service Last Accessed Data

To determine which **permissions are not used**, AWS lets you query when a principal last accessed a service:

```bash
aws iam generate-service-last-accessed-details \
  --arn arn:aws:iam::123456789012:role/MyAppRole
```

Then fetch the report:

```bash
aws iam get-service-last-accessed-details \
  --job-id <job-id>
```

This reveals:

* Services that haven't been accessed in 90+ days
* Evidence to trim down `Action` lists in your policies

This is your best friend for **permission pruning**.

---

## Step 3: Refine Policies with CloudTrail + Policy Simulator

For fine-tuning:

1. Use **CloudTrail** to view actual API calls made by a role.
2. Feed those into the **IAM Policy Simulator** to determine what the minimum required permissions are.
3. Manually edit the policy to keep only the actions that appeared in CloudTrail. For automation, IAM Access Analyzer’s policy generation feature can produce a scoped-down policy from CloudTrail data directly — far more reliable than manual correlation.

This is tedious but worth it — it’s the **real way** to enforce least privilege.

---

## Step 4: Detect Escalation in Real-Time

Least privilege isn't just about *static* policies — it's about monitoring *changes* too.

Use **EventBridge + CloudTrail** to catch events like:

* `CreatePolicy` or `AttachRolePolicy` with wildcards
* Roles being granted `AdministratorAccess`
* Roles using new services suddenly

Send these to **SNS**, **Slack**, or log them into a [central detection toolkit](/posts/aws-ir-toolkit/).

---

## Bonus: Automate Least Privilege Reviews with Lambda

Want to get proactive?

* Schedule a Lambda that runs `generate-service-last-accessed-details` weekly
* Parse results and send a report to security engineers or your team chat
* Automatically open a ticket if `iam:PassRole` appears on a dev role

You can add this to your [IR automation toolkit](/posts/aws-ir-toolkit/).

---

## Common Mistakes When Implementing Least Privilege

Even teams that invest in least privilege often stumble on the same patterns:

**Starting too broad, never tightening.** It's common to launch with `s3:*` "temporarily" and plan to scope down later. Later never comes. Start with Access Analyzer's generated policy from day one — it's easier to add a missing permission than to figure out which of 47 `s3:*` permissions are actually needed six months later.

**Ignoring condition keys.** A policy that allows `dynamodb:GetItem` on a table is less dangerous than it looks — until you realize it allows reading *any* item, not just the caller's. Use condition keys like `dynamodb:LeadingKeys` or `s3:prefix` to scope access to the caller's own data. See the [IDOR prevention guide](/posts/aws-preventing-idor/) for why this matters at the application layer too.

**Confusing identity-based and resource-based policies.** A role might have no `s3:GetObject` permission, but if the S3 bucket policy grants access to `*`, the data is still exposed. Access Analyzer catches these — run it regularly, not just once.

**Not revoking access for departed team members.** IAM users and SSO assignments accumulate. Schedule a quarterly review of `aws iam get-credential-report` output and cross-reference against your HR system. Automate this if you have more than 20 users.

---

## Related Reading

- [AWS Misconfigurations I Find in Every Security Audit](/posts/aws-security-misconfigurations-guide/) — the recurring findings across environments, including IAM
- [IAM Access Analyzer Deep Dive](/posts/iam-access-analyzer-least-privilege/) — the detailed walkthrough of policy generation and external access findings
- [Detect AWS IAM Privilege Escalation with CloudTrail](/posts/aws-detecting-privilege-escalation/) — what to monitor when least privilege fails
- [Securing Temporary AWS Credentials](/posts/aws-temporary-credentials-security/) — the foundation least privilege builds on
- [AWS Incident Response Toolkit](/posts/aws-ir-toolkit/) — templates and automation for when a permission gap gets exploited
- [AWS Security Checklist: 30-Minute Account Review](/posts/aws-security-checklist-2026/) — quick self-audit you can run today
