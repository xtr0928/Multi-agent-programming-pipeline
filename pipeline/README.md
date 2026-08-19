# 协同编码管线（可执行）

回归原始四模型分工架构的实现（**完整架构与技术要点见 [ARCHITECTURE.md](ARCHITECTURE.md)**）。

两段式流程：**规划阶段**（`planning.py`：需求澄清 → 开源调研 → 技术选型由用户拍板 → 设计文档由用户确认）→ **执行阶段**（`coding_pipeline.py`：四模型编码）。

```bash
# 规划阶段（每步产物停下来等用户决策）
python3 pipeline/planning.py research --project-dir ./proj --requirement "做一个xxx"
python3 pipeline/planning.py options  --project-dir ./proj     # 用户按 tech_options.md 选择 → 编排者写 choices_final.json
python3 pipeline/planning.py design   --project-dir ./proj     # 用户确认 design_doc.md
python3 pipeline/planning.py build    --project-dir ./proj     # 进入执行阶段

# 或跳过规划直接执行（仅需求非常明确时）
python3 pipeline/coding_pipeline.py --project-dir ./proj --requirement "……" \
  [--design-context @已确认设计文档.md]
```

执行阶段四模型分工：

```
DeepSeek V4 Pro  理解需求 · 编排调度 · 汇总修复 · 集成验证
GLM 5.3          设计整体情况（架构分析）+ 代码审查
Kimi K2.7 Code   编写具体代码（逐文件）
Qwen3.8-Max      视觉与 UI 设计 + 视觉产出审查（原 Kimi K3 视觉位）
```

## 使用

```bash
# 环境变量（或在本目录放 .env，已 gitignore）
export DEEPSEEK_API_KEY=... GLM_API_KEY=... KIMI_API_KEY=... QWEN_API_KEY=...

python3 pipeline/coding_pipeline.py \
  --project-dir ./demo \
  --requirement "制作一个学生成绩统计示例：utils.py 计算均值/中位数/及格率，index.html 静态页面展示"
```

需求也可以从文件读：`--requirement @req.txt`

## 流程

| Phase | 执行者 | 产出 |
|---|---|---|
| 0 | DeepSeek | `pipeline_artifacts/requirements.md`（含 VISUAL: yes/no 判定） |
| 1 | GLM ∥ Qwen | `design.md`（文件清单逐文件规格）· `visual_spec.md`（含视觉产出时） |
| 2 | Kimi coder | 按 GLM 清单逐文件写码，落盘到项目目录；`## GROUP` 标注的文件并行编写 |
| 3 | GLM ∥ Qwen | `review_code.md` · `review_visual.md`（html/svg 用 playwright 截图后送 Qwen 审查） |
| 4 | DeepSeek | 对 ⚠️ 文件应用修复，生成 `final_report.md` |

## 模型注意（实测 2026-08-15）

- `kimi-k2.7-code` 与 `glm-5.3` 均为推理模型：`reasoning_content` 消耗 max_tokens 预算，
  客户端已按需给足（编码 32K / 设计 64K）。
- Kimi 系列 API 仅允许 `temperature=1`（客户端已强制）。
- Qwen 走 DashScope compatible-mode（`qwen3.8-max`），支持图像输入（视觉审查用）。
- 视觉位触发条件：交付物含 HTML/CSS/SVG/图表代码/图片（Phase 0 判定）；纯后端/CLI 自动跳过。

## 边界（沿用原始 skill 使用边界）

- 用户催/急 → 不要跑管线，直接 solo
- 单文件 <50 行 / CRUD 3-5 文件 / 单行修复 → solo 更划算
- 10+ 文件重写 → 只跑 Phase 0-1 出规格，按规格 solo
