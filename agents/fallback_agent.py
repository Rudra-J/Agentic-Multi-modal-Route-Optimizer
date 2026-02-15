import random

PROVIDERS = ["Uber", "Ola"]

def emergency_cab(from_loc, to_loc):
    provider = random.choice(PROVIDERS)

    # mocked values
    return {
        "from": from_loc,
        "to": to_loc,
        "mode": "cab",
        "provider": provider,
        "time": 45,
        "cost": 300,
        "fallback": True
    }
