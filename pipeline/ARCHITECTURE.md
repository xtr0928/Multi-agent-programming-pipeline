# 协同编码管线 · 架构与技术要点

> 本文档是 `pipeline/` 可执行实现的完整设计说明。
> 架构源头：Multi-Agent 仓库 `multi-agent-pipeline` skill（默认协同架构），2026-08-15 视觉位由 Kimi K3 更换为 Qwen3.8-Max（成本指令）。
> 流程图见 `../docs/coding_pipeline_flow.png`（纸墨风）。

---

## 1. 设计目标与边界

一句话：**用四个不同模型家族的模型，按各自长板分工，把「需求 → 可运行代码 + 视觉验证通过的页面」流水线化。**

三条原则：

1. **先问清、再调研、再选型、再设计、最后编码**：编码永远是最后一步。动手前必须完成「需求澄清 → 开源调研 → 技术选型（用户决策）→ 设计文档（用户确认）」四个前置环节——这是用户 2026-08-15 明确要求保留的原则，也是本管线与「一口气自动跑完」类工具的本质区别。
2. **原始四角色，不加机制**：执行阶段只有「设计 → 编码 → 审查 → 集成」。没有门禁层、没有仲裁层、没有校准阶梯——那些是数模管线的机制，编码管线不引入。
3. **Solo 逃生口优先**：管线不是默认选项。用户催/急、单文件 <50 行、CRUD 3-5 文件、单行修复 → 直接 solo。

---

## 2. 两段式总览：规划（Stage A）→ 执行（Stage B）

### 2.1 规划阶段（planning.py + 编排者交互）

```
用户提出需求（可能模糊）
  │
  ▼
P1 需求澄清（交互）        编排者与用户对话：问清目标/功能/边界/偏好
  │                       产出: planning/requirements_confirmed.md
  ▼
P2 开源调研（research）    GitHub API 搜索同类开源项目 → DeepSeek 汇总技术架构报告
  │                       产出: planning/research_notes.md + research_raw.json
  ▼
P3 技术选型（options）     DeepSeek 按维度列出候选方案：每个候选附优点/缺点/适用场景/代表项目
  │                       产出: planning/tech_options.md + choices.json（选择问卷）
  │                       用户逐维度选择（编排者写入 choices_final.json）
  ▼
P4 详细设计文档（design）  DeepSeek 基于确认需求+已定选型输出：功能清单/技术选型/架构设计/
  │                       数据模型/接口/目录结构/里程碑/风险
  │                       产出: planning/design_doc.md
  │                       用户确认（可提修改意见，修改后重出，直到确认）
  ▼
P5 执行（build）           调用 coding_pipeline.py，设计文档作为硬约束传入
```

**关键机制：用户是唯一的技术决策者。** 管线负责调研和陈列（优点/缺点/案例），选择权在用户手里；设计文档未经确认，编码一步都不许走。

### 2.2 执行阶段（coding_pipeline.py）

```
输入（已确认的需求 + 已确认的设计文档）
  │
  ▼
┌─ Phase 0 ────────────────────────────────────────────────┐
│ DeepSeek 理解需求（结构化，含 VISUAL: yes|no 判定）       │
│ 产出: pipeline_artifacts/requirements.md                  │
└──────────────────────────┬───────────────────────────────┘
                           ▼
        ┌──────────────────┴──────────────────┐
        ▼                                     ▼
┌─ Phase 1a ───────────┐           ┌─ Phase 1b ──────────────┐
│ GLM 整体设计          │  并行      │ Qwen 视觉与 UI 设计      │
│ （受设计文档约束，     │◄─────────►│ 产出: visual_spec.md     │
│  不得改选型）          │           │                          │
│ 产出: design.md       │           │                          │
└──────────┬───────────┘           └────────────┬────────────┘
           └──────────────────┬────────────────┘
                              ▼
┌─ Phase 2 ────────────────────────────────────────────────┐
│ Kimi K2.7 Code 逐文件编写代码（依赖分组并行）              │
└──────────────────────────┬───────────────────────────────┘
                           ▼
        ┌──────────────────┴──────────────────┐
        ▼                                     ▼
┌─ Phase 3a ───────────┐           ┌─ Phase 3b ──────────────┐
│ GLM 代码审查          │  并行      │ Qwen 视觉产出审查        │
│ 产出: review_code.md  │◄─────────►│ playwright 截图 → 图像输入│
│                       │           │ 产出: review_visual.md   │
└──────────┬───────────┘           └────────────┬────────────┘
           └──────────────────┬────────────────┘
                              ▼
┌─ Phase 4 ────────────────────────────────────────────────┐
│ DeepSeek 汇总修复 · 集成验证 · 交付报告                    │
└───────────────────────────────────────────────────────────┘
```

