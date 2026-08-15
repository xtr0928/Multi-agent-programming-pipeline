#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""协同编码管线 LLM 客户端：四模型统一接口
DeepSeek V4 Pro（编排）/ GLM 5.2（整体设计+代码审查）/ Kimi K2.7 Code（逐文件编码）/ Qwen3.8-Max（视觉与UI设计+视觉审查）

用法：
    from llm_client import ask
    resp = ask('deepseek', system_prompt, user_prompt)
    resp = ask('qwen', system_prompt, user_prompt, images=['/path/to/img.jpg'])  # 视觉审查

环境变量（缺失时回退到本目录 .env 文件）：
    DEEPSEEK_API_KEY / GLM_API_KEY / KIMI_API_KEY / QWEN_API_KEY
    KIMI_BASE_URL（可选，默认 https://api.moonshot.cn/v1）
"""
import os, json, time, base64, mimetypes
import urllib.request

# ---------- env ----------
def _load_env():
    env = dict(os.environ)
    for p in [os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'), '.env']:
        try:
            with open(p, encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if '=' in line and not line.startswith('#'):
                        k, v = line.split('=', 1)
                        env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
        except OSError:
            pass
    return env

_ENV = _load_env()

CONFIG = {
    'deepseek': {
        'url': 'https://api.deepseek.com/chat/completions',
        'key': _ENV.get('DEEPSEEK_API_KEY', ''),
        'model': 'deepseek-v4-pro',
    },
    'glm': {
        'url': 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
        'key': _ENV.get('GLM_API_KEY', ''),
        'model': 'glm-5.2',  # 推理模型：reasoning_content 消耗 max_tokens，预算需给足
    },
    'kimi': {
        'url': (_ENV.get('KIMI_BASE_URL', 'https://api.moonshot.cn/v1').rstrip('/')
                + '/chat/completions'),
        'key': _ENV.get('KIMI_API_KEY', ''),
        'model': 'kimi-k2.7-code',  # 推理型 coder：reasoning_content 消耗 max_tokens
    },
    'qwen': {
        'url': 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
        'key': _ENV.get('QWEN_API_KEY', ''),
        'model': 'qwen3.8-max',
    },
}

ROLE_NAME = {'deepseek': 'DeepSeek', 'glm': 'GLM', 'kimi': 'Kimi-coder', 'qwen': 'Qwen'}


def _encode_image(path_or_data):
    """本地文件路径或 data URL → base64 data URL"""
    if path_or_data.startswith('data:'):
        return path_or_data
    with open(path_or_data, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    mime = mimetypes.guess_type(path_or_data)[0] or 'image/png'
    return f'data:{mime};base64,{b64}'


def ask(provider, system, user, reasoning=None, max_tokens=65536, temperature=0.3,
        timeout=900, images=None, retries=2, min_chars=4):
    """调用一个模型，空输出/网络错误自动重试。reasoning 仅 deepseek 支持。"""
    cfg = CONFIG[provider]
    payload = {
        'model': cfg['model'],
        'messages': [{'role': 'system', 'content': system}],
        'max_tokens': max_tokens,
        'temperature': temperature,
    }
    if images:
        content = [{'type': 'text', 'text': user}]
        for img in images:
            content.append({'type': 'image_url',
                            'image_url': {'url': _encode_image(img)}})
        payload['messages'].append({'role': 'user', 'content': content})
    else:
        payload['messages'].append({'role': 'user', 'content': user})
    if reasoning and provider == 'deepseek':
        payload['reasoning_effort'] = reasoning  # none/minimal/low/medium/high/xhigh/max
    if provider == 'kimi':
        payload['temperature'] = 1.0  # kimi 系列只允许 temperature=1

    last_err = None
    for attempt in range(retries + 1):
        t0 = time.time()
        req = urllib.request.Request(
            cfg['url'], data=json.dumps(payload).encode(),
            headers={'Content-Type': 'application/json',
                     'Authorization': f'Bearer {cfg["key"]}'})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                data = json.loads(r.read())
        except Exception as e:
            last_err = str(e)
            time.sleep(8 * (attempt + 1))
            continue
        msg = data['choices'][0]['message']
        out = {'provider': provider, 'model': data.get('model', cfg['model']),
               'content': (msg.get('content') or '').strip(),
               'elapsed': round(time.time() - t0, 1)}
        rc = msg.get('reasoning_content')
        if rc:
            out['reasoning_chars'] = len(rc)
        if len(out['content']) >= min_chars:
            return out
        last_err = f'content too short ({len(out["content"])} chars, rc={out.get("reasoning_chars")})'
        time.sleep(8 * (attempt + 1))
    return {'provider': provider, 'error': last_err, 'elapsed': 0}


if __name__ == '__main__':
    for p in ['deepseek', 'glm', 'kimi', 'qwen']:
        r = ask(p, '你是编码管线中的一个环节。', '用一句话说明你在这个管线里的职责。', max_tokens=2000)
        if 'error' in r:
            print(f'{p}: ERROR {r["error"][:100]}')
        else:
            c = r['content'][:60].replace('\n', ' ')
            print(f'{p}: OK {r["elapsed"]}s rc={r.get("reasoning_chars","-")} | {c}')
