from agents.planner_agent import plan_day


def execute(decision: dict, state, meetings):
    """
    Executes the action chosen by the LLM brain.
    """

    action = decision.get("action")

    if action == "update_preferences":
        for mode in decision.get("avoid_modes", []):
            state.add_avoid_mode(mode)

        state.add_note(decision.get("reason", ""))

        return {
            "status": "preferences_updated",
            "avoid_modes": list(state.avoid_modes)
        }

    if action == "edit_leg":
        from_loc = decision.get("from_location")
        to_loc = decision.get("to_location")
        mode = decision.get("transport_mode")
        reason = decision.get("reason", "")

        state.set_leg_override(from_loc, to_loc, mode, reason)

        return {
            "status": "leg_override_set",
            "from": from_loc,
            "to": to_loc,
            "mode": mode,
            "reason": reason
        }

    if action == "clear_leg_override":
        from_loc = decision.get("from_location")
        to_loc = decision.get("to_location")

        state.clear_leg_override(from_loc, to_loc)

        return {
            "status": "leg_override_cleared",
            "from": from_loc,
            "to": to_loc
        }

    if action == "clear_leg_preference":
        from_loc = decision.get("from_location")
        to_loc = decision.get("to_location")

        had_override = state.get_leg_override(from_loc, to_loc) is not None
        had_avoid = state.get_leg_avoid_modes(from_loc, to_loc) is not None

        state.clear_leg_override(from_loc, to_loc)
        state.clear_leg_avoid_modes(from_loc, to_loc)

        cleared = []
        if had_override:
            cleared.append("mode override")
        if had_avoid:
            cleared.append("avoid constraint")

        summary = ", ".join(cleared) if cleared else "no active preferences"

        return {
            "status": "leg_preferences_cleared",
            "from": from_loc,
            "to": to_loc,
            "cleared": summary
        }

    if action == "avoid_mode_on_leg":
        from_loc = decision.get("from_location")
        to_loc = decision.get("to_location")
        avoid_modes = decision.get("avoid_modes", [])
        reason = decision.get("reason", "")

        state.set_leg_avoid_modes(from_loc, to_loc, avoid_modes, reason)

        return {
            "status": "leg_avoid_modes_set",
            "from": from_loc,
            "to": to_loc,
            "avoid": avoid_modes,
            "reason": reason
        }
        
    if action == "plan":
        plan = plan_day(
            meetings,
            avoid_modes=state.avoid_modes,
            leg_overrides=state.leg_overrides,
            leg_avoid_modes=state.leg_avoid_modes
        )

        print("\n[DEBUG action_agent] Plan result:")
        print(f"  Plan type: {type(plan)}")
        print(f"  Plan keys: {plan.keys() if isinstance(plan, dict) else 'N/A'}")
        print(f"  Has 'route' key: {'route' in plan if isinstance(plan, dict) else 'N/A'}")
        if isinstance(plan, dict) and 'route' in plan:
            print(f"  Route type: {type(plan['route'])}")
            print(f"  Route length: {len(plan['route'])}")
            if plan['route']:
                print(f"  First leg: {plan['route'][0]}")
        print(f"  Full plan: {plan}\n")

        state.last_plan = plan
        return plan


    if action == "replan":
        plan = plan_day(
            meetings,
            avoid_modes=state.avoid_modes,
            leg_overrides=state.leg_overrides,
            leg_avoid_modes=state.leg_avoid_modes
        )

        print("\n[DEBUG action_agent] Replan result:")
        print(f"  Plan type: {type(plan)}")
        print(f"  Plan keys: {plan.keys() if isinstance(plan, dict) else 'N/A'}")
        print(f"  Full plan: {plan}\n")

        state.last_plan = plan
        return plan

    if action == "explain":
        if state.last_plan is None:
            return {"error": "No plan available yet"}
        return state.last_plan

    if action == "unclear":
        return {
            "status": "unclear",
            "message": "I didn't quite understand that request. Could you rephrase it? For example, you can say 'plan my day', 'avoid trains', 'use cab from Powai to BKC', or 'is there a bus from X to Y?'"
        }

    return {"status": "no_action_taken"}
