"""
Subject Workspaces & File Grouping View Page.
Allows students to organize uploaded lectures into Subjects (e.g. Math, Chinese, Physics)
and launch scoped Knowledge Graphs, Study Guides, and Quizzes for specific files or groups of files.
"""
import streamlit as st
from pathlib import Path

from src.config import VAULT_ROOT
from src.workspace.workspace_manager import (
    get_workspace_data,
    save_workspace_data,
    create_subject,
    delete_subject,
    assign_files_to_subject,
    get_all_lecture_files
)
from src.workspace.synthesis_engine import (
    get_existing_synthesis,
    synthesize_subject_cross_links
)

def render_workspace_view():
    st.header("📁 Subject Workspaces & File Manager")
    st.caption("Organize your uploaded lectures and YouTube videos into Subject Collections (e.g., Math vs. Chinese) to isolate knowledge graphs, study guides, and quizzes.")

    vault_dir = Path(VAULT_ROOT)
    data = get_workspace_data(vault_dir)
    subjects = data.get("subjects", {})
    all_files = get_all_lecture_files(vault_dir)

    # Top Toolbar: Create New Subject
    col_create1, col_create2 = st.columns([3, 1])
    with col_create1:
        new_subj_name = st.text_input("Create New Subject Collection", placeholder="e.g. Math - Calculus, Chinese Literature, Physics")
    with col_create2:
        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
        if st.button("➕ Create Subject", type="primary", use_container_width=True):
            if new_subj_name and create_subject(vault_dir, new_subj_name):
                st.success(f"Subject '{new_subj_name}' created!")
                st.rerun()
            elif not new_subj_name:
                st.warning("Please enter a subject name.")
            else:
                st.info("Subject already exists.")

    st.markdown("---")

    tab1, tab2 = st.tabs(["📚 Subject Collections & Grouping", "📄 All Uploaded Files"])

    # TAB 1: SUBJECT COLLECTIONS
    with tab1:
        st.subheader("Manage Subject Groupings")
        if not subjects:
            st.info("No subjects created yet. Create a subject above to group your lectures.")
        else:
            for subj_name, assigned_files in subjects.items():
                with st.expander(f"📚 **{subj_name}** ({len(assigned_files)} files assigned)", expanded=True):
                    col_s1, col_s2 = st.columns([3, 1])

                    with col_s1:
                        # Multi-select to assign/unassign files
                        updated_assigned = st.multiselect(
                            f"Assign files to {subj_name}:",
                            options=all_files,
                            default=[f for f in assigned_files if f in all_files],
                            key=f"ms_{subj_name}"
                        )
                        if st.button(f"Save Files for {subj_name}", key=f"btn_save_{subj_name}"):
                            assign_files_to_subject(vault_dir, subj_name, updated_assigned)
                            st.success(f"Updated files for {subj_name}!")
                            st.rerun()

                    with col_s2:
                        st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
                        if st.button(f"🗑️ Delete {subj_name}", key=f"btn_del_{subj_name}"):
                            delete_subject(vault_dir, subj_name)
                            st.warning(f"Deleted subject {subj_name}.")
                            st.rerun()

                    # AI Synthesis Section
                    existing_syn = get_existing_synthesis(vault_dir, subj_name)
                    st.markdown("---")
                    st.markdown("##### 🔄 AI Cross-Lecture Synthesis Engine")
                    
                    col_syn1, col_syn2 = st.columns([3, 1])
                    with col_syn1:
                        if existing_syn and existing_syn.get("cross_bridges"):
                            st.success(f"✨ {len(existing_syn['cross_bridges'])} Cross-Lecture Bridges Discovered & Synthesized!")
                        else:
                            st.info("Discover non-obvious conceptual connections linking notes from different lectures in this subject.")
                    with col_syn2:
                        def _do_synthesis(s_name=subj_name):
                            with st.spinner("Analyzing cross-lecture bridges..."):
                                res = synthesize_subject_cross_links(vault_dir, s_name)
                                if res.get("status") == "success":
                                    st.toast(f"Synthesized {len(res.get('cross_bridges', []))} bridges for {s_name}!")

                        st.button(
                            "🔄 Synthesize Bridges",
                            key=f"btn_syn_{subj_name}",
                            use_container_width=True,
                            on_click=_do_synthesis
                        )

                    # Quick Scope Launcher
                    st.markdown("**Quick Actions for this Subject**:")
                    qa_col1, qa_col2, qa_col3 = st.columns(3)
                    with qa_col1:
                        if st.button(f"🕸️ Graph & Chat ({subj_name})", key=f"qa_graph_{subj_name}", use_container_width=True):
                            st.session_state["active_study_scope"] = f"Subject: {subj_name}"
                            st.session_state["navigation_target"] = '🕸️ Knowledge Graph & Chat'
                            st.rerun()
                    with qa_col2:
                        if st.button(f"💡 Study Guide ({subj_name})", key=f"qa_guide_{subj_name}", use_container_width=True):
                            st.session_state["active_study_scope"] = f"Subject: {subj_name}"
                            st.session_state["navigation_target"] = '💡 Study Guide & Insights'
                            st.rerun()
                    with qa_col3:
                        if st.button(f"📝 Start Quiz ({subj_name})", key=f"qa_quiz_{subj_name}", use_container_width=True):
                            st.session_state["active_study_scope"] = f"Subject: {subj_name}"
                            st.session_state["navigation_target"] = '📝 Active Recall Quiz'
                            st.rerun()

    # TAB 2: ALL UPLOADED FILES
    with tab2:
        st.subheader("All Uploaded Lecture Files & YouTube Ingestions")
        if not all_files:
            st.info("No lecture files uploaded yet. Record audio or ingest YouTube videos using the Sidebar or Record page.")
        else:
            for fname in all_files:
                matching_subjs = [s for s, flist in subjects.items() if fname in flist]
                subj_badge = ", ".join([f"`{s}`" for s in matching_subjs]) if matching_subjs else "*Uncategorized*"

                with st.container(border=True):
                    fcol1, fcol2 = st.columns([3, 2])
                    with fcol1:
                        st.markdown(f"📄 **[[{fname}]]**")
                        st.caption(f"**Subjects**: {subj_badge}")

                    with fcol2:
                        st.markdown("**Quick Actions for this File**:")
                        fbtn1, fbtn2 = st.columns(2)
                        with fbtn1:
                            if st.button(f"🕸️ Graph", key=f"f_graph_{fname}", use_container_width=True):
                                st.session_state["active_study_scope"] = f"File: {fname}"
                                st.session_state["navigation_target"] = '🕸️ Knowledge Graph & Chat'
                                st.rerun()
                        with fbtn2:
                            if st.button(f"📝 Quiz", key=f"f_quiz_{fname}", use_container_width=True):
                                st.session_state["active_study_scope"] = f"File: {fname}"
                                st.session_state["navigation_target"] = '📝 Active Recall Quiz'
                                st.rerun()
