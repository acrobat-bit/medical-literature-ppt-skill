#!/usr/bin/env python3
"""Check real PDF image extraction and page capture with local-file provenance."""
import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from PIL import Image
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, NumberObject, DecodedStreamObject

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import source_assets as source

class PdfAssetTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name)
        self.pdf=self.root/'paper.pdf';self.out=self.root/'figure.png'
        writer=PdfWriter();page=writer.add_blank_page(width=72,height=72)
        picture=DecodedStreamObject();picture.set_data(bytes([255,0,0,0,255,0,0,0,255,255,255,255]))
        picture.update({NameObject('/Type'):NameObject('/XObject'),NameObject('/Subtype'):NameObject('/Image'),NameObject('/Width'):NumberObject(2),NameObject('/Height'):NumberObject(2),NameObject('/ColorSpace'):NameObject('/DeviceRGB'),NameObject('/BitsPerComponent'):NumberObject(8)})
        page[NameObject('/Resources')]=DictionaryObject({NameObject('/XObject'):DictionaryObject({NameObject('/Im1'):writer._add_object(picture)})})
        content=DecodedStreamObject();content.set_data(b'q 36 0 0 36 0 0 cm /Im1 Do Q')
        page[NameObject('/Contents')]=writer._add_object(content)
        writer.add_blank_page(width=72,height=72)
        writer.write(self.pdf)
    def tearDown(self):self.temp.cleanup()
    def extract(self,**kwargs):
        args=dict(pdf=self.pdf,page=1,image_index=1,out=self.out,root=self.root,source_id='paper',locator='Figure 1')
        args.update(kwargs);return source.extract_image(**args)
    def test_inventory_lists_native_images_and_page_numbers(self):
        report=source.inspect_pdf(self.pdf)
        self.assertEqual(report['page_count'],2)
        self.assertEqual([p['page']for p in report['pages']],[1])
        self.assertEqual(report['pages'][0]['images'][0]['pixel_size'],[2,2])
    def test_extract_keeps_pixels_and_local_pdf_provenance(self):
        a=self.extract()
        with Image.open(self.out)as im:
            self.assertEqual(im.size,(2,2))
            self.assertEqual(list(im.convert('RGB').getdata()),[(255,0,0),(0,255,0),(0,0,255),(255,255,255)])
        self.assertEqual(a['origin'],'pdf_image')
        self.assertEqual(a['source_pdf_sha256'],source.sha(self.pdf))
        self.assertEqual((a['page'],a['image_index']),(1,1))
        self.assertNotIn('source_url',a)
        self.assertEqual(json.loads(self.out.with_suffix('.asset.json').read_text()),a)
    def test_downloaded_pdf_can_keep_its_url(self):
        self.assertEqual(self.extract(source_url='https://example.org/paper.pdf')['source_url'],'https://example.org/paper.pdf')
    def test_invalid_page_and_image_indices_leave_no_output(self):
        for args in [dict(page=0),dict(page=3),dict(image_index=0),dict(image_index=2),dict(page=2)]:
            with self.subTest(args=args),self.assertRaises(ValueError):self.extract(**args)
            self.assertFalse(self.out.exists())
    def test_existing_image_and_metadata_are_preserved(self):
        a=self.extract();before=self.out.read_bytes()
        with self.assertRaises(ValueError):self.extract()
        self.assertEqual(self.out.read_bytes(),before)
        self.assertEqual(json.loads(self.out.with_suffix('.asset.json').read_text()),a)
    def test_wrong_extension_is_rejected(self):
        with self.assertRaisesRegex(ValueError,'扩展名'):self.extract(out=self.root/'figure.jpg')
    def test_default_page_capture_is_600dpi_and_accepts_local_pdf(self):
        target=self.root/'crop.png'
        with contextlib.redirect_stdout(io.StringIO()):
            source.crop_pdf(self.pdf,1,[0,0,72,72],target,self.root,'paper','Figure 1')
        with Image.open(target)as im:self.assertEqual(im.size,(600,600))
        a=json.loads(target.with_suffix('.asset.json').read_text())
        self.assertEqual(a['dpi'],600);self.assertNotIn('source_url',a)
    def test_rotated_capture_keeps_original_pdf_provenance(self):
        before=source.sha(self.pdf);target=self.root/'rotated.png'
        with contextlib.redirect_stdout(io.StringIO()):
            source.crop_pdf(self.pdf,1,[0,0,72,72],target,self.root,'paper','Figure 1',rotation=90)
        a=json.loads(target.with_suffix('.asset.json').read_text())
        self.assertEqual(a['source_pdf'],'paper.pdf');self.assertEqual(a['source_pdf_sha256'],before)
        self.assertEqual(a['page'],1);self.assertEqual(a['page_rotation'],90)
        self.assertEqual(source.sha(self.pdf),before)
        with Image.open(target)as im:self.assertEqual(im.size,(600,600))
        self.assertFalse(list(self.root.glob('.pdf-rotate-*')))

if __name__=='__main__':unittest.main(verbosity=2)
