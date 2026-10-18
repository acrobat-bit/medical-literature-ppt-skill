import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import {pathToFileURL} from 'node:url';

export async function finalizeDemo(out,candidate,font){
 const runtime=path.join(os.homedir(),'.cache/codex-runtimes/codex-primary-runtime/dependencies');
 let skill=process.env.ACADEMIC_SLIDES_PRESENTATIONS_DIR;
 if(!skill){const base=path.join(os.homedir(),'.codex/plugins/cache/openai-primary-runtime/presentations');
  const versions=(await fs.readdir(base)).sort((a,b)=>b.localeCompare(a,undefined,{numeric:true}));
  for(const v of versions){const p=path.join(base,v,'skills/presentations');try{await fs.access(path.join(p,'container_tools/artifact_tool_utils.mjs'));skill=p;break;}catch{}}
 }
 if(!skill)throw Error('缺少 Presentations finalizer；请设置 ACADEMIC_SLIDES_PRESENTATIONS_DIR。');
 process.env.RUNTIME_NODE_MODULES??=process.env.ACADEMIC_SLIDES_NODE_MODULES||path.join(runtime,'node/node_modules');
 process.env.RUNTIME_NODE??=process.execPath;
 const {finalizePresentation}=await import(pathToFileURL(path.join(skill,'container_tools/artifact_tool_utils.mjs')).href);
 const finalPath=path.join(out,'files/deck.pptx');
 await fs.mkdir(path.dirname(finalPath),{recursive:true});
 await finalizePresentation({workspaceDir:out,candidatePath:candidate,finalPath,
  pythonExecutable:process.env.ACADEMIC_SLIDES_PYTHON||path.join(runtime,'python/bin/python3'),
  integrityValidatorPath:path.join(skill,'container_tools/inspect_presentation_package_integrity.py'),
  layoutValidatorPath:path.join(skill,'container_tools/inspect_presentation_layout_geometry.py'),
  layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit','--require-native-table-slide','1'],
  explicitTotalSlideCount:3,requiredNativeTableOwnerSlides:[1],requiredNativeChartOwnerSlides:[2],
  materializeLiteralChartWorkbooks:true,fontPolicy:{basis:'design',families:[font]},
  verifyArtifactToolImport:true,receiptPath:path.join(out,'.build/validation.json')});
 return finalPath;
}
