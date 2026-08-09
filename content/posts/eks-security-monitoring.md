---
title: "EKS Security Monitoring: Audit Logs, Falco Runtime Detection & GuardDuty"
date: 2025-09-17
draft: false
description: "Most EKS clusters ship with control plane logging off and no runtime detection. Here's the step-by-step: audit logs, Falco, GuardDuty for containers, and the gaps teams miss."
slug: "eks-security-monitoring"
tags: ["AWS", "EKS", "Kubernetes", "Security", "Monitoring", "Falco", "CloudWatch"]
categories: ["Cloud Security", "Guides"]
keywords: ["eks security monitoring", "eks audit logs", "eks container security", "aws eks monitoring", "falco eks", "eks runtime monitoring", "eks control plane logs", "eks threat detection"]
enable_comments: true
summary: "Practical EKS security checklist — control plane audit logs, Falco runtime detection, GuardDuty for containers, and the monitoring gaps most teams miss."
canonicalURL: "https://thehiddenport.dev/posts/eks-security-monitoring/"
lastmod: 2026-07-30
---

Monitoring Kubernetes on AWS adds layers that traditional EC2 monitoring doesn't cover — pods are ephemeral, containers restart constantly, and the control plane is managed by AWS but the security visibility is your problem. Most EKS clusters I see in audits have control plane logging disabled and zero runtime detection, which means an attacker who gets into a pod can move laterally without generating a single alert.

This guide covers what to monitor, how to configure it, and where the gaps are that teams consistently miss.

> For hardening your cluster before you monitor it — RBAC, network policies, pod security, image scanning — see [EKS Security Best Practices: Hardening Your Cluster](/posts/eks-security-best-practices/).

---

## What Makes EKS Monitoring Different

EKS monitoring is harder than EC2 monitoring for four specific reasons:

- **Ephemeral infrastructure**: Pods start and die constantly. You can't SSH in and check logs after the fact — if you weren't collecting when it happened, the evidence is gone.
- **Multi-layered architecture**: Control plane, worker nodes, container runtime, pod networking, and application logs are all separate streams that need separate collection.
- **Shared responsibility gaps**: AWS manages the control plane, but worker node security, pod configuration, and runtime detection are entirely on you.
- **Volume**: Kubelet, CNI plugins, application pods, kube-proxy, and audit events all generate logs. Without filtering, you're paying for noise.

---

## Types of EKS Monitoring

| Type | What It Covers | Why It Matters |
|------|----------------|----------------|
| **Control Plane** | API server logs, audit events, scheduler, authenticator | Detect privilege abuse, RBAC changes, unauthorized API calls |
| **Application / Pod** | Container stdout/stderr, resource usage, restarts | Catch misbehaving containers and application failures |
| **Runtime Security** | `kubectl exec`, privilege escalation, filesystem anomalies | Detect attacks, reverse shells, container escapes |
| **Network** | Pod-to-pod traffic, ingress/egress, DNS queries | Spot exfiltration, lateral movement, misconfigured network policies |

---

## AWS-Native Monitoring Tools

### Control Plane Logging

This is the single most important step and the one most often skipped. Enable it via the console or CLI:

```bash
aws eks update-cluster-config \
  --name my-cluster \
  --logging '{"clusterLogging":[{"types":["api","audit","authenticator","controllerManager","scheduler"],"enabled":true}]}'
```

At minimum, enable **api** and **audit** logs. The audit log captures every Kubernetes API request — who called what, when, and whether it was allowed. This is your CloudTrail equivalent for Kubernetes.

### CloudWatch Container Insights

Collects cluster, node, and pod-level metrics with the CloudWatch agent:

```bash
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name amazon-cloudwatch-observability
```

### Fluent Bit for Log Collection

Deploy as a DaemonSet to collect pod logs (stdout/stderr), kubelet logs, and system logs from every node:

```bash
kubectl apply -f https://raw.githubusercontent.com/aws-samples/amazon-cloudwatch-container-insights/latest/k8s-deployment-manifest-templates/deployment-mode/daemonSet/container-insights-monitoring/fluent-bit/fluent-bit.yaml
```

Configure filters to drop high-volume, low-value logs (verbose debug output, health check noise) early in the pipeline to control CloudWatch costs.

### Other AWS Tools

- **Amazon Managed Prometheus + Grafana** — PromQL queries and dashboards without managing the infrastructure
- **AWS X-Ray / OpenTelemetry** — distributed tracing for microservices running in pods
- **Security Hub** — centralize findings from GuardDuty, Config, and custom detections

---

## Runtime Security & Threat Detection

### GuardDuty EKS Protection

GuardDuty's EKS audit log monitoring detects suspicious Kubernetes API activity — anonymous API calls, known attack tools, pods launched with privileged containers. Enable it alongside [GuardDuty Runtime Monitoring](/posts/aws-guardduty-runtime-monitoring/) for process-level visibility inside containers.

```bash
# Check if EKS protection is enabled
aws guardduty list-detectors --query 'DetectorIds[0]' --output text | \
  xargs -I {} aws guardduty get-detector --detector-id {} \
  --query 'Features[?Name==`EKS_AUDIT_LOGS`].Status'
```

