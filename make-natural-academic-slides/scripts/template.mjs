import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import os from 'node:os';
import {pathToFileURL,fileURLToPath} from 'node:url';
import {artifactModule} from './runtime.mjs';
import {flowText} from './source_style.mjs';

export const sha=bytes=>crypto.createHash('sha256').update(bytes).digest('hex');
const ensure=(ok,message)=>{if(!ok)throw Error(message);};
const read=async file=>JSON.parse(await fs.readFile(file,'utf8'));
const write=async(file,data)=>fs.writeFile(file,JSON.stringify(data,null,2)+'\n');
const own=layout=>layout.elements.filter(e=>e.scope==='slide'&&e.editable!==false);
async function fresh(file){try{await fs.access(file);throw Error('输出已存在，请为新版使用新路径：'+file);}catch(e){if(e.code!=='ENOENT')throw e;}}
async function layoutOf(slide){return JSON.parse(await(await slide.export({format:'layout',detail:'full'})).text());}
function select(elements,selector){
 const matches=elements.filter(e=>typeof selector==='string'?e.name===selector:e.order===selector?.order);
 ensure(matches.length===1,'模板对象需唯一匹配：'+JSON.stringify(selector));return matches[0];
}
export function rolesFor(D,r,index){
 const c=D.literature,values={},images={};
 if(r.section_key==='cover'){
  values.paper_title=c.paper_title;
  const p=c.presenter||{};
  values.presenter_name='演讲者：'+(p.name||'________________');
  if(r.layout.cover_composition==='split'){
   const j=c.journal||{},m=j.impact_factor||{};
   values.journal='期刊：'+(j.name||'________________');
   values.impact_factor=m.value===undefined?'IF：待填写':`IF：${m.value}（${m.year} 年）`;
  }else values.presenter_affiliation='单位：'+(p.affiliation||'________________________');
  values.presenter_date='日期：'+(p.date||'____________');
  images.title_capture=c.title_capture;
 }else{
  values.major=r.title;values.minor=r.subtitle;
  if(r.section_key==='authors'){
   const a=c.authors[0];images.portrait=a.portrait;
   values.author_identity=[a.name,a.contribution,a.position,a.affiliation].join('\n');
   values.body=(a.profile_paragraphs||['其已发表研究涉及'+a.research_areas.map(x=>x.label).join('、')+'。',a.publications.filter(w=>w.on_slide!==false).map(w=>`${w.year} 年以${w.author_role}发表《${w.display_title}》（${w.journal}）`).join('；')+'。']).join('\n\n');
  }else if(r.section_key==='reflection'){
   const f=r.reflection;
   const first='可以选择'+f.directions.join('、')+'，把论文中的一个发现与自己的工作联系起来，再提出下一步要验证的问题。';
   const filled=f.prompts.some(p=>f.answers?.[p.id]);
   const second=filled?f.prompts.map(p=>p.label+'：'+(f.answers?.[p.id]||'待填写')+'。').join(''):'填写时可以依次回应“'+f.prompts.map(p=>p.label).join('”、“')+'”，每个部分用一两句话展开。';
   values.body=first+'\n\n'+second;
  }else values.body=(r.layout.paragraphs||[]).join('\n\n');
  for(const [i,a]of(r.source_images||[]).entries()){
   ensure(!a.crop_regions?.length,'模板改版的原图槽位使用完整图片，请为局部选取另建对应图像槽位。');images['source_'+(i+1)]=a;
  }
 }
 return {values,images,optional:r.section_key==='cover'||D.deck?.footer_policy==='none'?{}:{footer:r.footer||c.cover_footer||r.section,page:String(index+1).padStart(2,'0')}};
}
export function ruleFor(map,r){
 const key=r.layout.kind+(r.layout.orientation?':'+r.layout.orientation:'');
 const rule=map.slides?.[r.id]||map.layouts?.[key]||map.layouts?.[r.layout.kind];
 ensure(rule&&Number.isInteger(rule.slide)&&rule.slide>0&&rule.bind,'请配置页面版式：'+r.id+' / '+key);return rule;
}
async function inspect(file,out){
 await fresh(out);const bytes=await fs.readFile(file);
 ensure(bytes[0]===0x50&&bytes[1]===0x4b,'请将 .ppt 在 PowerPoint 另存为 .pptx 后导入。');
 const{PresentationFile,FileBlob}=await artifactModule();
 const P=await PresentationFile.importPptx(await FileBlob.load(file));
 await fs.mkdir(out,{recursive:true});
 const report={schema_version:1,file:path.basename(file),sha256:sha(bytes),slide_size:P.slides.items[0].frame,slides:[]};
 for(const[i,s]of P.slides.items.entries()){
  const l=await layoutOf(s);await write(path.join(out,`slide-${i+1}.json`),l);
  const png=Buffer.from(await(await s.export({format:'png',scale:1.5})).arrayBuffer());
  await fs.writeFile(path.join(out,`slide-${i+1}.png`),png);
  report.slides.push({slide:i+1,preview:`slide-${i+1}.png`,layout:`slide-${i+1}.json`,background:l.slide.backgroundColor,elements:own(l).map(e=>({order:e.order,name:e.name,kind:e.kind,text:e.text,position:e.position,style:e.style})),inherited:l.inheritedLayers});
 }
 await write(path.join(out,'template.json'),report);
 await write(path.join(out,'mapping.json'),{schema_version:1,template_sha256:report.sha256,layouts:{},slides:{}});
 console.log('已生成模板预览、对象位置和映射文件：'+out);
}
async function finalize(candidate,finalPath,W,count,families,size,receipt,template){
 const runtime=path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies');
 let skill=process.env.ACADEMIC_SLIDES_PRESENTATIONS_DIR;
 if(!skill){const base=path.join(os.homedir(),'.codex/plugins/cache/openai-primary-runtime/presentations');for(const v of(await fs.readdir(base)).sort((a,b)=>b.localeCompare(a,undefined,{numeric:true}))){const p=path.join(base,v,'skills/presentations');try{await fs.access(path.join(p,'container_tools/artifact_tool_utils.mjs'));skill=p;break;}catch{}}}
 ensure(skill,'请设置 ACADEMIC_SLIDES_PRESENTATIONS_DIR');
 process.env.RUNTIME_NODE_MODULES??=process.env.ACADEMIC_SLIDES_NODE_MODULES||path.join(runtime,'node/node_modules');process.env.RUNTIME_NODE??=process.execPath;
 const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
 await finalizePresentation({workspaceDir:W,candidatePath:candidate,finalPath,pythonExecutable:process.env.ACADEMIC_SLIDES_PYTHON||path.join(runtime,'python/bin/python3'),integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu',`${Math.round(size.width*9525)},${Math.round(size.height*9525)}`,'--validate-heading-fit'],explicitTotalSlideCount:count,fontPolicy:{basis:'reference',families,referencePath:template,referenceSha256:sha(await fs.readFile(template))},verifyArtifactToolImport:true,receiptPath:receipt});
}
async function apply(record,template,mapping,out,version,options={}){
 const W=path.dirname(record),D=await read(record),map=await read(mapping),templateBytes=await fs.readFile(template);
 ensure(D.deck.report_type==='literature'&&D.deck.style_policy==='original_sources_two_levels','模板改版使用原文图片与连续段落的文献记录');
 ensure(map.schema_version===1&&map.template_sha256===sha(templateBytes),'模板文件已变化，请重新检查版式映射');
 ensure(path.dirname(out)===W,'新版内容记录与原记录放在同一材料目录');
 if(options.inPlace)ensure(out===record&&version===D.deck.version,'默认模板保留当前内容版本');else await fresh(out);
 ensure(version&&(options.inPlace||version!==D.deck.version),'请填写新的版本号');
 const outputName=path.basename(out,'.json');const finalPath=options.inPlace?path.resolve(W,D.deck.pptx):path.join(W,'files',outputName+'.pptx');
 ensure(finalPath.startsWith(W+path.sep),'PPTX 请保存在材料目录内');await fresh(finalPath);
 const{PresentationFile,FileBlob}=await artifactModule();const P=await PresentationFile.importPptx(await FileBlob.load(template));
 const originals=[...P.slides.items],made=[],manifest=[],families=new Set();
 for(const[i,r]of D.slides.entries()){
  const rule=ruleFor(map,r),source=originals[rule.slide-1];ensure(source,'模板页码超出范围：'+rule.slide);
  const slide=source.duplicate();slide.moveTo(P.slides.items.length-1);
  const l=await layoutOf(slide),elements=own(l),payload=rolesFor(D,r,i);
  for(const layer of l.inheritedLayers||[])for(const e of layer.elements||[])if(e.text?.trim()&&e.style?.typeface)families.add(e.style.typeface);
  const required=[...Object.keys(payload.values),...Object.keys(payload.images)];
  ensure(required.every(k=>rule.bind[k]),'模板页面缺少内容槽位：'+r.id+' / '+required.filter(k=>!rule.bind[k]).join(', '));
  ensure(Object.keys(rule.bind).every(k=>required.includes(k)||k in payload.optional),'模板页面含多余内容槽位：'+r.id);
  const used=new Set(),bound={},fixedText=[],fixedImages=[];
  for(const[role,selector]of Object.entries(rule.bind)){
   const e=select(elements,selector);ensure(!used.has(e.id),'模板槽位重复使用：'+role);used.add(e.id);
   const target=P.resolve(e.id);const before={position:e.position,style:e.style};
   if(role in payload.images){
    ensure(['image','shape','textbox'].includes(e.kind),'图片槽位请使用图片或占位形状：'+role);
    const asset=payload.images[role],file=path.resolve(W,asset.file);ensure(file.startsWith(W+path.sep),'图片路径越出材料目录');
    const bytes=await fs.readFile(file);ensure(sha(bytes)===asset.sha256,'原图已变化：'+asset.file);
    P.delete(e.id);
    slide.images.add({name:'academic-'+role,blob:bytes,contentType:bytes[0]===0x89?'image/png':'image/jpeg',alt:asset.locator||role,fit:'contain',position:e.position});
    bound[role]={kind:'image',sha256:asset.sha256,...before};
   }else{
    ensure(['textbox','shape'].includes(e.kind),'文字槽位请使用原生文本框：'+role);
    const text=payload.values[role]??payload.optional[role];target.name='academic-'+role;
    const size=e.style?.fontSize||24,insets=e.style?.insets||{};
    const width=e.position.width-(insets.left||0)-(insets.right||0),height=e.position.height-(insets.top||0)-(insets.bottom||0);
    const formatted=flowText(text,Math.max(1,Math.floor(width/size*.90)));
    ensure(formatted.split('\n').length*size*1.25<=height+size*.2,'第 '+(i+1)+' 页 '+role+' 的文字框空间较小，请选择更宽或更高的模板版式');
    target.text=formatted;target.text.style={...e.style,wrap:'none'};
    if(e.style?.typeface)families.add(e.style.typeface);
    bound[role]={kind:'text',text,...before};
   }
  }
  const keep=new Set((rule.keep||[]).map(sel=>select(elements,sel).id));
  const remove=new Set((rule.remove||[]).map(sel=>select(elements,sel).id));
  for(const e of elements){
   ensure(!(used.has(e.id)&&(keep.has(e.id)||remove.has(e.id)))&&!(keep.has(e.id)&&remove.has(e.id)),'模板对象的用途重复：'+e.order);
   if(used.has(e.id))continue;
   if(remove.has(e.id)){P.delete(e.id);continue;}
   const content=Boolean(e.text?.trim())||['image','chart','table'].includes(e.kind);
   ensure(!content||keep.has(e.id),'请为模板对象配置保留或删除：第 '+rule.slide+' 页对象 '+e.order);
   ensure(!['chart','table'].includes(e.kind),'文献改版保留原文图表，请移除模板示例图表');
   if(e.kind==='image'){const obj=P.resolve(e.id);obj.name='template-decoration-'+e.order;fixedImages.push(e.order);}
   if(e.text?.trim()){fixedText.push(e.text);if(e.style?.typeface)families.add(e.style.typeface);}
  }
  const sources=new Map(D.sources.map(s=>[s.id,s]));
  slide.speakerNotes.text=r.notes+'\n\n'+r.evidence.map(e=>{const s=sources.get(e.source_id);return '来源：'+s.citation+'\n位置：'+e.locator+'\n'+(s.url||'');}).join('\n\n');
  const after=await layoutOf(slide);made.push(after.slide.id);
  manifest.push({slide_id:r.id,template_slide:rule.slide,slots:bound,fixed_text:fixedText,fixed_image_count:fixedImages.length,background:l.slide.backgroundColor});
 }
 P.slides.keep(made);P.slides.reorder(made);
 await fs.mkdir(path.join(W,'.build'),{recursive:true});const buildDir=await fs.mkdtemp(path.join(W,'.build/template-'));
 await fs.mkdir(path.dirname(finalPath),{recursive:true});const candidate=path.join(buildDir,'candidate.pptx');
 await(await PresentationFile.exportPptx(P)).save(candidate);
 const typographySource=path.join(buildDir,'source-template.pptx');await fs.writeFile(typographySource,templateBytes);
 await finalize(candidate,finalPath,W,D.slides.length,[...families],P.slides.items[0].frame,path.join(buildDir,'validation.json'),typographySource);
 const templateDir=path.join(W,'template',outputName);await fs.mkdir(templateDir,{recursive:true});
 const templateCopy=path.join(templateDir,'source.pptx'),mapCopy=path.join(templateDir,'mapping.json');await fs.writeFile(templateCopy,templateBytes);await fs.copyFile(mapping,mapCopy);
 D.deck.version=version;D.deck.pptx=path.relative(W,finalPath);delete D.deck.render_receipt;
 if(!options.inPlace)D.deck.design_theme='provided_template';
 D.deck.template={file:path.relative(W,templateCopy),sha256:sha(templateBytes),mapping:path.relative(W,mapCopy),mapping_sha256:sha(await fs.readFile(mapCopy)),slide_size:P.slides.items[0].frame,slides:manifest};
 for(const r of D.slides)if(r.section_key==='cover'){r.layout.title_mode='editable_title';r.subtitle='';if(!r.expected_text.includes(D.literature.paper_title))r.expected_text.unshift(D.literature.paper_title);}
 D.checks={evidence:{...D.checks.evidence,pptx_sha256:sha(await fs.readFile(finalPath))},file:{status:'not_checked',note:'模板版本已生成，待完成文件复核。'},visual:{status:'not_checked',note:'模板版本已生成，待逐页对照模板预览。'}};
 await write(out,D);await write(path.join(buildDir,'template-receipt.json'),D.deck.template);
 console.log('已按模板生成 '+D.slides.length+' 页：'+finalPath+'\n新版内容记录：'+out);
}
export async function applyDefaultTemplate(record){
 const root=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../assets/beamer-metropolis');
 const D=await read(record);
 await apply(record,path.join(root,'template.pptx'),path.join(root,'mapping.json'),record,D.deck.version,{inPlace:true});
}
export async function main(args=process.argv.slice(2)){
 const [command,...a]=args;
 if(command==='inspect'&&a.length===2)return inspect(path.resolve(a[0]),path.resolve(a[1]));
 if(command==='apply'&&a.length===5)return apply(...a.slice(0,4).map(v=>path.resolve(v)),a[4]);
 throw Error('用法：template.mjs inspect 模板.pptx 检查目录\n或：template.mjs apply deck.json 模板.pptx mapping.json deck-new.json 新版本号');
}
if(process.argv[1]&&path.resolve(process.argv[1])===path.resolve(fileURLToPath(import.meta.url)))main().catch(e=>{console.error(e.message);process.exitCode=1;});
