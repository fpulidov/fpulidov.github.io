---
title: "EKS Security Best Practices: Hardening Your Cluster"
date: 2026-07-07
draft: false
description: "Harden Amazon EKS with RBAC, network policies, pod security standards, image scanning, secrets encryption, and node lockdown. Practical guide with YAML examples."
summary: "10 actionable EKS security best practices covering IAM integration, RBAC, network policies, pod security, image scanning, secrets management, and node hardening."
slug: "eks-security-best-practices"
tags: ["AWS", "EKS", "Kubernetes", "Security", "RBAC", "Network Policy", "Pod Security"]
categories: ["Cloud Security", "Guides"]
keywords: ["eks security", "eks security best practices", "aws eks security", "kubernetes security aws", "eks hardening", "eks rbac", "eks network policy"]
canonicalURL: "https://thehiddenport.dev/posts/eks-security-best-practices/"
enable_comments: true
---

Amazon EKS gives you a managed Kubernetes control plane, but security is still your responsibility. AWS handles patching the API server and etcd — everything else is on you: RBAC, network policies, pod security, image trust, secrets, and node configuration.

This post covers the security controls that matter most for production EKS clusters, with practical examples you can apply today.

> For monitoring and threat detection (CloudWatch, GuardDuty, Falco, audit logs), see [EKS Security: Monitoring, Audit Logs & Runtime Detection](/posts/eks-security-monitoring/).

---

## 1. Use IRSA Instead of Node-Level IAM Roles

By default, every pod on a node inherits the node's IAM role. If that role has broad permissions, any compromised pod can access them.

**IAM Roles for Service Accounts (IRSA)** binds IAM roles to specific Kubernetes service accounts, so each workload gets only the permissions it needs.

```bash
# Create an OIDC provider for the cluster (one-time)
eksctl utils associate-iam-oidc-provider \
  --cluster my-cluster --approve

# Create a service account with a scoped IAM role
eksctl create iamserviceaccount \
  --cluster my-cluster \
  --namespace app \
  --name s3-reader \
  --attach-policy-arn arn:aws:iam::aws:policy/AmazonS3ReadOnlyAccess \
  --approve
```

Then reference the service account in your pod spec:

```yaml
spec:
  serviceAccountName: s3-reader
```

The pod gets temporary STS credentials scoped to `AmazonS3ReadOnlyAccess`. No other pod on the same node can use them.

**Also consider:** EKS Pod Identity as a newer alternative to IRSA. It simplifies the setup by removing the need for an OIDC provider, but IRSA is still more widely adopted and documented.

---

## 2. Lock Down RBAC

Kubernetes RBAC controls who can do what inside the cluster. Misconfigurations here are one of the most common EKS security issues.

**Key rules:**

- Never bind `cluster-admin` to service accounts used by applications.
- Use `Role` and `RoleBinding` (namespace-scoped) instead of `ClusterRole` and `ClusterRoleBinding` wherever possible.
- Audit who has `create`, `update`, or `patch` on `pods`, `deployments`, `secrets`, `roles`, and `clusterroles`.

Create a read-only role for a monitoring service:

```yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  namespace: production
  name: pod-reader
rules:
- apiGroups: [""]
  resources: ["pods", "pods/log"]
  verbs: ["get", "list", "watch"]
```

**Audit existing RBAC** with `kubectl`:

```bash
# Who has cluster-admin?
kubectl get clusterrolebindings -o json | \
  jq '.items[] | select(.roleRef.name=="cluster-admin") | .subjects[]'

# What can a specific service account do?
kubectl auth can-i --list --as=system:serviceaccount:app:my-sa
```

---

## 3. Enable and Enforce Pod Security Standards

Kubernetes Pod Security Standards (PSS) replaced the deprecated PodSecurityPolicy. EKS supports Pod Security Admission (PSA) natively.

Three levels exist: `privileged` (unrestricted), `baseline` (prevents known escalations), and `restricted` (hardened).

Apply `baseline` enforcement to a namespace:

