"""
CatalogIQ -- Evidence-Driven Product Intelligence for Industrial Commerce

Run with:  streamlit run app.py
"""

from __future__ import annotations

import csv
import io
import time

import pandas as pd
import streamlit as st

from evaluation.scorer import error_category_summary, evaluate
from pipeline.correction_memory import load_corrections, record_correction
from pipeline.enrichment import enrich_catalog
from pipeline.icons import LOGO_MARK, icon
from pipeline.run_history import load_history, recent_history, record_run
from pipeline.reference_data import DATA_DIR, load_reference_data, reference_data_status
from pipeline.schemas import Decision

st.set_page_config(page_title="CatalogIQ", page_icon=None, layout="wide", initial_sidebar_state="expanded")

# ------------------------------------------------------------- theme state --
if "theme" not in st.session_state:
    st.session_state.theme = "light"


def toggle_theme():
    st.session_state.theme = "dark" if st.session_state.theme == "light" else "light"


THEMES = {
    "light": {
        "bg": "#F7F9FC", "bg2": "#FFFFFF", "card": "#FFFFFF", "border": "#E5E9F0",
        "text": "#0F172A", "muted": "#6B7280", "sidebar_bg": "#FFFFFF",
        "sidebar_border": "#E5E9F0", "hover": "#F1F5F9", "active_bg": "#EFF6FF",
        "active_text": "#2563EB", "header_grad": "linear-gradient(135deg, #0B1220 0%, #14264A 55%, #1E3A5F 100%)",
        "pipeline_bg": "#F4F7FB", "evidence_bg": "#F9FAFB", "input_bg": "#FFFFFF",
    },
    "dark": {
        "bg": "#0B1220", "bg2": "#111827", "card": "#151E2E", "border": "#26324A",
        "text": "#E5E9F0", "muted": "#94A3B8", "sidebar_bg": "#0E1626",
        "sidebar_border": "#1F2A40", "hover": "#1B2740", "active_bg": "#1E3A5F",
        "active_text": "#93C5FD", "header_grad": "linear-gradient(135deg, #050810 0%, #0C1830 55%, #12233F 100%)",
        "pipeline_bg": "#111B2E", "evidence_bg": "#131C2E", "input_bg": "#151E2E",
    },
}
T = THEMES[st.session_state.theme]

