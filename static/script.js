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

        const response = await apiFetch(apiUrl("/api/search", {
            query: query,
            location: location,
            category: selectedCategories.join(","),
            types: selectedTypes.join(","),
        }));

        // Errors reach us as JSON, but a crash or a proxy could still return
        // HTML. Read as text first so a parse failure produces a real message
        // instead of an unhandled rejection and a silently stopped spinner.
        const body = await response.text();
        let businesses;
        try {
            businesses = JSON.parse(body);
        } catch {
            throw new Error(
                `The server returned an unexpected response (HTTP ${response.status}).`
            );
        }

        if (!response.ok || businesses.error) {
            alert("Search failed: " + (businesses.error || `HTTP ${response.status}`));
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
    } catch (error) {
        alert("Search failed: " + error.message);
    } finally {
        setLoading(false);
    }
}

document.getElementById("search-btn").addEventListener("click", searchBusinesses);

const settingsOverlay = document.getElementById("settings-overlay");
const settingsFields = document.getElementById("settings-fields");
const settingsStatus = document.getElementById("settings-status");

// Names the user asked to remove; applied on the next save.
let pendingKeyClears = new Set();

async function loadSettingsFields() {
    try {
        const response = await apiFetch("/api/settings", { cache: "no-store" });
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
                const cleared = pendingKeyClears.has(setting.name);

                const current = document.createElement("p");
                current.className = "settings-current";
                if (cleared) {
                    current.textContent = "Will be removed when you save";
                } else {
                    current.textContent = setting.is_set
                        ? `Currently set (${setting.preview})`
                        : "Not set yet";
                }

                const input = document.createElement("input");
                input.type = "password";
                input.id = `setting-${setting.name}`;
                input.dataset.keyName = setting.name;
                input.placeholder = setting.is_set
                    ? "Enter a new value to replace it"
                    : "Paste your API key";

                wrapper.appendChild(current);
                wrapper.appendChild(input);

                if (setting.is_set) {
                    const clearBtn = document.createElement("button");
                    clearBtn.type = "button";
                    clearBtn.className = "settings-clear-btn";
                    clearBtn.textContent = cleared ? "Undo remove" : "Remove key";
                    clearBtn.addEventListener("click", () => {
                        if (pendingKeyClears.has(setting.name)) {
                            pendingKeyClears.delete(setting.name);
                        } else {
                            pendingKeyClears.add(setting.name);
                        }
                        loadSettingsFields();
                    });
                    wrapper.appendChild(clearBtn);
                }
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
    pendingKeyClears = new Set();
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

    if (pendingKeyClears.size > 0) {
        payload.clear_keys = [...pendingKeyClears];
    }

    if (Object.keys(payload).length === 0) {
        settingsStatus.textContent = "Nothing to save.";
        return;
    }

    try {
        const response = await apiFetch("/api/settings", {
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
        pendingKeyClears = new Set();
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
const downloadAiPdfBtn = document.getElementById("download-ai-pdf-btn");
const analysisActions = document.getElementById("analysis-actions");
const businessPhoto = document.getElementById("business-photo");
const businessPhotoPlaceholder = document.getElementById("business-photo-placeholder");
const businessRating = document.getElementById("business-rating");
const businessPhone = document.getElementById("business-phone");
const businessBadges = document.getElementById("business-badges");
const businessLinks = document.getElementById("business-links");

let currentBusiness = null;
let lastAnalysisMarkdown = null;

function setDownloadButtonVisible(visible) {
    analysisActions.classList.toggle("hidden", !visible);
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

    renderBusinessLinks(biz);
}

function addBusinessLink(label, href) {
    const link = document.createElement("a");
    link.className = "business-link";
    link.href = href;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = label;
    businessLinks.appendChild(link);
}

function renderBusinessLinks(biz) {
    businessLinks.innerHTML = "";

    if (biz.website_url) {
        addBusinessLink("🔗 Visit website", biz.website_url);
    }

    const mapsQuery = encodeURIComponent(`${biz.name} ${biz.address}`);
    addBusinessLink(
        "📍 View on Google Maps",
        `https://www.google.com/maps/search/?api=1&query=${mapsQuery}`
    );

    if (biz.phone) {
        addBusinessLink("📞 Call", `tel:${biz.phone.replace(/[^\d+]/g, "")}`);
    }
}

function renderBusinessPhoto(biz) {
    if (biz.photo_name) {
        businessPhoto.src = apiUrl("/api/photo", { name: biz.photo_name });
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

    const eventSource = new EventSource(apiUrl("/api/analyze/stream", {
        name: currentBusiness.name,
        address: currentBusiness.address,
        has_website: String(Boolean(currentBusiness.has_website)),
        has_photos: String(Boolean(currentBusiness.photo_name)),
        has_reviews: String(Boolean(currentBusiness.rating_count)),
        has_phone: String(Boolean(currentBusiness.phone)),
        website_url: currentBusiness.website_url || "",
    }));

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

            if (data.truncated) {
                const notice = document.createElement("p");
                notice.className = "analysis-truncated";
                notice.textContent =
                    "This report hit the AI provider's output limit and stops early. " +
                    "Try a provider with a larger output budget in Settings.";
                analysisContent.appendChild(notice);
            }

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

function describePdfLine(rawLine) {
    const line = rawLine.replace(/\s+$/, "");

    if (!line.trim()) {
        return { type: "blank" };
    }

    const heading = line.match(/^(#{1,6})\s+(.*)$/);
    if (heading) {
        const level = heading[1].length;
        return {
            type: "heading",
            text: stripInlineMarkdown(heading[2]),
            size: level <= 1 ? 15 : level === 2 ? 13 : 11.5,
            bold: true,
            spaceBefore: level <= 2 ? 14 : 10,
            spaceAfter: 4,
        };
    }

    // Markdown table alignment rows (|---|---|) carry no information once the
    // pipes are rendered as text, so drop them.
    if (/^\s*\|?[\s:|-]+\|[\s:|-]*$/.test(line) && line.includes("-")) {
        return { type: "blank" };
    }

    if (line.trim().startsWith("|")) {
        const cells = line.trim().replace(/^\||\|$/g, "").split("|");
        return {
            type: "text",
            text: cells.map((c) => stripInlineMarkdown(c.trim())).join("  \u2014  "),
            indent: 12,
        };
    }

    const bullet = line.match(/^(\s*)[-*+]\s+(.*)$/);
    if (bullet) {
        const depth = Math.min(Math.floor(bullet[1].length / 2), 3);
        return {
            type: "text",
            text: `\u2022 ${stripInlineMarkdown(bullet[2])}`,
            indent: 12 + depth * 14,
        };
    }

    const numbered = line.match(/^(\s*)(\d+[.)])\s+(.*)$/);
    if (numbered) {
        const depth = Math.min(Math.floor(numbered[1].length / 2), 3);
        return {
            type: "text",
            text: `${numbered[2]} ${stripInlineMarkdown(numbered[3])}`,
            indent: 12 + depth * 14,
        };
    }

    return { type: "text", text: stripInlineMarkdown(line) };
}

function stripInlineMarkdown(text) {
    return text
        .replace(/\*\*(.*?)\*\*/g, "$1")
        .replace(/(^|[^*])\*([^*]+)\*/g, "$1$2")
        .replace(/`([^`]+)`/g, "$1")
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, "$1 ($2)");
}

const PDF_MARGIN_LEFT = 48;
const PDF_MAX_WIDTH = 515;
const PDF_PAGE_BOTTOM = 740;

function pdfFileName(suffix) {
    const safeName = currentBusiness.name.replace(/[^a-z0-9]+/gi, "_");
    return `${safeName}_${suffix}.pdf`;
}

function buildHumanPdf() {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ unit: "pt", format: "letter" });

    const marginLeft = PDF_MARGIN_LEFT;
    const maxWidth = PDF_MAX_WIDTH;
    const pageBottom = PDF_PAGE_BOTTOM;
    const bodySize = 10.5;
    let y = 60;

    function newPageIfNeeded(needed) {
        if (y + needed > pageBottom) {
            doc.addPage();
            y = 60;
        }
    }

    doc.setFont("helvetica", "bold");
    doc.setFontSize(17);
    doc.text(currentBusiness.name, marginLeft, y);
    y += 22;

    doc.setFont("helvetica", "normal");
    doc.setFontSize(10);
    doc.setTextColor(100);
    doc.text(currentBusiness.address, marginLeft, y);
    y += 14;

    if (currentBusiness.website_url) {
        doc.text(currentBusiness.website_url, marginLeft, y);
        y += 14;
    }

    doc.text(
        `Prospectr marketing analysis \u2014 ${new Date().toLocaleDateString()}`,
        marginLeft,
        y
    );
    y += 24;
    doc.setTextColor(0);

    let inCodeBlock = false;

    lastAnalysisMarkdown.split("\n").forEach((rawLine) => {
        if (rawLine.trim().startsWith("```")) {
            inCodeBlock = !inCodeBlock;
            y += 4;
            return;
        }

        if (inCodeBlock) {
            doc.setFont("courier", "normal");
            doc.setFontSize(9);
            doc.splitTextToSize(rawLine || " ", maxWidth - 12).forEach((wrapped) => {
                newPageIfNeeded(12);
                doc.text(wrapped, marginLeft + 12, y);
                y += 12;
            });
            return;
        }

        const spec = describePdfLine(rawLine);

        if (spec.type === "blank") {
            y += 6;
            return;
        }

        if (spec.type === "heading") {
            y += spec.spaceBefore;
            newPageIfNeeded(spec.size + spec.spaceAfter);
            doc.setFont("helvetica", "bold");
            doc.setFontSize(spec.size);
            doc.splitTextToSize(spec.text, maxWidth).forEach((wrapped) => {
                newPageIfNeeded(spec.size + 4);
                doc.text(wrapped, marginLeft, y);
                y += spec.size + 4;
            });
            y += spec.spaceAfter;
            return;
        }

        const indent = spec.indent || 0;
        doc.setFont("helvetica", "normal");
        doc.setFontSize(bodySize);
        doc.splitTextToSize(spec.text, maxWidth - indent).forEach((wrapped) => {
            newPageIfNeeded(15);
            doc.text(wrapped, marginLeft + indent, y);
            y += 15;
        });
    });

    doc.save(pdfFileName("marketing_analysis"));
}


const AI_PDF_PREAMBLE = [
    "HOW TO USE THIS DOCUMENT",
    "",
    "This is a marketing analysis of the business named above, produced by",
    "Prospectr. Everything after the BEGIN marker is Markdown source,",
    "reproduced verbatim and set in a monospaced face so that it survives",
    "text extraction unchanged. Read it as Markdown, not as prose.",
    "",
    "Section 13, \"AI Handoff Brief\", is written specifically for you. It",
    "contains a KEY: value block describing the business, an ordered list of",
    "recommended page sections with draft copy, and the conversion features",
    "this kind of business needs. If you are building a landing page or a",
    "website, that section is your specification.",
    "",
    "Section 13 also lists facts that could NOT be verified. Do not state",
    "any of those on a public page, and do not invent details about this",
    "business that appear nowhere in this document. Where the analysis",
    "marks something unverified, treat it as unknown.",
];

function buildAiPdf() {
    const { jsPDF } = window.jspdf;
    const doc = new jsPDF({ unit: "pt", format: "letter" });

    const marginLeft = PDF_MARGIN_LEFT;
    const maxWidth = PDF_MAX_WIDTH;
    const pageBottom = PDF_PAGE_BOTTOM;
    const lineHeight = 12;
    let y = 60;

    function writeLine(text, { font = "courier", style = "normal", size = 9 } = {}) {
        doc.setFont(font, style);
        doc.setFontSize(size);
        doc.splitTextToSize(text || " ", maxWidth).forEach((wrapped) => {
            if (y + lineHeight > pageBottom) {
                doc.addPage();
                y = 60;
            }
            doc.text(wrapped, marginLeft, y);
            y += lineHeight;
        });
    }

    writeLine("PROSPECTR - AI HANDOFF DOCUMENT", { style: "bold", size: 12 });
    y += 6;

    writeLine(`BUSINESS_NAME: ${currentBusiness.name}`);
    writeLine(`ADDRESS: ${currentBusiness.address}`);
    writeLine(
        `EXISTING_WEBSITE: ${currentBusiness.website_url || "NONE LISTED ON GOOGLE"}`
    );
    writeLine(`PHONE: ${currentBusiness.phone || "NONE LISTED ON GOOGLE"}`);
    writeLine(
        `GOOGLE_RATING: ${
            currentBusiness.rating
                ? `${currentBusiness.rating} from ${currentBusiness.rating_count || 0} reviews`
                : "NONE"
        }`
    );
    writeLine(`GENERATED: ${new Date().toISOString().slice(0, 10)}`);
    y += 10;

    AI_PDF_PREAMBLE.forEach((line) => writeLine(line));
    y += 10;

    writeLine("--- BEGIN ANALYSIS (MARKDOWN) ---", { style: "bold" });
    y += 6;

    lastAnalysisMarkdown.split("\n").forEach((line) => writeLine(line));

    y += 6;
    writeLine("--- END ANALYSIS ---", { style: "bold" });

    doc.save(pdfFileName("ai_handoff"));
}

downloadPdfBtn.addEventListener("click", () => {
    if (!lastAnalysisMarkdown || !currentBusiness) return;
    buildHumanPdf();
});

downloadAiPdfBtn.addEventListener("click", () => {
    if (!lastAnalysisMarkdown || !currentBusiness) return;
    buildAiPdf();
});


async function checkApiKeyStatus() {
    const response = await apiFetch("/api/settings");
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

function sendHeartbeat() {
    apiFetch("/api/heartbeat", { method: "POST" }).catch(() => {});
}

sendHeartbeat();
setInterval(sendHeartbeat, 3000);
