import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import focus_plan as f
class FocusTests(unittest.TestCase):
 def setUp(self):
  slides=[{'id':k,'section_key':k,'title':t,'subtitle':'主题','emphasis':'core','talk_time_sec':80,'focus_links':[domain]}for k,t,domain in [('background','背景','question'),('methods','方法','method'),('results','结果','visual'),('discussion','讨论','interpretation')]]
  slides +=[{'id':'advantages','section_key':'advantages','title':'亮点','emphasis':'standard','talk_time_sec':40,'focus_links':[]},{'id':'disadvantages','section_key':'disadvantages','title':'局限','emphasis':'standard','talk_time_sec':40,'focus_links':[]},{'id':'reflection','section_key':'reflection','title':'感想','emphasis':'brief','talk_time_sec':20,'focus_links':[]}]
  entries=[{'id':dom,'domain':dom,'novelty':'incremental'if dom=='question'else'established','quality':'strong','priority':'primary'if dom=='question'else'secondary','claim':'具体贡献','what_new':'已有工作的增量','what_well':'具体的完成质量','why_it_matters':'回答研究问题','evidence':[{'source_id':'paper','locator':'Figure 2'if dom=='visual'else'Methods'}],'comparisons':[{'source_id':'prior','year':2010,'difference':'扩大比较范围'}]if dom=='question'else[],'slide_ids':[section]}for dom,section in [('question','background'),('method','methods'),('interpretation','discussion'),('visual','results')]]
  self.d={'deck':{'focus_policy':f.POLICY},'sources':[{'id':'paper','citation':'测试论文'},{'id':'prior','citation':'既往测试论文'}],'slides':slides,'literature':{'paper_title':'测试论文','focus_plan':{'publication_year':2013,'narrative_priority':'重点解释研究问题与贡献','assessments':entries}}}
 def test_valid_and_readable_export(self):f.validate(self.d);self.assertIn('图表表达',f.render_text(self.d))
 def test_missing_visual_review_rejected(self):
  self.d['literature']['focus_plan']['assessments'].pop()
  with self.assertRaisesRegex(ValueError,'覆盖'):f.validate(self.d)
 def test_newness_requires_prior_comparison(self):
  self.d['literature']['focus_plan']['assessments'][0]['comparisons']=[]
  with self.assertRaisesRegex(ValueError,'已有研究'):f.validate(self.d)
 def test_future_comparison_rejected(self):
  self.d['literature']['focus_plan']['assessments'][0]['comparisons'][0]['year']=2020
  with self.assertRaisesRegex(ValueError,'同期比较'):f.validate(self.d)
 def test_primary_highlight_must_change_emphasis(self):
  self.d['slides'][0]['emphasis']='brief'
  with self.assertRaisesRegex(ValueError,'重点讲述'):f.validate(self.d)
 def test_new_labels_required(self):
  self.d['slides'][4]['title']='优势'
  with self.assertRaisesRegex(ValueError,'文章亮点'):f.validate(self.d)
 def test_legacy_record_is_compatible(self):f.validate({'deck':{}})
if __name__=='__main__':unittest.main(verbosity=2)
