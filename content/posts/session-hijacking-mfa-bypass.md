---
title: "Session Hijacking: How Stolen Cookies Bypass MFA (and How to Catch It)"
date: 2026-11-27
draft: false
description: "MFA protects the login, not the session that comes after it. How attackers steal session cookies with infostealers and phishing proxies, why passkeys only stop one of the two, and how to detect and contain it in Microsoft 365, Google Workspace, and AWS."
summary: "A practical guide to session hijacking: how session cookies and tokens get stolen (infostealers, AiTM phishing, malicious extensions), why MFA doesn't stop a replayed session, what actually helps in 2026 (device-bound sessions, token protection, shorter sessions), and how to detect and revoke hijacked sessions in Microsoft 365, Google Workspace, and AWS."
slug: "session-hijacking-mfa-bypass"
lastmod: 2026-11-27
tags: ["Security", "Credentials", "MFA", "Identity", "Threat Detection", "Incident Response"]
keywords: ["session hijacking", "session cookie theft", "pass the cookie attack", "bypass mfa session cookie", "stolen session token", "infostealer session cookies", "how to prevent session hijacking", "detect session hijacking"]
categories: ["Security"]
author: "Javier Pulido"
canonicalURL: "https://thehiddenport.dev/posts/session-hijacking-mfa-bypass/"
enable_comments: true
---

"We have MFA everywhere" is one of the most common things I hear right before an account takeover. It's true, and it doesn't matter — because the attacker never logged in. They walked in with a session that was *already* logged in.

That's session hijacking: stealing the cookie or token a service hands you *after* you pass MFA, and replaying it from somewhere else. The service sees a valid, authenticated session and has no reason to ask for a second factor. MFA did its job; it protected the login. Nobody protected what came after.

This post covers how sessions actually get stolen, why the usual advice only stops half of it, what genuinely helps in 2026, and how to detect and kill a hijacked session in Microsoft 365, Google Workspace, and AWS.

---

## What a "session" actually is

When you sign in to Microsoft 365, Google, Okta, or the AWS console, you do the hard part once — password, MFA prompt, maybe a device check. The service then issues a **session cookie or token**: a bearer credential your browser presents on every request so you don't have to log in again for hours or days.

"Bearer" is the important word. Whoever holds the cookie *is* you, as far as the service is concerned. Unless the session is bound to your device (more on that below), it works just as well from an attacker's laptop in another country.

Some sessions are short (an hour). Many are long — days, weeks, sometimes "until you sign out." And some services issue **refresh tokens** that can mint new sessions for much longer than any single cookie lives. A stolen refresh token is the jackpot.

## The three ways sessions get stolen

**1. Infostealer malware (the big one).** Infostealers are commodity malware — sold as a subscription — that grabs everything a browser has saved: passwords, autofill data, and **cookies for every site the user is logged into**. It often runs once, exfiltrates, and deletes itself. The haul is packaged as a "log" and sold in bulk, sorted by which services it contains. A single log from a developer's laptop can hold live sessions for your SSO portal, your email, your cloud console, and your CI system.

The infection usually doesn't happen on a managed corporate machine. It happens on a personal laptop where someone also checks work email, or a contractor's device you've never seen, after a cracked game or a fake software download.

**2. Adversary-in-the-middle (AiTM) phishing.** Instead of a fake login page that just collects a password, the phishing site is a **reverse proxy** in front of the real one. The victim logs in to the genuine service — including a real MFA prompt — through the attacker's proxy, which captures the session cookie the service issues at the end. Off-the-shelf kits make this routine, and it defeats push notifications, SMS codes, and authenticator-app codes alike.

**3. Malicious or compromised browser extensions.** An extension with broad permissions can read cookies directly from the browser. Researchers demonstrated this against Microsoft 365 in 2025 with a technique dubbed "Cookie-Bite" — an extension quietly exporting Entra ID session cookies. Extensions get bought, updated, and turned malicious after they've built up an install base.

## Why "just use passkeys" only fixes half of it

