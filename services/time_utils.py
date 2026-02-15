from datetime import datetime

def to_minutes(t: str):
    dt = datetime.strptime(t, "%H:%M")
    return dt.hour * 60 + dt.minute
