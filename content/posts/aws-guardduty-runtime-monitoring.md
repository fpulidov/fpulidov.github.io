---
title: "AWS GuardDuty Runtime Monitoring: The Security Agent That Sees Inside Your Workloads"
date: 2026-07-27
draft: false
description: "Standard GuardDuty watches network traffic. Runtime Monitoring deploys an agent that sees process execution, file access, and privilege escalation inside EC2, EKS, and ECS — here's how to enable it without blowing up your bill."
slug: "aws-guardduty-runtime-monitoring"
tags: ["AWS", "Security", "GuardDuty", "Runtime Monitoring", "EC2", "EKS", "ECS", "Threat Detection"]
keywords: ["aws security agent", "guardduty runtime monitoring", "aws guardduty security agent", "guardduty ec2 runtime monitoring", "guardduty eks runtime monitoring", "aws runtime threat detection", "guardduty agent deployment"]
categories: ["Cloud Security"]
canonicalURL: "https://thehiddenport.dev/posts/aws-guardduty-runtime-monitoring/"
enable_comments: true
---

Standard GuardDuty analyzes VPC Flow Logs, CloudTrail events, and DNS queries — all metadata about what happened around your workloads. It sees that an EC2 instance connected to a suspicious IP, but it can't tell you which process made that connection, what command-line arguments it used, or whether it escalated privileges first.

Runtime Monitoring changes that. It deploys a lightweight security agent inside your EC2 instances, EKS pods, and ECS tasks that watches operating system events in real time. Process execution, file access, network connections, privilege changes — all visible to GuardDuty without you writing a single detection rule.

This post covers what the agent monitors, how to deploy it across EC2/EKS/ECS, what findings it generates, and how to control costs.

---

## What Standard GuardDuty Misses

Standard GuardDuty (without the security agent) detects threats using external signals:

- **VPC Flow Logs** — IP addresses, ports, byte counts. No process or payload visibility.
- **CloudTrail** — API calls made to AWS services. Nothing about what happens inside the OS.
- **DNS logs** — Domain queries. No context about which binary made the request.

This means standard GuardDuty catches things like "instance talked to a C2 server" but misses the full kill chain: the initial reverse shell, the privilege escalation from user to root, the lateral movement tools being dropped to `/tmp`.

Runtime Monitoring fills that gap by monitoring OS-level activity directly.

---

## What the Security Agent Monitors

The GuardDuty security agent collects events across multiple categories. Here's what it actually watches:

### Process Events

Every process that starts on a monitored host is observed:

- Process name, path, and PID
- Command-line arguments at execution time
- Parent process details (full lineage)
- User/group IDs (including effective UID/GID)
- Present working directory
- SHA-256 hash of the executable
- Environment variables (`LD_PRELOAD`, `LD_LIBRARY_PATH` — the ones attackers abuse)

### File System Events

- File opens with access mode (read-only, write, read-write)
- File renames and permission changes (chmod)
- Hard links and symbolic links created
- Mounts and unmounts of file systems
- Kernel module loads

### Network Events

- Socket creation (type, address family, protocol)
- Outbound connections (destination IP, port)
- Listening sockets (bind, listen)
- DNS queries and responses (full payload)

### Memory and Process Manipulation

- Memory protection changes (mprotect)
- Memory-mapped files
- Cross-process memory reads/writes (process_vm_readv/writev)
- Ptrace usage (the syscall used for debugging — and for process injection)
- File descriptor duplication (dup — used in reverse shells)

### Container Context

For containerized workloads, every event includes:

- Container name, ID, runtime, and image
- Kubernetes pod name, namespace, and cluster (for EKS)
- ECS task ARN, cluster, service name, and launch type (for Fargate/ECS)

This means a finding like "reverse shell detected" includes the full path: which container, which pod, which process, what command was run, and what parent process spawned it.

---

## What It Detects (Finding Types)

Runtime Monitoring generates findings that standard GuardDuty simply cannot produce. They're grouped by MITRE ATT&CK tactic:

### Execution

| Finding | What it means |
|---------|---------------|
| `Execution:Runtime/ReverseShell` | A process redirected stdin/stdout to a network socket |
| `Execution:Runtime/NewBinaryExecuted` | A binary not part of the original image was run |
| `Execution:Runtime/NewLibraryLoaded` | A shared library not in the original image was loaded |
| `Execution:Runtime/SuspiciousTool` | Pentesting/hacking tools executed (nmap, mimikatz, etc.) |
| `Execution:Runtime/MaliciousFileExecuted` | Known malware binary executed |
| `Execution:Runtime/SuspiciousShellCreated` | Interactive shell spawned in an unexpected context |

