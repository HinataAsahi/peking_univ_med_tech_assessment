"""Validate 阶段数据模型 — ValidationReport"""

from pydantic import BaseModel, Field


class ReviewItem(BaseModel):
    field_path: str          # "claims[3].text"
    reason: str              # "extraction_method = review_required"
    suggestion: str = ""     # 给人工复核者的建议


class ValidationReport(BaseModel):
    arm_id: str = ""
    schema_valid: bool = True
    schema_errors: list[str] = []

    provenance_score: float = 1.0   # 0.0 ~ 1.0
    unverified_fields: list[str] = []

    review_required_count: int = 0
    review_items: list[ReviewItem] = []

    claim_evidence_gaps: list[str] = []       # "C-003 缺 evidence"
    hallucination_flags: list[str] = []       # "C-005 quoted_text 不匹配"

    warnings: list[str] = []
    passed: bool = True
