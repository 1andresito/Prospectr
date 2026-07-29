const map = L.map("map").setView([43.0731, -89.4012], 13);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

let currentMarkers = [];

function clearMarkers() {
    currentMarkers.forEach((marker) => map.removeLayer(marker));
    currentMarkers = [];
}

function setLoading(isLoading) {
    const overlay = document.getElementById("loading-overlay");
    const searchBtn = document.getElementById("search-btn");

    overlay.classList.toggle("hidden", !isLoading);
    overlay.setAttribute("aria-hidden", String(!isLoading));
    document.body.classList.toggle("loading-active", isLoading);
    searchBtn.disabled = isLoading;
}

async function searchBusinesses() {
    const query = document.getElementById("query-input").value;
    const location = document.getElementById("location-input").value;

    if (!query || !location) {
        alert("Please enter both a business type and a location.");
        return;
    }

    const url = `/api/search?query=${encodeURIComponent(query)}&location=${encodeURIComponent(location)}`;

    setLoading(true);

    try {
        const response = await fetch(url);
        const businesses = await response.json();

        if (businesses.error) {
            alert("Search failed: " + businesses.error);
            return;
        }

        clearMarkers();

        if (businesses.length === 0) {
            alert("No businesses without a website were found for that search.");
            return;
        }

        // Loop through each business Flask sent back and drop a pin.
        businesses.forEach((biz) => {
            if (biz.lat == null || biz.lng == null) return;

            const marker = L.marker([biz.lat, biz.lng]).addTo(map);

            marker.bindPopup(`<strong>${biz.name}</strong><br>${biz.address}`);

            currentMarkers.push(marker);
        });

        // Re-center the map's view to fit all the new markers on screen.
        const group = new L.featureGroup(currentMarkers);
        map.fitBounds(group.getBounds().pad(0.2));
    } finally {
        setLoading(false);
    }
}

// Wire the button click to trigger the search function above.
document.getElementById("search-btn").addEventListener("click", searchBusinesses);

// ---- Settings panel logic ----

const settingsOverlay = document.getElementById("settings-overlay");
const settingsFields = document.getElementById("settings-fields");
const settingsStatus = document.getElementById("settings-status");

async function loadSettingsFields() {
    const response = await fetch("/api/settings");
    const keyStatuses = await response.json();

    settingsFields.innerHTML = "";

    keyStatuses.forEach((key) => {
        const wrapper = document.createElement("div");
        wrapper.className = "settings-field";

        const label = document.createElement("label");
        label.textContent = key.label;
        label.setAttribute("for", `key-${key.name}`);

        const current = document.createElement("p");
        current.className = "settings-current";
        current.textContent = key.is_set
            ? `Currently set (${key.preview})`
            : "Not set yet";

        const input = document.createElement("input");
        input.type = "password";
        input.id = `key-${key.name}`;
        input.dataset.keyName = key.name;
        input.placeholder = key.is_set ? "Enter a new value to replace it" : "Paste your API key";

        wrapper.appendChild(label);
        wrapper.appendChild(current);
        wrapper.appendChild(input);
        settingsFields.appendChild(wrapper);
    });
}

function openSettings() {
    settingsStatus.textContent = "";
    loadSettingsFields();
    settingsOverlay.classList.remove("hidden");
}

function closeSettings() {
    settingsOverlay.classList.add("hidden");
}

// Reads whatever was typed into each key's input field and sends
// only the non-empty ones to the backend to be saved.
async function saveSettings() {
    const inputs = settingsFields.querySelectorAll("input[data-key-name]");
    const payload = {};

    inputs.forEach((input) => {
        if (input.value.trim() !== "") {
            payload[input.dataset.keyName] = input.value.trim();
        }
    });

    if (Object.keys(payload).length === 0) {
        settingsStatus.textContent = "Enter at least one key to save.";
        return;
    }

    const response = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
    });

    const result = await response.json();

    if (response.ok) {
        settingsStatus.textContent = "Saved.";
        loadSettingsFields(); // refresh so the "currently set" preview updates
    } else {
        settingsStatus.textContent = "Error: " + (result.error || "could not save");
    }
}

document.getElementById("settings-btn").addEventListener("click", openSettings);
document.getElementById("settings-close-btn").addEventListener("click", closeSettings);
document.getElementById("settings-save-btn").addEventListener("click", saveSettings);