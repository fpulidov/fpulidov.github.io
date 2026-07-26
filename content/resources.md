---
title: "AWS Security Resources: Tools, Guides & Free Downloads"
layout: "single"
url: "/resources/"
summary: "Free downloads, curated tools, and starting-point guides for AWS security engineers and teams building their security posture."
description: "AWS security resources — free IR toolkit, open-source tools I actually use, and where to start if you're new to cloud security."
---

A curated list of the tools, guides, and resources I actually reach for. Free downloads from The Hidden Port, open-source tools I've tested in production, and starting-point posts for common problems.

Missing a category? [Reach out](/consulting/) and I'll add it.

---

## Free Downloads from The Hidden Port

Practical templates and code you can grab today.

### [AWS Incident Response Toolkit](/posts/aws-ir-toolkit/)
Complete IR bundle — printable playbook template (PDF), Terraform-deployed notification pipeline (EventBridge → Lambda → SES), Slack notification function, forensic tool matrix. Deploys with one `terraform apply`.

**Best for:** teams building their first IR process, or replacing an ad-hoc "we'll figure it out" approach.

---

## My Starting-Point Guides

If you're new to AWS security, these are the posts to start with.

### [AWS Security Checklist: 30-Minute Account Review](/posts/aws-security-checklist-2026/)
A self-audit you can run today. Covers the 20 controls that catch 80% of what auditors and attackers look for.

### [AWS Incident Response Guide: The Framework for Cloud-Native IR](/posts/incident-response-aws-guide/)
The framework and mindset for cloud IR — why it's different from traditional IR, how to build maturity progressively, how to actually test your process with tabletops.

### [AWS Misconfigurations I Find in Every Security Audit](/posts/aws-security-misconfigurations-guide/)
The recurring findings across environments I've reviewed. Fix these first.

### [IAM Users Are Dead: Modern AWS Access Control](/posts/aws-iam-users-alternatives/)
Why long-lived IAM users are obsolete in 2026 and how to migrate to Identity Center, OIDC, and temporary credentials.

---

## Open-Source Tools I Actually Use

Not an exhaustive list — just the ones I reach for in real engagements.

### Cloud Security Auditing

**[Prowler](https://github.com/prowler-cloud/prowler)** — AWS security posture scanner. My default for "give me a report of what's wrong in this account." Covers CIS Benchmarks, AWS Foundational Security Best Practices, and more.
*Best for:* fast, thorough account audits before any manual review.

**[Cloudsplaining](https://github.com/salesforce/cloudsplaining)** — IAM policy analyzer. Finds privilege escalation paths, wildcards, and permissions your IAM policies grant that you probably didn't mean to.
*Best for:* pre-migration audits before consolidating IAM roles.

**[Cartography](https://github.com/lyft/cartography)** — Neo4j-based asset mapping. Overkill for small environments; powerful for large multi-account orgs where you need to visualize trust relationships and data flow.

### Infrastructure as Code Security

**[Checkov](https://github.com/bridgecrewio/checkov)** — static analysis for Terraform, CloudFormation, Kubernetes. Runs pre-commit. Catches the misconfigurations before they ship.
*Best for:* CI/CD gate on IaC changes.

**[tfsec](https://github.com/aquasecurity/tfsec)** — Terraform-specific security scanner. Faster than Checkov, more focused. Good complement, not replacement.

**[KICS](https://github.com/Checkmarx/kics)** — multi-cloud IaC scanner. Broader coverage than Checkov, less opinionated. Worth evaluating if you're multi-cloud.

### Container & Runtime Security

**[Trivy](https://github.com/aquasecurity/trivy)** — scanner for container images, filesystems, git repos, and SBOMs. My default for container image CVE scanning. Fast, accurate, low-noise.

**[Falco](https://github.com/falcosecurity/falco)** — runtime threat detection for containers. Rules-based, works alongside GuardDuty Runtime Monitoring. See [EKS Security Monitoring](/posts/eks-security-monitoring/) for how to integrate it.

### Threat Detection & Response

**[Sigma](https://github.com/SigmaHQ/sigma)** — vendor-neutral detection rules. Write once, convert to whatever SIEM you use (Wazuh, Splunk, Elastic, Sentinel).

**[AVML](https://github.com/microsoft/avml)** — Linux memory acquisition tool from Microsoft. Small, fast, works over SSM. The tool referenced in the [IR toolkit](/posts/aws-ir-toolkit/) for memory capture.

---

## Reference Documentation Worth Reading

Not tools, but references that actually get used in real work.

### [AWS Security Reference Architecture (SRA)](https://github.com/aws-samples/aws-security-reference-architecture-examples)
Official AWS modular blueprints for multi-account security. Read the account structure section even if you don't adopt the full pattern — it's the best free resource on how to structure security in AWS Organizations.

### [AWS Well-Architected Security Pillar](https://docs.aws.amazon.com/wellarchitected/latest/security-pillar/welcome.html)
The canonical reference for AWS security design principles. Skim the questions checklist annually.

### [CIS AWS Foundations Benchmark](https://www.cisecurity.org/benchmark/amazon_web_services)
The baseline compliance framework. Most Security Hub controls map to this. Free PDF download after registration.

---

## Need Help Implementing These?

I take on a small number of AWS security consulting engagements each quarter — security audits, GuardDuty/Security Hub deployment, IAM hardening, IR readiness, ISO 27001 preparation.

**[Book a free 30-minute call](https://calendly.com/javier-thehiddenport/30min)** or see [how consulting engagements work](/consulting/).

---

*Have an open-source tool you think belongs here? [Email me](mailto:javier@thehiddenport.dev) — I'll evaluate it and add it if it earns its place.*
