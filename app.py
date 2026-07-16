"""ECS Paper-to-ARM Agent — Streamlit Web UI"""

import os
import tempfile
import streamlit as st
from pathlib import Path
from agents.orchestrator import Orchestrator


st.set_page_config(
    page_title="ECS Paper-to-ARM",
    page_icon="",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

:root {
  --slate: #0F172A;
  --green: #10B981;
  --amber: #F59E0B;
  --red: #EF4444;
  --indigo: #6366F1;
  --surface: #FFFFFF;
  --bg: #F8FAFC;
  --border: #E2E8F0;
  --text: #1E293B;
  --muted: #94A3B8;
  --ink: #334155;
}

* { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
h1 { font-size: 1.5rem !important; letter-spacing: -0.03em; }
h2 { font-size: 1.15rem !important; margin-top: 2rem !important; }
h3 { font-size: 0.95rem !important; }
code { font-family: 'JetBrains Mono', monospace !important; font-size: 0.82rem; }

[data-testid="stMetric"] label { font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; }
[data-testid="stMetricValue"] { font-size: 1.1rem; }
.stButton > button { border-radius: 6px; font-weight: 600; font-size: 0.875rem; }
[data-testid="stExpander"] summary { font-weight: 500; }
[data-testid="stTabs"] [data-baseweb="tab"] { font-weight: 500; }

/* Pipeline indicator */
.stage-dot {
  display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; vertical-align: middle;
}
.dot-active { background: var(--indigo); box-shadow: 0 0 6px rgba(99,102,241,0.5); }
.dot-done { background: var(--green); }
.dot-pending { background: #CBD5E1; }

/* Claim badge */
.badge-exact { background: #D1FAE5; color: #065F46; }
.badge-inferred { background: #FEF3C7; color: #92400E; }
.badge-review { background: #FEE2E2; color: #991B1B; }

/* Dry-run verification panel */
.dryrun-panel {
  background: linear-gradient(135deg, #F8FAFC 0%, #F1F5F9 100%);
  border: 1px solid var(--border); border-radius: 8px;
  padding: 1rem 1.25rem; margin: 0.5rem 0;
}
.dryrun-panel .result-pass { color: var(--green); font-weight: 700; }
.dryrun-panel .result-fail { color: var(--red); font-weight: 700; }
.dryrun-panel .result-insufficient { color: var(--amber); font-weight: 700; }
</style>
""", unsafe_allow_html=True)


# ── i18n ─────────────────────────────────────────────────────
T = {
    "en": {
        "title": "ECS Paper-to-ARM",
        "subtitle": "Brain extracellular space papers -- structured Agent-Ready Manuscripts",
        "tab_analyze": "Analyze",
        "tab_search": "Search",
        "sidebar_config": "Config",
        "sidebar_api_key": "DeepSeek API Key",
        "sidebar_api_help": "Auto-read from ~/.claude/settings.json, or enter manually",
        "sidebar_req": "Requirements",
        "sidebar_req_track": "Track A: Paper-to-ARM",
        "sidebar_req_papers": ">= 5 papers",
        "sidebar_req_traceable": "Claims traceable to source",
        "sidebar_req_distinguish": "Model inference vs source text",
        "sidebar_req_dryrun": ">= 1 dry-run step",
        "sidebar_req_cases": "Success + failure cases",
        "sidebar_about": "About",
        "sidebar_about_text": "ECS Paper-to-ARM Agent. Converts papers into structured, verifiable, traceable research assets.",
        "search_title": "Search ECS papers",
        "search_caption": "Europe PMC API -- search 5 categories, auto-download OA PDFs",
        "search_max": "Max papers per category",
        "search_email": "Contact email",
        "search_button": "Search",
        "search_spinner": "Searching...",
        "search_found": "Found {n}, downloaded {d}",
        "search_oa": "OA",
        "search_closed": "Closed",
        "search_dl_pmc": "[downloaded: europepmc]",
        "search_dl_doi": "[downloaded: doi]",
        "search_has_pdf": "[has PDF]",
        "search_no_dl": "[not downloaded]",
        "search_abstract": "Abstract",
        "search_saved": "Saved {n} files to `papers/`",
        "analyze_title": "Upload paper PDFs",
        "analyze_uploader": "Select PDF files",
        "analyze_uploader_help": "ECS papers, 2023-2026",
        "analyze_button": "Analyze",
        "analyze_api_error": "Please enter DeepSeek API Key in the sidebar",
        "analyze_processing": "Processing ({i}/{total})",
        "results_title": "Results",
        "results_error": "Error",
        "pipeline_ingest": "Ingest",
        "pipeline_extract": "Extract",
        "pipeline_compute": "Compute",
        "pipeline_validate": "Validate",
        "claims_title": "Claims ({n})",
        "claim_type": "Type",
        "claim_method": "Method",
        "claim_page": "Page {page}, {section}",
        "claim_evidence": "Evidence",
        "verification_title": "Verification ({n})",
        "verification_none": "No numerical statements extracted for verification",
        "validation_title": "Validation",
        "validation_result": "Result",
        "validation_provenance": "Provenance",
        "validation_passed": "PASSED",
        "validation_failed": "FAILED",
        "validation_hallucination": "Hallucination: {n}",
        "validation_review": "Review required: {n}",
        "validation_gaps": "Claim-evidence gaps: {n}",
        "export_title": "Export",
        "export_download": "Download {key}",
        "summary_title": "Summary",
        "summary_paper": "Paper",
        "summary_claims": "Claims",
        "summary_verifications": "Verifications",
        "summary_passed": "Passed",
        "summary_hallucination": "Hallucination",
        "summary_review": "Review",
        "summary_valid": "Valid",
        "summary_yes": "Yes",
        "summary_no": "No",
        "stage_ingest": "Ingest",
        "stage_extract": "Extract",
        "stage_compute": "Compute",
        "stage_validate": "Validate",
        "stage_export": "Export",
        "lang_switch": "Language",
    },
    "zh": {
        "title": "ECS Paper-to-ARM",
        "subtitle": "将脑细胞外间隙论文转化为结构化 Agent-Ready Manuscript",
        "tab_analyze": "分析",
        "tab_search": "搜索",
        "sidebar_config": "配置",
        "sidebar_api_key": "DeepSeek API Key",
        "sidebar_api_help": "从 ~/.claude/settings.json 自动读取，或手动输入",
        "sidebar_req": "考核要求",
        "sidebar_req_track": "Track A: Paper-to-ARM",
        "sidebar_req_papers": "不少于 5 篇论文",
        "sidebar_req_traceable": "结论可追溯到原文",
        "sidebar_req_distinguish": "模型推断与原文区分",
        "sidebar_req_dryrun": "至少 1 步可试运行",
        "sidebar_req_cases": "成功案例 + 失败案例",
        "sidebar_about": "关于",
        "sidebar_about_text": "ECS Paper-to-ARM Agent。将论文转化为结构化、可验证、可追溯的科研资产。",
        "search_title": "搜索 ECS 论文",
        "search_caption": "通过 Europe PMC API 搜索 5 类论文，自动下载开放获取 PDF",
        "search_max": "每类最大论文数",
        "search_email": "联系邮箱",
        "search_button": "搜索",
        "search_spinner": "搜索中...",
        "search_found": "找到 {n} 篇，下载 {d} 篇",
        "search_oa": "开放获取",
        "search_closed": "未开放",
        "search_dl_pmc": "[已下载: europepmc]",
        "search_dl_doi": "[已下载: doi]",
        "search_has_pdf": "[有 PDF]",
        "search_no_dl": "[未下载]",
        "search_abstract": "摘要",
        "search_saved": "已保存 {n} 个文件到 `papers/`",
        "analyze_title": "上传论文 PDF",
        "analyze_uploader": "选择 PDF 文件",
        "analyze_uploader_help": "ECS 领域论文，2023-2026",
        "analyze_button": "开始分析",
        "analyze_api_error": "请在侧边栏输入 DeepSeek API Key",
        "analyze_processing": "正在处理 ({i}/{total})",
        "results_title": "分析结果",
        "results_error": "错误",
        "pipeline_ingest": "解析",
        "pipeline_extract": "提取",
        "pipeline_compute": "验证",
        "pipeline_validate": "校验",
        "claims_title": "结论 ({n})",
        "claim_type": "类型",
        "claim_method": "方式",
        "claim_page": "第 {page} 页, {section}",
        "claim_evidence": "证据",
        "verification_title": "计算验证 ({n})",
        "verification_none": "未提取到可计算的数值声明",
        "validation_title": "校验",
        "validation_result": "结果",
        "validation_provenance": "溯源覆盖率",
        "validation_passed": "通过",
        "validation_failed": "未通过",
        "validation_hallucination": "幻觉检测: {n} 条",
        "validation_review": "需复核: {n} 条",
        "validation_gaps": "结论-证据缺口: {n} 条",
        "export_title": "导出",
        "export_download": "下载 {key}",
        "summary_title": "批量汇总",
        "summary_paper": "论文",
        "summary_claims": "结论数",
        "summary_verifications": "验证数",
        "summary_passed": "通过",
        "summary_hallucination": "幻觉",
        "summary_review": "需复核",
        "summary_valid": "有效",
        "summary_yes": "是",
        "summary_no": "否",
        "stage_ingest": "解析",
        "stage_extract": "提取",
        "stage_compute": "计算",
        "stage_validate": "校验",
        "stage_export": "导出",
        "lang_switch": "语言",
    },
}


def t(key: str, **kwargs) -> str:
    """Get translated string. Uses session_state.lang (defaults to 'zh')."""
    lang = st.session_state.get("lang", "zh")
    s = T.get(lang, T["zh"]).get(key, key)
    if kwargs:
        s = s.format(**kwargs)
    return s


# ── Helpers ──────────────────────────────────────────────────
def show_pipeline_stages(active: int = -1):
    stages = [
        t("stage_ingest"), t("stage_extract"), t("stage_compute"),
        t("stage_validate"), t("stage_export"),
    ]
    cols = st.columns(5)
    for i, name in enumerate(stages):
        with cols[i]:
            if i < active:
                dot = '<span class="stage-dot dot-done"></span>'
                color = "#065F46"
            elif i == active:
                dot = '<span class="stage-dot dot-active"></span>'
                color = "#6366F1"
            else:
                dot = '<span class="stage-dot dot-pending"></span>'
                color = "#94A3B8"
            st.markdown(
                f"""<div style="font-size:0.72rem;font-weight:600;color:{color};white-space:nowrap;">
                {dot} {name}</div>""",
                unsafe_allow_html=True,
            )


def badge(method: str) -> str:
    if method == "exact_quote":
        return '<span class="badge-exact" style="display:inline-block;padding:1px 8px;border-radius:10px;font-size:0.7rem;font-weight:600;">Exact</span>'
    elif method == "llm_inferred":
        return '<span class="badge-inferred" style="display:inline-block;padding:1px 8px;border-radius:10px;font-size:0.7rem;font-weight:600;">Infer</span>'
    else:
        return '<span class="badge-review" style="display:inline-block;padding:1px 8px;border-radius:10px;font-size:0.7rem;font-weight:600;">Review</span>'


# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    # Language toggle
    if "lang" not in st.session_state:
        st.session_state.lang = "zh"
    lang = st.radio(
        t("lang_switch"), ["zh", "en"],
        index=0 if st.session_state.lang == "zh" else 1,
        horizontal=True, label_visibility="collapsed",
    )
    st.session_state.lang = lang

    st.markdown(f"### {t('sidebar_config')}")
    api_key = st.text_input(
        t("sidebar_api_key"),
        value=os.environ.get("DEEPSEEK_API_KEY", ""),
        type="password",
        help=t("sidebar_api_help"),
    )
    if api_key:
        os.environ["DEEPSEEK_API_KEY"] = api_key

    st.divider()
    st.markdown(f"### {t('sidebar_req')}")
    st.markdown(f"""
    <div style="font-size:0.8rem; opacity:0.85">
    {t('sidebar_req_track')}<br>
    {t('sidebar_req_papers')}<br>
    {t('sidebar_req_traceable')}<br>
    {t('sidebar_req_distinguish')}<br>
    {t('sidebar_req_dryrun')}<br>
    {t('sidebar_req_cases')}
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.markdown(f"### {t('sidebar_about')}")
    st.markdown(f"""<div style="font-size:0.75rem; opacity:0.7">{t('sidebar_about_text')}</div>""", unsafe_allow_html=True)


# ── Main ─────────────────────────────────────────────────────
st.title(t("title"))
st.caption(t("subtitle"))

tab_analyze, tab_search = st.tabs([t("tab_analyze"), t("tab_search")])

# ═══════════════════ SEARCH TAB ═══════════════════
with tab_search:
    st.markdown(f"### {t('search_title')}")
    st.caption(t("search_caption"))

    col1, col2 = st.columns([3, 2])
    with col1:
        max_papers = st.slider(t("search_max"), 1, 5, 3)
    with col2:
        email = st.text_input(t("search_email"), value="student@example.com", label_visibility="collapsed")

    if st.button(t("search_button"), type="primary", use_container_width=True):
        with st.spinner(t("search_spinner")):
            from tools.search_papers import search_and_download_ecs_papers
            search_results = search_and_download_ecs_papers(
                output_dir="papers", max_per_query=max_papers,
                email=email, auto_download=True,
            )

        st.success(t("search_found", n=len(search_results.papers), d=len(search_results.downloaded)))

        if search_results.papers:
            for p in search_results.papers:
                oa = t("search_oa") if p.is_open_access else t("search_closed")
                if p.download_source:
                    dl = t("search_dl_pmc") if p.download_source == "europepmc" else t("search_dl_doi")
                else:
                    dl = t("search_has_pdf") if p.has_pdf else t("search_no_dl")

                with st.container():
                    st.markdown(f"**[{p.year}]** {p.title}  --  *{oa}, {dl}*")
                    st.caption(f"{', '.join(p.authors[:3])}  |  {p.journal}  |  DOI: `{p.doi}`")
                    if p.abstract:
                        with st.expander(t("search_abstract")):
                            st.caption(p.abstract[:600])

        if search_results.downloaded:
            st.divider()
            st.caption(t("search_saved", n=len(search_results.downloaded)))

# ═══════════════════ ANALYZE TAB ═══════════════════
with tab_analyze:
    st.markdown(f"### {t('analyze_title')}")
    uploaded_files = st.file_uploader(
        t("analyze_uploader"),
        type=["pdf"],
        accept_multiple_files=True,
        help=t("analyze_uploader_help"),
        label_visibility="collapsed",
    )

    if uploaded_files and st.button(t("analyze_button"), type="primary", use_container_width=True):
        if not api_key:
            st.error(t("analyze_api_error"))
        else:
            orchestrator = Orchestrator(output_dir="output")
            all_results = []

            progress_bar = st.progress(0)
            status_placeholder = st.empty()
            show_pipeline_stages(active=0)

            for i, uploaded in enumerate(uploaded_files):
                status_placeholder.markdown(
                    f"**{t('analyze_processing', i=i+1, total=len(uploaded_files))}**: `{uploaded.name}`"
                )

                with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                    tmp.write(uploaded.read())
                    tmp_path = tmp.name

                try:
                    results = orchestrator.run(tmp_path)
                    all_results.append(results)
                finally:
                    Path(tmp_path).unlink(missing_ok=True)

                progress_bar.progress((i + 1) / len(uploaded_files))

            progress_bar.empty()
            status_placeholder.empty()

            # Results
            st.divider()
            st.markdown(f"## {t('results_title')}")
            show_pipeline_stages(active=5)

            tabs = st.tabs([r.get('paper_id', '?')[:40] for r in all_results])

            for tab, results in zip(tabs, all_results):
                with tab:
                    if "error" in results:
                        st.error(f"{t('results_error')}: {results['error']}")
                        continue

                    arm = results["arm"]
                    validation = results["validation"]
                    dry_runs = results.get("dry_runs", [])

                    # Pipeline timing
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric(t("pipeline_ingest"), f"{results['ingest_ms']}ms")
                    c2.metric(t("pipeline_extract"), f"{results['extract_ms']}ms")
                    c3.metric(t("pipeline_compute"), f"{results['compute_ms']}ms")
                    c4.metric(t("pipeline_validate"), f"{results['validate_ms']}ms")

                    # Claims
                    st.markdown(f"### {t('claims_title', n=len(arm.claims))}")
                    for c in arm.claims:
                        excerpt = c.text[:120] + ("..." if len(c.text) > 120 else "")
                        with st.expander(f"{badge(c.extraction_method.value)} **{c.id}** {excerpt}"):
                            st.markdown(c.text)
                            cols = st.columns([1, 1, 2])
                            cols[0].caption(f"{t('claim_type')}: `{c.type.value}`")
                            cols[1].caption(f"{t('claim_method')}: `{c.extraction_method.value}`")
                            if c.source.page > 0:
                                cols[2].caption(t("claim_page", page=c.source.page, section=c.source.section))
                            if c.source.quoted_text:
                                st.info(c.source.quoted_text)
                            if c.source.figure_ref or c.source.table_ref:
                                refs = []
                                if c.source.figure_ref: refs.append(f"Fig: {c.source.figure_ref}")
                                if c.source.table_ref: refs.append(f"Table: {c.source.table_ref}")
                                st.caption(" | ".join(refs))
                            if c.evidence_refs:
                                st.caption(f"{t('claim_evidence')}: {', '.join(c.evidence_refs)}")

                    # Dry-runs
                    st.markdown(f"### {t('verification_title', n=len(dry_runs))}")
                    if dry_runs:
                        for dr in dry_runs:
                            status = dr.status.value
                            if status == "passed":
                                icon, css_class = "+", "result-pass"
                            elif status == "mismatch":
                                icon, css_class = "!", "result-fail"
                            else:
                                icon, css_class = "?", "result-insufficient"

                            computed = f"{dr.computed_value:.4g}" if dr.computed_value is not None else "--"
                            reported = f"{dr.reported_value:.4g}" if dr.reported_value is not None else "--"
                            dev = f"{dr.deviation_pct:.1f}%" if dr.deviation_pct is not None else "--"

                            st.markdown(
                                f"""<div class="dryrun-panel">
                                <span class="{css_class}" style="font-size:1.2rem;">{icon}</span>
                                <span style="font-weight:600;">{dr.statement_id}</span>
                                <span style="float:right;font-size:0.8rem;">{status}</span>
                                <br>
                                <span style="font-family:'JetBrains Mono',monospace;font-size:0.85rem;">
                                computed = {computed} | reported = {reported} | dev = {dev}
                                </span>
                                </div>""",
                                unsafe_allow_html=True,
                            )
                    else:
                        st.info(t("verification_none"))

                    # Validation
                    st.markdown(f"### {t('validation_title')}")
                    v1, v2 = st.columns(2)
                    with v1:
                        result_label = t("validation_passed") if validation.passed else t("validation_failed")
                        st.metric(t("validation_result"), result_label)
                        st.metric(t("validation_provenance"), f"{validation.provenance_score:.0%}")
                    with v2:
                        if validation.hallucination_flags:
                            st.error(t("validation_hallucination", n=len(validation.hallucination_flags)))
                            for hf in validation.hallucination_flags:
                                st.caption(hf)
                        if validation.review_required_count:
                            st.warning(t("validation_review", n=validation.review_required_count))
                        if validation.claim_evidence_gaps:
                            st.warning(t("validation_gaps", n=len(validation.claim_evidence_gaps)))

                    # Downloads
                    st.markdown(f"### {t('export_title')}")
                    paths = results.get("export_paths", {})
                    dl_cols = st.columns(len(paths) if paths else 1)
                    for col, (key, path) in zip(dl_cols, paths.items()):
                        if Path(path).exists():
                            with open(path, "r", encoding="utf-8") as f:
                                content = f.read()
                            ext = Path(path).suffix
                            mime = {".yaml": "text/yaml", ".json": "application/json", ".log": "text/plain"}.get(ext, "text/plain")
                            col.download_button(t("export_download", key=key), data=content, file_name=f"{results['paper_id']}_{key}{ext}", mime=mime, use_container_width=True)

            # Summary table
            st.divider()
            st.markdown(f"## {t('summary_title')}")
            summary_rows = []
            for r in all_results:
                if "error" in r:
                    continue
                a = r["arm"]
                d = r.get("dry_runs", [])
                v = r["validation"]
                summary_rows.append({
                    t("summary_paper"): r["paper_id"][:50],
                    t("summary_claims"): len(a.claims),
                    t("summary_verifications"): len(d),
                    t("summary_passed"): sum(1 for x in d if x.status.value == "passed"),
                    t("summary_hallucination"): len(v.hallucination_flags),
                    t("summary_review"): v.review_required_count,
                    t("summary_valid"): t("summary_yes") if v.passed else t("summary_no"),
                })
            if summary_rows:
                st.dataframe(summary_rows, use_container_width=True, hide_index=True)
