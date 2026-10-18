import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {pathToFileURL} from 'node:url';
import {artifactModule} from './runtime.mjs';
import {drawSourceStyle,SOURCE_STYLE} from './source_style.mjs';
const record=path.resolve(process.argv[2]||'deck.json'),W=path.dirname(record);
const D=JSON.parse(await fs.readFile(record,'utf8'));
if(D.deck.report_type!=='literature')throw Error('请先使用 literature.py 编排文献汇报');
const mappedKinds=new Set(['paper_cover','authors','prose','reflection','source_full','source_image','source_side','source_pair']);
if(D.deck.design_theme==='beamer_metropolis'&&D.deck.style_policy===SOURCE_STYLE&&D.slides.every(s=>mappedKinds.has(s.layout.kind)&&!(s.source_images||[]).some(a=>a.crop_regions?.length))){
 const {applyDefaultTemplate}=await import('./template.mjs');
 await applyDefaultTemplate(record);
 process.exit(0);
}
const finalPath=path.resolve(W,D.deck.pptx);
if(!finalPath.startsWith(W+path.sep))throw Error('PPTX 请保存在材料目录内');
try{await fs.access(finalPath);throw Error('PPTX 已存在，请为新版使用新路径');}catch(e){if(e.code!=='ENOENT')throw e;}
const {Presentation,PresentationFile}=await artifactModule();
const P=Presentation.create({slideSize:{width:1280,height:720}});
const F=process.env.ACADEMIC_SLIDES_FONT||'Hiragino Sans GB',C=D.deck.design_theme==='beamer_metropolis'?{ink:'#23373B',green:'#23373B',muted:'#748287',paper:'#FAFAFA',soft:'#EFF2F2',line:'#CCD4D5',grey:'#748287',amber:'#EB811B'}:{ink:'#25392F',green:'#205B45',muted:'#58685E',paper:'#FAFBF7',soft:'#E3ECE1',line:'#CCD7CC',grey:'#8C9C95',amber:'#855B25'};
const sourceMap=new Map(D.sources.map(s=>[s.id,s]));
function txt(s,value,x,y,w,h,size=25,color=C.ink,bold=false,wrap='square'){const b=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{style:'solid',fill:'none',width:0}});b.text=value;b.text.style={typeface:F,fontSize:size,color,bold,insets:0,verticalAlignment:'top',wrap};return b;}
function wrapText(value,limit=29){
 const lines=[];for(const paragraph of value.split('\n')){let line='',width=0;for(const token of paragraph.match(/[A-Za-z0-9]+(?:[.\-/%±][A-Za-z0-9]+)*|\s+|./gu)||[]){const size=[...token].reduce((n,c)=>n+(/\s/.test(c)?.28:/[\u0000-\u00ff]/.test(c)?.56:1),0);if(line&&width+size>limit&&!/^[，。；：、？！）]$/.test(token)){lines.push(line.trim());line='';width=0;}line+=token;width+=size;}lines.push(line.trim());}if(lines.length>1&&lines.at(-1).length<6){const last=lines.pop(),prior=lines.pop(),comma=Math.max(prior.lastIndexOf('，'),prior.lastIndexOf('；'));const cut=comma>prior.length/2?comma+1:Math.max(1,prior.length-8);lines.push(prior.slice(0,cut),prior.slice(cut)+last);}return lines.join('\n');
}
function table(s,rows,x,y,width,height,widths,size=24){const t=s.tables.add({rows:rows.length,columns:rows[0].length,left:x,top:y,width,height,columnWidths:widths,values:rows});t.borders.assign({style:'solid',fill:C.line,width:1});for(let r=0;r<rows.length;r++)for(let c=0;c<rows[r].length;c++){const cell=t.getCell(r,c);cell.fill=r===0?C.soft:'#FFFFFF';cell.text.style={typeface:F,fontSize:size,color:C.ink,bold:r===0};}return t;}
async function pic(s,file,x,y,w,h,alt,crop){const resolved=path.resolve(W,file);if(!resolved.startsWith(W+path.sep))throw Error('图片路径越出材料目录');const bytes=await fs.readFile(resolved);s.images.add({blob:bytes,contentType:bytes[0]===0x89?'image/png':'image/jpeg',alt:alt||path.basename(file),fit:crop?'cover':'contain',...(crop?{crop}:{}),position:{left:x,top:y,width:w,height:h}});}
function chart(s,l){const c=s.charts.add('bar',{position:{left:68,top:252,width:660,height:340},categories:l.categories,series:[{name:l.unit,values:l.values,fill:C.green,points:[{idx:0,fill:C.green},{idx:1,fill:C.grey}]}],barOptions:{direction:'column',grouping:'clustered',gapWidth:100},hasLegend:false,xAxis:{textStyle:{fontSize:23,fill:C.ink},line:{style:'solid',fill:C.line,width:1}},yAxis:{min:0,max:l.max,majorUnit:l.step,textStyle:{fontSize:20,fill:C.muted},majorGridlines:{style:'solid',fill:C.line,width:1},line:{style:'solid',fill:C.line,width:1}},dataLabels:{showValue:true,position:'outEnd',numberFormatCode:l.number_format||'0.0',textStyle:{fontSize:26,bold:true,fill:C.ink}},chartFill:'none',plotAreaFill:'none'});for(const st of[c.legend?.textStyle,c.dataLabels?.textStyle,c.xAxis?.textStyle,c.yAxis?.textStyle])if(st)st.typeface=F;txt(s,l.unit,80,211,650,32,20,C.muted);}
for(const[i,r]of D.slides.entries()){
 const s=P.slides.add();s.background.fill=C.paper;const l=r.layout,c=D.literature;
 if(D.deck.style_policy===SOURCE_STYLE){
  await drawSourceStyle(s,r,D,{txt,pic,wrapText,C,F});
 }else if(l.kind==='paper_cover'){
  txt(s,r.title,72,43,1136,112,43,C.green,true);txt(s,r.question,74,154,1120,35,23,C.muted);
  await pic(s,c.title_capture.file,150,202,980,300,'论文全文题名、作者与刊期截图');
  const presenter=c.presenter||{};
  txt(s,'演讲者：'+(presenter.name||'________________'),290,552,880,42,26,C.ink);
  txt(s,'单位：'+(presenter.affiliation||'________________________'),290,605,520,36,23,C.muted);
  txt(s,'日期：'+(presenter.date||'____________'),870,605,340,36,23,C.muted);
  if(D.deck.footer_policy!=='none')txt(s,c.cover_footer,76,677,1090,25,15,C.muted);
 }else{
  txt(s,r.title,70,50,1140,70,42,C.green,true);txt(s,r.question,72,130,1135,60,22,C.muted);
  if(l.kind==='authors'){
   if(c.author_policy==='first_author_then_corresponding'){
    const a=c.authors[0];
    await pic(s,a.portrait.file,76,214,320,214,a.name+' 公开照片');
    txt(s,a.name,76,451,336,44,29,C.green,true);
    txt(s,a.contribution,76,506,336,42,21,C.muted);
    txt(s,a.position,76,551,336,37,25);
    txt(s,a.affiliation,76,599,336,54,21);
    txt(s,'研究领域',460,207,740,40,28,C.green,true);
    a.research_areas.forEach((area,j)=>txt(s,area.label,460,253+j*39,744,38,24));
    txt(s,'相关发表',460,389,744,39,27,C.green,true);
    a.publications.filter(w=>w.on_slide!==false).forEach((work,j)=>{
     const y=439+j*74,src=sourceMap.get(work.source_id);
     txt(s,`${work.year}  ${work.display_title}`,460,y,744,36,22,C.ink,true);
     txt(s,`${work.journal}，${work.author_role}。${src.doi?'DOI '+src.doi:'PMID '+src.pmid}`,460,y+36,744,27,17,C.muted);
    });
   }else{
   const n=c.authors.length,w=1124/n,gap=30;
   for(const[aIndex,a]of c.authors.entries()){const x=76+aIndex*w;await pic(s,a.portrait.file,x+12,214,w-gap-24,214,a.name+' 公开照片');txt(s,a.name,x,449,w-gap,43,31,C.green,true);txt(s,a.contribution,x,499,w-gap,36,21,C.muted);txt(s,a.position,x,546,w-gap,36,25);txt(s,a.affiliation,x,592,w-gap,58,21);}
   }
  }else if(l.kind==='reflection'){
   const f=r.reflection;txt(s,'可选方向：'+f.directions.join(' / '),76,214,1120,42,26,C.green,true);
   for(const[j,p]of f.prompts.entries()){const y=283+j*(f.prompts.length>3?88:116);txt(s,p.label,78,y,1100,36,27,C.green,true);txt(s,f.answers?.[p.id]||p.hint,78,y+43,1100,62,f.answers?.[p.id]?25:21,f.answers?.[p.id]?C.ink:C.muted);}
  }else if(l.kind==='points'){
   if(!l.items?.length||l.items.length>4)throw Error('points 版式支持 1–4 项，长内容请拆页');
   const step=l.items.length<=3?132:105;
   l.items.forEach((item,j)=>{txt(s,item.heading,76,220+j*step,270,70,28,C.green,true);txt(s,wrapText(item.body),378,220+j*step,820,95,25);});
  }else if(l.kind==='table'){
   const height=l.rows.length>5?375:300;table(s,l.rows,75,218,1130,height,l.widths,24);if(l.note)txt(s,l.note,78,218+height+28,1120,64,25);if(l.caption)txt(s,l.caption,78,631,1120,34,18,C.muted);
  }else if(l.kind==='columns_table'){
   txt(s,l.left_heading,76,220,530,65,28,C.green,true);txt(s,l.left_text,76,313,540,240,25);table(s,l.rows,674,215,530,300,l.widths,23);txt(s,l.note,674,550,530,75,21,C.muted);
  }else if(l.kind==='comparison'){
   txt(s,l.left_title,76,211,540,48,30,C.green,true);txt(s,l.right_title,686,211,520,48,30,C.ink,true);l.left.forEach((v,j)=>txt(s,`${j+1}. ${v}`,76,282+j*66,535,62,25));l.right.forEach((v,j)=>txt(s,`${j+1}. ${v}`,686,282+j*66,520,62,25));txt(s,l.shared||'',76,523,1124,80,23);txt(s,l.caption||'',76,615,1124,32,19,C.muted);
  }else if(l.kind==='image_pair'){
   for(let j=0;j<2;j++){const x=100+j*595;txt(s,l.labels[j],x,193,490,42,27,C.green,true);await pic(s,l.images[j],x+32,244,380,355,l.labels[j]);txt(s,l.captions[j],x,615,500,36,23);}
  }else if(l.kind==='image_detail'){
   await pic(s,l.image,95,193,310,425,l.caption);txt(s,l.headline,450,211,744,58,35,C.green,true);l.lines.forEach((v,j)=>txt(s,v,452,294+j*50,740,45,25));txt(s,l.formula||'',452,537,740,88,25);txt(s,l.caption||'',80,631,360,30,17,C.muted);
  }else if(l.kind==='bar'){
   chart(s,l);txt(s,l.headline,792,224,416,100,32,C.green,true);txt(s,l.detail,792,343,416,197,24);txt(s,l.extra||'',792,549,416,80,22,l.extra_tone==='issue'?C.amber:C.ink);txt(s,l.caption||'',78,635,1120,32,18,C.muted);
  }else throw Error('未知文献版式：'+l.kind);
  if(D.deck.footer_policy!=='none')txt(s,r.footer||r.section,76,677,1090,25,15,C.muted);
 }
 if(D.deck.footer_policy!=='none'&&l.title_mode!=='editable_title')txt(s,String(i+1).padStart(2,'0'),1170,676,50,28,18,C.muted);
 s.speakerNotes.text=r.notes+'\n\n'+r.evidence.map(e=>{const src=sourceMap.get(e.source_id);return '来源：'+src.citation+'\n位置：'+e.locator+'\n'+(src.url||'');}).join('\n\n');
}
await fs.mkdir(path.join(W,'.build'),{recursive:true});await fs.mkdir(path.dirname(finalPath),{recursive:true});
const buildDir=await fs.mkdtemp(path.join(W,'.build/literature-'));
const candidate=path.join(buildDir,'candidate.pptx');await(await PresentationFile.exportPptx(P)).save(candidate);
const runtime=path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies');
let skill=process.env.ACADEMIC_SLIDES_PRESENTATIONS_DIR;
if(!skill){const base=path.join(os.homedir(),'.codex/plugins/cache/openai-primary-runtime/presentations');for(const v of(await fs.readdir(base)).sort((a,b)=>b.localeCompare(a,undefined,{numeric:true}))){const candidate=path.join(base,v,'skills/presentations');try{await fs.access(path.join(candidate,'container_tools/artifact_tool_utils.mjs'));skill=candidate;break;}catch{}}}
if(!skill)throw Error('请设置 ACADEMIC_SLIDES_PRESENTATIONS_DIR');
process.env.RUNTIME_NODE_MODULES??=process.env.ACADEMIC_SLIDES_NODE_MODULES||path.join(runtime,'node/node_modules');process.env.RUNTIME_NODE??=process.execPath;
const{finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
const tableSlides=D.slides.flatMap((s,i)=>s.required_objects.includes('table')?[i+1]:[]),chartSlides=D.slides.flatMap((s,i)=>s.required_objects.includes('chart')?[i+1]:[]);
await finalizePresentation({workspaceDir:W,candidatePath:candidate,finalPath,pythonExecutable:process.env.ACADEMIC_SLIDES_PYTHON||path.join(runtime,'python/bin/python3'),integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit',...tableSlides.flatMap(n=>['--require-native-table-slide',String(n)])],explicitTotalSlideCount:D.slides.length,requiredNativeTableOwnerSlides:tableSlides,requiredNativeChartOwnerSlides:chartSlides,materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'design',families:[F]},verifyArtifactToolImport:true,receiptPath:path.join(buildDir,'validation.json')});
await fs.writeFile(path.join(W,'.build/latest-generation.json'),JSON.stringify({receipt:path.relative(W,path.join(buildDir,'validation.json')),pptx:D.deck.pptx},null,2));
console.log(`已生成 ${D.slides.length} 页可编辑文献汇报：${finalPath}`);
