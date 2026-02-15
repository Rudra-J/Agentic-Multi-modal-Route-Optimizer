def minutes_to_hm(minutes):
    h = minutes // 60
    m = minutes % 60
    return f"{h}h{m}m"


def minutes_to_time(minutes):
    """Convert minutes since midnight to HH:MM format"""
    h = int(minutes // 60)
    m = int(minutes % 60)
    return f"{h:02d}:{m:02d}"


def format_plan(itinerary):
    total_cost = 0
    total_time = 0
    max_risk = 0
    fallback = None
    sections = []

    for leg_block in itinerary:
        route = leg_block["route"]
        section_legs = []
        current_time = leg_block["start_time"]
        section_cost = 0
        section_time = 0

        for leg in route["legs"]:
            leg_start_time = minutes_to_time(current_time)
            leg_end_time = minutes_to_time(current_time + leg["time"])
            
            section_legs.append({
                "from": leg["from"],
                "to": leg["to"],
                "mode": leg["mode"],
                "time": leg["time"],
                "cost": leg["cost"],
                "reliability": leg["reliability"],
                "start_time": leg_start_time,
                "end_time": leg_end_time
            })
            
            current_time += leg["time"]
            total_cost += leg["cost"]
            total_time += leg["time"]
            section_cost += leg["cost"]
            section_time += leg["time"]

            if leg.get("fallback"):
                fallback = f"{leg.get('provider')} from {leg['from']}"

        # Create section with origin-destination information
        sections.append({
            "from": leg_block["from"],
            "to": leg_block["to"],
            "legs": section_legs,
            "section_time": minutes_to_hm(section_time),
            "section_cost": section_cost,
            "section_start": minutes_to_time(leg_block["start_time"]),
            "section_end": minutes_to_time(leg_block["end_time"])
        })

        max_risk = max(max_risk, leg_block["delay_probability"])

    # Ensure minimum delay risk of 5%
    min_delay_risk = max(0.05, max_risk)

    return {
        "sections": sections,
        "route": [leg for section in sections for leg in section["legs"]],
        "total_cost": total_cost,
        "total_time": minutes_to_hm(total_time),
        "delay_risk": f"{int(min_delay_risk * 100)}%",
        "fallback": fallback
    }