# ---------------------------------------------------------------- styling --
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    html, body, [class*="css"] {{ font-family: 'Inter', -apple-system, sans-serif; }}

    #MainMenu, footer {{visibility: hidden;}}
    .block-container {{padding-top: 1.2rem; max-width: 1180px;}}

    /* --- global app background / text following theme --- */
    [data-testid="stAppViewContainer"], .main {{ background: {T['bg']}; }}
    [data-testid="stAppViewContainer"] * {{ color: {T['text']}; }}
    [data-testid="stHeader"] {{ background: transparent; }}

    /* --- sidebar --- */
    section[data-testid="stSidebar"] {{
        background: {T['sidebar_bg']}; border-right: 1px solid {T['sidebar_border']};
    }}
    section[data-testid="stSidebar"] * {{ color: {T['text']}; }}

    .cq-side-logo {{ display: flex; align-items: center; gap: 10px; padding: 6px 4px 18px 4px; }}
    .cq-side-logo-mark {{
        background: {T['active_bg']}; border-radius: 9px; padding: 6px; display: flex;
    }}
    .cq-side-logo-text {{ font-size: 17px; font-weight: 800; letter-spacing: -0.02em; }}
    .cq-side-sub {{ font-size: 10.5px; color: {T['muted']}; font-weight: 600; letter-spacing: .03em; text-transform: uppercase; margin-top: -2px;}}

    div[data-testid="stSidebarUserContent"] div[role="radiogroup"] label {{
        border-radius: 8px; padding: 8px 10px; margin-bottom: 2px; width: 100%;
        transition: background .12s ease;
    }}
    div[data-testid="stSidebarUserContent"] div[role="radiogroup"] label:hover {{ background: {T['hover']}; }}

    /* --- header banner --- */
    .cq-header {{
        background: {T['header_grad']};
        padding: 24px 30px; border-radius: 14px; margin-bottom: 20px;
        display: flex; align-items: center; justify-content: space-between; gap: 16px;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.18);
    }}
    .cq-header-left {{ display: flex; align-items: center; gap: 16px; }}
    .cq-header-text h1 {{ color: #FFFFFF; margin: 0; font-size: 26px; font-weight: 800; letter-spacing: -0.02em; }}
    .cq-header-text p {{ color: #9FB2CC; margin: 3px 0 0 0; font-size: 13px; font-weight: 500; }}
    .cq-header-logo {{
        background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.12);
        border-radius: 10px; padding: 8px; display: flex; align-items: center; justify-content: center;
    }}
    .cq-header-status {{ color: #9FB2CC; font-size: 12px; font-weight: 600; text-align: right; }}

    /* --- KPI cards --- */
    .cq-kpi {{
        border: 1px solid {T['border']}; border-radius: 12px; padding: 16px 18px;
        background: {T['card']}; display: flex; align-items: flex-start; gap: 12px;
        box-shadow: 0 1px 2px rgba(16, 24, 40, 0.04);
        transition: box-shadow .15s ease, border-color .15s ease;
    }}
    .cq-kpi:hover {{ box-shadow: 0 4px 12px rgba(16, 24, 40, 0.10); }}
    .cq-kpi-icon {{
        width: 38px; height: 38px; border-radius: 9px; flex-shrink: 0;
        display: flex; align-items: center; justify-content: center;
    }}
    .cq-kpi .label {{font-size: 11.5px; color: {T['muted']}; text-transform: uppercase; letter-spacing: .05em; font-weight: 600;}}
    .cq-kpi .value {{font-size: 24px; font-weight: 800; color: {T['text']}; margin-top: 1px; letter-spacing: -0.02em;}}

    /* --- decision badges --- */
    .cq-badge {{
        display: inline-flex; align-items: center; gap: 5px; padding: 3px 11px 3px 8px;
        border-radius: 999px; font-size: 11.5px; font-weight: 700; letter-spacing: .02em;
    }}
    .cq-auto {{background: {'#DCFCE7' if st.session_state.theme=='light' else '#0F3324'}; color: {'#15803D' if st.session_state.theme=='light' else '#4ADE80'};}}
    .cq-review {{background: {'#FEF3C7' if st.session_state.theme=='light' else '#3A2A0A'}; color: {'#92400E' if st.session_state.theme=='light' else '#FBBF24'};}}
    .cq-investigate {{background: {'#FEE2E2' if st.session_state.theme=='light' else '#3A1414'}; color: {'#B91C1C' if st.session_state.theme=='light' else '#F87171'};}}

    /* --- evidence cards --- */
    .cq-evidence-card {{
        border: 1px solid {T['border']}; border-radius: 10px; padding: 11px 14px;
        background: {T['evidence_bg']}; margin-bottom: 8px; display: flex; gap: 10px; align-items: flex-start;
    }}
    .cq-evidence-icon {{
        width: 28px; height: 28px; border-radius: 7px; background: {T['active_bg']}; color: {T['active_text']};
        display: flex; align-items: center; justify-content: center; flex-shrink: 0; margin-top: 1px;
    }}
    .cq-note {{color: {T['muted']}; font-size: 12.5px; font-style: italic;}}
    .cq-strength-bar {{
        height: 5px; border-radius: 3px; background: {T['border']}; margin-top: 6px; overflow: hidden; width: 160px;
    }}
    .cq-strength-fill {{height: 100%; background: linear-gradient(90deg, #60A5FA, #2563EB); border-radius: 3px;}}

    /* --- pipeline strip --- */
    .cq-pipeline {{
        display: flex; align-items: center; gap: 4px; flex-wrap: wrap;
        padding: 10px 14px; background: {T['pipeline_bg']}; border-radius: 10px; border: 1px solid {T['border']};
    }}
    .cq-pipeline-step {{
        font-size: 12px; font-weight: 700; color: {T['text']}; background: {T['card']};
        border: 1px solid {T['border']}; padding: 4px 10px; border-radius: 6px; letter-spacing: .02em;
    }}
    .cq-pipeline-arrow {{color: {T['muted']}; display: flex; align-items: center;}}

    div[data-testid="stMetric"] {{
        background: {T['card']}; border: 1px solid {T['border']}; border-radius: 10px; padding: 10px 14px;
    }}
    div[data-testid="stExpander"] {{
        background: {T['card']}; border: 1px solid {T['border']}; border-radius: 10px;
    }}
    div[data-testid="stDataFrame"] {{ border: 1px solid {T['border']}; border-radius: 8px; }}
</style>
""", unsafe_allow_html=True)


def decision_badge(decision: str) -> str:
    cls = {"AUTO_APPROVED": "cq-auto", "REVIEW_REQUIRED": "cq-review", "INVESTIGATE": "cq-investigate"}
    label = {"AUTO_APPROVED": "AUTO APPROVED", "REVIEW_REQUIRED": "REVIEW REQUIRED", "INVESTIGATE": "INVESTIGATE"}
    ic = icon(decision, "currentColor")
    return f'<span class="cq-badge {cls.get(decision, "cq-review")}">{ic}{label.get(decision, decision)}</span>'


def kpi_card(label: str, value, icon_name: str, bg: str, fg: str) -> str:
    return f"""
    <div class="cq-kpi">
        <div class="cq-kpi-icon" style="background:{bg}; color:{fg};">{icon(icon_name)}</div>
        <div>
            <div class="label">{label}</div>
            <div class="value">{value}</div>
        </div>
    </div>
    """


@st.cache_resource(show_spinner=False)
def get_reference_data():
    return load_reference_data()


def read_uploaded_or_sample(uploaded_file) -> list[dict]:
    if uploaded_file is not None:
        content = uploaded_file.getvalue().decode("utf-8-sig")
        return list(csv.DictReader(io.StringIO(content)))
    with open(f"{DATA_DIR}/sample_input.csv", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


def load_ground_truth() -> list[dict]:
    with open(f"{DATA_DIR}/sample_ground_truth.csv", newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f))


# ------------------------------------------------------------- session state --
if "results" not in st.session_state:
    st.session_state.results = None
if "input_rows" not in st.session_state:
    st.session_state.input_rows = None

ref = get_reference_data()

# --------------------------------------------------------------- sidebar nav --
with st.sidebar:
    st.markdown(f"""
    <div class="cq-side-logo">
        <div class="cq-side-logo-mark">{LOGO_MARK}</div>
        <div>
            <div class="cq-side-logo-text">CatalogIQ</div>
            <div class="cq-side-sub">Product Intelligence</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    theme_label = "\U0001F319 Dark mode" if st.session_state.theme == "light" else "\u2600\uFE0F Light mode"
    st.button(theme_label, on_click=toggle_theme, use_container_width=True)
    st.markdown("---")

    page = st.radio(
        "Navigate",
        [
            "Dashboard", "Product Explainability", "Contradictions",
            "Human Review", "Benchmark & Quality", "Health Trend",
            "Scale Test", "Raw vs Enriched / Export",
        ],
        label_visibility="collapsed",
    )

    st.markdown("---")
    status = reference_data_status()
    with st.expander("System status: reference data", expanded=False):
        st.caption(
            "The reference master data bundled with this build is a small SYNTHETIC sample "
            "(manufacturer/brand list, LOV, UOM standards) built to demonstrate the pipeline. "
            "It is NOT the official UniHack reference files. Replace the CSVs in /data with the "
            "official files (same column names) to run this against the real benchmark."
        )
        for label, present in status.items():
            st.write(f"{'\u2713' if present else '\u2717'} {label}")

# ------------------------------------------------------------------ header --
st.markdown(f"""
<div class="cq-header">
    <div class="cq-header-left">
        <div class="cq-header-logo">{LOGO_MARK}</div>
        <div class="cq-header-text">
            <h1>CatalogIQ</h1>
            <p>Evidence-Driven Product Intelligence for Industrial Commerce</p>
        </div>
    </div>
    <div class="cq-header-status">SYSTEM ONLINE<br/>Sample reference data loaded</div>
</div>
""", unsafe_allow_html=True)

# ==================================================================== DASHBOARD
if page == "Dashboard":
    st.subheader("Run the intelligence engine")
    col_a, col_b = st.columns([2, 1])
    with col_a:
        uploaded = st.file_uploader(
            "Upload a catalog CSV (columns: product_id, manufacturer, mpn, description, category, raw_specs). "
            "Leave empty to use the bundled 20-row sample catalog.",
            type=["csv"],
        )
    with col_b:
        st.write("")
        st.write("")
        run_clicked = st.button("RUN INTELLIGENCE ENGINE", type="primary", use_container_width=True)

    if run_clicked:
        rows = read_uploaded_or_sample(uploaded)
        corrections = load_corrections()
        t0 = time.perf_counter()
        results = enrich_catalog(rows, ref, corrections)
        elapsed = time.perf_counter() - t0
        st.session_state.results = results
        st.session_state.input_rows = rows
        st.session_state.last_run_seconds = elapsed
        n = len(results)
        auto_count = sum(1 for r in results if r.overall_decision() == Decision.AUTO_APPROVED)
        conflict_count = sum(r.conflict_count() for r in results)
        avg_trust = sum(r.overall_trust() for r in results) / n if n else 0
        record_run(
            n_records=n,
            overall_field_accuracy=avg_trust,
            auto_approved_pct=auto_count / n if n else 0,
            conflict_count=conflict_count,
        )
        st.success(f"Processed {n} products in {elapsed:.2f}s.")

    results = st.session_state.results
    if results:
        n = len(results)
        avg_trust = sum(r.overall_trust() for r in results) / n
        auto = sum(1 for r in results if r.overall_decision() == Decision.AUTO_APPROVED)
        review = sum(1 for r in results if r.overall_decision() == Decision.REVIEW_REQUIRED)
        investigate = sum(1 for r in results if r.overall_decision() == Decision.INVESTIGATE)
        conflicts = sum(r.conflict_count() for r in results)

        st.write("")
        k1, k2, k3, k4, k5 = st.columns(5)
        if st.session_state.theme == "light":
            kpi_specs = [
                ("Products", n, "products", "#EFF6FF", "#2563EB"),
                ("Avg Trust Score", f"{avg_trust*100:.1f}%", "trust", "#EFF6FF", "#2563EB"),
                ("Auto Approved", auto, "auto", "#F0FDF4", "#16A34A"),
                ("Review Required", review, "review", "#FFFBEB", "#D97706"),
                ("Conflicts", conflicts, "conflict", "#FEF2F2", "#DC2626"),
            ]
        else:
            kpi_specs = [
                ("Products", n, "products", "#1E3A5F", "#93C5FD"),
                ("Avg Trust Score", f"{avg_trust*100:.1f}%", "trust", "#1E3A5F", "#93C5FD"),
                ("Auto Approved", auto, "auto", "#0F3324", "#4ADE80"),
                ("Review Required", review, "review", "#3A2A0A", "#FBBF24"),
                ("Conflicts", conflicts, "conflict", "#3A1414", "#F87171"),
            ]
        for col, (label, value, icon_name, bg, fg) in zip([k1, k2, k3, k4, k5], kpi_specs):
            col.markdown(kpi_card(label, value, icon_name, bg, fg), unsafe_allow_html=True)

        st.write("")
        pipeline_steps = ["INPUT", "NORMALIZE", "RESOLVE", "EVIDENCE", "ENRICH", "VALIDATE", "TRUST", "REVIEW"]
        arrow = f'<span class="cq-pipeline-arrow">{icon("pipeline_arrow")}</span>'
        steps_html = arrow.join(f'<span class="cq-pipeline-step">{s}</span>' for s in pipeline_steps)
        st.markdown(f'<div class="cq-pipeline">{steps_html}</div>', unsafe_allow_html=True)

        st.write("")
        st.subheader("Results")
        table_rows = []
        for r in results:
            mfg = r.fields.get("manufacturer")
            brand = r.fields.get("brand")
            cat = r.fields.get("category")
            table_rows.append({
                "Product": r.product_id,
                "Manufacturer": mfg.value if mfg else None,
                "Brand": brand.value if brand else None,
                "Category": cat.value if cat else None,
                "Trust": f"{r.overall_trust()*100:.1f}%",
                "Status": r.overall_decision().value,
            })
        st.dataframe(pd.DataFrame(table_rows), use_container_width=True, hide_index=True)
    else:
        st.info("No run yet. Click RUN INTELLIGENCE ENGINE above (using the sample catalog or your own upload).")

# ============================================================ PRODUCT DETAIL
elif page == "Product Explainability":
    st.subheader("Product Intelligence \u2014 Explainability")
    results = st.session_state.results
    if not results:
        st.info("Run the intelligence engine on the Dashboard page first.")
    else:
        ids = [r.product_id for r in results]
        selected_id = st.selectbox("Select a product", ids)
        product = next(r for r in results if r.product_id == selected_id)

        st.markdown("**Identity**")
        mfg = product.fields.get("manufacturer")
        brand = product.fields.get("brand")
        cat = product.fields.get("category")
        c1, c2, c3 = st.columns(3)
        c1.metric("Manufacturer", mfg.value or "\u2014", f"{mfg.confidence_pct()} confidence")
        c2.metric("Brand", brand.value or "\u2014", f"{brand.confidence_pct()} confidence")
        c3.metric("Category", cat.value or "\u2014", f"{cat.confidence_pct()} confidence")

        st.markdown("---")
        st.markdown("**Why did CatalogIQ choose this?**")
        for field_name, fr in product.fields.items():
            with st.expander(f"{field_name.upper()}  \u2014  {fr.value or '(none)'}  \u2014  {fr.confidence_pct()}", expanded=(field_name == "manufacturer")):
                st.markdown(decision_badge(fr.decision.value), unsafe_allow_html=True)
                st.write(fr.reason)
                if fr.evidence:
                    st.markdown("Evidence signals:")
                    for e in fr.evidence:
                        pct = int(round(e.strength * 100))
                        st.markdown(
                            f'<div class="cq-evidence-card">'
                            f'<div class="cq-evidence-icon">{icon(e.type.value)}</div>'
                            f'<div style="flex:1;">'
                            f'<b>{e.type.value.replace("_", " ").title()}</b> \u2192 <code>{e.value}</code> '
                            f'<span style="color:{T["muted"]}; font-size:12.5px;">({pct}%)</span>'
                            f'<div class="cq-strength-bar"><div class="cq-strength-fill" style="width:{pct}%;"></div></div>'
                            f'<div class="cq-note">{e.signal}</div>'
                            f'</div></div>',
                            unsafe_allow_html=True,
                        )
                else:
                    st.caption("No evidence signals found for this field.")
                if fr.validation.notes:
                    st.markdown("Validation notes: " + "; ".join(fr.validation.notes))
                if fr.correction_applied:
                    st.info("A prior human correction (correction memory) influenced this result.")

# ============================================================= CONTRADICTIONS
elif page == "Contradictions":
    st.subheader("Contradiction Engine")
    st.caption("Fields where evidence signals disagreed strongly enough to block auto-approval.")
    results = st.session_state.results
    if not results:
        st.info("Run the intelligence engine on the Dashboard page first.")
    else:
        found_any = False
        for r in results:
            for field_name, fr in r.fields.items():
                if fr.is_conflict:
                    found_any = True
                    st.markdown(f"### {r.product_id} \u2014 {field_name}")
                    st.markdown("CONFLICT DETECTED", unsafe_allow_html=False)
                    for e in fr.evidence:
                        st.write(f"- **{e.type.value}** signal: `{e.value}` \u2014 {e.strength*100:.0f}%")
                    st.write(f"Conflict severity: **{fr.conflict_severity*100:.0f}%**")
                    st.write(f"Decision: {decision_badge(fr.decision.value)}", unsafe_allow_html=True)
                    st.write(f"Reason CatalogIQ refused to auto-publish: {fr.reason}")
                    st.markdown("---")
        if not found_any:
            st.success("No field-level conflicts detected in the current run.")

# ================================================================ HUMAN REVIEW
elif page == "Human Review":
    st.subheader("Human Review Queue")
    results = st.session_state.results
    if not results:
        st.info("Run the intelligence engine on the Dashboard page first.")
    else:
        review_items = []
        for r in results:
            for field_name, fr in r.fields.items():
                if fr.decision != Decision.AUTO_APPROVED:
                    review_items.append((r, field_name, fr))

        st.caption(f"{len(review_items)} field(s) require human attention.")
        for r, field_name, fr in review_items:
            with st.container(border=True):
                cols = st.columns([2, 2, 2, 2, 2, 2])
                cols[0].write(f"**{r.product_id}**")
                cols[1].write(field_name)
                cols[2].write(f"AI value: `{fr.value or '(none)'}`")
                cols[3].write(f"Confidence: {fr.confidence_pct()}")
                cols[4].markdown(decision_badge(fr.decision.value), unsafe_allow_html=True)

                action_key = f"{r.product_id}_{field_name}"
                action = cols[5].selectbox(
                    "Action", ["\u2014", "Accept", "Correct", "Mark Unknown"],
                    key=f"action_{action_key}", label_visibility="collapsed",
                )
                if action == "Correct":
                    corrected_value = st.text_input("Corrected value", key=f"correct_val_{action_key}")
                    reason = st.text_input("Reason (optional)", key=f"reason_{action_key}")
                    if st.button("Save correction", key=f"save_{action_key}"):
                        if corrected_value.strip():
                            input_row = next((row for row in (st.session_state.input_rows or []) if row.get("product_id") == r.product_id), {})
                            record_correction(
                                product_id=r.product_id, field=field_name,
                                mpn=input_row.get("mpn"), manufacturer_input=input_row.get("manufacturer"),
                                predicted_value=fr.value, corrected_value=corrected_value.strip(), reason=reason,
                            )
                            st.success("Correction saved to correction memory. Re-run the engine to see it applied.")
                        else:
                            st.warning("Enter a corrected value before saving.")
                elif action == "Mark Unknown":
                    input_row = next((row for row in (st.session_state.input_rows or []) if row.get("product_id") == r.product_id), {})
                    if st.button("Confirm mark unknown", key=f"unk_{action_key}"):
                        record_correction(
                            product_id=r.product_id, field=field_name,
                            mpn=input_row.get("mpn"), manufacturer_input=input_row.get("manufacturer"),
                            predicted_value=fr.value, corrected_value="UNKNOWN", reason="Marked unknown by reviewer",
                        )
                        st.success("Marked unknown and saved to correction memory.")

# ============================================================ BENCHMARK PAGE
elif page == "Benchmark & Quality":
    st.subheader("Benchmark & Quality")
    st.markdown("**Sample Ground Truth Benchmark (20 hand-labeled items)**")
    st.warning(
        "This is a 20-item SAMPLE ground truth bundled with this build for demonstration -- "
        "it is NOT the official UniHack 200-item ground truth. Replace "
        "data/sample_ground_truth.csv (and sample_input.csv) with the official files, matching "
        "the same column names, to run the real benchmark.",
        icon="\u26A0\uFE0F",
    )

    if st.button("Run benchmark now"):
        rows = read_uploaded_or_sample(None)
        gt = load_ground_truth()
        corrections = load_corrections()
        results = enrich_catalog(rows, ref, corrections)
        report = evaluate(results, gt)
        st.session_state.eval_report = report

    report = st.session_state.get("eval_report")
    if report:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Overall Field Accuracy", f"{report.overall_field_accuracy*100:.1f}%")
        c2.metric("Manufacturer Accuracy", f"{report.field_accuracies['manufacturer'].accuracy()*100:.1f}%")
        c3.metric("Brand Accuracy", f"{report.field_accuracies['brand'].accuracy()*100:.1f}%")
        c4.metric("Category Accuracy", f"{report.field_accuracies['category'].accuracy()*100:.1f}%")

        c5, c6, c7, c8 = st.columns(4)
        c5.metric("Auto Approved", report.auto_approved)
        c6.metric("Review Required", report.review_required)
        c7.metric("Investigate", report.investigate)
        c8.metric("Avg Confidence", f"{report.avg_confidence*100:.1f}%")

        st.markdown("**Field accuracy chart**")
        chart_df = pd.DataFrame({
            "field": list(report.field_accuracies.keys()),
            "accuracy": [a.accuracy() * 100 for a in report.field_accuracies.values()],
        }).set_index("field")
        st.bar_chart(chart_df)

        st.markdown("**Top error categories**")
        errs = error_category_summary(report)
        if errs:
            for field_name, count in errs:
                st.write(f"- {field_name}: {count} error(s)")
        else:
            st.success("No field errors on this sample benchmark.")

        st.markdown("**Error case detail**")
        if report.error_cases:
            err_df = pd.DataFrame([{
                "Product": e.product_id, "Field": e.field, "Predicted": e.predicted,
                "Expected": e.expected, "Confidence": f"{e.confidence*100:.1f}%",
                "Was Conflict": e.was_conflict, "Reason": e.reason,
            } for e in report.error_cases])
            st.dataframe(err_df, use_container_width=True, hide_index=True)
        else:
            st.caption("No mismatches to show.")
    else:
        st.info("Click 'Run benchmark now' to compute live metrics against the sample ground truth.")

# ============================================================ HEALTH TREND
elif page == "Health Trend":
    st.subheader("Catalog Health Trend")
    history = load_history()
    if not history:
        st.info("No run history yet. Run the intelligence engine on the Dashboard to start tracking catalog health over time.")
    else:
        st.caption(f"Showing the most recent {len(history)} run(s).")
        rows_data = []
        for r in history:
            rows_data.append({
                "Timestamp": r.timestamp[:19].replace("T", " "),
                "Records": r.n_records,
                "Field Accuracy": f"{r.overall_field_accuracy * 100:.1f}%",
                "Auto-Approved %": f"{r.auto_approved_pct * 100:.1f}%",
                "Conflicts": r.conflict_count,
            })
        st.dataframe(pd.DataFrame(rows_data), use_container_width=True, hide_index=True)

        st.write("")
        st.markdown("**Trend over time**")
        chart_df = pd.DataFrame({
            "Run": list(range(1, len(history) + 1)),
            "Field Accuracy (%)": [r.overall_field_accuracy * 100 for r in history],
            "Auto-Approved (%)": [r.auto_approved_pct * 100 for r in history],
            "Conflicts": [r.conflict_count for r in history],
        }).set_index("Run")
        st.line_chart(chart_df)

        if len(history) >= 2:
            latest = history[-1]
            previous = history[-2]
            delta_acc = latest.overall_field_accuracy - previous.overall_field_accuracy
            delta_auto = latest.auto_approved_pct - previous.auto_approved_pct
            delta_conf = latest.conflict_count - previous.conflict_count
            c1, c2, c3 = st.columns(3)
            c1.metric("Field Accuracy", f"{latest.overall_field_accuracy * 100:.1f}%", f"{delta_acc * 100:+.1f}%")
            c2.metric("Auto-Approved %", f"{latest.auto_approved_pct * 100:.1f}%", f"{delta_auto * 100:+.1f}%")
            c3.metric("Conflicts", latest.conflict_count, f"{delta_conf:+d}")

# =================================================================== SCALE TEST
elif page == "Scale Test":
    st.subheader("Scale Test")
    st.warning(
        "The 1,000-row file bundled here is SYNTHETIC (the 20 sample rows cycled with new "
        "IDs), built only to demonstrate throughput end-to-end. It is NOT the official "
        "1,000-row UniHack dataset. Drop the real file into /data with the same column names "
        "to get a genuine large-catalog run.",
        icon="\u26A0\uFE0F",
    )
    if st.button("Run 1,000-row scale test"):
        with open(f"{DATA_DIR}/synthetic_scale_1000.csv", newline="", encoding="utf-8-sig") as f:
            rows = list(csv.DictReader(f))
        corrections = load_corrections()
        t0 = time.perf_counter()
        results = enrich_catalog(rows, ref, corrections)
        elapsed = time.perf_counter() - t0

        n = len(results)
        auto = sum(1 for r in results if r.overall_decision() == Decision.AUTO_APPROVED)
        review = sum(1 for r in results if r.overall_decision() == Decision.REVIEW_REQUIRED)
        investigate = sum(1 for r in results if r.overall_decision() == Decision.INVESTIGATE)
        avg_conf = sum(r.overall_trust() for r in results) / n

        st.success(f"Processed {n} products in {elapsed:.2f}s ({n/elapsed:.0f} products/sec) -- measured this run, on this machine.")
        s1, s2, s3, s4, s5 = st.columns(5)
        s1.metric("Processed", n)
        s2.metric("Duration", f"{elapsed:.2f}s")
        s3.metric("Throughput", f"{n/elapsed:.0f}/s")
        s4.metric("Auto / Review / Investigate", f"{auto}/{review}/{investigate}")
        s5.metric("Avg Trust", f"{avg_conf*100:.1f}%")
        st.caption(
            "This measures single-process throughput on this machine, not a claimed "
            "production SKU/month figure. The pipeline is stateless per-product and reference "
            "data is loaded once and cached, so it is architecturally suited to batching and "
            "horizontal scaling -- that scaling has not itself been benchmarked here."
        )

# =========================================================== RAW VS ENRICHED
elif page == "Raw vs Enriched / Export":
    st.subheader("Raw vs Enriched")
    results = st.session_state.results
    if not results:
        st.info("Run the intelligence engine on the Dashboard page first.")
    else:
        ids = [r.product_id for r in results]
        selected_id = st.selectbox("Select a product", ids, key="compare_select")
        product = next(r for r in results if r.product_id == selected_id)

        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**BEFORE (raw input)**")
            st.json(product.raw_input)
        with c2:
            st.markdown("**AFTER (commerce-ready)**")
            st.json(product.to_dict())

        st.markdown("---")
        st.subheader("Export")
        export_rows = []
        for r in results:
            row = {"product_id": r.product_id, "overall_trust": r.overall_trust(), "overall_decision": r.overall_decision().value}
            for field_name, fr in r.fields.items():
                row[f"{field_name}_value"] = fr.value
                row[f"{field_name}_confidence"] = fr.confidence
                row[f"{field_name}_decision"] = fr.decision.value
                row[f"{field_name}_evidence_summary"] = "; ".join(e.signal for e in fr.evidence)
                row[f"{field_name}_validation"] = "; ".join(fr.validation.notes) if fr.validation.notes else "ok"
            export_rows.append(row)
        export_df = pd.DataFrame(export_rows)
        csv_bytes = export_df.to_csv(index=False).encode("utf-8")
        st.download_button("Download enriched catalog (CSV)", data=csv_bytes, file_name="catalogiq_enriched_output.csv", mime="text/csv")

        