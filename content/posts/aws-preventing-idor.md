---
title: "What Is IDOR? Finding and Preventing Insecure Direct Object References in AWS APIs"
description: "A technical deep-dive into IDOR vulnerabilities, real bug-bounty cases, AWS API examples, detection, prevention strategies, and how to secure your AWS services."
summary: "Learn what IDOR is, why it's so common (and dangerous), see real AWS-related examples, and discover prevention and detection methods for robust API security."
date: 2025-06-27
tags: ["Bug Bounty", "Security", "Web", "AWS", "API", "IDOR"]
canonicalURL: "https://thehiddenport.dev/posts/what-is-idor-aws-apis/"
enable_comments: true
---

# What Is IDOR? Finding and Preventing Insecure Direct Object References in AWS APIs

In bug bounty and pentesting, **IDOR (Insecure Direct Object Reference)** remains one of the most frequent and dangerous vulnerabilities—even today. OWASP defines it as a classic **Broken Access Control** issue, overwhelming APIs that use predictable or guessable object identifiers ([cheatsheetseries.owasp.org](https://cheatsheetseries.owasp.org/cheatsheets/Insecure_Direct_Object_Reference_Prevention_Cheat_Sheet.html )). But its real impact goes beyond HTTP—IDOR can silently appear in **AWS APIs**, Lambda functions, and internal tooling. This post examines how that happens, how bounty hunters find them, and how AWS developers can prevent and detect IDOR effectively.

---

# Personal Note

I'm currently starting my journey into bug bounty hunting. Given my background in AWS security, I realized there’s a natural overlap between the two worlds—especially when it comes to misconfigurations, permission boundaries, and API behavior. This article is my first step into exploring that intersection.

If you’re curious to follow along as I dive deeper into bug bounty topics—real findings, tooling, and mindset—stay tuned. More coming soon.


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

### Use CloudTrail + EventBridge for IDOR Detection

Any API returning 404 or 200 on unexpected IDs can trigger alerts:
```json
{
  "detail-type": ["API Call via CloudTrail"],
  "detail": {
    "eventSource": ["execute-api.amazonaws.com"],
    "httpStatus": ["200"],
    "requestParameters": {
      "resourceId": ["*"]
    }
  }
}
```
Then trigger SNS or Lambda to log suspicious enumeration.

### Log-based alerts in CloudWatch

Watch for:
- Many 404s within a minute
- Access to resources owned by a different AWS account or user

---

## Putting It All Together: A Hardened Example

- API Gateway → Lambda → DynamoDB access
- Lambda code strictly checks `userId` ownership
- IAM policy only allows access to items under `${aws:userid}`
- WAF blocks >50 requests/minute per IP to `/internal/api/`
- CloudTrail/CloudWatch logs feed into SIEM alerts for anomalies

---

## Why IDOR Still Wins in Bug Bounty

Despite being well-known, IDOR persists due to:

- **Fast development cycles**: devs quickly expose objects without validation.
- **False confidence in UUIDs**: obfuscation ≠ security.
- **Lack of server-side enforcement**: clients control identifiers, so attackers can enumerate.

---

## Related Reading

- [My full IAM least privilege guide](/posts/aws-enforcing-least-privilege/)
- [EventBridge detection for privilege escalation](/posts/aws-detecting-privilege-escalation/)
- [EC2 Hardening & AMI automation](/posts/aws-ec2-hardening/)

---

## Final Thoughts

IDOR is simple to understand—but complex to eliminate completely, especially in cloud environments. With thoughtful access control, logging, detection, and auditing, you can significantly reduce risk. For bug hunters, IDOR remains a low-hanging but impactful vulnerability, especially when combined with AWS APIs or internal tools.

Keep hunting, keep securing—and if you find an AWS-based IDOR, do share the example (anonymized) so the whole community learns with you.
```
