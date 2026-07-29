from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from calculate import geocode_location, generate_grid, search_grid_cell

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

app = Flask(
    __name__,
    template_folder=str(BASE_DIR / "templates"),
    static_folder=str(BASE_DIR / "static"),
)

GRID_SIZE = 4
GRID_SPACING_MILES = 1.5
SEARCH_RADIUS_METERS = 1800  # ~1.1 miles; overlaps adjacent cells slightly


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


@app.route("/api/search")
def search_businesses():
    query = request.args.get("query")
    location = request.args.get("location")

    if not query or not location:
        return jsonify({"error": "Missing 'query' or 'location' parameter"}), 400

    center = geocode_location(location)
    if center is None:
        return jsonify({"error": f"Could not find location: {location}"}), 400

    center_lat, center_lng = center
    grid_points = generate_grid(
        center_lat, center_lng, grid_size=GRID_SIZE, spacing_miles=GRID_SPACING_MILES
    )

    all_places_by_id = {}
    for lat, lng in grid_points:
        for place in search_grid_cell(query, lat, lng, SEARCH_RADIUS_METERS):
            place_id = place.get("id")
            if place_id:
                all_places_by_id[place_id] = place

    no_website_places = [
        _place_to_result(place)
        for place in all_places_by_id.values()
        if "websiteUri" not in place
    ]

    return jsonify(no_website_places)


if __name__ == "__main__":
    app.run(debug=True, port=5001)
