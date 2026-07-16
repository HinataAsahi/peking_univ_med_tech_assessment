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
/* ── Palette: neuroscience dark-field + fluorescent tracer ── */
:root {
  --navy: #0D1B2A;
  --teal: #00E5A0;
  --surface: #ffffff;
  --bg: #F5F7FA;
  --text: #1A1A2E;
  --muted: #6B7280;
  --warn: #F59E0B;
  --danger: #EF4444;
}

/* ── Global ── */
.stApp { background: var(--bg); }
h1, h2, h3 { color: var(--navy) !important; font-weight: 700 !important; }
h1 { font-size: 1.75rem !important; letter-spacing: -0.02em; }
h2 { font-size: 1.25rem !important; margin-top: 2rem !important; }
h3 { font-size: 1rem !important; }

/* ── Sidebar ── */
[data-testid="stSidebar"] {
  background: linear-gradient(180deg, #0D1B2A 0%, #1B2D45 100%);
}
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stCaption { color: rgba(255,255,255,0.85) !important; }
[data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: #00E5A0 !important; }
[data-testid="stSidebar"] [data-testid="stTextInput"] input {
  background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); color: white;
}

/* ── Cards ── */
.stCard {
  background: white; border-radius: 12px; padding: 1.25rem;
  box-shadow: 0 1px 3px rgba(0,0,0,0.08); border: 1px solid #E5E7EB;
  margin-bottom: 0.75rem;
}

/* ── Claim expander ── */
[data-testid="stExpander"] {
  border: 1px solid #E5E7EB; border-radius: 8px;
  margin-bottom: 0.5rem; background: white;
}

/* ── Metric cards ── */
[data-testid="stMetric"] {
  background: white; border-radius: 8px; padding: 0.75rem 1rem;
  border: 1px solid #E5E7EB;
}
[data-testid="stMetric"] label { font-size: 0.75rem; color: var(--muted); }
[data-testid="stMetricValue"] { color: var(--navy); }

/* ── Buttons ── */
.stButton > button {
  border-radius: 8px; font-weight: 600; transition: all 0.2s;
}
.stButton > button:hover { transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,0,0,0.15); }

/* ── Progress bar ── */
[data-testid="stProgress"] > div > div { background: var(--teal); }

/* ── Pipeline stage tags ── */
.stage-tag {
  display: inline-block; padding: 2px 10px; border-radius: 12px;
  font-size: 0.75rem; font-weight: 600; margin-right: 4px;
}
.stage-ingest { background: #E0E7FF; color: #3730A3; }
.stage-extract { background: #EDE9FE; color: #6D28D9; }
.stage-compute { background: #FCE7F3; color: #BE185D; }
.stage-validate { background: #D1FAE5; color: #065F46; }

/* ── Claim method badges ── */
.claim-exact { background: #D1FAE5; color: #065F46; }
.claim-inferred { background: #FEF3C7; color: #92400E; }
.claim-review { background: #FEE2E2; color: #991B1B; }

/* ── Horizontal rule ── */
hr { border-color: #E5E7EB; margin: 1.5rem 0; }
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
    """显示 5 阶段 Pipeline 进度条。active: -1=未开始, 0-4=当前阶段"""
    stages = [
        ("📄", "Ingest", "PDF → 文本"),
        ("🧠", "Extract", "提取 Claims"),
        ("⚡", "Compute", "Dry-run 验证"),
        ("✅", "Validate", "Schema 校验"),
        ("📦", "Export", "YAML/JSON"),
    ]
    cols = st.columns(5)
    for i, (icon, name, desc) in enumerate(stages):
        with cols[i]:
            if i < active:
                bg = "#D1FAE5" if i < 4 else "#D1FAE5"
                color = "#065F46"
            elif i == active:
                bg = "#FEF3C7"
                color = "#92400E"
            else:
                bg = "#F3F4F6"
                color = "#9CA3AF"
            st.markdown(
                f"""<div style="text-align:center;padding:0.5rem 0.25rem;
                background:{bg};border-radius:8px;">
                <div style="font-size:1.25rem;">{icon}</div>
                <div style="font-size:0.7rem;font-weight:700;color:{color};">{name}</div>
                <div style="font-size:0.6rem;color:{color};">{desc}</div>
                </div>""",
                unsafe_allow_html=True,
            )


def badge(method: str) -> str:
    """根据 extraction_method 返回 HTML badge"""
    if method == "exact_quote":
        cls, label = "claim-exact", "📎 原文"
    elif method == "llm_inferred":
        cls, label = "claim-inferred", "🤖 推断"
    else:
        cls, label = "claim-review", "⚠️ 待复核"
    return f'<span class="{cls}" style="display:inline-block;padding:2px 8px;border-radius:10px;font-size:0.7rem;font-weight:600;">{label}</span>'


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

                    # ── Dry-runs ──
                    st.markdown(f"### 🧮 Dry-run ({len(dry_runs)})")
                    if dry_runs:
                        cols = st.columns(min(len(dry_runs), 4))
                        for i, dr in enumerate(dry_runs):
                            with cols[i % len(cols)]:
                                status = dr.status.value
                                icon_map = {
                                    "passed": "✅", "mismatch": "⚠️",
                                    "insufficient_data": "❓", "calculation_error": "✗",
                                }
                                st.metric(
                                    f"{icon_map.get(status, '❌')} {dr.statement_id}",
                                    f"{dr.computed_value}" if dr.computed_value is not None else "—",
                                    delta=f"vs {dr.reported_value} ({dr.deviation_pct}%)" if dr.reported_value is not None else None,
                                )
                                st.caption(status)
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
