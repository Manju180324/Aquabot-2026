import math
import random

def update_gps(lat, lon):
    lat += random.uniform(-0.00001, 0.00001)
    lon += random.uniform(-0.00001, 0.00001)
    return lat, lon

def distance_m(prev, curr):
    return math.sqrt((curr[0]-prev[0])**2 + (curr[1]-prev[1])**2) * 111139