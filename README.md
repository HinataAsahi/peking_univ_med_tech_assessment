# ECS Paper-to-ARM Agent

> 将脑细胞外间隙（ECS）研究论文转化为结构化、可验证、可追溯的 Agent-Ready Manuscript（ARM）。
>
> NEURONCLAW 2026 · Track A · 3.5 天完成

[![Python](https://img.shields.io/badge/Python-3.11-blue)](https://python.org)
[![Streamlit](https://img.shields.io/badge/Streamlit-Web%20UI-red)](https://streamlit.io)
[![DeepSeek](https://img.shields.io/badge/LLM-DeepSeek%20V4-green)](https://deepseek.com)
[![Tests](https://img.shields.io/badge/tests-15%20passed-brightgreen)](tests/)

---

## 项目概述

ECS Paper-to-ARM Agent 是一个 5 阶段流水线系统，将脑细胞外间隙研究论文自动转化为**可计算验证**的结构化知识资产。每条提取的科学结论（Claim）都包含精确的原文追溯（页码 + 引用），并可通过沙箱化的 dry-run 计算独立验证论文中的定量数据。

### 核心指标

| 指标 | 数值 |
|------|------|
| 处理论文 | 14 篇（1990–2026） |
| Claim 提取 | 87 条 |
| Dry-Run 验证 | 68 次执行，23 次通过 |
| 最佳论文 | AQP4-KO Tortuosity（5/6 passed, 83%） |
| 测试覆盖 | 15 tests, 100% pass |

### 为什么需要 ARM？

- **结论追溯困难**：传统文献阅读无法精确追溯到原文页码和引用
- **数值验证缺失**：论文报告的 α（体积分数）、λ（弯曲度）、D*（有效扩散系数）等关键参数缺乏独立计算验证
- **证据可信度未知**：无法区分论文直接陈述（exact_quote）vs 模型推断（llm_inferred）vs 需要人工复核（review_required）

---

## 架构

```
PDF → [Ingest] → [Extract] → [Compute] → [Validate] → [Export] → ARM
       PyMuPDF    DeepSeek V4  Sandbox     6-Rule       YAML/JSON
```

### 5 阶段流水线

| 阶段 | 工具 | 输入 | 输出 | 核心职责 |
|------|------|------|------|----------|
| **1. Ingest** | PyMuPDF | PDF 文件 | `ParsedPaper` | 文本提取、元数据、页码标注 |
| **2. Extract** | DeepSeek V4 | `ParsedPaper` | `ExtractionResult` | Claims、Evidence、NumericalStatements、Protocol、Limitations |
| **3. Compute** | Sandbox `exec()` | `NumericalStatement` | `DryRunResult` | 安全执行公式、计算偏差（5% 容差） |
| **4. Validate** | 6-Rule Engine | `ARM` | `ValidationReport` | Schema 校验、Hallucination 检测、Provenance 评分 |
| **5. Export** | PyYAML / JSON | 完整 ARM | `.yaml` + `.json` + `.log` | 持久化 + 日志 |

### 数据模型

所有阶段通过 Pydantic v2 类型化对象通信：

- **`Claim`** — 科学结论（text, extraction_method, source 页码/章节/原文引用, evidence_refs）
- **`Evidence`** — 支撑证据（type: text/figure/table, source_location, quoted_text）
- **`NumericalStatement`** — 数值声明（formula, parameters, reported_value, unit）
- **`DryRunResult`** — 计算结果（status: passed/mismatch/insufficient_data/calculation_error, deviation_pct）
- **`ARM`** — 最终产出（metadata, claims, evidence, protocol, runbook, eval_plan, provenance, limitations）

---

## 快速开始

### 环境要求

- Python 3.11+
- DeepSeek API Key（[获取地址](https://platform.deepseek.com)）

### 安装

```bash
git clone https://github.com/HinataAsahi/peking_univ_med_tech_assessment.git
cd peking_univ_med_tech_assessment
pip install -r requirements.txt
```

### 配置 API Key

```bash
# 方法 1：环境变量（推荐）
export DEEPSEEK_API_KEY="sk-your-key-here"

# 方法 2：写入 ~/.claude/settings.json（持久化）
# 在 env 字段中添加 "DEEPSEEK_API_KEY": "sk-your-key-here"
```

### 运行

```bash
# ① CLI — 单篇论文
python main.py --paper papers/aqp4_ko_2008.pdf

# ② CLI — 批量处理
python main.py --dir papers/

# ③ CLI — 搜索并下载 ECS 论文
python main.py --search --years "1990:2017" --output papers/broad

# ④ CLI — 仅搜索不下载（快速预览）
python main.py --search --years "1990:2017" --no-download

# ⑤ Streamlit Web UI
streamlit run app.py
```

---

## Dry-Run 验证

系统从论文中提取定量声明，在安全沙箱中执行计算，与论文报告值对比。

### 验证案例：AQP4-KO 论文

> *Aquaporin-4-deficient mice have increased extracellular space without tortuosity change* (J Neurosci, 2008)

| 验证项 | 公式 | 计算值 | 论文值 | 偏差 | 结果 |
|--------|------|--------|--------|------|------|
| α 百分比变化 | `(alpha_KO - alpha_WT) / alpha_WT * 100` | 27.78% | 28.0% | 0.79% | ✅ PASS |
| α 差值 | `alpha_KO - alpha_WT` | 0.050 | 0.050 | 0.00% | ✅ PASS |
| λ 差值 | `lambda_KO - lambda_WT` | 0.010 | 0.010 | 0.00% | ✅ PASS |
| k' 差值 | `k_prime_KO - k_prime_WT` | 0.0014 | 0.0014 | 0.00% | ✅ PASS |
| α 比值 | `alpha_KO / alpha_WT` | 1.278 | 1.28 | 0.17% | ✅ PASS |

**参数映射**：`α_KO=0.23, α_WT=0.18, λ_KO=1.62, λ_WT=1.61`

### Dry-Run 状态说明

| 状态 | 含义 |
|------|------|
| `passed` | 计算值与报告值偏差 < 5% |
| `mismatch` | 偏差 ≥ 5%，可能存在矛盾 |
| `insufficient_data` | 缺少参数或报告值 |
| `calculation_error` | 公式执行失败 |

---

## 项目结构

```
peking_univ_med_tech_assessment/
├── main.py                     # CLI 入口（--paper / --dir / --search）
├── app.py                      # Streamlit Web UI（中/英双语）
├── agents/
│   └── orchestrator.py         # Pipeline 主控制器 + ARM 组装
├── tools/
│   ├── parse_pdf.py            # Tool 1: PyMuPDF PDF 文本提取
│   ├── extract_claims.py       # Tool 2: DeepSeek V4 结构化提取
│   ├── dry_run_calc.py         # Tool 3: 安全沙箱计算验证
│   ├── validate_arm.py         # Tool 4: 6-规则验证引擎
│   └── search_papers.py        # Tool 5: Europe PMC 搜索 + PDF 下载
├── schemas/
│   ├── arm.py                  # ARM Pydantic 模型（Claim, Evidence, etc.）
│   ├── pipeline.py             # 流水线模型（ParsedPaper, DryRunResult, etc.）
│   └── validation.py           # 验证模型（ValidationReport, ReviewItem）
├── prompts/
│   └── extract_claims.md       # DeepSeek V4 系统 Prompt
├── tests/
│   ├── conftest.py             # 测试共享 fixtures
│   ├── test_dry_run_calc.py    # 5 tests — 沙箱计算
│   ├── test_validate_arm.py    # 5 tests — 验证引擎
│   └── test_pipeline.py        # 5 tests — 流水线集成
├── docs/
│   ├── literature-survey.md    # 文献调研报告（12 篇参考）
│   ├── design-*.html/md        # 设计文档（架构、pipeline、工具等）
│   └── PROJECT_BRIEF.md        # 项目简要
├── papers/                     # 下载的 PDF 论文
├── output/                     # 生成的 ARM 文件
├── requirements.txt
├── CLAUDE.md                   # Claude Code 项目指南
└── README.md
```

---

## 命令行参考

| 参数 | 说明 | 示例 |
|------|------|------|
| `--paper, -p` | 单篇论文路径 | `--paper paper.pdf` |
| `--dir, -d` | 批量处理目录 | `--dir papers/` |
| `--search, -s` | 搜索 ECS 论文 | `--search --years "1990:2017"` |
| `--output, -o` | 输出目录 | `--output my_results/` |
| `--years` | 检索年份范围 | `--years "1990:2017"` |
| `--no-download` | 仅搜索不下载 | `--search --no-download` |
| `--email` | PubMed 邮箱 | `--email user@example.com` |

---

## 关键技术决策

| 决策 | 说明 |
|------|------|
| **线性 Pipeline 架构** | 先跑通端到端流程，后续可扩展循环迭代 |
| **LLM 用 DeepSeek V4** | 通过 OpenAI SDK 兼容层调用，temperature=0 确保确定性 |
| **沙箱 exec() 执行** | 白名单（math only）+ 5s 超时，替代 subprocess 方案 |
| **逐条 try/except 解析** | 一条 Claim 解析失败不影响其他，提高整体鲁棒性 |
| **HAS_PDF:Y > OPEN_ACCESS:Y** | 搜索过滤改用 HAS_PDF，纳入 PMC Free 论文 |
| **Publisher 直链 > PMC ?pdf=render** | PMC ?pdf=render 经常 404，优先使用出版商 PDF 直链 |
| **Prompt ASCII 化** | 参数名从 `α_AQP4_KO` 改为 `alpha_KO`，公式从描述改为可执行表达式 |

---

## 测试

```bash
# 全部测试
pytest tests/ -v

# 单个模块
pytest tests/test_dry_run_calc.py -v
pytest tests/test_validate_arm.py -v
pytest tests/test_pipeline.py -v

# 覆盖率
pytest tests/ --cov=. --cov-report=term-missing
```

测试不调用实际 DeepSeek API，使用 `tests/conftest.py` 中的预构建 Pydantic 对象。

---

## 已知限制

- **PDF 文本层**：仅支持含文本层的 PDF，不支持扫描版（OCR）
- **图表提取**：不自动提取图片和表格中的数据
- **多栏排版**：复杂多栏 PDF 可能导致段落顺序混乱
- **公式覆盖**：`_translate_formula` 仅支持预定义模式 + 参数推导，复杂公式可能失败
- **DeepSeek V4**：不支持视觉输入（图片/图表）
- **PDF 下载**：出版商付费墙 403、PMC `?pdf=render` 404，已通过出版商直链 + DOI 回退缓解

---

## 许可证

本项目为 NEURONCLAW 2026 Hackathon 提交作品。
