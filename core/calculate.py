import math
import os
import time

import requests

MILES_PER_DEGREE_LATITUDE = 69.0

DEFAULT_NEARBY_TYPE_GROUPS = [
    ["restaurant", "cafe", "bar", "bakery"],
    ["store", "clothing_store", "shoe_store", "jewelry_store", "book_store",
     "electronics_store", "furniture_store", "home_goods_store", "pet_store", "florist"],
    ["hair_salon", "beauty_salon", "spa", "gym"],
    ["dentist", "doctor", "veterinary_care", "physiotherapist"],
    ["lawyer", "accounting", "real_estate_agency", "insurance_agency", "travel_agency"],
    ["car_repair", "car_dealer", "car_wash"],
    ["plumber", "electrician", "locksmith", "roofing_contractor", "moving_company"],
]


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


_PLACES_FIELD_MASK = (
    "places.id,"
    "places.displayName,"
    "places.formattedAddress,"
    "places.location,"
    "places.websiteUri,"
    "places.photos,"
    "places.rating,"
    "places.userRatingCount,"
    "places.nationalPhoneNumber"
)

_MAX_TEXT_SEARCH_PAGES = 3
_PAGE_TOKEN_RETRY_DELAYS = (2, 3)  # seconds; only used if a token isn't ready yet


def _search_text(query, lat, lng, radius_meters, headers, included_types=None):
    url = "https://places.googleapis.com/v1/places:searchText"
    base_body = {
        "textQuery": query,
        "locationBias": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": radius_meters,
            }
        },
    }
    if included_types:
        base_body["includedType"] = included_types[0]

    all_places = []
    page_token = None

    for page_num in range(_MAX_TEXT_SEARCH_PAGES):
        body = dict(base_body)
        if page_token:
            body["pageToken"] = page_token

        response = None
        for delay in (0,) + _PAGE_TOKEN_RETRY_DELAYS:
            if delay:
                time.sleep(delay)
            response = requests.post(url, headers=headers, json=body, timeout=30)
            if response.status_code == 200 or not page_token:
                break

        if response is None or response.status_code != 200:
            break

        data = response.json()
        all_places.extend(data.get("places", []))

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return all_places


def _search_nearby(lat, lng, radius_meters, headers, included_types=None):
    url = "https://places.googleapis.com/v1/places:searchNearby"
    body = {
        "locationRestriction": {
            "circle": {
                "center": {"latitude": lat, "longitude": lng},
                "radius": radius_meters,
            }
        },
        "maxResultCount": 20,
        "rankPreference": "DISTANCE",
    }
    if included_types:
        body["includedTypes"] = included_types

    response = requests.post(url, headers=headers, json=body, timeout=30)
    if response.status_code != 200:
        return []

    return response.json().get("places", [])


def search_grid_cell(query, lat, lng, radius_meters, included_types=None):
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": _api_key(),
        "X-Goog-FieldMask": _PLACES_FIELD_MASK,
    }

    if query:
        return _search_text(query, lat, lng, radius_meters, headers, included_types)

    groups = [included_types] if included_types else DEFAULT_NEARBY_TYPE_GROUPS

    places_by_id = {}
    for group in groups:
        for place in _search_nearby(lat, lng, radius_meters, headers, included_types=group):
            place_id = place.get("id")
            if place_id:
                places_by_id[place_id] = place

    return list(places_by_id.values())


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