Phishing-resistant MFA — FIDO2 security keys and passkeys — is the single best upgrade most organizations can make. It **kills AiTM phishing**: the credential is cryptographically bound to the real domain, so a proxy on a look-alike domain can't complete the login.

But it does **nothing against infostealers**. The malware isn't involved in the login at all; it copies the session *after* a perfectly legitimate, passkey-protected sign-in. Same for malicious extensions. So passkeys close one of the three doors. The other two need different controls.

## What actually helps in 2026

**Bind sessions to the device.** This is the real fix, and it's finally arriving:

- **Google Workspace / Chrome:** *Device Bound Session Credentials (DBSC)* ties the session to a key stored in the device's secure hardware, so a copied cookie stops working on another machine. It became generally available in Chrome on Windows in 2026 and is on by default for Workspace users there; macOS support was announced as coming next.
- **Microsoft Entra:** *Token Protection* (a Conditional Access session control) binds tokens to the device — but read the fine print: it covers supported **native apps** on Windows (and Apple platforms via the Enterprise SSO plug-in on managed devices). **Browser sessions aren't covered**, which is exactly where most cookie theft happens.

Device binding is a big step, but coverage is still partial. Treat it as one layer, not a solution.

**Require managed, compliant devices for anything sensitive.** If only enrolled, healthy devices can reach your admin consoles and SSO portal, a stolen session replayed from an attacker's machine fails the device check (where the device check is evaluated per request or per token refresh). This also shrinks the "personal laptop" infection surface.

**Shorten sessions where it matters.** A session that lasts 90 days is a 90-day window for whoever steals it. Keep everyday sessions reasonable and make privileged ones short — admin consoles, cloud access, anything that can change other people's access. Users tolerate re-authenticating for admin work; they shouldn't tolerate it for email.

**Control browser extensions.** Allowlist extensions on managed browsers. Most organizations have never looked at what's installed.

**Stop saving work passwords in the browser.** Use a password manager. It doesn't protect cookies, but it removes the passwords from the same haul.

## How to detect a hijacked session

The core signal is simple: **one session, two places.** A legitimate session comes from one device and a stable network. A hijacked one suddenly appears from a different IP, ASN, country, or user agent — often while the real user is still active on theirs.

**Microsoft 365 / Entra ID.** Entra ID Protection (P2) raises risk detections such as *anomalous token* and *unfamiliar sign-in properties* that are designed for this. Without P2, look in sign-in logs for the same user active from two distant locations or networks in a short window, and for token activity that doesn't match the user's usual devices. Continuous Access Evaluation helps revocation take effect quickly for supported apps.

**Google Workspace.** Use the Admin console's audit and investigation tools to look for sign-ins and activity from unusual locations and devices; with DBSC enabled, the audit logs also show session-binding events, which help you see which sessions are actually bound.

**AWS.** Console and IAM Identity Center sessions show up in CloudTrail as temporary credentials (`ASIA…` access key IDs). A hijacked session reuses the *same* session credentials from a new IP — and notably, replaying a stolen session doesn't produce a new `ConsoleLogin` event, so alerting on logins alone misses it. Hunt for one temporary key used from more than one source:

```sql
SELECT useridentity.arn,
       useridentity.accesskeyid,
       count(DISTINCT sourceipaddress)  AS source_ips,
       array_agg(DISTINCT sourceipaddress) AS ips,
       array_agg(DISTINCT useragent)    AS user_agents,
       min(eventtime) AS first_seen,
       max(eventtime) AS last_seen
FROM cloudtrail_logs
WHERE useridentity.accesskeyid LIKE 'ASIA%'
  AND sourceipaddress NOT LIKE '%amazonaws.com'
  AND eventtime > to_iso8601(current_timestamp - interval '1' day)
GROUP BY 1, 2
HAVING count(DISTINCT sourceipaddress) > 1;
```

