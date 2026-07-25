import json
from pathlib import Path


CASES_PATH = Path(__file__).resolve().parent / "evals" / "pipeline_cases.json"
VALID_SPLITS = {"development", "validation", "held_out"}
VALID_DECISIONS = {"no_incident", "accept", "clarify", "no_coverage"}
EXPECTED_FIELDS = {
    "retrieval_should_run": bool,
    "expected_candidate_sources": list,
    "decision": str,
    "accepted_sources": list,
    "llm_should_run": bool,
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_string_list(value, field, case_id):
    require(
        all(isinstance(item, str) and item for item in value),
        f"{case_id}: {field} must contain non-empty strings",
    )
    require(
        len(value) == len(set(value)),
        f"{case_id}: {field} must not contain duplicates",
    )


def validate_case(case, seen_ids):
    require(isinstance(case, dict), "Each pipeline case must be an object")
    case_id = case.get("id")
    require(isinstance(case_id, str) and case_id, "Case id must be a non-empty string")
    require(case_id not in seen_ids, f"Duplicate case id: {case_id}")
    seen_ids.add(case_id)

    require(case.get("split") in VALID_SPLITS, f"{case_id}: invalid split")
    require(
        isinstance(case.get("query"), str) and case["query"].strip(),
        f"{case_id}: query must be a non-empty string",
    )

    expected = case.get("expected")
    require(isinstance(expected, dict), f"{case_id}: expected must be an object")
    require(
        set(expected) == set(EXPECTED_FIELDS),
        f"{case_id}: expected fields must be {sorted(EXPECTED_FIELDS)}",
    )
    for field, expected_type in EXPECTED_FIELDS.items():
        require(
            type(expected[field]) is expected_type,
            f"{case_id}: {field} must be {expected_type.__name__}",
        )

    decision = expected["decision"]
    require(decision in VALID_DECISIONS, f"{case_id}: invalid decision {decision!r}")
    validate_string_list(
        expected["expected_candidate_sources"],
        "expected_candidate_sources",
        case_id,
    )
    validate_string_list(expected["accepted_sources"], "accepted_sources", case_id)

    retrieval_should_run = expected["retrieval_should_run"]
    accepted_sources = expected["accepted_sources"]
    llm_should_run = expected["llm_should_run"]

    if decision == "no_incident":
        require(not retrieval_should_run, f"{case_id}: no_incident must stop retrieval")
        require(
            not expected["expected_candidate_sources"],
            f"{case_id}: no_incident cannot expect retrieval candidates",
        )
    else:
        require(retrieval_should_run, f"{case_id}: {decision} requires retrieval")

    if decision == "accept":
        require(accepted_sources, f"{case_id}: accept requires accepted evidence")
        require(llm_should_run, f"{case_id}: accept must allow the LLM")
        require(
            set(accepted_sources).issubset(expected["expected_candidate_sources"]),
            f"{case_id}: accepted sources must first appear as candidates",
        )
    else:
        require(not accepted_sources, f"{case_id}: {decision} cannot accept evidence")
        require(not llm_should_run, f"{case_id}: {decision} must not call the LLM")


def load_and_validate_cases(path=CASES_PATH):
    cases = json.loads(path.read_text(encoding="utf-8"))
    require(isinstance(cases, list) and cases, "Pipeline cases must be a non-empty list")

    seen_ids = set()
    for case in cases:
        validate_case(case, seen_ids)
    return cases


if __name__ == "__main__":
    validated_cases = load_and_validate_cases()
    split_counts = {
        split: sum(case["split"] == split for case in validated_cases)
        for split in sorted(VALID_SPLITS)
    }

    print(f"Validated {len(validated_cases)} pipeline cases")
    print(
        "Splits: "
        + ", ".join(f"{split}={count}" for split, count in split_counts.items())
    )
    print("Data contract: PASS")
