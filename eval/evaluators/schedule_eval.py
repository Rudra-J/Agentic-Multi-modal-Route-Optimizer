# eval/evaluators/schedule_eval.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from agents.schedule_agent import schedule
from eval.models import EvalResult, MetricScore, FailureDetail


def run(fixtures: list) -> EvalResult:
    result = EvalResult(area="Schedule Feasibility")

    order_pass = order_total = 0

    for case in fixtures:
        cid = case["id"]
        meetings = case["meetings"]
        expected_order = case.get("expected_order", [])

        sorted_meetings = schedule(meetings)
        actual_order = [m["location"] for m in sorted_meetings]

        order_total += 1
        if actual_order == expected_order:
            order_pass += 1
        else:
            result.failures.append(FailureDetail(
                case_id=cid, metric="sort_order_correctness",
                input_summary=str([m["location"] for m in meetings]),
                expected=str(expected_order),
                actual=str(actual_order)
            ))

    result.metrics = [
        MetricScore("Sort order correctness", order_pass, order_total),
    ]
    return result
