# ALB 502 and Health Check Runbook

## Symptoms

- Load balancer returns increasing 502 responses.
- One or more targets fail health checks.
- Only part of the target group may be unhealthy.

## Probable Causes

- Application instances are overloaded or crashing.
- Upstream service dependency is failing.
- Health check path changed or no longer responds correctly.

## Immediate Actions

- Check unhealthy targets, target response codes, and recent deployments.
- Drain unhealthy instances if enough healthy capacity remains.
- Review application logs for startup failures, dependency errors, or port mismatch.

## Safety Notes

- Do not remove too many targets at once.
- Confirm remaining capacity before draining or restarting instances.
