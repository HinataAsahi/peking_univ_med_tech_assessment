"""Test Tool 3: dry_run_calc"""

import pytest
from schemas.pipeline import NumericalStatement, DryRunResult, DryRunStatus
from tools.dry_run_calc import dry_run_calc


class TestDryRunCalc:
    def test_passed_within_tolerance(self, sample_numerical_statement):
        """计算值与报告值在 5% 容差内 → passed"""
        result = dry_run_calc(sample_numerical_statement)

        assert result.status == DryRunStatus.PASSED
        assert result.computed_value is not None
        assert result.computed_value == pytest.approx(1.618, rel=0.01)
        assert result.deviation_pct is not None
        assert result.deviation_pct < 5.0

    def test_mismatch_outside_tolerance(self):
        """计算值与报告值偏差 > 5% → mismatch"""
        ns = NumericalStatement(
            id="N-002",
            formula_nl="D / D_star",
            parameters={"D": 7.6e-6, "D_star": 2.9e-6},
            reported_value=10.0,  # 显然不匹配
        )
        result = dry_run_calc(ns)

        assert result.status == DryRunStatus.MISMATCH
        assert result.computed_value == pytest.approx(2.62, rel=0.01)
        assert result.deviation_pct is not None
        assert result.deviation_pct > 5.0

    def test_insufficient_data_no_params(self):
        """parameters 为空 → insufficient_data"""
        ns = NumericalStatement(
            id="N-003",
            formula_nl="sqrt(D / D_star)",
            parameters={},
            reported_value=1.62,
        )
        result = dry_run_calc(ns)

        assert result.status == DryRunStatus.INSUFFICIENT_DATA

    def test_insufficient_data_no_reported(self):
        """reported_value 为 None → insufficient_data"""
        ns = NumericalStatement(
            id="N-004",
            formula_nl="sqrt(D / D_star)",
            parameters={"D": 7.6e-6, "D_star": 2.9e-6},
            reported_value=None,
        )
        result = dry_run_calc(ns)

        assert result.status == DryRunStatus.INSUFFICIENT_DATA

    def test_calculation_error_invalid_expr(self):
        """公式执行出错 → calculation_error"""
        ns = NumericalStatement(
            id="N-005",
            formula_nl="undefined_func(D)",
            parameters={"D": 7.6e-6},
            reported_value=1.0,
        )
        result = dry_run_calc(ns)

        assert result.status == DryRunStatus.CALCULATION_ERROR
        assert result.error_message is not None
