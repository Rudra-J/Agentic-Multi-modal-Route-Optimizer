PEAK_HOURS = [(8, 10), (17, 20)]


def is_peak(hour):
    for start, end in PEAK_HOURS:
        if start <= hour <= end:
            return True
    return False


def compute_risk(legs, start_hour):
    risk = 0.0
    current_hour = start_hour

    for leg in legs:
        mode = leg["mode"]

        if mode == "bus" and is_peak(current_hour):
            risk += 0.2

        if mode == "train" and is_peak(current_hour):
            risk += 0.15

        if mode == "cab":
            risk += 0.1

        # advance time
        current_hour += leg["time"] / 60

    return min(1.0, risk)
