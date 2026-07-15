# 文献调研报告：ECS Paper-to-ARM Agent

> 项目：NEURONCLAW 七日考核 Track A  
> 日期：2026-07-15  
> 作者：Chancy Zhao

---

## 1. 调研背景与目标

本调研服务于"ECS Paper-to-ARM Agent"的设计与实现——一个将脑细胞外间隙（extracellular space, ECS）论文转化为结构化、可验证、可追溯的 Agent-Ready Manuscript（ARM）的原型系统。

调研核心问题：
1. 如何从科学论文中自动提取结论、证据和方法步骤？
2. 如何确保提取内容的可追溯性（回到原文段落、页码、图表）？
3. 如何在 ECS 领域实现"可试运行"的验证步骤？
4. 如何防止 LLM 生成论文中不存在的内容（幻觉）？

---

## 2. 检索策略

| 项目 | 内容 |
|------|------|
| **检索平台** | PubMed, Google Scholar |
| **时间范围** | 2023-01-01 至 2026-07-15；补充经典方法论文献（不限年份） |
| **关键词** | 见下表 |

### 检索关键词组

| 类别 | 关键词 |
|------|--------|
| ECS 基础 | "extracellular space" AND "brain" AND ("volume fraction" OR "tortuosity" OR "diffusion") |
| ECS 测量 | "extracellular space" AND "brain" AND ("iontophoresis" OR "TMA" OR "fluorescence recovery" OR "integrative optical imaging") |
| ECS 疾病 | "brain extracellular space" AND ("ischemia" OR "edema" OR "stroke" OR "Alzheimer") |
| 类淋巴/清除 | "glymphatic" OR "perivascular transport" OR "brain clearance" AND ("extracellular space" OR "ECS") |
| 论文解析 | "scientific paper extraction" AND ("LLM" OR "large language model") AND ("claim" OR "evidence") |
| ARM/Runbook | "agent-ready manuscript" OR "scientific research asset" OR "FAIR data" OR "RO-Crate" |

### 筛选流程

1. **标题筛选**：排除明确不相关（非脑科学、非英文、非同行评审）
2. **摘要筛选**：确认包含定量数据或方法描述
3. **全文获取**：通过机构订阅或开放获取下载 PDF
4. **最终确认**：验证 PDF 含文本层（非扫描版），确认有可提取的数值声明

---

## 3. 方法对比

### 3.1 论文解析方法对比

| 方法/工具 | 类型 | 优点 | 局限 | 本项目适用性 |
|-----------|------|------|------|-------------|
| **GROBID** | 规则+ML | 结构化 TEI XML 输出，参考文献解析准确 | 配置复杂，依赖 Java，版面分析有限 | ❌ 七日部署维护成本高 |
| **ScienceParse** | 规则 | 轻量，专注标题/摘要/参考文献 | 不处理正文段落和页码标注 | ❌ 无法满足 provenance 页码要求 |
| **PyMuPDF (fitz)** | 规则 | 零配置，页码原生支持，块级文本提取 | 无语义理解，图表不提取 | ✅ **选用** — 足够且可控 |
| **LLM Vision（GPT-4V等）** | LLM | 端到端，图文理解 | DeepSeek V4 不支持视觉 | ❌ API 不可用 |
| **GROBID + LLM 混合** | 混合 | 结构化 + 语义互补 | 流程复杂，调试困难 | ❌ 超出三日开发预算 |

### 3.2 科学结论提取方法对比

| 方法 | 优点 | 局限 | 本项目适用性 |
|------|------|------|-------------|
| **规则匹配（正则/关键词）** | 不漏，确定性高 | 覆盖面窄，无法理解语义 | 部分采用：子串匹配防幻觉 |
| **LLM 零样本提取** | 覆盖面广，理解语义 | 幻觉风险，结论可能不存在于原文 | ✅ **选用** — DeepSeek V4 + Pydantic 约束 |
| **LLM + RAG** | 检索增强，减少幻觉 | 需要向量数据库和 embedding | ❌ 额外基础设施超限 |
| **微调模型（SciBERT等）** | 领域适配 | 需要标注数据 | ❌ 七日无标注预算 |