```bash
kubectl label namespace production \
  pod-security.kubernetes.io/enforce=baseline \
  pod-security.kubernetes.io/warn=restricted
```

This blocks pods that request `privileged: true`, `hostNetwork`, `hostPID`, or dangerous capabilities. The `warn=restricted` label logs warnings for pods that would fail the stricter level without blocking them — useful for gradual adoption.

**What baseline blocks:**
- Privileged containers
- Host namespace sharing (`hostPID`, `hostIPC`, `hostNetwork`)
- Dangerous capabilities (`NET_RAW`, `SYS_ADMIN`)
- Writable root filesystem (under `restricted`)

---

## 4. Restrict Network Traffic with Network Policies

By default, every pod can talk to every other pod in the cluster. Network Policies let you enforce least-privilege networking.

EKS doesn't ship with a network policy controller by default. You need to enable the **VPC CNI Network Policy** feature or install **Calico**.

Enable the VPC CNI network policy agent:

```bash
aws eks create-addon \
  --cluster-name my-cluster \
  --addon-name vpc-cni \
  --configuration-values '{"enableNetworkPolicy": "true"}'
```

Then apply policies. Example — allow the `api` pods to reach only the `database` pods on port 5432:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: api-to-db-only
  namespace: production
spec:
  podSelector:
    matchLabels:
      app: api
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: database
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - namespaceSelector: {}
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
```

The DNS egress rule is important — without it, pods can't resolve service names.

**Start with:** a default-deny policy per namespace, then allow specific traffic. This is the network equivalent of IAM least privilege.

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: production
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

---

## 5. Scan and Restrict Container Images

Running untrusted or unscanned images is one of the fastest ways to get compromised.

**Use Amazon ECR with image scanning:**

```bash
# Enable scan-on-push for a repository
aws ecr put-image-scanning-configuration \
  --repository-name my-app \
  --image-scanning-configuration scanOnPush=true
```

**Restrict image sources** with an OPA/Gatekeeper constraint or Kyverno policy. Example Kyverno policy that only allows images from your ECR registry:

```yaml
apiVersion: kyverno.io/v1
kind: ClusterPolicy
metadata:
  name: restrict-image-registries
spec:
  validationFailureAction: Enforce
  rules:
  - name: allowed-registries
    match:
      any:
      - resources:
          kinds:
          - Pod
    validate:
      message: "Images must come from the approved ECR registry."
      pattern:
        spec:
          containers:
          - image: "123456789012.dkr.ecr.*.amazonaws.com/*"
```

**Also:** never use `:latest` tags in production. Pin images to specific digests or immutable tags so you know exactly what's running.

---

## 6. Encrypt Secrets with KMS Envelope Encryption

By default, Kubernetes secrets are stored as base64-encoded plaintext in etcd. EKS supports envelope encryption with a KMS key, adding a real encryption layer.

```bash
aws eks associate-encryption-config \
  --cluster-name my-cluster \
  --encryption-config '[{
    "resources": ["secrets"],
    "provider": {
      "keyArn": "arn:aws:kms:eu-west-1:123456789012:key/your-key-id"
    }
  }]'
```

After enabling, re-create existing secrets to encrypt them:

```bash
kubectl get secrets -A -o json | kubectl replace -f -
```

**For sensitive credentials** (database passwords, API keys), consider AWS Secrets Manager with the [Secrets Store CSI Driver](https://docs.aws.amazon.com/secretsmanager/latest/userguide/integrating_csi_driver.html) instead of Kubernetes secrets. This pulls secrets directly from Secrets Manager into pod volumes without storing them in etcd at all.

---

## 7. Secure the Cluster Endpoint

EKS clusters can have a public API endpoint, a private one, or both. For production, restrict access.

**Option A — Private only** (most secure, requires VPN or Direct Connect):

```bash
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config endpointPublicAccess=false,endpointPrivateAccess=true
```

**Option B — Public with CIDR restrictions** (pragmatic for smaller teams):

```bash
aws eks update-cluster-config \
  --name my-cluster \
  --resources-vpc-config \
    endpointPublicAccess=true,endpointPrivateAccess=true,publicAccessCidrs='["203.0.113.0/24"]'
