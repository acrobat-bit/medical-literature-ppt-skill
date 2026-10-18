#!/usr/bin/env python3
"""Acquire a paper PDF, extract its embedded images, and capture figures or tables."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

CLOUD='https://pmc-oa-opendata.s3.amazonaws.com/'
RUNTIME=Path.home()/'.cache/codex-runtimes/codex-primary-runtime/dependencies'

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,d):Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def request(url):return urllib.request.urlopen(url,timeout=45).read()
def cloud_url(value):
    u=urllib.parse.urlparse(value)
    if u.scheme!='s3' or u.netloc!='pmc-oa-opendata':raise ValueError('需要 PMC 公开数据集链接')
    return CLOUD+u.path.lstrip('/'),urllib.parse.parse_qs(u.query).get('md5',[None])[0]

def fetch_pmc(pmcid,out,doi=None,version=None):
    if not re.fullmatch(r'PMC\d+',pmcid):raise ValueError('PMCID 格式为 PMC 后接数字')
    if out.exists():raise ValueError('输出文件已存在，请使用新路径')
    listing=request(CLOUD+'?'+urllib.parse.urlencode({'list-type':2,'prefix':pmcid+'.','delimiter':'/'}))
    ns={'s':'http://s3.amazonaws.com/doc/2006-03-01/'}
    prefixes=[p.text for p in ET.fromstring(listing).findall('s:CommonPrefixes/s:Prefix',ns)]
    candidates=[]
    for prefix in prefixes:
        meta=json.loads(request(CLOUD+prefix+prefix.rstrip('/')+'.json'))
        if version is not None and meta.get('version')!=version:continue
        if meta.get('pdf_url') and (version is not None or not meta.get('is_manuscript')):candidates.append(meta)
    if len(candidates)!=1:raise ValueError('请检查可用版本并用 --version 指定一份包含 PDF 的版本')
    meta=candidates[0]
    if meta.get('pmcid')!=pmcid or doi and meta.get('doi','').lower()!=doi.lower():raise ValueError('论文身份与指定 PMCID/DOI 不一致')
    url,md5=cloud_url(meta['pdf_url']);raw=request(url)
    if not raw.startswith(b'%PDF-'):raise ValueError('下载内容不是 PDF')
    if md5 and hashlib.md5(raw).hexdigest()!=md5:raise ValueError('下载文件与官方校验值不一致')
    out.parent.mkdir(parents=True,exist_ok=True);out.write_bytes(raw)
    save(out.with_suffix('.metadata.json'),meta)
    save(out.with_suffix('.provenance.json'),{'source':'NLM PMC Article Datasets on AWS','source_url':url,'retrieved_at':datetime.now(timezone.utc).isoformat(),'pmcid':pmcid,'doi':meta['doi'],'version':meta['version'],'license':meta.get('license_code'),'md5':md5,'sha256':sha(out)})
    print(str(out))

def inspect_pdf(pdf):
    from pypdf import PdfReader
    pdf=Path(pdf).resolve();reader=PdfReader(pdf)
    pages=[]
    for number,page in enumerate(reader.pages,1):
        images=[]
        for index,item in enumerate(page.images,1):
            raw=item.data
            extension='.jpg' if raw.startswith(b'\xff\xd8\xff') else '.png'
            images.append({'image_index':index,'image_name':item.name,'pixel_size':list(item.image.size),'suggested_extension':extension})
        if images:pages.append({'page':number,'images':images})
    return {'source_pdf':pdf.name,'source_pdf_sha256':sha(pdf),'page_count':len(reader.pages),'pages':pages}

def extract_image(pdf,page,image_index,out,root,source_id,locator,source_url=None):
    from pypdf import PdfReader
    pdf=Path(pdf).resolve();out=Path(out).resolve();root=Path(root).resolve()
    if not pdf.is_relative_to(root) or not out.is_relative_to(root):raise ValueError('PDF 与图片应位于当前材料目录内')
    if out.exists() or out.with_suffix('.asset.json').exists():raise ValueError('输出文件已存在，请使用新路径')
    reader=PdfReader(pdf)
    if not 1<=page<=len(reader.pages):raise ValueError('PDF 页码超出范围')
    images=reader.pages[page-1].images
    if not 1<=image_index<=len(images):raise ValueError('该页图像序号超出范围，请先运行 inspect-pdf')
    item=images[image_index-1];raw=item.data
    if raw.startswith(b'\xff\xd8\xff'):
        suffixes={'.jpg','.jpeg'};conversion=False
    elif raw.startswith(b'\x89PNG\r\n\x1a\n'):
        suffixes={'.png'};conversion=False
    else:
        suffixes={'.png'};conversion=True
    if out.suffix.lower() not in suffixes:raise ValueError('输出扩展名请使用 '+sorted(suffixes)[0])
    out.parent.mkdir(parents=True,exist_ok=True)
    if conversion:
        image=item.image
        if image.mode not in ['1','L','LA','P','RGB','RGBA']:image=image.convert('RGB')
        image.save(out,format='PNG')
    else:out.write_bytes(raw)
    size=list(item.image.size)
    asset={'file':str(out.relative_to(root)),'sha256':sha(out),'source_id':source_id,'locator':locator,'kind':'figure','origin':'pdf_image','source_pdf':str(pdf.relative_to(root)),'source_pdf_sha256':sha(pdf),'page':page,'image_index':image_index,'image_name':item.name,'source_pixel_size':size,'pixel_size':size,'captured_at':datetime.now(timezone.utc).isoformat(),'transform':'提取 PDF 内嵌图像，保持原生像素尺寸。'+('另存为 PNG，保留像素尺寸。' if conversion else '')}
    if source_url:asset['source_url']=source_url
    save(out.with_suffix('.asset.json'),asset)
    return asset

def crop_pdf(pdf,page,bbox,out,root,source_id,locator,source_url=None,dpi=600,kind='table',rotation=0):
    import pdfplumber
    from PIL import Image
    pdf=pdf.resolve();out=out.resolve();root=root.resolve()
    if not pdf.is_relative_to(root) or not out.is_relative_to(root):raise ValueError('PDF 与截图应位于当前材料目录内')
    if out.exists():raise ValueError('截图已存在，请使用新路径')
    if rotation not in [0,90,180,270]:raise ValueError('旋转角度使用 0、90、180 或 270')
    if rotation:
        from pypdf import PdfReader,PdfWriter
        reader=PdfReader(pdf)
        if not 1<=page<=len(reader.pages):raise ValueError('PDF 页码超出范围')
        with tempfile.TemporaryDirectory(dir=root,prefix='.pdf-rotate-')as temp:
            rotated=Path(temp)/'rotated.pdf';writer=PdfWriter();writer.add_page(reader.pages[page-1].rotate(rotation));writer.write(rotated)
            crop_pdf(rotated,1,bbox,out,root,source_id,locator,source_url,dpi,kind)
        asset=json.loads(out.with_suffix('.asset.json').read_text())
        asset.update(source_pdf=str(pdf.relative_to(root)),source_pdf_sha256=sha(pdf),page=page,page_rotation=rotation,transform=f'原始 PDF 页顺时针旋转 {rotation}° 后按原页范围截取，内容保持原样。')
        save(out.with_suffix('.asset.json'),asset)
        return
    with pdfplumber.open(pdf)as doc:
        if not 1<=page<=len(doc.pages):raise ValueError('PDF 页码超出范围')
        p=doc.pages[page-1];width,height=p.width,p.height
    x0,y0,x1,y1=bbox
    if not(0<=x0<x1<=width and 0<=y0<y1<=height):raise ValueError('裁切范围需位于 PDF 页面内')
    executable=RUNTIME/'bin/override/pdftoppm'
    if not executable.is_file():executable=shutil.which('pdftoppm')
    if not executable:raise ValueError('请配置 Poppler 的 pdftoppm')
    out.parent.mkdir(parents=True,exist_ok=True);scale=dpi/72
    command=[str(executable),'-f',str(page),'-l',str(page),'-singlefile','-r',str(dpi),'-x',str(round(x0*scale)),'-y',str(round(y0*scale)),'-W',str(round((x1-x0)*scale)),'-H',str(round((y1-y0)*scale)),'-png',str(pdf),str(out.with_suffix(''))]
    subprocess.run(command,check=True,capture_output=True)
    if not out.is_file() or not out.read_bytes().startswith(b'\x89PNG\r\n\x1a\n'):raise ValueError('原页截图未生成')
    with Image.open(out)as image:size=list(image.size)
    asset={'file':str(out.relative_to(root)),'sha256':sha(out),'source_id':source_id,'source_url':source_url,'locator':locator,'kind':kind,'origin':'pdf_crop','source_pdf':str(pdf.relative_to(root)),'source_pdf_sha256':sha(pdf),'page':page,'page_size_points':[width,height],'crop_points':bbox,'dpi':dpi,'pixel_size':size,'captured_at':datetime.now(timezone.utc).isoformat(),'transform':'从原始 PDF 直接裁切，保留原始表头、数值和脚注。'}
    if not source_url:asset.pop('source_url')
    save(out.with_suffix('.asset.json'),asset);print(str(out.with_suffix('.asset.json')))

def main():
    p=argparse.ArgumentParser(description=__doc__);s=p.add_subparsers(dest='command',required=True)
    f=s.add_parser('fetch-pmc');f.add_argument('pmcid');f.add_argument('--out',type=Path,required=True);f.add_argument('--doi');f.add_argument('--version',type=int)
    i=s.add_parser('inspect-pdf');i.add_argument('pdf',type=Path)
    e=s.add_parser('extract-image');e.add_argument('pdf',type=Path);e.add_argument('--page',type=int,required=True);e.add_argument('--image',type=int,required=True);e.add_argument('--out',type=Path,required=True);e.add_argument('--root',type=Path,required=True);e.add_argument('--source-id',required=True);e.add_argument('--locator',required=True);e.add_argument('--source-url')
    c=s.add_parser('crop');c.add_argument('pdf',type=Path);c.add_argument('--page',type=int,required=True);c.add_argument('--bbox',required=True);c.add_argument('--out',type=Path,required=True);c.add_argument('--root',type=Path,required=True);c.add_argument('--source-id',required=True);c.add_argument('--locator',required=True);c.add_argument('--source-url');c.add_argument('--dpi',type=int,default=600);c.add_argument('--kind',choices=['table','figure','excerpt'],default='table');c.add_argument('--rotate',type=int,choices=[0,90,180,270],default=0)
    a=p.parse_args()
    if a.command=='fetch-pmc':fetch_pmc(a.pmcid,a.out,a.doi,a.version)
    elif a.command=='inspect-pdf':print(json.dumps(inspect_pdf(a.pdf),ensure_ascii=False,indent=2))
    elif a.command=='extract-image':extract_image(a.pdf,a.page,a.image,a.out,a.root,a.source_id,a.locator,a.source_url);print(str(a.out.with_suffix('.asset.json')))
    else:crop_pdf(a.pdf,a.page,[float(v)for v in a.bbox.split(',')],a.out,a.root,a.source_id,a.locator,a.source_url,a.dpi,a.kind,a.rotate)
if __name__=='__main__':main()
