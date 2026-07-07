---
title: "AmazonSSMManagedInstanceCore Explained: What This IAM Policy Does and When to Use It"
date: 2026-07-07
draft: false
description: "A breakdown of the AmazonSSMManagedInstanceCore IAM policy — what permissions it grants, why your EC2 instances need it for Session Manager, and how to scope it down for production."
summary: "The AmazonSSMManagedInstanceCore policy is the standard IAM policy for connecting to EC2 via Session Manager. This guide explains every permission it grants, when to use it as-is, and how to build a tighter custom policy for production."
slug: "amazonssmmanagedinstancecore-iam-policy-explained"
tags: ["AWS", "IAM", "SSM", "Session Manager", "EC2", "Security", "Least Privilege"]
categories: ["Cloud Security", "Guides"]
keywords: ["AmazonSSMManagedInstanceCore", "SSM IAM policy", "Session Manager permissions", "SSM role for EC2", "aws ssm permissions", "ec2 session manager iam"]
canonicalURL: "https://thehiddenport.dev/posts/amazonssmmanagedinstancecore-iam-policy-explained/"
enable_comments: true
---

If you've set up AWS Systems Manager Session Manager to connect to EC2 instances without SSH, you've probably attached the `AmazonSSMManagedInstanceCore` managed policy to your instance role and moved on. It works — but do you know what it actually allows?

This post breaks down the policy, explains each permission block, and shows you how to build a scoped-down alternative for production environments where least privilege matters.

> For the full Session Manager setup walkthrough (VPC endpoints, logging, disabling SSH), see [Securing EC2 Access with AWS Systems Manager Session Manager](/posts/securing-ec2-access-with-ssm/).

---

## What is AmazonSSMManagedInstanceCore?

`AmazonSSMManagedInstanceCore` is an AWS-managed IAM policy designed to be attached to EC2 instance profiles. It grants the minimum permissions an instance needs to be managed by AWS Systems Manager — including Session Manager, Run Command, Patch Manager, and Inventory.

It is **not** a user-facing policy. You attach it to the IAM role assumed by the EC2 instance itself, not to the IAM user or role of the person connecting.

---

## The Full Policy (as of 2026)

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ssm:DescribeAssociation",
        "ssm:GetDeployablePatchSnapshotForInstance",
        "ssm:GetDocument",
        "ssm:DescribeDocument",
        "ssm:GetManifest",
        "ssm:GetParameter",
        "ssm:GetParameters",
        "ssm:ListAssociations",
        "ssm:ListInstanceAssociations",
        "ssm:PutInventory",
        "ssm:PutComplianceItems",
        "ssm:PutConfigurePackageResult",
        "ssm:UpdateAssociationStatus",
        "ssm:UpdateInstanceAssociationStatus",
        "ssm:UpdateInstanceInformation"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ssmmessages:CreateControlChannel",
        "ssmmessages:CreateDataChannel",
        "ssmmessages:OpenControlChannel",
        "ssmmessages:OpenDataChannel"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ec2messages:AcknowledgeMessage",
        "ec2messages:DeleteMessage",
        "ec2messages:FailMessage",
        "ec2messages:GetEndpoint",
        "ec2messages:GetMessages",
        "ec2messages:SendReply"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "cloudwatch:PutMetricData",
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "ds:CreateComputer",
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": "ds:DescribeDirectories",
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:DescribeLogGroups",
        "logs:DescribeLogStreams",
        "logs:PutLogEvents"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetBucketLocation",
        "s3:PutObject",
        "s3:GetObject",
        "s3:GetEncryptionConfiguration",
        "s3:AbortMultipartUpload",
        "s3:ListMultipartUploadParts",
        "s3:ListBucket",
        "s3:ListBucketMultipartUploads"
      ],
      "Resource": "*"
    }
  ]
}
```

That's a lot of `"Resource": "*"`. Let's break it down.

---

## Permission Blocks Explained

### 1. Core SSM Agent Communication (`ssm:*`)

```
ssm:UpdateInstanceInformation
ssm:GetDocument
ssm:ListAssociations
ssm:PutInventory
...
```

These let the SSM Agent on your instance register itself with Systems Manager, pull documents (commands/scripts) to execute, report inventory data, and update its status. Without these, the instance won't appear in the Systems Manager console at all.

### 2. Session Manager Channels (`ssmmessages:*`)

```
ssmmessages:CreateControlChannel
ssmmessages:CreateDataChannel
ssmmessages:OpenControlChannel
ssmmessages:OpenDataChannel
```

This is what makes Session Manager work. The agent opens a WebSocket-based control channel to the `ssmmessages` endpoint — no inbound ports needed. If you only care about Session Manager and nothing else, these four actions (plus `ssm:UpdateInstanceInformation`) are the absolute minimum.

### 3. Run Command Messaging (`ec2messages:*`)

```
ec2messages:GetMessages
ec2messages:SendReply
ec2messages:AcknowledgeMessage
...
```

Used by the older Run Command delivery mechanism. If you exclusively use Session Manager and don't use Run Command or State Manager associations, you can technically drop these — but most environments use both.

### 4. Logging and Monitoring (`logs:*`, `cloudwatch:*`, `s3:*`)

The policy grants broad CloudWatch Logs, CloudWatch Metrics, and S3 access so the agent can ship session logs, output, and metrics. This is where the `"Resource": "*"` gets concerning — the instance can write to **any** log group and **any** S3 bucket in the account.

### 5. Directory Service (`ds:*`)

```
ds:CreateComputer
ds:DescribeDirectories
```

Only relevant if you're joining instances to an AWS Managed Microsoft AD domain. Most Linux-only environments don't need this at all.

---

## When to Use It As-Is

The managed policy is fine for:

- **Dev/test environments** where speed matters more than tight scoping
- **Initial setup and validation** before you know which SSM features you'll actually use
- **Environments with a single AWS account** where the blast radius of `"Resource": "*"` is contained

It's an AWS-managed policy, so AWS keeps it updated when new SSM features require additional permissions. You don't have to maintain it.

---

## When to Scope It Down

In production, `"Resource": "*"` on S3 and CloudWatch Logs means a compromised instance could write to any bucket or log group in the account. You should create a custom policy when:

- You run **multi-tenant workloads** or share an AWS account across teams
- Your compliance framework requires **least-privilege IAM** (SOC 2, CIS, PCI-DSS)
- You want to **limit blast radius** if an instance is compromised

### Custom Policy: Session Manager Only

If all you need is Session Manager access with logging to a specific S3 bucket and log group:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "SSMAgentCore",
      "Effect": "Allow",
      "Action": [
        "ssm:UpdateInstanceInformation",
        "ssm:GetDocument",
        "ssm:DescribeDocument",
        "ssm:GetParameter",
        "ssm:GetParameters"
      ],
      "Resource": "*"
    },
    {
      "Sid": "SessionManagerChannels",
      "Effect": "Allow",
      "Action": [
        "ssmmessages:CreateControlChannel",
        "ssmmessages:CreateDataChannel",
        "ssmmessages:OpenControlChannel",
        "ssmmessages:OpenDataChannel"
      ],
      "Resource": "*"
    },
    {
      "Sid": "SessionLogsToS3",
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetEncryptionConfiguration"
      ],
      "Resource": [
        "arn:aws:s3:::YOUR-SESSION-LOGS-BUCKET",
        "arn:aws:s3:::YOUR-SESSION-LOGS-BUCKET/*"
      ]
    },
    {
      "Sid": "SessionLogsToCloudWatch",
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogStream",
        "logs:DescribeLogGroups",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:log-group:/aws/ssm/session-logs:*"
    }
  ]
}
```

