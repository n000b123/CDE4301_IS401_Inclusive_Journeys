import os
import requests
from dotenv import load_dotenv
import numpy as np
import pandas as pd
from scipy.spatial import KDTree
from datetime import datetime, timezone, timedelta

mrt_df = pd.read_csv("data/TrainStationChineseNames.csv")
mrt_dict = {
    (row["mrt_station_english"].lower(), row["stn_code"][:2]): row["stn_code"]
    for _, row in mrt_df.iterrows()
}

def get_mrt_station_code(mrt_station_name, line_abbrev):
    return mrt_dict.get((mrt_station_name.lower(), line_abbrev.upper()))
    
# LTA api data
# load variables from .env
load_dotenv()
LTA_API_KEY = os.getenv("LTA_API_KEY")
BASE_URL = "https://datamall2.mytransport.sg/ltaodataservice"

HEADERS = {
    "AccountKey": LTA_API_KEY,
    "accept": "application/json"
}

# return bus stop code for a bus stop coordinate
def load_bus_stops_with_tree():
    """Fetch all bus stops and build a KDTree for fast coordinate lookup."""
    all_stops = []
    skip = 0

    while True:
        resp = requests.get(f"{BASE_URL}/BusStops?$skip={skip}", headers=HEADERS)
        if resp.status_code != 200:
            print(f"Error fetching BusStops: {resp.status_code}")
            break
        data = resp.json().get("value", [])
        if not data:
            break
        all_stops.extend(data)
        skip += 500

    # Build KDTree using (Latitude, Longitude)
    coords = np.array([(stop["Latitude"], stop["Longitude"]) for stop in all_stops])
    tree = KDTree(coords)

    return all_stops, tree

def find_nearest_bus_stop_kdtree(coord, all_stops, tree, radius_m=100):
    """
    Find the nearest bus stop (within radius_m) using KDTree.
    Returns the full stop record: Description, BusStopCode, etc.
    """
    lat, lon = coord
    deg_per_meter = 1 / 111_320  # ~111.32 km per degree (Singapore)
    radius_deg = radius_m * deg_per_meter

    dist, idx = tree.query([lat, lon])
    nearest = all_stops[idx]

    # Convert approximate degree distance to meters
    if dist / deg_per_meter <= radius_m:
        return nearest
    else:
        return None

def get_bus_arrival(bus_stop_code):
    url = f"{BASE_URL}/v3/BusArrival"
    resp = requests.request("GET", url, headers=HEADERS, params={"BusStopCode": bus_stop_code})
    return resp.json()

def get_train_crowd_density_real_time(station_code):
    url = f"{BASE_URL}/PCDRealTime"
    train_line = station_code[:2] + "L"
    resp = requests.request("GET", url, headers=HEADERS, params={"TrainLine": train_line})
    platforms = resp.json().get("value", [])
    station_platform = [p for p in platforms if p.get("Station") == station_code]
    crowd_level_map = {"l": "Low", "m": "Moderate", "h": "High", "na": "NA"}
    crowd_level = crowd_level_map.get(station_platform[0]["CrowdLevel"])
    return crowd_level

def get_train_service_alerts(train_line):
    url = f"{BASE_URL}/TrainServiceAlerts"
    resp = requests.request("GET", url, headers=HEADERS)
    data = resp.json()

    alerts = data.get("value", [])
    if not alerts:
        return "No data available"

    if alerts.get("Status") == 1:
        return "NA"

    affected_segments = alerts.get("AffectedSegments", [])
    for seg in affected_segments:
        if seg.get("Line") == train_line:
            msg = alerts.get("Message", "Disruption detected.")
            direction = seg.get("Direction", "")
            stations = ", ".join(seg.get("Stations", []))
            return f"⚠️ {msg}\nAffected: {train_line} ({direction}) → {stations}"
        

SG_TZ = timezone(timedelta(hours=8))  
def parse_datetime(dt_str):
    if "+" in dt_str: 
        dt = datetime.fromisoformat(dt_str)
        return dt.astimezone(SG_TZ)
    else: 
        dt = datetime.fromisoformat(dt_str)
        return dt.replace(tzinfo=SG_TZ)
    

def get_train_platform_forecast(station_code, target_time):
    target_time = parse_datetime(target_time)
    url = f"{BASE_URL}/PCDForecast"
    train_line = station_code[:2] + "L"
    resp = requests.request("GET", url, headers=HEADERS, params={"TrainLine": train_line})
    data = resp.json().get("value", [])

    nearest_entry = None
    min_diff = float("inf")

    for day in data:
        for station in day.get("Stations", []):
            if station.get("Station") == station_code:
                for interval in station.get("Interval", []):
                    start_str = interval.get("Start")
                    if not start_str:
                        continue
                    start_time = parse_datetime(start_str)
                    diff = abs((start_time - target_time).total_seconds())
                    if diff < min_diff:
                        min_diff = diff
                        nearest_entry = {
                            "station": station_code,
                            "nearest_forecast_time": start_time.strftime("%H:%M"),
                            "requested_time": target_time.strftime("%H:%M"),
                            "crowd_level": interval.get("CrowdLevel")
                        }

    if not nearest_entry:
        return {"error": f"No forecast data for station {station_code}"}

    crowd_map = {"l": "Low", "m": "Medium", "h": "High"}
    nearest_entry["crowd_level"] = crowd_map.get(nearest_entry["crowd_level"], "Unknown")

    return nearest_entry

#print(get_train_platform_forecast("CC14", "2025-10-13T15:17:13+08:00"))