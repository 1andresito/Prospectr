import re
import os
from urllib.parse import urlparse

import requests

BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"
REQUEST_TIMEOUT_SECONDS = 12
MAX_RESULTS_PER_QUERY = 5
MAX_SOURCES = 15
MAX_PAGE_CHARS = 9000
MAX_TOTAL_RESEARCH_CHARS = 30000

USER_AGENT = "Prospectr-Research/1.0"


def _clean_text(value):
    if not value:
        return ""
    value = re.sub(r"<[^>]+>", " ", str(value))
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def _search(query):
    api_key = os.getenv("BRAVE_SEARCH_API_KEY")
    if not api_key:
        return []

    headers = {
        "Accept": "application/json",
        "X-Subscription-Token": api_key,
        "User-Agent": USER_AGENT,
    }

    params = {
        "q": query,
        "count": MAX_RESULTS_PER_QUERY,
        "safesearch": "moderate",
    }

    try:
        response = requests.get(
            BRAVE_SEARCH_URL,
            headers=headers,
            params=params,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError):
        return []

    results = []
    for item in data.get("web", {}).get("results", []):
        url = item.get("url")
        if not url:
            continue

        results.append({
            "title": _clean_text(item.get("title")),
            "url": url,
            "description": _clean_text(item.get("description")),
        })

    return results


def _fetch_page(url):
    """Fetch a public HTML page and extract readable text conservatively."""
    try:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https"):
            return None

        response = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT_SECONDS,
            allow_redirects=True,
        )
        response.raise_for_status()

        content_type = response.headers.get("content-type", "").lower()
        if "text/html" not in content_type:
            return None

        html = response.text[:300000]

        html = re.sub(
            r"<(script|style|noscript|svg)\b[^>]*>.*?</\1>",
            " ",
            html,
            flags=re.I | re.S,
        )
        text = _clean_text(html)

        if not text:
            return None

        return {
            "url": response.url,
            "text": text[:MAX_PAGE_CHARS],
        }
    except requests.RequestException:
        return None


def research_business(name, address, website_url=None):
    """
    Research a business using a configurable web search API plus its public
    homepage when available.

    Returns source metadata and a bounded research context for the AI.
    """
    queries = [
        f'"{name}" "{address}"',
        f'"{name}" reviews',
        f'"{name}" social media',
        f'"{name}" competitors "{address}"',
    ]

    seen_urls = set()
    sources = []

    for query in queries:
        for result in _search(query):
            url = result["url"]
            if url in seen_urls:
                continue
            seen_urls.add(url)
            sources.append(result)
            if len(sources) >= MAX_SOURCES:
                break
        if len(sources) >= MAX_SOURCES:
            break

    pages = []
    if website_url:
        page = _fetch_page(website_url)
        if page:
            pages.append(page)

    context_parts = []

    if sources:
        context_parts.append("WEB SEARCH RESULTS:")
        for source in sources:
            context_parts.append(
                f"- {source['title']}\n"
                f"  URL: {source['url']}\n"
                f"  Summary: {source['description']}"
            )

    if pages:
        context_parts.append("\nWEBSITE HOMEPAGE CONTENT:")
        for page in pages:
            context_parts.append(
                f"- URL: {page['url']}\n"
                f"  Content: {page['text']}"
            )

    context = "\n".join(context_parts)
    context = context[:MAX_TOTAL_RESEARCH_CHARS]

    return {
        "enabled": bool(os.getenv("BRAVE_SEARCH_API_KEY")),
        "sources": sources,
        "pages": pages,
        "context": context,
    }
