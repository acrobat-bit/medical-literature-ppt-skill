import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {artifactModule} from './runtime.mjs';

const hash = b => crypto.createHash('sha256').update(b).digest('hex');
async function main() {
  const {PresentationFile, FileBlob} = await artifactModule();
  if (process.argv[2] === '--doctor') { console.log('PPTX 导入与渲染运行库可用'); return; }
  const [input, output] = process.argv.slice(2);
  if (!input || !output) throw new Error('使用方式：node render.mjs final.pptx new-render-dir');
  const source = path.resolve(input), out = path.resolve(output);
  try { await fs.access(out); throw new Error('输出目录已存在；请选择新目录。'); } catch(e) { if(e.code !== 'ENOENT') throw e; }
  const bytes = await fs.readFile(source);
  const presentation = await PresentationFile.importPptx(await FileBlob.load(source));
  const slides = presentation.slides.items;
  if (!slides?.length) throw new Error('导入的 PPTX 没有页面');
  await fs.mkdir(out, {recursive:true});
  const scale=Number(process.env.ACADEMIC_SLIDES_RENDER_SCALE||3);
  if(!Number.isFinite(scale)||scale<1||scale>4)throw new Error('预览倍率请设为 1–4');
  const receipt = {schema_version:1, pptx_sha256:hash(bytes), renderer:'@oai/artifact-tool · import final PPTX', render_scale:scale, rendered_at:new Date().toISOString(), slides:[]};
  for (const [i, slide] of slides.entries()) {
    const png = Buffer.from(await (await presentation.export({slide, format:'png', scale})).arrayBuffer());
    const file = `slide-${i+1}.png`;
    await fs.writeFile(path.join(out,file),png);
    receipt.slides.push({slide:i+1,file,sha256:hash(png)});
  }
  if (hash(await fs.readFile(source)) !== receipt.pptx_sha256) throw new Error('渲染过程中 PPTX 被修改，请重新渲染');
  await fs.writeFile(path.join(out,'render.json'), JSON.stringify(receipt,null,2)+'\n');
  console.log(`已重新导入并渲染 ${slides.length} 页`);
}
main().catch(e=>{console.error(e.message);process.exitCode=1;});
