+++
platform = "aws-alb"
category = "gateway-timeout"
+++

# HTTP 504 Gateway Timeout Runbook

## Symptoms

- Clients receive HTTP 504 gateway timeout responses.
- Load balancer or gateway waits too long for an upstream target response.
- Request duration rises before errors appear.

## Probable Causes

- Upstream service or dependency is too slow to respond.
- Target application threads or workers are saturated.
- Backend timeout settings are lower than real processing time.

## Immediate Actions

- Check target response time, request duration, and upstream dependency latency.
- Compare recent deployments, traffic spikes, and slow endpoint metrics.
- Scale or route around slow targets only after confirming capacity and dependency health.

## Safety Notes

- Do not treat 504 the same as 502 without checking response timing.
- Increasing timeouts can hide a slow dependency and delay recovery.
