---
title: "AWS SCPs That Actually Work: Practical Guide for Real Teams"
date: 2026-07-08
tags: ["AWS", "Security", "Organizations", "SCP", "IAM", "Cloud Security"]
keywords: ["aws scp best practices", "service control policies aws", "aws organizations scp examples", "scp guide aws", "aws scp break glass"]
categories: ["Cloud Security", "Guides"]
description: "Practical AWS Service Control Policies for real organizations. Includes must-have SCPs, break-glass patterns, and lessons from managing 25 accounts across 6 OUs."
summary: "SCPs every AWS org should deploy on day one — plus the break-glass pattern, limit gotchas, and why you shouldn't use SCPs to fix human behavior."
slug: "aws-scp-best-practices"
canonicalURL: "https://thehiddenport.dev/posts/aws-scp-best-practices/"
enable_comments: true
---

Service Control Policies are the most powerful guardrail in AWS — and one of the most misunderstood. Most guides give you a list of JSON blobs and call it a day. But SCPs are as much about organizational design as they are about policy syntax.

I managed SCPs across 25 accounts organized in 6 OUs at a previous company. Some of those policies prevented real incidents. Others taught me hard lessons about what SCPs can and can't do. This guide covers both.

---

## What SCPs Actually Do (and Don't)

SCPs set the **maximum permissions** for accounts in your AWS Organization. They don't grant access — they define the boundary of what IAM policies *can* grant.

Key mental model: **SCPs are a ceiling, not a floor.** If an SCP denies `s3:DeleteBucket`, no IAM policy in that account can override it. But an SCP allowing `s3:*` doesn't mean anyone in the account can access S3 — they still need an IAM policy granting it.

This distinction matters because it's where most SCP mistakes start.

---

## The SCPs Every Organization Should Deploy

These are the policies I'd set up on day one of any new AWS Organization. They're ordered by impact.

### 1. Block Access from Outside Your Organization

This is the single most valuable SCP I've ever deployed. It uses `aws:PrincipalOrgID` to ensure only principals belonging to your organization can interact with your resources.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyExternalAccess",
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:PrincipalOrgID": "o-your-org-id"
        },
        "BoolIfExists": {
          "aws:PrincipalIsAWSService": "false"
        }
      }
    }
  ]
}
```

The `aws:PrincipalIsAWSService` condition is critical — without it, you'd block AWS services like CloudTrail and Config from writing to your S3 buckets.

We deployed this proactively after learning from AWS best practices, not after an incident. It's one of those policies where you're glad you never had to prove it worked.

### 2. Deny Root User Actions

Root should never be used for day-to-day operations. Lock it down at the org level:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyRootActions",
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*",
      "Condition": {
        "StringLike": {
          "aws:PrincipalArn": "arn:aws:iam::*:root"
        }
      }
    }
  ]
}
```

See also: [How to Detect AWS Root Account Usage (And Respond to It)](/posts/detect-root-account-usage/) for the monitoring side of this.

### 3. Restrict Allowed Regions

If you only operate in `eu-west-1` and `us-east-1`, there's no reason to allow resources in `ap-southeast-1`. Restrict regions to reduce your attack surface:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyNonApprovedRegions",
      "Effect": "Deny",
      "NotAction": [
        "iam:*",
        "organizations:*",
        "sts:*",
        "support:*",
        "budgets:*",
        "cloudfront:*",
        "route53:*",
        "wafv2:*"
      ],
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "aws:RequestedRegion": [
            "eu-west-1",
            "us-east-1"
          ]
        }
      }
    }
  ]
}
```

The `NotAction` list includes global services that don't operate in a specific region — IAM, Organizations, STS, and others. If you skip these, you'll break basic account functionality.

### 4. Protect Security Tooling

Prevent anyone from disabling CloudTrail, GuardDuty, or Security Hub — the services you rely on to detect incidents:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "ProtectSecurityServices",
      "Effect": "Deny",
      "Action": [
        "cloudtrail:StopLogging",
        "cloudtrail:DeleteTrail",
        "guardduty:DeleteDetector",
        "guardduty:DisassociateFromMasterAccount",
        "securityhub:DisableSecurityHub",
        "config:StopConfigurationRecorder",
        "config:DeleteConfigurationRecorder"
      ],
      "Resource": "*"
    }
  ]
}
```

### 5. Require Encryption on S3 and EBS

Enforce encryption at the org level so no one can accidentally create unencrypted storage:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyUnencryptedS3",
      "Effect": "Deny",
      "Action": "s3:PutObject",
      "Resource": "*",
      "Condition": {
        "StringNotEquals": {
          "s3:x-amz-server-side-encryption": [
            "AES256",
            "aws:kms"
          ]
        }
      }
    },
    {
      "Sid": "DenyUnencryptedEBS",
      "Effect": "Deny",
      "Action": "ec2:CreateVolume",
      "Resource": "*",
      "Condition": {
        "Bool": {
          "ec2:Encrypted": "false"
        }
      }
    }
  ]
}
```

### 6. Prevent Accounts from Leaving the Organization

Simple but important — don't let anyone detach an account from your org:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyLeaveOrg",
      "Effect": "Deny",
      "Action": "organizations:LeaveOrganization",
      "Resource": "*"
    }
  ]
}
```

---

## The Break-Glass Pattern

