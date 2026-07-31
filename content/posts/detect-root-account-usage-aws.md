---
title: "How to Detect AWS Root Account Usage (And Respond to It)"
date: 2025-04-21
tags: ["aws", "security", "root-account", "eventbridge", "monitoring", "sns", "cloudtrail"]
keywords: ["detect root account usage aws", "aws root login alert", "eventbridge root detection", "aws root account monitoring", "cloudtrail root user"]
categories: ["Cloud Security", "Detection"]
summary: "Detect and alert on AWS root account usage using CloudTrail, EventBridge, SNS, and optional Slack notifications. Step-by-step setup with CLI commands and Terraform included."
description: "Step-by-step root account detection with EventBridge, SNS, and Slack alerts — CLI commands and Terraform included. Plus what to do when the alert fires."
slug: "detect-root-account-usage"
draft: false
author: "Javier Pulido"
canonicalURL: "https://thehiddenport.dev/posts/detect-root-account-usage/"
lastmod: 2026-07-31
enable_comments: true
---

In a secure AWS setup, the root user should almost never be used. It bypasses every IAM guardrail in the account — SCPs don't apply to it, permission boundaries don't scope it, and a compromised root account means full control over everything.

The first check on every security audit I run is whether root account usage generates an alert. In most accounts, it doesn't. Here's how to set it up in under 15 minutes.

---

## What We Want to Detect

- **Any API call** made by the root user — `CreateUser`, `StartInstances`, `PutBucketPolicy`, anything
- **Especially sensitive actions** like `DeleteTrail`, `CreateAccessKey`, or `UpdateAccountPasswordPolicy`
- **Console sign-ins** by root — even just logging in warrants review

CloudTrail captures all of these. We route them through EventBridge to trigger an alert.

---

## Step 1: Verify CloudTrail Is Logging

CloudTrail must be enabled and logging management events. Most accounts have a default trail, but verify:

```bash
# Check for an active multi-region trail
aws cloudtrail describe-trails \
  --query 'trailList[?IsMultiRegionTrail==`true`].{Name:Name,Bucket:S3BucketName,IsLogging:HomeRegion}' \
  --output table

# Verify it's actually logging
aws cloudtrail get-trail-status --name <trail-name> --query 'IsLogging'
```

If no trail exists:

```bash
aws cloudtrail create-trail \
  --name security-trail \
  --s3-bucket-name your-cloudtrail-bucket \
  --is-multi-region-trail \
  --enable-log-file-validation

aws cloudtrail start-logging --name security-trail
```

---

## Step 2: Create an SNS Topic for Alerts

```bash
aws sns create-topic --name root-usage-alerts

# Subscribe your email
aws sns subscribe \
  --topic-arn arn:aws:sns:us-east-1:123456789012:root-usage-alerts \
  --protocol email \
  --notification-endpoint security-team@example.com
```

Confirm the subscription from your inbox before proceeding.

---

## Step 3: Create the EventBridge Rule

This rule matches any event where the root user is the caller:

```bash
aws events put-rule \
  --name DetectRootUserUsage \
  --event-pattern '{
    "detail": {
      "userIdentity": {
        "type": ["Root"]
      }
    }
  }' \
  --state ENABLED
```

Add the SNS topic as the target:

```bash
aws events put-targets \
  --rule DetectRootUserUsage \
  --targets '[{
    "Id": "RootAlertTarget",
    "Arn": "arn:aws:sns:us-east-1:123456789012:root-usage-alerts"
  }]'
```

Grant EventBridge permission to publish to the SNS topic:

```bash
aws sns set-topic-attributes \
  --topic-arn arn:aws:sns:us-east-1:123456789012:root-usage-alerts \
  --attribute-name Policy \
  --attribute-value '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": { "Service": "events.amazonaws.com" },
      "Action": "sns:Publish",
      "Resource": "arn:aws:sns:us-east-1:123456789012:root-usage-alerts"
    }]
  }'
```

---

## Optional: Route Alerts to Slack

Email alerts work but get buried. The same EventBridge → Lambda → Slack pattern used for [GuardDuty alerts](/posts/aws-guardduty-setup/) and [Secrets Manager notifications](/posts/aws-secrets-manager-eventbridge-notifications/) works here:

