+++
platform = "kubernetes"
category = "memory"
+++

# Kubernetes OOMKilled Pod Runbook

## Symptoms

- Pod enters CrashLoopBackOff.
- Container termination reason is OOMKilled.
- Restart count increases repeatedly in a short time window.

## Probable Causes

- Memory limit below the workload's real peak usage.
- Memory leak introduced by a recent deployment.
- Sudden traffic increase or expensive request path.

## Immediate Actions

- Check pod events, memory usage trend, deployment time, and recent config changes.
- Compare memory limit with previous stable versions.
- Roll back or raise memory limit only after confirming the pressure pattern.

## Safety Notes

- Do not keep deleting the pod without understanding why memory rises again.
- Treat repeated OOMKills on auth or payment services as high urgency.
