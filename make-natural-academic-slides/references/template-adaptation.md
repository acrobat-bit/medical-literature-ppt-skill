# 按提供的模板 PPT 改版

使用者提供模板文件，助手完成识别、映射、替换、渲染和交付。用户可直接说：“用这个模板修改当前文献汇报。”现有演示文稿的研究内容和讲稿先与内容记录核对，已手工修改的内容合并到记录中。

## 模板检查

将模板保存到工作目录。PPTX、POTX 可直接导入；旧版 PPT 通过 PowerPoint 另存为 PPTX。调用 Presentations 技能，读取其模板跟随和最终验收流程，执行本次制作要求的操作记录。

```bash
node <skill>/scripts/template.mjs inspect template.pptx template-inspection
```

检查目录包含逐页 PNG、完整版式 JSON、`template.json` 摘要和 `mapping.json` 骨架。查看全部模板页，确定封面、作者、连续正文、横向原图、竖向原图和双图的布局。读取字号、字体、颜色、背景、页宽高、文字框与图片框位置，以及母版和布局中的固定元素。使用模板自己的尺寸。

## 版式映射

`mapping.json` 保存 `schema_version: 1`、检查时取得的 `template_sha256`、`layouts` 和 `slides`。通用版式按 `layout.kind` 映射，竖向原图用 `source_full:portrait`；`slides` 可按汇报中的稳定页 id 单独覆盖。每项记录模板页码 `slide`，页码从 1 开始。

`bind` 将内容角色绑定到模板对象。优先使用检查结果中的唯一 `name`；对象无名称时使用 `{"order": 3}`。`keep` 明确保留模板的固定文字、标识或图片，`remove` 明确删除示例内容。背景、母版和布局继续随复制页保留。每个带文字或图片的本页对象都需指定用途，避免模板示例进入文献汇报。整套页面去掉模板中的新增来源小字和页码，封面的题名、期刊、IF、演讲者、日期对应左侧文字槽位，title_capture 对应右侧图片槽位。旧版上下封面使用 presenter_affiliation 字段保持兼容。

```json
{
  "schema_version": 1,
  "template_sha256": "填写检查得到的模板哈希",
  "layouts": {
    "prose": {
      "slide": 3,
      "bind": {
        "major": "章节标题",
        "minor": "页面主题",
        "body": "正文"
      },
      "keep": ["机构标识"],
      "remove": ["示例说明", "页码"]
    }
  },
  "slides": {}
}
```

内容角色与填入的字段：

| 页面 | 必需角色 |
|---|---|
| 左右封面 | paper_title、journal、impact_factor、presenter_name、presenter_date、title_capture |
| 作者 | major、minor、portrait、author_identity、body |
| 正文与感想 | major、minor、body |
| 一张原图 | major、minor、body、source_1 |
| 两张原图 | major、minor、body、source_1、source_2 |

`deck.footer_policy: none` 时，整套页面的页脚来源行与页码对象加入 remove；母版内对应的小字在工作副本中清理。旧版记录可沿用 page 与 footer 槽位。所有角色各用一个独立对象。文字角色使用文本框，原图角色使用图片或图片占位形状。脚本替换文字并沿用槽位的字体、字号、颜色和位置；原图按比例完整置入图像框，保留源图像字节。感想内容由当前记录的引导或实际填写生成。

模板正文框的字号低于小标题，小标题字号低于大标题。根据内容长度选择足够宽高的正文框；若原模板只有一层标题，为此模板建立保留两级标题的工作副本。竖向完整流程图使用高幅图片框。论文原图中的文字在放映尺寸下清楚，拥挤时选择更合适的版式。PDF 局部选取按独立图像槽位安排后再适配。母版中的固定文字也要逐页核对，模板与论文的语境保持一致。

## 实际改版

```bash
node <skill>/scripts/template.mjs apply deck.json template.pptx template-inspection/mapping.json deck-template.json v2
python3 <skill>/scripts/review.py render deck-template.json --out rendered-template
python3 <skill>/scripts/review.py validate deck-template.json
python3 <skill>/scripts/review.py build deck-template.json --out delivery-template
```

输出记录放在原材料目录，使用新的文件名与版本号。脚本复制并填写对应模板页，保留模板背景、母版和固定元素，生成 `files/deck-template.pptx`。来源模板和映射复制到材料目录内的 `template/`，绑定哈希并随审阅包交付。原图仍来自已登记的论文 PDF，讲稿与证据继续写入备注。

模板检查和套用发生在 Skill 的本地制作流程。网页用于预览、查看证据和记录改版意见。收到新模板后，助手重新执行套用与渲染，交付对应的新网页。

## 验收

逐页对照模板预览，检查完整题名、两级标题、段落换行、原图完整性、固定标识及背景，确认示例文字已处理。检查最终 PPTX 的原生文字、图片哈希、备注、页数与页面顺序。检查网页显示的是新版 PPTX 的实际渲染，下载文件与当前版本一致。

实现维护时使用独立标记的测试模板，至少覆盖封面、作者、正文、横图和竖图，并验证不同页面尺寸、字体、配色及固定元素的保留。实际收到的用户模板仍逐页检查和适配。

模板中已有图片的替换同样采用原比例完整置入，继承槽位的范围并重新计算图片显示位置。验收同时比较源图宽高比、最终 PPTX 中图片框的宽高比与裁切参数，覆盖作者照片、题名截图及论文图表。原图完整保留，已有图片槽位和占位形状采用同一套适配方式。
