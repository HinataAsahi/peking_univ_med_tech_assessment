# ECS Paper-to-ARM Agent — 架构设计 v1

## 1. 整体分层架构

```mermaid
flowchart TB
    subgraph UI["🖥️ Streamlit Web UI"]
        U1["上传 PDF"]
        U2["查看处理进度"]
        U3["浏览 ARM 结构化结果"]
        U4["下载 YAML/JSON"]
        U5["查看运行日志"]
    end

    subgraph ORCH["🎯 Orchestrator（主控）"]
        O1["按序调用 5 个 Pipeline 阶段"]
        O2["管理全局状态"]
        O3["记录 Provenance"]
        O4["处理异常 & 错误恢复"]
    end

    subgraph PIPELINE["📊 Pipeline 阶段（纯函数，可单独测试）"]
        direction TB
        P1["1️⃣ Ingest<br/>PDF 截图 → 结构化文本 + 页码"]
        P2["2️⃣ Extract<br/>文本 → Claims + Evidence + 数值声明"]
        P3["3️⃣ Compute<br/>数值声明 → 公式提取 → 安全计算 → 对比报告"]
        P4["4️⃣ Validate<br/>Schema 完整性 + Provenance 覆盖 + review_required"]
        P5["5️⃣ Export<br/>组装 ARM YAML/JSON + 运行日志"]
    end

    subgraph TOOLS["🔧 Tools（被 Pipeline 阶段调用）"]
        T1["parse_page()"]
        T2["extract_claims()"]
        T3["dry_run_calc()"]
        T4["validate_arm()"]
    end

    UI --> ORCH
    ORCH --> PIPELINE
    P1 --> P2 --> P3 --> P4 --> P5
    P1 -.-> T1
    P2 -.-> T2
    P3 -.-> T3
    P4 -.-> T4
```

## 2. 数据流向（Pipeline 阶段细节）

```mermaid
flowchart LR
    A["📄 PDF 文件"] -->|"parse_page()"| B["📝 结构化文本<br/>+ 页码映射"]
    B -->|"extract_claims()"| C["✅ Claim 列表<br/>📎 Evidence 列表<br/>🔢 数值声明列表"]
    C -->|"dry_run_calc()"| D["🧮 Dry-run 结果<br/>✓ 通过 / ✗ 失败 / ? 无法验证"]
    D -->|"validate_arm()"| E["📋 校验报告<br/>通过项 / 缺失项 / review_required"]
    E --> F["📦 ARM 文件<br/>.yaml / .json"]
    E --> G["📜 运行日志<br/>.log"]
    F --> H["🖥️ UI 展示 & 下载"]
    G --> H
```

## 3. ARM 结构（Pydantic Schema）

```mermaid
classDiagram
    class ARM {
        +Metadata metadata
        +List~Claim~ claims
        +List~Evidence~ evidence
        +Protocol protocol
        +Runbook runbook
        +EvalPlan eval_plan
        +Provenance provenance
        +List~Limitation~ limitations
        +List~Artifact~ artifacts
    }

    class Claim {
        +str id
        +str text
        +ClaimType type
        +ClaimStatus status
        +List~EvidenceRef~ evidence_refs
    }

    class Evidence {
        +str id
        +str source_location
        +int page
        +str paragraph
        +EvidenceType type
        +str quoted_text
    }

    class RunbookStep {
        +str id
        +str action
        +str input_spec
        +str expected_output
        +bool can_dry_run
        +DryRunResult result
    }

    class Provenance {
        +str source_paper_doi
        +str extraction_date
        +str extraction_method
        +List~ProcessingStep~ steps
    }

    ARM "1" --> "5+" Claim
    ARM "1" --> "5+" Evidence
    ARM "1" --> "1" Protocol
    ARM "1" --> "1" Runbook
    ARM "1" --> "1" EvalPlan
    ARM "1" --> "1" Provenance
    ARM "1" --> "*" Limitation
    ARM "1" --> "*" Artifact
    Claim "1" --> "1..*" EvidenceRef
```

## 4. 核心设计决策

| # | 决策 | 理由 |
|---|------|------|
| 1 | 每阶段输入输出都是 **Pydantic 对象** | 接口清晰，阶段可独立单元测试 |
| 2 | **Provenance 贯穿全流程** | 每个字段记录来源页码、段落、提取方式 |
| 3 | Pipeline **确定性优先** | 同一论文两次运行结构一致；LLM 调用 temperature=0 |
| 4 | Dry-run 在**安全沙箱**中运行 | 只允许 `math` + 基础统计函数，禁止文件/网络/系统调用 |
| 5 | 提取方式三分类 | `exact_quote`（原文引用）/ `llm_inferred`（模型推断）/ `review_required`（需人工） |
| 6 | 先 Pipeline 后 Agentic | 线性流程优先确保七日交付，逻辑验证后加入 self-check 循环 |

## 5. 技术选型

| 组件 | 选择 | 原因 |
|------|------|------|
| Agent 框架 | OpenAI Agents SDK | 考核推荐，Pydantic 原生集成，tracing 内置 |
| LLM | DeepSeek V4 | 考核提供 API（100 元额度） |
| 结构化输出 | Pydantic BaseModel | SDK 原生支持 `output_type` |
| Web UI | Streamlit | 开发快，单页面上传+展示足够 |
| PDF 处理 | PyMuPDF (fitz) 文本提取 + 页码标注 | DeepSeek V4 不支持视觉；PyMuPDF 更快、更确定、零 API 成本 |
| Dry-run 沙箱 | 受限 `exec()` + 白名单内置函数 | 简单可控，无需 Docker |
| 导出格式 | YAML（人读）+ JSON（机器读） | 考核要求可导出 |
| 测试 | pytest + fixture 论文文本 | 确定性 pipeline 阶段独立可测 |
