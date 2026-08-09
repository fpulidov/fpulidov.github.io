---
title: "Detect AWS IAM Privilege Escalation with CloudTrail"
description: "How to detect IAM privilege escalation in AWS using CloudTrail events, EventBridge rules, and real-world API patterns. Includes alerting setup and Terraform."
summary: "Set up AWS-native detection for privilege escalation using CloudTrail, EventBridge, and minimal infrastructure. Real API patterns and alerting included."
date: 2025-06-20
tags: ["AWS", "IAM", "CloudTrail", "EventBridge", "Detection", "Security"]
keywords: ["iam privilege escalation", "aws privilege escalation detection", "cloudtrail iam monitoring", "eventbridge security rules", "aws iam attack detection"]
categories: ["Cloud Security"]
canonicalURL: "https://thehiddenport.dev/posts/aws-detecting-privilege-escalation/"
aliases: ["/posts/aws-detecting-privilege-escalation-cloudtrail-eventbridge/"]
lastmod: 2026-07-29
enable_comments: true
---

Privilege escalation — when an entity gains more permissions than it should — is one of the most dangerous patterns in AWS. An attacker with read-only access who can attach `AdministratorAccess` to their own role has effectively rooted your account.

AWS doesn't detect most of these patterns out of the box. GuardDuty catches some credential abuse, but the IAM-level escalation paths — `AttachUserPolicy`, `PutRolePolicy`, `PassRole` chains — fly under the radar unless you build your own detection.

With **CloudTrail**, **EventBridge**, and a handful of rules, you can alert on these escalation attempts in near real-time using only native AWS services.

---

## Why Privilege Escalation Matters in AWS

Unlike traditional infrastructure, in AWS **permissions are programmable**, and every misstep can have systemic impact. Privilege escalation is not theoretical—it has been exploited both in internal red team exercises and real-world attacks.

For example, an attacker with limited access to Lambda functions might:
- Modify an existing function to assume a high-privilege IAM role
- Add a new inline policy to their own user
- Or pass an admin role to an EC2 instance they control

All of these leave traces in **CloudTrail**—if you're watching.

---

## Common Privilege Escalation Techniques in AWS

Most escalation paths involve IAM or STS actions. Here are common patterns:

| Action | What It Does |
|--------|--------------|
| `iam:AttachUserPolicy` / `AttachRolePolicy` | Grants an existing policy to a principal |
| `iam:PutUserPolicy` / `PutRolePolicy` | Creates an inline policy (can contain anything) |
| `iam:PassRole` + `ec2:RunInstances` | Launches EC2 with powerful role attached |
| `lambda:UpdateFunctionCode` + `iam:PassRole` | Runs arbitrary code under elevated permissions |
| `sts:AssumeRole` | Switches identity if allowed by trust policy |
| `iam:CreatePolicyVersion` | May set an older, more permissive version as active |

Even if you're using SCPs or guardrails, these events are useful for threat hunting or detection.

---

## CloudTrail Configuration

Ensure you have:
- **CloudTrail enabled in all regions**
- Logging for **management events**
- Optionally delivering to an S3 bucket and integrated with CloudWatch Logs to bypass the 90 day retention limit of Cloudtrail

All of the mentioned escalation actions are **management events**, and appear in CloudTrail as part of the `eventName` field.

Example CloudTrail log (truncated):

```json
{
  "eventName": "AttachUserPolicy",
  "eventSource": "iam.amazonaws.com",
  "userIdentity": {
    "type": "IAMUser",
    "userName": "alice"
  },
  "requestParameters": {
    "userName": "alice",
    "policyArn": "arn:aws:iam::aws:policy/AdministratorAccess"
  },
  ...
}
```

---

## Creating Detection Rules with EventBridge

EventBridge can subscribe to the CloudTrail event stream and match on **suspicious API calls**. You can then trigger notifications or automated actions.

### Rule Example: Detect AttachUserPolicy

```json
{
  "source": ["aws.iam"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventName": ["AttachUserPolicy", "AttachRolePolicy", "PutUserPolicy", "PutRolePolicy"],
    "requestParameters": {
      "policyArn": [{
        "prefix": "arn:aws:iam::aws:policy/AdministratorAccess"
      }]
    }
  }
}
```

This rule matches when someone attaches `AdministratorAccess` to any user or role. The `requestParameters` must be nested (not dot-notation) for EventBridge to match correctly. Note that `PutUserPolicy` and `PutRolePolicy` (inline policies) won't have a `policyArn` — they'll match on `eventName` alone, which is what you want since any inline policy creation warrants review.

### Other Useful Event Names to Watch

* `CreatePolicy`
* `CreatePolicyVersion`
* `SetDefaultPolicyVersion`
* `PutRolePolicy`
* `PassRole`
* `AssumeRole`

If you’re watching cross-service escalation:

* `RunInstances` (check if `iam:PassRole` was used)
* `UpdateFunctionCode` (especially if the Lambda uses an elevated role)

---

## Alerting via SNS or Lambda

Once your EventBridge rule matches, you can:

* Trigger an **SNS notification** (email, Slack, SMS)
* Invoke a **Lambda function** that writes to a SIEM, sends to Discord, or logs to S3
* Write to **CloudWatch Logs** for later review

### Example: Send to SNS

```json
{
  "State": "ENABLED",
  "Targets": [
    {
      "Arn": "arn:aws:sns:us-east-1:111122223333:PrivEscAlerts",
      "Id": "PrivEscAlertTarget"
    }
  ]
}
```

---

## Tuning and Limitations

### False Positives

* Some actions might be part of normal automation pipelines
* Devs might update Lambda or IAM configs legitimately

You can reduce noise by:

* Filtering on `userIdentity.principalId` or `userName`
* Excluding known automation roles (with conditions in EventBridge)
* Only alerting on attachments of *privileged* policies (e.g., `AdministratorAccess`, `PowerUserAccess`)

### Blind Spots

* **Inline policy abuse** might not be obvious
* If CloudTrail isn’t enabled in all regions, you’ll miss stuff
* Identity switching (`sts:AssumeRole`) requires combining multiple events to trace the full chain

---

## Related Reading

- [IAM Least Privilege in AWS: Access Analyzer Guide](/posts/iam-access-analyzer-least-privilege/) — tighten the permissions these detections are watching for
- [Enforcing Least Privilege in AWS IAM](/posts/aws-enforcing-least-privilege/) — the workflow for auditing and pruning IAM policies
- [CloudTrail Log Analysis: How to Find Who Did What](/posts/aws-cloudtrail-log-analysis/) — Athena queries for investigating the events these detections surface
- [AWS Incident Response: 5 Scenarios & How to Contain Them](/posts/aws-incident-response-scenarios/) — what to do when a detection fires
- [GuardDuty Runtime Monitoring: The Security Agent That Sees Inside Your Workloads](/posts/aws-guardduty-runtime-monitoring/) — complements IAM-level detection with process-level visibility
- [AWS Security Checklist: 30-Minute Account Review](/posts/aws-security-checklist-2026/) — quick self-audit to check your detection coverage