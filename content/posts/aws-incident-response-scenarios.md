---
title: "AWS Incident Response: 5 Scenarios & How to Contain Them"
date: 2026-07-07
draft: false
description: "Handle real AWS security incidents step by step. Covers compromised keys, public S3 buckets, cryptomining, privilege escalation, and automated containment."
summary: "Five real-world AWS incident response scenarios with detection signals, containment steps, CLI commands, and automation examples. Practical guide for security teams."
slug: "aws-incident-response-scenarios"
tags: ["AWS", "Incident Response", "CloudTrail", "GuardDuty", "Security", "Forensics", "EventBridge"]
categories: ["Cloud Security", "Guides"]
keywords: ["aws incident response", "aws incident detection and response", "aws security incident", "aws incident response playbook", "compromised aws credentials", "aws containment"]
canonicalURL: "https://thehiddenport.dev/posts/aws-incident-response-scenarios/"
enable_comments: true
---

Most AWS incident response guides explain the theory — preparation, detection, containment, eradication, recovery, lessons learned. That's useful, but when you're staring at a GuardDuty alert at 2 AM, you need to know exactly what to do.

This post covers five incident scenarios that AWS security teams encounter regularly, with detection signals, containment commands, and follow-up actions you can execute immediately.

> For the full process framework, see [Incident Response in AWS: A Practical Guide](/posts/incident-response-aws-guide/). For a ready-to-use template, see the [AWS IR Playbook Template](/posts/aws-ir-playbook-template/).

---

## Before You Start: Detection Stack

Every scenario below assumes you have the basics in place:

- **CloudTrail** enabled in all regions with management events logging
- **GuardDuty** active (at minimum in your primary region)
- **AWS Config** recording resource changes
- **EventBridge rules** forwarding high-severity findings to SNS or Slack

If you don't have these yet, stop here and set them up first. Without logging, incident response is guesswork.

---

## Scenario 1: Compromised IAM Access Keys

**Detection signals:**
- GuardDuty finding: `UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration`
- CloudTrail: API calls from unfamiliar IP addresses or regions
- Console login from a location your team doesn't operate in
- Sudden spike in API calls (especially `DescribeInstances`, `ListBuckets`, or `GetCallerIdentity`)

**Immediate containment:**

1. Disable the access key — don't delete it yet (you need it for forensics):

```bash
aws iam update-access-key \
  --user-name compromised-user \
  --access-key-id AKIA... \
  --status Inactive
```

2. Check what the key was used for:

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=AccessKeyId,AttributeValue=AKIA... \
  --start-time 2026-07-01T00:00:00Z \
  --max-results 50
```

3. Revoke any active sessions for the user by attaching a deny-all inline policy:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Deny",
    "Action": "*",
    "Resource": "*",
    "Condition": {
      "DateLessThan": {
        "aws:TokenIssueTime": "2026-07-07T12:00:00Z"
      }
    }
  }]
}
```

This invalidates all session tokens issued before the specified time without disrupting the user's ability to get new (clean) credentials after you've secured the account.

4. Scope the blast radius — check if the attacker created any new resources:

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=AccessKeyId,AttributeValue=AKIA... \
  --start-time 2026-07-01T00:00:00Z | \
  grep -E "RunInstances|CreateUser|CreateAccessKey|CreateRole|PutBucketPolicy"
```

**Follow-up:** Rotate the compromised key, audit other keys on the account with `aws iam generate-credential-report`, and check if the key was hardcoded in any repository.

---

## Scenario 2: Public S3 Bucket Data Exposure

**Detection signals:**
- AWS Config rule: `s3-bucket-public-read-prohibited` or `s3-bucket-public-write-prohibited` flagged non-compliant
- GuardDuty finding: `Policy:S3/BucketAnonymousAccessGranted`
- Macie alert for sensitive data in a public bucket
- External report or disclosure (bug bounty, security researcher, press)

**Immediate containment:**

1. Block all public access at the account level:

```bash
aws s3control put-public-access-block \
  --account-id 123456789012 \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

2. If you need to target a specific bucket without affecting others:

```bash
aws s3api put-public-access-block \
  --bucket exposed-bucket-name \
  --public-access-block-configuration \
    BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true
```

3. Check S3 server access logs to see who accessed the data:

```bash
aws s3 cp s3://your-log-bucket/s3-access-logs/ ./logs/ --recursive
grep "REST.GET.OBJECT" ./logs/* | grep "exposed-bucket-name"
```

