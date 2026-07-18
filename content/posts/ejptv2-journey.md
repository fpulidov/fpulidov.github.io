---
title: "eJPTv2 Prep Guide: Study Plan for Cloud Security Engineers"
date: 2025-09-08
draft: false
description: "How to prepare for eJPTv2 when your background is cloud security, not pentesting. Study plan, resource ranking, lab strategy, and what to focus on from a defender's perspective."
slug: "ejptv2-journey"
tags: ["ejpt", "ethical hacking", "pentesting", "career development", "certifications"]
keywords: ["ejptv2 study guide", "ejpt preparation", "ejptv2 study plan", "ejpt for cloud engineers", "junior penetration tester cert", "ejptv2 resources", "ine ejpt review"]
aliases: ["/ejpt-journey/"]
canonicalURL: "https://thehiddenport.dev/posts/ejptv2-journey/"
enable_comments: true
---

If your background is cloud security and you're thinking about breaking into pentesting, the eJPTv2 is a solid entry point. I took it coming from years of AWS security work — hardening infrastructure, responding to incidents, writing detection rules — and found the transition both natural and surprisingly humbling.

This post covers how I prepared, what resources were worth the time, and how a defender's background actually helps (and where it blinds you).

---

## Why eJPTv2 (and Why as a Cloud Engineer)

Working defense gives you a mental model of what *should* happen. Pentesting teaches you what *does* happen when those controls fail. After years of writing IAM policies and reviewing CloudTrail logs, I wanted to understand the attacker's side — not theoretically, but hands-on.

eJPTv2 is the right starting point because:
- It's **practical** — a 48-hour hands-on exam, not multiple choice
- It covers **network pentesting fundamentals** that cloud security often skips
- The difficulty is approachable without being trivial
- It forces you to **chain findings together**, not just run a scanner

---

## My Study Plan (6 Weeks)

| Week | Focus | Hours/week |
|---|---|---|
| 1–2 | INE course: networking, enumeration, web basics | 8–10 |
| 3–4 | TryHackMe labs: active practice | 10–12 |
| 5 | Weak areas + command cheat sheet | 6–8 |
| 6 | Practice exam + review | 8 |

Total: ~50–60 hours over 6 weeks. Doable alongside a full-time job if you're disciplined about evenings and weekends.

---

## Resources Ranked

### Worth every minute

- **INE's official eJPT course** — follows the exam objectives closely. Some modules feel slow, but skip at your own risk — the exam tests fundamentals, not flashy techniques.
- **TryHackMe rooms** — specifically: "Network Exploitation Basics", "Web Fundamentals", "Nmap", "Metasploit", "SQL Injection". Hands-on practice is where the learning actually sticks.
- **Obsidian for notes** — I built a personal knowledge base organized by technique. During the exam, having searchable notes saved me hours.

### Useful but not essential

- **HackTheBox (easy machines)** — good practice but overkill for eJPT scope. Save these for OSCP prep.
- **YouTube walkthroughs** (John Hammond, IppSec) — helpful for understanding methodology, but watching isn't doing.

### Skip

- **Any "eJPT dumps" or brain dumps** — the exam is hands-on, not memorization. Dumps won't help and are ethically questionable.
- **Overly broad "pentesting courses"** that cover 40 tools superficially — focus beats breadth at this level.

---

## What Cloud Security Background Gives You

Coming from AWS security, I had unexpected advantages:

- **Networking fundamentals** — VPC design, subnets, routing, firewall rules translate directly to understanding scan results and pivot opportunities.
- **Enumeration mindset** — cloud security is all about "what's exposed, what shouldn't be." That's literally what the first phase of a pentest is.
- **Log analysis** — reading Nmap output, HTTP responses, and service banners feels familiar when you've spent years reading CloudTrail JSON.
- **Scripting** — Bash and Python for automating checks is the same whether you're writing detection rules or exploitation scripts.

---

## Where Defenders Get Stuck

Being a defender also creates blind spots:

- **"I would never leave this open"** — you'll waste time assuming the target is hardened because *you* would have hardened it. The whole point is that it isn't.
- **Over-reliance on scanners** — in cloud security, AWS Config and Security Hub do the scanning for you. In pentesting, tools give you data but *you* have to chain it into access.
- **Privilege escalation feels foreign** — as a defender, you prevent it. As a pentester, you need to think creatively about *how* to do it. This was my weakest area initially.
- **Web exploitation** — if you've only done infrastructure security, SQLi and XSS feel entirely new. Budget extra time here.

---

## Exam Tips

Without spoiling anything:

1. **Enumerate everything before exploiting anything.** Scan all ports, all hosts. Document what's open. The exam rewards thoroughness.
2. **Take notes as you go.** Screenshot findings, write down credentials, map the network. You'll need to answer questions about your findings.
3. **Don't overcomplicate it.** If a service is running on an obvious port with a known vulnerability, try the obvious exploit. This isn't OSCP — they're not trying to trick you.
4. **Use your 48 hours wisely.** Take breaks. Sleep. A fresh brain finds things a tired one misses.
5. **Build a cheat sheet beforehand.** Nmap flags, Metasploit commands, SQLMap syntax, basic web payloads. Having these ready saves time during the exam.

---

## My Command Cheat Sheet (Abridged)

```bash
# Full TCP scan
nmap -sV -sC -p- -oN full_scan.txt TARGET

# UDP top ports
nmap -sU --top-ports 20 TARGET

# Directory brute force
gobuster dir -u http://TARGET -w /usr/share/wordlists/dirb/common.txt

# SQLMap basic
sqlmap -u "http://TARGET/page?id=1" --dbs

# Hydra SSH brute force
hydra -l admin -P /usr/share/wordlists/rockyou.txt ssh://TARGET

# Metasploit search
msfconsole -q -x "search type:exploit name:SERVICE"
```

---

## What's Next After eJPT

The natural progression:
- **eWPT** (web application pentesting) — if you enjoyed the web exploitation portions
- **OSCP** — the industry standard, significantly harder, requires months of dedicated practice
- **Cloud-specific pentesting** — combining AWS knowledge with offensive techniques (HackTricks Cloud, Pacu, CloudGoat)

For cloud security engineers specifically, I'd recommend going from eJPT → cloud pentesting tools (Pacu, Prowler in offensive mode) → OSCP. This path lets you leverage your existing expertise while building offensive skills.

---

## Key Takeaway

If you're in cloud security and feel like you only understand half the picture, pentesting fills in the other half. The eJPTv2 is a low-risk, high-reward way to start. Six weeks of focused study is enough if you're consistent.

The skills transfer in both directions — understanding attacks makes you a better defender, and your defensive background makes you a more methodical attacker.

---

**Related posts:**
- [How I Passed the AWS Security Specialty (SCS-C02)](/posts/aws-scs-c02-exam-experience/) — my other cert experience, from the defensive side
- [AWS Incident Response: 5 Scenarios & How to Contain Them](/posts/aws-incident-response-scenarios/) — the defender's side of what pentesters simulate
- [I Investigated a Real Phishing Attack — Here's the Full Kill Chain](/posts/real-world-phishing-incident-response/) — real-world attack chain analysis
- [Detect AWS IAM Privilege Escalation with CloudTrail](/posts/aws-detecting-privilege-escalation/) — detecting what pentesters do in AWS environments
