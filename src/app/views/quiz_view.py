"""
Active Recall Quiz & Flashcards View Page with Active Scope Filtering.
Features Redo Quiz and Regenerate New Questions capabilities.
"""
import streamlit as st
import random
from pathlib import Path

from src.config import VAULT_ROOT
from src.quiz.quiz_generator import generate_quiz
from src.workspace.workspace_manager import get_scoped_notes

def render_quiz_view():
    vault_dir = Path(VAULT_ROOT)
    active_scope = st.session_state.get("active_study_scope", "All Files (Global Vault)")

    st.header("📝 Active Recall Quiz & Flashcards")
    st.caption(f"🎯 **Active Scope**: `{active_scope}` | Test your recall with AI-generated questions grounded in your selected study scope.")

    scoped_notes = get_scoped_notes(vault_dir, active_scope)
    if not scoped_notes:
        st.info(f"Vault scope `{active_scope}` has no notes. Record or upload a lecture to generate interactive quizzes.")
        return

    # Track scope change to auto-regenerate quiz when scope switches
    if "last_quiz_scope" not in st.session_state or st.session_state["last_quiz_scope"] != active_scope:
        st.session_state["last_quiz_scope"] = active_scope
        st.session_state.quiz_questions = generate_quiz(vault_dir)
        st.session_state.quiz_user_answers = {}
        st.session_state.quiz_submitted = False
        st.session_state.flashcard_states = {}

    # Initialize Session State if missing
    if "quiz_questions" not in st.session_state:
        st.session_state.quiz_questions = generate_quiz(vault_dir)
        st.session_state.quiz_user_answers = {}
        st.session_state.quiz_submitted = False
        st.session_state.flashcard_states = {}

    # Action Toolbar: Redo & Regenerate Buttons
    col_action1, col_action2, col_space = st.columns([1, 1, 2])

    with col_action1:
        if st.button("🔄 Redo Current Quiz", use_container_width=True):
            st.session_state.quiz_user_answers = {}
            st.session_state.quiz_submitted = False
            st.session_state.flashcard_states = {}
            st.success("Quiz reset! Try answering the questions again.")
            st.rerun()

    with col_action2:
        if st.button("✨ Regenerate New Questions", type="primary", use_container_width=True):
            with st.spinner(f"Generating fresh recall questions for `{active_scope}`..."):
                seed_val = random.randint(1, 99999)
                st.session_state.quiz_questions = generate_quiz(vault_dir, force_new=True, seed=seed_val)
                st.session_state.quiz_user_answers = {}
                st.session_state.quiz_submitted = False
                st.session_state.flashcard_states = {}
                st.success("New quiz generated!")
                st.rerun()

    st.markdown("---")

    questions = st.session_state.quiz_questions
    if not questions:
        st.warning("Could not generate questions for this scope. Please ingest more lecture content.")
        return

    mc_questions = [q for q in questions if q.get("type") == "multiple_choice"]
    flashcards = [q for q in questions if q.get("type") == "flashcard"]

    tab_mc, tab_cards = st.tabs([
        f"🎯 Multiple Choice Quiz ({len(mc_questions)} Questions)",
        f"🎴 Flashcard Deck ({len(flashcards)} Cards)"
    ])

    # TAB 1: MULTIPLE CHOICE
    with tab_mc:
        st.subheader("Multiple Choice Assessment")
        
        user_answers = st.session_state.quiz_user_answers

        for idx, q in enumerate(mc_questions, 1):
            st.markdown(f"### Q{idx}. [[{q.get('concept', 'Concept')}]]")
            st.markdown(f"**{q.get('question')}**")

            opts = q.get("options", [])
            q_key = f"mc_q_{q.get('id', idx)}"
            
            selected_opt = st.radio(
                "Select option:",
                opts,
                index=None if q_key not in user_answers else (opts.index(user_answers[q_key]) if user_answers[q_key] in opts else None),
                key=q_key,
                disabled=st.session_state.quiz_submitted
            )
            if selected_opt:
                user_answers[q_key] = selected_opt

            if st.session_state.quiz_submitted:
                correct_ans = q.get("answer", "")
                user_ans = user_answers.get(q_key, "")

                if user_ans == correct_ans:
                    st.success(f"✅ **Correct!** Answer: `{correct_ans}`")
                else:
                    st.error(f"❌ **Incorrect.** You selected: `{user_ans or 'No Answer'}` | **Correct Answer**: `{correct_ans}`")

                st.info(f"💡 **Explanation**: {q.get('explanation', '')}")

            st.markdown("---")

        if not st.session_state.quiz_submitted:
            if st.button("Submit Quiz & Grade Answers", type="primary"):
                st.session_state.quiz_submitted = True
                st.rerun()
        else:
            # Calculate Score
            score = 0
            for q in mc_questions:
                q_key = f"mc_q_{q.get('id')}"
                if user_answers.get(q_key) == q.get("answer"):
                    score += 1

            total = len(mc_questions)
            pct = (score / total * 100) if total > 0 else 0
            
            st.metric(label="Your Quiz Score", value=f"{score} / {total}", delta=f"{pct:.1f}% Accuracy")
            if pct >= 80:
                st.balloons()
                st.success("🎉 Excellent recall! You mastered these lecture concepts.")

    # TAB 2: FLASHCARDS
    with tab_cards:
        st.subheader("Interactive Flashcards")
        st.markdown("Flip cards to test active recall of key definitions and equations.")

        for idx, card in enumerate(flashcards, 1):
            c_key = f"card_flip_{card.get('id', idx)}"
            concept = card.get("concept", "Concept")
            question = card.get("question", "")
            answer = card.get("answer", "")
            explanation = card.get("explanation", "")

            with st.container(border=True):
                st.markdown(f"#### 🎴 Card #{idx}: [[{concept}]]")
                st.markdown(f"**Front (Question)**:\n\n{question}")

                is_flipped = st.session_state.flashcard_states.get(c_key, False)

                if st.button(f"🔄 {'Hide Answer' if is_flipped else 'Show Answer / Back'}", key=f"btn_flip_{c_key}"):
                    st.session_state.flashcard_states[c_key] = not is_flipped
                    st.rerun()

                if is_flipped:
                    st.success(f"**Back (Answer)**:\n\n{answer}")
                    if explanation:
                        st.caption(f"**Notes**: {explanation}")
