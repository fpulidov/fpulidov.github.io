---
title: "I Investigated a Real Phishing Attack — Here's the Full Kill Chain"
date: 2026-07-17
draft: false
description: "A real spearphishing incident I handled from ticket to remediation. Full attack chain reconstruction, forensic analysis, IOC extraction, and the mistakes that cost us days."
summary: "Walkthrough of a real phishing-initiated endpoint compromise I investigated. Covers the full attack chain from password-protected PDF to PowerShell loader, forensic analysis in an isolated lab, and the response failures that delayed containment."
slug: "real-world-phishing-incident-response"
tags: ["Incident Response", "Phishing", "Forensics", "Security", "Email Security", "MITRE ATT&CK"]
categories: ["Cloud Security", "Incident Response"]
keywords: ["phishing incident response", "spearphishing attack chain", "phishing forensic analysis", "BEC incident response", "email compromise investigation", "mshta attack chain", "powershell phishing payload"]
canonicalURL: "https://thehiddenport.dev/posts/real-world-phishing-incident-response/"
enable_comments: true
---

Most phishing posts explain what phishing *is*. This one walks through a real incident I handled back in 2018 — from the moment the ticket came in to the full attack chain reconstruction in an isolated lab.

The attacker got code execution on a corporate endpoint and abused the victim's email identity to stage ~300 outbound drafts to external recipients. I'll break down every stage of the kill chain, show how I extracted IOCs from the payload without executing it, and — maybe more usefully — explain what we got wrong in the response that cost us four days.

I was working security for a mid-size SaaS company at the time — around 400 employees, mostly Windows endpoints, Microsoft 365 for email. The security team was small (just me and one other person), which made every gap in our process painfully visible.

---

## How It Started: A Ticket Nobody Saw

The incident began with a support ticket: *"Problems with possible phishing."* The affected user reported that desktop folders were opening on their own and approximately 300 draft emails addressed to external recipients had appeared in their mailbox.

I was working an unrelated ticket when I happened to notice it. No notification had fired. No alert. The ticket had been sitting there for **four days** before anyone from security saw it.

That delay is the first lesson, and I'll come back to it.

When I read the details — folders opening autonomously, hundreds of outbound drafts the user didn't create — this wasn't a "possible" phishing. This was confirmed compromise with active mailbox abuse.

---

## The Timeline

Reconstructed from email gateway logs, the support ticket, and forensic analysis:

| Day | Event |
|---|---|
| **Day 0** (10 days before report) | Email gateway detects phishing messages from two external senders to several internal functional mailboxes. The senders were likely compromised third parties — legitimate businesses whose accounts had been taken over. |
| **Day 10** | User opens a support ticket reporting strange behavior: folders opening by themselves, ~300 draft emails to external addresses appearing in their mailbox. |
| **Day 10 + 20 min** | I request more details — what systems, what behavior, when it started. |
| **Day 10 + 30 min** | User replies with screenshots showing the drafts. |
| **Day 14** | I see the reply. Four-day gap caused by missing notifications on the ticket queue. Immediately escalate to IT management. |
| **Day 14** | User is told to stop work and power off the laptop. IT cuts all remote connections to the device. |
| **Day 14–15** | I begin forensic analysis of the attachment in an isolated lab. Attack chain reconstructed. |
| **Day 15** | Endpoint reimaged and replaced by IT. Final-stage attacker infrastructure already offline (HTTP 404). |

---

## Reconstructing the Kill Chain

The user had received a spearphishing email with a password-protected PDF attachment. I took the original file and analyzed it statically in an isolated lab — no execution, just dissection.

Here's what each stage did:

### Stage 1: Password-Protected PDF (Delivery)

The attachment was a password-protected PDF. Password protection isn't there to protect the user — it's an **evasion technique**. Most email gateway sandboxes can't open password-protected files, so they pass through uninspected.

Static analysis with `pdfid` and `pdf-parser` showed:
- No embedded JavaScript
- No embedded files
- No auto-execution triggers
- The `/OpenAction` only set the initial view (`/FitH`)
- The PDF was generated with TCPDF (a PHP library) — this was programmatically created, not a modified legitimate document

The malicious element was a single **clickable link annotation** overlaying the page body. The entire PDF was a clickable button.

### Stage 2: Redirect & ZIP Download

Clicking the link resolved to a page hosted on shared hosting infrastructure. That page delivered a ZIP archive.

