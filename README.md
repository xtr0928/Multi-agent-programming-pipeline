# Multi-agent Programming Pipeline（协同编码管线）

多模型协同编码管线独立仓库。2026-08-15 起与数模管线、通用工具分仓库演进：
- 数模管线 → [xtr0928/Multi-agent-mathematical-modeling](https://github.com/xtr0928/Multi-agent-mathematical-modeling)
- 通用工具/编排 → [xtr0928/Multi-Agent](https://github.com/xtr0928/Multi-Agent)
- 分家说明：`docs/pipelines-split-2026-08.md`

## 仓库结构

```
pipeline/
  coding_pipeline.py                  # 可执行管线：DS 理解需求 → GLM 设计 ∥ Qwen 视觉UI → Kimi 编码 → 并行审查 → DS 集成
  llm_client.py                       # 四模型统一接口（含 Qwen 图像输入）
  README.md                           # 管线用法
skills/
  multi-model-orchestration/          # 核心：任务分级路由 + 门禁 + 评审编排
    SKILL.md                          # 多模型编排模式与实操流程
    references/provider-model-matrix.md  # 各 provider 实测矩阵（模型/上下文/key 格式）
  hermes-model-management/            # 配套：API key 验证/连接调试
docs/
  coding_pipeline_flow.png/.html      # 四模型分工流程图（回归原始架构，视觉位=Qwen）
  qwen_coding_arch.png                # Qwen 接入编码管线架构图（纸墨风）
```

## 协同编码管线（原始四模型分工）

```
DeepSeek V4 Pro  理解需求 · 编排调度 · 汇总修复 · 集成验证
GLM 5.2          设计整体情况（架构分析）+ 代码审查
Kimi K2.7 Code   编写具体代码（逐文件）
Qwen3.8-Max      视觉与 UI 设计 + 视觉产出审查（原 Kimi K3 视觉位，成本指令）
```

可执行实现见 `pipeline/`（`python3 pipeline/coding_pipeline.py --project-dir ... --requirement ...`）。

## 版本时间线（git tag）

| tag | 内容 |
|---|---|
| `v1.0.0` | 多模型编排初版（DS 编排 / GLM 评审 / Kimi 编码分工） |
| `v1.1.0` | 接入 Qwen3.8-Max：qwen-coder 位挂 T3 长任务路由（准入三测） |
| `v1.2.0` | 视觉审查/UI 设计全迁 Qwen3.8-Max，kimi-ocr 仅剩推理审查 |

## 铁律

- 写评分离：任何模型的编码产物同过确定性门禁 + GLM 架构评审
- 门禁不认模型：编译/测试/可复现/provenance 由规则引擎判定
- 失败 ≤2 次回退 DeepSeek 接管；旧进程不杀并行对照
- 新模型接入准入三测：API 可达 → 质量 A-B 对照 → 成本 ≤ DeepSeek×1.5
