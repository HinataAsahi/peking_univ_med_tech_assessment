# 第二节：论文选择策略与 Dry-run 计算设计

## 0. 变更记录

| 日期 | 变更 | 原因 |
|------|------|------|
| 7/15 | PDF 解析从"LLM 截图"改为"PyMuPDF 文本提取" | DeepSeek V4 不支持视觉输入 |
| 7/15 | 论文时效约束从"不限"改为"2023-2026 优先" | 考核文献调研要求展示检索策略和时效性 |

---

## 1. PDF 输入方案（更新）

### 主方案：PyMuPDF (fitz)

```
PDF → PyMuPDF 文本提取 → 带页码标记的结构化文本 → 进入 Extract 阶段
```

- 零 API 成本，确定性行为
- 原生页码标注（`page.number`）
- 按段落/块提取，保留大致阅读顺序
- 单栏 PDF 准确率高，双栏需额外处理

### 限制（已知，不设为必达目标）

- 图表内容不提取（仅记录位置：`Figure 3 at page 5`）
- 复杂排版（三栏、大量浮动元素）可能段落顺序错乱
- 数学公式提取不完整（依赖论文中是否有 Unicode 表达或 LaTeX 源码）

### 工具接口

```python
# tools/pdf_parser.py
def parse_pdf(file_path: str) -> ParsedPaper:
    """返回带页码标注的结构化文本"""
    return ParsedPaper(
        pages=[
            Page(number=1, text="..."),
            Page(number=2, text="..."),
        ],
        metadata={"title": "...", "authors": "..."}
    )
```

---

## 2. 论文选择策略（更新）

### 选题标准（6 条约束，4 硬 + 2 软）

| # | 约束 | 类型 | 说明 |
|---|------|------|------|
| **C1** | **时效性** | **硬（新增）** | 优先 2023-2026 年发表；如某子主题无近期论文，允许 1 篇 2020+ 经典方法论文 |
| **C2** | 包含**定量数据** | 硬 | 每篇至少有 1-2 个可提取的数值：α、λ、D*、清除率、浓度变化等 |
| **C3** | 覆盖 **ECS 学习目标** | 硬 | 5 篇分散在不同子主题，不重复覆盖同一知识点 |
| **C4** | **可获取全文 PDF** | 硬 | 开源优先，机构订阅其次；7 天内能下载 |
| **C5** | 多样性 | 软 | 综述 1 + 方法学 2 + 疾病关联 2 |
| **C6** | 权威性 | 软 | PubMed 索引、有 DOI、优先高引用期刊 |

### 检索策略（文献调研报告素材）

```
检索平台：PubMed, Google Scholar
关键词：
  - "extracellular space" AND "brain" AND ("volume fraction" OR "tortuosity")
  - "ECS" AND ("diffusion" OR "iontophoresis" OR "fluorescence recovery")
  - "glymphatic" AND ("clearance" OR "perivascular")
  - "brain extracellular space" AND ("ischemia" OR "edema" OR "Alzheimer")
时间范围：2023-01-01 至 2026-07-15
筛选流程：标题筛选 → 摘要筛选（确认含定量数据）→ 全文获取 → 最终确认
预期命中：每类 3-5 篇候选 → 各选 1 篇
```

### 5 篇候选论文分类（确认中，由 deep-research agent 搜索后确定最终 DOI）

#### 论文 1：综述类 — ECS 结构与生理

| 项目 | 内容 |
|------|------|
| **搜索词** | brain extracellular space review volume fraction tortuosity 2023 2024 2025 |
| **预期来源** | Physiological Reviews / Nature Reviews Neuroscience / Trends in Neurosciences |
| **覆盖目标** | ECS 定义、α 概念、λ 概念、测量方法总览 |
| **定量要求** | 包含 α 和 λ 在不同脑区的典型值表 |
| **计算验证** | λ = √(D/D*) 定义式；α 在不同脑区的对比 |

```
计算示例：
  输入：D_free = 7.6×10⁻⁶ cm²/s, λ = 1.6
  计算：D* = D_free / λ² = 2.97×10⁻⁶ cm²/s
  对比：论文报告值 ≈ 2.9×10⁻⁶ → ✓ 通过（误差 2.4%）
```

#### 论文 2：方法学类 — ECS 扩散参数测量

| 项目 | 内容 |
|------|------|
| **搜索词** | ECS diffusion measurement iontophoresis integrative optical imaging FRAP 2023 2024 |
| **预期来源** | Journal of Neuroscience Methods / NeuroImage / eLife |
| **覆盖目标** | ECS 测量方法、示踪剂、扩散方程应用 |
| **定量要求** | 包含浓度-时间数据或可拟合的扩散参数 |
| **计算验证** | 扩散方程拟合；α 和 λ 的交叉验证 |

```
计算示例：
  模型：C(t) = (Q/α)·(4πD*t)^(-3/2)·exp(-r²/4D*t - k't)
  输入：从论文表格提取的浓度-时间数据点
  拟合：最小二乘法 → α_fitted, λ_fitted
  对比：α_fitted vs α_reported, λ_fitted vs λ_reported
```

