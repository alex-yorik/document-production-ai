import streamlit as st
from pathlib import Path

from src.utils import INPUT_DIR, OUTPUT_DIR

# Инициализация состояния сессии
if 'generation_complete' not in st.session_state:
    st.session_state.generation_complete = False

# Конфигурация страницы
st.set_page_config(
    page_title="Document Production AI",
    page_icon="📄",
    layout="wide"
)

# Заголовок
st.title("📄 Document Production AI")
st.markdown("Automated document generation with AI Quality Control")

# Боковая панель с информацией
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

# Экран 1: Загрузка файлов
st.subheader("Upload Source Documents")
st.markdown("Upload 2-5 files (company brief, market data, methodology)")

uploaded_files = st.file_uploader(
    "Choose files",
    type=["md", "txt"],
    accept_multiple_files=True,
    key="file_uploader"
)

project_name = st.text_input(
    "Project name (optional)",
    "Market Entry Report",
    key="project_name"
)

st.caption("The pipeline requires a file named `methodology.md` among the uploaded files.")


# Функция для очистки входной папки
def clean_input_dir():
    input_dir = Path(INPUT_DIR)
    if input_dir.exists():
        for file in input_dir.iterdir():
            if file.is_file():
                file.unlink()


# Функция для сохранения загруженных файлов
def save_uploaded_files(uploaded_files):
    clean_input_dir()
    input_dir = Path(INPUT_DIR)
    input_dir.mkdir(parents=True, exist_ok=True)

    for uploaded_file in uploaded_files:
        file_path = input_dir / uploaded_file.name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getvalue())


def format_delta(value: int) -> str:
    """Format a signed delta for the metrics display."""
    return f"+{value}" if value > 0 else str(value)


# Экран с результатами (показывается повторно после re-run страницы)
def show_results_page(output):
    st.success("Document generated successfully!")

    # Метрики
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            label="Draft Quality Score",
            value=f"{output['draft_score']}/100",
            delta=None
        )

    with col2:
        st.metric(
            label="Final Quality Score",
            value=f"{output['final_score']}/100",
            delta=format_delta(output['final_score'] - output['draft_score'])
        )

    with col3:
        st.metric(
            label="Issues Resolved",
            value=f"{output['resolved_issues']}/{output['draft_issues']}",
            delta=f"{output['resolution_rate']}%"
        )

    # Предупреждение о оставшихся HIGH issues
    if output['remaining_high'] > 0:
        st.warning(
            f"⚠️ {output['remaining_high']} HIGH-severity issues remain "
            "— flagged for human review"
        )
    else:
        st.success("✅ All HIGH-severity issues resolved automatically")

    # Раскрывающийся список оставшихся issues
    if output['remaining_issues']:
        with st.expander(
            f"View remaining issues ({len(output['remaining_issues'])})"
        ):
            for idx, issue in enumerate(output['remaining_issues'], 1):
                st.markdown(f"**{idx}. {issue.get('section', 'N/A')}**")
                st.text(
                    f"Type: {issue.get('severity', 'N/A')} - "
                    f"{issue.get('issue_type', 'N/A')}"
                )
                st.text(f"Description: {issue.get('description', 'N/A')}")
                st.text(f"Suggestion: {issue.get('suggestion', 'N/A')}")
                st.divider()

    # Кнопки скачивания
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
                    use_container_width=True
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
                    use_container_width=True
                )

    # Показываем ссылку на QC Report
    st.subheader("QC Report Preview")
    if qc_path.exists():
        with open(qc_path, "r", encoding="utf-8") as f:
            st.markdown(f.read()[:2000] + "...")


# Если генерация уже завершена — показываем результаты (страница не сбрасывается)
if st.session_state.get('generation_complete', False):
    show_results_page(st.session_state['output'])


# Кнопка Generate
if st.button("🚀 Generate Report", type="primary", disabled=len(uploaded_files) == 0):
    # Сбрасываем флаг перед новой генерацией
    st.session_state['generation_complete'] = False

    # Сохраняем файлы
    save_uploaded_files(uploaded_files)

    # Экран 2: Обработка (спиннер)
    with st.spinner("Processing document... This will take 2-4 minutes"):
        progress_bar = st.progress(0)
        status_text = st.empty()

        # Запускаем pipeline
        try:
            status_text.text("Stage 1-2: Ingestion & Retrieval...")
            progress_bar.progress(20)

            status_text.text("Stage 3: Outline Generation...")
            progress_bar.progress(40)

            status_text.text("Stage 4: Section Generation...")
            progress_bar.progress(60)

            status_text.text("Stage 5-6: QC Review & Revision...")
            progress_bar.progress(80)

            status_text.text("Stage 7: Document Assembly...")
            progress_bar.progress(90)

            # Импортируем и запускаем pipeline
            from run_pipeline import run_full_pipeline
            output = run_full_pipeline()

            progress_bar.progress(100)
            status_text.text("✅ Complete!")

            # Сохраняем результат в session_state
            st.session_state['generation_complete'] = True
            st.session_state['output'] = output

            # Экран 3: Результат
            show_results_page(output)

        except Exception as e:
            st.error(f"Error: {str(e)}")
            import traceback
            st.code(traceback.format_exc())

# Footer
st.markdown("---")
st.caption("Document Production AI v1.0")