### Privilege Escalation

| Finding | What it means |
|---------|---------------|
| `PrivilegeEscalation:Runtime/ElevationToRoot` | A non-root process became root |
| `PrivilegeEscalation:Runtime/DockerSocketAccessed` | Docker socket accessed from inside a container |
| `PrivilegeEscalation:Runtime/RuncContainerEscape` | CVE-2019-5736 (runc) container escape attempted |
| `PrivilegeEscalation:Runtime/CGroupsReleaseAgentModified` | Cgroups escape technique detected |
| `PrivilegeEscalation:Runtime/ContainerMountsHostDirectory` | Host filesystem mounted inside container |
| `PrivilegeEscalation:Runtime/UserfaultfdUsage` | Userfaultfd exploit technique detected |

### Defense Evasion

| Finding | What it means |
|---------|---------------|
| `DefenseEvasion:Runtime/FilelessExecution` | Code executed from memory without touching disk |
| `DefenseEvasion:Runtime/ProcessInjection.Proc` | Process injection via /proc |
| `DefenseEvasion:Runtime/ProcessInjection.Ptrace` | Process injection via ptrace |
| `DefenseEvasion:Runtime/ProcessInjection.VirtualMemoryWrite` | Process injection via memory write |
| `DefenseEvasion:Runtime/KernelModuleLoaded` | Suspicious kernel module loaded |
| `DefenseEvasion:Runtime/PtraceAntiDebugging` | Anti-debugging techniques used |

### Persistence & Discovery

| Finding | What it means |
|---------|---------------|
| `Persistence:Runtime/SuspiciousCommand` | Commands to establish persistence (cron, systemd, init) |
| `Persistence:Runtime/SensitiveFileModified` | Modification to auth files (/etc/passwd, SSH keys) |
| `Discovery:Runtime/SuspiciousCommand` | Reconnaissance commands run (whoami, ifconfig, etc.) |

### Impact

| Finding | What it means |
|---------|---------------|
| `Impact:Runtime/CryptoMinerExecuted` | Crypto mining process detected |
| `CryptoCurrency:Runtime/BitcoinTool.B` | Connection to crypto mining pool |

Every one of these findings includes the full process tree — parent process, command-line arguments, user context, and container metadata. That's what makes Runtime Monitoring actionable: you don't just know "something bad happened," you know exactly what ran, who ran it, and where.

---

## How It Works (Architecture)

```
┌─────────────────────────────────────────────────┐
│               Your VPC                          │
│                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │
│  │   EC2    │  │   EKS    │  │ ECS/Fargate  │  │
│  │ Instance │  │   Pod    │  │    Task      │  │
│  │          │  │          │  │              │  │
│  │ [Agent]  │  │ [Agent]  │  │   [Agent]    │  │
│  └────┬─────┘  └────┬─────┘  └──────┬───────┘  │
│       │              │               │          │
│       └──────────────┼───────────────┘          │
│                      ▼                          │
│         ┌────────────────────────┐              │
│         │  VPC Endpoint (private)│              │
│         └────────────┬───────────┘              │
│                      │                          │
└──────────────────────┼──────────────────────────┘
                       ▼
            ┌─────────────────────┐
            │  GuardDuty Backend  │
            │  (threat analysis)  │
            └──────────┬──────────┘
                       ▼
            ┌─────────────────────┐
            │     Findings        │
            │  → EventBridge      │
            │  → Security Hub     │
            └─────────────────────┘
```

Key architecture points:

1. **Agent runs inside the workload** — on EC2 it's an RPM/DEB package managed by SSM; on EKS it's a DaemonSet; on ECS it's a sidecar managed by AWS.
2. **Data stays in your VPC** — the agent sends events to a VPC endpoint (private link), never over the public internet.
3. **No access to your data** — the agent observes syscalls and metadata. It doesn't read file contents, memory, or application data.
4. **VPC Flow Log charges waived** — when the agent is active on an instance, GuardDuty stops charging for VPC Flow Log analysis on that instance (avoids double-billing).

---

## Enabling Runtime Monitoring

### Console Setup

