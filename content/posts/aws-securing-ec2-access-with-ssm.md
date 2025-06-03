---
title: "Securing EC2 Access with AWS Systems Manager Session Manager: Eliminating SSH"
date: 2025-06-03
description: "A comprehensive guide to replacing SSH access with AWS Systems Manager Session Manager for EC2 instances, enhancing security and compliance."
tags: ["AWS", "EC2", "Security", "Session Manager", "SSM", "IAM", "Cloud Security"]
canonicalURL: "https://thehiddenport.dev/securing-ec2-access-with-ssm"
---

## Introduction

Traditional SSH access to EC2 instances poses several security challenges, including the management of SSH keys, exposure of ports, and lack of centralized auditing. AWS Systems Manager Session Manager offers a secure and auditable alternative, allowing you to manage EC2 instances without opening inbound ports or maintaining bastion hosts.

This guide provides a step-by-step approach to configuring Session Manager for secure EC2 access, aligning with AWS's official documentation and best practices.

## Prerequisites

Before proceeding, ensure the following:

* **SSM Agent Installed**: Amazon EC2 instances must have the SSM Agent installed. Amazon Linux 2 and Ubuntu 16.04 or later come with the agent pre-installed. For other operating systems, refer to the [SSM Agent installation guide](https://docs.aws.amazon.com/systems-manager/latest/userguide/ssm-agent.html).

* **IAM Role with SSM Permissions**: Instances require an IAM role with the `AmazonSSMManagedInstanceCore` policy attached. This policy grants the necessary permissions for Systems Manager to manage the instance.

* **Outbound Internet Access or VPC Endpoints**: Instances must be able to communicate with Systems Manager endpoints. This can be achieved via outbound internet access (e.g., through a NAT gateway) or by configuring [VPC endpoints for Systems Manager](https://docs.aws.amazon.com/systems-manager/latest/userguide/setup-create-vpc.html).

## Step 1: Create an IAM Role for SSM

1. Navigate to the [IAM Console](https://console.aws.amazon.com/iam/).

2. Select **Roles** > **Create role**.

3. Choose **AWS service** as the trusted entity and select **EC2**.

4. Click **Next: Permissions**.

5. Attach the **AmazonSSMManagedInstanceCore** policy.

6. Proceed through the remaining steps to name and create the role.

## Step 2: Attach the IAM Role to EC2 Instances

1. Open the [EC2 Console](https://console.aws.amazon.com/ec2/).

2. Select the instance(s) you wish to manage.

3. Choose **Actions** > **Security** > **Modify IAM Role**.

4. Select the IAM role created in Step 1 and apply the changes.

## Step 3: Verify SSM Agent Status

Ensure the SSM Agent is running on your instance:

```bash
sudo systemctl status amazon-ssm-agent
```

If the agent is not running, start it with:

```bash
sudo systemctl start amazon-ssm-agent
```

## Step 4: Connect to the Instance Using Session Manager

With the IAM role attached and the SSM Agent running, you can initiate a session:

### Using AWS Console

1. Navigate to the [Systems Manager Console](https://console.aws.amazon.com/systems-manager/).

2. Select **Session Manager** > **Start session**.

3. Choose the instance and click **Start session**.

### Using AWS CLI

Ensure you have the [Session Manager plugin](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html) installed.

Initiate a session with:

```bash
aws ssm start-session --target i-0123456789abcdef0
```

Replace `i-0123456789abcdef0` with your instance ID.

## Step 5: Enhance Security by Disabling SSH Access

After verifying that Session Manager access works as intended, you can enhance security by disabling SSH access:

* **Security Groups**: Remove inbound rules for port 22.

* **Key Pairs**: Avoid assigning key pairs to instances.

* **Bastion Hosts**: Decommission any bastion hosts used for SSH access.

This approach reduces the attack surface and aligns with the principle of least privilege.

## Step 6: Configure Logging for Auditing

To maintain an audit trail of session activity:

1. In the Systems Manager Console, navigate to **Session Manager** > **Preferences**.

2. Click **Edit** and enable logging.

3. Choose to send session logs to Amazon S3 and/or Amazon CloudWatch Logs.

This configuration ensures that all session activity is recorded for compliance and auditing purposes.

Absolutely! Let's enhance your article by adding two comprehensive sections: **Common Issues and Troubleshooting** and **Monitoring SSM Agent with CloudWatch**. These additions will provide readers with practical insights into potential pitfalls and proactive monitoring strategies.

---

## Common Issues and Troubleshooting

While AWS Systems Manager Session Manager offers a secure and efficient method for managing EC2 instances, users may encounter certain challenges during setup or operation. Below are some common issues and their resolutions:

### 1. **Instance Not Appearing in Session Manager**

**Issue**: The EC2 instance does not appear in the Session Manager console.

**Possible Causes and Solutions**:

* **SSM Agent Not Installed or Running**: Ensure that the SSM Agent is installed and actively running on the instance. For Amazon Linux 2 and Ubuntu 16.04 or later, the agent is pre-installed. For other operating systems, refer to the [SSM Agent installation guide](https://docs.aws.amazon.com/systems-manager/latest/userguide/ssm-agent.html).

* **Missing IAM Role or Incorrect Permissions**: Verify that the instance has an IAM role attached with the `AmazonSSMManagedInstanceCore` policy. This policy grants the necessary permissions for Systems Manager to manage the instance.

* **Network Connectivity Issues**: The instance must be able to communicate with Systems Manager endpoints. Ensure that the instance has outbound internet access or is configured with the appropriate VPC endpoints for Systems Manager.

### 2. **Session Initiation Fails**

**Issue**: Attempting to start a session results in an error.

**Possible Causes and Solutions**:

* **SSM Agent Version Incompatibility**: Ensure that the SSM Agent is updated to the latest version. Older versions may lack support for certain features or have known issues.

* **Session Manager Plugin Missing**: When using the AWS CLI, the Session Manager plugin must be installed. Follow the [installation instructions](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-install-plugin.html) to set it up.

* **IAM User Permissions**: The IAM user initiating the session must have the necessary permissions, such as `ssm:StartSession`. Review and update IAM policies as needed.

### 3. **SSM Agent Connectivity Issues**

**Issue**: The SSM Agent cannot connect to Systems Manager endpoints.

**Possible Causes and Solutions**:

* **Firewall or Security Group Restrictions**: Ensure that the instance's security groups and network ACLs allow outbound HTTPS (port 443) traffic to Systems Manager endpoints.

* **DNS Resolution Problems**: Verify that the instance can resolve domain names. Misconfigured DNS settings can prevent the agent from reaching AWS services.

* **Endpoint Configuration**: If using VPC endpoints, confirm that they are correctly configured and associated with the appropriate route tables and security groups.

For a comprehensive troubleshooting guide, refer to the [AWS Systems Manager Troubleshooting Documentation](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-troubleshooting.html).

---

## Monitoring SSM Agent with CloudWatch

Proactive monitoring of the SSM Agent ensures that you are promptly alerted to any issues, maintaining the reliability and security of your EC2 instances. Here's how to set up monitoring using Amazon CloudWatch:

### 1. **Send SSM Agent Logs to CloudWatch Logs**

**Steps**:

1. **Create a CloudWatch Log Group**: In the CloudWatch console, create a log group to store SSM Agent logs.

2. **Configure the SSM Agent to Send Logs**: Modify the SSM Agent configuration to send logs to the newly created log group. This can be done by editing the agent's configuration file or using Systems Manager Run Command.

3. **Restart the SSM Agent**: After configuration, restart the SSM Agent to apply changes.

For detailed instructions, consult the [AWS Systems Manager Monitoring Guide](https://docs.aws.amazon.com/systems-manager/latest/userguide/monitoring.html).

### 2. **Create Metric Filters and Alarms**

**Steps**:

1. **Define Metric Filters**: In the CloudWatch console, create metric filters to identify specific log events, such as agent start or stop events. For example, to detect when the agent stops:

   ```
   filter pattern: "Stopping ssm agent worker"
   ```

2. **Create Alarms**: Based on the metric filters, set up alarms to notify you when certain thresholds are met. For instance, if the agent stops unexpectedly, an alarm can trigger an SNS notification.

3. **Subscribe to Notifications**: Ensure that relevant personnel are subscribed to the SNS topic to receive timely alerts.

For a practical example and additional guidance, refer to the AWS blog post on [Monitoring the Health of AWS Systems Manager Agent Using Amazon CloudWatch](https://aws.amazon.com/blogs/mt/monitor-health-aws-systems-manager-agent-using-amazon-cloudwatch/).


## Additional Considerations

* **User Permissions**: Control who can start sessions by defining IAM policies that grant `ssm:StartSession` permissions to specific users or roles.

* **Port Forwarding**: Session Manager supports port forwarding, allowing secure access to applications running on instances without opening additional ports.

* **Hybrid Environments**: Session Manager can manage on-premises servers and virtual machines by registering them as managed instances.

## Conclusion

By leveraging AWS Systems Manager Session Manager, you can eliminate the need for SSH access to EC2 instances, thereby enhancing security, simplifying access management, and ensuring comprehensive auditing. This approach aligns with AWS's best practices for secure and compliant infrastructure management.

---

*For further reading on IAM misconfigurations and security risks, refer to my previous article: [AWS IAM Misconfigurations: Security Risks and How to Fix Them](../aws-security-misconfigurations-guide).*

*To explore incident response strategies in AWS, check out: [Incident Response in AWS: A Practical Playbook](../incident-response-aws-guide).*

*For tools to automate incident response, visit: [AWS Incident Response Toolkit](../aws-ir-toolkit).*

*Learn about securing temporary AWS credentials here: [Securing Temporary AWS Credentials with STS](../aws-temporary-credentials-security).*

---