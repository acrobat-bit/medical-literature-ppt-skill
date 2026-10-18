# 从 PDF 获取论文素材

## 取得论文 PDF

优先使用使用者提供的 PDF。已提供题名、DOI、论文链接或选题方向时，自行查找并下载正式全文；文件和论文信息都缺少时，请使用者提供 PDF 或论文标识。核对题名、作者、刊期及 DOI，确认版本后保存到材料目录的 source/，记录文件校验值。补充材料按需取得对应的补充 PDF。

网页检索到取得 PDF 即完成论文素材搜集入口，后续图片、原表和封面题名都从保存的 PDF 获取。作者照片与任职资料沿用 [作者介绍流程](author-profile.md)。

PMC 正式全文可通过官方 [PMC Cloud Service](https://pmc.ncbi.nlm.nih.gov/tools/pmcaws/) 获取：

```bash
python3 <skill>/scripts/source_assets.py fetch-pmc PMC11541113 --doi 10.1111/os.14196 --out source/article.pdf
```

工具查询实际版本，核对 DOI，读取官方 PDF 链接并核对校验值。多份候选版本时使用 --version 选择正式发表版本。本地提供的 PDF 直接进入提取步骤；source_url 可省略，出处由 source_id、source_pdf、source_pdf_sha256 和页码记录。

## 提取 PDF 内嵌图片

先列出 PDF 页码、图像序号和原生像素尺寸，再对照原页与图注确定所需图像。页码和图像序号从 1 开始：

```bash
python3 <skill>/scripts/source_assets.py inspect-pdf source/article.pdf
python3 <skill>/scripts/source_assets.py extract-image source/article.pdf --page 3 --image 1 --out assets/figure-1.jpg --root . --source-id paper --locator "Figure 1，原刊第 2734 页"
```

使用 inspect-pdf 返回的扩展名。提取命令保存图片与 .asset.json，记录 PDF 校验值、页码、图像序号、对象名称及原生像素尺寸。JPEG/PNG 提取结果直接写出，其他格式按原生尺寸保存为 PNG。下载所得 PDF 可另加 --source-url 记录原始下载链接。

对照原页检查完整图例、坐标、箭头和面板。矢量文字、线条、额外标注或多个面板分别存储在页面中时，改用原页整图截取，使这一张图片保留全部内容。

## 截取原表、矢量图和题名

查看 PDF 原页，确定完整图表范围，再按页面左上角为原点的点数记录坐标。默认 600 dpi，按实际放映尺寸调整 --dpi。横向排版的原表可使用 --rotate 90，先将 PDF 页转为正向阅读，再以旋转后页面的坐标填写 --bbox；记录仍绑定原始 PDF、原页码与 page_rotation。示例：

```bash
python3 <skill>/scripts/source_assets.py crop source/article.pdf --page 6 --bbox 40,481,555,566 --out assets/table-1.png --root . --source-id paper --locator "Table 1，原刊第 2737 页"
```

截图与 .asset.json 同时保存，包含原页、范围、导出分辨率、PDF 校验值和图片校验值。题名截图使用 --kind excerpt，研究图使用 --kind figure；原表默认 kind 为 table。封面 title_capture 使用 kind: pdf，并保留原始 PDF、页码与范围。

完整保留题名、表头、所有数据列、图例与脚注。原表过密时按用户的展示要求安排版面与页数。正文仍用短段落提炼重要信息。

提取与截取使用 load_workspace_dependencies 返回的 Python：内嵌图片提取依赖 pypdf 和 Pillow，原页截取依赖 pdfplumber、Pillow 与配套 Poppler。工具均保持原文内容。

## 高清原图与清晰度

内嵌图片采用原生像素；矢量图和原表采用原页高清渲染。分别记录原生位图尺寸与截图导出尺寸，保持比例、标注和图表内容。以 1920 × 1080 放映为常用检查尺度，图片像素应覆盖实际显示区域；密集文字图优先达到显示宽高的两倍。目标分辨率另有要求时按目标换算。

检查最终 PPTX 内嵌图片的哈希和尺寸，再看实际渲染与网页放大视图中的最小文字、小数点、数字、箭头及细线。清晰度由实际原图与渲染结果确认；插值放大只改变输出像素数量。扫描 PDF 按原页保留内容，记录原生清晰度与实际显示效果。

图片 quality 记录 status（passed、issues 或 not_checked）、PDF 来源、页码、native_pixel_size 或 rendered_pixel_size、target_display_pixels 和 note。实际检查后填写状态。

## 研究流程图

检查论文 PDF、补充 PDF 及其中的图形摘要。存在研究流程或患者入组图时，提取或截取完整图，在方法第一页用 source_full 版式单张展示；图中人数对应的研究阶段写入图注和讲稿。PDF 中未找到流程图时，记录 searched_locations 和 not_found，方法第一页用连续文字说明研究流程。

用户明确指定局部选取时，采用 PPT 原生裁切并保留整图。source_images 中记录 source_pixel_size 和 crop_regions，坐标为原图像素。裁切参数、原始图片文件与校验值一起留存。

## 素材字段与交付

source_images 保留 file、sha256、source_id、locator、kind 和 origin。新提取的内嵌图片 origin 为 pdf_image，原页截图为 pdf_crop；两类均包含 source_pdf、source_pdf_sha256 和 page。本地提供的 PDF 采用文件与页码定位，网络下载的 PDF 同时记录 source_url。

pdf_image 另记录 image_index、image_name、source_pixel_size 和 pixel_size；pdf_crop 另记录 page_size_points、crop_points、dpi 和 pixel_size。旧版 article_image、full_text_capture 继续用于重建已有文稿。

校验程序核对 PDF 与图片哈希、页码记录、PPTX 内实际图片和完整显示。网页包携带本次使用的 PDF、提取图和原页截图，并提供“原文 PDF”下载入口。
