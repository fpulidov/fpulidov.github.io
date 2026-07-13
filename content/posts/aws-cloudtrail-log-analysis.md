---
title: "AWS CloudTrail Log Analysis: How to Find Who Did What (And When)"
date: 2026-07-13
tags: ["AWS", "CloudTrail", "Security", "Compliance", "IAM", "Athena"]
keywords: ["aws cloudtrail log analysis", "cloudtrail athena queries", "aws who created resource", "cloudtrail investigate", "aws audit trail", "cloudtrail security analysis"]
categories: ["Cloud Security", "Guides"]
description: "Practical guide to analyzing AWS CloudTrail logs — Athena queries for tracing non-compliant resources, finding who opened SSH to the world, and building your investigation workflow."
summary: "How to actually use CloudTrail logs day-to-day — tracing non-compliant resources to their source, querying with Athena, and setting up alerts before things go wrong."
slug: "aws-cloudtrail-log-analysis"
canonicalURL: "https://thehiddenport.dev/posts/aws-cloudtrail-log-analysis/"
enable_comments: true
---

Most CloudTrail guides jump straight into detecting credential compromise and lateral movement. That's not how most teams actually use CloudTrail.

In my experience, the real day-to-day value of CloudTrail is answering one question: **who did this?** Someone created a VPC that doesn't follow naming conventions. A security group appeared with SSH open to the world. An IAM user got admin privileges that nobody approved. CloudTrail is how you trace those back to a person, a role, and a timestamp.

This guide covers how I actually use CloudTrail for internal investigations and compliance forensics — the unglamorous but critical work that keeps environments clean.

---

## How CloudTrail Works (The Parts That Matter)

CloudTrail records API calls as **events**. Every `CreateSecurityGroup`, `AttachRolePolicy`, `RunInstances` — all of it gets logged with who called it, from where, and when.

Three things to understand upfront:

1. **Management events** (control plane operations like creating resources, modifying IAM) are logged by default. **Data events** (S3 object reads, Lambda invocations) are not — you have to enable them explicitly, and they cost more.

2. **CloudTrail delivers logs with a delay** — typically 5-15 minutes. Don't expect real-time. If you need faster alerting, pair it with [EventBridge rules](/posts/aws-guardduty-setup/) that trigger on specific API calls.

3. **90 days of event history** is available in the console for free. For anything older, you need a trail writing to S3, and Athena or CloudTrail Lake to query it.

For compliance investigations, management events are almost always enough. You're tracing resource creation and permission changes, not auditing who read which S3 object.

---

## Setting Up CloudTrail for Analysis

If you're running an AWS Organization, set up an **organization trail** that captures events from all accounts into a central S3 bucket in your security account. This is non-negotiable — you can't investigate across accounts if each one has its own isolated trail.

```bash
aws cloudtrail create-trail \
  --name org-trail \
  --s3-bucket-name my-cloudtrail-bucket \
  --is-organization-trail \
  --is-multi-region-trail \
  --enable-log-file-validation

aws cloudtrail start-logging --name org-trail
```

Key settings:
- **Multi-region**: Always. An attacker (or a misconfiguring engineer) won't limit themselves to your primary region.
- **Log file validation**: Enables digest files that let you verify logs haven't been tampered with.
- **S3 lifecycle policy**: Move logs to Glacier after 90 days, delete after 1 year (adjust to your compliance requirements).

If you're using [SCPs to protect security tooling](/posts/aws-scp-best-practices/), make sure `cloudtrail:StopLogging` and `cloudtrail:DeleteTrail` are denied — otherwise someone could cover their tracks.

---

## Querying CloudTrail with Athena

The CloudTrail console search works for quick lookups, but for real investigations you need Athena. It lets you run SQL against your CloudTrail logs stored in S3.

### Create the Athena Table

CloudTrail can create this for you automatically. Go to **CloudTrail > Event history > Create Athena table** and select your S3 bucket. Or create it manually:

```sql
CREATE EXTERNAL TABLE cloudtrail_logs (
    eventversion STRING,
    useridentity STRUCT<
        type:STRING,
        principalid:STRING,
        arn:STRING,
        accountid:STRING,
        invokedby:STRING,
        accesskeyid:STRING,
        userName:STRING,
        sessioncontext:STRUCT<
            attributes:STRUCT<
                mfaauthenticated:STRING,
                creationdate:STRING>,
            sessionissuer:STRUCT<
                type:STRING,
                principalId:STRING,
                arn:STRING,
                accountId:STRING,
                userName:STRING>,
            ec2RoleDelivery:STRING,
            webIdFederationData:MAP<STRING,STRING>>>,
    eventtime STRING,
    eventsource STRING,
    eventname STRING,
    awsregion STRING,
    sourceipaddress STRING,
    useragent STRING,
    errorcode STRING,
    errormessage STRING,
    requestparameters STRING,
    responseelements STRING,
    additionaleventdata STRING,
    requestid STRING,
    eventid STRING,
    resources ARRAY<STRUCT<
        arn:STRING,
        accountid:STRING,
        type:STRING>>,
    eventtype STRING,
    apiversion STRING,
    readonly STRING,
    recipientaccountid STRING,
    serviceeventdetails STRING,
    sharedeventid STRING,
    vpcendpointid STRING,
    tlsdetails STRUCT<
        tlsVersion:STRING,
        cipherSuite:STRING,
        clientProvidedHostHeader:STRING>
)
COMMENT 'CloudTrail table for org-trail'
ROW FORMAT SERDE 'org.apache.hive.hcatalog.data.JsonSerDe'
STORED AS INPUTFORMAT 'com.amazon.emr.cloudtrail.CloudTrailInputFormat'
OUTPUTFORMAT 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'
LOCATION 's3://my-cloudtrail-bucket/AWSLogs/ACCOUNT-ID/CloudTrail/'
TBLPROPERTIES ('classification'='cloudtrail');
```

