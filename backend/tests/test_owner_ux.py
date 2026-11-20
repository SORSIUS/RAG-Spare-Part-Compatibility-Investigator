import tempfile
import unittest
from pathlib import Path
from app.repositories.conversations import ConversationRepository
from app.services.vehicle_questions import needs_vehicle_details
from app.services.passage_quality import substantive
from app.services.parts_overview import overview
from app.models.chat import GeneratedAnswer
from app.core.settings import Settings

class OwnerUxRegressionTests(unittest.TestCase):
 def test_deleted_chat_can_be_restored_with_messages_intact(self):
  with tempfile.TemporaryDirectory() as folder:
   repo=ConversationRepository(Path(folder)/'chats.db')
   message=repo.append(None,'My brake question',{'claims':[]})
   key=message['conversation_id']
   self.assertTrue(repo.set_deleted(key));self.assertEqual(repo.list(),[]);self.assertIsNone(repo.get(key))
   self.assertTrue(repo.set_deleted(key,False));self.assertEqual(repo.get(key)['messages'][0]['question'],'My brake question')

 def test_single_car_brake_compatibility_does_not_trigger_suspension_swap(self):
  self.assertFalse(needs_vehicle_details('which brakes should I use in my corolla 1.8 2012? and which brakes are compatible with it?'))
  self.assertTrue(needs_vehicle_details('Can I swap Corolla suspension into a City?'))

 def test_contents_pages_are_not_substantive_evidence(self):
  self.assertFalse(substantive('Driving the vehicle ........ 120\nEngine ignition ........ 132\nBrake system ........ 145 '+('contents '*20)))
  self.assertTrue(substantive('The cabin air filter removes dust from air entering the cabin through the ventilation system. Check the manufacturer reference for the correct replacement for your vehicle.'))

 def test_parts_explanation_is_generated_once_and_cached_without_false_citations(self):
  class Library:
   def cached_search(self,query,limit):
    return [{'document_id':'b'*64,'source':'brakes.pdf','page_number':4,'content':'Brake pads press against the brake disc to slow the wheel. Check the exact vehicle version before selecting replacement pads. This general explanation does not establish vehicle-specific fitment.','pdf_url':'/api/documents/'+('b'*64)+'/pdf#page=4'}]
  class Client:
   calls=0
   def __init__(self,settings):pass
   def generate(self,question,sources,history):
    Client.calls+=1
    return GeneratedAnswer(insufficient_evidence=True,claims=[{'text':'Pads press against a disc.','citations':[{'source_id':sources[0]['id'],'quote':sources[0]['content']}]}],general_guidance='Brakes slow your car.',unknowns=['Exact fit is not established.'],follow_up_questions=[]),{'total_tokens':100}
  settings=Settings(api_key='test-key')
  body={'category':'brakes','make':'TestMake','model':'CacheTest'}
  first=overview(Library(),settings,Client,body);second=overview(Library(),settings,Client,body)
  self.assertEqual(Client.calls,1);self.assertTrue(first['claims']);self.assertTrue(second['cached']);self.assertEqual(second['usage'],{})
