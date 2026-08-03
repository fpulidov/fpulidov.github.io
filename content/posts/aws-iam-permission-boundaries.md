---
title: "AWS IAM Permission Boundaries: The Sandbox Pattern That Actually Works"
date: 2026-08-03
draft: false
description: "Permission boundaries let you scope individual IAM identities in ways SCPs can't. Here's the developer sandbox pattern I deploy — with real policy code, the ceiling-vs-grant mental model, and the traps most teams fall into."
summary: "How to use IAM permission boundaries to sandbox developers in AWS — with the sandbox pattern I deploy for clients, the mental model people get wrong, and when to reach for boundaries instead of SCPs."
slug: "aws-iam-permission-boundaries"
tags: ["AWS", "IAM", "Security", "Permission Boundaries", "Sandbox", "SCP", "Cloud Security"]
keywords: ["aws permission boundaries", "iam permission boundary", "permission boundary vs scp", "aws developer sandbox iam", "iam permission boundary example", "aws iam sandbox account", "permission boundary terraform"]
categories: ["Cloud Security"]
canonicalURL: "https://thehiddenport.dev/posts/aws-iam-permission-boundaries/"
enable_comments: true
---

Every AWS account I audit has some version of the same problem: developers need enough IAM access to be productive (create roles for their Lambdas, attach policies to their EC2 instances) — but the moment you grant `iam:*`, you've given them the ability to escalate to admin. The usual answer is "just use SCPs" — until you realize SCPs apply to the entire account, and you can't say "developers get this ceiling, but the security team gets more."

That's where **permission boundaries** come in. They're the AWS feature that lets you scope down individual IAM identities without affecting others in the same account. And they're one of the most misunderstood features in IAM — I've watched teams attach a boundary and then wonder why the user still can't do anything.

Here's how they actually work, the sandbox pattern I deploy at clients, and the mental model most teams get wrong.

---

## Why SCPs Aren't Enough

Service Control Policies are the natural first tool for "restrict what people can do in this account." They're org-wide, they're powerful, and they apply to root — so nothing bypasses them.

The problem: **SCPs apply to every principal in every account they cover.** If you attach an SCP to a sandbox OU that says "deny IAM writes," it denies IAM writes for everyone in that OU — developers, admins, security engineers, break-glass roles, everyone.

For a sandbox account where you want:
- Developers scoped to a narrow set of services
- Admins and security engineers with broader access to investigate and remediate
- CI/CD roles with their own separate permissions

...an SCP can't express that. It's account-level or nothing.

Permission boundaries let you scope **individual identities** (users or roles). Developers get one boundary, admins get another, CI/CD roles get a third. Same account, different ceilings.

---

## The Mental Model: A Ceiling, Not a Grant

The #1 mistake teams make with permission boundaries: **they think attaching a boundary gives the identity permissions.**

It doesn't. A permission boundary is a **maximum**. The identity's actual permissions are the intersection of:

1. What their identity-based policies allow (grants)
2. What the boundary allows (ceiling)

If your policy grants `s3:GetObject` but the boundary doesn't allow `s3:*`, the identity gets nothing on S3. If the boundary allows `s3:*` but the policy grants nothing, the identity still gets nothing.

**Boundary = ceiling. Policy = grant. Effective permission = the intersection.**

I've seen teams attach a `PowerUserAccess`-style boundary and then complain that a user with no attached policy can't do anything. That's the boundary working correctly. You still need to attach policies that grant what you want them to do.

---

## The Developer Sandbox Pattern

Here's the pattern I deploy when a client wants a sandbox account for developers to experiment without giving them admin.

**Requirements:**
- Developers can use RDS, EC2, ECS, CloudWatch, S3 (their working set)
- Developers can create IAM roles for their Lambdas — but only within a naming prefix, and only with a boundary attached
- Developers cannot escalate to admin, delete audit logs, or touch security tooling
- Admins in the same account keep unrestricted access

### The Developer Permission Boundary

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "AllowedServices",
      "Effect": "Allow",
      "Action": [
        "rds:*",
        "ec2:*",
        "ecs:*",
        "cloudwatch:*",
        "logs:*",
        "s3:*",
        "lambda:*",
        "iam:GetRole",
        "iam:GetRolePolicy",
        "iam:ListRoles",
        "iam:PassRole"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AllowIAMCreationWithinBoundary",
      "Effect": "Allow",
      "Action": [
        "iam:CreateRole",
        "iam:PutRolePolicy",
        "iam:AttachRolePolicy",
        "iam:DeleteRole",
        "iam:DeleteRolePolicy",
        "iam:DetachRolePolicy"
      ],
      "Resource": "arn:aws:iam::*:role/dev-*",
      "Condition": {
        "StringEquals": {
          "iam:PermissionsBoundary": "arn:aws:iam::*:policy/DeveloperBoundary"
        }
      }
    },
    {
      "Sid": "DenyDangerousActions",
      "Effect": "Deny",
      "Action": [
        "iam:*User*",
        "iam:*Group*",
        "iam:CreatePolicy*",
        "iam:DeletePolicy*",
        "iam:AttachUserPolicy",
        "iam:PutUserPolicy",
        "cloudtrail:StopLogging",
        "cloudtrail:DeleteTrail",
        "guardduty:*",
        "securityhub:*",
        "config:Delete*",
        "config:Stop*",
        "kms:ScheduleKeyDeletion",
        "organizations:*"
      ],
      "Resource": "*"
    }
  ]
}
```

Three things this policy is doing:

1. **AllowedServices** — the ceiling for normal work. Developers can do anything they want with RDS, EC2, ECS, CloudWatch, Lambda, S3.
2. **AllowIAMCreationWithinBoundary** — they can create IAM roles, but only with the `dev-` prefix AND only if the new role has the same boundary attached. This prevents them from creating a role without a boundary and then escalating through it.
3. **DenyDangerousActions** — explicit deny for anything that could compromise security tooling or escalate privileges. Explicit denies always win, so even if their attached policy grants these, they can't do them.

### Attaching to a Developer Role

```bash
# Create the boundary policy
aws iam create-policy \
  --policy-name DeveloperBoundary \
  --policy-document file://developer-boundary.json

