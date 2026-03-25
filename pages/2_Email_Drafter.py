import sys
import os
import streamlit as st

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from utils.api_clients import ask_claude
from utils.config import ANTHROPIC_API_KEY

st.set_page_config(page_title="Email Drafter · Jarvis", page_icon="✉️", layout="wide")

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("# ✉️ Email Drafter")
st.caption("Draft professional ISZE emails with Claude — IML, ITUK, distributor-ready")

if not ANTHROPIC_API_KEY:
    st.warning("⚠️ ANTHROPIC_API_KEY not set. Add it to your `.env` file to use this page.")

st.divider()

# ── Inputs ────────────────────────────────────────────────────────────────────
col_left, col_right = st.columns([1, 1], gap="large")

with col_left:
    st.subheader("Email inputs")

    to_field = st.text_input("To", placeholder="e.g. Ryusuke Tanaka (IML), James Marsh (ITUK)")
    subject = st.text_input("Subject", placeholder="e.g. FY2026 Q4 Parts Revenue Update")
    context = st.text_area(
        "Context / bullet points",
        placeholder=(
            "- Q4 revenue came in at €X vs. target €Y\n"
            "- Key shortfall: ITUK brake disc volume down 18%\n"
            "- Request: approval to proceed with pricing review"
        ),
        height=180,
    )

    tone = st.selectbox(
        "Tone",
        options=["Professional", "Formal Japanese-style", "Direct"],
        help=(
            "Professional: standard business English. "
            "Formal Japanese-style: respectful hierarchy, indirect framing. "
            "Direct: concise, no filler."
        ),
    )

    language = st.selectbox("Language", options=["English", "French"])

    draft_btn = st.button("✉️ Draft with Claude", type="primary", use_container_width=True)

# ── Output ────────────────────────────────────────────────────────────────────
with col_right:
    st.subheader("Draft output")

    if draft_btn:
        if not context.strip():
            st.error("Please enter some context or bullet points.")
        else:
            TONE_INSTRUCTIONS = {
                "Professional": "Use clear, professional business English. Structured paragraphs, courteous but not overly formal.",
                "Formal Japanese-style": (
                    "Use formal, hierarchically respectful language appropriate for communications to Japanese parent company (IML). "
                    "Open with respectful acknowledgement, frame requests as alignment opportunities, "
                    "avoid direct criticism, lead with appreciation before raising issues."
                ),
                "Direct": (
                    "Be concise and direct. No filler phrases, no padding. Lead with the key point immediately. "
                    "Short paragraphs. Bullet points where appropriate."
                ),
            }

            system_prompt = (
                "You are drafting professional emails on behalf of Jérôme Van der Pluym, "
                "Parts Sales Manager at Isuzu Motors Europe (ISZE/IE40). "
                "ISZE is a parts distribution hub supplying genuine Isuzu parts to European distributors. "
                "Key contacts: IML (Japan parent — Ryusuke Tanaka, Tomoaki Hiratsuka), "
                "ITUK (UK distributor — largest by volume), "
                "European distributors (UTI/UMI Israel, GA Armenia, CBC Kazakhstan, IMG Germany). "
                f"Tone instruction: {TONE_INSTRUCTIONS[tone]} "
                f"Language: write the email in {language}. "
                "Output ONLY the email (subject line + body). Do not add commentary outside the email."
            )

            user_prompt = (
                f"Draft an email with the following details:\n\n"
                f"To: {to_field or '(not specified)'}\n"
                f"Subject: {subject or '(not specified)'}\n\n"
                f"Key points / context:\n{context}"
            )

            with st.spinner("Drafting..."):
                result = ask_claude(user_prompt, system=system_prompt)

            st.text_area("", value=result, height=420, key="draft_output")
            st.caption("Select all and copy, or edit inline above.")
    else:
        st.info("Fill in the inputs on the left and click **Draft with Claude**.")
