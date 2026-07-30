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


def search_grid_cell(query, lat, lng, radius_meters, included_types=None):
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": _api_key(),
        "X-Goog-FieldMask": (
            "places.id,"
            "places.displayName,"
            "places.formattedAddress,"
            "places.location,"
            "places.websiteUri,"
            "places.photos,"
            "places.rating,"
            "places.userRatingCount,"
            "places.nationalPhoneNumber"
        ),
    }

    if query:
        url = "https://places.googleapis.com/v1/places:searchText"
        body = {
            "textQuery": query,
            "locationBias": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": radius_meters,
                }
            },
        }
        if included_types:
            body["includedType"] = included_types[0]
    else:
        url = "https://places.googleapis.com/v1/places:searchNearby"
        body = {
            "locationRestriction": {
                "circle": {
                    "center": {"latitude": lat, "longitude": lng},
                    "radius": radius_meters,
                }
            },
            "maxResultCount": 20,
        }
        if included_types:
            body["includedTypes"] = included_types

    response = requests.post(url, headers=headers, json=body, timeout=30)
    if response.status_code != 200:
        return []

    return response.json().get("places", [])


def get_photo_uri(photo_name, max_width=600):
    """
    Given a Places photo resource name (e.g. 'places/ABC123/photos/XYZ'),
    exchanges it for a direct, signed googleusercontent.com image URL.
    Using skipHttpRedirect keeps our API key entirely server-side — the
    browser only ever receives the returned URL, never the key itself.
    Returns None if the photo can't be resolved.
    """
    if not photo_name:
        return None

    url = f"https://places.googleapis.com/v1/{photo_name}/media"
    params = {
        "key": _api_key(),
        "maxWidthPx": max_width,
        "skipHttpRedirect": "true",
    }

    response = requests.get(url, params=params, timeout=15)
    if response.status_code != 200:
        return None

    return response.json().get("photoUri")