1. Open the [GuardDuty console](https://console.aws.amazon.com/guardduty/)
2. Go to **Protection plans** → **Runtime Monitoring**
3. Toggle **Runtime Monitoring** to **Enabled**
4. Under **Automated agent configuration**, enable the resource types you want:
   - **Amazon EC2** — GuardDuty installs/updates the agent via SSM
   - **Amazon EKS** — GuardDuty deploys an EKS add-on (DaemonSet)
   - **AWS Fargate (ECS)** — GuardDuty injects a sidecar container

That's it. With automated management, GuardDuty handles agent installation, updates, and VPC endpoint creation.

### Terraform Setup

```hcl
resource "aws_guardduty_detector" "main" {
  enable = true
}

resource "aws_guardduty_detector_feature" "runtime_monitoring" {
  detector_id = aws_guardduty_detector.main.id
  name        = "RUNTIME_MONITORING"
  status      = "ENABLED"

  additional_configuration {
    name   = "EKS_ADDON_MANAGEMENT"
    status = "ENABLED"
  }

  additional_configuration {
    name   = "ECS_FARGATE_AGENT_MANAGEMENT"
    status = "ENABLED"
  }

  additional_configuration {
    name   = "EC2_AGENT_MANAGEMENT"
    status = "ENABLED"
  }
}
```

The `additional_configuration` blocks control whether GuardDuty manages the agent automatically for each resource type. Set any to `"DISABLED"` if you prefer to deploy the agent yourself.

### Manual Agent Deployment (EC2)

If you choose manual management instead of automated:

1. **Create a VPC endpoint** for `com.amazonaws.<region>.guardduty-data` in your VPC
2. **Install the agent** using SSM or user data:

```bash
# Amazon Linux 2 / AL2023
sudo yum install -y amazon-guardduty-agent

# Ubuntu/Debian
sudo apt-get install -y amazon-guardduty-agent
```

3. **Verify the agent is running**:

```bash
sudo systemctl status amazon-guardduty-agent
```

For EKS manual management, you install the `amazon-guardduty-agent` EKS add-on yourself through the EKS console or `eksctl`.

---

## Prerequisites

Before the security agent works, your environment needs:

**For EC2 (automated):**
- SSM Agent installed and running (comes pre-installed on Amazon Linux 2, AL2023, Ubuntu 20.04+)
- Instance must have an instance profile (for Instance Identity Role authentication)
- Kernel version 5.4+ (most modern AMIs qualify)

**For EKS:**
- EKS cluster version 1.24+
- Nodes running Amazon Linux 2 or Bottlerocket
- VPC CNI plugin installed

**For ECS/Fargate:**
- Platform version 1.4.0+ (Fargate)
- No special prerequisites for EC2-backed ECS tasks

**For all resource types:**
- GuardDuty already enabled in the region
- Outbound connectivity to the VPC endpoint (security groups must allow TCP 443 to the endpoint)

---

## Checking Coverage

After enabling, verify the agent is deployed and reporting:

1. Go to **GuardDuty** → **Runtime Monitoring** → **Runtime coverage**
2. Check the **Coverage status** for each instance/cluster/task:
   - **Healthy** — agent deployed and sending events
   - **Unhealthy** — agent has issues (missing SSM, connectivity problems, unsupported OS)

For EC2, you can also filter by tag. This is useful when rolling out gradually — tag a subset of instances and enable automated management only for those tags first.

---

## Pricing

Runtime Monitoring is priced per vCPU per month, regardless of resource type:

| Volume | Cost (US East) |
|--------|---------------|
| First 500 vCPUs | $1.50/vCPU/month |
| Next 4,500 vCPUs | $0.75/vCPU/month |
| Over 5,000 vCPUs | $0.25/vCPU/month |

**What counts as a vCPU:**
- EC2: vCPUs of the instance type (a `t3.medium` = 2 vCPUs)
- EKS: vCPUs of the underlying node (not the pod request)
- Fargate: vCPUs allocated to the task

**Cost offset:** When the agent is active on an EC2 instance, VPC Flow Log analysis charges (~$1.00–$1.50 per GB) are waived for that instance. For high-traffic instances, this offset can be significant.

**Free trial:** 30 days of Runtime Monitoring at no cost when first enabled. Use this to evaluate findings and estimate ongoing costs in the **Usage** tab.

### Cost Example

A typical small environment:
- 10 EC2 instances (mix of `t3.medium` and `t3.large`) = ~25 vCPUs
- 1 EKS cluster with 3 `m5.large` nodes = 6 vCPUs
- 5 Fargate tasks at 1 vCPU each = 5 vCPUs

Total: 36 vCPUs × $1.50 = **$54/month**

For that price, you get process-level threat detection that would otherwise require deploying and maintaining a separate EDR agent (Falco, Sysdig, CrowdStrike) — which typically costs more and requires operational overhead.

---

## When Runtime Monitoring Is Worth It

**Enable it when:**
- You run workloads that process untrusted input (web apps, APIs, CI runners)
- You need container-escape detection (EKS/ECS multi-tenant environments)
- Compliance requires host-level intrusion detection (PCI, SOC2)
- You want to detect compromised instances before lateral movement happens
- You already use GuardDuty and want deeper visibility without deploying a third-party agent

**Skip it when:**
- All your workloads are serverless (Lambda already has its own GuardDuty monitoring)
- You already run a full EDR solution (CrowdStrike, SentinelOne) on every host — adding the GuardDuty agent creates duplication
- Cost is critical and your instances are idle/low-risk (dev environments, batch jobs that run infrequently)

---

## Runtime Monitoring vs Third-Party EDR

| | GuardDuty Runtime Monitoring | Third-Party EDR (Falco, CrowdStrike, etc.) |
|---|---|---|
| **Deployment** | One toggle in console or Terraform | Agent installation, rule management, infrastructure |
| **Rule management** | Fully managed (AWS maintains detections) | You write/maintain rules (Falco) or vendor manages (CrowdStrike) |
| **Custom rules** | No — detections are fixed | Yes — full flexibility |
| **AWS integration** | Native (EventBridge, Security Hub, Organizations) | Requires custom integration |
| **Container metadata** | Automatic (pod, namespace, task, cluster) | Varies by tool |
| **Cost** | Per vCPU, simple | Per host/per agent, often higher |
| **Coverage depth** | OS-level events + AWS threat intel | OS-level events + vendor threat intel |

The practical answer for most teams: start with GuardDuty Runtime Monitoring (it's one toggle). If you need custom detection rules or broader endpoint protection beyond AWS, layer a third-party tool on top.

---

## Routing Runtime Findings to Slack

Runtime Monitoring findings flow through EventBridge like all GuardDuty findings. Here's a focused rule that alerts only on the high-value runtime findings:

```hcl
resource "aws_cloudwatch_event_rule" "runtime_findings" {
  name        = "guardduty-runtime-high-severity"
  description = "High severity GuardDuty Runtime Monitoring findings"

  event_pattern = jsonencode({
    source      = ["aws.guardduty"]
    detail-type = ["GuardDuty Finding"]
    detail = {
      severity = [{ numeric = [">=", 7] }]
      type = [{
        prefix = "Execution:Runtime"
      }, {
        prefix = "PrivilegeEscalation:Runtime"
      }, {
        prefix = "DefenseEvasion:Runtime"
      }, {
        prefix = "Backdoor:Runtime"
      }]
    }
  })
}

resource "aws_cloudwatch_event_target" "sns" {
  rule      = aws_cloudwatch_event_rule.runtime_findings.name
  target_id = "send-to-sns"
  arn       = aws_sns_topic.security_alerts.arn
}
```

This filters for runtime-specific findings at severity 7+ (HIGH/CRITICAL). You avoid getting paged for informational network findings while catching the ones that indicate active compromise.

---

## Common Pitfalls

**1. Enabling automated management without SSM**

EC2 automated agent management requires SSM Agent running and the instance to have an instance profile. If your instances don't have SSM connectivity, the agent won't deploy and you'll see "Unhealthy" coverage status with no findings.

Fix: ensure `AmazonSSMManagedInstanceCore` is attached to instance roles, and SSM endpoints are reachable.

**2. Security groups blocking the VPC endpoint**

The agent communicates with GuardDuty via a VPC endpoint on TCP 443. If your security groups don't allow outbound HTTPS to the endpoint's ENIs, the agent reports as healthy but can't deliver events.

Fix: allow TCP 443 from instances to the `com.amazonaws.<region>.guardduty-data` VPC endpoint security group.

**3. Expecting immediate findings**

Like all GuardDuty features, Runtime Monitoring builds a baseline before generating findings. Normal process activity on day one won't trigger alerts. Give it 7–14 days before testing with simulated attacks.

**4. Not checking kernel compatibility**

The agent requires kernel 5.4+ for full eBPF tracing support. Older Amazon Linux 1 AMIs or custom kernels below 5.4 won't work. Check with `uname -r` before enabling.

---

**Related guides:**
- [AWS GuardDuty Setup: Route Findings to Slack & Your SIEM in 10 Minutes](/posts/aws-guardduty-setup/) — the foundation: enable GuardDuty and wire up alerts
- [GuardDuty vs Security Hub: What Each Does and When You Need Both](/posts/aws-guardduty-vs-security-hub/) — where Runtime Monitoring findings end up
- [EKS Security Monitoring: Audit Logs, Falco & GuardDuty](/posts/eks-security-monitoring/) — how Runtime Monitoring compares to Falco for EKS
- [AWS Security Monitoring Without the Enterprise Price Tag](/posts/affordable-aws-security-monitoring/) — full monitoring stack on a budget
