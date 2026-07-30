// script.js
const map = L.map("map").setView([43.0731, -89.4012], 13);

L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
}).addTo(map);

let currentMarkers = [];

const loadingOverlay = document.getElementById("loading-overlay");

function setLoading(isLoading) {
    loadingOverlay.classList.toggle("hidden", !isLoading);
    loadingOverlay.setAttribute("aria-hidden", String(!isLoading));
}

function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
}

function clearMarkers() {
    currentMarkers.forEach((marker) => map.removeLayer(marker));
    currentMarkers = [];
}

async function searchBusinesses() {
    const query = document.getElementById("query-input").value;
    const location = document.getElementById("location-input").value;

    if (!location) {
        alert("Please enter a location.");
        return;
    }

    setLoading(true);

    try {
        const keyIsReady = await checkApiKeyStatus();
        if (!keyIsReady) {
            alert("No API key set. Please add your Google Places API key in Settings first.");
            openSettings();
            return;
        }

        const typesParam = selectedTypes.join(",");
        const url = `/api/search?query=${encodeURIComponent(query)}&location=${encodeURIComponent(location)}&category=${encodeURIComponent(selectedCategory)}&types=${encodeURIComponent(typesParam)}`;

        const response = await fetch(url);
        const businesses = await response.json();

        if (businesses.error) {
            alert("Search failed: " + businesses.error);
            return;
        }

        clearMarkers();

        if (businesses.length === 0) {
            const catLabel = CATEGORIES.find((c) => c.value === selectedCategory)?.label ?? selectedCategory;
            alert(`No businesses matching "${catLabel}" were found for that search.`);
            return;
        }

        // Loop through each business Flask sent back and drop a pin.
        businesses.forEach((biz) => {
            if (biz.lat == null || biz.lng == null) return;

            const marker = L.marker([biz.lat, biz.lng]).addTo(map);

            const safeName = escapeHtml(biz.name);
            const safeAddress = escapeHtml(biz.address);

            const popupHtml = `
                <div class="popup-content">
                    <strong>${safeName}</strong><br>
                    ${safeAddress}<br>
                    <button class="analyze-btn">Analyze Marketing Strategies</button>
                </div>
            `;

            marker.bindPopup(popupHtml, { maxWidth: 280 });

            marker.on("popupopen", () => {
                const popupEl = marker.getPopup().getElement();
                const oldBtn = popupEl.querySelector(".analyze-btn");
            
                const analyzeBtn = oldBtn.cloneNode(true);
                oldBtn.replaceWith(analyzeBtn);
            
                analyzeBtn.addEventListener("click", async () => {
                    analyzeBtn.disabled = true;
                    analyzeBtn.textContent = "Analyzing...";
            
                    marker.closePopup();
                    openAnalysisPanel(biz.name);
            
                    try {
                        const response = await fetch("/api/analyze", {
                            method: "POST",
                            headers: { "Content-Type": "application/json" },
                            body: JSON.stringify({ name: biz.name, address: biz.address }),
                        });
                        const result = await response.json();
            
                        if (result.error) {
                            showAnalysisError(result.error);
                        } else {
                            showAnalysisResult(result.analysis);
                        }
                    } catch (err) {
                        showAnalysisError("Something went wrong. Please try again.");
                    } finally {
                        analyzeBtn.disabled = false;
                        analyzeBtn.textContent = "Analyze Marketing Strategies";
                    }
                });
            });

            currentMarkers.push(marker);
        });

        const group = new L.featureGroup(currentMarkers);
        map.fitBounds(group.getBounds().pad(0.2));
    } finally {
        setLoading(false);
    }
}

document.getElementById("search-btn").addEventListener("click", searchBusinesses);

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
        loadSettingsFields();
        checkApiKeyStatus();
    } else {
        settingsStatus.textContent = "Error: " + (result.error || "could not save");
    }
}

document.getElementById("settings-btn").addEventListener("click", openSettings);
document.getElementById("settings-close-btn").addEventListener("click", closeSettings);
document.getElementById("settings-save-btn").addEventListener("click", saveSettings);
document.getElementById("warning-settings-link").addEventListener("click", openSettings);


const analysisPanel = document.getElementById("analysis-panel");
const analysisContent = document.getElementById("analysis-content");
const analysisTitle = document.getElementById("analysis-panel-title");

