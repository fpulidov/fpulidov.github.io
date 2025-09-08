---
title: "Enforcing Least Privilege in AWS IAM with Access Analyzer and Last Access Data"
description: "A practical guide on enforcing least privilege in AWS IAM by using IAM Access Analyzer and service Last Accessed data. Includes real workflows, auditing strategies, and automation tips."
summary: "This article shows how to audit and refine IAM permissions using Access Analyzer, CloudTrail, and service access history — enforcing least privilege the right way in AWS."
date: 2025-06-09
tags: ["AWS", "IAM", "Least Privilege", "Access Analyzer", "Security"]
canonicalURL: "https://thehiddenport.dev/posts/enforcing-least-privilege-iam-access-analyzer"
enable_comments: true
---

# Enforcing Least Privilege in AWS IAM with Access Analyzer and Last Access Data

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
````

Once active, it scans all supported resources and generates findings like:

* "S3 bucket is shared with the public"
* "KMS key accessible to another AWS account"

This is your first pass: shut down **explicit external access** that violates least privilege.

[Read more in my Access Analyzer deep dive](../iam-access-analyzer-least-privilege/)

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
3. Manually edit the policy or use tools like [repokid](https://github.com/Netflix/repokid) for automation.

This is tedious but worth it — it’s the **real way** to enforce least privilege.

---

## Step 4: Detect Escalation in Real-Time

Least privilege isn't just about *static* policies — it's about monitoring *changes* too.

Use **EventBridge + CloudTrail** to catch events like:

* `CreatePolicy` or `AttachRolePolicy` with wildcards
* Roles being granted `AdministratorAccess`
* Roles using new services suddenly

Send these to **SNS**, **Slack**, or log them into a [central detection toolkit](../aws-ir-toolkit/).

---

## Bonus: Automate Least Privilege Reviews with Lambda

Want to get proactive?

* Schedule a Lambda that runs `generate-service-last-accessed-details` weekly
* Parse results and send a report to security engineers or your team chat
* Automatically open a ticket if `iam:PassRole` appears on a dev role

You can add this to your [IR automation playbook](../aws-ir-playbook-template/).

---

## Related Reading

* [Common AWS IAM Misconfigurations](/posts/aws-security-misconfigurations/)
* [IAM Access Analyzer Deep Dive](/posts/iam-access-analyzer-least-privilege/)
* [AWS IR Toolkit with Detection Rules](/posts/aws-ir-toolkit/)
* [Securing Temporary AWS Credentials](/posts/aws-temporary-credentials-security/)

---

**Happy hunting**
