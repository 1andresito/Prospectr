#calculate.py
import math
import os

import requests

MILES_PER_DEGREE_LATITUDE = 69.0


def _api_key():
    return os.getenv("GOOGLE_PLACES_API_KEY")


def geocode_location(location_text):
    """Convert a place name to (latitude, longitude). Returns None if not found."""
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": _api_key(),
        "X-Goog-FieldMask": "places.location",
    }
    body = {"textQuery": location_text}

    response = requests.post(url, headers=headers, json=body, timeout=30)
    if response.status_code != 200:
        return None

    places = response.json().get("places", [])
    if not places:
        return None

    loc = places[0].get("location", {})
    lat, lng = loc.get("latitude"), loc.get("longitude")
    if lat is None or lng is None:
        return None

    return lat, lng


def generate_grid(center_lat, center_lng, grid_size=4, spacing_miles=1.5):
    """Return a grid_size x grid_size list of (lat, lng) points centered on the coordinate."""
    points = []
    start_offset = -(grid_size - 1) / 2
    miles_per_degree_lng = MILES_PER_DEGREE_LATITUDE * math.cos(math.radians(center_lat))

    for row in range(grid_size):
        for col in range(grid_size):
            lat_offset_miles = (row + start_offset) * spacing_miles
            lng_offset_miles = (col + start_offset) * spacing_miles

            lat = center_lat + (lat_offset_miles / MILES_PER_DEGREE_LATITUDE)
            lng = center_lng + (lng_offset_miles / miles_per_degree_lng)
            points.append((lat, lng))

    return points


def search_grid_cell(query, lat, lng, radius_meters):
    """Search one grid cell via Google Places Text Search. Returns raw place dicts."""
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": _api_key(),
        "X-Goog-FieldMask": (
            "places.id,"
            "places.displayName,"
            "places.formattedAddress,"
            "places.location,"
            "places.websiteUri"
        ),
    }

    body = {
        "textQuery": query,
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": radius_meters,
            }
        },
    }

    response = requests.post(url, headers=headers, json=body, timeout=30)
    if response.status_code != 200:
        return []

    return response.json().get("places", [])