4. Identify what was exposed:

```bash
aws s3 ls s3://exposed-bucket-name --recursive --human-readable --summarize
```

**Follow-up:** If sensitive data was exposed, this may trigger a breach notification obligation depending on your jurisdiction. Document the exposure window (when public access was enabled vs. when it was blocked), what data was accessible, and whether access logs show external downloads.

---

## Scenario 3: Cryptomining on EC2

**Detection signals:**
- GuardDuty finding: `CryptoCurrency:EC2/BitcoinTool.B!DNS` or `CryptoCurrency:EC2/BitcoinTool.B`
- Unexpected billing spike — EC2 costs jump, especially for GPU or large instance types
- CloudWatch: CPU utilization at 100% on instances that normally run low
- Outbound network traffic to known mining pool IPs

**Immediate containment:**

1. Isolate the instance by swapping its security group to one that blocks all traffic:

```bash
# Create an isolation security group (do this once, ahead of time)
aws ec2 create-security-group \
  --group-name ir-isolation \
  --description "IR isolation - no inbound or outbound" \
  --vpc-id vpc-xxx

# Remove all outbound rules (SGs allow all outbound by default)
aws ec2 revoke-security-group-egress \
  --group-id sg-isolation-id \
  --ip-permissions '[{"IpProtocol": "-1", "FromPort": -1, "ToPort": -1, "IpRanges": [{"CidrIp": "0.0.0.0/0"}]}]'

# Apply to the compromised instance
aws ec2 modify-instance-attribute \
  --instance-id i-compromised \
  --groups sg-isolation-id
```

2. Snapshot the volumes before doing anything else:

```bash
# Get volume IDs
aws ec2 describe-instances --instance-ids i-compromised \
  --query 'Reservations[].Instances[].BlockDeviceMappings[].Ebs.VolumeId' --output text

# Snapshot each volume
aws ec2 create-snapshot \
  --volume-id vol-xxx \
  --description "IR evidence - cryptomining incident" \
  --tag-specifications 'ResourceType=snapshot,Tags=[{Key=incident,Value=crypto-mining},{Key=date,Value=2026-07-07}]'
```

3. Check how the instance was compromised — look at the instance profile role and recent SSM or SSH activity:

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=i-compromised \
  --start-time 2026-07-01T00:00:00Z
```

**Follow-up:** After evidence is preserved, terminate the instance and investigate the entry point. Common vectors: exposed SSH key, SSRF on a web app running on the instance, overprivileged instance profile that allowed lateral movement.

---

## Scenario 4: Unauthorized Privilege Escalation

**Detection signals:**
- CloudTrail events: `CreateRole`, `AttachRolePolicy`, `PutUserPolicy`, `CreateAccessKey` (for another user)
- EventBridge alert on `iam:AttachRolePolicy` with `AdministratorAccess`
- GuardDuty finding: `Persistence:IAMUser/AnomalousBehavior`
- A role or user suddenly has permissions it shouldn't

**Immediate containment:**

1. Identify what changed:

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=AttachRolePolicy \
  --start-time 2026-07-06T00:00:00Z
```

2. Revert the policy attachment:

```bash
aws iam detach-role-policy \
  --role-name escalated-role \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess
```

3. If a new role or user was created by the attacker, disable it:

```bash
# For a rogue user
aws iam put-user-policy --user-name rogue-user --policy-name DenyAll \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Deny","Action":"*","Resource":"*"}]}'

# For a rogue role — revoke sessions
aws iam put-role-policy --role-name rogue-role --policy-name DenyAll \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Deny","Action":"*","Resource":"*"}]}'
```

4. Check the full chain — did the escalated permissions get used?

```bash
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=rogue-user \
  --start-time 2026-07-06T00:00:00Z
```

**Follow-up:** Audit all IAM policies modified in the last 7 days with AWS Config. Set up an EventBridge rule that triggers on any `AttachRolePolicy` or `PutUserPolicy` call containing `AdministratorAccess` — this should always fire an alert.

> For a deep dive on detection rules for privilege escalation, see [Detect AWS IAM Privilege Escalation with CloudTrail](/posts/aws-detecting-privilege-escalation-cloudtrail-eventbridge/).

---

## Scenario 5: Suspicious GuardDuty High-Severity Finding

Sometimes GuardDuty fires a high-severity finding that doesn't fit a clean pattern. Here's a triage workflow for any finding type.