### Falco for Runtime Detection

Falco monitors system calls inside containers and detects anomalies that GuardDuty doesn't cover — shell spawns in non-interactive containers, sensitive file reads, unexpected outbound connections.

Deploy via Helm:

```bash
helm repo add falcosecurity https://falcosecurity.github.io/charts
helm install falco falcosecurity/falco \
  --namespace falco --create-namespace \
  --set falcosidekick.enabled=true \
  --set falcosidekick.config.aws.cloudwatchlogs.loggroup="/eks/falco-alerts"
```

Example custom rule — detect a shell spawned inside a container that shouldn't have interactive access:

```yaml
- rule: Shell Spawned in Non-Interactive Container
  desc: Detect shell processes in containers not marked for interactive use
  condition: >
    spawned_process and container and
    proc.name in (bash, sh, zsh, dash) and
    not container.image.repository in (allowed-debug-image)
  output: >
    Shell spawned in container
    (user=%user.name command=%proc.cmdline container=%container.name
    image=%container.image.repository pod=%k8s.pod.name ns=%k8s.ns.name)
  priority: WARNING
  tags: [container, shell, mitre_execution]
```

### Audit Log Queries

With control plane audit logs in CloudWatch, use Logs Insights to hunt for suspicious activity:

```sql
# Find kubectl exec sessions (potential lateral movement)
fields @timestamp, user.username, objectRef.resource, objectRef.name, objectRef.namespace
| filter verb = "create" and objectRef.subresource = "exec"
| sort @timestamp desc
| limit 50
```

```sql
# Detect privilege escalation — ClusterRoleBindings granting cluster-admin
fields @timestamp, user.username, objectRef.name, requestObject
| filter verb in ["create", "update"] and objectRef.resource = "clusterrolebindings"
| sort @timestamp desc
```

```sql
# Find pods running as privileged
fields @timestamp, user.username, objectRef.name, objectRef.namespace
| filter verb = "create" and objectRef.resource = "pods"
| filter requestObject like "privileged"
| sort @timestamp desc
```

---

## Building the Monitoring Pipeline

Here's the architecture that covers all four monitoring types:

1. **Enable control plane logging** — API server + audit logs to CloudWatch
2. **Deploy Fluent Bit DaemonSet** — pod and node logs to CloudWatch, with filters to drop noise
3. **Deploy Container Insights** — cluster and pod metrics
4. **Enable GuardDuty EKS protection** — audit log monitoring + runtime monitoring
5. **Deploy Falco** — custom runtime rules, alerts to CloudWatch via Falcosidekick
6. **Route alerts** — CloudWatch alarms or EventBridge rules to SNS/Slack/PagerDuty for high-severity findings

### Cost Control

EKS monitoring generates high log volume. Keep costs manageable:

- **Filter early**: Drop verbose debug logs and health check noise in Fluent Bit before they reach CloudWatch
- **Retention tiers**: Keep hot logs 30 days in CloudWatch, archive to S3 for long-term retention
- **Scope Falco rules**: Overly broad rules generate alert fatigue and storage costs. Start with the [default ruleset](https://github.com/falcosecurity/rules) and add custom rules as you learn your cluster's baseline
- **Resource budget**: Falco and Fluent Bit consume CPU and memory on every node. Size node groups accordingly or isolate monitoring agents in a dedicated node group

---

## Common Pitfalls

**Control plane logging disabled by default.** Unlike CloudTrail, EKS doesn't log anything until you explicitly enable it. Every new cluster starts blind.

**Monitoring the monitors.** Fluent Bit crashes or Falco stops collecting, and nobody notices because the thing that would alert you is the thing that's broken. Add a heartbeat check — a CloudWatch alarm on the absence of log data from your agents.

**Static thresholds instead of baselines.** "Alert on >100 API calls/minute" fires during normal deployments. Baseline your cluster's normal behavior first, then alert on deviations.

**Ignoring IRSA for monitoring agents.** Fluent Bit and Falco need IAM permissions to write to CloudWatch/S3. Use [IAM Roles for Service Accounts](https://docs.aws.amazon.com/eks/latest/userguide/iam-roles-for-service-accounts.html) instead of node-level instance profiles — it limits blast radius if a monitoring pod is compromised.

---

## Related Reading

- [EKS Security Best Practices: Hardening Your Cluster](/posts/eks-security-best-practices/) — RBAC, network policies, and pod security standards
- [GuardDuty Runtime Monitoring](/posts/aws-guardduty-runtime-monitoring/) — process-level detection inside containers and EC2
- [GuardDuty vs Security Hub: What Each Does and When You Need Both](/posts/aws-guardduty-vs-security-hub/) — how these tools fit together
- [CloudTrail Log Analysis: How to Find Who Did What](/posts/aws-cloudtrail-log-analysis/) — similar analysis techniques for AWS API events
- [Detect AWS IAM Privilege Escalation](/posts/aws-detecting-privilege-escalation/) — the IAM-level detection that complements EKS monitoring
- [AWS Security Checklist: 30-Minute Account Review](/posts/aws-security-checklist-2026/) — baseline controls including GuardDuty and logging
