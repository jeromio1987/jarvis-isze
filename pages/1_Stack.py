import streamlit as st

st.set_page_config(page_title="Stack · Jarvis", page_icon="📋", layout="wide")

# ── Data ──────────────────────────────────────────────────────────────────────
PROJECTS = [
    {
        "name": "FY2026 VP Action Plan",
        "status": "🔥",
        "status_label": "Active",
        "summary": "Year-end review + FY2027 planning across all distributors",
        "risk": "ITUK revenue shortfall may skew total GP% — need confirmed Q4 numbers",
    },
    {
        "name": "2026 Pricing / ITUK Dispute",
        "status": "🔥",
        "status_label": "Active",
        "summary": "ITUK challenging ISZE pricing methodology; building defensible position",
        "risk": "Any concession to ITUK sets precedent for all other DBs",
    },
    {
        "name": "PMS Coverage Pilot",
        "status": "🔥",
        "status_label": "Active",
        "summary": "Periodic Maintenance Service campaign — filters, clutch, brake kits",
        "risk": "Coverage gaps in N-Series parts; IML confirmation on kit BOM pending",
    },
    {
        "name": "Lubricants Project",
        "status": "⏳",
        "status_label": "Waiting",
        "summary": "BESCO-brand lubricants upsell initiative; IML go-ahead pending",
        "risk": "No IML green light yet — cannot commit distributor volumes",
    },
    {
        "name": "Competitiveness Dashboard",
        "status": "🔥",
        "status_label": "Active",
        "summary": "IAM vs. ISZE price benchmarking across PMS categories",
        "risk": "Brake disc/pad exposure (~1.9–2.3× IAM) needs pricing response plan",
    },
    {
        "name": "UIO Tool v9",
        "status": "🔥",
        "status_label": "Active",
        "summary": "Units In Operation demand model — Hasegawa survival rate methodology",
        "risk": "D-Max survival curve not confirmed by IML; using proxy from N-Series",
    },
    {
        "name": "AIM — Aftermarket Intelligence",
        "status": "⏳",
        "status_label": "Waiting",
        "summary": "Aftermarket intelligence framework for competitive monitoring",
        "risk": "Scope not yet agreed with IML; resource allocation unclear",
    },
]

STATUS_COLOR = {
    "🔥": "#dc2626",  # red
    "✅": "#16a34a",  # green
    "⏳": "#d97706",  # amber
}

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
.project-card {
    background: #1f2937;
    border-radius: 10px;
    padding: 18px 20px;
    margin-bottom: 14px;
    border-left: 4px solid #3b82f6;
}
.project-card.waiting { border-left-color: #d97706; }
.project-card.done    { border-left-color: #16a34a; }
.card-name  { font-size: 1.05rem; font-weight: 700; color: #f9fafb; margin-bottom: 4px; }
.card-sum   { font-size: 0.88rem; color: #d1d5db; margin-bottom: 6px; }
.card-risk  { font-size: 0.8rem;  color: #fca5a5; }
.badge {
    display: inline-block;
    font-size: 0.72rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 999px;
    margin-left: 8px;
    vertical-align: middle;
}
.badge-active  { background: #7f1d1d; color: #fecaca; }
.badge-waiting { background: #78350f; color: #fde68a; }
.badge-done    { background: #14532d; color: #bbf7d0; }
</style>
""",
    unsafe_allow_html=True,
)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# 📋 Stack")
st.caption("Jerome's active ISZE projects — hardcoded personal dashboard")

active = sum(1 for p in PROJECTS if p["status"] == "🔥")
waiting = sum(1 for p in PROJECTS if p["status"] == "⏳")
done = sum(1 for p in PROJECTS if p["status"] == "✅")

m1, m2, m3 = st.columns(3)
m1.metric("🔥 Active", active)
m2.metric("⏳ Waiting", waiting)
m3.metric("✅ Done", done)

st.divider()

# ── Cards ─────────────────────────────────────────────────────────────────────
for p in PROJECTS:
    status = p["status"]
    css_class = {"🔥": "active", "⏳": "waiting", "✅": "done"}.get(status, "")
    badge_class = f"badge-{css_class}"

    st.markdown(
        f"""
<div class="project-card {css_class}">
  <div class="card-name">
    {status} {p['name']}
    <span class="badge {badge_class}">{p['status_label']}</span>
  </div>
  <div class="card-sum">{p['summary']}</div>
  <div class="card-risk">⚠ Risk: {p['risk']}</div>
</div>
""",
        unsafe_allow_html=True,
    )
