"""Tool 2: DeepSeek V4 结构化提取 Claims + Evidence + 数值声明"""

import os
from openai import OpenAI
from schemas.pipeline import ParsedPaper, ExtractionResult, NumericalStatement
from schemas.arm import (
    Claim, Evidence, Limitation, ExtractionMethod, ClaimType,
    EvidenceType, SourceLocation
)


def _load_prompt() -> str:
    """加载系统 prompt"""
    prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "extract_claims.md")
    with open(prompt_path, "r", encoding="utf-8") as f:
        return f.read()


def _build_client() -> OpenAI:
    """构建 DeepSeek API 客户端（兼容 OpenAI SDK）"""
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    if not api_key:
        raise RuntimeError("DEEPSEEK_API_KEY 环境变量未设置")
    return OpenAI(
        api_key=api_key,
        base_url="https://api.deepseek.com",
    )


def _parse_claims_from_response(response_text: str, paper: ParsedPaper) -> ExtractionResult:
    """解析 LLM 返回的 JSON，提取为 ExtractionResult。

    如果 LLM 返回的不是有效 JSON，尝试用启发式方法提取。
    """
    import json
    import re

    # 尝试直接 JSON 解析
    try:
        data = json.loads(response_text)
    except json.JSONDecodeError:
        # 尝试提取 JSON 块
        match = re.search(r'\{[\s\S]*\}', response_text)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                return ExtractionResult()
        else:
            return ExtractionResult()

    result = ExtractionResult()

    # 解析 claims
    for i, c in enumerate(data.get("claims", [])):
        method_str = c.get("extraction_method", "review_required")
        try:
            extraction_method = ExtractionMethod(method_str)
        except ValueError:
            extraction_method = ExtractionMethod.REVIEW_REQUIRED

        claim_type_str = c.get("type", "review_statement")
        try:
            claim_type = ClaimType(claim_type_str)
        except ValueError:
            claim_type = ClaimType.REVIEW

        src = c.get("source", {})
        result.claims.append(Claim(
            id=c.get("id", f"C-{i+1:03d}"),
            text=c.get("text", ""),
            type=claim_type,
            extraction_method=extraction_method,
            source=SourceLocation(
                page=src.get("page", 0),
                section=src.get("section", ""),
                quoted_text=src.get("quoted_text", ""),
                figure_ref=src.get("figure_ref"),
                table_ref=src.get("table_ref"),
            ),
            evidence_refs=c.get("evidence_refs", []),
        ))

    # 解析 evidence
    for i, e in enumerate(data.get("evidence", [])):
        ev_type_str = e.get("type", "text")
        try:
            ev_type = EvidenceType(ev_type_str)
        except ValueError:
            ev_type = EvidenceType.TEXT

        src = e.get("source", {}) if isinstance(e.get("source"), dict) else {}
        result.evidence_items.append(Evidence(
            id=e.get("id", f"E-{i+1:03d}"),
            claim_ids=e.get("claim_ids", []),
            type=ev_type,
            source_location=SourceLocation(
                page=src.get("page", 0),
                section=src.get("section", ""),
                quoted_text=src.get("quoted_text", ""),
                figure_ref=src.get("figure_ref"),
                table_ref=src.get("table_ref"),
            ),
            quoted_text=e.get("quoted_text", ""),
        ))

    # 解析 numerical_statements
    for i, ns in enumerate(data.get("numerical_statements", [])):
        result.numerical_statements.append(NumericalStatement(
            id=ns.get("id", f"N-{i+1:03d}"),
            claim_id=ns.get("claim_id", ""),
            formula_nl=ns.get("formula", ""),
            parameters=ns.get("parameters", {}),
            reported_value=ns.get("reported_value"),
            unit=ns.get("unit", ""),
            source_page=ns.get("source", {}).get("page", 0) if isinstance(ns.get("source"), dict) else 0,
            source_section=ns.get("source", {}).get("section", "") if isinstance(ns.get("source"), dict) else "",
        ))

    # 解析 protocol
    proto = data.get("protocol", {})
    if isinstance(proto, dict):
        result.protocol.summary = proto.get("summary", "")
        result.protocol.methods = proto.get("methods", [])
        result.protocol.instruments = proto.get("instruments", [])
        result.protocol.subjects = proto.get("subjects", "")

    # 解析 limitations
    for lim in data.get("limitations", []):
        if isinstance(lim, dict):
            result.limitations.append(Limitation(
                text=lim.get("text", ""),
                type=lim.get("type", "agent_identified"),
            ))

    return result


def extract_claims(paper: ParsedPaper, target_claims: int = 5) -> ExtractionResult:
    """从论文中提取科学结论、证据和数值声明。

    策略：先传前 3000 字（摘要+引言）做第一轮提取；
    如果 claims 不够 target_claims，逐章追加。

    Args:
        paper: parse_pdf 的输出
        target_claims: 最少提取的 claim 数

    Returns:
        ExtractionResult: claims, evidence, numerical_statements, protocol, limitations
    """
    client = _build_client()
    system_prompt = _load_prompt()

    # 第一轮：摘要 + 前几页
    first_pass_text = _build_first_pass(paper)
    result = _call_llm(client, system_prompt, first_pass_text, paper)

    # 如果 claims 不够，追加更多章节
    attempts = 0
    while len(result.claims) < target_claims and attempts < 2:
        attempts += 1
        extra_text = _build_extra_pass(paper, result)
        if not extra_text.strip():
            break
        extra_result = _call_llm(client, system_prompt, extra_text, paper)
        # 合并：避免重复 claims
        existing_texts = {c.text for c in result.claims}
        for c in extra_result.claims:
            if c.text not in existing_texts:
                result.claims.append(c)
                existing_texts.add(c.text)
        result.evidence_items.extend(extra_result.evidence_items)
        result.numerical_statements.extend(extra_result.numerical_statements)

    return result


def _build_first_pass(paper: ParsedPaper) -> str:
    """构建第一轮 LLM 输入：标题 + 摘要 + 前 3000 字符"""
    parts = []
    if paper.title:
        parts.append(f"Title: {paper.title}")
    # 取前几页直到 3000 字符
    total = 0
    for p in paper.pages[:5]:
        chunk = f"[Page {p.number}]\n{p.text[:1500]}\n"
        parts.append(chunk)
        total += len(chunk)
        if total > 5000:
            break
    return "\n\n".join(parts)


def _build_extra_pass(paper: ParsedPaper, existing: ExtractionResult) -> str:
    """构建追加轮 LLM 输入：未被覆盖的章节"""
    covered_pages = set()
    for c in existing.claims:
        if c.source.page > 0:
            covered_pages.add(c.source.page)

    parts = []
    for p in paper.pages:
        if p.number not in covered_pages and p.text.strip():
            parts.append(f"[Page {p.number}]\n{p.text[:2000]}")
            if len(parts) >= 3:
                break

    return "\n\n".join(parts)


def _call_llm(client: OpenAI, system_prompt: str, user_text: str, paper: ParsedPaper) -> ExtractionResult:
    """调用 DeepSeek V4，返回 ExtractionResult"""
    if not user_text.strip():
        return ExtractionResult()

    try:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text},
            ],
            temperature=0,
            max_tokens=4096,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        return _parse_claims_from_response(content, paper)
    except Exception as e:
        result = ExtractionResult()
        result.limitations.append(Limitation(
            text=f"LLM 调用失败: {e}",
            type="agent_identified",
        ))
        return result
