#!/usr/bin/env python3
import base64,copy,hashlib,json
from pathlib import Path
import sys,tempfile,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import visual_policy as v
class SourceStyleTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.base=Path(self.tmp.name)
  # Synthetic bytes exercise provenance bindings; real PDF capture is checked in acceptance work.
  (self.base/'source.pdf').write_bytes(b'%PDF-1.4\nsynthetic hash fixture')
  (self.base/'table.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+j1xkAAAAASUVORK5CYII='))
  self.asset={'file':'table.png','sha256':v.sha(self.base/'table.png'),'source_id':'paper','source_url':'https://example.org/paper.pdf','locator':'Table 1','origin':'pdf_crop','source_pdf':'source.pdf','source_pdf_sha256':v.sha(self.base/'source.pdf'),'page':1,'page_size_points':[100,100],'crop_points':[0,0,90,90]}
  slides=[]
  for key,title in v.MAJORS.items():
   kind={'cover':'paper_cover','authors':'authors','reflection':'reflection'}.get(key,'prose')
   slides.append({'id':key,'section_key':key,'title':title,'subtitle':'具体内容','layout':{'kind':kind,'paragraphs':['采用连续文字说明本页内容。']}})
  self.data={'deck':{'style_policy':v.STYLE},'sources':[{'id':'paper'}],'slides':slides}
  self.bg=slides[2];self.bg['background_coverage']=['keywords','progress','study_question']
  slides[3]['method_coverage']=['workflow','participants','interventions','outcomes','statistics']
  self.result=slides[4];self.result['layout']['kind']='source_image';self.result['source_images']=[self.asset]
 def tearDown(self):self.tmp.cleanup()
 def native(self):return [{'text':'','heading_texts':[s['title'],s['subtitle']],'objects':{'chart':0,'table':0,'image':len(s.get('source_images',[]))+(1 if s['section_key'] in ['cover','authors'] else 0)},'image_sha256':[self.asset['sha256']]}for s in self.data['slides']]
 def test_valid_source_style_and_portable_pdf(self):
  self.assertEqual(v.validate(self.data,self.base,self.native()),['table.png','source.pdf'])
 def test_two_character_major_title(self):
  self.bg['title']='研究背景'
  with self.assertRaisesRegex(ValueError,'两个汉字'):v.validate(self.data,self.base)
 def test_subtitle_required(self):
  self.bg.pop('subtitle')
  with self.assertRaisesRegex(ValueError,'小标题'):v.validate(self.data,self.base)
 def test_third_native_heading_rejected(self):
  actual=self.native();actual[2]['heading_texts'].append('第三层标题')
  with self.assertRaisesRegex(ValueError,'两级'):v.validate(self.data,self.base,actual)
 def test_native_table_rejected(self):
  actual=self.native();actual[4]['objects']['table']=1
  with self.assertRaisesRegex(ValueError,'原文图片'):v.validate(self.data,self.base,actual)
 def test_native_chart_rejected(self):
  actual=self.native();actual[4]['objects']['chart']=1
  with self.assertRaisesRegex(ValueError,'原文图片'):v.validate(self.data,self.base,actual)
 def test_redrawn_image_origin_rejected(self):
  self.asset['origin']='redrawn'
  with self.assertRaisesRegex(ValueError,'原始图片'):v.validate(self.data,self.base)
 def test_source_pdf_binding_checked(self):
  (self.base/'source.pdf').write_bytes(b'%PDF-1.4 changed')
  with self.assertRaisesRegex(ValueError,'PDF 已变化'):v.validate(self.data,self.base)
 def test_screenshot_binding_checked(self):
  (self.base/'table.png').write_bytes((self.base/'table.png').read_bytes()+b'x')
  with self.assertRaisesRegex(ValueError,'图片已变化'):v.validate(self.data,self.base)
 def test_source_image_must_be_in_actual_pptx(self):
  actual=self.native();actual[4]['image_sha256']=[]
  with self.assertRaisesRegex(ValueError,'实际 PPTX'):v.validate(self.data,self.base,actual)
 def test_background_bullets_rejected(self):
  self.bg['layout']['paragraphs']=['• 研究背景']
  with self.assertRaisesRegex(ValueError,'连续叙述'):v.validate(self.data,self.base)
 def test_missing_background_progress_rejected(self):
  self.bg['background_coverage']=['keywords','study_question']
  with self.assertRaisesRegex(ValueError,'研究进展'):v.validate(self.data,self.base)
 def test_missing_method_workflow_rejected(self):
  self.data['slides'][3]['method_coverage']=['participants','interventions','outcomes','statistics']
  with self.assertRaisesRegex(ValueError,'研究流程'):v.validate(self.data,self.base)
 def test_native_bullet_list_rejected(self):
  actual=self.native();actual[2]['bullet_count']=1
  with self.assertRaisesRegex(ValueError,'连续段落'):v.validate(self.data,self.base,actual)
 def test_unregistered_image_rejected(self):
  actual=self.native();actual[3]['objects']['image']=1
  with self.assertRaisesRegex(ValueError,'逐一对应'):v.validate(self.data,self.base,actual)
 def test_old_record_compatible(self):
  self.data['deck'].pop('style_policy');self.assertEqual(v.validate(self.data,self.base),[])
 def pdf_image(self):
  self.asset.update(origin='pdf_image',image_index=1,image_name='Im1.png',source_pixel_size=[1,1]);self.asset.pop('source_url')
 def test_extracted_local_pdf_image_is_portable(self):
  self.pdf_image();self.assertEqual(v.validate(self.data,self.base,self.native()),['table.png','source.pdf'])
 def test_local_pdf_crop_accepts_file_provenance(self):
  self.asset.pop('source_url');v.validate(self.data,self.base,self.native())
 def test_rotated_pdf_crop_keeps_source_binding(self):
  self.asset['page_rotation']=90;v.validate(self.data,self.base,self.native())
 def test_invalid_pdf_rotation_is_rejected(self):
  self.asset['page_rotation']=45
  with self.assertRaisesRegex(ValueError,'旋转角度'):v.validate(self.data,self.base)
 def test_pdf_image_source_hash_is_checked(self):
  self.pdf_image();(self.base/'source.pdf').write_bytes(b'%PDF-1.4 changed')
  with self.assertRaisesRegex(ValueError,'PDF 已变化'):v.validate(self.data,self.base)
 def test_pdf_image_requires_object_locator(self):
  self.pdf_image();self.asset['image_index']=0
  with self.assertRaisesRegex(ValueError,'图像序号'):v.validate(self.data,self.base)
 def test_web_image_still_requires_its_source_url(self):
  self.asset['origin']='article_image';self.asset.pop('source_url')
  with self.assertRaisesRegex(ValueError,'来源链接'):v.validate(self.data,self.base)
 def add_crops(self):
  self.asset['source_pixel_size']=[100,100];self.asset['crop_regions']=[[0,0,60,40],[0,40,20,100]]
  actual=self.native();actual[4]['objects']['image']=2
  actual[4]['image_crops']=[{'sha256':self.asset['sha256'],'crop':dict(zip(('l','t','r','b'),c))}for c in [(0,0,40000,60000),(0,40000,80000,0)]]
  return actual
 def test_native_crop_preserves_registered_regions(self):
  v.validate(self.data,self.base,self.add_crops())
 def test_native_crop_mismatch_rejected(self):
  actual=self.add_crops();actual[4]['image_crops'][1]['crop']['t']=0
  with self.assertRaisesRegex(ValueError,'原图裁切'):v.validate(self.data,self.base,actual)
 def test_crop_outside_original_rejected(self):
  self.add_crops();self.asset['crop_regions'][0][2]=101
  with self.assertRaisesRegex(ValueError,'原图范围'):v.validate(self.data,self.base)
 def test_available_flow_belongs_on_first_methods_slide(self):
  self.data['literature']={'flow_diagram':{'status':'available','file':'table.png'}}
  m=self.data['slides'][3];m['layout']['kind']='source_flow';m['source_images']=[copy.deepcopy(self.asset)]
  v.validate(self.data,self.base,self.native())
 def test_available_flow_missing_from_methods_rejected(self):
  self.data['literature']={'flow_diagram':{'status':'available','file':'table.png'}}
  with self.assertRaisesRegex(ValueError,'方法部分第一页'):v.validate(self.data,self.base)
 def test_flow_on_later_methods_slide_rejected(self):
  self.data['literature']={'flow_diagram':{'status':'available','file':'table.png'}}
  later=copy.deepcopy(self.data['slides'][3]);later['id']='methods2';later['layout']['kind']='source_flow';later['source_images']=[copy.deepcopy(self.asset)];self.data['slides'].insert(4,later)
  with self.assertRaisesRegex(ValueError,'方法部分第一页'):v.validate(self.data,self.base)
 def test_flow_search_without_figure_keeps_prose(self):
  self.data['literature']={'flow_diagram':{'status':'not_found','searched_locations':['main_text','graphical_abstract']}}
  v.validate(self.data,self.base,self.native())
 def whole_flow(self):
  self.data['literature']={'flow_diagram':{'status':'available','file':'table.png','display':'whole_image'}}
  m=self.data['slides'][3];m['layout']['kind']='source_full';m['source_images']=[copy.deepcopy(self.asset)]
  actual=self.native();actual[3]['image_crops']=[{'sha256':self.asset['sha256'],'crop':dict.fromkeys(('l','t','r','b'),0)}]
  return actual
 def test_whole_flow_is_one_uncropped_picture(self):
  v.validate(self.data,self.base,self.whole_flow())
 def test_whole_flow_rejects_region_selection(self):
  self.whole_flow();a=self.data['slides'][3]['source_images'][0];a['source_pixel_size']=[100,100];a['crop_regions']=[[0,0,80,80]]
  with self.assertRaisesRegex(ValueError,'完整原图'):v.validate(self.data,self.base)
 def test_whole_flow_rejects_native_crop(self):
  actual=self.whole_flow();actual[3]['image_crops'][0]['crop']['r']=10000
  with self.assertRaisesRegex(ValueError,'完整原图'):v.validate(self.data,self.base,actual)
 def test_editable_cover_checks_native_paper_title(self):
  self.data['literature']={'paper_title':'A Full Paper Title'}
  cover=self.data['slides'][0];cover['layout']['title_mode']='editable_title';cover['subtitle']=''
  actual=self.native();actual[0]['heading_texts']=['A Full\nPaper Title']
  v.validate(self.data,self.base,actual)
  actual[0]['heading_texts']=[]
  with self.assertRaisesRegex(ValueError,'可编辑文献题名'):v.validate(self.data,self.base,actual)
 def test_image_title_cover_has_no_native_headings(self):
  cover=self.data['slides'][0];cover['layout']['title_mode']='source_image';cover['subtitle']=''
  actual=self.native();actual[0]['heading_texts']=[]
  v.validate(self.data,self.base,actual)
 def test_added_heading_on_image_title_cover_rejected(self):
  self.data['slides'][0]['layout']['title_mode']='source_image'
  with self.assertRaisesRegex(ValueError,'封面'):v.validate(self.data,self.base,self.native())
 def test_cover_title_mode_does_not_hide_body_headings(self):
  self.bg['layout']['title_mode']='source_image';actual=self.native();actual[2]['heading_texts']=[]
  with self.assertRaisesRegex(ValueError,'两级'):v.validate(self.data,self.base,actual)
 def test_familiar_terms_need_no_glossary(self):
  self.bg['background_coverage']=['progress','study_question']
  v.validate(self.data,self.base,self.native())
 def test_study_question_still_required(self):
  self.bg['background_coverage']=['progress']
  with self.assertRaisesRegex(ValueError,'本文研究问题'):v.validate(self.data,self.base)
if __name__=='__main__':unittest.main(verbosity=2)
