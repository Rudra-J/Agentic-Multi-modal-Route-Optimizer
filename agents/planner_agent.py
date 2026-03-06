from agents.schedule_agent import schedule
from agents.route_agent import find_route
from agents.risk_agent import compute_risk
from services.time_utils import to_minutes
from agents.fallback_agent import emergency_cab
from services.output_formatter import format_plan


BUFFER = 10


def plan_day(meetings, transport_mode="any", avoid_modes=None, leg_overrides=None, leg_avoid_modes=None):
    if avoid_modes is None:
        avoid_modes = set()
    if leg_overrides is None:
        leg_overrides = {}
    if leg_avoid_modes is None:
        leg_avoid_modes = {}
    
    # Convert Meeting objects to dictionaries if needed
    if meetings and hasattr(meetings[0], '__dict__'):
        meetings = [m.dict() if hasattr(m, 'dict') else m.__dict__ for m in meetings]
    
    meetings = schedule(meetings)

    itinerary = []
    current_time = to_minutes(meetings[0]['start_time'])

    for i in range(len(meetings) - 1):
        src = meetings[i]
        dst = meetings[i + 1]

        # Account for current meeting duration before travel
        meeting_duration = src.get('duration_minutes', 30)
        travel_start_time = current_time + meeting_duration

        # Check for leg override (normalize keys to avoid casing/whitespace mismatch)
        leg_key = f"{src['location'].strip().lower()}->{dst['location'].strip().lower()}"
        override = leg_overrides.get(leg_key)
        
        if override:
            # normalize common user-provided mode strings to the route_agent expectations
            user_mode = (override.get("mode") or "").strip().lower()
            if user_mode in ("cab", "taxi"):
                route_mode = "cab_only"
            elif user_mode in ("public", "public_only"):
                route_mode = "public_only"
            elif user_mode in ("metro", "train", "bus"):
                route_mode = user_mode
            elif user_mode in ("any", ""):
                route_mode = transport_mode
            else:
                route_mode = user_mode
        else:
            route_mode = transport_mode

        # Calculate current hour for traffic adjustment (based on when travel starts)
        start_hour = travel_start_time / 60

        # Combine global avoid modes with leg-specific avoid modes
        combined_avoid_modes = set(avoid_modes)
        leg_avoid_constraint = leg_avoid_modes.get(leg_key) if leg_key in leg_avoid_modes else None
        if leg_avoid_constraint:
            combined_avoid_modes.update(leg_avoid_constraint.get("avoid", []))

        # initial route
        route = find_route(
                    src['location'],
                    dst['location'],
                    transport_mode=route_mode,
                    avoid_modes=combined_avoid_modes,
                    current_hour=start_hour
                )

        if route is None:
            return {"status": "failed", "reason": "No feasible route"}

        risk = compute_risk(route["legs"], start_hour)

        # Skip risk-based rerouting if user explicitly overrode this leg
        if risk > 0.3 and transport_mode == "any" and not override:
            route = find_route(src['location'], dst['location'], "public_only", avoid_modes=combined_avoid_modes, current_hour=start_hour)

            if route is None:
                fallback = emergency_cab(src['location'], dst['location'])

                route = {
                    "legs": [fallback],
                    "total_time": fallback["time"],
                    "total_cost": fallback["cost"],
                    "score": fallback["time"] + 0.5 * fallback["cost"]
                }
        
        risk = compute_risk(route["legs"], start_hour)

        travel_time = route["total_time"]
        arrival_time = travel_start_time + travel_time
        next_start = to_minutes(dst['start_time'])

        if arrival_time + BUFFER > next_start:
            # If user explicitly overrode this leg and it causes infeasibility,
            # return details so UI can offer a one-click revert.
            if override:
                return {
                    "status": "failed",
                    "reason": f"Cannot reach {dst['location']} in time",
                    "failed_override": {
                        "from": src['location'],
                        "to": dst['location'],
                        "mode": override.get('mode'),
                        "reason": override.get('reason', "")
                    },
                    "suggest_clear_override": True
                }

            return {
                "status": "failed",
                "reason": f"Cannot reach {dst['location']} in time"
            }

        itinerary.append({
            "from": src['location'],
            "to": dst['location'],
            "route": route,
            "delay_probability": risk,
            "start_time": travel_start_time,
            "end_time": arrival_time
        })

        current_time = next_start

    return format_plan(itinerary)


# Debug helper
def debug_route(route):
    """Print route details for debugging"""
    print("\n========== DEBUG: Route Object ==========")
    print(f"Route type: {type(route)}")
    print(f"Route keys: {route.keys() if isinstance(route, dict) else 'N/A'}")
    print(f"Has 'route' key: {'route' in route if isinstance(route, dict) else 'N/A'}")
    if isinstance(route, dict) and 'route' in route:
        print(f"Route.route type: {type(route['route'])}")
        print(f"Route.route length: {len(route['route'])}")
        print(f"First leg: {route['route'][0] if route['route'] else 'empty'}")
    print(f"Full route object: {route}")
    print("========== END DEBUG ==========\n")
    return route

