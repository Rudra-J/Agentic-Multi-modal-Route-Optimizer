import networkx as nx
from data.mumbai_routes import MUMBAI_ROUTES, estimate_traffic_multiplier, adjust_for_weather

# Build graph from real Mumbai data
G = nx.MultiDiGraph()

for from_loc, to_loc, duration, mode, cost, reliability in MUMBAI_ROUTES:
    # Add edge in both directions for better connectivity
    G.add_edge(
        from_loc, 
        to_loc, 
        duration=duration, 
        mode=mode, 
        cost=cost,
        reliability=reliability
    )
    # Add reverse edge with same properties (assuming routes work both ways)
    G.add_edge(
        to_loc,
        from_loc,
        duration=duration,
        mode=mode,
        cost=cost,
        reliability=reliability
    )

ALPHA = 0.4          # Cost weight (lower = prioritize time)
CAB_PENALTY = 50     # Applied when prefer_public=True


def score_path(path, transport_mode="any", avoid_modes=None, weather="clear", current_hour=12):
    """
    Score a path with traffic and weather adjustments
    """
    legs = []
    total_time = 0
    total_cost = 0

    for i in range(len(path) - 1):
        u = path[i]
        v = path[i + 1]

        candidates = []

        for edge in G.get_edge_data(u, v).values():

            # HARD FILTER: avoid modes
            if avoid_modes and edge["mode"] in avoid_modes:
                continue

            # HARD FILTER: transport mode
            if transport_mode == "cab_only" and edge["mode"] != "cab":
                continue

            if transport_mode == "public_only" and edge["mode"] == "cab":
                continue

            candidates.append(edge)

        if not candidates:
            return None

        # Choose best option (weighted by reliability during peak hours)
        def calculate_score(edge):
            base_score = edge["duration"]
            
            # Adjust for traffic based on time of day
            if edge["mode"] in ["bus", "cab"]:
                traffic_mult = estimate_traffic_multiplier(current_hour)
                base_score *= traffic_mult
            
            # Reduce score for more reliable modes
            base_score *= (2 - edge["reliability"])
            
            return base_score

        edge = min(candidates, key=calculate_score)

        # Apply weather adjustment
        adjusted_duration = edge["duration"] * adjust_for_weather(edge["mode"], weather)

        legs.append({
            "from": u,
            "to": v,
            "mode": edge["mode"],
            "time": int(adjusted_duration),
            "cost": edge["cost"],
            "reliability": f"{int(edge['reliability'] * 100)}%"
        })

        total_time += adjusted_duration
        total_cost += edge["cost"]

    score = total_time + ALPHA * total_cost

    return {
        "legs": legs,
        "total_time": int(total_time),
        "total_cost": total_cost,
        "score": score
    }


def find_route(start, end, transport_mode="any", avoid_modes=None, weather="clear", current_hour=12):
    """
    Find best route between two locations using real Mumbai data.
    
    If no direct route exists, automatically chains legs through intermediate stops.
    For example: Andheri -> Malad -> BKC will be found if no direct Andheri->BKC exists.
    """
    if avoid_modes is None:
        avoid_modes = set()

    try:
        # all_simple_paths finds ALL possible paths between start and end
        # If direct edge doesn't exist, it chains through intermediate nodes
        paths = list(nx.all_simple_paths(G, start, end, cutoff=5))
    except nx.NetworkXNoPath:
        return None

    if not paths:
        return None

    best = None

    for p in paths:
        candidate = score_path(p, transport_mode, avoid_modes, weather, current_hour)

        if candidate is None:
            continue

        if best is None or candidate["score"] < best["score"]:
            best = candidate

    if best is None:
        return None

    return best
