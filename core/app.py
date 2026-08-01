import sys
import threading
import time
import json
import webbrowser
from pathlib import Path

from dotenv import load_dotenv
from platformdirs import user_config_dir
from flask import Flask, jsonify, redirect, render_template, request, Response, stream_with_context

from calculate import geocode_location, generate_grid, get_photo_uri, search_grid_cell
from env_manager import ENV_KEYS, get_key_status, save_keys
from analysis import generate_marketing_analysis_stream
from providers.registry import detect_provider
from updater import get_update_status
import os

if getattr(sys, "frozen", False):
    RESOURCE_DIR = Path(sys._MEIPASS)
    DATA_DIR = Path(sys.executable).resolve().parent

    CONFIG_DIR = Path(user_config_dir("Prospectr", appauthor=False))
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    ENV_PATH = CONFIG_DIR / ".env"

    _legacy_env_path = DATA_DIR / ".env"
    if _legacy_env_path.exists() and not ENV_PATH.exists():
        ENV_PATH.write_text(_legacy_env_path.read_text())
        _legacy_env_path.unlink()
else:
    RESOURCE_DIR = Path(__file__).resolve().parent.parent
    DATA_DIR = RESOURCE_DIR
    ENV_PATH = DATA_DIR / ".env"

load_dotenv(ENV_PATH)

app = Flask(
    __name__,
    template_folder=str(RESOURCE_DIR / "templates"),
    static_folder=str(RESOURCE_DIR / "static"),
)

GRID_SIZE = 4
GRID_SPACING_MILES = 1.5
SEARCH_RADIUS_METERS = 1800

AUTO_SHUTDOWN_ENABLED = getattr(sys, "frozen", False)
HEARTBEAT_TIMEOUT_SECONDS = 10

_last_heartbeat = time.time()
_heartbeat_lock = threading.Lock()


def _watch_for_disconnect():
    """
    Runs forever in a background thread. Every second, checks how long
    it's been since the browser last pinged us. If that gap grows past
    HEARTBEAT_TIMEOUT_SECONDS, we assume the tab was closed and exit the
    whole process — this is what actually makes the app stop running in
    the background after the user closes the window.
    """
    while True:
        time.sleep(1)
        with _heartbeat_lock:
            elapsed = time.time() - _last_heartbeat
        if elapsed > HEARTBEAT_TIMEOUT_SECONDS:
            os._exit(0)

CATEGORY_FILTERS = {
    "no_website": lambda place: "websiteUri" not in place,
    "no_photos": lambda place: not place.get("photos"),
    "no_reviews": lambda place: not place.get("userRatingCount"),
    "no_phone": lambda place: "nationalPhoneNumber" not in place,
}


def _place_to_result(place):

    photos = place.get("photos") or []
    photo_name = photos[0].get("name") if photos else None

    return {
        "name": place.get("displayName", {}).get("text", "Unknown"),
        "address": place.get("formattedAddress", "No address"),
        "lat": place.get("location", {}).get("latitude"),
        "lng": place.get("location", {}).get("longitude"),
        "rating": place.get("rating"),
        "rating_count": place.get("userRatingCount"),
        "phone": place.get("nationalPhoneNumber"),
        "has_website": "websiteUri" in place,
        "photo_name": photo_name,
    }


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/api/debug/resources")
def debug_resources():
    import os
    return jsonify({
        "resource_dir": str(RESOURCE_DIR),
        "resource_dir_contents": os.listdir(RESOURCE_DIR),
        "meipass_or_none": getattr(sys, "_MEIPASS", None),
    })


@app.route("/api/check-update")
def check_update():
    return get_update_status()


@app.route("/api/heartbeat", methods=["POST"])
def heartbeat():
    global _last_heartbeat
    with _heartbeat_lock:
        _last_heartbeat = time.time()
    return "", 204


@app.route("/api/shutdown", methods=["POST"])
def shutdown():
    if AUTO_SHUTDOWN_ENABLED:
        os._exit(0)
    return "", 204


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
    category_param = request.args.get("category", "no_website")
    categories = [c.strip() for c in category_param.split(",") if c.strip()] or ["no_website"]
    types_param = request.args.get("types", "")
    included_types = [t.strip() for t in types_param.split(",") if t.strip()] or None

    if not location:
        return jsonify({"error": "Missing 'location' parameter"}), 400

    filter_fns = [CATEGORY_FILTERS[c] for c in categories if c in CATEGORY_FILTERS]
    if not filter_fns:
        return jsonify({"error": f"Unknown category: {category_param}"}), 400

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
        if any(fn(place) for fn in filter_fns)
    ]

    return jsonify(matching_places)


@app.route("/api/photo")
def get_photo():

    photo_name = request.args.get("name")
    if not photo_name:
        return jsonify({"error": "Missing 'name' parameter"}), 400

    if not os.getenv("GOOGLE_PLACES_API_KEY"):
        return jsonify({"error": "No API key set"}), 400

    photo_uri = get_photo_uri(photo_name)
    if photo_uri is None:
        return jsonify({"error": "Photo not found"}), 404

    return redirect(photo_uri)


def _bool_param(name, default=False):
    raw = request.args.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in ("1", "true", "yes")


@app.route("/api/analyze/stream")
def analyze_business_stream():
    name = request.args.get("name")
    address = request.args.get("address")

    if not name or not address:
        return jsonify({"error": "Missing business name or address"}), 400

    has_website = _bool_param("has_website", default=False)
    has_photos = _bool_param("has_photos", default=True)
    has_reviews = _bool_param("has_reviews", default=True)
    has_phone = _bool_param("has_phone", default=True)

    agent_key = os.getenv("AGENT_API_KEY")
    if not agent_key:
        return jsonify({"error": "No Agent API key set. Add one in Settings first."}), 400

    provider = detect_provider(agent_key)
    if provider is None:
        return jsonify({
            "error": "Couldn't recognize this API key's provider. Double-check you pasted it correctly."
        }), 400

    def event_stream():
        got_any_chunks = False
        try:
            for chunk in generate_marketing_analysis_stream(
                name, address, provider, agent_key,
                has_website=has_website, has_photos=has_photos,
                has_reviews=has_reviews, has_phone=has_phone,
            ):
                got_any_chunks = True
                yield f"data: {json.dumps({'chunk': chunk})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            return

        if got_any_chunks:
            yield f"data: {json.dumps({'done': True})}\n\n"
        else:
            yield f"data: {json.dumps({'error': 'Analysis request failed. Check your API key and try again.'})}\n\n"

    return Response(stream_with_context(event_stream()), mimetype="text/event-stream")


def _open_browser():
    webbrowser.open("http://127.0.0.1:5001")


if __name__ == "__main__":
    if getattr(sys, "frozen", False):
        threading.Thread(target=_watch_for_disconnect, daemon=True).start()
        threading.Timer(1.0, _open_browser).start()
        app.run(debug=False, port=5001, use_reloader=False, threaded=True)
    else:
        app.run(debug=True, port=5001, threaded=True)