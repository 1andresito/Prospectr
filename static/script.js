const map = L.map("map").setView([43.0731, -89.4012], 13);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

let currentMarkers = [];

function clearMarkers() {
    currentMarkers.forEach((marker) => map.removeLayer(marker));
    currentMarkers = [];
}

async function searchBusinesses() {
    const query = document.getElementById("query-input").value;
    const location = document.getElementById("location-input").value;

    if (!query || !location) {
        alert("Please enter both a business type and a location.");
        return;
    }

    const url = `/api/search?query=${encodeURIComponent(query)}&location=${encodeURIComponent(location)}`;

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

    businesses.forEach((biz) => {
        if (biz.lat == null || biz.lng == null) return;

        const marker = L.marker([biz.lat, biz.lng]).addTo(map);

        marker.bindPopup(`<strong>${biz.name}</strong><br>${biz.address}`);

        currentMarkers.push(marker);
    });

    const group = new L.featureGroup(currentMarkers);
    map.fitBounds(group.getBounds().pad(0.2));
}

document.getElementById("search-btn").addEventListener("click", searchBusinesses);