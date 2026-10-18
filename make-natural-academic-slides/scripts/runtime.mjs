import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';

export async function artifactModule() {
  const roots = [process.env.ACADEMIC_SLIDES_NODE_MODULES, path.join(os.homedir(), '.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules')].filter(Boolean);
  for (const root of roots) {
    const pkg = path.join(root, '@oai/artifact-tool/package.json');
    if (fs.existsSync(pkg)) {
      const req = createRequire(path.join(root, '../package.json'));
      return import(pathToFileURL(req.resolve('@oai/artifact-tool')).href);
    }
  }
  try { return await import('@oai/artifact-tool'); }
  catch { throw new Error('未找到 @oai/artifact-tool。请调用 load_workspace_dependencies，再设置 ACADEMIC_SLIDES_NODE_MODULES 为返回的包目录。'); }
}