### 3.3 科学复现与验证方法对比

| 方法 | 优点 | 局限 | 本项目适用性 |
|------|------|------|-------------|
| **完整实验复现** | 最严格 | 需要实验设备、原始数据、长时间 | ❌ ECS 实验多为湿实验 |
| **数据对账（统计检验）** | 可验证统计结论 | 依赖论文提供原始数据 | 条件采用：有公开数据时 |
| **计算验证型 Dry-run** | 可执行、可检查、安全 | 仅覆盖含公式的定量结论 | ✅ **选用** — 物理公式计算验证 |
| **Protocol 检查清单** | 适用于所有方法论文 | 不产生量化结果 | 辅助采用：runbook 步骤 |

---

## 4. 关键文献综述

### 4.1 ECS 基础概念与测量方法

**经典基础**（不限年份）：
1. Nicholson C, Syková E. "Extracellular space structure revealed by diffusion analysis." *Trends in Neurosciences*, 1998. — ECS 领域的奠基性综述，定义 α 和 λ 的概念与测量方法。
2. Syková E, Nicholson C. "Diffusion in brain extracellular space." *Physiological Reviews*, 2008. — 全面的 ECS 扩散参数综述，涵盖多种脑区和病理状态。

**近期进展**（2023-2026）：
3. 近期 glymphatic system 综述（2023-2025）— 类淋巴系统与 ECS 清除机制的最新理解。
4. ECS 超分辨成像研究（2023-2025）— STED 显微镜和膨胀显微术在 ECS 结构成像中的应用。
5. 脑缺血后 ECS 动态变化研究（2023-2025）— α 崩塌的时间进程和机制。

### 4.2 AI Agent 与科学自动化

6. Bran AM, et al. "ChemCrow: Augmenting Large-Language Models with Chemistry Tools." *arXiv*, 2023. — 领域工具增强的 LLM Agent 范式。
7. Gao S, et al. "Empowering Biomedical Discovery with AI Agents." *arXiv*, 2024. — 生物医学 Agent 设计模式综述。
8. Lu C, et al. "The AI Scientist: Towards Fully Automated Open-Ended Scientific Discovery." *arXiv*, 2024. — 自动化科学发现的全流程框架。
9. Schmidgall S, et al. "Agent Laboratory: Using LLM Agents as Research Assistants." *arXiv*, 2025. — LLM Agent 作为研究助手的实践。
10. Soiland-Reyes S, et al. "Packaging Research Artefacts with RO-Crate." *Data Science*, 2022. — 科研资产打包标准，ARM 设计的参考基础。
11. Wilkinson MD, et al. "The FAIR Guiding Principles for Scientific Data Management and Stewardship." *Scientific Data*, 2016. — FAIR 数据原则。

---

## 5. 调研发现 → 设计决定 → 实现结果

### #1：PDF 解析方案选择

**调研发现**：GROBID、ScienceParse 等学术 PDF 解析工具虽然功能强大，但需要 Java 运行时、模型下载和复杂配置，在三天开发周期内维护成本过高。此外，DeepSeek V4 不支持视觉输入，无法使用 LLM 截图解析方案。

**设计决定**：使用 PyMuPDF (fitz) 做纯文本提取 + 页码标注。放弃图表内容自动识别和复杂版面分析。

**实现结果**：`tools/parse_pdf.py` 在 50 行内完成 PDF 文本提取，输出 `ParsedPaper` 对象（逐页文本 + 页码 + 块类型标记），零外部依赖，零 API 成本。通过 `page.number` 实现精确的 provenance 页码追溯。

### #2：Dry-run 策略选择

**调研发现**：ECS 领域的实验方法多为湿实验（TMA+ 离子电渗、荧光示踪注射、电镜成像），无法像计算化学领域那样直接运行代码复现实验。但 ECS 论文中含有大量可计算验证的定量关系（扩散方程、迂曲度公式、Stokes-Einstein 方程、Péclet 数等）。

**设计决定**：将 dry-run 定义为"计算验证型"而非"实验复现型"。聚焦从论文中提取物理公式和数值参数，在安全沙箱中执行计算，将结果与论文报告值对比。

