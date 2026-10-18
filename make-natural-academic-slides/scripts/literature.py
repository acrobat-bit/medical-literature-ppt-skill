#!/usr/bin/env python3
"""Assemble a reusable literature-report record and check its source assets."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import re
import author_profile
import visual_policy
import focus_plan

ROOT = Path(__file__).resolve().parents[1]
ORDER = ['cover', 'authors', 'background', 'methods', 'results', 'discussion', 'advantages', 'disadvantages', 'reflection']
LABELS = dict(zip(ORDER, ['原文标题', '作者信息', '背景 Background', '方法 Methods', '结果 Results', '讨论 Discussion', '亮点 Highlights', '局限 Limitations', '感想']))

def ensure(condition, message):
    if not condition:
        raise ValueError(message)

def image_asset(base, asset):
    ensure(isinstance(asset, dict), '图片需包含文件与来源信息')
    name = asset.get('file', '')
    ensure(isinstance(name, str) and name and not Path(name).is_absolute() and '\\' not in name, '图片使用材料目录内的相对路径')
    p = (base / name).resolve()
    ensure(p.is_relative_to(base.resolve()), '图片路径越出材料目录')
    ensure(p.is_file(), f'图片文件缺失：{name}')
    content = p.read_bytes()
    ensure(content.startswith(b'\x89PNG\r\n\x1a\n') or content.startswith(b'\xff\xd8\xff'), '图片需为真实 PNG 或 JPEG 文件')
    url=asset.get('source_url','')
    if asset.get('source_pdf'):
        visual_policy.validate_pdf_source(asset,base)
        ensure(not url or isinstance(url,str)and re.match(r'^https?://[^\s]+$',url),'PDF 来源链接请使用 http/https；本地提供的 PDF 可省略链接')
    else:ensure(isinstance(url,str)and re.match(r'^https?://[^\s]+$',url),'图片需记录原始来源链接')
    digest = hashlib.sha256(content).hexdigest()
    if asset.get('sha256'):
        ensure(asset['sha256'] == digest, f'图片校验值变化：{name}')
    return digest

def validate_literature(data, base, native=None):
    if data.get('deck', {}).get('report_type') != 'literature':
        return []
    config = data.get('literature', {})
    presenter = config.get('presenter', {})
    ensure(isinstance(presenter, dict) and all(isinstance(presenter.get(k, ''), str) for k in ['name', 'affiliation', 'date']), '演讲者信息使用姓名、单位和日期文本')
    slides = data.get('slides', [])
    keys = [s.get('section_key') for s in slides]
    compressed = [k for i, k in enumerate(keys) if i == 0 or k != keys[i-1]]
    ensure(compressed == ORDER, '文献汇报顺序需为：原文标题、作者、背景、方法、结果、讨论、亮点、局限、感想')
    ensure(keys[:2] == ['cover', 'authors'] and keys.count('cover') == keys.count('authors') == keys.count('reflection') == 1, '标题与作者分别位于第 1、2 页，感想位于末页')
    sources = {s['id']: s for s in data['sources']}
    ensure(config.get('paper_source_id') in sources, '缺少论文来源关联')
    journal=config.get('journal',{});metric=journal.get('impact_factor',{})
    if metric:
        ensure(isinstance(journal.get('name'),str) and journal['name'].strip(),'请填写期刊名称')
        ensure(isinstance(metric.get('value'),(int,float)) and not isinstance(metric['value'],bool) and 0<=metric['value']<1000,'IF 使用有效数值')
        ensure(isinstance(metric.get('year'),int) and 1900<=metric['year']<=2100,'IF 需记录数据年份')
        ensure(metric.get('source_id')in sources and sources[metric['source_id']]['identity_status']=='verified','IF 需关联已核对的期刊官网或 JCR 来源')
        ensure(re.fullmatch(r'\d{4}-\d{2}-\d{2}',metric.get('verified_at','')),'IF 需记录核对日期')
    capture = config.get('title_capture', {})
    ensure(capture.get('kind') in ['pdf', 'full_text_page'], '标题截图来源需为论文 PDF 或全文页面')
    ensure(re.fullmatch(r'\d{4}-\d{2}-\d{2}', capture.get('captured_at', '')), '标题截图需记录截取日期')
    capture_hash = image_asset(base, capture)
    authors = config.get('authors', [])
    ensure(isinstance(authors, list) and 1 <= len(authors) <= 3, '作者页展示 1–3 位重点作者，其余作者写入补充信息')
    assets = [capture['file']]
    if capture.get('source_pdf'):assets.append(capture['source_pdf'])
    for slide in slides:
        layout = slide.get('layout', {})
        images = layout.get('images', [])
        ensure(isinstance(images, list), '正文图片需使用列表')
        for file in [*images, *([layout['image']] if layout.get('image') else [])]:
            ensure(isinstance(file, str) and file and not Path(file).is_absolute() and '\\' not in file, '正文图片使用材料目录内的相对路径')
            p = (base / file).resolve()
            ensure(p.is_relative_to(base.resolve()) and p.is_file(), f'正文图片文件缺失或路径无效：{file}')
            assets.append(file)
    author_hashes = []
    for author in authors:
        for k in ['name', 'contribution', 'position', 'affiliation', 'verified_at']:
            ensure(isinstance(author.get(k), str) and author[k].strip(), f'作者缺少 {k}')
        ensure(re.fullmatch(r'\d{4}-\d{2}-\d{2}', author['verified_at']), '作者任职需记录核对日期')
        ensure(author.get('profile_source_id') in sources, '作者需关联任职信息来源')
        author_hashes.append(image_asset(base, author.get('portrait', {})))
        assets.append(author['portrait']['file'])
        if author['portrait'].get('source_pdf'):assets.append(author['portrait']['source_pdf'])
    author_profile.validate(config, sources, data.get('deck', {}).get('mode') == 'test_fixture', native[1] if native is not None else None)
    form = slides[-1].get('reflection', {})
    ensure(isinstance(form.get('directions'), list) and 1 <= len(form['directions']) <= 5 and all(isinstance(x, str) and x.strip() for x in form['directions']), '感想需提供填写方向')
    prompts = form.get('prompts', [])
    ensure(isinstance(prompts, list) and 1 <= len(prompts) <= 4, '感想需包含 1–4 个填写提示')
    ids = set()
    for p in prompts:
        ensure(isinstance(p.get('id'), str) and re.fullmatch(r'[a-z][a-z0-9_]{0,39}', p['id']) and p['id'] not in ids, '感想提示 id 无效或重复')
        ids.add(p['id'])
        ensure(isinstance(p.get('label'), str) and p['label'].strip() and isinstance(p.get('hint'), str), '感想提示需有标签和说明')
    answers = form.get('answers', {})
    ensure(isinstance(answers, dict) and all(k in ids and isinstance(v, str) and len(v) <= 4000 for k, v in answers.items()), '演讲者填写内容需对应当前提示')
    if native is not None:
        ensure(capture_hash in native[0]['image_sha256'], '第 1 页需嵌入已登记的原文标题截图')
        visual_policy.check_native_image_ratio(capture,base,native[0])
        ensure(all(h in native[1]['image_sha256'] for h in author_hashes), '第 2 页需嵌入已登记的作者照片')
        for author in authors:
            for k in ['name', 'contribution', 'position', 'affiliation']:
                ensure(re.sub(r'\s+', '', author[k]) in re.sub(r'\s+', '', native[1]['text']), f'作者页缺少 {author[k]}')
        for p in prompts:
            ensure(re.sub(r'\s+', '', p['label']) in re.sub(r'\s+', '', native[-1]['text']), '感想填写提示需进入实际 PPTX')
        for value in answers.values():
            ensure(re.sub(r'\s+', '', value) in re.sub(r'\s+', '', native[-1]['text']), '演讲者填写内容需进入实际 PPTX')
    assets.extend(visual_policy.validate(data, base, native))
    focus_plan.validate(data)
    return list(dict.fromkeys(assets))

def reflection_notes(form):
    answers = form.get('answers', {})
    filled = [f"{p['label']}：{answers[p['id']].strip()}" for p in form['prompts'] if answers.get(p['id'], '').strip()]
    if filled:
        return '\n\n'.join(filled)
    directions = '、'.join(form['directions'])
    prompts = '、'.join('“'+p['label']+'”' for p in form['prompts'])
    return f"感想方向包括{directions}。{form['guidance']}填写内容依次为{prompts}。"

def assemble(brief, base):
    data = copy.deepcopy(brief)
    data['schema_version'] = 1
    data['deck']['report_type'] = 'literature'
    data['deck'].setdefault('style_policy', visual_policy.STYLE)
    data['deck'].setdefault('footer_policy','none')
    data['deck'].setdefault('design_theme','beamer_metropolis')
    if data['deck']['style_policy']==visual_policy.STYLE and data['deck'].get('mode')!='test_fixture':data['deck'].setdefault('focus_policy',focus_plan.POLICY)
    data['deck'].pop('render_receipt', None)
    c = data['literature']
    if c.get('flow_diagram',{}).get('status') == 'available':
        c['flow_diagram'].setdefault('display','whole_image')
    c.setdefault('presenter', {'name':'', 'affiliation':'', 'date':''})
    c.setdefault('author_policy', author_profile.POLICY)
    if c['author_policy'] == author_profile.POLICY:
        author_profile.configure(c, {s['id']:s for s in data['sources']}, data['deck'].get('mode') == 'test_fixture')
    c['title_capture']['sha256'] = image_asset(base, c['title_capture'])
    for a in c['authors']:
        a['portrait']['sha256'] = image_asset(base, a['portrait'])
    body = data.pop('body_slides')
    for s in body:
        ensure(s.get('section_key') in ORDER[2:-1], '正文页面需指定 Background 至 Disadvantages 对应的 section_key')
        s['section'] = LABELS[s['section_key']]
    source = next(s for s in data['sources'] if s['id'] == c['paper_source_id'])
    cover = dict(id='cover', section_key='cover', section=LABELS['cover'], title=c['cover_title'], question=c['cover_subtitle'], notes=c['cover_notes'], expected_text=[], required_objects=['text', 'image'], layout={'kind':'paper_cover'}, evidence=[{'source_id':c['paper_source_id'], 'claim':c['paper_title'], 'locator':'论文全文题名与作者区', 'status':source['identity_status']}])
    cover['expected_text'] = ['演讲者', '单位', '日期', *[c['presenter'][k] for k in ['name', 'affiliation', 'date'] if c['presenter'].get(k)]]
    author_evidence = [{'source_id':c['paper_source_id'], 'claim':c['author_note'], 'locator':'Author information / Article notes', 'status':source['identity_status']}]
    for a in c['authors']:
        author_evidence.append({'source_id':a['profile_source_id'], 'claim':f"{a['name']}，{a['affiliation']}，{a['position']}。", 'locator':a.get('profile_locator', '官网个人介绍'), 'status':a.get('verification_status','unverified'), 'image_transform':'使用来源页面公开照片，等比例展示。'})
    authors = dict(id='authors', section_key='authors', section=LABELS['authors'], title='作者简介', question=c['author_note'], notes=c['author_notes'], expected_text=[], required_objects=['text','image'], layout={'kind':'authors'}, evidence=author_evidence)
    if c['author_policy'] == author_profile.POLICY:
        author_profile.enrich_slide(authors, c)
    form = copy.deepcopy(c.get('reflection') or json.loads((ROOT/'assets/reflection-prompts.json').read_text()))
    reflection = dict(id='reflection', section_key='reflection', section=LABELS['reflection'], title='感想：连接自己的临床或研究问题', question=form['guidance'], notes=reflection_notes(form), expected_text=[p['label'] for p in form['prompts']], required_objects=['text'], layout={'kind':'reflection'}, reflection=form, evidence=[])
    data['slides'] = [cover, authors, *body, reflection]
    if data['deck']['style_policy'] == visual_policy.STYLE:
        cover.update(title='文献', subtitle='')
        cover['layout']['title_mode']='editable_title'
        cover['layout']['cover_composition']='split'
        cover['expected_text']=['期刊','IF','演讲者','日期',*[c['presenter'][k] for k in ['name','date'] if c['presenter'].get(k)]]
        journal=c.get('journal',{})
        if journal.get('name'):cover['expected_text'].append(journal['name'])
        metric=journal.get('impact_factor',{})
        if metric.get('value') is not None:
            cover['expected_text'] += [str(metric['value']),str(metric['year'])]
            cover['evidence'].append({'source_id':metric['source_id'],'claim':f"{journal['name']} 的 {metric['year']} 年 Journal Impact Factor 为 {metric['value']}。",'locator':'Journal Impact Factor / Journal Citation Reports','status':'verified'})
        cover['expected_text'].insert(0,c['paper_title'])
        authors.update(title='作者', subtitle='简介')
        reflection.update(title='感想', subtitle='选题方向')
        for slide in data['slides']:
            if slide['section_key']in ['advantages','disadvantages']:slide['title']=visual_policy.MAJORS[slide['section_key']]
            slide['section'] = visual_policy.MAJORS[slide['section_key']]
            if slide.get('subtitle'):slide.setdefault('expected_text',[]).append(slide['subtitle'])
    if data['deck'].get('focus_policy'):
        allocations=c.get('focus_plan',{}).get('allocation',{})
        for slide in data['slides']:
            if slide['id']in allocations:slide.update(copy.deepcopy(allocations[slide['id']]))
    data['checks'] = {k:{'status':'not_checked','note':'等待本版本生成与核对。'} for k in ['evidence','file','visual']}
    validate_literature(data, base)
    return data

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('brief',type=Path);p.add_argument('--out',type=Path,required=True)
    a=p.parse_args();brief=a.brief.resolve();out=a.out.resolve()
    ensure(brief.parent==out.parent, '内容记录与输入材料放在同一目录，保留相对资源路径')
    ensure(not out.exists(), '输出内容记录已存在，请使用新文件名')
    data=assemble(json.loads(brief.read_text()),brief.parent)
    out.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
    print(f'已按文献汇报流程编排 {len(data["slides"])} 页：{out}')

if __name__=='__main__':
    try: main()
    except (ValueError, KeyError, OSError) as e: raise SystemExit(str(e))
