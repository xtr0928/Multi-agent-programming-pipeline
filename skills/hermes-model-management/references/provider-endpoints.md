# Provider API Endpoints for Connectivity Testing

Use these base URLs to test connectivity by hitting the `/v1/models` endpoint.

| Provider | Base URL | Auth Header | Env Var |
|----------|----------|-------------|---------|
| DeepSeek | `https://api.deepseek.com/v1` | `Bearer $DEEPSEEK_API_KEY` | `DEEPSEEK_API_KEY` |
| Kimi/Moonshot (Intl) | `https://api.moonshot.ai/v1` | `Bearer $KIMI_API_KEY` | `KIMI_API_KEY` |
| Kimi/Moonshot (CN) | `https://api.moonshot.cn/v1` | `Bearer $KIMI_CN_API_KEY` | `KIMI_CN_API_KEY` |
| Kimi Coding API | `https://api.kimi.com/coding/v1` | `Bearer $KIMI_API_KEY` | `KIMI_API_KEY` |
| OpenRouter | `https://openrouter.ai/api/v1` | `Bearer $OPENROUTER_API_KEY` | `OPENROUTER_API_KEY` |
| Anthropic | `https://api.anthropic.com/v1` | `x-api-key: $ANTHROPIC_API_KEY` | `ANTHROPIC_API_KEY` |
| OpenAI | `https://api.openai.com/v1` | `Bearer $OPENAI_API_KEY` | `OPENAI_API_KEY` |
| Google Gemini | `https://generativelanguage.googleapis.com/v1beta` | `key=$GEMINI_API_KEY` (query param) | `GEMINI_API_KEY` |
| xAI / Grok | `https://api.x.ai/v1` | `Bearer $XAI_API_KEY` | `XAI_API_KEY` |
| Z.AI / GLM | `https://api.z.ai/api/paas/v4` **or** `https://open.bigmodel.cn/api/paas/v4` | `Bearer $GLM_API_KEY` | `GLM_API_KEY` |
| MiniMax | `https://api.minimax.chat/v1` | `Bearer $MINIMAX_API_KEY` | `MINIMAX_API_KEY` |
| MiniMax CN | `https://api.minimaxi.com/v1` | `Bearer $MINIMAX_CN_API_KEY` | `MINIMAX_CN_API_KEY` |

## Testing pattern

For providers that support OpenAI-compatible `/v1/models`:
```python
req = urllib.request.Request(f'{base_url}/models', headers={'Authorization': f'Bearer {key}'})
```

For Anthropic (different auth header, no `/models`):
```python
req = urllib.request.Request(f'{base_url}/messages', headers={'x-api-key': key, 'anthropic-version': '2023-06-01'})
```

For Gemini (key in query string):
```python
req = urllib.request.Request(f'{base_url}/models?key={key}')
```
