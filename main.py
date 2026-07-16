#!/usr/bin/env python3
"""ECS Paper-to-ARM Agent — CLI 入口

Usage:
    python main.py --paper path/to/paper.pdf
    python main.py --dir path/to/papers/
    python main.py --paper paper.pdf --output my_output/
"""

import argparse
import sys
import json
from pathlib import Path
from agents.orchestrator import Orchestrator


def main():
    parser = argparse.ArgumentParser(
        description="ECS Paper-to-ARM Agent — 将论文转化为结构化科研资产"
    )
    parser.add_argument(
        "--paper", "-p", type=str,
        help="单篇论文 PDF 路径"
    )
    parser.add_argument(
        "--dir", "-d", type=str,
        help="批量处理：论文目录路径"
    )
    parser.add_argument(
        "--search", "-s", action="store_true",
        help="搜索并下载 ECS 论文（5 类 × 3 篇）"
    )
    parser.add_argument(
        "--output", "-o", type=str, default="output",
        help="输出目录（默认: output/）"
    )
    parser.add_argument(
        "--email", type=str, default="student@example.com",
        help="PubMed API 要求的联系邮箱"
    )
    parser.add_argument(
        "--years", type=str, default="2023:2026",
        help="论文检索年份范围，格式如 '2000:2010'（默认: 2023:2026）"
    )
    parser.add_argument(
        "--no-download", action="store_true",
        help="仅搜索，不下载 PDF"
    )
    args = parser.parse_args()

    if args.search:
        _do_search(args)
        return

    if not args.paper and not args.dir:
        parser.print_help()
        print("\n请指定 --paper 或 --dir")
        sys.exit(1)

    orchestrator = Orchestrator(output_dir=args.output)

    if args.paper:
        _process_single(orchestrator, args.paper)
    elif args.dir:
        _process_batch(orchestrator, args.dir)


def _do_search(args):
    """搜索并下载 ECS 论文"""
    from tools.search_papers import search_and_download_ecs_papers

    print(f"\n{'='*60}")
    print(f"  搜索 ECS 论文（Europe PMC REST API）")
    print(f"  5 个类别 × 3 篇/类 = 最多 15 篇")
    print(f"{'='*60}\n")

    print(f"  年份范围: {args.years}")

    results = search_and_download_ecs_papers(
        output_dir=args.output or "papers",
        email=args.email,
        auto_download=not args.no_download,
        years=args.years,
    )

    print(f"找到 {len(results.papers)} 篇论文，下载 {len(results.downloaded)} 篇\n")

    for i, p in enumerate(results.papers, 1):
        oa_icon = "🔓" if p.is_open_access else "🔒"
        if p.download_source:
            dl_icon = {"europepmc": "📥PMC", "doi": "📥DOI"}.get(p.download_source, "✅")
        else:
            dl_icon = "✅" if p.has_pdf else "❌"
        print(f"{i}. {oa_icon} {dl_icon} [{p.year}] {p.title[:100]}")
        print(f"   {', '.join(p.authors[:3])}{', ...' if len(p.authors) > 3 else ''}")
        print(f"   DOI: {p.doi} | PMID: {p.pmid}")
        print()

    if results.downloaded:
        print(f"📦 已下载到 {args.output or 'papers'}/:")
        for d in results.downloaded:
            print(f"   {d}")


def _process_single(orchestrator: Orchestrator, paper_path: str):
    """处理单篇论文"""
    print(f"\n{'='*60}")
    print(f"  ECS Paper-to-ARM Agent")
    print(f"  Paper: {paper_path}")
    print(f"{'='*60}\n")

    results = orchestrator.run(paper_path)

    if "error" in results:
        print(f"❌ 错误: {results['error']}")
        sys.exit(1)

    arm = results["arm"]
    validation = results["validation"]
    dry_runs = results.get("dry_runs", [])

    # ── Summary ──
    print(f"📄 论文: {arm.metadata.title or results['paper_id']}")
    print(f"⏱️  Ingest: {results['ingest_ms']}ms | Extract: {results['extract_ms']}ms | "
          f"Compute: {results['compute_ms']}ms | Validate: {results['validate_ms']}ms")
    print()

    print(f"📊 Claims: {len(arm.claims)} 条")
    for c in arm.claims:
        method_icon = {"exact_quote": "📎", "llm_inferred": "🤖", "review_required": "⚠️"}
        icon = method_icon.get(c.extraction_method.value, "❓")
        print(f"  {icon} {c.id} [{c.extraction_method.value}] {c.text[:100]}")
    print()

    print(f"🧮 Dry-runs: {len(dry_runs)} 个")
    passed = sum(1 for d in dry_runs if d.status.value == "passed")
    failed = sum(1 for d in dry_runs if d.status.value != "passed")
    for dr in dry_runs:
        icon = "✅" if dr.status.value == "passed" else "❌"
        print(f"  {icon} {dr.statement_id}: {dr.status.value} "
              f"(computed={dr.computed_value}, reported={dr.reported_value}, "
              f"deviation={dr.deviation_pct}%)")
    print()

    print(f"🔍 Validation: {'✅ PASSED' if validation.passed else '❌ FAILED'}")
    if validation.hallucination_flags:
        print(f"  🚨 Hallucination flags: {len(validation.hallucination_flags)}")
        for hf in validation.hallucination_flags:
            print(f"     - {hf}")
    if validation.review_required_count > 0:
        print(f"  ⚠️  Review required: {validation.review_required_count}")
    if validation.claim_evidence_gaps:
        print(f"  📎 Claim-evidence gaps: {len(validation.claim_evidence_gaps)}")
    print()

    # ── Export paths ──
    print("📦 导出文件:")
    for key, path in results.get("export_paths", {}).items():
        print(f"  {key}: {path}")
    print()

    # ── Stats for PPT ──
    stats = {
        "paper": results["paper_id"],
        "claims": len(arm.claims),
        "dry_run_total": len(dry_runs),
        "dry_run_passed": passed,
        "dry_run_failed": failed,
        "validation_passed": validation.passed,
        "hallucination_count": len(validation.hallucination_flags),
        "review_required": validation.review_required_count,
    }
    print(f"📈 Stats (JSON): {json.dumps(stats, ensure_ascii=False)}")

    return stats


def _process_batch(orchestrator: Orchestrator, dir_path: str):
    """批量处理目录中的所有 PDF"""
    pdf_dir = Path(dir_path)
    pdfs = sorted(pdf_dir.glob("*.pdf"))
    if not pdfs:
        print(f"目录 {dir_path} 中没有找到 PDF 文件")
        sys.exit(1)

    all_stats = []
    for i, pdf in enumerate(pdfs, 1):
        print(f"\n[{i}/{len(pdfs)}] {pdf.name}")
        print("-" * 40)
        stats = _process_single(orchestrator, str(pdf))
        all_stats.append(stats)

    # Batch summary
    print(f"\n{'='*60}")
    print(f"  BATCH SUMMARY: {len(pdfs)} papers processed")
    print(f"{'='*60}")
    print(json.dumps(all_stats, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
