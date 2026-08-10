from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class ToolPolicy:
    name: str
    mode: Literal["read_only", "write"]
    risk_level: Literal["low", "high"]
    requires_accepted_incident: bool
    requires_action_evidence: bool
    requires_human_approval: bool


TOOL_POLICIES = {
    "inspect_lambda_metrics": ToolPolicy(
        name="inspect_lambda_metrics",
        mode="read_only",
        risk_level="low",
        requires_accepted_incident=True,
        requires_action_evidence=False,
        requires_human_approval=False,
    ),
    "rollback_lambda_deployment": ToolPolicy(
        name="rollback_lambda_deployment",
        mode="write",
        risk_level="high",
        requires_accepted_incident=True,
        requires_action_evidence=True,
        requires_human_approval=True,
    ),
}

def evaluate_tool_request(
    policy: ToolPolicy,
    *,
    incident_accepted: bool,
    action_evidence_complete: bool,
    human_approved: bool,
) -> tuple[bool, str]:
    if policy.requires_accepted_incident and not incident_accepted:
        return False, "Accepted incident evidence is required."

    if policy.requires_action_evidence and not action_evidence_complete:
        return False, "Action-specific evidence is required."

    if policy.requires_human_approval and not human_approved:
        return False, "Human approval is required."

    return True, "Tool request satisfies policy."