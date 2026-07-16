"""ECS Paper-to-ARM Agent — Streamlit Web UI"""

import os
import tempfile
import streamlit as st
from pathlib import Path
from agents.orchestrator import Orchestrator


# ── Page config ──────────────────────────────────────────────
st.set_page_config(
    page_title="ECS Paper-to-ARM",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ───────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');

/* ── Palette: scientific instrument panel ── */
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

/* ── Global ── */
.stApp { background: var(--bg); }
* { font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif; }
h1, h2, h3 { color: var(--slate) !important; font-weight: 700 !important; }
h1 { font-size: 1.5rem !important; letter-spacing: -0.03em; }
h2 { font-size: 1.15rem !important; margin-top: 2rem !important; font-weight: 600 !important; }
h3 { font-size: 0.95rem !important; color: var(--ink) !important; }
code, .stCode, [data-testid="stCode"] { font-family: 'JetBrains Mono', monospace !important; font-size: 0.82rem; }

/* ── Sidebar: clean slate ── */
[data-testid="stSidebar"] {
  background: var(--slate);
  border-right: none;
}
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stCaption { color: rgba(255,255,255,0.8) !important; }
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
  color: #818CF8 !important; font-weight: 600 !important; letter-spacing: 0.02em;
}
[data-testid="stSidebar"] [data-testid="stTextInput"] input {
  background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.15);
  color: white; border-radius: 6px;
}

/* ── Metric cards: instrument readout style ── */
[data-testid="stMetric"] {
  background: white; border-radius: 6px; padding: 0.6rem 0.75rem;
  border: 1px solid var(--border); box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}
[data-testid="stMetric"] label { font-size: 0.7rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.05em; }
[data-testid="stMetricValue"] { color: var(--slate); font-size: 1.1rem; }

/* ── Buttons ── */
.stButton > button {
  border-radius: 6px; font-weight: 600; font-size: 0.875rem;
  transition: all 0.15s; border: none;
}
.stButton > button:hover { filter: brightness(0.95); }

/* ── Progress bar ── */
[data-testid="stProgress"] > div > div { background: var(--indigo); }

/* ── Expanders (claim cards) ── */
[data-testid="stExpander"] {
  border: 1px solid var(--border); border-radius: 6px;
  margin-bottom: 0.4rem; background: white;
  box-shadow: 0 1px 2px rgba(0,0,0,0.03);
}
[data-testid="stExpander"] summary { font-weight: 500; }

/* ── Tabs ── */
[data-testid="stTabs"] [data-baseweb="tab"] {
  font-weight: 500; font-size: 0.9rem;
}

/* ── Horizontal rule ── */
hr { border-color: var(--border); margin: 1.5rem 0; }

