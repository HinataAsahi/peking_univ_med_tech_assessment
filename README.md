# ECS Paper-to-ARM Agent

> 将 ECS（脑细胞外间隙）论文转化为可验证、可追溯、可回放的结构化科研资产（Agent-Ready Manuscript）。

## 快速开始

```bash
pip install -r requirements.txt
export DEEPSEEK_API_KEY="your-key"
python main.py --paper path/to/paper.pdf
```

## 项目结构

```
├── main.py              # CLI 入口
├── app.py               # Streamlit Web UI
├── agents/               # Agent 编排
├── tools/                # 4 个工具
├── schemas/              # Pydantic 数据模型
├── prompts/              # LLM 指令模板
├── fixtures/             # 测试用 fixture 数据
├── output/               # 生成的 ARM 文件
└── tests/                # pytest 测试
```

## 运行命令

```bash
# CLI 模式 — 单篇论文
python main.py --paper papers/nicholson_1998.pdf

# CLI 模式 — 批量处理
python main.py --dir papers/

# Streamlit Web UI
streamlit run app.py

# 运行测试
pytest tests/ -v
```

## 成功案例

从综述论文中提取 λ = √(D/D*) 公式，验证计算值与论文报告值一致（误差 < 5%）。

## 失败案例

1. **insufficient_data**：论文声明 α 降低 30% 但未提供基线绝对值 → review_required
2. **hallucination**：LLM 生成的 quoted_text 无法在原文中定位 → extraction_method 降级

## 已知限制

- 仅支持含文本层的 PDF（非扫描版）
- 图表内容不自动提取
- 复杂多栏排版可能段落顺序错乱
- Dry-run 仅支持数学计算验证，不执行湿实验
- DeepSeek V4 不支持视觉输入
