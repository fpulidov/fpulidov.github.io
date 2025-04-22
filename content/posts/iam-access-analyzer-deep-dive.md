---
title: "Building Least-Privilege IAM Roles with IAM Access Analyzer"
date: 2025-04-21
tags: ["aws", "iam", "least-privilege", "access-analyzer", "terraform", "security"]
categories: ["Cloud Security", "Guides"]
summary: "Use IAM Access Analyzer to build least-privilege IAM roles in AWS — includes policy generation from CloudTrail, Terraform integration, and AWS best practices."
description: "Learn how to use IAM Access Analyzer to identify risky permissions, generate fine-tuned IAM policies, and integrate the tool into your AWS development workflow."
slug: "iam-access-analyzer-least-privilege"
draft: false
author: "Javier Pulido"
canonicalURL: "https://thehiddenport.dev/iam-access-analyzer-least-privilege"
---

## Why Least Privilege Matters

Overly permissive IAM roles are still one of the **most exploited weaknesses in AWS**. Whether it’s a developer giving `s3:*` to an app or a CI/CD pipeline allowed to `iam:*`, misconfigurations create unnecessary attack surface.

**IAM Access Analyzer** helps fix that — by showing you *what access your policies really grant*, and by helping you build tighter permissions from real-world usage data.

---

## What Is IAM Access Analyzer?

IAM Access Analyzer is a native AWS feature that helps you:

- **Identify** who has access to your AWS resources (trust policies)
- **Analyze** what your IAM policies allow (policy analyzer)
- **Generate** fine-grained IAM policies based on actual usage

It's split into two capabilities:

| Feature | Purpose |
|--------|---------|
| **Policy validation & simulation** | Checks whether your policies are overly broad |
| **Access Analyzer (policy generation)** | Watches IAM role activity and suggests tight-scoped policy JSON |

> Available via console, CLI, SDK, and supported by Terraform

---

## Enabling IAM Access Analyzer

You must have **AWS Organizations** enabled or a standalone account with IAM Analyzer permissions.

### CLI:
```bash
aws accessanalyzer create-analyzer   --analyzer-name "org-analyzer"   --type ORGANIZATION
```

> Use `--type ACCOUNT` if you're not using AWS Organizations.

### Terraform:
```hcl
resource "aws_accessanalyzer_analyzer" "default" {
  name = "org-analyzer"
  type = "ORGANIZATION"
}
```

Once enabled, it starts monitoring for:
- External access grants (e.g., cross-account S3 bucket access, CICD access...)
- Overly broad IAM policies

---

## Analyzing a Role for Over-Permission

Let’s simulate a policy and see if it’s too permissive.

### Step 1: Write the IAM policy
```json
{
  "Version": "2012-10-17",
  "Statement": {
    "Effect": "Allow",
    "Action": "*",
    "Resource": "*"
  }
}
```

### Step 2: Run a simulation
```bash
aws iam simulate-custom-policy   --policy-input-list file://policy.json   --action-names "s3:ListBucket" "ec2:StartInstances" "iam:DeleteUser"
```

You’ll get a result for each action: `allowed` or `explicitDeny`.

---

## Generating Policies from CloudTrail Activity

IAM Access Analyzer can automatically generate **least-privilege IAM policies** by analyzing your CloudTrail logs. This lets you replace over-permissive policies with ones that reflect actual usage.

> This requires **CloudTrail to be enabled** in the account and set to log to an S3 bucket.

### Step-by-Step in AWS Console

1. **Go to the IAM Console**:
   - Navigate to **IAM** and click on the desired role.

2. **Go to “Generate policy based on CloudTrail events”**:
   - Here you’ll see the "Generate Policy" button, click it.

3. **Fill the form**:
   - Fill the form to meet your criteria.
   - You can choose a time range from the available CloudTrail logs.
   - Choose the CloudTrail trail that has the relevant data.

4. **Click on Generate Policy**:
   - AWS will scan CloudTrail logs and determine which actions were used.

5. **Review and download the policy** once ready:
   - Once the job completes, you’ll see a generated policy document.
   - You can copy the JSON, edit it if needed, and attach it to the principal directly or via Terraform.

> 🧠 This process can take a few minutes depending on the volume of logs. The policy reflects only *observed* usage — consider reviewing manually before attaching.

---

## Pro Tips

- Always start Access Analyzer **before** running new workloads (so it can monitor them)
- Run it again after a few days of usage to refine permissions
- Use **managed policies** for standard access, but **custom policies** for sensitive services like S3, IAM, EC2

---

## Extra Hardening

Use these IAM policy techniques to limit blast radius:

### Require MFA for IAM console sessions

```json
{
  "Condition": {
    "BoolIfExists": {"aws:MultiFactorAuthPresent": "false"}
  }
}
```

### Use Permission Boundaries

Permission boundaries are a powerful but often misunderstood feature of IAM.

A permission boundary is an **advanced policy** that defines the *maximum* permissions a role or user can be granted — even if their assigned IAM policy is broader. It acts as a safety net or “guardrail” to prevent privilege escalation or accidental over-permissioning.

For example, if a developer tries to attach an `AdministratorAccess` policy to a role, but a permission boundary restricts actions to `s3:*` and `ec2:Describe*`, then only those actions will be allowed — everything else is denied.

This is especially useful in environments where:
- Developers or CI/CD pipelines create their own roles or policies
- You're delegating IAM permissions within a sandbox or dev account
- You want to limit access in automation scenarios without managing every detail

To use them effectively:
- Define a boundary policy that allows a scoped set of actions
- Attach the boundary to IAM roles during creation
- Enforce via Infrastructure as Code (like Terraform) to avoid manual missteps



---

## Final Thoughts

IAM Access Analyzer helps bridge the gap between "theory of least privilege" and actual **policy enforcement**. It's not perfect — but when combined with Terraform and CloudTrail, it's one of the best tools to clean up risky roles without slowing down dev teams.

Use it to:
- Simulate policies before deployment
- Detect risky cross-account access
- Generate scoped policies from real CloudTrail usage

---

*In a world of too much access, precision wins. IAM Access Analyzer gives you the tools — now go sharpen your policies.* 🔐