/* ── Pipeline stage indicator ── */
.stage-dot {
  display: inline-block; width: 8px; height: 8px; border-radius: 50%;
  margin-right: 6px; vertical-align: middle;
}
.dot-active { background: var(--indigo); box-shadow: 0 0 6px rgba(99,102,241,0.5); }
.dot-done { background: var(--green); }
.dot-pending { background: #CBD5E1; }

/* ── Claim badge ── */
.badge-exact { background: #D1FAE5; color: #065F46; }
.badge-inferred { background: #FEF3C7; color: #92400E; }
.badge-review { background: #FEE2E2; color: #991B1B; }

/* ── Dry-run verification panel ── */
.dryrun-panel {
  background: linear-gradient(135deg, #F8FAFC 0%, #F1F5F9 100%);
  border: 1px solid var(--border); border-radius: 8px;
  padding: 1rem 1.25rem; margin: 0.5rem 0;
}
.dryrun-panel .formula { font-family: 'JetBrains Mono', monospace; font-size: 1rem; color: var(--slate); }
.dryrun-panel .result-pass { color: var(--green); font-weight: 700; }
.dryrun-panel .result-fail { color: var(--red); font-weight: 700; }
.dryrun-panel .result-insufficient { color: var(--amber); font-weight: 700; }

/* ── Info/status boxes ── */
.info-box {
  background: white; border: 1px solid var(--border);
  border-radius: 6px; padding: 0.75rem 1rem; margin: 0.5rem 0;
  font-size: 0.85rem;
}
.info-box .label { color: var(--muted); font-size: 0.7rem; text-transform: uppercase; letter-spacing: 0.05em; }
</style>
""", unsafe_allow_html=True)


# ── Sidebar ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ 配置")
    api_key = st.text_input(
        "DeepSeek API Key",
        value=os.environ.get("DEEPSEEK_API_KEY", ""),
        type="password",
        help="从 ~/.claude/settings.json 自动读取，也可手动输入",
    )
    if api_key:
        os.environ["DEEPSEEK_API_KEY"] = api_key

    st.divider()
    st.markdown("### 📋 考核要求")
    st.markdown("""
    <div style="font-size:0.8rem; opacity:0.85">
    ✅ Track A: Paper-to-ARM<br>
    ✅ ≥ 5 篇论文<br>
    ✅ 结论可追溯到原文<br>
    ✅ 模型推断 vs 原文区分<br>
    ✅ 至少 1 步 dry-run<br>
    ✅ 成功案例 + 失败案例
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    st.markdown("### 🔬 关于")
    st.markdown("""
    <div style="font-size:0.75rem; opacity:0.7">
    脑细胞外间隙（ECS）Paper-to-ARM Agent。<br>
    将论文转化为结构化、可验证、<br>
    可追溯的科研资产。
    </div>
    """, unsafe_allow_html=True)


# ── Pipeline stage visual ────────────────────────────────────
def show_pipeline_stages(active: int = -1):
    """5 阶段指示器。active: -1=未开始, 0-4=当前, 5=全部完成"""
    stages = ["Ingest", "Extract", "Compute", "Validate", "Export"]
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
                {dot} {name}
                </div>""",
                unsafe_allow_html=True,
            )


def badge(method: str) -> str:
    """extraction_method → HTML badge"""
    if method == "exact_quote":
        return '<span class="badge-exact" style="display:inline-block;padding:1px 8px;border-radius:10px;font-size:0.7rem;font-weight:600;">引</span>'
    elif method == "llm_inferred":
        return '<span class="badge-inferred" style="display:inline-block;padding:1px 8px;border-radius:10px;font-size:0.7rem;font-weight:600;">推</span>'
    else:
        return '<span class="badge-review" style="display:inline-block;padding:1px 8px;border-radius:10px;font-size:0.7rem;font-weight:600;">审</span>'


# ── Main ─────────────────────────────────────────────────────
st.title("🧠 ECS Paper-to-ARM")
st.caption("脑细胞外间隙论文 → 结构化 Agent-Ready Manuscript")

tab_analyze, tab_search = st.tabs(["📤 上传 & 分析", "🔍 搜索 & 下载"])

# ═══════════════════ SEARCH TAB ═══════════════════
with tab_search:
    st.markdown("### 🔍 自动搜索 ECS 论文")
    st.caption("通过 Europe PMC API 搜索 5 类 ECS 论文，自动下载开放获取 PDF")

    col1, col2 = st.columns([3, 2])
    with col1:
        max_papers = st.slider("每类最大论文数", 1, 5, 3)
    with col2:
        email = st.text_input("联系邮箱", value="student@example.com", label_visibility="collapsed")

    if st.button("🔍 开始搜索", type="primary", use_container_width=True):
        with st.spinner("搜索中..."):
            from tools.search_papers import search_and_download_ecs_papers
            search_results = search_and_download_ecs_papers(
                output_dir="papers", max_per_query=max_papers,
                email=email, auto_download=True,
            )

        st.success(f"找到 {len(search_results.papers)} 篇，下载 {len(search_results.downloaded)} 篇")

        if search_results.papers:
            for p in search_results.papers:
                oa_icon = "🔓" if p.is_open_access else "🔒"
                if p.download_source:
                    dl = f"📥 {p.download_source.upper()}"
                else:
                    dl = "✅" if p.has_pdf else "❌ 未下载"

                with st.container():
                    st.markdown(
                        f"**{oa_icon} {dl}**  [{p.year}]  {p.title}"
                    )
                    st.caption(
                        f"{', '.join(p.authors[:3])}  ·  {p.journal}  ·  DOI: `{p.doi}`"
                    )
                    if p.abstract:
                        with st.expander("摘要"):
                            st.caption(p.abstract[:600])

        if search_results.downloaded:
            st.divider()
            st.caption(f"📦 已保存 {len(search_results.downloaded)} 个文件到 `papers/`")

# ═══════════════════ ANALYZE TAB ═══════════════════
with tab_analyze:
    st.markdown("### 📤 上传论文 PDF")
    uploaded_files = st.file_uploader(
        "拖拽或选择 PDF 文件",
        type=["pdf"],
        accept_multiple_files=True,
        help="支持 2023-2026 年 ECS 领域论文",
        label_visibility="collapsed",
    )

    if uploaded_files and st.button("🚀 开始分析", type="primary", use_container_width=True):
        if not api_key:
            st.error("请先在侧边栏输入 DeepSeek API Key")
        else:
            orchestrator = Orchestrator(output_dir="output")
            all_results = []

            # ── Pipeline progress ──
            progress_bar = st.progress(0)
            status_placeholder = st.empty()
            show_pipeline_stages(active=0)

            for i, uploaded in enumerate(uploaded_files):
                status_placeholder.markdown(
                    f"**正在处理 ({i+1}/{len(uploaded_files)})**: `{uploaded.name}`"
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

            # ════ Results ════
            st.divider()
            st.markdown("## 📊 分析结果")
            show_pipeline_stages(active=5)

            tabs = st.tabs([f"📄 {r.get('paper_id','?')[:40]}" for r in all_results])

            for tab, results in zip(tabs, all_results):
                with tab:
                    if "error" in results:
                        st.error(f"❌ {results['error']}")
                        continue

                    arm = results["arm"]
                    validation = results["validation"]
                    dry_runs = results.get("dry_runs", [])

                    # ── Pipeline timing ──
                    c1, c2, c3, c4 = st.columns(4)
                    c1.metric("📄 Ingest", f"{results['ingest_ms']}ms")
                    c2.metric("🧠 Extract", f"{results['extract_ms']}ms")
                    c3.metric("⚡ Compute", f"{results['compute_ms']}ms")
                    c4.metric("✅ Validate", f"{results['validate_ms']}ms")

                    with st.expander("⏱️ 阶段详情", expanded=False):
                        passed_count = sum(1 for d in dry_runs if d.status.value == "passed")
                        st.markdown(
                            f"**总耗时**: {results['ingest_ms'] + results['extract_ms'] + results['compute_ms'] + results['validate_ms']}ms  |  "
                            f"**Claims**: {len(arm.claims)}  |  "
                            f"**Dry-runs**: {len(dry_runs)} ({passed_count} passed)  |  "
                            f"**Validation**: {'✅' if validation.passed else '❌'}"
                        )

                    # ── Claims ──
                    st.markdown(f"### ✅ Claims ({len(arm.claims)})")
                    for c in arm.claims:
                        excerpt = c.text[:120] + ("..." if len(c.text) > 120 else "")
                        with st.expander(
                            f"{badge(c.extraction_method.value)} **{c.id}** {excerpt}",
                        ):
                            st.markdown(c.text)
                            cols = st.columns([1, 1, 2])
                            cols[0].caption(f"类型: `{c.type.value}`")
                            cols[1].caption(f"方法: `{c.extraction_method.value}`")
                            if c.source.page > 0:
                                cols[2].caption(
                                    f"📍 第 {c.source.page} 页, {c.source.section}"
                                )
                            if c.source.quoted_text:
                                st.info(f"💬 {c.source.quoted_text}")
                            if c.source.figure_ref or c.source.table_ref:
                                refs = []
                                if c.source.figure_ref: refs.append(f"📊 {c.source.figure_ref}")
                                if c.source.table_ref: refs.append(f"📋 {c.source.table_ref}")
                                st.caption(" · ".join(refs))
                            if c.evidence_refs:
                                st.caption(f"📎 证据: {', '.join(c.evidence_refs)}")

                    # ── Dry-runs (verification panel) ──
                    st.markdown(f"### 🧮 计算验证 ({len(dry_runs)})")
                    if dry_runs:
                        for dr in dry_runs:
                            status = dr.status.value
                            if status == "passed":
                                icon, css_class = "✓", "result-pass"
                            elif status == "mismatch":
                                icon, css_class = "⚠", "result-fail"
                            else:
                                icon, css_class = "?", "result-insufficient"

                            computed = f"{dr.computed_value:.4g}" if dr.computed_value is not None else "—"
                            reported = f"{dr.reported_value:.4g}" if dr.reported_value is not None else "—"
                            dev = f"{dr.deviation_pct:.1f}%" if dr.deviation_pct is not None else "—"

                            st.markdown(
                                f"""<div class="dryrun-panel">
                                <span class="{css_class}" style="font-size:1.2rem;">{icon}</span>
                                <span style="font-weight:600;color:#334155;">{dr.statement_id}</span>
                                <span style="float:right;font-size:0.8rem;color:#94A3B8;">{status}</span>
                                <br>
                                <span style="font-family:'JetBrains Mono',monospace;font-size:0.85rem;">
                                计算值 = {computed} 　 论文值 = {reported} 　 偏差 = {dev}
                                </span>
                                </div>""",
                                unsafe_allow_html=True,
                            )
                    else:
                        st.info("未提取到可计算的数值声明")

                    # ── Validation ──
                    st.markdown("### 🔍 校验")
                    v1, v2 = st.columns(2)
                    with v1:
                        result_label = "✅ PASSED" if validation.passed else "❌ FAILED"
                        st.metric("结果", result_label)
                        st.metric("Provenance", f"{validation.provenance_score:.0%}")
                    with v2:
                        if validation.hallucination_flags:
                            st.error(f"🚨 Hallucination: {len(validation.hallucination_flags)} 条")
                            for hf in validation.hallucination_flags:
                                st.caption(hf)
                        if validation.review_required_count:
                            st.warning(f"⚠️ Review: {validation.review_required_count}")
                        if validation.claim_evidence_gaps:
                            st.warning(f"📎 Gaps: {len(validation.claim_evidence_gaps)}")

                    # ── Downloads ──
                    st.markdown("### 📦 导出")
                    paths = results.get("export_paths", {})
                    dl_cols = st.columns(len(paths) if paths else 1)
                    for col, (key, path) in zip(dl_cols, paths.items()):
                        if Path(path).exists():
                            with open(path, "r", encoding="utf-8") as f:
                                content = f.read()
                            ext = Path(path).suffix
                            mime = {".yaml": "text/yaml", ".json": "application/json", ".log": "text/plain"}.get(ext, "text/plain")
                            col.download_button(f"📥 {key}", data=content, file_name=f"{results['paper_id']}_{key}{ext}", mime=mime, use_container_width=True)

            # ── Summary table ──
            st.divider()
            st.markdown("## 📈 批量汇总")
            summary_rows = []
            for r in all_results:
                if "error" in r:
                    continue
                a = r["arm"]
                d = r.get("dry_runs", [])
                v = r["validation"]
                summary_rows.append({
                    "论文": r["paper_id"][:50],
                    "Claims": len(a.claims),
                    "Dry-runs": len(d),
                    "Passed": sum(1 for x in d if x.status.value == "passed"),
                    "Hallucination": len(v.hallucination_flags),
                    "Review": v.review_required_count,
                    "校验": "✅" if v.passed else "❌",
                })
            if summary_rows:
                st.dataframe(summary_rows, use_container_width=True, hide_index=True)
