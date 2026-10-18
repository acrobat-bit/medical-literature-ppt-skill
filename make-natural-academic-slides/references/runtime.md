# 内容记录与运行

## 依赖

网页构建、校验和查看均在本机完成。构建需 Python 3.10+；HTML 已内嵌图片和下载文件，浏览器可直接打开。

`render` 重新导入最终 PPTX，需要 Node 18+ 和 Codex 自带 `@oai/artifact-tool`。先执行 `python3 scripts/review.py doctor`。默认识别 Codex 桌面配套运行库；找不到时调用 `load_workspace_dependencies`，将返回的 Node 和模块目录分别设为 `ACADEMIC_SLIDES_NODE`、`ACADEMIC_SLIDES_NODE_MODULES`。使用工具返回的运行库路径。

网页预览默认按 3 倍尺寸重新渲染最终 PPTX（1280 × 720 画布对应 3840 × 2160），用于放大查看密集原表和流程图。ACADEMIC_SLIDES_RENDER_SCALE 可设为 1–4；PDF 预览保持对应的页面尺寸。

可选 PDF 是渲染图片合成的预览，需要 Pillow；Pillow 可用时生成 PDF，并显示下载入口。使用 Codex 配套 Python 即可。正式编辑使用 PPTX。渲染图由最终 PPTX 导入生成，原生 PowerPoint 的检查结果单独记录。

PDF 内嵌图片提取使用 pypdf 与 Pillow；原页高清截取使用 pdfplumber、Pillow 和 Poppler。优先使用 load_workspace_dependencies 返回的配套运行库。本地提供的 PDF 使用文件与页码追溯，source_url 可省略。操作见 [PDF 素材流程](source-materials.md)。

## 快速试运行

在自己的新工作目录执行，下文 `<skill>` 为安装目录：

```bash
node <skill>/examples/make_demo.mjs demo
python3 <skill>/scripts/review.py render demo/deck.json --out demo/rendered
python3 <skill>/scripts/review.py validate demo/deck.json
python3 <skill>/scripts/review.py build demo/deck.json --out demo-delivery
python3 <skill>/scripts/review.py serve demo-delivery --open
```

测试样张的制作使用当前 Presentations 的 finalizer；默认识别配套版本，可显式设置 `ACADEMIC_SLIDES_PRESENTATIONS_DIR` 和 `ACADEMIC_SLIDES_PYTHON`。Mac 默认使用已安装的 Hiragino Sans GB；其他设备用 `ACADEMIC_SLIDES_FONT` 指定实际存在的中文字体。同时检查字体安装情况与 PPTX 字体设置。

直接打开 `demo-delivery/index.html` 即可查看。`serve` 使用本机地址 127.0.0.1，并由系统分配空闲端口。临时测试服务器用 Ctrl+C 停止。

## 内容记录

`schema_version` 为 1。见 `examples/demo.json` 的完整例子；真实任务移除 `mode: test_fixture` 和所有演示内容。

| 字段 | 要求 |
|---|---|
| deck.id | 文稿长期稳定 id，字母/数字/下划线/短横线 |
| deck.title / version | 显示名称、明确版本；内容变更时递增版本 |
| deck.pptx | 内容记录所在目录内的相对 PPTX 路径 |
| deck.render_receipt | `render` 自动写入，指向渲染凭据 |
| sources | id、citation、identity_status；可选 DOI/PMID、http(s) url |
| slides | 顺序与 PPTX 一致；id 长期稳定且唯一 |
| 每页字段 | id、section、title、question、notes、evidence |
| expected_text | 必须出现在该页的关键文字与数值字符串；与标题一起对账，封面对账可编辑文献题名、演讲者字段及截图哈希 |
| required_objects | 可选 `text`、`table`、`chart`、`image`；实际检查原生对象 |
| evidence | claim、source_id、locator、status；其他医学字段见证据规范 |
| checks | evidence/file/visual，各含 status、note；已执行检查绑定 pptx_sha256 |

`layout` 供自带样张生成器使用。真实文件可由 Presentations 的任意合适流程制作；更新 `deck.json` 使其准确对应最终文件即可。

文献汇报的 `deck.report_type` 为 `literature`，扩展字段和通用生成器见 [文献汇报流程](literature-report.md)。普通汇报继续使用已有结构。文献汇报交付包同时携带标题截图与作者图片，方便重新验证和生成。

使用材料目录内的相对路径，外部文件先复制进工作目录。构建时检查预览、图片、页数、顺序、声明文字、讲稿、页面 id、来源关联和核查记录。交付版本单独保存。

## 修改与交付

网页意见 JSON 包含文稿 id、版本、内容指纹、PPTX 哈希，以及每页稳定 id、页码、标题、意见、时间和处理标记。只对完全匹配版本导入；冲突替换由页面明确询问。导出的 Markdown 适合直接交给 Codex。

感想以可选 `reflections` 数组保存：slide_id、direction、custom_topic、answers、updated_at。answers 的键来自页面 reflection.prompts[].id。JSON 和文字导出同时包含意见与感想，导入旧版意见文件会保留已有感想。

收到反馈先核对导出标识，再修改源内容和实际 PPT。保留既有版本；新版重新渲染并重新构建，按本次执行情况更新核查状态。如果只改了讲稿/证据记录，内容指纹也会变化，保持意见与内容版本对应。

交付目录有 `index.html`、PPTX、可选 PDF、notes.md、sources.json、deck.json、rendered/、validation.json 和启动器。单个 HTML 可独立拷贝查看与下载；整目录/ZIP 保留可重建材料。意见保存在当前浏览器中，可通过 JSON 文件迁移。

## 测试与安装

```bash
python3 <skill>/tests/test_review.py --record demo/deck.json
python3 <skill>/scripts/install.py
```

安装器默认安装到 `$CODEX_HOME/skills`（未设置时 `~/.codex/skills`），已有不同版本会保留；可指定 `--root /path/to/skills`。已有内容相同时返回已安装。新版本请先备份旧目录，再指定空位置；保留用户修改。

安装规范：[OpenAI Skills 文档](https://developers.openai.com/codex/skills)。若技能选择器尚未刷新，先尝试在新聊天中使用完整名称；只有仍不可见时再刷新或重开应用。
