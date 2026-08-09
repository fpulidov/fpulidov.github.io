---
title: "AWS Security Checklist: The 30-Minute Audit I Run on Every Account"
date: 2026-07-07
tags: ["aws", "cloud-security", "checklist", "beginner-guide", "iam", "s3", "cloudtrail"]
keywords: ["aws security checklist", "aws account security review", "aws security audit checklist", "aws security checklist startups", "aws security quick review", "aws security best practices 2026"]
categories: ["Cloud Security"]
description: "The baseline I verify on every AWS security engagement — 10 checks with CLI commands covering IAM, S3, logging, and network hardening. Takes 30 minutes, catches 80% of what goes wrong."
summary: "The 30-minute security baseline I run on every AWS account — 10 sections with copy-paste CLI commands covering IAM, S3, CloudTrail, network hardening, and cost monitoring."
slug: "aws-security-checklist-2026"
aliases: ["/posts/aws-security-checklist-2025/", "/aws-security-checklist-2025/"]
image: "/images/checklist.png"
draft: false
author: "Javier Pulido"
canonicalURL: "https://thehiddenport.dev/posts/aws-security-checklist-2026/"
lastmod: 2026-07-30
enable_comments: true
---

Every AWS security engagement I run starts the same way — a 30-minute sweep of the account's baseline controls. Not because it's thorough (it isn't), but because the same ten things are misconfigured in nearly every account I see. Root accounts without MFA, public S3 buckets nobody knows about, CloudTrail disabled in half the regions.

This checklist is what I actually run. Each section includes the CLI commands to verify the control, so you can work through it in a terminal session. If you want the full picture of what I find repeatedly, read the [misconfigurations guide](/posts/aws-security-misconfigurations-guide/) — this is the quick version.

---

## 1. Secure the Root Account

The root account can bypass every guardrail in your AWS environment. If it's compromised, nothing else matters.

- **Enable MFA** (hardware key — YubiKey or FIDO2, not a phone app)
- **Delete root access keys** if any exist
- **Use IAM Identity Center** for daily admin tasks

Verify:

```bash
# Check if root has access keys
aws iam get-account-summary --query 'SummaryMap.AccountAccessKeysPresent'

# Check if root has MFA
aws iam get-account-summary --query 'SummaryMap.AccountMFAEnabled'
```

Both should return `1` for MFA and `0` for access keys. If not, fix it before moving on — everything else is secondary. For a deeper look at root account monitoring, see the [root account usage detection guide](/posts/detect-root-account-usage/).

---

## 2. Block Public S3 Access

Public buckets are still the #1 source of accidental data exposure in AWS.

- Enable **Block Public Access at the account level**
- Verify bucket-level settings for sensitive workloads
- Monitor with **Access Analyzer** for cross-account sharing

```bash
# Check account-level public access block
aws s3control get-public-access-block --account-id $(aws sts get-caller-identity --query Account --output text)

# List any buckets with public ACLs
aws s3api list-buckets --query 'Buckets[].Name' --output text | tr '\t' '\n' | while read bucket; do
  acl=$(aws s3api get-bucket-acl --bucket "$bucket" --query 'Grants[?Grantee.URI==`http://acs.amazonaws.com/groups/global/AllUsers`]' --output text 2>/dev/null)
  [ -n "$acl" ] && echo "PUBLIC: $bucket"
done
```

AWS enables account-level blocking by default on new accounts, but older accounts and accounts created via Organizations may still be open.

---

## 3. Apply IAM Best Practices

Over-permissioned IAM roles are in every account I audit. The fix is a process, not a one-time action.

- Use **IAM Identity Center (SSO)** for human access — [stop creating IAM users](/posts/aws-iam-users-alternatives/)
- Replace long-term credentials with **STS temporary credentials**
- Enforce MFA on all human identities

```bash
# Find IAM users with access keys older than 90 days
aws iam generate-credential-report > /dev/null 2>&1
aws iam get-credential-report --query Content --output text | base64 -d | \
  awk -F, '$5 == "true" && $6 != "N/A" {print $1, $6}'

# Find policies with wildcard actions
aws iam list-policies --scope Local --query 'Policies[].Arn' --output text | tr '\t' '\n' | while read arn; do
  version=$(aws iam get-policy --policy-arn "$arn" --query 'Policy.DefaultVersionId' --output text)
  aws iam get-policy-version --policy-arn "$arn" --version-id "$version" --query 'PolicyVersion.Document' --output json | grep -l '"Action": "\*"' && echo "WILDCARD: $arn"
done
```

Use [IAM Access Analyzer](/posts/iam-access-analyzer-least-privilege/) and service last-accessed data to scope down permissions. The [least privilege guide](/posts/aws-enforcing-least-privilege/) walks through the full workflow.

---

## 4. Enable Logging Everywhere

If you can't see what happened, you can't investigate it. Logging is the one control that makes every other control useful.

| Service | Configuration |
|---------|---------------|
| **CloudTrail** | Org-wide, multi-region, logs to S3 and CloudWatch |
| **VPC Flow Logs** | All VPCs, at least to S3 |
| **GuardDuty** | All regions + runtime monitoring enabled |
| **AWS Config** | Track all resource types across all regions |

```bash
# Check CloudTrail status across regions
for region in $(aws ec2 describe-regions --query 'Regions[].RegionName' --output text); do
  trails=$(aws cloudtrail describe-trails --region "$region" --query 'trailList[?IsMultiRegionTrail==`true`].Name' --output text 2>/dev/null)
  [ -z "$trails" ] && echo "NO MULTI-REGION TRAIL: $region"
done

# Check if CloudTrail is actually logging
aws cloudtrail get-trail-status --name <trail-name> --query 'IsLogging'
```

Set log retention (30-90 days in CloudWatch, longer in S3) to keep costs predictable. See the [CloudTrail analysis guide](/posts/aws-cloudtrail-log-analysis/) for what to do with these logs once you have them.

---

## 5. Enable Threat Detection

Logging tells you what happened. Detection tells you when something bad is happening *right now*.

- Enable **GuardDuty** in all regions (monitors DNS, CloudTrail, network, and runtime activity)
- Enable **Security Hub** for a centralized findings view
- Set up SNS alerts for **critical and high** findings

```bash
# Check GuardDuty status across regions
for region in $(aws ec2 describe-regions --query 'Regions[].RegionName' --output text); do
  detector=$(aws guardduty list-detectors --region "$region" --query 'DetectorIds[0]' --output text 2>/dev/null)
  [ "$detector" = "None" ] || [ -z "$detector" ] && echo "GUARDDUTY DISABLED: $region"
done

# Check Security Hub status
aws securityhub describe-hub 2>/dev/null || echo "SECURITY HUB NOT ENABLED"
```

For GuardDuty setup with Slack routing, see the [GuardDuty setup guide](/posts/aws-guardduty-setup/). For runtime-level visibility inside containers and EC2, see [GuardDuty Runtime Monitoring](/posts/aws-guardduty-runtime-monitoring/).

---

## 6. Harden Network Security

Network misconfigurations are the easiest to exploit and the easiest to prevent.

- Audit **Security Groups** — block `0.0.0.0/0` on SSH/RDP
- Use **SSM Session Manager** instead of bastion hosts
- Enable **VPC Flow Logs** for visibility
- Use **private subnets** for anything that doesn't need direct internet access

```bash
# Find security groups with SSH/RDP open to the world
aws ec2 describe-security-groups \
  --filters "Name=ip-permission.from-port,Values=22,3389" "Name=ip-permission.cidr,Values=0.0.0.0/0" \
  --query 'SecurityGroups[].{ID:GroupId, Name:GroupName}' --output table

# Check which VPCs have flow logs
aws ec2 describe-vpcs --query 'Vpcs[].VpcId' --output text | tr '\t' '\n' | while read vpc; do
  logs=$(aws ec2 describe-flow-logs --filter "Name=resource-id,Values=$vpc" --query 'FlowLogs[0].FlowLogId' --output text 2>/dev/null)
  [ "$logs" = "None" ] || [ -z "$logs" ] && echo "NO FLOW LOGS: $vpc"
done
```

For the full EC2 hardening workflow, see the [EC2 hardening guide](/posts/aws-ec2-hardening/) and [CIS benchmarks guide](/posts/ec2-cis-benchmarks-guide/).

---

## 7. Secure Secrets and Credentials

Hardcoded credentials in code, environment variables, or config files are a breach waiting to happen.

- Store all secrets in **Secrets Manager** or **SSM Parameter Store** (SecureString)
- Enable **automatic rotation** for database credentials
- Monitor for unexpected secret changes with **EventBridge**

```bash
# Find secrets without rotation configured
aws secretsmanager list-secrets --query 'SecretList[?RotationEnabled==`false`].Name' --output table

# Check for secrets that haven't been rotated in 90+ days
aws secretsmanager list-secrets --query 'SecretList[?LastRotatedDate!=`null`].[Name,LastRotatedDate]' --output table
```

Secrets Manager now publishes change events to EventBridge automatically — set up alerts for unexpected manual changes. See the [Secrets Manager EventBridge guide](/posts/aws-secrets-manager-eventbridge-notifications/) for the setup.

---

## 8. Monitor Cloud Costs

Unexpected cost spikes often signal compromised resources — crypto miners on EC2, exfiltration through NAT Gateway, or someone spinning up GPU instances in a region you don't use.

- Create **AWS Budgets** with thresholds for cost spikes
- Enable **Anomaly Detection** for new service usage or region activity

```bash
# Check existing budgets
aws budgets describe-budgets --account-id $(aws sts get-caller-identity --query Account --output text) \
  --query 'Budgets[].{Name:BudgetName,Limit:BudgetLimit.Amount,Actual:CalculatedSpend.ActualSpend.Amount}' --output table
```

If you have no budgets configured, create at least one that alerts at 80% and 100% of your expected monthly spend.

---

## 9. Automate Compliance Checks

Manual reviews don't scale. Set up automation so drift gets caught before it becomes a finding.

- Use **Control Tower** for multi-account environments
- Define **AWS Config rules** for your critical controls (public S3, unencrypted volumes, unrestricted security groups)
- Send **weekly Security Hub summaries** to Slack or email
- Run **IAM Credential Reports** on a schedule to catch stale credentials

```bash
# Check AWS Config recorder status
aws configservice describe-configuration-recorder-status \
  --query 'ConfigurationRecordersStatus[].{Name:name,Recording:recording,LastStatus:lastStatus}' --output table

# Get Security Hub standards compliance score
aws securityhub get-enabled-standards --query 'StandardsSubscriptions[].StandardsArn' --output text | tr '\t' '\n' | while read std; do
  aws securityhub describe-standards-controls --standards-subscription-arn "$std" \
    --query 'Controls[?ComplianceStatus==`FAILED`] | length(@)' --output text 2>/dev/null
done
```

---

## 10. Review and Repeat

Security isn't a project — it's a recurring process. The controls you verified today will drift by next quarter.

- Run this checklist **quarterly** at minimum
- Subscribe to AWS Security blog updates and re:Post
- Review your [SCP guardrails](/posts/aws-scp-best-practices/) whenever your organization structure changes
- Build [incident response playbooks](/posts/aws-incident-response-scenarios/) before you need them — not during an incident

---

## Related Reading

- [AWS Misconfigurations I Find in Every Security Audit](/posts/aws-security-misconfigurations-guide/) — the full breakdown of what this checklist catches
- [AWS SCPs That Actually Work](/posts/aws-scp-best-practices/) — org-level guardrails that enforce these controls automatically
- [CloudTrail Log Analysis: How to Find Who Did What](/posts/aws-cloudtrail-log-analysis/) — investigate when a checklist item gets violated
- [IDOR in AWS APIs: Real Examples & How to Fix Them](/posts/aws-preventing-idor/) — application-layer access control this checklist doesn't cover
- [GuardDuty Runtime Monitoring](/posts/aws-guardduty-runtime-monitoring/) — process-level visibility inside your workloads
- [AWS Secrets Manager EventBridge Notifications](/posts/aws-secrets-manager-eventbridge-notifications/) — automated alerts for credential changes
- [How I Passed the AWS Security Specialty (SCS-C02)](/posts/aws-scs-c02-exam-experience/) — the cert that covers these topics in depth
