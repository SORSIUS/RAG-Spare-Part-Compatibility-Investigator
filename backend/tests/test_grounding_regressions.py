import unittest
from app.models.chat import GeneratedAnswer
from app.services.answer_guardrails import guard_answer,clean_general
from app.services.passage_quality import category_sources

class GroundingRegressionTests(unittest.TestCase):
 def answer(self,**changes):
  return GeneratedAnswer(**{'insufficient_evidence':False,'claims':[],'general_guidance':'','unknowns':[],'follow_up_questions':[],**changes})
 def test_screenshot_vehicle_details_are_removed_but_definition_remains(self):
  text='Brake pads press against the brake disc to slow the wheel. For a 2012 Toyota Corolla 1.8 the front wheels have disc brakes. The rear may have drums depending on the market. The same pad model fits both ABS and non-ABS setups. Check chassis E150.'
  result=guard_answer(self.answer(general_guidance=text,follow_up_questions=['What year?']),[], 'Toyota Corolla 2012 1.8 Pakistan brake pads')
  self.assertIn('Brake pads press',result.general_guidance)
  for token in ('2012','Corolla','rear','same pad','E150'):self.assertNotIn(token,result.general_guidance)
  self.assertTrue(result.insufficient_evidence);self.assertEqual(result.follow_up_questions,[])
 def test_uncited_vehicle_claim_is_not_rescued_by_a_generic_quote(self):
  quote='Brake pads press against a disc to slow a wheel. Select replacement parts from the manufacturer application.'
  result=guard_answer(self.answer(claims=[{'text':'The Corolla uses front disc brakes.','citations':[{'source_id':'S1','quote':quote}]}],general_guidance='Brake pads slow wheels.'),[{'id':'S1','content':quote,'evidence_scope':'general_reference'}],'Corolla brakes')
  self.assertEqual(result.claims,[]);self.assertTrue(result.insufficient_evidence)
 def test_generic_education_and_documented_candidate_are_preserved(self):
  quote='Toyota Corolla front shock absorber KYB 339175; application conditions must be checked.'
  result=guard_answer(self.answer(claims=[{'text':'The document lists a front shock absorber candidate for Toyota Corolla: KYB 339175.','citations':[{'source_id':'S1','quote':quote}]}],general_guidance='Shock absorbers dampen suspension movement.'),[{'id':'S1','content':quote,'section':'vehicle_part_link'}],'Toyota Corolla suspension')
  self.assertEqual(len(result.claims),1);self.assertEqual(result.general_guidance,'Shock absorbers dampen suspension movement.')
 def test_vehicle_matching_beats_repeated_component_keywords(self):
  class Library:
   def cached_search(self,query,limit):
    return [{'source':'generic.pdf','page_number':1,'content':'Brake pads brake pads brake pads brake pads brake pads brake pads brake pads brake pads brake pads brake pads.'},{'source':'manual.pdf','page_number':9,'content':'Toyota Corolla 2012 Pakistan brake reference. This page explains braking components for the stated vehicle. Application details must still be checked before ordering any replacement.'}]
  result=category_sources(Library(),'brakes','Toyota Corolla 2012 Pakistan brakes',2)
  self.assertEqual(result[0]['source'],'manual.pdf');self.assertEqual(result[0]['evidence_scope'],'vehicle_reference');self.assertEqual(result[1]['evidence_scope'],'general_reference')
 def test_live_pad_vs_drum_error_is_removed(self):
  result=guard_answer(self.answer(general_guidance='Brake pads are the friction material that presses against the brake disc (or drum) to slow the vehicle.'),[],'Corolla brake pads')
  self.assertNotIn('(or drum)',result.general_guidance)
  self.assertIn('drum brakes use shoes',result.general_guidance)

 def test_verified_candidates_survive_a_general_only_model_answer(self):
  from app.services.answer_service import validate_citations
  source={'id':'S1','section':'vehicle_part_link','market_unconfirmed':True,'requested_market':'Pakistan','content':'Catalogue application: Toyota COROLLA; period 07/10-On; application ZRE152 1.8 L; front shock absorber; KYB NST5387L.', 'fitment':{'make':'Toyota','model':'Corolla','vehicle_label':'COROLLA','period':'07/10-On','application':'ZRE152 1.8 L','axle':'front','component':'shock_absorber','brand':'KYB','part_number':'NST5387L'}}
  result=guard_answer(self.answer(general_guidance='Suspension dampers help control movement.'),[source],'Toyota Corolla 2012 1.8 Pakistan suspension')
  self.assertIn('NST5387L',result.claims[0].text)
  self.assertIn('ZRE152 1.8 L',result.claims[0].text)
  self.assertIn('Pakistan',result.unknowns[0])
  self.assertTrue(result.insufficient_evidence)
  validate_citations(result,[source])
