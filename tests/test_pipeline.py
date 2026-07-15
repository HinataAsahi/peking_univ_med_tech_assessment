"""端到端 Pipeline 测试"""

import pytest
from agents.orchestrator import Orchestrator


class TestOrchestrator:
    """Orchestrator 集成测试"""

    def test_error_on_missing_file(self):
        """文件不存在时返回 error"""
        orch = Orchestrator()
        result = orch.run("/nonexistent/paper.pdf")
        assert "error" in result

    def test_formula_translation(self):
        """公式转译正确"""
        from agents.orchestrator import _translate_formula
        from schemas.pipeline import NumericalStatement

        ns = NumericalStatement(
            id="N-001",
            formula_nl="λ = √(D/D*)",
            parameters={"D": 7.6e-6, "D_star": 2.9e-6},
            reported_value=1.62,
        )
        result = _translate_formula(ns)
        assert "sqrt" in result or "/" in result


class TestArmSchema:
    """ARM Schema 验证"""

    def test_arm_creation(self):
        """ARM 可以正常创建"""
        from schemas.arm import ARM, PaperMetadata

        arm = ARM(metadata=PaperMetadata(title="Test"))
        assert arm.metadata.title == "Test"
        assert len(arm.claims) == 0

    def test_claim_creation(self, sample_claims):
        """Claims 可以正常创建"""
        assert len(sample_claims) == 5
        assert sample_claims[0].id == "C-001"
        assert sample_claims[0].extraction_method.value == "exact_quote"

    def test_dry_run_result(self, sample_numerical_statement):
        """DryRunResult 创建和执行正常"""
        from tools.dry_run_calc import dry_run_calc

        result = dry_run_calc(sample_numerical_statement)
        assert result.status.value == "passed"
        assert result.computed_value is not None
