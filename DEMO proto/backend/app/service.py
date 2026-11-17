from .comparison import compare_parts

class DemoService:
    def __init__(self,repository,config):self.repository=repository;self.config=config

    def public_project(self):
        return {**self.config,'comparison':compare_parts(self.repository.sample,'FAN-12')}

    def run(self,payload):
        if not isinstance(payload,dict):raise ValueError('Expected a JSON object.')
        original=payload.get('query','FAN-12');bulletin=payload.get('bulletin',False)
        if not isinstance(original,str) or len(original)>50:raise ValueError('Choose a valid original part.')
        if not isinstance(bulletin,bool):raise ValueError('The bulletin option must be true or false.')
        return compare_parts(self.repository.sample,original,bulletin)

    def confirm(self,proposal_id):raise ValueError('This investigation is read-only; it does not approve installation.')
    def reset(self):return self.repository.reset()
