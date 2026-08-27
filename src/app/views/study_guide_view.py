"""
Study Guide & Hidden Insights View Page with Scope Filtering.
"""
import streamlit as st
from pathlib import Path

from src.config import VAULT_ROOT
from src.quiz.insight_extractor import extract_study_insights
from src.workspace.workspace_manager import get_scoped_notes

def render_study_guide_view():
    vault_dir = Path(VAULT_ROOT)
    active_scope = st.session_state.get("active_study_scope", "All Files (Global Vault)")

    st.header("💡 Study Guide & Hidden Insights")
    st.caption(f"🎯 **Active Scope**: `{active_scope}` | Deep conceptual insights, summaries, formula cheat sheets, and exam alerts.")

    scoped_notes = get_scoped_notes(vault_dir, active_scope)
    if not scoped_notes:
        st.info(f"No lecture notes found in scope `{active_scope}`. Record or upload a lecture to generate your study guide.")
        return

    with st.spinner(f"Extracting hidden study insights for `{active_scope}`..."):
        insights_data = extract_study_insights(vault_dir)

    exec_summary = insights_data.get("executive_summary", [])
    hidden_insights = insights_data.get("hidden_insights", [])
    exam_alerts = insights_data.get("exam_alerts", [])
    cheat_sheet = insights_data.get("cheat_sheet", [])

    tab1, tab2, tab3, tab4 = st.tabs([
        "🎧 Executive Audio Summary",
        "🧠 Hidden Insights",
        "⚠️ Exam Alerts & Traps",
        "📐 Formula Cheat Sheet"
    ])

    with tab1:
        st.subheader(f"Executive Summary ({active_scope})")
        st.markdown("Synthesized overview of key themes and core objectives across your selected scope.")
        for idx, point in enumerate(exec_summary, 1):
            st.markdown(f"**{idx}.** {point}")

    with tab2:
        st.subheader("Hidden Conceptual Insights")
        st.markdown("Implicit relationships and higher-order mental models extracted between connected notes.")
        
        for ins in hidden_insights:
            title = ins.get("title", "Insight")
            desc = ins.get("description", "")
            rel = ins.get("related_concepts", [])
            
            with st.expander(f"✨ {title}", expanded=True):
                st.markdown(desc)
                if rel:
                    st.caption(f"**Related Concepts**: {', '.join(['[[' + r + ']]' for r in rel])}")

    with tab3:
        st.subheader("⚠️ Exam Alerts & Common Pitfalls")
        st.markdown("Critical warnings, edge cases, and typical student mistakes identified during lectures.")
        
        for alert in exam_alerts:
            warn = alert.get("warning", "Exam Caution")
            exp = alert.get("explanation", "")
            
            st.warning(f"**Warning**: {warn}\n\n{exp}")

    with tab4:
        st.subheader("📐 Formulas & Definitions Cheat Sheet")
        st.markdown("Reference guide of key formulas, scientific parameters, definitions, and usage contexts.")

        if cheat_sheet:
            st.table(cheat_sheet)
        else:
            st.info("No formulas extracted yet.")
