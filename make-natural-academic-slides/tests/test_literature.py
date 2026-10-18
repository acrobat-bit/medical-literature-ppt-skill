#!/usr/bin/env python3
import base64
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import literature as lit

class LiteratureTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name)
        # A labelled synthetic image fixture; tests exercise records, not medical evidence.
        (self.base/'figure.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j1xkAAAAASUVORK5CYII='))
        source={'id':'fixture','citation':'功能测试数据','identity_status':'test_fixture','url':'https://example.org/paper'}
        asset={'file':'figure.png','source_url':'https://example.org/figure.png'}
        self.brief={'deck':{'style_policy':'legacy','id':'alternate-paper','title':'另一篇论文功能测试','version':'v2','mode':'test_fixture','pptx':'files/deck.pptx'},'sources':[source], 'literature':{'author_policy':'legacy_profiles','paper_source_id':'fixture','paper_title':'A different study','cover_title':'另一篇论文','cover_subtitle':'功能测试','cover_notes':'封面讲稿','cover_footer':'测试材料','title_capture':dict(asset,kind='pdf',captured_at='2026-10-17'),'authors':[{'name':'测试作者','contribution':'第一作者兼通讯作者','position':'研究员','affiliation':'测试机构','verified_at':'2026-10-17','profile_source_id':'fixture','portrait':asset}],'author_note':'测试作者承担作者角色','author_notes':'作者功能测试'},'body_slides':[{'id':key,'section_key':key,'title':key,'question':'测试问题','notes':'测试讲稿','layout':{'kind':'points','items':[{'heading':'项目','body':'内容'}]},'evidence':[],'required_objects':['text']}for key in lit.ORDER[2:-1]]}
        self.data=lit.assemble(self.brief,self.base)
    def tearDown(self):self.temp.cleanup()
    def native(self):
        digest=lit.image_asset(self.base,self.data['literature']['title_capture'])
        result=[{'text':s['title'],'image_sha256':[]}for s in self.data['slides']]
        result[0]['image_sha256']=[digest]
        result[1]={'text':'测试作者 第一作者兼通讯作者 研究员 测试机构','image_sha256':[digest]}
        result[-1]['text']=' '.join(p['label']for p in self.data['slides'][-1]['reflection']['prompts'])
        return result
    def test_alternate_paper_assembles_and_validates(self):
        self.assertEqual([s['section_key']for s in self.data['slides']],lit.ORDER)
        lit.validate_literature(self.data,self.base,self.native())
        self.assertNotIn('answers',self.data['slides'][-1]['reflection'])
        self.assertTrue(all(c['status']=='not_checked'for c in self.data['checks'].values()))
    def test_multiple_methods_pages_keep_order(self):
        b=copy.deepcopy(self.brief);second=copy.deepcopy(b['body_slides'][1]);second['id']='methods2';b['body_slides'].insert(2,second)
        d=lit.assemble(b,self.base);self.assertEqual(len(d['slides']),10)
    def test_missing_discussion_is_rejected(self):
        self.data['slides']=[s for s in self.data['slides']if s['section_key']!='discussion']
        with self.assertRaisesRegex(ValueError,'顺序'):lit.validate_literature(self.data,self.base)
    def test_section_reordering_is_rejected(self):
        self.data['slides'][5],self.data['slides'][6]=self.data['slides'][6],self.data['slides'][5]
        with self.assertRaisesRegex(ValueError,'顺序'):lit.validate_literature(self.data,self.base)
    def test_title_requires_full_text_origin(self):
        self.data['literature']['title_capture']['kind']='redrawn_title'
        with self.assertRaisesRegex(ValueError,'PDF'):lit.validate_literature(self.data,self.base)
    def test_source_image_hash_change_is_rejected(self):
        (self.base/'figure.png').write_bytes((self.base/'figure.png').read_bytes()+b'change')
        with self.assertRaisesRegex(ValueError,'校验值变化'):lit.validate_literature(self.data,self.base)
    def test_missing_title_image_in_pptx_is_rejected(self):
        actual=self.native();actual[0]['image_sha256']=[]
        with self.assertRaisesRegex(ValueError,'第 1 页'):lit.validate_literature(self.data,self.base,actual)
    def test_missing_author_portrait_in_pptx_is_rejected(self):
        actual=self.native();actual[1]['image_sha256']=[]
        with self.assertRaisesRegex(ValueError,'第 2 页'):lit.validate_literature(self.data,self.base,actual)
    def test_author_position_must_appear_in_native_text(self):
        actual=self.native();actual[1]['text']='测试作者 第一作者兼通讯作者 测试机构'
        with self.assertRaisesRegex(ValueError,'研究员'):lit.validate_literature(self.data,self.base,actual)
    def test_author_profile_requires_source(self):
        self.data['literature']['authors'][0]['profile_source_id']='unknown'
        with self.assertRaisesRegex(ValueError,'任职信息来源'):lit.validate_literature(self.data,self.base)
    def test_reflection_prompts_must_appear_in_pptx(self):
        actual=self.native();actual[-1]['text']='结束'
        with self.assertRaisesRegex(ValueError,'提示需进入'):lit.validate_literature(self.data,self.base,actual)
    def test_duplicate_prompt_ids_rejected(self):
        f=self.data['slides'][-1]['reflection'];f['prompts'][1]['id']=f['prompts'][0]['id']
        with self.assertRaisesRegex(ValueError,'重复'):lit.validate_literature(self.data,self.base)
    def test_image_path_traversal_rejected(self):
        self.data['literature']['title_capture']['file']='../outside.png'
        with self.assertRaisesRegex(ValueError,'越出'):lit.validate_literature(self.data,self.base)
    def test_user_answers_are_checked_against_pptx(self):
        self.data['slides'][-1]['reflection']['answers']={'finding':'Presenter supplied content'}
        actual=self.native()
        with self.assertRaisesRegex(ValueError,'填写内容需进入'):lit.validate_literature(self.data,self.base,actual)
        actual[-1]['text']+=' Presenter supplied content'
        lit.validate_literature(self.data,self.base,actual)
    def test_body_images_are_part_of_portable_assets(self):
        self.data['slides'][3]['layout']={'kind':'image_detail','image':'figure.png'}
        self.assertIn('figure.png',lit.validate_literature(self.data,self.base))
    def local_pdf_cover(self):
        (self.base/'paper.pdf').write_bytes(b'%PDF-1.4 local source fixture')
        a=self.data['literature']['title_capture'];a.pop('source_url')
        a.update(source_pdf='paper.pdf',source_pdf_sha256=lit.visual_policy.sha(self.base/'paper.pdf'),page=1)
    def test_user_supplied_pdf_cover_is_portable_without_url(self):
        self.local_pdf_cover();self.assertIn('paper.pdf',lit.validate_literature(self.data,self.base,self.native()))
    def test_local_pdf_cover_checks_original_hash(self):
        self.local_pdf_cover();(self.base/'paper.pdf').write_bytes(b'%PDF-1.4 changed')
        with self.assertRaisesRegex(ValueError,'PDF 已变化'):lit.validate_literature(self.data,self.base)
    def test_old_record_has_no_new_requirements(self):
        self.assertEqual(lit.validate_literature({'deck':{},'slides':[]},self.base),[])
    def test_reflection_notes_follow_custom_prompt_order(self):
        b=copy.deepcopy(self.brief)
        b['literature']['reflection']={'directions':['研究选题'],'guidance':'围绕研究选题填写。','prompts':[{'id':'second','label':'解释','hint':''},{'id':'first','label':'发现','hint':''}],'answers':{'first':'用户提供的发现','second':'用户提供的解释'}}
        d=lit.assemble(b,self.base);notes=d['slides'][-1]['notes']
        self.assertIn('用户提供的发现',notes);self.assertIn('用户提供的解释',notes)
        self.assertLess(notes.index('用户提供的解释'),notes.index('用户提供的发现'))
    def test_empty_reflection_uses_custom_direction_and_prompts(self):
        b=copy.deepcopy(self.brief)
        b['literature']['reflection']={'directions':['影像测量'],'guidance':'从测量方法展开。','prompts':[{'id':'method','label':'测量方案','hint':''}]}
        d=lit.assemble(b,self.base);notes=d['slides'][-1]['notes']
        self.assertIn('影像测量',notes);self.assertIn('测量方案',notes)
        self.assertNotIn('answers',d['slides'][-1]['reflection'])
    def test_new_literature_has_editable_title_and_compact_background(self):
        b=copy.deepcopy(self.brief);b['deck'].pop('style_policy')
        for s in b['body_slides']:
            s.update(title=lit.visual_policy.MAJORS[s['section_key']],subtitle='具体主题',expected_text=[],layout={'kind':'prose','paragraphs':['研究说明。']})
        b['body_slides'][0]['background_coverage']=['progress','study_question']
        b['body_slides'][1]['method_coverage']=['workflow','participants','interventions','outcomes','statistics']
        d=lit.assemble(b,self.base);cover=d['slides'][0]
        self.assertTrue(lit.visual_policy.editable_title_cover(cover))
        self.assertFalse(cover['subtitle'])
        self.assertEqual(cover['expected_text'],['A different study','期刊','IF','演讲者','日期'])
        self.assertEqual(sum(s['section_key']=='background' for s in d['slides']),1)

if __name__=='__main__':unittest.main(verbosity=2)
