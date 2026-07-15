"""Pipeline 阶段数据模型 — Ingest / Extract / Compute 的输入输出"""

from pydantic import BaseModel, Field
from typing import Literal, Optional
from enum import Enum
from .arm import Claim, Evidence, Protocol, Limitation


# ── Stage 1: Ingest ────────────────────────────────────────────

class TextBlock(BaseModel):
    text: str
    bbox: tuple[float, float, float, float] = (0, 0, 0, 0)
    block_type: Literal["text", "image", "table"] = "text"


class Page(BaseModel):
    number: int
    text: str = ""
    blocks: list[TextBlock] = []


class ParsedPaper(BaseModel):
    title: str = ""
    pages: list[Page] = []
    metadata: dict = Field(default_factory=dict)
    raw_text: str = ""

    @property
    def full_text(self) -> str:
        return "\n\n".join(f"[Page {p.number}]\n{p.text}" for p in self.pages)


# ── Stage 2: Extract ───────────────────────────────────────────

class NumericalStatement(BaseModel):
    id: str  # "N-001"
    claim_id: str = ""
    formula_nl: str = ""                # 自然语言公式
    parameters: dict[str, float] = Field(default_factory=dict)
    reported_value: Optional[float] = None
    unit: str = ""
    source_page: int = 0
    source_section: str = ""


class ExtractionResult(BaseModel):
    claims: list[Claim] = []
    evidence_items: list[Evidence] = []
    numerical_statements: list[NumericalStatement] = []
    protocol: Protocol = Field(default_factory=Protocol)
    limitations: list[Limitation] = []


# ── Stage 3: Compute ───────────────────────────────────────────

class DryRunStatus(str, Enum):
    PASSED = "passed"
    MISMATCH = "mismatch"
    INSUFFICIENT_DATA = "insufficient_data"
    CALCULATION_ERROR = "calculation_error"


class DryRunResult(BaseModel):
    statement_id: str
    status: DryRunStatus = DryRunStatus.CALCULATION_ERROR
    computed_value: Optional[float] = None
    reported_value: Optional[float] = None
    deviation_pct: Optional[float] = None
    python_expr: str = ""
    error_message: Optional[str] = None
    sandbox_log: str = ""
