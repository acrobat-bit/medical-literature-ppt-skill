# Beamer Metropolis 初始模板

分发包仅内置通用 Beamer 模板。使用者的机构模板作为项目材料单独处理。

新建医学文献汇报默认使用 Beamer Metropolis 风格的可编辑 PPTX。样式来自 Metropolis 1.2：浅色背景、深色标题栏、简洁无衬线文字和明确留白。保留用户已确定的两级标题、连续段落、左右封面与原文完整图表；底部页码、导航符号和新增来源小字省去。

assets/beamer-metropolis/template.pptx 包含封面、作者、连续正文、竖图、横图及双图六种版式，mapping.json 供生成器填写。中文使用 Hiragino Sans GB，模板尺寸为 1280×720。普通图表使用原始 PDF 素材；图像槽位按原比例完整置入。原始 LaTeX 模板压缩包与设计来源记录一同保存。

literature.py 为新内容记录设置 deck.design_theme: beamer_metropolis。make_literature.mjs 自动填写内置模板，将模板和映射复制进项目，并保持文稿 id、版本、PPTX 路径和讲稿对应关系。显式调用 template.mjs apply 时使用提供的模板，并标记 provided_template。早期记录保留原有绘制路径；明确指定局部选取的原图沿用原图绘制功能及同一 Beamer 配色。

来源：https://ctan.org/pkg/beamertheme-metropolis 和 https://github.com/matze/mtheme 。原始设计：Matthias Vogelgesang 与贡献者。模板及改编遵循 CC-BY-SA-4.0；出处和具体改编说明保存在随包 NOTICE.txt。论文内容的来源继续保存在讲稿和证据索引。
