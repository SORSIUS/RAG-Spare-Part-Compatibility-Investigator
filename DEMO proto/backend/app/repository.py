import json
import threading
from pathlib import Path
from datetime import datetime, timezone

class Repository:
    def __init__(self, data_dir):
        self.directory = Path(data_dir)
        self.sample = json.loads((self.directory / 'sample' / 'records.json').read_text(encoding='utf-8'))
        self.path = self.directory / 'runtime' / 'state.json'
        self.lock = threading.RLock()
        self.state = json.loads(self.path.read_text()) if self.path.exists() else {'revision': 0, 'commits': []}

    def snapshot(self):
        with self.lock:
            return json.loads(json.dumps(self.state))

    def save(self, proposal, revision):
        with self.lock:
            if revision != self.state['revision']:
                raise ValueError('Records changed after this proposal. Run the workflow again.')
            if any(p['id'] == proposal['id'] for p in self.state['commits']):
                raise ValueError('This proposal was already confirmed.')
            self.state['commits'].append({**proposal, 'confirmed_at': datetime.now(timezone.utc).isoformat()})
            self.state['revision'] += 1
            self._persist()
            return self.snapshot()

    def reset(self):
        with self.lock:
            self.state = {'revision': self.state['revision'] + 1, 'commits': []}
            self._persist()
            return self.snapshot()

    def _persist(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.state, indent=2), encoding='utf-8')
        temporary.replace(self.path)
