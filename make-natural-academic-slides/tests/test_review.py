#!/usr/bin/env python3
"""Exercise the actual exported PPTX, render receipt, and offline review builder."""
import argparse
from pathlib import Path
import importlib.util
import json
import shutil
import tempfile
import sys
import unittest
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
spec=importlib.util.spec_from_file_location('review',ROOT/'scripts/review.py')
review=importlib.util.module_from_spec(spec);spec.loader.exec_module(review)
parser=argparse.ArgumentParser()
parser.add_argument('--record',required=True,type=Path)
args,remaining=parser.parse_known_args()
RECORD=args.record.resolve()

class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.root=Path(self.temp.name)/'fixture'
        # Copy only this record's assets, not neighboring output/work directories.
        self.root.mkdir()
        self.data=json.loads(RECORD.read_text())
        self.record=self.root/'deck.json'
        pptx=Path(self.data['deck']['pptx'])
        (self.root/pptx).parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(RECORD.parent/pptx,self.root/pptx)
        rec=Path(self.data['deck']['render_receipt'])
        shutil.copytree((RECORD.parent/rec).parent,(self.root/rec).parent,dirs_exist_ok=True)
        self.save()
    def tearDown(self):self.temp.cleanup()
    def save(self):review.dump(self.record,self.data)
    def invalid(self,match):
        self.save()
        with self.assertRaisesRegex(review.Invalid,match):review.validate(self.record)
    def test_real_package_and_offline_bundle(self):
        data,assets,report,_=review.validate(self.record)
        self.assertEqual(report['slide_count'],3)
        self.assertGreater(report['native_objects'][0]['table'],0)
        self.assertGreater(report['native_objects'][1]['chart'],0)
        out=review.build(self.record,self.root/'delivery')
        html=(out/'index.html').read_text()
        self.assertIn('data:image/png;base64,',html)
        self.assertNotIn('__DECK_DATA__',html)
        self.assertNotIn('<script src=',html)
        self.assertEqual(review.sha(out/'deck.pptx'),report['pptx_sha256'])
        review.validate(out/'deck.json')
        rebuilt=review.build(out/'deck.json',self.root/'rebuilt')
        def bundle_id(html):
            return json.loads(html.split('<script type="application/json" id="deck-data">',1)[1].split('</script>',1)[0])['bundle_id']
        self.assertEqual(bundle_id(html),bundle_id((rebuilt/'index.html').read_text()))
    def test_pptx_tampering_requires_rerender(self):
        p=self.root/self.data['deck']['pptx']
        with ZipFile(p,'a')as z:z.comment=b'changed-after-render'
        # Reset declared reviews so the precise render mismatch is reached.
        self.data['checks']={}
        self.invalid('重新渲染')
    def test_rendered_image_hash_is_checked(self):
        receipt_path=self.root/self.data['deck']['render_receipt']
        receipt=review.read_json(receipt_path)
        image=receipt_path.parent/receipt['slides'][0]['file']
        image.write_bytes(image.read_bytes()+b'changed')
        self.invalid('预览图已被修改')
    def test_missing_preview_does_not_silently_drop_page(self):
        rec=self.root/self.data['deck']['render_receipt'];receipt=review.read_json(rec)
        (rec.parent/receipt['slides'][0]['file']).unlink()
        self.invalid('缺少文件')
    def test_slide_order_is_checked(self):
        self.data['slides'][0],self.data['slides'][1]=self.data['slides'][1],self.data['slides'][0]
        self.invalid('缺少或改变')
    def test_duplicate_slide_ids_rejected(self):
        self.data['slides'][1]['id']=self.data['slides'][0]['id'];self.invalid('id 重复')
    def test_unknown_source_rejected(self):
        self.data['slides'][0]['evidence'][0]['source_id']='missing';self.invalid('不存在的来源')
    def test_missing_native_object_rejected(self):
        self.data['slides'][0]['required_objects'].append('image');self.invalid('缺少原生 image')
    def test_notes_are_checked(self):
        self.data['slides'][0]['notes']='This note never entered the PPTX.';self.invalid('备注不一致')
    def test_path_cannot_escape_material_directory(self):
        self.data['deck']['pptx']='../outside.pptx';self.invalid('越出材料目录')
    def test_unsafe_source_url_rejected(self):
        self.data['sources'][0]['url']='javascript:alert(1)';self.invalid('http/https')
    def test_cover_pdf_download_uses_validated_assets(self):
        self.data['literature']={'title_capture':{'source_pdf':'../outside.pdf'}};self.save()
        with self.assertRaisesRegex(review.Invalid,'封面 PDF'):
            review.build(self.record,self.root/'delivery')
        self.assertFalse((self.root/'delivery').exists())
    def test_untrusted_text_cannot_close_script_element(self):
        self.data['sources'][0]['citation']='</script><img src=x onerror=alert(1)>'
        self.save();out=review.build(self.record,self.root/'safe')
        html=(out/'index.html').read_text()
        self.assertNotIn('</script><img src=x',html)
        encoded=html.split('<script type="application/json" id="deck-data">',1)[1].split('</script>',1)[0]
        self.assertEqual(json.loads(encoded)['sources'][0]['citation'],self.data['sources'][0]['citation'])
    def test_synthetic_evidence_cannot_be_called_verified(self):
        self.data['checks']['evidence']={'status':'passed','note':'wrong','pptx_sha256':review.sha(self.root/self.data['deck']['pptx'])}
        self.invalid('演示数据请采用素材类型状态')
    def test_reviews_are_version_bound(self):
        self.data['checks']['file']={'status':'passed','note':'old review','pptx_sha256':'0'*64};self.invalid('其他 PPTX')
    def test_visual_pass_requires_every_slide(self):
        self.data['checks']['visual']={'status':'passed','note':'incomplete','pptx_sha256':review.sha(self.root/self.data['deck']['pptx']),'reviewed_slides':['methods']};self.invalid('全部页面')
    def test_existing_delivery_is_preserved(self):
        out=self.root/'keep';out.mkdir();(out/'notes.txt').write_text('keep me')
        with self.assertRaisesRegex(review.Invalid,'已存在'):review.build(self.record,out)
        self.assertEqual((out/'notes.txt').read_text(),'keep me')
    def test_omitted_checks_are_not_inferred_passed(self):
        self.data.pop('checks');self.save()
        data,_,_,_=review.validate(self.record)
        self.assertTrue(all(c['status']=='not_checked' for c in data['checks'].values()))
    def test_wording_policy_checks_authored_text(self):
        original=self.data['deck']['title']
        for term in review.read_json(ROOT/'assets/language-policy.json')['avoid_terms']:
            with self.subTest(term_index=len(term)):
                self.data['deck']['title']=original+term
                self.invalid('文案用语')
    def test_wording_policy_checks_native_pptx_text(self):
        pptx=self.root/self.data['deck']['pptx']
        with ZipFile(pptx)as z:parts={n:z.read(n)for n in z.namelist()}
        name='ppt/slides/slide1.xml'
        slide=review.ET.fromstring(parts[name]);run=slide.find('.//a:t',review.NS)
        run.text=(run.text or '')+review.read_json(ROOT/'assets/language-policy.json')['avoid_terms'][0]
        parts[name]=review.ET.tostring(slide,encoding='utf-8',xml_declaration=True)
        with ZipFile(pptx,'w')as z:
            for name,content in parts.items():z.writestr(name,content)
        self.invalid('文案用语')

if __name__=='__main__':unittest.main(argv=['test_review.py',*remaining],verbosity=2)
