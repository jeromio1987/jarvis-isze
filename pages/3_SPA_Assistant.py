import sys
import os
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.api_clients import ask_claude
from utils.config import ANTHROPIC_API_KEY

st.set_page_config(page_title="SPA Assistant · Jarvis", page_icon="📄", layout="wide")

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# 📄 SPA Assistant")
st.caption("Special Price Agreement — draft responses and get approval recommendations")

if not ANTHROPIC_API_KEY:
    st.warning("⚠️ ANTHROPIC_API_KEY not set. Add it to your `.env` file to use this page.")

st.divider()

# ── Routing logic ─────────────────────────────────────────────────────────────
IML_ESCALATION_KEYWORDS = ["masumi", "yoshimoto"]


def requires_iml_escalation(distributor: str, justification: str) -> bool:
    text = (distributor + " " + justification).lower()
    return any(kw in text for kw in IML_ESCALATION_KEYWORDS)


# ── Inputs ────────────────────────────────────────────────────────────────────
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.subheader("SPA request details")

    distributor = st.text_input(
        "Distributor name", placeholder="e.g. ITUK, UTI, IMG, GA, CBC"
    )
    part_numbers = st.text_area(
        "Part number(s)",
        placeholder="One per line, e.g.:\n8-97352080-0\n8-97352081-0",
        height=120,
    )
    discount_pct = st.slider(
        "Requested discount %",
        min_value=1,
        max_value=50,
        value=10,
        step=1,
        format="%d%%",
    )
    justification = st.text_area(
        "Distributor justification",
        placeholder="e.g. Fleet tender, competitive pressure from IAM, end-customer price cap",
        height=120,
    )

    generate_btn = st.button("📄 Generate SPA response", type="primary", use_container_width=True)

# ── Output ────────────────────────────────────────────────────────────────────
with col_right:
    st.subheader("SPA recommendation & draft letter")

    if generate_btn:
        if not distributor.strip():
            st.error("Please enter a distributor name.")
        elif not part_numbers.strip():
            st.error("Please enter at least one part number.")
        else:
            escalate = requires_iml_escalation(distributor, justification)

            # Determine routing label for prompt context
            if escalate:
                routing = "IML ESCALATION REQUIRED"
                routing_reason = (
                    "The request involves contacts or conditions that require IML (Japan parent) approval. "
                    "ISZE cannot approve independently."
                )
                rec_color = "orange"
                rec_label = "🔶 Escalate to IML"
            elif discount_pct > 25:
                routing = "REJECT"
                routing_reason = f"Requested discount of {discount_pct}% exceeds ISZE's standard maximum threshold (25%)."
                rec_color = "red"
                rec_label = "🔴 Recommend Reject"
            elif discount_pct > 15:
                routing = "CONDITIONAL APPROVAL — senior review required"
                routing_reason = f"Discount of {discount_pct}% is above standard tier; requires VP sign-off."
                rec_color = "orange"
                rec_label = "🟡 Conditional Approval"
            else:
                routing = "APPROVE (standard flow)"
                routing_reason = f"Discount of {discount_pct}% is within standard SPA parameters for this distributor type."
                rec_color = "green"
                rec_label = "🟢 Recommend Approve"

            # Show recommendation badge
            st.markdown(f"### Recommendation: {rec_label}")
            st.caption(routing_reason)
            st.divider()

            system_prompt = (
                "You are drafting Special Price Agreement (SPA) response letters for Isuzu Motors Europe (ISZE/IE40). "
                "An SPA is a formal discount granted to a distributor for specific part numbers, "
                "typically for fleet tenders or competitive situations. "
                "Jerome Van der Pluym is Parts Sales Manager. "
                "Tone: professional, concise, data-referenced where possible. "
                "Structure the letter: ISZE letterhead reference, date placeholder, distributor address block, "
                "RE: line, body (acknowledge request, state decision, conditions if any, validity period), "
                "closing. Add a CONDITIONS section if the approval is conditional. "
                "Output ONLY the letter."
            )

            parts_list = "\n".join(
                f"  - {p.strip()}" for p in part_numbers.strip().splitlines() if p.strip()
            )

            user_prompt = (
                f"Draft a SPA response letter.\n\n"
                f"Distributor: {distributor}\n"
                f"Part numbers:\n{parts_list}\n"
                f"Requested discount: {discount_pct}%\n"
                f"Distributor justification: {justification or '(none provided)'}\n\n"
                f"Routing decision: {routing}\n"
                f"Reason: {routing_reason}\n\n"
                "Write the response letter accordingly."
            )

            with st.spinner("Generating SPA response..."):
                result = ask_claude(user_prompt, system=system_prompt)

            st.text_area("Draft letter", value=result, height=460, key="spa_output")
            st.caption("Review before sending. Adjust conditions, validity dates, and part-number list as needed.")
    else:
        st.info("Fill in the SPA details on the left and click **Generate SPA response**.")