### 2.3 数据流契约（规划阶段）

| 文件 | 生产者 | 消费者 | 说明 |
|---|---|---|---|
| `requirements_confirmed.md` | 编排者（与用户澄清后） | research/options/design/build | 需求的唯一确认版 |
| `research_notes.md` | P2 DeepSeek | P3/P4 | 开源项目技术架构调研 |
| `tech_options.md` | P3 DeepSeek | 用户阅读 | 候选方案优缺点详解 |
| `choices.json` | P3 DeepSeek | 编排者 | 选择问卷模板 |
| `choices_final.json` | 编排者（按用户答复） | P4 design | 用户最终选择 |
| `design_doc.md` | P4 DeepSeek | 用户确认 → build | 详细代码设计架构文档 |

### 2.4 数据流契约（执行阶段）

所有中间产物落盘在 `<项目>/pipeline_artifacts/`：

| 文件 | 生产者 | 消费者 |
|---|---|---|
| `requirements.md` | Phase 0 DeepSeek | Phase 1a/1b、Phase 4 |
| `design.md` | Phase 1a GLM | Phase 1b/2/3a |
| `visual_spec.md` | Phase 1b Qwen | Phase 3b |
| `review_code.md` | Phase 3a GLM | Phase 4 |
| `review_visual.md` | Phase 3b Qwen | Phase 4 |
| `final_report.md` | Phase 4 DeepSeek | 人 |

---

## 3. 视觉环节的触发与实现

### 3.1 触发判定（执行阶段 Phase 0）

DeepSeek 在 requirements 中输出一行 `VISUAL: yes|no`。判定依据：交付物是否含 HTML/CSS/SVG/图表生成代码/图片。

- `no` → Phase 1b 与 Phase 3b 整体跳过（纯后端/CLI 项目不付视觉调用成本）
- `yes` → 视觉设计 + 视觉审查全开

### 3.2 视觉审查的文件类型路由

| 文件类型 | 审查方式 |
|---|---|
| `.html` / `.svg` | playwright（chromium headless）以 `file://` 加载渲染 → 截图 → 送 Qwen |
| `.png` / `.jpg` / `.webp` | 直接作为图像输入送 Qwen |
| `.css` / `.scss` | 不单独审——随页面截图一并覆盖 |
| 后端代码 | 不送视觉审查 |

### 3.3 截图与图像处理细节

1. playwright 加载静态页面（无服务器依赖，`file://` 协议），等待 600ms 让 JS 渲染完成；
2. PIL 压缩：宽度 >1280px 缩至 1280，转 JPEG quality 72；
3. 图像以 base64 data URL 放进 `messages[].content[]` 的 `image_url` 字段（DashScope compatible-mode 接受）。

---

## 4. 关键技术要点

### 4.1 四模型 API 实测特性（llm_client.py）

| 模型 | 实测特性 | 客户端处理 |
|---|---|---|
| `deepseek-v4-pro` | 推理模型；支持 `reasoning_effort`（none~max） | 编排/调研/选型/设计任务用 `high` |
| `glm-5.3` | **推理模型：`reasoning_content` 消耗 max_tokens 预算** | 设计 64K、审查 8K 预算 |
| `kimi-k2.7-code` | **推理型 coder：同上**；API 仅允许 `temperature=1` | 编码 32K 预算、强制 temperature=1 |
| `qwen3.8-max` | 支持图像输入（多模态）；DashScope compatible-mode | 图像走 base64 data URL |

> ⚠️ 模型 ID 教训：仓库旧文档曾写 `kimi-k2.7-coder`，实测 `/v1/models` 端点 404——正确 ID 是 `kimi-k2.7-code`。模型 ID 一律以 `/models` 端点实测为准。

### 4.2 开源调研实现（planning.py research）

1. DeepSeek 从需求提取 3-6 组英文搜索关键词；
2. GitHub `search/repositories` API（未认证，sort=stars，每组取前 10）——未认证限流 10 次/分钟，请求间节流 7 秒；
3. 按 star 去重取前 15 个仓库，落盘 `research_raw.json`（名称/语言/star/简介/topics）；
4. DeepSeek 汇总为调研报告：主流技术方向 + 代表项目 + 架构模式 + 与需求的匹配度 + 待选维度初判。

### 4.3 技术选型实现（planning.py options）

