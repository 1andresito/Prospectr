#app.py
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from calculate import geocode_location, generate_grid, search_grid_cell
from env_manager import ENV_KEYS, get_key_status, save_keys
from analysis import generate_marketing_analysis
import os

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(ENV_PATH)

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)

GRID_SIZE = 4
GRID_SPACING_MILES = 1.5
SEARCH_RADIUS_METERS = 1800

CATEGORY_FILTERS = {
    "no_website": lambda place: "websiteUri" not in place,
    "no_photos": lambda place: not place.get("photos"),
    "no_reviews": lambda place: not place.get("userRatingCount"),
    "no_phone": lambda place: "nationalPhoneNumber" not in place,
}


def _place_to_result(place):
    return {
        "name": place.get("displayName", {}).get("text", "Unknown"),
        "address": place.get("formattedAddress", "No address"),
        "lat": place.get("location", {}).get("latitude"),
        "lng": place.get("location", {}).get("longitude"),
    }


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/settings", methods=["GET"])
def get_settings():
    return jsonify(get_key_status(ENV_PATH))


@app.route("/api/settings", methods=["POST"])
def update_settings():
    data = request.get_json(silent=True) or {}

    allowed_names = {key_def["name"] for key_def in ENV_KEYS}
    new_values = {name: value for name, value in data.items() if name in allowed_names}

    if not new_values:
        return jsonify({"error": "No valid keys provided"}), 400

    updated = save_keys(ENV_PATH, new_values)

    for key, value in updated.items():
        os.environ[key] = value

    return jsonify({"status": "saved"})


@app.route("/api/search")
def search_businesses():
    query = request.args.get("query") or None
    location = request.args.get("location")
    category = request.args.get("category", "no_website")
    types_param = request.args.get("types", "")
    included_types = [t.strip() for t in types_param.split(",") if t.strip()] or None

    if not location:
        return jsonify({"error": "Missing 'location' parameter"}), 400

    filter_fn = CATEGORY_FILTERS.get(category)
    if filter_fn is None:
        return jsonify({"error": f"Unknown category: {category}"}), 400

    if not os.getenv("GOOGLE_PLACES_API_KEY"):
        return jsonify({"error": "No API key set. Add your Google Places API key in Settings first."}), 400

    center = geocode_location(location)
    if center is None:
        return jsonify({"error": f"Could not find location: {location}"}), 400

    center_lat, center_lng = center
    grid_points = generate_grid(
        center_lat, center_lng, grid_size=GRID_SIZE, spacing_miles=GRID_SPACING_MILES
    )

    all_places_by_id = {}
    for lat, lng in grid_points:
        for place in search_grid_cell(query, lat, lng, SEARCH_RADIUS_METERS, included_types):
            place_id = place.get("id")
            if place_id:
                all_places_by_id[place_id] = place

    matching_places = [
        _place_to_result(place)
        for place in all_places_by_id.values()
        if filter_fn(place)
    ]

    return jsonify(matching_places)


@app.route("/api/analyze", methods=["POST"])
def analyze_business():
    data = request.get_json(silent=True) or {}
    name = data.get("name")
    address = data.get("address")

    if not name or not address:
        return jsonify({"error": "Missing business name or address"}), 400

    if not os.getenv("NVIDIA_API_KEY"):
        return jsonify({"error": "No NVIDIA API key set. Add one in Settings first."}), 400

    analysis = generate_marketing_analysis(name, address)

    if analysis is None:
        return jsonify({"error": "Analysis request failed. Check your NVIDIA API key and try again."}), 502

    return jsonify({"analysis": analysis})


if __name__ == "__main__":
    app.run(debug=True, port=5001)