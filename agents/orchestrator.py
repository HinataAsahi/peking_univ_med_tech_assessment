"""Orchestrator — Pipeline 主循环，按序调用 5 个阶段"""

import os
import time
import json
import yaml
from pathlib import Path
from datetime import datetime

from tools.parse_pdf import parse_pdf
from tools.extract_claims import extract_claims
from tools.dry_run_calc import dry_run_calc
from tools.validate_arm import validate_arm

from schemas.arm import (
    ARM, PaperMetadata, Provenance, ProcessingStep,
    Runbook, RunbookStep, EvalPlan, ExtractionMethod, DryRunStatus,
)
from schemas.pipeline import ParsedPaper, ExtractionResult, DryRunResult, NumericalStatement
from schemas.validation import ValidationReport


class Orchestrator:
    """Pipeline 主控制器"""

    def __init__(self, output_dir: str = "output"):
        self.output_dir = Path(output_dir)

    def run(self, paper_path: str) -> dict:
        """运行完整 Pipeline，返回包含 ARM + 各阶段结果的 dict"""
        paper_path = Path(paper_path)
        if not paper_path.exists():
            return {"error": f"文件不存在: {paper_path}"}

        paper_id = paper_path.stem
        results: dict = {"paper_id": paper_id, "paper_path": str(paper_path)}

        # ── Stage 1: Ingest ──
        t0 = time.time()
        try:
            parsed = parse_pdf(str(paper_path))
        except Exception as e:
            return {"error": f"Ingest 失败: {e}", "paper_id": paper_id}
        t1 = time.time()
        results["parsed"] = parsed
        results["ingest_ms"] = int((t1 - t0) * 1000)

        # ── Stage 2: Extract ──
        try:
            extraction = extract_claims(parsed)
        except Exception as e:
            return {"error": f"Extract 失败: {e}", "paper_id": paper_id, "parsed": parsed}
        t2 = time.time()
        results["extraction"] = extraction
        results["extract_ms"] = int((t2 - t1) * 1000)

        # ── Stage 3: Compute ──
        dry_runs = []
        for ns in extraction.numerical_statements:
            # 先做公式转译（简化版：直接使用 formula_nl 中可执行的表达式）
            if not ns.formula_nl.strip():
                continue
            python_expr = _translate_formula(ns)
            ns_copy = NumericalStatement(
                id=ns.id, claim_id=ns.claim_id,
                formula_nl=python_expr,
                parameters=ns.parameters,
                reported_value=ns.reported_value,
                unit=ns.unit,
                source_page=ns.source_page,
                source_section=ns.source_section,
            )
            dr = dry_run_calc(ns_copy)
            dry_runs.append(dr)
        t3 = time.time()
        results["dry_runs"] = dry_runs
        results["compute_ms"] = int((t3 - t2) * 1000)

        # ── Stage 4: Build ARM ──
        arm = _build_arm(parsed, extraction, dry_runs, paper_id, results)
        results["arm"] = arm

        # ── Stage 5: Validate ──
        validation = validate_arm(arm, parsed)
        t4 = time.time()
        results["validation"] = validation
        results["validate_ms"] = int((t4 - t3) * 1000)

        # ── Export ──
        export_paths = self._export(arm, validation, results, paper_id)
        results["export_paths"] = export_paths

        return results

    def _export(self, arm: ARM, validation: ValidationReport, results: dict, paper_id: str) -> dict:
        """导出 ARM YAML/JSON + Run Log + Validation Report"""
        out_dir = self.output_dir / paper_id
        out_dir.mkdir(parents=True, exist_ok=True)

        paths = {}

        # ARM YAML
        yaml_path = out_dir / "arm.yaml"
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(arm.model_dump(), f, allow_unicode=True, default_flow_style=False)
        paths["yaml"] = str(yaml_path)

        # ARM JSON
        json_path = out_dir / "arm.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(arm.model_dump(), f, ensure_ascii=False, indent=2)
        paths["json"] = str(json_path)

        # Validation
        val_path = out_dir / "validation.json"
        with open(val_path, "w", encoding="utf-8") as f:
            json.dump(validation.model_dump(), f, ensure_ascii=False, indent=2)
        paths["validation"] = str(val_path)

        # Run Log
        log_lines = [
            f"=== ECS Paper-to-ARM Run Log ===",
            f"Paper: {paper_id}",
            f"Date: {datetime.now().isoformat()}",
            f"",
            f"--- Timing ---",
            f"Ingest: {results.get('ingest_ms', '?')}ms",
            f"Extract: {results.get('extract_ms', '?')}ms",
            f"Compute: {results.get('compute_ms', '?')}ms",
            f"Validate: {results.get('validate_ms', '?')}ms",
            f"",
            f"--- Claims ---",
        ]
        for c in arm.claims:
            log_lines.append(f"  {c.id}: [{c.extraction_method.value}] {c.text[:80]}...")
        log_lines.append(f"")
        log_lines.append(f"--- Dry-runs ---")
        for dr in results.get("dry_runs", []):
            log_lines.append(f"  {dr.statement_id}: {dr.status.value} (computed={dr.computed_value}, reported={dr.reported_value})")
        log_lines.append(f"")
        log_lines.append(f"--- Validation ---")
        log_lines.append(f"  Passed: {validation.passed}")
        log_lines.append(f"  Hallucination flags: {len(validation.hallucination_flags)}")
        log_lines.append(f"  Review required: {validation.review_required_count}")

        log_path = out_dir / "run.log"
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(log_lines))
        paths["log"] = str(log_path)

        return paths


