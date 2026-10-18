"""Validate the original-source, two-heading literature layout."""
import hashlib
import math
from pathlib import Path
import re
STYLE='original_sources_two_levels'
MAJORS={'cover':'文献','authors':'作者','background':'背景','methods':'方法','results':'结果','discussion':'讨论','advantages':'亮点','disadvantages':'局限','reflection':'感想'}
ALLOWED={'paper_cover','authors','reflection','prose','source_image','source_pair','source_side','source_flow','source_full'}

def require(ok,message):
    if not ok:raise ValueError(message)
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def image_only_cover(slide):
    return slide.get('section_key')=='cover' and slide.get('layout',{}).get('kind')=='paper_cover' and slide['layout'].get('title_mode')=='source_image'
def editable_title_cover(slide):
    return slide.get('section_key')=='cover' and slide.get('layout',{}).get('kind')=='paper_cover' and slide['layout'].get('title_mode')=='editable_title'
def asset_file(base,name):
    require(isinstance(name,str)and name and not Path(name).is_absolute()and'\\'not in name,'原文素材使用材料目录内的相对路径')
    p=(base/name).resolve();require(p.is_relative_to(base.resolve())and p.is_file(),f'原文素材缺失或路径无效：{name}');return p

def check_native_image_ratio(asset,base,native):
    content=asset_file(base,asset['file']).read_bytes()
    if not content.startswith(b'\x89PNG\r\n\x1a\n'):return
    width=int.from_bytes(content[16:20],'big');height=int.from_bytes(content[20:24],'big')
    for image in native.get('image_crops',[]):
        if image['sha256']!=asset['sha256'] or not image.get('frame_size'):continue
        fw,fh=image['frame_size'];crop=image['crop'];cw=100000-crop['l']-crop['r'];ch=100000-crop['t']-crop['b']
        require(width>0 and height>0 and fw>0 and fh>0 and cw>0 and ch>0,'图片尺寸或裁切范围无效')
        require(abs((fw/fh)/(width*cw/(height*ch))-1)<.005,'原图宽高比与 PPTX 显示比例不一致，请按原比例完整置入')

def validate_pdf_source(asset,base):
    name=asset.get('source_pdf');pdf=asset_file(base,name)
    require(pdf.read_bytes().startswith(b'%PDF-')and sha(pdf)==asset.get('source_pdf_sha256'),'素材对应的原始 PDF 已变化')
    require(isinstance(asset.get('page'),int)and not isinstance(asset['page'],bool)and asset['page']>0,'请记录有效的 PDF 页码')
    return name

