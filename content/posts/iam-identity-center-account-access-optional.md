---
title: "AWS IAM Identity Center: Account Access Is Now Optional — And Why That Matters"
date: 2026-08-19
draft: false
description: "AWS Identity Center can now be provisioned without pushing the service-linked role into every member account. A real blast radius reduction for orgs that use Identity Center only for SaaS SSO. Here's when to use the new option and when to skip it."
summary: "AWS IAM Identity Center now supports new organization instances without account access management enabled — no more service-linked role in every member account. When to use it, when to skip it, and the migration considerations for existing instances."
slug: "iam-identity-center-account-access-optional"
tags: ["AWS", "IAM", "Identity Center", "SSO", "Security", "Organizations"]
keywords: ["aws iam identity center account access", "identity center service linked role", "aws sso account access optional", "iam identity center blast radius", "identity center for saas only", "aws identity center setup"]
categories: ["Cloud Security"]
canonicalURL: "https://thehiddenport.dev/posts/iam-identity-center-account-access-optional/"
enable_comments: true
---

AWS quietly shipped a change to IAM Identity Center this month that reduces its default blast radius meaningfully: new organization instances can now be created **without** the account access management feature enabled. That means no `AWSServiceRoleForSSO` service-linked role auto-provisioned into every member account of your organization.

For most teams this will fly under the radar, because most teams use Identity Center specifically to manage AWS console access — the exact thing this option turns off. But for organizations that use Identity Center purely for SaaS SSO (Slack, GitHub, Salesforce) and manage AWS access some other way, this is a genuine security improvement that's been asked for for years.

Here's what the change actually does, when it matters, and the migration considerations if you're on an existing instance.

---

## What Identity Center Was Doing Before

When you enable IAM Identity Center at the AWS Organizations level, two capabilities activate together:

1. **Application access** — Identity Center as your IdP for SAML/OIDC apps (Slack, GitHub, Salesforce, any SAML-supporting SaaS)
2. **AWS account access** — Identity Center provisions users into member accounts via permission sets, which become IAM roles in each account

The second capability requires Identity Center to have write access into every member account. AWS implements that via a service-linked role — `AWSServiceRoleForSSO` — that gets auto-provisioned into every member account when you enable the service. That role has the IAM permissions needed to create, update, and delete the roles that back your permission sets.

That's convenient. It's also a very broad piece of trust to grant automatically. Every new account added to your organization gets this role deployed silently. If Identity Center itself is compromised, that trust becomes a lateral movement path across your entire organization.

The old design essentially forced you to accept that trade-off. You couldn't use Identity Center for SaaS SSO without also giving it the IAM footprint across every account.

---

## What Changed

New organization instances can now opt out of the account access management feature entirely. The setup flow gives you a choice: enable both, or enable only application access.

When you choose application-only:

- **No `AWSServiceRoleForSSO`** gets provisioned in member accounts
- **No permission sets** — the feature isn't available in the console
- **No account assignments** — you can't grant users AWS console/CLI access through Identity Center
- **SAML/OIDC application assignments still work** — users can be assigned to Slack, GitHub, etc. normally

The IAM footprint of Identity Center collapses from "every account in your org" to "just the delegated administrator account (usually your management account or a dedicated IdP account)."

**Important constraint:** this is currently only available for **new** organization instances. If your Identity Center is already enabled with account access, you can't just disable it and keep the same instance. More on migration in a moment.

---

## When This New Option Makes Sense

Three concrete scenarios where turning off account access is the right call:

### 1. Identity Center only for SaaS SSO

Your organization uses Identity Center to give employees SSO to Slack, GitHub, Notion, Salesforce, etc. AWS console access is managed through a completely different system — Okta, Azure AD, or (God forbid) IAM users.

Turning off account access removes a capability you were never going to use anyway. Pure blast radius reduction with zero functional loss.

### 2. AWS access managed by a third-party IdP

You're using Okta or Azure AD as the authoritative identity provider for AWS console access via SAML federation directly to each account (or via AWS Organizations SCIM). Identity Center is running just for the SaaS side.

Same result as above — you never touched Identity Center's account access capability, so removing it costs nothing.

### 3. Sensitive AWS environments where Identity Center compromise is a nightmare scenario

You have Identity Center enabled but only use it for a small subset of accounts. The service-linked role still gets deployed into every member account of your organization, including the sensitive ones (production, security tooling accounts, audit accounts). If you can accept moving AWS access to a different path for those accounts, opting out is a meaningful hardening measure.

---

## When You Should NOT Use This Option

If your organization uses Identity Center for AWS console access — which is AWS's recommended pattern — you cannot use the new option. You'd lose the entire reason you're running Identity Center.

Signs the new option is wrong for you:

- You have permission sets defined and assigned to accounts today
- Your engineers log into AWS via `<orgname>.awsapps.com/start`
- You use permission set boundaries or session duration configuration
- You've integrated Identity Center with third-party IdPs (Okta, Azure AD) specifically to federate AWS access

For all of the above, the SLR-in-every-account trade-off is what makes Identity Center work. Removing it removes the feature you're using.

---

## Migration Considerations for Existing Instances

