---
title: "Download: AWS Incident Response Toolkit"
description: "Download the free AWS Incident Response Toolkit — Terraform code, Lambda functions, IR playbook, and forensic tool matrix."
layout: "single"
robotsNoIndex: true
---

## Your download is ready

Thanks for subscribing. Here's your toolkit:

[Download AWS IR Toolkit v1.1 (.zip, ~100KB)](/downloads/aws-ir-toolkit-v1.1.zip)

### What's inside

- **IR Playbook Template (PDF)** — printable checklist aligned to ISO 27001 and AWS workflows
- **Terraform code** — deploys EventBridge → Lambda → SES notification pipeline with `terraform apply`
- **Lambda functions** — email notifications via SES + Slack alerts via webhook (both ready to deploy)
- **Notification flow architectures** — three patterns for routing Security Hub and GuardDuty findings
- **Cloud Forensics Tool Matrix (Excel)** — native and open-source tools by investigation category

### Quick start

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars  # edit with your SES email
terraform init && terraform apply
```

Questions? Reach out at javier@thehiddenport.dev.

[Back to The Hidden Port →](/posts/aws-ir-toolkit/)
