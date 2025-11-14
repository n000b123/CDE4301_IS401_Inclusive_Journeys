# main.py
from google_map_api import text_to_coords, get_routes
from lta_data_api import get_mrt_station_code, load_bus_stops_with_tree, find_nearest_bus_stop_kdtree, get_bus_arrival, get_train_crowd_density_real_time, get_train_service_alerts, parse_datetime, get_train_platform_forecast
import datetime

def main():
    origin_text = input("Enter starting location: ")
    destination_text = input("Enter destination: ")
    future_time_str = input("Enter desired departure (YYYY-MM-DD HH:MM) or leave blank for now: ")

    if future_time_str:
        dt = datetime.datetime.strptime(future_time_str, "%Y-%m-%d %H:%M")
        departure_time = int(dt.timestamp())
    else:
        departure_time = "now"

    origin_coords = text_to_coords(origin_text)
    destination_coords = text_to_coords(destination_text)

    routes = get_routes(origin_coords, destination_coords, departure_time)
    all_bus_stops, bus_tree = load_bus_stops_with_tree()

    bus_load_map = {"SEA": "Seats Available", "SDA": "Standing Available", "LSD": "Limited Standing"}
    bus_feature_map = {"WAB": "Yes", "": "No Info"}
    bus_type_map = {"SD": "Single Deck", "DD": "Double Deck", "BD": "Bendy Bus"}

    for route in routes:
        for leg in route["legs"]:
            if leg.get("mode") == "BUS":
                dep_stop_coords, arr_stop_coords = leg["departure_coords"], leg["arrival_coords"]
                dep_match, arr_match = find_nearest_bus_stop_kdtree(dep_stop_coords, all_bus_stops, bus_tree), find_nearest_bus_stop_kdtree(arr_stop_coords, all_bus_stops, bus_tree)
                if dep_match and departure_time == "now":
                    leg["departure_bus_stop_code"] = dep_match["BusStopCode"]
                    resp = get_bus_arrival(dep_match["BusStopCode"])
                    bus_info = next((b for b in resp["Services"] if b["ServiceNo"] == leg["line"]), None)
                    if bus_info:
                        leg["next_buses"] = []
                        for bus_key in ["NextBus", "NextBus2", "NextBus3"]:
                            next_bus = bus_info.get(bus_key)
                            if next_bus and next_bus.get("EstimatedArrival"):
                                leg["next_buses"].append({
                                    "eta": next_bus.get("EstimatedArrival"),
                                    "bus_load": bus_load_map.get(next_bus.get("Load"), "No Info"),
                                    "wheelchair_accessible": bus_feature_map.get(next_bus.get("Feature"), "No Info"),
                                    "bus_type": bus_type_map.get(next_bus.get("Type"), "No Info")
                                })
                if arr_match:
                    leg["arrival_bus_stop_code"] = arr_match["BusStopCode"]

            if leg.get("mode") == "SUBWAY":
                dep_stop_name, arr_stop_name, line = leg["departure_stop"], leg["arrival_stop"], leg["line"]
                leg["departure_mrt_code"], leg["arrival_mrt_code"] = get_mrt_station_code(dep_stop_name, line), get_mrt_station_code(arr_stop_name, line)
                if departure_time == "now":
                    if leg["departure_mrt_code"]:
                        leg["departure_platform_crowd_level"] = get_train_crowd_density_real_time(leg["departure_mrt_code"])
                    if leg["arrival_mrt_code"]:
                        leg["arrival_platform_crowd_level"] = get_train_crowd_density_real_time(leg["arrival_mrt_code"])
                    train_line_code = leg["line"] + "L"
                    leg["train_service_alert"] = get_train_service_alerts(train_line_code)
                else:
                    leg["departure_platform_crowd_level_forecast"] = get_train_platform_forecast(leg["departure_mrt_code"], future_time_str)
                    leg["arrival_platform_crowd_level_forecast"] = get_train_platform_forecast(leg["arrival_mrt_code"], future_time_str)

    for i, route in enumerate(routes):
        print(f"\n--- Route {i+1}: ---")
        for leg in route["legs"]:
            print(leg)

if __name__ == "__main__":
    main()