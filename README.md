# 医学文献汇报 PPT Skill

**Medical Literature Presentation Skill · v1.0 · for Codex**

从一篇医学论文的 PDF 出发，组织有重点的文献汇报，生成**可编辑 PPTX、逐页讲稿、证据索引与离线网页审阅台**。适用于医学文献汇报、Journal Club 与科室学术交流，已用真实骨科论文完成端到端试用。

[下载 v1.0 安装包](dist/medical-literature-ppt-skill-v1.0.zip?raw=1) · [Skill 入口](make-natural-academic-slides/SKILL.md) · [运行说明](make-natural-academic-slides/references/runtime.md)

## 亮点

### 1. 按文章的实际贡献分配重点

先评价选题、方法、结论讨论与图表表达，再安排页面和讲述时间。方法的新意明确落到测量、研究设计、算法或统计思路的具体改进，并结合论文发表时的已有研究比较。常规随机化、盲法、回归分析等按基础研究质量解释；具有实质贡献的部分获得更充分的展开。

### 2. 直接使用论文 PDF 中的高清原图

支持使用者提供 PDF，也支持根据题名、DOI 或链接获取全文。优先提取内嵌图片的原生像素，矢量图、原表及题名区默认按 600 dpi 截取。原图保留坐标、表头、图例与脚注；论文提供研究流程图时，将完整原图放到方法部分第一页。

### 3. 内容可以直接讲给听众

默认顺序为封面、作者简介、背景、方法、结果、讨论、亮点、局限与感想。背景通常集中一页，结果提炼关键发现，讨论和评价解释研究意义与具体影响。使用两级标题和连续段落，逐页讲稿补充推理与过渡，内容直接表达事实和分析。

### 4. PPT、讲稿与网页审阅保持一致

标题和正文保留 PowerPoint 原生可编辑文字，逐页讲稿写入备注。网页预览由最终 PPTX 重新导入并渲染，绑定文件哈希、页序和内容版本。交付同时包含讲稿、来源索引与可再次生成的内容记录。

### 5. 离线审阅形成修改闭环

浏览器中查看实际页面、放大原图、阅读讲稿和证据，并逐页填写修改意见。意见自动保存在当前浏览器，可导出 JSON 或 Markdown 交回 Codex，按稳定页面 ID 修改并生成下一版。感想页提供填写方向，也支持演讲者自定主题。

### 6. 自带学术模板，支持自定义模板

内置 Beamer Metropolis 风格的 16:9 可编辑模板，包含六种版式。封面左侧为完整题名、期刊、IF 与年份、演讲者和日期，右侧为原文题名图。使用者也可提供 PPTX/POTX，由 Skill 读取真实版式并映射内容。

![Beamer 风格封面模板](docs/images/template-cover.png)

## 安装

1. 下载并解压 [v1.0 安装包](dist/medical-literature-ppt-skill-v1.0.zip?raw=1)。
2. macOS 双击文件夹内的 `安装到Codex.command`；也可在解压目录运行：

   ```bash
   python3 make-natural-academic-slides/scripts/install.py
   ```

3. 在 Codex 新聊天中使用 `$make-natural-academic-slides`。

安装位置为 `$CODEX_HOME/skills`，默认 `~/.codex/skills`。安装器会识别内容相同的已安装版本；已有其他版本时保留原目录，并提供备份或另选安装目录的操作提示。

也可下载本仓库源码，在仓库根目录执行同一条安装命令。

## 使用示例

上传论文 PDF 后发送：

```text
$make-natural-academic-slides
用这篇论文制作 15 分钟的医学文献汇报。
先判断文章的主要亮点，再分配各部分篇幅。
生成可编辑 PPT、逐页讲稿和网页审阅台。
```

按提供的模板制作：

```text
使用这份 PPT 作为模板。保留完整原图，重点展开本文有新意的
研究设计与统计分析；讨论后安排亮点和局限，最后给出感想填写方向。
```

根据审阅意见修改：

```text
按我导出的审阅意见 JSON 更新这份汇报，保留已确认的研究数据，
同步生成新版 PPT、讲稿、证据索引和网页审阅台。
```

## 工作方式

这是由 Codex 执行的 Skill：助手负责阅读原文、检索作者资料、判断研究贡献并组织内容；随附脚本负责 PDF 素材处理、PPTX 生成与模板映射、渲染、审阅页构建和文件一致性检查。

```text
论文 PDF → 原文核对与亮点评价 → 内容记录与版式规划
       → 可编辑 PPTX + 讲稿 → 最终 PPTX 渲染 → 离线审阅台
       → 修改意见与感想导出 → 下一版生成
```

论文读取、网页检索与模型调用由 Codex 环境处理；生成后的审阅 HTML 可离线查看。修改意见保存在当前浏览器，通过导出的 JSON 迁移。

## 环境与检查

已在 macOS 的 Codex 桌面环境验证。完整制作流程使用 Codex 的 Presentations 技能及配套运行库：

| 功能 | 环境 |
| --- | --- |
| 网页构建、校验与本地服务 | Python 3.10+ 标准库 |
| 可编辑 PPTX 制作与渲染 | Node 18+、Codex 配套 `@oai/artifact-tool` |
| PDF 提图与高清截取 | pypdf、pdfplumber、Pillow、Poppler |
| 中文字体 | 默认 Hiragino Sans GB，可设置环境中已安装的字体 |

诊断命令：

```bash
python3 make-natural-academic-slides/scripts/review.py doctor
```

版本 v1.0 已完成安装包完整性、独立目录安装、文件一致性、PPTX 渲染、模板映射及网页导航和意见导出等检查。每次实际汇报仍按本次论文与成品记录证据、文件和视觉三类检查结果。

## 仓库内容

```text
make-natural-academic-slides/
  SKILL.md                 Skill 入口
  agents/                  Codex 展示信息
  scripts/                 生成、提图、模板、渲染、构建与安装
  references/              研究评价、内容、证据及视觉规范
  assets/                  离线审阅界面与 Beamer 默认模板
  examples/                明确标记的演示数据
  tests/                   关键流程检查
dist/                      v1.0 安装包
docs/images/               通用模板预览
```

## 模板来源

默认模板采用 [Beamer Metropolis](https://github.com/matze/mtheme) 的学术视觉样式，由原主题适配为原生 PowerPoint 版式。原主题、适配模板及对应预览遵循 CC BY-SA 4.0，作者、原始源码和改动说明保留在 [第三方说明](THIRD_PARTY_NOTICES.md) 与模板目录中。