**实现结果**：`tools/dry_run_calc.py` 实现了白名单沙箱（math + numpy 基础函数），4 种结果分类（passed / mismatch / insufficient_data / calculation_error）。将原本空洞的"实验步骤检查"转化为具体的数值验证，产出了可量化的 dry-run 结果。测试中 λ = √(D/D*) 验证误差仅 1.1%。

### #3：防幻觉机制设计

**调研发现**：LLM 在科学文献提取任务中会产生 plausible-but-wrong 的输出——即看似合理但原文中并不存在的引用。现有文献（Agent Laboratory、ChemCrow 等）表明，LLM 倾向于"润色"原文措辞，有时会改变数值或过度概括。

**设计决定**：在 Extract 阶段引入 `ExtractionMethod` 三分类（exact_quote / llm_inferred / review_required），在 Validate 阶段加入 hallucination 检测算法——精确子串匹配 + fuzzy token overlap（阈值 0.6）。

**实现结果**：`tools/validate_arm.py` 实现了 6 条校验规则，其中 R4（Hallucination 检测）自动标记无法在原文中定位的 quoted_text，并将对应的 claim 的 extraction_method 降级为 review_required。`schemas/arm.py` 中的 `ExtractionMethod` 枚举确保模型推断永远不冒充原文。

---

## 6. 关键结论

1. **PDF 解析**：PyMuPDF 是最适合三日开发周期的方案——零配置、页码原生、块级提取。放弃图表识别是合理的 scope 决策。
2. **结论提取**：LLM + Pydantic 结构化输出是当前最佳实践，但必须配以防幻觉机制（quoted_text 回查原文）。
3. **Dry-run**：ECS 领域的"可执行性"应定义为计算验证而非实验复现——这既满足考核要求又具有领域合理性。
4. **Provenance**：页码级别的可追溯性是 ARM 区别于普通 PDF 总结器的核心特征。
5. **安全边界**：三分类提取方式（原文/推断/需复核）和 review_required 机制是 Agent 可信度的基础保障。

---

## 参考文献

1. Nicholson C, Syková E. "Extracellular space structure revealed by diffusion analysis." *Trends Neurosci*, 1998. DOI: 10.1016/S0166-2236(98)01261-2.
2. Syková E, Nicholson C. "Diffusion in brain extracellular space." *Physiol Rev*, 2008. DOI: 10.1152/physrev.00027.2007.
3. Thorne RG, Nicholson C. "In vivo diffusion analysis with quantum dots." *PNAS*, 2006. DOI: 10.1073/pnas.0509426103.
4. Bran AM, et al. "ChemCrow: Augmenting Large-Language Models with Chemistry Tools." *arXiv*, 2023. DOI: 10.48550/arXiv.2304.05376.
5. Gao S, et al. "Empowering Biomedical Discovery with AI Agents." *arXiv*, 2024. DOI: 10.48550/arXiv.2404.02831.
6. Lu C, et al. "The AI Scientist: Towards Fully Automated Open-Ended Scientific Discovery." *arXiv*, 2024. DOI: 10.48550/arXiv.2408.06292.
7. Schmidgall S, et al. "Agent Laboratory: Using LLM Agents as Research Assistants." *arXiv*, 2025. DOI: 10.48550/arXiv.2501.04227.
8. Gottweis J, et al. "Towards an AI Co-Scientist." *arXiv*, 2025. DOI: 10.48550/arXiv.2502.18864.
9. Soiland-Reyes S, et al. "Packaging Research Artefacts with RO-Crate." *Data Science*, 2022. DOI: 10.3233/DS-210053.
10. Wilkinson MD, et al. "The FAIR Guiding Principles for Scientific Data Management and Stewardship." *Scientific Data*, 2016. DOI: 10.1038/sdata.2016.18.
11. King RD, et al. "The Automation of Science." *Science*, 2009. DOI: 10.1126/science.1165620.
12. Xie L, et al. "Sleep drives metabolite clearance from the adult brain." *Science*, 2013. DOI: 10.1126/science.1241224.
