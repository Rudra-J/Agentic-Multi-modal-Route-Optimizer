# eval/evaluators/whatif_eval.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from agents.mobility_agent import MobilityAgent
from eval.models import EvalResult, MetricScore, FailureDetail


def _leg_mode_for(plan: dict, from_loc: str, to_loc: str) -> str:
    for leg in plan.get("route", []):
        if leg.get("from") == from_loc and leg.get("to") == to_loc:
            if "legs" in leg and leg["legs"]:
                return leg["legs"][0].get("mode", "")
            return leg.get("mode", "")
    return ""


def run(fixtures: list) -> EvalResult:
    result = EvalResult(area="What-If Scenarios")

    preview_pass = preview_total = 0
    pending_pass = pending_total = 0
    confirm_pass = confirm_total = 0

    for case in fixtures:
        cid = case["id"]
        turns = case["turns"]
        meetings = case["meetings"]
        expected = case["expected"]

        agent = MobilityAgent()
        last_response = None

        for turn in turns:
            last_response = agent.chat(turn["message"], meetings)

        result_data = last_response.get("result", {}) if isinstance(last_response, dict) else {}

        # Check last result status (proposal_preview)
        if "last_result_status" in expected:
            preview_total += 1
            actual_status = result_data.get("status") if isinstance(result_data, dict) else None
            if actual_status == expected["last_result_status"]:
                preview_pass += 1
            else:
                result.failures.append(FailureDetail(
                    case_id=cid, metric="whatif_preview_trigger",
                    input_summary=str([t["message"] for t in turns]),
                    expected=expected["last_result_status"],
                    actual=str(actual_status)
                ))

        # Check pending_leg_change mode
        if "pending_leg_change_mode" in expected:
            pending_total += 1
            plc = agent.state.pending_leg_change
            actual_mode = plc.get("mode") if plc else None
            if actual_mode == expected["pending_leg_change_mode"]:
                pending_pass += 1
            else:
                result.failures.append(FailureDetail(
                    case_id=cid, metric="whatif_pending_state",
                    input_summary=str([t["message"] for t in turns]),
                    expected=f"pending mode = {expected['pending_leg_change_mode']}",
                    actual=str(actual_mode)
                ))

        # Check pending_leg_change is absent
        if "pending_leg_change_absent" in expected and expected["pending_leg_change_absent"]:
            pending_total += 1
            if agent.state.pending_leg_change is None:
                pending_pass += 1
            else:
                result.failures.append(FailureDetail(
                    case_id=cid, metric="whatif_pending_state",
                    input_summary=str([t["message"] for t in turns]),
                    expected="pending_leg_change is None",
                    actual=str(agent.state.pending_leg_change)
                ))

        # Check confirmed what-if applies leg mode in plan
        if "leg_mode" in expected:
            confirm_total += 1
            if isinstance(result_data, dict) and "route" in result_data:
                lm = expected["leg_mode"]
                actual_mode = _leg_mode_for(result_data, lm["from"], lm["to"])
                if actual_mode == lm["mode"]:
                    confirm_pass += 1
                else:
                    result.failures.append(FailureDetail(
                        case_id=cid, metric="whatif_confirmation",
                        input_summary=str([t["message"] for t in turns]),
                        expected=f"{lm['from']}->{lm['to']} = {lm['mode']}",
                        actual=actual_mode
                    ))
            else:
                result.failures.append(FailureDetail(
                    case_id=cid, metric="whatif_confirmation",
                    input_summary=str([t["message"] for t in turns]),
                    expected="route in result",
                    actual=str(result_data)
                ))

    result.metrics = [
        MetricScore("What-if preview trigger", preview_pass, preview_total) if preview_total > 0
            else MetricScore("What-if preview trigger", 1, 1),
        MetricScore("What-if pending state", pending_pass, pending_total) if pending_total > 0
            else MetricScore("What-if pending state", 1, 1),
        MetricScore("What-if confirmation", confirm_pass, confirm_total) if confirm_total > 0
            else MetricScore("What-if confirmation", 1, 1),
    ]
    return result
