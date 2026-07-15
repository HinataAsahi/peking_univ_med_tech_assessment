"""ARM 核心数据结构 — Claim, Evidence, Protocol, Runbook 等"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import Literal, Optional


# ── Enums ──────────────────────────────────────────────────────

class ClaimType(str, Enum):
    EXPERIMENTAL = "experimental_result"
    COMPUTATIONAL = "computational"
    REVIEW = "review_statement"


class ClaimStatus(str, Enum):
    UNVERIFIED = "unverified"
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    PARTIAL = "partial"


class ExtractionMethod(str, Enum):
    EXACT_QUOTE = "exact_quote"          # 原文直接引用
    LLM_INFERRED = "llm_inferred"        # 模型推断/概括
    REVIEW_REQUIRED = "review_required"  # 需人工复核


class EvidenceType(str, Enum):
    TEXT = "text"
    FIGURE = "figure"
    TABLE = "table"
    SUPPLEMENTARY = "supplementary"


# ── Source Tracking ────────────────────────────────────────────

class SourceLocation(BaseModel):
    page: int
    section: str = ""
    quoted_text: str = ""
    figure_ref: Optional[str] = None
    table_ref: Optional[str] = None


class EvidenceRef(BaseModel):
    evidence_id: str
    relation: Literal["supports", "contradicts", "qualifies"] = "supports"


class ProcessingStep(BaseModel):
    stage: str
    tool: str
    timestamp: str = ""
    duration_ms: int = 0


# ── ARM Components ─────────────────────────────────────────────

class Claim(BaseModel):
    id: str  # "C-001"
    text: str
    type: ClaimType = ClaimType.REVIEW
    status: ClaimStatus = ClaimStatus.UNVERIFIED
    extraction_method: ExtractionMethod = ExtractionMethod.REVIEW_REQUIRED
    source: SourceLocation = Field(default_factory=SourceLocation)
    evidence_refs: list[str] = []


class Evidence(BaseModel):
    id: str  # "E-001"
    claim_ids: list[str] = []
    source_location: SourceLocation = Field(default_factory=SourceLocation)
    type: EvidenceType = EvidenceType.TEXT
    quoted_text: str = ""


class Protocol(BaseModel):
    summary: str = ""
    methods: list[str] = []
    instruments: list[str] = []
    subjects: str = ""


class RunbookStep(BaseModel):
    id: str  # "R-001"
    action: str
    input_spec: str = ""
    expected_output: str = ""
    can_dry_run: bool = False
    dry_run_result: Optional[dict] = None


class Runbook(BaseModel):
    steps: list[RunbookStep] = []


class EvalPlan(BaseModel):
    criteria: list[str] = []
    metrics: list[str] = []


class Provenance(BaseModel):
    source_paper_doi: str = ""
    extraction_date: str = ""
    model_version: str = "DeepSeek V4"
    processing_steps: list[ProcessingStep] = []


class Limitation(BaseModel):
    text: str
    type: Literal["paper_stated", "agent_identified"] = "agent_identified"
    source: Optional[SourceLocation] = None


class Artifact(BaseModel):
    path: str
    description: str = ""
    format: str = ""


class PaperMetadata(BaseModel):
    title: str = ""
    authors: list[str] = []
    doi: str = ""
    journal: str = ""
    year: int = 0
    abstract: str = ""
    keywords: list[str] = []


# ── ARM Top-Level ──────────────────────────────────────────────

class ARM(BaseModel):
    metadata: PaperMetadata = Field(default_factory=PaperMetadata)
    claims: list[Claim] = []
    evidence: list[Evidence] = []
    protocol: Protocol = Field(default_factory=Protocol)
    runbook: Runbook = Field(default_factory=Runbook)
    eval_plan: EvalPlan = Field(default_factory=EvalPlan)
    provenance: Provenance = Field(default_factory=Provenance)
    limitations: list[Limitation] = []
    artifacts: list[Artifact] = []
