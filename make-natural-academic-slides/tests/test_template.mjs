import assert from 'node:assert/strict';
import {rolesFor,ruleFor} from '../scripts/template.mjs';
const c={paper_title:'An actual title',presenter:{name:'Dr A'},title_capture:{file:'title.png'},authors:[]};
const D={literature:c};
const cover={section_key:'cover',layout:{kind:'paper_cover'}};
const p=rolesFor(D,cover,0);assert.equal(p.values.paper_title,c.paper_title);assert.equal(p.values.presenter_name,'演讲者：Dr A');assert.equal(p.images.title_capture,c.title_capture);assert.deepEqual(p.optional,{});
const r={id:'flow',section_key:'methods',title:'方法',subtitle:'研究流程',section:'方法',layout:{kind:'source_full',orientation:'portrait',paragraphs:['先入组。','再随访。']},source_images:[{file:'flow.png',sha256:'123'}]};
const a=rolesFor(D,r,3);assert.equal(a.values.body,'先入组。\n\n再随访。');assert.equal(a.images.source_1.file,'flow.png');assert.equal(a.optional.page,'04');
const map={layouts:{'source_full:portrait':{slide:4,bind:{body:'text'}}},slides:{flow:{slide:5,bind:{body:'text'}}}};
assert.equal(ruleFor(map,r).slide,5);delete map.slides.flow;assert.equal(ruleFor(map,r).slide,4);assert.throws(()=>ruleFor({},r),/请配置页面版式/);
assert.throws(()=>rolesFor(D,{...r,source_images:[{crop_regions:[[1,2,3,4]]}]},3),/局部选取/);
console.log('Template roles, exact cover title, presenter fields, whole-source image, portrait mapping and per-slide overrides passed.');

const split=rolesFor({literature:{...c,journal:{name:"NEJM",impact_factor:{value:84.5,year:2025}}}},{...cover,layout:{kind:"paper_cover",cover_composition:"split"}},0);
assert.equal(split.values.journal,"期刊：NEJM");assert.equal(split.values.impact_factor,"IF：84.5（2025 年）");assert.equal("presenter_affiliation" in split.values,false);
console.log("Split cover journal, IF year, presenter and date roles passed.");
