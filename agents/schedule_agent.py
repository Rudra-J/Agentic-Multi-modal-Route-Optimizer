def schedule(meetings):
    return sorted(meetings, key=lambda x: x["start_time"])