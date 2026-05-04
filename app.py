"""Simple UI for the integrated agent pipeline.

Run Streamlit UI:
    streamlit run app.py

Run terminal UI / demo:
    python3 app.py --cli
    python3 app.py --demo
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from agents import AgentPipeline


def run_cli(prompt: str | None = None) -> None:
    pipeline = AgentPipeline()
    user_prompt = prompt or input("Enter your research prompt: ").strip()
    result = pipeline.run(user_prompt, max_revision_rounds=1)

    print("\n=== FINAL ANSWER ===")
    print(result["final_answer"])

    print("\n=== MANAGER REPORT ===")
    print(result["manager_report"]["summary"])

    print("\n=== AGENT INTERACTION LOG ===")
    print(result["log_text"])

    Path("demo_log.json").write_text(json.dumps(result["log"], indent=2), encoding="utf-8")
    Path("demo_log.txt").write_text(result["log_text"], encoding="utf-8")
    print("\nSaved demo_log.json and demo_log.txt")


def run_streamlit() -> None:
    try:
        import streamlit as st
    except ImportError as exc:
        raise SystemExit("Streamlit is not installed. Run: pip install streamlit") from exc

    st.set_page_config(page_title="Agent Pipeline", page_icon="🧠", layout="wide")
    st.title("Researcher + Manager Agent Pipeline")
    st.caption("Prompt → Researcher draft → Manager review → optional revision → approved final answer")

    prompt = st.text_area(
        "Enter a research prompt",
        value="How can students use AI tools for active learning without becoming dependent on them?",
        height=120,
    )
    max_revisions = st.slider("Maximum revision rounds", min_value=0, max_value=3, value=1)

    if st.button("Run pipeline", type="primary"):
        pipeline = AgentPipeline()
        with st.spinner("Running agents..."):
            result = pipeline.run(prompt, max_revision_rounds=max_revisions)

        status = "✅ Approved" if result["approved"] else "⚠️ Not approved"
        st.subheader(status)

        st.markdown("### Final answer")
        st.write(result["final_answer"])

        st.markdown("### Manager report")
        st.code(result["manager_report"]["summary"])

        st.markdown("### Agent interaction log")
        st.dataframe(result["log"], use_container_width=True)
        st.download_button("Download demo log", result["log_text"], file_name="demo_log.txt")


def main() -> None:
    parser = argparse.ArgumentParser(description="Integrated UI + Researcher + Manager pipeline")
    parser.add_argument("--cli", action="store_true", help="Run terminal UI")
    parser.add_argument("--demo", action="store_true", help="Run built-in demo prompt")
    args = parser.parse_args()

    if args.demo:
        run_cli("How can students use AI tools for active learning without becoming dependent on them?")
    elif args.cli:
        run_cli()
    else:
        run_streamlit()


if __name__ == "__main__":
    main()
