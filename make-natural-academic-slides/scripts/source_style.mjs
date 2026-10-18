export const SOURCE_STYLE='original_sources_two_levels';
export function flowText(value,limit){
 const lines=[];for(const paragraph of value.split('\n')){let line='',width=0;for(const token of paragraph.match(/[A-Za-z0-9αβχ²]+(?:[A-Za-z0-9αβχ².\-–−/%±°<>≤≥=]+)*|\s+|./gu)||[]){const size=[...token].reduce((n,c)=>n+(/\s/.test(c)?.28:/[\u0000-\u00ff]/.test(c)?.56:1),0);if(line&&width+size>limit&&!/^[，。；：、？！）》”]$/.test(token)){lines.push(line.trim());line='';width=0;}line+=token;width+=size;}lines.push(line.trim());}return lines.join('\n');
}
export async function drawSourceStyle(s,r,D,{txt,pic,wrapText,C,F}){
 const l=r.layout,c=D.literature;
 const beamer=D.deck.design_theme==='beamer_metropolis';
 const imageOnlyCover=r.section_key==='cover'&&l.kind==='paper_cover'&&l.title_mode==='source_image';
 const editableCover=r.section_key==='cover'&&l.kind==='paper_cover'&&l.title_mode==='editable_title';
 if(!imageOnlyCover&&!editableCover){
  if(beamer){const head=txt(s,r.title,0,0,1280,94,42,C.paper,true);head.fill=C.ink;head.text.style={typeface:F,fontSize:42,color:C.paper,bold:true,insets:{left:72,right:72,top:19,bottom:12},verticalAlignment:'top',wrap:'none'};}
  else txt(s,r.title,72,42,1136,60,44,C.green,true);
  txt(s,r.subtitle,74,116,1130,48,30,C.ink,false);
 }
 function prose(paragraphs,x=78,y=218,w=1124,bottom=650,size=27,gap=28){
  for(const text of paragraphs){const formatted=flowText(text,Math.floor(w/size*.90)),height=formatted.split('\n').length*size*1.45+4;if(y+height>bottom)throw Error(`第 ${r.id} 页正文较长，请拆页：${y+height} > ${bottom}`);txt(s,formatted,x,y,w,height,size,C.ink,false,'none');y+=height+gap;}
 }
 async function sourcePicture(asset,x,y,w,h){
  if(!asset.crop_regions?.length)return pic(s,asset.file,x,y,w,h,asset.locator);
  const [sw,sh]=asset.source_pixel_size,regions=asset.crop_regions;
  const left=Math.min(...regions.map(a=>a[0])),top=Math.min(...regions.map(a=>a[1]));
  const right=Math.max(...regions.map(a=>a[2])),bottom=Math.max(...regions.map(a=>a[3]));
  const scale=Math.min(w/(right-left),h/(bottom-top));
  const ox=x+(w-(right-left)*scale)/2,oy=y+(h-(bottom-top)*scale)/2;
  for(const [i,[x0,y0,x1,y1]]of regions.entries()){
   await pic(s,asset.file,ox+(x0-left)*scale,oy+(y0-top)*scale,(x1-x0)*scale,(y1-y0)*scale,asset.locator+' · 区域 '+(i+1),{left:x0/sw,top:y0/sh,right:1-x1/sw,bottom:1-y1/sh});
  }
 }
 if(l.kind==='paper_cover'){
  const p=c.presenter||{};
  if(editableCover&&l.cover_composition==='split'){
   let size=38,title=flowText(c.paper_title,Math.floor(610/size*.90));
   while(title.split('\n').length>5&&size>34){size-=2;title=flowText(c.paper_title,Math.floor(610/size*.90));}
   if(title.split('\n').length>5)throw Error('文献题名较长，请调整封面左侧标题框');
   txt(s,title,76,82,610,250,size,C.green,true,'none');
   const journal=c.journal||{},metric=journal.impact_factor||{};
   txt(s,flowText('期刊：'+(journal.name||'________________'),23),78,365,610,75,25,C.ink,false,'none');
   txt(s,metric.value===undefined?'IF：待填写':`IF：${metric.value}（${metric.year} 年）`,78,458,610,40,25,C.ink);
   txt(s,'演讲者：'+(p.name||'________________'),78,548,610,42,26,C.ink);
   txt(s,'日期：'+(p.date||'____________'),78,608,610,38,24,C.muted);
   await pic(s,c.title_capture.file,742,160,474,420,'论文原文题名补充图片');
  }else{
   if(editableCover){
    let size=44,title=flowText(c.paper_title,Math.floor(1104/size*.90));
    while(title.split('\n').length>3&&size>34){size-=2;title=flowText(c.paper_title,Math.floor(1104/size*.90));}
    if(title.split('\n').length>4)throw Error('文献题名较长，请调整封面标题框');
    txt(s,title,88,66,1104,210,size,C.green,true,'none');
    await pic(s,c.title_capture.file,330,295,620,215,'论文原文题名补充图片');
   }else await pic(s,c.title_capture.file,150,imageOnlyCover?148:199,980,300,'论文原文题名截图');
   txt(s,'演讲者：'+(p.name||'________________'),290,552,880,42,26,C.ink);
   txt(s,'单位：'+(p.affiliation||'________________________'),290,605,520,36,23,C.muted);
   txt(s,'日期：'+(p.date||'____________'),870,605,340,36,23,C.muted);
  }
 }else if(l.kind==='authors'){
  const a=c.authors[0];await pic(s,a.portrait.file,76,214,320,214,a.name+' 公开照片');
  prose([a.name+'\n'+a.contribution+'\n'+a.position+'\n'+a.affiliation],76,457,336,654,24,16);
  const areas=a.research_areas.map(x=>x.label).join('、');
  const pubs=a.publications.filter(w=>w.on_slide!==false).map(w=>`${w.year} 年以${w.author_role}发表《${w.display_title}》（${w.journal}）`).join('；')+'。';
  prose(a.profile_paragraphs||[`其已发表研究涉及${areas}。`,pubs],450,214,758,650,24,27);
 }else if(l.kind==='reflection'){
  const f=r.reflection;const introduction='可以选择'+f.directions.join('、')+'，把论文中的一个发现与自己的工作联系起来，再提出下一步要验证的问题。';
  const filled=f.prompts.some(p=>f.answers?.[p.id]);const writing=filled?f.prompts.map(p=>p.label+'：'+(f.answers?.[p.id]||'待填写')+'。').join(''):'填写时可以依次回应“'+f.prompts.map(p=>p.label).join('”、“')+'”，每个部分用一两句话展开。';
  prose([introduction,writing],78,232,1124,650,27,46);
 }else if(l.kind==='prose'){
  prose(l.paragraphs);
 }else if(l.kind==='source_image'){
  await sourcePicture(r.source_images[0],76,207,1128,320);
  prose(l.paragraphs,78,540,1124,658,25,16);
 }else if(l.kind==='source_pair'){
  for(let j=0;j<2;j++)await sourcePicture(r.source_images[j],82+j*588,207,526,330);
  prose(l.paragraphs,78,565,1124,653,25,16);
 }else if(l.kind==='source_side'){
  await sourcePicture(r.source_images[0],90,207,300,435);
  prose(l.paragraphs,450,224,755,650,26,30);
 }else if(l.kind==='source_flow'){
  await sourcePicture(r.source_images[0],78,211,500,420);
  prose(l.paragraphs,628,225,576,650,26,32);
 }else if(l.kind==='source_full'){
  if(l.orientation==='portrait'){
   await sourcePicture(r.source_images[0],718,beamer?184:40,486,beamer?480:620);
   prose(l.paragraphs,78,228,560,650,25,30);
  }else{
   await sourcePicture(r.source_images[0],76,188,1128,420);
   prose(l.paragraphs,78,620,1124,660,23,16);
  }
 }else throw Error('该版式需要原文图片或连续段落');
 if(!editableCover&&D.deck.footer_policy!=='none')txt(s,r.footer||c.cover_footer||r.section,76,677,1090,25,15,C.muted);
}
