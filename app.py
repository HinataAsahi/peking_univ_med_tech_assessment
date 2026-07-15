"""ECS Paper-to-ARM Agent — Streamlit Web UI"""

import os
import json
import tempfile
import streamlit as st
from pathlib import Path
from agents.orchestrator import Orchestrator


st.set_page_config(
    page_title="ECS Paper-to-ARM",
    page_icon="🧠",
    layout="wide",
)

st.title("🧠 ECS Paper-to-ARM Agent")
st.caption("将脑细胞外间隙（ECS）论文转化为结构化、可验证、可追溯的科研资产（Agent-Ready Manuscript）")

# ── Sidebar ──
with st.sidebar:
    st.header("⚙️ 配置")
    api_key = st.text_input(
        "DeepSeek API Key",
        value=os.environ.get("DEEPSEEK_API_KEY", ""),
        type="password",
        help="从 https://platform.deepseek.com 获取"
    )
    if api_key:
        os.environ["DEEPSEEK_API_KEY"] = api_key

    st.divider()
    st.header("📋 考核要求对标")
    st.markdown("""
    - ✅ Track A: Paper-to-ARM
    - ✅ ≥ 5 篇论文
    - ✅ 结论可追溯到原文
    - ✅ 模型推断 vs 原文区分
    - ✅ 至少 1 步 dry-run
    - ✅ 成功案例 + 失败案例
    """)

# ── Main ──
mode = st.radio("模式", ["📤 上传论文分析", "🔍 搜索并下载论文"], horizontal=True)

if mode == "🔍 搜索并下载论文":
    st.header("🔍 自动搜索 ECS 论文")
    st.caption("通过 PubMed API 搜索 5 类 ECS 论文，检查开放获取状态，自动下载 PDF")

    email = st.text_input("联系邮箱（PubMed API 要求）", value="student@example.com")
    max_papers = st.slider("每类最大论文数", 1, 5, 3)

    if st.button("🔍 开始搜索", type="primary", use_container_width=True):
        with st.spinner("搜索中（Europe PMC API，可能需要 15 秒）..."):
            from tools.search_papers import search_and_download_ecs_papers
            results = search_and_download_ecs_papers(
                output_dir="papers",
                max_per_query=max_papers,
                email=email,
                auto_download=True,
            )

        st.success(f"找到 {len(results.papers)} 篇，下载 {len(results.downloaded)} 篇")

        if results.papers:
            st.subheader("📋 搜索结果")
            for p in results.papers:
                oa = "🔓" if p.is_open_access else "🔒"
                dl = "✅" if p.has_pdf else "❌"
                st.markdown(
                    f"{oa} {dl} **[{p.year}]** {p.title}\n\n"
                    f"*{', '.join(p.authors[:3])}* | "
                    f"*{p.journal}* | DOI: `{p.doi}`"
                )
                if p.abstract:
                    with st.expander("摘要"):
                        st.caption(p.abstract[:500])

        if results.downloaded:
            st.subheader("📦 已下载文件")
            for d in results.downloaded:
                st.code(d)

    st.stop()

uploaded_files = st.file_uploader(
    "上传 ECS 论文 PDF（支持多篇）",
    type=["pdf"],
    accept_multiple_files=True,
    help="支持 2023-2026 年发表的 ECS 领域论文"
)

