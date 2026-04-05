# eval/run_eval.py
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from eval.evaluators import intent_eval, constraint_eval, route_eval, schedule_eval, conversation_eval, whatif_eval, availability_eval
from eval.report import print_report, save_report


FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

AREAS = {
    "intent": ("intent_parsing.json", intent_eval),
    "constraint": ("constraint_application.json", constraint_eval),
    "route": ("route_optimization.json", route_eval),
    "schedule": ("schedule_feasibility.json", schedule_eval),
    "conversation": ("conversation_flow.json", conversation_eval),
    "whatif": ("whatif.json", whatif_eval),
    "availability": ("availability.json", availability_eval),
}


def load_fixtures(filename: str) -> list:
    path = os.path.join(FIXTURE_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    parser = argparse.ArgumentParser(description="Run Mumbai Mobility Agent evals")
    parser.add_argument(
        "--area",
        choices=list(AREAS.keys()),
        help="Run only this eval area (default: all)",
        default=None
    )
    args = parser.parse_args()

    areas_to_run = {args.area: AREAS[args.area]} if args.area else AREAS

    results = []
    for area_name, (fixture_file, evaluator) in areas_to_run.items():
        print(f"Running {area_name} eval...", flush=True)
        fixtures = load_fixtures(fixture_file)
        result = evaluator.run(fixtures)
        results.append(result)

    print()
    print_report(results)
    saved = save_report(results)
    print(f"\nResults saved to: {saved}")


if __name__ == "__main__":
    main()
