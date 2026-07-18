import re

from runbook_rag import normalize_operational_signals


INCIDENT_PROFILES = {
    "http-504-gateway-timeout.md": {
        "family_signals": ("alb", "load balancer", "gateway"),
        "category_signals": ("504", "gateway timeout", "upstream timeout"),
        "distinctive_category": True,
        "clarifying_question": "Is the gateway returning HTTP 504, HTTP 502, or another status code?",
    },
    "alb-502-health-checks.md": {
        "family_signals": ("alb", "load balancer", "gateway", "checkout"),
        "category_signals": ("502", "bad gateway", "health check", "unhealthy"),
        "distinctive_category": True,
        "clarifying_question": "What HTTP status code and target health-check result are reported?",
    },
    "kubernetes-oomkill.md": {
        "family_signals": ("kubernetes", "pod", "container"),
        "category_signals": (
            "oomkilled",
            "oom killed",
            "out of memory",
            "memory limit",
            "memory killed",
        ),
        "distinctive_category": True,
        "clarifying_question": "What termination reason, exit code, or pod event is reported?",
    },
    "lambda-timeout.md": {
        "family_signals": ("lambda",),
        "category_signals": ("timeout",),
        "distinctive_category": False,
        "clarifying_question": "Which Lambda function failed, and did it time out or fail for another reason?",
    },
    "rds-connection-pool.md": {
        "family_signals": ("rds", "database", "db"),
        "category_signals": (
            "max connections",
            "maxed connections",
            "connections reached",
            "connection pool",
            "connections exhausted",
        ),
        "distinctive_category": False,
        "clarifying_question": "Is the database reaching its maximum connection or pool limit?",
    },
    "ssl-certificate-expiry.md": {
        "family_signals": ("certificate", "ssl", "tls"),
        "category_signals": ("expiry", "expired", "expires", "expiring", "renewal"),
        "distinctive_category": False,
        "clarifying_question": "Is the certificate expired, expiring, untrusted, or failing hostname validation?",
    },
    "api-cpu-saturation.md": {
        "family_signals": ("api", "server", "compute"),
        "category_signals": ("cpu", "saturation", "slow", "latency", "95 percent"),
        "distinctive_category": False,
        "clarifying_question": "Is the API slow because CPU is saturated, or is another dependency failing?",
    },
    "iam-accessdenied.md": {
        "family_signals": ("iam", "permission", "policy", "role"),
        "category_signals": (
            "accessdenied",
            "access denied",
            "unauthorizedoperation",
            "permission denied",
        ),
        "distinctive_category": True,
        "clarifying_question": "What denied action, resource, and principal appear in the error?",
    },
}

NEGATION_PATTERN = re.compile(
    r"\b(?:no|not|never|without)\b(?:\W+\w+){0,3}\W*$",
    flags=re.IGNORECASE,
)


def is_signal_negated(text, signal_start):
    prefix = text[max(0, signal_start - 60) : signal_start]
    return bool(NEGATION_PATTERN.search(prefix))


def contains_signal(text, signal):
    pattern = rf"(?<![a-z0-9]){re.escape(signal)}(?![a-z0-9])"

    for match in re.finditer(pattern, text, flags=re.IGNORECASE):
        if not is_signal_negated(text, match.start()):
            return True

    return False


def matching_signals(query, signals):
    return [signal for signal in signals if contains_signal(query, signal)]


def assess_evidence(query, candidates):
    normalized_query = normalize_operational_signals(query).lower()
    family_aligned = []
    valid_matches = {}

    for candidate in candidates:
        profile = INCIDENT_PROFILES.get(candidate["source"])
        if not profile:
            continue

        family_matches = matching_signals(
            normalized_query,
            profile["family_signals"],
        )
        category_matches = matching_signals(
            normalized_query,
            profile["category_signals"],
        )

        if family_matches:
            family_aligned.append((candidate, profile, family_matches))

        category_is_sufficient = bool(category_matches) and (
            profile["distinctive_category"] or bool(family_matches)
        )
        if not category_is_sufficient:
            continue

        accepted_source = candidate["source"]
        valid_matches.setdefault(accepted_source, set()).update(
            category_matches
        )

    if len(valid_matches) > 1:
        conflicting_sources = sorted(valid_matches)
        return {
            "decision": "clarify",
            "reason": (
                "Multiple supported incident categories align: "
                f"{', '.join(conflicting_sources)}"
            ),
            "clarifying_question": (
                "Multiple incident signals were detected. Which error occurred "
                "first, and are they part of the same failure?"
            ),
            "evidence": [],
            "raw_candidates": candidates,
        }

    if len(valid_matches) == 1:
        accepted_source, category_matches = next(iter(valid_matches.items()))
        accepted_evidence = [
            result for result in candidates if result["source"] == accepted_source
        ]
        return {
            "decision": "accept",
            "reason": (
                f"Incident signals align with {accepted_source}: "
                f"{', '.join(sorted(category_matches))}"
            ),
            "clarifying_question": None,
            "evidence": accepted_evidence,
            "raw_candidates": candidates,
        }

    if family_aligned:
        candidate, profile, family_matches = family_aligned[0]
        return {
            "decision": "clarify",
            "reason": (
                f"The query matches the {candidate['source']} incident family "
                f"through {', '.join(family_matches)}, but not its problem category."
            ),
            "clarifying_question": profile["clarifying_question"],
            "evidence": [],
            "raw_candidates": candidates,
        }

    return {
        "decision": "no_coverage",
        "reason": "No retrieved runbook aligns with a supported incident family and category.",
        "clarifying_question": None,
        "evidence": [],
        "raw_candidates": candidates,
    }