def _build_arm(
    parsed: ParsedPaper,
    extraction: ExtractionResult,
    dry_runs: list[DryRunResult],
    paper_id: str,
    results: dict,
) -> ARM:
    """组装 ARM 对象"""

    # 将 dry-run 结果关联到 claims
    for claim in extraction.claims:
        for dr in dry_runs:
            ns = next((n for n in extraction.numerical_statements if n.id == dr.statement_id), None)
            if ns and ns.claim_id == claim.id:
                if dr.status == DryRunStatus.PASSED:
                    claim.status = "supported"
                elif dr.status == DryRunStatus.MISMATCH:
                    claim.status = "contradicted"
                elif dr.status in (DryRunStatus.INSUFFICIENT_DATA, DryRunStatus.CALCULATION_ERROR):
                    claim.extraction_method = ExtractionMethod.REVIEW_REQUIRED

    # 构建 runbook
    runbook_steps = []
    for i, ns in enumerate(extraction.numerical_statements):
        dr = next((d for d in dry_runs if d.statement_id == ns.id), None)
        runbook_steps.append(RunbookStep(
            id=f"R-{i+1:03d}",
            action=f"验证 {ns.formula_nl}",
            input_spec=f"参数: {ns.parameters}",
            expected_output=f"预期值: {ns.reported_value} {ns.unit}",
            can_dry_run=bool(ns.parameters and ns.reported_value is not None),
            dry_run_result=dr.model_dump() if dr else None,
        ))

    return ARM(
        metadata=PaperMetadata(
            title=parsed.title or paper_id,
            doi=parsed.metadata.get("doi", ""),
            year=parsed.metadata.get("year", 0),
            authors=parsed.metadata.get("authors", []),
        ),
        claims=extraction.claims,
        evidence=extraction.evidence_items,
        protocol=extraction.protocol,
        runbook=Runbook(steps=runbook_steps),
        eval_plan=EvalPlan(
            criteria=["每条 claim 可追溯到原文", "dry-run 通过率", "无 hallucination"],
            metrics=["provenance_score", "dry_run_passed_count", "hallucination_count"],
        ),
        provenance=Provenance(
            source_paper_doi=parsed.metadata.get("doi", ""),
            extraction_date=datetime.now().isoformat(),
            model_version="DeepSeek V4",
            processing_steps=[
                ProcessingStep(stage="ingest", tool="parse_pdf", duration_ms=results.get("ingest_ms", 0)),
                ProcessingStep(stage="extract", tool="extract_claims", duration_ms=results.get("extract_ms", 0)),
                ProcessingStep(stage="compute", tool="dry_run_calc", duration_ms=results.get("compute_ms", 0)),
                ProcessingStep(stage="validate", tool="validate_arm", duration_ms=results.get("validate_ms", 0)),
            ],
        ),
        limitations=extraction.limitations,
    )


def _translate_formula(ns: NumericalStatement) -> str:
    """将自然语言公式转为 Python 表达式（简化版映射）"""
    formula = ns.formula_nl.strip()

    # 常见公式映射
    mappings = {
        "λ = √(D/D*)": "sqrt(D / D_star)",
        "λ² = D/D*": "D / D_star",
        "D* = D/λ²": "D / (lambda_val ** 2)",
        "D = kT/(6πηr)": "k * T / (6 * pi * eta * r)",
        "Pe = v·L/D*": "v * L / D_star",
    }

    # 精确匹配
    for nl, py in mappings.items():
        if nl.lower().replace(" ", "") == formula.lower().replace(" ", ""):
            return py

    # 如果 formula_nl 本身已经是 Python 表达式
    if any(op in formula for op in ["sqrt", "**", "*", "/", "+", "-"]):
        # 替换常见符号
        formula = formula.replace("×", "*").replace("·", "*").replace("÷", "/")
        return formula

    return formula
