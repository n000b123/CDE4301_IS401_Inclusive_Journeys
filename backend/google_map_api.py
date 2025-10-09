# backend/google_api.py
import requests
import os
from dotenv import load_dotenv

# load variables from .env
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if GOOGLE_API_KEY is None:
    raise ValueError("Google API key not found. Check .env file.")

# convert location text to coordinates
def text_to_coords(place_text):
    autocomplete_url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
    resp = requests.get(autocomplete_url, params={
        "input": place_text,
        "types": "establishment",
        "key": GOOGLE_API_KEY
    })

    data = resp.json()
    predictions = data.get("predictions", [])
    if not predictions:
        print(f"No predictions found for: {place_text}")
        return None

    place_id = predictions[0].get("place_id")
    if not place_id:
        print(f"No place_id found for: {place_text}")
        return None

    # Get place details
    details_url = "https://maps.googleapis.com/maps/api/place/details/json"
    resp2 = requests.get(details_url, params={
        "place_id": place_id,
        "fields": "geometry,name",
        "key": GOOGLE_API_KEY
    })

    result = resp2.json().get("result", {})
    location = result.get("geometry", {}).get("location", {})
    if not location:
        print(f"No location found for: {place_text}")
        return None

    return location.get("lat"), location.get("lng")


# get route from origin to destination (in coords)
def get_route(origin_coords, destination_coords, api_key):
    """Get transit route between two coordinates."""
    origin_str = f"{origin_coords[0]},{origin_coords[1]}"
    destination_str = f"{destination_coords[0]},{destination_coords[1]}"

    url = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin_str,
        "destination": destination_str,
        "mode": "transit",  # walk + bus/train
        "key": api_key
    }

    resp = requests.get(url, params=params)
    data = resp.json()

    route_legs = []

    try:
        steps = data["routes"][0]["legs"][0]["steps"]
    except (KeyError, IndexError):
        print("No route found")
        return []

    for step in steps:
        travel_mode = step.get("travel_mode")
        if travel_mode == "WALKING":
            route_legs.append({
                "mode": "WALK",
                "start": step.get("start_location", {}),
                "end": step.get("end_location", {}),
                "duration": step.get("duration", {}).get("text", "")
            })
        elif travel_mode == "TRANSIT":
            transit = step.get("transit_details", {})
            line = transit.get("line", {})
            vehicle = line.get("vehicle", {}).get("type", "TRANSIT")
            line_name = line.get("short_name") or line.get("name") or "Unknown Line"

            departure = transit.get("departure_stop", {})
            arrival = transit.get("arrival_stop", {})

            dep_loc = departure.get("location", {})
            arr_loc = arrival.get("location", {})

            route_legs.append({
                "mode": vehicle,
                "line": line_name,
                "departure_stop": departure.get("name", "Unknown"),
                "arrival_stop": arrival.get("name", "Unknown"),
                "duration": step.get("duration", {}).get("text", ""),
                "departure_coords": (
                    dep_loc.get("lat", 0),
                    dep_loc.get("lng", 0)
                ),
                "arrival_coords": (
                    arr_loc.get("lat", 0),
                    arr_loc.get("lng", 0)
                )
            })
    return route_legs


origin_coords = text_to_coords("Tampines MRT")
destination_coords = text_to_coords("Kent Ridge MRT")

print(origin_coords)
print(destination_coords)

# Get route
legs = get_route(origin_coords, destination_coords, GOOGLE_API_KEY)

# Print results
for i, leg in enumerate(legs, 1):
    print(f"Leg {i}: {leg}")