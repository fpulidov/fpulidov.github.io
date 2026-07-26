---
title: "AWS Incident Response Guide: The Framework for Cloud-Native IR (2026)"
date: 2025-05-04
lastmod: 2026-07-26
tags: ["aws", "incident-response", "cloud-security", "forensics", "ssm", "security-hub"]
keywords: ["aws incident response guide", "aws incident response framework", "cloud incident response process", "aws ir maturity", "incident response tabletop aws", "aws ir process", "small team incident response", "aws forensics"]
categories: ["Cloud Security", "Guides"]
description: "Most small teams write an IR plan and never test it. Here's the framework for cloud-native AWS incident response — from preparation and forensics to tabletop exercises that expose the gaps."
summary: "The full framework for AWS incident response — why cloud IR is fundamentally different, how to build maturity progressively, and how to actually test your plan with tabletop exercises."
slug: "incident-response-aws-guide"
draft: false
author: "Javier Pulido"
canonicalURL: "https://thehiddenport.dev/posts/incident-response-aws-guide/"
enable_comments: true
---

> **Last updated:** 2026-07-26 — expanded analysis phase, added IR maturity progression, added tabletop exercise section, sharpened cloud-vs-traditional IR framing.

Most incident response guides read like they were written for a datacenter in 2010. They assume you can walk to a rack, pull a cable, image a disk. In AWS, none of that applies.

This guide is the framework I recommend for teams building incident response from scratch in AWS — what to think about, in what order, and where the cloud-specific gotchas live. It's the *why* and *how to structure it* piece. For ready-to-use templates and Terraform automation, see the [AWS Incident Response Toolkit](/posts/aws-ir-toolkit/). For step-by-step containment on specific incidents, see [AWS Incident Response: 5 Scenarios](/posts/aws-incident-response-scenarios/).

---

## Why Cloud IR Is Fundamentally Different

Traditional incident response evolved around physical assets and network perimeters. Cloud IR breaks most of those assumptions:

**No physical isolation.** You can't unplug a cable. Containment happens through API calls — security group modifications, IAM policy detachments, EBS snapshots. If your responders don't have the right IAM permissions pre-provisioned, containment stalls while someone hunts for admin credentials at 2am.

**Ephemeral evidence.** An EC2 instance under Auto Scaling can be terminated and replaced automatically — taking your evidence with it. If GuardDuty flags an instance and the ASG replaces it 90 seconds later, the disk and memory you needed are gone unless you snapshotted first.

**Distributed logs.** In traditional IR, you might collect logs from a handful of servers. In AWS, evidence is scattered across CloudTrail, VPC Flow Logs, GuardDuty findings, Security Hub, ALB access logs, S3 server access logs, WAF logs, and application logs in CloudWatch. Each has its own retention window and query interface.

**Identity is the perimeter.** Compromised IAM credentials are the #1 attack vector, not network intrusion. Your IR playbook needs to treat "an IAM principal did something suspicious" as the primary incident type, not a footnote.

**Everything is API-driven.** Every containment action is a Terraform-able API call — which means it can be automated end-to-end. Teams that treat IR as manual runbooks are leaving a huge lever on the table.

Once you accept these differences, the structure of a good IR process changes. Everything below is designed for cloud-native workloads, not adapted from an on-prem playbook.

---

## IR Maturity Progression: What to Build When

Small teams often try to build the "complete" IR program on day one — dedicated forensic accounts, automated evidence collection, hot standby responders. Then they burn out before shipping anything usable. Build in stages:

### Month 1 — The Bare Minimum

- CloudTrail enabled in all regions, sending to an S3 bucket in a separate account (or at minimum with Object Lock)
- GuardDuty enabled in all regions
- One EventBridge rule that fires HIGH/CRITICAL GuardDuty findings to Slack or email
- A one-page written response process — who does what, whose phone rings, where the runbook lives
- Root account MFA on a physical key stored in a safe

