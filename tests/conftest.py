"""共享 fixtures"""

import pytest
from schemas.pipeline import ParsedPaper, Page, NumericalStatement
from schemas.arm import (
    ARM, Claim, Evidence, PaperMetadata, SourceLocation,
    ExtractionMethod, ClaimType, EvidenceType,
)


@pytest.fixture
def sample_parsed_paper() -> ParsedPaper:
    """构造一个简单的 ParsedPaper fixture"""
    return ParsedPaper(
        title="Test ECS Paper",
        pages=[
            Page(number=1, text="The volume fraction α is 0.20 in cortex."),
            Page(number=2, text="The tortuosity λ was found to be 1.6, with D=7.6e-6 and D*=2.9e-6."),
            Page(number=3, text="Following ischemia, α decreased to 30% of baseline."),
        ],
        metadata={"title": "Test ECS Paper", "author": "Test Author", "page_count": 3},
        raw_text="[Page 1]\nThe volume fraction α is 0.20 in cortex.\n\n[Page 2]\nThe tortuosity λ was found to be 1.6, with D=7.6e-6 and D*=2.9e-6.\n\n[Page 3]\nFollowing ischemia, α decreased to 30% of baseline.",
    )


@pytest.fixture
def sample_claims() -> list[Claim]:
    """构造 5 条测试 claims"""
    return [
        Claim(
            id="C-001",
            text="皮层 α ≈ 0.20",
            type=ClaimType.REVIEW,
            extraction_method=ExtractionMethod.EXACT_QUOTE,
            source=SourceLocation(page=1, section="Results", quoted_text="volume fraction α is 0.20 in cortex"),
            evidence_refs=["E-001"],
        ),
        Claim(
            id="C-002",
            text="皮层 λ ≈ 1.6",
            type=ClaimType.EXPERIMENTAL,
            extraction_method=ExtractionMethod.EXACT_QUOTE,
            source=SourceLocation(page=2, section="Results", quoted_text="tortuosity λ was found to be 1.6"),
            evidence_refs=["E-002"],
        ),
        Claim(
            id="C-003",
            text="D = 7.6×10⁻⁶ cm²/s, D* = 2.9×10⁻⁶ cm²/s",
            type=ClaimType.EXPERIMENTAL,
            extraction_method=ExtractionMethod.EXACT_QUOTE,
            source=SourceLocation(page=2, section="Results", quoted_text="D=7.6e-6 and D*=2.9e-6"),
            evidence_refs=["E-002"],
        ),
        Claim(
            id="C-004",
            text="缺血后 α 降至基线 30%",
            type=ClaimType.EXPERIMENTAL,
            extraction_method=ExtractionMethod.LLM_INFERRED,
            source=SourceLocation(page=3, section="Discussion", quoted_text="α decreased to 30% of baseline"),
            evidence_refs=["E-003"],
        ),
        Claim(
            id="C-005",
            text="ECS 在药物递送中发挥关键作用",
            type=ClaimType.REVIEW,
            extraction_method=ExtractionMethod.LLM_INFERRED,
            source=SourceLocation(page=3, section="Discussion", quoted_text="α decreased to 30% of baseline"),
            evidence_refs=["E-005"],
        ),
    ]


@pytest.fixture
def sample_evidence() -> list[Evidence]:
    """构造 5 条测试 evidence"""
    return [
        Evidence(id="E-001", claim_ids=["C-001"], type=EvidenceType.TEXT, quoted_text="volume fraction α is 0.20 in cortex"),
        Evidence(id="E-002", claim_ids=["C-002", "C-003"], type=EvidenceType.TEXT, quoted_text="tortuosity λ was found to be 1.6, with D=7.6e-6 and D*=2.9e-6"),
        Evidence(id="E-003", claim_ids=["C-004"], type=EvidenceType.TEXT, quoted_text="α decreased to 30% of baseline"),
        Evidence(id="E-004", claim_ids=["C-001"], type=EvidenceType.FIGURE, quoted_text=""),
        Evidence(id="E-005", claim_ids=["C-002"], type=EvidenceType.TABLE, quoted_text=""),
    ]


@pytest.fixture
def sample_numerical_statement() -> NumericalStatement:
    """构造一个数值声明 fixture"""
    return NumericalStatement(
        id="N-001",
        claim_id="C-002",
        formula_nl="sqrt(D / D_star)",
        parameters={"D": 7.6e-6, "D_star": 2.9e-6},
        reported_value=1.62,
        unit="",
        source_page=2,
        source_section="Results",
    )
