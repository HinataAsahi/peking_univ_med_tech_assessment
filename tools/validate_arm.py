"""Tool 4: ARM 结构化校验 — Schema + Provenance + Hallucination 检测"""

from schemas.arm import ARM, ExtractionMethod
from schemas.pipeline import ParsedPaper
from schemas.validation import ValidationReport, ReviewItem


def validate_arm(arm: ARM, paper: ParsedPaper) -> ValidationReport:
    """校验 ARM 的完整性、一致性和可追溯性。

    6 条校验规则：
    1. Schema 完整性（Pydantic 类型校验）
    2. Claim ≥ 5, Evidence ≥ 5
    3. 每条 Claim 关联 ≥ 1 Evidence
    4. Hallucination 检测（quoted_text vs 原文）
    5. Provenance 覆盖率
    6. 模型推断不冒充原文

    Args:
        arm: 待校验的 ARM 对象
        paper: 原文（用于规则 4 的文本匹配）

    Returns:
        ValidationReport: 含 passed bool + 所有违规项
    """
    report = ValidationReport(arm_id=arm.metadata.doi or "unknown")

    # ── R2: 数量下限 ──
    if len(arm.claims) < 5:
        report.schema_errors.append(f"claims 数量不足: {len(arm.claims)} < 5")
        report.schema_valid = False

    if len(arm.evidence) < 5:
        report.schema_errors.append(f"evidence 数量不足: {len(arm.evidence)} < 5")
        report.schema_valid = False

    # ── R3: Claim-Evidence 关联 ──
    evidence_ids = {e.id for e in arm.evidence}
    for claim in arm.claims:
        if not claim.evidence_refs:
            report.claim_evidence_gaps.append(f"{claim.id} 未关联任何 evidence")
        else:
            for ref in claim.evidence_refs:
                if ref not in evidence_ids:
                    report.claim_evidence_gaps.append(
                        f"{claim.id} 引用了不存在的 evidence {ref}"
                    )

    # ── R4: Hallucination 检测 ──
    paper_full = paper.raw_text
    for claim in arm.claims:
        quoted = claim.source.quoted_text
        if not quoted:
            continue
        page_num = claim.source.page
        # 找到对应页的文本
        page_text = ""
        for p in paper.pages:
            if p.number == page_num:
                page_text = p.text
                break

        # 精确匹配
        if quoted in page_text or quoted in paper_full:
            continue

        # Fuzzy 匹配：token overlap
        quoted_lower = quoted.lower()
        page_lower = page_text.lower() if page_text else paper_full.lower()
        quoted_tokens = set(quoted_lower.split())
        page_tokens = set(page_lower.split())
        if quoted_tokens:
            overlap = len(quoted_tokens & page_tokens) / len(quoted_tokens)
            if overlap < 0.6:
                report.hallucination_flags.append(
                    f"{claim.id}: quoted_text 在原文中无法匹配 "
                    f"(fuzzy overlap={overlap:.2f})"
                )
                # 降级 extraction_method
                if claim.extraction_method == ExtractionMethod.EXACT_QUOTE:
                    claim.extraction_method = ExtractionMethod.REVIEW_REQUIRED
                    report.review_items.append(ReviewItem(
                        field_path=f"claims[{claim.id}].extraction_method",
                        reason="exact_quote 降级为 review_required: quoted_text 无法在原文中定位",
                        suggestion=f"请人工核对原文第 {page_num} 页确认该结论"
                    ))

    # ── R5: Provenance 覆盖率 ──
    total_fields = len(arm.claims)
    if total_fields == 0:
        report.provenance_score = 0.0
    else:
        sourced = sum(1 for c in arm.claims if c.source.page > 0 and c.source.quoted_text)
        report.provenance_score = round(sourced / total_fields, 2)

    if report.provenance_score < 0.8:
        missing = [c.id for c in arm.claims if not c.source.quoted_text]
        report.unverified_fields = missing
        report.warnings.append(f"Provenance 覆盖率 {report.provenance_score:.0%} < 80%")

    # ── R6: 推断标记检查 ──
    for claim in arm.claims:
        if claim.extraction_method == ExtractionMethod.LLM_INFERRED:
            # 验证确实标记了 llm_inferred
            continue  # 已正确标记
        if claim.extraction_method == ExtractionMethod.EXACT_QUOTE:
            # 检查 quoted_text 非空
            if not claim.source.quoted_text:
                report.review_items.append(ReviewItem(
                    field_path=f"claims[{claim.id}].extraction_method",
                    reason="exact_quote 但 quoted_text 为空",
                    suggestion="补充原文引用或将 extraction_method 改为 llm_inferred"
                ))

    # ── 汇总 ──
    report.review_required_count = len(report.review_items)

    has_critical = (
        not report.schema_valid
        or bool(report.claim_evidence_gaps)
        or bool(report.hallucination_flags)
    )
    report.passed = not has_critical

    return report
