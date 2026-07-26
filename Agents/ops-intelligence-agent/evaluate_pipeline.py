import argparse

from evidence_acceptance import assess_evidence
from hybrid_retriever import hybrid_search_rrf, should_run_hybrid_retrieval
from validate_pipeline_cases import load_and_validate_cases


def evaluate_signal_gate(cases):
    results = []
    for case in cases:
        expected = case["expected"]["retrieval_should_run"]
        actual = should_run_hybrid_retrieval(case["query"])
        results.append(
            {
                "id": case["id"],
                "split": case["split"],
                "query": case["query"],
                "expected": expected,
                "actual": actual,
                "passed": actual == expected,
            }
        )
    return results


def summarize_signal_gate(results):
    total = len(results)
    correct = sum(result["passed"] for result in results)
    false_positives = sum(
        result["actual"] and not result["expected"] for result in results
    )
    false_negatives = sum(
        result["expected"] and not result["actual"] for result in results
    )
    return {
        "total": total,
        "correct": correct,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
    }


def print_signal_gate_results(results, summary):
    print("Signal Gate")
    for result in results:
        print(f"\n{'PASS' if result['passed'] else 'FAIL'} {result['id']}")
        print(f"Split: {result['split']}")
        print(f"Query: {result['query']}")
        print(f"Expected retrieval: {result['expected']}")
        print(f"Actual retrieval: {result['actual']}")

    print("\nSummary")
    print(f"Correct: {summary['correct']}/{summary['total']}")
    print(f"False positives: {summary['false_positives']}")
    print(f"False negatives: {summary['false_negatives']}")


def evaluate_retrieval(
    cases,
    signal_gate_results,
    top_k=3,
    candidate_k=5,
    ranking_mode="chunk",
):
    gate_results_by_id = {result["id"]: result for result in signal_gate_results}
    results = []

    for case in cases:
        required_sources = set(case["expected"]["expected_candidate_sources"])
        retrieval_ran = gate_results_by_id[case["id"]]["actual"]
        candidates = (
            hybrid_search_rrf(
                case["query"],
                top_k=top_k,
                candidate_k=candidate_k,
                ranking_mode=ranking_mode,
            )
            if retrieval_ran
            else []
        )
        actual_sources = list(
            dict.fromkeys(candidate["source"] for candidate in candidates)
        )
        found_required_sources = required_sources.intersection(actual_sources)
        missing_sources = required_sources.difference(actual_sources)
        irrelevant_sources = set(actual_sources).difference(required_sources)
        candidate_source_precision = (
            len(found_required_sources) / len(actual_sources)
            if required_sources and actual_sources
            else None
        )

        results.append(
            {
                "id": case["id"],
                "query": case["query"],
                "retrieval_ran": retrieval_ran,
                "candidates": candidates,
                "required_sources": sorted(required_sources),
                "actual_sources": actual_sources,
                "found_required_sources": sorted(found_required_sources),
                "missing_sources": sorted(missing_sources),
                "irrelevant_sources": sorted(irrelevant_sources),
                "candidate_source_precision": candidate_source_precision,
                "evaluated": bool(required_sources),
                "passed": not missing_sources if required_sources else None,
            }
        )
    return results


def summarize_retrieval(results):
    evaluated_results = [result for result in results if result["evaluated"]]
    required_total = sum(len(result["required_sources"]) for result in results)
    found_total = sum(len(result["found_required_sources"]) for result in results)
    retrieved_total = sum(
        len(result["actual_sources"]) for result in evaluated_results
    )
    irrelevant_total = sum(
        len(result["irrelevant_sources"]) for result in evaluated_results
    )
    return {
        "cases_evaluated": len(evaluated_results),
        "cases_passed": sum(result["passed"] for result in evaluated_results),
        "required_total": required_total,
        "found_total": found_total,
        "retrieved_total": retrieved_total,
        "irrelevant_total": irrelevant_total,
        "source_coverage": found_total / required_total if required_total else 1.0,
        "candidate_source_precision": (
            found_total / retrieved_total if retrieved_total else 1.0
        ),
    }


def print_retrieval_results(results, summary):
    print("\nRetrieval Candidate Coverage")
    for result in results:
        if not result["retrieval_ran"]:
            status = "SKIP"
            detail = "signal gate stopped retrieval"
        elif not result["evaluated"]:
            status = "INFO"
            detail = "no required source; acceptance must evaluate coverage"
        else:
            status = "PASS" if result["passed"] else "FAIL"
            detail = (
                "all required sources found"
                if result["passed"]
                else f"missing: {', '.join(result['missing_sources'])}"
            )

        print(f"\n{status} {result['id']}")
        print(f"Required sources: {result['required_sources']}")
        print(f"Actual unique sources: {result['actual_sources']}")
        if result["evaluated"]:
            print(f"Irrelevant sources: {result['irrelevant_sources']}")
            print(
                "Candidate-source precision: "
                f"{result['candidate_source_precision']:.1%}"
            )
        print(f"Result: {detail}")

    print("\nSummary")
    print(
        "Cases with required sources: "
        f"{summary['cases_passed']}/{summary['cases_evaluated']}"
    )
    print(
        f"Required sources found: {summary['found_total']}/"
        f"{summary['required_total']}"
    )
    print(f"Required-source coverage: {summary['source_coverage']:.1%}")
    print(
        "Candidate-source precision: "
        f"{summary['candidate_source_precision']:.1%}"
    )
    print(f"Irrelevant sources retrieved: {summary['irrelevant_total']}")


