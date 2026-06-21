from runbook_rag import (
    has_operational_problem_signal,
    normalize_operational_signals,
)


TEST_CASES = [
    ("lambda timeout repeatedly", True),
    ("lambda timed out repeatedly", True),
    ("lambda timing out repeatedly", True),
    ("lambda time out repeatedly", True),
    ("lambda times out repeatedly", True),
    ("lambda timed-out repeatedly", True),
    ("lambda acting weird", False),
    ("lambda strange today", False),
    ("lambda operating normally", False),
    ("employee password reset request", False),
]


passed = 0
for query, expected in TEST_CASES:
    normalized = normalize_operational_signals(query)
    actual = has_operational_problem_signal(query)
    is_correct = actual == expected
    if is_correct:
        passed += 1

    print(f"\n{'PASS' if is_correct else 'FAIL'}")
    print(f"Query: {query}")
    print(f"Normalized: {normalized}")
    print(f"Expected gate: {'pass' if expected else 'reject'}")
    print(f"Actual gate: {'pass' if actual else 'reject'}")

print()
print("Summary")
print(f"Signal gate cases: {passed}/{len(TEST_CASES)}")
