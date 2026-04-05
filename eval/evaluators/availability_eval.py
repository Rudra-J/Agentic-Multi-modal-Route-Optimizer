# eval/evaluators/availability_eval.py
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from tqdm import tqdm
from agents.mobility_agent import MobilityAgent
from eval.models import EvalResult, MetricScore, FailureDetail


def run(fixtures: list) -> EvalResult:
    result = EvalResult(area="Route Availability")

    status_pass = status_total = 0
    availability_pass = availability_total = 0

    for case in tqdm(fixtures, desc="availability", unit="case"):
        cid = case["id"]
        message = case["message"]
        meetings = case["meetings"]
        expected = case["expected"]

        agent = MobilityAgent()
        response = agent.chat(message, meetings)
        result_data = response.get("result", {}) if isinstance(response, dict) else {}

        # Check status field
        if "status" in expected:
            status_total += 1
            actual_status = result_data.get("status") if isinstance(result_data, dict) else None
            if actual_status == expected["status"]:
                status_pass += 1
            else:
                result.failures.append(FailureDetail(
                    case_id=cid, metric="route_check_status",
                    input_summary=message,
                    expected=expected["status"],
                    actual=str(actual_status)
                ))

        # Check availability flag
        if "available" in expected:
            availability_total += 1
            actual_available = result_data.get("available") if isinstance(result_data, dict) else None
            if actual_available == expected["available"]:
                availability_pass += 1
            else:
                result.failures.append(FailureDetail(
                    case_id=cid, metric="route_availability_flag",
                    input_summary=message,
                    expected=str(expected["available"]),
                    actual=str(actual_available)
                ))

    result.metrics = [
        MetricScore("Route check status", status_pass, status_total),
        MetricScore("Route availability flag", availability_pass, availability_total),
    ]
    return result
