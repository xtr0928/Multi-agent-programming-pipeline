# Multi-agent Programming Pipeline（协同编码管线）

多模型协同编码管线独立仓库。2026-08-15 起与数模管线、通用工具分仓库演进：
- 数模管线 → [xtr0928/Multi-agent-mathematical-modeling](https://github.com/xtr0928/Multi-agent-mathematical-modeling)
- 通用工具/编排 → [xtr0928/Multi-Agent](https://github.com/xtr0928/Multi-Agent)
- 分家说明：`docs/pipelines-split-2026-08.md`

## 仓库结构

```
skills/
  multi-model-orchestration/          # 核心：任务分级路由 + 门禁 + 评审编排
    SKILL.md                          # 多模型编排模式与实操流程
    references/provider-model-matrix.md  # 各 provider 实测矩阵（模型/上下文/key 格式）
  hermes-model-management/            # 配套：API key 验证/连接调试
docs/
  qwen_coding_arch.png                # Qwen 接入编码管线架构图（纸墨风）
```

## 管线结构

```
编码需求
  → DeepSeek 编排·任务分级路由
      T1 快速修复 <30min  → kimi-coder (K2.7)
      T2 标准模块 0.5–2h  → kimi-coder (K2.7)
      T3 复杂/长时程 >2h  → qwen-coder (Qwen3.8-Max)
  → 确定性验收门禁（编译/测试/可复现/provenance，不认模型）
  → GLM 5.2 架构评审
  → 收敛判定：失败 ≤2 次 → DeepSeek 接管（旧进程不杀并行对照）
```

视觉/UI/OCR（vision_analyze、渲染检查、页面验收）= Qwen3.8-Max 视觉官（K3 视觉已退役）。

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