function openAnalysisPanel(businessName) {
    analysisTitle.textContent = businessName;
    analysisContent.innerHTML = '<p class="analysis-loading">Generating marketing suggestions...</p>';
    analysisPanel.classList.remove("hidden");
}

function closeAnalysisPanel() {
    analysisPanel.classList.add("hidden");
}

function showAnalysisResult(markdownText) {
    const rawHtml = marked.parse(markdownText);
    const safeHtml = DOMPurify.sanitize(rawHtml);
    analysisContent.innerHTML = safeHtml;
}

function showAnalysisError(message) {
    analysisContent.innerHTML = `<p class="analysis-loading">Error: ${escapeHtml(message)}</p>`;
}

document.getElementById("analysis-close-btn").addEventListener("click", closeAnalysisPanel);

async function checkApiKeyStatus() {
    const response = await fetch("/api/settings");
    const keyStatuses = await response.json();

    const googleKey = keyStatuses.find((k) => k.name === "GOOGLE_PLACES_API_KEY");
    const isReady = Boolean(googleKey && googleKey.is_set);

    document.getElementById("api-key-warning").classList.toggle("hidden", isReady);
    return isReady;
}

const CATEGORIES = [
    { value: "no_website", label: "No Website" },
    { value: "no_photos", label: "No Photos" },
    { value: "no_reviews", label: "No Reviews" },
    { value: "no_phone", label: "No Phone Number" },
];

let selectedCategory = "no_website";

const categoryOverlay = document.getElementById("category-overlay");
const categoryList = document.getElementById("category-list");
const categoryBtn = document.getElementById("category-btn");

function renderCategoryList() {
    categoryList.innerHTML = "";
    CATEGORIES.forEach((cat) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "category-option" + (cat.value === selectedCategory ? " selected" : "");
        btn.textContent = cat.label;
        btn.addEventListener("click", () => {
            selectedCategory = cat.value;
            categoryBtn.textContent = `Category: ${cat.label} ▾`;
            closeCategoryOverlay();
        });
        categoryList.appendChild(btn);
    });
}

function openCategoryOverlay() {
    renderCategoryList();
    categoryOverlay.classList.remove("hidden");
}

function closeCategoryOverlay() {
    categoryOverlay.classList.add("hidden");
}

categoryBtn.addEventListener("click", openCategoryOverlay);
document.getElementById("category-close-btn").addEventListener("click", closeCategoryOverlay);

const PLACE_TYPES = [
    { value: "restaurant", label: "Restaurants" },
    { value: "cafe", label: "Cafes" },
    { value: "bar", label: "Bars" },
    { value: "store", label: "Retail Stores" },
    { value: "hair_salon", label: "Hair Salons" },
    { value: "gym", label: "Gyms" },
    { value: "dentist", label: "Dentists" },
    { value: "lawyer", label: "Lawyers" },
    { value: "real_estate_agency", label: "Real Estate" },
    { value: "car_repair", label: "Auto Repair" },
];

let selectedTypes = [];

const typesOverlay = document.getElementById("types-overlay");
const typesList = document.getElementById("types-list");
const typesBtn = document.getElementById("types-btn");

function renderTypesList() {
    typesList.innerHTML = "";
    PLACE_TYPES.forEach((t) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "category-option" + (selectedTypes.includes(t.value) ? " selected" : "");
        btn.textContent = t.label;
        btn.addEventListener("click", () => {
            if (selectedTypes.includes(t.value)) {
                selectedTypes = selectedTypes.filter((v) => v !== t.value);
            } else {
                selectedTypes.push(t.value);
            }
            renderTypesList();
            updateTypesBtnLabel();
        });
        typesList.appendChild(btn);
    });
}

function updateTypesBtnLabel() {
    typesBtn.textContent = selectedTypes.length === 0
        ? "Types: All ▾"
        : `Types: ${selectedTypes.length} selected ▾`;
}

typesBtn.addEventListener("click", () => {
    renderTypesList();
    typesOverlay.classList.remove("hidden");
});
document.getElementById("types-close-btn").addEventListener("click", () => {
    typesOverlay.classList.add("hidden");
});
document.getElementById("types-clear-btn").addEventListener("click", () => {
    selectedTypes = [];
    updateTypesBtnLabel();
    typesOverlay.classList.add("hidden");
});

checkApiKeyStatus();