# eval/evaluators/intent_eval.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tqdm import tqdm
from agents.brain_agent import think
from eval.models import EvalResult, MetricScore, FailureDetail


def run(fixtures: list) -> EvalResult:
    result = EvalResult(area="LLM Intent Parsing")

    intent_pass = intent_total = 0
    loc_pass = loc_total = 0
    mode_pass = mode_total = 0
    fallback_count = total_count = 0
    parse_pass = parse_total = 0

    for case in tqdm(fixtures, desc="intent", unit="case"):
        cid = case["id"]
        user_input = case["input"]
        expected = case["expected"]

        decision = think(user_input)
        total_count += 1
        parse_total += 1

        if not isinstance(decision, dict) or not decision.get("action"):
            result.failures.append(FailureDetail(
                case_id=cid, metric="parse_success_rate",
                input_summary=user_input, expected=str(expected), actual=str(decision)
            ))
            continue

        parse_pass += 1

        if decision.get("reason") == "fallback_rule":
            fallback_count += 1

        # Intent classification
        intent_total += 1
        if decision.get("action") == expected.get("action"):
            intent_pass += 1
        else:
            result.failures.append(FailureDetail(
                case_id=cid, metric="intent_classification_accuracy",
                input_summary=user_input,
                expected=expected.get("action"),
                actual=decision.get("action")
            ))

        # Location extraction (only for leg-level actions)
        if "from_location" in expected:
            loc_total += 2
            if decision.get("from_location") == expected.get("from_location"):
                loc_pass += 1
            else:
                result.failures.append(FailureDetail(
                    case_id=cid, metric="location_extraction_accuracy",
                    input_summary=user_input,
                    expected=f"from={expected.get('from_location')}",
                    actual=f"from={decision.get('from_location')}"
                ))
            if decision.get("to_location") == expected.get("to_location"):
                loc_pass += 1
            else:
                result.failures.append(FailureDetail(
                    case_id=cid, metric="location_extraction_accuracy",
                    input_summary=user_input,
                    expected=f"to={expected.get('to_location')}",
                    actual=f"to={decision.get('to_location')}"
                ))

        # Mode extraction
        if "transport_mode" in expected:
            mode_total += 1
            if decision.get("transport_mode") == expected.get("transport_mode"):
                mode_pass += 1
            else:
                result.failures.append(FailureDetail(
                    case_id=cid, metric="mode_extraction_accuracy",
                    input_summary=user_input,
                    expected=expected.get("transport_mode"),
                    actual=decision.get("transport_mode")
                ))

        if "avoid_modes" in expected:
            mode_total += 1
            expected_modes = sorted(expected.get("avoid_modes", []))
            actual_modes = sorted(decision.get("avoid_modes", []))
            if actual_modes == expected_modes:
                mode_pass += 1
            else:
                result.failures.append(FailureDetail(
                    case_id=cid, metric="mode_extraction_accuracy",
                    input_summary=user_input,
                    expected=str(expected_modes),
                    actual=str(actual_modes)
                ))

    result.metrics = [
        MetricScore("Intent classification accuracy", intent_pass, intent_total),
        MetricScore("Location extraction accuracy", loc_pass, loc_total),
        MetricScore("Mode extraction accuracy", mode_pass, mode_total),
        MetricScore("Fallback rate (lower is better)", total_count - fallback_count, total_count),
        MetricScore("Parse success rate", parse_pass, parse_total),
    ]
    return result
