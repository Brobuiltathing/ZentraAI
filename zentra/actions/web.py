import re
import urllib.parse
from html import unescape

import requests

from zentra.logger import log
from zentra.ollama import ollama_raw_sync


_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


def _strip_html(html: str) -> str:
    html = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<style[\s\S]*?</style>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<nav[\s\S]*?</nav>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<footer[\s\S]*?</footer>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<header[\s\S]*?</header>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<aside[\s\S]*?</aside>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<[^>]+>", " ", html)
    text = unescape(html)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


def _search_duckduckgo_sync(query: str, max_results: int = 5) -> list[dict]:
    try:
        url = "https://html.duckduckgo.com/html/"
        params = {"q": query}
        headers = {"User-Agent": _DEFAULT_UA}
        r = requests.post(url, data=params, headers=headers, timeout=10)
        r.raise_for_status()
        html = r.text

        results = []
        pattern = re.compile(
            r'<a[^>]+class="result__a"[^>]+href="([^"]+)"[^>]*>(.*?)</a>[\s\S]*?'
            r'<a[^>]+class="result__snippet"[^>]*>(.*?)</a>',
            re.IGNORECASE,
        )

        for m in pattern.finditer(html):
            raw_url = m.group(1)
            title = _strip_html(m.group(2))
            snippet = _strip_html(m.group(3))

            if raw_url.startswith("//duckduckgo.com/l/?uddg="):
                try:
                    actual = urllib.parse.parse_qs(raw_url.split("?", 1)[1])
                    raw_url = urllib.parse.unquote(actual.get("uddg", [raw_url])[0])
                except Exception:
                    pass

            if raw_url.startswith("/"):
                raw_url = "https:" + raw_url

            if raw_url and title:
                results.append({
                    "url": raw_url,
                    "title": title[:200],
                    "snippet": snippet[:300],
                })

            if len(results) >= max_results:
                break

        return results
    except Exception as exc:
        log.warning(f"DuckDuckGo search failed: {exc}")
        return []


def handle_web_search(data: dict) -> str:
    query = (data.get("app") or data.get("reply") or data.get("content") or "").strip()
    if not query:
        return "web_search: provide a search query."

    log.info(f"Web search: {query}")
    results = _search_duckduckgo_sync(query, max_results=6)

    if not results:
        return f"No search results found for: {query}"

    result_text = "\n\n".join(
        f"[{i+1}] {r['title']}\n{r['url']}\n{r['snippet']}"
        for i, r in enumerate(results)
    )

    answer = ollama_raw_sync(
        "Answer the user's question using ONLY the search results provided. "
        "Be concise. Cite sources by number like [1] or [2].",
        f"Question: {query}\n\nSearch results:\n{result_text}",
        max_tokens=400,
    )

    source_list = "\n".join(f"  [{i+1}] {r['title']} — {r['url']}" for i, r in enumerate(results))
    return f"**Search:** {query}\n\n{answer}\n\n**Sources:**\n{source_list}"


def handle_web_fetch(data: dict) -> str:
    url = (data.get("app") or data.get("filename") or data.get("reply") or "").strip()
    instruction = (data.get("reply") or "").strip()

    if not url:
        return "web_fetch: provide a URL."

    if not url.startswith(("http://", "https://")):
        url = "https://" + url

    log.info(f"Web fetch: {url}")

    try:
        r = requests.get(url, headers={"User-Agent": _DEFAULT_UA}, timeout=15)
        r.raise_for_status()
    except Exception as exc:
        return f"Failed to fetch `{url}`: {exc}"

    content_type = r.headers.get("content-type", "").lower()
    if "html" not in content_type and "text" not in content_type:
        return f"URL returned non-text content ({content_type}). Cannot process."

    text = _strip_html(r.text)
    text = text[:8000]

    if instruction and instruction.lower() not in ("fetch this", url.lower()):
        summary_prompt = f"User instruction: {instruction}\n\nPage content:\n{text}"
        system = "You are analysing a web page according to the user's instruction. Be direct and concise."
    else:
        summary_prompt = f"Summarise this web page in 3-5 sentences. Include the key points.\n\n{text}"
        system = "Summarise web content concisely."

    summary = ollama_raw_sync(system, summary_prompt, max_tokens=400)

    return f"**Page:** {url}\n\n{summary}"
