#!/usr/bin/env python3
"""Build a portable review desk from a final PPTX and its evidence record. Stdlib only."""
from __future__ import annotations
import argparse
import base64
import hashlib
import http.server
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from functools import partial
import webbrowser
import xml.etree.ElementTree as ET
from zipfile import ZipFile
import posixpath
from literature import validate_literature
import focus_plan

ROOT = Path(__file__).resolve().parents[1]
NS = {"p": "http://schemas.openxmlformats.org/presentationml/2006/main",
      "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
      "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
      "c": "http://schemas.openxmlformats.org/drawingml/2006/chart"}
STATES = {"verified", "partial", "unverified", "conflict", "test_fixture"}
CHECKS = {"passed", "issues", "not_checked"}
RUNTIME = Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies"

class Invalid(ValueError):
    pass

def require(condition, message):
    if not condition:
        raise Invalid(message)

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def now():
    return datetime.now(timezone.utc).isoformat()

def dump(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def safe_file(base, value):
    require(isinstance(value, str) and value and not Path(value).is_absolute(), "文件路径必须为材料目录内的相对路径")
    require("\\" not in value, "路径请使用 / 分隔")
    resolved = (base / value).resolve()
    require(resolved.is_relative_to(base.resolve()), f"文件路径越出材料目录：{value}")
    require(resolved.is_file(), f"缺少文件：{value}")
    return resolved

def text_value(value, name, allow_empty=False):
    require(isinstance(value, str) and (allow_empty or value.strip()), f"{name} 必须为文本")
    require(len(value) <= 200000, f"{name} 过长")

def normalize(text):
    return re.sub(r"\s+", "", text)

def package_slides(path):
    """Read declared presentation order, native objects, chart text and speaker notes."""
    with ZipFile(path) as z:
        require(sum(i.file_size for i in z.infolist()) < 512 * 1024 * 1024, "PPTX 解压体积超过 512 MB")
        presentation = ET.fromstring(z.read("ppt/presentation.xml"))
        rels = {x.get("Id"): x.get("Target") for x in ET.fromstring(z.read("ppt/_rels/presentation.xml.rels"))}
        result = []
        for entry in presentation.findall("p:sldIdLst/p:sldId", NS):
            target = rels[entry.get("{" + NS["r"] + "}id")]
            name = posixpath.normpath(posixpath.join("ppt", target)) if not target.startswith("/") else target.lstrip("/")
            el = ET.fromstring(z.read(name))
            slide_text = "\n".join(x.text or "" for x in el.findall(".//a:t", NS))
            rel_path = posixpath.join(posixpath.dirname(name), "_rels", posixpath.basename(name) + ".rels")
            notes = ""
            image_sha256 = []
            image_crops = []
            image_parts = {}
            heading_texts = []
            text_shapes = []
            footer_texts = []
            for shape in el.findall('.//p:sp', NS):
                value = ''.join(x.text or '' for x in shape.findall('.//a:t', NS))
                sizes = [int(x.get('sz')) for tag in ('rPr', 'defRPr') for x in shape.findall('.//a:'+tag, NS) if x.get('sz')]
                props=shape.find('p:nvSpPr/p:cNvPr',NS)
                text_shapes.append({'name':props.get('name','') if props is not None else '', 'text':value, 'font_size':max(sizes)/75 if sizes else 0})
                offset=shape.find('p:spPr/a:xfrm/a:off',NS)
                canvas=presentation.find('p:sldSz',NS)
                if value and sizes and max(sizes)<2250 and offset is not None and canvas is not None and int(offset.get('y','0'))>=int(canvas.get('cy'))*.92:
                    footer_texts.append(value)
                if value and sizes and max(sizes) >= 2250:
                    heading_texts.append(value)
            if rel_path in z.namelist():
                for rel in ET.fromstring(z.read(rel_path)):
                    if rel.get("TargetMode") == "External":
                        continue
                    dest = rel.get("Target", "")
                    part = dest.lstrip("/") if dest.startswith("/") else posixpath.normpath(posixpath.join(posixpath.dirname(name), dest))
                    if rel.get("Type", "").endswith("/notesSlide"):
                        notes = "\n".join(x.text or "" for x in ET.fromstring(z.read(part)).findall(".//a:t", NS))
                    if rel.get("Type", "").endswith("/chart"):
                        ch = ET.fromstring(z.read(part))
                        slide_text += "\n" + "\n".join(x.text or "" for x in ch.findall(".//c:v", NS))
                    if rel.get("Type", "").endswith("/image") and part in z.namelist():
                        digest = hashlib.sha256(z.read(part)).hexdigest()
                        image_sha256.append(digest)
                        image_parts[rel.get('Id')] = digest
            for picture in el.findall('.//p:pic', NS):
                blip = picture.find('p:blipFill/a:blip', NS)
                rid = blip.get('{'+NS['r']+'}embed') if blip is not None else None
                if rid in image_parts:
                    rect = picture.find('p:blipFill/a:srcRect', NS)
                    frame=picture.find('p:spPr/a:xfrm/a:ext',NS)
                    image_crops.append({'sha256':image_parts[rid], 'frame_size':[int(frame.get('cx','0')),int(frame.get('cy','0'))] if frame is not None else None, 'crop':{k:int(rect.get(k, '0')) if rect is not None else 0 for k in ('l','t','r','b')}})
            result.append({"text": slide_text, "notes": notes, "image_sha256": image_sha256, "image_crops":image_crops, "heading_texts": heading_texts, "text_shapes":text_shapes, "footer_texts":footer_texts, "bullet_count": len(el.findall('.//a:buChar', NS)) + len(el.findall('.//a:buAutoNum', NS)), "objects": {
                "text": len(el.findall(".//p:sp/p:txBody", NS)),
                "table": len(el.findall(".//a:tbl", NS)),
                "chart": len(el.findall(".//c:chart", NS)),
                "image": len(el.findall(".//p:pic", NS))}})
        require(result, "PPTX 中没有幻灯片")
        return result

def validate(record_path, need_render=True):
    record_path = Path(record_path).resolve()
    base = record_path.parent
    data = read_json(record_path)
    require(isinstance(data, dict) and data.get("schema_version") == 1, "不支持的内容记录版本")
    terms = read_json(ROOT / "assets/language-policy.json")["avoid_terms"]
    authored = json.dumps({"title": data.get("deck", {}).get("title"),
                           "sources": data.get("sources"), "slides": data.get("slides"),
                           "checks": data.get("checks"), "literature": data.get("literature")}, ensure_ascii=False)
    require(all(term not in authored for term in terms), "请按措辞规范调整内容记录中的文案用语")
    deck = data.get("deck", {})
    for key in ("id", "title", "version"):
        text_value(deck.get(key), f"deck.{key}")
    require(re.fullmatch(r"[A-Za-z0-9_-]{1,80}", deck["id"]), "deck.id 请使用字母、数字、下划线或短横线")
    pptx = safe_file(base, deck.get("pptx"))
    require(pptx.suffix.lower() == ".pptx", "需要最终 .pptx 文件")
    native = package_slides(pptx)
    slides = data.get("slides")
    require(isinstance(slides, list) and len(slides) == len(native), "内容记录页数与 PPTX 不一致")
    require(len(slides) <= 300, "单个审阅包最多 300 页；较大的文稿请分卷")
    sources = data.get("sources", [])
    require(isinstance(sources, list), "sources 必须为列表")
    source_ids = set()
    warnings = []
    for source in sources:
        require(isinstance(source, dict), "来源必须为对象")
        sid = source.get("id")
        text_value(sid, "source.id")
        require(sid not in source_ids, "来源 id 重复")
        source_ids.add(sid)
        text_value(source.get("citation"), "source.citation")
        require(source.get("identity_status") in STATES, "来源核查状态无效")
        url = source.get("url", "")
        require(not url or (isinstance(url, str) and re.match(r"^https?://[^\s]+$", url)), "来源链接只支持 http/https")
        if source["identity_status"] == "test_fixture":
            require(deck.get("mode") == "test_fixture", "测试来源只能用于 test_fixture 文稿")
    ids = set()
    for i, (slide, actual) in enumerate(zip(slides, native), 1):
        require(all(term not in actual["text"] + actual["notes"] for term in terms),
                f"请按措辞规范调整第 {i} 页的文案用语")
        require(isinstance(slide, dict), "每页记录必须为对象")
        sid = slide.get("id")
        require(isinstance(sid, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,80}", sid), f"第 {i} 页 id 无效")
        require(sid not in ids, "页面 id 重复")
        ids.add(sid)
        for field in ("title", "section", "question", "notes"):
            text_value(slide.get(field), f"第 {i} 页 {field}")
        expected = slide.get("expected_text", [])
        require(isinstance(expected, list) and all(isinstance(x, str) and x for x in expected), "expected_text 必须为非空文本列表")
        image_cover = (deck.get('report_type') == 'literature' and deck.get('style_policy') == 'original_sources_two_levels'
                       and slide.get('section_key') == 'cover' and slide.get('layout', {}).get('kind') == 'paper_cover'
                       and slide['layout'].get('title_mode') in ['source_image','editable_title'])
        for value in ([*expected] if image_cover else [slide["title"], *expected]):
            require(normalize(value) in normalize(actual["text"]), f"第 {i} 页缺少或改变了声明文字：{value[:70]}")
        require(normalize(slide["notes"]) in normalize(actual["notes"]), f"第 {i} 页讲稿与 PPTX 备注不一致")
        require(actual["objects"]["text"] > 0, f"第 {i} 页缺少原生文字对象")
        required = slide.get("required_objects", [])
        require(isinstance(required, list) and all(x in actual["objects"] for x in required), "required_objects 无效")
        for kind in required:
            require(actual["objects"][kind] > 0, f"第 {i} 页缺少原生 {kind} 对象")
        evidence = slide.get("evidence", [])
        require(isinstance(evidence, list), "evidence 必须为列表")
        for item in evidence:
            require(isinstance(item, dict), "证据必须为对象")
            require(item.get("source_id") in source_ids, f"第 {i} 页证据关联了不存在的来源")
            text_value(item.get("claim"), "evidence.claim")
            text_value(item.get("locator"), "evidence.locator")
            require(item.get("status") in STATES, "证据核查状态无效")
            if item["status"] == "test_fixture":
                require(deck.get("mode") == "test_fixture", "测试证据只能用于演示文稿")
            if item["status"] in {"unverified", "partial", "conflict"}:
                warnings.append(f"第 {i} 页证据状态：{item['status']} — {item['claim'][:60]}")
    try:
        literature_assets = validate_literature(data, base, native)
    except ValueError as exc:
        raise Invalid(str(exc)) from exc
    digest = sha(pptx)
    checks = data.get("checks", {})
    require(isinstance(checks, dict), "checks 必须为对象")
    for name in ("evidence", "file", "visual"):
        check = checks.get(name, {"status": "not_checked", "note": "待核查"})
        require(check.get("status") in CHECKS, f"{name} 核查状态无效")
        text_value(check.get("note"), f"{name}.note")
        if check["status"] != "not_checked":
            require(check.get("pptx_sha256") == digest, f"{name} 核查记录属于其他 PPTX；请更新核查记录")
        if name == "visual" and check["status"] == "passed":
            require(set(check.get("reviewed_slides", [])) == ids, "视觉通过需要逐页检查全部页面")
        if name == "evidence" and check["status"] == "passed":
            require(deck.get("mode") != "test_fixture", "演示数据请采用素材类型状态")
            require(all(s["identity_status"] == "verified" for s in sources), "请完成来源身份核对")
            require(all(e["status"] == "verified" for s in slides for e in s.get("evidence", [])), "请完成论断核对")
        checks[name] = check
    data["checks"] = checks
    assets = {"pptx": pptx, "literature_assets": {name: safe_file(base, name) for name in literature_assets}}
    receipt = None
    if need_render:
        receipt_path = safe_file(base, deck.get("render_receipt"))
        receipt = read_json(receipt_path)
        require(receipt.get("pptx_sha256") == digest, "PPTX 已变化，必须重新渲染")
        text_value(receipt.get("renderer"), "renderer")
        rendered = receipt.get("slides", [])
        require(len(rendered) == len(slides), "预览页数不一致")
        assets["images"] = []
        for i, item in enumerate(rendered, 1):
            require(item.get("slide") == i, "预览顺序不一致")
            img = safe_file(receipt_path.parent, item.get("file"))
            require(img.read_bytes().startswith(b"\x89PNG\r\n\x1a\n"), "预览必须为 PNG")
            require(sha(img) == item.get("sha256"), "预览图已被修改，请重新渲染")
            assets["images"].append(img)
        if receipt.get("pdf"):
            pdf = safe_file(receipt_path.parent, receipt["pdf"].get("file"))
            require(pdf.read_bytes().startswith(b"%PDF-") and sha(pdf) == receipt["pdf"].get("sha256"), "PDF 预览与凭据不一致")
            assets["pdf"] = pdf
    report = {"schema_version": 1, "checked_at": now(), "pptx_sha256": digest,
              "slide_count": len(slides), "structural_checks": "passed", "warnings": warnings,
              "declared_reviews": checks, "native_objects": [s["objects"] for s in native],
              "scope": "核对包结构、声明文字、备注、对象类型和渲染哈希；医学语义与逐页视觉检查分别记录。"}
    return data, assets, report, receipt

def node_path():
    custom = os.environ.get("ACADEMIC_SLIDES_NODE")
    bundled = RUNTIME / "node/bin/node"
    return custom or (str(bundled) if bundled.is_file() else shutil.which("node"))

def render(record, out):
    data, assets, report, _ = validate(record, need_render=False)
    record = Path(record).resolve()
    out = Path(out).resolve()
    require(out.is_relative_to(record.parent), "渲染目录必须在内容记录目录内")
    require(not out.exists(), "渲染目录已存在，请选择新目录，保留旧版本")
    node = node_path()
    require(node, "缺少 Node.js；请使用 Codex 配套运行环境")
    result = subprocess.run([node, str(ROOT / "scripts/render.mjs"), str(assets["pptx"]), str(out)], text=True, capture_output=True)
    require(result.returncode == 0, "PPTX 渲染失败：" + result.stderr[-3000:])
    receipt_path = out / "render.json"
    receipt = read_json(receipt_path)
    try:
        from PIL import Image
        images = [Image.open(out / item["file"]).convert("RGB") for item in receipt["slides"]]
        try:
            images[0].save(out / "preview.pdf", "PDF", save_all=True, append_images=images[1:], resolution=96*receipt.get('render_scale',1.25))
        finally:
            for im in images:
                im.close()
        receipt["pdf"] = {"file": "preview.pdf", "sha256": sha(out / "preview.pdf"), "kind": "raster_preview"}
        dump(receipt_path, receipt)
    except ImportError:
        print("Pillow 不可用：已生成逐页 PNG，未生成可选 PDF 预览。")
    data["deck"]["render_receipt"] = str(receipt_path.relative_to(record.parent))
    dump(record, data)
    print(f"已从最终 PPTX 渲染 {len(receipt['slides'])} 页：{receipt_path}")

def data_uri(path, mime):
    return f"data:{mime};base64," + base64.b64encode(path.read_bytes()).decode("ascii")

def build(record, out):
    data, assets, report, receipt = validate(record)
    out = Path(out).resolve()
    require(not out.exists(), "交付目录已存在；请使用新目录，保留旧稿及反馈")
    out.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".review-build-", dir=out.parent))
    try:
        shutil.copyfile(assets["pptx"], staging / "deck.pptx")
        if "pdf" in assets:
            shutil.copyfile(assets["pdf"], staging / "preview.pdf")
        (staging / "rendered").mkdir()
        portable = json.loads(json.dumps(data))
        portable["deck"]["pptx"] = "deck.pptx"
        portable["deck"]["render_receipt"] = "rendered/render.json"
        for name, src in assets["literature_assets"].items():
            target = staging / name
            require(not target.exists(), "图片路径与交付文件重名")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src, target)
        portable_receipt = dict(receipt)
        portable_receipt["slides"] = []
        for i, src in enumerate(assets["images"], 1):
            name = f"slide-{i}.png"
            shutil.copyfile(src, staging / "rendered" / name)
            portable_receipt["slides"].append({"slide": i, "file": name, "sha256": sha(src)})
        if "pdf" in assets:
            shutil.copyfile(assets["pdf"], staging / "rendered/preview.pdf")
            portable_receipt["pdf"] = {"file": "preview.pdf", "sha256": sha(assets["pdf"]), "kind": "raster_preview"}
        dump(staging / "rendered/render.json", portable_receipt)
        dump(staging / "deck.json", portable)
        dump(staging / "validation.json", report)
        dump(staging / "sources.json", {"deck": data["deck"]["id"], "version": data["deck"]["version"], "sources": data.get("sources", []), "slides": [{"id": s["id"], "title": s["title"], "subtitle": s.get("subtitle"), "evidence": s.get("evidence", []), "source_images": s.get("source_images", [])} for s in data["slides"]]})
        notes = f"# {data['deck']['title']} · {data['deck']['version']}\n\n" + "\n\n".join(f"## {i}. {s['title']}" + (f"：{s['subtitle']}" if s.get('subtitle') else '') + f"\n\n{s['notes']}" for i, s in enumerate(data["slides"], 1))
        (staging / "notes.md").write_text(notes + "\n", encoding="utf-8")
        if data['deck'].get('focus_policy'):
            (staging/'focus-plan.txt').write_text(focus_plan.render_text(data),encoding='utf-8')
        payload = json.loads(json.dumps(data))
        payload["pptx_sha256"] = report["pptx_sha256"]
        canonical = json.dumps(portable, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
        binding = {k: v for k, v in portable_receipt.items() if k != "rendered_at"}
        payload["bundle_id"] = hashlib.sha256((canonical + json.dumps(binding, sort_keys=True)).encode()).hexdigest()
        payload["render_info"] = {"renderer": receipt["renderer"], "rendered_at": receipt["rendered_at"]}
        payload["downloads"] = []
        for name, label, mime in [("deck.pptx", "PPTX", "application/vnd.openxmlformats-officedocument.presentationml.presentation"), ("preview.pdf", "PDF 预览", "application/pdf"), ("notes.md", "逐页讲稿", "text/markdown;charset=utf-8"), ("sources.json", "来源索引", "application/json"), ("focus-plan.txt", "讲述重点", "text/plain;charset=utf-8")]:
            f = staging / name
            if f.exists():
                payload["downloads"].append({"filename": name, "label": label, "mime": mime, "base64": base64.b64encode(f.read_bytes()).decode("ascii")})
        originals = {a['source_pdf'] for s in data['slides'] for a in s.get('source_images', []) if a.get('origin') in ['pdf_crop','pdf_image']}
        capture_pdf=data.get('literature',{}).get('title_capture',{}).get('source_pdf')
        if capture_pdf:
            require(capture_pdf in assets['literature_assets'],'封面 PDF 需先完成素材校验')
            originals.add(capture_pdf)
        originals=sorted(originals)
        for number, name in enumerate(originals, 1):
            f = safe_file(staging, name)
            payload["downloads"].append({"filename": f"original-paper-{number}.pdf", "label": "原文 PDF" if len(originals) == 1 else f"原文 PDF {number}", "mime": "application/pdf", "base64": base64.b64encode(f.read_bytes()).decode("ascii")})
        for slide, img in zip(payload["slides"], assets["images"]):
            slide["image"] = data_uri(img, "image/png")
        embedded = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c").replace("&", "\\u0026").replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
        template = (ROOT / "assets/review.html").read_text(encoding="utf-8")
        require(template.count("__DECK_DATA__") == 1, "网页模板数据占位符异常")
        (staging / "index.html").write_text(template.replace("__DECK_DATA__", embedded), encoding="utf-8")
        launcher = staging / "打开审阅台.command"
        shutil.copyfile(ROOT / "assets/start_review.py", staging / "start_review.py")
        launcher.write_text('#!/bin/zsh\nset -eu\npython3 "$(dirname "$0")/start_review.py"\n', encoding="utf-8")
        launcher.chmod(0o755)
        (staging / "使用说明.txt").write_text("双击 打开审阅台.command，在本机浏览器打开；无需联网，需要 Python 3。关闭启动窗口或 Ctrl+C 可停止本地服务。\n也可手动打开 index.html，预览和下载文件已内嵌。\n意见自动保存到当前浏览器。启动器会记住地址；只有端口冲突时更换地址并提示。结束审阅前请导出 JSON 备份，跨浏览器、换地址或清除站点数据后可导入恢复，也可粘贴备份内容。\n导出修改清单，交给 Codex 更新 PPT。\n修改清单只接受同一文稿和同一版本。新版文件请重新生成审阅台。\nPDF 为 PPTX 实际渲染的图片预览，正式编辑请使用 PPTX。\n", encoding="utf-8")
        os.replace(staging, out)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    print(f"已生成审阅台：{out / 'index.html'}")
    return out

def doctor():
    node = node_path()
    result = subprocess.run([node, str(ROOT / "scripts/render.mjs"), "--doctor"], text=True, capture_output=True) if node else None
    print(json.dumps({"python": sys.version.split()[0], "review_builder": "ready", "node": node,
                      "pptx_renderer": "ready" if result and result.returncode == 0 else "missing",
                      "detail": result.stdout.strip() if result and result.returncode == 0 else (result.stderr.strip() if result else "安装或配置 Node.js")}, ensure_ascii=False, indent=2))
    return 0 if result and result.returncode == 0 else 1

def serve(directory, port, launch):
    directory = Path(directory).resolve()
    require((directory / "index.html").is_file(), "服务目录中没有审阅网页")
    class Handler(http.server.SimpleHTTPRequestHandler):
        def list_directory(self, path):
            self.send_error(404)
        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            super().end_headers()
        def log_message(self, *args):
            pass
    with http.server.ThreadingHTTPServer(("127.0.0.1", port), partial(Handler, directory=str(directory))) as server:
        url = f"http://127.0.0.1:{server.server_port}/"
        print(url, flush=True)
        if launch:
            webbrowser.open(url)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    for name in ("render", "validate", "build"):
        p = sub.add_parser(name)
        p.add_argument("record", type=Path)
        if name != "validate":
            p.add_argument("--out", required=True, type=Path)
    s = sub.add_parser("serve")
    s.add_argument("directory", type=Path)
    s.add_argument("--port", type=int, default=0)
    s.add_argument("--open", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "doctor":
            return doctor()
        if args.command == "render":
            render(args.record, args.out)
        elif args.command == "build":
            build(args.record, args.out)
        elif args.command == "validate":
            print(json.dumps(validate(args.record)[2], ensure_ascii=False, indent=2))
        elif args.command == "serve":
            serve(args.directory, args.port, args.open)
    except (Invalid, OSError, KeyError, TypeError, json.JSONDecodeError, ET.ParseError) as exc:
        print(f"未完成：{exc}", file=sys.stderr)
        return 2
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
