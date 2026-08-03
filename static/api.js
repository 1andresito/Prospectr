// api.js — shared access to the per-launch API token.
//
// Flask stamps a fresh random token into the page it renders. Every /api/
// route requires it, which stops any other site the user happens to have open
// from driving this app's endpoints and spending their Google Places or AI
// credits in the background.

const PROSPECTR_TOKEN =
    document.querySelector('meta[name="prospectr-token"]')?.content ?? "";

/** Build an /api/ URL with the token and any extra query parameters. */
function apiUrl(path, params = {}) {
    const url = new URL(path, window.location.origin);
    Object.entries(params).forEach(([key, value]) => {
        url.searchParams.set(key, value);
    });
    url.searchParams.set("token", PROSPECTR_TOKEN);
    return url.toString();
}

/** fetch() wrapper that attaches the token header. */
function apiFetch(path, options = {}) {
    return fetch(path, {
        ...options,
        headers: {
            ...(options.headers ?? {}),
            "X-Prospectr-Token": PROSPECTR_TOKEN,
        },
    });
}
