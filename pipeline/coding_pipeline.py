#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""协同编码管线（四模型分工，回归原始架构）

    DeepSeek V4 Pro  理解需求 · 编排 · 汇总修复 · 集成验证
    GLM 5.2          设计整体情况（架构分析）+ 代码审查
    Kimi K2.7 Code   编写具体代码（逐文件）
    Qwen3.8-Max      视觉与 UI 设计 + 视觉产出审查

用法：
    python3 coding_pipeline.py --project-dir ./demo --requirement "做一个xxx"
    python3 coding_pipeline.py --project-dir ./demo --requirement @req.txt

产物：
    <project>/pipeline_artifacts/  requirements / design / visual_spec / review_code / review_visual / final_report
    <project>/<GLM 设计的文件路径>   Kimi 编写的代码（Phase 4 修复后为终版）
"""
import argparse, json, os, re, sys, time, base64
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from llm_client import ask, ROLE_NAME

ARTIFACTS = 'pipeline_artifacts'
VISUAL_RE = re.compile(r'\.(html?|css|scss|less|svg|png|jpe?g|webp)$', re.I)


# ---------------------------------------------------------------- 进度输出
def banner(text):
    print(f'\n━━━ {text} ━━━')


def sent(name):
    print(f'📤 {name} 派发中...')


def done(name, r):
    if 'error' in r:
        print(f'❌ {name} 失败: {r["error"][:120]}')
    else:
        rc = f' rc={r.get("reasoning_chars", "-")}' if 'reasoning_chars' in r else ''
        print(f'✅ {name} 返回 {r["elapsed"]}s{rc} ({len(r["content"])} chars)')


# ---------------------------------------------------------------- 工具
def safe_path(project_dir, rel):
    rel = rel.strip().lstrip('/').replace('\\', '/')
    assert '..' not in rel.split('/'), f'非法路径: {rel}'
    full = os.path.normpath(os.path.join(project_dir, rel))
    assert full.startswith(os.path.normpath(project_dir) + os.sep), f'越界路径: {rel}'
    return full


def strip_fences(code):
    code = code.strip()
    if code.startswith('```'):
        code = re.sub(r'^```[a-zA-Z0-9_+-]*\s*\n?', '', code)
        code = re.sub(r'\n?```\s*$', '', code)
    return code.strip() + '\n'


def read_text(path):
    if os.path.exists(path):
        with open(path, encoding='utf-8', errors='replace') as f:
            return f.read()
    return ''


# ---------------------------------------------------------------- Phase 0
def phase0_requirements(project_dir, requirement):
    banner('Phase 0/4 · DeepSeek 理解需求')
    system = ('你是协同编码管线的编排者 DeepSeek。输入用户需求，输出结构化需求文档（中文）。\n'
              '必须包含以下小节：\n'
              '# 需求文档\n'
              '## 目标（一段话）\n'
              '## 功能清单（- 条目）\n'
              '## 边界（做什么/不做什么）\n'
              '## 技术约束（语言/框架/环境，若用户未指定则由你按最简原则选择）\n'
              '## 交付物清单（预期产出哪些文件，逐条）\n'
              '## 视觉判定\n'
              'VISUAL: yes|no   ← 仅一行。若交付物含 HTML/CSS/SVG/图表生成代码/图片，填 yes，否则 no')
    sent(ROLE_NAME['deepseek'])
    r = ask('deepseek', system, f'用户需求：\n{requirement}', reasoning='high')
    done(ROLE_NAME['deepseek'], r)
    if 'error' in r:
        sys.exit(1)
    os.makedirs(os.path.join(project_dir, ARTIFACTS), exist_ok=True)
    with open(os.path.join(project_dir, ARTIFACTS, 'requirements.md'), 'w', encoding='utf-8') as f:
        f.write(r['content'])
    m = re.search(r'VISUAL:\s*(yes|no)', r['content'], re.I)
    return r['content'], (m.group(1).lower() == 'yes' if m else False)


# ---------------------------------------------------------------- Phase 1
def phase1_design(project_dir, requirements, has_visual, design_context=''):
    banner('Phase 1/4 · GLM 整体设计' + (' ∥ Qwen 视觉与UI设计' if has_visual else ''))
    ctx = (f'\n\n【已确认的设计架构文档（技术选型与架构方向已由用户确认，必须严格遵守，不得更改或引入新选型）】\n{design_context[:12000]}'
           if design_context else '')
    system = ('你是协同编码管线的架构设计者 GLM。基于需求文档，设计整体情况（不写代码）。\n'
              '输出必须严格按以下格式（中文）：\n\n'
              '# 设计文档\n'
              '## 项目结构（树状）\n'
              '## 数据模型/接口（如有）\n\n'
              '## 文件清单\n'
              '对每个文件输出一节，格式：\n'
              '### FILE: <相对路径>\n'
              '职责：一句话\n'
              '依赖: <本文件依赖的其他文件路径，逗号分隔；无依赖则写 无>\n'
              '规格：<该文件的完整规格——做什么、接口/函数、关键逻辑、输入输出、注意事项>\n\n'
              '文件按实施顺序排列（先基础后上层）。前端文件也列入清单（若需求含视觉产出）。\n'
              '若多个文件相互独立，可在它们之前加一行 "## GROUP" 表示可并行编写。')
    sent(ROLE_NAME['glm'])
    r = ask('glm', system, f'需求文档：\n{requirements}{ctx}', max_tokens=65536)
    done(ROLE_NAME['glm'], r)
    if 'error' in r:
        sys.exit(1)
    design = r['content']
    with open(os.path.join(project_dir, ARTIFACTS, 'design.md'), 'w', encoding='utf-8') as f:
        f.write(design)

    # 解析文件清单（### FILE: 块 + ## GROUP 分组）
    files, groups, cur_group = [], [], 0
    for block in re.split(r'\n(?=### FILE:|\n## GROUP)', design):
        block = block.strip()
        if block.startswith('## GROUP'):
            cur_group += 1
            continue
        m = re.match(r'### FILE:\s*(\S+)', block)
        if not m:
            continue
        path = m.group(1)
        depm = re.search(r'依赖:\s*([^\n]+)', block)
        deps = [] if not depm or '无' in depm.group(1) else \
            [d.strip() for d in depm.group(1).split(',') if d.strip()]
        spec = block[m.end():].strip()
        files.append({'path': path, 'spec': spec, 'deps': deps, 'group': cur_group})
    if not files:
        print('❌ GLM 设计文档未解析出 FILE 块，请检查 design.md')
        sys.exit(1)
    print(f'📋 文件清单 {len(files)} 个')
    for f in files:
        print(f'   - {f["path"]}')
    return design, files


def phase1b_visual(project_dir, requirements, design, files):
    banner('Phase 1b · Qwen 视觉与UI设计')
    system = ('你是协同编码管线的视觉与 UI 设计者 Qwen。基于需求与设计文档，'
              '输出视觉规格（中文），包含：\n'
              '# 视觉规格\n'
              '## 页面清单（- 页面路径 + 用途）\n'
              '## 每个页面的视觉规格（布局结构、配色方案、字号层级、组件样式、响应式要求）\n'
              '## 图表/图片清单（类型、数据标注要求）\n'
              '## 视觉检查清单（可逐项核对的检查项）')
    sent(ROLE_NAME['qwen'])
    r = ask('qwen', system, f'需求文档：\n{requirements}\n\n设计文档（节选文件清单）：\n{design[:6000]}')
    done(ROLE_NAME['qwen'], r)
    if 'error' in r:
        print('⚠️ 视觉设计失败（继续主流程，视觉审查将跳过）')
        return ''
    with open(os.path.join(project_dir, ARTIFACTS, 'visual_spec.md'), 'w', encoding='utf-8') as f:
        f.write(r['content'])
    return r['content']


# ---------------------------------------------------------------- Phase 2
def _write_one(project_dir, f, files_done):
    context = ''
    for d in f['deps']:
        full = safe_path(project_dir, d)
        if os.path.exists(full):
            context += f'\n\n【依赖文件 {d} 内容】\n{read_text(full)[:4000]}'
    system = ('你是协同编码管线的代码编写者 Kimi coder。按规格编写该文件的完整代码。\n'
              '规则：只输出完整代码，不要任何解释、不要 markdown 代码块围栏。')
    user = (f'文件路径：{f["path"]}\n\n规格：\n{f["spec"]}\n'
            f'{context}\n\n现在输出 {f["path"]} 的完整代码：')
    r = ask('kimi', system, user, max_tokens=32768)
    if 'error' in r:
        return f['path'], None, r['error']
    full = safe_path(project_dir, f['path'])
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, 'w', encoding='utf-8') as fh:
        fh.write(strip_fences(r['content']))
    return f['path'], full, len(r['content'])


def phase2_code(project_dir, files):
    banner(f'Phase 2/4 · Kimi coder 编写代码（{len(files)} 个文件）')
    written = {}
    i = 0
    while i < len(files):
        group = [files[i]]
        # 同组（相邻 group 号相同）→ 并行
        while i + 1 < len(files) and files[i + 1]['group'] == files[i]['group'] and files[i]['group'] > 0:
            group.append(files[i + 1])
            i += 1
        i += 1
        if len(group) == 1:
            f = group[0]
            sent(f'Kimi ← {f["path"]}')
            path, full, res = _write_one(project_dir, f, written)
            if full:
                print(f'✅ {path} 完成 ({res} chars)')
                written[path] = full
            else:
                print(f'❌ {path} 失败: {res}')
        else:
            sent('Kimi ← ' + ' ∥ '.join(f['path'] for f in group) + '（并行）')
            with ThreadPoolExecutor(max_workers=len(group)) as ex:
                fut = {ex.submit(_write_one, project_dir, f, written): f for f in group}
                for fu in as_completed(fut):
                    path, full, res = fu.result()
                    if full:
                        print(f'✅ {path} 完成 ({res} chars)')
                        written[path] = full
                    else:
                        print(f'❌ {path} 失败: {res}')
    return written


# ---------------------------------------------------------------- Phase 3
def phase3a_review_code(project_dir, files):
    banner('Phase 3/4 · GLM 代码审查')
    report = ['# 代码审查报告（GLM）\n']
    for f in files:
        full = safe_path(project_dir, f['path'])
        code = read_text(full)
        if not code:
            report.append(f'\n## {f["path"]}\n⚠️ 文件不存在或为空')
            continue
        system = ('你是协同编码管线的代码审查者 GLM。对照规格审查代码（逻辑/安全/风格/遗漏）。\n'
                  '输出第一行：✅ 通过 或 ⚠️ 需修改；若需修改，随后逐条列出'
                  '「问题位置 + 问题说明 + 修改建议」。')
        user = f'文件：{f["path"]}\n\n规格：\n{f["spec"]}\n\n代码：\n{code[:16000]}'
        sent(f'GLM 审查 ← {f["path"]}')
        r = ask('glm', system, user, max_tokens=8000)
        done('GLM 审查', r)
        report.append(f'\n## {f["path"]}\n' + (r.get('content') or r.get('error', '')))
        time.sleep(1)
    with open(os.path.join(project_dir, ARTIFACTS, 'review_code.md'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(report))
    return '\n'.join(report)


def _screenshot(url_or_file, out_png, viewport=(1280, 800)):
    from PIL import Image
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={'width': viewport[0], 'height': viewport[1]})
        page.goto(url_or_file)
        page.wait_for_timeout(600)
        page.screenshot(path=out_png, full_page=False)
        b.close()
    im = Image.open(out_png)
    if im.width > 1280:
        im = im.resize((1280, int(im.height * 1280 / im.width)), Image.LANCZOS)
    im.convert('RGB').save(out_png, 'JPEG', quality=72)
    return out_png


def phase3b_review_visual(project_dir, files, visual_spec):
    banner('Phase 3/4 · Qwen 视觉产出审查')
    if not visual_spec:
        print('⚠️ 无视觉规格，跳过')
        return ''
    report = ['# 视觉审查报告（Qwen）\n']
    system = ('你是协同编码管线的视觉审查者 Qwen。对照视觉规格检查页面/图片的实际渲染效果。\n'
              '检查：布局与规格一致性 / 配色 / 文字可读性与截断 / 元素可见性 / 图表标注。\n'
              '输出：✅ 通过 或 ⚠️ 需修改（逐条列出问题位置+建议）。')
    tmp = os.path.join(project_dir, ARTIFACTS, '.visual_tmp')
    os.makedirs(tmp, exist_ok=True)
    for f in files:
        full = safe_path(project_dir, f['path'])
        if not os.path.exists(full):
            continue
        imgs = []
        if re.search(r'\.(html?|svg)$', f['path'], re.I):
            png = os.path.join(tmp, os.path.basename(f['path']) + '.jpg')
            try:
                _screenshot('file://' + full, png)
                imgs = [png]
            except Exception as e:
                print(f'⚠️ 截图失败 {f["path"]}: {str(e)[:100]}（退化为源码检查）')
        elif re.search(r'\.(png|jpe?g|webp)$', f['path'], re.I):
            imgs = [full]
        else:  # css 等：随页面审查，单独文件跳过
            continue
        user = f'文件：{f["path"]}\n\n视觉规格（节选）：\n{visual_spec[:4000]}\n\n' + \
               ('页面渲染截图见附件。' if imgs else '该文件为样式/资源文件，结合页面审查。')
        sent(f'Qwen 视觉审查 ← {f["path"]}')
        r = ask('qwen', system, user, images=imgs if imgs else None, max_tokens=8000)
        done('Qwen 视觉审查', r)
        report.append(f'\n## {f["path"]}\n' + (r.get('content') or r.get('error', '')))
        time.sleep(1)
    with open(os.path.join(project_dir, ARTIFACTS, 'review_visual.md'), 'w', encoding='utf-8') as fh:
        fh.write('\n'.join(report))
    return '\n'.join(report)


# ---------------------------------------------------------------- Phase 4
def phase4_integrate(project_dir, files, review_code, review_visual, requirements):
    banner('Phase 4/4 · DeepSeek 汇总修复 · 集成验证')
    # 收集 ⚠️ 文件
    flagged = {}
    for f in files:
        section = re.search(rf'##\s*{re.escape(f["path"])}\n(.*?)(?=\n##\s|\Z)', review_code, re.S)
        if section and '⚠️' in section.group(1) and '✅ 通过' not in section.group(1):
            flagged.setdefault(f['path'], []).append('代码问题：' + section.group(1)[:1500])
    for f in files:
        if not re.search(r'\.(html?|svg|png|jpe?g|webp)$', f['path'], re.I):
            continue
        section = re.search(rf'##\s*{re.escape(f["path"])}\n(.*?)(?=\n##\s|\Z)', review_visual, re.S)
        if section and '⚠️' in section.group(1) and '✅ 通过' not in section.group(1):
            flagged.setdefault(f['path'], []).append('视觉问题：' + section.group(1)[:1500])

    fixed = []
    if flagged:
        print(f'⚠️ 需修复文件 {len(flagged)} 个: {", ".join(flagged)}')
        for path, issues in flagged.items():
            full = safe_path(project_dir, path)
            system = ('你是协同编码管线的编排者 DeepSeek，负责应用审查修复。'
                      '输出修复后的完整文件内容，不要解释，不要 markdown 围栏。')
            user = f'文件：{path}\n\n当前内容：\n{read_text(full)[:12000]}\n\n审查发现的问题：\n' + '\n---\n'.join(issues)
            sent(f'DeepSeek 修复 ← {path}')
            r = ask('deepseek', system, user, reasoning='high', max_tokens=32768)
            done('DeepSeek 修复', r)
            if 'error' not in r:
                with open(full, 'w', encoding='utf-8') as fh:
                    fh.write(strip_fences(r['content']))
                fixed.append(path)
    else:
        print('✅ 无审查问题，无需修复')

    # 最终报告
    system = ('你是协同编码管线的编排者 DeepSeek。生成最终交付报告（中文），包含：\n'
              '# 交付报告\n'
              '## 交付物（文件清单与用途）\n'
              '## 审查与修复摘要（代码/视觉各多少问题、修复状态）\n'
              '## 验证状态（哪些已验证、如何验证）\n'
              '## 残留风险与使用说明')
    user = (f'需求：\n{requirements[:3000]}\n\n文件：\n' +
            '\n'.join(f'- {f["path"]}' for f in files) +
            f'\n\n代码审查：\n{review_code[:4000]}\n\n视觉审查：\n{review_visual[:3000]}'
            f'\n\n已修复：{fixed}')
    sent(ROLE_NAME['deepseek'])
    r = ask('deepseek', system, user, reasoning='high', max_tokens=16000)
    done(ROLE_NAME['deepseek'], r)
    if 'error' not in r:
        with open(os.path.join(project_dir, ARTIFACTS, 'final_report.md'), 'w', encoding='utf-8') as fh:
            fh.write(r['content'])
    return fixed


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description='协同编码管线（DS 编排 / GLM 设计+审查 / Kimi 编码 / Qwen 视觉）')
    ap.add_argument('--project-dir', required=True, help='项目目录（代码与产物都写入这里）')
    ap.add_argument('--requirement', required=True, help='需求文本，或以 @ 开头的文件路径')
    ap.add_argument('--design-context', help='已确认的设计架构文档（@文件路径）——技术选型已定，GLM 不再重做选型')
    args = ap.parse_args()

    project_dir = os.path.abspath(args.project_dir)
    os.makedirs(project_dir, exist_ok=True)
    requirement = args.requirement
    if requirement.startswith('@'):
        requirement = read_text(requirement[1:])
    design_context = ''
    if args.design_context:
        dc = args.design_context
        if dc.startswith('@'):
            dc = read_text(dc[1:])
        design_context = dc
    if not requirement.strip():
        sys.exit('❌ 需求为空')

    print('=' * 62)
    print(f'协同编码管线 · 项目 {project_dir}')
    print('DeepSeek 理解需求 → GLM 整体设计 ∥ Qwen 视觉UI → Kimi coder 编码 → 并行审查 → DeepSeek 集成')
    print('=' * 62)

    requirements, has_visual = phase0_requirements(project_dir, requirement)
    design, files = phase1_design(project_dir, requirements, has_visual, design_context)
    visual_spec = phase1b_visual(project_dir, requirements, design, files) if has_visual else ''
    written = phase2_code(project_dir, files)
    print(f'\n📦 代码产出 {len(written)}/{len(files)} 个文件')
    review_code = phase3a_review_code(project_dir, files)
    review_visual = phase3b_review_visual(project_dir, files, visual_spec) if has_visual else ''
    fixed = phase4_integrate(project_dir, files, review_code, review_visual, requirements)

    print('\n' + '=' * 62)
    print(f'✅ 管线完成。代码：{project_dir}')
    print(f'   产物：{os.path.join(project_dir, ARTIFACTS)}/')
    if fixed:
        print(f'   修复：{len(fixed)} 个文件（{", ".join(fixed)}）')
    print('=' * 62)


if __name__ == '__main__':
    main()
