from agent_loop import run_pipeline_tool
from basic_chain import analyze_alert


def run_oia_agent(
    alert: dict,
    *,
    action_evidence_complete: bool = False,
    human_approved: bool = False,
    analyzer=None,
) -> dict:
    analysis_result = (analyzer or analyze_alert)(alert)
    action_result = run_pipeline_tool(
        analysis_result,
        action_evidence_complete=action_evidence_complete,
        human_approved=human_approved,
    )

    return {
        "alert_id": alert.get("id"),
        "analysis": analysis_result,
        "action": action_result,
    }
