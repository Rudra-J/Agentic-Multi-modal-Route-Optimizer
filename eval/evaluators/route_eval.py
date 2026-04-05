# eval/evaluators/route_eval.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tqdm import tqdm
from agents.planner_agent import plan_day
from eval.models import EvalResult, MetricScore, FailureDetail


def _all_leg_modes(plan: dict) -> list:
    modes = []
    for leg in plan.get("route", []):
        if "legs" in leg:
            for sub in leg["legs"]:
                modes.append(sub.get("mode", ""))
        elif "mode" in leg:
            modes.append(leg["mode"])
    return modes


def _leg_mode_for(plan: dict, from_loc: str, to_loc: str) -> str:
    for leg in plan.get("route", []):
        if leg.get("from") == from_loc and leg.get("to") == to_loc:
            if "legs" in leg and leg["legs"]:
                return leg["legs"][0].get("mode", "")
            return leg.get("mode", "")
    return ""


def run(fixtures: list) -> EvalResult:
    result = EvalResult(area="Route Optimization")

    validity_pass = validity_total = 0
    constraint_pass = constraint_total = 0
    leg_constraint_pass = leg_constraint_total = 0
    infeasibility_pass = infeasibility_total = 0

    for case in tqdm(fixtures, desc="route", unit="case"):
        cid = case["id"]
        meetings = case["meetings"]
        avoid_modes = case.get("avoid_modes", [])
        leg_overrides = case.get("leg_overrides", {})
        leg_avoid_modes = case.get("leg_avoid_modes", {})
        expected = case["expected"]

        plan = plan_day(
            meetings,
            avoid_modes=set(avoid_modes),
            leg_overrides=leg_overrides,
            leg_avoid_modes=leg_avoid_modes
        )

        expected_status = expected.get("status")

        # Route validity
        if expected_status == "success":
            validity_total += 1
            if plan.get("status") != "failed":
                validity_pass += 1
                # has_route is redundant when status=="success" is present; no separate check needed
            else:
                result.failures.append(FailureDetail(
                    case_id=cid, metric="route_validity_rate",
                    input_summary=str([m["location"] for m in meetings]),
                    expected="valid route", actual=str(plan.get("reason"))
                ))
                continue

        # Infeasibility detection
        if expected_status == "failed":
            infeasibility_total += 1
            if plan.get("status") == "failed":
                infeasibility_pass += 1
            else:
                result.failures.append(FailureDetail(
                    case_id=cid, metric="infeasibility_detection",
                    input_summary=str([m["location"] for m in meetings]),
                    expected="failed", actual="succeeded"
                ))
            continue

        all_modes = _all_leg_modes(plan)

        # Global constraint compliance
        if avoid_modes:
            constraint_total += 1
            violations = [m for m in all_modes if m in avoid_modes]
            if not violations:
                constraint_pass += 1
            else:
                result.failures.append(FailureDetail(
                    case_id=cid, metric="constraint_compliance",
                    input_summary=f"avoid={avoid_modes}",
                    expected="none of avoided modes",
                    actual=f"found {violations}"
                ))

        # Leg constraint compliance (specific leg mode check)
        if "leg_mode" in expected:
            leg_constraint_total += 1
            lm = expected["leg_mode"]
            actual_mode = _leg_mode_for(plan, lm["from"], lm["to"])
            if actual_mode == lm["mode"]:
                leg_constraint_pass += 1
            else:
                result.failures.append(FailureDetail(
                    case_id=cid, metric="leg_constraint_compliance",
                    input_summary=f"{lm['from']}->{lm['to']}",
                    expected=lm["mode"], actual=actual_mode
                ))

        if "leg_mode_absent" in expected:
            leg_constraint_total += 1
            lm = expected["leg_mode_absent"]
            actual_mode = _leg_mode_for(plan, lm["from"], lm["to"])
            if actual_mode != lm["mode"]:
                leg_constraint_pass += 1
            else:
                result.failures.append(FailureDetail(
                    case_id=cid, metric="leg_constraint_compliance",
                    input_summary=f"{lm['from']}->{lm['to']} should not be {lm['mode']}",
                    expected=f"not {lm['mode']}", actual=actual_mode
                ))

        if "modes_absent" in expected:
            constraint_total += 1
            violations = [m for m in all_modes if m in expected["modes_absent"]]
            if not violations:
                constraint_pass += 1
            else:
                result.failures.append(FailureDetail(
                    case_id=cid, metric="constraint_compliance",
                    input_summary=f"modes_absent={expected['modes_absent']}",
                    expected="absent", actual=f"found {violations}"
                ))

        if "all_legs_mode" in expected:
            constraint_total += 1
            expected_mode = expected["all_legs_mode"]
            wrong = [m for m in all_modes if m != expected_mode]
            if not wrong:
                constraint_pass += 1
            else:
                result.failures.append(FailureDetail(
                    case_id=cid, metric="constraint_compliance",
                    input_summary=f"all legs should be {expected_mode}",
                    expected=expected_mode, actual=str(set(all_modes))
                ))

        if "leg_count" in expected:
            validity_total += 1
            actual_count = len(plan.get("route", []))
            if actual_count == expected["leg_count"]:
                validity_pass += 1
            else:
                result.failures.append(FailureDetail(
                    case_id=cid, metric="route_validity_rate",
                    input_summary=f"{len(meetings)} meetings",
                    expected=f"{expected['leg_count']} legs",
                    actual=f"{actual_count} legs"
                ))

    result.metrics = [
        MetricScore("Route validity rate", validity_pass, validity_total),
        MetricScore("Constraint compliance", constraint_pass, constraint_total),
        MetricScore("Leg constraint compliance", leg_constraint_pass, leg_constraint_total),
        MetricScore("Infeasibility detection", infeasibility_pass, infeasibility_total),
    ]
    return result
