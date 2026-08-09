---
title: "AWS Security Hub MCP App: Turn Compliance Findings into Action"
date: 2026-08-01
draft: false
description: "Security Hub now has an MCP server for Claude Desktop. Query your exposure findings in natural language, visualize attack paths, and prioritize fixes — here's how to set it up and what it's actually useful for."
summary: "Security Hub's new MCP app brings exposure findings into Claude Desktop. Setup, available tools, and practical use cases for compliance triage and remediation prioritization."
slug: "aws-security-hub-mcp-app"
tags: ["AWS", "Security Hub", "MCP", "Claude", "Compliance", "AI", "Security"]
keywords: ["aws security hub mcp", "security hub claude desktop", "security hub mcp app", "aws security hub ai", "security hub exposure findings", "security hub compliance triage"]
categories: ["Cloud Security"]
canonicalURL: "https://thehiddenport.dev/posts/aws-security-hub-mcp-app/"
enable_comments: true
---

Security Hub is one of those AWS services that's easy to enable and hard to use well. It aggregates findings from GuardDuty, Config, Inspector, and third-party tools into one dashboard — but then you're staring at hundreds of findings across multiple compliance frameworks, trying to figure out which ones actually matter and where to start.

As of July 2026, AWS released a **Security Hub MCP App** (in preview) that brings your exposure findings directly into Claude Desktop. Instead of clicking through the console, you can ask questions like "what are my top exposures?" or "how can I improve my PCI-DSS compliance with quick wins?" and get prioritized answers with interactive visualizations — attack paths, network hops, correlated findings — right in the conversation.

Here's how to set it up and where it's actually useful.

---

## What It Is