That's it. If you have this, you can respond to an incident. Slowly, imperfectly, but you can respond.

### Month 3 — Making It Work Under Pressure

- Security Hub aggregating findings with AWS Foundational Security Best Practices standard
- Pre-provisioned IAM role for IR with permissions to snapshot volumes, isolate instances, and read logs across accounts
- SSM Session Manager enabled everywhere (so you can shell into a compromised instance without SSH)
- The [IR toolkit's notification pipeline](/posts/aws-ir-toolkit/) deployed so alerts land in the right channel with severity filtering
- First tabletop exercise run (see below) — usually reveals 3-5 things missing that seemed obvious

### Month 6+ — Scaling and Automation

- Dedicated IR AWS account (or hardened region) for evidence storage
- Automated evidence collection Lambda — triggered by high-severity findings, snapshots the volume + captures memory via AVML
- Runtime detection with [GuardDuty Runtime Monitoring](/posts/aws-guardduty-runtime-monitoring/) for EKS/EC2 workloads
- SIEM ingestion of GuardDuty + CloudTrail (Wazuh if budget-constrained, Splunk/Datadog otherwise)
- Quarterly tabletop cadence with rotating scenarios

Trying to skip stages usually fails. A team without CloudTrail in all regions doesn't need SOAR automation — they need CloudTrail in all regions.

---

## Phase 1: Preparation

### The Account Structure Decision

Where you store evidence and run analysis is the first architectural decision. Three viable options, ranked by security:

**Option A — Dedicated IR account (best).**
A separate AWS account within your Organization used exclusively for storing forensic snapshots, memory dumps, and running analysis. Access limited to security engineers via cross-account roles. Compromised workloads can't tamper with evidence because they're in a different account.

Use when: you have 3+ AWS accounts and use AWS Organizations. Adding one more account is trivial.

**Option B — Locked-down region (workable).**
One AWS region reserved for IR, protected by an SCP that denies access to anyone except the IR role. All evidence goes there. Analysis instances launched only in that region.

Use when: you're on a single account and can't add another. It's not as clean as separation, but SCPs make it materially harder for an attacker with compromised prod credentials to reach evidence.

**Option C — Same account, same region (not great, but sometimes reality).**
Evidence stored in a dedicated S3 bucket with Object Lock in Compliance mode. IAM policies keep the responder role out of production workloads and vice versa.

Use when: you have zero organizational buy-in for account/region separation. It's better than nothing. Fix it in month 6.

### Pre-Provision the Tools You'll Need Under Pressure

The mistake I see most: teams that plan to "figure it out when it happens." Under pressure, nobody remembers where the AVML binary is or which role has snapshot permissions. Pre-provision:

- **AVML** — bake into your base AMIs, or store in a private S3 bucket that the IR role can pull from
- **Isolation security group** — a pre-created SG named `sg-quarantine` that allows no ingress and only egress to your log-forwarding endpoints
- **IR IAM role** — permissions for `ec2:CreateSnapshot`, `ec2:ModifyNetworkInterfaceAttribute`, `ssm:SendCommand`, `s3:PutObject` on the evidence bucket, `logs:*` read on CloudTrail. Never attach `AdministratorAccess` even for IR — you'll regret it in the post-mortem.
- **Forensic AMI** — an EC2 AMI with Volatility, Plaso, log analysis tools pre-installed. Destroy after each investigation to guarantee a clean environment next time.
- **Evidence S3 bucket** — Object Lock in Compliance mode, KMS-encrypted with a key only the IR role can decrypt, versioning enabled.

For the full checklist and Terraform to deploy this, see the [AWS IR Toolkit](/posts/aws-ir-toolkit/).

---

## Phase 2: Detection & Triage

The goal isn't to detect everything — it's to detect the things that actually matter, with low enough noise that your team acts on them.

### Data Sources and What They Actually Tell You

- **GuardDuty** — anomalous behavior (unusual API calls, connections to known bad IPs, cryptocurrency mining). High signal-to-noise, low volume.
- **Security Hub** — compliance and configuration state. Higher volume; use for posture, not real-time incidents.
- **CloudTrail** — every API call. Not a detection source on its own; the correlation layer when you're investigating.
- **VPC Flow Logs** — network-level activity. Useful for scoping lateral movement after an incident. Rarely useful for initial detection.
- **DNS logs (Route 53 Resolver)** — DGA domains, DNS tunneling. Underused; enable it.

### Severity Filtering That Actually Works

The default GuardDuty output includes low-severity noise (informational findings, sample findings, expected activity from your own automation). If you page for every finding, your team stops reading pages within a week.

Filter aggressively at the EventBridge layer:

```json
{
  "source": ["aws.guardduty"],
  "detail-type": ["GuardDuty Finding"],
  "detail": {
    "severity": [{ "numeric": [">=", 7] }]
  }
}
```

Severity 7+ = HIGH and CRITICAL only. Everything else goes to a review queue (Slack channel, ticket), not to pages.

For step-by-step containment commands per incident type, see [AWS Incident Response: 5 Scenarios](/posts/aws-incident-response-scenarios/).

---

## Phase 3: Isolation

Three isolation approaches, ordered by preference:

**1. Security group swap (preferred).**
Replace the instance's security groups with `sg-quarantine`. The instance stays running (preserving memory), stops accepting new connections, and can only reach your log-forwarding endpoints. No reboot required.

```bash
aws ec2 modify-network-interface-attribute \
  --network-interface-id eni-xxxx \
  --groups sg-quarantine
```

**2. Detach from load balancer / target group.**
Stops public exposure without touching the instance itself. Useful when you need to preserve the exact runtime state before further action.

**3. Stop instance.**
Only as a last resort. You lose memory (and often, the most valuable forensic evidence). Do this only if the instance is actively causing harm and you can't contain it via network isolation fast enough.

**For IAM compromise**, isolation is different: attach a `Deny *` policy to the principal, disable the access key, and revoke active STS sessions. The [scenarios post](/posts/aws-incident-response-scenarios/#scenario-1-compromised-iam-credentials) covers this in detail.

---

## Phase 4: Evidence Collection

Once isolated, capture evidence before anything changes. Order matters — memory volatile, disk persistent, logs already exist.

### Memory First

Memory contains active processes, network connections, decrypted secrets, and injected code that never touched disk. Capture it before you stop the instance:

```bash
aws ssm send-command \
  --document-name "AWS-RunShellScript" \
  --targets "Key=instanceIds,Values=i-xxxx" \
  --parameters commands=["sudo /opt/avml/avml /tmp/memdump.lime && \
    aws s3 cp /tmp/memdump.lime s3://ir-evidence-bucket/<case-id>/memdump.lime"]
```

### Disk Snapshots

Snapshot every attached volume. Tag with case ID and timestamp so you can find them later:

```bash
aws ec2 create-snapshot \
  --volume-id vol-xxxx \
  --description "IR-2026-042 evidence snapshot" \
  --tag-specifications 'ResourceType=snapshot,Tags=[
    {Key=CaseId,Value=IR-2026-042},
    {Key=Evidence,Value=true},
    {Key=CollectedAt,Value=2026-07-26T14:23:00Z}
  ]'
```

Copy snapshots to the IR account/region. Encrypt with the IR KMS key.

### Chain of Custody in a Cloud World

Traditional chain of custody assumes physical handoff — evidence bag, signature, locker. In cloud IR, chain of custody is:

- **CloudTrail logs of the snapshot/copy operations** — proof of who created what evidence, when, from where
- **SHA-256 hashes of the evidence artifacts** — stored separately (in your case management system, not next to the evidence)
- **KMS key access logs** — proof of who decrypted the evidence, when
- **S3 Object Lock retention** — proof that the evidence hasn't been tampered with since collection

Every one of these is automatic if you configured the account right. That's the beauty of cloud IR when done well — chain of custody becomes an emergent property of the infrastructure, not paperwork.

---

## Phase 5: Analysis

The phase most teams underinvest in. You can collect perfect evidence and still miss the incident if you don't know what to look for.

### Memory Analysis

Mount the memory dump with Volatility on a forensic EC2 instance:

```bash
volatility -f memdump.lime --profile=LinuxUbuntu2004x64 linux_pslist
volatility -f memdump.lime --profile=LinuxUbuntu2004x64 linux_netstat
volatility -f memdump.lime --profile=LinuxUbuntu2004x64 linux_bash
```

What to look for:

- **Unexpected processes** — a `python3` running from `/tmp` is suspicious. So is anything running out of `/dev/shm` (memory-only filesystem, often used by malware to avoid disk persistence).
- **Suspicious network connections** — connections to non-standard ports, to IPs outside your VPC's expected traffic, or to known bad IPs from threat intel feeds.
- **Bash history in memory** — even if the attacker deleted `.bash_history`, the recent commands live in memory until the shell exits. `linux_bash` extracts them.

### Disk Analysis

Mount the snapshot **read-only** on a forensic instance. Never mount evidence writable — a single accidental modification breaks chain of custody.

```bash
aws ec2 create-volume --snapshot-id snap-xxxx --availability-zone eu-west-1a --volume-type gp3
# attach to forensic instance
sudo mount -o ro,noexec,nosuid /dev/xvdf1 /mnt/evidence
```

Focus areas:

- `/var/log/auth.log` (Linux) or Security event log (Windows) — authentication history, failed logins, privilege escalation
- `/tmp` and `/dev/shm` — staging areas for dropped tools
- `/etc/cron.*` and systemd timers — persistence mechanisms
- Web server access logs — the initial exploitation vector, often
- User home directories — `.ssh/authorized_keys` for planted access, shell history

### CloudTrail Analysis

The unique advantage of cloud IR: every API call is logged. Patterns that indicate compromise:

- **`GetCallerIdentity` from an unusual IP** — often the first thing an attacker does after stealing credentials, to confirm they work
- **`ConsoleLogin` events followed by IAM changes** — someone logged in and immediately started creating access keys or roles
- **Large batches of `Describe*` / `List*` calls** — reconnaissance, mapping out what the compromised principal can access
- **`AssumeRole` chains** — attackers pivoting through roles to escalate privilege
- **`DeleteTrail`, `StopLogging`, `PutBucketPolicy` on logging buckets** — attempts to cover tracks. Should be near-impossible if you've configured logging correctly, but always worth checking

For step-by-step queries, see [AWS CloudTrail Log Analysis for Security](/posts/aws-cloudtrail-log-analysis/).

### Common False Positives

Not everything unusual is malicious. Before you page the CTO, check:

- **New deployment or migration** — a burst of unusual API activity might be a new service coming online
- **Automated scanners** — Prowler, Steampipe, Wiz agents make lots of Describe calls that look like reconnaissance
- **New team member** — someone joining might legitimately access things they've never touched before
- **Backup or DR job** — cross-region snapshot copies can look like data exfiltration if you don't know they're scheduled

The team that responds to every anomaly burns out fast. The team that ignores them all gets breached. The middle ground is documenting expected patterns so responders can quickly rule them out.

---

## Phase 6: Remediation & Lessons Learned

Once the incident is contained:

- **Rotate credentials** — every access key, every long-lived credential that could have been exposed. When in doubt, rotate.
- **Find root cause** — not "the attacker got in via SSH" (that's the vector) but "we had a default security group allowing SSH from 0.0.0.0/0" (that's the cause). Fix the class of problem, not the specific instance.
- **Rebuild, don't clean** — assume the compromised workload is untrustworthy. Terminate it, redeploy from clean code. Never trust a system after compromise, no matter how thoroughly you think you cleaned it.
- **Blameless retro** — the person who ran the command that led to the incident is often the same person who spotted it. Blame kills the willingness to report future issues.
- **Update the runbook** — every incident should produce at least one change to your IR process. If your post-mortem doesn't produce concrete process improvements, you're doing them wrong.

---

## Tabletop Exercises: How to Actually Test Your IR

The single highest-leverage IR activity, and the one most teams skip. I've run tabletop exercises for teams that had beautifully documented IR plans on paper — and within 20 minutes of the first scenario, the whole thing fell apart. Not because the plan was bad, but because nobody had walked through it under (simulated) pressure.

### What a Tabletop Actually Is

Not a technical simulation. Not a red team exercise. Not a fire drill. A tabletop is a facilitator-led discussion where the team walks through a realistic incident scenario step by step, saying what they'd do at each moment. No systems are touched. The whole exercise takes 60-90 minutes.

The point is not to test the technology. It's to test **the humans, the process, and the assumptions** — which is where every real incident actually breaks.

### The Format That Works

- **Facilitator** — one person, ideally not on the responding team. Runs the scenario, throws in complications, keeps discussion focused. Can be you initially; rotate later.
- **Participants** — the actual on-call responders. 3-6 people is ideal. More than that, people disengage.
- **Observers** — engineering managers, product leads, execs. They watch, they don't speak. This exposes them to what response actually looks like and often unlocks budget for gaps.
- **Duration** — 90 minutes. 30 for setup + scenario, 45 for walkthrough, 15 for retro.

### Scenarios That Reveal the Most Gaps

Start with realistic, then get harder. My starter set:

1. **Compromised IAM access key** — an engineer's key was pushed to a public GitHub repo. GuardDuty fires. What do you do first? (Reveals: who has permission to disable the key? Do you know which resources that key can access?)
2. **Suspicious EC2 activity** — GuardDuty flags an instance mining crypto. It's a production API server. (Reveals: isolation vs. availability tradeoff, who owns the decision, whether you have snapshot procedures)
3. **Public S3 bucket found via Have I Been Pwned** — someone external reports your bucket is public and contained customer data. (Reveals: legal/comms process, breach notification timelines, whether you know who owns the bucket)
4. **Insider threat** — a departed employee's credentials were used yesterday. (Reveals: offboarding gaps, session revocation, audit trail literacy)
5. **Ransomware in EKS** — pods are being encrypted, spreading between namespaces. (Reveals: whether anyone knows the network policies, backup restore process, containment for containerized workloads)

Change one scenario per quarter. Repeating scenarios teaches the exact scenario; varying them teaches the framework.

### What to Actually Do During the Exercise

At each step, the facilitator asks:

- Who owns this decision?
- What tool would you use?
- What permission do you need? Do you have it?
- Where would you find this information?
- What happens if the answer is "I don't know"?

The answers reveal the gaps. Document them. Every "I don't know" or "we should probably..." becomes a follow-up item.

### Common Findings From Tabletops

Predictable but universal:

- **Nobody knows who owns the decision** to isolate a production workload — everyone waits for the CTO
- **The IR role doesn't exist yet**, or has been rotated and nobody has current access
- **The runbook lives in a Confluence page** nobody can find under stress
- **Contact info for critical people is stale** — the number listed for the on-call engineer is 6 months out of date
- **The team assumes GuardDuty is enabled in region X** — it isn't
- **The evidence bucket has never been tested** for write access with the IR role
- **Nobody has ever actually done a snapshot restore** and doesn't know how long it takes

The goal isn't to solve all of these in the tabletop. It's to *find them* so you can solve them before a real incident.

### Cadence

Quarterly at minimum. Monthly if you're building out the process for the first time. Skip a quarter and you'll be surprised how much decays.

---

## Common Mistakes Small Teams Make

Patterns I see repeatedly:

**1. Building the perfect plan before shipping any of it.**
The team spends 3 months writing the IR playbook. During those 3 months, they have no IR capability. Ship the minimum in month 1, iterate from real incidents and tabletops.

**2. Confusing detection with response.**
Enabling GuardDuty is not incident response. It's incident *notification*. Response is what happens after the alert fires. Most teams have the detection layer but no response process.

**3. Storing evidence in the compromised account.**
"We have Object Lock, we're fine." No — if the account itself is compromised, the attacker can potentially disable Object Lock rules, or exfiltrate the KMS keys, or simply flood the bucket with garbage. Cross-account isolation is worth the setup cost.

**4. Over-relying on automation.**
Automated isolation Lambdas are great — until they trigger on a false positive at 3am and take down a production API. Automation should assist responders, not replace them, especially early on. Build tooling that reduces response time, not tooling that responds without humans.

**5. Never testing.**
Covered above. Every team that skips tabletops discovers their plan is broken during the first real incident.

**6. Treating IR as a security-team-only concern.**
Real incidents pull in engineering, legal, comms, customer support, execs. If those people first meet during an incident, the response is chaos. Include them in tabletops.

---

## Long-Term Evidence Storage

Once analysis is complete, evidence must be retained — regulations (PCI-DSS, ISO 27001, GDPR) often mandate retention periods measured in years.

### S3 Object Lock in Compliance Mode

The gold standard for tamper-proof evidence storage:

```bash
aws s3api put-object-lock-configuration \
  --bucket ir-evidence-storage \
  --object-lock-configuration '{
    "ObjectLockEnabled": "Enabled",
    "Rule": {
      "DefaultRetention": {
        "Mode": "COMPLIANCE",
        "Days": 365
      }
    }
  }'
```

Compliance mode is true WORM — even the root user can't delete the objects before the retention period expires. Combined with versioning, this gives you a legally defensible evidence chain.

### Lifecycle to Glacier Deep Archive

Evidence that's rarely accessed but must be retained belongs in Glacier Deep Archive. Roughly 1/25th the cost of S3 Standard:

```hcl
resource "aws_s3_bucket_lifecycle_configuration" "evidence_archive" {
  bucket = aws_s3_bucket.evidence.id

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

Keep metadata and hashes in S3 Standard for fast audit lookup. Move the actual evidence blobs to Deep Archive after 30 days.

---

## Getting Started

If you're building your first IR process:

1. Start with the [month 1 checklist](#month-1--the-bare-minimum) above
2. Download the [AWS IR Toolkit](/posts/aws-ir-toolkit/) for playbook templates and Terraform for the notification pipeline
3. Run your first tabletop within 4 weeks of shipping the basics — the goal is to expose gaps, not to be perfect
4. Read [5 IR Scenarios](/posts/aws-incident-response-scenarios/) for concrete containment steps and [a real phishing case study](/posts/real-world-phishing-incident-response/) for what full IR looks like end-to-end

Building IR is iterative. Ship the minimum, test with tabletops, iterate from real incidents, expand coverage as your team grows.

If you'd like help structuring your team's IR process — from designing the maturity roadmap to running your first tabletops — [that's one of the engagements I take on](/consulting/).

---

**Related guides:**
- [AWS Incident Response Toolkit](/posts/aws-ir-toolkit/) — free download: playbook templates, Terraform notification pipeline, forensic tool matrix
- [AWS Incident Response: 5 Scenarios & How to Contain Them](/posts/aws-incident-response-scenarios/) — step-by-step containment for compromised credentials, public S3, cryptomining, privilege escalation
- [Real-World Phishing Incident Response](/posts/real-world-phishing-incident-response/) — full IR walkthrough of a real incident
- [AWS CloudTrail Log Analysis for Security](/posts/aws-cloudtrail-log-analysis/) — the primary analysis data source
- [AWS GuardDuty Setup: Route Findings to Slack](/posts/aws-guardduty-setup/) — the detection layer that feeds this process