def evaluate_acceptance(cases, retrieval_results):
    retrieval_results_by_id = {result["id"]: result for result in retrieval_results}
    results = []

    for case in cases:
        retrieval_result = retrieval_results_by_id[case["id"]]
        expected = case["expected"]

        if retrieval_result["retrieval_ran"]:
            assessment = assess_evidence(case["query"], retrieval_result["candidates"])
        else:
            assessment = {
                "decision": "no_incident",
                "reason": "Signal gate stopped retrieval.",
                "evidence": [],
            }

        actual_accepted_sources = list(
            dict.fromkeys(item["source"] for item in assessment["evidence"])
        )
        actual_llm_should_run = assessment["decision"] == "accept"
        decision_passed = assessment["decision"] == expected["decision"]
        sources_passed = set(actual_accepted_sources) == set(
            expected["accepted_sources"]
        )
        llm_routing_passed = actual_llm_should_run == expected["llm_should_run"]

        results.append(
            {
                "id": case["id"],
                "expected_decision": expected["decision"],
                "actual_decision": assessment["decision"],
                "expected_accepted_sources": expected["accepted_sources"],
                "actual_accepted_sources": actual_accepted_sources,
                "expected_llm_should_run": expected["llm_should_run"],
                "actual_llm_should_run": actual_llm_should_run,
                "reason": assessment["reason"],
                "decision_passed": decision_passed,
                "sources_passed": sources_passed,
                "llm_routing_passed": llm_routing_passed,
                "passed": decision_passed and sources_passed and llm_routing_passed,
            }
        )
    return results


def summarize_acceptance(results):
    return {
        "total": len(results),
        "passed": sum(result["passed"] for result in results),
        "decision_correct": sum(result["decision_passed"] for result in results),
        "sources_correct": sum(result["sources_passed"] for result in results),
        "llm_routing_correct": sum(
            result["llm_routing_passed"] for result in results
        ),
    }


def print_acceptance_results(results, summary):
    print("\nEvidence Acceptance")
    for result in results:
        print(f"\n{'PASS' if result['passed'] else 'FAIL'} {result['id']}")
        print(
            f"Decision: expected={result['expected_decision']}, "
            f"actual={result['actual_decision']}"
        )
        print(
            f"Accepted sources: expected={result['expected_accepted_sources']}, "
            f"actual={result['actual_accepted_sources']}"
        )
        print(
            f"LLM should run: expected={result['expected_llm_should_run']}, "
            f"actual={result['actual_llm_should_run']}"
        )
        print(f"Reason: {result['reason']}")

    print("\nSummary")
    print(f"Cases passed: {summary['passed']}/{summary['total']}")
    print(f"Decision accuracy: {summary['decision_correct']}/{summary['total']}")
    print(f"Accepted-source accuracy: {summary['sources_correct']}/{summary['total']}")
    print(f"LLM-routing accuracy: {summary['llm_routing_correct']}/{summary['total']}")


def positive_integer(value):
    parsed = int(value)
    if parsed < 1:
        raise argparse.ArgumentTypeError("value must be at least 1")
    return parsed


def parse_args():
    parser = argparse.ArgumentParser(
        description="Evaluate the OIA pipeline stage by stage."
    )
    parser.add_argument(
        "--split",
        choices=("development", "validation", "held_out", "all"),
        default="development",
        help=(
            "Dataset split to evaluate. Defaults to development so validation "
            "and held-out cases are not exposed accidentally."
        ),
    )
    parser.add_argument("--top-k", type=positive_integer, default=3)
    parser.add_argument("--candidate-k", type=positive_integer, default=5)
    parser.add_argument(
        "--ranking-mode",
        choices=("chunk", "source"),
        default="chunk",
        help="Use normal chunk RRF or experimental source-level aggregation.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    all_pipeline_cases = load_and_validate_cases()
    pipeline_cases = (
        all_pipeline_cases
        if args.split == "all"
        else [case for case in all_pipeline_cases if case["split"] == args.split]
    )
    if not pipeline_cases:
        raise SystemExit(f"No pipeline cases found for split: {args.split}")

    print(
        f"Configuration: split={args.split}, cases={len(pipeline_cases)}, "
        f"top_k={args.top_k}, candidate_k={args.candidate_k}, "
        f"ranking_mode={args.ranking_mode}"
    )
    signal_gate_results = evaluate_signal_gate(pipeline_cases)
    signal_gate_summary = summarize_signal_gate(signal_gate_results)
    print_signal_gate_results(signal_gate_results, signal_gate_summary)

    retrieval_results = evaluate_retrieval(
        pipeline_cases,
        signal_gate_results,
        top_k=args.top_k,
        candidate_k=args.candidate_k,
        ranking_mode=args.ranking_mode,
    )
    retrieval_summary = summarize_retrieval(retrieval_results)
    print_retrieval_results(retrieval_results, retrieval_summary)

    acceptance_results = evaluate_acceptance(pipeline_cases, retrieval_results)
    acceptance_summary = summarize_acceptance(acceptance_results)
    print_acceptance_results(acceptance_results, acceptance_summary)

    signal_gate_failed = signal_gate_summary["correct"] != signal_gate_summary["total"]
    retrieval_failed = (
        retrieval_summary["cases_passed"] != retrieval_summary["cases_evaluated"]
    )
    acceptance_failed = acceptance_summary["passed"] != acceptance_summary["total"]
    if signal_gate_failed or retrieval_failed or acceptance_failed:
        raise SystemExit(1)
