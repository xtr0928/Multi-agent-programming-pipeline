# Provider / Model / API Matrix

Known-good combinations discovered and validated through direct API testing.

## Z.AI / GLM (ZhipuAI)

| Model | Context | Tested | Notes |
|---|---|---|---|
| `glm-5.2` | 1,048,576 | ✅ | Latest, 1M context |
| `glm-4-plus` | ~128K | ✅ | General purpose |
| `glm-4-flash` | ~128K | ✅ | Fast/cheap |

Provider internal name: `zai`
Default base URL: `https://api.z.ai/api/paas/v4`
API key env var: `GLM_API_KEY`

Key format: `17cac...XXXX.MShY...` (32 hex + dot + 16 alphanum)

## Kimi / Moonshot (Coding API)

| Model | Tested | Notes |
|---|---|---|
| `kimi-k2.7-code` | ✅ 2026-08-15 实测 | 推理型 coder（coding pipeline Phase 2 位）；reasoning_content 消耗 max_tokens，编码需 ≥8K 预算 |
| `kimi-k2.7-code-highspeed` | — | 高速变体（models 列表可见，未实测） |
| `kimi-k3` | ✅ | 通用旗舰（原视觉审查位，2026-08-14 起视觉退役，仅推理审查） |
| `kimi-k2.6` | ✅ | Previous gen, **supports vision/image input** (confirmed via multimodal API test) |
| `kimi-k2.5` | ✅ | Stable |

> ⚠️ 旧文档曾写 `kimi-k2.7-coder` / `kimi-k2.7`——`/models` 端点实测不存在（404）。
> 正确 ID 以 `/v1/models` 返回为准。Kimi 系列仅允许 `temperature=1`。

Provider internal name: `kimi`

### Qwen3.8-Max / Alibaba DashScope

| Model | Status | Notes |
|---|---|---|
| `qwen3.8-max` | ✅ | 2.4T MoE flagship (2026-08-14), programming/long-horizon autonomous coding |
| `qwen-max` | ✅ | Alias (latest max) |
| `qwen3-max` | ✅ | Alias |

Provider internal name: `qwen`
Default base URL: `https://dashscope.aliyuncs.com/compatible-mode/v1` (OpenAI-compatible)
Key: `QWEN_API_KEY` (sk-...)
Role in Multi-Agent pipeline: **coder-executor** (T3 long-horizon coding) + **vision reviewer / UI design** (visual review, OCR, page-render checks — replaces Kimi vision since 2026-08-14, config: auxiliary.vision provider=custom model=qwen3.8-max base_url=dashscope compatible-mode) — T3 long-horizon coding tasks (complex module from scratch, multi-file projects). Gate: compile/test/reproducibility before glm-review. Admission test required (API reachability / quality A-B vs DeepSeek / cost) before formal T3 routing.

## DeepSeek

| Model | Context | Notes |
|---|---|---|
| `deepseek-v4-pro` | — | Primary model |
| `deepseek-v4-pro` | — | Faster variant |

Provider internal name: `deepseek`
Default base URL: `https://api.deepseek.com/v1`
API key env var: `DEEPSEEK_API_KEY`

## Validating API Keys

Use `execute_code` with Python's `urllib` — avoids terminal secret redaction:

```python
import urllib.request, json

data = json.dumps({
    "model": "glm-4-flash",
    "messages": [{"role": "user", "content": "hi"}],
    "max_tokens": 10
}).encode()

req = urllib.request.Request(
    "https://api.z.ai/api/paas/v4/chat/completions",
    data=data,
    headers={
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
)
with urllib.request.urlopen(req, timeout=15) as resp:
    print(json.loads(resp.read()))
```
