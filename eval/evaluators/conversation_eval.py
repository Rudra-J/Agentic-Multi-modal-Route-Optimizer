# eval/evaluators/conversation_eval.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from agents.mobility_agent import MobilityAgent
from eval.models import EvalResult, MetricScore, FailureDetail


def _all_leg_modes(plan: dict) -> list:
    modes = []
    for leg in plan.get("route", []):
        for sub in leg.get("legs", []):
            modes.append(sub.get("mode", ""))
    return modes


def _leg_mode_for(plan: dict, from_loc: str, to_loc: str) -> str:
    for leg in plan.get("route", []):
        if leg.get("from") == from_loc and leg.get("to") == to_loc:
            sub_legs = leg.get("legs", [])
            if sub_legs:
                return sub_legs[0].get("mode", "")
    return ""


def run(fixtures: list) -> EvalResult:
    result = EvalResult(area="Conversation Flow")

    state_pass = state_total = 0
    conflict_pass = conflict_total = 0

    for case in fixtures:
        cid = case["id"]
        turns = case["turns"]
        meetings = case["meetings"]
        expected = case["expected"]

        agent = MobilityAgent()
        last_plan = None

        for turn in turns:
            response = agent.chat(turn["message"], meetings)
            if isinstance(response, dict) and response.get("status") != "failed" and "route" in response:
                last_plan = response

        # State persistence: check final plan respects constraints
        if "plan_modes_absent" in expected and last_plan:
            state_total += 1
            all_modes = _all_leg_modes(last_plan)
            violations = [m for m in all_modes if m in expected["plan_modes_absent"]]
            if not violations:
                state_pass += 1
            else:
                result.failures.append(FailureDetail(
                    case_id=cid, metric="multi_turn_state_persistence",
                    input_summary=str([t["message"] for t in turns]),
                    expected=f"no {expected['plan_modes_absent']} in plan",
                    actual=f"found {violations}"
                ))

        if "leg_mode" in expected and last_plan:
            state_total += 1
            lm = expected["leg_mode"]
            actual_mode = _leg_mode_for(last_plan, lm["from"], lm["to"])
            if actual_mode == lm["mode"]:
                state_pass += 1
            else:
                result.failures.append(FailureDetail(
                    case_id=cid, metric="multi_turn_state_persistence",
                    input_summary=str([t["message"] for t in turns]),
                    expected=f"{lm['from']}->{lm['to']} = {lm['mode']}",
                    actual=actual_mode
                ))

        if "leg_override_absent" in expected:
            conflict_total += 1
            lm = expected["leg_override_absent"]
            key = f"{lm['from'].lower()}->{lm['to'].lower()}"
            if key not in agent.state.leg_overrides:
                conflict_pass += 1
            else:
                result.failures.append(FailureDetail(
                    case_id=cid, metric="conflict_surfacing",
                    input_summary=str([t["message"] for t in turns]),
                    expected=f"no override on {key} (conflict should prevent it)",
                    actual=str(agent.state.leg_overrides.get(key))
                ))

    result.metrics = [
        MetricScore("Multi-turn state persistence", state_pass, state_total),
        MetricScore("Conflict surfacing", conflict_pass, conflict_total) if conflict_total > 0
            else MetricScore("Conflict surfacing", 1, 1),
    ]
    return result