Expect some noise — VPN reconnects, mobile networks, IPv4/IPv6 switching — so in practice you tune by ASN or country rather than raw IP. ([CloudTrail Log Analysis](/posts/aws-cloudtrail-log-analysis/) covers setting up the Athena table this runs against.) GuardDuty adds anomaly-based IAM findings on top, which is one more reason to have it on ([setup guide](/posts/aws-guardduty-setup/)).

## Responding: revoke the session, not just the password

The classic mistake: someone's account is compromised, IT resets the password, ticket closed. **A password reset doesn't necessarily kill existing sessions or refresh tokens.** The attacker's stolen session can keep working.

The right order:

1. **Revoke all sessions and refresh tokens for the user.** In Entra ID, *Revoke sessions* on the user (or `Revoke-MgUserSignInSession`). In Google Workspace, sign the user out of all sessions from the Admin console. In AWS IAM Identity Center, delete the user's active sessions — and remember that console role sessions already issued **keep working until they expire** (up to the permission set's session duration, which can be 12 hours). AWS documents a procedure for revoking active permission-set sessions with a deny policy; rehearse it before you need it. For plain IAM roles, *Revoke active sessions* attaches a time-based deny for you.
2. **Then reset the password** (and re-register MFA if there's any doubt about the factor itself).
3. **Treat the device as compromised.** If the theft was an infostealer, every session and saved password on that machine is gone, not just the one you noticed. Wipe or reimage, then rotate everything that browser had access to.
4. **Check what the attacker did with the access** — mailbox rules, OAuth app grants, new MFA methods, new access keys or IAM users. Persistence is the point of a hijacked session. For the AWS side, [AWS Incident Response Scenarios](/posts/aws-incident-response-scenarios/) and [Leaked AWS Credentials](/posts/leaked-aws-credentials/) walk through the first hour.

## The earliest signal isn't in your logs

Everything above happens *after* the stolen session is used. But infostealer logs are sold — often within days of the infection — and they list exactly which of your company's services the victim was logged into. That's an earlier warning than any sign-in anomaly: the session is for sale before anyone has replayed it.

That's the gap I built a service around. [**The Hidden Port Monitoring**](/monitoring/) watches your domain across infostealer logs and breach data and tells you when a live credential or session tied to your company turns up — what leaked, which account, and what to revoke. If you'd like to know whether anything is out there today, the [free exposure check](/monitoring/free-exposure-check/) is the place to start. ([How to check if your company's credentials are already leaked](/posts/check-company-credentials-leaked/) explains the difference between old breach data and live infostealer logs.)

---

## The short version

- **Session hijacking skips MFA** because it steals what you get *after* MFA: the session cookie or token.
- **Three theft routes:** infostealer malware (the biggest), AiTM phishing proxies, and malicious browser extensions.
- **Passkeys stop AiTM, not infostealers.** Device-bound sessions (Chrome DBSC, Entra Token Protection) are the real fix, but coverage is still partial in 2026.
- **Detect "one session, two places"** — in Entra risk detections, Workspace audit logs, and CloudTrail (same `ASIA…` key from multiple IPs).
- **Respond by revoking sessions first**, then resetting the password, then treating the device as compromised.
- **Watch outside your logs** for your company's sessions showing up in infostealer data — that's the warning that comes before the replay.

---

**Related guides:**
- [How to Check If Your Company's Credentials Are Already Leaked](/posts/check-company-credentials-leaked/) — breach data vs. infostealer logs, and how to check a whole domain
- [Leaked AWS Credentials: How Access Keys End Up for Sale](/posts/leaked-aws-credentials/) — the AWS-specific version of the leak-to-incident timeline
- [Temporary Credentials in AWS](/posts/aws-temporary-credentials-security/) — why short-lived credentials limit what a stolen session can do
- [IAM Identity Center Account Access](/posts/iam-identity-center-account-access-optional/) — structuring human access to AWS through SSO
- [I Investigated a Real Phishing Attack — Here's the Full Kill Chain](/posts/real-world-phishing-incident-response/) — what an end-to-end compromise investigation looks like
- [Credential Exposure Monitoring](/monitoring/) — early warning when your team's sessions and passwords show up for sale