The Security Hub MCP App is a local [Model Context Protocol](https://modelcontextprotocol.io/) server that runs on your machine and connects to Claude Desktop. It calls Security Hub APIs using your existing AWS credentials, and every tool is **read-only** — it can't modify your environment.

Each query returns two things: a text summary that Claude reasons over, and an interactive visualization you can inspect in the same conversation. AWS calls this a "dual response" — the AI gets the data it needs to answer follow-up questions, and you get a visual to verify what it's saying.

The app works with **exposure findings** — a newer Security Hub concept that correlates multiple signals (vulnerabilities, misconfigurations, network reachability, sensitive data presence) into a single view of a resource that's exposed to risk. This is different from the individual findings you're used to seeing; an exposure finding tells you "this EC2 instance has a known CVE, is publicly reachable, and sits in a subnet with a database" — the full picture, not just one signal.

---

## Setup

Prerequisites:
- **AWS credentials configured** — the server uses your standard credential chain
- **Claude Desktop installed** — [download here](https://claude.ai/download) if you don't have it
- **Security Hub enabled** with exposure findings available in your account

Verify your credentials work:

```bash
aws sts get-caller-identity
aws configure get region
```

Both must succeed. Then:

1. Download the MCP App bundle: [sechub-mcp.mcpb](https://d29a07xw1myhp4.cloudfront.net/latest/sechub-mcp.mcpb)
2. Open the `.mcpb` file — Claude Desktop starts a configuration flow
3. Follow the prompts to install the server

Test it by asking Claude: **"What are my top security exposures?"**

If it works, you'll see an interactive table of your most critical exposure findings. If not, the error message will tell you whether the issue is credentials, region, or Security Hub configuration.

---

## Available Tools

The MCP app exposes eight read-only tools:

| Tool | What It Does |
|------|-------------|
| `top_exposures` | Lists your most urgent exposure findings as an interactive table. **Start here** — the other tools need a finding ID from this list. |
| `finding_detail` | Overview of one finding with its correlated-finding trait summary |
| `finding_overview` | Text summary of a single finding |
| `correlated_finding_detail` | Findings correlated to one exposure by trait (vulnerability, misconfiguration, reachability) |
| `attack_path` | Interactive graph showing how an exposure is reachable — resources, identities, and relationships |
| `network_path` | Ordered network hops from the AWS edge to the target (Internet Gateway → NACL → Security Group → ENI → Instance) |
| `recommendation` | Remediation guidance with documentation links |
| `resource_detail` | Resource configuration by instance ID or ARN |

The workflow is: `top_exposures` → pick a finding → `finding_detail` or `attack_path` → `recommendation`. Each step returns both text and visuals.

---

## Where This Is Actually Useful

### Compliance Triage

This is the use case that makes the MCP app worth installing. Instead of scrolling through Security Hub's findings console and mentally prioritizing, you can ask:

- *"What are my top PCI-DSS compliance gaps that I can fix quickly?"*
- *"Which exposures affect production accounts only?"*
- *"Show me findings related to public network reachability"*

Claude can cross-reference the exposure findings, filter by framework or severity, and suggest a prioritized remediation order — starting with the fixes that improve your compliance score the most with the least effort.

### Understanding Attack Paths

The `attack_path` tool visualizes how an exposure is reachable. Instead of reading a finding that says "EC2 instance has CVE-2026-XXXX" and guessing how exploitable it is, you see the full chain: is it internet-facing? What's between the attacker and the resource? What else can the resource access?

This is the context that turns a finding from "medium severity, we'll get to it" into "this is directly reachable from the internet and has access to our database subnet — fix it today."

### Drafting Preventive Controls

If the same misconfiguration keeps appearing across accounts — say, security groups with SSH open to the world, or S3 buckets without encryption — you can ask Claude to draft an SCP or Config rule based on the actual findings pattern. The conversation has the finding data, the affected resources, and the remediation guidance all in context, so the generated policy is grounded in what's actually happening in your environment, not a generic template.

### Client-Facing Summaries

For consultants running security reviews, the dual-response format is useful for generating summaries. Ask for the top exposures, walk through the critical ones with attack paths, and the conversation itself becomes a structured artifact you can reference when writing the audit report.

---

## What It Doesn't Do

**It's read-only.** The MCP app can't remediate findings, modify security groups, update IAM policies, or change any configuration. It's an investigation and triage tool, not a remediation bot. You still do the fixing.

**It works with exposure findings, not all Security Hub findings.** If you're looking for individual Config rule violations or GuardDuty alerts that haven't been correlated into an exposure, they won't appear here. Use the Security Hub console or CLI for those.

**It's local.** The MCP server runs on your machine with your credentials. This means the access scope matches whatever IAM permissions your credentials have — it's not a shared team tool. Each team member runs their own instance.

**It's in preview.** Expect rough edges. The tool set may change, and the exposure findings feature itself is relatively new in Security Hub.

---

## Cost

No additional cost beyond your existing Security Hub subscription. The MCP app is free to install and use. You pay for Security Hub's per-finding pricing as usual, but the MCP layer adds nothing on top.

---

## Setting It Up Alongside Other MCP Servers

If you're already running MCP servers in Claude Desktop (analytics tools, custom internal servers, etc.), the Security Hub MCP app adds to your existing configuration. Each server runs independently — they don't conflict. This means you can have your analytics data, your Security Hub findings, and your code context all available in the same Claude conversation.

---

## Key Takeaway

Security Hub has always been good at collecting findings. The problem was never the data — it was turning that data into prioritized action. The MCP app doesn't add new findings or new detection capabilities. What it does is make the findings you already have **queryable** — and that changes the workflow from "scroll through hundreds of findings and hope you notice the important ones" to "ask which ones matter and get a prioritized answer."

If you're already running Security Hub, this is a free upgrade to how you interact with it. Install it, ask about your top exposures, and see if the prioritization matches what you'd have picked manually. In my experience, the attack path visualization alone surfaces context that the flat findings table never shows.

---

## Related Reading

- [GuardDuty vs Security Hub: What Each Does and When You Need Both](/posts/aws-guardduty-vs-security-hub/) — understand what feeds into Security Hub before querying it
- [AWS Security Checklist: 30-Minute Account Review](/posts/aws-security-checklist-2026/) — the baseline controls that prevent many of these findings
- [AWS SCPs That Actually Work](/posts/aws-scp-best-practices/) — preventive guardrails you can draft from findings patterns
- [AWS Misconfigurations I Find in Every Security Audit](/posts/aws-security-misconfigurations-guide/) — the recurring findings this tool helps you triage
- [GuardDuty Runtime Monitoring](/posts/aws-guardduty-runtime-monitoring/) — runtime detection that generates the findings Security Hub correlates
- [Enforcing Least Privilege in AWS IAM](/posts/aws-enforcing-least-privilege/) — fix the IAM-related exposures this tool will surface
