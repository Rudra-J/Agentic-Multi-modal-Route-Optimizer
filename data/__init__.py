"""
City data loader - easily add more cities
"""

def load_city_data(city_name):
    """Load routing data for a specific city"""
    if city_name.lower() == "mumbai":
        from data.mumbai_routes import MUMBAI_ROUTES, LOCATION_COORDS, LOCATION_NAMES
        return {
            "routes": MUMBAI_ROUTES,
            "coords": LOCATION_COORDS,
            "names": LOCATION_NAMES
        }
    else:
        raise ValueError(f"City '{city_name}' data not available")
