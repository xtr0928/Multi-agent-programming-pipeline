# Multi-agent Programming Pipeline

> **一句话：让四个大模型各干自己最擅长的事——你给一句需求，它流水线式产出「设计 → 代码 → 审查 → 修复」后的完整可运行项目。**

这是一个**多模型协同编码管线**：不再让单个模型包办一切，而是把一次软件开发拆成设计、编码、审查、集成四个环节，分别交给四个不同模型家族的模型，用交叉审查补单模型的盲区，最后交回一个验证过的成品。

```
DeepSeek V4 Pro   理解需求 · 编排调度 · 汇总修复 · 集成验证
GLM 5.2           设计整体架构（文件清单+逐文件规格）· 代码审查
Kimi K2.7 Code    编写具体代码（逐文件）
Qwen3.8-Max       视觉与 UI 设计 · 视觉产出审查（截图级）
```

## 一张图看懂

![协同编码管线流程图](docs/coding_pipeline_flow.png)

## 怎么工作的（5 阶段）

| 阶段 | 谁 | 做什么 | 产出 |
|---|---|---|---|
| Phase 0 | DeepSeek | 理解需求、定边界、判定是否含视觉产出 | `requirements.md` |
| Phase 1 | GLM ∥ Qwen（并行） | GLM 设计整体架构（每个文件写什么、接口是什么）；Qwen 出视觉与 UI 规格 | `design.md` + `visual_spec.md` |
| Phase 2 | Kimi coder | 按 GLM 的清单逐文件写代码，独立文件并行、有依赖串行 | 项目代码 |
| Phase 3 | GLM ∥ Qwen（并行） | GLM 对照规格审代码；Qwen 把页面渲染成截图逐像素审视觉 | 两份审查报告 |
| Phase 4 | DeepSeek | 汇总问题、重写修复被标记的文件、出交付报告 | 修复后的代码 + `final_report.md` |

核心原则只有三条：**设计的不写码，写码的不自审，审视觉的做视觉设计**——三个环节互相交叉，谁的问题都会被下一环看到。

## 快速开始

```bash
git clone git@github.com:xtr0928/Multi-agent-programming-pipeline.git
cd Multi-agent-programming-pipeline

# 配置四个模型的 API key（或写入 pipeline/.env，已 gitignore）
export DEEPSEEK_API_KEY=... GLM_API_KEY=... KIMI_API_KEY=... QWEN_API_KEY=...

# 一条命令出项目
python3 pipeline/coding_pipeline.py \
  --project-dir ./my_project \
  --requirement "做一个xxx：……（功能、技术栈、边界）"
```

产物：代码写在 `my_project/` 下，全过程中间产物（需求/设计/审查/交付报告）在 `my_project/pipeline_artifacts/`。

> 什么时候**不**用管线：单文件小改、CRUD、用户催着要结果——直接自己写（solo）更快更省。管线是给「多文件、有前端、值得走一遍设计」的任务准备的。

## 仓库结构

```
pipeline/
  coding_pipeline.py            # 主流程（5 阶段编排）
  llm_client.py                 # 四模型统一接口（含 Qwen 图像输入、重试、推理预算）
  ARCHITECTURE.md               # 架构与技术要点详细文档（必读）
  README.md                     # 管线用法速查
skills/
  multi-model-orchestration/    # 多模型编排方法论（SKILL + provider 实测矩阵）
  hermes-model-management/      # API key 验证/连接调试
docs/
  coding_pipeline_flow.png      # 四模型分工流程图（本 README 所嵌）
  pipelines-split-2026-08.md    # 三仓库分家说明（数模/编码/通用工具）
  qwen_coding_arch.png          # 历史：Qwen 接入编码管线设计图
```

## 演进时间线

| tag | 里程碑 |
|---|---|
| `v1.0.0` | 多模型编排初版（DS 编排 / GLM 设计评审 / Kimi 编码分工） |
| `v1.1.0` | 接入 Qwen3.8-Max：长任务编码位（准入三测通过） |
| `v1.2.0` | 视觉/UI 全迁 Qwen3.8-Max（Kimi K3 视觉位退役，成本指令） |
| `main` | 可执行管线落地：五阶段实现 + 四模型接口 + 详细架构文档 |

## 相关仓库

- 数模管线（MCM 竞赛解题）→ [Multi-agent-mathematical-modeling](https://github.com/xtr0928/Multi-agent-mathematical-modeling)
- 通用工具与编排 → [Multi-Agent](https://github.com/xtr0928/Multi-Agent)
