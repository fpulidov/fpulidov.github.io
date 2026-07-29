---
title: "IDOR in AWS APIs: Real Examples from Bug Bounty & How to Fix Them"
description: "One hunter reported 220 IDOR finds in a single year. Here's how insecure direct object references show up in Lambda, API Gateway, and DynamoDB — with prevention code."
summary: "Deep dive into IDOR vulnerabilities with real AWS API examples, bug bounty cases, and prevention strategies for Lambda, API Gateway, and internal tooling."
date: 2025-06-27
tags: ["Bug Bounty", "Security", "Web", "AWS", "API", "IDOR"]
keywords: ["idor vulnerability aws", "idor bug bounty", "insecure direct object reference", "aws api security", "idor prevention", "broken access control aws", "aws lambda idor", "api gateway authorization bypass"]
categories: ["Cloud Security"]
canonicalURL: "https://thehiddenport.dev/posts/aws-preventing-idor/"
lastmod: 2026-07-29
enable_comments: true
---

In bug bounty and pentesting, **IDOR (Insecure Direct Object Reference)** remains one of the most frequent and dangerous vulnerabilities—even today. OWASP defines it as a classic **Broken Access Control** issue, overwhelming APIs that use predictable or guessable object identifiers ([cheatsheetseries.owasp.org](https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html )). But its real impact goes beyond HTTP—IDOR can silently appear in **AWS APIs**, Lambda functions, and internal tooling. This post examines how that happens, how bounty hunters find them, and how AWS developers can prevent and detect IDOR effectively.

---

## What Is IDOR?

IDOR occurs when an application uses **user-supplied identifiers** (in URL, body, header, or cookie) to reference internal objects *without verifying ownership or permissions*. It comes in flavors:

- **URL tampering**: Changing `GET /orders?id=1234` to `id=1235` to access someone else’s order.
- **Body tampering**: Modifying JSON body in POST/PUT to point at unauthorized user ids.
- **Header/cookie manipulation**: Modifying session tokens or headers like `X-User-ID`.
- **Path traversal cases**: IDOR via file paths or uploaded object references.

