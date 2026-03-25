import sys
import os
import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.api_clients import ask_claude
from utils.config import ANTHROPIC_API_KEY

st.set_page_config(page_title="TED Scraper · Jarvis", page_icon="🎤", layout="wide")

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# 🎤 TED Scraper")
st.caption("Browse TED talks by topic — scraped live from ted.com")

st.divider()

# ── Inputs ────────────────────────────────────────────────────────────────────
col1, col2 = st.columns([3, 1], gap="medium")
with col1:
    topic = st.text_input("Topic search", placeholder="e.g. leadership, supply chain, AI, pricing")
with col2:
    n_results = st.slider("Max results", min_value=5, max_value=20, value=10)

search_btn = st.button("🔍 Search TED Talks", type="primary")

# ── Scraper ───────────────────────────────────────────────────────────────────

def scrape_ted(query: str, max_results: int) -> list[dict]:
    """Scrape TED talk search results."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    url = f"https://www.ted.com/talks?q={requests.utils.quote(query)}&language=en"

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        return [{"error": str(e)}]

    soup = BeautifulSoup(resp.text, "lxml")
    talks = []

    # TED uses a mix of structured article tags
    cards = soup.select("div.media__message") or soup.select("[class*='talk-link']")

    # Fallback: generic article / h4 approach
    if not cards:
        cards = soup.find_all("div", class_=lambda c: c and "talk" in c.lower())

    # Try data from <script type="application/ld+json"> structured data
    import json as _json

    ld_blocks = soup.find_all("script", type="application/ld+json")
    for block in ld_blocks:
        try:
            data = _json.loads(block.string or "")
            if isinstance(data, list):
                items = data
            elif isinstance(data, dict) and data.get("@type") == "ItemList":
                items = data.get("itemListElement", [])
            else:
                items = [data]
            for item in items:
                thing = item.get("item", item)
                if thing.get("@type") in ("VideoObject", "CreativeWork", "Article"):
                    title = thing.get("name", "")
                    desc = thing.get("description", "")
                    talk_url = thing.get("url", "")
                    author = ""
                    if "author" in thing:
                        author_info = thing["author"]
                        if isinstance(author_info, dict):
                            author = author_info.get("name", "")
                        elif isinstance(author_info, list) and author_info:
                            author = author_info[0].get("name", "")
                    duration = thing.get("duration", "")
                    talks.append({
                        "Title": title,
                        "Speaker": author,
                        "Duration": duration,
                        "Description": desc[:120] + "…" if len(desc) > 120 else desc,
                        "URL": talk_url,
                    })
                    if len(talks) >= max_results:
                        break
        except Exception:
            continue
        if len(talks) >= max_results:
            break

    # If structured data gave nothing, do a simple link parse
    if not talks:
        for a in soup.select("a[href*='/talks/']"):
            href = a.get("href", "")
            text = a.get_text(strip=True)
            if text and "/talks/" in href and not href.endswith("/talks/"):
                full_url = "https://www.ted.com" + href if href.startswith("/") else href
                talks.append({
                    "Title": text,
                    "Speaker": "",
                    "Duration": "",
                    "Description": "",
                    "URL": full_url,
                })
            if len(talks) >= max_results:
                break

    return talks[:max_results]


# ── Results ───────────────────────────────────────────────────────────────────
if search_btn:
    if not topic.strip():
        st.error("Please enter a topic to search.")
    else:
        with st.spinner(f"Searching TED for '{topic}'..."):
            results = scrape_ted(topic, n_results)

        if not results:
            st.warning("No results found. Try a different topic.")
        elif "error" in results[0]:
            st.error(f"Scraping error: {results[0]['error']}")
        else:
            st.success(f"Found {len(results)} talk(s) for **{topic}**")
            st.divider()

            for i, talk in enumerate(results):
                with st.container():
                    col_a, col_b = st.columns([5, 1])
                    with col_a:
                        title = talk.get("Title", "—")
                        url = talk.get("URL", "")
                        speaker = talk.get("Speaker", "")
                        duration = talk.get("Duration", "")
                        desc = talk.get("Description", "")

                        if url:
                            st.markdown(f"### [{title}]({url})")
                        else:
                            st.markdown(f"### {title}")

                        meta_parts = []
                        if speaker:
                            meta_parts.append(f"**{speaker}**")
                        if duration:
                            meta_parts.append(duration)
                        if meta_parts:
                            st.caption(" · ".join(meta_parts))
                        if desc:
                            st.write(desc)

                    with col_b:
                        # Summarize stub — placeholder until transcript API available
                        if st.button("Summarize", key=f"sum_{i}"):
                            if not ANTHROPIC_API_KEY:
                                st.warning("API key needed.")
                            else:
                                st.info(
                                    "📌 Transcript extraction not yet implemented. "
                                    "Future: fetch YouTube auto-captions via yt-dlp and summarize with Claude."
                                )

                    st.divider()

            # Also show as a compact table
            with st.expander("View as table"):
                df = pd.DataFrame(results)
                if "URL" in df.columns:
                    df["Link"] = df["URL"].apply(
                        lambda u: f"[Open]({u})" if u else ""
                    )
                    df = df.drop(columns=["URL"])
                st.markdown(df.to_markdown(index=False), unsafe_allow_html=True)
else:
    st.info("Enter a topic above and click **Search TED Talks** to browse talks.")
