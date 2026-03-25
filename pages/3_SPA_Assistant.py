import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import sys
import os
import io

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.config import ANTHROPIC_API_KEY, ISZE_CONTEXT
from utils.api_clients import ask_claude

st.set_page_config(page_title="SPA Assistant v2", layout="wide")
st.title("SPA Assistant v2")
st.caption("Special Price Agreement evaluator — ROI, margin floor, and approval routing for ISZE")

with st.sidebar:
    st.header("Settings")
    fx_rate = st.number_input("FX Rate (JPY/EUR)", value=163.7, step=0.1, format="%.1f")
    min_gp_pct = st.slider("Min GP% Floor", min_value=10, max_value=40, value=22) / 100
    tml_threshold = st.number_input("IML Escalation Threshold (EUR/yr)", value=5000, step=500)
    st.caption("Annual GP impact above this triggers IML escalation review")

SOURCE_DISCOUNTS = {"J (Japan)": 0.62, "T (Thailand)": 0.611}
CLASSES = ["C", "D", "F", "J", "M", "P", "V", "T", "0", "XC", "XF", "XD", "DD", "Other"]

if "spa_rows" not in st.session_state:
    st.session_state.spa_rows = [{}]
if "prefill" not in st.session_state:
    st.session_state.prefill = {}

def add_row():
    st.session_state.spa_rows.append({})

def remove_row(i):
    if len(st.session_state.spa_rows) > 1:
        st.session_state.spa_rows.pop(i)

def fob_cost(bp_jpy, fx, src_discount):
    if fx <= 0:
        return 0
    return bp_jpy / fx * src_discount

def gp_eur(price, cost):
    return price - cost

def gp_pct(price, cost):
    if price <= 0:
        return 0
    return (price - cost) / price

def floor_price(cost, min_gp):
    if min_gp >= 1:
        return float('inf')
    return cost / (1 - min_gp)

def breakeven_volume(current_gp_eur, current_vol, new_gp_eur):
    if new_gp_eur <= 0:
        return float('inf')
    return (current_gp_eur * current_vol) / new_gp_eur

def detect_header_row(df_raw):
    """Find the row index that looks like the real header — must have multi-word column names."""
    for i, row in df_raw.iterrows():
        vals = [str(v).strip() for v in row.values if str(v).strip() not in ("nan", "", "None")]
        if len(vals) < 3:
            continue
        # Require at least one value longer than 3 chars (not just single letters like C/D/F)
        has_multichar = any(len(v) > 3 for v in vals)
        # Require "part" or "b/p" somewhere in the row
        row_text = " ".join(vals).lower()
        has_part_col = "part" in row_text or "b/p" in row_text or "bp" in row_text
        if has_multichar and has_part_col:
            return i
    return 0

def parse_pricer_file(uploaded_file):
    """Parse ISZE New Parts Pricer Excel/CSV, return list of dicts."""
    try:
        if uploaded_file.name.endswith(".csv"):
            df_raw = pd.read_csv(uploaded_file, header=None, dtype=str)
        else:
            df_raw = pd.read_excel(uploaded_file, header=None, dtype=str)
    except Exception as e:
        return None, f"Could not read file: {e}"

    header_row = detect_header_row(df_raw)
    df = df_raw.iloc[header_row:].reset_index(drop=True)
    df.columns = df.iloc[0].astype(str).str.strip()
    df = df.iloc[1:].reset_index(drop=True)
    df = df.dropna(how="all")

    col_map = {}
    cols_lower = {c.lower().strip(): c for c in df.columns}

    for candidate in ["inquired part no.", "stock part no. (isuzu)", "stock part no.", "part no.", "part number"]:
        if candidate in cols_lower:
            col_map["pn"] = cols_lower[candidate]
            break
    if "pn" not in col_map:
        col_map["pn"] = df.columns[0]

    for candidate in ["part name", "description", "name"]:
        if candidate in cols_lower:
            col_map["desc"] = cols_lower[candidate]
            break

    for candidate in ["b/p (new pn)", "b/p", "bp", "base price", "b/p(new pn)"]:
        if candidate in cols_lower:
            col_map["bp"] = cols_lower[candidate]
            break

    for candidate in ["class"]:
        if candidate in cols_lower:
            col_map["cls"] = cols_lower[candidate]
            break

    rows = []
    for _, row in df.iterrows():
        pn_val = str(row.get(col_map.get("pn", ""), "")).strip()
        if not pn_val or pn_val.lower() in ("nan", "", "none"):
            continue
        # Skip single-letter rows (class legend) and note/source rows
        if len(pn_val) <= 2 and pn_val.isalpha():
            continue
        if pn_val.lower().startswith("note") or pn_val.lower().startswith("source"):
            continue
        bp_raw = str(row.get(col_map.get("bp", ""), "0")).strip()
        try:
            bp_val = float(bp_raw.replace(",", ""))
        except Exception:
            bp_val = 0.0
        rows.append({
            "pn": pn_val,
            "desc": str(row.get(col_map.get("desc", ""), "")).strip(),
            "bp_jpy": bp_val,
            "cls": str(row.get(col_map.get("cls", ""), "C")).strip(),
        })
    return rows, None