```

Never leave the public endpoint open to `0.0.0.0/0` in production.

---

## 8. Harden Worker Nodes

Worker nodes run your pods. If they're compromised, everything on them is compromised.

**Key hardening steps:**

- **Use managed node groups or Fargate** — AWS patches the underlying OS for managed node groups running the EKS-optimized AMI. Fargate removes node management entirely.
- **Disable SSH access** — use SSM Session Manager instead. No inbound ports, full audit logging. See [Replace SSH with Session Manager](/posts/securing-ec2-access-with-ssm/).
- **Enable IMDSv2** — prevents SSRF-based credential theft from the instance metadata service:

```yaml
# In your launch template
MetadataOptions:
  HttpTokens: required
  HttpPutResponseHopLimit: 1
  HttpEndpoint: enabled
```

- **Use Bottlerocket or Amazon Linux 2023** — minimal OS images designed for containers with automatic security updates and reduced attack surface.

---

## 9. Enable Audit Logging

EKS control plane logs include API server audit events that record every request to the Kubernetes API. This is your forensic trail.

```bash
aws eks update-cluster-config \
  --name my-cluster \
  --logging '{"clusterLogging":[{
    "types":["api","audit","authenticator"],
    "enabled":true
  }]}'
```

Log types to enable:

| Type | What it captures | When to enable |
|---|---|---|
| `api` | API server request/response | Always |
| `audit` | Who did what, when, on which resource | Always |
| `authenticator` | IAM-to-Kubernetes auth mapping | Always |
| `controllerManager` | Controller reconciliation loops | Debugging |
| `scheduler` | Pod scheduling decisions | Debugging |

Enable `api`, `audit`, and `authenticator` for all production clusters. The other two generate high volume and are primarily useful for troubleshooting.

> For building detection rules on top of these logs, see [EKS Security: Monitoring, Audit Logs & Runtime Detection](/posts/eks-security-monitoring/).

---

## 10. Implement Service Mesh or mTLS

Pod-to-pod traffic inside the cluster is unencrypted by default. Any pod that can capture network traffic can read it.

For workloads that handle sensitive data, add a service mesh that provides mutual TLS (mTLS) between services:

- **AWS App Mesh** — managed, integrates with EKS natively
- **Istio** — feature-rich, more operational overhead
- **Linkerd** — lightweight, easy to adopt

If a full service mesh is too heavy, consider **cert-manager** with pod-level TLS certificates as a lighter alternative.

---

## Quick Reference Checklist

| Control | Priority | Status |
|---|---|---|
| IRSA or Pod Identity for IAM | Critical | |
| RBAC audit — remove unnecessary `cluster-admin` | Critical | |
| Pod Security Standards enforced | High | |
| Network Policies with default deny | High | |
| ECR image scanning enabled | High | |
| Image registry restrictions | High | |
| KMS envelope encryption for secrets | Medium | |
| Private or CIDR-restricted cluster endpoint | Medium | |
| Worker node hardening (IMDSv2, no SSH) | Medium | |
| Control plane audit logging enabled | Critical | |
| mTLS between services | Medium | |

---

## Conclusion

EKS security is about layers. No single control protects you, but combining IAM scoping (IRSA), access control (RBAC), network segmentation (Network Policies), workload hardening (PSA), and visibility (audit logs) gives you a strong posture that's practical to maintain.

Start with the critical items — IRSA, RBAC audit, audit logging, and pod security standards. Then work your way down the list. Each control you add reduces your attack surface and makes incident response faster when something does happen.

**Related guides:**
- [EKS Security: Monitoring, Audit Logs & Runtime Detection](/posts/eks-security-monitoring/)
- [IAM Least Privilege in AWS: Access Analyzer Guide](/posts/iam-access-analyzer-least-privilege/)
- [Replace SSH with Session Manager: Secure EC2 Access Guide](/posts/securing-ec2-access-with-ssm/)
- [AWS Security Checklist 2026](/posts/aws-security-checklist-2026/)
