"""Validate evidence-backed highlights and their speaking emphasis."""
import re
POLICY='contribution_driven_v1'
DOMAINS={'question','method','interpretation','visual'}
SECTION_FOR={'question':{'background'},'method':{'methods'},'interpretation':{'results','discussion'},'visual':{'background','methods','results','discussion'}}

def require(ok,message):
    if not ok:raise ValueError(message)
def text(v):return isinstance(v,str)and bool(v.strip())

def validate(data):
    policy=data.get('deck',{}).get('focus_policy')
    if policy is None:return
    require(policy==POLICY,'讲述重点策略版本无效')
    plan=data.get('literature',{}).get('focus_plan');require(isinstance(plan,dict),'请先填写文章亮点判断与讲述重点')
    year=plan.get('publication_year');require(isinstance(year,int)and not isinstance(year,bool)and 1900<=year<=2100,'请记录本文发表年份')
    sources={s['id']:s for s in data.get('sources',[])};slides={s['id']:s for s in data['slides']}
    entries=plan.get('assessments');require(isinstance(entries,list)and entries,'请评估选题、方法、结论讨论和图表表达')
    require({e.get('domain')for e in entries}==DOMAINS,'亮点评估需覆盖选题、方法、结论讨论和图表表达')
    ids=set();primary=[]
    for e in entries:
        ident=e.get('id');require(isinstance(ident,str)and re.fullmatch(r'[a-z][a-z0-9_-]{0,39}',ident)and ident not in ids,'亮点判断 id 无效或重复');ids.add(ident)
        require(e.get('novelty')in {'new','incremental','established','unassessed'},'请区分新意、增量贡献与成熟做法')
        require(e.get('quality')in {'strong','adequate','mixed','unassessed'},'请记录具体完成质量判断')
        require(e.get('priority')in {'primary','secondary','routine'},'亮点优先级无效')
        require(all(text(e.get(k))for k in ['claim','what_new','what_well','why_it_matters']),'亮点需写清新增内容、优秀之处和实际价值')
        basis=e.get('evidence');require(isinstance(basis,list)and basis,'每项判断需有原文依据')
        for b in basis:require(b.get('source_id')in sources and text(b.get('locator')),'亮点依据需关联来源与位置')
        comparisons=e.get('comparisons',[])
        if e['novelty']in {'new','incremental'}:require(comparisons,'新颖性判断需与发表时已有研究比较')
        for c in comparisons:
            if c.get('source_id')in sources and sources[c['source_id']].get('publication_year') is not None:require(c.get('year')==sources[c['source_id']]['publication_year'],'比较年份需与来源记录一致')
            require(c.get('source_id')in sources and isinstance(c.get('year'),int)and c['year']<=year and text(c.get('difference')),'同期比较需有来源、年份及具体差别')
        linked=e.get('slide_ids',[]);require(isinstance(linked,list)and linked and all(s in slides for s in linked),'亮点需落实到实际页面')
        require(any(slides[s]['section_key']in SECTION_FOR[e['domain']]for s in linked),'讲述重点需落在相应的背景、方法、结果或讨论页')
        if e['domain']=='visual':require(any('figure' in b['locator'].lower()or'图' in b['locator']or'table' in b['locator'].lower()for b in basis),'图表亮点需定位到具体原图或原表')
        if e['priority']=='primary':
            primary.append(e)
            require(any(slides[s].get('emphasis')=='core'for s in linked),'主要亮点需对应重点讲述页面')
    require(1<=len(primary)<=3,'请选择 1–3 项主要亮点')
    require(text(plan.get('narrative_priority')),'请概括本次汇报的叙事重心')
    for s in slides.values():
        require(s.get('emphasis')in {'core','standard','brief'},'每页需标明重点、常规或简述')
        require(isinstance(s.get('talk_time_sec'),int)and not isinstance(s['talk_time_sec'],bool)and 5<=s['talk_time_sec']<=900,'请为每页填写合理的建议讲述时间')
        refs=s.get('focus_links',[]);require(isinstance(refs,list)and all(x in ids for x in refs),'页面亮点关联无效')
        if s['emphasis']=='core':require(refs,'重点页面需关联具体亮点判断')
    brief=[s['talk_time_sec']for s in slides.values()if s['emphasis']=='brief'];core=[s['talk_time_sec']for s in slides.values()if s['emphasis']=='core']
    if brief:require(core and sum(core)/len(core)>sum(brief)/len(brief),'重点页面的讲述时间需体现更充分的展开')
    require(any(s['section_key']=='advantages'and s['title']=='亮点'for s in slides.values()),'讨论后需设置文章亮点页')
    require(any(s['section_key']=='disadvantages'and s['title']=='局限'for s in slides.values()),'亮点后需设置局限页')

def render_text(data):
    validate(data)
    plan=data['literature']['focus_plan'];sources={s['id']:s for s in data['sources']}
    labels={'question':'选题','method':'方法','interpretation':'结论与讨论','visual':'图表表达'}
    priority={'primary':'主要亮点','secondary':'支持亮点','routine':'常规内容'}
    level={'core':'重点展开','standard':'常规说明','brief':'简述'}
    novelty={'new':'新贡献','incremental':'增量贡献','established':'成熟做法','unassessed':'待判断'}
    lines=['文章亮点与讲述重点',data['literature']['paper_title'],f"按 {plan['publication_year']} 年发表时的证据背景判断。",'',plan['narrative_priority'],'']
    for e in plan['assessments']:
        lines.extend([labels[e['domain']]+'（'+priority[e['priority']]+'）','新颖性：'+novelty[e['novelty']],'判断：'+e['claim'],'新增内容：'+e['what_new'],'优秀之处：'+e['what_well'],'实际价值：'+e['why_it_matters']])
        for b in e['evidence']:lines.append('依据：'+sources[b['source_id']]['citation']+'；'+b['locator'])
        for c in e.get('comparisons',[]):lines.append('既往研究比较：'+sources[c['source_id']]['citation']+'；'+c['difference'])
        lines.append('')
    lines.append('逐页讲述安排')
    for i,s in enumerate(data['slides'],1):lines.append(f"{i:02d} {s['title']}"+(f"：{s['subtitle']}"if s.get('subtitle')else'')+f"；{level[s['emphasis']]}，建议 {s['talk_time_sec']} 秒")
    lines+=['',f"建议总时长：{sum(s['talk_time_sec'] for s in data['slides'])/60:.1f} 分钟。",'讨论后依次为文章亮点、局限和演讲者感想。']
    return '\n'.join(lines)+'\n'