Every SCP strategy needs an escape hatch. If you lock things down too tightly and something breaks in production at 2 AM, you need a way to act fast without dismantling your policies.

The approach that worked for us: a **break-glass IAM role** deployed to every account, accessible only by the DevOps team (our first responders for incidents). This role was excluded from restrictive SCPs using a condition:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenySomethingExceptBreakGlass",
      "Effect": "Deny",
      "Action": "...",
      "Resource": "*",
      "Condition": {
        "ArnNotLike": {
          "aws:PrincipalArn": "arn:aws:iam::*:role/BreakGlassRole"
        }
      }
    }
  ]
}
```

Add this condition to your most restrictive SCPs so the break-glass role can bypass them when needed. Then wrap the role assumption with CloudTrail alerting (see [AWS Incident Response Scenarios](/posts/aws-incident-response-scenarios/) for examples) — every time someone assumes it, you want to know about it.

A break-glass role that's used regularly isn't a break-glass role — it's a shadow admin. Monitor usage and investigate every assumption.

---

## Lessons Learned the Hard Way

### Don't Use SCPs to Fix Human Behavior

This is the biggest lesson I took away from managing SCPs across a real organization.

We had engineers creating IAM users with admin privileges to bypass restrictions. The instinct was to write an SCP blocking `iam:CreateUser` or denying admin policy attachments. And we tried it.

It didn't work. Not technically — the SCP worked fine. But it created a worse problem: engineers felt suffocated, started looking for other workarounds, and trust between security and engineering eroded.

What actually fixed it was **talking to people**. I met with each team lead, learned what AWS services they actually needed, and enabled those services for their accounts. We also created a **sandbox account per team** — near-admin access, minimal restrictions, no production data. Engineers could prototype freely and push to production through the proper channels.

The result: the admin-user creation stopped. Not because we blocked it, but because people didn't need to do it anymore.

**SCPs are for preventing accidents and enforcing compliance boundaries — not for policing behavior.** If you find yourself writing SCPs to stop people from doing things, the real problem is usually a gap in permissions, process, or communication.

### Watch Your Limits

SCP limits are poorly documented and will bite you when you least expect it.

The ones that caught us off guard:
- **5 SCPs per OU** (attached directly — inherited SCPs from parent OUs also count toward your effective policy)
- **5,120 characters per SCP** (including whitespace — minify your policies)
- **Inherited SCPs stack** — if your root OU has 3 SCPs and a child OU has 3, that child effectively has 6. Plan your OU hierarchy with this in mind

The character limit is the most painful. You'll start with clean, readable policies and eventually need to combine multiple statements into a single SCP just to stay under the limit. Use short `Sid` values and strip unnecessary whitespace when you hit the wall.

### Test SCPs in a Sandbox OU First

Never attach a new SCP directly to a production OU. Create a `Test` or `Sandbox` OU, move a non-critical account into it, attach the SCP, and verify nothing breaks.

Even better: use [AWS IAM Policy Simulator](https://policysim.aws.amazon.com/) to validate the expected behavior before deploying. Though be aware that the simulator doesn't perfectly replicate SCP evaluation in all cases — real-world testing is still necessary.

### Use Deny Lists, Not Allow Lists

AWS recommends (and defaults to) a deny-list strategy: start with the `FullAWSAccess` SCP and add explicit denies. The alternative — removing `FullAWSAccess` and writing explicit allows — sounds more secure, but it's an operational nightmare.

With an allow-list approach, every new AWS service your team needs requires an SCP change. With deny-lists, you only write policies for what you want to block. For most organizations, deny-lists strike the right balance between security and velocity.

---

## Recommended OU Structure for SCPs

How you organize your OUs directly impacts how SCPs inherit. Here's a practical structure:

```
Root
├── Security OU          (logging, audit, security tooling accounts)
├── Infrastructure OU    (shared services, networking)
├── Workloads OU
│   ├── Production OU    (strictest SCPs)
│   └── Development OU   (relaxed SCPs)
├── Sandbox OU           (minimal restrictions, no prod data)
└── Suspended OU         (deny-all SCP for decommissioned accounts)
```

Apply your most restrictive SCPs at the Root level (external access block, region restrictions, org-leave denial). Then layer additional restrictions on Production and relax them on Sandbox.

The **Suspended OU** is often overlooked — when you need to decommission an account, move it here with a deny-all SCP instead of deleting it. This preserves audit history while ensuring zero access.

---

## Quick Reference

| SCP | Where to attach | Priority |
|---|---|---|
| Block external access (`PrincipalOrgID`) | Root | Day 1 |
| Deny root user actions | Root | Day 1 |
| Restrict regions | Root | Day 1 |
| Prevent leaving org | Root | Day 1 |
| Protect security tooling | Root | Day 1 |
| Require encryption | Workloads OU | Week 1 |
| Break-glass exemptions | Where restrictive SCPs live | Day 1 |

---

## Related Resources

- [AWS Security Checklist 2026](/posts/aws-security-checklist-2026/) — broader security controls including SCPs
- [How to Detect Root Account Usage](/posts/detect-root-account-usage/) — monitoring complement to the root-deny SCP
- [IAM Users Are Dead: Modern AWS Access Control](/posts/aws-iam-users-alternatives/) — why Identity Center replaces IAM users
- [AWS Incident Response Scenarios](/posts/aws-incident-response-scenarios/) — detection and response patterns for break-glass monitoring
