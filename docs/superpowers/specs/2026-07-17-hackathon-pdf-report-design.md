# Hackathon PDF 报告 — 设计文档

## 概述

为 NEURONCLAW Track A 提交制作一份 8 页 PDF 总结报告。

- **语言**: 中文
- **篇幅**: 8 页（简洁版）
- **格式**: HTML → Chrome headless 打印 PDF
- **核心要求**: 美观、有图表、突出协作过程、体现工作量和收获

## 技术方案

方案 A：HTML + CSS → Chrome headless `--print-to-pdf`

- 复用项目 `docs/design-*.html` 的设计风格
- 字体：Inter（标题）+ 系统无衬线（正文）+ JetBrains Mono（代码/数据）
- 配色：ECS 主题色系（深蓝 #1a365d + 青色 #0891b2 + 琥珀 #d97706）
- 图表：内嵌 SVG（流程图）+ CSS 表格 + matplotlib 生成的统计图

## 页面结构

### Page 1: 封面
- 项目名称：ECS Paper-to-ARM Agent
- Track A: Agent-Ready Manuscript
- NEURONCLAW 2026
- 一句话描述

### Page 2: 问题与方案
- 痛点：ECS 论文数量多，结论难以追溯验证
- 方案：5-Stage Pipeline 架构图（Mermaid → SVG）
- 关键指标：13 篇论文、27 dry-runs 通过、5 篇有定量验证

### Page 3: 协作与决策过程
- 时间线 + 对话节点图
- 关键决策表格：架构选择、执行规则、时间管理、检索策略、Prompt 优化、UI 迭代
- 每个决策标注：你的观点 → 采纳结果 → 影响

### Page 4: Pipeline 技术详解
- 5 阶段流程图
- 每阶段：工具、输入、输出、技术选型理由（表格）

### Page 5: Dry-Run 验证案例
- AQP4-KO 案例深入分析
- 公式展示 + 参数表格 + 验证结果
- 改进前后对比（0 passed → 5/6 passed）

### Page 6: 全量结果
- 13 篇论文统计表
- Dry-run 通过率柱状图（matplotlib → PNG）
- 最佳论文排名

### Page 7: Streamlit UI
- 界面截图
- 功能矩阵：i18n、Pipeline 可视化、搜索下载
- 技术栈

### Page 8: 收获与展望
- 技术收获
- 当前局限
- 未来方向
- 致谢 / 团队信息

## 图表清单

| 图表 | 类型 | 页 |
|------|------|----|
| Pipeline 架构图 | Mermaid SVG | 2 |
| 协作决策时间线 | CSS 时间线 + 表格 | 3 |
| 5 阶段流程图 | Mermaid SVG | 4 |
| 公式验证流程 | 手写 SVG / CSS | 5 |
| Dry-run 对比图 | matplotlib 柱状图 PNG | 6 |
| 论文统计表 | CSS 表格 | 6 |
| UI 截图 | PNG | 7 |

## 数据来源

- `output/batch_v2/` — 批量 dry-run 结果
- `output/aqp4_ko_v2/` — AQP4-KO 最佳案例
- git log — 提交记录和工作量统计
- `papers/` — 下载论文清单

## 实施步骤

1. 收集数据：运行统计脚本，汇总所有 dry-run 结果
2. 用 matplotlib 生成 dry-run 柱状图
3. 截取 Streamlit UI 截图
4. 编写 8 页 HTML
5. Chrome headless 打印 PDF
6. 交付 PDF 文件
