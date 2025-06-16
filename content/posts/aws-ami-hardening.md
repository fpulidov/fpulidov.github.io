---
title: "Building a Hardened Amazon Linux 2 AMI for Secure EC2 Deployments"
description: "Learn how to create a hardened, compliant Amazon Linux 2 AMI using EC2 Image Builder with CIS benchmarks, security tools, and automation for production-ready AWS environments."
summary: "Step-by-step guide to build a hardened Amazon Linux 2 AMI with EC2 Image Builder including CIS benchmarks, IMDSv2 enforcement, auditd, and logging configuration."
date: 2025-06-09
tags: ["AWS", "EC2", "AMI", "Hardening", "Security", "Image Builder"]
canonicalURL: "https://thehiddenport.dev/posts/building-hardened-amazon-linux-2-ami-secure-ec2"
---

# Building a Hardened Amazon Linux 2 AMI for Secure EC2 Deployments

In cloud environments, spinning up secure, hardened EC2 instances rapidly and consistently is a critical security and operational requirement. Manually configuring instances after launch is error-prone and inefficient. The solution? Automate the creation of hardened, compliant AMIs using AWS EC2 Image Builder.

This article walks you through building a hardened Amazon Linux 2 AMI using EC2 Image Builder, integrating CIS benchmark checks, IMDSv2 enforcement, auditd, CloudWatch logging, and common security best practices.

---

## Why Build a Hardened AMI?

While Amazon Linux 2 is secure by default, production workloads demand additional layers of security:

- Consistent baseline configuration across instances
- Disabling unnecessary services and users
- Enforcing instance metadata protection (IMDSv2 only)
- Pre-installed monitoring and audit agents
- Automatic patching and versioning of AMIs

Building a custom hardened AMI ensures every EC2 instance launched from it meets your organization’s security standards from day one.

---

## Step 1: Overview of EC2 Image Builder

EC2 Image Builder is an AWS-managed service that automates creating, testing, and distributing AMIs. It uses pipeline workflows where you define:

- **Base image** (Amazon Linux 2 official image)
- **Components** (scripts and configuration steps)
- **Tests** (CIS benchmark validation)
- **Distribution settings** (account and region targets)

---

## Step 2: Define Your Base Image and Components

Start with the official Amazon Linux 2 AMI as the base. Add components such as:

- **Patch updates**: Apply all current OS patches automatically.
- **CIS Benchmark hardening**: Disable unnecessary services, set secure kernel parameters, lock down SSH configuration.
- **IMDSv2 enforcement**: Disable IMDSv1 by configuring the `aws-ec2-metadata-service` to require tokens.
- **Auditd setup**: Enable system auditing and forward logs to CloudWatch Logs.
- **Install monitoring agents**: CloudWatch agent, osquery for endpoint visibility.

You can create custom components in EC2 Image Builder or use community-supported ones, ensuring scripts are idempotent and secure.

---

## Step 3: Create the Image Pipeline

Configure the image pipeline with these key settings:

- **Schedule**: Weekly or monthly builds to include the latest patches.
- **Tests**: Run automated CIS Benchmark compliance tests after build.
- **Distribution**: Share the hardened AMI across your AWS accounts or regions.
- **Tags and Naming**: Use semantic versioning and tags for easy identification.

Example AWS CLI snippet to create a simple [pipeline]('https://docs.aws.amazon.com/imagebuilder/latest/userguide/cli-create-image-pipeline.html'):

```bash
aws imagebuilder create-image-pipeline --cli-input-json file://pipeline-config.json
```

---

## Step 4: Validate Your Hardened AMI

After each build, run tests to verify:

- CIS benchmark pass rate (using open-source tools or AWS Inspector)
- IMDSv1 is disabled, only IMDSv2 accessible
- Audit logs forwarding to CloudWatch
- SSH key restrictions and root login disabled

Automate these checks to fail pipelines if hardening criteria aren’t met.

---

## Step 5: Launch and Use Your Hardened AMI

Use your hardened AMI for:

- Production EC2 instances
- Auto Scaling groups
- ECS container instances (if applicable)

Maintain version control on AMIs and rotate them regularly for patch compliance.

---

## Best Practices and Tips

- Combine EC2 Image Builder with **AWS Systems Manager Automation** to patch running instances.
- Store your pipeline definitions in version control (e.g., Git) for auditability.
- Use **IMDSv2 exclusively** to mitigate SSRF risks.
- Monitor your hardened AMIs with CloudWatch and AWS Config rules.
- Document your build process and security rationale.

---

## Related Reading

- [Hardening EC2 Instances for AWS Security](../aws-ec2-hardening/)
- [Securing EC2 Access with AWS Systems Manager (No SSH)](../aws-securing-ec2-access-with-ssm/)
- [AWS Incident Response Toolkit](../aws-ir-toolkit/)
- [Enforcing Least Privilege in AWS IAM](../aws-enforcing-least-privilege/)

---

## Final Thoughts

Building and maintaining hardened AMIs is a cornerstone of secure AWS infrastructure. Automating this process with EC2 Image Builder not only improves security posture but also accelerates deployment workflows. Start small, automate everything, and iterate for continuous improvement.