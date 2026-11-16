import random

def simulate_microplastic():
    # Fluorescence-like behavior
    base = random.randint(20, 60)
    spike = random.choice([0, 0, 0, random.randint(70, 95)])
    return max(base, spike)

def ultrasonic_decision(distance):
    if distance < 20:
        return "STOP"
    elif distance < 50:
        return "TURN"
    return "FORWARD"