#### 论文 3：方法学/成像类 — ECS 结构成像

| 项目 | 内容 |
|------|------|
| **搜索词** | brain ECS imaging super-resolution microscopy two-photon tracer diffusion 2023 2024 2025 |
| **预期来源** | Nature Communications / Science Advances / eLife |
| **覆盖目标** | ECS 成像方法、示踪剂尺寸与扩散关系 |
| **定量要求** | 包含扩散系数或 tracer 分布数据 |
| **计算验证** | Stokes-Einstein 方程：D = kT/(6πηr)；示踪剂半径 vs 扩散系数 |

```
计算示例：
  输入：T=310K, η=0.001 Pa·s, r=10nm
  计算：D_pred = kT/(6πηr) = 2.27×10⁻¹¹ m²/s
  实测：ECS 中 D_eff ≈ 2.0×10⁻¹² m²/s
  结论：D_eff << D_pred → ECS 几何约束显著 ✓
```

#### 论文 4：疾病关联类 — ECS 与脑水肿/缺血

| 项目 | 内容 |
|------|------|
| **搜索词** | brain extracellular space ischemia edema volume fraction change 2023 2024 2025 |
| **预期来源** | Stroke / Journal of Cerebral Blood Flow & Metabolism / Brain |
| **覆盖目标** | ECS 与脑水肿、脑缺血的病理关联 |
| **定量要求** | 包含正常 vs 病理状态的 α 或扩散参数对比 |
| **计算验证** | 扩散时间在不同 α 下的变化；病理条件下的 D* 估算 |

```
计算示例：
  输入：扩散距离 x=100μm, D*_normal = 2.0×10⁻⁶ cm²/s
  正常：t = x²/(2D*) = 25s
  缺血：α 崩塌 → D*_eff 下降 3 倍 → t = 75s
  结论：扩散延迟 3 倍，与论文描述一致 ✓
```

#### 论文 5：清除/递送类 — 类淋巴系统与 ECS 转运

| 项目 | 内容 |
|------|------|
| **搜索词** | glymphatic brain clearance perivascular transport ECS drug delivery 2023 2024 2025 |
| **预期来源** | Science / Nature / Nature Neuroscience / Cell |
| **覆盖目标** | ECS 与脑内清除、药物递送 |
| **定量要求** | 包含清除率、半衰期或 Péclet 数计算所需参数 |
| **计算验证** | Péclet 数（对流 vs 扩散主导）；清除半衰期与扩散参数的关系 |

```
计算示例：
  输入：D* = 5×10⁻⁷ cm²/s, v = 10 μm/min, L = 100 μm
  计算：Pe = v·L/D* = 0.33
  结论：Pe < 1 → 扩散主导清除（非对流），与论文一致 ✓
```

### 学习目标覆盖矩阵

| 学习目标 | 综述 | 方法学1 | 成像 | 水肿 | 清除 |
|----------|:----:|:----:|:----:|:----:|:----:|
| ECS 定义与组成 | ● | ○ | | | |
| α（体积分数） | ● | ● | | ● | |
| λ（迂曲度） | ● | ● | | | |
| 扩散与物质运输 | ● | ● | ● | | ● |
| 测量/示踪/成像 | ○ | ● | ● | | |
| 脑水肿/缺血 | | | | ● | |
| 药物递送/清除 | | | | | ● |

> ● 主题核心  ○ 相关内容

---

## 3. Dry-run 沙箱设计（不变）

### 安全边界

- **允许**：算术运算、math 模块、numpy 基础函数（mean/std/sum/array/linspace）
- **禁止**：文件读写、网络请求、系统调用、未白名单模块导入、嵌套 eval/exec
- **强制限制**：超时 5s、内存 100MB、输出 10KB

### 执行流程（4 步）

1. **公式解析**：LLM 将自然语言公式转为 Python 表达式
2. **参数绑定**：论文参数名映射到 Python 变量
3. **安全执行**：在白名单沙箱中 exec
4. **结果对比**：容差 5%，输出 passed/mismatch/insufficient_data/calculation_error

### 四种结果

| 结果 | 触发条件 | 演示用途 |
|------|----------|----------|
| `passed` | 计算值与论文报告值在容差内一致 | **成功案例** |
| `mismatch` | 计算值与论文报告值偏离超过容差 | 失败案例：数值对不上 |
| `insufficient_data` | 论文声明了结论但缺少计算参数 | 失败案例：→ review_required |
| `calculation_error` | 公式无法解析或执行出错 | 失败案例：解析失败 |

---

## 4. 成功与失败案例设计（不变）

### 成功案例

场景：从综述论文中提取 λ = √(D/D*) 关系并验证。

论文原文 → Extract claim → 识别公式 → Dry-run 计算 → 结果一致 (误差 < 5%) → passed

### 失败案例

场景：疾病论文声明了 α 的相对变化但未报告绝对值。

论文原文 → Extract claim → 尝试计算 → 缺少参数 → insufficient_data → review_required
