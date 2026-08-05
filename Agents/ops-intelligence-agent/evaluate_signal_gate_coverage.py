from runbook_rag import (
    expand_query_for_retrieval,
    has_operational_problem_signal,
    normalize_operational_signals,
)


TEST_CASES = [
    {
        "name": "http_504_gateway_timeout",
        "query": "checkout HTTP 504 gateway timeout",
        "expected": True,
        "why": "504 gateway timeout is an operational failure signal.",
    },
    {
        "name": "rds_max_connections_reached",
        "query": "RDS max database connections reached",
        "expected": True,
        "why": "Database max connections reached is an operational database incident.",
    },
    {
        "name": "database_connections_exhausted",
        "query": "database connections exhausted",
        "expected": True,
        "why": "Exhausted database connections should pass the gate.",
    },
    {
        "name": "api_latency_high",
        "query": "API latency high",
        "expected": True,
        "why": "High latency is an operational performance issue.",
    },
    {
        "name": "access_denied_deployment",
        "query": "AccessDenied on deployment",
        "expected": True,
        "why": "Access denied during deployment is an operational failure.",
    },
    {
        "name": "dynamodb_requests_throttled_traffic",
        "query": "DynamoDB requests are being throttled after traffic increased.",
        "expected": True,
        "why": "Actively throttled requests are an operational incident.",
    },
    {
        "name": "dynamodb_requests_throttled_deployment",
        "query": "DynamoDB requests are being throttled after deployment.",
        "expected": True,
        "why": "Actively throttled requests after a deployment should pass the gate.",
    },
    {
        "name": "dynamodb_requests_not_throttled",
        "query": "DynamoDB requests are not being throttled after deployment.",
        "expected": False,
        "why": "A negated throttling condition is not an active incident.",
    },
    {
        "name": "dynamodb_throttling_documentation",
        "query": "Reviewing documentation about DynamoDB requests being throttled.",
        "expected": False,
        "why": "Informational text about throttling is not an active incident.",
    },
    {
        "name": "team_connection_meeting",
        "query": "team connection meeting",
        "expected": False,
        "why": "Connection here is social wording, not an incident.",
    },
    {
        "name": "database_design_discussion",
        "query": "database design discussion",
        "expected": False,
        "why": "Database alone is not enough to indicate an incident.",
    },
    {
        "name": "http_documentation_review",
        "query": "HTTP documentation review",
        "expected": False,
        "why": "HTTP alone is not an incident.",
    },
    {
        "name": "certificate_training_notes",
        "query": "certificate training notes",
        "expected": False,
        "why": "Certificate alone is not enough to indicate an incident.",
    },
    {
        "name": "lambda_ok",
        "query": "lambda ok",
        "expected": False,
        "why": "Normal status text should not enter retrieval.",
    },
    {
    "name": "healthy_redis_latency",
    "query": (
        "Redis cache is healthy; no requests are timing out, "
        "and latency is normal."
    ),
    "expected": False,
    "why": "Healthy and locally normalized signals must not enter retrieval.",
},
{
    "name": "healthy_latency_with_active_504",
    "query": (
        "Redis latency is normal, but checkout requests return HTTP 504."
    ),
    "expected": True,
    "why": "A healthy latency signal must not hide an independent 504 incident.",
},
{
    "name": "healthy_api_error_rate",
    "query": (
        "API error rate is normal, latency remains stable, "
        "and no requests are failing."
    ),
    "expected": False,
    "why": "Normal error rate and stable latency do not describe an incident.",
},
]


passes = 0
false_negatives = 0
false_positives = 0

for case in TEST_CASES:
    expanded = expand_query_for_retrieval(case["query"])
    normalized = normalize_operational_signals(expanded)
    actual = has_operational_problem_signal(normalized)
    passed = actual == case["expected"]
    if passed:
        passes += 1
    elif case["expected"]:
        false_negatives += 1
    else:
        false_positives += 1

    print(f"\n{'PASS' if passed else 'FAIL'} {case['name']}")
    print(f"Query: {case['query']}")
    if expanded != case["query"]:
        print(f"Expanded: {expanded}")
    if normalized != expanded:
        print(f"Normalized: {normalized}")
    print(f"Expected gate: {'pass' if case['expected'] else 'reject'}")
    print(f"Actual gate: {'pass' if actual else 'reject'}")
    print(f"Why: {case['why']}")

print("\nSummary")
print(f"Cases: {len(TEST_CASES)}")
print(f"Correct: {passes}/{len(TEST_CASES)}")
print(f"False negatives: {false_negatives}")
print(f"False positives: {false_positives}")
print(
    "Meaning: improve recall for real incidents without allowing broad words "
    "like connection, database, HTTP, or certificate to pass alone."
)
