import json
from http.server import BaseHTTPRequestHandler
from urllib.parse import urlsplit

def make_handler(service):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def reply(self, status, payload):
            body = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.send_header('Content-Length', str(len(body)))
            self.send_header('Cache-Control', 'no-store')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            path = urlsplit(self.path).path
            if path == '/api/project':
                self.reply(200, service.public_project())
            elif path == '/api/health':
                self.reply(200, {'status':'ok', 'mode':'local deterministic prototype', 'version':service.config.get('version', 1)})
            else:
                self.reply(404, {'error':'Unknown API route.'})

        def do_POST(self):
            try:
                size = int(self.headers.get('Content-Length', '0'))
                if size < 0 or size > 16384:
                    self.reply(413, {'error':'Request too large.'})
                    return
                payload = json.loads(self.rfile.read(size) or b'{}')
                if not isinstance(payload, dict):
                    raise ValueError('Expected a JSON object.')
                path = urlsplit(self.path).path
                if path == '/api/run':
                    self.reply(200, service.run(payload))
                elif path == '/api/confirm':
                    self.reply(200, service.confirm(str(payload.get('proposal_id', ''))))
                elif path == '/api/reset':
                    self.reply(200, {'state':service.reset()})
                else:
                    self.reply(404, {'error':'Unknown API route.'})
            except (ValueError, TypeError, KeyError) as error:
                self.reply(400, {'error':str(error)})
            except Exception:
                self.reply(500, {'error':'Unable to finish. Check the backend and try again.'})
    return Handler
