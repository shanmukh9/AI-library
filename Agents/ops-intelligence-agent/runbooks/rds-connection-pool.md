+++
platform = "aws-rds"
category = "database"
+++

# RDS Connection Pool Exhaustion Runbook

## Symptoms

- Database max connections are reached.
- Application requests fail while waiting for available connections.
- Connection count remains high even when traffic is not unusually high.

## Probable Causes

- Application connection leak.
- Pool size too large across many replicas.
- Long-running queries holding connections.

## Immediate Actions

- Check active connections, long-running queries, and recent application deployments.
- Reduce excessive pool size or recycle leaking application workers carefully.
- Add read capacity only after confirming the bottleneck.

## Safety Notes

- Restarting the database is a last resort.
- Killing all connections can worsen customer impact if done without coordination.
