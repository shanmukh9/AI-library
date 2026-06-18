+++
platform = "aws-lambda"
category = "timeout"
+++

# Lambda Timeout Runbook

## Symptoms

- A Lambda function repeatedly reaches its timeout limit.
- Consecutive failures appear for the same function or event source.
- Downstream queues may show growing backlog.

## Probable Causes

- Downstream API or database latency.
- Function timeout set below realistic processing duration.
- Cold start, memory pressure, or oversized payloads.

## Immediate Actions

- Check recent deployment, duration metrics, error rate, and retry volume.
- Inspect downstream dependency latency before increasing timeout.
- Pause or throttle event source if retries are amplifying the incident.

## Safety Notes

- Increasing timeout without checking dependencies can hide the real issue.
- Avoid replaying failed events until the dependency is stable.