### Stage 3: The .LNK Launcher

The ZIP contained a single Windows shortcut (`.lnk`) file disguised with a Microsoft Edge icon. Users see what looks like a browser bookmark or saved webpage.

The shortcut's target was:

```
powershell.exe -NoProfile -WindowStyle Hidden -Command ...
```

A hidden PowerShell window. No console flash, no visible execution.

### Stage 4: Obfuscated PowerShell

The `.lnk` command built a Base64-encoded string using decoy markers and a junk GUID prefix split on `|`. It reassembled the real payload via `[ScriptBlock]::Create`, then executed it.

The decoded command launched `mshta.exe` against a remote HTA URL.

### Stage 5: MSHTA + VBScript Injection

This is where it gets clever. The HTA file created a `<script>` element with `type="text/vbscript"` pointing to a remote URL, then appended it to the document head.

Why this matters: if you opened this HTA in a normal browser, **nothing would happen**. Browsers ignore VBScript. But `mshta.exe` executes it — which is precisely why the chain used `mshta.exe` in the first place. This is a well-known living-off-the-land technique ([T1218.005](https://attack.mitre.org/techniques/T1218/005/)).

### Stage 6: Final Payload (Not Retrieved)

The VBScript loader at the final URL was supposed to fetch and run the implant. But by the time I analyzed it, the attacker infrastructure was returning HTTP 404. The campaign was over — either taken down or rotated.

This is common with commodity phishing kits: infrastructure is ephemeral. If you don't capture the payload in the first hours, it's gone.

### What We Observed on the Endpoint

Even without the final payload, the effects were clear:
- Unexpected folder creation on the desktop
- ~300 outbound email drafts to external recipients
- Behavior consistent with mailbox identity abuse and attempted lateral spread

The drafts were the real danger. This wasn't just an endpoint compromise — it was **business email compromise (BEC) staging**. The attacker was using the victim's corporate identity to reach clients and partners.

---

## MITRE ATT&CK Mapping

| Technique | What We Saw |
|---|---|
| [T1566.001](https://attack.mitre.org/techniques/T1566/001/) — Spearphishing Attachment | Password-protected PDF via email |
| [T1204.002](https://attack.mitre.org/techniques/T1204/002/) — User Execution: Malicious File | User clicked link in PDF, opened ZIP and .lnk |
| [T1036.005](https://attack.mitre.org/techniques/T1036/005/) — Masquerading | .lnk disguised with Edge icon |
| [T1059.001](https://attack.mitre.org/techniques/T1059/001/) — PowerShell | Hidden, Base64-obfuscated command |
| [T1218.005](https://attack.mitre.org/techniques/T1218/005/) — System Binary Proxy: Mshta | mshta.exe running remote HTA |
| [T1059.005](https://attack.mitre.org/techniques/T1059/005/) — Visual Basic | Injected VBScript loader |
| [T1027](https://attack.mitre.org/techniques/T1027/) — Obfuscated Files | Base64 + decoy markers + junk GUID split |
| [T1534](https://attack.mitre.org/techniques/T1534/) — Internal Spearphishing | ~300 drafts from the compromised account |

---

## What We Got Wrong

This section matters more than the attack chain. Attackers will always find a way in. What determines the outcome is how fast and how well you respond.

### 1. The Four-Day Notification Gap

The support ticket sat unnoticed for four days because security incident notifications weren't configured on the ticketing system. I found it by accident while working on something else.

Four days is an eternity in incident response. During that window, the attacker had uninterrupted access to the user's mailbox and potentially their credentials.

**Fix:** Security incident tickets must trigger immediate notifications to the security team. No exceptions. If your ticketing system doesn't support this reliably, set up a parallel alerting channel — a dedicated Slack channel, a PagerDuty integration, anything that guarantees eyes-on within minutes.

### 2. Evidence Destroyed Before Collection

IT reimaged the laptop before anyone captured a disk or memory image. This is understandable — the priority was getting the user back to work — but it destroyed our ability to:
- Recover the final payload
- Identify persistence mechanisms
- Determine what data was accessed or exfiltrated
- Confirm the full scope of compromise

**Fix:** Your incident response procedure needs a clear decision point: **image before you reimage**. Even a basic `dd` of the disk or a memory dump with a tool like WinPmem gives you something to work with later. The 30 minutes this takes can save weeks of uncertainty.

### 3. Identity Remediation Was Treated as Secondary

The initial response focused on the endpoint: isolate it, reimage it, replace it. But the real exposure was the **cloud identity**. The user's email account was actively being abused, and reimaging a laptop does nothing to revoke OAuth tokens, clear malicious mail rules, or rotate credentials.

For any incident involving email or identity compromise, the containment order should be:

1. **Revoke all active sessions and tokens** (immediately)
2. **Reset password + MFA** (immediately)
3. **Audit mailbox rules and OAuth grants** (within the hour)
4. **Then** deal with the endpoint

The endpoint is a crime scene. The identity is a live weapon.

---

## Indicators of Compromise

I'm sharing sanitized IOC patterns rather than exact values, since the infrastructure is down and the specific indicators have limited value. The **behavioral indicators** are what matter for detection:

| Type | What to Hunt For |
|---|---|
| Email pattern | Password-protected PDF attachments from compromised third-party senders |
| Execution chain | `explorer.exe` → `powershell.exe -WindowStyle Hidden` → `mshta.exe` |
| Network | Outbound `mshta.exe` connections to unfamiliar domains |
| Mailbox abuse | Sudden creation of bulk draft emails to external recipients |
| Endpoint | Unexpected folder creation in user profile directories |

If your EDR or SIEM can alert on `mshta.exe` spawned by `powershell.exe` with a `-WindowStyle Hidden` flag, you'll catch this entire class of attack — not just this specific campaign.

---

## What Would Have Caught This Earlier

Looking back, three controls would have changed the outcome:

1. **EDR with behavioral detection.** The endpoint had no EDR agent. A solution like CrowdStrike or Defender for Endpoint would have flagged the PowerShell → mshta chain immediately — this is a textbook living-off-the-land pattern that modern EDR detects out of the box.

2. **Mail gateway rules for password-protected attachments.** These should be quarantined or at minimum flagged for manual review. Legitimate password-protected PDFs exist, but they're rare enough that a quarantine-and-release workflow is worth the friction.

3. **Mailbox anomaly detection.** 300 draft emails appearing in an account should trigger an automated alert. If you're running Microsoft 365, Defender for Office 365 can detect this. If not, a simple rule watching for bulk draft creation would work.

---

## Connecting This to AWS

If you're reading this blog, you probably work in AWS environments. The same identity-first response principles apply:

- **Compromised IAM credentials** require immediate key rotation and session revocation — not just "delete the EC2 instance." See [AWS Incident Response: 5 Scenarios & How to Contain Them](/posts/aws-incident-response-scenarios/).
- **CloudTrail is your forensic timeline** for cloud incidents the same way email gateway logs were mine here. If you haven't set up centralized logging, see [CloudTrail Log Analysis with Athena](/posts/aws-cloudtrail-log-analysis/).
- **GuardDuty** is the behavioral detection layer that would have caught anomalous API calls — the cloud equivalent of EDR. See [Setting Up AWS GuardDuty](/posts/aws-guardduty-setup/).
- **Privilege escalation detection** is critical when an attacker gains any foothold. See [Detect AWS IAM Privilege Escalation with CloudTrail](/posts/aws-detecting-privilege-escalation/).

The lesson is the same across corporate IT and cloud: **identity is the perimeter now**, and your response procedures need to treat it that way.

---

## Key Takeaways

1. **Static analysis is enough to reconstruct most attack chains.** I never executed the payload. `pdfid`, `pdf-parser`, and reading the PowerShell/HTA/VBScript source told me everything I needed to know.
2. **The response matters more than the attack.** A four-day delay and destroyed evidence hurt more than the phishing itself.
3. **Identity containment comes before endpoint remediation.** Reimaging a laptop while the attacker still controls the email account is treating the symptom, not the disease.
4. **Attacker infrastructure is ephemeral.** If you don't capture payloads early, they'll be gone. Automate artifact collection.
5. **Password-protected attachments are a red flag.** They exist primarily to bypass security controls. Treat them accordingly.

---

**Related guides:**
- [AWS Incident Response: 5 Scenarios & How to Contain Them](/posts/aws-incident-response-scenarios/)
- [CloudTrail Log Analysis with Athena: Compliance Forensics](/posts/aws-cloudtrail-log-analysis/)
- [Setting Up AWS GuardDuty: EventBridge Alerts & Threat Detection](/posts/aws-guardduty-setup/)
- [AWS IR Playbook Template (Free)](/posts/aws-ir-playbook-template/)