DeepSeek 按「技术维度」组织候选（语言/框架/库/架构模式/部署方式等），每个候选必须给出**具体可对比的优缺点 + 适用场景 + 代表开源项目**（从调研报告引用，禁止凭空推荐）；同回复输出 `choices.json` 问卷（维度与候选名严格一致）。用户选择结果由编排者写入 `choices_final.json`。

### 4.4 GLM 设计文档解析协议（执行阶段）

GLM 被要求输出严格格式，管线用正则解析：

```markdown
### FILE: <相对路径>
职责：一句话
依赖: <依赖的其他文件路径，逗号分隔；无依赖写 无>
规格：<完整规格——做什么/接口/关键逻辑/输入输出/注意事项>
```

解析规则：

1. 按 `### FILE:` 分块；`依赖:` 行决定写入顺序（依赖先写，其内容摘要注入编码 prompt）；
2. `## GROUP` 标记 = 相互独立，Phase 2 用 `ThreadPoolExecutor` 并行编写；无标记则串行；
3. **路径安全**：路径必须相对、禁止 `..`，落盘前断言仍在项目目录内。

### 4.5 设计文档硬约束（--design-context）

执行阶段的 GLM 设计 prompt 会注入已确认的 `design_doc.md`（截断 12K），并声明「技术选型与架构方向已由用户确认，必须严格遵守，不得更改或引入新选型」——规划阶段的用户决策对执行阶段有强制约束力。

### 4.6 Kimi 逐文件编码的上下文控制

每个文件只注入三样：①该文件的规格；②`依赖:` 声明的文件内容（各截 4000 字符）；③输出约束（只输出完整代码，围栏残留被 `strip_fences` 剥掉）。这是原始架构「Do NOT give Kimi the entire spec at once」原则的实现。

### 4.7 审查 → 修复闭环（执行阶段 Phase 4）

1. 从两份审查报告按文件名正则切节，找 `⚠️` 且不含 `✅ 通过` 的文件；
2. DeepSeek 拿「当前内容 + 问题清单」重写完整文件覆盖；
3. 只跑一轮，剩余问题写进 final_report 的「残留风险」。

### 4.8 可靠性与重试

- `ask()` 网络错误/空输出自动重试 2 次，指数退避（8s/16s）；
- `min_chars=4`：兼容「✅ 通过」短输出，低于阈值视为失败；
- 各阶段产物先落盘再进下一阶段——中断后可从产物恢复。

### 4.9 密钥与环境

加载顺序：`os.environ` > `pipeline/.env` > 当前目录 `.env`（后两者已 gitignore）。

```
DEEPSEEK_API_KEY / GLM_API_KEY / KIMI_API_KEY / QWEN_API_KEY
KIMI_BASE_URL（可选，默认 https://api.moonshot.cn/v1）
```

---

## 5. 成本控制要点

| 手段 | 说明 |
|---|---|
| 规划阶段按需推进 | 调研/选型/设计每步产出后**停下来等用户**，不确认不烧下一步的钱 |
| GitHub 搜索零 LLM 成本 | 搜索用公开 API，DeepSeek 只做关键词提取与报告汇总 |
| 视觉环节条件触发 | `VISUAL: no` 时省掉 Phase 1b/3b 全部视觉调用 |
| 逐文件最小上下文 | Kimi 编码只注入规格 + 依赖摘要 |
| 单轮修复 | 修复循环最多一轮 |
| Solo 边界 | 小任务不启动管线 |

---

## 6. 已知边界（诚实声明）

1. **审查深度受限于单次调用**：GLM 代码审查对语义级 bug（如 `>` 与 `>=`）可能漏检并输出「✅ 通过」。管线不内置确定性检查层（「不加机制」原则），依赖 Phase 3b 与 Phase 4 兜底。
2. **设计阶段无算术核验**：设计文档中的数字性内容无独立复算，错误会沿规格传播。
3. **静态页面优先**：视觉审查基于 `file://` 渲染；需后端服务的项目要先自行起服务。
4. **调研广度受限于 GitHub 搜索**：「其他所有开源项目」的实际覆盖以 GitHub API 搜索 + 前 15 仓库为界；深度调研（读 README/源码）未自动化，需要时由编排者补充。
5. **修复环节不验证编译**：Phase 4 重写后不自动执行测试/编译（原始架构边界）。

---

## 7. 目录结构

```
pipeline/
  planning.py           # Stage A 规划阶段（research/options/design/build 子命令）
  coding_pipeline.py    # Stage B 执行阶段（5 阶段编排）
  llm_client.py         # 四模型统一接口
  README.md             # 快速上手
  ARCHITECTURE.md       # 本文档
docs/
  coding_pipeline_flow.png / .html   # 执行阶段流程图（四模型分工）
```
