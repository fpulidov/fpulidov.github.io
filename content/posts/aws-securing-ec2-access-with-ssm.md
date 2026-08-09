---
title: "AWS Session Manager Setup: Replace SSH with Zero Inbound Ports"
date: 2025-06-03
description: "Step-by-step SSM Session Manager setup — IAM role, AmazonSSMManagedInstanceCore policy, instance profile, and session logging. No SSH keys, no bastion hosts, no port 22."
tags: ["AWS", "EC2", "Security", "Session Manager", "SSM", "IAM", "Cloud Security"]
keywords: ["amazonssmmanagedinstancecore", "aws session manager setup", "ssm ec2 access", "aws ssm iam role", "session manager instance profile", "replace ssh with session manager"]
categories: ["Cloud Security"]
canonicalURL: "https://thehiddenport.dev/posts/aws-securing-ec2-access-with-ssm/"
summary: "Step-by-step SSM Session Manager setup — IAM role, instance profile, session logging, and removing SSH entirely. No keys, no bastions, no port 22."
lastmod: 2026-07-30
enable_comments: true
---

Every AWS account I audit still has port 22 open on at least a few instances. SSH keys scattered across laptops, a bastion host nobody remembers deploying, and zero logging of who connected when. AWS Systems Manager Session Manager solves all of this — shell access through IAM with full audit trails, no inbound ports, and no key management.

This guide walks through the setup end to end: IAM role, instance profile, agent verification, session logging, and finally killing SSH for good.

---

## Prerequisites

Before starting, verify three things:

