#!/usr/bin/env python3
"""Check a real template adaptation against its source and final native objects."""
import argparse,hashlib,json,re,sys,xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile
from PIL import Image
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from review import validate,package_slides,NS
p=argparse.ArgumentParser();p.add_argument('--source',required=True,type=Path);p.add_argument('--record',required=True,type=Path);a=p.parse_args()
D,assets,report,_=validate(a.record);original=json.loads(a.source.read_text());T=D['deck']['template'];base=a.record.resolve().parent
assert [s['id']for s in D['slides']]==[s['id']for s in original['slides']]
assert [s['notes']for s in D['slides']]==[s['notes']for s in original['slides']]
assert D['sources']==original['sources'];assert D['literature']==original['literature']
native=package_slides(assets['pptx'])
for i,slide in enumerate(D['slides']):
 pics=slide.get('source_images',[])
 if slide['section_key']=='cover':pics=[D['literature']['title_capture']]
 if slide['section_key']=='authors':pics=[D['literature']['authors'][0]['portrait']]
 for asset in pics:
  with Image.open(base/asset['file'])as im:expected=im.width/im.height
  frames=[v for v in native[i]['image_crops']if v['sha256']==asset['sha256']]
  assert len(frames)==1
  assert all(v==0 for v in frames[0]['crop'].values())
  width,height=frames[0]['frame_size'];assert abs(width/height/expected-1)<.005,(slide['id'],asset['file'],expected,width/height)
for s,t in zip(D['slides'],original['slides']):
 assert s['evidence']==t['evidence'];assert s.get('source_images')==t.get('source_images')
with ZipFile(assets['pptx'])as z:
 pres=ET.fromstring(z.read('ppt/presentation.xml'));size=pres.find('p:sldSz',NS)
 assert int(size.get('cx'))==round(T['slide_size']['width']*9525);assert int(size.get('cy'))==round(T['slide_size']['height']*9525)
 for i,spec in enumerate(T['slides'],1):
  root=ET.fromstring(z.read(f'ppt/slides/slide{i}.xml'))
  shapes={s.find('p:nvSpPr/p:cNvPr',NS).get('name'):s for s in root.findall('.//p:sp',NS)}
  for role,slot in spec['slots'].items():
   if slot['kind']!='text':continue
   s=shapes['academic-'+role];text=''.join(x.text or '' for x in s.findall('.//a:t',NS));assert re.sub(r'\s+','',text)==re.sub(r'\s+','',slot['text'])
   sz={int(x.get('sz'))for tag in ['rPr','defRPr']for x in s.findall('.//a:'+tag,NS)if x.get('sz')};assert round(slot['style']['fontSize']*75)in sz
   fonts={x.get('typeface')for x in s.findall('.//a:latin',NS)};assert slot['style']['typeface']in fonts
   colors={x.get('val').upper()for x in s.findall('.//a:srgbClr',NS)}
   if re.fullmatch(r'#[0-9a-fA-F]{6}',slot['style'].get('color','')):assert slot['style']['color'][1:].upper()in colors
   x=s.find('p:spPr/a:xfrm',NS);o=x.find('a:off',NS);e=x.find('a:ext',NS)
   for actual,k in [(o.get('x'),'left'),(o.get('y'),'top'),(e.get('cx'),'width'),(e.get('cy'),'height')]:assert abs(int(actual)/9525-slot['position'][k])<.02
print(json.dumps({'slides':len(D['slides']),'template_dimensions_fonts_colors_positions':'passed','source_images_notes_evidence':'preserved','native_content_and_render_binding':'passed'},ensure_ascii=False))
