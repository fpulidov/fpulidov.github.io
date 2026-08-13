---
title: "ISO 27001 for AWS: What Auditors Actually Ask For"
date: 2026-08-11
draft: false
description: "The AWS evidence requests that show up in real ISO 27001 audits — log retention proofs, access control evidence, past investigation examples, and DR tests. Written from actual audit prep, not a vendor checklist."
summary: "The four AWS evidence categories ISO 27001 auditors actually ask for, from someone who's prepared environments for a real audit. Custom evidence collection, common gaps, and where teams get caught off guard."
slug: "iso-27001-aws-audit-prep"
tags: ["AWS", "ISO 27001", "Compliance", "Audit", "Security", "Governance"]
keywords: ["iso 27001 aws", "iso 27001 aws checklist", "iso 27001 aws controls", "aws iso 27001 audit", "iso 27001 evidence aws", "aws audit prep", "iso 27001 cloud"]
categories: ["Cloud Security", "Compliance"]
canonicalURL: "https://thehiddenport.dev/posts/iso-27001-aws-audit-prep/"
enable_comments: true
---

Every CNAPP vendor and consultancy has an "ISO 27001 for AWS" checklist. They're mostly the same content — a mapping of Annex A controls to AWS services, with a bit of tooling pitch at the end. What they consistently miss: **the specific evidence your auditor will actually ask you to produce**, which is not always what the framework text suggests.

I've prepared an AWS environment for a real ISO 27001 audit, and I'm currently preparing another client for PCI-DSS. The pattern of what auditors actually request — versus what the checklist templates imply — is remarkably consistent. Here's what you'll be asked for, how to prepare the evidence, and where I've seen teams get caught off guard.

---

## Why Framework Templates Underprepare You

The published Annex A controls tell you *what* to control. They don't tell you what your auditor will accept as proof. In practice, the framework language ("A.8.15 Logging: logs recording activities, exceptions, faults and other relevant events shall be produced, stored, protected and analysed") maps to a very specific set of auditor asks:

- Show me the written policy that says how long you keep logs
- Show me evidence the retention is actually enforced
- Show me an example of a log you analyzed for a real event

The template will list "logging" as a checkbox. The auditor wants three separate pieces of evidence, and if you only have one, you fail that control.

That gap between "checklist tells you it exists" and "auditor wants three specific things" is why most first-time audit preps have a scramble in the last two weeks. The four categories below are the ones where the gap is widest.

---

## 1. Log Retention — Policy + Enforcement + Analysis Example

**What the framework says:** logs must be retained and protected.

**What the auditor asks for:**
1. A written **log retention policy** stating how long each log type is kept and why
2. **Technical evidence** that the retention is enforced (not just written down)
3. An **example of analysis** — a log query you ran to investigate something, with the output and the conclusion

The first is a doc. The second and third are where most teams struggle.

For AWS, the technical evidence looks like:

```bash
# CloudTrail — show the retention configured on the S3 bucket where logs land
aws s3api get-bucket-lifecycle-configuration \
  --bucket your-cloudtrail-bucket

# CloudWatch Logs — show retention setting per log group
aws logs describe-log-groups \
  --query 'logGroups[].{Name:logGroupName,Retention:retentionInDays}' \
  --output table
```

Screenshot both, cross-reference with your written policy, done.

For the analysis example — auditors love this one because it's where policy meets practice. A CloudTrail Athena query you ran to investigate an odd login, an alert triage record, a query showing you looked at 4xx spikes — anything that shows the logs are actually used, not just collected. Keep a folder of these throughout the year.

---

## 2. Access Control — Password Policy, MFA, Access Reviews

**What the auditor asks for:**
1. **Minimum password requirements** — screenshot of your IAM account password policy AND the corresponding written policy
2. **MFA enforcement evidence** — proof that MFA is required for privileged access, not just available
3. **Periodic access reviews** — evidence you review who has access to what, and remove stale access

For AWS:

```bash
# Password policy — the JSON output goes in your evidence pack
aws iam get-account-password-policy

# Credential report — shows MFA status per user, last used, key age
aws iam generate-credential-report > /dev/null 2>&1
aws iam get-credential-report --query Content --output text | base64 -d
```

The credential report is the single most useful piece of evidence for the access-review control. Auditors love it because it's dated, comprehensive, and machine-generated. Save the CSV monthly with the date in the filename — that's your access review evidence right there.

The gap I've seen: teams enforce MFA on the console but forget CLI/API access. The auditor will ask specifically about programmatic access. If any IAM user has an active access key and no MFA condition on their permissions, that's a finding.

---

## 3. Investigation Examples — The Control That Trips Up First Audits

This is the sleeper. **A.16 (Information Security Incident Management)** — auditors will ask for evidence that you can actually investigate an incident, not just that you have a written incident response plan.

**What they ask for:**
- An **example investigation** you conducted (real or tabletop)
- The **timeline of the investigation**, including who was notified and when
- The **outcome** — what you found, what you fixed, what you changed to prevent recurrence

Most teams have the IR plan document. They don't have any evidence they've ever exercised it. The first audit prep I supported, this was the biggest gap: months of GuardDuty findings acknowledged and closed, with zero written record of the actual investigation for any of them.

**Prevention:** for every GuardDuty finding or CloudTrail alert you look at seriously, write a short investigation note. Even a two-paragraph markdown file: what triggered the alert, what you checked, what you concluded, what you did. Store them in a folder. When the auditor asks, you have 12 examples ready.

