---
title: "Detecting Privilege Escalation in AWS Using CloudTrail and EventBridge"
description: "Learn how to detect IAM privilege escalation attempts in AWS using CloudTrail logs, EventBridge rules, and practical detection engineering strategies. Includes examples, alerting techniques, and real-world API call patterns."
summary: "A deep technical guide to setting up AWS-native detection for privilege escalation using CloudTrail, EventBridge, and minimal infrastructure."
date: 2025-06-20
tags: ["AWS", "IAM", "CloudTrail", "EventBridge", "Detection", "Security"]
canonicalURL: "https://thehiddenport.dev/posts/aws-detecting-privilege-escalation-cloudtrail-eventbridge/"
---

# Detecting Privilege Escalation in AWS Using CloudTrail and EventBridge

One of the most dangerous threats in an AWS environment is **privilege escalation**—when an entity (a user, role, or service) gains more permissions than it should, either by misconfiguration or abuse. Detecting these escalation attempts is essential to protecting your cloud environment.

AWS does not provide out-of-the-box detection for many of these patterns, but with **CloudTrail**, **EventBridge**, and some **detection engineering**, you can build native alerts for high-risk API calls that indicate an escalation in progress—or one about to happen.

This article will dive deep into:
- Why privilege escalation is critical
- How attackers typically escalate privileges in AWS
- Which CloudTrail events to monitor
- How to configure EventBridge to catch suspicious patterns
- How to alert in real-time (SNS, Lambda, etc.)
- Caveats and tuning recommendations

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
````

---

## Creating Detection Rules with EventBridge

EventBridge can subscribe to the CloudTrail event stream and match on **suspicious API calls**. You can then trigger notifications or automated actions.

### Rule Example: Detect AttachUserPolicy

```json
{
  "source": ["aws.iam"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventName": ["AttachUserPolicy", "PutUserPolicy"],
    "requestParameters.policyArn": [{
      "prefix": "arn:aws:iam::aws:policy/AdministratorAccess"
    }]
  }
}
```

This rule matches when someone attaches `AdministratorAccess` to themselves (or anyone).

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

If this post interests you, check these out:

* [Enforcing Least Privilege in AWS IAM](/posts/aws-enforcing-least-privilege/)
* [AWS Incident Response Toolkit](/posts/aws-ir-toolkit/)
* [Securing EC2 Access with AWS Systems Manager](/posts/aws-securing-ec2-access-with-ssm/)
* [AWS Security Checklist 2025](/posts/aws-security-checklist-2025/)

---

## Conclusion

Privilege escalation is one of the most critical actions you need to monitor in AWS. While AWS provides the logs (via CloudTrail), it’s your responsibility to wire up detection logic. Thankfully, with **EventBridge** and **a few well-designed rules**, you can begin detecting these escalation attempts in near real-time.

Even a single detection rule—targeting `AttachUserPolicy` with `AdministratorAccess`—can surface abuse before it becomes a breach.

Don’t wait for an incident to act. Harden your detection stack today.

---