**Step 1 — Get finding details:**

```bash
aws guardduty list-findings \
  --detector-id YOUR_DETECTOR_ID \
  --finding-criteria '{"Criterion":{"severity":{"Gte":7}}}'

aws guardduty get-findings \
  --detector-id YOUR_DETECTOR_ID \
  --finding-ids "finding-id-here"
```

**Step 2 — Classify the finding type:**

| Finding prefix | Target | Typical action |
|---|---|---|
| `UnauthorizedAccess:IAMUser/` | IAM credentials | Disable key, revoke sessions |
| `Recon:EC2/` | EC2 instance | Check instance profile, review traffic |
| `CryptoCurrency:EC2/` | EC2 instance | Isolate, snapshot, terminate |
| `Trojan:EC2/` | EC2 instance | Isolate immediately |
| `Policy:S3/` | S3 bucket | Block public access |
| `Exfiltration:S3/` | S3 bucket | Review access logs, block source |

**Step 3 — Enrich with context:**

Check CloudTrail for the affected resource in the finding's time window. Cross-reference with AWS Config to see if any resource configuration changed around the same time.

**Step 4 — Decide: contain or investigate further.**

If the finding involves active compromise (Trojan, CryptoCurrency, Exfiltration), contain first, investigate second. If it's reconnaissance (Recon, Discovery), you may have time to investigate before acting — but set a deadline and don't let the finding sit in "NEW" status.

---

## Automating Containment with EventBridge

Manual response doesn't scale. For your most common and highest-confidence scenarios, automate the containment step.

Example: auto-isolate an EC2 instance when GuardDuty detects cryptomining.

**EventBridge rule pattern:**

```json
{
  "source": ["aws.guardduty"],
  "detail-type": ["GuardDuty Finding"],
  "detail": {
    "type": [{
      "prefix": "CryptoCurrency:EC2/"
    }],
    "severity": [{
      "numeric": [">=", 7]
    }]
  }
}
```

**Lambda target** (Python):

```python
import boto3

ec2 = boto3.client('ec2')
ISOLATION_SG = 'sg-0abc123isolation'

def handler(event, context):
    instance_id = event['detail']['resource']['instanceDetails']['instanceId']

    # Swap security groups to isolation
    ec2.modify_instance_attribute(
        InstanceId=instance_id,
        Groups=[ISOLATION_SG]
    )

    # Tag the instance
    ec2.create_tags(
        Resources=[instance_id],
        Tags=[
            {'Key': 'ir-status', 'Value': 'isolated'},
            {'Key': 'ir-finding', 'Value': event['detail']['type']}
        ]
    )

    return {'isolated': instance_id}
```

> Start by automating high-confidence, high-severity findings only. False-positive auto-containment is worse than manual response.

---

## What Happens After Containment

Containment is step one, not the finish line. After you've stopped the bleeding:

1. **Preserve evidence** — snapshot all volumes, export CloudTrail logs to a tamper-proof S3 bucket with Object Lock. See the [IR Playbook Template](/posts/aws-ir-playbook-template/) for the full evidence checklist.

2. **Determine root cause** — how did the attacker get in? Leaked key in a repo? SSRF? Over-permissioned role? The root cause determines whether your fix is "rotate one key" or "redesign your network."

3. **Remediate** — fix the vulnerability, not just the symptom. If an access key was compromised because it was committed to GitHub, rotating the key alone isn't enough — you need to remove it from the repo history and set up secret scanning.

4. **Run a blameless retro** — document the timeline, what worked, what didn't, and what you'll change. Update your detection rules and playbooks based on what you learned.

---

## Conclusion

Incident response in AWS comes down to three things: detecting quickly, containing aggressively, and preserving evidence before you clean up. The five scenarios above cover most of what security teams encounter day to day.

Build your detection stack, pre-create your isolation security group, and automate the high-confidence responses. When the alert fires, you want to execute a playbook — not design one.

**Related resources:**
- [AWS Incident Response Guide for Small Security Teams](/posts/incident-response-aws-guide/)
- [AWS IR Playbook Template (Free)](/posts/aws-ir-playbook-template/)
- [AWS Incident Response Toolkit](/posts/aws-ir-toolkit/)
- [Detect AWS IAM Privilege Escalation with CloudTrail](/posts/aws-detecting-privilege-escalation-cloudtrail-eventbridge/)
