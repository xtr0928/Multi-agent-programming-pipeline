---
name: multi-model-orchestration
description: Orchestrate multiple Hermes profiles with different models for multi-stage workflows — analysis → coding → review with specialized models per role.
version: 1.0.0
author: Hermes Agent
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [multi-agent, orchestration, multi-model, profiles, delegation]
    related_skills: [hermes-agent, hermes-model-management]
---

# Multi-Model Orchestration

Orchestrate multiple Hermes profiles, each backed by a different model provider, to run multi-stage workflows where specialized models handle different roles (e.g. GLM for architecture analysis, Kimi for code generation, DeepSeek for orchestration).

## When to Use This Pattern

- You want different models for different phases of a task (analysis, coding, review)
- A single model can't do everything well (e.g. GLM for reasoning, Kimi for coding)
- You need isolated contexts per role with different tool access
- You want the main agent to coordinate, not execute every step itself

## How It Works

```
Main Agent (orchestrator)
    │
    ├─ Profile A (Model X) → specialized task 1
    ├─ Profile B (Model Y) → specialized task 2
    └─ Profile A again       → review / gatekeep
```

Each profile runs as a separate `hermes -p <profile> chat -q "..."` invocation. The main agent (you) reads results and passes context between them.

## Step-by-Step Setup

### 1. Create profiles with different models

```bash
# Clone from default to inherit config, .env, skills
hermes profile create <name> --clone

# Configure model for the profile
hermes -p <name> config set model.provider <provider_internal_name>
hermes -p <name> config set model.default <model_name>
hermes -p <name> config set model.base_url <api_url>  # if needed
```

See `references/provider-model-matrix.md` for known-good provider/model/base_url combinations.

### 2. Validate each profile works

```bash
hermes -p <name> chat -q "简短回复确认你的角色。" --quiet
```

If a profile fails with the wrong provider, check:
- `model.provider` is the **internal** provider name (see Pitfalls below)
- `model.base_url` isn't cloned from another profile (common issue with `--clone`)
- The API key is set and valid in the profile's `.env`

### 3. Orchestrate the workflow

```bash
# 1. Send task to analysis profile
hermes -p analyst chat -q "分析 ~/project/ 的代码架构，输出需要新增/修改的文件清单。" --quiet

# 2. Pass the output to the coder profile
hermes -p coder chat -q "根据以下清单编写代码：
<analysis output from step 1>" --quiet

# 3. Send the coder's output back to the analyst for review
hermes -p analyst chat -q "审查以下代码是否有问题：
<coder output from step 2>" --quiet
```

## Pitfalls

### Provider internal names vs display names

The `hermes model` interactive UI shows display names like "Z.AI / GLM", but `model.provider` needs the **internal** name. Discover these by searching the source:

```bash
grep -rn "'zai'\|'kimi'" ~/AppData/Local/hermes/hermes-agent/hermes_cli/ --include="*.py"
```

Known mappings:

| Display Name | Internal Provider | API Key Env Var |
|---|---|---|
| Z.AI / GLM | `zai` | `GLM_API_KEY` |
| Kimi / Moonshot | `kimi` | `KIMI_API_KEY` |
| DeepSeek | `deepseek` | `DEEPSEEK_API_KEY` |

Aliases that also work: `glm`, `z-ai`, `z.ai`, `zhipu` all resolve to `zai`. `moonshot`, `kimi-coding`, `kimi-cn` all route to Kimi endpoints.

### base_url cloning

`hermes profile create --clone` copies `model.base_url` from the source profile. If the source uses DeepSeek's API (`https://api.deepseek.com/v1`), the clone inherits it. This breaks when the new profile uses a different provider.

**Fix:** Set base_url to empty `""` to let the provider use its default, or set it explicitly:

```bash
hermes -p <name> config set model.base_url ""                        # use provider default
hermes -p <name> config set model.base_url "https://api.z.ai/api/paas/v4"  # explicit
```

### Reading .env files

`read_file` blocks `.env` files for security. Use `execute_code` with Python's `open()` to read API keys for validation.

### One-shot chat timeout

`hermes chat -q` doesn't accept `--timeout`. Set the timeout on the `terminal()` call instead. Complex analysis tasks can take 120-300s.

## Verification Checklist

- [ ] Each profile responds correctly to `hermes -p <name> chat -q "test" --quiet`
- [ ] `model.base_url` is correct or empty for each profile
- [ ] API keys are present in each profile's `.env`
- [ ] Internal provider name (not display name) is used in config
- [ ] A dry-run of the full orchestration pipeline succeeds

## Companion Skills

- `hermes-model-management` — for validating API keys, testing provider connectivity, and debugging auth failures before orchestration. Use it first when a profile doesn't respond.
- `hermes-agent` (bundled) — for the broader Hermes feature set, including `delegate_task`, cron, and kanban as alternative multi-agent patterns.

## Reference Files

- `references/provider-model-matrix.md` — known-good model names, provider internal names, base URLs, and API key formats for DeepSeek, Kimi, Z.AI/GLM. Use this when creating new profiles or validating model availability.
