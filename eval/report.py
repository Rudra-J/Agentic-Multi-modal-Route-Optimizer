# eval/report.py
from eval.models import EvalResult


PASS_THRESHOLD = 85.0
WARN_THRESHOLD = 70.0


def print_report(results: list) -> None:
    """Print a formatted eval report to stdout."""
    width = 60
    print("=" * width)
    print(" MUMBAI MOBILITY AGENT - EVAL REPORT")
    print("=" * width)
    print()

    areas_passed = 0

    for i, result in enumerate(results, 1):
        print(f"[{i}] {result.area}")
        for metric in result.metrics:
            label = metric.name.ljust(40)
            score_str = f"{metric.passed}/{metric.total}".rjust(6)
            pct_str = f"{metric.score_pct}%".rjust(7)
            symbol = "PASS" if metric.score_pct >= 85 else ("WARN" if metric.score_pct >= 70 else "FAIL")
            print(f"    {label} {score_str} {pct_str}  {symbol}")
        area_symbol = "PASS" if result.passed else "FAIL"
        print(f"    {'Area score:'.ljust(40)} {'':6} {result.overall_score:>6.1f}%  {area_symbol}")
        print()
        if result.passed:
            areas_passed += 1

    all_scores = [r.overall_score for r in results]
    overall = round(sum(all_scores) / len(all_scores), 1) if all_scores else 0.0

    print("=" * width)
    print(f" OVERALL SCORE: {overall}%   |   PASSED: {areas_passed}/{len(results)} areas")
    print("=" * width)

    # Print failures
    all_failures = [(r.area, f) for r in results for f in r.failures]
    if all_failures:
        print()
        print("FAILURES")
        print("-" * width)
        current_area = None
        for area, failure in all_failures:
            if area != current_area:
                print(f"\n{area}")
                current_area = area
            print(f"  [{failure.case_id}] {failure.metric}")
            print(f"    Input:    {failure.input_summary}")
            print(f"    Expected: {failure.expected}")
            print(f"    Actual:   {failure.actual}")