def validate(data,base,native=None):
    if data.get('deck',{}).get('style_policy')!=STYLE:return []
    files=[]
    template=data.get('deck',{}).get('template')
    if template:
        for field,digest in [('file','sha256'),('mapping','mapping_sha256')]:
            p=asset_file(base,template.get(field));require(sha(p)==template.get(digest),'模板或版式映射已变化，请重新生成');files.append(template[field])
        require(len(template.get('slides',[]))==len(data['slides']),'模板映射需覆盖整套幻灯片')
    source_ids={s['id']for s in data['sources']};bg=set();methods=set()
    for i,s in enumerate(data['slides']):
        cover=image_only_cover(s) or editable_title_cover(s)
        require(re.fullmatch(r'[\u4e00-\u9fff]{2}',s.get('title','')) is not None,'每页大标题使用两个汉字')
        accepted={MAJORS.get(s['section_key'])}
        if not data.get('deck',{}).get('focus_policy'):accepted.update({'advantages':{'优势'},'disadvantages':{'不足'}}.get(s['section_key'],set()))
        require(s['title']in accepted,'大标题需对应本页章节')
        if not cover:require(isinstance(s.get('subtitle'),str)and s['subtitle'].strip(),'每页需填写一个概括内容的小标题')
        layout=s.get('layout',{});kind=layout.get('kind');require(kind in ALLOWED,'当前文献版式使用原文图片与连续段落')
        require(not({'items','left_title','right_title','headline','labels','rows','values'}&set(layout)),'请将分点、分栏小标题和重建图表改为连续段落或原文截图')
        paragraphs=layout.get('paragraphs',[])
        require(isinstance(paragraphs,list)and all(isinstance(p,str)and p.strip()for p in paragraphs),'正文使用完整段落')
        for p in paragraphs:
            require(not re.search(r'(?m)^\s*(?:[-*]\s+|[•●▪]|\d+[.)、]\s*|[①②③④⑤⑥])',p),'正文采用连续叙述，移除分点标记')
        if s['section_key']=='background':
            require(kind=='prose'and paragraphs,'背景使用连续段落介绍内容');bg.update(s.get('background_coverage',[]))
        if s['section_key']=='methods':methods.update(s.get('method_coverage',[]))
        assets=s.get('source_images',[]);require(isinstance(assets,list),'原文图片记录需为列表')
        if kind in ['source_image','source_side','source_flow','source_full']:require(len(assets)==1,'本版式需关联一张原文截图')
        if kind=='source_pair':require(len(assets)==2,'双图版式需关联两张原图')
        for a in assets:
            p=asset_file(base,a.get('file'));files.append(a['file'])
            require(sha(p)==a.get('sha256'),'原文图片已变化，请重新核对截图')
            require(p.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')or p.read_bytes().startswith(b'\xff\xd8\xff'),'原文图片需为 PNG 或 JPEG')
            require(a.get('source_id')in source_ids and isinstance(a.get('locator'),str)and a['locator'].strip(),'原文图片需关联文献与具体图表位置')
            require(a.get('origin')in ['pdf_crop','pdf_image','article_image','full_text_capture'],'图表使用原文截图或原始图片')
            url=a.get('source_url','')
            if a['origin']in ['pdf_crop','pdf_image']:
                files.append(validate_pdf_source(a,base))
                require(not url or isinstance(url,str)and re.match(r'^https?://[^\s]+$',url),'PDF 来源链接请使用 http/https；本地提供的 PDF 可省略链接')
            else:require(isinstance(url,str)and re.match(r'^https?://[^\s]+$',url),'原文图片需保留来源链接')
            if 'crop_regions' in a:
                regions=a['crop_regions'];size=a.get('source_pixel_size',[])
                require(isinstance(size,list)and len(size)==2 and all(isinstance(v,int)and not isinstance(v,bool)and v>0 for v in size),'请记录原图像素尺寸')
                require(isinstance(regions,list)and 1<=len(regions)<=8,'原图裁切需记录 1–8 个区域')
                for box in regions:
                    require(isinstance(box,list)and len(box)==4 and all(isinstance(v,(int,float))and not isinstance(v,bool)and math.isfinite(v)for v in box)and 0<=box[0]<box[2]<=size[0]and 0<=box[1]<box[3]<=size[1],'原图裁切区域需位于原图范围内')
                if native is not None:
                    available=[v['crop']for v in native[i].get('image_crops',[])if v['sha256']==a['sha256']]
                    for x0,y0,x1,y1 in regions:
                        expected=dict(zip(('l','t','r','b'),(round(100000*v)for v in (x0/size[0],y0/size[1],1-x1/size[0],1-y1/size[1]))))
                        match=next((j for j,crop in enumerate(available)if all(abs(crop[k]-expected[k])<=2 for k in expected)),None)
                        require(match is not None,'实际 PPTX 的原图裁切与内容记录不一致')
                        available.pop(match)
            if a['origin']=='pdf_crop':
                require(a.get('page_rotation',0)in [0,90,180,270],'PDF 原页旋转角度无效')
                box=a.get('crop_points',[]);size=a.get('page_size_points',[])
                require(isinstance(a.get('page'),int)and a['page']>0 and len(box)==4 and len(size)==2 and 0<=box[0]<box[2]<=size[0]and 0<=box[1]<box[3]<=size[1],'请记录有效的原页页码与裁切位置')
            if a['origin']=='pdf_image':
                require(isinstance(a.get('image_index'),int)and not isinstance(a['image_index'],bool)and a['image_index']>0 and isinstance(a.get('image_name'),str)and a['image_name'].strip(),'PDF 内嵌图片需记录图像序号与名称')
                size=a.get('source_pixel_size',[])
                require(isinstance(size,list)and len(size)==2 and all(isinstance(v,int)and not isinstance(v,bool)and v>0 for v in size),'请记录原图像素尺寸')
            if native is not None:
                require(a['sha256']in native[i]['image_sha256'],'实际 PPTX 缺少已登记的原文图片')
                check_native_image_ratio(a,base,native[i])
        if native is not None:
            actual=native[i]
            if data.get('deck',{}).get('footer_policy')=='none':require(not actual.get('footer_texts'),'请移除整套页面底部的来源小字与页码')
            require(actual['objects']['chart']==0 and actual['objects']['table']==0,'当前文献汇报的图表需使用原文图片')
            expected_headings=([data['literature']['paper_title']] if editable_title_cover(s) else []) if cover else [s['title'],s['subtitle']]
            normalize=lambda text:re.sub(r'\s+','',text)
            if template:
                spec=template['slides'][i];require(spec.get('slide_id')==s['id'],'模板映射页面顺序已变化')
                slots=spec.get('slots',{});texts={x['name']:x for x in actual.get('text_shapes',[])}
                for role,slot in slots.items():
                    if slot['kind']=='text':
                        item=texts.get('academic-'+role);require(item and normalize(item['text'])==normalize(slot['text']),'模板中的原生文字与内容记录不一致：'+role)
                if editable_title_cover(s):
                    require(normalize(slots.get('paper_title',{}).get('text',''))==normalize(data['literature']['paper_title']),'封面需显示文献题名')
                    require('footer' not in slots and not spec.get('fixed_text'),'封面保留题名、补充原图与演讲者信息')
                elif not image_only_cover(s):
                    require(slots.get('major',{}).get('text')==s['title'] and slots.get('minor',{}).get('text')==s['subtitle'],'模板需保留两级学术标题')
                    major=texts['academic-major']['font_size'];minor=texts['academic-minor']['font_size']
                    require(major>minor,'大标题字号需大于小标题')
                    for role,slot in slots.items():
                        if role not in ['major','minor'] and slot['kind']=='text':require(texts['academic-'+role]['font_size']<minor,'正文与固定信息使用小于小标题的字号')
                for text in spec.get('fixed_text',[]):require(normalize(text) in normalize(actual['text']),'模板固定文字丢失')
            else:require(list(map(normalize,actual.get('heading_texts',[])))==list(map(normalize,expected_headings)),'封面显示可编辑文献题名，其余页保留大标题和小标题两级')
            require(actual.get('bullet_count',0)==0,'实际 PPTX 正文使用连续段落')
            expected_images=sum(len(a.get('crop_regions',[]))or 1 for a in assets)+(1 if s['section_key'] in ['cover','authors'] else 0)
            if template:expected_images+=template['slides'][i].get('fixed_image_count',0)
            require(actual['objects'].get('image',0)==expected_images,'实际 PPTX 图片需与原文素材及作者照片记录逐一对应')
    require({'progress','study_question'}<=bg,'背景需覆盖研究进展与本文研究问题；术语解释按听众需要安排')
    require({'workflow','participants','interventions','outcomes','statistics'}<=methods,'方法需覆盖研究流程、对象、干预、测量与统计分析')
    flow=data.get('literature',{}).get('flow_diagram')
    if flow is not None:
        require(isinstance(flow,dict)and flow.get('status')in ['available','not_found'],'请记录原文流程图检索结果')
        if flow['status']=='available':
            first=next(s for s in data['slides']if s['section_key']=='methods')
            require(flow.get('file')in [a['file']for a in first.get('source_images',[])]and'workflow'in first.get('method_coverage',[]),'原文流程图应放在方法部分第一页')
            require(flow.get('display')in [None,'whole_image','requested_crop'],'流程原图采用完整展示或用户指定的裁切方式')
            if flow.get('display')=='whole_image':
                require(len(first['source_images'])==1 and not first['source_images'][0].get('crop_regions'),'流程图默认使用一张完整原图')
                if native is not None:
                    actual=native[data['slides'].index(first)]
                    crops=[p['crop']for p in actual.get('image_crops',[])if p['sha256']==first['source_images'][0]['sha256']]
                    require(len(crops)==1 and all(v==0 for v in crops[0].values()),'实际 PPTX 的流程图需显示为一张完整原图')
    return list(dict.fromkeys(files))
