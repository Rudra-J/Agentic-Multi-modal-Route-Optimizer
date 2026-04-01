# eval/evaluators/constraint_eval.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from models.world_state import WorldState
from agents.action_agent import execute
from eval.models import EvalResult, MetricScore, FailureDetail


def _make_state(pre_state: dict) -> WorldState:
    state = WorldState()
    if not pre_state:
        return state
    for mode in pre_state.get("avoid_modes", []):
        state.avoid_modes.add(mode)
    for key, val in pre_state.get("leg_overrides", {}).items():
        state.leg_overrides[key] = val
    for key, val in pre_state.get("leg_avoid_modes", {}).items():
        state.leg_avoid_modes[key] = val
    return state


def run(fixtures: list) -> EvalResult:
    result = EvalResult(area="Constraint Application")

    global_pass = global_total = 0
    leg_avoid_pass = leg_avoid_total = 0
    leg_override_pass = leg_override_total = 0
    conflict_pass = conflict_total = 0

    for case in fixtures:
        cid = case["id"]
        decision = case["decision"]
        expected = case["expected"]
        pre_state = case.get("pre_state", {})

        state = _make_state(pre_state)
        execute(decision, state, [])

        action = decision.get("action")

        if action == "update_preferences":
            global_total += 1
            expected_modes = set(expected.get("avoid_modes", []))
            if expected_modes.issubset(state.avoid_modes):
                global_pass += 1
            else:
                result.failures.append(FailureDetail(
                    case_id=cid, metric="global_avoid_stored",
                    input_summary=str(decision),
                    expected=str(expected_modes),
                    actual=str(state.avoid_modes)
                ))
            if "leg_overrides" in expected:
                conflict_total += 1
                if state.leg_overrides == expected["leg_overrides"]:
                    conflict_pass += 1
                else:
                    result.failures.append(FailureDetail(
                        case_id=cid, metric="conflict_detection_rate",
                        input_summary=str(decision),
                        expected=str(expected["leg_overrides"]),
                        actual=str(state.leg_overrides)
                    ))

        elif action == "edit_leg":
            leg_override_total += 1
            if state.leg_overrides == expected.get("leg_overrides", {}):
                leg_override_pass += 1
            else:
                result.failures.append(FailureDetail(
                    case_id=cid, metric="leg_override_stored",
                    input_summary=str(decision),
                    expected=str(expected.get("leg_overrides")),
                    actual=str(state.leg_overrides)
                ))
            if "leg_avoid_modes" in expected:
                conflict_total += 1
                if state.leg_avoid_modes == expected["leg_avoid_modes"]:
                    conflict_pass += 1
                else:
                    result.failures.append(FailureDetail(
                        case_id=cid, metric="conflict_detection_rate",
                        input_summary=str(decision),
                        expected=str(expected["leg_avoid_modes"]),
                        actual=str(state.leg_avoid_modes)
                    ))

        elif action == "avoid_mode_on_leg":
            leg_avoid_total += 1
            if state.leg_avoid_modes == expected.get("leg_avoid_modes", {}):
                leg_avoid_pass += 1
            else:
                result.failures.append(FailureDetail(
                    case_id=cid, metric="leg_avoid_stored",
                    input_summary=str(decision),
                    expected=str(expected.get("leg_avoid_modes")),
                    actual=str(state.leg_avoid_modes)
                ))
            if "leg_overrides" in expected:
                conflict_total += 1
                if state.leg_overrides == expected["leg_overrides"]:
                    conflict_pass += 1
                else:
                    result.failures.append(FailureDetail(
                        case_id=cid, metric="conflict_detection_rate",
                        input_summary=str(decision),
                        expected=str(expected["leg_overrides"]),
                        actual=str(state.leg_overrides)
                    ))

        elif action in ("clear_leg_override", "clear_leg_preference"):
            leg_override_total += 1
            expected_overrides = expected.get("leg_overrides", {})
            if state.leg_overrides == expected_overrides:
                leg_override_pass += 1
            else:
                result.failures.append(FailureDetail(
                    case_id=cid, metric="leg_override_stored",
                    input_summary=str(decision),
                    expected=str(expected_overrides),
                    actual=str(state.leg_overrides)
                ))
            if "leg_avoid_modes" in expected:
                leg_avoid_total += 1
                if state.leg_avoid_modes == expected["leg_avoid_modes"]:
                    leg_avoid_pass += 1
                else:
                    result.failures.append(FailureDetail(
                        case_id=cid, metric="leg_avoid_stored",
                        input_summary=str(decision),
                        expected=str(expected["leg_avoid_modes"]),
                        actual=str(state.leg_avoid_modes)
                    ))

    result.metrics = [
        MetricScore("Global avoid stored correctly", global_pass, global_total),
        MetricScore("Leg avoid stored correctly", leg_avoid_pass, leg_avoid_total),
        MetricScore("Leg override stored correctly", leg_override_pass, leg_override_total),
        MetricScore("Conflict detection rate", conflict_pass, conflict_total),
    ]
    return result