**SSM Agent installed.** Amazon Linux 2, Amazon Linux 2023, and Ubuntu 16.04+ come with it pre-installed. For other operating systems, see the [SSM Agent installation guide](https://docs.aws.amazon.com/systems-manager/latest/userguide/ssm-agent.html).

**IAM role with SSM permissions.** Instances need the `AmazonSSMManagedInstanceCore` managed policy. For a breakdown of what this policy allows and how to scope it down, see the [AmazonSSMManagedInstanceCore deep dive](/posts/amazonssmmanagedinstancecore-iam-policy-explained/).

**Network path to SSM endpoints.** Instances need outbound HTTPS (443) to Systems Manager endpoints — either through a NAT gateway or [VPC endpoints for Systems Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/setup-create-vpc.html). No inbound ports required.

---

## Step 1: Create the IAM Role

Create a role that EC2 can assume with the SSM managed policy attached:

```bash
# Create the trust policy
cat > ssm-trust-policy.json << 'POLICY'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "ec2.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
POLICY

# Create the role and attach the SSM policy
aws iam create-role \
  --role-name EC2-SSM-Role \
  --assume-role-policy-document file://ssm-trust-policy.json

aws iam attach-role-policy \
  --role-name EC2-SSM-Role \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore

# Create an instance profile and add the role
aws iam create-instance-profile --instance-profile-name EC2-SSM-Profile
aws iam add-role-to-instance-profile \
  --instance-profile-name EC2-SSM-Profile \
  --role-name EC2-SSM-Role
```

Or in the console: IAM > Roles > Create role > AWS service > EC2 > attach `AmazonSSMManagedInstanceCore`.

---

## Step 2: Attach the Role to EC2 Instances

For existing instances:

```bash
aws ec2 associate-iam-instance-profile \
  --instance-id i-0123456789abcdef0 \
  --iam-instance-profile Name=EC2-SSM-Profile
```

For new instances, specify the instance profile at launch. The instance will register with Systems Manager automatically once the agent starts and the IAM role is in place.

---

## Step 3: Verify the SSM Agent

SSH in one last time (or use EC2 Instance Connect) to confirm the agent is running:

```bash
sudo systemctl status amazon-ssm-agent
```

If it's not running:

```bash
sudo systemctl enable amazon-ssm-agent
sudo systemctl start amazon-ssm-agent
```

You can also check from outside the instance — if it shows up in Fleet Manager, the agent is working:

```bash
aws ssm describe-instance-information \
  --query 'InstanceInformationList[].{ID:InstanceId,Status:PingStatus,Agent:AgentVersion}' \
  --output table
```

Instances with `PingStatus: Online` are ready for Session Manager.

---

## Step 4: Connect via Session Manager

### CLI

Install the [Session Manager plugin](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html), then:

```bash
aws ssm start-session --target i-0123456789abcdef0
```

### Console

Systems Manager > Session Manager > Start session > select the instance.

### Port Forwarding

Session Manager also handles port forwarding — useful for database access or internal web interfaces without exposing ports:

```bash
aws ssm start-session \
  --target i-0123456789abcdef0 \
  --document-name AWS-StartPortForwardingSession \
  --parameters '{"portNumber":["5432"],"localPortNumber":["15432"]}'
```

This forwards the instance's PostgreSQL port (5432) to localhost:15432 through the SSM tunnel. No security group changes needed.

---

## Step 5: Enable Session Logging

Without logging, Session Manager is just SSH with extra steps. The real value is the audit trail.

In Systems Manager > Session Manager > Preferences > Edit:

- **S3 logging**: send session output to a bucket for long-term retention
- **CloudWatch Logs**: send session output for real-time search and alerting
- **KMS encryption**: encrypt session data in transit and at rest

```bash
# Verify logging is configured
aws ssm describe-document --name SSM-SessionManagerRunShell \
  --query 'Document.{Name:Name,Status:Status}' --output table
```

With CloudWatch logging enabled, you can search session transcripts — every command typed during a session is recorded.

---

## Step 6: Kill SSH

Once Session Manager is verified and logging is in place, remove SSH access entirely:

```bash
# Find security groups with port 22 open
aws ec2 describe-security-groups \
  --filters "Name=ip-permission.from-port,Values=22" \
  --query 'SecurityGroups[].{ID:GroupId,Name:GroupName}' --output table

# Remove the SSH rule (replace sg-xxx and the CIDR with your values)
aws ec2 revoke-security-group-ingress \
  --group-id sg-xxx \
  --protocol tcp --port 22 --cidr 0.0.0.0/0
```

Also:
- **Stop assigning key pairs** to new instances — they're unnecessary with Session Manager
- **Decommission bastion hosts** — they're attack surface you no longer need
- **Update runbooks** so the team knows to use `aws ssm start-session` instead of `ssh`

---

## Troubleshooting

**Instance not showing in Session Manager:**
1. Check IAM — the instance profile must have `AmazonSSMManagedInstanceCore` attached
2. Check the agent — `systemctl status amazon-ssm-agent` should show `active (running)`
3. Check network — the instance needs outbound 443 to `ssm.<region>.amazonaws.com`, `ssmmessages.<region>.amazonaws.com`, and `ec2messages.<region>.amazonaws.com`. If in a private subnet without NAT, you need VPC endpoints for all three services

**Session starts but immediately closes:**
- Usually an agent version issue. Update with `sudo yum install -y amazon-ssm-agent` (Amazon Linux) or `sudo snap refresh amazon-ssm-agent` (Ubuntu)

**"TargetNotConnected" error:**
- The instance's `PingStatus` in `describe-instance-information` will show `ConnectionLost`. Most common cause is a network change (new NACL rule, removed NAT gateway, or VPC endpoint misconfiguration)

For the full troubleshooting reference, see [AWS Systems Manager Troubleshooting](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-troubleshooting.html).

---

## Related Reading

- [AmazonSSMManagedInstanceCore Explained](/posts/amazonssmmanagedinstancecore-iam-policy-explained/) — what the SSM policy actually grants and how to scope it down
- [EC2 Hardening Guide: Secure Instances Step by Step](/posts/aws-ec2-hardening/) — the full hardening workflow that Session Manager is part of
- [Meeting CIS Benchmarks for EC2](/posts/ec2-cis-benchmarks-guide/) — CIS controls that include disabling SSH
- [AWS Misconfigurations I Find in Every Security Audit](/posts/aws-security-misconfigurations-guide/) — open SSH is one of the top findings
- [AWS Security Checklist: 30-Minute Account Review](/posts/aws-security-checklist-2026/) — quick baseline check including network hardening
- [Securing Temporary AWS Credentials](/posts/aws-temporary-credentials-security/) — the IAM foundation Session Manager builds on