col_left, col_right = st.columns([1, 1.2], gap="large")

with col_left:
    st.subheader("SPA Request Details")
    distributor = st.text_input("Distributor", placeholder="e.g. ITUK, Universal Motors Israel")
    justification = st.text_area("Distributor Justification", placeholder="Reason for requesting special price", height=80)

    # ── File upload ────────────────────────────────────────────────────────────
    with st.expander("Upload from Pricer File", expanded=False):
        template_csv = "Part No.,Part Name,B/P,Class,Source,PR00_EUR,Requested_EUR,Volume_yr\n8982705240,Oil filter,1200,C,J (Japan),6.80,5.80,500\n"
        st.download_button("Download template CSV", template_csv, "spa_template.csv", "text/csv")

        uploaded = st.file_uploader("Upload ISZE Pricer (.xlsx or .csv)", type=["xlsx", "xls", "csv"], key="pricer_upload")
        if uploaded is not None:
            rows, err = parse_pricer_file(uploaded)
            if err:
                st.error(err)
            elif rows:
                preview_df = pd.DataFrame(rows).rename(columns={"pn": "Part No.", "desc": "Description", "bp_jpy": "BP (JPY)", "cls": "Class"})
                st.write(f"Detected {len(rows)} parts:")
                st.dataframe(preview_df[["Part No.", "Description", "BP (JPY)", "Class"]].head(20), use_container_width=True)

                # Check if full template with all columns
                full_cols = False
                try:
                    if uploaded.name.endswith(".csv"):
                        uploaded.seek(0)
                        check_df = pd.read_csv(uploaded, dtype=str)
                    else:
                        uploaded.seek(0)
                        check_df = pd.read_excel(uploaded, dtype=str)
                    check_cols = [c.lower().strip() for c in check_df.columns]
                    if all(c in check_cols for c in ["pr00_eur", "requested_eur", "volume_yr", "source"]):
                        full_cols = True
                except Exception:
                    pass

                if st.button(f"Load {len(rows)} parts into SPA form"):
                    if full_cols:
                        # Load full template with all columns
                        uploaded.seek(0)
                        if uploaded.name.endswith(".csv"):
                            tdf = pd.read_csv(uploaded, dtype=str)
                        else:
                            tdf = pd.read_excel(uploaded, dtype=str)
                        tdf.columns = tdf.columns.str.lower().str.strip()
                        new_prefill = {}
                        for idx, row in tdf.iterrows():
                            try:
                                new_prefill[idx] = {
                                    "pn": str(row.get("part no.", row.get("part no", ""))).strip(),
                                    "desc": str(row.get("part name", row.get("description", ""))).strip(),
                                    "bp_jpy": float(str(row.get("b/p", row.get("bp", 0))).replace(",", "") or 0),
                                    "cls": str(row.get("class", "C")).strip(),
                                    "source": str(row.get("source", "J (Japan)")).strip(),
                                    "pr00": float(str(row.get("pr00_eur", 0)).replace(",", "") or 0),
                                    "req": float(str(row.get("requested_eur", 0)).replace(",", "") or 0),
                                    "vol": int(float(str(row.get("volume_yr", 0)).replace(",", "") or 0)),
                                }
                            except Exception:
                                pass
                        st.session_state.prefill = new_prefill
                        st.session_state.spa_rows = [{} for _ in range(len(tdf))]
                    else:
                        st.session_state.spa_rows = [{} for _ in range(len(rows))]
                        st.session_state.prefill = {i: r for i, r in enumerate(rows)}
                    st.rerun()
            else:
                st.warning("No parts detected in the file. Check the format.")

    st.markdown("---")
    st.markdown("**Part Numbers**")

    pn_data = []
    for i, _ in enumerate(st.session_state.spa_rows):
        pf = st.session_state.prefill.get(i, {})
        with st.expander(f"Part #{i+1}" + (f" — {pf.get('pn', '')}" if pf.get("pn") else ""), expanded=True):
            c1, c2 = st.columns(2)
            pn = c1.text_input("Part Number", key=f"pn_{i}", value=pf.get("pn", ""), placeholder="e.g. 8982705240")
            desc = c2.text_input("Description", key=f"desc_{i}", value=pf.get("desc", ""), placeholder="e.g. Oil filter")
            c3, c4 = st.columns(2)
            src_default = pf.get("source", "J (Japan)")
            src_idx = list(SOURCE_DISCOUNTS.keys()).index(src_default) if src_default in SOURCE_DISCOUNTS else 0
            source_label = c3.selectbox("Source", list(SOURCE_DISCOUNTS.keys()), index=src_idx, key=f"src_{i}")
            cls_default = pf.get("cls", "C")
            cls_idx = CLASSES.index(cls_default) if cls_default in CLASSES else 0
            pn_class = c4.selectbox("Class", CLASSES, index=cls_idx, key=f"cls_{i}")
            c5, c6 = st.columns(2)
            bp_jpy = c5.number_input("BP (JPY)", min_value=0.0, value=float(pf.get("bp_jpy", 0.0)), step=100.0, key=f"bp_{i}", format="%.2f")
            pr00 = c6.number_input("PR00 Price (EUR)", min_value=0.0, value=float(pf.get("pr00", 0.0)), step=1.0, key=f"pr00_{i}", format="%.2f")
            c7, c8 = st.columns(2)
            req_price = c7.number_input("Requested Price (EUR)", min_value=0.0, value=float(pf.get("req", 0.0)), step=1.0, key=f"req_{i}", format="%.2f")
            volume = c8.number_input("Est. Volume (units/yr)", min_value=0, value=int(pf.get("vol", 0)), step=10, key=f"vol_{i}")
            comp_price = st.number_input("Competitor Ref. Price (EUR, 0=not provided)", min_value=0.0, value=0.0, step=1.0, key=f"comp_{i}", format="%.2f")
            if i > 0:
                st.button(f"Remove PN #{i+1}", on_click=remove_row, args=(i,), key=f"rem_{i}")

            if pn and bp_jpy > 0 and pr00 > 0 and req_price > 0 and volume > 0:
                src_disc = SOURCE_DISCOUNTS[source_label]
                cost = fob_cost(bp_jpy, fx_rate, src_disc)
                disc_pct = (pr00 - req_price) / pr00 if pr00 > 0 else 0
                fp = floor_price(cost, min_gp_pct)
                curr_gp_eur = gp_eur(pr00, cost)
                req_gp_eur = gp_eur(req_price, cost)
                curr_gp_pct = gp_pct(pr00, cost)
                req_gp_pct = gp_pct(req_price, cost)
                ann_curr = curr_gp_eur * volume
                ann_req = req_gp_eur * volume
                ann_impact = ann_req - ann_curr
                bev = breakeven_volume(curr_gp_eur, volume, req_gp_eur) if req_gp_eur > 0 else float('inf')
                if req_price <= cost:
                    status = "BELOW COST"
                elif req_price < fp:
                    status = "Below Floor"
                elif req_price < fp * 1.05:
                    status = "Near Floor"
                else:
                    status = "Above Floor"
                pn_data.append({
                    "PN": pn, "Description": desc, "Source": source_label.split()[0],
                    "Class": pn_class, "FOB Cost": cost, "PR00": pr00,
                    "Requested": req_price, "Discount %": disc_pct * 100,
                    "GP% Curr": curr_gp_pct * 100, "GP% Req": req_gp_pct * 100,
                    "GP Curr/u": curr_gp_eur, "GP Req/u": req_gp_eur,
                    "Ann GP Curr": ann_curr, "Ann GP Req": ann_req,
                    "Ann GP Impact": ann_impact, "Floor Price": fp,
                    "Break-even Vol": bev, "Stated Vol": volume,
                    "Comp Price": comp_price, "Status": status
                })

    st.button("Add Part Number", on_click=add_row)
    calculate = st.button("Calculate & Draft Response", type="primary", use_container_width=True)

