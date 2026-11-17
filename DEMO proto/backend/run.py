import argparse
import json
from pathlib import Path
from http.server import ThreadingHTTPServer
from app.repository import Repository
from app.service import DemoService
from app.api import make_handler

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8000)
    args = parser.parse_args()
    base = Path(__file__).resolve().parent
    config = json.loads((base / 'data' / 'sample' / 'project.json').read_text(encoding='utf-8'))
    service = DemoService(Repository(base / 'data'), config)
    server = ThreadingHTTPServer(('127.0.0.1', args.port), make_handler(service))
    print('READY_PORT=' + str(server.server_port), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()

if __name__ == '__main__':
    main()
