// script.js
const map = L.map("map").setView([39.8283, -98.5795], 4);

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

    if (selectedCategories.length === 0) {
        alert("Please select at least one category.");
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

        const categoryParam = selectedCategories.join(",");
        const typesParam = selectedTypes.join(",");
        const url = `/api/search?query=${encodeURIComponent(query)}&location=${encodeURIComponent(location)}&category=${encodeURIComponent(categoryParam)}&types=${encodeURIComponent(typesParam)}`;

        const response = await fetch(url);
        const businesses = await response.json();

        if (businesses.error) {
            alert("Search failed: " + businesses.error);
            return;
        }

        clearMarkers();

        if (businesses.length === 0) {
            const labels = selectedCategories.map((v) => CATEGORIES.find((c) => c.value === v)?.label ?? v);
            alert(`No businesses matching "${labels.join(", ")}" were found for that search.`);
            return;
        }

        businesses.forEach((biz) => {
            if (biz.lat == null || biz.lng == null) return;

            const marker = L.marker([biz.lat, biz.lng]).addTo(map);

            const popupHtml = `
                <div class="pin-popup">
                    <strong>${escapeHtml(biz.name)}</strong>
                    ${escapeHtml(biz.address)}
                </div>
            `;
            marker.bindPopup(popupHtml, { maxWidth: 220 });
            marker.on("click", () => openBusinessPanel(biz));

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
    try {
        const response = await fetch("/api/settings", { cache: "no-store" });
        if (!response.ok) throw new Error(`HTTP ${response.status}`);

        const settings = await response.json();
        settingsFields.innerHTML = "";

        settings.forEach((setting) => {
            const wrapper = document.createElement("div");
            wrapper.className = "settings-field";

            const label = document.createElement("label");
            label.textContent = setting.label;
            label.setAttribute("for", `setting-${setting.name}`);
            wrapper.appendChild(label);

            if (setting.type === "secret") {
                const current = document.createElement("p");
                current.className = "settings-current";
                current.textContent = setting.is_set
                    ? `Currently set (${setting.preview})`
                    : "Not set yet";

                const input = document.createElement("input");
                input.type = "password";
                input.id = `setting-${setting.name}`;
                input.dataset.keyName = setting.name;
                input.placeholder = setting.is_set
                    ? "Enter a new value to replace it"
                    : "Paste your API key";

                wrapper.appendChild(current);
                wrapper.appendChild(input);
            } else if (setting.type === "select") {
                const select = document.createElement("select");
                select.id = `setting-${setting.name}`;
                select.dataset.settingName = setting.name;

                setting.options.forEach((option) => {
                    const optionEl = document.createElement("option");
                    optionEl.value = option.value;
                    optionEl.textContent = option.label;
                    optionEl.selected = option.value === setting.value;
                    select.appendChild(optionEl);
                });

                wrapper.appendChild(select);

                if (setting.name === "AI_PROVIDER") {
                    const help = document.createElement("p");
                    help.className = "settings-help";
                    help.textContent =
                        "Choose the provider that matches the AI key you enter below.";
                    wrapper.appendChild(help);
                }
            } else if (setting.type === "range") {
                const valueLabel = document.createElement("span");
                valueLabel.className = "settings-range-value";
                valueLabel.textContent = `${setting.value} × ${setting.value} search grid`;

                const range = document.createElement("input");
                range.type = "range";
                range.id = `setting-${setting.name}`;
                range.dataset.settingName = setting.name;
                range.min = setting.min;
                range.max = setting.max;
                range.step = "1";
                range.value = setting.value;

                range.addEventListener("input", () => {
                    valueLabel.textContent =
                        `${range.value} × ${range.value} search grid`;
                });

                wrapper.appendChild(valueLabel);
                wrapper.appendChild(range);

                const help = document.createElement("p");
                help.className = "settings-help";
                help.textContent = setting.description;
                wrapper.appendChild(help);
            }

            settingsFields.appendChild(wrapper);
        });
    } catch (error) {
        settingsFields.innerHTML =
            `<p class="settings-status">Could not load settings: ${escapeHtml(error.message)}</p>`;
    }
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
    const payload = {};

    settingsFields.querySelectorAll("input[data-key-name]").forEach((input) => {
        if (input.value.trim() !== "") {
            payload[input.dataset.keyName] = input.value.trim();
        }
    });

    const provider = document.getElementById("setting-AI_PROVIDER");
    if (provider) {
        payload.AI_PROVIDER = provider.value;
    }

    const gridSize = document.getElementById("setting-SEARCH_GRID_SIZE");
    if (gridSize) {
        payload.SEARCH_GRID_SIZE = Number(gridSize.value);
    }

    if (Object.keys(payload).length === 0) {
        settingsStatus.textContent = "Nothing to save.";
        return;
    }

    try {
        const response = await fetch("/api/settings", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
        });

        const result = await response.json();

        if (!response.ok) {
            settingsStatus.textContent =
                "Error: " + (result.error || "could not save");
            return;
        }

        settingsStatus.textContent = "Saved.";
        await loadSettingsFields();
        await checkApiKeyStatus();
    } catch (error) {
        settingsStatus.textContent =
            "Error: " + error.message;
    }
}

document.getElementById("settings-btn").addEventListener("click", openSettings);
document.getElementById("settings-close-btn").addEventListener("click", closeSettings);
document.getElementById("settings-save-btn").addEventListener("click", saveSettings);
document.getElementById("warning-settings-link").addEventListener("click", openSettings);


const analysisPanel = document.getElementById("analysis-panel");
const analysisContent = document.getElementById("analysis-content");
const analysisTitle = document.getElementById("analysis-panel-title");
const analysisAddress = document.getElementById("analysis-address");
const analyzeBtn = document.getElementById("analyze-btn");
const downloadPdfBtn = document.getElementById("download-pdf-btn");
const businessPhoto = document.getElementById("business-photo");
const businessPhotoPlaceholder = document.getElementById("business-photo-placeholder");
const businessRating = document.getElementById("business-rating");
const businessPhone = document.getElementById("business-phone");
const businessBadges = document.getElementById("business-badges");

let currentBusiness = null;
let lastAnalysisMarkdown = null;

function setDownloadButtonVisible(visible) {
    downloadPdfBtn.classList.toggle("hidden", !visible);
}

function renderBusinessMeta(biz) {
    if (biz.rating) {
        const count = biz.rating_count ? ` (${biz.rating_count})` : "";
        businessRating.textContent = `⭐ ${biz.rating.toFixed(1)}${count}`;
        businessRating.classList.remove("hidden");
    } else {
        businessRating.classList.add("hidden");
    }

    if (biz.phone) {
        businessPhone.textContent = `📞 ${biz.phone}`;
        businessPhone.classList.remove("hidden");
    } else {
        businessPhone.classList.add("hidden");
    }

    businessBadges.innerHTML = "";
    const missing = [];
    if (!biz.has_website) missing.push("No Website");
    if (!biz.photo_name) missing.push("No Photos");
    if (!biz.rating_count) missing.push("No Reviews");
    if (!biz.phone) missing.push("No Phone");

    missing.forEach((label) => {
        const badge = document.createElement("span");
        badge.className = "missing-badge";
        badge.textContent = label;
        businessBadges.appendChild(badge);
    });
}

function renderBusinessPhoto(biz) {
    if (biz.photo_name) {
        businessPhoto.src = `/api/photo?name=${encodeURIComponent(biz.photo_name)}`;
        businessPhoto.classList.remove("hidden");
        businessPhotoPlaceholder.classList.add("hidden");
        businessPhoto.onerror = () => {
            businessPhoto.classList.add("hidden");
            businessPhotoPlaceholder.classList.remove("hidden");
        };
    } else {
        businessPhoto.classList.add("hidden");
        businessPhotoPlaceholder.classList.remove("hidden");
    }
}

function openBusinessPanel(biz) {
    currentBusiness = biz;
    lastAnalysisMarkdown = null;

    analysisTitle.textContent = biz.name;
    analysisAddress.textContent = biz.address;
    analysisContent.innerHTML = "";
    setDownloadButtonVisible(false);
    analyzeBtn.disabled = false;
    analyzeBtn.textContent = "Analyze Marketing Strategies";

    renderBusinessMeta(biz);
    renderBusinessPhoto(biz);

    analysisPanel.classList.remove("hidden");
}

function closeAnalysisPanel() {
    analysisPanel.classList.add("hidden");
}

function showAnalysisResult(markdownText) {
    lastAnalysisMarkdown = markdownText;
    const rawHtml = marked.parse(markdownText);
    const safeHtml = DOMPurify.sanitize(rawHtml);
    analysisContent.innerHTML = safeHtml;
    setDownloadButtonVisible(true);
}

function showAnalysisError(message) {
    analysisContent.innerHTML = `<p class="analysis-loading">Error: ${escapeHtml(message)}</p>`;
    setDownloadButtonVisible(false);
}

document.getElementById("analysis-close-btn").addEventListener("click", closeAnalysisPanel);

analyzeBtn.addEventListener("click", () => {
    if (!currentBusiness) return;

    analyzeBtn.disabled = true;
    analyzeBtn.textContent = "Analyzing...";
    analysisContent.innerHTML = '<p class="analysis-loading">Generating marketing suggestions...</p>';
    setDownloadButtonVisible(false);

    let fullText = "";
    let firstChunkReceived = false;

    const params = new URLSearchParams({
        name: currentBusiness.name,
        address: currentBusiness.address,
        has_website: String(Boolean(currentBusiness.has_website)),
        has_photos: String(Boolean(currentBusiness.photo_name)),
        has_reviews: String(Boolean(currentBusiness.rating_count)),
        has_phone: String(Boolean(currentBusiness.phone)),
        website_url: currentBusiness.website_url || "",
    });
    const eventSource = new EventSource(`/api/analyze/stream?${params.toString()}`);

    eventSource.onmessage = (event) => {
        const data = JSON.parse(event.data);

        if (data.status === "researching") {
            analysisContent.innerHTML =
                '<p class="analysis-loading">Researching the business online...</p>';
        }

        if (data.status === "research_complete") {
            analysisContent.innerHTML =
                `<p class="analysis-loading">Research complete (${data.source_count} sources). Generating analysis...</p>`;
        }

        if (data.status === "research_unavailable") {
            analysisContent.innerHTML =
                '<p class="analysis-loading">Search research is not configured. Generating analysis from available business data...</p>';
        }

        if (data.chunk) {
            if (!firstChunkReceived) {
                analysisContent.innerHTML = "";
                firstChunkReceived = true;
            }
            fullText += data.chunk;
            analysisContent.innerHTML = DOMPurify.sanitize(marked.parse(fullText));
        }

        if (data.done) {
            lastAnalysisMarkdown = fullText;
            setDownloadButtonVisible(true);
            analyzeBtn.disabled = false;
            analyzeBtn.textContent = "Analyze Marketing Strategies";
            eventSource.close();
        }

        if (data.error) {
            showAnalysisError(data.error);
            analyzeBtn.disabled = false;
            analyzeBtn.textContent = "Analyze Marketing Strategies";
            eventSource.close();
        }
    };

    eventSource.onerror = () => {
        if (!firstChunkReceived) {
            showAnalysisError("Connection lost. Please try again.");
        }
        analyzeBtn.disabled = false;
        analyzeBtn.textContent = "Analyze Marketing Strategies";
        eventSource.close();
    };
});


downloadPdfBtn.addEventListener("click", () => {
    if (!lastAnalysisMarkdown || !currentBusiness) return;

    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ unit: "pt", format: "letter" });

    const marginLeft = 48;
    const maxWidth = 515;
    let y = 60;

    doc.setFontSize(16);
    doc.text(currentBusiness.name, marginLeft, y);
    y += 22;

    doc.setFontSize(10);
    doc.setTextColor(100);
    doc.text(currentBusiness.address, marginLeft, y);
    y += 28;

    doc.setTextColor(0);
    doc.setFontSize(11);

    const plainText = lastAnalysisMarkdown
        .replace(/\*\*(.*?)\*\*/g, "$1")
        .replace(/^#+\s*/gm, "")
        .replace(/^[-*]\s+/gm, "\u2022 ");

    const lines = doc.splitTextToSize(plainText, maxWidth);

    lines.forEach((line) => {
        if (y > 740) {
            doc.addPage();
            y = 60;
        }
        doc.text(line, marginLeft, y);
        y += 16;
    });

    const safeName = currentBusiness.name.replace(/[^a-z0-9]+/gi, "_");
    doc.save(`${safeName}_marketing_analysis.pdf`);
});


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

let selectedCategories = ["no_website"];

const categoryOverlay = document.getElementById("category-overlay");
const categoryList = document.getElementById("category-list");
const categoryBtn = document.getElementById("category-btn");

function renderCategoryList() {
    categoryList.innerHTML = "";
    CATEGORIES.forEach((cat) => {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "category-option" + (selectedCategories.includes(cat.value) ? " selected" : "");
        btn.textContent = cat.label;
        btn.addEventListener("click", () => {
            if (selectedCategories.includes(cat.value)) {
                selectedCategories = selectedCategories.filter((v) => v !== cat.value);
            } else {
                selectedCategories.push(cat.value);
            }
            renderCategoryList();
            updateCategoryBtnLabel();
        });
        categoryList.appendChild(btn);
    });
}

function updateCategoryBtnLabel() {
    categoryBtn.textContent = selectedCategories.length === 1
        ? `Category: ${CATEGORIES.find((c) => c.value === selectedCategories[0]).label} ▾`
        : `Category: ${selectedCategories.length} selected ▾`;
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

setInterval(() => {
    fetch("/api/heartbeat", { method: "POST" }).catch(() => {});
}, 3000);

window.addEventListener("beforeunload", () => {
    navigator.sendBeacon("/api/shutdown");
});