```python
import json
import urllib3
import os

http = urllib3.PoolManager()
SLACK_WEBHOOK = os.environ["SLACK_WEBHOOK_URL"]

def lambda_handler(event, context):
    event_name = event["detail"].get("eventName", "Unknown")
    source_ip = event["detail"].get("sourceIPAddress", "Unknown")
    region = event["region"]
    time = event["time"]

    message = {
        "text": f":rotating_light: *Root account used*\n*Action:* `{event_name}`\n*Source IP:* {source_ip}\n*Region:* {region}\n*Time:* {time}"
    }

    http.request(
        "POST",
        SLACK_WEBHOOK,
        body=json.dumps(message),
        headers={"Content-Type": "application/json"}
    )
```

Set the EventBridge rule to target this Lambda instead of (or in addition to) SNS.

---

## Terraform

```hcl
resource "aws_cloudwatch_event_rule" "root_usage" {
  name        = "detect-root-user-usage"
  description = "Fires on any API call or console sign-in by the root user"

  event_pattern = jsonencode({
    detail = {
      userIdentity = {
        type = ["Root"]
      }
    }
  })
}

resource "aws_sns_topic" "root_alerts" {
  name = "root-usage-alerts"
}

resource "aws_sns_topic_policy" "allow_eventbridge" {
  arn = aws_sns_topic.root_alerts.arn

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "events.amazonaws.com" }
      Action    = "sns:Publish"
      Resource  = aws_sns_topic.root_alerts.arn
    }]
  })
}

resource "aws_cloudwatch_event_target" "root_alert_sns" {
  rule      = aws_cloudwatch_event_rule.root_usage.name
  target_id = "send-to-sns"
  arn       = aws_sns_topic.root_alerts.arn
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.root_alerts.arn
  protocol  = "email"
  endpoint  = "security-team@example.com"
}
```

---

## How to Test It

Trigger a benign root action to verify the pipeline works:

```bash
# Sign in as root, then run any read-only API call
aws sts get-caller-identity
```

You should see an alert within a few minutes. If not, check:
- CloudTrail is logging (`get-trail-status`)
- The EventBridge rule is enabled (`describe-rule`)
- The SNS subscription is confirmed (check your inbox)

---

## When the Alert Fires: Response Steps

Root usage is always worth investigating. When you get an alert:

1. **Check the event in CloudTrail** — what action was taken, from what IP, at what time?
2. **Determine if it was legitimate** — did someone on the team use root for a valid reason (billing, support case)?
3. **If unauthorized**: rotate root credentials immediately, enable MFA if not already set, and check for persistence (new IAM users, access keys, or modified trust policies)
4. **Document and close** — even legitimate root usage should be logged and reviewed

For a full incident response workflow, see the [IR scenarios guide](/posts/aws-incident-response-scenarios/).

---

## Prevention: Reduce Root Usage to Zero

Detection is the safety net, but the goal is to make root usage unnecessary:

- **Enable MFA** on root — phishing-resistant (YubiKey, FIDO2), not a phone app
- **Delete root access keys** if any exist
- **Use IAM Identity Center** for all human access — [stop creating IAM users](/posts/aws-iam-users-alternatives/)
- **Apply SCPs** to deny root actions at the org level — the [SCP best practices guide](/posts/aws-scp-best-practices/) covers this pattern

---

## Related Reading

- [AWS SCPs That Actually Work](/posts/aws-scp-best-practices/) — deny root actions at the org level so detection becomes your safety net, not your only defense
- [CloudTrail Log Analysis: How to Find Who Did What](/posts/aws-cloudtrail-log-analysis/) — Athena queries for investigating root activity
- [AWS Security Checklist: 30-Minute Account Review](/posts/aws-security-checklist-2026/) — root account hardening is check #1
- [Detect AWS IAM Privilege Escalation](/posts/aws-detecting-privilege-escalation/) — the next detection to set up after root monitoring
- [AWS Incident Response: 5 Scenarios & How to Contain Them](/posts/aws-incident-response-scenarios/) — what to do when a detection fires
- [GuardDuty Runtime Monitoring](/posts/aws-guardduty-runtime-monitoring/) — complements CloudTrail-based detection with process-level visibility
