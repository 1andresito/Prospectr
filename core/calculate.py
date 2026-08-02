import math
import os
import time

import requests

MILES_PER_DEGREE_LATITUDE = 69.0

DEFAULT_NEARBY_TYPES = [
    "restaurant", "cafe", "bar", "bakery",
    "store", "clothing_store", "shoe_store", "jewelry_store", "book_store",
    "electronics_store", "furniture_store", "home_goods_store", "pet_store", "florist",
    "hair_salon", "beauty_salon", "spa", "gym",
    "dentist", "doctor", "veterinary_care", "physiotherapist",
    "lawyer", "accounting", "real_estate_agency", "insurance_agency", "travel_agency",
    "car_repair", "car_dealer", "car_wash",
    "plumber", "electrician", "locksmith", "roofing_contractor", "moving_company",
]


class PlacesAPIError(RuntimeError):
    """Raised when Google Places rejects or fails a request."""

    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


def _api_key():
    return os.getenv("GOOGLE_PLACES_API_KEY")


def _raise_for_places_error(response, operation):
    if response.status_code == 200:
        return

    try:
        payload = response.json()
        detail = (
            payload.get("error", {}).get("message")
            or payload.get("message")
            or response.text
        )
    except (ValueError, AttributeError):
        detail = response.text

    detail = str(detail).strip() or "Unknown Google Places API error."
    raise PlacesAPIError(
        response.status_code,
        f"{operation} failed ({response.status_code}): {detail}",
    )


def geocode_location(location_text):
    """Convert a place name to (latitude, longitude)."""
    url = "https://places.googleapis.com/v1/places:searchText"
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": _api_key(),
        "X-Goog-FieldMask": "places.location",
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            json={"textQuery": location_text},
            timeout=30,
        )
    except requests.exceptions.RequestException as exc:
        raise PlacesAPIError(0, f"Could not contact Google Places: {exc}") from exc

    _raise_for_places_error(response, "Location search")

    places = response.json().get("places", [])
    if not places:
        return None

    loc = places[0].get("location", {})
    lat, lng = loc.get("latitude"), loc.get("longitude")

    if lat is None or lng is None:
        return None

    return lat, lng


def generate_grid(center_lat, center_lng, grid_size=3, spacing_miles=2.0):
    """
    Return a compact grid centered on the coordinate.

    3x3 keeps coverage broad while avoiding the 16-cell request volume
    of the old 4x4 grid.
    """
    points = []
    start_offset = -(grid_size - 1) / 2
    miles_per_degree_lng = MILES_PER_DEGREE_LATITUDE * math.cos(
        math.radians(center_lat)
    )

    miles_per_degree_lng = max(miles_per_degree_lng, 0.01)

    for row in range(grid_size):
        for col in range(grid_size):
            lat_offset_miles = (row + start_offset) * spacing_miles
            lng_offset_miles = (col + start_offset) * spacing_miles

            lat = center_lat + lat_offset_miles / MILES_PER_DEGREE_LATITUDE
            lng = center_lng + lng_offset_miles / miles_per_degree_lng
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
    "places.nationalPhoneNumber,"
    "places.types"
)

_MAX_TEXT_SEARCH_PAGES = 2
_PAGE_TOKEN_RETRY_DELAYS = (2, 3)


def _post_places(url, headers, body, operation, timeout=30):
    try:
        response = requests.post(
            url,
            headers=headers,
            json=body,
            timeout=timeout,
        )
    except requests.exceptions.RequestException as exc:
        raise PlacesAPIError(
            0,
            f"Could not contact Google Places: {exc}",
        ) from exc

    _raise_for_places_error(response, operation)
    return response.json()


def _search_text(
    query,
    lat,
    lng,
    radius_meters,
    headers,
    included_types=None,
):
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

    all_places = []
    page_token = None

    for page_num in range(_MAX_TEXT_SEARCH_PAGES):
        body = dict(base_body)
        if page_token:
            body["pageToken"] = page_token

        data = None

        for delay in (0,) + _PAGE_TOKEN_RETRY_DELAYS:
            if delay:
                time.sleep(delay)

            try:
                response = requests.post(
                    url,
                    headers=headers,
                    json=body,
                    timeout=30,
                )
            except requests.exceptions.RequestException as exc:
                raise PlacesAPIError(
                    0,
                    f"Text search failed: {exc}",
                ) from exc

            if response.status_code == 200 or not page_token:
                break

        _raise_for_places_error(response, "Text search")
        data = response.json()

        places = data.get("places", [])

        if included_types and len(included_types) > 1:
            requested = set(included_types)
            places = [
                place
                for place in places
                if requested.intersection(set(place.get("types", [])))
            ]

        all_places.extend(places)

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

    return _post_places(
        url,
        headers,
        body,
        "Nearby search",
    ).get("places", [])


def search_grid_cell(query, lat, lng, radius_meters, included_types=None):
    """
    Search one grid cell.

    With no text query, all requested/default place types are sent in one
    Nearby Search request instead of one request for each type group.
    """
    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": _api_key(),
        "X-Goog-FieldMask": _PLACES_FIELD_MASK,
    }

    if query:
        return _search_text(
            query,
            lat,
            lng,
            radius_meters,
            headers,
            included_types,
        )

    types = included_types or DEFAULT_NEARBY_TYPES
    places = _search_nearby(
        lat,
        lng,
        radius_meters,
        headers,
        included_types=types,
    )

    places_by_id = {}
    for place in places:
        place_id = place.get("id")
        if place_id:
            places_by_id[place_id] = place

    return list(places_by_id.values())


def get_photo_uri(photo_name, max_width=600):
    """
    Exchange a Places photo resource name for a direct image URL without
    exposing the Google Places API key to the browser.
    """
    if not photo_name:
        return None

    url = f"https://places.googleapis.com/v1/{photo_name}/media"
    params = {
        "key": _api_key(),
        "maxWidthPx": max_width,
        "skipHttpRedirect": "true",
    }

    try:
        response = requests.get(url, params=params, timeout=15)
    except requests.exceptions.RequestException as exc:
        raise PlacesAPIError(
            0,
            f"Photo request failed: {exc}",
        ) from exc

    _raise_for_places_error(response, "Photo request")
    return response.json().get("photoUri")
