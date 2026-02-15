"""
Real-world Mumbai transport network with realistic travel times and costs.
Based on actual BEST (buses), local trains, Metro, and cab services.
"""

# Base routes (will be made bidirectional below)
_BASE_ROUTES = [
    # Format: (from, to, duration_minutes, mode, cost_rupees, reliability_score 0-1)
    
    # === METRO (Line 1 & 2A) ===
    ("Andheri", "Malad", 5, "metro", 10, 0.95),
    ("Malad", "Borivali", 8, "metro", 15, 0.95),
    ("Andheri", "BKC", 28, "metro", 30, 0.92),  # Via transfer
    ("Andheri", "Powai", 35, "metro", 35, 0.90),  # Via transfer
    ("BKC", "Powai", 12, "metro", 20, 0.93),
    ("BKC", "Lower Parel", 18, "metro", 25, 0.91),
    ("Lower Parel", "Bandra", 15, "metro", 20, 0.93),
    ("Bandra", "Dadar", 12, "metro", 25, 0.92),
    ("Dadar", "CST", 15, "metro", 20, 0.94),
    ("CST", "Colaba", 8, "metro", 15, 0.95),
    
    # === Local Trains (Fast/Main lines) ===
    ("Andheri", "Dadar", 25, "train", 10, 0.88),  # Western line
    ("Dadar", "CST", 12, "train", 8, 0.87),       # Central line
    ("Powai", "Thane", 35, "train", 15, 0.85),    # Central line
    ("Thane", "Navi Mumbai", 45, "train", 20, 0.82),
    ("CST", "Navi Mumbai", 50, "train", 25, 0.84),
    ("Andheri", "Borivali", 20, "train", 10, 0.86),
    ("Borivali", "Thane", 50, "train", 15, 0.83),
    
    # === BEST Buses (limited, major corridors only) ===
    ("Andheri", "BKC", 45, "bus", 20, 0.75),      # Traffic prone
    ("Andheri", "Malad", 15, "bus", 10, 0.80),
    ("BKC", "Powai", 35, "bus", 15, 0.72),        # Heavy traffic
    ("Powai", "Thane", 55, "bus", 25, 0.70),      # Very traffic prone
    ("Bandra", "Dadar", 35, "bus", 15, 0.75),
    ("Dadar", "CST", 30, "bus", 10, 0.78),
    ("CST", "Colaba", 25, "bus", 10, 0.80),
    
    # === Cabs (Uber/Ola) - based on distance & traffic ===
    ("Andheri", "BKC", 35, "cab", 150, 0.98),
    ("Andheri", "Powai", 40, "cab", 180, 0.97),
    ("BKC", "Powai", 30, "cab", 120, 0.98),
    ("BKC", "Lower Parel", 25, "cab", 100, 0.98),
    ("Lower Parel", "Bandra", 20, "cab", 90, 0.98),
    ("Bandra", "Dadar", 15, "cab", 70, 0.99),
    ("Dadar", "CST", 20, "cab", 80, 0.98),
    ("CST", "Colaba", 10, "cab", 50, 0.99),
    ("Andheri", "Borivali", 25, "cab", 110, 0.98),
    ("Borivali", "Thane", 30, "cab", 130, 0.97),
    ("Powai", "Thane", 40, "cab", 160, 0.97),
    ("Thane", "Navi Mumbai", 50, "cab", 200, 0.96),
    ("Malad", "Borivali", 20, "cab", 80, 0.99),
]

# Make routes bidirectional
MUMBAI_ROUTES = _BASE_ROUTES.copy()
for route in _BASE_ROUTES:
    from_loc, to_loc, duration, mode, cost, reliability = route
    # Add reverse route with same properties
    reverse_route = (to_loc, from_loc, duration, mode, cost, reliability)
    if reverse_route not in MUMBAI_ROUTES:
        MUMBAI_ROUTES.append(reverse_route)

# Location coordinates (for future map integration)
LOCATION_COORDS = {
    "Andheri": (19.1136, 72.8697),
    "Malad": (19.1823, 72.8389),
    "Borivali": (19.2298, 72.8135),
    "BKC": (19.0760, 72.8295),
    "Powai": (19.1136, 72.9260),
    "Lower Parel": (19.0176, 72.8194),
    "Bandra": (19.0596, 72.8295),
    "Dadar": (19.0176, 72.8530),
    "CST": (18.9404, 72.8349),
    "Colaba": (18.9563, 72.8338),
    "Thane": (19.2183, 72.9781),
    "Navi Mumbai": (19.0330, 73.0297),
}

# Peak hours for each day (affects reliability)
PEAK_HOURS = {
    "morning": (7, 11),    # 7 AM - 11 AM
    "evening": (17, 21),   # 5 PM - 9 PM
}

LOCATION_NAMES = {
    "Andheri": "Andheri Station (Western Mumbai)",
    "Malad": "Malad Station",
    "Borivali": "Borivali (North Mumbai)",
    "BKC": "Bandra Kurla Complex (Business District)",
    "Powai": "Powai Tech District",
    "Lower Parel": "Lower Parel Corporate Zone",
    "Bandra": "Bandra Station (Western Suburbs)",
    "Dadar": "Dadar Junction",
    "CST": "Chhatrapati Shivaji Terminus (Downtown)",
    "Colaba": "Colaba (South Mumbai)",
    "Thane": "Thane Station (Eastern Suburbs)",
    "Navi Mumbai": "Navi Mumbai Hub",
}

def get_route_info(from_loc, to_loc, mode="any"):
    """Get route information between two locations"""
    matching_routes = [r for r in MUMBAI_ROUTES 
                       if r[0] == from_loc and r[1] == to_loc and 
                       (mode == "any" or r[3] == mode)]
    return matching_routes

def estimate_traffic_multiplier(start_hour):
    """Estimate traffic impact based on hour of day"""
    morning_start, morning_end = PEAK_HOURS["morning"]
    evening_start, evening_end = PEAK_HOURS["evening"]
    
    if morning_start <= start_hour <= morning_end:
        return 1.5  # 50% increase during morning peak
    elif evening_start <= start_hour <= evening_end:
        return 1.6  # 60% increase during evening peak
    elif 11 <= start_hour <= 17:
        return 0.9  # 10% decrease during off-peak
    else:
        return 1.0  # Normal night traffic

def adjust_for_weather(mode, weather="clear"):
    """Adjust times based on weather conditions"""
    weather_multipliers = {
        "clear": 1.0,
        "light_rain": 1.2,
        "heavy_rain": 1.5,
        "extreme_weather": 2.0,
    }
    return weather_multipliers.get(weather, 1.0)

def get_location_name(location):
    """Get full name and description of location"""
    return LOCATION_NAMES.get(location, location)

def get_location_coords(location):
    """Get GPS coordinates for a location"""
    return LOCATION_COORDS.get(location)

def get_all_locations():
    """Get list of all available locations"""
    return list(LOCATION_COORDS.keys())
