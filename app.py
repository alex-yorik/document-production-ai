import os
import traceback
from pathlib import Path

import streamlit as st

from src.upload_utils import format_delta, save_uploaded_files, validate_uploads
from src.utils import OUTPUT_DIR

# Initialize session state
if "generation_complete" not in st.session_state:
    st.session_state.generation_complete = False
if "error" not in st.session_state:
    st.session_state.error = None


def _reset_generation_state():
    """Return the UI to the upload form and clear any previous run."""
    st.session_state["generation_complete"] = False
    st.session_state["error"] = None
    st.session_state.pop("output", None)


# Page configuration
st.set_page_config(page_title="Document Production AI", page_icon="📄", layout="wide")

# Title
st.title("📄 Document Production AI")
st.markdown("Automated document generation with AI Quality Control")

st.warning(
    "Demo. Do not upload real personal or confidential data. Uploaded text is "
    "sent to an external LLM service (DeepSeek)."
)

if st.session_state.get("error"):
    st.error(st.session_state["error"])

# Sidebar with information
with st.sidebar:
    st.header("How it works")
    st.markdown("""
    1. Upload source documents (.md, .txt)
    2. Click 'Generate Report'
    3. AI creates outline, writes sections
    4. QC Reviewer checks for errors
    5. Revision Loop fixes issues
    6. Download final DOCX + QC Report
    """)

    st.info("Processing time: 2-4 minutes")

# Screen 1: File upload
st.subheader("Upload Source Documents")
st.markdown(
    "Upload 2-5 files. `methodology.md` is required; `company_brief.md` and "
    "`market_data.md` are used by the demo (optional extras are used for "
    "retrieval only)."
)

uploaded_files = st.file_uploader("Choose files", type=["md", "txt"], accept_multiple_files=True, key="file_uploader")

st.warning("Generating a report replaces all files currently stored in input/.")

project_name = st.text_input("Project name (optional)", os.getenv("REPORT_TITLE", ""), key="project_name")

st.caption("Required file name: `methodology.md`.")


# Results screen (shown again after the page re-runs)
def _show_metrics(output):
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="Draft Quality Score", value=f"{output['draft_score']}/100", delta=None)

    with col2:
        st.metric(
            label="Final Quality Score",
            value=f"{output['final_score']}/100",
            delta=format_delta(output["final_score"] - output["draft_score"]),
        )

    with col3:
        st.metric(
            label="Issues Resolved",
            value=f"{output['resolved_issues']}/{output['draft_issues']}",
            delta=f"{output['resolution_rate']}%",
        )

    # Warn about remaining HIGH issues
    if output["remaining_high"] > 0:
        st.warning(f"⚠️ {output['remaining_high']} HIGH-severity issues remain — flagged for human review")
    else:
        st.success("✅ All HIGH-severity issues resolved automatically")


def _show_remaining_issues(output):
    if not output["remaining_issues"]:
        return
    with st.expander(f"View remaining issues ({len(output['remaining_issues'])})"):
        for idx, issue in enumerate(output["remaining_issues"], 1):
            st.markdown(f"**{idx}. {issue.get('section', 'N/A')}**")
            st.text(f"Type: {issue.get('severity', 'N/A')} - {issue.get('issue_type', 'N/A')}")
            st.text(f"Description: {issue.get('description', 'N/A')}")
            st.text(f"Suggestion: {issue.get('suggestion', 'N/A')}")
            st.divider()


def _show_downloads():
    st.subheader("Download")

    col1, col2 = st.columns(2)

    docx_path = Path(OUTPUT_DIR) / "Final_Report.docx"
    with col1:
        if docx_path.exists():
            with open(docx_path, "rb") as f:
                st.download_button(
                    label="📄 Download Final Report (DOCX)",
                    data=f.read(),
                    file_name="Final_Report.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )

    qc_path = Path(OUTPUT_DIR) / "QC_Report.md"
    with col2:
        if qc_path.exists():
            with open(qc_path, "rb") as f:
                st.download_button(
                    label="📊 Download QC Report (MD)",
                    data=f.read(),
                    file_name="QC_Report.md",
                    mime="text/markdown",
                    use_container_width=True,
                )

    # Show the QC Report link
    st.subheader("QC Report Preview")
    if qc_path.exists():
        with open(qc_path, encoding="utf-8") as f:
            st.markdown(f.read()[:2000] + "...")


def show_results_page(output):
    st.success("Document generated successfully!")
    _show_metrics(output)
    _show_remaining_issues(output)
    _show_downloads()


# If generation has already finished, show the results (page state is preserved)
if st.session_state.get("generation_complete", False):
    output = st.session_state.get("output")
    if isinstance(output, dict):
        try:
            show_results_page(output)
        except Exception as e:  # noqa: BLE001 — never leave the UI in a broken state
            _reset_generation_state()
            st.session_state["error"] = f"Could not display results: {e}"
            st.error(st.session_state["error"])
    else:
        _reset_generation_state()
        st.error("Previous results are unavailable. Please generate the report again.")

# Let the user clear results and start over without reloading the page
if st.button("🔄 Reset / New Report", key="reset_button"):
    _reset_generation_state()
    st.rerun()


# Generate button
if st.button("🚀 Generate Report", type="primary", key="generate_button", disabled=len(uploaded_files) == 0):
    # Reset the flag before a new generation
    _reset_generation_state()

    upload_error = validate_uploads(uploaded_files)
    if upload_error:
        st.error(upload_error)
        st.stop()

    # Save the files
    save_uploaded_files(uploaded_files)

    if project_name:
        os.environ["REPORT_TITLE"] = project_name

    # Screen 2: Processing (spinner)
    with st.spinner("Processing (usually a few minutes)..."):
        try:
            from run_pipeline import run_full_pipeline

            output = run_full_pipeline()

        except Exception as e:  # noqa: BLE001 — surface any pipeline failure in the Streamlit UI
            st.session_state["generation_complete"] = False
            st.session_state["error"] = f"Pipeline failed: {e}"
            st.session_state.pop("output", None)
            st.error(st.session_state["error"])
            st.code(traceback.format_exc())

        else:
            # Store the result in session_state
            st.session_state["generation_complete"] = True
            st.session_state["error"] = None
            st.session_state["output"] = output

            # Screen 3: Result
            show_results_page(output)

# Footer
st.markdown("---")
st.caption("Document Production AI v1.0")