with col_right:
    if calculate and pn_data:
        df = pd.DataFrame(pn_data)

        st.subheader("Financial Summary")
        display_cols = ["PN", "Description", "FOB Cost", "PR00", "Requested",
                        "Discount %", "GP% Curr", "GP% Req",
                        "Ann GP Curr", "Ann GP Req", "Ann GP Impact",
                        "Floor Price", "Status"]

        def color_status(val):
            if "BELOW COST" in str(val) or "Below Floor" in str(val):
                return "background-color: #ffcccc"
            elif "Near Floor" in str(val):
                return "background-color: #fff3cc"
            else:
                return "background-color: #ccffcc"

        fmt = {c: "{:.2f}" for c in ["FOB Cost", "PR00", "Requested", "Floor Price",
                                      "Ann GP Curr", "Ann GP Req", "Ann GP Impact"]}
        fmt["Discount %"] = "{:.1f}%"
        fmt["GP% Curr"] = "{:.1f}%"
        fmt["GP% Req"] = "{:.1f}%"
        st.dataframe(df[display_cols].style.applymap(color_status, subset=["Status"]).format(fmt, na_rep="—"), use_container_width=True)

        st.subheader("Portfolio Summary")
        total_curr = df["Ann GP Curr"].sum()
        total_req = df["Ann GP Req"].sum()
        total_impact = df["Ann GP Impact"].sum()
        wavg_curr = (df["GP% Curr"] * df["Stated Vol"]).sum() / df["Stated Vol"].sum() if df["Stated Vol"].sum() > 0 else 0
        wavg_req = (df["GP% Req"] * df["Stated Vol"]).sum() / df["Stated Vol"].sum() if df["Stated Vol"].sum() > 0 else 0
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total GP @ PR00", f"EUR {total_curr:,.0f}")
        m2.metric("Total GP @ Requested", f"EUR {total_req:,.0f}")
        m3.metric("Annual GP Impact", f"EUR {total_impact:,.0f}", delta=f"{total_impact:,.0f}", delta_color="inverse")
        m4.metric("Avg GP% Change", f"{wavg_curr:.1f}% to {wavg_req:.1f}%")

        below_floor = df[df["Status"].str.contains("Below Floor|BELOW COST")]
        if not below_floor.empty:
            st.error(f"WARNING: {len(below_floor)} PN(s) below minimum floor: {', '.join(below_floor['PN'].tolist())}")

        st.subheader("Break-even Volume Analysis")
        fig = go.Figure()
        pns = df["PN"].tolist()
        stated = df["Stated Vol"].tolist()
        bevs = [min(v, stated[i]*3) if v != float('inf') else stated[i]*3 for i, v in enumerate(df["Break-even Vol"].tolist())]
        fig.add_trace(go.Bar(name="Stated Volume", x=pns, y=stated, marker_color="#2196F3"))
        fig.add_trace(go.Bar(name="Break-even Volume", x=pns, y=bevs, marker_color="#FF5722"))
        fig.update_layout(barmode="group", xaxis_title="Part Number", yaxis_title="Units/Year",
                         height=300, margin=dict(l=0, r=0, t=20, b=0),
                         legend=dict(orientation="h", yanchor="bottom", y=1.02))
        st.plotly_chart(fig, use_container_width=True)

        weak_vol = df[df["Break-even Vol"] > df["Stated Vol"] * 1.5]
        if not weak_vol.empty:
            st.warning(f"Weak volume justification for: {', '.join(weak_vol['PN'].tolist())} — break-even exceeds stated volume by >50%")

        if len(df) > 0:
            st.subheader("Sensitivity Table — Top GP Impact PN")
            top_pn = df.loc[df["Ann GP Impact"].abs().idxmax()]
            cost_top = top_pn["FOB Cost"]
            pr00_top = top_pn["PR00"]
            vol_top = int(top_pn["Stated Vol"])
            disc_levels = [0, 0.05, 0.10, 0.15, 0.20, 0.25]
            vol_scenarios = [int(vol_top * 0.7), vol_top, int(vol_top * 1.3)]
            sens_data = {}
            for d in disc_levels:
                price_d = pr00_top * (1 - d)
                gp_d = price_d - cost_top
                row = {}
                for v in vol_scenarios:
                    row[f"Vol {v}u"] = f"EUR {gp_d*v:,.0f}"
                sens_data[f"{d*100:.0f}% disc (EUR {price_d:.2f})"] = row
            st.dataframe(pd.DataFrame(sens_data).T, use_container_width=True)

        st.subheader("Recommendation")
        iml_keywords = ["masumi", "yoshimoto"]
        iml_flag = any(k in (distributor + justification).lower() for k in iml_keywords)
        below_floor_flag = not below_floor.empty
        below_cost_flag = any("BELOW COST" in s for s in df["Status"])
        impact_flag = abs(total_impact) > tml_threshold
        max_disc = df["Discount %"].max()
        weak_vol_flag = not weak_vol.empty
        comp_flag = any((row["Comp Price"] > 0 and row["Requested"] > row["Comp Price"]) for _, row in df.iterrows())

        if below_cost_flag:
            rec = "REJECT — Below Cost"
            rec_color = "error"
            rec_detail = "One or more PNs requested at or below FOB cost. Cannot approve."
        elif iml_flag:
            rec = "ESCALATE TO IML"
            rec_color = "error"
            rec_detail = "IML contact flagged in request (Masumi/Yoshimoto). Forward to IML International Parts Sales Dept."
        elif below_floor_flag:
            rec = "REJECT — Below GP Floor"
            rec_color = "error"
            rec_detail = f"One or more PNs priced below minimum {min_gp_pct*100:.0f}% GP floor. Counter-offer at floor price."
        elif impact_flag and max_disc > 20:
            rec = "ESCALATE — Significant Impact"
            rec_color = "warning"
            rec_detail = f"Annual GP impact of EUR {abs(total_impact):,.0f} exceeds threshold of EUR {tml_threshold:,.0f} with >20% discount. VP + IML sign-off required."
        elif max_disc <= 15 and not weak_vol_flag:
            rec = "APPROVE"
            rec_color = "success"
            rec_detail = "Discount within standard range, volume justification acceptable, all PNs above floor."
        elif max_disc <= 25:
            rec = "CONDITIONAL — Volume Commitment Required"
            rec_color = "warning"
            bev_max = df["Break-even Vol"].replace(float('inf'), 0).max()
            rec_detail = f"Approve on condition distributor commits to minimum {bev_max:.0f} units/year in writing. Review after 6 months."
        else:
            rec = "VP REVIEW REQUIRED"
            rec_color = "warning"
            rec_detail = "Discount exceeds 25% or justification is weak. Requires VP approval before proceeding."

        if comp_flag:
            rec_detail += " Note: requested price is above competitor reference — distributor's market pressure claim is weakened."

        if rec_color == "success":
            st.success(f"**{rec}**\n\n{rec_detail}")
        elif rec_color == "warning":
            st.warning(f"**{rec}**\n\n{rec_detail}")
        else:
            st.error(f"**{rec}**\n\n{rec_detail}")

        st.subheader("Draft SPA Response Letter")
        if not ANTHROPIC_API_KEY:
            st.warning("ANTHROPIC_API_KEY not set. Add it to your Streamlit Secrets to generate the letter.")
        else:
            with st.spinner("Drafting letter with Claude..."):
                pn_summary = "\n".join([
                    f"- {r['PN']} ({r['Description']}): PR00 EUR {r['PR00']:.2f} to Requested EUR {r['Requested']:.2f} ({r['Discount %']:.1f}% discount), GP impact EUR {r['Ann GP Impact']:,.0f}/yr, Status: {r['Status']}"
                    for _, r in df.iterrows()
                ])
                prompt = f"""Draft a formal SPA response letter from Jerome Van der Pluym (Parts Sales Manager, Isuzu Motors Europe) to the distributor {distributor or '[Distributor]'}.

RECOMMENDATION: {rec}
REASONING: {rec_detail}

PART NUMBERS ANALYSED:
{pn_summary}

TOTAL ANNUAL GP IMPACT: EUR {total_impact:,.0f}
DISTRIBUTOR JUSTIFICATION: {justification or 'Not provided'}

Requirements:
- Formal business letter format
- Reference specific GP figures
- State the decision clearly
- If conditional: specify volume commitment required
- If rejecting: offer counter-proposal at floor price where possible
- Sign off as: Jerome Van der Pluym | Parts Sales Manager | Isuzu Motors Europe
- Keep to 200-300 words"""
                letter = ask_claude(prompt, system=ISZE_CONTEXT + "\nYou draft formal SPA response letters. Use exact figures. Be concise and professional.")
                st.code(letter, language=None)
                st.caption("Copy the letter above and paste into your email client.")

        st.subheader("Export")
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download Analysis CSV", csv, "spa_analysis.csv", "text/csv", use_container_width=True)

    elif calculate and not pn_data:
        st.warning("Please fill in at least one complete part number row (Part Number, BP, PR00, Requested Price, Volume all required).")
    else:
        st.info("Fill in the SPA request on the left and click Calculate & Draft Response.")
        st.markdown("""
**Upload workflow:**
1. Click 'Upload from Pricer File' to expand the uploader
2. Upload the ISZE New Parts Pricer Excel — Part No., Description, BP(JPY) and Class auto-fill
3. Add PR00 price, requested price, and volume per row
4. Hit Calculate

**Or use the template CSV** to prepare a complete basket offline (all columns) and upload that.

**Recommendation logic:**
- Approve: discount 15% or less, above floor, volume justified
- Conditional: 15-25% discount, requires volume commitment
- Reject: below GP floor or below cost
- Escalate IML: Masumi/Yoshimoto flagged, or impact over EUR 5k with over 20% discount
""")
