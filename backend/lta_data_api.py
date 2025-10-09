import os
import requests
from dotenv import load_dotenv # clean this up later to include in .main

# load variables from .env
load_dotenv()
LTA_API_KEY = os.getenv("LTA_API_KEY")
BASE_URL = "https://datamall2.mytransport.sg/ltaodataservice"

HEADERS = {
    "AccountKey": LTA_API_KEY,
    "accept": "application/json"
}

# get LTA data
def get_bus_arrival(bus_stop_code):
    url = f"{BASE_URL}/v3/BusArrival"
    resp = requests.request("GET", url, headers=HEADERS, params={"BusStopCode": bus_stop_code})
    return resp.json()

def get_train_crowd_density_real_time(train_line):
    url = f"{BASE_URL}/PCDRealTime"
    resp = requests.request("GET", url, headers=HEADERS, params={"TrainLine": train_line})
    return resp.json()

def get_traffic_incidents():
    url = f"{BASE_URL}/TrafficIncidents"
    resp = requests.request("GET", url, headers=HEADERS)
    return resp.json()

# test
print(get_bus_arrival("64101"))
print(get_train_crowd_density_real_time("NEL"))
print(get_traffic_incidents())