if uploaded_files and st.button("🚀 开始分析", type="primary", use_container_width=True):
    if not api_key:
        st.error("请先在侧边栏输入 DeepSeek API Key")
    else:
        orchestrator = Orchestrator(output_dir="output")

        all_results = []
        progress = st.progress(0, "处理中...")

        for i, uploaded in enumerate(uploaded_files):
            status_text = st.empty()
            status_text.text(f"正在处理 ({i+1}/{len(uploaded_files)}): {uploaded.name}")

            # 保存临时文件
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
                tmp.write(uploaded.read())
                tmp_path = tmp.name

            try:
                results = orchestrator.run(tmp_path)
                all_results.append(results)
            finally:
                Path(tmp_path).unlink(missing_ok=True)

            progress.progress((i + 1) / len(uploaded_files))

        progress.empty()
        status_text.empty()

        # ── Display Results ──
        st.divider()
        st.header("📊 分析结果")

        tabs = st.tabs([f"📄 {r['paper_id']}" for r in all_results])

        for tab, results in zip(tabs, all_results):
            with tab:
                if "error" in results:
                    st.error(f"❌ {results['error']}")
                    continue

                arm = results["arm"]
                validation = results["validation"]
                dry_runs = results.get("dry_runs", [])

                # Timing
                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Ingest", f"{results['ingest_ms']}ms")
                col2.metric("Extract", f"{results['extract_ms']}ms")
                col3.metric("Compute", f"{results['compute_ms']}ms")
                col4.metric("Validate", f"{results['validate_ms']}ms")

                st.divider()

                # Claims
                st.subheader(f"✅ Claims ({len(arm.claims)} 条)")
                for c in arm.claims:
                    method_icon = {"exact_quote": "📎", "llm_inferred": "🤖", "review_required": "⚠️"}
                    icon = method_icon.get(c.extraction_method.value, "❓")
                    with st.expander(f"{icon} {c.id}: {c.text[:80]}..."):
                        st.markdown(f"**结论**: {c.text}")
                        st.markdown(f"**类型**: `{c.type.value}`")
                        st.markdown(f"**提取方式**: `{c.extraction_method.value}`")
                        if c.source.page > 0:
                            st.markdown(f"**出处**: 第 {c.source.page} 页, {c.source.section}")
                            if c.source.quoted_text:
                                st.markdown(f"> {c.source.quoted_text}")
                        if c.evidence_refs:
                            st.markdown(f"**证据**: {', '.join(c.evidence_refs)}")

                st.divider()

                # Dry-runs
                st.subheader(f"🧮 Dry-run 结果 ({len(dry_runs)} 个)")
                if dry_runs:
                    cols = st.columns(min(len(dry_runs), 4))
                    for i, dr in enumerate(dry_runs):
                        col = cols[i % len(cols)]
                        status = dr.status.value
                        delta_color = "normal"
                        if status == "passed":
                            col.metric(
                                f"{'✅' if status == 'passed' else '❌'} {dr.statement_id}",
                                f"{dr.computed_value}",
                                delta=f"vs {dr.reported_value} ({dr.deviation_pct}%)",
                                delta_color="off" if status == "passed" else "inverse",
                            )
                        col.caption(f"状态: {status}")
                else:
                    st.info("该论文未提取到可计算的数值声明")

                st.divider()

                # Validation
                val_col1, val_col2 = st.columns(2)
                with val_col1:
                    status_text = "✅ PASSED" if validation.passed else "❌ FAILED"
                    st.metric("校验结果", status_text)
                    st.metric("Provenance 覆盖率", f"{validation.provenance_score:.0%}")

                with val_col2:
                    if validation.hallucination_flags:
                        st.error(f"🚨 Hallucination: {len(validation.hallucination_flags)} 条")
                        for hf in validation.hallucination_flags:
                            st.caption(hf)
                    if validation.review_required_count > 0:
                        st.warning(f"⚠️ Review Required: {validation.review_required_count}")
                    if validation.claim_evidence_gaps:
                        st.warning(f"📎 Claim-Evidence Gaps: {len(validation.claim_evidence_gaps)}")

                st.divider()

                # Download
                st.subheader("📦 下载导出")
                paths = results.get("export_paths", {})
                dl_col1, dl_col2, dl_col3, dl_col4 = st.columns(4)
                for col, (key, path) in zip([dl_col1, dl_col2, dl_col3, dl_col4], paths.items()):
                    if Path(path).exists():
                        with open(path, "r", encoding="utf-8") as f:
                            content = f.read()
                        ext = Path(path).suffix
                        mime = {
                            ".yaml": "text/yaml",
                            ".json": "application/json",
                            ".log": "text/plain",
                        }.get(ext, "text/plain")
                        col.download_button(
                            f"📥 {key.upper()}",
                            data=content,
                            file_name=f"{results['paper_id']}_{key}{ext}",
                            mime=mime,
                            use_container_width=True,
                        )

        # ── Overall Summary ──
        st.divider()
        st.header("📈 批量汇总")
        summary = []
        for results in all_results:
            if "error" in results:
                continue
            arm = results["arm"]
            drs = results.get("dry_runs", [])
            val = results["validation"]
            summary.append({
                "论文": results["paper_id"],
                "Claims": len(arm.claims),
                "Dry-runs": len(drs),
                "Passed": sum(1 for d in drs if d.status.value == "passed"),
                "Hallucination": len(val.hallucination_flags),
                "Review Required": val.review_required_count,
                "Validated": "✅" if val.passed else "❌",
            })
        st.dataframe(summary, use_container_width=True)
