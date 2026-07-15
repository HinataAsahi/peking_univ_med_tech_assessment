"""Test Tool 4: validate_arm"""

import pytest
from schemas.arm import ARM, Claim, Evidence, ExtractionMethod, ClaimType, EvidenceType, SourceLocation
from schemas.pipeline import ParsedPaper, Page
from tools.validate_arm import validate_arm


class TestValidateArm:
    """校验规则测试"""

    def test_valid_arm_passes(self, sample_claims, sample_evidence, sample_parsed_paper):
        """完全合规的 ARM 应通过校验"""
        arm = ARM(
            claims=sample_claims,
            evidence=sample_evidence,
        )
        result = validate_arm(arm, sample_parsed_paper)

        assert result.passed is True
        assert len(result.claim_evidence_gaps) == 0

    def test_insufficient_claims_fails(self, sample_parsed_paper):
        """claims < 5 → 校验失败"""
        claim = Claim(id="C-001", text="test", source=SourceLocation(page=0))
        arm = ARM(claims=[claim], evidence=[])
        result = validate_arm(arm, sample_parsed_paper)

        assert result.schema_valid is False
        assert any("claims 数量不足" in e for e in result.schema_errors)

    def test_claim_without_evidence(self, sample_parsed_paper):
        """claim 未关联 evidence → gap"""
        claim = Claim(
            id="C-001", text="test",
            extraction_method=ExtractionMethod.EXACT_QUOTE,
            source=SourceLocation(page=1, quoted_text="volume fraction α is 0.20"),
        )
        arm = ARM(claims=[claim], evidence=[])
        result = validate_arm(arm, sample_parsed_paper)

        assert len(result.claim_evidence_gaps) > 0 or result.schema_valid is False

    def test_hallucination_detection(self, sample_parsed_paper):
        """quoted_text 不在原文中 → hallucination flag"""
        claim = Claim(
            id="C-001", text="fake claim",
            extraction_method=ExtractionMethod.EXACT_QUOTE,
            source=SourceLocation(page=1, quoted_text="THIS TEXT DOES NOT EXIST IN THE PAPER AT ALL"),
            evidence_refs=[],
        )
        arm = ARM(claims=[claim], evidence=[])
        result = validate_arm(arm, sample_parsed_paper)

        assert len(result.hallucination_flags) > 0
        assert result.passed is False

    def test_provenance_score(self, sample_claims, sample_evidence, sample_parsed_paper):
        """Provenance 覆盖率计算正确"""
        arm = ARM(claims=sample_claims, evidence=sample_evidence)
        result = validate_arm(arm, sample_parsed_paper)

        assert result.provenance_score >= 0.8  # 5 claims, all with source