# Create the developer role WITH the boundary
aws iam create-role \
  --role-name dev-alice \
  --assume-role-policy-document file://trust-policy.json \
  --permissions-boundary arn:aws:iam::123456789012:policy/DeveloperBoundary

# Attach the actual working policies
aws iam attach-role-policy \
  --role-name dev-alice \
  --policy-arn arn:aws:iam::aws:policy/PowerUserAccess
```

Alice now has `PowerUserAccess` granted, but constrained by the DeveloperBoundary ceiling. She can't touch GuardDuty, can't delete trails, can only create IAM roles within her prefix. Admins in the same account keep whatever their own policies grant, unaffected.

### Terraform

```hcl
resource "aws_iam_policy" "developer_boundary" {
  name        = "DeveloperBoundary"
  description = "Ceiling for developer roles in sandbox account"
  policy      = file("${path.module}/developer-boundary.json")
}

resource "aws_iam_role" "developer" {
  name                 = "dev-${var.developer_name}"
  assume_role_policy   = data.aws_iam_policy_document.developer_trust.json
  permissions_boundary = aws_iam_policy.developer_boundary.arn
}

resource "aws_iam_role_policy_attachment" "developer_power_user" {
  role       = aws_iam_role.developer.name
  policy_arn = "arn:aws:iam::aws:policy/PowerUserAccess"
}
```

---

## Common Traps

Even teams that understand the ceiling-vs-grant model still trip on these:

**Trap 1: Forgetting `iam:PermissionsBoundary` condition in the boundary itself.** If you let developers create IAM roles but don't require the new role to have a boundary attached, they can create a role with no boundary, then assume it, and escape their own restrictions. Always require the same (or a more restrictive) boundary on any IAM roles they create.

**Trap 2: Missing the `iam:PassRole` gap.** If a developer can create a Lambda function and pass any role to it, they can escalate through the Lambda's permissions. Constrain `PassRole` in the boundary to roles they own (e.g., `arn:aws:iam::*:role/dev-*`), not `*`.

**Trap 3: Assuming boundaries protect against SCPs.** They don't. SCPs are evaluated separately and can still deny actions the boundary allows. Boundaries live inside the SCP's ceiling — not above it.

**Trap 4: Attaching a boundary to a role that already had broader permissions.** The boundary silently caps the existing policies. Developers wake up unable to do things they could yesterday. Coordinate the cutover — attach the boundary at role creation, or announce the change.

**Trap 5: Forgetting boundaries apply to the identity's effective permissions, not to who can assume the role.** A boundary on `dev-alice` doesn't stop someone else from assuming that role (that's the trust policy's job). Boundaries only shape what the identity can do once assumed.

---

## When to Use Boundaries vs SCPs

They solve different problems, and most mature AWS setups use both:

| Use case | Tool |
|----------|------|
| Restrict entire account or OU (applies to root, all identities) | **SCP** |
| Restrict individual users/roles within an account | **Permission Boundary** |
| Enforce security team's non-negotiable denies across the org | **SCP** |
| Give developers self-service IAM within limits | **Permission Boundary** |
| Prevent regions, block specific services org-wide | **SCP** |
| Cap a specific role's max permissions regardless of attached policies | **Permission Boundary** |

**Rule of thumb:** if the restriction should apply to *everyone in the account*, use an SCP. If it should apply to *specific identities*, use a permission boundary.

See the [SCP best practices guide](/posts/aws-scp-best-practices/) for the SCP side of this equation.

---

## Key Takeaway

Permission boundaries are the answer to "how do I let developers do their work in AWS without giving them the ability to escalate?" — and they're the one IAM feature that lets you scope down individual identities in ways SCPs fundamentally can't.

The mental model matters more than the syntax: **boundaries are ceilings, not grants.** Attach them at role creation, require developer-created roles to inherit the boundary, and constrain `PassRole` to a naming prefix. Do that, and you get a real sandbox where developers can move fast without being able to compromise the account.

---

## Related Reading

- [AWS SCPs That Actually Work](/posts/aws-scp-best-practices/) — the account-wide equivalent, and when to reach for it
- [Enforcing Least Privilege in AWS IAM](/posts/aws-enforcing-least-privilege/) — the workflow for tightening the policies that boundaries cap
- [IAM Users Are Dead: Modern AWS Access Control for 2026](/posts/aws-iam-users-alternatives/) — pair boundaries with Identity Center for human access
- [Detect AWS IAM Privilege Escalation with CloudTrail](/posts/aws-detecting-privilege-escalation/) — detection layer for when boundaries fail or aren't in place
- [AWS Misconfigurations I Find in Every Security Audit](/posts/aws-security-misconfigurations-guide/) — missing permission boundaries on privileged roles is a recurring finding
- [AWS Security Checklist: 30-Minute Account Review](/posts/aws-security-checklist-2026/) — where boundary coverage fits in the baseline
