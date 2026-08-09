---
title: "AWS Incident Response Toolkit: Playbook, Terraform Automation & Forensic Tools"
description: "Free toolkit with an IR playbook template, Terraform-deployed notification pipeline, Lambda functions for SES and Slack alerts, and a forensic tool matrix — everything you need to respond to AWS security incidents."
date: 2025-05-20
summary: "A complete incident response toolkit for AWS — playbook template, Terraform notification pipeline, Lambda alert functions, and a forensic tool reference. Free download."
tags: ["aws", "security", "incident-response", "toolkit"]
keywords: ["aws incident response toolkit", "aws ir tools", "incident response templates", "aws security toolkit", "ir automation aws", "aws incident response playbook", "security hub notifications terraform"]
slug: "aws-ir-toolkit"
aliases: ["/posts/aws-ir-playbook-template/"]
canonicalURL: "https://thehiddenport.dev/posts/aws-ir-toolkit/"
enable_comments: true
---

When a Security Hub finding fires at 2am, the last thing you want is to be piecing together a response process from scratch — figuring out who to notify, what to isolate, and where to look for evidence.

I built this toolkit after going through that exact situation too many times. It's the set of templates, automation, and reference material I wish I'd had from day one.

---

## What's in the Toolkit

### IR Playbook Template (PDF)

A printable, checklist-style playbook covering the five standard IR phases, aligned to ISO 27001 and AWS-native workflows:

1. **Preparation** — roles (Incident Commander, Comms Lead, IR Engineer), CloudTrail/GuardDuty/Config prerequisites, forensic IAM roles, asset documentation
2. **Detection & Analysis** — trigger sources (Security Hub, GuardDuty), CloudTrail correlation, resource identification, volatile data capture via SSM
3. **Containment** — security group isolation, credential revocation, IAM suspension
4. **Eradication & Recovery** — patching, secret rotation, re-imaging, backup restoration
5. **Lessons Learned** — post-mortem, root cause documentation, playbook updates, stakeholder debrief

Each phase has checkboxes you can print and use during an active incident.

### Notification Pipeline (Terraform + Lambda)

Deployable automation that routes Security Hub findings to your team:

```
Security Hub → EventBridge → Lambda → SES Email / Slack
```

The Terraform code creates everything in one `terraform apply`:

- **EventBridge rule** — matches findings with severity >= MEDIUM, compliance status FAILED, workflow status NEW
- **Lambda function** — extracts finding metadata and sends a formatted email via SES, then marks the finding as NOTIFIED to prevent duplicate alerts
- **IAM role** — least-privilege permissions for SES and Security Hub only
- **CloudWatch log group** — 14-day retention for Lambda logs

The EventBridge rule pattern filters on severity and compliance status so you don't get paged for every informational finding:

```hcl
event_pattern = jsonencode({
  source      = ["aws.securityhub"]
  detail-type = ["Security Hub Findings - Imported"]
  detail = {
    findings = {
      Workflow   = { Status = ["NEW"] }
      Compliance = { Status = ["FAILED"] }
      Severity   = { Label = ["MEDIUM", "HIGH", "CRITICAL"] }
    }
  }
})
```

### Slack Notification Lambda

A second Lambda function that posts formatted alerts to Slack via incoming webhook. Uses Slack Block Kit for structured messages with:

- Severity color-coding (red for CRITICAL, orange for HIGH, yellow for MEDIUM)
- Finding title, source service, account, region, and resource
- Direct "View in Security Hub" button

Uses only Python's built-in `urllib` — no external dependencies, no Lambda layers required.

### Notification Flow Architectures

Three reference patterns documented with triggers, logic, and what to configure:

1. **Security Hub → SES email** (fully implemented with Terraform)
2. **GuardDuty/Security Hub → Slack** (Lambda included, Terraform target left as exercise)
3. **IAM policy changes → CloudTrail → EventBridge → SQS** (reference architecture with EventBridge pattern)

### Cloud Forensics Tool Matrix (Excel)

A categorized reference of tools for AWS incident investigation — native AWS services and open-source alternatives, mapped by use case (memory acquisition, log analysis, network forensics, disk forensics).

---

## How to Deploy

1. Download the toolkit and extract it
2. Create `terraform/terraform.tfvars` with your email addresses:

```hcl
aws_region     = "eu-west-1"
ses_from_email = "alerts@yourdomain.com"
ses_to_email   = "security-team@yourdomain.com"
```

3. Deploy:

```bash
cd terraform
terraform init
terraform plan
terraform apply
```

4. Generate sample findings to test:

```bash
aws securityhub create-sample-findings --region eu-west-1
```

**Prerequisites:** SES sender email must be verified (or SES out of sandbox mode). AWS credentials configured locally.

---

## Download the Toolkit (Free)

[Download AWS IR Toolkit v1.1 (.zip, ~100KB)](/downloads/aws-ir-toolkit-v1.1.zip)

Includes the playbook PDF, all Terraform and Python code above, the notification flow architectures, and the forensic tool matrix.

---

**Related guides:**
- [AWS Incident Response Scenarios: 5 Real-World Attack Patterns](/posts/aws-incident-response-scenarios/) — practice these scenarios with the playbook
- [AWS CloudTrail Log Analysis for Security](/posts/aws-cloudtrail-log-analysis/) — the primary data source for IR investigation
- [AWS GuardDuty Setup: Route Findings to Slack & Your SIEM](/posts/aws-guardduty-setup/) — the detection layer that feeds the notification pipeline
- [Real-World Phishing Incident Response](/posts/real-world-phishing-incident-response/) — a full IR walkthrough using this methodology
