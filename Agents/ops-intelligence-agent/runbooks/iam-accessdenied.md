+++
platform = "aws-iam"
category = "access-denied"
+++

# IAM AccessDenied Runbook

## Symptoms

- Service requests fail with AccessDenied, UnauthorizedOperation, or permission denied errors.
- Failures begin after a deployment, policy change, role rotation, or secret/config update.
- Only specific actions, resources, or environments may be affected.

## Probable Causes

- IAM role, service account, or execution policy is missing a required permission.
- Deployment changed the role ARN, resource ARN, region, or account boundary.
- Resource policy, KMS key policy, bucket policy, or secret policy denies access.

## Immediate Actions

- Identify the denied action, resource ARN, principal, account, and region from logs.
- Compare the deployed role and policy with the last known working version.
- Roll back the policy or deployment only after confirming the denied permission path.

## Safety Notes

- Do not add broad wildcard permissions just to clear the alert.
- Prefer the smallest permission change that restores the failing action.
- Check audit logs before assuming the application code is at fault.