This drops Directory Service, Run Command (`ec2messages`), Inventory, Patch Manager, and the wide S3/CloudWatch scope. Replace `YOUR-SESSION-LOGS-BUCKET` and the log group ARN with your actual resources.

### Terraform Example

```hcl
resource "aws_iam_role" "ssm_session_only" {
  name = "ec2-ssm-session-only"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy" "ssm_session_only" {
  name = "ssm-session-manager-scoped"
  role = aws_iam_role.ssm_session_only.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "SSMAgentCore"
        Effect = "Allow"
        Action = [
          "ssm:UpdateInstanceInformation",
          "ssm:GetDocument",
          "ssm:DescribeDocument",
          "ssm:GetParameter",
          "ssm:GetParameters",
        ]
        Resource = "*"
      },
      {
        Sid    = "SessionManagerChannels"
        Effect = "Allow"
        Action = [
          "ssmmessages:CreateControlChannel",
          "ssmmessages:CreateDataChannel",
          "ssmmessages:OpenControlChannel",
          "ssmmessages:OpenDataChannel",
        ]
        Resource = "*"
      },
      {
        Sid    = "SessionLogsS3"
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetEncryptionConfiguration",
        ]
        Resource = [
          aws_s3_bucket.session_logs.arn,
          "${aws_s3_bucket.session_logs.arn}/*",
        ]
      },
      {
        Sid    = "SessionLogsCW"
        Effect = "Allow"
        Action = [
          "logs:CreateLogStream",
          "logs:DescribeLogGroups",
          "logs:PutLogEvents",
        ]
        Resource = "${aws_cloudwatch_log_group.ssm_sessions.arn}:*"
      },
    ]
  })
}

resource "aws_iam_instance_profile" "ssm_session_only" {
  name = "ec2-ssm-session-only"
  role = aws_iam_role.ssm_session_only.name
}
```

---

## VPC Endpoints: Required for Private Subnets

If your instances are in private subnets without NAT gateway access, the SSM Agent can't reach the public SSM endpoints. You need three VPC endpoints:

| Endpoint | Service Name | Used For |
|----------|-------------|----------|
| SSM | `com.amazonaws.REGION.ssm` | Core agent communication |
| SSM Messages | `com.amazonaws.REGION.ssmmessages` | Session Manager channels |
| EC2 Messages | `com.amazonaws.REGION.ec2messages` | Run Command delivery |

All three must be **Interface** type endpoints (not Gateway). Their security groups must allow inbound HTTPS (443) from your instance subnets.

> You only need the `ec2messages` endpoint if you use Run Command. Session Manager only requires `ssm` + `ssmmessages`.

---

## Common Mistakes

**Attaching the policy to an IAM user instead of an instance role.** `AmazonSSMManagedInstanceCore` is designed for EC2 instance profiles. The person connecting needs different permissions (`ssm:StartSession`).

**Forgetting the instance profile.** Creating the IAM role and policy isn't enough — you must also create an instance profile and attach it to the EC2 instance. Terraform's `aws_iam_instance_profile` handles this; in the console, it's done when you attach the role to the instance.

**Missing VPC endpoints in private subnets.** The SSM Agent fails silently when it can't reach endpoints. The instance just never appears in Session Manager — no error in the console. Check the agent log at `/var/log/amazon/ssm/amazon-ssm-agent.log`.

---

## Related Posts

- [Securing EC2 Access with AWS Systems Manager Session Manager](/posts/securing-ec2-access-with-ssm/) — full setup guide covering VPC endpoints, logging, and disabling SSH
- [Enforcing Least Privilege in AWS IAM](/posts/enforcing-least-privilege-iam-access-analyzer/) — using Access Analyzer to audit and tighten IAM policies
- [Hardening EC2 Instances for AWS Security](/posts/aws-ec2-hardening/) — OS-level hardening, encryption, and compliance checks

---
