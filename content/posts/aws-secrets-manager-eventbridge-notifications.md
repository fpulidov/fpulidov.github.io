---
title: "AWS Secrets Manager Now Sends Events to EventBridge: How to Set Up Rotation Alerts"
date: 2026-07-25
draft: false
description: "Secrets Manager now publishes secret change events to EventBridge automatically — no CloudTrail workarounds needed. Here's how to set up alerts for rotation failures, stale secrets, and unexpected changes."
slug: "aws-secrets-manager-eventbridge-notifications"
tags: ["AWS", "Security", "Secrets Manager", "EventBridge", "Automation", "Monitoring"]
keywords: ["aws secrets manager eventbridge", "secrets manager notifications", "secret rotation alerts", "aws secrets manager events", "secrets manager monitoring", "aws secret rotation eventbridge", "secrets manager update notifications"]
categories: ["Cloud Security"]
canonicalURL: "https://thehiddenport.dev/posts/aws-secrets-manager-eventbridge-notifications/"
enable_comments: true
---

As of July 2026, AWS Secrets Manager automatically publishes events to Amazon EventBridge whenever a secret value changes. No opt-in, no configuration, no extra cost. This is a significant improvement for anyone monitoring credential rotation or building event-driven security workflows.

Before this, detecting secret changes meant parsing CloudTrail logs and correlating multiple API calls (`PutSecretValue`, `UpdateSecretValue`, rotation success/failure) — doable but brittle. Now you get a single, clean event on the default EventBridge bus every time a secret changes.

Here's how to set it up and what to do with it.

---

## What Changed

Previously, Secrets Manager had no native notification mechanism for secret value changes. You had two options:

1. **CloudTrail + EventBridge** — create a rule matching `PutSecretValue` or `RotationSucceeded` API calls in CloudTrail. This works but requires filtering through noisy CloudTrail data and handling multiple event types.
2. **Polling** — periodically call `DescribeSecret` or `GetSecretValue` to check for changes. Wasteful and slow.

Now, Secrets Manager emits events directly to EventBridge's default event bus. The event fires on any active secret value change — whether from manual updates, automated rotation, or API calls. One event, one signal, no correlation needed.

---

## Setting Up EventBridge Rules

### Console

1. Go to **Amazon EventBridge → Rules → Create rule**
2. Event bus: **default**
3. Rule type: **Rule with an event pattern**
4. Event source: **AWS events**
5. Event pattern:

```json
{
  "source": ["aws.secretsmanager"],
  "detail-type": ["Secret Value Updated"]
}
```

6. Select your target (SNS topic, Lambda function, SQS queue, etc.)
7. Create the rule

### Terraform

```hcl
resource "aws_cloudwatch_event_rule" "secret_changed" {
  name        = "secrets-manager-value-changed"
  description = "Fires when any Secrets Manager secret value is updated"

  event_pattern = jsonencode({
    source      = ["aws.secretsmanager"]
    detail-type = ["Secret Value Updated"]
  })
}

resource "aws_cloudwatch_event_target" "notify_sns" {
  rule      = aws_cloudwatch_event_rule.secret_changed.name
  target_id = "send-to-sns"
  arn       = aws_sns_topic.security_alerts.arn
}

resource "aws_sns_topic" "security_alerts" {
  name = "security-alerts"
}

resource "aws_sns_topic_policy" "allow_eventbridge" {
  arn = aws_sns_topic.security_alerts.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = { Service = "events.amazonaws.com" }
        Action    = "sns:Publish"
        Resource  = aws_sns_topic.security_alerts.arn
      }
    ]
  })
}
```

### Filtering by Specific Secrets

If you only care about certain secrets (e.g., production database credentials), add a filter to the event pattern:

```json
{
  "source": ["aws.secretsmanager"],
  "detail-type": ["Secret Value Updated"],
  "detail": {
    "secretId": ["arn:aws:secretsmanager:us-east-1:123456789012:secret:prod/db-*"]
  }
}
```

This avoids alerting on every dev/test secret change.

---

## Route Alerts to Slack

