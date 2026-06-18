+++
platform = "compute"
category = "cpu"
+++

# API CPU Saturation Runbook

## Symptoms

- CPU on an API server remains above 90 percent for several minutes.
- Response latency increases or request queues grow.
- Application logs may show slow endpoints, retry storms, or worker starvation.

## Probable Causes

- Traffic spike against one or more expensive endpoints.
- Inefficient loop, unbounded background job, or retry amplification.
- Instance count too low for current demand.

## Immediate Actions

- Check request rate, p95 latency, and top endpoints for the affected service.
- Scale out the API service if customer-facing latency or errors are increasing.
- Capture process-level CPU and thread metrics before restarting.

## Safety Notes

- Do not restart all instances at once.
- Prefer rolling mitigation and preserve diagnostic evidence before destructive action.
