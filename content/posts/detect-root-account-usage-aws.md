---
title: "How to Detect AWS Root Account Usage (And Respond to It)"
date: 2025-04-21
tags: ["aws", "security", "root-account", "eventbridge", "monitoring", "sns", "cloudtrail"]
categories: ["Cloud Security", "Detection"]
summary: "Root account usage in AWS is rare—and dangerous. Learn how to detect it in real time and set up alerts using EventBridge, SNS, and optional Lambda or Slack integration."
description: "This guide walks you through detecting and responding to AWS root account usage using CloudTrail, EventBridge, SNS, and optionally Lambda or Slack. Includes Terraform examples and AWS Console workflows."
slug: "detect-root-account-usage"
draft: false
author: "Javier Pulido"
canonicalURL: "https://thehiddenport.dev/detect-root-account-usage"
---

## Why Root Account Usage Should Raise an Alarm

In a secure AWS setup, the root user should almost never be used. It has unrestricted access to everything in the account, and actions taken with it can’t be scoped or logged per identity.

If your root user performs any API call, it’s almost always worth reviewing.

---

## What We Want to Detect

- **Any API call** made by the root user (e.g., `CreateUser`, `StartInstances`, etc.)
- **Especially sensitive actions** like `UpdateAccountPasswordPolicy`, `CreateAccessKey`, or `DeleteTrail`

CloudTrail captures these events, and we can route them into EventBridge to trigger an alert.

---

## Solution Overview

- **CloudTrail** logs all management events
- **EventBridge Rule** matches events made by the root user
- **SNS Topic** or **Lambda Function** sends alerts (email, Slack, etc.)

---

## Step 1: Enable CloudTrail

CloudTrail must be enabled and logging to an S3 bucket in your account.

> Most accounts have a default trail. If not:
- Go to **CloudTrail > Trails**
- Create a new multi-region trail
- Enable **management events**

---

## Step 2: Create an EventBridge Rule for Root User Events

### In the Console:

1. Go to **EventBridge > Rules**
2. Click **Create rule**
3. Name your rule (e.g., `DetectRootUserUsage`)
4. Choose **Event Source: AWS events**
5. Under **Event pattern**, choose **Custom pattern** and paste:

```json
{
  "detail": {
    "userIdentity": {
      "type": ["Root"]
    }
  }
}
```

6. **Target:** Choose **SNS topic** (or Lambda if you require some formatting text or to write to Slack for example)

---

## Step 3: Create SNS Topic and Email Subscription

### In the Console:

1. Go to **SNS > Topics > Create topic**
2. Choose **Standard**, name it `root-usage-alerts`
3. Create a **subscription** to this topic (email)
4. Confirm the subscription from your inbox

---

## Optional: Send Slack Alert via Lambda

If you prefer Slack notifications instead of email:

- Create a simple Lambda function that posts to Slack using a webhook
- Set your EventBridge rule target to that Lambda

This allows formatting and routing alerts into your team's incident channel.

---

## How to Test It

Use the AWS root account to perform a benign action (e.g., visit the Billing Dashboard).

You should see an alert shortly after in your email or Slack.

---

## Best Practices

- **Lock away your root credentials** in a secure vault (not used for daily access)
- **Enable MFA** on root — ideally phishing-resistant (YubiKey, FIDO2)
- **Delete root access keys** if they exist
- **Regularly review CloudTrail and GuardDuty findings**

---

## Final Thoughts

If you're detecting root usage in AWS — that's a signal. Either something's misconfigured, or something's wrong. By setting up this detection and alerting pipeline, you can react quickly and minimize risk.

In future guides, we'll build on this with incident response workflows and automated remediations.