Despite best practices, IDOR stays frequent. One bug-hunter reported ~220 IDOR finds out of 650 bounties in a year ([reddit.com](https://www.reddit.com/r/cybersecurity/comments/15y5f56 )).

---

## AWS API IDOR: A Bug Bounty Sweet Spot

On AWS, IDOR may “live” in:

1. **Custom APIs backed by DynamoDB or S3**  
   - Example: `GET /user-files?fileId=123` without checking if current user owns `fileId`  
   - Dynamo allows querying without owner checks—easy to exploit

2. **Internal tooling** using AWS SDK  
   - Unpublished endpoints with `objectKey` or `roleArn` parameters, similar vulnerability

3. **Metadata abuse scenarios**  
   - A Lambda calling `iam.getUser({UserName: input})` without proper validation

---

### Sample IDOR Scenario in AWS

```http
POST /internal/api/lambda/invoke
{
  "functionName": "user-lambdas-arn",
  "payload": { "userId": "1234", "action": "listSecrets" }
}
```

If backend doesn’t check the authenticated Lambda’s permissions before calling AWS APIs like `ListSecrets`, an attacker could escalate privileges. Many abused internal lambdas share this pattern.

---

## Why IDOR Is Dangerous in AWS Environments

In AWS, IDOR can lead to elevated risk beyond stolen data:

| Risk | Description |
|------|-------------|
| **Cross-account leakage** | Exfiltrate data from other AWS accounts |
| **AssumeRole abuse** | Use vulnerable APIs to call `sts:AssumeRole({RoleArn:...})` |
| **Privilege escalation** | Access unauthorized secrets, functions, roles |
| **Large-scale enumeration** | Automate API calls to enumerate S3, DB, IAM |

With AWS’s "programmatic everything" model, these bugs can scale to severe breaches, as multiple researchers have demonstrated ([comolho.com](https://www.comolho.com/post/hijacking-the-cloud-an-aws-takeover-and-rce-taleat-xyz-company )).

---

## Hunting IDOR in AWS APIs

### 1. **Inventory APIs & Parameters**

Map out all internal APIs—Lambda proxies, API Gateway, custom services—and identify params like `userId`, `resourceId`, `fileKey`, `orderId`.

### 2. **Test for direct object access**

Send requests with someone else’s known identifiers (e.g., `?id=1`). Erroneous access or HTTP 200 for wrong objects? Found IDOR.

### 3. **Automate enumeration**

With tools like **ffuf** or **burp intruder**, fuzz `resourceId`: `1000–1010`, or test for UUID formats. Look for differences in responses.

### 4. **Monitor enumeration attempts**

If APIs log every `SELECT * WHERE id = ?`, watch CloudWatch Logs for weird 404 patterns—indicates enumeration.

### 5. **Review IAM permissions**

Check if callers are authorized to access underlying resources (Dynamo, S3). If object access relies solely on client-sent IDs, it’s likely vulnerable.

---

## Preventing IDOR in AWS

Best practices aligned with OWASP guidance include ([cheatsheetseries.owasp.org](https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html )):

1. **Always verify object ownership in code**:
   ```js
   const item = await dynamo.get({Key:{userId: currentUser, objectId: inputId}});
   if (!item) throw new Error("Not found");
   ```

2. **Use indirect references** for public APIs  
   - Generate UUIDs or random keys instead of sequential integers, but access control is non-negotiable.

3. **Scope AWS permissions appropriately**  
   - Avoid `Resource: "*"`. Use fine-grained `Condition` blocks (e.g., `dynamodb:LeadingKeys` set to `${aws:userid}`).

4. **Rate-limit and detect enumeration**  
   - CloudFront or WAF rules can throttle suspicious enumeration patterns.

5. **Log everything**  
   - Emit structured logs to CloudWatch, alert on spikes of unauthorized requests or repeated access attempts.

---

## Detection & Alerting Strategy

### CloudWatch Logs Insights for Enumeration Detection

API Gateway access logs capture every request with status code and caller identity. Use CloudWatch Logs Insights to detect enumeration patterns:

```sql
fields @timestamp, httpMethod, resourcePath, status, ip
| filter status in [403, 404]
| stats count(*) as errorCount by ip, bin(5m) as window
| filter errorCount > 20
| sort errorCount desc
```

This catches a single IP generating >20 unauthorized or not-found responses in 5 minutes — the signature of someone enumerating object IDs.

### CloudWatch Metric Filter + Alarm

Create a metric filter on your API Gateway access logs that increments on `403` or `404` status codes, then attach a CloudWatch Alarm that fires when the error rate spikes:

```json
{
  "filterPattern": "[ip, user, timestamp, request, status = 403 || status = 404, size, referer, agent]",
  "metricTransformations": [{
    "metricName": "IDOREnumerationAttempts",
    "metricNamespace": "APIGateway/Security",
    "metricValue": "1"
  }]
}
```

Set the alarm threshold based on your normal traffic — for most internal APIs, >50 4xx responses in 5 minutes from a single source warrants investigation.

---

## Putting It All Together: A Hardened API Pattern

Here's what a properly defended API Gateway → Lambda → DynamoDB path looks like — and why each layer matters:

**Application layer (Lambda):** Every read or write operation includes the authenticated `userId` as a partition key condition. The caller can send whatever `objectId` they want — if they don't own it, DynamoDB returns nothing.

```js
const result = await dynamo.get({
  TableName: "user-documents",
  Key: { userId: event.requestContext.authorizer.claims.sub, objectId: event.pathParameters.id }
});
if (!result.Item) return { statusCode: 404, body: "Not found" };
```

**IAM layer:** The Lambda execution role restricts DynamoDB access to items matching the caller's identity using a condition key — defense in depth even if the application logic has a bug:

```json
{
  "Effect": "Allow",
  "Action": ["dynamodb:GetItem", "dynamodb:Query"],
  "Resource": "arn:aws:dynamodb:*:*:table/user-documents",
  "Condition": {
    "ForAllValues:StringEquals": {
      "dynamodb:LeadingKeys": "${aws:userid}"
    }
  }
}
```

**Network layer:** WAF rate-limits to 50 requests/minute per IP on internal endpoints. This won't stop a sophisticated attacker, but it slows automated enumeration enough for your alerts to fire.

**Observability layer:** CloudWatch metric filter on 403/404 spikes (described above) triggers a PagerDuty alert. CloudTrail captures every API Gateway invocation for forensic analysis.

The key principle: **object ownership checks in code, IAM conditions as a safety net, rate limiting as a speed bump, and logging to catch what slips through.**

---

## Why IDOR Still Wins in Bug Bounty

Despite being a well-known vulnerability, IDOR persists because of how teams actually build software:

- **Fast development cycles** — a new endpoint gets shipped in a sprint, the authorization check gets deferred to "next sprint," and nobody comes back for it.
- **False confidence in UUIDs** — teams assume that random identifiers are unfindable. They're not — UUIDs leak in URLs, API responses, browser history, and logs.
- **Lack of server-side enforcement** — frontend validation hides the ID field, but the API accepts whatever you send. Every IDOR is a server-side bug, never a client-side one.
- **Microservices trust boundaries** — internal service-to-service calls often skip authorization because "only our services call this endpoint." Until they don't.

---

## Related Reading

- [AWS Misconfigurations I Find in Every Security Audit](/posts/aws-security-misconfigurations-guide/) — the recurring findings across environments, including access control gaps
- [IAM Least Privilege: From Theory to Practice](/posts/aws-enforcing-least-privilege/) — how to scope permissions properly
- [Detecting Privilege Escalation in AWS](/posts/aws-detecting-privilege-escalation/) — EventBridge detection rules for suspicious API calls
- [AWS Security Checklist: 30-Minute Account Review](/posts/aws-security-checklist-2026/) — quick self-audit you can run today