AWS scoped this to new instances only, which is annoying but understandable — retroactively yanking the SLR from every member account would break existing permission sets everywhere.

If you're on an existing instance and want to move to the new "app-only" model, your options are:

**Option A: Create a second Identity Center instance for apps only.** Since AWS now supports multiple Identity Center instances per organization (introduced separately), you can leave your existing AWS-access-enabled instance running and create a new app-only instance for SaaS SSO. This gets messy for users (two IdPs, two portals) unless you're careful about which apps go where.

**Option B: Migrate off Identity Center entirely, then re-enable fresh.** Move AWS account access to another mechanism (typically SAML federation from your existing IdP directly to each account), delete the Identity Center configuration, wait for propagation, and re-enable Identity Center fresh with app-only mode. Highly disruptive; only worth it if the security benefit is critical.

**Option C: Wait.** AWS has been iterating on Identity Center rapidly. It's plausible they'll add a way to disable account access on existing instances in a future update. If your current setup is working, don't rush.

For most existing customers, Option C is the pragmatic call unless you have a specific compliance or threat model driving the migration.

---

## The Blast Radius Argument, Concretely

The blast radius reduction is real, but it's easy to overstate. Here's what actually changes:

**Before (SLR in every account):**
- Identity Center compromise → attacker with control of Identity Center can modify the SLR trust or use SLR credentials
- SLR has IAM permissions in every member account, scoped to Identity Center's own roles (`aws-reserved/sso.amazonaws.com/`)
- Attacker can create new permission sets, assign them broadly, and pivot into any account

**After (no SLR in member accounts):**
- Identity Center compromise → attacker controls the SAML IdP for SaaS apps
- No native path into member accounts via Identity Center
- Blast radius contained to whatever SaaS apps Identity Center federates to

The reduction is meaningful but doesn't eliminate risk — a compromised IdP for your SaaS apps is still very bad. It just stops being an AWS-org-wide event.

For orgs handling sensitive workloads (PCI-DSS, healthcare, financial services) where the AWS environment is the crown jewel, this is a genuinely useful hardening step. For most SMB and mid-size AWS setups where Identity Center is the primary AWS access mechanism, it doesn't apply.

---

## What to Check in Your Environment

Whether you're setting up a new Identity Center instance or reviewing an existing one:

```bash
# List Identity Center instances in your org
aws sso-admin list-instances

# For an existing instance, check what permission sets are defined
aws sso-admin list-permission-sets \
  --instance-arn arn:aws:sso:::instance/ssoins-xxxxxxxxxxxxxx

# Check what accounts have Identity Center assignments
aws sso-admin list-permission-sets-provisioned-to-account \
  --instance-arn arn:aws:sso:::instance/ssoins-xxxxxxxxxxxxxx \
  --account-id <account-id>

# Check whether the SLR is present in a specific member account
aws iam get-role --role-name AWSServiceRoleForSSO
```

If `list-permission-sets` returns an empty result and no accounts have assignments, you're already effectively running Identity Center in app-only mode from an operational standpoint — the SLR is deployed but unused. A future instance you create fresh could formalize that with the new option.

---

## The Bigger Pattern

This change fits a broader AWS pattern from the last year: giving customers more granular control over the trust footprint that AWS services request by default. GuardDuty runtime monitoring made agent deployment more targeted. Security Hub added the option to consolidate findings without cross-account role sprawl. And now Identity Center lets you skip the account access footprint entirely.

The theme: AWS is finally acknowledging that "enable everywhere by default" isn't always the right default. For security-conscious customers, more of these options are going to keep landing.

---

## Key Takeaway

If you use Identity Center primarily for AWS console access — which is most AWS customers — this announcement doesn't change your life. Keep doing what you're doing.

If you use Identity Center for SaaS SSO and manage AWS access some other way, the new app-only option is a genuinely useful hardening step for any new org instances you create. Existing instances stay as they are for now, but you can create a fresh instance with the new option if your setup benefits from it.

For everyone else, this is worth understanding because clients will start asking about it once security-focused folks in their orgs read the announcement. Being the person with a ready answer — "yes, here's when it applies to us, here's when it doesn't" — is a small but real trust signal.

---

## Related Reading

- [IAM Users Are Dead: Modern AWS Access Control for 2026](/posts/aws-iam-users-alternatives/) — the identity approach Identity Center replaces
- [AWS IAM Permission Boundaries: The Sandbox Pattern That Actually Works](/posts/aws-iam-permission-boundaries/) — per-identity scoping, complementary to Identity Center
- [Enforcing Least Privilege in AWS IAM](/posts/aws-enforcing-least-privilege/) — the workflow around IAM policies Identity Center deploys
- [AWS SCPs That Actually Work](/posts/aws-scp-best-practices/) — org-level guardrails that constrain what Identity Center's SLR can do
- [AWS Security Checklist: 30-Minute Account Review](/posts/aws-security-checklist-2026/) — where Identity Center's footprint shows up in a baseline audit
- [ISO 27001 for AWS: What Auditors Actually Ask For](/posts/iso-27001-aws-audit-prep/) — access control evidence auditors expect