### Partition by Date

Without partitioning, every query scans your entire log history. Add partitions to limit scans to the timeframe you care about:

```sql
ALTER TABLE cloudtrail_logs ADD
    PARTITION (region='eu-west-1', year='2026', month='07', day='13')
    LOCATION 's3://my-cloudtrail-bucket/AWSLogs/ACCOUNT-ID/CloudTrail/eu-west-1/2026/07/13/';
```

Or use partition projection for automatic partitioning — saves you from manually adding partitions every day.

---

## The Queries I Actually Use

These are the queries I've run most in real investigations. All of them answer the same fundamental question: **who did this, and when?**

### Who Created This Security Group?

Someone opened SSH to the world. Find who:

```sql
SELECT
    eventtime,
    useridentity.arn AS who,
    sourceipaddress,
    json_extract_scalar(requestparameters, '$.groupName') AS sg_name,
    json_extract_scalar(requestparameters, '$.groupId') AS sg_id,
    requestparameters
FROM cloudtrail_logs
WHERE eventname = 'CreateSecurityGroup'
    AND eventtime > '2026-07-01'
ORDER BY eventtime DESC;
```

To find who added the offending inbound rule:

```sql
SELECT
    eventtime,
    useridentity.arn AS who,
    sourceipaddress,
    requestparameters
FROM cloudtrail_logs
WHERE eventname = 'AuthorizeSecurityGroupIngress'
    AND requestparameters LIKE '%0.0.0.0/0%'
    AND eventtime > '2026-07-01'
ORDER BY eventtime DESC;
```

This is the query I've run more than any other. Non-compliant security groups are the most common finding in every environment I've worked in.

### Who Created This IAM User?

When an IAM user shows up that shouldn't exist — especially one with admin permissions — trace it back:

```sql
SELECT
    eventtime,
    useridentity.arn AS created_by,
    sourceipaddress,
    json_extract_scalar(requestparameters, '$.userName') AS new_user,
    responseelements
FROM cloudtrail_logs
WHERE eventname = 'CreateUser'
    AND eventtime > '2026-06-01'
ORDER BY eventtime DESC;
```

Then check what policies were attached to that user:

```sql
SELECT
    eventtime,
    useridentity.arn AS attached_by,
    json_extract_scalar(requestparameters, '$.userName') AS target_user,
    json_extract_scalar(requestparameters, '$.policyArn') AS policy
FROM cloudtrail_logs
WHERE eventname IN ('AttachUserPolicy', 'PutUserPolicy')
    AND eventtime > '2026-06-01'
ORDER BY eventtime DESC;
```

If you see `AdministratorAccess` being attached, that's the conversation you need to have with that team. See [why IAM users should be replaced entirely](/posts/aws-iam-users-alternatives/) for the longer-term fix.

### Who Launched This EC2 Instance?

Useful when unknown instances appear, or when you need to trace back who spun up something in a non-approved region:

```sql
SELECT
    eventtime,
    useridentity.arn AS launched_by,
    awsregion,
    sourceipaddress,
    json_extract_scalar(responseelements, '$.instancesSet.items[0].instanceId') AS instance_id,
    json_extract_scalar(requestparameters, '$.instanceType') AS instance_type
FROM cloudtrail_logs
WHERE eventname = 'RunInstances'
    AND eventtime > '2026-07-01'
ORDER BY eventtime DESC;
```

### Who Modified This IAM Role's Trust Policy?

Trust policy changes can grant cross-account access. If a role suddenly trusts an external account, you want to know who changed it:

```sql
SELECT
    eventtime,
    useridentity.arn AS modified_by,
    sourceipaddress,
    json_extract_scalar(requestparameters, '$.roleName') AS role_name,
    requestparameters
FROM cloudtrail_logs
WHERE eventname = 'UpdateAssumeRolePolicy'
    AND eventtime > '2026-06-01'
ORDER BY eventtime DESC;
```

