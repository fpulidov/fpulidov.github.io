---
title: "Incident Response in AWS: A Playbook for Small Security Teams"
date: 2025-05-04
tags: ["aws", "incident-response", "cloud-security", "forensics", "ssm", "security-hub"]
categories: ["Cloud Security", "Guides"]
description: "A practical guide to incident response in AWS for small teams. Includes step-by-step playbook, memory acquisition techniques, and evidence handling in the cloud."
summary: "Learn how to run an effective incident response process in AWS using automation and forensic best practices — without needing a separate IR account."
slug: "incident-response-aws-guide"
draft: false
author: "Javier Pulido"
---

Cloud breaches are no longer a question of if — but when. For small teams, this means preparing lightweight yet effective incident response workflows that work in the cloud, with the tools you already have.

In this guide, I’ll walk you through a modern approach to Incident Response (IR) in AWS, shaped by experience and battle-tested tactics. A downloadable IR playbook is included at the end.

## Why Cloud IR Is Different

In traditional IR, you usually walk into a server room. In AWS, you don’t have physical access — everything is virtual, API-driven, and ephemeral.

What changes:
- You can't unplug a cable — so you isolate via automations, SSM, IAM ...
- Forensic imaging becomes memory dumps and logs.
- Evidence handling must be automated and secure while ensuring its chain of custody.

---

## Phase 1: Preparation

> "The worst time to build an IR plan is when you're under attack."

### Ideally: Use a Dedicated IR Account

If your organization allows, the most secure approach is to:
- Create a dedicated AWS account within your Organization for incident response.
- Use it to store forensic snapshots, memory dumps, and analysis artifacts.
- Restrict access to security engineers only.

### Alternative: Lock Down a Region

If managing another account is out of scope:
- Choose an unused region as your **IR region**.
- Create strict SCPs that deny access to that region except for IR roles.
- Use it to store snapshots, launch analysis EC2 instances.
- This keeps investigation resources separate and auditable without needing another account.

### Pre-Provision IR Tools

- Store AVML (for memory dumps) in a private S3 bucket or include it as a binary in your base AMIs.
- Create a Lambda to trigger AVML remotely using SSM.
- Use write-once S3 with versioning for evidence.
- Provision EC2 instance profiles for analysis tooling.
- Prepare your own forensics AMI.
- Destroy used forensics instance to ensure a clean environment.

---

## Phase 2: Detection & Triage

Enable and monitor:
- **Security Hub** and **GuardDuty** (region-wide detection)
- **AWS Inspector**
- **AWS Config** for change auditing
- EventBridge rules for high-severity findings to trigger automatic notifications
- Ideally you would have a SIEM ingesting your notifications with a curated set of rules

Example triage filter:
```bash
aws securityhub get-findings \
  --filters WorkflowStatus=NEW SeverityLabel=CRITICAL
```

Send alerts to SNS topics, email, or Slack integrations for immediate triage.

---

## Phase 3: Isolation

### Option 1: SSM Isolation (no reboot needed)
```bash
aws ec2 modify-instance-attribute \
  --instance-id i-12345678 \
  --no-source-dest-check

aws ec2 modify-network-interface-attribute \
  --network-interface-id eni-xyz \
  --groups sg-isolated-only
```

### Option 2: Detach From Load Balancers
Quick way to prevent public exposure without shutting down the instance.

#### Pro Tip

It is recommended to define your isolation process and automate it.

---

## Phase 4: Evidence Collection

### Snapshot Disks
```bash
aws ec2 create-snapshot --volume-id vol-0c0e757e277111f3c \
--description 'IR evidence snapshot' --tag-specifications \
'ResourceType=snapshot,Tags=[{Key=evidence,Value=true},{Key=investigation,Value=InProgress}]'
```

Copy to your IR region or account.

### Capture Memory (Linux)
```bash
aws ssm send-command \
  --document-name "AWS-RunShellScript" \
  --targets "Key=instanceIds,Values=i-xxxx" \
  --parameters commands=["sudo ./avml /tmp/memdump.lime"]
```

Send output to your S3 bucket with versioning enabled.

#### Pro Tip

There is no such thing as too many tags, make sure to tag everything, it will help you in the future with your automations or Audits

---

## Phase 5: Analysis

Mount snapshot volumes in EC2 instances in your IR region:
- Use Plaso, Volatility, or log parsing tools
- Analyze user activity, binaries, system logs

Always mount snapshots read-only.

---

## Phase 6: Remediation & Lessons Learned

- Rotate IAM keys, delete old roles if it applies
- Find root cause and generate new AMI/code fix to prevent from happening again
- Redeploy infrastructure from clean code if it applies
- Run a blameless retro
- Store timeline, findings, and action items securely
- Every user access and actions must be recorded and documented for future audits

---


## (Optional) Long-Term Evidence Storage (Cold, Tamper-Proof)

Once analysis is complete, evidence must be retained securely — sometimes for years — depending on your industry, legal requirements, or internal policies.

### Why It Matters
- Regulatory requirements (e.g., PCI-DSS, ISO 27001) often mandate retention.
- You may need to revisit evidence in future investigations.
- Chain-of-custody must be intact — even if team members change.

### Best Practice: S3 with Object Lock in Compliance Mode

Use an **S3 bucket with Object Lock enabled**, configured for **Compliance mode**:

- **WORM (Write Once, Read Many)**: After the retention period is set, **no one — not even the root user — can delete or modify the data**.
- **Versioning** must be enabled.
- **Compliance mode** ensures true immutability.

```bash
aws s3api put-object-lock-configuration   --bucket forensic-evidence-storage   --object-lock-configuration '{
    "ObjectLockEnabled": "Enabled",
    "Rule": {
      "DefaultRetention": {
        "Mode": "COMPLIANCE",
        "Days": 365
      }
    }
  }'
```

> **Pro Tip**: Store a signed hash (SHA-256) of the evidence metadata separately in a ticket or case management system for added integrity validation.

### Glacier Deep Archive

After the case is closed and data is rarely accessed:

1. You should consider setting a lifecycle policy to **transition older snapshots or S3 objects to Glacier Deep Archive**.
2. Keep metadata and hashes in S3 Standard for fast audit access.

```hcl
resource "aws_s3_bucket_lifecycle_configuration" "archive" {
  bucket = aws_s3_bucket.forensic.id

  rule {
    id     = "archive-old-evidence"
    status = "Enabled"

    transition {
      days          = 30
      storage_class = "DEEP_ARCHIVE"
    }
  }
}
```

This minimizes cost while still preserving a chain-of-custody–friendly trail.


## Check my own IR Playbook Template

📄 [Online IR Playbook template](/posts/aws-ir-playbook-template/)

Includes:
- Triage checklist
- Memory and disk acquisition workflows
- Region lockdown guide
- Incident summary format

---

## Final Thoughts

You don’t need a massive budget to handle incidents well in AWS. With preparation and automation, even small teams can contain breaches quickly and gather clean forensic evidence.

Adapt this guide, test it regularly, and scale it as your team grows.
