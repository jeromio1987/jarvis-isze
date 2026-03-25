import streamlit as st

st.set_page_config(
    page_title="Jarvis · ISZE",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ───────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
[data-testid="stSidebar"] { background-color: #111827; }
[data-testid="stSidebar"] * { color: #e5e7eb !important; }
[data-testid="stSidebarNav"] a { font-size: 0.9rem; }
.jarvis-title {
    font-size: 2.4rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    color: #f9fafb;
}
.jarvis-sub {
    font-size: 0.85rem;
    color: #9ca3af;
    margin-top: -8px;
    margin-bottom: 24px;
}
footer { visibility: hidden; }
.jarvis-footer {
    position: fixed;
    bottom: 0;
    left: 0;
    width: 100%;
    background: #111827;
    color: #6b7280;
    text-align: center;
    font-size: 0.72rem;
    padding: 6px 0;
    z-index: 999;
    letter-spacing: 0.05em;
}
</style>
""",
    unsafe_allow_html=True,
)

# ── Sidebar header ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        '<div class="jarvis-title">⚡ Jarvis</div>'
        '<div class="jarvis-sub">ISZE Internal Tool</div>',
        unsafe_allow_html=True,
    )
    st.divider()
    st.caption("Navigate using the pages above.")
    st.divider()
    st.caption("Model: claude-opus-4-6")

# ── Home page content ─────────────────────────────────────────────────────────
st.markdown("## Welcome to Jarvis")
st.markdown(
    """
Jarvis is your personal AI workspace for Isuzu Motors Europe (ISZE) work.

| Page | What it does |
|------|-------------|
| **Stack** | Live status of your active ISZE projects |
| **Email Drafter** | Draft emails to IML, ITUK, or distributors with Claude |
| **SPA Assistant** | Generate Special Price Agreement responses |
| **TED Scraper** | Browse TED talks by topic |

Select a page from the sidebar to get started.
"""
)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown(
    '<div class="jarvis-footer">Jarvis — ISZE Internal Tool &nbsp;|&nbsp; Not for external distribution</div>',
    unsafe_allow_html=True,
)
