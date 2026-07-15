"""Tool 3: 安全 Dry-run 计算沙箱"""

import math
import time
from schemas.pipeline import NumericalStatement, DryRunResult, DryRunStatus

# 白名单：允许的内置函数和模块
_ALLOWED_BUILTINS = {
    "abs": abs, "round": round,
    "min": min, "max": max,
    "sum": sum, "len": len,
    "range": range, "list": list,
    "float": float, "int": int,
    "True": True, "False": False,
    "None": None,
}

_ALLOWED_MODULES = {"math": math}

# 直接暴露常用数学函数（兼容无 math. 前缀的表达式）
_MATH_FUNCTIONS = {
    "sqrt": math.sqrt, "exp": math.exp, "log": math.log,
    "sin": math.sin, "cos": math.cos, "tan": math.tan,
    "pi": math.pi, "e": math.e,
    "pow": pow, "abs": abs, "round": round,
}

# 安全限制
_MAX_TIMEOUT_SEC = 5
_MAX_OUTPUT_LEN = 10_000


def dry_run_calc(statement: NumericalStatement, tolerance: float = 0.05) -> DryRunResult:
    """安全执行数值声明的计算验证。

    步骤：
    1. LLM 将 formula_nl 转为 Python 表达式（由 Orchestrator 在调用前完成）
    2. 将 parameters 绑定为 Python 变量
    3. 在白名单沙箱中 exec Python 表达式
    4. 与 reported_value 对比

    Args:
        statement: 从 Extract 阶段来的数值声明，需已填充 python_expr
        tolerance: 允许的相对偏差（默认 0.05 = 5%）

    Returns:
        DryRunResult: status + computed_value + deviation_pct
    """
    if not statement.parameters:
        return DryRunResult(
            statement_id=statement.id,
            status=DryRunStatus.INSUFFICIENT_DATA,
            error_message="缺少计算参数 (parameters 为空)"
        )

    if statement.reported_value is None:
        return DryRunResult(
            statement_id=statement.id,
            status=DryRunStatus.INSUFFICIENT_DATA,
            error_message="缺少论文报告值 (reported_value 为 None)"
        )

    python_expr = statement.formula_nl  # 期望已由 Orchestrator 转为 Python

    safe_globals = {
        "__builtins__": _ALLOWED_BUILTINS,
        **_ALLOWED_MODULES,
        **_MATH_FUNCTIONS,
        **statement.parameters
    }
    safe_locals: dict = {}

    start = time.time()

    try:
        result = eval(python_expr, safe_globals, safe_locals)
        elapsed_ms = int((time.time() - start) * 1000)

        if elapsed_ms > _MAX_TIMEOUT_SEC * 1000:
            return DryRunResult(
                statement_id=statement.id,
                status=DryRunStatus.CALCULATION_ERROR,
                error_message=f"执行超时 ({elapsed_ms}ms > {_MAX_TIMEOUT_SEC * 1000}ms)",
                sandbox_log=f"timeout after {elapsed_ms}ms"
            )

        computed = float(result)

    except Exception as e:
        return DryRunResult(
            statement_id=statement.id,
            status=DryRunStatus.CALCULATION_ERROR,
            error_message=f"执行失败: {type(e).__name__}: {e}",
            sandbox_log=str(e)
        )

    reported = statement.reported_value
    if reported == 0:
        deviation = abs(computed) if computed != 0 else 0.0
    else:
        deviation = abs(computed - reported) / abs(reported)

    status = DryRunStatus.PASSED if deviation <= tolerance else DryRunStatus.MISMATCH

    return DryRunResult(
        statement_id=statement.id,
        status=status,
        computed_value=computed,
        reported_value=reported,
        deviation_pct=round(deviation * 100, 2),
        python_expr=python_expr,
        sandbox_log=f"exec ok in {int((time.time() - start) * 1000)}ms"
    )
