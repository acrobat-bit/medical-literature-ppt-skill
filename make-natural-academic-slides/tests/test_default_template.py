#!/usr/bin/env python3
"""Verify the built-in Beamer route and user-template precedence on real decks."""
import argparse,hashlib,json,sys,xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from review import validate,NS
p=argparse.ArgumentParser();p.add_argument('--default-record',type=Path,required=True);p.add_argument('--provided-record',type=Path,required=True);a=p.parse_args()
default,assets,_,_=validate(a.default_record);provided,_,_,_=validate(a.provided_record)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
assert default['deck']['design_theme']=='beamer_metropolis'
assert default['deck']['template']['sha256']==sha(ROOT/'assets/beamer-metropolis/template.pptx')
assert provided['deck']['design_theme']=='provided_template'
assert provided['deck']['template']['sha256']!=default['deck']['template']['sha256']
assert [s['id'] for s in default['slides']]==[s['id'] for s in provided['slides']]
assert [s['notes'] for s in default['slides']]==[s['notes'] for s in provided['slides']]
with ZipFile(assets['pptx']) as z:
 for i,s in enumerate(default['slides'],1):
  x=ET.fromstring(z.read(f'ppt/slides/slide{i}.xml'))
  assert x.find('p:cSld/p:bg/p:bgPr/a:solidFill/a:srgbClr',NS).get('val').upper()=='FAFAFA'
  shapes={e.find('p:nvSpPr/p:cNvPr',NS).get('name'):e for e in x.findall('.//p:sp',NS)}
  if s['section_key']!='cover':assert shapes['academic-major'].find('p:spPr/a:solidFill/a:srgbClr',NS).get('val').upper()=='23373B'
  if s['layout']['kind']=='prose':assert len(x.findall('.//p:pic',NS))==0
assert len(json.loads((ROOT/'assets/beamer-metropolis/mapping.json').read_text())['layouts'])>=8
print('Default Beamer theme, editable native headings, content preservation and provided-template precedence passed.')
