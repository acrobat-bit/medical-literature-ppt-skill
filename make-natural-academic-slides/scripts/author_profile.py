"""Select one author and bind inferred research themes to verified publications."""
POLICY = 'first_author_then_corresponding'

def require(condition, message):
    if not condition:
        raise ValueError(message)

def eligible_works(author, sources, paper_id, fixture=False):
    allowed = {'verified', 'test_fixture'} if fixture else {'verified'}
    paper = sources.get(paper_id, {})
    result = []
    for work in author.get('publications', []):
        source = sources.get(work.get('source_id'), {})
        same_doi = source.get('doi') and source['doi'].lower() == paper.get('doi', '').lower()
        same_pmid = source.get('pmid') and source['pmid'] == paper.get('pmid')
        if work.get('source_id') != paper_id and not same_doi and not same_pmid and work.get('status') in allowed and source.get('identity_status') in allowed:
            result.append(work)
    return result

def configure(config, sources, fixture=False):
    """Choose the first author whenever another verified work is available."""
    candidates = config.pop('author_candidates', config.get('authors', []))
    first_name = config.get('first_author_name')
    require(isinstance(first_name, str) and first_name.strip(), '请填写原文署名列首位的第一作者姓名')
    first = next((a for a in candidates if a.get('publication_name') == first_name), None)
    require(first is not None, '请提供第一作者的著作检索记录')
    first_works = eligible_works(first, sources, config['paper_source_id'], fixture)
    if first_works:
        selected, role = first, 'first_author'
    else:
        selected = next((a for name in config.get('corresponding_author_names', []) for a in candidates if a.get('publication_name') == name and eligible_works(a, sources, config['paper_source_id'], fixture)), None)
        require(selected is not None, '请继续检索通讯作者的发表文章并填写候选资料')
        role = 'corresponding_author'
    config['authors'] = [selected]
    config['author_selection'] = {'role':role, 'first_author_name':first_name, 'selected_name':selected['publication_name'], 'first_author_verified_other_works':[w['source_id'] for w in first_works]}

def validate(config, sources, fixture=False, native=None):
    if config.get('author_policy') != POLICY:
        return
    authors = config.get('authors', [])
    require(len(authors) == 1, '作者介绍页只展示一位作者')
    author = authors[0]
    selection = config.get('author_selection', {})
    role = selection.get('role')
    require(role in ['first_author', 'corresponding_author'], '作者选择需记录第一作者或通讯作者')
    require(selection.get('selected_name') == author.get('publication_name'), '作者选择记录与展示对象不一致')
    require(selection.get('first_author_name') == config.get('first_author_name'), '请保留原文第一作者姓名')
    search = config.get('author_search', [])
    first_search = [q for q in search if q.get('author_name') == config['first_author_name'] and q.get('status') == 'completed']
    require(first_search and all(isinstance(q.get('query'), str) and q['query'].strip() and q.get('searched_at') and q.get('source') for q in first_search), '请记录第一作者的实际检索式、来源和日期')
    first_works = selection.get('first_author_verified_other_works', [])
    require(isinstance(first_works, list), '第一作者著作关联需使用列表')
    if role == 'first_author':
        require(author['publication_name'] == config['first_author_name'] and first_works, '查到第一作者的其他著作后介绍第一作者')
    else:
        require(not first_works, '第一作者已有可确认的其他著作，介绍对象应为第一作者')
        require(author['publication_name'] in config.get('corresponding_author_names', []), '替代介绍对象需为本文通讯作者')
        require(len({q['source'] for q in first_search}) >= 2, '切换通讯作者前完成第一作者的数据库检索和补充检索')
    works = author.get('publications', [])
    verified = eligible_works(author, sources, config['paper_source_id'], fixture)
    require(works and len(verified) == len(works), '作者研究领域需使用已核对的其他发表文章')
    ids = [w['source_id'] for w in works]
    require(len(set(ids)) == len(ids), '作者发表文章重复')
    if role == 'first_author':
        require(set(first_works) == set(ids), '第一作者著作核对清单与展示资料不一致')
    shown = [w for w in works if w.get('on_slide', True)]
    require(1 <= len(shown) <= 3, '作者页展示 1–3 篇相关发表，完整清单保存于证据索引')
    for work in works:
        for key in ['title', 'display_title', 'journal', 'author_role']:
            require(isinstance(work.get(key), str) and work[key].strip(), f'作者发表记录缺少 {key}')
        require(isinstance(work.get('year'), int), '发表年份需为整数')
        require(work.get('author_name') == author['publication_name'], '发表记录中的作者姓名与介绍对象不一致')
        signals = work.get('identity_evidence', [])
        require(isinstance(signals, list) and len(signals) >= 2 and all(isinstance(x, str) and x.strip() for x in signals), '每篇发表需记录署名、机构或合作者等归属依据')
    areas = author.get('research_areas', [])
    require(isinstance(areas, list) and 1 <= len(areas) <= 3, '作者研究领域概括为 1–3 项')
    for area in areas:
        require(isinstance(area.get('label'), str) and area['label'].strip(), '研究领域需有名称')
        require(area.get('publication_ids') and set(area['publication_ids']) <= set(ids), '每个研究领域需关联已核对的发表文章')
    if native is not None:
        normalized = ''.join(native['text'].split())
        for text in [*[a['label'] for a in areas], *[w['display_title'] for w in shown]]:
            require(''.join(text.split()) in normalized, '作者研究领域或相关发表需进入实际 PPTX')

def enrich_slide(slide, config):
    """Populate visible claims and source links without adding more people."""
    author = config['authors'][0]
    slide['title'] = '作者简介'
    slide['footer'] = f"任职与照片：机构官网（{author['verified_at']} 核对）；研究领域据已发表论文归纳"
    for work in author['publications']:
        slide['evidence'].append({'source_id':work['source_id'], 'claim':f"{author['name']}以{work['author_role']}身份发表：{work['title']}", 'locator':'文章题名、作者署名、机构及摘要', 'status':work['status'], 'author_identity':'；'.join(work['identity_evidence'])})
        if work.get('on_slide', True):
            slide['expected_text'].append(work['display_title'])
    for area in author['research_areas']:
        slide['expected_text'].append(area['label'])
        for source_id in area['publication_ids']:
            status = next(w['status'] for w in author['publications'] if w['source_id'] == source_id)
            slide['evidence'].append({'source_id':source_id, 'claim':f"研究领域：{area['label']}", 'locator':'已核对论文的题名与摘要', 'status':status, 'interpretation':'依据作者已发表论文的研究主题归纳。'})