For the audit prep itself, you can retroactively write up recent investigations from CloudTrail logs — but do it earlier rather than later. I usually recommend clients start this habit 6 months before their audit date.

If you want the technical scaffolding for this, my [CloudTrail Log Analysis guide](/posts/aws-cloudtrail-log-analysis/) covers the Athena queries that make retroactive investigation write-ups fast.

---

## 4. Disaster Recovery — Policy + Tested Restore

**What the auditor asks for:**
1. Written **DR / business continuity policy**
2. **RTO/RPO targets** for each critical system
3. Evidence of a **recent DR test** — not "we could restore if we needed to," but "we did restore and here's what happened"

For AWS environments, the technical evidence typically includes:

```bash
# Backup coverage — which resources are covered by AWS Backup
aws backup list-protected-resources \
  --query 'Results[].{Resource:ResourceArn,Type:ResourceType}' \
  --output table

# Recent backup jobs — proof backups actually ran
aws backup list-backup-jobs \
  --by-state COMPLETED \
  --query 'BackupJobs[0:10].{Job:BackupJobId,Resource:ResourceArn,Date:CompletionDate}' \
  --output table
```

The critical piece is the **restore test**. Set up a quarterly (or at minimum, annual) restore drill — pick one backed-up resource, restore it to a test account, verify data integrity, document the elapsed time. That single-page write-up is the evidence the auditor wants.

Teams often show me their backup schedule and think it's enough. It isn't. Backups without a documented restore test fail this control.

---

## Evidence Collection Across Multiple Accounts

Once you have 3+ AWS accounts, running these commands manually per account becomes unmanageable. Your options:

1. **AWS Audit Manager** — AWS's own tool. Good for large, mature environments. Overkill and expensive for smaller setups.
2. **Security Hub's ISO 27001 standard** — the built-in ISO 27001:2013 compliance pack. Covers a subset of controls automatically, gives you a dashboard. Doesn't cover everything auditors ask for, but a useful baseline.
3. **Custom scripts** — the approach I've used. Bash or Python that assumes an audit-reader role in each account, runs the evidence collection commands, dumps outputs into a structured folder (`/evidence/{account_id}/{date}/`). Simple to write, cheap to run, and produces evidence in the exact format your auditor requests.

For most SMB and mid-size setups, the custom scripts approach is what I recommend. It's a one-day build that saves days of scrambling later. You can schedule it weekly via EventBridge and pipe results to S3 with lifecycle policies matching your log retention policy.

---

## Common Gaps I Find in Pre-Audit Reviews

Even teams with good AWS security posture consistently miss these during audit prep:

**No written policies backing the technical controls.** You have MFA enforced everywhere. You don't have a document that says "MFA is required." Auditors need both.

**Encryption "in place" but no proof of key rotation.** AES-256 on S3 is fine. But if you use customer-managed KMS keys, the auditor asks about rotation. Enable automatic annual rotation on all CMKs and pull the config as evidence.

**Access reviews performed but not documented.** Someone on the team spot-checks IAM quarterly. There's no artifact. If it's not written down, it didn't happen.

**No evidence of security awareness training for engineers with AWS access.** ISO 27001 A.7.2.2 (in the older 2013 version) requires this. AWS access without documented training is a finding.

**No documented offboarding process for AWS access.** When someone leaves, is their IAM Identity Center access revoked? Their access keys deleted? Their permissions on any assumed roles removed? You need a written process AND evidence it ran for the last few departures.

---

## When You're Getting Close to an Audit

Rough timeline that's worked for the environments I've prepped:

- **6+ months out**: start the investigation-notes habit; write policies if missing
- **3-4 months out**: build or deploy your evidence collection scripts
- **2 months out**: run a mock audit — go through the Annex A controls, for each one collect the exact evidence and see where the gaps are
- **1 month out**: fix the gaps found in the mock, run scripts weekly to keep evidence fresh
- **Audit week**: your evidence pack should already be complete; you should not be scrambling

If you're inside 2 months and you don't have most of this in place, it becomes a fire drill. That's usually when I get called.

---

## Key Takeaway

ISO 27001 in AWS is less about knowing the controls (they're all published) and more about producing the specific evidence your auditor accepts. The gap between "we're doing this" and "here's the proof, dated, signed, cross-referenced with the policy" is where first-time audits fail.

The habit that makes the biggest difference: **collect evidence continuously, not right before the audit.** Write investigation notes as you go, save credential reports monthly, run a restore drill quarterly. If you build the habit, your audit prep collapses from a 3-month scramble into a 3-week review of what you've already produced.

If you're facing an audit within the next 6 months and the checklist above surfaced gaps you didn't realize you had — that's the exact situation where an outside pair of hands compresses the work substantially. It's what I do.

---

## Related Reading

- [AWS Misconfigurations I Find in Every Security Audit](/posts/aws-security-misconfigurations-guide/) — the recurring technical findings across environments
- [AWS Security Checklist: 30-Minute Account Review](/posts/aws-security-checklist-2026/) — quick baseline check you can run before an audit
- [CloudTrail Log Analysis: How to Find Who Did What](/posts/aws-cloudtrail-log-analysis/) — Athena queries useful for retroactive investigation write-ups
- [Detect AWS IAM Privilege Escalation](/posts/aws-detecting-privilege-escalation/) — the kind of finding that becomes an investigation example
- [How to Detect AWS Root Account Usage](/posts/detect-root-account-usage/) — root usage is always an incident, always worth an investigation note
- [Enforcing Least Privilege in AWS IAM](/posts/aws-enforcing-least-privilege/) — the access reviews auditors ask about start here
