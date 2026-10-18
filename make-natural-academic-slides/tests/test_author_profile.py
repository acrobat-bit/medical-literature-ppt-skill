#!/usr/bin/env python3
import copy
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import author_profile as ap

class AuthorProfileTests(unittest.TestCase):
    def setUp(self):
        self.sources={'paper':{'identity_status':'verified','doi':'10.1/current'},'work-a':{'identity_status':'verified','doi':'10.1/a'},'work-b':{'identity_status':'verified','doi':'10.1/b'}}
        def candidate(name,sid):
            return {'name':name,'publication_name':name,'publications':[{'source_id':sid,'title':'Published research','display_title':'发表题名','journal':'Journal','year':2025,'author_name':name,'author_role':'第一作者','identity_evidence':['作者全名一致','机构与共同作者匹配'],'status':'verified'}],'research_areas':[{'label':'研究领域','publication_ids':[sid]}]}
        self.config={'author_policy':ap.POLICY,'paper_source_id':'paper','first_author_name':'First Author','corresponding_author_names':['Corresponding Author'],'author_candidates':[candidate('First Author','work-a'),candidate('Corresponding Author','work-b')],'author_search':[{'author_name':'First Author','source':'PubMed','query':'First Author AND institution','searched_at':'2026-10-17','status':'completed'},{'author_name':'First Author','source':'Institution website','query':'First Author publications','searched_at':'2026-10-17','status':'completed'}]}
    def configure(self):
        ap.configure(self.config,self.sources);ap.validate(self.config,self.sources)
    def fallback(self):
        self.config['author_candidates'][0]['publications']=[];self.configure()
    def test_first_author_selected_when_both_have_publications(self):
        self.configure();self.assertEqual(len(self.config['authors']),1);self.assertEqual(self.config['authors'][0]['publication_name'],'First Author')
    def test_corresponding_author_selected_after_first_author_search(self):
        self.fallback();self.assertEqual(self.config['author_selection']['role'],'corresponding_author')
    def test_current_reported_paper_does_not_count_as_other_work(self):
        self.config['author_candidates'][0]['publications'][0]['source_id']='paper';self.configure();self.assertEqual(self.config['author_selection']['role'],'corresponding_author')
    def test_duplicate_current_doi_does_not_count_as_other_work(self):
        self.sources['work-a']['doi']='10.1/current';self.configure();self.assertEqual(self.config['author_selection']['role'],'corresponding_author')
    def test_coauthored_work_keeps_first_author_profile(self):
        self.config['author_candidates'][0]['publications'][0]['author_role']='共同作者';self.configure();self.assertEqual(self.config['author_selection']['role'],'first_author')
    def test_fallback_requires_supplementary_search(self):
        self.config['author_candidates'][0]['publications']=[];self.config['author_search']=self.config['author_search'][:1];ap.configure(self.config,self.sources)
        with self.assertRaisesRegex(ValueError,'补充检索'):ap.validate(self.config,self.sources)
    def test_wrong_corresponding_author_rejected(self):
        self.fallback();self.config['corresponding_author_names']=['Someone Else']
        with self.assertRaisesRegex(ValueError,'本文通讯作者'):ap.validate(self.config,self.sources)
    def test_multiple_people_rejected(self):
        self.configure();self.config['authors'].append(copy.deepcopy(self.config['authors'][0]))
        with self.assertRaisesRegex(ValueError,'一位作者'):ap.validate(self.config,self.sources)
    def test_wrong_person_publication_rejected(self):
        self.configure();self.config['authors'][0]['publications'][0]['author_name']='Namesake'
        with self.assertRaisesRegex(ValueError,'姓名'):ap.validate(self.config,self.sources)
    def test_identity_evidence_required(self):
        self.configure();self.config['authors'][0]['publications'][0]['identity_evidence']=['Name only']
        with self.assertRaisesRegex(ValueError,'归属依据'):ap.validate(self.config,self.sources)
    def test_unverified_publication_rejected(self):
        self.configure();self.config['authors'][0]['publications'][0]['status']='unverified'
        with self.assertRaisesRegex(ValueError,'已核对'):ap.validate(self.config,self.sources)
    def test_research_theme_must_link_to_verified_work(self):
        self.configure();self.config['authors'][0]['research_areas'][0]['publication_ids']=['unmatched']
        with self.assertRaisesRegex(ValueError,'关联'):ap.validate(self.config,self.sources)
    def test_profile_claims_must_appear_in_pptx(self):
        self.configure()
        with self.assertRaisesRegex(ValueError,'实际 PPTX'):ap.validate(self.config,self.sources,native={'text':'Author only'})
        ap.validate(self.config,self.sources,native={'text':'研究领域 发表题名'})
    def test_invented_first_author_work_list_rejected(self):
        self.configure();self.config['author_selection']['first_author_verified_other_works']=['work-b']
        with self.assertRaisesRegex(ValueError,'清单'):ap.validate(self.config,self.sources)
    def test_old_record_keeps_existing_validation_path(self):
        ap.validate({'authors':[]},{})

if __name__=='__main__':unittest.main(verbosity=2)