This is one to watch closely. Trust policy changes can be a sign of [privilege escalation](/posts/aws-detecting-privilege-escalation/).

### Failed API Calls (Access Denied Patterns)

A burst of `AccessDenied` errors from a single principal often means someone is probing for permissions:

```sql
SELECT
    useridentity.arn AS who,
    COUNT(*) AS denied_count,
    array_agg(DISTINCT eventname) AS actions_attempted
FROM cloudtrail_logs
WHERE errorcode = 'AccessDenied'
    AND eventtime > '2026-07-01'
GROUP BY useridentity.arn
ORDER BY denied_count DESC
LIMIT 20;
```

This is where compliance forensics starts bleeding into security investigation. A developer testing permissions looks different from an attacker enumerating them — but the CloudTrail events are the same. Context matters.

---

## CloudWatch Insights for Quick Searches

If your CloudTrail logs are also flowing to CloudWatch Logs, you can use Insights for faster ad-hoc queries without setting up Athena:

```
fields @timestamp, userIdentity.arn, eventName, sourceIPAddress
| filter eventName = "AuthorizeSecurityGroupIngress"
| filter requestParameters like "0.0.0.0/0"
| sort @timestamp desc
| limit 50
```

CloudWatch Insights is faster for one-off lookups. Athena is better for deep dives across large time ranges.

---

## Building Proactive Alerts

Investigations are reactive by definition — something already happened. The real leverage is catching things as they happen.

Set up EventBridge rules for the API calls you care about most:

```json
{
  "source": ["aws.ec2"],
  "detail-type": ["AWS API Call via CloudTrail"],
  "detail": {
    "eventName": ["AuthorizeSecurityGroupIngress"],
    "requestParameters": {
      "ipPermissions": {
        "items": {
          "ipRanges": {
            "items": {
              "cidrIp": ["0.0.0.0/0"]
            }
          }
        }
      }
    }
  }
}
```

Route these to an SNS topic, a Lambda function, or directly to Slack. Now you know about the open security group in minutes, not days.

The events worth alerting on, in order of priority:
1. **`StopLogging` / `DeleteTrail`** — someone trying to disable your audit trail
2. **`ConsoleLogin` without MFA** — especially for IAM users (see [detecting root account usage](/posts/detect-root-account-usage/))
3. **`AuthorizeSecurityGroupIngress` with `0.0.0.0/0`** — open to the world
4. **`AttachUserPolicy` / `AttachRolePolicy` with `AdministratorAccess`** — admin escalation
5. **`CreateAccessKey`** — new long-term credentials being created

If you're already running [GuardDuty](/posts/aws-guardduty-setup/), it covers some of these patterns automatically. But GuardDuty uses ML-based detection with its own alerting timeline. EventBridge rules give you deterministic, instant alerts for specific actions you've decided are never acceptable.

---

## From Compliance to Incident Response

Everything above covers the 95% use case: tracing internal activity for compliance. But the same skills and queries apply when things get serious.

When you're investigating an actual security incident — compromised credentials, unauthorized access, data exfiltration — CloudTrail is your primary evidence source. The difference is scope and urgency:

- **Compliance**: "Who created this non-compliant resource?" — you have days.
- **Incident response**: "What did this compromised role do across all accounts in the last 4 hours?" — you have minutes.

The queries are fundamentally the same. What changes is that you're filtering by a specific principal ARN or access key across your entire organization trail, looking for every action they took.

I'll cover a real incident investigation workflow in an upcoming post — including reverse-engineering indicators of compromise from CloudTrail when a phishing campaign went sideways. The foundation you build here is exactly what you'll need when that day comes.

---

## Quick Reference

| Investigation | Key Event Names | Where to Query |
|---|---|---|
| Who created a security group? | `CreateSecurityGroup`, `AuthorizeSecurityGroupIngress` | Athena or CloudWatch Insights |
| Who created an IAM user? | `CreateUser`, `AttachUserPolicy` | Athena |
| Who launched instances? | `RunInstances` | Athena |
| Who changed a trust policy? | `UpdateAssumeRolePolicy` | Athena |
| Permission probing | `errorcode = 'AccessDenied'` | Athena (aggregation) |
| Real-time alerts | Any event | EventBridge + SNS/Lambda |

---

## Related Resources

- [Detecting Privilege Escalation in AWS with CloudTrail and EventBridge](/posts/aws-detecting-privilege-escalation/) — automated detection for IAM escalation patterns
- [Amazon GuardDuty Setup Guide](/posts/aws-guardduty-setup/) — ML-based threat detection that complements manual CloudTrail analysis
- [How to Detect Root Account Usage](/posts/detect-root-account-usage/) — alerting on the most sensitive IAM events
- [AWS SCPs That Actually Work](/posts/aws-scp-best-practices/) — prevent the non-compliant actions before they reach CloudTrail
- [IAM Users Are Dead](/posts/aws-iam-users-alternatives/) — why the `CreateUser` query above should eventually return zero results
