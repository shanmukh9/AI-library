from tool_policy import TOOL_POLICIES, evaluate_tool_request
from simulated_tools import TOOL_HANDLERS

def authorize_tool(
    tool_name: str,
    *,
    incident_accepted: bool,
    action_evidence_complete: bool,
    human_approved: bool,
) -> dict:
    if tool_name not in TOOL_POLICIES:
        return {
            "tool": tool_name,
            "status": "blocked",
            "reason": "Unknown tool is not permitted.",
        }

    policy = TOOL_POLICIES[tool_name]

    allowed, reason = evaluate_tool_request(
        policy,
        incident_accepted=incident_accepted,
        action_evidence_complete=action_evidence_complete,
        human_approved=human_approved,
    )

    return {
        "tool": tool_name,
        "status": "authorized" if allowed else "blocked",
        "reason": reason,
    }

def run_agent_step(
    tool_name: str,
    *,
    incident_accepted: bool,
    action_evidence_complete: bool,
    human_approved: bool,
) -> dict:
    authorization = authorize_tool(
        tool_name,
        incident_accepted=incident_accepted,
        action_evidence_complete=action_evidence_complete,
        human_approved=human_approved,
    )

    if authorization["status"] != "authorized":
        return authorization

    handler = TOOL_HANDLERS.get(tool_name)

    if handler is None:
        return {
            "tool": tool_name,
            "status": "blocked",
            "reason": "No executable handler is registered.",
        }

    result = handler()

    return {
        "tool": tool_name,
        "status": "executed",
        "reason": "Tool executed after policy authorization.",
        "result": result,
    }

PROPOSAL_FIELDS = {"tool_name", "rationale", "evidence_refs"}

def run_pipeline_tool(
    pipeline_result: dict,
    *,
    action_evidence_complete: bool,
    human_approved: bool,
) -> dict:
    pipeline_status = pipeline_result.get("status")

    if pipeline_status in {
        "no_incident",
        "no_coverage",
        "clarification_required",
    }:
        return {
            "tool": None,
            "status": "not_applicable",
            "reason": (
                f"Action stage is not applicable for pipeline status: "
                f"{pipeline_status}."
            ),
        }

    if pipeline_status != "analysis_ready":
        return {
            "tool": None,
            "status": "blocked",
            "reason": "Analysis did not complete successfully.",
        }

    retrieval = pipeline_result.get("retrieval")

    if not isinstance(retrieval, dict):
        return {
            "tool": None,
            "status": "blocked",
            "reason": "Retrieval trace is missing or invalid.",
        }

    if retrieval.get("decision") != "accept":
        return {
            "tool": None,
            "status": "blocked",
            "reason": "Incident evidence was not accepted.",
        }

    analysis = pipeline_result.get("analysis")

    if not isinstance(analysis, dict):
        return {
            "tool": None,
            "status": "blocked",
            "reason": "Analysis payload is invalid.",
        }

    if "tool_proposal" not in analysis:
        return {
            "tool": None,
            "status": "blocked",
            "reason": "Analysis is missing tool_proposal.",
        }

    proposal = analysis["tool_proposal"]

    if proposal is None:
        return {
            "tool": None,
            "status": "no_action",
            "reason": "Analysis completed without proposing a tool.",
        }

    valid, reason = validate_tool_proposal(proposal)

    if not valid:
        return {
            "tool": None,
            "status": "blocked",
            "reason": reason,
        }

    accepted_sources = set(retrieval.get("accepted_sources", []))
    referenced_sources = set(proposal["evidence_refs"])

    if not referenced_sources.issubset(accepted_sources):
        return {
            "tool": proposal["tool_name"],
            "status": "blocked",
            "reason": "Tool proposal references evidence that was not accepted.",
        }

    return run_agent_step(
        proposal["tool_name"],
        incident_accepted=True,
        action_evidence_complete=action_evidence_complete,
        human_approved=human_approved,
    )


def validate_tool_proposal(proposal: object) -> tuple[bool, str]:
    if not isinstance(proposal, dict):
        return False, "Tool proposal must be an object."

    

    unexpected = set(proposal) - PROPOSAL_FIELDS
    if unexpected:
        return False, f"Unexpected proposal fields: {sorted(unexpected)}"

    missing = PROPOSAL_FIELDS - set(proposal)
    if missing:
        return False, f"Missing proposal fields: {sorted(missing)}"

    if not isinstance(proposal["tool_name"], str):
        return False, "tool_name must be a string."

    if not isinstance(proposal["rationale"], str):
        return False, "rationale must be a string."

    if not isinstance(proposal["evidence_refs"], list):
        return False, "evidence_refs must be a list."

    if not proposal["evidence_refs"]:
        return False, "evidence_refs must not be empty."
    
    if not all(
        isinstance(reference, str) and reference.strip()
        for reference in proposal["evidence_refs"]
    ):
        return False, "Every evidence reference must be a non-empty string."

    

    return True, "Tool proposal is structurally valid."