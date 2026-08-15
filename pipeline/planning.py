#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""协同编码管线 · 规划阶段（Stage A）

用户定下的前置流程：
  ① 先问清具体需求（编排者与用户交互澄清，产出 requirements_confirmed.md）
  ② 搜索 GitHub 等开源项目的技术架构（research）
  ③ 列出各技术方案优缺点供用户权衡选择（options → 用户选择）
  ④ 用户选完后输出详细代码设计架构文档（design → 用户确认）
  ⑤ 确认后进入执行阶段（build → 调 coding_pipeline.py）

子命令：
  python3 planning.py research  --project-dir X --requirement "..."|@file
  python3 planning.py options   --project-dir X
  python3 planning.py design    --project-dir X            （读取 choices_final.json）
  python3 planning.py build     --project-dir X            （调执行阶段）

产物（<project>/planning/）：
  requirements_confirmed.md  需求确认版（编排者与用户澄清后写入，research 的输入）
  research_notes.md          开源项目技术架构调研报告
  tech_options.md            技术方案选项（优缺点详解，供用户阅读选择）
  choices.json               选择问卷模板（编排者展示）
  choices_final.json         用户最终选择（编排者按用户答复写入）
  design_doc.md              详细代码设计架构文档（用户确认后 build）
"""
import argparse, json, os, re, sys, time, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm_client import ask

PLANNING_DIR = 'planning'
GH_API = 'https://api.github.com/search/repositories'


def read_text(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def pdir(project_dir):
    d = os.path.join(project_dir, PLANNING_DIR)
    os.makedirs(d, exist_ok=True)
    return d


def gh_search(q, per_page=10):
    url = GH_API + '?' + urllib.parse.urlencode(
        {'q': q, 'sort': 'stars', 'order': 'desc', 'per_page': per_page})
    req = urllib.request.Request(url, headers={
        'Accept': 'application/vnd.github+json',
        'User-Agent': 'coding-pipeline-planning'})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())


def ask_json(provider, system, user, max_tokens=32768):
    """要求模型输出纯 JSON 并解析"""
    r = ask(provider, system, user, max_tokens=max_tokens)
    if 'error' in r:
        print(f'❌ {provider} 调用失败: {r["error"]}')
        sys.exit(1)
    text = r['content'].strip()
    m = re.search(r'\[.*\]|\{.*\}', text, re.S)
    if not m:
        print(f'❌ {provider} 输出无法解析为 JSON，原文前 200 字：\n{text[:200]}')
        sys.exit(1)
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        print(f'❌ JSON 解析失败，原文前 300 字：\n{text[:300]}')
        sys.exit(1)


# ---------------------------------------------------------------- research
def cmd_research(project_dir, requirement):
    print('━━━ P2 开源项目技术架构调研 ━━━')
    # 1. 提取搜索关键词
    sys_p = ('你是需求分析师。从用户需求中提取适合在 GitHub 搜索相关开源项目的关键词。'
             '输出纯 JSON 字符串数组（3-6 个，英文为主，每个 1-4 词）。')
    print('📤 DeepSeek 提取搜索关键词...')
    keywords = ask_json('deepseek', sys_p, requirement, max_tokens=4000)
    print('   关键词:', keywords)

    # 2. GitHub API 搜索（未认证，10 次/分钟 → 节流）
    repos = {}
    for kw in keywords:
        try:
            res = gh_search(kw)
            for it in res.get('items', []):
                repos[it['full_name']] = {
                    'name': it['full_name'], 'url': it['html_url'],
                    'desc': (it.get('description') or '')[:200],
                    'lang': it.get('language'), 'stars': it.get('stargazers_count'),
                    'topics': it.get('topics', [])[:8]}
        except Exception as e:
            print(f'   ⚠️ 搜索 "{kw}" 失败: {str(e)[:80]}')
        time.sleep(7)  # 未认证限流 10/min
    top = sorted(repos.values(), key=lambda x: -x['stars'])[:15]
    if not top:
        print('❌ GitHub 搜索无结果')
        sys.exit(1)
    print(f'   去重后 {len(repos)} 个仓库，取 star 前 {len(top)} 个：')
    for t in top:
        print(f'     - {t["name"]} ★{t["stars"]} [{t["lang"]}] {t["desc"][:50]}')
    with open(os.path.join(pdir(project_dir), 'research_raw.json'), 'w', encoding='utf-8') as f:
        json.dump(top, f, ensure_ascii=False, indent=2)

    # 3. 综合调研报告
    sys_p2 = ('你是技术调研分析师。基于搜索到的开源项目清单与用户需求，输出中文调研报告：\n'
              '# 开源项目技术架构调研\n'
              '## 主流技术方向（每个方向：主流技术栈/代表项目/它们采用的架构模式）\n'
              '## 各方向与本题需求的匹配度分析\n'
              '## 可供用户选择的技术维度初判（每维度点出候选方向，详情留给选型环节）')
    user2 = (f'用户需求：\n{requirement}\n\n开源项目清单（JSON）：\n' +
             json.dumps(top, ensure_ascii=False, indent=1)[:12000])
    print('📤 DeepSeek 汇总调研报告...')
    r = ask('deepseek', sys_p2, user2, reasoning='high', max_tokens=16000)
    if 'error' in r:
        sys.exit(f'❌ 调研报告失败: {r["error"]}')
    out = os.path.join(pdir(project_dir), 'research_notes.md')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(r['content'])
    print(f'✅ 调研报告: {out} ({len(r["content"])} chars)')


# ---------------------------------------------------------------- options
def cmd_options(project_dir):
    print('━━━ P3 技术方案选型 ━━━')
    req_path = os.path.join(pdir(project_dir), 'requirements_confirmed.md')
    notes_path = os.path.join(pdir(project_dir), 'research_notes.md')
    requirement = read_text(req_path) if os.path.exists(req_path) else ''
    notes = read_text(notes_path) if os.path.exists(notes_path) else '(未调研)'

    sys_p = ('你是技术选型顾问。为用户逐维度列出候选技术方案，供其权衡选择。\n'
             '输出两部分（同一回复中，先 markdown 后 JSON）：\n'
             '第一部分 markdown（中文）：# 技术方案选项\n'
             '对每个技术维度（语言/框架/库/架构模式/部署方式等，覆盖项目全部关键决策点）：\n'
             '## 维度N：<维度名>\n'
             '### 候选A：<名称>\n优点：…\n缺点：…\n适用场景：…\n代表开源项目：<从调研报告中引用>\n'
             '（每个维度 2-4 个候选，优缺点必须具体、可对比，讲清楚让用户能决策）\n'
             '第二部分 JSON：{"choices": [{"dim": "维度名", "options": ["候选名..."]}]}'
             '——维度与候选名与第一部分严格一致。')
    user = (f'用户确认的需求：\n{requirement}\n\n调研报告：\n{notes[:12000]}')
    print('📤 DeepSeek 生成技术方案选项...')
    r = ask('deepseek', sys_p, user, reasoning='high', max_tokens=32768)
    if 'error' in r:
        sys.exit(f'❌ 选型失败: {r["error"]}')
    d = pdir(project_dir)
    with open(os.path.join(d, 'tech_options.md'), 'w', encoding='utf-8') as f:
        f.write(r['content'])
    m = re.search(r'\{[\s\S]*"choices"[\s\S]*\}', r['content'])
    if not m:
        sys.exit('❌ 未在输出中找到 choices JSON')
    choices = json.loads(m.group(0))
    with open(os.path.join(d, 'choices.json'), 'w', encoding='utf-8') as f:
        json.dump(choices, f, ensure_ascii=False, indent=2)
    print(f'✅ 选项报告: {d}/tech_options.md')
    print(f'✅ 选择问卷: {d}/choices.json')
    print('\n请编排者把 tech_options.md 讲给用户 → 用户逐维度选择 → 编排者写 choices_final.json（格式同 choices.json + "note" 字段）')


# ---------------------------------------------------------------- design
def cmd_design(project_dir):
    print('━━━ P4 详细代码设计架构文档 ━━━')
    d = pdir(project_dir)
    cpath = os.path.join(d, 'choices_final.json')
    if not os.path.exists(cpath):
        sys.exit('❌ 缺少 choices_final.json：请先完成技术选型（用户逐维度选择后写入）')
    choices = read_text(cpath)
    requirement = read_text(os.path.join(d, 'requirements_confirmed.md')) if \
        os.path.exists(os.path.join(d, 'requirements_confirmed.md')) else ''
    notes = read_text(os.path.join(d, 'research_notes.md')) if \
        os.path.exists(os.path.join(d, 'research_notes.md')) else ''

    sys_p = ('你是软件架构师。基于用户确认的需求与已定的技术选型，输出详细代码设计架构文档（中文），包含：\n'
             '# 代码设计架构文档\n'
             '## 1. 功能清单（逐条，含验收标准）\n'
             '## 2. 技术选型（列出用户已选的每项技术及其在项目中的角色）\n'
             '## 3. 总体架构设计（分层/模块划分 + 数据流）\n'
             '## 4. 数据模型（实体/字段/关系）\n'
             '## 5. 接口设计（模块间接口、对外接口）\n'
             '## 6. 项目目录结构（规划到目录级）\n'
             '## 7. 里程碑与实施顺序\n'
             '## 8. 风险与边界\n'
             '约束：技术选型已由用户确认，不得更改或引入新选型；'
             '架构描述要具体到能让执行阶段直接照做。')
    user = (f'用户确认的需求：\n{requirement}\n\n用户确认的技术选型：\n{choices}\n\n调研报告（节选）：\n{notes[:6000]}')
    print('📤 DeepSeek 输出详细设计文档...')
    r = ask('deepseek', sys_p, user, reasoning='high', max_tokens=32768)
    if 'error' in r:
        sys.exit(f'❌ 设计文档失败: {r["error"]}')
    out = os.path.join(d, 'design_doc.md')
    with open(out, 'w', encoding='utf-8') as f:
        f.write(r['content'])
    print(f'✅ 设计文档: {out} ({len(r["content"])} chars)')
    print('\n请编排者把 design_doc.md 讲给用户确认 → 用户确认（或提出修改意见，修改后重跑本命令）→ 确认后执行 build')


# ---------------------------------------------------------------- build
def cmd_build(project_dir):
    print('━━━ P5 执行阶段（按确认文档编码） ━━━')
    d = pdir(project_dir)
    doc = os.path.join(d, 'design_doc.md')
    req = os.path.join(d, 'requirements_confirmed.md')
    if not os.path.exists(doc):
        sys.exit('❌ 缺少 design_doc.md：请先完成 P4 设计文档')
    if not os.path.exists(req):
        sys.exit('❌ 缺少 requirements_confirmed.md')
    import subprocess
    here = os.path.dirname(os.path.abspath(__file__))
    cmd = [sys.executable, os.path.join(here, 'coding_pipeline.py'),
           '--project-dir', project_dir,
           '--requirement', '@' + req,
           '--design-context', '@' + doc]
    print('$ ' + ' '.join(cmd))
    subprocess.run(cmd, check=True)


def main():
    ap = argparse.ArgumentParser(description='协同编码管线 · 规划阶段（调研/选型/设计文档）')
    ap.add_argument('cmd', choices=['research', 'options', 'design', 'build'])
    ap.add_argument('--project-dir', required=True)
    ap.add_argument('--requirement', help='需求文本或以 @ 开头的文件（research 用）')
    args = ap.parse_args()
    project_dir = os.path.abspath(args.project_dir)
    os.makedirs(project_dir, exist_ok=True)

    if args.cmd == 'research':
        if not args.requirement:
            sys.exit('❌ research 需要 --requirement（需求文本或 @requirements_confirmed.md）')
        requirement = args.requirement
        if requirement.startswith('@'):
            requirement = read_text(requirement[1:])
        cmd_research(project_dir, requirement)
    elif args.cmd == 'options':
        cmd_options(project_dir)
    elif args.cmd == 'design':
        cmd_design(project_dir)
    elif args.cmd == 'build':
        cmd_build(project_dir)


if __name__ == '__main__':
    main()
