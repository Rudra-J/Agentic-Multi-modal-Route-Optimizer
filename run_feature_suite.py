import os
import traceback

import requests

from services.output_formatter import format_plan


BASE_MEETINGS = [
    {"location": "Powai", "start_time": "09:00", "duration_minutes": 30},
    {"location": "BKC", "start_time": "12:30", "duration_minutes": 45},
    {"location": "Bandra", "start_time": "14:00", "duration_minutes": 30},
    {"location": "CST", "start_time": "16:30", "duration_minutes": 60},
]


TIGHT_MEETINGS = [
    {"location": "Powai", "start_time": "09:00", "duration_minutes": 30},
    {"location": "BKC", "start_time": "09:50", "duration_minutes": 30},
    {"location": "Bandra", "start_time": "12:00", "duration_minutes": 30},
]


TRAIN_LIST_MEETINGS = [
    {"location": "Andheri", "start_time": "09:00", "duration_minutes": 30},
    {"location": "Dadar", "start_time": "10:30", "duration_minutes": 30},
    {"location": "CST", "start_time": "12:00", "duration_minutes": 30},
]


class FeatureSuite:
    def __init__(self, base_url="http://127.0.0.1:8001"):
        self.base_url = base_url.rstrip("/")
        self.passed = 0
        self.failed = 0
        self.failed_names = []

    def _assert(self, condition, message):
        if not condition:
            raise AssertionError(message)

    def _chat(self, message, meetings):
        response = requests.post(
            f"{self.base_url}/chat",
            json={"message": message, "meetings": meetings},
            timeout=60,
        )
        self._assert(response.status_code == 200, f"/chat failed ({response.status_code}) for message: {message}")
        return response.json()

    def _reset(self):
        response = requests.post(f"{self.base_url}/reset_state", timeout=10)
        self._assert(response.status_code == 200, "/reset_state failed")
        payload = response.json()
        self._assert(payload.get("status") == "ok", "reset_state did not return status=ok")

    def _run_case(self, name, fn):
        try:
            fn()
            self.passed += 1
            print(f"[PASS] {name}")
        except Exception as exc:
            self.failed += 1
            self.failed_names.append(name)
            print(f"[FAIL] {name}: {exc}")
            print(traceback.format_exc())

    def case_health_and_locations(self):
        health = requests.get(f"{self.base_url}/health", timeout=10)
        self._assert(health.status_code == 200, "/health should return 200")
        health_json = health.json()
        self._assert(health_json.get("status") == "ok", "health status should be ok")

        locations = requests.get(f"{self.base_url}/locations", timeout=10)
        self._assert(locations.status_code == 200, "/locations should return 200")
        locations_json = locations.json()
        self._assert(locations_json.get("count", 0) > 0, "locations count should be > 0")

        names = {entry["name"] for entry in locations_json.get("locations", [])}
        self._assert("Powai" in names, "Powai should exist in locations")
        self._assert("BKC" in names, "BKC should exist in locations")

    def case_csv_upload(self):
        csv_path = os.path.join(os.path.dirname(__file__), "sample_itinerary.csv")
        self._assert(os.path.exists(csv_path), "sample_itinerary.csv is missing")

        with open(csv_path, "rb") as file_handle:
            response = requests.post(
                f"{self.base_url}/upload_itinerary",
                files={"file": ("sample_itinerary.csv", file_handle, "text/csv")},
                timeout=20,
            )

        self._assert(response.status_code == 200, "/upload_itinerary should return 200")
        payload = response.json()
        self._assert(payload.get("success") is True, "upload response should contain success=true")
        self._assert(payload.get("count", 0) > 0, "upload should return one or more meetings")

    def case_basic_plan(self):
        self._reset()
        result = self._chat("plan my day", BASE_MEETINGS)

        decision = result.get("decision", {})
        self._assert(decision.get("action") in {"plan", "replan"}, "plan request should trigger plan/replan action")

        route = result.get("result", {}).get("route", [])
        self._assert(isinstance(route, list) and len(route) > 0, "planned route should be a non-empty list")

    def case_global_preference_and_replan(self):
        self._reset()

        pref = self._chat("avoid train", BASE_MEETINGS)
        avoid_modes = set(pref.get("memory", {}).get("avoid_modes", []))
        self._assert("train" in avoid_modes, "train should be stored in global avoid modes")

        plan = self._chat("plan my day", BASE_MEETINGS)
        for leg in plan.get("result", {}).get("route", []):
            self._assert(leg.get("mode") != "train", "route should not contain train after global train avoid")

    def case_leg_avoid_constraint(self):
        self._reset()

        avoid = self._chat("don't take train from bandra to cst", BASE_MEETINGS)
        leg_avoid = avoid.get("memory", {}).get("leg_avoid_modes", {})
        self._assert("bandra->cst" in leg_avoid, "leg_avoid_modes must contain bandra->cst")

        leg_entry = leg_avoid["bandra->cst"]
        self._assert("train" in leg_entry.get("avoid", []), "bandra->cst avoid list should include train")

        planned = self._chat("plan my day", BASE_MEETINGS)
        sections = planned.get("result", {}).get("sections", [])
        target = [section for section in sections if section.get("from") == "Bandra" and section.get("to") == "CST"]
        self._assert(target, "plan must include Bandra -> CST section")

        for leg in target[0].get("legs", []):
            self._assert(leg.get("mode") != "train", "Bandra -> CST section should avoid train")

    def case_route_qna_and_followup_apply(self):
        self._reset()

        qna = self._chat("is there a bus from powai to bkc?", BASE_MEETINGS)
        self._assert(
            qna.get("decision", {}).get("action") == "check_route_availability",
            "route availability question should return check_route_availability",
        )
        self._assert(qna.get("result", {}).get("status") == "route_check", "route check should return status=route_check")

        followup = self._chat("can i take the bus then?", BASE_MEETINGS)
        self._assert(followup.get("decision", {}).get("action") == "plan", "follow-up apply should return plan")
        self._assert(
            followup.get("decision", {}).get("reason") == "followup_route_apply",
            "follow-up apply should set reason=followup_route_apply",
        )

        overrides = followup.get("memory", {}).get("leg_overrides", {})
        self._assert("powai->bkc" in overrides, "follow-up apply should set powai->bkc override")
        self._assert(overrides["powai->bkc"].get("mode") == "bus", "powai->bkc override mode should be bus")

    def case_question_not_treated_as_override(self):
        self._reset()

        # Test various question phrasings that should NOT trigger plan or edit_leg
        question_cases = [
            "are we using a cab from powai to bkc?",
            "what are we using to go from powai to bkc?",
            "how are we getting from bkc to bandra?",
            "which mode is the powai to bkc leg using?",
        ]
        for q in question_cases:
            self._reset()
            r = self._chat(q, BASE_MEETINGS)
            action = r.get("decision", {}).get("action", "")
            self._assert(
                action not in ("edit_leg", "plan"),
                f"question '{q}' should NOT trigger {action}",
            )
            overrides = r.get("memory", {}).get("leg_overrides", {})
            self._assert(
                overrides == {} or "powai->bkc" not in overrides,
                f"question '{q}' should NOT create an override, got: {overrides}",
            )

    def case_unclear_fallback(self):
        self._reset()

        r = self._chat("banana smoothie recipe", BASE_MEETINGS)
        action = r.get("decision", {}).get("action", "")
        self._assert(
            action == "unclear",
            f"gibberish input should return 'unclear', got: {action}",
        )
        self._assert(
            "rephrase" in r.get("result", {}).get("message", "").lower(),
            "unclear response should ask user to rephrase",
        )

    def case_itinerary_train_listing(self):
        self._reset()

        listing = self._chat("list all available train routes for this itinerary", TRAIN_LIST_MEETINGS)
        self._assert(
            listing.get("decision", {}).get("action") == "list_itinerary_mode_routes",
            "itinerary route listing should return list_itinerary_mode_routes action",
        )
        self._assert(
            listing.get("result", {}).get("status") == "itinerary_mode_list",
            "itinerary route listing should return itinerary_mode_list status",
        )

        matches = listing.get("result", {}).get("matches", [])
        self._assert(isinstance(matches, list), "itinerary mode listing matches should be a list")
        self._assert(len(matches) > 0, "train listing should include at least one direct leg for TRAIN_LIST_MEETINGS")
        for item in matches:
            self._assert(item.get("mode") == "train", "all listed itinerary matches should be train mode")

    def case_what_if_confirm_and_reject(self):
        self._reset()

        preview = self._chat("how much extra time taking a cab from powai to bkc would take", BASE_MEETINGS)
        self._assert(preview.get("decision", {}).get("action") == "what_if", "what-if query should return what_if action")
        proposal = preview.get("result", {}).get("proposal")
        self._assert(bool(proposal), "what-if preview should include a staged proposal")

        apply_change = self._chat("yes", BASE_MEETINGS)
        self._assert(apply_change.get("decision", {}).get("action") == "plan", "confirmation should apply and replan")
        self._assert(
            apply_change.get("decision", {}).get("reason") == "proposal_confirmed",
            "confirmation should set reason=proposal_confirmed",
        )

        overrides = apply_change.get("memory", {}).get("leg_overrides", {})
        self._assert("powai->bkc" in overrides, "confirmed what-if should create powai->bkc override")
        self._assert(overrides["powai->bkc"].get("mode") == "cab", "powai->bkc override should be cab")

        self._reset()
        preview_again = self._chat("how much extra time taking a cab from powai to bkc would take", BASE_MEETINGS)
        self._assert(preview_again.get("decision", {}).get("action") == "what_if", "second what-if preview should be created")
        self._assert(bool(preview_again.get("result", {}).get("proposal")), "second what-if preview should stage proposal")

        reject = self._chat("no", BASE_MEETINGS)
        self._assert(reject.get("decision", {}).get("action") == "no_action", "reject should not apply changes")
        self._assert(reject.get("decision", {}).get("reason") == "proposal_cancelled", "reject should cancel proposal")

    def case_no_pending_confirmation_guard(self):
        self._reset()

        reply = self._chat("yes", BASE_MEETINGS)
        self._assert(reply.get("decision", {}).get("action") == "no_action", "yes without pending proposal should do no action")
        self._assert(
            reply.get("decision", {}).get("reason") == "no_pending_proposal",
            "yes without pending proposal should return no_pending_proposal reason",
        )

    def case_preference_fallback_infeasible(self):
        self._reset()

        set_override = requests.post(
            f"{self.base_url}/set_leg_override",
            json={"from": "Powai", "to": "BKC", "mode": "bus", "reason": "force infeasible for test"},
            timeout=10,
        )
        self._assert(set_override.status_code == 200, "/set_leg_override should return 200")
        self._assert(set_override.json().get("status") == "ok", "set_leg_override should return status=ok")

        plan = self._chat("plan my day", TIGHT_MEETINGS)
        self._assert(plan.get("result", {}).get("status") == "failed", "tight plan with bus override should fail")
        self._assert(
            bool(plan.get("result", {}).get("failed_override")),
            "failed plan should include failed_override for preference fallback",
        )
        self._assert(
            plan.get("result", {}).get("suggest_clear_override") is True,
            "failed plan should suggest clearing override",
        )

    def case_formatter_cab_aggregation(self):
        itinerary = [
            {
                "from": "A",
                "to": "C",
                "start_time": 540,
                "end_time": 570,
                "delay_probability": 0.1,
                "route": {
                    "legs": [
                        {"from": "A", "to": "B", "mode": "cab", "time": 10, "cost": 50, "reliability": "99%"},
                        {"from": "B", "to": "C", "mode": "cab", "time": 20, "cost": 70, "reliability": "97%"},
                    ]
                },
            }
        ]

        formatted = format_plan(itinerary)
        route = formatted.get("route", [])
        self._assert(len(route) == 1, "consecutive cab legs should be aggregated into one displayed leg")
        self._assert(route[0].get("from") == "A" and route[0].get("to") == "C", "aggregated cab leg should span A -> C")
        self._assert(route[0].get("time") == 30, "aggregated cab time should be summed")
        self._assert(route[0].get("cost") == 120, "aggregated cab cost should be summed")

    def case_constraint_conflict_resolution(self):
        """Avoiding a mode on a leg should remove a conflicting force-override, and vice versa."""
        self._reset()

        # Plan first so there's state
        self._chat("plan my day", BASE_MEETINGS)

        # Force cab on Powai->BKC via API
        requests.post(
            f"{self.base_url}/set_leg_override",
            json={"from": "Powai", "to": "BKC", "mode": "cab", "reason": "test_force"},
            timeout=10,
        )

        # Now avoid cab on the same leg via chat
        r = self._chat("i dont want to use powai to bkc cab", BASE_MEETINGS)
        mem = r.get("memory", {})

        # The force-cab override should have been removed
        overrides = mem.get("leg_overrides", {})
        self._assert(
            "powai->bkc" not in overrides,
            f"force-cab override should be removed when avoiding cab, got overrides={overrides}",
        )

        # The avoid-cab entry should be present
        avoids = mem.get("leg_avoid_modes", {})
        self._assert(
            "powai->bkc" in avoids and "cab" in avoids["powai->bkc"].get("avoid", []),
            f"avoid-cab should be set, got leg_avoid_modes={avoids}",
        )

        # Reverse direction: force metro on the same leg should clear the avoid-cab
        self._chat("use metro from powai to bkc", BASE_MEETINGS)
        r2 = self._chat("plan my day", BASE_MEETINGS)
        mem2 = r2.get("memory", {})
        avoids2 = mem2.get("leg_avoid_modes", {}).get("powai->bkc", {}).get("avoid", [])
        overrides2 = mem2.get("leg_overrides", {})

        # If metro was forced and cab was in avoid list, cab should still be in avoid (no conflict).
        # But if metro was in avoid list, it should have been removed.
        # Main check: force metro override exists
        self._assert(
            "powai->bkc" in overrides2 and overrides2["powai->bkc"].get("mode") == "metro",
            f"metro override should be set, got overrides={overrides2}",
        )

    def case_contextual_route_followup(self):
        """After asking about a leg via plan_query, a contextual route question
        like 'is there a bus i can use in that route?' should resolve to the
        same leg rather than falling through to explain."""
        self._reset()
        # 1. generate a plan
        plan_resp = self._chat("plan my day", BASE_MEETINGS)
        self._assert(plan_resp["result"].get("status") != "failed", "plan should succeed")
        # 2. ask about BKC→Bandra leg (plan_query)
        pq = self._chat("what are we using for bkc to bandra?", BASE_MEETINGS)
        self._assert(pq["decision"]["action"] == "plan_query", "should be plan_query")
        # 3. contextual follow-up with no explicit locations
        ctx = self._chat("is there a bus i can use in that route?", BASE_MEETINGS)
        self._assert(
            ctx["decision"]["action"] == "check_route_availability",
            f"expected check_route_availability but got {ctx['decision']['action']}"
        )
        result = ctx.get("result", {})
        self._assert("BKC" in result.get("message", ""), "result should mention BKC")
        self._assert("Bandra" in result.get("message", ""), "result should mention Bandra")

    def case_modeless_followup_apply(self):
        """After a route availability check, 'can i use that?' (no explicit mode)
        should apply the previously discussed mode to the leg.
        Also: 'can i use that instead of the metro?' should apply the route_query
        mode, not the mode mentioned after 'instead of'."""
        self._reset()
        # 1. generate a plan
        plan_resp = self._chat("plan my day", BASE_MEETINGS)
        self._assert(plan_resp["result"].get("status") != "failed", "plan should succeed")
        # 2. ask about Powai→BKC (plan_query)
        pq = self._chat("what are we using from powai to bkc?", BASE_MEETINGS)
        self._assert(pq["decision"]["action"] == "plan_query", "should be plan_query")
        # 3. ask about bus availability (route_check, sets mode=bus)
        rc = self._chat("is there a bus i can use for that route?", BASE_MEETINGS)
        self._assert(rc["decision"]["action"] == "check_route_availability", "should be route_check")
        # 4. "instead of the metro" — should apply bus, NOT metro
        apply_resp = self._chat("can i use that instead of the metro?", BASE_MEETINGS)
        self._assert(
            apply_resp["decision"]["action"] == "plan",
            f"expected plan but got {apply_resp['decision']['action']}"
        )
        overrides = apply_resp.get("memory", {}).get("leg_overrides", {})
        key = "powai->bkc"
        self._assert(key in overrides, f"expected override key '{key}' in {overrides}")
        self._assert(overrides[key]["mode"] == "bus",
                     f"'instead of metro' should apply bus, got {overrides[key]['mode']}")
        # 5. reset and test mode-less followup ("can i use that?")
        self._reset()
        self._chat("plan my day", BASE_MEETINGS)
        self._chat("is there a bus from powai to bkc?", BASE_MEETINGS)
        apply2 = self._chat("can i use that?", BASE_MEETINGS)
        self._assert(apply2["decision"]["action"] == "plan", "mode-less followup should plan")
        overrides2 = apply2.get("memory", {}).get("leg_overrides", {})
        self._assert(key in overrides2, f"expected override key '{key}' in {overrides2}")
        self._assert(overrides2[key]["mode"] == "bus", f"expected bus, got {overrides2[key]['mode']}")

    def case_global_avoid_clears_leg_override(self):
        """When user globally avoids a mode, any leg override forcing that mode
        should be auto-cleared so the planner doesn't fail."""
        self._reset()
        # 1. plan, then force bus on Powai→BKC via followup
        self._chat("plan my day", BASE_MEETINGS)
        self._chat("is there a bus from powai to bkc?", BASE_MEETINGS)
        apply_resp = self._chat("can i use that?", BASE_MEETINGS)
        overrides = apply_resp.get("memory", {}).get("leg_overrides", {})
        self._assert("powai->bkc" in overrides, "bus override should be set")
        # 2. globally avoid bus
        avoid_resp = self._chat("i dont want to use the bus", BASE_MEETINGS)
        mem = avoid_resp.get("memory", {})
        self._assert("bus" in mem.get("avoid_modes", []), "bus should be in avoid_modes")
        self._assert("powai->bkc" not in mem.get("leg_overrides", {}),
                     "leg override forcing bus should be cleared after global avoid bus")
        # 3. replan should succeed (no conflict)
        replan = self._chat("replan my day", BASE_MEETINGS)
        self._assert(replan["result"].get("status") != "failed",
                     f"replan should succeed, got {replan['result']}")

    def case_plan_schedule_question(self):
        """Questions like 'what time do I leave from Bandra?' should return
        the departure time from the plan, not dump the full plan."""
        self._reset()
        self._chat("plan my day", BASE_MEETINGS)
        # Departure question
        dep = self._chat("what time do i have to leave from bandra?", BASE_MEETINGS)
        self._assert(dep["decision"]["action"] == "plan_query",
                     f"expected plan_query but got {dep['decision']['action']}")
        msg = dep["result"].get("message", "")
        self._assert("Bandra" in msg, "answer should mention Bandra")
        self._assert("14:" in msg, "answer should mention departure time around 14:xx")

    def case_contextual_other_options(self):
        """After asking about a leg's mode, 'are there other options?' should
        list alternatives on that leg, not dump the plan."""
        self._reset()
        self._chat("plan my day", BASE_MEETINGS)
        # Ask about Powai→BKC (exists in BASE_MEETINGS plan)
        pq = self._chat("what are we using from powai to bkc?", BASE_MEETINGS)
        self._assert(pq["decision"]["action"] == "plan_query", "should be plan_query")
        # Follow up with 'are there other options?'
        ctx = self._chat("are there other options?", BASE_MEETINGS)
        self._assert(
            ctx["decision"]["action"] == "check_route_availability",
            f"expected check_route_availability but got {ctx['decision']['action']}"
        )
        result = ctx.get("result", {})
        self._assert("Powai" in result.get("message", ""), "should mention Powai")
        self._assert("BKC" in result.get("message", ""), "should mention BKC")

    def case_clear_and_reset_helpers(self):
        self._reset()

        self._chat("avoid all buses today", BASE_MEETINGS)

        clear_pref = requests.post(f"{self.base_url}/clear_preferences", timeout=10)
        self._assert(clear_pref.status_code == 200, "/clear_preferences should return 200")
        self._assert(clear_pref.json().get("avoid_modes") == [], "clear_preferences should clear avoid_modes")

        requests.post(
            f"{self.base_url}/set_leg_override",
            json={"from": "Powai", "to": "BKC", "mode": "bus", "reason": "reset check"},
            timeout=10,
        )
        reset = requests.post(f"{self.base_url}/reset_state", timeout=10)
        self._assert(reset.status_code == 200, "/reset_state should return 200")

        memory_probe = self._chat("yes", BASE_MEETINGS).get("memory", {})
        self._assert(memory_probe.get("avoid_modes") == [], "reset_state should clear avoid_modes")
        self._assert(memory_probe.get("leg_overrides") == {}, "reset_state should clear leg_overrides")
        self._assert(memory_probe.get("leg_avoid_modes") == {}, "reset_state should clear leg_avoid_modes")

    def run(self):
        print("\n=== Running Feature Suite (Sequential) ===")
        print(f"Target base URL: {self.base_url}\n")

        try:
            ping = requests.get(f"{self.base_url}/health", timeout=5)
            self._assert(ping.status_code == 200, "health check failed before suite run")
        except Exception as exc:
            print(f"[FATAL] Cannot reach app at {self.base_url}: {exc}")
            print("Start the app first, for example:")
            print("  .\\.venv\\Scripts\\python -m uvicorn main:app --host 127.0.0.1 --port 8001")
            return 2

        self._run_case("health_and_locations", self.case_health_and_locations)
        self._run_case("csv_upload", self.case_csv_upload)
        self._run_case("basic_plan", self.case_basic_plan)
        self._run_case("global_preference_and_replan", self.case_global_preference_and_replan)
        self._run_case("leg_avoid_constraint", self.case_leg_avoid_constraint)
        self._run_case("route_qna_and_followup_apply", self.case_route_qna_and_followup_apply)
        self._run_case("question_not_treated_as_override", self.case_question_not_treated_as_override)
        self._run_case("unclear_fallback", self.case_unclear_fallback)
        self._run_case("itinerary_train_listing", self.case_itinerary_train_listing)
        self._run_case("what_if_confirm_and_reject", self.case_what_if_confirm_and_reject)
        self._run_case("no_pending_confirmation_guard", self.case_no_pending_confirmation_guard)
        self._run_case("preference_fallback_infeasible", self.case_preference_fallback_infeasible)
        self._run_case("formatter_cab_aggregation", self.case_formatter_cab_aggregation)
        self._run_case("constraint_conflict_resolution", self.case_constraint_conflict_resolution)
        self._run_case("contextual_route_followup", self.case_contextual_route_followup)
        self._run_case("modeless_followup_apply", self.case_modeless_followup_apply)
        self._run_case("global_avoid_clears_leg_override", self.case_global_avoid_clears_leg_override)
        self._run_case("plan_schedule_question", self.case_plan_schedule_question)
        self._run_case("contextual_other_options", self.case_contextual_other_options)
        self._run_case("clear_and_reset_helpers", self.case_clear_and_reset_helpers)

        print("\n=== Feature Suite Summary ===")
        print(f"Passed: {self.passed}")
        print(f"Failed: {self.failed}")

        if self.failed_names:
            print("Failed tests:")
            for name in self.failed_names:
                print(f" - {name}")
            return 1

        print("All feature tests passed.")
        return 0


if __name__ == "__main__":
    suite = FeatureSuite(base_url=os.getenv("FEATURE_SUITE_BASE_URL", "http://127.0.0.1:8001"))
    raise SystemExit(suite.run())
