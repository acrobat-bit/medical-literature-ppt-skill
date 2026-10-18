// Generate an editable, explicitly synthetic three-slide fixture from demo.json.
import fs from 'node:fs/promises';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {artifactModule} from '../scripts/runtime.mjs';
import {finalizeDemo} from '../scripts/finalize_demo.mjs';

const here=path.dirname(fileURLToPath(import.meta.url));
const out=path.resolve(process.argv[2]||'demo');
const font=process.env.ACADEMIC_SLIDES_FONT||'Hiragino Sans GB';
const {Presentation,PresentationFile}=await artifactModule();
await fs.mkdir(out,{recursive:true});
try {await fs.access(path.join(out,'files/deck.pptx'));throw Error('输出目录已有 deck.pptx，请使用新目录');}catch(e){if(e.code!=='ENOENT')throw e;}
const data=JSON.parse(await fs.readFile(path.join(here,'demo.json'),'utf8'));
const ppt=Presentation.create({slideSize:{width:1280,height:720}});
function text(slide,value,x,y,w,h,size=25,color='#263B33',bold=false){
 const shape=slide.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{style:'solid',fill:'none',width:0}});
 shape.text=value;shape.text.style={typeface:font,fontSize:size,color,bold};return shape;
}
for(const [i,s]of data.slides.entries()){
 const slide=ppt.slides.add();slide.background.fill='#FAFBF7';
 text(slide,s.title,72,58,1136,72,42,'#214C3C',true);
 text(slide,s.question,74,140,1120,52,22,'#5A6960');
 const l=s.layout;
 if(l.type==='table'){
  text(slide,l.intro,75,242,380,220,28);
  const table=slide.tables.add({rows:l.table.length,columns:3,left:510,top:226,width:690,height:302,columnWidths:[230,170,290],values:l.table});
  table.borders.assign({fill:'#D6DFD5',width:1,style:'solid'});
  for(let r=0;r<l.table.length;r++)for(let c=0;c<3;c++){
   const cell=table.getCell(r,c);cell.fill=r===0?'#DFE9DD':'#FFFFFF';cell.text.style={typeface:font,fontSize:23,color:'#263B33',bold:r===0};
  }
  text(slide,l.caption,510,555,690,65,18,'#58665D');
 }else if(l.type==='chart'){
  const chart=slide.charts.add('bar',{position:{left:64,top:225,width:745,height:345},categories:l.categories,series:[{name:'测试指标',values:l.values,fill:'#4B7B60'}],hasLegend:false,dataLabels:{showValue:true,position:'outEnd'},yAxis:{minimumScale:0,maximumScale:20,majorUnit:5,majorGridlines:{fill:'#D8DFD4',width:1}}});
  for(const style of [chart.legend?.textStyle,chart.dataLabels?.textStyle,chart.xAxis?.textStyle,chart.yAxis?.textStyle])if(style){style.typeface=font;style.fontSize=22;style.color='#263B33';}
  text(slide,l.intro,875,255,330,275,29);
  text(slide,l.caption,78,588,1080,45,19,'#58665D');
 }else{
  text(slide,l.left_title,76,244,510,55,29,'#214C3C',true);text(slide,l.left,76,325,510,220,25);
  text(slide,l.right_title,690,244,510,55,29,'#214C3C',true);text(slide,l.right,690,325,510,220,25);
 }
 text(slide,'医学文献汇报 · 演示数据',76,661,850,30,16,'#6A746D');
 text(slide,String(i+1).padStart(2,'0'),1150,657,58,32,18,'#6A746D');
 slide.speakerNotes.text=s.notes+'\n\n来源：'+data.sources[0].citation;
}
await fs.mkdir(path.join(out,'.build'),{recursive:true});
const candidate=path.join(out,'.build/candidate.pptx');
await(await PresentationFile.exportPptx(ppt)).save(candidate);
await finalizeDemo(out,candidate,font);
data.deck.pptx='files/deck.pptx';
await fs.writeFile(path.join(out,'deck.json'),JSON.stringify(data,null,2)+'\n');
console.log('已生成 3 页可编辑测试样张：'+out);