Most teams want secret change notifications in Slack, not email. The pattern is the same one used for [GuardDuty alerts](/posts/aws-guardduty-setup/) — EventBridge → Lambda → Slack webhook.

```python
import json
import urllib3
import os

http = urllib3.PoolManager()
SLACK_WEBHOOK = os.environ["SLACK_WEBHOOK_URL"]

def lambda_handler(event, context):
    secret_id = event["detail"]["secretId"]
    region = event["region"]
    time = event["time"]

    message = {
        "text": f":rotating_light: Secret value changed\n*Secret:* `{secret_id}`\n*Region:* {region}\n*Time:* {time}"
    }

    http.request(
        "POST",
        SLACK_WEBHOOK,
        body=json.dumps(message),
        headers={"Content-Type": "application/json"}
    )
```

Deploy this as a Lambda function, set the EventBridge rule target to it, and store the Slack webhook URL as — naturally — a Secrets Manager secret.

---

## Practical Use Cases

### 1. Rotation Failure Detection

Secret rotation can fail silently. The application keeps using the old credential until it expires, then breaks at 2am. With EventBridge notifications, you can detect when a rotation *should* have happened but didn't:

- Set up a scheduled EventBridge rule that runs daily
- The Lambda checks `DescribeSecret` for secrets where `LastRotatedDate` is older than the rotation schedule
- If a secret is overdue, alert

The new change events complement this — you get notified when rotation succeeds, and the absence of that notification tells you something failed.

### 2. Unexpected Manual Changes

In a mature environment, secrets should only change via automated rotation. A manual `PutSecretValue` call could mean:

- Someone bypassed the rotation process
- A credential was compromised and force-rotated
- An unauthorized change

The EventBridge event lets you flag manual changes for review, especially in production accounts.

### 3. Cache Invalidation

Applications that cache database credentials or API keys locally can subscribe to the EventBridge event and refresh their cache immediately instead of waiting for the next polling interval. This reduces the window where stale credentials cause errors after rotation.

### 4. Compliance Logging

For audits that require proof of credential rotation, the EventBridge events provide a clean, timestamped record. Route them to S3 or your SIEM for long-term storage.

---

## Cost

Zero additional cost. The events publish to the default EventBridge bus automatically. You only pay for:

- **EventBridge rules** — free for AWS service events
- **Targets** — whatever Lambda/SNS/SQS costs you incur from processing the events

If you're already running EventBridge rules for GuardDuty or CloudTrail, adding a Secrets Manager rule costs nothing extra.

---

## What This Doesn't Cover

A few things to keep in mind:

- **This is not rotation monitoring** — the event fires when a value *changes*, not when rotation *runs*. A rotation that fails before updating the value won't trigger the event.
- **No event for secret deletion** — use CloudTrail for `DeleteSecret` monitoring.
- **No event for access** — `GetSecretValue` calls don't generate EventBridge events. Use CloudTrail for access auditing.

For comprehensive secrets monitoring, combine EventBridge events (value changes) with CloudTrail (access and deletion) and Config rules (encryption and rotation policy compliance).

---

## Key Takeaway

This is one of those small AWS updates that removes a real pain point. Secret rotation monitoring used to require CloudTrail gymnastics. Now it's a five-minute EventBridge rule. If you're running any kind of security monitoring in AWS, add this rule — it's free, it's automatic, and the first time it catches a failed rotation before your application breaks, it'll have been worth it.

---

**Related guides:**
- [AWS GuardDuty Setup: Route Findings to Slack & Your SIEM in 10 Minutes](/posts/aws-guardduty-setup/) — same EventBridge → Slack pattern for threat detection
- [GuardDuty vs Security Hub: What Each Does and When You Need Both](/posts/aws-guardduty-vs-security-hub/) — how Secrets Manager monitoring fits into your broader security stack
- [AWS Security Monitoring Without the Enterprise Price Tag](/posts/affordable-aws-security-monitoring/) — build a full monitoring stack including secret rotation alerts
- [AWS Misconfigurations I Find in Every Security Audit](/posts/aws-security-misconfigurations-guide/) — missing rotation monitoring is one of the common gaps
